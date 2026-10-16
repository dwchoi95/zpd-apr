"""No model or sandbox execution: fixed missing-only scope and lifecycle tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_anchored_diagnosis as m
from scripts import watch_zpd_completion as observer
from tests.test_diagnose_zpd_transition_failure import fixture, serialized


def loaded_fixture():
    inputs,attempts,predictions,vectors=fixture()
    manifest=dict(runtime={},runtime_sha256='b'*64,testcase_files_sha256={},input_sha256='c'*64)
    return dict(inputs=inputs,attempts=attempts,predictions=predictions,vector_map=vectors,
                vectors=serialized(vectors),manifest=manifest,
                pins={'private-v1/evaluation/vectors.json':'d'*64})


class AnchoredDiagnosisTests(unittest.TestCase):
    def test_bundle_missing_only_exact_memberships(self):
        loaded=loaded_fixture();bundle=m.make_bundle(loaded)
        with m.configured(dict(original_vectors_sha256='d'*64)):
            tasks=m.replay.validate_tasks(bundle,loaded['vectors'],len(bundle['tasks']))
            m.replay.recipient_memberships(bundle,tasks,2)
        self.assertFalse(set(tasks)&set(loaded['vector_map']))
        self.assertFalse(bundle['generation_authorized'])
        self.assertFalse(bundle['retry_existing_vectors'])
        self.assertFalse(bundle['selection_changes_authorized'])
        self.assertEqual(bundle['total_planned_case_attempts'],4*len(tasks))

    def test_command_uses_new_family_and_bounded_worker(self):
        with m.configured(dict(original_vectors_sha256='a'*64)):
            cmd=m.command(Path('/snapshot'),Path('/snapshot/release.json'),'b'*64)
        self.assertIn('--unit='+m.UNIT,cmd)
        self.assertIn('scripts.run_zpd_anchored_diagnosis',cmd)
        self.assertIn('--property=RuntimeMaxSec=21600',cmd)
        self.assertIn('--property=TasksMax=128',cmd)
        self.assertNotIn('scripts.run_zpd_transition_missing_replay',cmd)

    def test_scoped_patch_restores_even_on_error(self):
        old=(m.replay.ROOT,m.replay.UNIT,m.replay.command,m.replay.source_barrier)
        with self.assertRaises(RuntimeError):
            with m.configured(dict(original_vectors_sha256='a'*64)):
                self.assertEqual(m.replay.ROOT,m.ROOT)
                raise RuntimeError('synthetic')
        self.assertEqual(old,(m.replay.ROOT,m.replay.UNIT,m.replay.command,m.replay.source_barrier))

    def test_selected_unknown_and_success_are_invariants(self):
        report=dict(per_arm={a:dict(selected_stable_ac=m.SELECTED[a],selected_unknown=m.UNKNOWN[a]) for a in m.diag.ARMS})
        m.verify_selected(report)
        for field in ('selected_stable_ac','selected_unknown'):
            bad=copy.deepcopy(report);bad['per_arm']['H'][field]+=1
            with self.assertRaises(ValueError):m.verify_selected(bad)

    def test_duplicate_rejected_without_stopping_someone_elses_worker(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp).resolve()), \
                patch.object(m.recovery,'properties',return_value={'LoadState':'loaded'}), \
                patch.object(m.subprocess,'run') as run:
            with self.assertRaises(ValueError):m.supervise(Path('/s'),{},Path('/r'),'r')
            run.assert_not_called()

    def test_own_failed_worker_is_stopped_without_retry(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(m,'ROOT',Path(temp).resolve()), \
                patch.object(m.recovery,'properties',return_value={'LoadState':'not-found'}), \
                patch.object(m.subprocess,'run') as run:
            def fail(*args):
                (Path(temp)/'COORDINATOR.json').write_text(json.dumps(dict(release_sha256='r')))
                raise ValueError('synthetic')
            with patch.object(m.replay,'supervise',side_effect=fail) as call:
                with self.assertRaisesRegex(ValueError,'synthetic'):m.supervise(Path('/s'),{},Path('/r'),'r')
                call.assert_called_once()
            run.assert_called_once_with(['/usr/bin/systemctl','--user','stop',m.UNIT],check=True,timeout=30)

    def test_observer_reads_release_and_test_progress(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'outputs'/observer.DIAGNOSIS_FAMILY
            (root/'run-v1').mkdir(parents=True)
            (root/'COORDINATOR.json').write_text(json.dumps(dict(release_sha256='a'*64)))
            (root/'run-v1/STATUS.json').write_text(json.dumps(dict(phase='missing_candidate_replay',
                completed_examples=17,total_examples=320,completed_case_attempts=300,total_case_attempts=44420,
                completed_unique_sources=0,total_unique_sources=544,elapsed_seconds=10)))
            snapshot=observer.remote_snapshot(Path(temp))
            row=next(r for r in snapshot['experiments'] if r['family']==observer.DIAGNOSIS_FAMILY)
            self.assertEqual(row['state'],'running');self.assertEqual(row['release_sha256'],'a'*64)
            self.assertEqual(row['completed_case_attempts'],300)
            report=observer.korean_report(snapshot)
            self.assertIn('17/320',report);self.assertIn('블록별 병렬도 차이',report)

    def test_observer_does_not_accept_incomplete_certificate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'outputs'/observer.DIAGNOSIS_FAMILY;root.mkdir(parents=True)
            (root/'COORDINATOR.json').write_text(json.dumps(dict(release_sha256='a'*64)))
            (root/'VERIFIED_COMPLETE.json').write_text(json.dumps(dict(release_sha256='a'*64,status='complete',
                worker_certificate_sha256='b'*64)))
            row=next(r for r in observer.remote_snapshot(Path(temp))['experiments'] if r['family']==observer.DIAGNOSIS_FAMILY)
            self.assertEqual(row['state'],'error')


if __name__=='__main__':unittest.main()
