from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_crossed_inference as m
from scripts import watch_zpd_completion as observer
from tests.test_generate_zpd_paired_history import GenerationTests


class CrossedTests(unittest.TestCase):
    def release(self):
        old=dict(family_path=str(m.previous.FAMILY),phases=list(m.PHASES),adapter_arm_map=m.ORIGINAL_MAP,
            source_sha256={'scripts/generate_zpd_paired_history.py':'a'},recovery={},
            inputs_sha256='input',tokenization_sha256='tokens',seed=2027,development_gate={'unchanged':True})
        new=deepcopy(old);new.pop('recovery')
        new.update(family_path=str(m.FAMILY),adapter_arm_map=m.CROSSED_MAP,diagnostic=m.diagnostic_contract())
        new['source_sha256'].update({p:'a' for p in m.REQUIRED})
        return old,new

    def test_exact_missing_cells_no_scientific_drift(self):
        old,new=self.release();m.validate_release(new,old)
        for key,value in [('inputs_sha256','drift'),('seed',42),('development_gate',{})]:
            bad=deepcopy(new);bad[key]=value
            with self.assertRaisesRegex(ValueError,'frozen scientific'):m.validate_release(bad,old)
        bad=deepcopy(new);bad['adapter_arm_map']=m.ORIGINAL_MAP
        with self.assertRaisesRegex(ValueError,'missing cells'):m.validate_release(bad,old)
        bad=deepcopy(new);bad['source_sha256']['scripts/generate_zpd_paired_history.py']='b'
        with self.assertRaisesRegex(ValueError,'algorithm pin'):m.validate_release(bad,old)
        for arm in m.core.ARMS:self.assertNotEqual(m.ORIGINAL_MAP[arm],m.CROSSED_MAP[arm])

    def test_diagnostic_cannot_enable_promotion_or_retraining(self):
        old,new=self.release()
        for key in ('model_promotion','training_repeated','original_cells_repeated'):
            bad=deepcopy(new);bad['diagnostic'][key]=True
            with self.assertRaisesRegex(ValueError,'exact diagnostic'):m.validate_release(bad,old)

    def test_context_restored_on_error(self):
        saved=(m.core.FAMILY,m.core.generation,m.driver.finalize,m.driver.command)
        with self.assertRaises(RuntimeError):
            with m.configured():
                self.assertEqual(m.core.FAMILY,m.FAMILY);self.assertIs(m.driver.finalize,m.finalize)
                raise RuntimeError()
        self.assertEqual(saved,(m.core.FAMILY,m.core.generation,m.driver.finalize,m.driver.command))

    def test_generation_map_restored_on_error(self):
        old=m.generator.ADAPTER_ARM_MAP
        def fake(*args):
            self.assertEqual(m.generator.ADAPTER_ARM_MAP,m.CROSSED_MAP)
            raise RuntimeError('test')
        with patch.object(m.generator,'generation',side_effect=fake):
            with self.assertRaises(RuntimeError):m.generation({},dict(adapter_arm_map=m.CROSSED_MAP),Path('/unused'))
        self.assertIs(m.generator.ADAPTER_ARM_MAP,old)

    def test_scoped_units_and_short_ipc(self):
        with m.configured():
            for phase in m.PHASES:
                cmd=m.command(phase,Path('/snapshot/release.json'),'a'*64,Path('/snapshot'))
                self.assertIn('scripts.run_zpd_crossed_inference',cmd)
                self.assertIn('--unit='+m.UNIT_PREFIX+'-'+phase+'.service',cmd)
                self.assertIn('--setenv=VLLM_RPC_BASE_PATH='+str(m.RPC_BASE),cmd)
                self.assertIn('--setenv=TMPDIR='+str(m.RPC_BASE),cmd)
                self.assertIn('--property=Restart=no',cmd)
        self.assertTrue(m.RPC_BASE.is_relative_to(m.PROJECT/'tmp'))
        self.assertLessEqual(len(str(m.RPC_BASE/'00000000-0000-0000-0000-000000000000').encode()),107)

    def labels(self,offset):
        labels=[]
        for i in range(320):
            for j,arm in enumerate((*m.core.ARMS,'noop')):
                labels.append(dict(example_id=str(i),arm=arm,problem_id='p',fold=i%5,current_source_sha256='a',
                    status='unknown' if i==0 else 'stable',all_ac=(i+j+offset)%3==0,loss=0.0))
        report=dict(execution_complete=True,development_gate=dict(passed=True,decision='proceed'),full=dict(results={}))
        for arm in (*m.core.ARMS,'noop'):
            rows=[r for r in labels if r['arm']==arm]
            report['full']['results'][arm]={'counts':dict(stable_ac=sum(r['status']=='stable' and r['all_ac'] for r in rows),
                                                        stable_regression=0,unknown=1)}
        return report,labels

    def test_factorial_join_counts_unknown_and_no_promotion_even_raw_pass(self):
        old,ol=self.labels(0);new,nl=self.labels(1)
        result=m.factorial_analysis(old,new,ol,nl)
        self.assertEqual(len(result['cells']),8)
        self.assertEqual(result['cells']['H/C'],new['full']['results']['C']['counts'])
        self.assertEqual(result['cells']['H/H'],old['full']['results']['H']['counts'])
        self.assertEqual(result['decision'],'diagnostic_only_no_promotion')
        self.assertFalse(result['model_promotion']);self.assertTrue(result['crossed_raw_gate_not_method_gate']['passed'])
        self.assertEqual(result['history_minus_controls']['H']['C']['unknown_either'],1)
        self.assertEqual(result['training_H_minus_C']['H']['jointly_known'],319)

    def test_factorial_reject_missing_duplicate_misaligned_or_unsealed_counts(self):
        old,ol=self.labels(0);new,nl=self.labels(1)
        for bad in (nl[:-1],nl+[nl[0]]):
            with self.assertRaisesRegex(ValueError,'unique factorial'):m.factorial_analysis(old,new,ol,bad)
        bad=deepcopy(nl);bad[0]['current_source_sha256']='drift'
        with self.assertRaisesRegex(ValueError,'binding'):m.factorial_analysis(old,new,ol,bad)
        bad=deepcopy(new);bad['full']['results']['H']['counts']['stable_ac']+=1
        with self.assertRaisesRegex(ValueError,'count/label'):m.factorial_analysis(old,bad,ol,nl)

    def test_predecessor_running_rejects(self):
        with patch.object(m.core,'read_pinned',side_effect=[{},dict(status='complete',release_sha256=m.PREVIOUS_SHA,
                phases={p:'x' for p in m.PHASES},files_sha256={})]+[
                dict(cleanup_verified=True,exit=dict(Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0',SubState='exited'),
                     release_sha256=m.PREVIOUS_SHA,complete_sha256='x') for _ in m.PHASES]), \
             patch.object(m.previous,'verify_parent'),patch.object(m.core,'sha_file',return_value='x'), \
             patch.object(m.core,'verify_stage'),patch.object(m.core,'props',return_value=dict(MainPID='123',ControlGroup='live')):
            with self.assertRaisesRegex(ValueError,'still running'):m.verify_predecessor()

    def test_crossed_observer_current_phase_and_release(self):
        with tempfile.TemporaryDirectory() as d:
            project=Path(d);root=project/'outputs'/observer.CROSSED_FAMILY
            (root/'generation-v1').mkdir(parents=True);(root/'public-v1').mkdir()
            (root/'COORDINATOR.json').write_text(json.dumps(dict(release_sha256='a'*64)))
            (root/'STATUS.json').write_text(json.dumps(dict(phase='public',completed_phases=['generation'])))
            (root/'generation-v1/STATUS.json').write_text(json.dumps(dict(completed_examples=320)))
            (root/'public-v1/STATUS.json').write_text(json.dumps(dict(completed_examples=15,total_examples=320)))
            row=next(r for r in observer.remote_snapshot(project)['experiments'] if r['family']==observer.CROSSED_FAMILY)
            self.assertEqual(row['family'],observer.CROSSED_FAMILY);self.assertEqual(row['completed_examples'],15)
            self.assertEqual(row['release_sha256'],'a'*64);self.assertEqual(row['unit_prefix'],m.UNIT_PREFIX)


class CrossedGenerationTests(GenerationTests):
    """Run the original full 2,560-slot fake-vLLM test under the new mapping."""
    def test_mixed_requests_preserve_all_slots_and_per_prompt_roles(self):
        with patch.object(m.generator,'ADAPTER_ARM_MAP',m.CROSSED_MAP):
            super().test_mixed_requests_preserve_all_slots_and_per_prompt_roles()


if __name__=='__main__':unittest.main()
