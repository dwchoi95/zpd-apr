from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_preference_objective as m
from scripts import run_zpd_preference_pilot as run
from scripts import watch_zpd_completion as w
from tests.test_zpd_splice_pilot import record
from tests.test_train_zpd_paired_history import Tokenizer


def fixture(current='print(0)\n', target='print(1)\n'):
    c = record(current=current, target=target)
    h = record(current=current, target=target, history=True)
    for row in (c, h): row.update(trajectory_id='p:u', user_id='u', problem_id='p')
    p = dict(example_id='e', trajectory_id='p:u', user_id='u', problem_id='p', split='train',
        current=dict(source=current, timestamp=1), target_code=target,
        target_sha256=m.train.sha(target.encode()), target_timestamp=2)
    return c, h, p


class PairTests(unittest.TestCase):
    def test_exact_input_output_and_native_provenance(self):
        c, h, p = fixture(); before = deepcopy((c, h, p))
        result = m.audit_pair(c, h, Tokenizer(), p)
        self.assertEqual(before, (c, h, p)); self.assertEqual(result['issues'], [])
        self.assertGreater(result['arms']['H']['chosen']['prompt_tokens'], result['arms']['C']['chosen']['prompt_tokens'])
        pair = m.encode_pair(h, Tokenizer())
        self.assertEqual(pair['chosen']['messages_sha256'], pair['rejected']['messages_sha256'])
        for feature in pair.values():
            n = feature['prompt_tokens']
            self.assertTrue(all(x == -100 for x in feature['labels'][:n]))
            self.assertEqual(feature['input_ids'][-1], Tokenizer.eos_token_id)

    def test_mismatched_pair_or_provenance_is_fatal(self):
        for key in ('example_id', 'trajectory_id', 'user_id', 'problem_id', 'current_code', 'target_code'):
            c, h, p = fixture(); h[key] = 'foreign'
            with self.subTest(key=key), self.assertRaises(ValueError): m.audit_pair(c, h, Tokenizer(), p)
        c, h, p = fixture(); p['target_timestamp'] = 1
        with self.assertRaises(ValueError): m.audit_pair(c, h, Tokenizer(), p)
        c, h, p = fixture(); p['target_sha256'] = '0'*64
        with self.assertRaises(ValueError): m.audit_pair(c, h, Tokenizer(), p)

    def test_equal_normalized_targets_hold_without_filter(self):
        c, h, p = fixture('print(0)\n', 'print(0) \n')
        audit = m.audit_pair(c, h, Tokenizer(), p)
        self.assertIn('normalized_chosen_equals_rejected', audit['issues'])
        with self.assertRaises(ValueError): m.longest_indices([audit])

    def test_overflow_not_truncated_or_accepted(self):
        c, h, p = fixture(target='x'*5000)
        audit = m.audit_pair(c, h, Tokenizer(), p)
        self.assertIn('H:chosen:overflow', audit['issues'])
        self.assertGreater(audit['arms']['H']['chosen']['target_tokens'], 4096)
        self.assertEqual(c['target_code'], 'x'*5000)

    def test_union_of_longest_each_arm_side_and_deterministic_ties(self):
        rows = []
        for i in range(5):
            rows.append(dict(issues=[], arms={a:{s:dict(full_tokens=100+i) for s in ('chosen','rejected')} for a in ('C','H')}))
        rows[0]['arms']['C']['chosen']['full_tokens'] = 200
        rows[1]['arms']['C']['rejected']['full_tokens'] = 200
        rows[2]['arms']['H']['chosen']['full_tokens'] = 200
        rows[3]['arms']['H']['rejected']['full_tokens'] = 200
        rows[4]['arms']['H']['rejected']['full_tokens'] = 200
        self.assertEqual(m.longest_indices(rows), [0,1,2,3])


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('transformers'), 'optional torch unavailable')
class NumericTests(unittest.TestCase):
    def test_detached_chain_rule_matches_monolithic_dpo(self):
        import torch
        for values in ((-5.,-4.,-5.,-4.),(-4.,-8.,-5.,-4.),(-15.,-2.,-5.,-4.)):
            x = torch.tensor(values[:2], dtype=torch.float64, requires_grad=True)
            m.dpo_loss(x[0],x[1],values[2],values[3]).backward()
            coefficients = m.sequential_coefficients(*values)
            self.assertTrue(torch.allclose(x.grad, torch.tensor(coefficients, dtype=torch.float64), atol=1e-7))
            self.assertLess(coefficients[0],0); self.assertGreater(coefficients[1],0)
        for bad in (float('nan'),float('inf')):
            with self.assertRaises(ValueError): m.sequential_coefficients(bad,0,0,0)

    def test_causal_sum_eos_chunking_and_gradient_match(self):
        import torch
        import torch.nn.functional as F
        from transformers import Qwen2Config,Qwen2ForCausalLM
        torch.manual_seed(2027)
        model=Qwen2ForCausalLM(Qwen2Config(vocab_size=32,hidden_size=16,intermediate_size=32,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,attention_dropout=0.)).eval()
        ids=[1,2,3]+[4]*35+[31]; feature=dict(input_ids=ids,prompt_tokens=3)
        logits=model(torch.tensor([ids]),use_cache=False).logits[0,2:-1]
        expected=-F.cross_entropy(logits.float(),torch.tensor(ids[3:]),reduction='sum')
        expected.backward(); grads=[p.grad.clone() for p in model.parameters()]; model.zero_grad()
        actual=m.sequence_logprob(model,feature); actual.backward()
        self.assertAlmostEqual(float(actual),float(expected),places=4)
        for p,g in zip(model.parameters(),grads): self.assertTrue(torch.allclose(p.grad,g,atol=2e-5,rtol=2e-5))

    def test_no_update_probe_matches_real_model_gradient_and_preserves_weights(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM
        model=Qwen2ForCausalLM(Qwen2Config(vocab_size=32,hidden_size=16,intermediate_size=32,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,attention_dropout=0.)).train()
        pair=dict(chosen=dict(input_ids=[1,2,4,5,31],prompt_tokens=2),
                  rejected=dict(input_ids=[1,2,3,31],prompt_tokens=2))
        params=[p.detach().clone() for p in model.parameters()]
        result=m.probe_pair(model,pair)
        self.assertAlmostEqual(result['initial_loss'],math.log(2)); self.assertGreater(result['gradient_norm'],0)
        self.assertFalse(result['actual_fit'])
        for p,q in zip(model.parameters(),params): self.assertTrue(torch.equal(p,q))


class LifecycleTests(unittest.TestCase):
    def test_scoped_driver_resources_and_project_cache(self):
        old=(run.lifecycle.ROOT,run.lifecycle.command,run.lifecycle.worker)
        with run.configured():
            cmd=run.lifecycle.command('capacity',Path('/snapshot/release.json'),'pin')
            self.assertIn('scripts.run_zpd_preference_pilot',cmd)
            self.assertIn(str(run.core.PROJECT/'.runtime/fse-env/bin/python'),cmd)
            for item in ('--property=RuntimeMaxSec=3600','--property=Restart=no','--property=TasksMax=1024',
                '--setenv=CUDA_CACHE_PATH='+str(run.ROOT/'runtime-cache/capacity/cuda')): self.assertIn(item,cmd)
        self.assertEqual(old,(run.lifecycle.ROOT,run.lifecycle.command,run.lifecycle.worker))

    def test_duplicate_root_never_launches_or_stops(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run,'ROOT',Path(tmp)),run.configured(),\
             patch.object(run.lifecycle,'barrier',return_value=('r',{})),patch.object(run.lifecycle.subprocess,'run') as call:
            with self.assertRaises(ValueError): run.lifecycle.supervise(Path('/r'),'p')
            call.assert_not_called()

    def test_capacity_blocked_before_model_if_stage_not_certified(self):
        with patch.object(run,'barrier',return_value=('r',{})),\
             patch.object(run,'verify_stage',side_effect=ValueError('bad exit')),patch.object(run,'capacity') as cap:
            with self.assertRaises(ValueError):run.worker('capacity',Path('/r'),'p')
            cap.assert_not_called()

    def test_observer_exact_new_family_and_normal_exit_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'outputs'/w.PREFERENCE_PILOT_FAMILY;(root/'materialize-v1').mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            run.core.write_new(root/'materialize-v1/STATUS.json',dict(phase='materialize',completed_examples=128,total_examples=23564))
            def get(): return next(r for r in w.remote_snapshot(Path(tmp))['experiments'] if r['family']==w.PREFERENCE_PILOT_FAMILY)
            with patch.object(w,'preference_pilot_properties',return_value=dict(MainPID='5',ActiveState='active')):
                self.assertEqual(get()['completed_examples'],128)
                run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
                self.assertEqual(get()['state'],'running')
            with patch.object(w,'preference_pilot_properties',return_value=dict(MainPID='0',ActiveState='failed')):
                self.assertEqual(get()['state'],'error')


if __name__=='__main__':unittest.main()
