"""Synthetic own-fold execution; no global empirical source or label access."""
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_repair_progress_cv as worker
from scripts import zpd_repair_progress_capsule as capsule
from scripts import zpd_repair_progress_newton as solver
from scripts import zpd_repair_structure as structural
from tests.test_zpd_repair_feedback_cv import fixture as original_fixture, materialized


def fixture(n=10):
    old, labels = original_fixture(n)
    examples = tuple(replace(ex, observation=replace(ex.observation,
        current=replace(ex.observation.current, submission_id=ex.example_id))) for ex in old.examples)
    interactions = {arm: {} for arm in capsule.ARMS}
    for bid, bank in old.banks.items():
        ids = tuple(c.candidate_id for c in bank.candidates)
        for index, arm in enumerate(capsule.ARMS):
            x = np.zeros((len(ids), 32), dtype=np.float64)
            for row in range(1, len(ids)):
                x[row, 0] = row*.01
                if arm != 'CF': x[row, 16] = -row*(index+1)*.005
            interactions[arm][bid] = solver.CandidateBlock(ids, x)
    inputs = {}
    for fold, parent in old.parent_folds.items():
        base = {ex.bank_id: structural.score_model(parent.models['structural_C'], ex.observation, (), old.banks[ex.bank_id])
                for ex in examples}
        predictions = tuple({**{k: p[k] for k in capsule.PREDICTION_FIELDS-{'choices', 'candidate_scores'}},
            'choices': {k: p['choices'][k] for k in capsule.PARENT_METHODS},
            'candidate_scores': {k: p['candidate_scores'][k] for k in capsule.BASELINES}} for p in parent.predictions)
        inputs[fold] = capsule.FoldInputs(fold, examples, old.banks, old.assignment, interactions, base,
            predictions, copy.deepcopy(parent.models['structural_C']['training']),
            parent.models['structural_C']['model_sha256'], old.fold_assignment_sha256, 'e'*64, True)
    return inputs, labels


class ProgressWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = fixture()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.labels_root = self.root/'prepared'; self.output = self.root/'fold-0'
        self.contracts = materialized(self.inputs[0], self.labels, self.labels_root)

    def run_worker(self, inputs=None, recheck=lambda: None):
        with redirect_stdout(io.StringIO()):
            return worker.fit_fold(inputs or self.inputs[0], self.labels_root, self.contracts[0], self.output, recheck=recheck)

    def test_own_file_only_six_fits_thirteen_methods_and_signed_inputs(self):
        actual_open = Path.open; reads = []; plans = []
        original_plan = solver.make_pair_plan
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode:
                reads.append(path)
                self.assertTrue(path == self.labels_root/'fold-0/train-labels.json' or path.parent == self.output)
            return actual_open(path, mode, *args, **kwargs)
        def planned(examples, banks, labels):
            plans.append(1)
            self.assertEqual({e.bank_id for e in examples}, set(banks))
            self.assertEqual(set(banks), {key[0] for key in labels})
            self.assertTrue(all(self.inputs[0].assignment['example_fold'][e.example_id] != 0 for e in examples))
            return original_plan(examples, banks, labels)
        with patch.object(Path, 'open', opened), patch.object(solver, 'make_pair_plan', planned):
            predictions = self.run_worker()
        self.assertEqual(plans, [1]); self.assertEqual(len(predictions), 2)
        self.assertEqual(set(predictions[0]['choices']), set(worker.METHODS)); self.assertEqual(len(worker.METHODS), 13)
        marker = json.loads((self.output/'COMPLETE.json').read_bytes())
        self.assertEqual(marker['completed_fits'], 6)
        self.assertEqual(set(marker['files_sha256']), set(worker.FILES))
        for arm in capsule.ARMS:
            model = json.loads((self.output/(arm+'.json')).read_bytes())
            worker.validate_model(model, self.inputs[0], arm)
            self.assertEqual(model['label_contract'], vars(self.contracts[0]))
            self.assertEqual(len(model['offset_model']['coefficients']), 32)
        cf = json.loads((self.output/'CF.json').read_bytes())
        self.assertEqual(cf['offset_model']['coefficients'][16:], [0.]*16)

    def test_zero_design_retains_all_unequal_pairs_and_mass(self):
        source = copy.deepcopy(self.inputs[0]); zero = {arm: {} for arm in capsule.ARMS}
        for arm in capsule.ARMS:
            for bid, block in source.interactions[arm].items():
                zero[arm][bid] = solver.CandidateBlock(block.candidate_ids, np.zeros_like(block.matrix))
        source = replace(source, interactions=zero)
        predictions = self.run_worker(source)
        for p, parent in zip(predictions, source.parent_predictions):
            for arm in capsule.ARMS:
                self.assertEqual(p['candidate_scores'][arm], parent['candidate_scores']['structural_C'])
                self.assertEqual(p['choices'][arm], parent['choices']['structural_C'])
        m = json.loads((self.output/'H.json').read_bytes()); s = m['pair_summary']
        self.assertEqual(s['exact_zero_difference_rows'], s['mirrored_rows'])
        self.assertEqual(s['exact_zero_difference_natural_weight_mass'], s['natural_weight_mass'])
        self.assertAlmostEqual(s['natural_weight_mass'], 1900.)

    def test_failed_third_cell_no_retry_and_no_complete(self):
        actual = solver.fit_offset; called = []
        def fit(*args, **kwargs):
            called.append(1)
            if len(called) == 3: raise solver.OffsetOptimizationError('synthetic', {'accepted': False})
            return actual(*args, **kwargs)
        with patch.object(solver, 'fit_offset', fit), self.assertRaises(solver.OffsetOptimizationError): self.run_worker()
        self.assertTrue((self.output/'FAILED.json').is_file()); self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'Jm.json').exists()); self.assertFalse((self.output/'HS.json').exists())
        with self.assertRaisesRegex(ValueError, 'no overwrite or retry'): self.run_worker()

    def test_late_output_consumption_rechecks_external_authority(self):
        drift = []; real = worker.sha
        def digest(path):
            result = real(path)
            if path == self.output/'STATUS.json': drift.append(True)
            return result
        def check():
            if drift: raise ValueError('late capsule drift')
        with patch.object(worker, 'sha', digest), self.assertRaisesRegex(ValueError, 'late capsule drift'):
            self.run_worker(recheck=check)
        self.assertFalse((self.output/'COMPLETE.json').exists()); self.assertTrue((self.output/'FAILED.json').exists())

    def test_own_label_drift_and_wrong_contract_fail(self):
        calls = []
        def check():
            calls.append(1)
            if len(calls) == 2:
                with (self.labels_root/'fold-0/train-labels.json').open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'own training-label file changed'): self.run_worker(recheck=check)
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_completed_marker_fsync_failure_is_quarantined(self):
        actual = worker.write
        def save(path, value):
            result = actual(path, value)
            if path.name == 'COMPLETE.json': raise OSError('synthetic completion fsync failure')
            return result
        with patch.object(worker, 'write', save), self.assertRaisesRegex(OSError, 'fsync'): self.run_worker()
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists()); self.assertTrue((self.output/'FAILED.json').exists())

    def test_all_five_folds_produce_full_population_without_assessment(self):
        result = []
        for fold in range(5):
            with redirect_stdout(io.StringIO()):
                result += worker.fit_fold(self.inputs[fold], self.labels_root, self.contracts[fold], self.root/f'all-{fold}', recheck=lambda: None)
        self.assertEqual(len(result), 10); self.assertEqual(len({p['example_id'] for p in result}), 10)
        self.assertFalse((self.root/'assessment').exists())
        self.assertTrue(all(set(p['choices']) == set(worker.METHODS) for p in result))


if __name__ == '__main__': unittest.main()
