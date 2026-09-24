"""Synthetic own-fold integration: control-flow doubles and one real7-arm fit.

Temporary synthetic artifacts from doubled tests are explicitly nonnumerical;
only RealJointWorkerTests invokes the actual4131 solver without replacement.
"""
import copy
from contextlib import ExitStack, redirect_stdout
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_joint_progress_cv as worker
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from tests.test_zpd_repair_progress_cv import fixture as original_fixture
from tests.test_zpd_repair_feedback_cv import materialized


def fixture():
    previous, labels = original_fixture()
    inputs = {}
    for fold, old in previous.items():
        inputs[fold] = capsule.FoldInputs(old.fold, old.examples, old.banks, old.assignment,
            {ex.bank_id: features.raw_current(ex, old.banks[ex.bank_id]) for ex in old.examples},
            old.interactions, old.parent_predictions, old.parent_training, old.parent_structure_model_sha256,
            old.fold_assignment_sha256, old.readiness_complete_sha256, True)
    return inputs, labels


def control_flow_fit(matrix, y, weights, *, spec):
    """Not a numerical fit: test double used only with its explicit validator."""
    x = matrix.copy(); x.eliminate_zeros()
    theta = np.zeros(4131, dtype=np.float64)
    theta[:3] = [1., -.1, -1.]; theta[4099] = .25; theta[4115] = .5
    theta[np.asarray(x.getnnz(axis=0)).ravel() == 0] = 0.
    return dict(synthetic_control_flow_stub=True, coefficients=theta.tolist(), final_gradient=[0.]*4131,
        training=dict(rows=len(y), unordered_pairs=len(y)//2,
            zero_difference_rows=int((np.asarray(x.getnnz(axis=1)).ravel() == 0).sum())))


def control_flow_validate(model, *, expected_spec):
    if model.get('synthetic_control_flow_stub') is not True: raise AssertionError('explicit test stub required')
    return np.asarray(model['coefficients'], dtype=np.float64)


class JointWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = fixture()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.labels_root = self.root/'prepared'; self.output = self.root/'fold-0'
        self.contracts = materialized(self.inputs[0], self.labels, self.labels_root)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.fit = self.stack.enter_context(patch.object(worker.solver, 'fit_joint', side_effect=control_flow_fit))
        self.stack.enter_context(patch.object(worker.solver, 'validate_model', side_effect=control_flow_validate))

    def run_worker(self, *, source=None, check=lambda: None, output=None, fold=0):
        with redirect_stdout(io.StringIO()):
            return worker.fit_fold(source or self.inputs[fold], self.labels_root, self.contracts[fold],
                output or self.output, recheck=check)

    def test_exact_own_read_scaler_once_seven_calls_fourteen_methods(self):
        actual_open = Path.open; actual_scaler = features.fit_own_scaler; reads = []; scalers = []
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode:
                reads.append(path)
                self.assertTrue(path == self.labels_root/'fold-0/train-labels.json' or path.parent == self.output)
            return actual_open(path, mode, *args, **kwargs)
        def scale(examples, banks, raw, labels):
            scalers.append(1)
            expected = {ex.bank_id for ex in capsule.scope(self.inputs[0])[0]}
            self.assertEqual(set(banks), expected); self.assertEqual(set(raw), expected)
            self.assertEqual({key[0] for key in labels}, expected)
            return actual_scaler(examples, banks, raw, labels)
        with patch.object(Path, 'open', opened), patch.object(features, 'fit_own_scaler', scale):
            predictions = self.run_worker()
        self.assertEqual(scalers, [1]); self.assertEqual(self.fit.call_count, 7)
        self.assertEqual(len(predictions), 2); self.assertTrue(reads)
        self.assertEqual(set(predictions[0]['choices']), set(worker.METHODS)); self.assertEqual(len(worker.METHODS), 14)
        complete = json.loads((self.output/'COMPLETE.json').read_bytes())
        self.assertEqual(complete['completed_fits'], 7); self.assertEqual(set(complete['files_sha256']), set(worker.FILES))
        for name, pin in complete['files_sha256'].items(): self.assertEqual(worker.sha(self.output/name), pin)
        transform = worker.decode_transform(json.loads((self.output/'SCALER.json').read_bytes()))
        for arm in worker.ARMS:
            saved = json.loads((self.output/(arm+'.json')).read_bytes())
            worker.validate_model(saved, self.inputs[0], arm, transform)
        self.assertNotIn('base_scores', capsule.encode_inputs(self.inputs[0]))

    def test_shared_control_holds_current_and_history_coefficients_fixed(self):
        result = self.run_worker(); source = self.inputs[0]
        transform = worker.decode_transform(json.loads((self.output/'SCALER.json').read_bytes()))
        model = json.loads((self.output/'H.json').read_bytes())
        theta = np.asarray(model['joint_model']['coefficients'])
        for prediction in result:
            bid = prediction['bank_id']
            blocks = features.compose_blocks(source.raw_current[bid], transform,
                {arm: source.interactions[arm][bid] for arm in features.PROGRESS_ARMS})
            for arm in ('HS', 'Jm', 'CF'):
                expected = dict(zip(blocks[arm].candidate_ids, map(float, blocks[arm].matrix@theta)))
                self.assertEqual(prediction['candidate_scores']['shared_H_'+arm], expected)

    def test_third_arm_failure_is_terminal_no_retry_and_preserves_first_two(self):
        calls = []
        def fit(*args, **kwargs):
            calls.append(1)
            if len(calls) == 3: raise worker.solver.JointOptimizationError('synthetic failure', dict(accepted=False))
            return control_flow_fit(*args, **kwargs)
        with patch.object(worker.solver, 'fit_joint', fit), self.assertRaises(worker.solver.JointOptimizationError):
            self.run_worker()
        self.assertEqual(len(calls), 3); self.assertTrue((self.output/'Jm.json').exists())
        self.assertFalse((self.output/'HS.json').exists()); self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists())
        with self.assertRaisesRegex(ValueError, 'no overwrite or retry'): self.run_worker()

    def test_wrong_fold_contract_rejected_before_any_output_or_fit(self):
        with self.assertRaises(ValueError), redirect_stdout(io.StringIO()):
            bad = replace(self.contracts[0], expected_fold_assignment_sha256='b'*64)
            worker.fit_fold(self.inputs[0], self.labels_root, bad, self.output, recheck=lambda: None)
        self.assertFalse(self.output.exists()); self.fit.assert_not_called()

    def test_label_drift_rejected_before_first_fit(self):
        calls = []
        def check():
            calls.append(1)
            if len(calls) == 2:
                with (self.labels_root/'fold-0/train-labels.json').open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'own training-label file changed'): self.run_worker(check=check)
        self.fit.assert_not_called(); self.assertTrue((self.output/'FAILED.json').exists())

    def test_completed_marker_write_side_effect_is_quarantined(self):
        actual = worker.write
        def write(path, value):
            result = actual(path, value)
            if path.name == 'COMPLETE.json':
                with (self.output/'SCALER.json').open('ab') as stream: stream.write(b' ')
            return result
        with patch.object(worker, 'write', write), self.assertRaisesRegex(ValueError, 'own output changed'):
            self.run_worker()
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists()); self.assertTrue((self.output/'FAILED.json').exists())

    def test_completion_fsync_failure_is_quarantined(self):
        actual = worker.write
        def write(path, value):
            result = actual(path, value)
            if path.name == 'COMPLETE.json': raise OSError('synthetic fsync failure')
            return result
        with patch.object(worker, 'write', write), self.assertRaisesRegex(OSError, 'fsync'): self.run_worker()
        self.assertFalse((self.output/'COMPLETE.json').exists()); self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists())

    def test_transform_roundtrip_tampering_and_label_free_prediction(self):
        predictions = self.run_worker()
        payload = json.loads((self.output/'SCALER.json').read_bytes()); transform = worker.decode_transform(payload)
        self.assertEqual(payload, worker.transform_payload(transform))
        for key in ('numeric_scale', 'y', 'weights'):
            changed = copy.deepcopy(payload); changed[key][0] = True
            with self.subTest(key=key), self.assertRaises(ValueError): worker.decode_transform(changed)
        models = {arm: json.loads((self.output/(arm+'.json')).read_bytes()) for arm in worker.ARMS}
        with (patch.object(worker.labels, 'load_fold_labels', side_effect=AssertionError('prediction reads no labels')),
              patch.object(features, 'fit_own_scaler', side_effect=AssertionError('prediction fits no scaler'))):
            self.assertEqual(predictions, worker.predict_fold(self.inputs[0], models, transform))
        changed = worker.decode_transform(dict(payload, numeric_scale=[v*2 for v in payload['numeric_scale']]))
        with self.assertRaises(ValueError): worker.predict_fold(self.inputs[0], models, changed)

    def test_five_folds_cover_whole_population_without_assessment_or_foreign_reads(self):
        result = []
        for fold in range(5): result += self.run_worker(fold=fold, output=self.root/f'all-{fold}')
        self.assertEqual(self.fit.call_count, 35)
        self.assertEqual(len(result), len(self.inputs[0].examples))
        self.assertEqual(len({row['example_id'] for row in result}), len(result))
        self.assertFalse((self.root/'assessment').exists())


class RealJointWorkerTests(unittest.TestCase):
    def test_actual_seven_native_models_and_scoring_on_one_synthetic_fold(self):
        inputs, labels = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); contracts = materialized(inputs[0], labels, root/'prepared')
            with redirect_stdout(io.StringIO()):
                result = worker.fit_fold(inputs[0], root/'prepared', contracts[0], root/'fold', recheck=lambda: None)
            transform = worker.decode_transform(json.loads((root/'fold'/'SCALER.json').read_bytes()))
            for arm in worker.ARMS:
                model = json.loads((root/'fold'/(arm+'.json')).read_bytes())
                worker.validate_model(model, inputs[0], arm, transform)
                self.assertNotIn('synthetic_control_flow_stub', model['joint_model'])
                self.assertLessEqual(model['joint_model']['optimization']['gradient_infinity_norm'], 1e-8)
            self.assertEqual(len(result), 2)
            self.assertTrue(all(set(row['choices']) == set(worker.METHODS) for row in result))


if __name__ == '__main__': unittest.main()
