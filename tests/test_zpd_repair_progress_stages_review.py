"""Independent, no-fit synthetic stage boundary regressions.

The reviewer authored progress_inputs, not the coordinator stages. Numerical
validation is mocked only where the test specifically targets artifact ordering;
these tests are not optimizer/model-quality evidence or a production release.
"""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_repair_progress_stages as stages
from tests.test_zpd_repair_progress_capsule import fixture


def raw(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


class ProgressStagesReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.family=self.root/'family';self.labels=self.root/'labels'
        self.inputs={f:fixture(fold=f) for f in range(5)}
        self.contracts={f:stages.LabelContract(str(f)*64,'c'*64,'e'*64) for f in range(5)}
        self.assessment_raw=raw({'synthetic':'no outcomes'})
        self.contracts[None]=stages.LabelContract(hashlib.sha256(self.assessment_raw).hexdigest(),'c'*64,'e'*64)
        self.source=dict(source_state=dict(revision='a'*40,tree='b'*40),source_root='/synthetic/source',
            source_sha256={'scripts/worker.py':'c'*64},runtime={'synthetic':True},controller_native={'synthetic':True})
        self.context=stages.initialize(self.inputs,self.contracts,self.family,job_source=copy.deepcopy(self.source),
            authority=dict(release_sha256='f'*64,readiness_complete_sha256='d'*64,parent_complete_sha256='b'*64),
            provenance={},recheck=lambda:None)

    def fake_folds(self):
        """Exact metadata only; models deliberately require mocked validation."""
        result={}
        for fold in range(5):
            x=self.inputs[fold];train,held=stages.capsule.scope(x);directory=self.context['run']/f'fold-{fold}'
            directory.mkdir()
            predictions=[]
            for ex,parent in zip(held,x.parent_predictions,strict=True):
                noop=parent['choices']['noop']
                p={k:parent[k] for k in ('example_id','user_id','bank_id','problem_id','fold','bank_seal_sha256')}
                p.update(choices={a:noop for a in stages.worker.METHODS},
                    shared_theta_diagnostics={a:dict(features_identical_exact=True,choice_changed=False,transition='same')
                                              for a in ('HS','Jm','CF')})
                predictions.append(p)
            pins={a+'.json':stages.write(directory/(a+'.json'),{'label_contract':vars(self.contracts[fold])})
                  for a in stages.worker.ARMS}
            model_marker=dict(fold=fold,model_files_sha256=dict(pins),train_example_ids=[e.example_id for e in train],
                held_example_ids=[e.example_id for e in held],input_fingerprint=self.context['fingerprints'][str(fold)],
                label_contract=vars(self.contracts[fold]))
            pins['MODELS_COMPLETE.json']=stages.write(directory/'MODELS_COMPLETE.json',model_marker)
            pins['predictions.json']=stages.write(directory/'predictions.json',predictions)
            pins['STATUS.json']=stages.write(directory/'STATUS.json',dict(phase='complete',fold=fold,completed_fits=6,
                total_fits=6,predicted_examples=len(held),total_held_examples=len(held)))
            stages.write(directory/'COMPLETE.json',dict(status='complete',kind='statement_progress32_fold_complete_v1',
                fold=fold,completed_fits=6,predicted_examples=len(held),input_fingerprint=self.context['fingerprints'][str(fold)],
                automatic_retries=0,files_sha256=pins))
            result[fold]=predictions
        return result

    def assessment_boundary(self):
        rows=[p for values in self.fake_folds().values() for p in values]
        self.context['predictions_complete_sha256']=stages.write(self.context['run']/'PREDICTIONS_COMPLETE.json',{'synthetic':True})
        stages.write(self.context['run']/'predictions.json',rows)
        path=self.labels/'assessment'/'all320-labels.json';path.parent.mkdir(parents=True);path.write_bytes(self.assessment_raw)
        return rows

    def test_initial_contract_cannot_be_replaced_by_self_consistent_mutable_context(self):
        for fold in (0,None):
            old=self.context['contracts'][fold]
            self.context['contracts'][fold]=replace(old,expected_sha256='f'*64)
            with self.assertRaises(ValueError):stages.verify_initialization(self.context)
            self.context['contracts'][fold]=old

    def test_consumed_fold_complete_bytes_are_pinned_not_a_later_snapshot(self):
        predictions=self.fake_folds();target=self.context['run']/'fold-0'/'COMPLETE.json'
        original=Path.read_bytes;done={'value':False}
        def changed(path):
            value=original(path)
            if path==target and not done['value']:
                done['value']=True;altered=json.loads(value);altered['completed_fits']=0;target.write_bytes(raw(altered))
            return value
        with patch.object(Path,'read_bytes',changed),patch.object(stages.worker,'validate_model'),\
             patch.object(stages.worker,'predict_fold',side_effect=lambda x,m:predictions[x.fold]),self.assertRaises(ValueError):
            stages.fold_predictions(self.context)

    def test_assessment_first_write_pins_survive_later_report_rehash(self):
        rows=self.assessment_boundary();original=stages.write;target=self.context['run']/'assessment'/'COMPLETE.json'
        def changed(path,value):
            pin=original(path,value)
            if path==target:
                report=path.parent/'report.json';body=stages.read(report);body['gate']['passed']=True;report.write_bytes(raw(body))
            return pin
        with patch.object(stages,'prediction_barrier',return_value=rows),\
             patch.object(stages.provider,'validate_assessment_envelope',return_value={}),\
             patch.object(stages.assessment,'assess',return_value={'gate':{'passed':False}}),\
             patch.object(stages,'write',side_effect=changed),self.assertRaises(ValueError):
            stages.assess_predictions(self.context,self.labels)
        self.assertFalse((self.context['run']/'COMPLETE.json').exists())
        self.assertFalse(target.exists())
        self.assertTrue((target.parent/'REJECTED_COMPLETE.json').exists())

    def test_run_complete_fsync_failure_quarantines_both_markers(self):
        rows=self.assessment_boundary();original=stages.write;target=self.context['run']/'COMPLETE.json'
        def broken(path,value):
            pin=original(path,value)
            if path==target:raise OSError('synthetic post-write fsync failure')
            return pin
        with patch.object(stages,'prediction_barrier',return_value=rows),\
             patch.object(stages.provider,'validate_assessment_envelope',return_value={}),\
             patch.object(stages.assessment,'assess',return_value={'gate':{'passed':False}}),\
             patch.object(stages,'write',side_effect=broken),self.assertRaises(OSError):
            stages.assess_predictions(self.context,self.labels)
        for directory in (self.context['run'],self.context['run']/'assessment'):
            self.assertFalse((directory/'COMPLETE.json').exists())
            self.assertTrue((directory/'REJECTED_COMPLETE.json').exists())
            self.assertTrue((directory/'FAILED.json').exists())

    def test_last_boundary_cannot_change_report_after_the_artifact_check(self):
        rows=self.assessment_boundary();armed={'value':False};calls={'value':0}
        target=self.context['run']/'assessment'/'report.json'
        def recheck():
            if (self.context['run']/'COMPLETE.json').exists():
                calls['value']+=1
                if calls['value']==2:
                    armed['value']=True;body=stages.read(target);body['gate']['passed']=True;target.write_bytes(raw(body))
        self.context['recheck']=recheck
        with patch.object(stages,'prediction_barrier',return_value=rows),\
             patch.object(stages.provider,'validate_assessment_envelope',return_value={}),\
             patch.object(stages.assessment,'assess',return_value={'gate':{'passed':False}}),self.assertRaises(ValueError):
            stages.assess_predictions(self.context,self.labels)
        self.assertTrue(armed['value']);self.assertFalse((self.context['run']/'COMPLETE.json').exists())

    def test_late_assessment_contract_switch_cannot_open_new_label_body(self):
        rows=self.assessment_boundary();old=self.context['contracts'][None]
        def switched(context):
            context['contracts'][None]=replace(old,expected_sha256='f'*64)
            return rows
        actual=Path.read_bytes
        def reading(path):
            if path.is_relative_to(self.labels):raise AssertionError('contract mismatch must precede label body read')
            return actual(path)
        with patch.object(stages,'prediction_barrier',side_effect=switched),\
             patch.object(Path,'read_bytes',reading),self.assertRaises(ValueError):
            stages.assess_predictions(self.context,self.labels)

    def test_final_prediction_boundary_rechecks_model_files_not_only_global_marker(self):
        predictions=self.fake_folds()
        with patch.object(stages.worker,'validate_model'),\
             patch.object(stages.worker,'predict_fold',side_effect=lambda x,m:predictions[x.fold]):
            stages.finalize_predictions(self.context)
            original=stages.read;consumed={'value':False};changed={'value':False}
            def read(path):
                value=original(path)
                if path==self.context['run']/'predictions.json':consumed['value']=True
                return value
            def recheck():
                if consumed['value'] and not changed['value']:
                    changed['value']=True
                    with (self.context['run']/'fold-0'/'H.json').open('ab') as stream:stream.write(b' ')
            self.context['recheck']=recheck
            with patch.object(stages,'read',side_effect=read),self.assertRaises(ValueError):
                stages.prediction_barrier(self.context)
            self.assertTrue(changed['value'])


if __name__=='__main__':unittest.main()
