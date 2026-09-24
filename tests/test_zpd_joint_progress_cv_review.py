"""Nonauthor worker-boundary regressions, synthetic control-flow doubles only.

These tests deliberately do not establish Newton convergence. The numerical
solver/validator are the author's explicitly marked doubles; current/history
score decomposition, type identity and terminal artifact checks are real.
"""
import copy
import json
import math
import unittest

import numpy as np

from scripts import run_zpd_joint_progress_cv as worker
from tests import test_zpd_joint_progress_cv as authored


class JointWorkerReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = authored.fixture()

    # Reuse only temporary synthetic setup/explicitly marked solver doubles.
    setUp = authored.JointWorkerTests.setUp
    run_worker = authored.JointWorkerTests.run_worker

    def artifacts(self):
        transform = worker.decode_transform(json.loads((self.output/'SCALER.json').read_bytes()))
        models = {arm: json.loads((self.output/(arm+'.json')).read_bytes()) for arm in worker.ARMS}
        return transform, models

    def test_last_preseal_input_consumer_cannot_change_already_checked_scaler(self):
        seen = []
        def check():
            if (self.output/'STATUS.json').exists() and not (self.output/'COMPLETE.json').exists():
                seen.append(1)
                if len(seen) == 3:
                    with (self.output/'SCALER.json').open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'own output changed'): self.run_worker(check=check)
        self.assertEqual(seen, [1, 1, 1]); self.assertEqual(self.fit.call_count, 7)
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists())

    def test_postseal_authority_consumer_drift_quarantines_marker(self):
        seen = []
        def check():
            if (self.output/'COMPLETE.json').exists() and not seen:
                seen.append(1)
                with (self.output/'predictions.json').open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'own output changed'): self.run_worker(check=check)
        self.assertEqual(seen, [1]); self.assertEqual(self.fit.call_count, 7)
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists())

    def test_training_bool_integer_alias_rejected_in_transform_and_model(self):
        self.run_worker(); transform, models = self.artifacts()
        payload = worker.transform_payload(transform)
        self.assertEqual(payload['training']['uninformative_train_prefixes'], 0)
        payload['training']['uninformative_train_prefixes'] = False
        altered = worker.decode_transform(payload)
        with self.assertRaisesRegex(ValueError, 'weighting parity'): worker.validate_transform(altered, self.inputs[0])
        model = models['H']; model['training']['uninformative_train_prefixes'] = False
        model['model_sha256'] = worker.canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
        with self.assertRaises(ValueError): worker.validate_model(model, self.inputs[0], 'H', transform)

    def test_resealed_foreign_training_contract_on_one_arm_is_rejected(self):
        self.run_worker(); transform, models = self.artifacts()
        model = models['Jm']; model['label_contract']['expected_source_binding_sha256'] = 'f'*64
        model['model_sha256'] = worker.canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
        # Shape/fold-only validation cannot establish an external label authority.
        worker.validate_model(model, self.inputs[0], 'Jm', transform)
        with self.assertRaisesRegex(ValueError, 'same own training-label contract'):
            worker.predict_fold(self.inputs[0], models, transform)

    def test_independent_dense_scalar_shared_scores_fix_all_h_coefficients(self):
        self.run_worker(); transform, models = self.artifacts()
        # Deliberately make separately fitted control current coefficients differ.
        # These are test-double coefficients, not numerical certificates.
        for arm in ('HS', 'Jm', 'CF'):
            model = models[arm]
            for i in range(3): model['joint_model']['coefficients'][i] *= 9.
            model['model_sha256'] = worker.canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
        result = worker.predict_fold(self.inputs[0], models, transform)
        theta = models['H']['joint_model']['coefficients']; different_current = False
        for prediction in result:
            bid = prediction['bank_id']; raw = self.inputs[0].raw_current[bid]
            numeric = raw.numeric.toarray()/transform.numeric_scale
            hashed = raw.hashed.toarray()
            for arm in ('HS', 'Jm', 'CF'):
                phi = self.inputs[0].interactions[arm][bid].matrix
                for index, cid in enumerate(raw.candidate_ids):
                    row = [*numeric[index], *hashed[index], *phi[index]]
                    expected = math.fsum(float(v)*t for v, t in zip(row, theta, strict=True))
                    actual = prediction['candidate_scores']['shared_H_'+arm][cid]
                    self.assertAlmostEqual(actual, expected, delta=1e-12)
                    different_current |= abs(actual-prediction['candidate_scores'][arm][cid]) > 1e-8
        self.assertTrue(different_current)

    def test_scaler_transform_hash_and_current_only_nested_zero_are_enforced(self):
        self.run_worker(); transform, models = self.artifacts()
        changed = copy.deepcopy(models)
        changed['H']['transform_sha256'] = 'f'*64
        changed['H']['model_sha256'] = worker.canonical_hash({k: v for k, v in changed['H'].items() if k != 'model_sha256'})
        with self.assertRaises(ValueError): worker.predict_fold(self.inputs[0], changed, transform)
        for arm, position in (('CF', 4115), ('C_joint', 4099)):
            changed = copy.deepcopy(models); model = changed[arm]
            model['joint_model']['coefficients'][position] = np.nextafter(0., 1.).item()
            model['model_sha256'] = worker.canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, 'nested zero columns'):
                worker.validate_model(model, self.inputs[0], arm, transform)


if __name__ == '__main__': unittest.main()
