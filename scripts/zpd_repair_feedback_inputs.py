"""Label-free input and frozen-base artifact binding for the repair residual.

No production CLI, outcome access, fitting or candidate execution. This module
only supplies observed objects and old sealed model/prediction artifacts. A
separate execution release must authorize any production use. The stage driver
independently checks supplied model membership, scores and feature contracts.
"""
import hashlib
import json
from pathlib import Path

from scripts import audit_zpd_repair_feedback_support as support
from scripts.zpd_repair_fit import Example
from scripts.zpd_repair_feedback_pairs import CandidateInteractions
from src.repair.pilot_contracts import ObservationSource, PilotObservation, source_hash

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = support.FAMILY + '/support-v1'
SUPPORT_SHA = '64d8f2a11de01ee08a2ed0ac51ac44b1ad4ec56281eaac971eadbb88cc4270d0'
TRAIN_PREFIXES = 320
BASE_SOURCE_FILES = ('scripts/zpd_repair_structure.py', 'scripts/zpd_repair_pairwise.py',
    'scripts/zpd_repair_fit.py', 'src/repair/pilot_contracts.py', 'src/repair/pilot_ranker.py')
OLD_MODELS = {v + '_' + c + '.json' for v in ('lexical', 'structural') for c in ('C', 'H', 'U')}


def _sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class ArtifactReader:
    """Fixed source/model/prediction inventory, never arbitrary manifest paths."""
    def __init__(self, project):
        self.project = Path(project).absolute()
        if self.project.resolve() != self.project:
            raise ValueError('canonical nonsymlink project required')
        self.allowed = {SUPPORT + '/' + n for n in ('COMPLETE.json', 'manifest.json', 'folds.json', 'report.json', 'STATUS.json')}
        self.allowed |= {support.PARENT + '/' + n for n in ('COMPLETE.json', 'manifest.json', 'folds.json',
                            'PREDICTIONS_COMPLETE.json', 'predictions.json')}
        self.allowed |= {support.PARENT + f'/fold-{f}/' + n for f in range(5)
                         for n in ('COMPLETE.json', 'MODELS_COMPLETE.json', 'predictions.json', 'structural_C.json', 'lexical_C.json')}
        self.bindings = {}

    def read(self, relative, expected):
        if relative not in self.allowed:
            raise ValueError('artifact outside fixed label-free inventory: ' + str(relative))
        path = self.project / relative
        if path.resolve() != path or not path.is_file():
            raise ValueError('missing or aliased label-free artifact')
        data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest()
        if digest != expected or relative in self.bindings and self.bindings[relative] != digest:
            raise ValueError('label-free artifact hash mismatch: ' + relative)
        self.bindings[relative] = digest
        return json.loads(data.decode('utf-8', errors='strict'))

    def recheck(self):
        for name, digest in list(self.bindings.items()):
            path = self.project / name
            if path.resolve() != path or _sha(path) != digest:
                raise ValueError('label-free input changed before completion: ' + name)


def observed_examples(observations):
    """Restore typed exact-byte examples from the certified observed join."""
    result = []
    for row in observations:
        if type(row) is not dict or set(row) != support.OBSERVATION_FIELDS:
            raise ValueError('strict certified observation fields required')
        ids = row['observed_source_ids']; donors = row['donor_source_ids']
        if (not ids or ids[0] != row['example_id'] or len(ids) != len(row['history']) + 1
                or len(donors) != len(row['donor_history'])):
            raise ValueError('exact observed identity/history alignment required')
        def source(ident, value):
            code = value['code'].encode('utf-8', errors='strict')
            return ObservationSource(submission_id=ident, timestamp=value['timestamp'],
                source=code, source_sha256=source_hash(code), verdict=value['verdict'])
        current = source(ids[0], dict(code=row['current_code'], timestamp=row['current_timestamp'], verdict=row['current_verdict']))
        if current.source_sha256 != row['current_source_sha256']:
            raise ValueError('current exact-byte source hash differs')
        prior = tuple(source(ident, value) for ident, value in zip(ids[1:], row['history']))
        donor = tuple(source(ident, value) for ident, value in zip(donors, row['donor_history']))
        observation = PilotObservation(row['problem_id'], current, prior)
        PilotObservation(row['problem_id'], current, donor)
        result.append(Example(row['example_id'], row['user_id'], 'train', row['bank_id'], observation, donor))
    return tuple(result)


