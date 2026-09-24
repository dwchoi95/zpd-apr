"""Independent wrapper/I-O boundary tests; synthetic artifacts, no model fit."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import guard_zpd_repair_feedback as guard
from scripts import run_zpd_repair_feedback_cv as engine
from tests.test_zpd_repair_feedback_guard import metadata_fixture, put, wrapper


def fake_fold(location, fold):
    """Only exercise artifact plumbing; these are explicitly non-model bodies."""
    directory = location['run'] / f'fold-{fold}'
    files = {}
    for arm in engine.ARMS:
        put(directory / (arm + '.json'), {'synthetic_unread_model': arm})
        files[arm + '.json'] = guard.sha(directory / (arm + '.json'))
    put(directory / 'MODELS_COMPLETE.json', {'model_files_sha256': dict(files)})
    put(directory / 'predictions.json', {'synthetic_unread_predictions': fold})
    put(directory / 'STATUS.json', {'phase': 'complete'})
    for name in ('MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'):
        files[name] = guard.sha(directory / name)
    put(directory / 'COMPLETE.json', dict(status='complete', completed_fits=5,
        fold=fold, files_sha256=files))


class IndependentGuardBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        patched = patch.object(guard, 'PROJECT', self.project)
        patched.start(); self.addCleanup(patched.stop)
        # This suite isolates file-access boundaries; the author's separate
        # direct-stage tests check the real resource-boundary requirements.
        resource_boundary = patch.object(guard, 'verify_child_boundary')
        resource_boundary.start(); self.addCleanup(resource_boundary.stop)
        self.location = metadata_fixture(self.project)
        self.context = dict(source={'revision': 'a'*40, 'tree': 'b'*40},
            release_sha256='c'*64, source_sha256={}, input_sha256={},
            runtime=guard.RUNTIME, project=str(self.project))
        self.inputs = SimpleNamespace(assignment={'synthetic': True},
            fold_assignment_sha256='b'*64)
        self.provenance = dict(source_sha256={}, input_sha256={})
        wrapper(self.location, 'preflight', self.context)
        wrapper(self.location, 'prepare', self.context)
        for name, value in [('manifest.json', {'synthetic': True}),
                            ('cohort.json', []), ('folds.json', self.inputs.assignment)]:
            put(self.location['run'] / name, value)
        put(self.location['run'] / 'FOLDS_COMPLETE.json', dict(files_sha256={
            name: guard.sha(self.location['run'] / name)
            for name in ('manifest.json', 'cohort.json', 'folds.json')}))
        wrapper(self.location, 'initialize', self.context)

    def _prior_folds(self, count):
        for fold in range(count):
            fake_fold(self.location, fold)
            wrapper(self.location, f'fold-{fold}', self.context)

    def test_fold4_actual_previous_checks_never_read_sibling_labels_or_models(self):
        self._prior_folds(4)
        own = self.location['prepared'] / 'fold-4/train-labels.json'
        opened_labels = []
        actual_open = Path.open

        def checked(path, *args, **kwargs):
            if path.name in ('train-labels.json', 'all320-labels.json', 'labels.jsonl'):
                self.assertEqual(path, own, 'fit worker touched an inaccessible label file')
                opened_labels.append(path)
            for fold in range(4):
                if path.parent == self.location['run'] / f'fold-{fold}':
                    self.assertNotIn(path.name, {arm + '.json' for arm in engine.ARMS},
                                     'worker previous-stage check consumed prior model bodies')
            return actual_open(path, *args, **kwargs)

        def fit(inputs, fold, prepared, contract, run):
            self.assertIs(inputs, self.inputs); self.assertEqual(fold, 4)
            self.assertEqual(prepared, self.location['prepared'])
            self.assertEqual(guard.sha(own), contract.expected_sha256)
            own.read_bytes()
            fake_fold(self.location, fold)
            return [None] * 64

        with patch.object(guard, 'preflight', return_value=self.context), \
                patch.object(guard, 'recheck'), \
                patch.object(guard, '_load_inputs', return_value=(self.inputs, self.provenance)), \
                patch.object(engine, 'fit_fold', fit), patch.object(Path, 'open', checked):
            result = guard.execute_stage(self.project, 'fold-4')
        self.assertTrue(opened_labels)
        self.assertEqual(set(opened_labels), {own})
        self.assertEqual(result['result']['only_label_file'], 'fold-4/train-labels.json')

    def test_finalize_actual_previous_checks_open_no_label_body(self):
        self._prior_folds(5)
        actual_open = Path.open

        def checked(path, *args, **kwargs):
            if path.name in ('train-labels.json', 'all320-labels.json', 'labels.jsonl'):
                raise AssertionError('finalize consumed label bytes, including hashing')
            return actual_open(path, *args, **kwargs)

        def finalize(inputs, run):
            put(run / 'predictions.json', [])
            put(run / 'PREDICTIONS_COMPLETE.json', dict(
                status='all_folds_label_blind_predictions_complete', completed_fits=25,
                recipients=320, methods=list(engine.METHODS),
                predictions_sha256=guard.sha(run / 'predictions.json'),
                fold_complete_sha256={str(fold): guard.sha(run / f'fold-{fold}/COMPLETE.json')
                                      for fold in range(5)}))
            return [None] * 320

        with patch.object(guard, 'preflight', return_value=self.context), \
                patch.object(guard, 'recheck'), \
                patch.object(guard, '_load_inputs', return_value=(self.inputs, self.provenance)), \
                patch.object(engine, 'finalize_predictions', finalize), \
                patch.object(Path, 'open', checked):
            result = guard.execute_stage(self.project, 'finalize')
            guard.verify_wrapper(self.project, 'finalize', deep=True)
        self.assertTrue(result['result']['label_bodies_opened'] is False)

    def test_inner_verified_marker_cannot_replace_outer_stage_or_override_failure(self):
        put(self.location['verified'] / 'report.json', {'verified': True})
        put(self.location['verified'] / 'COMPLETE.json', dict(status='complete',
            files_sha256={'report.json': guard.sha(self.location['verified'] / 'report.json')}))
        with self.assertRaises(FileNotFoundError):
            guard.verify_wrapper(self.project, 'audit', deep=True)
        directory = wrapper(self.location, 'audit', self.context)
        self.assertEqual(guard.verify_wrapper(self.project, 'audit', deep=True)['report']['status'], 'complete')
        put(directory / 'FAILED.json', {'error': 'synthetic late source barrier failure'})
        with self.assertRaisesRegex(ValueError, 'valid completed fixed stage'):
            guard.verify_wrapper(self.project, 'audit', deep=True)


if __name__ == '__main__':
    unittest.main()
