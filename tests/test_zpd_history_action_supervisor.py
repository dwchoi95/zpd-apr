import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts import supervise_zpd_history_action as supervisor


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def completed(self, directory):
        directory.mkdir()
        supervisor.write(directory / 'report.json', {'ok': True})
        supervisor.write(directory / 'COMPLETE.json', {'status': 'complete',
            'files_sha256': {'report.json': supervisor.sha(directory / 'report.json')}})

    def test_marker_and_drift(self):
        self.completed(self.root / 'run')
        self.assertEqual(supervisor.verify_marker(self.root / 'run')['files_verified'], 1)
        supervisor.write(self.root / 'run/report.json', {'ok': False})
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            supervisor.verify_marker(self.root / 'run')

    def test_reject_traversal(self):
        run = self.root / 'run'
        run.mkdir()
        supervisor.write(run / 'COMPLETE.json', {'files_sha256': {'../outside': 'a' * 64}})
        with self.assertRaisesRegex(ValueError, 'invalid completion'):
            supervisor.verify_marker(run)

    def test_reject_symlink(self):
        run = self.root / 'run'
        run.mkdir()
        supervisor.write(self.root / 'outside.json', {'ok': True})
        (run / 'report.json').symlink_to(self.root / 'outside.json')
        supervisor.write(run / 'COMPLETE.json', {'files_sha256': {
            'report.json': supervisor.sha(self.root / 'outside.json')}})
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            supervisor.verify_marker(run)

    def test_reject_symlink_stage_root(self):
        self.completed(self.root / 'run')
        (self.root / 'alias').symlink_to(self.root / 'run', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink stage directory'):
            supervisor.verify_marker(self.root / 'alias')

    def test_no_completion_on_zero_exit_without_marker(self):
        with self.assertRaises(FileNotFoundError):
            supervisor.run_stage([sys.executable, '-c', 'pass'], name='child',
                cwd=self.root, output=self.root, stage_output=self.root / 'run',
                timeout_seconds=5, heartbeat_seconds=.05, memory_bytes=None)

    def test_child_failure_stops(self):
        with self.assertRaisesRegex(RuntimeError, 'exited 3'):
            supervisor.run_stage([sys.executable, '-c', 'raise SystemExit(3)'], name='child',
                cwd=self.root, output=self.root, stage_output=self.root / 'run',
                timeout_seconds=5, heartbeat_seconds=.05, memory_bytes=None)

    def test_timeout_is_bounded_and_no_next_stage(self):
        started = time.monotonic()
        with self.assertRaises(TimeoutError):
            supervisor.run_stage([sys.executable, '-c', 'import time; time.sleep(30)'],
                name='child', cwd=self.root, output=self.root,
                stage_output=self.root / 'run', timeout_seconds=.12,
                heartbeat_seconds=.05, memory_bytes=None)
        self.assertLess(time.monotonic() - started, 5)

    def test_success_requires_marker(self):
        code = ("from pathlib import Path; import json,hashlib; p=Path('run'); p.mkdir(); "
                "b=b'{}'; (p/'report.json').write_bytes(b); "
                "(p/'COMPLETE.json').write_text(json.dumps({'status':'complete','files_sha256':"
                "{'report.json':hashlib.sha256(b).hexdigest()}}))")
        result = supervisor.run_stage([sys.executable, '-c', code], name='child',
            cwd=self.root, output=self.root, stage_output=self.root / 'run',
            timeout_seconds=5, heartbeat_seconds=.05, memory_bytes=None)
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(supervisor.read(self.root / 'STATUS.json')['phase'], 'stage_complete')

    def test_existing_stage_not_reused(self):
        self.completed(self.root / 'run')
        with self.assertRaisesRegex(ValueError, 'no implicit retry'):
            supervisor.run_stage([sys.executable, '-c', 'pass'], name='child',
                cwd=self.root, output=self.root, stage_output=self.root / 'run', timeout_seconds=5)

    def test_pipeline_automatic_order_and_completion(self):
        family = self.root / supervisor.FAMILY
        calls = []

        def fake(command, *, name, stage_output, **kwargs):
            calls.append(name)
            self.completed(stage_output)
            if name == 'diagnose':
                supervisor.write(stage_output / 'report.json', {'next_action': {'action': 'inspect'}})
                supervisor.write(stage_output / 'COMPLETE.json', {'status': 'complete',
                    'files_sha256': {'report.json': supervisor.sha(stage_output / 'report.json')}})
            return {'name': name, 'output': str(stage_output),
                    'complete_sha256': supervisor.sha(stage_output / 'COMPLETE.json')}

        with patch.object(supervisor, 'source_state', return_value={'revision': 'fake', 'tree': 'fake'}), \
                patch.object(supervisor, 'run_stage', side_effect=fake):
            supervisor.supervise(self.root, family / 'supervised-v1', family / 'run-v1')
        self.assertEqual(calls, ['crossfit', 'verify', 'diagnose'])
        self.assertTrue((family / 'supervised-v1/COMPLETE.json').is_file())

    def test_pipeline_child_error_cannot_release_followup(self):
        family = self.root / supervisor.FAMILY
        calls = []

        def fail(command, *, name, **kwargs):
            calls.append(name)
            raise RuntimeError('synthetic failure')

        with patch.object(supervisor, 'source_state', return_value={'revision': 'fake', 'tree': 'fake'}), \
                patch.object(supervisor, 'run_stage', side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
                supervisor.supervise(self.root, family / 'supervised-v1', family / 'run-v1')
        self.assertEqual(calls, ['crossfit'])
        self.assertTrue((family / 'supervised-v1/FAILED.json').is_file())
        self.assertFalse((family / 'supervised-v1/COMPLETE.json').exists())

    def test_unsealed_report_rejected(self):
        self.completed(self.root / 'run')
        with self.assertRaisesRegex(ValueError, 'consumed artifact'):
            supervisor.verify_marker(self.root / 'run', required_files=('missing-report.json',))

    def test_previous_stage_resealed_mutation_rejected(self):
        self.completed(self.root / 'run')
        previous = {'output': str(self.root / 'run'),
                    'complete_sha256': supervisor.sha(self.root / 'run/COMPLETE.json')}
        supervisor.write(self.root / 'run/report.json', {'different': True})
        supervisor.write(self.root / 'run/COMPLETE.json', {'status': 'complete',
            'files_sha256': {'report.json': supervisor.sha(self.root / 'run/report.json')}})
        with self.assertRaisesRegex(ValueError, 'previous stage completion changed'):
            supervisor.verify_previous_stages([previous])


if __name__ == '__main__':
    unittest.main()