def load_parent(reader, assignment):
    """Follow only the pinned parent's prediction/model completion chain."""
    parent = support.PARENT
    marker = reader.read(parent + '/COMPLETE.json', support.PARENT_SHA)
    if marker.get('status') != 'complete':
        raise ValueError('completed frozen structural parent required')
    seals = marker['files_sha256']
    manifest = reader.read(parent + '/manifest.json', seals['manifest.json'])
    if reader.read(parent + '/folds.json', seals['folds.json']) != assignment:
        raise ValueError('support and structural parent fold assignments differ')
    sources = manifest['provenance']['source_sha256']
    source_bindings = {}
    for name in BASE_SOURCE_FILES:
        if _sha(ROOT / name) != sources.get(name):
            raise ValueError('frozen base feature/scorer source differs: ' + name)
        source_bindings[name] = sources[name]
    prediction_seal = reader.read(parent + '/PREDICTIONS_COMPLETE.json', seals['PREDICTIONS_COMPLETE.json'])
    if prediction_seal['predictions_sha256'] != seals['predictions.json']:
        raise ValueError('parent OOF prediction seal mismatch')
    all_predictions = reader.read(parent + '/predictions.json', seals['predictions.json'])
    if set(prediction_seal['fold_complete_sha256']) != {str(f) for f in range(5)}:
        raise ValueError('exact five parent fold seals required')
    folds = {}; joined = []
    for fold in range(5):
        base = parent + f'/fold-{fold}/'
        complete = reader.read(base + 'COMPLETE.json', prediction_seal['fold_complete_sha256'][str(fold)])
        if complete.get('status') != 'label_blind_predictions_complete':
            raise ValueError('parent fold predictions were not sealed')
        fitted = reader.read(base + 'MODELS_COMPLETE.json', complete['models_complete_sha256'])
        if fitted['folds_sha256'] != seals['folds.json'] or set(fitted['model_files_sha256']) != OLD_MODELS:
            raise ValueError('original full model/fold seal inventory differs')
        models = {name: reader.read(base + name + '.json', fitted['model_files_sha256'][name + '.json'])
                  for name in ('structural_C', 'lexical_C')}
        predictions = reader.read(base + 'predictions.json', complete['predictions_sha256'])
        folds[fold] = dict(fold=fold, train_example_ids=tuple(fitted['train_example_ids']),
            held_example_ids=tuple(fitted['held_example_ids']), models=models, predictions=tuple(predictions))
        joined.extend(predictions)
    if sorted(joined, key=lambda p: p['example_id']) != all_predictions:
        raise ValueError('parent per-fold and global sealed predictions differ')
    return folds, source_bindings


def load_observed_components(project):
    """Load label-free components; no production fitting authority is implied."""
    reader = ArtifactReader(project)
    complete = reader.read(SUPPORT + '/COMPLETE.json', SUPPORT_SHA)
    if complete.get('status') != 'complete' or complete.get('fitting_performed') is not False:
        raise ValueError('completed observed-only support required')
    names = {'manifest.json', 'folds.json', 'report.json', 'STATUS.json'}
    if set(complete['files_sha256']) != names:
        raise ValueError('exact support seal inventory required')
    saved = {name: reader.read(SUPPORT + '/' + name, complete['files_sha256'][name]) for name in names}
    report = saved['report.json']; manifest = saved['manifest.json']
    if (report.get('variation_prerequisite') is not True or report.get('excluded_prefixes') != 0
            or report.get('totals', {}).get('prefixes') != TRAIN_PREFIXES
            or any(report.get(k) is not False for k in ('fitting_performed', 'outcomes_opened',
                   'successors_opened', 'models_opened', 'predictions_opened', 'fit_release_authorized'))):
        raise ValueError('unchanged source-only support prerequisite required')
    observations, banks, assignment, coverage, observed_reader = support.load_inputs(project)
    if (assignment != saved['folds.json'] or observed_reader.bindings != manifest['input_sha256']
            or coverage != manifest['source_coverage']):
        raise ValueError('observed input ancestry differs from the sealed support run')
    for name, digest in manifest['source_sha256'].items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name or _sha(ROOT / path) != digest:
            raise ValueError('sealed observation feature/source closure differs')
    interactions = {arm: {} for arm in support.ARMS}
    support_rows = {row['example_id']: row for row in report['rows']}
    if len(support_rows) != TRAIN_PREFIXES or set(support_rows) != {row['example_id'] for row in observations}:
        raise ValueError('exact support recipient coverage required')
    for row in observations:
        bank = banks[row['bank_id']]; saved_row = support_rows[row['example_id']]
        values, masks, matrices = support.interaction_matrices(row, bank)
        ids = tuple(c.candidate_id for c in bank.candidates)
        if saved_row['bank_seal_sha256'] != bank.seal_sha256 or [c['candidate_id'] for c in saved_row['candidates']] != list(ids):
            raise ValueError('support bank/candidate order changed')
        for arm in support.ARMS:
            block = matrices[arm]
            for i, c in enumerate(saved_row['candidates']):
                digest = hashlib.sha256(block[i].astype('<f8').tobytes()).hexdigest()
                if c['interaction_sha256'][arm] != digest or c['values'] != values[i].tolist() or c['masks'] != masks[i].tolist():
                    raise ValueError('candidate interaction differs from sealed source support')
            interactions[arm][row['bank_id']] = CandidateInteractions(ids, block, values, masks)
    parent_folds, base_sources = load_parent(reader, assignment)
    reader.recheck(); observed_reader.recheck()
    bindings = {str(reader.project / name): digest for name, digest in {**observed_reader.bindings, **reader.bindings}.items()}
    sources = {**manifest['source_sha256'], **base_sources}
    for name, digest in sources.items():
        path = ROOT / name
        if path.resolve() != path or _sha(path) != digest:
            raise ValueError('source changed before returning observed components: ' + name)
    return dict(examples=observed_examples(observations), banks=banks, assignment=assignment,
        interactions=interactions, parent_folds=parent_folds,
        # The support writer uses compact JSON while the original parent used
        # indentation. Bind the original bytes used by the label provider,
        # after checking the parsed assignments equal; do not conflate hashes.
        fold_assignment_sha256=reader.bindings[support.PARENT + '/folds.json'],
        support_complete_sha256=SUPPORT_SHA, parent_complete_sha256=support.PARENT_SHA,
        source_bindings={str(ROOT / name): digest for name, digest in sources.items()}, input_bindings=bindings)


if __name__ == '__main__':
    raise SystemExit('No production CLI: an independently reviewed execution release is required.')
