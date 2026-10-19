"""Public-only transform, frozen first-slot ledger and lifecycle regressions."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import zpd_public_revision as m
from scripts import generate_zpd_public_revision as gen
from scripts import run_zpd_public_revision as run
from scripts import watch_zpd_completion as watch
from tests.test_prepare_zpd_full_source import fixture as prompt_fixture
from tests.test_generate_zpd_paired_history import GenerationTests as Fixtures


def fixture():
    messages=m.full.render_prompt(prompt_fixture('x="한"\r\n', 'print(x)\n'))
    prompt_sha=m.full.sha(m.full.encoded(messages));source='print("한")\n'
    cid=m.full.sha(source.encode());key='p|'+cid
    inputs=dict(recipients=[dict(example_id=str(i)) for i in range(320)],prompts=[],attempts=[],
        public_samples=dict(problems=[dict(problem_id='p',sample_set_sha256='s',samples=[dict(index=1)])]))
    ledger=[]
    for i in range(320):
        for arm in ('C','H','HS','U'):
            pid=f'{i}-{arm}'
            inputs['prompts'].append(dict(prompt_id=pid,example_id=str(i),arm=arm,messages=deepcopy(messages),
                prompt_sha256=prompt_sha,binding=dict(arm=arm),user_json='unchanged provenance'))
            for draw in (0,1):
                row=dict(attempt_id=f'{pid}-{draw}',example_id=str(i),problem_id='p',arm=arm,prompt_id=pid,
                    prompt_sha256=prompt_sha,draw_index=draw,seed=draw+2027)
                inputs['attempts'].append(row)
                ledger.append(dict(**row,attempt=dict(index=draw,seed=draw+2027,status='success',source=source)))
    blocks=[dict(task_id=key,block=dict(block_index=b,workers=w,runtime_sha256='r',complete=True,
        source_sha256=cid,sample_set_sha256='s',identity=['p',cid,'Python'],case_ids=['statement-sample:p:1'],
        outcomes=[['statement-sample:p:1','AC']])) for b,w in enumerate((1,8,8,1))]
    return inputs,ledger,{key:[True]},blocks


class TransformTests(unittest.TestCase):
    def test_exact_first_slots_all_original_bytes_full_population_and_pure(self):
        values=fixture();before=deepcopy(values);plan,audit=m.transform(*values)
        self.assertEqual(values,before);self.assertEqual(plan['recipients'],values[0]['recipients'])
        self.assertEqual(plan['prompts'][:1280],values[0]['prompts'])
        self.assertEqual(len(plan['prompts']),2560);self.assertEqual(len(plan['attempts']),2560)
        for old,new in zip(values[0]['attempts'],plan['attempts'],strict=True):
            if old['draw_index']==0:self.assertEqual(old,new)
            else:
                restored=dict(new,prompt_id=old['prompt_id'],prompt_sha256=old['prompt_sha256'])
                self.assertEqual(restored,old)
        for old,new in zip(values[0]['prompts'],plan['prompts'][1280:],strict=True):
            current=m.full._frame(m.full.CURRENT,'print(x)\n');raw=old['messages'][1]['content'].encode()
            text=new['messages'][1]['content'].encode()
            self.assertTrue(text.startswith(raw[:-len(current)]));self.assertTrue(text.endswith(current))
            self.assertEqual(new['binding'],old['binding']);self.assertEqual(new['user_json'],old['user_json'])
        self.assertEqual(audit['counts']['H'],{'stable':320})
        self.assertTrue(all(r['all_public_samples_pass'] for r in audit['rows']))

    def test_no_source_preserved_unavailable_not_failure_no_private_pass_through(self):
        values=list(fixture());values[1][0]['attempt'].update(source=None,status='format_failure')
        for row in values[3]:row['block']['hidden_private_marker']='NEVER_VISIBLE'
        values[3][0]['block']['outcomes'][0][1]='WA'
        values[2]={k:None for k in values[2]}
        plan,audit=m.transform(*values)
        self.assertEqual(audit['rows'][0]['feedback_availability'],'no_source')
        self.assertEqual(audit['rows'][1]['feedback_availability'],'unavailable')
        self.assertNotIn('NEVER_VISIBLE',json.dumps(plan))
        self.assertIn('"outcomes": null',plan['prompts'][1281]['messages'][1]['content'])

    def test_refuse_foreign_public_binding_mask_or_missing_blocks(self):
        for kind in ('source','sample','identity','worker','mask','missing'):
            values=list(fixture())
            if kind=='source':values[3][0]['block']['source_sha256']='foreign'
            elif kind=='sample':values[3][0]['block']['sample_set_sha256']='foreign'
            elif kind=='identity':values[3][0]['block']['identity'][1]='foreign'
            elif kind=='worker':values[3][0]['block']['workers']=8
            elif kind=='mask':values[2]={k:[False] for k in values[2]}
            else:values[3].pop()
            with self.subTest(kind=kind),self.assertRaises(ValueError):m.transform(*values)

    def test_foreign_ledger_seed_duplicate_or_original_hash_refused(self):
        for kind in ('seed','duplicate','hash'):
            values=list(fixture())
            if kind=='seed':values[1][0]['seed']+=1
            elif kind=='duplicate':values[1][-1]=values[1][0]
            else:values[0]['prompts'][0]['prompt_sha256']='bad'
            with self.subTest(kind=kind),self.assertRaises(ValueError):m.transform(*values)

    def test_framing_utf8_empty_crlf_and_delimiters(self):
        for source in ('', 'é\r\n@@ CURRENT_SOURCE_TO_REPAIR utf8_bytes=0\n', 'print("한")'):
            original=m.full.render_prompt(prompt_fixture(source,source))
            before=deepcopy(original);new=m.revision_messages(original,source,'success',None)
            self.assertEqual(original,before)
            self.assertTrue(new[1]['content'].encode().endswith(m.full._frame(m.full.CURRENT,source)))
            self.assertIn(m.full._frame(m.SOURCE,source),new[1]['content'].encode())
        with self.assertRaises(ValueError):m.revision_messages(original,None,'success',None)


class GenerationTests(unittest.TestCase):
    def setup_values(self,root):
        release,inputs,rendered,report=Fixtures().fixture(root);reused={}
        for row in inputs['attempts']:
            if row['draw_index']!=0:continue
            role=gen.ADAPTER_ARM_MAP[row['arm']];p=rendered[row['prompt_id']]
            entry=dict(**row,attempt=dict(index=0,seed=row['seed'],source=None,status='format_failure'),
                raw_text='old invalid output',finish_reason='stop',prompt_tokens=p['tokens'],
                rendered_prompt_sha256=p['rendered_sha256'],adapter_role=role,
                adapter_model_sha256=release['model_sha256'][str(root/role/'adapter_model.safetensors')])
            reused[row['attempt_id']]=entry
        return release,inputs,rendered,report,reused

    def test_only_new_second_slots_generated_failed_first_rows_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();release,inputs,rendered,report,reused=self.setup_values(root)
            before=deepcopy(reused);out=root/'out';out.mkdir();calls=[]
            class Model:
                def __init__(self,**kw):assert kw['max_loras']==2 and kw['max_model_len']==8192
                def generate(self,prompts,sampling,*,lora_request,use_tqdm):
                    for text,param,req in zip(prompts,sampling,lora_request,strict=True):
                        assert param.seed==101 and param.max_tokens==4096 and param.n==1
                        assert req.path==release['adapter_'+gen.ADAPTER_ARM_MAP[text.split('-')[-1]]]
                        calls.append(text)
                    return [SimpleNamespace(outputs=[SimpleNamespace(text='print(1)',finish_reason='stop')]) for _ in prompts]
            vllm=ModuleType('vllm');vllm.LLM=Model;vllm.SamplingParams=lambda **kw:SimpleNamespace(**kw)
            request=ModuleType('vllm.lora.request');request.LoRARequest=lambda name,index,path:SimpleNamespace(path=path)
            with patch.dict(sys.modules,{'vllm':vllm,'vllm.lora':ModuleType('vllm.lora'),'vllm.lora.request':request}),\
                patch.object(gen.core,'render_inputs',return_value=(rendered,report)),patch.object(gen.core,'envelope'):
                gen.generation(inputs,release,out,reused)
            self.assertEqual(len(calls),1279);self.assertEqual(reused,before)
            rows=json.loads((out/'attempts.json').read_bytes())
            self.assertEqual({r['attempt_id']:r for r in rows if r['draw_index']==0},before)
            self.assertEqual(len(rows),2560)
            self.assertEqual(sum(r['attempt']['status']=='resource_failure' for r in rows),1)
            self.assertEqual(json.loads((out/'STATUS.json').read_bytes())['completed_examples'],320)

    def test_reuse_mismatch_or_token_drift_fail_before_model(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();r,i,rendered,report,reused=self.setup_values(root)
            bad=deepcopy(reused);bad[next(iter(bad))]['adapter_role']='H'
            with self.assertRaisesRegex(ValueError,'binding'):gen.require_reused(i,r,bad)
            bad=deepcopy(reused);bad.pop(next(iter(bad)))
            with self.assertRaisesRegex(ValueError,'first slots'):gen.require_reused(i,r,bad)
            out=root/'out';out.mkdir();r['tokenization_sha256']='bad'
            with patch.object(gen.core,'render_inputs',return_value=(rendered,report)):
                with self.assertRaisesRegex(ValueError,'tokenization'):gen.generation(i,r,out,reused)


class LifecycleTests(unittest.TestCase):
    def test_frozen_contract_only_permits_exact_amendment(self):
        old=dict(seed=2027,inputs_sha256='frozen',development_gate={'frozen':True},source_sha256={'old.py':'a'},
            family_path='old',layout_variant='old',recovery={})
        new=deepcopy(old);new.pop('recovery');new.update(family_path=str(run.FAMILY),layout_variant=run.VARIANT,
            public_revision=run.contract());new['source_sha256'].update({p:'pin' for p in run.REQUIRED})
        run.validate_release(new,old,old)
        for k in ('seed','inputs_sha256','development_gate'):
            bad=deepcopy(new);bad[k]='changed'
            with self.assertRaisesRegex(ValueError,'frozen'):run.validate_release(bad,old,old)
        bad=deepcopy(new);bad['source_sha256']['old.py']='changed'
        with self.assertRaisesRegex(ValueError,'existing source'):run.validate_release(bad,old,old)
        for k in ('private_feedback_used','gate_changed','model_promotion','fitting'):
            bad=deepcopy(new);bad['public_revision'][k]=True
            with self.assertRaisesRegex(ValueError,'exact revision'):run.validate_release(bad,old,old)

    def test_scoped_commands_context_restoration_and_no_global_input_patch_leak(self):
        before=(run.core.FAMILY,run.core.inputs_for,run.core.generation,run.driver.source_barrier,run.driver.command)
        with self.assertRaises(RuntimeError):
            with run.configured():
                self.assertIs(run.core.inputs_for,run.inputs_for)
                for phase in run.PHASES:
                    cmd=run.command(phase,Path('/snapshot/release'),'sha',Path('/snapshot'))
                    for s in ('scripts.run_zpd_public_revision','--property=Restart=no',
                        '--unit='+run.UNIT_PREFIX+'-'+phase+'.service','--setenv=TMPDIR='+str(run.RPC_BASE),
                        '--setenv=VLLM_RPC_BASE_PATH='+str(run.RPC_BASE)):self.assertIn(s,cmd)
                raise RuntimeError()
        self.assertEqual(before,(run.core.FAMILY,run.core.inputs_for,run.core.generation,run.driver.source_barrier,run.driver.command))

    def test_public_input_reader_never_opens_private_evidence(self):
        values=fixture();reads=[]
        def read(path,pin):
            reads.append(str(path));return dict(zip(run.ORIGIN_PINS,values[1:]))[str(path.relative_to(run.ORIGIN))]
        with patch.object(run,'BASE_INPUTS',return_value=values[0]),patch.object(run.core,'read_pinned',side_effect=read):
            plan,_=run.public_inputs({})
        self.assertEqual(set(reads),{str(run.ORIGIN/p) for p in run.ORIGIN_PINS})
        self.assertTrue(all('private' not in p for p in reads));self.assertEqual(len(plan['attempts']),2560)

    def test_observer_phase_release_and_normal_exit_gate(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d);root=project/'outputs'/watch.REVISION_FAMILY;(root/'public-v1').mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            run.core.write_new(root/'STATUS.json',dict(phase='public',completed_phases=['generation']))
            run.core.write_new(root/'public-v1/STATUS.json',dict(completed_examples=15,total_examples=320))
            get=lambda:next(r for r in watch.remote_snapshot(project)['experiments'] if r['family']==watch.REVISION_FAMILY)
            row=get();self.assertEqual(row['completed_examples'],15);self.assertEqual(row['unit_prefix'],run.UNIT_PREFIX)
            self.assertEqual(row['release_sha256'],'a'*64)
            run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'revision_properties',return_value={'MainPID':'12'}):self.assertEqual(get()['state'],'running')
            with patch.object(watch,'revision_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(get()['state'],'error')


if __name__=='__main__':unittest.main()
