"""Synthetic objective, unchanged-input and scoped-lifecycle regressions."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import train_zpd_paired_history as training
from scripts import zpd_edit_balanced_objective as loss
from scripts import run_zpd_edit_balanced as m
from scripts import watch_zpd_completion as watch
from tests.test_train_zpd_paired_history import Tokenizer, record


class ObjectiveTests(unittest.TestCase):
    def test_edit_copy_equal_mass_total_mass_and_eos(self):
        for n in (2, 10, 4095):
            for edited in ([0], list(range(n-1))):
                w = loss.target_weights(n, edited)
                self.assertAlmostEqual(sum(w), n+1)
                self.assertAlmostEqual(sum(w[i] for i in edited), n/2)
                self.assertAlmostEqual(sum(w[i] for i in range(n) if i not in edited), n/2)
                self.assertEqual(w[-1], 1.0)

    def test_no_edit_all_edit_empty_are_uniform(self):
        self.assertEqual(loss.target_weights(0, []), [1.0])
        self.assertEqual(loss.target_weights(3, []), [1.0]*4)
        self.assertEqual(loss.target_weights(3, [0,1,2]), [1.0]*4)

    def test_alignment_insert_replace_delete_boundaries_and_equal(self):
        for current, target, expected in [([1,2],[1,3,2],[1]), ([1,2],[1,3],[1]),
            ([0,1,2],[1,2],[0]), ([1,2,3],[1,2],[1]), ([1,0,2],[1,2],[1]),
            ([1,2],[1,2],[]), ([1],[],[]), ([],[1,2],[0,1])]:
            self.assertEqual(loss.edit_indices(current,target), expected)

    def test_invalid_alignment_refused(self):
        for changed in ([-1], [3], [1,1], [2,0], [True], '0'):
            with self.assertRaises(ValueError): loss.target_weights(3, changed)

    def test_objective_only_change_same_pair_tokens_roster_and_weights(self):
        c=[record()]; h=[record(prompt='history current')]
        plain=training.paired_preflight(c,h,Tokenizer())
        balanced=loss.paired_preflight(c,h,Tokenizer())
        training.validate_preflight(balanced)
        for key in ('example_ids','order_sha256','caps','records_sha256','target_contract'):
            self.assertEqual(plain['report'][key],balanced['report'][key])
        weights=[]
        for arm in ('C','H'):
            for key in ('input_ids','labels','attention_mask','example_id'):
                self.assertEqual(plain['encoded'][arm][0][key],balanced['encoded'][arm][0][key])
            n=balanced['report']['per_example'][0]['arms'][arm]['prompt_tokens']
            w=balanced['encoded'][arm][0]['loss_weights']
            self.assertEqual(w[:n],[0.0]*n); weights.append(w[n:])
        self.assertEqual(*weights)

    def test_resealed_weight_or_contract_tamper_rejected(self):
        for kind in ('weight','objective','indices','pin'):
            p=loss.paired_preflight([record()],[record()],Tokenizer())
            if kind=='weight':
                p['encoded']['H'][0]['loss_weights'][-1]=2.0
                p['report']['encoded_sha256']['H']=training.sha(training.encoded(p['encoded']['H']))
            elif kind=='objective':p['report']['objective']['code_edit_mass']=0.9
            elif kind=='indices':p['report']['per_example'][0]['edit_indices']=[9999]
            else:p['report']['per_example'][0]['target_loss_weights_sha256']='0'*64
            with self.subTest(kind=kind),self.assertRaises(ValueError):training.validate_preflight(p)

    def test_mixed_train_valid_objectives_rejected_before_model(self):
        p=loss.paired_preflight([record()],[record()],Tokenizer())
        v=training.paired_preflight([record('valid')],[record('valid')],Tokenizer())
        with patch.object(training,'load_fresh_model') as load:
            with self.assertRaisesRegex(ValueError,'objectives differ'):
                training.train_arm('C',p,v,base_model='/never',output_dir='/never')
            load.assert_not_called()


class LifecycleTests(unittest.TestCase):
    def test_seven_stage_success_and_failed_child_blocks_successor(self):
        for fail in (None, 'train-H'):
            with tempfile.TemporaryDirectory() as tmp, m.configured(), ExitStack() as stack:
                family=Path(tmp).resolve()/'family';launched=[];certified=[]
                stack.enter_context(patch.object(m.parent,'FAMILY',family))
                stack.enter_context(patch.object(m.parent,'source_barrier',return_value=('revision',{})))
                stack.enter_context(patch.object(m.parent,'validate_phase_result'))
                def props(name):
                    phase=next(p for p in m.PHASES if m.parent.unit(p)==name)
                    if phase not in launched:return {'LoadState':'not-found'}
                    return dict(Result='success' if phase!=fail else 'exit-code',ExecMainCode='1',
                        ExecMainStatus='0' if phase!=fail else '1',MainPID='0',SubState='exited',ControlGroup='')
                def run(cmd,**kwargs):
                    if cmd[0]=='/usr/bin/systemctl':return
                    phase=cmd[cmd.index('--phase')+1]
                    self.assertEqual(certified,list(m.PHASES[:m.PHASES.index(phase)]));launched.append(phase)
                    root=family/(phase+'-v1');root.mkdir()
                    digest='dynamic' if phase in m.parent.INFERENCE else 'parent'
                    m.core.write_new(root/'stage-manifest.json',dict(revision='revision',release_sha256=digest,
                        phase=phase,envelope={'cgroup':'/fixture'}))
                    m.core.seal_stage(root,phase,digest)
                def cleanup(values,recorded,name):
                    certified.append(next(p for p in m.PHASES if m.parent.unit(p)==name))
                    return dict(cleanup_verified=True)
                def inference(*args,create=False):
                    if create:self.assertEqual(certified,list(m.PHASES[:4]))
                    return family/'inference-release.json','dynamic'
                stack.enter_context(patch.object(m.core,'props',side_effect=props))
                stack.enter_context(patch.object(m.parent.subprocess,'run',side_effect=run))
                stack.enter_context(patch.object(m.parent,'terminal_group',side_effect=cleanup))
                stack.enter_context(patch.object(m.parent,'inference_release',side_effect=inference))
                stack.enter_context(patch.object(m.parent,'_inference_pin',return_value=(Path('/dynamic'),'dynamic')))
                finish=stack.enter_context(patch.object(m.parent,'finalize',return_value={'complete':True}))
                if fail is None:
                    self.assertEqual(m.parent.supervise(Path('/release'),'parent'),{'complete':True})
                    self.assertEqual(certified,list(m.PHASES));finish.assert_called_once()
                else:
                    with self.assertRaisesRegex(ValueError,'did not exit normally'):
                        m.parent.supervise(Path('/release'),'parent')
                    self.assertEqual(launched,list(m.PHASES[:4]));finish.assert_not_called()
                    self.assertFalse((family/'train-H-VERIFIED_COMPLETE.json').exists())
                    self.assertTrue((family/'COORDINATOR_FAILED.json').exists())

    def test_scoped_binding_restores_even_on_error(self):
        before=dict(vars(m.parent))
        with self.assertRaises(RuntimeError):
            with m.configured():
                self.assertEqual(m.parent.FAMILY,m.FAMILY)
                self.assertEqual(m.parent.PHASES,('materialize','capacity','train-C','train-H','generation','public','private'))
                self.assertIs(m.parent._paired,m.paired)
                raise RuntimeError()
        self.assertEqual({k for k,v in vars(m.parent).items() if before.get(k) is not v},set())

    def test_command_fixed_limits_short_ipc_and_no_cache(self):
        with m.configured():
            for phase in m.PHASES:
                cmd=m.command(phase,Path('/snapshot/release.json'),'a'*64,Path('/snapshot'))
                self.assertEqual(cmd[cmd.index('-m')+1],'scripts.run_zpd_edit_balanced')
                self.assertIn('--property=Restart=no',cmd)
                self.assertIn('--unit='+m.UNIT_PREFIX+'-'+phase+'.service',cmd)
                if phase=='generation':
                    self.assertIn('--setenv=VLLM_RPC_BASE_PATH='+str(m.RPC_BASE),cmd)
                    self.assertIn('--setenv=TMPDIR='+str(m.RPC_BASE),cmd)
                else:self.assertFalse(any(x.startswith('--setenv=VLLM_RPC_BASE_PATH') for x in cmd))
            with self.assertRaises(ValueError):m.command('cache',Path('/snapshot/release.json'),'a'*64)
        self.assertLessEqual(len(str(m.RPC_BASE))+37,107)

    def test_release_rejects_science_drift_but_allows_only_objective_source_change(self):
        old=dict(seed=2027,source_sha256={'src/repair/prompts.py':'old','scripts/train_zpd_paired_history.py':'old'})
        new=deepcopy(old);new['source_sha256'].update({k:'new' for k in m.REQUIRED})
        new['source_sha256']['scripts/train_zpd_paired_history.py']='new'
        new.update(objective_intervention=m.amendment(),family_path=str(m.FAMILY))
        m.validate_amendment(new,old,old)
        for field in ('seed','prompt','objective'):
            changed=deepcopy(new)
            if field=='seed':changed['seed']=1
            elif field=='prompt':changed['source_sha256']['src/repair/prompts.py']='new'
            else:changed['objective_intervention']['objective']['eos_weight']=2
            with self.assertRaises(ValueError):m.validate_amendment(changed,old,old)

    def test_materialization_byte_identical_with_frozen_order_and_no_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=Path(tmp).resolve()/'old';old.mkdir();out=Path(tmp).resolve()/'new';out.mkdir()
            for split in ('train','valid'):
                rows={a:[record(split,prompt=a+' prompt')] for a in ('C','H')}
                for a in rows:(old/(split+'-'+a+'.jsonl')).write_text(json.dumps(rows[a][0])+'\n')
                report=training.paired_preflight(rows['C'],rows['H'],Tokenizer())['report']
                m.core.write_new(old/(split+'-token-preflight.json'),report)
                m.core.write_new(old/(split+'-trajectory-exclusions.json'),{'unchanged':[]})
            m.core.write_new(old/'report.json',dict(counts={'train':1,'valid':1}))
            seal=dict(status='complete',history_truncated=False,dev_evaluation_recipients_filtered=False,
                files_sha256={p.name:m.core.sha_file(p) for p in old.iterdir()})
            with patch.object(m,'MATERIALIZED',old),patch.object(m,'verify_reuse',return_value=seal),\
                    patch.object(m.parent,'_tokenizer',return_value=Tokenizer()):
                m.materialize({},out);m.validate_phase_result('materialize',{},out)
                for split in ('train','valid'):
                    for a in ('C','H'):
                        name=split+'-'+a+'.jsonl'
                        self.assertEqual((old/name).read_bytes(),(out/'materialized'/name).read_bytes())

    def test_materialization_and_training_dispatch_keep_parent_primitive(self):
        with patch.object(m,'materialize') as materialize,patch.object(m,'BASE_EARLY') as base:
            m.run_early_phase('materialize',{},Path('/out'),None,'a')
            materialize.assert_called_once();base.assert_not_called()
            m.run_early_phase('train-C',{},Path('/out'),None,'a')
            base.assert_called_once()


class ObserverTests(unittest.TestCase):
    def test_new_family_seven_stages_and_example_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            project=Path(tmp);root=project/'outputs'/watch.BALANCED_FAMILY;root.mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'STATUS.json',dict(phase='capacity',completed_phases=['materialize']))
            row=next(r for r in watch.remote_snapshot(project)['experiments'] if r['family']==watch.BALANCED_FAMILY)
            self.assertEqual(row['total_examples'],7);self.assertEqual(row['completed_examples'],1)
            self.assertEqual(row['unit_prefix'],watch.BALANCED_UNIT_PREFIX)
            (root/'STATUS.json').write_text(json.dumps(dict(phase='train-C',completed_phases=['materialize','capacity'])))
            status=root/'train-C-v1/training';status.mkdir(parents=True)
            m.core.write_new(status/'STATUS.json',dict(phase='training',completed_examples=16,total_examples=19199,elapsed_seconds=30))
            row=next(r for r in watch.remote_snapshot(project)['experiments'] if r['family']==watch.BALANCED_FAMILY)
            self.assertEqual(row['completed_examples'],16);self.assertEqual(row['total_examples'],19199)
            self.assertIn('C 어댑터 학습 16/19199 예제',watch.korean_report(
                dict(checked_at='2026-10-16T14:00:00+09:00',experiments=[row])))

    def test_outer_seal_cannot_precede_normal_coordinator_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'outputs'/watch.BALANCED_FAMILY;root.mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'balanced_properties',return_value=dict(MainPID='99')):
                row=next(r for r in watch.remote_snapshot(Path(tmp))['experiments'] if r['family']==watch.BALANCED_FAMILY)
                self.assertEqual(row['state'],'running')
            with patch.object(watch,'balanced_properties',return_value=dict(MainPID='0',Result='exit-code')):
                row=next(r for r in watch.remote_snapshot(Path(tmp))['experiments'] if r['family']==watch.BALANCED_FAMILY)
                self.assertEqual(row['state'],'error')


if __name__=='__main__':unittest.main()
