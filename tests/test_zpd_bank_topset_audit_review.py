"""Nonauthor audit review: scalar math and temporary synthetic seals only.

Production feature/label authentication is deliberately doubled in lifecycle
fixtures; these tests do not certify that dependency or execute any fit.
"""
from contextlib import ExitStack
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts import audit_zpd_bank_topset_run as audit
from scripts import zpd_bank_topset_objective as objective


def scalar_reference(theta,banks,weights):
    g=[float(v) for v in theta];loss=[]
    for bank,w in zip(banks,weights,strict=True):
        rest=[i for i in range(len(bank.features)) if i not in bank.top_indices]
        if not rest or w == 0:continue
        for t in bank.top_indices:
            differences=[[float(bank.features[n,j])-float(bank.features[t,j]) for j in range(len(theta))] for n in rest]
            logits=[math.fsum(a*float(b) for a,b in zip(row,theta,strict=True))-math.log(len(rest)) for row in differences]
            pivot=max([0.,*logits]);q=[math.exp(z-pivot) for z in logits]
            denominator=math.fsum([math.exp(-pivot),*q]);factor=.1*float(w)/len(bank.top_indices)
            loss.append(factor*(pivot+math.log(denominator)))
            for j in range(len(theta)):g[j]+=factor*math.fsum(row[j]*p/denominator for row,p in zip(differences,q,strict=True))
    penalty=.5*math.fsum(float(v)*float(v) for v in theta)
    return penalty+math.fsum(loss),np.asarray(g),math.fsum(loss),penalty


class DirectArithmeticReview(unittest.TestCase):
    def test_scalar_direct_affine_multitop_random_and_extreme_offsets(self):
        rng=np.random.default_rng(729)
        for count in (3,7,15):
            for tops in ((0,),(0,2),tuple(range(count))):
                banks=(objective.Bank(rng.integers(-4,5,size=(count,4)).astype(float)+2.**30,tops),)
                theta=rng.normal(size=4);w=np.array([1900.])
                actual=audit.direct_value_gradient(theta,banks,w);reference=scalar_reference(theta,banks,w)
                np.testing.assert_allclose(actual[1],reference[1],rtol=2e-14,atol=2e-12)
                for i in (0,2,3):self.assertAlmostEqual(actual[i],reference[i],places=10)

    def test_not_logsumexp_all_minus_top_and_translation_null(self):
        bank=objective.Bank(np.array([[1.,0.],[-1.,0.],[0.,0.]]),(0,1))
        theta=np.array([3.,.7]);value,g,data,penalty=audit.direct_value_gradient(theta,(bank,),np.array([1900.]))
        expected=95*(math.log1p(math.exp(-3))+math.log1p(math.exp(3)))
        self.assertAlmostEqual(data,expected,places=12)
        wrong=190*math.log1p(1/(math.exp(3)+math.exp(-3)))
        self.assertGreater(abs(data-wrong),200)
        self.assertEqual(g[1],theta[1]);self.assertEqual(value,data+penalty)

    def test_far_apart_scores_and_nonrepresentable_contrast_fail_closed(self):
        bank=objective.Bank(np.array([[1.],[0.]]),(0,))
        for theta in (np.array([-1000.]),np.array([1000.])):
            result=audit.direct_value_gradient(theta,(bank,),np.array([1900.]))
            self.assertTrue(all(math.isfinite(result[k]) for k in (0,2,3)))
            self.assertTrue(np.isfinite(result[1]).all())
        huge=objective.Bank(np.array([[-1e308],[1e308]]),(0,))
        with np.errstate(over='ignore',invalid='ignore'),self.assertRaises(FloatingPointError):
            audit.direct_value_gradient(np.zeros(1),(huge,),np.array([1900.]))


