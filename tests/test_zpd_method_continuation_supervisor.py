from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import supervise_zpd_method_continuation as supervisor


class MethodContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / supervisor.FAMILY / 'supervised-v1'

    def fake_stage(self, command, *, name, stage_output, **kwargs):
        self.calls.append(name)
        stage_output.mkdir(parents=True)
        # A scientific failure still advances the next independent experiment.
        supervisor.write(stage_output / 'report.json', {
            'decision': {'passed': False}})
        supervisor.write(stage_output / 'COMPLETE.json', {'status': 'complete',
            'files_sha256': {'report.json': supervisor.sha(stage_output / 'report.json')}})
        return dict(name=name, output=str(stage_output),
            complete_sha256=supervisor.sha(stage_output / 'COMPLETE.json'))

    def test_exact_order_and_scientific_failure_continues(self):
        self.calls = []
        with patch.object(supervisor, 'source_state', return_value={'revision': 'frozen'}), \
                patch.object(supervisor, 'run_stage', side_effect=self.fake_stage):
            report = supervisor.supervise(self.root, self.output)
        self.assertEqual(self.calls, ['repair_crossfit', 'repair_verify', 'action_crossfit', 'action_verify'])
        self.assertFalse(report['repair_decision']['passed'])
        self.assertFalse(report['action_decision']['passed'])
        self.assertTrue((self.output / 'COMPLETE.json').is_file())

    def test_operational_failure_stops_and_keeps_failure_record(self):
        self.calls = []
        def failing(*args, **kwargs):
            if kwargs['name'] == 'repair_verify':
                raise RuntimeError('independent verification failed')
            return self.fake_stage(*args, **kwargs)
        with patch.object(supervisor, 'source_state', return_value={'revision': 'frozen'}), \
                patch.object(supervisor, 'run_stage', side_effect=failing):
            with self.assertRaisesRegex(RuntimeError, 'verification failed'):
                supervisor.supervise(self.root, self.output)
        self.assertEqual(self.calls, ['repair_crossfit'])
        self.assertTrue((self.output / 'FAILED.json').is_file())
        self.assertFalse((self.output / 'COMPLETE.json').exists())

    def test_existing_run_is_not_overwritten(self):
        (self.root / supervisor.REPAIR_FAMILY / 'run-v1').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'all stage outputs must be new'):
            supervisor.supervise(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_source_drift_prevents_release(self):
        self.calls = []
        with patch.object(supervisor, 'source_state', side_effect=[{'revision': 'one'}, {'revision': 'two'}]), \
                patch.object(supervisor, 'run_stage', side_effect=self.fake_stage):
            with self.assertRaisesRegex(ValueError, 'source drift'):
                supervisor.supervise(self.root, self.output)
        self.assertEqual(self.calls, [])

    def test_final_gate_missing_cannot_mark_complete(self):
        self.calls = []
        def bad_stage(*args, **kwargs):
            result = self.fake_stage(*args, **kwargs)
            if kwargs['name'] == 'action_crossfit':
                directory = kwargs['stage_output']
                supervisor.write(directory / 'report.json', {'wrong_schema': True})
                supervisor.write(directory / 'COMPLETE.json', {'status': 'complete',
                    'files_sha256': {'report.json': supervisor.sha(directory / 'report.json')}})
                result['complete_sha256'] = supervisor.sha(directory / 'COMPLETE.json')
            return result
        with patch.object(supervisor, 'source_state', return_value={'revision': 'frozen'}), \
                patch.object(supervisor, 'run_stage', side_effect=bad_stage):
            with self.assertRaises(KeyError):
                supervisor.supervise(self.root, self.output)
        self.assertFalse((self.output / 'COMPLETE.json').exists())

    def test_report_mutation_while_reading_cannot_mark_complete(self):
        self.calls = []
        original_read = supervisor.read
        def changing_read(path):
            result = original_read(path)
            if Path(path).parent == self.root / supervisor.ACTION_FAMILY / 'run-v1':
                supervisor.write(path, {'decision': {'passed': True}})
            return result
        with patch.object(supervisor, 'source_state', return_value={'revision': 'frozen'}), \
                patch.object(supervisor, 'run_stage', side_effect=self.fake_stage), \
                patch.object(supervisor, 'read', side_effect=changing_read):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                supervisor.supervise(self.root, self.output)
        self.assertFalse((self.output / 'COMPLETE.json').exists())
        self.assertTrue((self.output / 'FAILED.json').exists())


if __name__ == '__main__':
    unittest.main()
