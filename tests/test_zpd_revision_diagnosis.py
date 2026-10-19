"""Synthetic paired-slot accounting, no-retry scope and normal-exit gates."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_revision_diagnosis as m
from scripts import zpd_revision_diagnosis as slots
from scripts import watch_zpd_completion as watch
from tests.test_zpd_anchored_diagnosis import loaded_fixture
from tests.test_diagnose_zpd_transition_failure import vector


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


class SlotTests(unittest.TestCase):
    def row(self,report,arm='H',eid='e0'):
        return next(r for r in report['rows'] if r['example_id']==eid and r['arm']==arm)

    def test_full_membership_pairing_missing_not_failure_and_pure(self):
        x=fixture();before=deepcopy(x);report=slots.assess_slots(x,x['vector_map'])
        self.assertEqual(x,before);self.assertEqual(len(report['rows']),8)
        r=self.row(report);self.assertEqual(r['second_private']['status'],'missing')
        self.assertFalse(r['ac_lost']);self.assertFalse(r['jointly_stable'])
        self.assertTrue(report['missing_unknown_and_terminal_failure_separate'])
        self.assertFalse(report['model_promotion'])

    def test_known_gain_and_missed_ac_are_distinct_from_selection(self):
        x=fixture();x['vector_map']['p',m.diag.source_hash(b'e0-H-1')]=vector('e0-H-1','AC')
        r=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertTrue(r['ac_gained']);self.assertTrue(r['known_second_ac_missed'])
        self.assertFalse(r['ac_lost']);self.assertFalse(r['regression_introduced'])

    def test_known_loss_and_regression_require_stable_current_and_candidates(self):
        x=fixture();x['vector_map']['p',m.diag.source_hash(b'current')]=vector('current','AC')
        x['vector_map']['p',m.diag.source_hash(b'e0-H-0')]=vector('e0-H-0','AC')
        x['vector_map']['p',m.diag.source_hash(b'e0-H-1')]=vector('e0-H-1','WA')
        r=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertTrue(r['ac_lost']);self.assertTrue(r['regression_introduced'])
        x['vector_map']['p',m.diag.source_hash(b'current')]=vector('current','AC',unstable=True)
        r=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertTrue(r['first_private_unknown']);self.assertTrue(r['second_private_unknown'])
        self.assertFalse(r['ac_lost']);self.assertFalse(r['regression_introduced'])

    def test_unstable_second_stays_unknown_not_nonac(self):
        x=fixture();x['vector_map']['p',m.diag.source_hash(b'e0-H-1')]=vector('e0-H-1','AC',unstable=True)
        r=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertTrue(r['second_private_unknown']);self.assertIsNone(r['second_private']['all_ac'])
        self.assertFalse(r['ac_gained']);self.assertFalse(r['known_second_ac_missed'])

    def test_original_feedback_not_relabelled_after_public_reexecution(self):
        x=fixture();x['public_masks']['p|'+m.diag.source_hash(b'e0-H-0')]=[True]
        r=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertEqual(r['original_public_feedback'],'fail');self.assertEqual(r['first_public_now'],'pass')
        self.assertTrue(r['feedback_public_state_changed'])
        x['revision_audit']['rows'][1]['feedback_availability']='unavailable'
        r=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertEqual(r['original_public_feedback'],'unavailable')

    def test_terminal_failure_not_missing_or_unknown(self):
        x=fixture();r=next(r for r in x['attempts'] if r['attempt_id']=='e0-H-1')
        cid=m.diag.source_hash(r['attempt']['source'].encode());r['attempt'].update(status='format_failure',source=None,error='invalid format')
        p=next(p for p in x['predictions'] if p['example_id']=='e0' and p['arm']=='H');p['eligible_candidate_ids'].remove(cid)
        row=self.row(slots.assess_slots(x,x['vector_map']))
        self.assertTrue(row['second_terminal_failure']);self.assertFalse(row['second_private_unknown'])
        self.assertFalse(row['second_private_missing']);self.assertFalse(row['ac_gained'])

    def test_copy_is_exact_source_bytes_not_semantic_equivalence(self):
        x=fixture();r=next(r for r in x['attempts'] if r['attempt_id']=='e0-H-1')
        cid=m.diag.source_hash(r['attempt']['source'].encode());r['attempt']['source']='e0-H-0'
        p=next(p for p in x['predictions'] if p['example_id']=='e0' and p['arm']=='H');p['eligible_candidate_ids'].remove(cid)
        self.assertTrue(self.row(slots.assess_slots(x,x['vector_map']))['identical_first_source'])

    def test_audit_hash_identity_and_duplicate_refused(self):
        for kind in ('hash','id','duplicate'):
            x=fixture()
            if kind=='hash':x['revision_audit']['rows'][0]['first_attempt_row_sha256']='bad'
            elif kind=='id':x['revision_audit']['rows'][0]['first_attempt_id']='bad'
            else:x['revision_audit']['rows'].append(deepcopy(x['revision_audit']['rows'][0]))
            with self.subTest(kind=kind),self.assertRaises(ValueError):slots.assess_slots(x,x['vector_map'])


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
                for s in ('scripts.run_zpd_revision_diagnosis','--unit='+m.UNIT,
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
            root=Path(d)/'outputs'/watch.REVISION_DIAGNOSIS_FAMILY;(root/'run-v1').mkdir(parents=True)
            m.core.write_new(root/'COORDINATOR.json',dict(release_sha256='a'*64))
            m.core.write_new(root/'run-v1/STATUS.json',dict(phase='missing_candidate_replay',completed_examples=3,
                total_examples=320,completed_case_attempts=500,total_case_attempts=53772,elapsed_seconds=60))
            get=lambda:next(r for r in watch.remote_snapshot(Path(d))['experiments'] if r['family']==watch.REVISION_DIAGNOSIS_FAMILY)
            row=get();self.assertEqual(row['state'],'running');self.assertEqual(row['completed_examples'],3)
            self.assertEqual(row['release_sha256'],'a'*64)
            m.core.write_new(root/'VERIFIED_COMPLETE.json',dict(status='complete'))
            with patch.object(watch,'revision_diagnosis_properties',return_value={'MainPID':'99'}):
                self.assertEqual(get()['state'],'running')
            with patch.object(watch,'revision_diagnosis_properties',return_value={'MainPID':'0','Result':'exit-code'}):
                self.assertEqual(get()['state'],'error')


if __name__=='__main__':unittest.main()
