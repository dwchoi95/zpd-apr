from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_anchored_routing as m
from scripts import watch_zpd_completion as observer
from tests.test_run_zpd_transition_generation import fixture
from tests.test_run_zpd_full_source import private_report


class RoutingTests(unittest.TestCase):
    def fixture(self):
        inputs,original=fixture(320)
        ledgers={'original':original,'crossed':deepcopy(original)}
        release=dict(adapter_C='/adapter/C',adapter_H='/adapter/H',model_sha256={
            '/adapter/C/adapter_model.safetensors':'c'*64,'/adapter/H/adapter_model.safetensors':'h'*64})
        for name,rows in ledgers.items():
            for row in rows:
                role=(m.crossed.ORIGINAL_MAP if name=='original' else m.crossed.CROSSED_MAP)[row['arm']]
                row.update(adapter_role=role,adapter_model_sha256=release['model_sha256'][release['adapter_'+role]+'/adapter_model.safetensors'])
                # Distinguish every actual source, even same prompt across adapters.
                row['attempt']['source']=repr((name,row['attempt_id']))
        return inputs,ledgers,release

    def test_routing_preserves_actual_prompts_seeds_and_two_slots(self):
        inputs,ledgers,release=self.fixture();original=deepcopy(inputs)
        plan=m.route_inputs(inputs);rows=m.assemble(plan,ledgers,release)
        self.assertEqual(inputs,original);self.assertEqual(plan['recipients'],inputs['recipients'])
        self.assertEqual(plan['prompts'],inputs['prompts']);self.assertEqual(len(rows),2560)
        by_id={r['attempt_id']:r for r in rows}
        for eid in [r['example_id'] for r in inputs['recipients']]:
            anchor=[r for r in rows if r['example_id']==eid and r['draw_index']==0]
            self.assertEqual(len(anchor),4);self.assertEqual(len({r['attempt']['source'] for r in anchor}),1)
            self.assertTrue(all(r['prompt_id'].endswith(':C') and r['adapter_role']=='C' for r in anchor))
        secondary=[r for r in rows if r['draw_index']==1]
        self.assertTrue(all(r['adapter_role']=='H' for r in secondary))
        self.assertEqual(sum(r['origin']['ledger']=='crossed' for r in rows),320)
        for row in rows:
            source=next(r for r in ledgers[row['origin']['ledger']] if r['attempt_id']==row['origin']['attempt_id'])
            self.assertEqual(row['origin_row_sha256'],m.core.sha(m.core.encoded(source)))
            self.assertEqual(row['attempt'],source['attempt'])
        bank,owned=m.core.candidate_banks(plan,rows,'a'*64)[inputs['recipients'][0]['example_id']]
        self.assertEqual(len(bank.attempts),8)
        self.assertTrue(all(len(v)==3 for v in owned.values()))
        self.assertEqual(len(set.intersection(*owned.values())),2) # current + common anchor

    def test_failure_and_duplicate_slots_survive_no_retry_fill(self):
        inputs,ledgers,release=self.fixture()
        ledgers['original'][0]['attempt'].update(status='resource_failure',source=None,error='limit')
        rows=m.assemble(m.route_inputs(inputs),ledgers,release)
        self.assertEqual(sum(r['attempt']['status']=='resource_failure' for r in rows),4)
        self.assertEqual(len(rows),2560)

    def test_bad_origin_prompt_seed_adapter_and_missing_draw_rejected(self):
        inputs,ledgers,release=self.fixture();plan=m.route_inputs(inputs)
        for field,value in [('prompt_id','wrong'),('seed',-1),('adapter_role','H'),('adapter_model_sha256','bad')]:
            bad=deepcopy(ledgers);bad['original'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):m.assemble(plan,bad,release)
        bad=deepcopy(ledgers);bad['crossed'].pop()
        with self.assertRaisesRegex(ValueError,'origin ledgers'):m.assemble(plan,bad,release)
        bad=deepcopy(plan);bad['attempts'][0]['origin']['ledger']='crossed'
        with self.assertRaisesRegex(ValueError,'origin route'):m.assemble(bad,ledgers,release)

    def test_routing_has_no_score_label_or_candidate_quality_input(self):
        inputs,_,_=self.fixture()
        plan=m.route_inputs(inputs)
        self.assertTrue(all('attempt' not in r for r in plan['attempts']))
        self.assertFalse(m.routing_contract()['private_labels_used_for_routing'])

    def test_release_freezes_gate_and_rejects_extra_generation(self):
        old=dict(family_path=str(m.crossed.FAMILY),source_sha256={'selector':'pin'},adapter_arm_map={},diagnostic={},
                 development_gate={'fixed':True},seed=2027,inputs_sha256='inputs')
        new=deepcopy(old);new.pop('adapter_arm_map');new.pop('diagnostic')
        new.update(family_path=str(m.FAMILY),routing=m.routing_contract(),overflow_attempts=9)
        new['source_sha256'].update({p:'x' for p in m.REQUIRED})
        m.validate_release(new,old)
        for key,value in [('seed',42),('development_gate',{}),('inputs_sha256','drift')]:
            bad=deepcopy(new);bad[key]=value
            with self.assertRaisesRegex(ValueError,'frozen'):m.validate_release(bad,old)
        bad=deepcopy(new);bad['routing']['new_generation']=True
        with self.assertRaisesRegex(ValueError,'exact routing'):m.validate_release(bad,old)

    def test_context_and_cpu_only_commands(self):
        before=(m.core.FAMILY,m.core.inputs_for,m.core.generation,m.driver.command)
        with self.assertRaises(RuntimeError):
            with m.configured():
                self.assertIs(m.core.inputs_for,m.routed_inputs)
                for phase in m.PHASES:
                    cmd=m.command(phase,Path('/snapshot/release'),'a'*64,Path('/snapshot'))
                    self.assertIn('scripts.run_zpd_anchored_routing',cmd)
                    self.assertIn(str(m.PROJECT/'.runtime/fse-env/bin/python'),cmd)
                    self.assertNotIn(str(m.PROJECT/'.runtime/fse-vllm/bin/python'),cmd)
                    self.assertIn('--property=Restart=no',cmd)
                raise RuntimeError()
        self.assertEqual(before,(m.core.FAMILY,m.core.inputs_for,m.core.generation,m.driver.command))

    def test_summary_preserves_gate_and_never_promotes(self):
        report=private_report();report['confirmatory']=False;report['model_promotion']=False
        out=m.summarize_private(report,'a'*64,'b'*64)
        self.assertEqual(out['development_gate'],report['development_gate'])
        self.assertEqual(out['generated_during_this_run'],0);self.assertFalse(out['model_promotion'])
        self.assertFalse(out['prior_single_policy_C_reference']['gate'])

    def test_registered_observer_reads_current_phase_and_release(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp);root=project/'outputs'/observer.ANCHORED_FAMILY
            (root/'public-v1').mkdir(parents=True)
            (root/'COORDINATOR.json').write_text(json.dumps(dict(release_sha256='a'*64)))
            (root/'STATUS.json').write_text(json.dumps(dict(phase='public',completed_phases=['generation'])))
            (root/'public-v1/STATUS.json').write_text(json.dumps(dict(completed_examples=23,total_examples=320)))
            row=next(r for r in observer.remote_snapshot(project)['experiments'] if r['family']==observer.ANCHORED_FAMILY)
            self.assertEqual(row['completed_examples'],23);self.assertEqual(row['release_sha256'],'a'*64)
            self.assertEqual(row['unit_prefix'],m.UNIT_PREFIX)


if __name__=='__main__':unittest.main()
