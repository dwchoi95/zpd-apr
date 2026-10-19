"""Public-only routing, byte-exact reuse, terminal budgets and lifecycle."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import zpd_counterexample_revision as m
from scripts import generate_zpd_counterexample_revision as gen
from scripts import run_zpd_counterexample_revision as run
from scripts import watch_zpd_completion as watch
from tests.test_zpd_public_revision import fixture as base_fixture
from tests.test_zpd_public_revision import GenerationTests as BaseGeneration


def fixture(failed=True):
    values=base_fixture();sample=values[0]['public_samples']['problems'][0]['samples'][0]
    for k,b in [('input','한\r\n'.encode()),('output',b'2\n')]:
        sample[k+'_hex']=b.hex();sample[k+'_sha256']=m.full.sha(b)
    if failed:
        for k in values[2]:values[2][k]=[False]
        for r in values[3]:r['block']['outcomes'][0][1]='WA'
    return values


class TransformTests(unittest.TestCase):
    def test_public_failure_all_original_bytes_and_terminal_identity(self):
        values=fixture();before=deepcopy(values);plan,audit=m.transform(*values)
        self.assertEqual(values,before);self.assertEqual(plan['recipients'],values[0]['recipients'])
        self.assertEqual(plan['prompts'][:1280],values[0]['prompts'])
        for old,new in zip(values[0]['prompts'],plan['prompts'][1280:],strict=True):
            current=m.full._frame(m.full.CURRENT,'print(x)\n');raw=old['messages'][1]['content'].encode()
            self.assertTrue(new['messages'][1]['content'].encode().startswith(raw[:-len(current)]))
            self.assertTrue(new['messages'][1]['content'].encode().endswith(current))
            self.assertIn('"expected_output": "2\\n"',new['messages'][1]['content'])
            self.assertIn('"observed_verdict": "WA"',new['messages'][1]['content'])
            self.assertEqual(new['binding'],old['binding'])
        keep=m.reused_rows(plan,audit,values[1]);self.assertEqual(len(keep),1280)
        self.assertTrue(all(r['draw_index']==0 for r in keep.values()))
        for old,new in zip(values[0]['attempts'],plan['attempts'],strict=True):
            self.assertEqual({k:v for k,v in new.items() if k not in ('prompt_id','prompt_sha256')},
                {k:v for k,v in old.items() if k not in ('prompt_id','prompt_sha256')})

    def test_public_pass_does_not_change_or_resample_any_slot(self):
        values=fixture(False);plan,audit=m.transform(*values)
        self.assertEqual(plan,values[0]);self.assertEqual(m.reused_rows(plan,audit,values[1]),
            {r['attempt_id']:r for r in values[1]})
        self.assertEqual(audit['counts']['H'],{'reuse_independent_draw':320})

    def test_unavailable_and_no_source_are_not_failure_and_private_fields_excluded(self):
        values=list(fixture());values[1][0]['attempt'].update(source=None,status='format_failure')
        values[3][0]['block']['outcomes'][0][1]='AC'
        values[2]={k:None for k in values[2]}
        for r in values[3]:r['block']['private_test']='SECRET_PRIVATE_SENTINEL'
        plan,audit=m.transform(*values)
        self.assertEqual(plan,values[0]);self.assertNotIn('SECRET_PRIVATE_SENTINEL',json.dumps(plan))
        self.assertEqual(audit['rows'][0]['feedback_availability'],'no_source')
        self.assertEqual(audit['rows'][1]['feedback_availability'],'unavailable')

    def test_sample_source_mask_hash_and_block_tamper_rejected(self):
        for kind in ('input','output','mask','outcome','sample_set','source','missing'):
            v=list(fixture())
            if kind in ('input','output'):v[0]['public_samples']['problems'][0]['samples'][0][kind+'_sha256']='bad'
            elif kind=='mask':v[2]={k:[True] for k in v[2]}
            elif kind=='outcome':
                for r in v[3]:r['block']['outcomes'][0][0]='foreign'
            elif kind=='sample_set':v[3][0]['block']['sample_set_sha256']='bad'
            elif kind=='source':v[3][0]['block']['source_sha256']='bad'
            else:v[3].pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):m.transform(*v)

    def test_mixed_branch_uses_original_second_even_if_failed(self):
        v=fixture(False);v[1][1]['attempt'].update(source=None,status='format_failure')
        plan,audit=m.transform(*v);keep=m.reused_rows(plan,audit,v[1])
        self.assertEqual(keep[v[1][1]['attempt_id']],v[1][1])
        bad=deepcopy(v[1]);bad[1]['seed']+=1
        with self.assertRaises(ValueError):m.reused_rows(plan,audit,bad)


class GenerationTests(unittest.TestCase):
    def setup_values(self,root):
        r,i,rendered,report,reused=BaseGeneration().setup_values(root)
        # Preserve 946 independent second rows; 334 new second slots remain.
        for p in [x for x in i['attempts'] if x['draw_index']==1][-946:]:
            first=reused[p['attempt_id'][:-1]+'0'];row=deepcopy(first);row.update(p)
            row['attempt'].update(index=1,seed=p['seed']);reused[p['attempt_id']]=row
        r['public_revision']=dict(existing_slots=2226,planned_new_slots=334)
        return r,i,rendered,report,reused

    def test_only_failed_branch_generated_and_all_reused_rows_byte_exact(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();r,i,rendered,report,reused=self.setup_values(root);before=deepcopy(reused)
            out=root/'out';out.mkdir();calls=[]
            class Model:
                def __init__(self,**kw):assert kw['max_loras']==2 and kw['max_model_len']==8192
                def generate(self,prompts,sampling,*,lora_request,use_tqdm):
                    for text,param,req in zip(prompts,sampling,lora_request,strict=True):
                        assert param.seed==101 and param.max_tokens==4096 and param.n==1
                        assert req.path==r['adapter_'+gen.ADAPTER_ARM_MAP[text.split('-')[-1]]]
                        calls.append(text)
                    return [SimpleNamespace(outputs=[SimpleNamespace(text='print(1)',finish_reason='stop')]) for _ in prompts]
            v=ModuleType('vllm');v.LLM=Model;v.SamplingParams=lambda **kw:SimpleNamespace(**kw)
            req=ModuleType('vllm.lora.request');req.LoRARequest=lambda name,index,path:SimpleNamespace(path=path)
            with patch.dict(sys.modules,{'vllm':v,'vllm.lora':ModuleType('vllm.lora'),'vllm.lora.request':req}),\
                 patch.object(gen.core,'render_inputs',return_value=(rendered,report)),patch.object(gen.core,'envelope'):
                gen.generation(i,r,out,reused)
            rows=json.loads((out/'attempts.json').read_text());status=json.loads((out/'STATUS.json').read_text())
            self.assertEqual(len(calls),333);self.assertEqual(len(rows),2560);self.assertEqual(reused,before)
            self.assertEqual({x['attempt_id']:x for x in rows if x['attempt_id'] in reused},before)
            self.assertEqual(status['completed_new_second_slots'],334);self.assertEqual(status['reused_slots'],2226)
            self.assertEqual(status['completed_examples'],320)
            self.assertEqual(sum(x['attempt']['status']=='resource_failure' for x in rows),1)

    def test_missing_first_slot_role_seed_or_token_drift_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();r,i,rendered,report,reused=self.setup_values(root)
            for kind in ('count','seed','role','index'):
                bad=deepcopy(reused);row=bad[next(iter(bad))]
                if kind=='count':bad.pop(next(iter(bad)))
                elif kind=='seed':row['attempt']['seed']+=1
                elif kind=='index':row['attempt']['index']=1
                else:row['adapter_role']='H'
                with self.subTest(kind=kind),self.assertRaises(ValueError):gen.require_reused(i,r,bad)
            out=root/'out';out.mkdir();r['tokenization_sha256']='wrong'
            with patch.object(gen.core,'render_inputs',return_value=(rendered,report)),self.assertRaisesRegex(ValueError,'tokenization'):
                gen.generation(i,r,out,reused)


class LifecycleTests(unittest.TestCase):
    def test_exact_contract_only_and_no_source_or_gate_change(self):
        old=dict(seed=2027,inputs_sha256='frozen',development_gate={'frozen':True},source_sha256={'old.py':'a'},
            family_path='old',layout_variant='old',recovery={})
        new=deepcopy(old);new.pop('recovery');new.update(family_path=str(run.FAMILY),layout_variant=run.VARIANT,
            public_revision=run.contract());new['source_sha256'].update({p:'pin' for p in run.REQUIRED})
        run.validate_release(new,old,old)
        for k in ('seed','inputs_sha256','development_gate'):
            bad=deepcopy(new);bad[k]='changed'
            with self.assertRaises(ValueError):run.validate_release(bad,old,old)
        bad=deepcopy(new);bad['source_sha256']['old.py']='changed'
        with self.assertRaises(ValueError):run.validate_release(bad,old,old)
        for k in ('private_feedback_used','gate_changed','model_promotion','fitting','all_public_pass_still_revised'):
            bad=deepcopy(new);bad['public_revision'][k]=True
            with self.assertRaises(ValueError):run.validate_release(bad,old,old)

    def test_scoped_commands_restored_after_failure(self):
        before=(run.core.FAMILY,run.core.inputs_for,run.core.generation,run.driver.source_barrier,run.driver.command)
        with self.assertRaises(RuntimeError):
            with run.configured():
                for phase in run.PHASES:
                    cmd=run.command(phase,Path('/snapshot/release'),'sha',Path('/snapshot'))
                    for s in ('scripts.run_zpd_counterexample_revision','--property=Restart=no',
                        '--unit='+run.UNIT_PREFIX+'-'+phase+'.service','--setenv=TMPDIR='+str(run.RPC_BASE)):
                        self.assertIn(s,cmd)
                raise RuntimeError()
        self.assertEqual(before,(run.core.FAMILY,run.core.inputs_for,run.core.generation,run.driver.source_barrier,run.driver.command))

    def test_generation_transform_reads_public_files_only(self):
        v=fixture();reads=[]
        def read(path,pin):
            reads.append(str(path));return dict(zip(run.ORIGIN_PINS,v[1:]))[str(path.relative_to(run.ORIGIN))]
        with patch.object(run,'BASE_INPUTS',return_value=v[0]),patch.object(run.core,'read_pinned',side_effect=read):
            plan,_=run.public_inputs({})
        self.assertTrue(all('private' not in n for n in reads));self.assertEqual(len(plan['attempts']),2560)

    def test_observer_awaits_actual_exit_and_correct_release(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d);root=project/'outputs'/watch.COUNTEREXAMPLE_FAMILY;(root/'public-v1').mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            run.core.write_new(root/'STATUS.json',dict(phase='public',completed_phases=['generation']))
            run.core.write_new(root/'public-v1/STATUS.json',dict(completed_examples=15,total_examples=320))
            get=lambda:next(r for r in watch.remote_snapshot(project)['experiments'] if r['family']==watch.COUNTEREXAMPLE_FAMILY)
            row=get();self.assertEqual(row['completed_examples'],15);self.assertEqual(row['unit_prefix'],run.UNIT_PREFIX)
            run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'counterexample_properties',return_value={'MainPID':'12'}):self.assertEqual(get()['state'],'running')
            with patch.object(watch,'counterexample_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(get()['state'],'error')


if __name__=='__main__':unittest.main()
