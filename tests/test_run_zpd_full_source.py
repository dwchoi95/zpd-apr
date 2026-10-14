"""Mocked full-source orchestration; no model, SSH, or candidate execution."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_full_source as m


SHA = 'a' * 64
REVISION = 'b' * 40


def private_report():
    counts = {arm: dict(stable_ac=i, stable_regression=0, unknown=1, noop_selected=0)
              for i, arm in enumerate((*m.core.ARMS, 'noop'))}
    return dict(methods=[*m.core.ARMS, 'noop'], execution_complete=True,
        full=dict(examples=320, results={a: {'counts': c} for a, c in counts.items()}),
        folds={'0': {'synthetic': True}}, paired_H={'C': {'ac_gained': 0}},
        current_status_subgroups={'unknown': {'examples': 1}},
        development_gate=dict(decision='hold', passed=False, checks={'strict_pooled_ac_H_over_C': False}),
        historical_gate_status='not_applicable_to_new_generation_arms', historical_gates_evaluated=False,
        confirmatory=False, model_promotion=False, educational_benefit_established=False)


def terminal(phase):
    return dict(Id=m.unit(phase), LoadState='loaded', ActiveState='active', SubState='exited',
        Result='success', ExecMainCode='1', ExecMainStatus='0', MainPID='0', ControlGroup='')


class NamespaceAndCommandTests(unittest.TestCase):
    def test_namespace_changes_only_two_core_bindings_and_restores_on_error(self):
        before = dict(vars(m.core))
        with self.assertRaisesRegex(RuntimeError, 'synthetic'):
            with m.configured_core():
                self.assertEqual(m.core.FAMILY, m.FAMILY)
                self.assertEqual(m.core.unit('generation'), 'zpd-full-source-20261014-v1-generation.service')
                changed = {k for k, value in vars(m.core).items() if before.get(k) is not value}
                self.assertEqual(changed, {'FAMILY', 'unit'})
                raise RuntimeError('synthetic')
        self.assertIs(m.core.FAMILY, before['FAMILY'])
        self.assertIs(m.core.unit, before['unit'])

    def test_worker_delegates_to_unchanged_core_with_scoped_namespace(self):
        original_family, original_unit = m.core.FAMILY, m.core.unit
        observed = []
        def delegated(*args):
            observed.append((args, m.core.FAMILY, m.core.unit('private')))
        with patch.object(m, 'source_barrier', return_value=(REVISION, {})) as barrier, \
                patch.object(m.core, 'worker', side_effect=delegated) as worker:
            m.worker('private', Path('/snapshot/release.json'), SHA)
        worker.assert_called_once_with('private', Path('/snapshot/release.json'), SHA)
        self.assertEqual(observed[0][1:], (m.FAMILY, m.unit('private')))
        self.assertEqual(barrier.call_count, 2)
        self.assertIs(m.core.FAMILY, original_family)
        self.assertIs(m.core.unit, original_unit)

    def test_worker_refuses_bad_release_before_core_worker(self):
        with patch.object(m, 'source_barrier', side_effect=ValueError('bad release')), patch.object(m.core, 'worker') as worker:
            with self.assertRaisesRegex(ValueError, 'bad release'):
                m.worker('generation', Path('/snapshot/release.json'), SHA)
            worker.assert_not_called()

    def test_command_targets_new_wrapper_with_original_limits(self):
        for phase in m.PHASES:
            cmd = m.command(phase, Path('/snapshot/release.json'), SHA, Path('/snapshot'))
            self.assertIn('--unit=' + m.unit(phase), cmd)
            self.assertEqual(cmd[cmd.index('-m') + 1], 'scripts.run_zpd_full_source')
            self.assertNotIn('scripts.run_zpd_transition_generation', cmd)
            memory, tasks, address = m.core.limits(phase)
            for item in (f'--property=MemoryMax={memory}', f'--property=TasksMax={tasks}',
                    f'--property=LimitAS={address}', '--property=RuntimeMaxSec=21600', '--property=Restart=no',
                    '--property=WorkingDirectory=/snapshot'):
                self.assertIn(item, cmd)
            self.assertIn(str(m.PROJECT / ('.runtime/fse-vllm/bin/python' if phase == 'generation' else '.runtime/fse-env/bin/python')), cmd)
            self.assertEqual(cmd[-6:], ['--phase', phase, '--release', '/snapshot/release.json', '--release-sha', SHA])


class RepresentationReleaseTests(unittest.TestCase):
    def test_variant_baseline_and_renderer_pin_are_explicit(self):
        self.assertEqual(m.VARIANT, 'full_source_messages_v1')
        self.assertEqual(str(m.BASELINE_INPUTS), '/home/cdw/VSCode/zpd-apr/outputs/zpd-current-last-inputs-20261013-v1/inputs.json')
        self.assertEqual(m.BASELINE_INPUTS_SHA, 'b49107c71a4df2a7318c9b93f7b42d29a03f502a0e81ce27735310efe7b2515f')
        self.assertIn('scripts/prepare_zpd_full_source.py', m.REQUIRED_SOURCE_PINS)

    def test_core_input_binding_accepts_provenance_json_separate_from_model_messages(self):
        from tests.test_run_zpd_transition_generation import fixture
        inputs, _ = fixture(320)
        for prompt in inputs['prompts']:
            prompt['user_json'] = '{"provenance":"original JSON"}'
            prompt['messages'] = [{'role': 'system', 'content': 'synthetic'},
                                  {'role': 'user', 'content': 'full source model message'}]
        with patch.object(m.core, 'read_pinned', return_value=inputs):
            result = m.core.inputs_for(dict(inputs_path='synthetic', inputs_sha256=SHA))
        self.assertIs(result, inputs)
        self.assertNotEqual(result['prompts'][0]['user_json'], result['prompts'][0]['messages'][1]['content'])
        self.assertEqual(len(result['recipients']), 320)
        self.assertEqual(len(result['prompts']), 1280)
        self.assertEqual(len(result['attempts']), 2560)

    def test_release_requires_full_source_paths_and_sealed_preparation(self):
        original, revised = {'old_provenance': True}, {'new_messages': True}
        release = dict(layout_variant=m.VARIANT, family_path=str(m.FAMILY), inputs_path='/snapshot/inputs.json',
            excluded_recipients=0, draws_per_arm=2, retries=0, fitting=False, no_retry=True, no_truncation=True,
            source_sha256={name: SHA for name in m.REQUIRED_SOURCE_PINS}, inputs_complete_sha256=SHA, inputs_sha256=SHA)
        complete = dict(status='complete', layout_variant=m.VARIANT, files_sha256={'inputs.json': SHA})
        def read(path, digest):
            return original if Path(path) == m.BASELINE_INPUTS else complete
        with patch.object(m, 'INPUTS', Path('/snapshot/inputs.json')), \
                patch.object(m.core, 'inputs_for', return_value=revised), patch.object(m.core, 'read_pinned', side_effect=read), \
                patch.object(m.core, 'sha_file', return_value=SHA), \
                patch.object(m, 'validate_representation') as validate:
            with patch.object(m.core, 'load_release', return_value=release):
                self.assertEqual(m.load_release(Path('/snapshot/release.json'), SHA), release)
                validate.assert_called_once_with(revised, original)
                with patch.object(m, 'validate_representation', side_effect=ValueError('representation corruption')):
                    with self.assertRaisesRegex(ValueError, 'representation corruption'):
                        m.load_release(Path('/snapshot/release.json'), SHA)
            for key, value in [('layout_variant', 'old'), ('family_path', str(m.core.FAMILY)),
                    ('inputs_path', str(m.BASELINE_INPUTS)), ('excluded_recipients', 1), ('fitting', True),
                    ('retries', 1), ('draws_per_arm', 8), ('source_sha256', {})]:
                changed = deepcopy(release); changed[key] = value
                with self.subTest(key=key), patch.object(m.core, 'load_release', return_value=changed), self.assertRaises(ValueError):
                    m.load_release(Path('/snapshot/release.json'), SHA)
            complete['layout_variant'] = 'old'
            with patch.object(m.core, 'load_release', return_value=release), self.assertRaisesRegex(ValueError, 'preparation seal'):
                m.load_release(Path('/snapshot/release.json'), SHA)


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.family = self.root / 'family'
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m, 'FAMILY', self.family))
        self.stack.enter_context(patch.object(m, 'source_barrier', return_value=(REVISION, {})))
        self.launched, self.stopped, self.corrupt, self.failed = [], [], None, None
        self.stack.enter_context(patch.object(m.core, 'props', side_effect=self.props))
        self.stack.enter_context(patch.object(m.subprocess, 'run', side_effect=self.fake_run))
        self.terminal = self.stack.enter_context(patch.object(m, 'terminal_group', return_value=dict(
            recorded_control_group='/synthetic', returned_control_group='', cgroup_removed=True, cleanup_verified=True)))

    def props(self, name):
        phase = next(p for p in m.PHASES if name == m.unit(p))
        if phase not in self.launched: return {'LoadState': 'not-found'}
        value = terminal(phase)
        if phase == self.failed: value.update(ActiveState='failed', SubState='failed', Result='exit-code', ExecMainStatus='1')
        return value

    def fake_run(self, cmd, **kwargs):
        if cmd[0] == '/usr/bin/systemctl':
            self.stopped.append(cmd[-1]); return
        phase = cmd[cmd.index('--phase') + 1]
        self.launched.append(phase)
        output = self.family / (phase + '-v1'); output.mkdir()
        m.core.write_new(output / 'stage-manifest.json', dict(phase=phase, revision=REVISION, release_sha256=SHA,
            envelope={'cgroup': '/synthetic/' + m.unit(phase)}))
        if phase == 'private':
            evaluation = output / 'evaluation'; evaluation.mkdir()
            m.core.write_new(evaluation / 'report.json', private_report())
            m.core.write_new(evaluation / 'COMPLETE.json', dict(status='complete', provisional_until_normal_unit_exit=True,
                files_sha256={'report.json': m.core.sha_file(evaluation / 'report.json')}))
        m.core.seal_stage(output, phase, SHA)
        if phase == self.corrupt:
            (output / 'FAILED.json').write_bytes(b'{}\n')

    def test_all_phases_normal_exit_seals_report_and_releases_exact_workers(self):
        summary = m.supervise(self.root / 'release.json', SHA)
        self.assertEqual(self.launched, list(m.PHASES))
        self.assertEqual(self.stopped, [m.unit(p) for p in m.PHASES])
        self.assertEqual(self.terminal.call_count, 3)
        marker = json.loads((self.family / 'VERIFIED_COMPLETE.json').read_bytes())
        self.assertEqual(set(marker['phases']), set(m.PHASES))
        self.assertFalse(marker['model_promotion'])
        self.assertEqual(marker['files_sha256']['REPORT.json'], m.core.sha_file(self.family / 'REPORT.json'))
        self.assertEqual(summary['development_gate'], private_report()['development_gate'])
        self.assertEqual(summary['counts']['H']['stable_ac'], 1)
        self.assertEqual(summary['historical_gate_status'], private_report()['historical_gate_status'])
        self.assertIn('모델 승격', summary['summary_ko'])

    def test_duplicate_family_or_existing_unit_never_launches(self):
        self.family.mkdir()
        with self.assertRaisesRegex(ValueError, 'family already exists'):
            m.supervise(self.root / 'release.json', SHA)
        self.assertEqual(self.launched, [])
        with patch.object(m, 'FAMILY', self.root / 'other'), patch.object(m.core, 'props', return_value={'LoadState': 'loaded'}):
            with self.assertRaisesRegex(ValueError, 'unit already exists'):
                m.supervise(self.root / 'release.json', SHA)
        self.assertFalse((self.root / 'other').exists())

    def test_failed_stage_stops_and_cannot_launch_next_phase_or_complete(self):
        self.failed = 'generation'
        with self.assertRaisesRegex(ValueError, 'did not exit normally'):
            m.supervise(self.root / 'release.json', SHA)
        self.assertEqual(self.launched, ['generation'])
        self.assertEqual(self.stopped, [m.unit('generation')])
        self.assertFalse((self.family / 'generation-VERIFIED_COMPLETE.json').exists())
        self.assertFalse((self.family / 'VERIFIED_COMPLETE.json').exists())
        failure = json.loads((self.family / 'COORDINATOR_FAILED.json').read_bytes())
        self.assertEqual(failure['completed_phases'], [])
        self.assertEqual(failure['retries'], 0)

    def test_corrupt_stage_blocks_continuation_even_after_exit_zero(self):
        self.corrupt = 'public'
        with self.assertRaisesRegex(ValueError, 'extra or missing'):
            m.supervise(self.root / 'release.json', SHA)
        self.assertEqual(self.launched, ['generation', 'public'])
        self.assertFalse((self.family / 'private-v1').exists())
        self.assertFalse((self.family / 'public-VERIFIED_COMPLETE.json').exists())

    def test_terminal_descendant_failure_blocks_certification(self):
        self.terminal.side_effect = ValueError('worker descendants remain')
        with self.assertRaisesRegex(ValueError, 'descendants'):
            m.supervise(self.root / 'release.json', SHA)
        self.assertEqual(self.launched, ['generation'])
        self.assertFalse((self.family / 'generation-VERIFIED_COMPLETE.json').exists())

    def test_launch_timeout_stops_exact_attempted_unit_without_retry(self):
        def timeout_after_creation(cmd, **kwargs):
            if cmd[0] == '/usr/bin/systemd-run':
                raise m.subprocess.TimeoutExpired(cmd, 30)
            self.stopped.append(cmd[-1])
        with patch.object(m.subprocess, 'run', side_effect=timeout_after_creation):
            with self.assertRaises(m.subprocess.TimeoutExpired):
                m.supervise(self.root / 'release.json', SHA)
        self.assertEqual(self.stopped, [m.unit('generation')])
        failure = json.loads((self.family / 'COORDINATOR_FAILED.json').read_bytes())
        self.assertEqual(failure['launched_phases'], ['generation'])
        self.assertEqual(failure['completed_phases'], [])
        self.assertEqual(failure['exact_unit_cleanup'], {'generation': 'stop_completed'})
        self.assertFalse((self.family / 'VERIFIED_COMPLETE.json').exists())


class ReportTests(unittest.TestCase):
    def test_report_keeps_raw_gate_and_does_not_reinterpret_proceed_as_promotion(self):
        report = private_report()
        report['development_gate'].update(decision='proceed', passed=True)
        summary = m.summarize_private(report, SHA, 'c' * 64)
        self.assertEqual(summary['development_gate'], report['development_gate'])
        self.assertEqual(summary['private_report_sha256'], 'c' * 64)
        self.assertFalse(summary['historical_gates_evaluated'])
        self.assertFalse(summary['historical_gates_passed'])
        self.assertFalse(summary['model_promotion'])
        self.assertFalse(summary['confirmatory'])
        self.assertFalse(summary['educational_benefit_established'])
        self.assertEqual(summary['intervention_kind'], 'representation_package')
        self.assertFalse(summary['pure_order_ablation'])
        self.assertFalse(summary['training_distribution_alignment_established'])
        self.assertFalse(summary['history_model_established'])
        self.assertIn('previous JSON-diff package', summary['limitations'][0])
        self.assertEqual(summary['methods'], ['C', 'H', 'HS', 'U', 'noop'])
        report['development_gate']['checks']['new'] = True
        self.assertNotIn('new', summary['development_gate']['checks'])

    def test_incomplete_or_claim_expanded_private_report_refuses(self):
        for key, value in [('execution_complete', False), ('model_promotion', True),
                ('historical_gates_evaluated', True), ('confirmatory', True)]:
            report = private_report(); report[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                m.summarize_private(report, SHA, SHA)


if __name__ == '__main__':
    unittest.main()
