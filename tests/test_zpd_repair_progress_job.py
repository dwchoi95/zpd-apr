"""Synthetic external own-job authorization tests; no empirical reads/fits."""
from contextlib import contextmanager
import copy
from dataclasses import asdict,replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from scripts import run_zpd_repair_progress_job as job
from tests.test_zpd_repair_progress_capsule import fixture


def encoded(value):return job.launcher.core.encoded(value)+b'\n'


@contextmanager
def environment(inputs):
    with tempfile.TemporaryDirectory() as temp:
        project=Path(temp).resolve();root=project/'.runtime'/'snapshot';root.mkdir(parents=True)
        fold=inputs.fold;path=project/job.FAMILY/'jobs'/f'fold-{fold}.json';path.parent.mkdir(parents=True)
        output=project/job.FAMILY/'run-v1'/f'fold-{fold}'
        label=project/job.LABELS/f'fold-{fold}'/'train-labels.json';label.parent.mkdir(parents=True)
        label_bytes=b'{"synthetic_only":"not an empirical label file"}\n';label.write_bytes(label_bytes)
        native={'synthetic':'no native or proc access'};state=dict(revision='a'*40,tree='b'*40)
        sources={'scripts/run_zpd_repair_progress_job.py':'c'*64,'analysis_protocols/synthetic.md':'d'*64}
        contract=job.worker.LabelContract(job.digest(label_bytes),inputs.fold_assignment_sha256,'e'*64)
        payload=dict(kind=job.JOB_KIND,fold=fold,inputs=job.capsule.encode_inputs(inputs),own_label_contract=asdict(contract),
            source_state=state,source_root=str(root),source_sha256=sources,runtime=dict(job.preparation.RUNTIME),controller_native=native,
            authority=dict(release_sha256='1'*64,initialization_sha256='2'*64,
                readiness_complete_sha256=job.READINESS_COMPLETE_SHA256,parent_complete_sha256=job.PARENT_COMPLETE_SHA256))
        def seal(body):raw=encoded(body);path.write_bytes(raw);return job.digest(raw)
        pin=seal(payload)
        with patch.object(job,'PROJECT',project),patch.object(job,'ROOT',root),\
             patch.object(job,'source_state',return_value=state),patch.object(job,'check_sources') as sources_mock,\
             patch.object(job,'runtime',return_value=dict(job.preparation.RUNTIME)),\
             patch.object(job,'verify_child_boundary'),\
             patch.object(job,'controller_native',return_value=native):
            yield dict(project=project,root=root,fold=fold,path=path,output=output,label=label,
                payload=payload,pin=pin,seal=seal,sources_mock=sources_mock)


def fake_worker(inputs,label_directory,contract,output,*,recheck):
    """Boundary-only stand-in; real numerical worker has its own independent tests."""
    recheck()
    label=label_directory/f'fold-{inputs.fold}'/'train-labels.json'
    if job.digest(label.read_bytes())!=contract.expected_sha256:raise ValueError('synthetic own label drift')
    output.mkdir(parents=True,exist_ok=False)
    held=job.capsule.scope(inputs)[1];predictions=[dict(example_id=ex.example_id,synthetic=True) for ex in held]
    pins={}
    for name in job.worker.FILES:
        pins[name]=job.worker.write(output/name,predictions if name=='predictions.json' else dict(synthetic=name))
    recheck()
    job.worker.write(output/'COMPLETE.json',dict(status='complete',kind='statement_progress32_fold_complete_v1',
        fold=inputs.fold,completed_fits=6,predicted_examples=len(held),input_fingerprint=job.capsule.fingerprint(inputs),
        files_sha256=pins,automatic_retries=0))
    return predictions


class ProgressJobTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=replace(fixture(320,synthetic=False),readiness_complete_sha256=job.READINESS_COMPLETE_SHA256)

    def test_readonly_exact_memory_and_all_six_environment_values(self):
        limit=job.CHILD_MEMORY_BYTES;environment=dict(job.launcher.ENVIRONMENT)
        self.assertEqual(limit,32*1024**3);self.assertEqual(len(environment),6)
        with patch.object(job.resource,'getrlimit',return_value=(limit,limit)) as read,\
             patch.object(job.resource,'setrlimit',side_effect=AssertionError('verification must never set limits')),\
             patch.object(job.os,'environ',environment):
            job.verify_child_boundary();read.assert_called_once_with(job.resource.RLIMIT_AS)
            for limits in ((-1,-1),(limit-1,limit),(limit,limit-1),(True,limit),(limit,True),
                           (float(limit),limit),(limit,),[limit,limit]):
                with self.subTest(limits=limits),patch.object(job.resource,'getrlimit',return_value=limits),\
                     self.assertRaisesRegex(ValueError,'RLIMIT_AS'):job.verify_child_boundary()
            for key in environment:
                wrong=dict(environment);wrong[key]='unexpected'
                with self.subTest(key=key),patch.object(job.os,'environ',wrong),\
                     self.assertRaisesRegex(ValueError,'environment'):job.verify_child_boundary()
            missing=dict(environment);missing.pop('JE_ARROW_MALLOC_CONF')
            with patch.object(job.os,'environ',missing),self.assertRaises(ValueError):job.verify_child_boundary()

    def test_resource_boundary_refuses_before_job_body_or_labels(self):
        with environment(self.inputs) as env,patch.object(job,'verify_child_boundary',side_effect=ValueError('wrong child bound')),\
             patch.object(job,'_own_job',side_effect=AssertionError('must stop before job body')) as body,\
             patch.object(job.worker,'fit_fold') as worker:
            with self.assertRaisesRegex(ValueError,'child bound'):job.execute(env['project'],env['fold'],env['pin'])
            body.assert_not_called();worker.assert_not_called();self.assertFalse(env['output'].exists())

    def test_success_reads_only_own_job_code_scope_own_label_and_own_outputs(self):
        with environment(self.inputs) as env:
            opened=[];actual=Path.open
            allowed={env['path'],env['label'],*(env['output']/n for n in (*job.worker.FILES,'COMPLETE.json'))}
            def guarded(path,mode='r',*args,**kwargs):
                if 'r' in mode or '+' in mode:
                    opened.append(path);self.assertIn(path,allowed,'global or sibling input forbidden even for hashing')
                return actual(path,mode,*args,**kwargs)
            with patch.object(Path,'open',guarded),patch.object(job.worker,'fit_fold',side_effect=fake_worker) as worker:
                result=job.execute(env['project'],env['fold'],env['pin'])
            self.assertEqual(worker.call_count,1);self.assertEqual(result['completed_fits'],6)
            self.assertEqual(result['predicted_examples'],len(job.capsule.scope(self.inputs)[1]))
            self.assertEqual(result['capsule_sha256'],env['pin'])
            self.assertEqual(result['complete_sha256'],job.sha(env['output']/'COMPLETE.json'))
            self.assertGreater(opened.count(env['path']),2);self.assertIn(env['label'],opened)
            self.assertFalse((env['output']/'FAILED.json').exists())

    def test_external_pin_is_checked_before_capsule_decoding_or_any_label(self):
        with environment(self.inputs) as env,patch.object(job.worker,'fit_fold') as worker,\
             patch.object(job.capsule,'decode_inputs',side_effect=AssertionError('must not decode unauthenticated body')):
            with self.assertRaisesRegex(ValueError,'expected own job SHA'):job.execute(env['project'],env['fold'],'0'*64)
            worker.assert_not_called();self.assertFalse(env['output'].exists())

    def test_strict_schema_fixed_pins_fold_and_own_label_contract_before_worker(self):
        modes=('extra','kind','fold_bool','fold_wrong','root','state','readiness','parent','contract_extra',
               'contract_fold','runtime','native','inputs_fold','synthetic')
        for mode in modes:
            with self.subTest(mode=mode),environment(self.inputs) as env,patch.object(job.worker,'fit_fold') as worker:
                body=env['payload']
                if mode=='extra':body['prepared_label_contracts']={}
                elif mode=='kind':body['kind']='another_job'
                elif mode=='fold_bool':body['fold']=False
                elif mode=='fold_wrong':body['fold']=1
                elif mode=='root':body['source_root']=str(env['project'])
                elif mode=='state':body['source_state']=dict(revision='e'*40,tree='b'*40)
                elif mode=='readiness':body['authority']['readiness_complete_sha256']='0'*64
                elif mode=='parent':body['authority']['parent_complete_sha256']='0'*64
                elif mode=='contract_extra':body['own_label_contract']['assessment_sha256']='0'*64
                elif mode=='contract_fold':body['own_label_contract']['expected_fold_assignment_sha256']='0'*64
                elif mode=='runtime':body['runtime']['python']='untrusted'
                elif mode=='native':body['controller_native']={'changed':True}
                elif mode=='inputs_fold':body['inputs']['fold']=1
                else:body['inputs']['synthetic']=True
                pin=env['seal'](body)
                with self.assertRaises(ValueError):job.execute(env['project'],env['fold'],pin)
                worker.assert_not_called();self.assertFalse(env['output'].exists())

    def test_source_path_allowlist_blocks_release_prepared_models_and_siblings(self):
        paths=('analysis_protocols/new-release.json','analysis_protocols/new-release.json.sha256',
            'outputs/prepared/COMPLETE.json','outputs/jobs/fold-1.json','scripts/../outputs/model.py',
            '/absolute.py','scripts//alias.py','data/source.py','src/cache.json','tests/sidecar.sha256')
        for path in paths:
            with self.subTest(path=path),self.assertRaises(ValueError):job.validate_source_map({path:'a'*64})
        for name in ('scripts/example.py','src/pkg/module.py','tests/test_example.py','analysis_protocols/frozen.md'):
            job.validate_source_map({name:'a'*64})
        with environment(self.inputs) as env,patch.object(job.worker,'fit_fold') as worker:
            env['payload']['source_sha256']={paths[0]:'a'*64};pin=env['seal'](env['payload'])
            with self.assertRaises(ValueError):job.execute(env['project'],env['fold'],pin)
            worker.assert_not_called();self.assertFalse(env['output'].exists())

    def test_source_tracking_hash_canonical_and_import_origin_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();relative='scripts/synthetic_job_code.py';path=root/relative;path.parent.mkdir()
            path.write_bytes(b'# synthetic code\n');mapping={relative:job.sha(path)}
            with patch.object(job,'ROOT',root),patch.object(job.subprocess,'check_output',return_value=(relative+'\0').encode()):
                job.check_sources(mapping)
                with patch.object(job.subprocess,'check_output',return_value=b''),self.assertRaises(ValueError):job.check_sources(mapping)
                with patch.dict(sys.modules,{'scripts.synthetic_job_code':SimpleNamespace(__file__=str(root/'foreign.py'))}),\
                     self.assertRaises(ValueError):job.check_sources(mapping)
                path.write_bytes(b'# changed\n')
                with self.assertRaises(ValueError):job.check_sources(mapping)
                path.unlink();target=root/'else.py';target.write_bytes(b'not canonical');path.symlink_to(target)
                with self.assertRaises(ValueError):job.check_sources({relative:job.digest(target.read_bytes())})

    def test_fixed_paths_output_preservation_and_aliases(self):
        for mode in ('existing','alias_project','alias_job','wrong_project','invalid_fold'):
            with self.subTest(mode=mode),environment(self.inputs) as env,patch.object(job.worker,'fit_fold') as worker:
                project=env['project'];fold=env['fold']
                if mode=='existing':env['output'].mkdir(parents=True);(env['output']/'user-file').write_bytes(b'keep')
                elif mode=='alias_project':
                    alias=project/'alias';alias.symlink_to(project,target_is_directory=True);project=alias
                elif mode=='alias_job':
                    moved=env['path'].with_suffix('.saved');env['path'].rename(moved);env['path'].symlink_to(moved)
                elif mode=='wrong_project':project=project.parent
                else:fold=True
                with self.assertRaises(ValueError):job.execute(project,fold,env['pin'])
                worker.assert_not_called()
                if mode=='existing':self.assertEqual((env['output']/'user-file').read_bytes(),b'keep')

    def test_recheck_after_parse_and_after_completion_catches_all_identity_drift(self):
        modes=('job','git','source','runtime','native','input','metadata','label')
        for mode in modes:
            with self.subTest(mode=mode),environment(self.inputs) as env:
                done=[]
                def changed_worker(inputs,label_directory,contract,output,*,recheck):
                    result=fake_worker(inputs,label_directory,contract,output,recheck=recheck);done.append(True)
                    if mode=='job':env['path'].write_bytes(b'changed own job')
                    elif mode=='input':inputs.examples[0].observation.prior[0].__dict__['verdict']='CE'
                    elif mode=='label':env['label'].write_bytes(b'changed own label')
                    return result
                state=lambda:dict(revision='e'*40,tree='b'*40) if done and mode=='git' else env['payload']['source_state']
                runtime=lambda:{'changed':True} if done and mode=='runtime' else job.preparation.RUNTIME
                native=lambda:{'changed':True} if done and mode=='native' else env['payload']['controller_native']
                def sources(mapping):
                    if done and mode=='source':raise ValueError('source drift')
                    if done and mode=='metadata':mapping['scripts/forged.py']='f'*64
                with patch.object(job.worker,'fit_fold',side_effect=changed_worker),\
                     patch.object(job,'source_state',side_effect=state),patch.object(job,'runtime',side_effect=runtime),\
                     patch.object(job,'controller_native',side_effect=native),patch.object(job,'check_sources',side_effect=sources):
                    with self.assertRaises(ValueError):job.execute(env['project'],env['fold'],env['pin'])
                self.assertFalse((env['output']/'COMPLETE.json').exists())
                self.assertTrue((env['output']/'REJECTED_COMPLETE.json').exists());self.assertTrue((env['output']/'FAILED.json').exists())

    def test_late_output_hash_consumer_and_terminal_marker_failures_are_rejected(self):
        for mode in ('late_job','late_model','marker_write'):
            with self.subTest(mode=mode),environment(self.inputs) as env:
                original_sha=job.sha;triggered=[]
                def sha(path):
                    result=original_sha(path)
                    if Path(path)==env['output']/'STATUS.json' and not triggered:
                        triggered.append(True)
                        if mode=='late_job':env['path'].write_bytes(b'late job drift')
                        elif mode=='late_model':(env['output']/'H.json').write_bytes(b'late output drift')
                    return result
                def run(*args,**kwargs):
                    result=fake_worker(*args,**kwargs)
                    if mode=='marker_write':raise OSError('after marker bytes, synthetic fsync failure')
                    return result
                with patch.object(job,'sha',side_effect=sha),patch.object(job.worker,'fit_fold',side_effect=run),\
                     self.assertRaises((ValueError,OSError)):job.execute(env['project'],env['fold'],env['pin'])
                self.assertFalse((env['output']/'COMPLETE.json').exists())
                self.assertTrue((env['output']/'REJECTED_COMPLETE.json').exists());self.assertTrue((env['output']/'FAILED.json').exists())

    def test_duplicate_JSON_key_rejected_even_with_external_matching_hash(self):
        with environment(self.inputs) as env,patch.object(job.worker,'fit_fold') as worker:
            raw=encoded(env['payload']);raw=b'{"fold":0,'+raw[1:];env['path'].write_bytes(raw)
            with self.assertRaises(ValueError):job.execute(env['project'],env['fold'],job.digest(raw))
            worker.assert_not_called();self.assertFalse(env['output'].exists())


if __name__=='__main__':unittest.main()
