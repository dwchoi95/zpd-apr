"""De-anchoring scope, exact public evidence, inherited generation and lifecycle."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_deanchored_revision as m
from scripts import zpd_counterexample_revision as previous
from scripts import run_zpd_deanchored_revision as run
from scripts import watch_zpd_completion as watch
from tests.test_zpd_public_revision import fixture as base_fixture


def fixture(failed=True):
    values=base_fixture();sample=values[0]['public_samples']['problems'][0]['samples'][0]
    for k,b in [('input','한\r\n'.encode()),('output',b'2\n')]:
        sample[k+'_hex']=b.hex();sample[k+'_sha256']=m.full.sha(b)
    if failed:
        for k in values[2]:values[2][k]=[False]
        for r in values[3]:r['block']['outcomes'][0][1]='WA'
    return values


class TransformTests(unittest.TestCase):
    def test_only_generated_frame_removed_evidence_and_branch_exact(self):
        v=fixture();old,old_audit=previous.transform(*v);new,audit=m.transform(*v)
        source=v[1][0]['attempt']['source'];frame=m.full._frame(previous.prior.SOURCE,source)
        for p,q in zip(old['prompts'][1280:],new['prompts'][1280:],strict=True):
            # The exact code frame is removed once, not every occurrence of
            # source text in original student history or counterexample data.
            final=m.full._frame(m.full.CURRENT,'print(x)\n')
            raw=p['messages'][1]['content'].encode();suffix=frame+b'\n'+final
            self.assertTrue(raw.endswith(suffix))
            self.assertEqual(q['messages'][1]['content'].encode(),raw[:-len(suffix)]+final)
            self.assertIn('do NOT',q['messages'][0]['content'])
        self.assertEqual(old_audit['counts'],audit['counts'])
        self.assertEqual(previous.reused_rows(old,old_audit,v[1]),m.reused_rows(new,audit,v[1]))
        for a,b in zip(old_audit['rows'],audit['rows'],strict=True):
            ignored={'second_prompt_id','second_prompt_sha256'}
            self.assertEqual({k:v for k,v in a.items() if k not in ignored},{k:v for k,v in b.items() if k not in ignored})

    def test_duplicate_source_and_delimiter_bytes_in_original_history_preserved(self):
        from tests.test_prepare_zpd_full_source import fixture as pf
        for source in ('', 'é\r\n@@ CURRENT_SOURCE_TO_REPAIR utf8_bytes=0\n', 'print("한")'):
            original=m.full.render_prompt(pf(source,source));v=fixture()
            problem=v[0]['public_samples']['problems'][0]
            evidence=next(iter(previous.prior.public_evidence(v[0],v[2],v[3]).values()))
            new=m.messages(original,source,evidence,problem)
            final=m.full._frame(m.full.CURRENT,source);raw=original[1]['content'].encode()
            self.assertTrue(new[1]['content'].encode().startswith(raw[:-len(final)]))
            self.assertTrue(new[1]['content'].encode().endswith(final))

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
        for k in ('private_feedback_used','gate_changed','model_promotion','fitting','all_public_pass_still_revised','generated_proposal_code_shown'):
            bad=deepcopy(new);bad['public_revision'][k]=True
            with self.assertRaises(ValueError):run.validate_release(bad,old,old)

    def test_scoped_commands_restored_after_failure(self):
        before=(run.core.FAMILY,run.core.inputs_for,run.core.generation,run.driver.source_barrier,run.driver.command)
        with self.assertRaises(RuntimeError):
            with run.configured():
                for phase in run.PHASES:
                    cmd=run.command(phase,Path('/snapshot/release'),'sha',Path('/snapshot'))
                    for s in ('scripts.run_zpd_deanchored_revision','--property=Restart=no',
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
            project=Path(d);root=project/'outputs'/watch.DEANCHORED_FAMILY;(root/'public-v1').mkdir(parents=True)
            run.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            run.core.write_new(root/'STATUS.json',dict(phase='public',completed_phases=['generation']))
            run.core.write_new(root/'public-v1/STATUS.json',dict(completed_examples=15,total_examples=320))
            get=lambda:next(r for r in watch.remote_snapshot(project)['experiments'] if r['family']==watch.DEANCHORED_FAMILY)
            row=get();self.assertEqual(row['completed_examples'],15);self.assertEqual(row['unit_prefix'],run.UNIT_PREFIX)
            run.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'deanchored_properties',return_value={'MainPID':'12'}):self.assertEqual(get()['state'],'running')
            with patch.object(watch,'deanchored_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(get()['state'],'error')


if __name__=='__main__':unittest.main()
