"""Mocked eight-phase lifecycle only; no SSH, systemd, GPU or submitted code."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_paired_history as m
from scripts import train_zpd_paired_history as training
from tests.test_run_zpd_full_source import private_report

SHA, INFER_SHA, REV = 'a' * 64, 'c' * 64, 'b' * 40


def terminal(phase):
    return dict(Id=m.unit(phase), LoadState='loaded', ActiveState='active', SubState='exited',
        Result='success', ExecMainCode='1', ExecMainStatus='0', MainPID='0', ControlGroup='')


def summary(arm):
    return dict(arm=arm, status='complete', actual_fit=True, seed=2027, config=deepcopy(training.CONFIG),
        lora=deepcopy(training.LORA), completed_epochs=1.0, truncation=False, exclusions=0,
        checkpoint_selection='fixed_final_epoch', validation_role='descriptive_only_no_checkpoint_selection',
        model_promotion=False, initial_adapter=dict(sha256=SHA, trainable_parameters=12, tensors=2),
        base_model='/base', completed_steps=2, train_preflight_sha256=SHA, validation_preflight_sha256=SHA,
        validation_examples=3, runtime_versions={'torch': 'fixture'},
        coverage=dict(consumed_order_sha256=SHA, planned_order_sha256=SHA,
                      completed_examples=8, unique_completed_examples=8, total_examples=8),
        adapter_files_sha256={})


class CommandsAndGuardTests(unittest.TestCase):
    def test_fixed_eight_phase_limits_and_interpreters(self):
        self.assertEqual(m.PHASES, ('cache', 'materialize', 'capacity', 'train-C', 'train-H', 'generation', 'public', 'private'))
        for phase in m.PHASES:
            cmd = m.command(phase, Path('/snapshot/release.json'), SHA, Path('/snapshot'))
            self.assertEqual(cmd[cmd.index('-m') + 1], 'scripts.run_zpd_paired_history')
            memory, tasks, address = m.limits(phase)
            for flag in (f'--property=MemoryMax={memory}', f'--property=TasksMax={tasks}',
                         f'--property=LimitAS={address}', f'--property=RuntimeMaxSec={m.PHASE_SECONDS[phase]}',
                         '--property=Restart=no', '--property=KillMode=control-group',
                         '--property=WorkingDirectory=/snapshot', '--unit=' + m.unit(phase)):
                self.assertIn(flag, cmd)
            gpu = phase in ('materialize', 'capacity', 'train-C', 'train-H', 'generation')
            self.assertIn(str(m.PROJECT / ('.runtime/fse-vllm/bin/python' if gpu else '.runtime/fse-env/bin/python')), cmd)
            self.assertIn('--setenv=TMPDIR=' + str(m.FAMILY / 'tmp' / phase), cmd)
        self.assertEqual(m.limits('materialize'), (16 * 2**30, 128, str(16 * 2**30)))
        self.assertEqual(m.PHASE_SECONDS['train-H'], 86400)
        self.assertEqual(m.PHASE_SECONDS['cache'], 43200)

    def test_core_namespace_mutates_only_family_unit_generation_and_restores(self):
        before = dict(vars(m.core))
        with self.assertRaisesRegex(RuntimeError, 'fixture'):
            with m.configured_core():
                self.assertEqual({k for k, v in vars(m.core).items() if before.get(k) is not v},
                                 {'FAMILY', 'unit', 'generation'})
                self.assertEqual(m.core.FAMILY, m.FAMILY)
                raise RuntimeError('fixture')
        for key in ('FAMILY', 'unit', 'generation'):
            self.assertIs(vars(m.core)[key], before[key])

    def test_guard_throttles_os_checks_but_not_monotonic_deadline(self):
        now = [0.0]
        with patch.object(m.time, 'monotonic', side_effect=lambda: now[0]), patch.object(m, 'envelope') as envelope:
            guard = m.PhaseGuard('cache')
            for moment in (0, 0.1, 1, 4.99, 5, 7, 9.9):
                now[0] = moment
                guard()
            self.assertEqual(envelope.call_count, 2)
            guard(force=True)
            self.assertEqual(envelope.call_count, 3)
            now[0] = 43200
            with self.assertRaisesRegex(ValueError, 'monotonic deadline'):
                guard()
            self.assertEqual(envelope.call_count, 3)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.family = Path(self.tmp.name).resolve() / 'run'
        self.patch = patch.object(m, 'FAMILY', self.family); self.patch.start(); self.addCleanup(self.patch.stop)

    def test_early_worker_requires_guards_source_barriers_inner_result_and_outer_seal(self):
        calls = []
        release = dict(training_versions={})
        with patch.object(m, 'source_barrier', return_value=(REV, release)) as barrier, \
                patch.object(m, 'envelope', return_value={'cgroup': '/fixture'}), \
                patch.object(m, 'run_early_phase', side_effect=lambda *a: calls.append(a[0])), \
                patch.object(m, 'validate_phase_result') as validate:
            m.worker('cache', Path('/snapshot/release.json'), SHA)
        self.assertEqual(calls, ['cache'])
        self.assertEqual(barrier.call_count, 2)
        validate.assert_called_once()
        sealed = m.core.verify_stage(self.family / 'cache-v1', 'cache', SHA)
        self.assertIn('stage-manifest.json', sealed['files_sha256'])

    def test_failed_primitive_leaves_failed_and_no_outer_complete(self):
        with patch.object(m, 'source_barrier', return_value=(REV, {})), \
                patch.object(m, 'envelope', return_value={'cgroup': '/fixture'}), \
                patch.object(m, 'run_early_phase', side_effect=RuntimeError('fixture failure')):
            with self.assertRaisesRegex(RuntimeError, 'fixture failure'):
                m.worker('cache', Path('/snapshot/release.json'), SHA)
        self.assertTrue((self.family / 'cache-v1/FAILED.json').exists())
        self.assertFalse((self.family / 'cache-v1/STAGE_COMPLETE.json').exists())

    def test_missing_inner_completion_cannot_be_outer_sealed(self):
        with patch.object(m, 'source_barrier', return_value=(REV, {})), \
                patch.object(m, 'envelope', return_value={'cgroup': '/fixture'}), \
                patch.object(m, 'run_early_phase'):
            with self.assertRaises(FileNotFoundError):
                m.worker('cache', Path('/snapshot/release.json'), SHA)
        self.assertTrue((self.family / 'cache-v1/FAILED.json').exists())
        self.assertFalse((self.family / 'cache-v1/STAGE_COMPLETE.json').exists())

    def test_inference_delegates_unchanged_core_worker_with_dynamic_release(self):
        dynamic = self.family / 'inference-release.json'
        observed = []
        def delegated(*args):
            observed.append((args, m.core.FAMILY, m.core.unit('private')))
        with patch.object(m, 'source_barrier', return_value=(REV, {})), \
                patch.object(m, 'verified_dependency') as dependency, \
                patch.object(m, 'inference_release', return_value=(dynamic, INFER_SHA)), \
                patch.object(m.core, 'worker', side_effect=delegated):
            m.worker('private', Path('/snapshot/parent.json'), SHA)
        self.assertEqual(observed, [(('private', dynamic, INFER_SHA), self.family, m.unit('private'))])
        self.assertEqual([call.args[0] for call in dependency.call_args_list], list(m.PHASES[:-1]))

    def test_actual_core_dependency_reads_scoped_family_and_dynamic_pin(self):
        output = self.family / 'generation-v1'; output.mkdir(parents=True)
        m.core.write_new(output / 'fixture.json', {'complete': True})
        m.core.seal_stage(output, 'generation', INFER_SHA)
        m.core.write_new(self.family / 'generation-VERIFIED_COMPLETE.json', dict(status='complete',
            release_sha256=INFER_SHA, complete_sha256=m.core.sha_file(output / 'STAGE_COMPLETE.json'),
            exit=terminal('generation')))
        with m.configured_core():
            seal = m.core.verified_dependency('generation', INFER_SHA)
            self.assertEqual(seal['phase'], 'generation')
            with self.assertRaisesRegex(ValueError, 'dependency seal differs'):
                m.core.verified_dependency('generation', SHA)

    def test_runtime_version_mismatch_prevents_training(self):
        with patch.object(m, 'source_barrier', return_value=(REV, {'training_versions': {'torch': 'required'}})), \
                patch.object(m, 'verified_dependency'), patch.object(m, 'envelope', return_value={'cgroup': '/fixture'}), \
                patch.object(m, 'version', return_value='wrong'), patch.object(m, 'run_early_phase') as run:
            with self.assertRaisesRegex(ValueError, 'training runtime differs'):
                m.worker('train-C', Path('/snapshot/parent.json'), SHA)
        run.assert_not_called()


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.family = Path(self.tmp.name).resolve() / 'family'
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m, 'FAMILY', self.family))
        self.stack.enter_context(patch.object(m, 'source_barrier', return_value=(REV, {})))
        self.stack.enter_context(patch.object(m, 'validate_phase_result'))
        self.launched, self.stopped, self.certified = [], [], []
        self.fail_exit = self.fail_cleanup = self.fail_launch = None

        def props(name):
            phase = next(p for p in m.PHASES if m.unit(p) == name)
            if phase not in self.launched:
                return {'LoadState': 'not-found'}
            value = terminal(phase)
            if self.fail_exit == phase:
                value.update(Result='exit-code', ExecMainStatus='1', ActiveState='failed')
            return value

        def run(cmd, **kwargs):
            if cmd[0] == '/usr/bin/systemctl':
                self.stopped.append(cmd[-1]); return
            phase = cmd[cmd.index('--phase') + 1]
            # Every previous phase must already be normal-exit/cleanup certified.
            self.assertEqual(self.certified, list(m.PHASES[:m.PHASES.index(phase)]))
            self.launched.append(phase)
            if self.fail_launch == phase:
                raise TimeoutError('launch timeout after possible unit creation')
            output = self.family / (phase + '-v1'); output.mkdir()
            pin = INFER_SHA if phase in m.INFERENCE else SHA
            m.core.write_new(output / 'stage-manifest.json', dict(phase=phase, revision=REV,
                release_sha256=pin, envelope={'cgroup': '/user.slice/user-1000.slice/' + m.unit(phase)}))
            m.core.write_new(output / 'fixture.json', {'phase': phase})
            m.core.seal_stage(output, phase, pin)

        def cleanup(values, recorded, name):
            phase = next(p for p in m.PHASES if m.unit(p) == name)
            if self.fail_cleanup == phase:
                raise ValueError('worker descendants remain')
            self.certified.append(phase)
            return dict(recorded_control_group=recorded, returned_control_group='',
                        cgroup_removed=True, cleanup_verified=True)

        def inference(*args, create=False):
            if create:
                self.assertEqual(self.certified, list(m.PHASES[:5]))
                m.core.write_new(self.family / 'inference-release.json', {'fixture': True})
                m.core.write_new(self.family / 'INFERENCE_RELEASE_COMPLETE.json', {'fixture': True})
            return self.family / 'inference-release.json', INFER_SHA

        self.stack.enter_context(patch.object(m.core, 'props', side_effect=props))
        self.stack.enter_context(patch.object(m.subprocess, 'run', side_effect=run))
        self.stack.enter_context(patch.object(m, 'terminal_group', side_effect=cleanup))
        self.stack.enter_context(patch.object(m, 'inference_release', side_effect=inference))
        self.stack.enter_context(patch.object(m, '_inference_pin', return_value=(self.family / 'inference-release.json', INFER_SHA)))
        self.finish = self.stack.enter_context(patch.object(m, 'finalize', return_value={'complete': True}))

    def run_coordinator(self):
        return m.supervise(Path('/snapshot/parent.json'), SHA)

    def test_success_advances_all_eight_only_after_normal_exit_and_cleanup(self):
        self.assertEqual(self.run_coordinator(), {'complete': True})
        self.assertEqual(self.launched, list(m.PHASES))
        self.assertEqual(self.certified, list(m.PHASES))
        for phase in m.PHASES:
            marker = json.loads((self.family / (phase + '-VERIFIED_COMPLETE.json')).read_bytes())
            self.assertTrue(marker['cleanup_verified'])
            self.assertEqual(marker['parent_release_sha256'], SHA)
            self.assertEqual(marker['release_sha256'], INFER_SHA if phase in m.INFERENCE else SHA)
        self.finish.assert_called_once()

    def test_nonzero_exit_prevents_successor_even_with_valid_stage_seal(self):
        self.fail_exit = 'capacity'
        with self.assertRaisesRegex(ValueError, 'did not exit normally'):
            self.run_coordinator()
        self.assertEqual(self.launched, ['cache', 'materialize', 'capacity'])
        self.assertFalse((self.family / 'capacity-VERIFIED_COMPLETE.json').exists())
        self.assertTrue((self.family / 'COORDINATOR_FAILED.json').exists())
        self.finish.assert_not_called()

    def test_residual_descendant_prevents_successor_and_certificate(self):
        self.fail_cleanup = 'train-C'
        with self.assertRaisesRegex(ValueError, 'descendants remain'):
            self.run_coordinator()
        self.assertEqual(self.launched, ['cache', 'materialize', 'capacity', 'train-C'])
        self.assertFalse((self.family / 'train-C-VERIFIED_COMPLETE.json').exists())
        self.assertIn(m.unit('train-C'), self.stopped)

    def test_launch_timeout_cleans_exact_potentially_created_unit(self):
        self.fail_launch = 'cache'
        with self.assertRaises(TimeoutError):
            self.run_coordinator()
        self.assertEqual(self.launched, ['cache'])
        self.assertEqual(self.stopped, [m.unit('cache')])
        failure = json.loads((self.family / 'COORDINATOR_FAILED.json').read_bytes())
        self.assertEqual(failure['launched_phases'], ['cache'])
        self.assertEqual(failure['retries'], 0)

    def test_existing_family_forbids_retry_without_mutating_evidence(self):
        self.family.mkdir(); m.core.write_new(self.family / 'sentinel.json', {'keep': True})
        before = (self.family / 'sentinel.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'family already exists'):
            self.run_coordinator()
        self.assertEqual((self.family / 'sentinel.json').read_bytes(), before)
        self.assertEqual(self.launched, [])

    def test_existing_unit_forbids_start(self):
        with patch.object(m.core, 'props', return_value={'LoadState': 'loaded'}):
            with self.assertRaisesRegex(ValueError, 'unit already exists'):
                self.run_coordinator()
        self.assertFalse(self.family.exists())

    def test_source_drift_after_child_exit_blocks_certification(self):
        def barrier(*args):
            if self.launched:
                raise ValueError('source drift')
            return REV, {}
        with patch.object(m, 'source_barrier', side_effect=barrier):
            with self.assertRaisesRegex(ValueError, 'source drift'):
                self.run_coordinator()
        self.assertEqual(self.launched, ['cache'])
        self.assertEqual(self.certified, [])

    def test_stage_hash_drift_blocks_certification(self):
        original = m.core.verify_stage
        def altered(output, phase, pin):
            (output / 'fixture.json').write_bytes(b'changed')
            return original(output, phase, pin)
        with patch.object(m.core, 'verify_stage', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'artifact drift'):
                self.run_coordinator()
        self.assertEqual(self.launched, ['cache'])
        self.assertEqual(self.certified, [])


class TrainingPairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.family = Path(self.tmp.name).resolve()
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m, 'FAMILY', self.family))
        self.stack.enter_context(patch.object(m, 'verified_dependency'))
        self.summaries = {a: summary(a) for a in ('C', 'H')}
        for arm in ('C', 'H'):
            root = self.family / ('train-' + arm + '-v1/training'); root.mkdir(parents=True)
            m.core.write_new(root / 'training_summary.json', self.summaries[arm])
            m.core.write_new(root / 'COMPLETE.json', dict(status='complete',
                training_summary_sha256=m.core.sha_file(root / 'training_summary.json'),
                files_sha256={'training_summary.json': m.core.sha_file(root / 'training_summary.json')}))
        capacity = self.family / 'capacity-v1/probe'; capacity.mkdir(parents=True)
        m.core.write_new(capacity / 'capacity_report.json', dict(status='passed', actual_fit=False,
            optimizer_steps=0, published_adapter=False, initial_adapter=self.summaries['C']['initial_adapter']))

    def change(self, arm, change):
        row = deepcopy(self.summaries[arm]); change(row)
        root = self.family / ('train-' + arm + '-v1/training')
        (root / 'training_summary.json').write_bytes(m.core.encoded(row))
        (root / 'COMPLETE.json').write_bytes(m.core.encoded(dict(status='complete',
            training_summary_sha256=m.core.sha_file(root / 'training_summary.json'),
            files_sha256={'training_summary.json': m.core.sha_file(root / 'training_summary.json')})))

    def test_exact_matched_training_passes(self):
        result = m.verify_training_pair(SHA)
        self.assertEqual(result['C']['initial_adapter'], result['H']['initial_adapter'])

    def test_initialization_order_config_target_and_consumption_mismatches_fail(self):
        changes = [lambda r: r['initial_adapter'].update(sha256='d' * 64),
                   lambda r: r['config'].update(learning_rate=1.0),
                   lambda r: r.update(train_preflight_sha256='d' * 64),
                   lambda r: r['coverage'].update(consumed_order_sha256='d' * 64),
                   lambda r: r['coverage'].update(completed_examples=7)]
        for change in changes:
            self.change('H', change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                m.verify_training_pair(SHA)
        self.change('H', lambda r: None)
        self.assertEqual(m.verify_training_pair(SHA)['H']['seed'], 2027)


class ClaimBoundaryTests(unittest.TestCase):
    def test_summary_preserves_private_gate_and_exposes_training_population(self):
        private = private_report(); original = deepcopy(private)
        population = {'train': {'candidate_examples': 20, 'retained_examples': 16, 'excluded_examples': 4}}
        result = m.summarize_private(private, SHA, INFER_SHA, population)
        self.assertEqual(result['development_gate'], private['development_gate'])
        self.assertEqual(result['counts']['H'], private['full']['results']['H']['counts'])
        self.assertEqual(result['training_population'], population)
        self.assertEqual(result['adapter_arm_map'], {'C': 'C', 'H': 'H', 'HS': 'H', 'U': 'H'})
        self.assertFalse(result['model_promotion'])
        self.assertFalse(result['historical_gates_passed'])
        self.assertFalse(result['confirmatory'])
        self.assertEqual(private, original)

    def test_changed_private_gate_claim_boundary_is_rejected(self):
        private = private_report(); private['historical_gates_evaluated'] = True
        with self.assertRaisesRegex(ValueError, 'claim boundary'):
            m.summarize_private(private, SHA, INFER_SHA, {})


class DynamicInferenceReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.family = Path(self.tmp.name).resolve()
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m, 'FAMILY', self.family))
        self.parent = dict(version=m.VERSION, fitting=True, phase_seconds=m.PHASE_SECONDS,
                           model_sha256={'/base/config.json': SHA})
        self.stack.enter_context(patch.object(m, 'source_barrier', return_value=(REV, self.parent)))
        summaries = {}
        for arm in ('C', 'H'):
            row = summary(arm)
            root = self.family / ('train-' + arm + '-v1/training')
            (root / 'adapter').mkdir(parents=True)
            for name in ('adapter_model.safetensors', 'adapter_config.json'):
                path = root / 'adapter' / name
                path.write_bytes((arm + name).encode())
                row['adapter_files_sha256']['adapter/' + name] = m.core.sha_file(path)
            m.core.write_new(self.family / ('train-' + arm + '-VERIFIED_COMPLETE.json'), {'arm': arm})
            summaries[arm] = row
        self.stack.enter_context(patch.object(m, 'verify_training_pair', return_value=summaries))
        self.path = Path('/snapshot/parent.json')

    def test_dynamic_release_is_nofit_bound_to_parent_and_both_fresh_adapters(self):
        path, pin = m.inference_release(self.path, SHA, REV, create=True)
        body = m.core.read_pinned(path, pin)
        self.assertEqual(body['version'], 'transition_generation_release_v1')
        self.assertFalse(body['fitting'])
        self.assertEqual(body['phase_seconds'], 21600)
        self.assertEqual(body['parent_release_sha256'], SHA)
        self.assertEqual(body['parent_revision'], REV)
        self.assertEqual(body['adapter_arm_map'], m.ADAPTER_ARM_MAP)
        self.assertEqual(body['initial_trainable_sha256'], SHA)
        self.assertEqual(len(body['model_sha256']), 5)
        self.assertEqual(set(body['training_certificates_sha256']), {'C', 'H'})
        self.assertEqual(m.inference_release(self.path, SHA, REV), (path, pin))
        self.assertTrue(self.parent['fitting'])  # Parent never mutated into nofit.

    def test_dynamic_release_certificate_drift_cannot_be_resealed_or_reused(self):
        m.inference_release(self.path, SHA, REV, create=True)
        certificate = self.family / 'train-H-VERIFIED_COMPLETE.json'
        certificate.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'dynamic inference release binding differs'):
            m.inference_release(self.path, SHA, REV)
        with self.assertRaises(FileExistsError):
            m.inference_release(self.path, SHA, REV, create=True)

    def test_dynamic_release_adapter_file_drift_blocks_inference(self):
        m.inference_release(self.path, SHA, REV, create=True)
        (self.family / 'train-C-v1/training/adapter/adapter_model.safetensors').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'fresh adapter file differs'):
            m.inference_release(self.path, SHA, REV)


class ModelPinTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve() / 'snapshot'; self.base.mkdir()
        for name in ('config.json', 'tokenizer_config.json', 'tokenizer.json', 'generation_config.json'):
            m.core.write_new(self.base / name, {'fixture': name})
        m.core.write_new(self.base / 'model.safetensors.index.json', {'weight_map': {'a': 'model-01.safetensors'}})
        blob = self.base.parent / 'blob'; blob.write_bytes(b'fixture-weights')
        (self.base / 'model-01.safetensors').symlink_to(blob)
        self.release = dict(base_model=str(self.base), model_sha256={str(p): m.core.sha_file(p)
                           for p in self.base.iterdir() if p.is_file()})

    def test_exact_snapshot_inventory_accepts_huggingface_blob_symlinks(self):
        m.verify_base_model(self.release)

    def test_unpinned_extra_generation_config_and_old_adapter_are_rejected(self):
        for mode in ('missing_generation_config', 'old_adapter'):
            release = deepcopy(self.release)
            if mode == 'missing_generation_config':
                release['model_sha256'].pop(str(self.base / 'generation_config.json'))
            else:
                release['model_sha256'][str(self.base.parent / 'answer/adapter_model.safetensors')] = SHA
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'exact base'):
                m.verify_base_model(release)

    def test_index_cannot_reference_unpinned_shards(self):
        path = self.base / 'model.safetensors.index.json'
        path.write_bytes(m.core.encoded({'weight_map': {'a': 'missing.safetensors'}}))
        self.release['model_sha256'][str(path)] = m.core.sha_file(path)
        with self.assertRaisesRegex(ValueError, 'every indexed model shard'):
            m.verify_base_model(self.release)


if __name__ == '__main__':
    unittest.main()
