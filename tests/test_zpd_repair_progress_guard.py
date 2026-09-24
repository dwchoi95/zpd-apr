"""Synthetic metadata/receipt boundaries only; no dataset reads or fitting."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import guard_zpd_repair_progress as guard

SOURCE_INVENTORY=guard.SOURCE_FILES


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True)+'\n')
    return guard.sha(path)


def synthetic_fold(location,fold,fingerprint='d'*64):
    directory=location['run']/f'fold-{fold}'
    for name in guard.worker.FILES:put(directory/name,dict(synthetic=name))
    put(directory/'COMPLETE.json',dict(status='complete',kind='statement_progress32_fold_complete_v1',fold=fold,
        completed_fits=6,predicted_examples=64,input_fingerprint=fingerprint,automatic_retries=0,
        files_sha256={n:guard.sha(directory/n) for n in guard.worker.FILES}))


class ProgressGuardTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.project=Path(temp.name).resolve();self.root=self.project/'.runtime/source';self.root.mkdir(parents=True)
        self.state=dict(revision='a'*40,tree='b'*40);self.native={'synthetic':'no native probe'}
        self.patch(guard,'PROJECT',self.project);self.patch(guard,'ROOT',self.root)
        self.patch(guard,'SOURCE_FILES',('scripts/synthetic_progress.py',guard.PROTOCOL))
        self.mock(guard,'source_state',return_value=self.state);self.mock(guard,'runtime',return_value=guard.RUNTIME)
        self.mock(guard,'controller_native',return_value=self.native);self.mock(guard,'verify_child_boundary')
        self.mock(guard.subprocess,'check_output',side_effect=lambda args,**kw:('\0'.join(args[args.index('--')+1:])+'\0').encode())
        self.location=guard.paths(self.project)
        for name in guard.SOURCE_FILES:
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('synthetic '+name)
        self.contracts={}
        for f in [*range(5),None]:
            name='assessment/all320-labels.json' if f is None else f'fold-{f}/train-labels.json'
            pin=put(self.location['prepared']/name,{'synthetic_label':f})
            self.contracts[f]=guard.worker.LabelContract(pin,'b'*64,'c'*64)
        for name in ('manifest.json','folds.json','COMPLETE.json'):put(self.location['prepared']/name,{'synthetic':name})
        self.patch(guard,'PREPARED_COMPLETE_SHA256',guard.sha(self.location['prepared']/'COMPLETE.json'))
        self.mock(guard.oldguard,'_metadata_preparation',return_value=(self.contracts,{},{}))
        parent=put(self.project/guard.accepted.observed.PARENT/'COMPLETE.json',{'status':'complete'})
        support=put(self.project/guard.observed.SUPPORT/'COMPLETE.json',{'status':'complete'})
        self.patch(guard.job,'PARENT_COMPLETE_SHA256',parent);self.patch(guard.job,'READINESS_COMPLETE_SHA256',support)
        prereqs={}
        for name in guard.PREREQUISITE_RELEASES:prereqs[name]=put(self.root/name,{'synthetic_release':name})
        self.patch(guard,'PREREQUISITE_RELEASES',prereqs)
        self.approval=dict(kind='repair_statement_progress32_fixed30_fit_release_v1',project=str(self.project),family=guard.FAMILY,
            fit_release_authorized=True,confirmatory=False,fresh_test_opened=False,configuration=guard.release_configuration(),runtime=guard.RUNTIME,
            input_complete_sha256={guard.observed.SUPPORT+'/COMPLETE.json':support,
                guard.accepted.observed.PARENT+'/COMPLETE.json':parent,guard.PREPARED+'/COMPLETE.json':guard.PREPARED_COMPLETE_SHA256},
            prepared_metadata_sha256={guard.PREPARED+'/'+n:guard.sha(self.location['prepared']/n) for n in ('manifest.json','folds.json')},
            prepared_label_contracts=guard.serialized_contracts(self.contracts),prerequisite_release_sha256=prereqs,
            protocol_sha256=guard.sha(self.root/guard.PROTOCOL),source_sha256={n:guard.sha(self.root/n) for n in guard.SOURCE_FILES},
            controller_native=self.native,decision_reason='synthetic test only')
        self.set_release(self.approval)

    def patch(self,obj,name,value):
        mock=patch.object(obj,name,value);mock.start();self.addCleanup(mock.stop)

    def mock(self,obj,name,**kwargs):
        mock=patch.object(obj,name,**kwargs);value=mock.start();self.addCleanup(mock.stop);return value

    def set_release(self,value):
        pin=put(self.root/guard.RELEASE,value);(self.root/guard.SIDECAR).write_text(pin+'\n')

    def context(self):return guard.preflight(self.project)

    def test_full_closure_is_code_protocol_only_and_transitive(self):
        self.assertTrue(set(guard.accepted.SOURCE_FILES)<=set(SOURCE_INVENTORY))
        self.assertTrue(set(guard.oldguard.SOURCE_FILES)<=set(SOURCE_INVENTORY))
        self.assertTrue(set(guard.observed.LOCAL_SOURCES)<=set(SOURCE_INVENTORY))
        guard.job.validate_source_map({n:'a'*64 for n in SOURCE_INVENTORY})
        self.assertNotIn(guard.RELEASE,SOURCE_INVENTORY)

    def test_preflight_no_label_body_or_outputs_and_six_metadata_contracts(self):
        real=Path.open
        def checked(path,*args,**kw):
            if path.name in ('train-labels.json','all320-labels.json','labels.jsonl'):raise AssertionError('body forbidden')
            return real(path,*args,**kw)
        with patch.object(Path,'open',checked):context=self.context();guard.recheck(context)
        self.assertEqual(set(context['label_contracts']),{'0','1','2','3','4','assessment'})
        for key in ('run','jobs','supervisor'):self.assertFalse(self.location[key].exists())

    def test_unreleased_strict_sidecar_and_no_cli_configuration_override(self):
        (self.root/guard.SIDECAR).unlink()
        with self.assertRaisesRegex(ValueError,'separate progress32'):self.context()
        for stage in ('prepare','fold-0'):
            with self.assertRaisesRegex(ValueError,'coordinator stage'):guard.execute_stage(self.project,stage,{})
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            guard.main(['--project',str(self.project),'--stage','preflight','--previous-stage-sha256','{}','--retry'])
        self.assertFalse(self.location['supervisor'].exists())

    def test_strict_release_schema_sources_runtime_and_types(self):
        mutations=[lambda v:v.update(fit_release_authorized=False),lambda v:v.update(extra=True),
            lambda v:v['configuration'].update(fits=25),lambda v:v['configuration'].update(automatic_retries=False),
            lambda v:v['source_sha256'].pop(guard.PROTOCOL),lambda v:v.update(controller_native={'changed':True}),
            lambda v:v['prepared_label_contracts']['0'].update(expected_sha256='0'*64)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                value=copy.deepcopy(self.approval);mutation(value);self.set_release(value)
                with self.assertRaises(ValueError):self.context()
        self.set_release(self.approval)
        (self.root/guard.SIDECAR).write_text(guard.sha(self.root/guard.RELEASE).upper()+'\n')
        with self.assertRaisesRegex(ValueError,'sidecar'):self.context()

    def test_loaded_source_and_native_drift_rejected(self):
        context=self.context();(self.root/'scripts/synthetic_progress.py').write_text('drift')
        with self.assertRaisesRegex(ValueError,'source changed'):guard.recheck(context)
        with patch.object(guard,'controller_native',return_value={'changed':True}),self.assertRaisesRegex(ValueError,'runtime/native'):
            guard.recheck(context)

    def test_alias_and_existing_wrapper_are_not_overwritten(self):
        alias=self.project/'alias';alias.symlink_to(self.project,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'canonical'):guard.paths(alias)
        context=self.context();guard.publish_wrapper(self.location,context,'preflight',{},lambda:None)
        with self.assertRaisesRegex(ValueError,'new stage receipt'):guard.publish_wrapper(self.location,context,'preflight',{},lambda:None)

    def test_externally_pinned_prior_receipt_rejects_self_reseal(self):
        context=self.context();value=guard.publish_wrapper(self.location,context,'preflight',{},lambda:None)
        directory=self.location['supervisor']/'stages/preflight';report=guard.read(directory/'report.json')
        report['result']['changed']=True;put(directory/'report.json',report)
        put(directory/'COMPLETE.json',{'status':'complete','files_sha256':{'report.json':guard.sha(directory/'report.json')}})
        with self.assertRaisesRegex(ValueError,'externally pinned'):guard.previous(self.project,'initialize',{'preflight':value['complete_sha256']},context)
        with self.assertRaisesRegex(ValueError,'exact externally'):guard.previous(self.project,'initialize',{},context)

    def test_wrapper_complete_write_pin_cannot_be_replaced_by_late_hash(self):
        context=self.context();directory=self.location['supervisor']/'stages/preflight'
        def drift():
            if (directory/'COMPLETE.json').exists():
                marker=guard.read(directory/'COMPLETE.json');put(directory/'COMPLETE.json',dict(marker,late=True))
        with self.assertRaisesRegex(ValueError,'externally pinned'):guard.publish_wrapper(self.location,context,'preflight',{},drift)
        self.assertFalse((directory/'COMPLETE.json').exists());self.assertTrue((directory/'REJECTED_COMPLETE.json').exists())
        self.assertTrue((directory/'FAILED.json').exists())

    def test_post_write_fsync_error_quarantines_exact_complete(self):
        context=self.context();real=guard.write;written=[]
        def fail(path,value):
            pin=real(path,value)
            if path.name=='COMPLETE.json':written.append(path.read_bytes());raise OSError('fsync synthetic failure')
            return pin
        with patch.object(guard,'write',side_effect=fail),self.assertRaises(OSError):
            guard.publish_wrapper(self.location,context,'preflight',{},lambda:None)
        directory=self.location['supervisor']/'stages/preflight'
        self.assertEqual((directory/'REJECTED_COMPLETE.json').read_bytes(),written[0])
        self.assertFalse((directory/'COMPLETE.json').exists())

    def test_actual_fold_seal_and_result_link_required(self):
        context=self.context();synthetic_fold(self.location,0)
        marker=self.location['run']/'fold-0/COMPLETE.json'
        result=dict(completed_fits=6,predicted_examples=64,fold_complete_sha256='0'*64,job_sha256='a'*64)
        with self.assertRaisesRegex(ValueError,'result and actual'):guard.publish_wrapper(self.location,context,'fold-0',result,lambda:None)
        self.assertTrue(marker.exists())

    def test_audit_label_recheck_is_explicit_and_all_six(self):
        guard.verify_audit_label_inputs(self.location,self.contracts)
        put(self.location['prepared']/'fold-4/train-labels.json',{'late':True})
        with self.assertRaisesRegex(ValueError,'label body drift'):guard.verify_audit_label_inputs(self.location,self.contracts)

    def test_audit_barrier_precedes_training_and_assessment_io(self):
        path=self.location['run'];put(path/'report.json',{})
        put(path/'COMPLETE.json',{'status':'complete','files_sha256':{'report.json':guard.sha(path/'report.json')}})
        restored=dict(inputs={},contracts=self.contracts)
        with patch.object(guard,'verify_marker'),patch.object(guard.stages,'prediction_barrier',side_effect=ValueError('not all30')),\
             patch.object(guard.labels,'load_fold_labels',side_effect=AssertionError('no training body before barrier')):
            with self.assertRaisesRegex(ValueError,'not all30'):guard._independent_audit(self.location,restored)


if __name__=='__main__':unittest.main()
