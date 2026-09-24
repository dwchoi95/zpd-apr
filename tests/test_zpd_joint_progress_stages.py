"""Synthetic coordinator boundaries with explicit nonnumerical solver doubles.

This module tests35 call/barrier orchestration, not35 Newton convergence claims.
Numerical integration is separately covered by the real seven-arm worker test.
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

from scripts import zpd_joint_progress_stages as stages
from scripts import zpd_joint_progress_capsule as capsule
from scripts import run_zpd_joint_progress_cv as worker
from scripts.zpd_repair_residual_core import make_pair_plan
from tests.test_zpd_joint_progress_cv import fixture, control_flow_fit, control_flow_validate
from tests.test_zpd_joint_progress_capsule import fixture as projected_fixture
from tests.test_zpd_repair_feedback_cv import materialized
from tests.test_zpd_repair_progress_stages import SOURCE


def architecture_stub(cohort, predictions, labels):
    return dict(kind='joint_vs_sealed_progress32_H_diagnostic_v1', model_promotion=False,
        primary_gate_effect='none', synthetic_control_flow_stub=True, examples=len(cohort))


def full_fixture():
    values = {fold: projected_fixture(320, fold=fold, synthetic=True) for fold in range(5)}
    labels = {}
    for i, (bid, bank) in enumerate(values[0].banks.items()):
        for j, candidate in enumerate(bank.candidates):
            unknown = i % 19 == 0 and j % 3 == 0
            ac = j == 1 or j == 0 and i % 7 == 0
            labels[bid, candidate.candidate_id] = dict(bank_id=bid, candidate_id=candidate.candidate_id,
                status='unknown' if unknown else 'stable', gain=None if unknown else .25 if ac and j else 0.,
                loss=None if unknown else .25 if j == 2 else 0., all_ac=None if unknown else ac)
    for fold, value in values.items():
        train, _ = capsule.scope(value); bids = {ex.bank_id for ex in train}
        plan = make_pair_plan(train, {bid: value.banks[bid] for bid in bids},
            {key: row for key, row in labels.items() if key[0] in bids})
        values[fold] = replace(value, parent_training=plan.metadata['training'])
    return values, labels


class JointStagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = fixture()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve(); self.family = self.root/'family'; self.prepared = self.root/'prepared'
        self.contracts = materialized(self.inputs[0], self.labels, self.prepared)
        stack = ExitStack(); self.addCleanup(stack.close)
        self.fit_mock = stack.enter_context(patch.object(worker.solver, 'fit_joint', side_effect=control_flow_fit))
        stack.enter_context(patch.object(worker.solver, 'validate_model', side_effect=control_flow_validate))

    def initialize(self, recheck=lambda: None):
        return stages.initialize(self.inputs, self.contracts, self.family, job_source=copy.deepcopy(SOURCE),
            authority=dict(release_sha256='f'*64, readiness_complete_sha256=self.inputs[0].readiness_complete_sha256,
                parent_complete_sha256='b'*64), provenance={}, recheck=recheck)

    def fit(self, context, fold):
        with redirect_stdout(io.StringIO()):
            return worker.fit_fold(context['inputs'][fold], self.prepared, context['contracts'][fold],
                context['run']/f'fold-{fold}', recheck=lambda: None)

    def test_initialization_no_labels_no_learned_scaler_or_sibling_hashes_in_job(self):
        actual = Path.open
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode: self.assertFalse(path.is_relative_to(self.prepared))
            return actual(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', opened): context = self.initialize()
        self.fit_mock.assert_not_called()
        for fold in range(5):
            job = stages.read(context['jobs']/f'fold-{fold}.json')
            self.assertEqual(job['kind'], stages.JOB_KIND)
            self.assertEqual(job['own_label_contract'], vars(self.contracts[fold]))
            self.assertNotIn('base_scores', job['inputs']); self.assertNotIn('numeric_scale', job['inputs'])
            for other in [*range(5), None]:
                if other != fold: self.assertNotIn(self.contracts[other].expected_sha256, json.dumps(job))
        with self.assertRaisesRegex(ValueError, 'no retry'): self.initialize()

    def test_incomplete_fold_prevents_assessment_label_or_architecture_access(self):
        context = self.initialize(); self.fit(context, 0); actual = Path.open
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode: self.assertFalse(path.is_relative_to(self.prepared))
            return actual(path, mode, *args, **kwargs)
        callback = unittest.mock.Mock(side_effect=AssertionError('old-result access too early'))
        with patch.object(Path, 'open', opened), self.assertRaises((ValueError, FileNotFoundError)):
            stages.assess_predictions(context, self.prepared, architecture_reporter=callback)
        callback.assert_not_called()
        self.assertFalse((context['run']/'assessment').exists()); self.assertTrue((context['run']/'FAILED.json').exists())

    def test_all35_calls_seal_fourteen_method_predictions_before_labels(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        self.assertEqual(self.fit_mock.call_count, 35)
        actual = Path.open
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode: self.assertFalse(path.is_relative_to(self.prepared))
            return actual(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', opened): predictions = stages.finalize_predictions(context)
        self.assertEqual(len(predictions), 10)
        seal = stages.read(context['run']/'PREDICTIONS_COMPLETE.json')
        self.assertEqual(seal['completed_fits'], 35); self.assertEqual(len(seal['methods']), 14)
        with self.assertRaisesRegex(ValueError, 'no overwrite'): stages.finalize_predictions(context)

    def test_resealed_model_foreign_contract_rejected(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        directory = context['run']/'fold-0'; model = stages.read(directory/'H.json')
        model['label_contract'] = vars(self.contracts[1])
        model['model_sha256'] = worker.canonical_hash({key: value for key, value in model.items() if key != 'model_sha256'})
        (directory/'H.json').write_text(json.dumps(model))
        seal = stages.read(directory/'COMPLETE.json'); seal['files_sha256']['H.json'] = stages.sha(directory/'H.json')
        (directory/'COMPLETE.json').write_text(json.dumps(seal))
        with self.assertRaisesRegex(ValueError, 'own-label contract'): stages.finalize_predictions(context)
        self.assertFalse((context['run']/'PREDICTIONS_COMPLETE.json').exists())

    def test_small_toy_is_not_accepted_as_production_assessment(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        predictions = stages.finalize_predictions(context)
        callback = unittest.mock.Mock(side_effect=AssertionError('not a full320 cohort'))
        self.assertEqual(len(predictions), 10)
        with self.assertRaisesRegex(ValueError, 'exact train320 assessment expected'):
            stages.assess_predictions(context, self.prepared, architecture_reporter=callback)
        callback.assert_not_called()

    def test_changed_job_and_changed_scaler_are_rejected(self):
        context = self.initialize()
        with (context['jobs']/'fold-2.json').open('ab') as stream: stream.write(b' ')
        with self.assertRaisesRegex(ValueError, 'own job changed'): stages.verify_initialization(context)


class FullJointStagesTests(JointStagesTests):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = full_fixture()

    # Only one full-size test; the inherited small-suite tests are not repeated.
    test_initialization_no_labels_no_learned_scaler_or_sibling_hashes_in_job = None
    test_incomplete_fold_prevents_assessment_label_or_architecture_access = None
    test_all35_calls_seal_fourteen_method_predictions_before_labels = None
    test_resealed_model_foreign_contract_rejected = None
    test_small_toy_is_not_accepted_as_production_assessment = None
    test_changed_job_and_changed_scaler_are_rejected = None

    def test_full320_23_2544_complete_orchestration_without_exclusions(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        predictions = stages.finalize_predictions(context)
        self.assertEqual(len(predictions), 320); self.assertEqual(self.fit_mock.call_count, 35)
        actual = Path.read_bytes; reads = []
        def read(path):
            if path.is_relative_to(self.prepared):
                self.assertEqual(path, self.prepared/'assessment/all320-labels.json')
                self.assertTrue((context['run']/'PREDICTIONS_COMPLETE.json').exists()); reads.append(path)
            return actual(path)
        expected = stages.assessment.assess(capsule.validate_inputs(self.inputs[0]),
            [{key: row[key] for key in stages.assessment.PREDICTION_FIELDS} for row in predictions], self.labels)
        def callback(cohort, rows, labels):
            self.assertTrue((context['run']/'PREDICTIONS_COMPLETE.json').exists())
            return dict(architecture_stub(cohort, rows, labels), falsely_claimed_positive=True)
        with patch.object(Path, 'read_bytes', read):
            result = stages.assess_predictions(context, self.prepared, architecture_reporter=callback)
        self.assertEqual(len(reads), 1)
        self.assertEqual(result['full']['examples'], 320); self.assertEqual(result['full']['problems'], 23)
        self.assertEqual(result['completed_fits'], 35); self.assertEqual(len(result['methods']), 14)
        self.assertEqual(result['exclusions'], 0)
        self.assertEqual(result['gate'], expected['gate']); self.assertEqual(result['methods'], expected['methods'])
        marker = stages.read(context['run']/'COMPLETE.json'); stages._files(context['run'], marker['files_sha256'])
        self.assertTrue(marker['independent_audit_required']); self.assertFalse(marker['model_promotion'])


if __name__ == '__main__': unittest.main()
