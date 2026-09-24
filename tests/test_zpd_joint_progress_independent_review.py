"""Nonauthor replay of actual seven-arm synthetic solves and scope attacks.

All input programs/labels are invented. The numerical test really solves the
4131-dimensional objective, then forbids new producer helpers during audit.
It is not an empirical experiment, resource-budget test or execution attestation.
"""
import copy
from contextlib import ExitStack
import unittest
from unittest.mock import patch

from scripts import audit_zpd_joint_progress_independent as audit
from scripts import zpd_joint_progress_features as features
from scripts import zpd_joint_progress_newton as solver
from scripts import run_zpd_joint_progress_cv as worker
from tests.test_zpd_joint_progress_cv import fixture as varying_fixture
from tests.test_zpd_joint_progress_independent import fixture as analytic_fixture


class JointIndependentNumericalReview(unittest.TestCase):
    def test_actual_nonzero_seven_arm_models_replay_without_new_producer_helpers(self):
        inputs, labels = varying_fixture(); part = inputs[0]
        train, held = audit.capsule.scope(part)
        banks = {ex.bank_id: part.banks[ex.bank_id] for ex in train}
        own = {k: v for k, v in labels.items() if k[0] in banks}
        transform = features.fit_own_scaler(train, banks,
            {bid: part.raw_current[bid] for bid in banks}, own)
        blocks = {bid: features.compose_blocks(part.raw_current[bid], transform,
            {a: part.interactions[a][bid] for a in features.PROGRESS_ARMS}) for bid in banks}
        contract = worker.LabelContract('a'*64, part.fold_assignment_sha256, 'b'*64)
        models = {}
        for arm in worker.ARMS:
            x, y, weights, _ = features.mirrored_pairs(transform, {bid: b[arm] for bid, b in blocks.items()})
            self.assertGreater(x.nnz, 0)
            fitted = solver.fit_joint(x, y, weights, spec=worker.SPEC)
            self.assertGreater(fitted['optimization']['updates'], 0)
            models[arm] = worker._model(part, arm, x, weights, fitted, contract, transform)
        predictions = worker.predict_fold(part, models, transform)
        saved = worker.transform_payload(transform)
        fingerprint = audit.input_fingerprint(part)
        runtime = models['H']['joint_model']['runtime']
        with ExitStack() as stack:
            for owner, name in ((features, 'fit_own_scaler'), (features, 'mirrored_pairs'),
                    (features, 'compose_blocks'), (worker, 'predict_fold'), (worker, 'validate_model'),
                    (solver, 'fit_joint'), (solver, 'validate_model'), (solver, '_evaluate')):
                stack.enter_context(patch.object(owner, name, side_effect=AssertionError('producer replay forbidden: '+name)))
            result = audit.verify_fold(part, models, saved, predictions, own,
                expected_input_fingerprint=fingerprint, expected_label_contract=vars(contract),
                expected_runtime=runtime)
        self.assertEqual(result['verified_models'], 7)
        self.assertEqual(result['held_prefixes'], len(held))
        self.assertLessEqual(result['maximum_score_recompute_difference'], 1e-10)


class JointIndependentScopeReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data = analytic_fixture()

    def test_positive_architecture_language_cannot_replace_exact_report_or_gate(self):
        for mutation in ('gate', 'architecture', 'prediction_barrier'):
            data = copy.deepcopy(self.data)
            if mutation == 'gate': data['report']['gate']['passed'] = True
            elif mutation == 'architecture': data['report']['architecture_diagnostic']['model_promotion'] = True
            else: data['report']['predictions_complete_sha256'] = '0'*64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): audit.audit_run(**data)

    def test_independently_resealed_old_scores_must_match_exact_selected_SHA(self):
        data = copy.deepcopy(self.data)
        row = data['old_predictions'][0]
        selected = row['choices']['H']
        other = next(cid for cid in row['candidate_scores']['H'] if cid != selected)
        row['candidate_scores']['H'][other] = 1e-12
        cohort = audit.capsule.validate_inputs(data['fold_inputs'][0])
        with self.assertRaisesRegex(ValueError, 'old exact SHA score choice'):
            audit.independent_architecture(cohort, data['predictions'], data['old_predictions'],
                data['assessment_labels'], data['reference_pins'], True)

    def test_same_shape_external_source_binding_change_in_one_fold_is_rejected(self):
        data = copy.deepcopy(self.data)
        data['expected_label_contracts'][4]['expected_source_binding_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'common label provenance'):
            audit.audit_run(**data)


if __name__ == '__main__': unittest.main()
