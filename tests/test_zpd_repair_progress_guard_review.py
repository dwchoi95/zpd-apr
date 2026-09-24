"""Independent guard boundary witnesses: synthetic metadata, no fit or corpus."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import guard_zpd_repair_progress as guard
from tests.test_zpd_repair_progress_capsule import fixture


def raw(value):return (json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()


class ProgressGuardReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name).resolve()
        scope=patch.object(guard,'PROJECT',self.project);scope.start();self.addCleanup(scope.stop)
        self.location=guard.paths(self.project)
        self.context=dict(source={'revision':'a'*40,'tree':'b'*40},release_sha256='c'*64,
            source_sha256={'scripts/synthetic.py':'d'*64},runtime={'synthetic':True},controller_native={'synthetic':True})

    def wrapper(self,stage,result):
        directory=self.location['supervisor']/'stages'/stage;directory.mkdir(parents=True)
        report=dict(kind='statement_progress32_production_stage_v1',stage=stage,status='complete',
            source=self.context['source'],release_sha256=self.context['release_sha256'],result=result,
            engine_artifact_sha256=guard._artifacts(self.location,stage))
        pin=guard.write(directory/'report.json',report)
        return guard.write(directory/'COMPLETE.json',dict(status='complete',files_sha256={'report.json':pin}))

    def fold(self):
        directory=self.location['run']/'fold-0';directory.mkdir(parents=True)
        files={n:guard.write(directory/n,{'synthetic':n}) for n in guard.worker.FILES}
        pin=guard.write(directory/'COMPLETE.json',dict(status='complete',kind='statement_progress32_fold_complete_v1',
            completed_fits=6,fold=0,predicted_examples=64,input_fingerprint='e'*64,automatic_retries=0,files_sha256=files))
        self.location['jobs'].mkdir(parents=True)
        job_pin=guard.write(self.location['jobs']/'fold-0.json',{'synthetic':'own job'})
        return dict(completed_fits=6,predicted_examples=64,job_sha256=job_pin,fold_complete_sha256=pin)

    def test_result_complete_identity_cannot_disagree_with_bound_engine_marker(self):
        result=self.fold();result['fold_complete_sha256']='f'*64
        pin=self.wrapper('fold-0',result)
        with self.assertRaises(ValueError):guard.verify_wrapper(self.project,'fold-0',pin)

    def test_valid_fold_receipt_requires_the_external_pin(self):
        result=self.fold();pin=self.wrapper('fold-0',result)
        checked=guard.verify_wrapper(self.project,'fold-0',pin)
        self.assertEqual(checked['report']['result'],result)
        with self.assertRaises(ValueError):guard.verify_wrapper(self.project,'fold-0','f'*64)

    def initialized(self):
        inputs={f:replace(fixture(fold=f),readiness_complete_sha256=guard.job.READINESS_COMPLETE_SHA256) for f in range(5)}
        contracts={f:guard.worker.LabelContract(str(f)*64,'c'*64,'e'*64) for f in range(5)}
        contracts[None]=guard.worker.LabelContract('f'*64,'c'*64,'e'*64)
        provenance={'source_sha256':{},'input_sha256':{}}
        context=guard.stages.initialize(inputs,contracts,self.location['family'],job_source=guard.job_source(self.context),
            authority=guard.authority(self.context),provenance=provenance,recheck=lambda:None)
        receipt={'initialize':{'result':{k:copy.deepcopy(context[k]) for k in
            ('initialization_sha256','jobs_complete_sha256','job_sha256','fingerprints')}}}
        return inputs,contracts,provenance,receipt

    def test_restore_keeps_externally_pinned_initialization_despite_self_reseal(self):
        inputs,contracts,provenance,receipt=self.initialized()
        restored=guard.restore(self.location,self.context,inputs,contracts,provenance,lambda:None,receipt)
        self.assertEqual(restored['initialization_sha256'],receipt['initialize']['result']['initialization_sha256'])
        path=self.location['run']/'cohort.json';value=guard.read(path);value[0]['user_id']='changed';path.write_bytes(raw(value))
        marker=self.location['run']/'INITIALIZATION_COMPLETE.json';value=guard.read(marker)
        value['files_sha256']['cohort.json']=guard.sha(path);marker.write_bytes(raw(value))
        with self.assertRaises(ValueError):guard.restore(self.location,self.context,inputs,contracts,provenance,lambda:None,receipt)

    def test_audit_prediction_barrier_precedes_every_label_read(self):
        restored=dict(inputs={0:fixture()},contracts={f:guard.worker.LabelContract(str(f)*64,'c'*64,'e'*64) for f in range(5)})
        restored['contracts'][None]=guard.worker.LabelContract('f'*64,'c'*64,'e'*64)
        with patch.object(guard,'verify_marker',return_value={'complete_sha256':'a'*64}),\
             patch.object(guard,'sha',return_value='a'*64),\
             patch.object(guard.stages,'prediction_barrier',side_effect=ValueError('unsealed predictions')),\
             patch.object(guard.labels,'load_fold_labels',side_effect=AssertionError('label body read before barrier')) as loader,\
             patch.object(Path,'read_bytes',side_effect=AssertionError('label/body read before barrier')),\
             self.assertRaisesRegex(ValueError,'unsealed predictions'):
            guard._independent_audit(self.location,restored)
        loader.assert_not_called()

    def test_wrapper_failed_complete_write_is_preserved_but_never_accepted(self):
        stage='preflight';directory=self.location['supervisor']/'stages'/stage;original=guard.write
        def broken(path,value):
            pin=original(path,value)
            if path==directory/'COMPLETE.json':raise OSError('synthetic post-write failure')
            return pin
        result=dict(recipients=320,labels_opened=False,label_bodies_opened=False,fingerprints={str(f):'e'*64 for f in range(5)})
        with patch.object(guard,'write',side_effect=broken),self.assertRaises(OSError):
            guard.publish_wrapper(self.location,self.context,stage,result,lambda:None)
        self.assertFalse((directory/'COMPLETE.json').exists())
        self.assertTrue((directory/'REJECTED_COMPLETE.json').exists())
        self.assertTrue((directory/'FAILED.json').exists())


if __name__=='__main__':unittest.main()
