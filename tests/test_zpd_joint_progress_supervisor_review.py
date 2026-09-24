"""Independent mocked lifecycle checks; no child, labels or empirical inputs."""
import hashlib
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import supervise_zpd_joint_progress as supervisor
from tests import test_zpd_joint_progress_supervisor as fixture


class JointSupervisorBoundaryReviewTests(unittest.TestCase):
    def test_readonly_parent_test_of_exact_child_limit_configuration(self):
        with patch.object(supervisor.resource, 'setrlimit') as limits:
            supervisor._limits()
        limits.assert_called_once_with(supervisor.resource.RLIMIT_AS,
                                       (32 * 1024 ** 3, 32 * 1024 ** 3))
        self.assertEqual(supervisor.HEARTBEAT_SECONDS, 30)
        self.assertEqual(len(supervisor.guard.STAGES), 10)
        self.assertEqual(supervisor.TIMEOUTS, {
            s: 3600 if s.startswith('fold-') or s == 'audit' else 900
            for s in supervisor.guard.STAGES})
        self.assertEqual(sum(supervisor.TIMEOUTS.values()), 25200)
        self.assertEqual(supervisor.guard.ENVIRONMENT, {
            'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1',
            'NUMEXPR_NUM_THREADS': '1', 'VECLIB_MAXIMUM_THREADS': '1',
            'JE_ARROW_MALLOC_CONF': 'background_thread:false'})
        self.assertEqual(supervisor.guard.worker.ARMS, ('H', 'Jm', 'HS', 'U', 'L', 'CF', 'C_joint'))
        self.assertEqual(supervisor.guard.worker.FILES, (
            'H.json', 'Jm.json', 'HS.json', 'U.json', 'L.json', 'CF.json', 'C_joint.json',
            'SCALER.json', 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'))

    def test_child_uses_own_session_fixed_env_preexec_and_heartbeat(self):
        with tempfile.TemporaryDirectory() as t:
            output = Path(t).resolve()
            stage = output / 'child'
            command = ['synthetic-python', '-B', '-m', 'synthetic.module']
            process = Mock(pid=2468)
            process.wait.side_effect = [subprocess.TimeoutExpired(command, 30), 0]
            with patch.object(supervisor.subprocess, 'Popen', return_value=process) as start, \
                    patch.object(supervisor, '_group_alive', return_value=False), \
                    patch.object(supervisor, 'event') as event, \
                    patch.object(supervisor, 'child_progress', return_value={'synthetic': True}), \
                    patch.object(supervisor.guard, 'verify_marker', return_value={
                        'complete_sha256': 'a' * 64, 'files_verified': 1}):
                result = supervisor.run_child(command, name='preflight', cwd=output,
                    stage_output=stage, output=output, timeout_seconds=900,
                    required_files=('report.json',))
            args, kwargs = start.call_args
            self.assertEqual(args, (command,))
            self.assertIs(kwargs['start_new_session'], True)
            self.assertIs(kwargs['preexec_fn'], supervisor._limits)
            for key, value in supervisor.guard.ENVIRONMENT.items():
                self.assertEqual(kwargs['env'][key], value)
            self.assertEqual(process.wait.call_args_list[0].kwargs['timeout'], 30)
            self.assertEqual(process.wait.call_count, 2)
            self.assertEqual(result['returncode'], 0)
            self.assertEqual(result['complete_sha256'], 'a' * 64)
            self.assertEqual(sum(c.kwargs.get('phase') == 'running' for c in event.call_args_list), 2)

    def test_child_failure_stops_only_supplied_child_and_never_retries(self):
        with tempfile.TemporaryDirectory() as t:
            output = Path(t).resolve()
            process = Mock(pid=5678)
            process.wait.return_value = 2
            with patch.object(supervisor.subprocess, 'Popen', return_value=process) as start, \
                    patch.object(supervisor, '_stop_owned') as stop, \
                    patch.object(supervisor, 'event'), \
                    patch.object(supervisor, 'child_progress', return_value={}):
                with self.assertRaisesRegex(RuntimeError, 'no retry'):
                    supervisor.run_child(['synthetic'], name='fold-0', cwd=output,
                        stage_output=output / 'child', output=output,
                        timeout_seconds=3600, required_files=('H.json',))
            start.assert_called_once()
            stop.assert_called_once_with(process)

    def test_rejects_preexisting_output_and_changed_stage_budget_before_spawn(self):
        with tempfile.TemporaryDirectory() as t:
            output = Path(t).resolve(); stage = output / 'child'; stage.mkdir()
            with patch.object(supervisor.subprocess, 'Popen') as start:
                with self.assertRaises(ValueError):
                    supervisor.run_child(['synthetic'], name='preflight', cwd=output,
                        stage_output=stage, output=output, timeout_seconds=900,
                        required_files=('report.json',))
                with self.assertRaises(ValueError):
                    supervisor.run_child(['synthetic'], name='preflight', cwd=output,
                        stage_output=output / 'new', output=output, timeout_seconds=901,
                        required_files=('report.json',))
            start.assert_not_called()

    def test_budget_expiry_and_descendant_survival_cannot_publish_child_success(self):
        for cause in ('expired', 'descendants'):
            with self.subTest(cause=cause), tempfile.TemporaryDirectory() as t:
                output = Path(t).resolve(); process = Mock(pid=7890)
                process.wait.return_value = 0
                clock = [0., 901.] if cause == 'expired' else [0., 1.]
                with patch.object(supervisor.subprocess, 'Popen', return_value=process) as start, \
                        patch.object(supervisor.time, 'monotonic', side_effect=clock), \
                        patch.object(supervisor, '_group_alive', return_value=True), \
                        patch.object(supervisor, '_stop_owned') as stop, \
                        patch.object(supervisor, 'event'), \
                        patch.object(supervisor, 'child_progress', return_value={}), \
                        patch.object(supervisor.guard, 'verify_marker') as marker:
                    with self.assertRaises((TimeoutError, RuntimeError)):
                        supervisor.run_child(['synthetic'], name='preflight', cwd=output,
                            stage_output=output / 'child', output=output, timeout_seconds=900,
                            required_files=('report.json',))
                start.assert_called_once(); stop.assert_called_once_with(process)
                marker.assert_not_called()

    def test_owned_cleanup_only_signals_exact_process_group(self):
        process = Mock(pid=1357)
        with patch.object(supervisor.os, 'killpg') as kill, \
                patch.object(supervisor, '_group_alive', side_effect=[True, False]), \
                patch.object(supervisor.time, 'sleep'):
            supervisor._stop_owned(process)
        self.assertEqual(kill.call_count, 1)
        kill.assert_called_once_with(1357, signal.SIGTERM)
        process.wait.assert_called_once()

    def test_fitting_command_contains_only_external_own_job_authority(self):
        with tempfile.TemporaryDirectory() as t:
            project = Path(t).resolve()
            jobs = project / 'jobs'; jobs.mkdir()
            pin = hashlib.sha256(b'synthetic own job').hexdigest()
            (jobs / 'fold-3.json').write_bytes(b'synthetic own job')
            location = dict(jobs=jobs, run=project / 'run', supervisor=project / 'supervisor')
            with patch.object(supervisor.guard, 'paths', return_value=location), \
                    patch.object(supervisor.guard, 'verify_wrapper', return_value={
                        'report': {'result': {'job_sha256': {'3': pin}}}}) as receipt:
                command, target, required = supervisor.command_for(project, 'fold-3',
                    {'initialize': 'b' * 64}, {'forbidden_global_metadata': 'never serialize'})
            self.assertEqual(command, [supervisor.sys.executable, '-B', '-m',
                'scripts.run_zpd_joint_progress_job', '--project', str(project),
                '--fold', '3', '--expected-capsule-sha', pin])
            receipt.assert_called_once_with(project, 'initialize', 'b' * 64)
            self.assertEqual(target, location['run'] / 'fold-3')
            self.assertEqual(required, supervisor.guard.worker.FILES)


class JointSupervisorTerminalReviewTests(unittest.TestCase):
    # Reuse only synthetic fixture construction, not the author's test methods.
    setUp = fixture.JointProgressSupervisorTests.setUp
    child = fixture.JointProgressSupervisorTests.child
    run_supervisor = fixture.JointProgressSupervisorTests.run_supervisor

    def _assert_failed(self, *, rejected):
        self.assertFalse((self.output / 'COMPLETE.json').exists())
        self.assertTrue((self.output / 'FAILED.json').exists())
        self.assertEqual((self.output / 'REJECTED_COMPLETE.json').exists(), rejected)

    def test_initial_manifest_hash_survives_later_final_hash_inventory(self):
        original = supervisor.guard.write
        def write(path, value):
            pin = original(path, value)
            if path == self.output / 'manifest.json':
                path.write_bytes(b'{"modified_after_original_write":true}\n')
            return pin
        with patch.object(supervisor.guard, 'write', side_effect=write), \
                self.assertRaisesRegex(ValueError, 'sealed artifact changed'):
            self.run_supervisor()
        self._assert_failed(rejected=False)

    def test_next_action_hash_is_write_time_not_adopted_from_replacement(self):
        original = supervisor.guard.write
        def write(path, value):
            pin = original(path, value)
            if path == self.output / 'next_action.json':
                path.write_bytes(b'{"modified_after_original_write":true}\n')
            return pin
        with patch.object(supervisor.guard, 'write', side_effect=write), \
                self.assertRaisesRegex(ValueError, 'sealed artifact changed'):
            self.run_supervisor()
        self._assert_failed(rejected=False)

    def test_last_external_callback_cannot_mutate_previously_checked_output(self):
        post_complete_checks = 0
        def recheck(_):
            nonlocal post_complete_checks
            if (self.output / 'COMPLETE.json').exists():
                post_complete_checks += 1
                if post_complete_checks == 2:
                    (self.output / 'next_action.json').write_bytes(b'{"last_callback_change":true}\n')
        with self.assertRaisesRegex(ValueError, 'sealed artifact changed'):
            self.run_supervisor(recheck=recheck)
        self.assertEqual(post_complete_checks, 2)
        self._assert_failed(rejected=True)

    def test_exact_completion_write_hash_is_bound_not_a_new_marker_hash(self):
        original = supervisor.guard.write; replaced = []
        def write(path, value):
            pin = original(path, value)
            if path == self.output / 'COMPLETE.json':
                data = path.read_bytes() + b' '
                path.write_bytes(data); replaced.append(data)
            return pin
        with patch.object(supervisor.guard, 'write', side_effect=write), \
                self.assertRaisesRegex(ValueError, 'outer completion changed'):
            self.run_supervisor()
        self._assert_failed(rejected=True)
        self.assertEqual((self.output / 'REJECTED_COMPLETE.json').read_bytes(), replaced[0])

    def test_external_previous_marker_change_stops_before_next_fit(self):
        def child(*args, **kwargs):
            result = self.child(*args, **kwargs)
            if kwargs['name'] == 'initialize':
                marker = self.output / 'stages/preflight/COMPLETE.json'
                marker.write_bytes(marker.read_bytes() + b' ')
            return result
        with self.assertRaisesRegex(ValueError, 'externally pinned stage receipt changed'):
            self.run_supervisor(child=child)
        self.assertEqual(self.calls, ['preflight', 'initialize'])
        self._assert_failed(rejected=False)

    def test_independent_audit_requires_all_fourteen_methods(self):
        original = supervisor.guard.verify_wrapper
        def verify(project, stage, expected):
            value = original(project, stage, expected)
            if stage == 'audit':value['report']['result']['methods'] = 13
            return value
        with patch.object(supervisor.guard, 'verify_wrapper', side_effect=verify), \
                self.assertRaisesRegex(ValueError, 'independent full320/35/14 architecture audit'):
            self.run_supervisor()
        self._assert_failed(rejected=False)

    def test_complete_model_count_does_not_replace_explicit_architecture_verification(self):
        original = supervisor.guard.verify_wrapper
        def verify(project, stage, expected):
            value = original(project, stage, expected)
            if stage == 'audit': value['report']['result']['architecture_verified'] = False
            return value
        with patch.object(supervisor.guard, 'verify_wrapper', side_effect=verify), \
                self.assertRaisesRegex(ValueError, 'architecture audit required'):
            self.run_supervisor()
        self._assert_failed(rejected=False)

    def test_previous_thirty_fit_audit_is_not_a_complete_joint_result(self):
        original = supervisor.guard.verify_wrapper
        def verify(project, stage, expected):
            value = original(project, stage, expected)
            if stage == 'audit': value['report']['result']['models'] = 30
            return value
        with patch.object(supervisor.guard, 'verify_wrapper', side_effect=verify), \
                self.assertRaisesRegex(ValueError, 'full320/35/14'):
            self.run_supervisor()
        self._assert_failed(rejected=False)

    def test_joint_current_gate_failure_is_visible_not_retry_or_promotion(self):
        self.gate.update(actual_repair_improvement=True, mechanism_contribution=True,
                         current_feedback_contribution=True, joint_current_contribution=False, passed=False)
        result = self.run_supervisor()
        self.assertFalse(result['joint_current_gate_passed'])
        self.assertTrue(result['development_repair_gate_passed'])
        self.assertFalse(result['gate']['passed'])
        self.assertFalse(result['automatic_retry_authorized'])
        self.assertFalse(result['full_train_refit_authorized'])
        self.assertFalse(result['model_promotion'])
        self.assertFalse(result['confirmatory'])
        self.assertFalse(result['educational_benefit_established'])
        self.assertEqual(self.calls, list(supervisor.guard.STAGES))
        self.assertEqual(supervisor.guard.read(self.output / 'COMPLETE.json')['completed_fits'], 35)

    def test_last_terminal_callback_cannot_change_old_diagnostic_reference_body(self):
        post_complete_checks = 0
        target = self.project / supervisor.guard.OLD_RUN / 'predictions.json'
        def recheck(_):
            nonlocal post_complete_checks
            if (self.output / 'COMPLETE.json').exists():
                post_complete_checks += 1
                if post_complete_checks == 2:
                    target.write_bytes(b'[{"late_old_reference_change":true}]\n')
        with self.assertRaisesRegex(ValueError, 'old.*(prediction|reference)'):
            self.run_supervisor(recheck=recheck)
        self.assertEqual(post_complete_checks, 2)
        self._assert_failed(rejected=True)

    def test_old_reference_body_is_unread_until_all_joint_children_and_audit_receipt(self):
        real_read = Path.read_bytes
        real_open = Path.open
        target = self.project / supervisor.guard.OLD_RUN / 'predictions.json'
        reads = []
        def check(path):
            if path == target:
                self.assertEqual(self.calls, list(supervisor.guard.STAGES))
                self.assertTrue((self.output / 'stages/audit/COMPLETE.json').is_file())
                reads.append(path)
        def read(path):
            check(path)
            return real_read(path)
        def opened(path, *args, **kwargs):
            check(path)
            return real_open(path, *args, **kwargs)
        with patch.object(Path, 'read_bytes', new=read), patch.object(Path, 'open', new=opened):
            self.run_supervisor()
        self.assertGreaterEqual(len(reads), 4)


if __name__ == '__main__':
    unittest.main()
