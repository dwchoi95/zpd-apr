"""Label-free directed144 input assembly; no fit or production CLI.

The fixed source-only support is replayed in full, including every unavailable
candidate/history diagnostic. Only the original frozen parent predictions and
two baseline models are opened; no new repair scores, labels or assessments.
The caller still needs a separately reviewed clean execution release.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import numpy as np

from scripts import audit_zpd_repair_directed_support as support
from scripts import audit_zpd_repair_feedback_support as observed
from scripts import zpd_repair_feedback_inputs as legacy
from scripts import zpd_repair_directed_history as directed
from scripts.zpd_repair_residual_core import CandidateBlock

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = support.FAMILY + '/support-v1'
SUPPORT_SHA = 'e04d475e3773e26ac37e277595450c7c272f0021f4f0fa2db939b96c26d62910'
FILES = frozenset(('manifest.json', 'folds.json', 'report.json', 'STATUS.json'))
COUNTS = dict(prefixes=320, users=320, problems=23, candidates=2544)
PREREQUISITES = frozenset(('edited_H_varies', 'old_equal_event_edited_split',
                         'contrast_Jm', 'contrast_HS', 'contrast_U', 'contrast_L'))
LOCAL_SOURCES = ('scripts/zpd_repair_directed_inputs.py',
                 'scripts/zpd_repair_feedback_inputs.py',
                 'scripts/zpd_repair_residual_core.py',
                 'scripts/zpd_repair_feedback_offset.py',
                 'scripts/zpd_repair_feedback_labels.py',
                 'scripts/zpd_repair_feedback_pairs.py')


def _sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _canonical_json(value):
    # Unlike Python mapping equality, this also separates booleans and numbers.
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


class SupportReader:
    """Only the pinned marker and its four fixed source-only children."""
    def __init__(self, project):
        self.project = observed._canonical(project)
        self.allowed = {SUPPORT + '/' + name for name in FILES | {'COMPLETE.json'}}
        self.bindings = {}

    def read(self, name, expected):
        if name not in self.allowed:
            raise ValueError('outside fixed directed source-only inventory: ' + str(name))
        if not _digest(expected):
            raise ValueError('external artifact SHA256 required')
        path = self.project / name
        if path.resolve() != path or not path.is_file():
            raise ValueError('missing or aliased directed support artifact')
        data = path.read_bytes(); digest = hashlib.sha256(data).hexdigest()
        if digest != expected or name in self.bindings and self.bindings[name] != digest:
            raise ValueError('directed support artifact hash mismatch: ' + name)
        self.bindings[name] = digest
        return json.loads(data.decode('utf-8', errors='strict'))

    def recheck(self):
        for name, digest in self.bindings.items():
            path = self.project / name
            if path.resolve() != path or _sha(path) != digest:
                raise ValueError('directed support changed before return: ' + name)


def _source_bindings(mapping, expected_names):
    if type(mapping) is not dict or set(mapping) != set(expected_names):
        raise ValueError('exact directed source closure required')
    result = {}
    for name, digest in mapping.items():
        if type(name) is not str:
            raise ValueError('canonical relative source/hash required')
        relative = Path(name)
        if (relative.is_absolute() or '..' in relative.parts
                or str(relative) != name or not _digest(digest)):
            raise ValueError('canonical relative source/hash required')
        path = ROOT / relative
        if path.resolve() != path or _sha(path) != digest:
            raise ValueError('sealed directed source closure differs: ' + name)
        result[name] = digest
    return result


def _merge(*mappings):
    result = {}
    for mapping in mappings:
        for key, value in mapping.items():
            if key in result and result[key] != value:
                raise ValueError('conflicting source/input binding: ' + key)
            result[key] = value
    return result


def _validate_headers(complete, saved):
    if (type(complete) is not dict or set(complete) != {'status', 'fitting_performed', 'files_sha256'}
            or complete['status'] != 'complete' or complete['fitting_performed'] is not False
            or type(complete['files_sha256']) is not dict or set(complete['files_sha256']) != FILES):
        raise ValueError('exact completed source-only support seal required')
    manifest = saved['manifest.json']; report = saved['report.json']
    required = {'source', 'source_root', 'source_sha256', 'input_sha256', 'runtime',
                'parent_complete_sha256', 'source_coverage', 'configuration', 'fitting_performed'}
    if type(manifest) is not dict or set(manifest) != required:
        raise ValueError('strict directed support manifest required')
    state = manifest['source']; source_root = manifest['source_root']
    if (type(state) is not dict or set(state) != {'revision', 'tree'}
            or any(type(x) is not str or re.fullmatch('[0-9a-f]{40}', x) is None for x in state.values())
            or type(source_root) is not str or not Path(source_root).is_absolute()
            or '..' in Path(source_root).parts or str(Path(source_root)) != source_root):
        raise ValueError('canonical sealed source revision/tree/root required')
    if (manifest['parent_complete_sha256'] != observed.PARENT_SHA
            or manifest['fitting_performed'] is not False
            or _canonical_json(manifest['configuration']) != _canonical_json(directed.configuration())
            or manifest['runtime'] != support.RUNTIME):
        raise ValueError('directed manifest parent/configuration/runtime differs')
    if (type(report) is not dict or report.get('kind') != 'observed_only_directed_history_support_v1'
            or report.get('arms') != list(support.ARMS)
            or type(report.get('feature_dimension')) is not int or report['feature_dimension'] != 144
            or report.get('variation_prerequisite') is not True
            or type(report.get('excluded_prefixes')) is not int or report['excluded_prefixes'] != 0
            or any(report.get(k) is not False for k in ('fitting_performed', 'outcomes_opened',
                'successors_opened', 'models_opened', 'predictions_opened', 'fit_release_authorized'))
            or _canonical_json(report.get('configuration')) != _canonical_json(directed.configuration())):
        raise ValueError('unchanged directed source-only prerequisite required')
    prerequisites = report.get('prerequisites')
    if (type(prerequisites) is not dict or set(prerequisites) != {str(f) for f in range(5)}
            or any(type(p) is not dict or set(p) != PREREQUISITES
                   or any(v is not True for v in p.values()) for p in prerequisites.values())):
        raise ValueError('all thirty fixed training-fold prerequisites required')
    totals = report.get('totals', {})
    if any(type(totals.get(k)) is not int or totals[k] != v for k, v in COUNTS.items()):
        raise ValueError('complete unchanged directed cohort counts required')
    status = dict(phase='complete', completed_examples=COUNTS['prefixes'], total_examples=COUNTS['prefixes'])
    if _canonical_json(saved['STATUS.json']) != _canonical_json(status):
        raise ValueError('completed full source-only support status required')


def load_observed_components(project):
    """Return source observations, CandidateBlocks, baselines and all bindings.

    Reproduction runs under the fixed support runtime. Output arrays are owned
    read-only float64 matrices. Language-bearing observations remain available
    independently of the historical typed Example, which has no language field.
    No label file is needed or permitted by either reader's fixed inventory.
    """
    reader = SupportReader(project)
    if support.runtime_versions() != support.RUNTIME:
        raise ValueError('reviewed directed support runtime required')
    local_sources = _source_bindings({name: _sha(ROOT / name) for name in LOCAL_SOURCES}, LOCAL_SOURCES)
    complete = reader.read(SUPPORT + '/COMPLETE.json', SUPPORT_SHA)
    if (type(complete) is not dict or type(complete.get('files_sha256')) is not dict
            or set(complete['files_sha256']) != FILES):
        raise ValueError('exact source-only four-file support inventory required')
    saved = {name: reader.read(SUPPORT + '/' + name, complete['files_sha256'][name]) for name in sorted(FILES)}
    _validate_headers(complete, saved)
    manifest = saved['manifest.json']
    sources = _source_bindings(manifest['source_sha256'], support.SOURCE_FILES)
    observations, banks, assignment, coverage, observed_reader = observed.load_inputs(reader.project)
    if (_canonical_json(assignment) != _canonical_json(saved['folds.json'])
            or observed_reader.bindings != manifest['input_sha256']
            or _canonical_json(coverage) != _canonical_json(manifest['source_coverage'])):
        raise ValueError('observed source/language/input/fold ancestry differs')
    # Full replay checks vectors AND all masks, opportunities, identities, source
    # reasons, equivalence classes, pair geometry, totals and per-fold counts.
    reproduced = support.support_summary(observations, banks, assignment)
    if _canonical_json(reproduced) != _canonical_json(saved['report.json']):
        raise ValueError('directed vectors/diagnostics differ from sealed source support')
    blocks = {arm: {} for arm in support.ARMS}
    for row in reproduced['rows']:
        bank = banks[row['bank_id']]
        ids = tuple(c.candidate_id for c in bank.candidates)
        if (row['bank_seal_sha256'] != bank.seal_sha256
                or tuple(c['candidate_id'] for c in row['candidates']) != ids):
            raise ValueError('exact directed candidate identity/order required')
        for arm in support.ARMS:
            matrix = np.asarray([c['arms'][arm]['vector'] for c in row['candidates']], dtype=np.float64)
            if matrix.shape != (len(ids), 144) or not np.isfinite(matrix).all():
                raise ValueError('finite exact directed144 matrix required')
            matrix.setflags(write=False)
            blocks[arm][row['bank_id']] = CandidateBlock(ids, matrix)
    parent_reader = legacy.ArtifactReader(reader.project)
    parent_folds, base_sources = legacy.load_parent(parent_reader, assignment)
    bindings = _merge(observed_reader.bindings, parent_reader.bindings, reader.bindings)
    sources = _merge(sources, base_sources, local_sources)
    examples = legacy.observed_examples(observations)
    reader.recheck(); parent_reader.recheck(); observed_reader.recheck()
    _source_bindings(sources, sources)
    if support.runtime_versions() != support.RUNTIME:
        raise ValueError('directed runtime changed before returning inputs')
    return dict(examples=examples, observations=tuple(observations), banks=banks,
        assignment=assignment, interactions=blocks, parent_folds=parent_folds,
        fold_assignment_sha256=parent_reader.bindings[observed.PARENT + '/folds.json'],
        support_complete_sha256=SUPPORT_SHA, parent_complete_sha256=observed.PARENT_SHA,
        feature_configuration=directed.configuration(),
        source_bindings={str(ROOT / name): digest for name, digest in sources.items()},
        input_bindings={str(reader.project / name): digest for name, digest in bindings.items()})


if __name__ == '__main__':
    raise SystemExit('No production CLI: a separate reviewed fitting release is required.')
