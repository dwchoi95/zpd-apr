"""Synthetic release/job/barrier tests; child fitting and assessment are doubled.

All artifacts are created under TemporaryDirectory. No real experiment artifact,
release, runtime snapshot, process resource limit or numerical fit is consumed.
"""
from contextlib import ExitStack, redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import supervise_zpd_bank_topset as coordinator

job = coordinator.job
worker = coordinator.worker
authority = coordinator.authority


class SyntheticRelease(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name).resolve()
        self.snapshot = self.project/'.runtime'/'synthetic-snapshot'; self.snapshot.mkdir(parents=True)
        self.root = self.project/job.FAMILY; self.run = self.root/'run-v1'
        self.state = dict(revision='a'*40, tree='b'*40)
        self.native = dict(synthetic_only='no native inspection')
        self.examples = [SimpleNamespace(example_id=f'e{i}', bank_id=f'b{i}',
            user_id=f'u{i}', problem_id=f'p{i % 23}') for i in range(320)]
        self.inputs = {f:SimpleNamespace(fold=f, synthetic=False, examples=self.examples,
            banks={e.bank_id:dict(synthetic=True) for e in self.examples},
            readiness_complete_sha256=authority.READINESS_COMPLETE_SHA256) for f in range(5)}
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for module, name, value in ((job,'PROJECT',self.project),(authority,'ROOT',self.snapshot)):
            self.stack.enter_context(patch.object(module,name,value))
        self.stack.enter_context(patch.object(authority,'source_state',return_value=self.state))
        self.stack.enter_context(patch.object(authority,'runtime',return_value=dict(authority.preparation.RUNTIME)))
        self.stack.enter_context(patch.object(authority,'controller_native',return_value=self.native))
        self.stack.enter_context(patch.object(authority,'check_sources'))
        self.boundary = self.stack.enter_context(patch.object(authority,'verify_child_boundary'))
        self.decode = self.stack.enter_context(patch.object(worker.capsule,'decode_inputs',
            side_effect=lambda value:self.inputs[value['synthetic_fold']]))
        self.stack.enter_context(patch.object(worker.capsule,'scope',side_effect=self.scope))
        self.stack.enter_context(patch.object(worker.capsule,'validate_inputs',return_value=[]))
        self.stack.enter_context(patch.object(worker.previous,'decode_transform',side_effect=lambda value:value))
        self.stack.enter_context(patch.object(worker.previous,'validate_transform',return_value='1'*64))
        self.stack.enter_context(patch.object(worker,'contract_values',side_effect=lambda contract,inputs:vars(contract)))
        self.fit = self.stack.enter_context(patch.object(worker.solver,'fit',side_effect=AssertionError('no fit permitted')))
        self.child = self.stack.enter_context(patch.object(coordinator.bounded,'run_child',side_effect=self.child_stub))
        self.assessment_reads = []
        self.provider = self.stack.enter_context(patch.object(coordinator.provider,'validate_assessment_envelope',
            side_effect=self.assessment_stub))
        self.assess = self.stack.enter_context(patch.object(worker.assessment,'assess',
            return_value=dict(gate=dict(passed=False),synthetic_control_flow_only=True)))
        self.label_path = self.project/job.LABELS/'assessment/all320-labels.json'
        assessment_pin = self.put(self.label_path,dict(synthetic_assessment_only=True))
        contracts = {str(f):dict(expected_sha256=self.put(self.project/job.LABELS/f'fold-{f}/train-labels.json',
                dict(synthetic_own_label_only=True,fold=f)),
            expected_fold_assignment_sha256='a'*64,expected_source_binding_sha256='b'*64) for f in range(5)}
        contracts['assessment'] = dict(expected_sha256=assessment_pin,
            expected_fold_assignment_sha256='a'*64,expected_source_binding_sha256='b'*64)
        self.contracts = contracts
        old = self.project/coordinator.OLD; old_job_pins = {}; old_files = {}
        for fold in range(5):
            old_job_pins[str(fold)] = self.put(old/'jobs'/f'fold-{fold}.json',
                dict(inputs=dict(synthetic_fold=fold),own_label_contract=contracts[str(fold)]))
            name = f'fold-{fold}/SCALER.json'
            old_files[name] = self.put(old/'run-v1'/name,dict(synthetic_scaler=fold))
        old_files['manifest.json'] = self.put(old/'run-v1/manifest.json',dict(label_contracts=contracts))
        old_run_pin = self.put(old/'run-v1/COMPLETE.json',dict(status='complete',recipients=320,
            completed_fits=35,job_sha256=old_job_pins,files_sha256=old_files))
        old_outer_pin = self.put(old/'supervised-v1/COMPLETE.json',
            dict(status='complete',experiment_complete_sha256=old_run_pin))
        prepared_pin = self.put(self.project/job.LABELS/'COMPLETE.json',dict(files_sha256={
            **{f'fold-{f}/train-labels.json':contracts[str(f)]['expected_sha256'] for f in range(5)},
            'assessment/all320-labels.json':assessment_pin}))
        for name,value in (('OLD_OUTER',old_outer_pin),('OLD_RUN',old_run_pin),('PREPARED',prepared_pin)):
            self.stack.enter_context(patch.object(coordinator,name,value))
        names = set(job.SOURCE_FILES)
        self.release = dict(kind='bank_topset4131_release_v1',source_root=str(self.snapshot),
            source_state=self.state,source_sha256={name:'c'*64 for name in names},
            runtime=dict(authority.preparation.RUNTIME),controller_native=self.native,
            protocol_sha256='c'*64,independent_preflight_passed=True,empirical_fits_authorized=True)
        self.release_path = self.root/'release.json'
        self.release_pin = self.put(self.release_path,self.release)

    def put(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        return worker.write(path,value)

    def reseal_release(self, value):
        # Synthetic input mutation only, never a run output or real release.
        self.release_path.unlink()
        self.release_pin = self.put(self.release_path,value)

    def scope(self,inputs):
        held = self.examples[inputs.fold*64:(inputs.fold+1)*64]
        selected = {e.example_id for e in held}
        return [e for e in self.examples if e.example_id not in selected],held

    def child_stub(self,command,*,name,cwd,stage_output,output,timeout_seconds,required_files):
        self.assertEqual(cwd,self.snapshot); self.assertEqual(timeout_seconds,3600)
        worker.write(output/(name+'.log'),dict(synthetic_control_flow_only=True))
        if name=='audit':
            self.assertEqual(tuple(required_files),('report.json',))
            self.assertEqual(command[1:4],['-B','-m','scripts.audit_zpd_bank_topset_run'])
            self.assertEqual(command[-1],authority.sha(self.run/'COMPLETE.json'))
            stage_output.mkdir()
            report_pin=worker.write(stage_output/'report.json',dict(verified=True,models=35,
                recipients=320,experiment_complete_sha256=command[-1],synthetic_control_flow_only=True))
            pin=worker.write(stage_output/'COMPLETE.json',dict(status='complete',files_sha256={'report.json':report_pin}))
            return dict(name=name,complete_sha256=pin,returncode=0,synthetic_control_flow_only=True)
        self.assertEqual(tuple(required_files),worker.FILES)
        self.assertEqual(command[1:4],['-B','-m','scripts.run_zpd_bank_topset_job'])
        fold = int(name[-1]); self.assertEqual(command[-1],authority.sha(self.root/'jobs'/f'fold-{fold}.json'))
        rows = [dict(example_id=e.example_id,user_id=e.user_id,bank_id=e.bank_id,
            problem_id=e.problem_id,fold=fold,bank_seal_sha256='d'*64,
            choices={method:'synthetic_candidate' for method in worker.METHODS}) for e in self.scope(self.inputs[fold])[1]]
        stage_output.mkdir()
        pins = {name:worker.write(stage_output/name,rows if name=='predictions.json' else dict(synthetic_only=name))
            for name in worker.FILES}
        pin = worker.write(stage_output/'COMPLETE.json',dict(status='complete',kind=worker.COMPLETE_KIND,
            completed_fits=7,fold=fold,predicted_examples=64,files_sha256=pins))
        return dict(name=f'fold-{fold}',complete_sha256=pin,returncode=0,synthetic_control_flow_only=True)

    def assessment_stub(self,*args,**kwargs):
        self.assertEqual(self.child.call_count,5)
        seal = json.loads((self.run/'PREDICTIONS_COMPLETE.json').read_bytes())
        self.assertEqual(seal['completed_fits'],35)
        self.assertEqual(authority.sha(self.run/'predictions.json'),seal['files_sha256']['predictions.json'])
        self.assessment_reads.append('after_five_sealed_children')
        return {}

    def run_supervisor(self):
        with redirect_stdout(io.StringIO()):return coordinator.supervise(self.project,self.release_pin)

    def test_five_children_new_authority_scaler_ancestry_and_assessment_barrier(self):
        actual_open=Path.open;observed=[]
        def opened(path,mode='r',*args,**kwargs):
            if path==self.label_path and 'r' in mode:
                observed.append(path)
                self.assertGreaterEqual(self.child.call_count,5)
                self.assertTrue((self.run/'PREDICTIONS_COMPLETE.json').exists())
            return actual_open(path,mode,*args,**kwargs)
        with patch.object(Path,'open',opened):self.assertEqual(self.run_supervisor(),dict(passed=False))
        self.assertTrue(observed)
        self.assertEqual(self.child.call_count,6); self.fit.assert_not_called()
        self.assertEqual(self.assessment_reads,['after_five_sealed_children'])
        self.assertEqual(len(worker.METHODS),14)
        for fold in range(5):
            own = json.loads((self.root/'jobs'/f'fold-{fold}.json').read_bytes())
            self.assertEqual(own['release_sha256'],self.release_pin)
            self.assertEqual(own['transform'],dict(synthetic_scaler=fold))
            self.assertEqual(own['own_label_contract'],self.contracts[str(fold)])
            self.assertEqual(own['inputs'],dict(synthetic_fold=fold))
        seal = json.loads((self.run/'COMPLETE.json').read_bytes())
        self.assertFalse(seal['scientific_gate_passed']); self.assertEqual(seal['automatic_retries'],0)
        for fold in range(5):self.assertIn(f'STATUS-fold-{fold}.json',seal['files_sha256'])
        coordinator.verify_marker(self.run,required_files=('report.json','PREDICTIONS_COMPLETE.json'))
        with self.assertRaisesRegex(ValueError,'no duplicate or resume'):self.run_supervisor()
        self.assertEqual(self.child.call_count,6)

    def test_release_flags_kind_and_protocol_are_required_before_old_artifacts(self):
        variants = []
        for key,value in (('kind','joint_progress4131_release_v1'),('independent_preflight_passed',False),
                          ('empirical_fits_authorized',False),('protocol_sha256','0'*64)):
            body=copy.deepcopy(self.release);body[key]=value;variants.append(body)
        body=copy.deepcopy(self.release);body['protocol_sha256']=None;body['source_sha256'].pop(coordinator.PROTOCOL)
        variants.append(body)
        body=copy.deepcopy(self.release);body['source_sha256'].pop('scripts/run_zpd_bank_topset_cv.py');variants.append(body)
        actual_read=coordinator.read_pinned
        def release_only(path,pin):
            self.assertEqual(path,self.release_path,'invalid release must stop before old artifact bodies')
            return actual_read(path,pin)
        for body in variants:
            with self.subTest(body=body):
                self.reseal_release(body)
                with patch.object(coordinator,'read_pinned',side_effect=release_only),self.assertRaises(ValueError):self.run_supervisor()
                self.assertFalse(self.run.exists());self.child.assert_not_called()

    def test_wrong_external_release_pin_rejected_before_decode_or_children(self):
        self.release_pin='0'*64
        with self.assertRaisesRegex(ValueError,'pinned artifact'):self.run_supervisor()
        self.decode.assert_not_called();self.child.assert_not_called();self.assertFalse(self.run.exists())

    def test_loaded_local_module_requires_explicit_source_binding(self):
        name='_synthetic_topset_import_inventory_review'
        mapped=SimpleNamespace(__file__=str(self.snapshot/'scripts/run_zpd_bank_topset_job.py'))
        with patch.dict(job.sys.modules,{name:mapped}):job.check_sources(self.release['source_sha256'])
        missing=SimpleNamespace(__file__=str(self.snapshot/'src/unlisted_synthetic_module.py'))
        with patch.dict(job.sys.modules,{name:missing}),self.assertRaisesRegex(ValueError,'loaded local module'):
            job.check_sources(self.release['source_sha256'])

    def test_orphan_audit_output_blocks_before_any_new_fit(self):
        (self.root/'verified-v1').mkdir()
        with self.assertRaisesRegex(ValueError,'fresh|duplicate'):self.run_supervisor()
        self.child.assert_not_called();self.decode.assert_not_called();self.assertFalse(self.run.exists())

    def test_prediction_mutation_is_caught_before_assessment(self):
        actual=worker.write
        def tamper(path,value):
            pin=actual(path,value)
            if path.name=='PREDICTIONS_COMPLETE.json':
                with (self.run/'predictions.json').open('ab') as stream:stream.write(b' ')
            return pin
        with patch.object(worker,'write',side_effect=tamper),self.assertRaisesRegex(ValueError,'sealed predictions changed'):
            self.run_supervisor()
        self.provider.assert_not_called();self.assess.assert_not_called()
        self.assertTrue((self.run/'FAILED.json').exists());self.assertFalse((self.run/'COMPLETE.json').exists())

    def test_child_failure_stops_no_retry_no_assessment(self):
        actual=self.child_stub
        def fail(command,**kwargs):
            if kwargs['name']=='fold-2':raise RuntimeError('synthetic child failed')
            return actual(command,**kwargs)
        self.child.side_effect=fail
        with self.assertRaisesRegex(RuntimeError,'synthetic child failed'):self.run_supervisor()
        self.assertEqual(self.child.call_count,3);self.provider.assert_not_called()
        self.assertTrue((self.run/'FAILED.json').exists());self.assertFalse((self.run/'COMPLETE.json').exists())
        with self.assertRaisesRegex(ValueError,'no duplicate or resume'):self.run_supervisor()
        self.assertEqual(self.child.call_count,3)

    def test_audit_failure_retires_producer_completion_and_cannot_complete_outer(self):
        actual=self.child_stub
        def fail(command,**kwargs):
            if kwargs['name']=='audit':raise RuntimeError('synthetic audit failed')
            return actual(command,**kwargs)
        self.child.side_effect=fail
        with self.assertRaisesRegex(RuntimeError,'synthetic audit failed'):self.run_supervisor()
        self.assertEqual(self.child.call_count,6);self.assertEqual(self.provider.call_count,1)
        self.assertTrue((self.run/'FAILED.json').exists());self.assertTrue((self.run/'REJECTED_COMPLETE.json').exists())
        self.assertFalse((self.run/'COMPLETE.json').exists());self.assertFalse((self.root/'supervised-v1/COMPLETE.json').exists())

    def test_outer_completion_write_failure_retires_both_complete_markers(self):
        actual=worker.write;outer=self.root/'supervised-v1/COMPLETE.json'
        def fail_after_write(path,value):
            pin=actual(path,value)
            if path==outer:raise OSError('synthetic terminal fsync failure')
            return pin
        with patch.object(worker,'write',side_effect=fail_after_write),self.assertRaisesRegex(OSError,'terminal fsync'):
            self.run_supervisor()
        self.assertTrue((self.run/'FAILED.json').exists());self.assertFalse((self.run/'COMPLETE.json').exists())
        self.assertFalse(outer.exists());self.assertTrue((outer.parent/'REJECTED_COMPLETE.json').exists())

    def test_post_outer_write_output_mutation_is_rejected(self):
        actual=worker.write;outer=self.root/'supervised-v1/COMPLETE.json'
        def mutate_after_write(path,value):
            pin=actual(path,value)
            if path==outer:
                with (outer.parent/'stages.json').open('ab') as stream:stream.write(b' ')
            return pin
        with patch.object(worker,'write',side_effect=mutate_after_write),self.assertRaisesRegex(ValueError,'terminal supervisor outputs changed'):
            self.run_supervisor()
        self.assertFalse(outer.exists());self.assertFalse((self.run/'COMPLETE.json').exists())
        self.assertTrue((self.run/'FAILED.json').exists())

    def own_job(self):
        payload=dict(kind=job.KIND,fold=0,inputs=dict(synthetic_fold=0),transform=dict(synthetic_scaler=0),
            own_label_contract=self.contracts['0'],source_state=self.state,source_sha256=self.release['source_sha256'],
            runtime=self.release['runtime'],controller_native=self.native,release_sha256=self.release_pin,
            original_job_sha256='1'*64,original_transform_sha256='2'*64)
        path=self.root/'jobs/fold-0.json';pin=self.put(path,payload)
        return path,pin

    def test_job_external_hash_and_resource_boundary_precede_input_decode(self):
        path,pin=self.own_job()
        with self.assertRaisesRegex(ValueError,'own job SHA differs'):job.execute(self.project,0,'0'*64)
        self.decode.assert_not_called()
        self.boundary.side_effect=ValueError('synthetic wrong resource boundary')
        with patch.object(Path,'read_bytes',side_effect=AssertionError('no input body permitted')):
            with self.assertRaisesRegex(ValueError,'resource boundary'):job.execute(self.project,0,pin)
        self.decode.assert_not_called();self.fit.assert_not_called()

    def test_job_reads_only_own_capsule_own_label_and_own_outputs(self):
        path,pin=self.own_job();output=self.run/'fold-0'
        label=self.project/job.LABELS/'fold-0/train-labels.json'
        original_open=Path.open;opened=[]
        def guarded(target,mode='r',*args,**kwargs):
            if 'r' in mode or '+' in mode:
                self.assertTrue(target in (path,label) or target.parent==output,'global/sibling body or hashing forbidden')
                opened.append(target)
            return original_open(target,mode,*args,**kwargs)
        def fake_fit(inputs,label_directory,contract,transform,destination,*,recheck):
            self.assertEqual(inputs.fold,0);self.assertEqual(destination,output)
            self.assertEqual(label_directory,self.project/job.LABELS)
            self.assertEqual(json.loads(label.read_bytes()),dict(synthetic_own_label_only=True,fold=0))
            recheck();destination.mkdir(parents=True)
            worker.write(destination/'COMPLETE.json',dict(synthetic_control_flow_only=True))
            return []
        with patch.object(Path,'open',guarded),patch.object(worker,'fit_fold',side_effect=fake_fit),redirect_stdout(io.StringIO()):
            job.execute(self.project,0,pin)
        self.assertIn(path,opened);self.assertIn(label,opened)
        self.fit.assert_not_called();self.child.assert_not_called()

    def test_job_postfit_authority_drift_retires_own_completion(self):
        path,pin=self.own_job();output=self.run/'fold-0'
        def fake_fit(inputs,label_directory,contract,transform,destination,*,recheck):
            self.assertEqual(label_directory,self.project/job.LABELS);self.assertEqual(inputs.fold,0)
            recheck();destination.mkdir(parents=True)
            worker.write(destination/'COMPLETE.json',dict(synthetic_control_flow_only=True))
            return []
        def current_state():return dict(revision='f'*40,tree='b'*40) if (output/'COMPLETE.json').exists() else self.state
        with patch.object(worker,'fit_fold',side_effect=fake_fit),patch.object(authority,'source_state',side_effect=current_state):
            with self.assertRaisesRegex(ValueError,'source/runtime/native drift'):job.execute(self.project,0,pin)
        self.assertFalse((output/'COMPLETE.json').exists());self.assertTrue((output/'REJECTED_COMPLETE.json').exists())
        self.fit.assert_not_called();self.child.assert_not_called()


if __name__=='__main__':unittest.main()
