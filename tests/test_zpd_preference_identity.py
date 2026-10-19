from copy import deepcopy
import importlib.util
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_preference_identity as m
from scripts import run_zpd_preference_identity_pilot as run
from scripts import watch_zpd_completion as w
from tests.test_zpd_preference_pilot import fixture
from tests.test_train_zpd_paired_history import Tokenizer


class IdentityTests(unittest.TestCase):
    def test_raw_and_normalized_identities_retained_without_relabel(self):
        for before,after in [('print(0)\n','print(0)\n'),('print(0) \n','print(0)\n')]:
            c,h,p=fixture(before,after);snapshot=deepcopy((c,h,p))
            a=m.audit_pair(c,h,Tokenizer(),p)
            self.assertTrue(a['identity_tie']);self.assertEqual(a['issues'],[])
            self.assertEqual(a['original_issues'],['normalized_chosen_equals_rejected'])
            self.assertFalse(a['preference_identifiable']);self.assertEqual((c,h,p),snapshot)
            self.assertEqual(a['raw_equal'],before==after)

    def test_nonidentity_preserves_strict_audit_and_objective(self):
        c,h,p=fixture();s=m.strict.audit_pair(c,h,Tokenizer(),p);a=m.audit_pair(c,h,Tokenizer(),p)
        self.assertFalse(a['identity_tie']);self.assertTrue(a['preference_identifiable'])
        for key,value in s.items():self.assertEqual(a[key],value)
        old=m.strict.contract();new=m.contract()
        for k in old:
            if k not in ('version','identical_or_overflow'):self.assertEqual(new[k],old[k])

    def test_identity_does_not_mask_overflow(self):
        c,h,p=fixture('x'*5000,'x'*5000);a=m.audit_pair(c,h,Tokenizer(),p)
        self.assertTrue(a['identity_tie']);self.assertIn('H:chosen:overflow',a['issues'])
        with self.assertRaises(ValueError):m.longest_indices([a])

    def test_false_identity_marker_rejected(self):
        c,h,p=fixture();a=m.strict.audit_pair(c,h,Tokenizer(),p);a['issues']=['token_identical_preference']
        with patch.object(m.strict,'audit_pair',return_value=a),self.assertRaises(ValueError):m.audit_pair(c,h,Tokenizer(),p)

    def test_longest_probe_union_adds_first_identity_not_filtering(self):
        audits=[]
        for i in range(6):
            c,h,p=fixture('x','x' if i==0 else 'y'* (i+1));audits.append(m.audit_pair(c,h,Tokenizer(),p))
        self.assertEqual(m.longest_indices(audits),[0,1,5])
        self.assertEqual(len(audits),6)


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('transformers'),'optional torch unavailable')
class NumericalTests(unittest.TestCase):
    def test_identity_zero_for_noninitial_policy_and_any_beta(self):
        import torch
        for value in (-100.,-5.,-.1):
            for beta in (.01,.1,1.):
                score=torch.tensor(value,requires_grad=True)
                loss=m.dpo_loss(score,score,-17.,-17.,beta=beta);loss.backward()
                self.assertAlmostEqual(loss.item(),math.log(2),places=6);self.assertEqual(score.grad.item(),0.)

    def test_identity_real_model_has_zero_gradient_without_weight_update(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM
        model=Qwen2ForCausalLM(Qwen2Config(vocab_size=32,hidden_size=16,intermediate_size=32,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,attention_dropout=0.)).train()
        before=[p.detach().clone() for p in model.parameters()]
        row=dict(input_ids=[1,2]+[4]*35+[31],prompt_tokens=2)
        result=m.probe_pair(model,dict(chosen=row,rejected=deepcopy(row)))
        self.assertTrue(result['identity_tie']);self.assertEqual(result['gradient_norm'],0)
        self.assertTrue(result['retained_in_loss_denominator'])
        for p,q in zip(model.parameters(),before):self.assertTrue(torch.equal(p,q))

    def test_nonidentity_still_requires_nonzero_gradient(self):
        pair=dict(chosen=dict(input_ids=[1,2,3],prompt_tokens=1),rejected=dict(input_ids=[1,2,4],prompt_tokens=1))
        with patch.object(m.strict,'probe_pair',return_value=dict(gradient_norm=1.0)) as call:
            result=m.probe_pair('model',pair)
            call.assert_called_once_with('model',pair);self.assertFalse(result['identity_tie'])


class LifecycleTests(unittest.TestCase):
    def test_scoped_driver_keeps_original_pilot_unchanged(self):
        old=(run.base.ROOT,run.base.objective,run.base.barrier,run.base.lifecycle.ROOT)
        with run.configured():
            self.assertEqual(run.base.objective,m)
            cmd=run.base.lifecycle.command('capacity',Path('/snapshot/r.json'),'pin')
            self.assertIn('scripts.run_zpd_preference_identity_pilot',cmd)
            self.assertNotIn('scripts.run_zpd_preference_pilot',cmd)
            self.assertIn('--unit='+run.UNIT_PREFIX+'-capacity.service',cmd)
            self.assertIn('--property=RuntimeMaxSec=3600',cmd)
        self.assertEqual(old,(run.base.ROOT,run.base.objective,run.base.barrier,run.base.lifecycle.ROOT))

    def test_duplicate_new_family_refused(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run,'ROOT',Path(tmp)),run.configured(),\
             patch.object(run.base.lifecycle,'barrier',return_value=('r',{})),patch.object(run.base.lifecycle.subprocess,'run') as call:
            with self.assertRaises(ValueError):run.base.lifecycle.supervise(Path('/r'),'p')
            call.assert_not_called()

    def test_capacity_does_not_open_model_before_certification(self):
        with run.configured(),patch.object(run.base,'barrier',return_value=('r',{})),\
             patch.object(run.base,'verify_stage',side_effect=ValueError('bad exit')),patch.object(run.base,'capacity') as cap:
            with self.assertRaises(ValueError):run.base.worker('capacity',Path('/r'),'p')
            cap.assert_not_called()

    def test_observer_uses_new_coordinator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'outputs'/w.PREFERENCE_IDENTITY_FAMILY;(root/'materialize-v1').mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            run.core.write_new(root/'materialize-v1/STATUS.json',dict(phase='materialize',completed_examples=256,total_examples=23564))
            def get():return next(r for r in w.remote_snapshot(Path(tmp))['experiments'] if r['family']==w.PREFERENCE_IDENTITY_FAMILY)
            with patch.object(w,'preference_identity_properties',return_value=dict(MainPID='7',ActiveState='active')):
                self.assertEqual(get()['completed_examples'],256)
                run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
                self.assertEqual(get()['state'],'running')
            with patch.object(w,'preference_identity_properties',return_value=dict(MainPID='0',ActiveState='failed')):
                self.assertEqual(get()['state'],'error')


if __name__=='__main__':unittest.main()
