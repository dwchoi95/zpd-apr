"""Prediction-only frozen C_joint bridge for newly generated candidate banks.

The trusted exporter authenticates the old archive and extracts only scales3
and theta4099. It never decodes SCALER.y, instantiates OwnTransform, fits a
transform/model, opens labels, or executes candidate code. A generator needs
only the exported projection, not access to the archive. Its canonical hash
must be pinned in the caller's sealed job (a self-hash is not authority).

Scoring recomputes source features for every supplied bank. It does not look up
old candidate scores. Parity is a separate source-only diagnostic, not evidence
of repair correctness or promotion of the previously failed scientific gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType

import numpy as np
from scipy import sparse
from sklearn.utils.sparsefuncs import inplace_column_scale

from scripts import zpd_joint_progress_features as features
from scripts.zpd_repair_fit import Example
from src.repair.pilot_contracts import (
    CandidateAttempt, CandidateBank, ObservationSource, PilotObservation,
    canonical_hash, source_hash)

VERSION = 'frozen_c_joint_transition_score_projection_v1'
RUN = 'archive/zpd-bank-topset-run-20260925/run-v1'
COMPLETE_SHA256 = '8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf'
BUNDLE = 'archive/zpd-public-candidates-20261012/prepared-v1/bundle.json'
BUNDLE_SHA256 = 'f0f598f89367e4d879a84763996e5e09b41375a5100e1af8d37e0a235f04d849'
BANK_PINS = {
    'outputs/zpd-repair-development-20260918/run-v1/generation/banks.jsonl':
        '857410476ca9e9f0665341b1f174c7975977ded29a525e56bf02172ca07375b0',
    'outputs/zpd-repair-risk-development-20260923/run-v1/banks.jsonl':
        '3769662063e39e7115e3be83ec17d50b57fa17dc65a6c9159ada5b8f371d00fc',
}
FOLDS = 5
RECIPIENTS = 320
PARITY_ATOL = 1e-12
FOLD_FIELDS = {'fold', 'numeric_scale', 'theta', 'held_example_ids',
               'model_file_sha256', 'model_sha256', 'top_model_sha256',
               'scaler_file_sha256', 'transform_sha256'}
PROJECTION_FIELDS = {'kind', 'arm', 'archive_complete_sha256', 'numeric_names',
    'numeric_dimension', 'hash_dimension', 'current_dimension', 'offset',
    'intercept', 'folds', 'example_folds', 'projection_sha256'}


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _read_pinned(path, expected):
    require(_sha(expected), 'explicit file SHA256 required')
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected, 'file seal mismatch: ' + str(path))
    return raw


def _vector(value, size, name, *, positive=False):
    require(type(value) is list and len(value) == size
            and all(type(x) in (int, float) and math.isfinite(x) for x in value),
            'finite exact ' + name + ' vector required')
    result = np.asarray(value, dtype=np.float64)
    require(not positive or bool(np.all(result > 0)), 'positive numeric scales required')
    return result


def _check_self_hash(value, key):
    require(type(value) is dict and _sha(value.get(key))
            and value[key] == canonical_hash({k: v for k, v in value.items() if k != key}),
            'canonical seal mismatch: ' + key)


def _scales_only(authenticated_raw):
    """Decode only the scales array, never the embedded pair-label payload.

    The complete file's bytes MUST already have passed the external SHA seal;
    this extractor is not a parser/validator for untrusted arbitrary JSON.
    """
    matches = re.findall(rb'"numeric_scale"\s*:\s*(\[[^\]]*\])', authenticated_raw)
    require(len(matches) == 1, 'one authenticated numeric_scale field required')
    values = json.loads(matches[0])
    _vector(values, 3, 'numeric_scale', positive=True)
    return values


def export_projection(run_dir):
    """Authenticate pinned completed archive, then return minimal JSON payload.

    Only COMPLETE, five C_joint models and five raw SCALER files are opened.
    SCALER labels are neither JSON-decoded nor returned to the generator.
    """
    run_dir = Path(run_dir)
    complete = json.loads(_read_pinned(run_dir / 'COMPLETE.json', COMPLETE_SHA256))
    require(complete['kind'] == 'bank_topset4131_complete_v1'
            and complete['status'] == 'complete' and complete['recipients'] == RECIPIENTS
            and complete['completed_fits'] == 35, 'frozen completed archive required')
    inventory = complete['files_sha256']; folds = []; example_folds = {}
    for fold in range(FOLDS):
        model_name = f'fold-{fold}/C_joint.json'; scaler_name = f'fold-{fold}/SCALER.json'
        model = json.loads(_read_pinned(run_dir / model_name, inventory[model_name]))
        scales = _scales_only(_read_pinned(run_dir / scaler_name, inventory[scaler_name]))
        _check_self_hash(model, 'model_sha256')
        top = model['top_model']; _check_self_hash(top, 'model_sha256')
        require(model['kind'] == 'bank_topset4131_own_fold_model_v1'
                and model['arm'] == 'C_joint' and type(model['fold']) is int
                and model['fold'] == fold, 'frozen C_joint own-fold model required')
        config = top['configuration']
        require(config['dimension'] == 4131 and config['offset'] == 'absent'
                and config['intercept'] == 'not_added', 'no offset or intercept permitted')
        theta = _vector(top['coefficients'], 4131, 'coefficients')
        gradient = _vector(top['final_gradient'], 4131, 'final_gradient')
        require(not np.any(theta[4099:]) and not np.any(gradient[4099:]),
                'C_joint progress tail32 must be exactly zero')
        held = model['held_example_ids']; train = model['train_example_ids']
        require(type(held) is list and held and all(type(x) is str and x for x in held)
                and len(set(held)) == len(held) and type(train) is list
                and len(set(train)) == len(train) and not set(train).intersection(held)
                and len(train) + len(held) == RECIPIENTS, 'disjoint complete train/held scope required')
        for example_id in held:
            require(example_id not in example_folds, 'duplicate held example across folds')
            example_folds[example_id] = fold
        folds.append(dict(fold=fold, numeric_scale=scales, theta=theta[:4099].tolist(),
            held_example_ids=list(held), model_file_sha256=inventory[model_name],
            scaler_file_sha256=inventory[scaler_name], model_sha256=model['model_sha256'],
            top_model_sha256=top['model_sha256'], transform_sha256=model['transform_sha256']))
    result = dict(kind=VERSION, arm='C_joint', archive_complete_sha256=COMPLETE_SHA256,
        numeric_names=list(features.NUMERIC_NAMES), numeric_dimension=3, hash_dimension=4096,
        current_dimension=4099, offset=False, intercept=False, folds=folds,
        example_folds=example_folds)
    result['projection_sha256'] = canonical_hash(result)
    validate_projection(result)
    return result


def validate_projection(value, *, expected_sha256=None):
    """Check a strict detached projection; caller pins expected_sha256 at release."""
    require(type(value) is dict and set(value) == PROJECTION_FIELDS, 'exact projection fields required')
    _check_self_hash(value, 'projection_sha256')
    require(expected_sha256 is None or (_sha(expected_sha256)
            and value['projection_sha256'] == expected_sha256), 'external projection SHA mismatch')
    require(value['kind'] == VERSION and value['arm'] == 'C_joint'
            and value['archive_complete_sha256'] == COMPLETE_SHA256
            and value['numeric_names'] == list(features.NUMERIC_NAMES)
            and (value['numeric_dimension'], value['hash_dimension'], value['current_dimension']) == (3, 4096, 4099)
            and value['offset'] is False and value['intercept'] is False,
            'frozen current-only prediction configuration required')
    folds = value['folds']; mapping = {}
    require(type(folds) is list and len(folds) == FOLDS, 'all five ordered folds required')
    for index, fold in enumerate(folds):
        require(type(fold) is dict and set(fold) == FOLD_FIELDS
                and type(fold['fold']) is int and fold['fold'] == index, 'strict ordered fold projection required')
        _vector(fold['numeric_scale'], 3, 'numeric_scale', positive=True)
        _vector(fold['theta'], 4099, 'theta')
        require(all(_sha(fold[k]) for k in FOLD_FIELDS if k.endswith('sha256')), 'fold provenance hashes required')
        held = fold['held_example_ids']
        require(type(held) is list and held and all(type(x) is str and x for x in held), 'held example IDs required')
        for example_id in held:
            require(example_id not in mapping, 'unique held example assignment required')
            mapping[example_id] = index
    require(type(value['example_folds']) is dict and len(mapping) == RECIPIENTS
            and all(type(x) is int for x in value['example_folds'].values())
            and value['example_folds'] == mapping, 'exact full held example/fold mapping required')
    return value['projection_sha256']


class FrozenScorer:
    """Validated immutable prediction state; no archive/file access during scoring."""

    def __init__(self, projection, *, expected_sha256=None):
        self.projection_sha256 = validate_projection(projection, expected_sha256=expected_sha256)
        self.example_folds = MappingProxyType(dict(projection['example_folds']))
        self._folds = tuple((np.frombuffer(np.asarray(f['numeric_scale'], dtype='float64').tobytes(), dtype='float64'),
                            np.frombuffer(np.asarray(f['theta'], dtype='float64').tobytes(), dtype='float64'))
                           for f in projection['folds'])

    def score_bank(self, example, bank):
        """Score arbitrary NEW bank candidates for an authenticated held recipient.

        The caller authenticates recipient source/problem and generation ledger.
        Bank IDs do not enter features; a new bank need not retain the old seal.
        Observation/current bytes must match. History and verdicts are unused.
        """
        require(type(example) is Example and type(bank) is CandidateBank, 'exact Example and CandidateBank required')
        require(example.example_id in self.example_folds, 'example absent from held fold mapping')
        scale, theta = self._folds[self.example_folds[example.example_id]]
        raw = features.raw_current(example, bank)
        numeric = raw.numeric.copy()
        with np.errstate(over='raise', divide='raise', invalid='raise'):
            inplace_column_scale(numeric, 1 / scale)
            current = sparse.hstack([numeric, raw.hashed], format='csr')
            scores = np.asarray(current @ theta).ravel()
        require(np.isfinite(scores).all(), 'finite source-derived scores required')
        return dict(zip(raw.candidate_ids, map(float, scores), strict=True))


def score_bank(projection, example, bank, *, expected_sha256=None):
    return FrozenScorer(projection, expected_sha256=expected_sha256).score_bank(example, bank)


def verify_oof_parity(projection, examples, banks, saved_rows, *, expected_candidates=2544):
    """Recompute ALL source-derived held scores; never accept a sampled subset.

    saved_rows uses archived predictions.json schema and must be authenticated
    by the caller. This verifies scoring only; no outcomes/labels are consulted.
    """
    scorer = FrozenScorer(projection)
    examples = list(examples); rows = list(saved_rows)
    by_id = {ex.example_id: ex for ex in examples}; saved = {row['example_id']: row for row in rows}
    require(len(examples) == len(by_id) == len(rows) == len(saved) == RECIPIENTS
            and set(by_id) == set(saved) == set(scorer.example_folds), 'complete unique OOF recipient coverage required')
    require(type(banks) is dict and set(banks) == {ex.bank_id for ex in examples}, 'exact OOF bank scope required')
    differences = []; replay = []; exact = 0
    for example_id, ex in by_id.items():
        row = saved[example_id]; bank = banks[ex.bank_id]
        require(row['fold'] == scorer.example_folds[example_id] and row['bank_id'] == ex.bank_id
                and row['user_id'] == ex.user_id and row['problem_id'] == bank.problem_id
                and row['bank_seal_sha256'] == bank.seal_sha256, 'OOF source/bank/fold identity differs')
        scores = scorer.score_bank(ex, bank); prior = row['candidate_scores']['C_joint']
        require(type(prior) is dict and set(scores) == set(prior)
                and all(type(v) in (int, float) and math.isfinite(v) for v in prior.values()),
                'exact finite OOF candidate score coverage required')
        for cid, value in scores.items():
            delta = abs(value - prior[cid]); differences.append(delta); exact += value == prior[cid]
            require(delta <= PARITY_ATOL, 'source-derived score parity failure: ' + example_id + '/' + cid)
        choice = min(scores, key=lambda cid: (-scores[cid], cid))
        require(choice == row['choices']['C_joint'], 'deterministic OOF argmax differs')
        replay.append(dict(example_id=example_id, bank_seal_sha256=bank.seal_sha256, scores=scores, choice=choice))
    require(type(expected_candidates) is int and len(differences) == expected_candidates,
            'full expected candidate membership count required')
    report = dict(kind='frozen_c_joint_source_score_parity_v1', status='passed',
        projection_sha256=scorer.projection_sha256, examples=len(examples),
        candidate_memberships=len(differences), exact_scores=exact,
        maximum_absolute_difference=max(differences), absolute_tolerance=PARITY_ATOL,
        matching_argmaxes=len(replay), replay_sha256=canonical_hash(replay),
        private_labels_opened=False, fitting_performed=False, candidate_execution=False,
        stored_scores_used_for_prediction=False)
    report['parity_sha256'] = canonical_hash(report)
    return report


def load_parity_inputs(project):
    """Pinned public bundle + original bank ledgers + saved predictions, no labels."""
    project = Path(project)
    bundle = json.loads(_read_pinned(project / BUNDLE, BUNDLE_SHA256))
    complete = json.loads(_read_pinned(project / RUN / 'COMPLETE.json', COMPLETE_SHA256))
    rows = json.loads(_read_pinned(project / RUN / 'predictions.json', complete['files_sha256']['predictions.json']))
    cohort = {row['example_id']: row for row in bundle['cohort']}
    require(len(cohort) == len(bundle['cohort']) == RECIPIENTS, 'complete public source cohort required')
    bank_ids = {row['bank_id'] for row in cohort.values()}; banks = {}
    for name, pin in BANK_PINS.items():
        require(bundle['input_sha256'][name] == pin, 'bundle original bank seal differs')
        for line in _read_pinned(project / name, pin).splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row['bank_id'] not in bank_ids:
                continue
            require(row['bank_id'] not in banks, 'duplicate original bank')
            attempts = tuple(CandidateAttempt(**dict(a, source=a['source'].encode('utf-8')
                if a['source'] is not None else None)) for a in row['attempts'])
            banks[row['bank_id']] = CandidateBank(row['problem_id'], row['current_source'].encode('utf-8'),
                row['generator_config_sha256'], tuple(row['seeds']), attempts)
    require(set(banks) == bank_ids, 'all original banks required')
    examples = []
    for row in rows:
        public = cohort[row['example_id']]; bank = banks[row['bank_id']]
        require(all(row[k] == public[k] for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold'))
                and row['candidate_scores']['C_joint'] == public['scores']['C_joint'], 'public OOF identity/scores differ')
        candidates = {c.candidate_id: c.source for c in bank.candidates}
        require(set(candidates) == set(public['candidate_ids']) == set(public['task_ids'])
                and source_hash(bank.current_source) == public['noop_candidate_id'], 'public candidate/current scope differs')
        for cid, source in candidates.items():
            task = bundle['tasks'][public['task_ids'][cid]]
            require(task['identity'] == [bank.problem_id, cid, 'Python']
                    and bytes.fromhex(task['source_hex']) == source, 'public candidate source bytes differ')
        # Metadata placeholders are explicitly not observed outcomes. None is
        # a C feature; raw_current receives only current bytes and empty history.
        current = ObservationSource(row['example_id'], 0, bank.current_source,
                                    source_hash(bank.current_source), 'UNUSED_SOURCE_ONLY')
        examples.append(Example(row['example_id'], row['user_id'], 'valid', row['bank_id'],
                                PilotObservation(bank.problem_id, current, ()), ()))
    return examples, banks, rows


def prepare_stage(project, output):
    """Write a new sealed projection/parity stage, refusing every overwrite."""
    project, output = Path(project), Path(output)
    require(not output.exists(), 'scorer stage exists; no overwrite')
    projection = export_projection(project / RUN)
    parity = verify_oof_parity(projection, *load_parity_inputs(project))
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, value in (('projection.json', projection), ('parity.json', parity)):
        raw = encoded(value)
        with (output / name).open('xb') as stream:
            stream.write(raw)
        files[name] = hashlib.sha256(raw).hexdigest()
    complete = dict(kind='transition_score_bridge_complete_v1', status='complete', files_sha256=files,
        archive_complete_sha256=COMPLETE_SHA256, public_bundle_sha256=BUNDLE_SHA256,
        projection_sha256=projection['projection_sha256'], private_labels_opened=False,
        fitting_performed=False, candidate_execution=False, model_promotion=False)
    with (output / 'COMPLETE.json').open('xb') as stream:
        stream.write(encoded(complete))
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare_stage(args.project, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
