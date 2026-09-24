"""Fixed10 mocked children; all test artifacts are synthetic placeholders."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import guard_zpd_joint_progress as guard
from scripts import supervise_zpd_joint_progress as supervisor
from tests.test_zpd_joint_progress_guard import put,synthetic_fold


class JointProgressSupervisorTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.project=Path(temp.name).resolve()
        p=patch.object(guard,'PROJECT',self.project);p.start();self.addCleanup(p.stop)
        self.location=guard.paths(self.project);self.output=self.location['supervisor'];self.calls=[]
        oldrun=self.project/guard.OLD_RUN
        body=put(oldrun/'predictions.json',[{'synthetic_old':i} for i in range(320)])
        seal=put(oldrun/'PREDICTIONS_COMPLETE.json',dict(status='all30_models_and_full_oof_predictions_complete',predictions_sha256=body))
        complete=put(oldrun/'COMPLETE.json',dict(status='complete',completed_fits=30,recipients=320,model_promotion=False,
            files_sha256={'predictions.json':body,'PREDICTIONS_COMPLETE.json':seal}))
        for name,value in [('OLD_COMPLETE_SHA256',complete)]:
            p=patch.object(guard,name,value);p.start();self.addCleanup(p.stop)
        p=patch.object(guard.architecture,'REFERENCE_PINS',dict(prediction_seal_sha256=seal,predictions_sha256=body))
        p.start();self.addCleanup(p.stop)
        self.context=dict(source={'revision':'a'*40,'tree':'b'*40},release_sha256='c'*64,
            source_sha256={},input_sha256={},runtime=guard.RUNTIME,controller_native={'synthetic':True},
            project=str(self.project),label_contracts={})
        for f in [*range(5),None]:
            name='assessment/all320-labels.json' if f is None else f'fold-{f}/train-labels.json'
            pin=put(self.location['prepared']/name,{'synthetic_label':f})
            self.context['label_contracts']['assessment' if f is None else str(f)]=dict(expected_sha256=pin,
                expected_fold_assignment_sha256='b'*64,expected_source_binding_sha256='c'*64)
        self.gate=dict(passed=False,actual_repair_improvement=False,mechanism_contribution=False,current_feedback_contribution=False,joint_current_contribution=False)

    def child(self,command,*,name,cwd,stage_output,output,timeout_seconds,required_files):
        self.calls.append(name);self.assertEqual(timeout_seconds,supervisor.TIMEOUTS[name])
        self.assertFalse(stage_output.exists());result={}
        if name.startswith('fold-'):
            self.assertEqual(command[:4],[supervisor.sys.executable,'-B','-m','scripts.run_zpd_joint_progress_job'])
            self.assertEqual(command[4:8],['--project',str(self.project),'--fold',name[-1]])
            self.assertEqual(command[8],'--expected-capsule-sha');self.assertEqual(len(command),10)
            self.assertEqual(tuple(required_files),guard.worker.FILES)
            self.assertEqual(command[9],guard.sha(self.location['jobs']/f'{name}.json'))
            self.assertEqual(stage_output,self.location['run']/name)
            synthetic_fold(self.location,int(name[-1]))
        else:
            self.assertEqual(command[:4],[supervisor.sys.executable,'-B','-m','scripts.guard_zpd_joint_progress'])
            self.assertEqual(command[4:8],['--project',str(self.project),'--stage',name])
            pins=guard.frozen_observed.decode_json(command[9].encode())
            self.assertEqual(set(pins),set(guard.STAGES[:guard.STAGES.index(name)]))
            self.assertEqual(required_files,('report.json',))
            if name=='initialize':
                for n in guard.stages.INITIAL_FILES:put(self.location['run']/n,{'synthetic':n})
                put(self.location['run']/'manifest.json',{'input_fingerprints':{str(f):'d'*64 for f in range(5)}})
                init=put(self.location['run']/'INITIALIZATION_COMPLETE.json',dict(kind='synthetic_init',
                    files_sha256={n:guard.sha(self.location['run']/n) for n in guard.stages.INITIAL_FILES}))
                jobs={str(f):put(self.location['jobs']/f'fold-{f}.json',{'synthetic_job':f}) for f in range(5)}
                index=put(self.location['run']/'JOBS_COMPLETE.json',dict(initialization_sha256=init,job_sha256=jobs))
                result=dict(initialization_sha256=init,jobs_complete_sha256=index,job_sha256=jobs,
                    fingerprints={str(f):'d'*64 for f in range(5)})
            elif name=='finalize':
                put(self.location['run']/'predictions.json',[])
                pin=put(self.location['run']/'PREDICTIONS_COMPLETE.json',{'synthetic_predictions':True})
                result=dict(predictions_complete_sha256=pin,recipients=320,completed_fits=35)
            elif name=='assess':
                directory=self.location['run']/'assessment'
                put(directory/'report.json',dict(gate=self.gate));put(directory/'STATUS.json',dict(phase='complete'))
                put(directory/'COMPLETE.json',dict(status='complete',files_sha256={n:guard.sha(directory/n) for n in ('report.json','STATUS.json')}))
                run=self.location['run'];names=['assessment/report.json','assessment/STATUS.json','assessment/COMPLETE.json','predictions.json','PREDICTIONS_COMPLETE.json']
                pin=put(run/'COMPLETE.json',dict(status='complete',completed_fits=35,recipients=320,
                    full_train_refits=0,model_promotion=False,files_sha256={n:guard.sha(run/n) for n in names}))
                result=dict(experiment_complete_sha256=pin,gate=self.gate)
            elif name=='audit':
                result=dict(verified=True,recipients=320,models=35,methods=14,architecture_verified=True,gate=self.gate,
                    experiment_complete_sha256=guard.sha(self.location['run']/'COMPLETE.json'))
                put(self.location['verified']/'report.json',result)
                put(self.location['verified']/'COMPLETE.json',dict(status='complete',files_sha256={'report.json':guard.sha(self.location['verified']/'report.json')}))
            guard.publish_wrapper(self.location,self.context,name,result,lambda:None)
        log=output/(name+'.log');log.write_text('synthetic child only\n')
        return dict(name=name,returncode=0,elapsed_seconds=.001,output=str(stage_output),
            complete_sha256=guard.sha(stage_output/'COMPLETE.json'),log_sha256=guard.sha(log),files_verified=len(required_files))

    def run_supervisor(self,child=None,recheck=None):
        with contextlib.redirect_stdout(io.StringIO()),patch.object(guard,'preflight',return_value=self.context),\
             patch.object(guard,'recheck',side_effect=recheck),patch.object(supervisor,'run_child',side_effect=child or self.child):
            return supervisor.supervise(self.project)

    def test_fixed10_all35_full320_fourteen_methods_and_negative_gate_retained(self):
        answer=self.run_supervisor()
        self.assertEqual(self.calls,list(guard.STAGES));self.assertFalse(answer['gate']['passed'])
        self.assertFalse(answer['model_promotion']);self.assertFalse(answer['confirmatory'])
        complete=guard.read(self.output/'COMPLETE.json');self.assertEqual(complete['completed_fits'],35)
        self.assertEqual(complete['completed_oof_examples'],320);self.assertEqual(complete['completed_stages'],10)
        for name,pin in complete['files_sha256'].items():self.assertEqual(guard.sha(self.output/name),pin)
        self.assertEqual(guard.read(self.output/'manifest.json')['maximum_child_budget_seconds'],25200)
        self.assertEqual(set(guard.ENVIRONMENT),set(guard.launcher.ENVIRONMENT))

    def test_operational_failure_keeps_prior_records_and_never_retries(self):
        def child(*args,**kwargs):
            if kwargs['name']=='fold-1':raise TimeoutError('fixed child cap')
            return self.child(*args,**kwargs)
        with self.assertRaisesRegex(TimeoutError,'fixed child cap'):self.run_supervisor(child=child)
        self.assertEqual(self.calls,['preflight','initialize','fold-0'])
        self.assertTrue((self.output/'stages/fold-0/COMPLETE.json').exists())
        self.assertFalse((self.output/'COMPLETE.json').exists());self.assertTrue((self.output/'FAILED.json').exists())

    def test_unreleased_existing_run_or_jobs_never_start_children(self):
        with patch.object(guard,'preflight',side_effect=ValueError('unreleased')),patch.object(supervisor,'run_child') as child:
            with self.assertRaisesRegex(ValueError,'unreleased'):supervisor.supervise(self.project)
            child.assert_not_called()
        self.assertFalse(self.output.exists());self.location['jobs'].mkdir(parents=True)
        with patch.object(guard,'preflight',side_effect=AssertionError('must stop earlier')):
            with self.assertRaisesRegex(ValueError,'new run/jobs'):supervisor.supervise(self.project)

    def test_previous_receipt_and_log_drift_stop_next_child(self):
        def child(*args,**kwargs):
            result=self.child(*args,**kwargs)
            if kwargs['name']=='initialize':(self.output/'preflight.log').write_text('changed')
            return result
        with self.assertRaisesRegex(ValueError,'previous child log'):self.run_supervisor(child=child)
        self.assertEqual(self.calls,['preflight','initialize']);self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_late_label_drift_after_audit_prevents_outer_acceptance(self):
        def child(*args,**kwargs):
            result=self.child(*args,**kwargs)
            if kwargs['name']=='audit':put(self.location['prepared']/'fold-1/train-labels.json',{'late':True})
            return result
        with self.assertRaisesRegex(ValueError,'audit label body drift'):self.run_supervisor(child=child)
        self.assertTrue((self.location['verified']/'COMPLETE.json').exists());self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_old_reference_drift_after_audit_prevents_outer_acceptance(self):
        def child(*args,**kwargs):
            result=self.child(*args,**kwargs)
            if kwargs['name']=='audit':put(self.project/guard.OLD_RUN/'predictions.json',[{'late':True}])
            return result
        with self.assertRaisesRegex(ValueError,'old diagnostic prediction body drift'):self.run_supervisor(child=child)
        self.assertFalse((self.output/'COMPLETE.json').exists());self.assertTrue((self.output/'FAILED.json').exists())

    def test_terminal_manifest_drift_is_not_adopted_by_fresh_hash(self):
        def child(*args,**kwargs):
            result=self.child(*args,**kwargs)
            if kwargs['name']=='audit':put(self.output/'manifest.json',{'late':True})
            return result
        with self.assertRaisesRegex(ValueError,'sealed artifact changed'):self.run_supervisor(child=child)
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_post_complete_callback_drift_quarantines_outer_marker(self):
        changed=False
        def recheck(context):
            nonlocal changed
            if not changed and (self.output/'COMPLETE.json').exists():
                changed=True;put(self.output/'next_action.json',{'late':True})
        with self.assertRaisesRegex(ValueError,'sealed artifact changed'):self.run_supervisor(recheck=recheck)
        self.assertFalse((self.output/'COMPLETE.json').exists());self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists())

    def test_outer_complete_postwrite_exception_preserves_rejected_bytes(self):
        real=guard.write;saved=[]
        def write(path,value):
            pin=real(path,value)
            if path==self.output/'COMPLETE.json':saved.append(path.read_bytes());raise OSError('synthetic fsync failure')
            return pin
        with patch.object(guard,'write',side_effect=write),self.assertRaises(OSError):self.run_supervisor()
        self.assertEqual((self.output/'REJECTED_COMPLETE.json').read_bytes(),saved[0])
        self.assertFalse((self.output/'COMPLETE.json').exists())


if __name__=='__main__':unittest.main()
