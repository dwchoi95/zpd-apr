"""Public-only ranking invariants and exact causal likelihood alignment."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import zpd_likelihood_selection as m
from scripts import run_zpd_likelihood_selection as run
from scripts import watch_zpd_completion as watch
from tests.test_diagnose_zpd_transition_failure import fixture as bank_fixture
from tests.test_prepare_zpd_full_source import fixture as prompt_fixture


def fixture():
    inputs,attempts,old,_=bank_fixture();inputs['prompts']=[]
    for p in old:
        eid,arm=p['example_id'],p['arm'];pid=eid+'-'+arm
        messages=m.full.render_prompt(prompt_fixture('prior','current'))
        pin=m.full.sha(m.full.encoded(messages))
        inputs['prompts'].append(dict(prompt_id=pid,prompt_sha256=pin,messages=messages,example_id=eid,arm=arm))
        for rows in (inputs['attempts'],attempts):
            for r in rows:
                if r['example_id']==eid and r['arm']==arm:r.update(prompt_id=pid,prompt_sha256=pin)
    roster,membership,_,sources,_,_=m.diag._inventory(inputs,attempts,old)
    masks={pid+'|'+cid:[True] for pid,cid in sources};scoring={}
    for p in old:
        eid,arm=p['example_id'],p['arm'];scores=scoring.setdefault(eid,{})
        scores.update({c:0.0 for c in membership[eid,arm]})
    for p in old:
        eid,arm=p['example_id'],p['arm'];scores={c:scoring[eid][c] for c in membership[eid,arm]}
        winner,detail=m.choose(scores,{c:[True] for c in scores},roster[eid]['current_source_sha256'],min(scores))
        p.update(selected_source_sha256=winner,selected_source=sources['p',winner],diagnostic=detail)
    return inputs,attempts,old,masks,scoring


class SelectionTests(unittest.TestCase):
    def test_pure_public_preparation_and_complete_roles(self):
        data=fixture();before=deepcopy(data);b=m.prepare(*data)
        self.assertEqual(data,before);self.assertEqual(len(b['tasks']),24)
        self.assertEqual(b['examples'],2);self.assertFalse(b['private_assessment_accessed'])
        self.assertTrue(all(t['adapter_role']==m.ROLES[t['arm']] for t in b['tasks']))
        self.assertEqual(len({t['task_id'] for t in b['tasks']}),24)

    def test_likelihood_changes_only_public_tied_owned_choice(self):
        b=m.prepare(*fixture());scores={t['task_id']:dict(status='scored',mean_logprob=-10.) for t in b['tasks']}
        for r in b['rows']:scores[max(r['task_ids'].values())]['mean_logprob']=-1.
        before=deepcopy(b);out=m.choose_scored(b,scores);self.assertEqual(b,before)
        for r,p in zip(b['rows'],out):
            chosen=next(c for c,t in r['task_ids'].items() if t==max(r['task_ids'].values()))
            self.assertEqual(p['selected_source_sha256'],chosen)
            self.assertEqual(p['eligible_candidate_ids'],r['original']['eligible_candidate_ids'])

    def test_unscorable_tie_retains_original_no_candidate_dropping(self):
        b=m.prepare(*fixture());scores={t['task_id']:dict(status='scored',mean_logprob=-1.) for t in b['tasks']}
        for r in b['rows']:scores[next(iter(r['task_ids'].values()))]=dict(status='overflow',mean_logprob=None)
        out=m.choose_scored(b,scores)
        self.assertTrue(all(p['diagnostic']['rule']=='unscorable_tie' and not p['diagnostic']['choice_changed'] for p in out))

    def test_equal_likelihood_uses_source_hash_not_iteration(self):
        b=m.prepare(*fixture());scores={t['task_id']:dict(status='scored',mean_logprob=-2.) for t in reversed(b['tasks'])}
        for r,p in zip(b['rows'],m.choose_scored(b,scores)):self.assertEqual(p['selected_source_sha256'],min(r['task_ids']))

    def test_invalid_or_missing_likelihood_rejected(self):
        b=m.prepare(*fixture());base={t['task_id']:dict(status='scored',mean_logprob=-2.) for t in b['tasks']}
        for value in (float('nan'),float('inf'),1.,None):
            s=deepcopy(base);s[next(iter(s))]['mean_logprob']=value
            with self.subTest(value=value),self.assertRaises(ValueError):m.choose_scored(b,s)
        s=deepcopy(base);s.pop(next(iter(s)))
        with self.assertRaises(ValueError):m.choose_scored(b,s)

    def test_public_fallback_or_unique_winner_not_scored(self):
        for unavailable in (True,False):
            data=list(fixture());roster,members,_,sources,_,_=m.diag._inventory(*data[:3])
            for key in data[3]:data[3][key]=None if unavailable else [False]
            if not unavailable:data[3]['p|'+m.full.sha(b'current')]=[True]
            for p in data[2]:
                eid,arm=p['example_id'],p['arm'];scores={c:data[4][eid][c] for c in members[eid,arm]}
                w,d=m.choose(scores,{c:data[3]['p|'+c] for c in scores},m.full.sha(b'current'),min(scores))
                p.update(selected_source_sha256=w,selected_source=sources['p',w],diagnostic=d)
            b=m.prepare(*data);self.assertEqual(b['tasks'],[])
            self.assertTrue(all(not p['diagnostic']['choice_changed'] for p in m.choose_scored(b,{})))

    def test_foreign_prompt_or_original_choice_refused(self):
        for kind in ('prompt','choice','source'):
            data=fixture()
            if kind=='prompt':data[0]['prompts'][0]['arm']='foreign'
            elif kind=='choice':data[2][0]['diagnostic']['fallback']=True
            else:data[1][0]['attempt']['source']='unbound'
            with self.subTest(kind=kind),self.assertRaises(ValueError):m.prepare(*data)

    def test_encode_normalization_eos_exact_caps_no_truncation(self):
        class Tok:
            eos_token_id=99
            def __call__(self,text,**kwargs):
                assert kwargs==dict(add_special_tokens=False,truncation=False)
                return dict(input_ids=[1]*len(text))
        t=dict(messages=[],source='x \n')
        with patch('src.repair.prompts.render_generation_prompt',return_value='p'*4096):
            r=m.encode_task(t,Tok());self.assertTrue(r['fits']);self.assertEqual(r['target_ids'],[1,99])
        with patch('src.repair.prompts.render_generation_prompt',return_value='p'*4097):
            r=m.encode_task(t,Tok());self.assertFalse(r['fits']);self.assertEqual(len(r['prompt_ids']),4097)


@unittest.skipUnless(importlib.util.find_spec('torch') and importlib.util.find_spec('transformers'),'optional torch/transformers unavailable')
class NumericalTests(unittest.TestCase):
    def test_exact_causal_alignment_against_full_logits_including_eos(self):
        import torch
        import torch.nn.functional as F
        from transformers import Qwen2Config,Qwen2ForCausalLM
        torch.manual_seed(2027)
        model=Qwen2ForCausalLM(Qwen2Config(vocab_size=32,hidden_size=16,intermediate_size=32,
            num_hidden_layers=1,num_attention_heads=2,num_key_value_heads=2,attention_dropout=0.)).eval()
        model.requires_grad_(False)
        for p,t in [([1],[2]),([1,2,3],[4,5,6]),([1,2],[3]*35+[31])]:
            ids=torch.tensor([p+t])
            with torch.inference_mode():
                logits=model(ids,use_cache=False).logits[0,len(p)-1:-1].float()
                expected=-F.cross_entropy(logits,torch.tensor(t),reduction='mean').item()
            actual=m.mean_logprob(model,dict(prompt_ids=p,target_ids=t,fits=True))
            self.assertAlmostEqual(actual,expected,places=5)

    def test_activate_freezes_and_disables_dropout(self):
        import torch
        class Fake(torch.nn.Module):
            def __init__(self):super().__init__();self.weight=torch.nn.Parameter(torch.ones(1))
            def set_adapter(self,role):self.active_adapter=role;self.weight.requires_grad_(True)
        x=Fake()
        for role in ('C','H','C'):
            run.activate(x,role);self.assertEqual(x.active_adapter,role)
            self.assertFalse(x.training);self.assertFalse(x.weight.requires_grad)


class LifecycleTests(unittest.TestCase):
    def test_no_private_read_by_public_input_loader(self):
        pins={str((run.BANK/n).relative_to(run.PROJECT)):'x' for n in run.PUBLIC_FILES}
        with patch.object(run.core,'read_pinned',return_value={}) as read:run.public_inputs(dict(input_sha256=pins))
        self.assertTrue(all('/private-' not in str(c.args[0]) and '/run-v1/vectors' not in str(c.args[0]) for c in read.call_args_list))

    def test_scoped_envelope_and_offline_no_retry_command(self):
        before=run.core.FAMILY,run.core.PHASES,run.core.unit
        with self.assertRaises(RuntimeError):
            with run.configured():
                self.assertEqual(run.core.unit('selection'),run.UNIT_PREFIX+'-selection.service')
                self.assertEqual(run.core.limits('selection'),(64*2**30,1024,'infinity'))
                raise RuntimeError()
        self.assertEqual(before,(run.core.FAMILY,run.core.PHASES,run.core.unit))
        for phase in run.PHASES:
            c=run.command(phase,Path('/snapshot/analysis_protocols/r.json'),'x')
            for v in ('--property=Restart=no','--setenv=HF_HUB_OFFLINE=1','--property=RuntimeMaxSec=21600'):
                self.assertIn(v,c)

    def test_observer_actual_release_progress_and_normal_exit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'outputs'/watch.LIKELIHOOD_FAMILY;(root/'selection-v1').mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            run.core.write_new(root/'STATUS.json',dict(phase='selection',completed_examples=0,total_examples=320))
            run.core.write_new(root/'selection-v1/STATUS.json',dict(phase='likelihood_selection',completed_examples=7,total_examples=320,
                completed_candidates=30,total_candidates=100,elapsed_seconds=60))
            get=lambda:next(r for r in watch.remote_snapshot(Path(d))['experiments'] if r['family']==watch.LIKELIHOOD_FAMILY)
            r=get();self.assertEqual(r['completed_examples'],7);self.assertEqual(r['completed_candidates'],30)
            self.assertEqual(r['release_sha256'],'a'*64)
            run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'likelihood_properties',return_value={'MainPID':'12'}):self.assertEqual(get()['phase'],'normal_exit_pending')
            with patch.object(watch,'likelihood_properties',return_value={'MainPID':'0','Result':'exit-code'}):self.assertEqual(get()['state'],'error')

    def test_abnormal_child_blocks_assessment_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as d,patch.object(run,'FAMILY',Path(d)/'new'),\
            patch.object(run,'verify_sources',return_value=({},'rev')),patch.object(run,'authenticate'),\
            patch.object(run.core,'props',return_value={'LoadState':'not-found','ActiveState':'failed'}),\
            patch.object(run.subprocess,'run') as call:
            with self.assertRaises(ValueError):run.supervise(Path('/snapshot/analysis_protocols/r.json'),'x')
            self.assertEqual(call.call_count,2)
            self.assertTrue((Path(d)/'new/COORDINATOR_FAILED.json').is_file())
            self.assertFalse((Path(d)/'new/assessment-v1').exists())


if __name__=='__main__':unittest.main()
