"""Synthetic directed source/base chains only; no empirical outcomes or fits."""
import copy
from contextlib import ExitStack, contextmanager
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_repair_directed_inputs as inputs
from tests.test_zpd_repair_feedback_inputs import parent_fixture, write
from tests.test_zpd_repair_feedback_support import fixture


def joined():
    selected, features, original, raw, assignment, _ = fixture()
    for i, bank in enumerate(raw):
        bank['attempts'][1]['source'] = f'x = {200+i}\n'
        bank['attempts'][2]['source'] = f'x = {300+i}\n'
        bank['attempts'][3]['source'] = 'if (\n'
    # Preserve certified non-Python history even though these bytes parse as
    # Python. It remains unavailable; another source is syntactically invalid.
    key = next(k for k in original['source_sha256'] if k.endswith('/s0a.txt'))
    original['source_sha256'][key.replace('/Python/', '/C++/')] = original['source_sha256'].pop(key)
    rows, banks, coverage = inputs.observed.join_observations(selected, features, original, raw, assignment)
    return rows, banks, assignment, coverage


@contextmanager
def synthetic(project, mutate=None, *, runtime=None):
    rows, banks, assignment, coverage = joined()
    parent_sha, folds_sha = parent_fixture(project, assignment)
    report = inputs.support.support_summary(rows, banks, assignment)
    manifest = dict(source=dict(revision='a'*40, tree='b'*40), source_root='/synthetic/source',
        source_sha256={n: inputs._sha(inputs.ROOT / n) for n in inputs.support.SOURCE_FILES},
        input_sha256={}, runtime=dict(inputs.support.RUNTIME),
        parent_complete_sha256=parent_sha, source_coverage=coverage,
        configuration=inputs.directed.configuration(), fitting_performed=False)
    saved = {'manifest.json': manifest, 'folds.json': assignment, 'report.json': report,
             'STATUS.json': dict(phase='complete', completed_examples=10, total_examples=10)}
    saved = copy.deepcopy(saved)
    if mutate:
        mutate(saved)
    output = project / inputs.SUPPORT
    hashes = {name: write(output / name, value, indent=None) for name, value in saved.items()}
    pin = write(output / 'COMPLETE.json', dict(status='complete', fitting_performed=False, files_sha256=hashes))
    observed_reader = SimpleNamespace(bindings={}, recheck=lambda: None)
    with ExitStack() as stack:
        stack.enter_context(patch.object(inputs, 'SUPPORT_SHA', pin))
        stack.enter_context(patch.object(inputs.observed, 'PARENT_SHA', parent_sha))
        stack.enter_context(patch.object(inputs, 'COUNTS', dict(prefixes=10, users=10, problems=5, candidates=40)))
        stack.enter_context(patch.object(inputs.support, 'runtime_versions', return_value=inputs.support.RUNTIME if runtime is None else runtime))
        stack.enter_context(patch.object(inputs.observed, 'load_inputs', return_value=(rows, banks, assignment, coverage, observed_reader)))
        yield SimpleNamespace(rows=rows, banks=banks, assignment=assignment, report=report,
            pin=pin, folds_sha=folds_sha, reader=observed_reader)


