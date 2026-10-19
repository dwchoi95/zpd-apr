from copy import deepcopy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import train_zpd_preference as m
from scripts import run_zpd_preference_training as run
from scripts import watch_zpd_completion as w
from tests.test_zpd_preference_pilot import fixture
from tests.test_train_zpd_paired_history import Tokenizer


class PureTests(unittest.TestCase):
    def test_pilot_token_bindings_and_overflow_are_not_bypassed(self):
        c,h,p=fixture();audit=m.objective.audit_pair(c,h,Tokenizer(),p)
        pair=m.checked_pair(c,Tokenizer(),audit,'C')
        self.assertFalse(m.identity(pair))
        for key in ('messages_sha256','target_token_ids_sha256','full_tokens'):
            bad=deepcopy(audit);bad['arms']['C']['chosen'][key]='wrong'
            with self.assertRaises(ValueError):m.checked_pair(c,Tokenizer(),bad,'C')

    def test_reference_binding_rejects_foreign_examples_or_features(self):
        c,h,p=fixture();pair=m.objective.encode_pair(c,Tokenizer())
        row=dict(example_id=c['example_id'],binding=m.binding(pair),identity_tie=False,
            reference=dict(chosen=-1.,rejected=-2.))
        self.assertEqual(m.bound_reference(pair,c,row),row['reference'])
        for key,value in [('example_id','foreign'),('identity_tie',True),('binding',{})]:
            bad=dict(row,**{key:value})
            with self.assertRaises(ValueError):m.bound_reference(pair,c,bad)
        bad=deepcopy(row);bad['reference']['chosen']=float('nan')
        with self.assertRaises(ValueError):m.bound_reference(pair,c,bad)

    def test_stable_loss_and_identity_reference_rejection(self):
        self.assertAlmostEqual(m.loss_value(dict(chosen=0.,rejected=0.),dict(chosen=-9.,rejected=-9.)),math.log(2))
        self.assertTrue(math.isfinite(m.loss_value(dict(chosen=-1e6,rejected=0.),dict(chosen=0.,rejected=0.))))
        pair=dict(chosen=dict(input_ids=[1,2],prompt_tokens=1),rejected=dict(input_ids=[1,2],prompt_tokens=1))
        self.assertEqual(m.backward_pair(None,pair,dict(chosen=-1.,rejected=-1.),16),math.log(2))
        with self.assertRaises(ValueError):m.backward_pair(None,pair,dict(chosen=-1.,rejected=-2.),16)
        with self.assertRaises(ValueError):m.backward_pair(None,pair,dict(chosen=-1.,rejected=-1.),0)

    def test_scoped_command_has_gpu_envelope_and_local_caches(self):
        before=(run.paired.FAMILY,run.paired.PHASES,run.paired.limits)
        for phase in run.PHASES:
            cmd=run.command(phase,Path('/snapshot/r.json'),'pin')
            for value in ('scripts.run_zpd_preference_training','--property=MemoryMax=68719476736',
                          '--property=TasksMax=1024','--property=LimitAS=infinity','--property=Restart=no',
                          '--property=RuntimeMaxSec='+str(run.SECONDS[phase])):self.assertIn(value,cmd)
            self.assertIn('--setenv=TMPDIR='+str(run.ROOT/'tmp'/phase),cmd)
        self.assertEqual(before,(run.paired.FAMILY,run.paired.PHASES,run.paired.limits))

    def test_all_predecessors_verified_before_fit(self):
        with patch.object(run,'verify_stage') as check:
            run.dependencies('train-C','pin')
            self.assertEqual([c.args[0] for c in check.call_args_list],['reference-C','reference-H'])
        with patch.object(run,'verify_stage',side_effect=ValueError('bad exit')),self.assertRaises(ValueError):
            run.dependencies('train-H','pin')

    def test_bad_dependency_prevents_model_loading(self):
        with patch.object(run,'barrier',return_value=('r',{})),patch.object(run,'dependencies',side_effect=ValueError('running')),\
             patch.object(m,'load_model') as load:
            with self.assertRaises(ValueError):run.worker('train-C',Path('/release'),'pin')
            load.assert_not_called()

    def test_duplicate_does_not_launch_or_stop(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(run,'ROOT',Path(tmp)),\
             patch.object(run,'barrier',return_value=('r',{})),patch.object(run.subprocess,'run') as call:
            with self.assertRaises(ValueError):run.supervise(Path('/release'),'pin')
            call.assert_not_called()

    def test_release_keeps_performance_gate_and_objective(self):
        old=json.loads(Path('analysis_protocols/zpd-preference-identity-pilot-release-20261020.json').read_bytes())
        new=deepcopy(old);new.update(version=run.VERSION,family_path=str(run.ROOT),phases=list(run.PHASES),
            phase_seconds=run.SECONDS,parent_release_sha256=run.PARENT_RELEASE,parent_complete_sha256=run.PARENT_SHA,
            method=m.contract())
        new['source_sha256'].update({k:'pin' for k in run.REQUIRED})
        run.validate_release(new,old)
        for key,value in [('development_gate',{}),('counts',{}),('method',{})]:
            bad=deepcopy(new);bad[key]=value
            with self.assertRaises(ValueError):run.validate_release(bad,old)

    def test_observer_reports_ref_not_training_and_validation_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'outputs'/w.PREFERENCE_TRAINING_FAMILY;root.mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            (root/'reference-C-v1/reference').mkdir(parents=True)
            run.core.write_new(root/'reference-C-v1/reference/STATUS.json',dict(phase='reference-C',
                completed_examples=64,total_examples=23564,elapsed_seconds=10))
            with patch.object(w,'preference_training_properties',return_value=dict(MainPID='7',ActiveState='active')):
                row=w.preference_training_progress(root)
                self.assertEqual(row['training_completed_examples_total'],0)
                self.assertEqual(row['completed_examples'],64)
                run.core.write_new(root/'STATUS.json',dict(phase='train-H',completed_phases=['reference-C','reference-H','train-C']))
                (root/'train-H-v1/training').mkdir(parents=True)
                run.core.write_new(root/'train-H-v1/training/STATUS.json',dict(phase='validation-H',
                    completed_examples=32,total_examples=4365,training_completed_examples=19199,elapsed_seconds=10))
                row=w.preference_training_progress(root)
                self.assertEqual(row['training_completed_examples_total'],38398)
                self.assertEqual(row['completed_examples'],32)
                run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
                self.assertEqual(w.preference_training_progress(root)['state'],'running')


@unittest.skipUnless(all(importlib.util.find_spec(x) for x in ('torch','transformers','peft')),'optional torch runtime absent')
class NumericalTests(unittest.TestCase):
    def tiny(self):
        import torch
        from transformers import Qwen2Config,Qwen2ForCausalLM
        from peft import LoraConfig,get_peft_model
        torch.manual_seed(2027)
        model=get_peft_model(Qwen2ForCausalLM(Qwen2Config(vocab_size=16,hidden_size=16,intermediate_size=32,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,attention_dropout=0.)),
            LoraConfig(r=2,lora_alpha=4,lora_dropout=0.,target_modules=['q_proj','v_proj'],task_type='CAUSAL_LM'))
        model.train();model.config.use_cache=False
        return model

    def pair(self,same=False):
        pos=dict(input_ids=[1,2,4,5,0],prompt_tokens=2)
        return dict(chosen=pos,rejected=deepcopy(pos) if same else dict(input_ids=[1,2,3,0],prompt_tokens=2))

    def test_sequential_gradient_matches_whole_loss_with_full_identity_denominator(self):
        import torch
        model=self.tiny();pair=self.pair();ref=dict(chosen=-17.,rejected=-13.)
        chosen=m.objective.sequence_logprob(model,pair['chosen']);rejected=m.objective.sequence_logprob(model,pair['rejected'])
        ((m.objective.dpo_loss(chosen,rejected,ref['chosen'],ref['rejected'])+math.log(2))/2).backward()
        expected={n:p.grad.clone() for n,p in model.named_parameters() if p.requires_grad};model.zero_grad()
        m.backward_pair(model,pair,ref,2)
        before={n:p.grad.clone() for n,p in model.named_parameters() if p.requires_grad}
        m.backward_pair(model,self.pair(True),dict(chosen=-2.,rejected=-2.),2)
        for n,p in model.named_parameters():
            if p.requires_grad:
                self.assertTrue(torch.allclose(p.grad,expected[n],atol=2e-5,rtol=2e-5))
                self.assertTrue(torch.equal(p.grad,before[n]))

    def test_full_reference_then_fit_keeps_cache_and_last_short_window(self):
        model=self.tiny();rows=dict(train=[dict(example_id='a'),dict(example_id='b'),dict(example_id='c')],
            valid=[dict(example_id='v')])
        pair_at=lambda s,i:self.pair(s=='train' and i==1)
        class Tok:
            def save_pretrained(self,path):m.core.write_new(path/'tokenizer-test.json',dict(test=True))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ref=root/'reference';out=root/'training'
            summary=m.reference_cache(model,rows,pair_at,ref,'C')
            self.assertFalse(summary['actual_fit']);self.assertEqual(summary['identity_counts']['train'],1)
            pin=m.core.sha_file(ref/'COMPLETE.json');before={p.name:p.read_bytes() for p in ref.iterdir()}
            config=dict(m.CONFIG,learning_rate=1e-3,accumulation_pairs=2,warmup_ratio=0.)
            result=m.fit(model,Tok(),rows,pair_at,ref,pin,out,'C',config=config)
            self.assertEqual(result['completed_examples'],3);self.assertEqual(result['optimizer_steps'],2)
            self.assertEqual(result['identity_examples'],1)
            self.assertNotEqual(result['initial_adapter'],result['final_adapter'])
            self.assertEqual(before,{p.name:p.read_bytes() for p in ref.iterdir()})
            journal=m.train._read_rows(out/'consumed-examples.jsonl')
            self.assertEqual([v['denominator'] for v in journal],[2,1])
            self.assertEqual([v for j in journal for v in j['example_ids']],['a','b','c'])
            self.assertTrue(m.paired.read_sealed(out,m.core.sha_file(out/'COMPLETE.json')))
            # Even well-formed replacement reference bytes fail the old seal.
            (ref/'valid.jsonl').write_text('{}\n')
            with self.assertRaises(ValueError):m.load_references(ref,pin,rows,'C')

    def test_changed_policy_cannot_replace_initial_reference(self):
        import torch
        model=self.tiny();rows=dict(train=[dict(example_id='a')],valid=[dict(example_id='v')])
        with tempfile.TemporaryDirectory() as tmp:
            ref=Path(tmp)/'reference';m.reference_cache(model,rows,lambda s,i:self.pair(),ref,'C')
            with torch.no_grad():
                for p in model.parameters():
                    if p.requires_grad:p.add_(.1)
            with self.assertRaisesRegex(ValueError,'cached original SFT'):
                m.fit(model,None,rows,lambda s,i:self.pair(),ref,m.core.sha_file(ref/'COMPLETE.json'),Path(tmp)/'fit','C')


if __name__=='__main__':unittest.main()
