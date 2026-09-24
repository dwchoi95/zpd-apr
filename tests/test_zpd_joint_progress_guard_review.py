"""Independent guard boundary tests, temporary synthetic files only."""
import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import guard_zpd_joint_progress as guard
from tests import test_zpd_joint_progress_guard as author


class JointGuardIndependentTests(unittest.TestCase):
    setUp = author.JointProgressGuardTests.setUp
    patch = author.JointProgressGuardTests.patch
    mock = author.JointProgressGuardTests.mock
    set_release = author.JointProgressGuardTests.set_release
    context = author.JointProgressGuardTests.context

    def test_late_failed_receipt_after_last_artifact_consumer_rejects(self):
        context = self.context()
        receipt = guard.publish_wrapper(self.location, context, 'preflight', {}, lambda: None)
        directory = self.location['supervisor'] / 'stages/preflight'
        real = guard._artifacts
        calls = 0

        def consume(location, stage):
            nonlocal calls
            value = real(location, stage)
            calls += 1
            if calls == 2:
                author.put(directory / 'FAILED.json', {'synthetic': 'late failed receipt'})
            return value

        with patch.object(guard, '_artifacts', side_effect=consume), self.assertRaises(ValueError):
            guard.verify_wrapper(self.project, 'preflight', receipt['complete_sha256'])

    def test_failed_or_rejected_engine_fold_cannot_authorize_a_receipt(self):
        context = self.context()
        author.synthetic_fold(self.location, 0)
        own = self.location['run'] / 'fold-0'
        result = dict(completed_fits=7, predicted_examples=64,
                      fold_complete_sha256=guard.sha(own / 'COMPLETE.json'), job_sha256='a' * 64)
        receipt = guard.publish_wrapper(self.location, context, 'fold-0', result, lambda: None)
        # Only newly created synthetic markers are removed between subcases.
        for base, name in ((own, 'FAILED.json'), (own, 'REJECTED_COMPLETE.json'),
                           (self.location['run'], 'FAILED.json')):
            with self.subTest(base=base.name, name=name):
                marker = base / name
                author.put(marker, {'synthetic': 'failure must be live'})
                try:
                    with self.assertRaises(ValueError):
                        guard.verify_wrapper(self.project, 'fold-0', receipt['complete_sha256'])
                finally:
                    marker.unlink()

    def test_late_engine_failure_after_artifact_hashing_rejects(self):
        context = self.context()
        author.synthetic_fold(self.location, 1)
        own = self.location['run'] / 'fold-1'
        result = dict(completed_fits=7, predicted_examples=64,
                      fold_complete_sha256=guard.sha(own / 'COMPLETE.json'), job_sha256='a' * 64)
        receipt = guard.publish_wrapper(self.location, context, 'fold-1', result, lambda: None)
        real = guard._artifacts
        calls = 0

        def consume(location, stage):
            nonlocal calls
            value = real(location, stage)
            calls += 1
            if calls == 2:
                author.put(own / 'FAILED.json', {'synthetic': 'post-consumption failure'})
            return value

        with patch.object(guard, '_artifacts', side_effect=consume), self.assertRaises(ValueError):
            guard.verify_wrapper(self.project, 'fold-1', receipt['complete_sha256'])

    def test_original_reference_body_is_not_preflight_input_and_pin_is_strict(self):
        old_body = self.project / guard.OLD_RUN / 'predictions.json'
        old_body.unlink()  # Metadata-only authentication must not require body I/O.
        context = self.context()
        guard.recheck(context)
        with patch.object(guard.stages, 'prediction_barrier', side_effect=ValueError('all35 absent')):
            with self.assertRaisesRegex(ValueError, 'all35 absent'):
                guard.old_reference(self.location, {})
        author.put(old_body, [{'synthetic_alternate': i} for i in range(320)])
        with patch.object(guard.stages, 'prediction_barrier'), self.assertRaisesRegex(ValueError, 'old predictions changed'):
            guard.old_reference(self.location, {})

    def test_missing_release_blocks_readers_and_never_creates_outputs(self):
        (self.root / guard.RELEASE).unlink()
        with (patch.object(guard, '_load_inputs', side_effect=AssertionError('reader before release')) as loader,
              patch.object(guard.labels, 'load_fold_labels', side_effect=AssertionError('label before release')) as labels,
              patch.object(guard, 'old_reference', side_effect=AssertionError('old body before release')) as old,
              self.assertRaisesRegex(ValueError, 'separate joint4131')):
            guard.execute_stage(self.project, 'preflight', {})
        loader.assert_not_called(); labels.assert_not_called(); old.assert_not_called()
        self.assertFalse(any(self.location[k].exists() for k in ('run', 'jobs', 'supervisor')))

    def test_source_closure_rejects_data_route_even_with_valid_digest(self):
        approval = copy.deepcopy(self.approval)
        approval['source_sha256']['outputs/private/labels.py'] = 'a' * 64
        self.set_release(approval)
        with self.assertRaisesRegex(ValueError, 'source closure'):
            self.context()
        for name in ('analysis_protocols/other-release.json', 'scripts/../labels.py',
                     '/scripts/absolute.py', 'outputs/disguised.py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                guard.job.validate_source_map({name: 'a' * 64})

    def test_changed_scaler_cannot_be_adopted_by_resealing_own_engine(self):
        context = self.context()
        author.synthetic_fold(self.location, 2)
        own = self.location['run'] / 'fold-2'
        result = dict(completed_fits=7, predicted_examples=64,
                      fold_complete_sha256=guard.sha(own / 'COMPLETE.json'), job_sha256='a' * 64)
        receipt = guard.publish_wrapper(self.location, context, 'fold-2', result, lambda: None)
        author.put(own / 'SCALER.json', {'synthetic_scaler': 'changed'})
        marker = guard.read(own / 'COMPLETE.json')
        marker['files_sha256']['SCALER.json'] = guard.sha(own / 'SCALER.json')
        author.put(own / 'COMPLETE.json', marker)
        with self.assertRaisesRegex(ValueError, 'bound actual engine artifacts'):
            guard.verify_wrapper(self.project, 'fold-2', receipt['complete_sha256'])

    def test_old_reference_failure_after_body_hash_is_not_hidden(self):
        run = self.project / guard.OLD_RUN
        body = run / 'predictions.json'
        original = guard.sha

        def after_hash(path):
            pin = original(path)
            if Path(path) == body:
                author.put(run / 'FAILED.json', {'synthetic': 'failure during body consumption'})
            return pin

        with patch.object(guard, 'sha', side_effect=after_hash), self.assertRaisesRegex(ValueError, 'failed old architecture'):
            guard.verify_old_reference_body(self.location)

    def test_exact_audit_maps_all35_models_five_scalers_and_six_label_scopes(self):
        # This tests the I/O adapter API, not the separate numeric auditor.
        run = self.location['run']
        run_pin = author.put(run / 'COMPLETE.json', {'synthetic': 'run seal'})
        prediction_pin = 'd' * 64
        author.put(run / 'assessment/report.json', {'predictions_complete_sha256': prediction_pin})
        models = {}
        scalers = {}
        examples = {}
        inputs = {}
        train_labels = {}
        for fold in range(5):
            models[fold] = {}
            for arm in guard.worker.ARMS:
                model = {'synthetic_fold': fold, 'synthetic_arm': arm}
                author.put(run / f'fold-{fold}' / (arm + '.json'), model)
                models[fold][arm] = model
            scalers[fold] = {'synthetic_scaler': fold}
            author.put(run / f'fold-{fold}/SCALER.json', scalers[fold])
            ex = SimpleNamespace(example_id=f'example-{fold}', bank_id=f'bank-{fold}')
            examples[fold] = (ex,)
            inputs[fold] = SimpleNamespace(fold=fold, banks={ex.bank_id: {'synthetic': fold}}, examples=(ex,))
            train_labels[fold] = {'synthetic_train_fold': fold}
        restored = dict(contracts=self.contracts, inputs=inputs, recheck=lambda: None,
                        predictions_complete_sha256=prediction_pin,
                        fingerprints={str(f): str(f) * 64 for f in range(5)})
        predictions = [{'synthetic_new': i} for i in range(320)]
        old_predictions = [{'synthetic_old': i} for i in range(320)]
        assessed = {'synthetic_assessed': True}
        scope_calls = []

        def own_labels(directory, fold, banks, identities, **contract):
            self.assertEqual(directory, self.location['prepared'])
            self.assertEqual(banks, inputs[fold].banks)
            self.assertEqual(identities, {f'example-{fold}': f'bank-{fold}'})
            self.assertEqual(contract, vars(self.contracts[fold]))
            scope_calls.append(fold)
            return train_labels[fold]

        def audit(got_inputs, got_models, got_scalers, got_predictions, got_training, got_assessed, report, **kw):
            self.assertEqual(got_inputs, inputs)
            self.assertEqual(got_models, models)
            self.assertEqual(got_scalers, scalers)
            self.assertIs(got_predictions, predictions)
            self.assertEqual(got_training, train_labels)
            self.assertIs(got_assessed, assessed)
            self.assertEqual(report, {'predictions_complete_sha256': prediction_pin})
            self.assertEqual(kw['expected_input_fingerprint'], {f: str(f) * 64 for f in range(5)})
            self.assertEqual(kw['expected_label_contracts'], {f: vars(self.contracts[f]) for f in range(5)})
            self.assertEqual(kw['expected_runtime'], {k: guard.RUNTIME[k] for k in ('python', 'numpy', 'scipy')})
            self.assertEqual(kw['expected_predictions_complete_sha256'], prediction_pin)
            self.assertIs(kw['old_predictions'], old_predictions)
            self.assertEqual(kw['reference_pins'], guard.architecture.REFERENCE_PINS)
            return dict(verified=True, recipients=320, models=35, methods=14, architecture_verified=True)

        from scripts import audit_zpd_joint_progress_independent as independent
        with (patch.object(guard, 'verify_marker'),
              patch.object(guard.stages, 'prediction_barrier', return_value=predictions) as barrier,
              patch.object(guard.capsule, 'scope', side_effect=lambda value: (examples[value.fold], ())),
              patch.object(guard.labels, 'load_fold_labels', side_effect=own_labels),
              patch.object(guard.labels, 'validate_assessment_envelope', return_value=assessed) as validate,
              patch.object(guard, 'old_reference', return_value=(old_predictions, lambda: None)),
              patch.object(independent, 'audit_run', side_effect=audit)):
            result = guard._independent_audit(self.location, restored)
        self.assertEqual(scope_calls, list(range(5)))
        self.assertEqual(barrier.call_count, 2)
        self.assertEqual(result['experiment_complete_sha256'], run_pin)
        validate.assert_called_once()


if __name__ == '__main__': unittest.main()
