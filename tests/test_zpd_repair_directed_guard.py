"""Temporary synthetic releases/seals only; no empirical input or fitting."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import guard_zpd_repair_directed as guard
from scripts import run_zpd_repair_directed_cv as engine

REAL_BOUNDARY = guard.verify_child_boundary


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True)+'\n')


def wrapper(location, stage, context):
    directory = location['supervisor']/'stages'/stage
    put(directory/'report.json', dict(kind='repair_directed_production_stage_v2',
        stage=stage, status='complete', source=context['source'],
        release_sha256=context['release_sha256'], result={},
        engine_artifact_sha256={guard.FAMILY+'/'+name: guard.sha(location['family']/name) for name in guard._artifact_paths(stage)}))
    put(directory/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(directory/'report.json')}))
    return directory


def fold_outputs(location, fold):
    path = location['run']/f'fold-{fold}'
    for arm in engine.ARMS: put(path/(arm+'.json'), {'forbidden_prior_model_body': arm})
    put(path/'MODELS_COMPLETE.json', dict(model_files_sha256={arm+'.json': guard.sha(path/(arm+'.json')) for arm in engine.ARMS}))
    put(path/'predictions.json', []); put(path/'STATUS.json', {'phase': 'complete'})
    names = [*(arm+'.json' for arm in engine.ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json']
    put(path/'COMPLETE.json', dict(status='complete', fold=fold, completed_fits=5,
        files_sha256={name: guard.sha(path/name) for name in names}))


class DirectedGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.project = Path(temp.name).resolve(); self.root = self.project/'.runtime/source'; self.root.mkdir(parents=True)
        for obj, name, value in ((guard, 'PROJECT', self.project), (guard, 'ROOT', self.root)):
            self.mock_value(obj, name, value)
        self.state = dict(revision='a'*40, tree='b'*40)
        for name, value in (('source_state', self.state), ('runtime', guard.RUNTIME)):
            mock = patch.object(guard, name, return_value=value); mock.start(); self.addCleanup(mock.stop)
        track = patch.object(guard.subprocess, 'check_output', side_effect=lambda args, **kwargs: '\n'.join(args[args.index('--')+1:])+'\n')
        track.start(); self.addCleanup(track.stop)
        limit = patch.object(guard, 'verify_child_boundary'); limit.start(); self.addCleanup(limit.stop)
        self.location = guard.paths(self.project)
        self.build_release()

    def mock_value(self, obj, name, value):
        mock = patch.object(obj, name, value); mock.start(); self.addCleanup(mock.stop)

    def build_release(self):
        for name in guard.SOURCE_FILES:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('synthetic '+name+'\n')
        parent = self.project/guard.ancestry.PARENT; put(parent/'COMPLETE.json', {'status': 'complete'})
        parent_sha = guard.sha(parent/'COMPLETE.json')
        for obj in (engine, guard.frozen.engine): self.mock_value(obj, 'PARENT_COMPLETE_SHA256', parent_sha)
        self.mock_value(guard.ancestry, 'PARENT_SHA', parent_sha)
        prepared = self.location['prepared']
        put(prepared/'manifest.json', dict(kind='repair_feedback_fold_label_materialization_v1', train_prefixes=320,
            original_valid32_materialized=False, fitting_performed=False, parent_complete_sha256=parent_sha,
            fold_assignment_sha256='b'*64, source_sha256={name: 'a'*64 for name in guard.labels.SOURCE_PATHS}))
        put(prepared/'folds.json', {'synthetic': True})
        for fold in range(5): put(prepared/f'fold-{fold}/train-labels.json', {'synthetic_label': fold})
        put(prepared/'assessment/all320-labels.json', {'synthetic_assessment': True})
        names = ['manifest.json', 'folds.json', *(f'fold-{fold}/train-labels.json' for fold in range(5)), 'assessment/all320-labels.json']
        put(prepared/'COMPLETE.json', dict(status='complete', parent_complete_sha256=parent_sha,
            fold_assignment_sha256='b'*64, files_sha256={name: guard.sha(prepared/name) for name in names}))
        self.mock_value(guard, 'PREPARED_COMPLETE_SHA256', guard.sha(prepared/'COMPLETE.json'))
        support = self.project/guard.observed.SUPPORT
        put(support/'manifest.json', dict(source=self.state, source_root=str(self.root),
            source_sha256={name: guard.sha(self.root/name) for name in guard.support.SOURCE_FILES}, input_sha256={},
            runtime=guard.support.RUNTIME, parent_complete_sha256=parent_sha, source_coverage={},
            configuration=guard.directed.configuration(), fitting_performed=False))
        put(support/'folds.json', {'synthetic': True})
        put(support/'STATUS.json', dict(phase='complete', completed_examples=320, total_examples=320))
        put(support/'report.json', dict(kind='observed_only_directed_history_support_v1', arms=list(engine.ARMS),
            feature_dimension=144, variation_prerequisite=True, excluded_prefixes=0, configuration=guard.directed.configuration(),
            totals=dict(guard.observed.COUNTS), prerequisites={str(f): {name: True for name in guard.observed.PREREQUISITES} for f in range(5)},
            **{key: False for key in ('fitting_performed', 'outcomes_opened', 'successors_opened', 'models_opened', 'predictions_opened', 'fit_release_authorized')}))
        put(support/'COMPLETE.json', dict(status='complete', fitting_performed=False,
            files_sha256={name: guard.sha(support/name) for name in guard.observed.FILES}))
        self.mock_value(engine, 'SUPPORT_COMPLETE_SHA256', guard.sha(support/'COMPLETE.json'))
        contracts, _, _ = guard._metadata_preparation(self.location)
        release = dict(kind='repair_directed_fixed25_fit_release_v2', project=str(self.project), family=guard.FAMILY,
            fit_release_authorized=True, confirmatory=False, fresh_test_opened=False, runtime=guard.RUNTIME,
            input_complete_sha256={guard.observed.SUPPORT+'/COMPLETE.json': engine.SUPPORT_COMPLETE_SHA256,
                guard.ancestry.PARENT+'/COMPLETE.json': parent_sha, guard.PREPARED+'/COMPLETE.json': guard.PREPARED_COMPLETE_SHA256},
            prepared_metadata_sha256={guard.PREPARED+'/'+name: guard.sha(prepared/name) for name in ('manifest.json', 'folds.json')},
            prepared_label_contracts=guard._serialized_contracts(contracts), protocol_sha256=guard.sha(self.root/guard.PROTOCOL),
            amendment_sha256=guard.sha(self.root/guard.AMENDMENT),
            configuration=guard.release_configuration(), source_sha256={name: guard.sha(self.root/name) for name in guard.SOURCE_FILES},
            decision_reason='synthetic approval only')
        self.set_release(release)

    def set_release(self, value):
        put(self.root/guard.RELEASE, value)
        (self.root/guard.SIDECAR).write_text(guard.sha(self.root/guard.RELEASE)+'\n')

    def context(self): return guard.preflight(self.project)

    def fake_inputs(self):
        return SimpleNamespace(examples=[object()]*320, observations=(), assignment={'synthetic': True},
                               fold_assignment_sha256='b'*64)

    def before_fold(self, context, target=4):
        wrapper(self.location, 'preflight', context)
        for name in ('manifest.json', 'cohort.json', 'folds.json'): put(self.location['run']/name, {})
        put(self.location['run']/'FOLDS_COMPLETE.json', dict(files_sha256={name: guard.sha(self.location['run']/name)
            for name in ('manifest.json', 'cohort.json', 'folds.json')}))
        wrapper(self.location, 'initialize', context)
        for fold in range(target):
            fold_outputs(self.location, fold); wrapper(self.location, f'fold-{fold}', context)

    def test_preflight_reads_only_pinned_metadata_preserves_preparation_and_no_outputs(self):
        actual = Path.open; opened = []
        def checked(path, *args, **kwargs):
            opened.append(path)
            if path.name in ('train-labels.json', 'all320-labels.json', 'labels.jsonl'):
                raise AssertionError('no label/cache body access')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', checked): result = guard.preflight(self.project)
        self.assertEqual(set(result['label_contracts']), {'0', '1', '2', '3', '4', 'assessment'})
        self.assertEqual(len(result['source_sha256']), len(guard.SOURCE_FILES))
        self.assertTrue(self.location['prepared'].exists())
        self.assertFalse(self.location['run'].exists()); self.assertFalse(self.location['supervisor'].exists())
        self.assertNotIn(guard.RELEASE, guard.SOURCE_FILES); self.assertNotIn(guard.SIDECAR, guard.SOURCE_FILES)
        self.assertTrue(all('train-labels.json' not in path.name for path in opened))

    def test_unreleased_prepare_stage_and_cli_overrides_fail_closed(self):
        (self.root/guard.SIDECAR).unlink()
        with self.assertRaisesRegex(RuntimeError, 'unreleased'): guard.execute_stage(self.project, 'preflight')
        with self.assertRaisesRegex(ValueError, 'preparation'): guard.execute_stage(self.project, 'prepare')
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            guard.main(['--project', str(self.project), '--stage', 'prepare'])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            guard.main(['--project', str(self.project), '--stage', 'preflight', '--retry'])
        self.assertFalse(self.location['supervisor'].exists())

    def test_v2_namespace_amendment_and_old_primitive_dependencies_are_explicit(self):
        self.assertEqual(self.location['run'], self.project/guard.FAMILY/'run-v2')
        self.assertEqual(self.location['supervisor'], self.project/guard.FAMILY/'supervised-v2')
        self.assertEqual(self.location['verified'], self.project/guard.FAMILY/'supervised-v2/verified')
        self.assertEqual(guard.RELEASE, 'analysis_protocols/zpd-repair-directed-newton-release-20260924.json')
        self.assertTrue({guard.AMENDMENT, 'scripts/zpd_repair_residual_newton.py',
            'tests/test_zpd_repair_residual_newton.py', 'scripts/zpd_repair_residual_core.py',
            'scripts/zpd_repair_feedback_offset.py'}.issubset(guard.SOURCE_FILES))
        for stage in guard.STAGES:
            self.assertTrue(all(name.startswith(('run-v2/', 'supervised-v2/'))
                                for name in guard._artifact_paths(stage)))
        release = guard.read(self.root/guard.RELEASE)
        self.assertEqual(release['amendment_sha256'], guard.sha(self.root/guard.AMENDMENT))
        self.assertEqual(release['protocol_sha256'], guard.sha(self.root/guard.PROTOCOL))

    def test_v1_release_is_never_used_as_implicit_v2_permission(self):
        old = self.root/'analysis_protocols/zpd-repair-directed-fit-release-20260924.json'
        put(old, dict(guard.read(self.root/guard.RELEASE), kind='repair_directed_fixed25_fit_release_v1'))
        old_sidecar = Path(str(old)+'.sha256'); old_sidecar.write_text(guard.sha(old)+'\n')
        before = old.read_bytes(), old_sidecar.read_bytes()
        (self.root/guard.RELEASE).unlink(); (self.root/guard.SIDECAR).unlink()
        with self.assertRaisesRegex(RuntimeError, 'unreleased'):
            guard.preflight(self.project)
        self.assertEqual(before, (old.read_bytes(), old_sidecar.read_bytes()))
        self.assertFalse(self.location['run'].exists()); self.assertFalse(self.location['supervisor'].exists())

    def test_strict_release_contracts_source_inventory_types_and_sidecar(self):
        original = guard.read(self.root/guard.RELEASE)
        mutations = [lambda v: v.update(fit_release_authorized=False), lambda v: v.update(extra=True),
            lambda v: v.update(kind='repair_directed_fixed25_fit_release_v1'),
            lambda v: v.update(amendment_sha256='0'*64), lambda v: v.pop('amendment_sha256'),
            lambda v: v['configuration'].update(dimension=1296), lambda v: v['configuration'].update(new_label_files=False),
            lambda v: v['source_sha256'].pop(next(iter(v['source_sha256']))),
            lambda v: v['prepared_label_contracts']['0'].update(expected_sha256='a'*64),
            lambda v: v['prepared_metadata_sha256'].pop(next(iter(v['prepared_metadata_sha256']))),
            lambda v: v['input_complete_sha256'].update({guard.PREPARED+'/COMPLETE.json': 'd'*64})]
        for mutate in mutations:
            value = copy.deepcopy(original); mutate(value); self.set_release(value)
            with self.assertRaisesRegex(ValueError, 'schema'): guard.preflight(self.project)
        self.set_release(original)
        (self.root/guard.SIDECAR).write_text(guard.sha(self.root/guard.RELEASE).upper()+'\n')
        with self.assertRaisesRegex(ValueError, 'sidecar'): guard.preflight(self.project)
        self.assertFalse(self.location['run'].exists())

    def test_source_runtime_preparation_pin_and_metadata_drift_are_fail_closed(self):
        context = self.context()
        with patch.object(guard, 'runtime', return_value=dict(guard.RUNTIME, numpy='wrong')):
            with self.assertRaisesRegex(ValueError, 'runtime'): guard.recheck(context)
            with self.assertRaisesRegex(ValueError, 'runtime'): guard.preflight(self.project)
        with patch.object(guard, 'source_state', side_effect=ValueError('dirty checkout')):
            with self.assertRaisesRegex(ValueError, 'dirty'): guard.preflight(self.project)
        with patch.object(guard.subprocess, 'check_output', return_value=''):
            with self.assertRaisesRegex(ValueError, 'tracked'): guard.preflight(self.project)
        file = self.location['prepared']/'COMPLETE.json'; old = file.read_text()
        put(file, dict(guard.read(file), changed=True))
        with self.assertRaisesRegex(ValueError, 'pin'): guard.preflight(self.project)
        file.write_text(old)
        put(self.location['prepared']/'manifest.json', {'changed': True})
        with self.assertRaisesRegex(ValueError, 'changed'): guard.recheck(context)

    def test_direct_stage_requires_fixed_child_limits_before_any_output(self):
        env = {name: '1' for name in guard.BLAS_ENVIRONMENT}; limit = guard.CHILD_MEMORY_BYTES
        with patch.dict(guard.frozen.os.environ, env), patch.object(guard.frozen.resource, 'getrlimit', return_value=(limit, limit)):
            REAL_BOUNDARY()
            with patch.dict(guard.frozen.os.environ, {guard.BLAS_ENVIRONMENT[0]: '2'}), self.assertRaises(ValueError): REAL_BOUNDARY()
        with patch.object(guard, 'verify_child_boundary', side_effect=ValueError('limits missing')):
            with self.assertRaisesRegex(ValueError, 'limits missing'): guard.execute_stage(self.project, 'preflight')
        self.assertFalse(self.location['supervisor'].exists())

    def test_fold4_worker_never_reads_sibling_labels_or_prior_model_bodies(self):
        context = self.context(); self.before_fold(context)
        actual = Path.open; labels_opened = []
        def checked(path, *args, **kwargs):
            if path.name in ('train-labels.json', 'all320-labels.json'):
                self.assertEqual(path, self.location['prepared']/'fold-4/train-labels.json'); labels_opened.append(path)
            if path.name in {arm+'.json' for arm in engine.ARMS}: raise AssertionError('prior model body in fold worker')
            return actual(path, *args, **kwargs)
        def fit(inputs, fold, directory, contract, run):
            self.assertEqual(fold, 4); self.assertEqual(directory, self.location['prepared'])
            with (directory/'fold-4/train-labels.json').open() as stream: json.load(stream)
            # Producer writes only synthetic new fold markers; no model bodies
            # are needed for this boundary test.
            path = run/'fold-4'; put(path/'MODELS_COMPLETE.json', {})
            put(path/'COMPLETE.json', {'status': 'complete'})
            return [None]*64
        with patch.object(guard, '_load_inputs', return_value=(self.fake_inputs(), dict(source_sha256={}, input_sha256={}))), \
                patch.object(engine, 'fit_fold', side_effect=fit), patch.object(Path, 'open', checked):
            report = guard.execute_stage(self.project, 'fold-4')
        self.assertEqual(len(labels_opened), 1)
        self.assertEqual(report['result']['predicted_examples'], 64)

    def test_finalize_has_no_label_body_io_and_assessment_barrier_precedes_open(self):
        context = self.context(); self.before_fold(context, target=5)
        actual = Path.open
        def checked(path, *args, **kwargs):
            if path.name in ('train-labels.json', 'all320-labels.json'): raise AssertionError('premature label body')
            return actual(path, *args, **kwargs)
        def finalize(inputs, run):
            put(run/'predictions.json', []); put(run/'PREDICTIONS_COMPLETE.json', {})
            return [None]*320
        with patch.object(guard, '_load_inputs', return_value=(self.fake_inputs(), dict(source_sha256={}, input_sha256={}))), \
                patch.object(engine, 'finalize_predictions', side_effect=finalize), patch.object(Path, 'open', checked):
            report = guard.execute_stage(self.project, 'finalize')
        self.assertFalse(report['result']['label_bodies_opened'])
        with patch.object(guard, '_previous'), patch.object(guard, '_load_inputs', return_value=(self.fake_inputs(), dict(source_sha256={}, input_sha256={}))), \
                patch.object(engine, 'assess_predictions', side_effect=ValueError('prediction barrier missing')), patch.object(Path, 'open', checked):
            with self.assertRaisesRegex(ValueError, 'prediction barrier'): guard.execute_stage(self.project, 'assess')
        self.assertTrue((self.location['supervisor']/'stages/assess/FAILED.json').exists())

    def test_preflight_loaded_input_drift_cannot_leave_complete(self):
        observed = self.project/'synthetic-observation.json'; put(observed, {'before': True})
        provenance = dict(source_sha256={}, input_sha256={str(observed): guard.sha(observed)})
        def fingerprint(inputs): put(observed, {'changed': True}); return 'a'*64
        with patch.object(guard, '_load_inputs', return_value=(self.fake_inputs(), provenance)), \
                patch.object(engine, 'input_fingerprint', side_effect=fingerprint):
            with self.assertRaisesRegex(ValueError, 'binding changed'): guard.execute_stage(self.project, 'preflight')
        stage = self.location['supervisor']/'stages/preflight'
        self.assertTrue((stage/'FAILED.json').exists()); self.assertFalse((stage/'COMPLETE.json').exists())

    def test_wrapper_cannot_hide_actual_engine_drift_or_substitute_inner_audit(self):
        context = self.context(); self.before_fold(context, target=1)
        path = self.location['run']/'fold-0/MODELS_COMPLETE.json'; put(path, {'changed': True})
        with self.assertRaisesRegex(ValueError, 'actual stage artifact'): guard.verify_wrapper(self.project, 'fold-0')
        put(self.location['verified']/'report.json', {'verified': True})
        put(self.location['verified']/'COMPLETE.json', {'status': 'complete', 'files_sha256': {'report.json': guard.sha(self.location['verified']/'report.json')}})
        with self.assertRaises((FileNotFoundError, ValueError)): guard.verify_wrapper(self.project, 'audit', deep=True)
        directory = wrapper(self.location, 'audit', context); put(directory/'FAILED.json', {'failed': True})
        with self.assertRaisesRegex(ValueError, 'valid completed'): guard.verify_wrapper(self.project, 'audit', deep=True)

    def test_resealed_v1_wrapper_kind_cannot_enter_v2(self):
        context = self.context(); directory = wrapper(self.location, 'preflight', context)
        guard.verify_wrapper(self.project, 'preflight')
        report = guard.read(directory/'report.json')
        report['kind'] = 'repair_directed_production_stage_v1'
        put(directory/'report.json', report)
        put(directory/'COMPLETE.json', dict(status='complete', files_sha256={
            'report.json': guard.sha(directory/'report.json')}))
        with self.assertRaisesRegex(ValueError, 'strict stage wrapper'):
            guard.verify_wrapper(self.project, 'preflight')

    def test_inner_audit_seal_waits_for_final_runtime_barrier(self):
        context = self.context(); result = dict(verified=True, experiment_complete_sha256='a'*64)
        with patch.object(guard, 'preflight', return_value=context), patch.object(guard, '_previous'), \
                patch.object(guard, '_load_inputs', return_value=(self.fake_inputs(), dict(source_sha256={}, input_sha256={}))), \
                patch.object(guard, '_independent_audit', return_value=result), \
                patch.object(guard, 'recheck', side_effect=ValueError('late runtime drift')):
            with self.assertRaisesRegex(ValueError, 'late runtime drift'): guard.execute_stage(self.project, 'audit')
        self.assertFalse((self.location['verified']/'COMPLETE.json').exists())
        self.assertTrue((self.location['supervisor']/'stages/audit/FAILED.json').exists())

    def _audit_with_label_mutation(self, when):
        context = self.context(); run = self.location['run']
        put(run/'assessment/report.json', {'synthetic_assessment': True}); put(run/'predictions.json', [])
        put(run/'COMPLETE.json', dict(status='complete', files_sha256={name: guard.sha(run/name)
            for name in ('assessment/report.json', 'predictions.json')}))
        result = dict(verified=True, experiment_complete_sha256=guard.sha(run/'COMPLETE.json'))
        label = self.location['prepared']/'fold-3/train-labels.json'
        def audited(*args):
            if when == 'after_return': put(label, {'changed_after_audit': True})
            return result
        actual_seal = engine._seal
        def seal(directory, names, **kwargs):
            value = actual_seal(directory, names, **kwargs)
            if directory == self.location['verified'] and when == 'after_inner':
                put(label, {'changed_after_inner_seal': True})
            return value
        with patch.object(guard, 'preflight', return_value=context), patch.object(guard, '_previous'), \
                patch.object(guard, '_load_inputs', return_value=(self.fake_inputs(), dict(source_sha256={}, input_sha256={}))), \
                patch.object(guard, '_independent_audit', side_effect=audited), patch.object(engine, '_seal', side_effect=seal):
            with self.assertRaisesRegex(ValueError, 'audit consumed label drift'):
                guard.execute_stage(self.project, 'audit')
        self.assertTrue((self.location['supervisor']/'stages/audit/FAILED.json').exists())
        self.assertFalse((self.location['supervisor']/'stages/audit/COMPLETE.json').exists())

    def test_label_drift_after_audit_return_blocks_inner_and_wrapper_seals(self):
        self._audit_with_label_mutation('after_return')
        self.assertFalse((self.location['verified']/'COMPLETE.json').exists())

    def test_label_drift_after_inner_seal_blocks_wrapper_seal(self):
        self._audit_with_label_mutation('after_inner')
        self.assertTrue((self.location['verified']/'COMPLETE.json').exists())


if __name__ == '__main__': unittest.main()
