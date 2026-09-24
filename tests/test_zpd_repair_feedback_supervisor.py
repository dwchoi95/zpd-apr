"""Mock-child lifecycle checks only; no actual training or production data."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import guard_zpd_repair_feedback as guard
from scripts import supervise_zpd_repair_feedback as supervisor
from tests.test_zpd_repair_feedback_guard import put


class FeedbackSupervisorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.project = Path(temp.name).resolve()
        context = patch.object(guard, 'PROJECT', self.project); context.start(); self.addCleanup(context.stop)
        self.location = guard.paths(self.project); self.output = self.location['supervisor']
        self.context = dict(source={'revision': 'a'*40, 'tree': 'b'*40}, release_sha256='c'*64,
            source_sha256={}, input_sha256={}, runtime=guard.RUNTIME, project=str(self.project))
        self.gate = dict(passed=False, actual_repair_improvement=False, mechanism_contribution=False)
        self.calls = []

    def child(self, command, *, name, cwd, stage_output, output, timeout_seconds, heartbeat_seconds, memory_bytes):
        self.calls.append(name)
        self.assertEqual(command[:4], [supervisor.sys.executable, '-B', '-m', 'scripts.guard_zpd_repair_feedback'])
        self.assertEqual(command[4:], ['--project', str(self.project), '--stage', name])
        self.assertEqual(stage_output, self.output/'stages'/name); self.assertFalse(stage_output.exists())
        self.assertEqual(timeout_seconds, 3600 if name.startswith('fold-') or name == 'audit' else 900)
        self.assertEqual(memory_bytes, 32*1024**3); self.assertEqual(heartbeat_seconds, 30)
        stage_output.mkdir(parents=True); result = {}
        if name.startswith('fold-'): result['predicted_examples'] = 64
        if name == 'assess':
            put(self.location['run']/'assessment/report.json', dict(gate=self.gate))
            put(self.location['run']/'COMPLETE.json', dict(status='synthetic-complete-only'))
        if name == 'audit':
            result = dict(verified=True, recipients=320, models=25, methods=11, gate=self.gate,
                experiment_complete_sha256=guard.sha(self.location['run']/'COMPLETE.json'))
            put(self.location['verified']/'report.json', result)
            put(self.location['verified']/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(self.location['verified']/'report.json')}))
        report = dict(stage=name, source=self.context['source'], release_sha256=self.context['release_sha256'], result=result)
        put(stage_output/'report.json', report)
        put(stage_output/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(stage_output/'report.json')}))
        log = self.output/(name+'.log'); log.write_text('synthetic child only\n')
        return dict(name=name, output=str(stage_output), returncode=0, elapsed_seconds=.01,
            complete_sha256=guard.sha(stage_output/'COMPLETE.json'), files_verified=1, log_sha256=guard.sha(log))

    def verify(self, project, stage, *, deep=False):
        self.assertTrue(deep)
        directory = self.output/'stages'/stage
        marker = guard.read(directory/'COMPLETE.json')
        self.assertEqual(marker['files_sha256']['report.json'], guard.sha(directory/'report.json'))
        return dict(complete_sha256=guard.sha(directory/'COMPLETE.json'), report=guard.read(directory/'report.json'))

    def run_supervisor(self, child=None, verify=None, recheck=None):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(guard, 'preflight', return_value=self.context), \
                patch.object(guard, 'recheck', side_effect=recheck), patch.object(guard, 'verify_wrapper', side_effect=verify or self.verify), \
                patch.object(supervisor, 'run_stage', side_effect=child or self.child):
            return supervisor.supervise(self.project)

    def test_exact11_separate_children_fixed_caps_no_refits_and_all_logs_sealed(self):
        result = self.run_supervisor()
        self.assertEqual(self.calls, list(guard.STAGES)); self.assertEqual(len(self.calls), 11)
        manifest = guard.read(self.output/'manifest.json')
        self.assertEqual(manifest['maximum_child_budget_seconds'], 26100)
        self.assertTrue(manifest['engine_own_cli_remains_unreleased'])
        self.assertEqual(manifest['automatic_retries'], 0); self.assertEqual(manifest['full_train_refits'], 0)
        self.assertFalse(result['development_repair_gate_passed']); self.assertFalse(result['model_promotion'])
        self.assertFalse(result['confirmatory']); self.assertFalse(result['educational_benefit_established'])
        marker = guard.read(self.output/'COMPLETE.json')
        self.assertEqual(marker['completed_oof_examples'], 320)
        for name, digest in marker['files_sha256'].items(): self.assertEqual(guard.sha(self.output/name), digest)
        self.assertTrue(all(stage+'.log' in marker['files_sha256'] for stage in guard.STAGES))
        status = guard.read(self.output/'STATUS.json'); self.assertEqual(status['completed_oof_examples'], 320)

    def test_child_failure_stops_immediately_preserving_previous_seals(self):
        def failed(*args, **kwargs):
            if kwargs['name'] == 'fold-1': raise TimeoutError('fixed cap reached')
            return self.child(*args, **kwargs)
        with self.assertRaisesRegex(TimeoutError, 'fixed cap'): self.run_supervisor(child=failed)
        self.assertEqual(self.calls, ['preflight', 'prepare', 'initialize', 'fold-0'])
        self.assertTrue((self.output/'FAILED.json').exists()); self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'stages/fold-0/COMPLETE.json').exists())
        self.assertFalse((self.output/'stages/fold-2').exists())

    def test_previous_stage_or_log_drift_stops_before_next_child(self):
        for target in ('COMPLETE.json', 'log'):
            # Separate temporary project for each irreversible failed run.
            with tempfile.TemporaryDirectory() as temporary:
                self.project = Path(temporary).resolve()
                with patch.object(guard, 'PROJECT', self.project):
                    self.location = guard.paths(self.project); self.output = self.location['supervisor']; self.calls = []
                    def changed(*args, **kwargs):
                        result = self.child(*args, **kwargs)
                        if kwargs['name'] == 'prepare':
                            if target == 'log': (self.output/'preflight.log').write_text('changed log')
                            else:
                                path = self.output/'stages/preflight/COMPLETE.json'; value = guard.read(path)
                                value['changed'] = True; put(path, value)
                        return result
                    with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'previous'):
                        self.run_supervisor(child=changed)
                    self.assertEqual(self.calls, ['preflight', 'prepare'])
                    self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_unreleased_or_existing_outputs_fail_before_creating_output_or_child(self):
        with patch.object(guard, 'preflight', side_effect=RuntimeError('unreleased')), \
                patch.object(supervisor, 'run_stage', side_effect=AssertionError('must not spawn')):
            with self.assertRaisesRegex(RuntimeError, 'unreleased'): supervisor.supervise(self.project)
        self.assertFalse(self.output.exists())
        self.location['run'].mkdir(parents=True)
        with patch.object(guard, 'preflight', side_effect=AssertionError('must not preflight existing run')):
            with self.assertRaisesRegex(ValueError, 'all three'): supervisor.supervise(self.project)

    def test_negative_audit_is_operational_failure_not_scientific_gate_rescue(self):
        def failed(*args, **kwargs):
            result = self.child(*args, **kwargs)
            if kwargs['name'] == 'audit':
                directory = kwargs['stage_output']; report = guard.read(directory/'report.json')
                report['result']['verified'] = False; put(directory/'report.json', report)
                put(directory/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(directory/'report.json')}))
                result['complete_sha256'] = guard.sha(directory/'COMPLETE.json')
            return result
        with self.assertRaisesRegex(ValueError, 'independent320'): self.run_supervisor(child=failed)
        self.assertEqual(len(self.calls), 11); self.assertTrue((self.output/'FAILED.json').exists())
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_terminal_progress_failure_never_leaves_complete(self):
        event = supervisor.event
        def failed(*args, **kwargs):
            if kwargs.get('phase') == 'complete': raise OSError('terminal progress failed')
            return event(*args, **kwargs)
        with patch.object(supervisor, 'event', failed), self.assertRaisesRegex(OSError, 'terminal progress'):
            self.run_supervisor()
        self.assertTrue((self.output/'FAILED.json').exists()); self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_fixed_resource_configuration_cannot_be_overridden_by_cli(self):
        self.assertEqual(set(supervisor.TIMEOUTS), set(guard.STAGES))
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            supervisor.main(['--project', str(self.project), '--timeout', '1'])


if __name__ == '__main__': unittest.main()
