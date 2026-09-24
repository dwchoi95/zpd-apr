"""Synthetic feasibility/closure tests; no real data or outcomes are opened."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

from scripts import audit_zpd_repair_directed_support as support
from scripts import audit_zpd_repair_feedback_support as observed
from tests.test_zpd_repair_feedback_support import fixture


def joined():
    s, f, o, b, a, _ = fixture()
    rows, banks, coverage = observed.join_observations(s, f, o, b, a)
    return rows, banks, a, coverage


class DirectedSupportTests(unittest.TestCase):
    def test_all_recipients_masks_failures_and_folds_retained(self):
        rows, banks, folds, _ = joined()
        callback = Mock()
        report = support.support_summary(rows, banks, folds, callback=callback)
        self.assertEqual(report['totals']['prefixes'], 10)
        self.assertEqual(report['totals']['candidates'], 30)
        self.assertEqual(report['totals']['terminal_attempts'], 80)
        self.assertEqual(report['totals']['failed_attempts'], 40)
        self.assertEqual(report['excluded_prefixes'], 0)
        self.assertFalse(report['fit_release_authorized'])
        self.assertTrue(all(report[k] is False for k in (
            'fitting_performed', 'outcomes_opened', 'successors_opened', 'models_opened', 'predictions_opened')))
        callback.assert_called_once_with(dict(completed_examples=10, total_examples=10))
        for f in report['folds'].values():
            self.assertEqual(f['train']['prefixes'], 8)
            self.assertEqual(f['held']['prefixes'], 2)
        for row in report['rows']:
            for arm, groups in row['equivalence_classes'].items():
                self.assertEqual(sorted(x for g in groups for x in g), sorted(c['candidate_id'] for c in row['candidates']))
            for c in row['candidates']:
                for arm, cell in c['arms'].items():
                    self.assertEqual(len(cell['vector']), 144)
                    self.assertEqual(len(cell['applicable_mask']), 1 if arm == 'L' else 2)
                    if c['is_noop']:
                        self.assertFalse(any(cell['vector']))
        self.assertEqual(report['totals']['candidate_diagnostics']['H']['no_opportunity'], 10)

    def test_future_fields_and_duplicate_or_wrong_membership_rejected(self):
        rows, banks, folds, _ = joined()
        for case in ('future', 'user', 'bank', 'fold', 'extra_bank'):
            r = copy.deepcopy(rows); b = dict(banks)
            if case == 'future': r[0]['next_code'] = 'not allowed'
            elif case == 'user': r[0]['user_id'] = r[1]['user_id']
            elif case == 'bank': r[0]['bank_id'] = r[1]['bank_id']
            elif case == 'fold': r[0]['fold'] = True
            else: b['extra'] = next(iter(b.values()))
            with self.subTest(case=case), self.assertRaises(ValueError):
                support.support_summary(r, b, folds)

    def test_common_offsets_are_not_pairwise_information(self):
        x = {a: np.full((3, 144), (i + 1) / 10.) for i, a in enumerate(support.ARMS)}
        g = support.geometry(x, np.zeros((3, 1296)), np.zeros((3, 18)), 0)
        for kind in ('all', 'edited'):
            self.assertTrue(all(n == 0 for n in g[kind]['varying_pairs'].values()))
            self.assertTrue(all(n == 0 for n in g[kind]['contrast_pairs'].values()))

    def test_exact_old_ties_and_lost_distinctions_are_reported(self):
        x = {a: np.zeros((3, 144)) for a in support.ARMS}
        x['H'][1, 0] = 1e-3
        old = np.zeros((3, 1296)); old[0, 0] = 1.
        g = support.geometry(x, old, np.zeros((3, 18)), 0)
        self.assertEqual(g['edited']['pairs'], 1)
        self.assertEqual(g['edited']['old_equal_event_new_distinct'], 1)
        self.assertEqual(g['edited']['old_equal_interaction_new_distinct'], 1)
        self.assertEqual(g['all']['old_distinct_new_nondistinct'], 1)
        self.assertEqual(g['all']['contrast_pairs']['Jm'], 2)

    def test_true_all_pair_contrast_near_tolerance(self):
        x = {a: np.zeros((3, 144)) for a in support.ARMS}
        x['H'][1, 0] = .75 * support.TOLERANCE
        x['H'][2, 0] = -.75 * support.TOLERANCE
        g = support.geometry(x, np.zeros((3, 1296)), np.zeros((3, 18)), 0)
        self.assertEqual(g['all']['contrast_pairs']['Jm'], 1)
        self.assertEqual(g['edited']['varying_pairs']['H'], 1)

    def test_nogo_retains_all_rows_and_does_not_authorize_fit(self):
        rows, banks, folds, _ = joined()
        # Identity HS and Jm equalities are not retried or filtered.
        for row in rows: row['history'] = row['history'][-1:]
        report = support.support_summary(rows, banks, folds)
        self.assertEqual(report['totals']['prefixes'], 10)
        self.assertFalse(report['variation_prerequisite'])
        self.assertTrue(all(not f['contrast_Jm'] and not f['contrast_HS'] for f in report['prerequisites'].values()))
        self.assertEqual(report['totals']['prior_one'], 10)

    def test_geometry_strict_dimensions_nonfinite_and_noop(self):
        x = {a: np.zeros((3, 144)) for a in support.ARMS}
        with self.assertRaises(ValueError): support.geometry(x, np.zeros((3, 1296)), np.zeros((3, 18)), True)
        x['H'][0, 0] = np.nan
        with self.assertRaises(ValueError): support.geometry(x, np.zeros((3, 1296)), np.zeros((3, 18)), 0)

    def audit_fixture(self, root, states, *, runtime_drift=False):
        rows, banks, folds, coverage = joined()
        reader = Mock(); reader.bindings = {'synthetic-observation-only': '0' * 64}
        runtime = dict(python=support.platform.python_version(),
            **{n: support.version(n) for n in ('numpy', 'scipy', 'scikit-learn')})
        with patch.object(observed, '_source_state', side_effect=states), \
                patch.object(observed, 'load_inputs', return_value=(rows, banks, folds, coverage, reader)), \
                patch.object(support, 'RUNTIME', runtime), \
                patch.object(support, 'runtime_versions', side_effect=[runtime, {} if runtime_drift else runtime]):
            return support.audit(root, root / support.FAMILY / 'support-v1'), reader

    def test_synthetic_completion_hashes_and_no_existing_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); state = dict(revision='synthetic', tree='synthetic')
            report, reader = self.audit_fixture(root, [state, state])
            out = root / support.FAMILY / 'support-v1'
            marker = json.loads((out / 'COMPLETE.json').read_text())
            for name, digest in marker['files_sha256'].items():
                self.assertEqual(observed.sha(out / name), digest)
            reader.recheck.assert_called_once()
            self.assertFalse(report['fit_release_authorized'])
            with self.assertRaisesRegex(ValueError, 'new exact'):
                support.audit(root, out)

    def test_source_drift_preserves_failure_without_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            with self.assertRaisesRegex(ValueError, 'source changed'):
                self.audit_fixture(root, [dict(revision='before'), dict(revision='after')])
            out = root / support.FAMILY / 'support-v1'
            self.assertTrue((out / 'FAILED.json').is_file())
            self.assertFalse((out / 'COMPLETE.json').exists())

    def test_late_runtime_drift_cannot_leave_completion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); state = dict(revision='synthetic', tree='synthetic')
            with self.assertRaisesRegex(ValueError, 'runtime changed'):
                self.audit_fixture(root, [state, state], runtime_drift=True)
            out = root / support.FAMILY / 'support-v1'
            self.assertTrue((out / 'FAILED.json').exists())
            self.assertFalse((out / 'COMPLETE.json').exists())

    def test_symlink_and_wrong_family_rejected_before_io(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); alias = root / 'alias'; alias.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'canonical'):
                support.audit(alias, alias / support.FAMILY / 'support-v1')
            with self.assertRaisesRegex(ValueError, 'new exact'):
                support.audit(root, root / 'other' / 'support-v1')


if __name__ == '__main__':
    unittest.main()
