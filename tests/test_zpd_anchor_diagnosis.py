"""Synthetic missing-only, safety, and observer checks; no candidate execution."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_anchor_diagnosis as m
from scripts import watch_zpd_completion as watch
from tests.test_zpd_anchored_diagnosis import loaded_fixture
from tests.test_diagnose_zpd_transition_failure import vector


def safety_fixture():
    loaded=loaded_fixture()
    for p in loaded['predictions']:
        p['diagnostic']=dict(top=p['eligible_candidate_ids'],fallback=False)
    loaded['vector_map']['p',m.diag.source_hash(b'current')]=vector('current','AC')
    return loaded


class DiagnosisTests(unittest.TestCase):
    def test_representation_audit_replays_strict_decoder_without_mutating(self):
        current='print(1)\n';rows=[]
        for arm,text,reason in [('C','[["print(1)\\n","if:\\n"]]','stop'),('H','[["absent","x"]]','stop'),
                                ('HS',None,None),('U','[]','stop')]:
            r=dict(arm=arm,attempt_id=arm,example_id='e',problem_id='p',draw_index=0,seed=2027,
                raw_text=text,finish_reason=reason)
            r['attempt']=m.anchor.terminal(r,text,reason,current) if text is not None else dict(
                index=0,seed=2027,source=None,status='resource_failure',
                error='untruncated prompt plus fixed output exceeds context')
            rows.append(r)
        loaded=dict(inputs=dict(recipients=[dict(example_id='e',current_source=current)]),attempts=rows)
        before=deepcopy(loaded);report=m.representation_audit(loaded)
        self.assertEqual(loaded,before)
        self.assertEqual(report['per_arm']['C']['current_valid_to_invalid'],1)
        self.assertEqual(report['per_arm']['H']['format_failure'],1)
        self.assertEqual(report['per_arm']['HS']['resource_failure'],1)
        self.assertEqual(report['per_arm']['U']['decoded_noop'],1)
        self.assertFalse(report['candidate_executed_by_audit']);self.assertFalse(report['candidate_repaired'])
        for kind in ('status','duplicate','missing_raw'):
            bad=deepcopy(before)
            if kind=='status':bad['attempts'][0]['attempt']['source']='changed'
            elif kind=='duplicate':bad['attempts'].append(deepcopy(bad['attempts'][0]))
            else:bad['attempts'][2]['attempt']['error']='foreign'
            with self.assertRaises(ValueError):m.representation_audit(bad)

    def test_missing_only_bundle_and_memberships(self):
        loaded=loaded_fixture();b=m.make_bundle(loaded)
        self.assertEqual(b['version'],m.VERSION)
        with m.configured(dict(original_vectors_sha256='d'*64)):
            tasks=m.replay.validate_tasks(b,loaded['vectors'],len(b['tasks']))
            m.replay.recipient_memberships(b,tasks,2)
        self.assertFalse(set(tasks)&set(loaded['vector_map']))
        self.assertFalse(b['retry_existing_vectors']);self.assertFalse(b['generation_authorized'])
        self.assertFalse(b['selection_changes_authorized'])

    def test_safe_alternative_excludes_noop_and_unknown(self):
        loaded=safety_fixture();vectors=loaded['vector_map']
        report=m.safety_diagnosis(loaded,vectors)
        row=next(r for r in report['rows'] if r['example_id']=='e0' and r['arm']=='H')
        self.assertTrue(row['selected_regressions'])
        self.assertEqual(row['known_nonnoop_safe_alternative_ids'],[])
        self.assertTrue(row['regression_with_unknown_nonnoop_alternative'])
        self.assertFalse(row['regression_with_known_nonnoop_safe_alternative'])

    def test_stable_ac_alternative_and_public_top_stratum(self):
        loaded=safety_fixture();cid=m.diag.source_hash(b'e0-H-1')
        loaded['vector_map']['p',cid]=vector('e0-H-1','AC')
        before=deepcopy(loaded['predictions'])
        report=m.safety_diagnosis(loaded,loaded['vector_map'])
        row=next(r for r in report['rows'] if r['example_id']=='e0' and r['arm']=='H')
        self.assertEqual(row['known_ac_alternative_ids'],[cid])
        self.assertTrue(row['regression_with_known_nonnoop_safe_alternative'])
        self.assertTrue(row['regression_with_public_top_ac_alternative'])
        self.assertEqual(loaded['predictions'],before)

    def test_unstable_alternative_and_current_remain_unknown(self):
        loaded=safety_fixture();cid=m.diag.source_hash(b'e0-H-1')
        loaded['vector_map']['p',cid]=vector('e0-H-1','AC',unstable=True)
        report=m.safety_diagnosis(loaded,loaded['vector_map'])
        row=next(r for r in report['rows'] if r['example_id']=='e0' and r['arm']=='H')
        self.assertFalse(row['regression_with_known_ac_alternative'])
        self.assertIn(cid,row['unknown_nonnoop_alternative_ids'])
        loaded['vector_map']['p',m.diag.source_hash(b'current')]=vector('current','AC',unstable=True)
        report=m.safety_diagnosis(loaded,loaded['vector_map'])
        self.assertTrue(all(r['selected_unknown'] and not r['selected_regressions'] for r in report['rows']))

    def test_foreign_public_candidate_refused(self):
        loaded=safety_fixture();loaded['predictions'][0]['diagnostic']['top']=['foreign']
        with self.assertRaisesRegex(ValueError,'public top'):m.safety_diagnosis(loaded,loaded['vector_map'])

    def test_selected_counts_are_invariants(self):
        r=dict(per_arm={a:dict(selected_stable_ac=m.SELECTED[a],selected_unknown=m.UNKNOWN[a]) for a in m.diag.ARMS})
        m.verify_selected(r)
        for key in ('selected_stable_ac','selected_unknown'):
            changed=deepcopy(r);changed['per_arm']['H'][key]+=1
            with self.assertRaises(ValueError):m.verify_selected(changed)

    def test_command_scoped_bounds_and_restore(self):
        before=(m.replay.ROOT,m.replay.UNIT,m.replay.command,m.replay.source_barrier)
        with self.assertRaises(RuntimeError):
            with m.configured(dict(original_vectors_sha256='d'*64)):
                cmd=m.command(Path('/snapshot'),Path('/snapshot/release.json'),'r')
                for expected in ('scripts.run_zpd_anchor_diagnosis','--unit='+m.UNIT,
                    '--property=RuntimeMaxSec=21600','--property=TasksMax=128','--property=Restart=no'):
                    self.assertIn(expected,cmd)
                raise RuntimeError('fixture')
        self.assertEqual(before,(m.replay.ROOT,m.replay.UNIT,m.replay.command,m.replay.source_barrier))

    def test_duplicate_cannot_stop_prior_worker(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp).resolve()),\
                patch.object(m.recovery,'properties',return_value={'LoadState':'loaded'}),patch.object(m.subprocess,'run') as run:
            with self.assertRaises(ValueError):m.supervise(Path('/s'),{},Path('/r'),'r')
            run.assert_not_called()

    def test_failed_owned_worker_cleanup_only(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp).resolve()),\
                patch.object(m.recovery,'properties',return_value={'LoadState':'not-found'}),patch.object(m.subprocess,'run') as run:
            def fail(*args):
                m.core.write_new(Path(temp)/'COORDINATOR.json',dict(release_sha256='r'))
                raise RuntimeError('fixture')
            with patch.object(m.replay,'supervise',side_effect=fail):
                with self.assertRaises(RuntimeError):m.supervise(Path('/s'),{},Path('/r'),'r')
            run.assert_called_once_with(['/usr/bin/systemctl','--user','stop',m.UNIT],check=True,timeout=30)

    def test_release_rejects_scope_or_population_change(self):
        loaded=loaded_fixture();bundle=m.make_bundle(loaded)
        r=dict(version=m.VERSION,family_path=str(m.ROOT),original_release_sha256=m.PARENT_RELEASE,
            original_complete_sha256=m.PARENT_COMPLETE,missing_tasks=m.MISSING,existing_tasks_reused=m.EXISTING,
            planned_case_attempts=m.CASES,phase_seconds=21600,examples=320,block_workers=[1,8,8,1],
            unchanged_selected_stable_ac=m.SELECTED,unchanged_selected_unknown=m.UNKNOWN,
            unchanged_selected_regressions=m.REGRESSIONS,original_vectors_sha256=bundle['original_vectors_sha256'],
            expected_runtime_sha256=bundle['expected_runtime_sha256'],source_sha256={n:'pin' for n in m.REQUIRED})
        keys=('new_generation','new_training','selected_choices_changed','scorer_changes','testcase_changes',
            'retry_existing_vectors','implicit_retry','overwrite','confirmatory','model_promotion')
        r.update({k:False for k in keys});m.validate_release(r,bundle,loaded)
        for key in keys:
            changed=deepcopy(r);changed[key]=True
            with self.assertRaises(ValueError):m.validate_release(changed,bundle,loaded)
        changed=deepcopy(r);changed['missing_tasks']-=1
        with self.assertRaises(ValueError):m.validate_release(changed,bundle,loaded)


class ObserverTests(unittest.TestCase):
    def test_registered_diagnosis_progress_and_normal_exit_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'outputs'/watch.ANCHOR_DIAGNOSIS_FAMILY;(root/'run-v1').mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'run-v1/STATUS.json',dict(phase='missing_candidate_replay',
                completed_examples=5,total_examples=320,completed_case_attempts=900,total_case_attempts=80528,
                completed_unique_sources=0,total_unique_sources=977,elapsed_seconds=60))
            getrow=lambda:next(r for r in watch.remote_snapshot(Path(tmp))['experiments'] if r['family']==watch.ANCHOR_DIAGNOSIS_FAMILY)
            row=getrow()
            self.assertEqual(row['state'],'running');self.assertEqual(row['release_sha256'],'a'*64)
            self.assertEqual(row['completed_case_attempts'],900)
            report=watch.korean_report(dict(checked_at='2026-10-17T02:00:00+09:00',experiments=[row]))
            self.assertIn('900/80528',report);self.assertIn('블록별 병렬도 차이',report)
            m.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'anchor_diagnosis_properties',return_value={'MainPID':'99'}):
                self.assertEqual(getrow()['state'],'running')
            with patch.object(watch,'anchor_diagnosis_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(getrow()['state'],'error')


if __name__=='__main__':unittest.main()
