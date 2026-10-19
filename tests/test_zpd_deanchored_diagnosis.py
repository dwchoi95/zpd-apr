"""Synthetic paired-slot accounting, no-retry scope and normal-exit gates."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_deanchored_diagnosis as m
from scripts import zpd_revision_diagnosis as slots
from scripts import watch_zpd_completion as watch
from tests.test_zpd_anchored_diagnosis import loaded_fixture
from tests.test_diagnose_zpd_transition_failure import vector
from scripts.zpd_deanchored_diagnosis import summarize_transfer


def fixture():
    loaded=loaded_fixture()
    sources=m.diag._inventory(loaded['inputs'],loaded['attempts'],loaded['predictions'])[3]
    loaded['public_masks']={pid+'|'+cid:[False] for pid,cid in sources}
    loaded['revision_audit']=dict(rows=[dict(example_id=r['example_id'],arm=r['arm'],first_attempt_id=r['attempt_id'],
        first_attempt_row_sha256=m.diag.canonical_hash(r),all_public_samples_pass=False,
        feedback_availability='stable',proposal_status=r['attempt']['status'])
        for r in loaded['attempts'] if r['draw_index']==0])
    for p in loaded['predictions']:p['diagnostic']=dict(top=p['eligible_candidate_ids'],fallback=False)
    return loaded


class LifecycleTests(unittest.TestCase):
    def test_missing_only_scope_and_full_recipient_memberships(self):
        x=fixture();b=m.make_bundle(x)
        with m.configured(dict(original_vectors_sha256='d'*64)):
            tasks=m.replay.validate_tasks(b,x['vectors'],len(b['tasks']))
            m.replay.recipient_memberships(b,tasks,2)
        self.assertFalse(set(tasks)&set(x['vector_map']))
        for key in ('retry_existing_vectors','generation_authorized','selection_changes_authorized'):
            self.assertFalse(b[key])

    def test_selected_success_unknown_are_invariants(self):
        r=dict(per_arm={a:dict(selected_stable_ac=m.SELECTED[a],selected_unknown=m.UNKNOWN[a]) for a in m.diag.ARMS})
        m.verify_selected(r)
        for key in ('selected_stable_ac','selected_unknown'):
            bad=deepcopy(r);bad['per_arm']['H'][key]+=1
            with self.assertRaises(ValueError):m.verify_selected(bad)

    def test_fixed_release_refuses_scope_expansion(self):
        x=fixture();b=m.make_bundle(x)
        r=dict(version=m.VERSION,family_path=str(m.ROOT),original_release_sha256=m.PARENT_RELEASE,
            original_complete_sha256=m.PARENT_COMPLETE,missing_tasks=m.MISSING,existing_tasks_reused=m.EXISTING,
            planned_case_attempts=m.CASES,phase_seconds=21600,examples=320,block_workers=[1,8,8,1],
            unchanged_selected_stable_ac=m.SELECTED,unchanged_selected_unknown=m.UNKNOWN,
            unchanged_selected_regressions=m.REGRESSIONS,original_vectors_sha256=b['original_vectors_sha256'],
            expected_runtime_sha256=b['expected_runtime_sha256'],source_sha256={n:'pin' for n in m.REQUIRED})
        keys=('new_generation','new_training','selected_choices_changed','scorer_changes','testcase_changes',
            'retry_existing_vectors','implicit_retry','overwrite','confirmatory','model_promotion')
        r.update({k:False for k in keys});m.validate_release(r,b,x)
        for key in keys:
            bad=deepcopy(r);bad[key]=True
            with self.assertRaises(ValueError):m.validate_release(bad,b,x)
        for key in ('missing_tasks','existing_tasks_reused','planned_case_attempts','examples'):
            bad=deepcopy(r);bad[key]+=1
            with self.assertRaises(ValueError):m.validate_release(bad,b,x)

    def test_scope_restored_on_error_and_worker_resource_bounds(self):
        before=(m.replay.ROOT,m.replay.UNIT,m.replay.command,m.replay.source_barrier)
        with self.assertRaises(RuntimeError):
            with m.configured(dict(original_vectors_sha256='d'*64)):
                cmd=m.command(Path('/snapshot'),Path('/snapshot/release.json'),'r')
                for s in ('scripts.run_zpd_deanchored_diagnosis','--unit='+m.UNIT,
                    '--property=RuntimeMaxSec=21600','--property=TasksMax=128','--property=Restart=no'):
                    self.assertIn(s,cmd)
                raise RuntimeError()
        self.assertEqual(before,(m.replay.ROOT,m.replay.UNIT,m.replay.command,m.replay.source_barrier))

    def test_duplicate_never_stops_existing_worker(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'ROOT',Path(d).resolve()),\
            patch.object(m.recovery,'properties',return_value={'LoadState':'loaded'}),patch.object(m.subprocess,'run') as call:
            with self.assertRaises(ValueError):m.supervise(Path('/s'),{},Path('/r'),'r')
            call.assert_not_called()

    def test_owned_failure_stops_only_own_worker_without_retry(self):
        with tempfile.TemporaryDirectory() as d,patch.object(m,'ROOT',Path(d).resolve()),\
            patch.object(m.recovery,'properties',return_value={'LoadState':'not-found'}),patch.object(m.subprocess,'run') as call:
            def fail(*args):
                m.core.write_new(Path(d)/'COORDINATOR.json',dict(release_sha256='r'));raise RuntimeError()
            with patch.object(m.replay,'supervise',side_effect=fail):
                with self.assertRaises(RuntimeError):m.supervise(Path('/s'),{},Path('/r'),'r')
            call.assert_called_once_with(['/usr/bin/systemctl','--user','stop',m.UNIT],check=True,timeout=30)

    def test_observer_release_progress_and_normal_exit(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'outputs'/watch.DEANCHORED_DIAGNOSIS_FAMILY;(root/'run-v1').mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'run-v1/STATUS.json',dict(phase='missing_candidate_replay',completed_examples=3,
                total_examples=320,completed_case_attempts=500,total_case_attempts=66916,elapsed_seconds=60))
            get=lambda:next(r for r in watch.remote_snapshot(Path(d))['experiments'] if r['family']==watch.DEANCHORED_DIAGNOSIS_FAMILY)
            row=get();self.assertEqual(row['state'],'running');self.assertEqual(row['completed_examples'],3)
            self.assertEqual(row['release_sha256'],'a'*64)
            m.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'deanchored_diagnosis_properties',return_value={'MainPID':'99'}):
                self.assertEqual(get()['state'],'running')
            with patch.object(watch,'deanchored_diagnosis_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(get()['state'],'error')


class TransferTests(unittest.TestCase):
    def rows(self):
        x=fixture()
        return slots.assess_slots(x,x['vector_map'])

    def test_pure_exact_counts_and_missing_separate(self):
        x=self.rows();before=deepcopy(x);r=summarize_transfer(x)
        self.assertEqual(x,before)
        self.assertEqual(r['per_arm']['H']['fail']['examples'],2)
        self.assertEqual(r['per_arm']['H']['fail']['second_public_fail_private_missing'],2)
        for arm in ('C','HS','U'):
            self.assertEqual(r['paired_H'][arm]['both_failed']['second_private']['not_jointly_stable'],2)
        for key in ('model_promotion','selection_changes_authorized','causal_history_effect_established'):
            self.assertFalse(r[key])

    def test_unknown_and_terminal_never_nonac(self):
        for status in ('unknown','terminal_failure'):
            x=self.rows();h=next(r for r in x['rows'] if r['arm']=='H')
            h['second_private']=dict(status=status,all_ac=None,regression=None)
            r=summarize_transfer(x)
            self.assertEqual(r['per_arm']['H']['fail']['second_public_fail_private_'+status],1)
            self.assertNotIn('second_public_fail_private_stable_nonac',r['per_arm']['H']['fail'])

    def test_original_branch_not_current_public_and_exact_pairing(self):
        x=self.rows()
        for row in x['rows']:
            if row['example_id']=='e0':
                row['original_public_feedback']='fail' if row['arm']=='H' else 'pass'
                row['first_public_now']='pass'
                row['second_public_now']='pass'
                row['second_private']=dict(status='stable',all_ac=row['arm']=='H',regression=row['arm']!='H')
        r=summarize_transfer(x)
        self.assertEqual(r['per_arm']['H']['fail']['second_public_pass_private_stable_ac'],1)
        for arm in ('C','HS','U'):
            p=r['paired_H'][arm]['H_only_failed']['second_private']
            self.assertEqual(p['jointly_stable'],1);self.assertEqual(p['H_ac_only'],1)
            self.assertEqual(p['control_regression_only'],1)

    def test_all_four_branch_groups(self):
        for hf in (False,True):
            for cf in (False,True):
                x=self.rows()
                for r in x['rows']:r['original_public_feedback']='fail' if (hf if r['arm']=='H' else cf) else 'pass'
                group='both_failed' if hf and cf else 'H_only_failed' if hf else 'control_only_failed' if cf else 'neither_failed'
                report=summarize_transfer(x)
                for arm in ('C','HS','U'):
                    self.assertEqual(set(report['paired_H'][arm]),{group})
                    self.assertEqual(report['paired_H'][arm][group]['selected_private']['examples'],2)

    def test_malformed_identity_or_evidence_rejected(self):
        for kind in ('duplicate','missing','fold','problem','unknown_as_false','stable_as_none','integer_bool','public'):
            x=self.rows()
            if kind=='duplicate':x['rows'].append(deepcopy(x['rows'][0]))
            elif kind=='missing':x['rows'].pop()
            elif kind=='fold':x['rows'][0]['fold']=99
            elif kind=='problem':x['rows'][0]['problem_id']='foreign'
            elif kind=='unknown_as_false':x['rows'][0]['second_private']=dict(status='unknown',all_ac=False,regression=False)
            elif kind=='stable_as_none':x['rows'][0]['second_private']=dict(status='stable',all_ac=None,regression=False)
            elif kind=='integer_bool':x['rows'][0]['second_private']=dict(status='stable',all_ac=1,regression=0)
            else:x['rows'][0]['original_public_feedback']='bad'
            with self.subTest(kind=kind),self.assertRaises(ValueError):summarize_transfer(x)


if __name__=='__main__':unittest.main()
