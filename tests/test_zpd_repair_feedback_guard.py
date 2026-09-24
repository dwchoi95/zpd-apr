"""Synthetic release/one-stage guards. Never open empirical files or fit."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

from scripts import guard_zpd_repair_feedback as guard
from scripts import run_zpd_repair_feedback_cv as engine

REAL_CHILD_BOUNDARY = guard.verify_child_boundary


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True)+'\n')


def metadata_fixture(project):
    location = guard.paths(project); root = location['prepared']; root.mkdir(parents=True)
    source = {name: 'a'*64 for name in guard.labels.SOURCE_PATHS}
    manifest = dict(kind='repair_feedback_fold_label_materialization_v1', train_prefixes=320,
        original_valid32_materialized=False, fitting_performed=False,
        parent_complete_sha256=engine.PARENT_COMPLETE_SHA256, fold_assignment_sha256='b'*64,
        source_sha256=source)
    put(root/'manifest.json', manifest); put(root/'folds.json', {'synthetic': True})
    files = {'manifest.json': guard.sha(root/'manifest.json'), 'folds.json': guard.sha(root/'folds.json')}
    for f in range(5):
        path = root/f'fold-{f}/train-labels.json'; put(path, {'unread_synthetic_label': f})
        files[f'fold-{f}/train-labels.json'] = guard.sha(path)
    path = root/'assessment/all320-labels.json'; put(path, {'unread_synthetic_assessment': True})
    files['assessment/all320-labels.json'] = guard.sha(path)
    put(root/'COMPLETE.json', dict(status='complete', files_sha256=files,
        parent_complete_sha256=engine.PARENT_COMPLETE_SHA256, fold_assignment_sha256='b'*64))
    return location


def wrapper(location, stage, context):
    directory = location['supervisor']/'stages'/stage; directory.mkdir(parents=True)
    report = dict(kind='repair_feedback_production_stage_v1', stage=stage, status='complete',
        source=context['source'], release_sha256=context['release_sha256'], runtime=guard.RUNTIME,
        result={}, engine_artifact_sha256={guard.FAMILY+'/'+name: guard.sha(location['family']/name) for name in guard._artifact_paths(stage)},
        retries=0, model_promotion=False)
    put(directory/'report.json', report)
    put(directory/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(directory/'report.json')}))
    return directory


class FeedbackGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.project = Path(temp.name).resolve(); self.root = self.project/'.runtime/source'; self.root.mkdir(parents=True)
        for name, value in [('PROJECT', self.project), ('ROOT', self.root)]:
            context = patch.object(guard, name, value); context.start(); self.addCleanup(context.stop)
        self.state = dict(revision='a'*40, tree='b'*40)
        for target, value in [('source_state', self.state), ('runtime', guard.RUNTIME)]:
            context = patch.object(guard, target, return_value=value); context.start(); self.addCleanup(context.stop)
        tracker = patch.object(guard.subprocess, 'check_output', side_effect=lambda args, **kwargs: '\n'.join(args[args.index('--')+1:])+'\n')
        tracker.start(); self.addCleanup(tracker.stop)
        boundary = patch.object(guard, 'verify_child_boundary')
        boundary.start(); self.addCleanup(boundary.stop)
        self.build_release()

    def build_release(self):
        for name in guard.SOURCE_FILES:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('synthetic source '+name+'\n')
        support = self.project/guard.observed.SUPPORT
        source_hashes = {name: guard.sha(self.root/name) for name in guard.support.SOURCE_FILES}
        put(support/'manifest.json', dict(source_sha256=source_hashes))
        put(support/'folds.json', {'synthetic': True}); put(support/'STATUS.json', {'phase': 'complete'})
        report = dict(variation_prerequisite=True, totals={'prefixes': 320}, excluded_prefixes=0,
            **{key: False for key in ('fitting_performed', 'outcomes_opened', 'successors_opened', 'models_opened', 'predictions_opened', 'fit_release_authorized')})
        put(support/'report.json', report)
        put(support/'COMPLETE.json', dict(status='complete', files_sha256={name: guard.sha(support/name)
            for name in ('manifest.json', 'folds.json', 'report.json', 'STATUS.json')}))
        parent = self.project/guard.support.PARENT; put(parent/'COMPLETE.json', {'status': 'complete'})
        for name, value in [('SUPPORT_COMPLETE_SHA256', guard.sha(support/'COMPLETE.json')),
                            ('PARENT_COMPLETE_SHA256', guard.sha(parent/'COMPLETE.json'))]:
            context = patch.object(engine, name, value); context.start(); self.addCleanup(context.stop)
        release = dict(kind='repair_feedback_fixed25_fit_release_v1', project=str(self.project), family=guard.FAMILY,
            fit_release_authorized=True, confirmatory=False, fresh_test_opened=False, runtime=guard.RUNTIME,
            input_complete_sha256={guard.observed.SUPPORT+'/COMPLETE.json': engine.SUPPORT_COMPLETE_SHA256,
                guard.support.PARENT+'/COMPLETE.json': engine.PARENT_COMPLETE_SHA256},
            protocol_sha256=guard.sha(self.root/guard.PROTOCOL), configuration=guard.release_configuration(),
            source_sha256={name: guard.sha(self.root/name) for name in guard.SOURCE_FILES}, decision_reason='synthetic test approval only')
        self.set_release(release)

    def set_release(self, value):
        put(self.root/guard.RELEASE, value)
        (self.root/guard.SIDECAR).write_text(guard.sha(self.root/guard.RELEASE)+'\n')

    def context(self):
        return dict(source=self.state, release_sha256=guard.sha(self.root/guard.RELEASE),
            source_sha256={}, input_sha256={}, runtime=guard.RUNTIME, project=str(self.project))

    def test_strict_release_has_full_closure_and_no_output_or_label_access(self):
        actual = Path.open; opened = []
        def checked(path, *args, **kwargs):
            opened.append(path)
            self.assertNotEqual(path.name, 'labels.jsonl')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', checked): result = guard.preflight(self.project)
        self.assertEqual(result['source'], self.state)
        self.assertEqual(len(result['source_sha256']), len(guard.SOURCE_FILES))
        self.assertTrue(all(not (self.project/guard.FAMILY/name).exists() for name in ('prepared-v1', 'run-v1', 'supervised-v1')))
        self.assertIn(self.root/guard.SIDECAR, opened)
        self.assertNotIn(guard.RELEASE, guard.SOURCE_FILES); self.assertNotIn(guard.SIDECAR, guard.SOURCE_FILES)

    def test_direct_child_requires_frozen_memory_and_all_thread_settings(self):
        limits = (guard.CHILD_MEMORY_BYTES, guard.CHILD_MEMORY_BYTES)
        environment = {name: '1' for name in guard.BLAS_ENVIRONMENT}
        with patch.dict(guard.os.environ, environment), patch.object(guard.resource, 'getrlimit', return_value=limits):
            REAL_CHILD_BOUNDARY()
            for name in guard.BLAS_ENVIRONMENT:
                with patch.dict(guard.os.environ, {name: '2'}), self.assertRaisesRegex(ValueError, 'BLAS'):
                    REAL_CHILD_BOUNDARY()
        with patch.dict(guard.os.environ, environment), patch.object(guard.resource, 'getrlimit', return_value=(limits[0], -1)), \
                self.assertRaisesRegex(ValueError, '32GiB'):
            REAL_CHILD_BOUNDARY()
        with patch.object(guard, 'preflight', return_value=self.context()), \
                patch.object(guard, 'verify_child_boundary', side_effect=ValueError('limits missing')), \
                patch.object(guard, '_load_inputs', side_effect=AssertionError('must fail before loading')):
            with self.assertRaisesRegex(ValueError, 'limits missing'):
                guard.execute_stage(self.project, 'preflight')
        self.assertFalse(guard.paths(self.project)['supervisor'].exists())
        from scripts import supervise_zpd_repair_feedback as supervisor
        config = guard.release_configuration()
        self.assertEqual(config['child_memory_bytes'], supervisor.MEMORY_BYTES)
        self.assertEqual(config['stage_timeout_seconds'], supervisor.TIMEOUTS)
        self.assertEqual(config['heartbeat_seconds'], supervisor.HEARTBEAT_SECONDS)

    def test_release_schema_nested_types_source_inventory_and_runtime_fail_closed(self):
        original = guard.read(self.root/guard.RELEASE)
        for kind in ('unreleased', 'extra', 'source_missing', 'source_extra', 'nested_bool', 'runtime', 'wrong_project', 'wrong_pin'):
            value = copy.deepcopy(original)
            if kind == 'unreleased': value['fit_release_authorized'] = False
            elif kind == 'extra': value['override'] = True
            elif kind == 'source_missing': value['source_sha256'].pop(next(iter(value['source_sha256'])))
            elif kind == 'source_extra': value['source_sha256']['unknown.py'] = 'a'*64
            elif kind == 'nested_bool': value['configuration']['full_train_refits'] = False
            elif kind == 'runtime': value['runtime']['scipy'] = '0'
            elif kind == 'wrong_project': value['project'] = '/different'
            else: value['input_complete_sha256'][guard.support.PARENT+'/COMPLETE.json'] = 'c'*64
            self.set_release(value)
            with self.subTest(kind=kind), self.assertRaises(ValueError): guard.preflight(self.project)
        self.assertTrue(all(not (self.project/guard.FAMILY/name).exists() for name in ('prepared-v1', 'run-v1', 'supervised-v1')))

    def test_sidecar_format_dirty_or_untracked_source_and_missing_release_rejected(self):
        digest = guard.sha(self.root/guard.RELEASE)
        for text in (digest, digest.upper()+'\n', digest+'  file\n', digest+'\n\n'):
            (self.root/guard.SIDECAR).write_text(text)
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, 'sidecar'): guard.preflight(self.project)
        (self.root/guard.SIDECAR).write_text(digest+'\n')
        with patch.object(guard.subprocess, 'check_output', return_value=''), self.assertRaisesRegex(ValueError, 'tracked'):
            guard.preflight(self.project)
        with patch.object(guard, 'source_state', side_effect=ValueError('dirty snapshot')), self.assertRaisesRegex(ValueError, 'dirty'):
            guard.preflight(self.project)
        (self.root/guard.SIDECAR).unlink()
        with self.assertRaisesRegex(RuntimeError, 'unreleased'): guard.preflight(self.project)

    def test_runtime_source_and_support_pin_drift_are_rejected(self):
        with patch.object(guard, 'runtime', return_value=dict(guard.RUNTIME, python='wrong')), self.assertRaisesRegex(ValueError, 'runtime'):
            guard.preflight(self.project)
        path = self.root/guard.SOURCE_FILES[0]; path.write_text('changed')
        with self.assertRaisesRegex(ValueError, 'source closure'): guard.preflight(self.project)
        # recheck independently binds the source paths consumed at preflight.
        context = self.context(); context['source_sha256'][str(path)] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'changed'): guard.recheck(context)

    def test_preparation_metadata_and_previous_wrapper_never_open_sibling_labels(self):
        location = metadata_fixture(self.project); context = self.context(); wrapper(location, 'prepare', context)
        actual = Path.open; opened = []
        def checked(path, *args, **kwargs):
            opened.append(path)
            if path.name in ('train-labels.json', 'all320-labels.json'): raise AssertionError('sibling label bytes forbidden')
            return actual(path, *args, **kwargs)
        with patch.object(Path, 'open', checked):
            contracts, _, _ = guard._metadata_preparation(location)
            guard.verify_wrapper(self.project, 'prepare', deep=True)
        self.assertEqual(set(contracts), {*range(5), None})
        self.assertTrue(all(c.expected_fold_assignment_sha256 == 'b'*64 for c in contracts.values()))
        self.assertTrue(opened)

    def test_wrapper_only_success_cannot_hide_actual_metadata_drift(self):
        location = metadata_fixture(self.project); directory = wrapper(location, 'prepare', self.context())
        guard.verify_wrapper(self.project, 'prepare')
        put(location['prepared']/'manifest.json', {'forged': True})
        with self.assertRaisesRegex(ValueError, 'actual stage artifact'): guard.verify_wrapper(self.project, 'prepare')
        report = guard.read(directory/'report.json'); report['engine_artifact_sha256'] = {}
        put(directory/'report.json', report)
        put(directory/'COMPLETE.json', dict(status='complete', files_sha256={'report.json': guard.sha(directory/'report.json')}))
        with self.assertRaisesRegex(ValueError, 'actual engine artifacts'): guard.verify_wrapper(self.project, 'prepare')

    def test_raw_preparation_reader_is_exact17_allowlist_only(self):
        for relative in guard.labels.SOURCE_PATHS:
            path = self.project/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic exact bytes')
        allowed = {self.project/name for name in guard.labels.SOURCE_PATHS}; opened = []
        real_read = Path.read_bytes
        def tracked(path):
            opened.append(path); self.assertIn(path, allowed); return real_read(path)
        def prepare(blobs, output):
            self.assertEqual(set(blobs), guard.labels.SOURCE_PATHS); metadata_fixture(self.project)
        with patch.object(guard, 'preflight', return_value=self.context()), patch.object(guard, '_previous'), \
                patch.object(guard, 'recheck'), patch.object(Path, 'read_bytes', tracked), \
                patch.object(engine, 'prepare_labels', prepare):
            result = guard.execute_stage(self.project, 'prepare')
        self.assertEqual(set(opened), allowed); self.assertEqual(len(opened), 17)
        self.assertFalse(result['result']['original_valid32_materialized'])

    def test_finalize_guard_does_not_open_any_label_body(self):
        location = metadata_fixture(self.project); fake = SimpleNamespace(assignment={'synthetic': True}, fold_assignment_sha256='b'*64)
        def finalize(inputs, run):
            put(run/'predictions.json', [])
            put(run/'PREDICTIONS_COMPLETE.json', {'synthetic': True})
            return [None]*320
        actual = Path.open
        def checked(path, *args, **kwargs):
            if path.name in ('labels.jsonl', 'train-labels.json', 'all320-labels.json'): raise AssertionError('no label reads allowed')
            return actual(path, *args, **kwargs)
        with patch.object(guard, 'preflight', return_value=self.context()), patch.object(guard, '_previous'), \
                patch.object(guard, 'recheck'), patch.object(guard, '_load_inputs', return_value=(fake, dict(source_sha256={}, input_sha256={}))), \
                patch.object(engine, 'finalize_predictions', finalize), patch.object(Path, 'open', checked):
            report = guard.execute_stage(self.project, 'finalize')
        self.assertTrue(report['result']['label_bodies_opened'] is False)

    def test_observation_drift_after_preflight_load_prevents_wrapper_seal(self):
        location = guard.paths(self.project); path = self.project/'observed.json'; put(path, {'before': True})
        provenance = dict(source_sha256={}, input_sha256={str(path): guard.sha(path)})
        fake = SimpleNamespace(examples=[None]*320)
        def drift(inputs):
            path.write_text('changed observation\n'); return 'a'*64
        with patch.object(guard, 'preflight', return_value=self.context()), patch.object(guard, '_previous'), \
                patch.object(guard, 'recheck'), patch.object(guard, '_load_inputs', return_value=(fake, provenance)), \
                patch.object(engine, 'input_fingerprint', side_effect=drift):
            with self.assertRaisesRegex(ValueError, 'binding changed'): guard.execute_stage(self.project, 'preflight')
        self.assertTrue((location['supervisor']/'stages/preflight/FAILED.json').exists())
        self.assertFalse((location['supervisor']/'stages/preflight/COMPLETE.json').exists())

    def test_assessor_and_auditor_never_preopen_labels_before_engine_barrier(self):
        location = metadata_fixture(self.project); fake = SimpleNamespace(assignment={'synthetic': True}, fold_assignment_sha256='b'*64)
        with patch.object(guard, 'preflight', return_value=self.context()), patch.object(guard, '_previous'), \
                patch.object(guard, 'recheck'), patch.object(guard, '_load_inputs', return_value=(fake, dict(source_sha256={}, input_sha256={}))), \
                patch.object(engine, 'assess_predictions', side_effect=ValueError('prediction barrier missing')), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('no pre-barrier labels')):
            with self.assertRaisesRegex(ValueError, 'barrier missing'): guard.execute_stage(self.project, 'assess')
        self.assertTrue((location['supervisor']/'stages/assess/FAILED.json').exists())
        with patch.object(guard, 'verify_marker', side_effect=ValueError('prediction seal missing')), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('no pre-barrier labels')):
            with self.assertRaisesRegex(ValueError, 'seal missing'):
                guard._independent_audit(fake, location, {}, {})

    def test_independent_audit_rejects_a_resealed_consumed_complete(self):
        from scripts import audit_zpd_repair_feedback_cv as auditor
        location = guard.paths(self.project); run = location['run']; prepared = location['prepared']
        empty = b'{}'; digest = hashlib.sha256(empty).hexdigest()
        contracts = {f: engine.LabelContract(digest, 'b'*64, 'c'*64) for f in [*range(5), None]}
        for fold in range(5):
            for arm in engine.ARMS: put(run/f'fold-{fold}'/(arm+'.json'), {'synthetic': True})
            path = prepared/f'fold-{fold}/train-labels.json'; path.parent.mkdir(parents=True); path.write_bytes(empty)
        path = prepared/'assessment/all320-labels.json'; path.parent.mkdir(); path.write_bytes(empty)
        put(run/'manifest.json', dict(input_fingerprint='a'*64,
            label_contracts={str(f) if f is not None else 'assessment': vars(c) for f, c in contracts.items()}))
        put(run/'assessment/report.json', {}); put(run/'COMPLETE.json', {'original': True})
        fake = SimpleNamespace(examples=(), banks={}, assignment={})
        reader = Mock()
        def audit(*args, **kwargs):
            put(run/'COMPLETE.json', {'resealed_after_consumption': True})
            return dict(verified=True)
        with patch.object(guard, 'verify_marker'), patch.object(engine, 'input_fingerprint', return_value='a'*64), \
                patch.object(engine, '_prediction_barrier', return_value=[]), patch.object(engine, '_scope', return_value=((), ())), \
                patch.object(engine, '_bindings'), patch.object(guard.support, 'load_inputs', return_value=([], {}, {}, {}, reader)), \
                patch.object(guard.labels, 'load_fold_labels', return_value={}), \
                patch.object(guard.labels, 'validate_assessment_envelope', return_value={}), patch.object(auditor, 'audit_run', audit):
            with self.assertRaisesRegex(ValueError, 'COMPLETE changed during independent audit'):
                guard._independent_audit(fake, location, contracts, {})

    def test_inner_audit_seal_waits_for_final_source_runtime_barrier(self):
        location = metadata_fixture(self.project)
        fake = SimpleNamespace(assignment={'synthetic': True}, fold_assignment_sha256='b'*64)
        with patch.object(guard, 'preflight', return_value=self.context()), patch.object(guard, '_previous'), \
                patch.object(guard, '_load_inputs', return_value=(fake, {})), patch.object(engine, '_bindings'), \
                patch.object(guard, '_independent_audit', return_value={'verified': True, 'experiment_complete_sha256': 'a'*64}), \
                patch.object(guard, 'recheck', side_effect=ValueError('late runtime drift')):
            with self.assertRaisesRegex(ValueError, 'late runtime drift'): guard.execute_stage(self.project, 'audit')
        self.assertTrue((location['verified']/'report.json').exists())
        self.assertFalse((location['verified']/'COMPLETE.json').exists())
        self.assertFalse((location['supervisor']/'stages/audit/COMPLETE.json').exists())
        self.assertTrue((location['supervisor']/'stages/audit/FAILED.json').exists())

    def test_invalid_project_alias_stage_and_cli_overrides_rejected(self):
        with self.assertRaisesRegex(ValueError, 'fixed canonical'): guard.paths(self.project/'other')
        alias = self.project/'alias'; alias.symlink_to(self.project, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'nonsymlink'): guard.paths(alias)
        with self.assertRaisesRegex(ValueError, 'one-stage'): guard.execute_stage(self.project, 'rescue')
        with self.assertRaises(SystemExit): guard.main(['--project', str(self.project), '--stage', 'preflight', '--retry'])


if __name__ == '__main__': unittest.main()
