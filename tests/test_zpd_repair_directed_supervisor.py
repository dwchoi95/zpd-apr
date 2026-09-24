"""Mock-child fixed10 lifecycle checks; no production files or fitting."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import guard_zpd_repair_directed as guard
from scripts import supervise_zpd_repair_directed as supervisor
from tests.test_zpd_repair_directed_guard import put


class DirectedSupervisorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        mock = patch.object(guard, 'PROJECT', self.project); mock.start(); self.addCleanup(mock.stop)
        self.location = guard.paths(self.project); self.output = self.location['supervisor']; self.calls = []
        self.context = dict(source={'revision': 'a'*40, 'tree': 'b'*40}, release_sha256='c'*64,
            source_sha256={}, input_sha256={}, runtime=guard.RUNTIME, project=str(self.project), label_contracts={})
        # Reused preparation MUST exist; supervisor must neither require it to
        # be new nor write/regenerate it. All bodies are synthetic placeholders.
        for fold in [*range(5), None]:
            name = 'assessment/all320-labels.json' if fold is None else f'fold-{fold}/train-labels.json'
            path = self.location['prepared']/name; put(path, {'synthetic_only': fold})
            self.context['label_contracts']['assessment' if fold is None else str(fold)] = dict(
                expected_sha256=guard.sha(path), expected_fold_assignment_sha256='b'*64, expected_source_binding_sha256='a'*64)
        self.original_labels = {str(path): path.read_bytes() for path in self.location['prepared'].rglob('*.json')}
        self.gate = dict(passed=False, actual_repair_improvement=False, mechanism_contribution=False)

    def child(self, command, *, name, cwd, stage_output, output, timeout_seconds, heartbeat_seconds, memory_bytes):
        self.calls.append(name)
        self.assertEqual(command[:4], [supervisor.sys.executable, '-B', '-m', 'scripts.guard_zpd_repair_directed'])
        self.assertEqual(command[4:], ['--project', str(self.project), '--stage', name])
        self.assertEqual(stage_output, self.output/'stages'/name); self.assertFalse(stage_output.exists())
        self.assertEqual(timeout_seconds, 3600 if name.startswith('fold-') or name == 'audit' else 900)
        self.assertEqual(memory_bytes, 32*1024**3); self.assertEqual(heartbeat_seconds, 30)
        stage_output.mkdir(parents=True); result = {}
        if name.startswith('fold-'): result['predicted_examples'] = 64
        if name == 'assess':
            put(self.location['run']/'assessment/report.json', dict(gate=self.gate))
            put(self.location['run']/'COMPLETE.json', dict(status='synthetic_complete'))
        if name == 'audit':
            result = dict(verified=True, recipients=320, models=25, methods=11, gate=self.gate,
                          experiment_complete_sha256=guard.sha(self.location['run']/'COMPLETE.json'))
            put(self.location['verified']/'report.json', result)
            put(self.location['verified']/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(self.location['verified']/'report.json')}))
        put(stage_output/'report.json', dict(kind='repair_directed_production_stage_v2',
            stage=name, source=self.context['source'], release_sha256=self.context['release_sha256'], result=result))
        put(stage_output/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(stage_output/'report.json')}))
        log = self.output/(name+'.log'); log.write_text('synthetic child\n')
        return dict(name=name, output=str(stage_output), returncode=0, elapsed_seconds=.01,
            complete_sha256=guard.sha(stage_output/'COMPLETE.json'), files_verified=1, log_sha256=guard.sha(log))

    def verify(self, project, stage, *, deep=False):
        self.assertTrue(deep); directory = self.output/'stages'/stage
        marker = guard.read(directory/'COMPLETE.json')
        self.assertEqual(marker['files_sha256']['report.json'], guard.sha(directory/'report.json'))
        return dict(complete_sha256=guard.sha(directory/'COMPLETE.json'), report=guard.read(directory/'report.json'))

    def run_supervisor(self, child=None, verify=None, recheck=None):
        with contextlib.redirect_stdout(io.StringIO()), patch.object(guard, 'preflight', return_value=self.context), \
                patch.object(guard, 'recheck', side_effect=recheck), patch.object(guard, 'verify_wrapper', side_effect=verify or self.verify), \
                patch.object(supervisor, 'run_stage', side_effect=child or self.child):
            return supervisor.supervise(self.project)

    def test_exact10_children_existing_labels_readonly_fixed_caps_and_no_promotion(self):
        result = self.run_supervisor()
        self.assertEqual(self.calls, list(guard.STAGES)); self.assertEqual(len(self.calls), 10)
        self.assertNotIn('prepare', self.calls)
        manifest = guard.read(self.output/'manifest.json')
        self.assertEqual(manifest['kind'], 'bounded_repair_directed_10_stage_supervisor_v2')
        self.assertEqual(manifest['maximum_child_budget_seconds'], 25200)
        self.assertEqual(guard.release_configuration()['stage_timeout_seconds'], supervisor.TIMEOUTS)
        self.assertFalse(manifest['preparation_permitted']); self.assertEqual(manifest['automatic_retries'], 0)
        self.assertFalse(result['development_repair_gate_passed']); self.assertFalse(result['model_promotion'])
        self.assertFalse(result['confirmatory']); self.assertFalse(result['educational_benefit_established'])
        marker = guard.read(self.output/'COMPLETE.json')
        self.assertEqual(marker['completed_stages'], 10); self.assertEqual(marker['completed_oof_examples'], 320)
        for name, digest in marker['files_sha256'].items(): self.assertEqual(guard.sha(self.output/name), digest)
        for name, data in self.original_labels.items(): self.assertEqual(Path(name).read_bytes(), data)
        self.assertTrue(all(stage+'.log' in marker['files_sha256'] for stage in guard.STAGES))

    def test_existing_v1_failure_is_preserved_without_resume_or_splicing(self):
        family = self.project/guard.FAMILY
        old_files = {family/'run-v1/FAILED.json': {'preserved_v1_failure': True},
                     family/'run-v1/fold-2/H.json': {'partial_v1_model': True},
                     family/'supervised-v1/FAILED.json': {'preserved_v1_supervisor': True}}
        for path, value in old_files.items(): put(path, value)
        before = {path: path.read_bytes() for path in old_files}
        self.run_supervisor()
        self.assertEqual(self.calls, list(guard.STAGES))
        self.assertEqual(self.location['run'], family/'run-v2')
        self.assertEqual(self.output, family/'supervised-v2')
        for path, value in before.items(): self.assertEqual(path.read_bytes(), value)
        self.assertTrue((self.output/'COMPLETE.json').exists())

    def test_child_failure_stops_without_retry_and_keeps_previous_complete(self):
        def failed(*args, **kwargs):
            if kwargs['name'] == 'fold-1': raise TimeoutError('fixed cap reached')
            return self.child(*args, **kwargs)
        with self.assertRaisesRegex(TimeoutError, 'fixed cap'): self.run_supervisor(child=failed)
        self.assertEqual(self.calls, ['preflight', 'initialize', 'fold-0'])
        self.assertTrue((self.output/'FAILED.json').exists()); self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'stages/fold-0/COMPLETE.json').exists())
        self.assertFalse((self.output/'stages/fold-2').exists())

    def test_prior_stage_seal_drift_prevents_next_child(self):
        def changed(*args, **kwargs):
            result = self.child(*args, **kwargs)
            if kwargs['name'] == 'initialize':
                path = self.output/'stages/preflight/COMPLETE.json'; put(path, dict(guard.read(path), changed=True))
            return result
        with self.assertRaisesRegex(ValueError, 'previous'): self.run_supervisor(child=changed)
        self.assertEqual(self.calls, ['preflight', 'initialize'])
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_prior_child_log_drift_prevents_next_child(self):
        def changed(*args, **kwargs):
            result = self.child(*args, **kwargs)
            if kwargs['name'] == 'initialize': (self.output/'preflight.log').write_text('changed')
            return result
        with self.assertRaisesRegex(ValueError, 'previous child log'): self.run_supervisor(child=changed)
        self.assertEqual(self.calls, ['preflight', 'initialize'])

    def test_unreleased_and_existing_run_fail_before_children_or_new_outputs(self):
        with patch.object(guard, 'preflight', side_effect=RuntimeError('unreleased')), \
                patch.object(supervisor, 'run_stage', side_effect=AssertionError('must not spawn')):
            with self.assertRaisesRegex(RuntimeError, 'unreleased'): supervisor.supervise(self.project)
        self.assertFalse(self.output.exists())
        self.location['run'].mkdir(parents=True)
        with patch.object(guard, 'preflight', side_effect=AssertionError('preflight should not run')):
            with self.assertRaisesRegex(ValueError, 'new directed'): supervisor.supervise(self.project)

    def test_invalid_audit_cannot_be_rescued_by_a_scientific_gate(self):
        def failed(*args, **kwargs):
            result = self.child(*args, **kwargs)
            if kwargs['name'] == 'audit':
                path = kwargs['stage_output']; report = guard.read(path/'report.json'); report['result']['verified'] = False
                put(path/'report.json', report)
                put(path/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(path/'report.json')}))
                result['complete_sha256'] = guard.sha(path/'COMPLETE.json')
            return result
        with self.assertRaisesRegex(ValueError, 'independent320'): self.run_supervisor(child=failed)
        self.assertEqual(len(self.calls), 10); self.assertTrue((self.output/'FAILED.json').exists())
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_label_drift_after_inner_audit_seal_prevents_supervisor_complete(self):
        def changed(*args, **kwargs):
            result = self.child(*args, **kwargs)
            if kwargs['name'] == 'audit': put(self.location['prepared']/'fold-1/train-labels.json', {'changed_after_audit': True})
            return result
        with self.assertRaisesRegex(ValueError, 'audit consumed label drift'): self.run_supervisor(child=changed)
        self.assertTrue((self.location['verified']/'COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists()); self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_terminal_event_failure_has_no_complete_and_cli_caps_not_overridable(self):
        actual = supervisor.event
        def failed(*args, **kwargs):
            if kwargs.get('phase') == 'complete': raise OSError('terminal event failed')
            return actual(*args, **kwargs)
        with patch.object(supervisor, 'event', failed), self.assertRaisesRegex(OSError, 'terminal event failed'):
            self.run_supervisor()
        self.assertFalse((self.output/'COMPLETE.json').exists())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            supervisor.main(['--project', str(self.project), '--timeout', '1'])


if __name__ == '__main__': unittest.main()
