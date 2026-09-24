"""Nonauthor audit integration against one actual native4131 synthetic fit."""
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import zpd_joint_progress_audit as audit
from scripts import zpd_joint_progress_newton as producer


class JointAuditReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = producer.ResidualSpec('independent_synthetic_review', 4131, 'a'*64, producer.KIND)
        cls.x = np.zeros((8, 4131), dtype=np.float64)
        cls.x[0, 0] = .6; cls.x[0, 1] = -.3
        cls.x[2, 4099] = .25; cls.x[2, 4115] = .1
        cls.x[4, 1] = .9; cls.x[4, 4115] = -.2
        cls.x[1::2] = -cls.x[::2]
        cls.y = np.array([1, 0, 0, 1, 1, 0, 1, 0], dtype=np.int64)
        cls.w = np.full(8, 237.5, dtype=np.float64)
        cls.model = producer.fit_joint(cls.x, cls.y, cls.w, spec=cls.spec)

    def test_independent_audit_accepts_real_nonzero_solver_and_zero_rows(self):
        with (patch.object(producer, 'fit_joint', side_effect=AssertionError('no refitting during audit')),
              patch.object(producer, 'validate_model', side_effect=AssertionError('no producer validator')),
              patch.object(producer, '_evaluate', side_effect=AssertionError('no producer arithmetic')),
              patch.object(producer, '_sha_arrays', side_effect=AssertionError('no producer hash'))):
            result = audit.audit_model(self.model, sparse.csr_matrix(self.x), self.y, self.w, self.spec)
        self.assertTrue(result['verified']); self.assertEqual(result['rows'], 8)
        self.assertEqual(self.model['training']['zero_difference_rows'], 2)
        self.assertGreater(self.model['optimization']['updates'], 0)
        self.assertLessEqual(result['recomputed']['gradient_infinity_norm'], 1e-8)
        self.assertLess(result['maximum_gradient_recompute_difference'], 1e-11)
        self.assertFalse(result['input_provenance_verified'])

    def test_independent_scores_agree_with_full_sparse_linear_scores(self):
        theta = np.array(self.model['coefficients'], dtype=np.float64)
        matrix = sparse.csr_matrix(self.x[::2]); ids = tuple(str(i)*64 for i in range(1, 5))
        scores = dict(zip(ids, map(float, matrix@theta)))
        result = audit.audit_scores(theta, matrix, ids, scores)
        self.assertEqual(result['selected_candidate_id'], min(scores, key=lambda key: (-scores[key], key)))
        self.assertLess(result['maximum_score_recompute_difference'], 1e-12)

    def test_resealed_real_model_cannot_change_parameters_without_array_evidence(self):
        model = copy.deepcopy(self.model); model['coefficients'][0] += .01
        model['model_sha256'] = hashlib.sha256(json.dumps({k: v for k, v in model.items() if k != 'model_sha256'},
            sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        with self.assertRaises(ValueError): audit.audit_model(model, self.x, self.y, self.w, self.spec)


if __name__ == '__main__': unittest.main()