class DirectedInputsTests(unittest.TestCase):
    def test_replays_entire_support_and_returns_all_language_bearing_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            with synthetic(project) as f:
                loaded = inputs.load_observed_components(project)
                self.assertEqual(loaded['observations'], tuple(f.rows))
                self.assertEqual(loaded['observations'][0]['history'][0]['language'], 'C++')
                self.assertEqual(len(loaded['examples']), 10)
                self.assertEqual(loaded['fold_assignment_sha256'], f.folds_sha)
                self.assertEqual(loaded['support_complete_sha256'], f.pin)
                self.assertEqual(set(loaded['parent_folds']), set(range(5)))
                self.assertEqual(set(loaded['interactions']), set(inputs.support.ARMS))
                self.assertTrue(all(str(project / inputs.SUPPORT / n) in loaded['input_bindings'] for n in inputs.FILES))
                self.assertTrue(all(str(inputs.ROOT / n) in loaded['source_bindings'] for n in inputs.LOCAL_SOURCES))
                for arm in inputs.support.ARMS:
                    self.assertEqual(set(loaded['interactions'][arm]), set(f.banks))
                    for bid, block in loaded['interactions'][arm].items():
                        self.assertEqual(block.candidate_ids, tuple(c.candidate_id for c in f.banks[bid].candidates))
                        self.assertEqual(block.matrix.shape, (4, 144))
                        self.assertEqual(block.matrix.dtype, np.dtype('float64'))
                        self.assertFalse(block.matrix.flags.writeable)
                        invalid = next(i for i, c in enumerate(f.banks[bid].candidates) if c.source == b'if (\n')
                        self.assertFalse(block.matrix[invalid].any())
                source_row = f.report['rows'][0]
                cells = [c['arms']['H'] for c in source_row['candidates']]
                self.assertTrue(any('non_python' in str(c['historical_transition_unavailable_reasons']) for c in cells))

    def test_reader_never_permits_labels_fresh_stores_or_new_predictions(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve(); reader = inputs.SupportReader(project)
            for path in ('outputs/zpd-repair-feedback-20260924/prepared-v1/assessment/all320-labels.json',
                         inputs.support.FAMILY + '/run-v1/predictions.json',
                         inputs.observed.PARENT + '/predictions.json', 'outputs/fresh128/labels.jsonl',
                         inputs.SUPPORT + '/../support-v1/report.json'):
                with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'inventory'):
                    reader.read(path, '0'*64)
            alias = project / 'alias'; alias.symlink_to(project, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'canonical'):
                inputs.SupportReader(alias)

    def test_only_new_support_and_explicit_old_parent_bodies_are_read(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            with synthetic(project):
                opened = []; original = Path.read_bytes
                def read(path):
                    opened.append(str(path.relative_to(project)))
                    return original(path)
                with patch.object(Path, 'read_bytes', read):
                    inputs.load_observed_components(project)
                self.assertTrue(opened)
                self.assertTrue(all(p.startswith(inputs.SUPPORT + '/') or p.startswith(inputs.observed.PARENT + '/') for p in opened))
                self.assertFalse(any('/prepared-v1/' in p or '/evaluation/' in p or '/assessment/' in p for p in opened))
                self.assertNotIn(inputs.legacy.SUPPORT + '/report.json', opened)

    def test_resealed_vectors_diagnostics_ids_and_geometry_cannot_bypass_replay(self):
        mutations = {
            'vector': lambda s: s['report.json']['rows'][0]['candidates'][0]['arms']['H']['vector'].__setitem__(0, .1),
            'mask': lambda s: s['report.json']['rows'][0]['candidates'][0]['arms']['H']['applicable_mask'].__setitem__(0, True),
            'candidate': lambda s: s['report.json']['rows'][0]['candidates'][0].__setitem__('candidate_id', '0'*64),
            'geometry': lambda s: s['report.json']['rows'][0]['geometry']['all'].__setitem__('pairs', 500),
            'opportunity': lambda s: s['report.json']['rows'][0]['candidates'][0]['arms']['H']['opportunity'].__setitem__(0, .8),
            'fold': lambda s: s['report.json']['rows'][0].__setitem__('fold', 4),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                project = Path(temp).resolve()
                with synthetic(project, mutate), self.assertRaisesRegex(ValueError, 'vectors/diagnostics differ'):
                    inputs.load_observed_components(project)

    def test_source_configuration_runtime_flags_and_all_thirty_prerequisites(self):
        mutations = {
            'source_hash': lambda s: s['manifest.json']['source_sha256'].__setitem__(inputs.support.SOURCE_FILES[0], '0'*64),
            'source_missing': lambda s: s['manifest.json']['source_sha256'].pop(inputs.support.SOURCE_FILES[0]),
            'source_extra': lambda s: s['manifest.json']['source_sha256'].__setitem__('../bad', '0'*64),
            'configuration': lambda s: s['manifest.json']['configuration'].__setitem__('dimension', 1296),
            'runtime': lambda s: s['manifest.json']['runtime'].__setitem__('python', 'bad'),
            'outcome_flag': lambda s: s['report.json'].__setitem__('outcomes_opened', True),
            'false_prerequisite': lambda s: s['report.json']['prerequisites']['0'].__setitem__('contrast_U', False),
            'numeric_prerequisite': lambda s: s['report.json']['prerequisites']['0'].__setitem__('contrast_U', 1),
            'missing_prerequisite': lambda s: s['report.json']['prerequisites']['4'].pop('contrast_L'),
            'missing_source_binding': lambda s: s['manifest.json']['input_sha256'].__setitem__('forbidden/labels', '0'*64),
            'language_coverage': lambda s: s['manifest.json']['source_coverage']['languages'].__setitem__('C++', 100),
            'fold_assignment': lambda s: s['folds.json']['example_fold'].__setitem__(next(iter(s['folds.json']['example_fold'])), 4),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                project = Path(temp).resolve()
                with synthetic(project, mutate), self.assertRaises(ValueError):
                    inputs.load_observed_components(project)

    def test_actual_runtime_and_late_runtime_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            with synthetic(project, runtime={}), self.assertRaisesRegex(ValueError, 'runtime required'):
                inputs.load_observed_components(project)
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            with synthetic(project), patch.object(inputs.support, 'runtime_versions', side_effect=[inputs.support.RUNTIME, {}]), \
                    self.assertRaisesRegex(ValueError, 'runtime changed'):
                inputs.load_observed_components(project)

    def test_late_sources_and_artifacts_rechecked_before_return(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            with synthetic(project) as f:
                real_sha = inputs._sha; drift = {'on': False}
                f.reader.recheck = lambda: drift.__setitem__('on', True)
                def changed(path):
                    if drift['on'] and path == inputs.ROOT / inputs.LOCAL_SOURCES[0]:
                        return '0'*64
                    return real_sha(path)
                with patch.object(inputs, '_sha', side_effect=changed), self.assertRaisesRegex(ValueError, 'source closure differs'):
                    inputs.load_observed_components(project)
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            with synthetic(project):
                path = project / inputs.SUPPORT / 'report.json'
                path.write_text(path.read_text() + ' ')
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    inputs.load_observed_components(project)

    def test_direct_numerical_and_label_validator_dependencies_are_rechecked(self):
        # Hashing validator source does not open any label body. These modules
        # are actually imported by the generic core/legacy input helper and
        # must remain fixed through the final observed-reader barrier.
        names = ('scripts/zpd_repair_feedback_offset.py',
                 'scripts/zpd_repair_feedback_labels.py',
                 'scripts/zpd_repair_feedback_pairs.py')
        self.assertTrue(set(names).issubset(inputs.LOCAL_SOURCES))
        for name in names:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp:
                project = Path(temp).resolve()
                with synthetic(project) as f:
                    real_sha = inputs._sha; drift = {'on': False}
                    f.reader.recheck = lambda: drift.__setitem__('on', True)
                    def changed(path):
                        if drift['on'] and path == inputs.ROOT / name:
                            return '0'*64
                        return real_sha(path)
                    with patch.object(inputs, '_sha', side_effect=changed), \
                            self.assertRaisesRegex(ValueError, 'source closure differs'):
                        inputs.load_observed_components(project)


if __name__ == '__main__':
    unittest.main()