class AuditLifecycleReview(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.project=Path(temp.name).resolve();self.root=self.project/audit.job.FAMILY
        self.run=self.root/'run-v1';self.output=self.root/'verified-v1';self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.state={'revision':'a'*40,'tree':'b'*40};self.native={'synthetic':True}
        self.examples=tuple(SimpleNamespace(example_id=f'e{i}',user_id=f'u{i}',bank_id=f'b{i}',problem_id=f'p{i%23}') for i in range(320))
        self.inputs={f:SimpleNamespace(fold=f,synthetic=False,examples=self.examples,
            readiness_complete_sha256=audit.authority.READINESS_COMPLETE_SHA256,
            banks={e.bank_id:SimpleNamespace(problem_id=e.problem_id,candidates=tuple(range(8 if i<304 else 7)),seal_sha256='d'*64)
                   for i,e in enumerate(self.examples)},fold_assignment_sha256='e'*64) for f in range(5)}
        self.rows={f:[dict(example_id=e.example_id,user_id=e.user_id,bank_id=e.bank_id,problem_id=e.problem_id,
            fold=f,bank_seal_sha256='d'*64,choices={m:'candidate' for m in audit.worker.METHODS},
            candidate_scores={m:{'candidate':0.} for m in audit.worker.METHODS}) for e in self.scope(self.inputs[f])[1]] for f in range(5)}
        self.install(audit.job,'PROJECT',self.project);self.install(audit.authority,'ROOT',self.project/'.runtime'/'source')
        self.install(audit.authority,'verify_child_boundary',lambda:None)
        self.install(audit.authority,'source_state',lambda:self.state)
        self.install(audit.authority,'runtime',lambda:dict(audit.authority.preparation.RUNTIME))
        self.install(audit.authority,'controller_native',lambda:self.native)
        self.install(audit.job,'check_sources',lambda m:None)
        self.install(audit.worker.capsule,'decode_inputs',lambda x:self.inputs[x['fold']])
        self.install(audit.worker.capsule,'scope',self.scope)
        self.install(audit.worker.capsule,'validate_inputs',lambda x:[dict(example_id=e.example_id) for e in x.examples])
        self.install(audit.worker.previous,'decode_transform',lambda x:x)
        self.install(audit.worker.previous,'validate_transform',lambda *a:'f'*64)
        self.install(audit.worker,'contract_values',lambda c,i:vars(c))
        self.label_reads=[]
        self.install(audit.worker.labels,'load_fold_labels',self.load_labels)
        banks=(objective.Bank(np.zeros((2,2)),(0,)),);weights=np.array([1900.])
        self.plan=SimpleNamespace(payload=lambda:{'synthetic_plan':True},banks=lambda arm:(banks,weights))
        self.install(audit.worker.planner,'build_plan',lambda *a:self.plan)
        self.install(audit.worker,'validate_model',lambda *a:np.zeros(2))
        self.install(audit.worker.solver,'validate_model',lambda *a,**k:np.zeros(2))
        self.install(audit.worker,'predict_fold',lambda inputs,*a:self.rows[inputs.fold])
        self.install(audit.worker.solver,'fit',lambda *a,**k:(_ for _ in ()).throw(AssertionError('no optimizer allowed')))
        self.pins={};jobpins={}
        for f in range(5):
            label=self.project/audit.job.LABELS/f'fold-{f}'/'train-labels.json'
            labelpin=self.put(label,{'own_fold':f})
            contract=dict(expected_sha256=labelpin,expected_fold_assignment_sha256='e'*64,expected_source_binding_sha256='b'*64)
            payload=dict(kind=audit.job.KIND,fold=f,inputs={'fold':f},transform={},own_label_contract=contract,
                source_state=self.state,runtime=dict(audit.authority.preparation.RUNTIME),controller_native=self.native,
                source_sha256={},release_sha256='a'*64,original_job_sha256='b'*64,original_transform_sha256='c'*64)
            jobpins[str(f)]=self.put(self.root/'jobs'/f'fold-{f}.json',payload)
            self.bind(f'fold-{f}/PLAN.json',self.plan.payload())
            for arm in audit.worker.ARMS:
                self.bind(f'fold-{f}/{arm}.json',{'top_model':{'final_gradient':[0.,0.],
                    'optimization':{'objective':190*math.log(2),'weighted_bank_loss':190*math.log(2),'l2_penalty':0.}}})
            self.bind(f'fold-{f}/predictions.json',self.rows[f])
        self.bind('manifest.json',dict(job_sha256=jobpins,methods=list(audit.worker.METHODS),recipients=320,fits=35))
        self.bind('report.json',{'synthetic':True});self.bind('PREDICTIONS_COMPLETE.json',{'completed_fits':35,'recipients':320})
        self.runpin=self.put(self.run/'COMPLETE.json',dict(status='complete',recipients=320,completed_fits=35,files_sha256=self.pins))

    def install(self,module,name,replacement):self.stack.enter_context(patch.object(module,name,replacement))
    def put(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);return audit.worker.write(path,value)
    def bind(self,name,value):self.pins[name]=self.put(self.run/name,value)
    def scope(self,inputs):
        held=self.examples[inputs.fold*64:(inputs.fold+1)*64];ids={e.example_id for e in held}
        return tuple(e for e in self.examples if e.example_id not in ids),held
    def load_labels(self,directory,fold,banks,examples,**kwargs):
        self.assertEqual(set(banks),{e.bank_id for e in self.scope(self.inputs[fold])[0]})
        self.assertEqual(set(examples),{e.example_id for e in self.scope(self.inputs[fold])[0]})
        self.label_reads.append(fold);return {}

    def test_normal_all35_replay_own_only_no_fit(self):
        audit.audit(self.project,self.runpin)
        report=json.loads((self.output/'report.json').read_bytes())
        self.assertEqual(report['models'],35);self.assertEqual(report['recipients'],320)
        self.assertEqual(self.label_reads,list(range(5)))
        self.assertEqual(len(report['models_replayed']),35)

    def test_terminal_source_drift_refuses_accepted_complete(self):
        actual=audit.worker.write
        def write(path,value):
            result=actual(path,value)
            if path==self.output/'report.json':self.state={'revision':'f'*40,'tree':'b'*40}
            return result
        with patch.object(audit.worker,'write',side_effect=write),self.assertRaises(ValueError):audit.audit(self.project,self.runpin)
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_complete_fsync_failure_preserves_rejected_marker(self):
        actual=audit.worker.write
        def write(path,value):
            result=actual(path,value)
            if path==self.output/'COMPLETE.json':raise OSError('synthetic postwrite fsync failure')
            return result
        with patch.object(audit.worker,'write',side_effect=write),self.assertRaises(OSError):audit.audit(self.project,self.runpin)
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists())

    def test_same_fold_or_synthetic_scope_refused_before_labels(self):
        self.inputs[0].synthetic=True
        with self.assertRaises(ValueError):audit.audit(self.project,self.runpin)
        self.assertEqual(self.label_reads,[])

    def test_final_source_consumer_cannot_mutate_prechecked_input(self):
        changed=[]
        def source_check(mapping):
            if (self.output/'COMPLETE.json').exists() and not changed:
                with (self.run/'report.json').open('ab') as stream:stream.write(b' ')
                changed.append(True)
        with patch.object(audit.job,'check_sources',side_effect=source_check),self.assertRaises(ValueError):
            audit.audit(self.project,self.runpin)
        self.assertTrue(changed);self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'REJECTED_COMPLETE.json').exists())

    def test_simultaneous_failure_marker_never_accepted(self):
        actual=audit.worker.write
        def write(path,value):
            pin=actual(path,value)
            if path==self.output/'COMPLETE.json':actual(self.output/'FAILED.json',{'synthetic_failure':True})
            return pin
        with patch.object(audit.worker,'write',side_effect=write),self.assertRaises(ValueError):audit.audit(self.project,self.runpin)
        self.assertFalse((self.output/'COMPLETE.json').exists())


if __name__=='__main__':unittest.main()
