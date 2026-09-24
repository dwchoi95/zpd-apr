"""Nonauthor stage-boundary regressions, synthetic transport/solver doubles only.

Full4131 numerical convergence is not claimed by these orchestration tests.
All bodies and writes belong to freshly created temporary synthetic fixtures.
"""
from contextlib import ExitStack
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import zpd_joint_progress_stages as stages
from tests import test_zpd_joint_progress_stages as author
from tests.test_zpd_joint_progress_cv import fixture


class JointStagesReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.inputs, cls.labels = fixture()

    setUp = author.JointStagesTests.setUp
    initialize = author.JointStagesTests.initialize
    fit = author.JointStagesTests.fit

    def complete_predictions(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        stages.finalize_predictions(context)
        return context

    def assessment_double(self):
        """Isolate filesystem failure paths on10 rows, not production science.

        The independent full320 author-fixture replay uses the real provider
        and assessment. This small double does not waive their320 requirement.
        Path reads, external label byte SHA, model/scaler/prediction barriers,
        artifact writes and terminal consumers remain the actual stage code.
        """
        stack = ExitStack()
        stack.enter_context(patch.object(stages.provider, 'validate_assessment_envelope', return_value=self.labels))
        stack.enter_context(patch.object(stages.assessment, 'assess', side_effect=lambda *args:
            dict(gate={'passed': False}, methods={m: {'synthetic_boundary_only': True} for m in stages.worker.METHODS})))
        return stack

    def test_initial_write_time_hash_not_replaced_by_fresh_hash(self):
        actual = stages.write
        for name in ('manifest.json', 'cohort.json', 'folds.json'):
            with self.subTest(name=name):
                # Isolate directories for each failed-attempt witness; no retry.
                self.family = self.root/('initial-'+name)
                def written(path, value):
                    pin = actual(path, value)
                    if path.name == 'folds.json':
                        target = path.parent/name
                        target.write_bytes(target.read_bytes()+b' ')
                    return pin
                with patch.object(stages, 'write', side_effect=written), self.assertRaises(ValueError): self.initialize()
                self.assertFalse((self.family/'run-v1'/'INITIALIZATION_COMPLETE.json').exists())
                self.assertTrue((self.family/'run-v1'/'FAILED.json').exists())

    def test_partial_seven_arm_inventory_stops_before_assessment_and_old_result(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        # A complete-looking marker cannot hide a missing seventh model body.
        missing = context['run']/'fold-4'/'C_joint.json'
        missing.rename(missing.with_name('C_joint.missing'))
        original_read = Path.read_bytes
        def forbidden(path):
            if path.is_relative_to(self.prepared): raise AssertionError('assessment opened before all35 model bodies')
            return original_read(path)
        callback = unittest.mock.Mock(side_effect=AssertionError('old-result callback too early'))
        with patch.object(Path, 'read_bytes', forbidden), self.assertRaises((ValueError, FileNotFoundError)):
            stages.assess_predictions(context, self.prepared, architecture_reporter=callback)
        callback.assert_not_called()
        self.assertFalse((context['run']/'assessment').exists())

    def test_job_directory_failure_after_run_creation_is_durable_failure(self):
        actual = Path.mkdir
        def broken(path, *args, **kwargs):
            if path == self.family/'jobs': raise OSError('synthetic job mkdir failure')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'mkdir', new=broken), self.assertRaises(OSError): self.initialize()
        self.assertTrue((self.family/'run-v1'/'FAILED.json').exists())
        self.assertFalse((self.family/'run-v1'/'INITIALIZATION_COMPLETE.json').exists())

    def test_late_failed_marker_cannot_coexist_with_accepted_completion(self):
        for name in ('root', 'assessment', 'fold-2'):
            with self.subTest(directory=name):
                self.family = self.root/('failed-marker-'+name)
                context = self.complete_predictions(); mutated = False
                def recheck():
                    nonlocal mutated
                    if (context['run']/'COMPLETE.json').exists() and not mutated:
                        mutated = True
                        target = context['run'] if name == 'root' else context['run']/name
                        (target/'FAILED.json').write_text('{"synthetic_late_failure":true}\n')
                context['recheck'] = recheck
                with self.assessment_double(), self.assertRaises(ValueError):
                    stages.assess_predictions(context, self.prepared, architecture_reporter=author.architecture_stub)
                self.assertTrue(mutated)
                self.assertFalse((context['run']/'COMPLETE.json').exists())
                self.assertTrue((context['run']/'REJECTED_COMPLETE.json').exists())

    def test_scaler_file_pin_must_hold_before_prediction_barrier(self):
        context = self.initialize()
        for fold in range(5): self.fit(context, fold)
        scaler = context['run']/'fold-2'/'SCALER.json'
        scaler.write_bytes(scaler.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'sealed artifact changed'): stages.finalize_predictions(context)
        self.assertFalse((context['run']/'PREDICTIONS_COMPLETE.json').exists())

    def test_late_recheck_artifact_or_label_drift_quarantines_both_completions(self):
        for mode in ('report', 'labels'):
            with self.subTest(mode=mode):
                self.family = self.root/('late-'+mode)
                context = self.complete_predictions(); mutated = False; written_marker = None
                def recheck():
                    nonlocal mutated, written_marker
                    marker = context['run']/'COMPLETE.json'
                    if marker.exists() and not mutated:
                        written_marker = marker.read_bytes(); mutated = True
                        target = context['run']/'assessment'/'report.json' if mode == 'report' else self.prepared/'assessment/all320-labels.json'
                        target.write_bytes(target.read_bytes()+b' ')
                context['recheck'] = recheck
                with self.assessment_double(), self.assertRaises(ValueError):
                    stages.assess_predictions(context, self.prepared, architecture_reporter=author.architecture_stub)
                self.assertTrue(mutated)
                for directory in (context['run'], context['run']/'assessment'):
                    self.assertFalse((directory/'COMPLETE.json').exists())
                    self.assertTrue((directory/'REJECTED_COMPLETE.json').exists())
                    self.assertTrue((directory/'FAILED.json').exists())
                self.assertEqual((context['run']/'REJECTED_COMPLETE.json').read_bytes(), written_marker)

    def test_physical_completion_written_then_write_failure_preserves_rejected_bytes(self):
        context = self.complete_predictions(); original = stages.write; raw = None
        def broken(path, value):
            nonlocal raw
            pin = original(path, value)
            if path == context['run']/'COMPLETE.json':
                raw = path.read_bytes(); raise OSError('synthetic fsync failure after marker bytes')
            return pin
        with self.assessment_double(), patch.object(stages, 'write', side_effect=broken), self.assertRaises(OSError):
            stages.assess_predictions(context, self.prepared, architecture_reporter=author.architecture_stub)
        self.assertIsNotNone(raw)
        self.assertEqual((context['run']/'REJECTED_COMPLETE.json').read_bytes(), raw)
        self.assertFalse((context['run']/'COMPLETE.json').exists())
        self.assertFalse((context['run']/'assessment'/'COMPLETE.json').exists())
        self.assertTrue((context['run']/'FAILED.json').exists())

    def test_architecture_return_cannot_promote_or_replace_primary_failure(self):
        context = self.complete_predictions()
        before = stages.prediction_barrier(context)
        self.assertEqual(len(before), 10)
        expected = dict(gate={'passed': False}, methods={m: {'synthetic_boundary_only': True} for m in stages.worker.METHODS})
        def callback(cohort, predictions, labels):
            return dict(author.architecture_stub(cohort, predictions, labels), gate={'passed': True}, selected_method='CF')
        with self.assessment_double(): report = stages.assess_predictions(context, self.prepared, architecture_reporter=callback)
        self.assertEqual(report['gate'], expected['gate'])
        self.assertEqual(report['methods'], expected['methods'])
        self.assertFalse(report['model_promotion'])
        marker = json.loads((context['run']/'COMPLETE.json').read_bytes())
        self.assertEqual(marker['scientific_gate_passed'], expected['gate']['passed'])
        self.assertTrue(marker['independent_audit_required'])


if __name__ == '__main__': unittest.main()
