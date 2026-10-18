from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import run_zpd_splice_training as m
from scripts import watch_zpd_completion as watch
from tests.test_zpd_splice_pilot import record
from tests.test_zpd_edit_balanced import LifecycleTests as BalancedLifecycleTests


def fixture():
    r=record(history=True)
    prompt=dict(prompt_id='p',example_id='e',arm='H',messages=r['messages'],
        prompt_sha256=m.full.sha(m.full.encoded(r['messages'])),
        binding=dict(current_source_sha256=m.full.sha(r['current_code'].encode())),user_json='unaltered',seeds=[1,2])
    return dict(prompts=[prompt],attempts=[dict(prompt_id='p',prompt_sha256=prompt['prompt_sha256'],seed=1,draw_index=0)],
                recipients=[dict(example_id='e',current_source=r['current_code'])],extra={'keep':True})


class ContractTests(unittest.TestCase):
    def test_collected_child_requires_certified_normal_exit_and_absent_group(self):
        unit=m.pilot.UNIT_PREFIX+'-materialize.service'
        path='/user.slice/user-1000.slice/'+unit
        normal=dict(Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0',SubState='exited')
        cert=dict(release_sha256=m.PILOT_RELEASE,cleanup_verified=True,cgroup_removed=True,
            returned_control_group='',recorded_control_group=path,exit=normal)
        props=dict(LoadState='not-found',ActiveState='inactive',SubState='dead',MainPID='0',ControlGroup='')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            m.verify_released_child(props,cert,unit,root)
            m.verify_released_child(dict(normal,LoadState='loaded',ControlGroup=''),cert,unit,root)
            for field,value in [('MainPID','42'),('ControlGroup',path),('ActiveState','active'),('SubState','running')]:
                with self.assertRaises(ValueError):m.verify_released_child(dict(props,**{field:value}),cert,unit,root)
            for field,value in [('release_sha256','foreign'),('cleanup_verified',False),('cgroup_removed',False),
                ('returned_control_group',path),('recorded_control_group','/user.slice/../'+unit),
                ('recorded_control_group','/user.slice/foreign.service'),('exit',dict(normal,ExecMainStatus='1'))]:
                with self.assertRaises(ValueError):m.verify_released_child(props,dict(cert,**{field:value}),unit,root)
            with self.assertRaises(ValueError):
                m.verify_released_child(dict(props,LoadState='loaded'),cert,unit,root)
            (root/path.lstrip('/')).mkdir(parents=True)
            with self.assertRaises(ValueError):m.verify_released_child(props,cert,unit,root)

    def test_observer_completed_pilot_population_schema(self):
        row=dict(family=watch.SPLICE_TRAINING_FAMILY,state='complete',total_examples=320,
            completed_at='2026-10-18T18:00:00+09:00',results={a:dict(stable_ac=1) for a in m.core.ARMS},
            training_population=dict(train=dict(examples=19199)))
        self.assertIn('동일 학습 19199예제',watch.korean_report(dict(experiments=[row])))

    def test_transform_only_system_and_bound_hashes_no_mutation(self):
        old=fixture();before=deepcopy(old);new=m.transform_inputs(old)
        self.assertEqual(old,before)
        reset=deepcopy(new)
        reset['prompts'][0]['messages']=old['prompts'][0]['messages']
        reset['prompts'][0]['prompt_sha256']=old['prompts'][0]['prompt_sha256']
        reset['attempts'][0]['prompt_sha256']=old['attempts'][0]['prompt_sha256']
        self.assertEqual(reset,old)
        self.assertEqual(new['prompts'][0]['messages'][0]['content'],m.codec.SYSTEM)
        self.assertEqual(new['attempts'][0]['prompt_sha256'],new['prompts'][0]['prompt_sha256'])

    def test_foreign_source_or_prompt_refused(self):
        for field in ('source','hash'):
            r=fixture()
            if field=='source':r['prompts'][0]['binding']['current_source_sha256']='wrong'
            else:r['prompts'][0]['prompt_sha256']='wrong'
            with self.assertRaises(ValueError):m.transform_inputs(r)

    def test_terminal_statuses_no_partial_source_or_retry(self):
        row=dict(draw_index=0,seed=2027)
        for text,reason,status in [('[]','stop','success'),('[[0,1,"print(1)\\n"]]','stop','success'),
            ('[]','length','resource_failure'),('[]',None,'unknown_failure'),('```json\n[]\n```','stop','format_failure'),
            ('[[9,10,"x"]]','stop','format_failure'),('[[true,1,"x"]]','stop','format_failure'),
            ('[[0,1,""]]','stop','format_failure'),('[[0,1,"\\ud800"]]','stop','format_failure')]:
            result=m.terminal(row,text,reason,'print(0)\n')
            self.assertEqual(result['status'],status)
            if status!='success':self.assertIsNone(result['source'])
        self.assertEqual(m.terminal(row,'[]','stop','print(0)\r\n')['source'],'print(0)\r\n')

    def test_generation_callback_binds_original_current_and_rejects_foreign(self):
        inputs=m.transform_inputs(fixture())
        with patch.object(m.generator,'generation') as run:
            m.generation(inputs,{},Path('/output'))
            callback=run.call_args.kwargs['terminalize']
            result=callback(dict(example_id='e',draw_index=1,seed=10),'[]','stop')
            self.assertEqual(result['source'],inputs['recipients'][0]['current_source'])
        inputs['recipients'][0]['current_source']='foreign'
        with self.assertRaises(ValueError):m.generation(inputs,{},Path('/output'))

    def test_scoped_config_and_ipc_command_restore(self):
        old=m.parent.FAMILY,m.core.inputs_for,m.parent.configured_core
        with m.configured():
            cmd=m.command('generation',Path('/r'),'pin',Path('/snapshot'))
            self.assertIn('scripts.run_zpd_splice_training',cmd)
            self.assertIn('--setenv=VLLM_RPC_BASE_PATH='+str(m.RPC_BASE),cmd)
            self.assertEqual(m.parent.PHASES,m.PHASES)
            self.assertEqual(m.core.inputs_for,m.inputs_for)
            with m.configured_core():self.assertEqual(m.core.generation,m.generation)
        self.assertEqual(old,(m.parent.FAMILY,m.core.inputs_for,m.parent.configured_core))

    def test_only_declared_amendment_and_optin_source_change_allowed(self):
        previous=dict(scientific='same',tokenization_sha256='old',source_sha256={})
        r=deepcopy(previous);r.update(splice_intervention=m.amendment(),tokenization_sha256='new',
            source_sha256={**{n:'pin' for n in m.REQUIRED},'src/runner/python_runner.py':'old'})
        prior=dict(source_sha256={'src/runner/python_runner.py':'old'})
        m.validate_amendment(r,previous,prior)
        for mode in ('scientific','source','amendment'):
            bad=deepcopy(r)
            if mode=='scientific':bad['scientific']='changed'
            elif mode=='source':bad['source_sha256']['src/runner/python_runner.py']='changed'
            else:bad['splice_intervention']['capacity_probe_repeated']=True
            with self.assertRaises(ValueError):m.validate_amendment(bad,previous,prior)

    def test_reuse_does_not_probe_or_fit(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);source=p/'pilot';source.mkdir();(source/'capacity-v1/probe').mkdir(parents=True)
            cap=source/'capacity-v1/probe/capacity_report.json';cap.write_text('{"status":"passed"}')
            out=p/'out';out.mkdir()
            with patch.object(m,'verify_pilot'),patch.object(m.pilot,'ROOT',source),\
                patch.object(m,'CAPACITY_SHA',m.core.sha_file(cap)),patch.object(m,'BASE_EARLY') as base:
                m.run_early_phase('capacity',{},out,None,'pin');base.assert_not_called()
            self.assertEqual((out/'probe/capacity_report.json').read_bytes(),cap.read_bytes())
            self.assertFalse(json.loads((out/'reuse.json').read_bytes())['probe_repeated'])

    def test_training_observer_is_examples_and_release_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'outputs'/watch.SPLICE_TRAINING_FAMILY;(root/'train-C-v1/training').mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='r'))
            m.core.write_new(root/'STATUS.json',dict(phase='train-C'))
            m.core.write_new(root/'train-C-v1/training/STATUS.json',dict(phase='training',completed_examples=32,total_examples=19199,elapsed_seconds=20))
            getrow=lambda:next(r for r in watch.remote_snapshot(Path(temp))['experiments'] if r['family']==watch.SPLICE_TRAINING_FAMILY)
            row=getrow();self.assertEqual(row['release_sha256'],'r');self.assertEqual(row['completed_examples'],32)
            self.assertEqual(row['total_examples'],19199)
            m.core.write_new(root/'VERIFIED_COMPLETE.json',{})
            with patch.object(watch,'splice_training_properties',return_value={'MainPID':'1'}):
                self.assertEqual(getrow()['state'],'running')
            with patch.object(watch,'splice_training_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(getrow()['state'],'error')


class LifecycleTests(unittest.TestCase):
    def test_same_seven_stage_success_and_failure_barriers(self):
        # Reuse the synthetic seven-stage harness with this wrapper, not the balanced method.
        with patch('tests.test_zpd_edit_balanced.m',m):
            BalancedLifecycleTests('test_seven_stage_success_and_failed_child_blocks_successor').test_seven_stage_success_and_failed_child_blocks_successor()


class GeneratorIntegrationTests(unittest.TestCase):
    def test_shared_default_and_splice_callback_each_complete_all_slots(self):
        attempts=[dict(example_id=str(e),prompt_id=f'{e}-{a}',arm=a,draw_index=d,seed=e*8+i*2+d,
            attempt_id=f'{e}-{a}-{d}') for e in range(320) for i,a in enumerate(m.core.ARMS) for d in (0,1)]
        rendered={r['prompt_id']:dict(text='prompt',fits=True,tokens=1,rendered_sha256='p') for r in attempts}
        paths={a:Path('/'+a) for a in ('C','H')}
        release=dict(gpu_versions={},model_sha256={str(p/'adapter_model.safetensors'):'pin' for p in paths.values()},
            base_model='/base',tokenization_sha256=m.core.sha(m.core.encoded({})))
        def generate(prompts,*args,**kwargs):
            return [SimpleNamespace(outputs=[SimpleNamespace(text='[]',finish_reason='stop')]) for _ in prompts]
        fake=SimpleNamespace(LLM=lambda **k:SimpleNamespace(generate=generate),SamplingParams=lambda **k:k)
        modules={'vllm':fake,'vllm.lora':SimpleNamespace(),
                 'vllm.lora.request':SimpleNamespace(LoRARequest=lambda *args:args)}
        for custom in (False,True):
            saved={};calls=[]
            def callback(row,text,reason):
                calls.append(row['attempt_id']);return m.terminal(row,text,reason,'print(1)\n')
            with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
                stack.enter_context(patch.dict(sys.modules,modules))
                stack.enter_context(patch.object(m.generator,'adapter_roles',return_value=paths))
                stack.enter_context(patch.object(m.core,'render_inputs',return_value=(rendered,{})))
                stack.enter_context(patch.object(m.core,'sha_file',return_value='pin'))
                stack.enter_context(patch.object(m.core,'envelope'))
                stack.enter_context(patch.object(m.core,'status_write'))
                stack.enter_context(patch.object(m.core,'write_new',side_effect=lambda p,v:saved.update({p.name:v})))
                m.generator.generation(dict(attempts=attempts),release,Path(temp),terminalize=callback if custom else None)
            self.assertEqual(len(saved['attempts.json']),2560)
            self.assertEqual(len(calls),2560 if custom else 0)
            for row in saved['attempts.json']:
                self.assertEqual(row['raw_text'],'[]')
                self.assertEqual(row['attempt']['source'],'print(1)\n' if custom else '[]')
                self.assertEqual(row['adapter_role'],'C' if row['arm']=='C' else 'H')


if __name__=='__main__':unittest.main()
