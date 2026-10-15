from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_paired_inference_recovery as m
from scripts import watch_zpd_completion as observer


class RecoveryTests(unittest.TestCase):
    def fixture(self):
        previous=dict(family_path=str(m.parent.FAMILY), phases=list(m.parent.PHASES),
            source_sha256={'scripts/generate_zpd_paired_history.py':'a'},
            adapter_C='C',adapter_H='H',inputs_sha256='input',tokenization_sha256='tokens',
            seed=2027,no_retry=True,retries=0,training_configuration={'epochs':1})
        release=deepcopy(previous)
        release.update(family_path=str(m.FAMILY),phases=list(m.PHASES),recovery=m.amendment())
        release['source_sha256'].update({name:'a' for name in m.REQUIRED})
        return previous,release

    def test_only_transport_namespace_and_source_registration_change(self):
        previous,release=self.fixture();m.validate_amendment(release,previous)
        for key,value in [('adapter_C','other'),('inputs_sha256','other'),('seed',42),
                          ('retries',1),('training_configuration',{'epochs':2})]:
            bad=deepcopy(release);bad[key]=value
            with self.assertRaisesRegex(ValueError,'scientific'):m.validate_amendment(bad,previous)

    def test_original_generator_change_rejected(self):
        previous,release=self.fixture()
        release['source_sha256']['scripts/generate_zpd_paired_history.py']='b'
        with self.assertRaisesRegex(ValueError,'algorithm pin'):m.validate_amendment(release,previous)

    def test_missing_required_source_and_unregistered_amendment_rejected(self):
        previous,release=self.fixture();release['source_sha256'].pop(next(iter(m.REQUIRED)))
        with self.assertRaisesRegex(ValueError,'missing'):m.validate_amendment(release,previous)
        previous,release=self.fixture();release['recovery']['training_repeated']=True
        with self.assertRaisesRegex(ValueError,'exact IPC'):m.validate_amendment(release,previous)

    def test_old_path_fails_and_short_in_project_path_passes(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temp:
            root=Path(temp).resolve()
            self.assertEqual(m.validate_rpc_path(root/'tmp/i',root),root/'tmp/i')
            with self.assertRaisesRegex(ValueError,'byte limit'):
                m.validate_rpc_path(root/'tmp'/('x'*80),root)
            with self.assertRaisesRegex(ValueError,'in-project'):
                m.validate_rpc_path(root/'elsewhere',root)
            (root/'tmp').mkdir();(root/'tmp/link').symlink_to(root/'tmp')
            with self.assertRaisesRegex(ValueError,'canonical'):
                m.validate_rpc_path(root/'tmp/link',root)

    def test_short_path_is_below_actual_linux_socket_limit(self):
        old=m.parent.FAMILY/'tmp/generation'/'00000000-0000-0000-0000-000000000000'
        new=m.RPC_BASE/'00000000-0000-0000-0000-000000000000'
        self.assertGreater(len(str(old).encode()),107)
        self.assertLessEqual(len(str(new).encode()),107)

    def test_wrapper_scope_restored_even_on_failure(self):
        before=(m.driver.FAMILY,m.driver.command,m.core.FAMILY,m.core.generation)
        with self.assertRaisesRegex(RuntimeError,'test'):
            with m.configured():
                self.assertEqual(m.core.FAMILY,m.FAMILY)
                self.assertIs(m.core.generation,m.generation)
                raise RuntimeError('test')
        self.assertEqual(before,(m.driver.FAMILY,m.driver.command,m.core.FAMILY,m.core.generation))

    def test_commands_use_new_units_no_training_and_explicit_short_ipc(self):
        with m.configured():
            for phase in m.PHASES:
                command=m.command(phase,Path('/snapshot/release.json'),'a'*64,Path('/snapshot'))
                self.assertIn('--unit='+m.UNIT_PREFIX+'-'+phase+'.service',command)
                self.assertIn('scripts.run_zpd_paired_inference_recovery',command)
                self.assertNotIn('scripts.run_zpd_full_source',command)
                self.assertIn('--setenv=VLLM_RPC_BASE_PATH='+str(m.RPC_BASE),command)
                self.assertIn('--setenv=TMPDIR='+str(m.RPC_BASE),command)
                self.assertIn('--property=Restart=no',command)
                self.assertIn('--property=RuntimeMaxSec=21600',command)
        self.assertEqual(m.PHASES,('generation','public','private'))

    def test_active_parent_prevents_release(self):
        # This rejects before any generation, directory creation or model access.
        with patch.object(m,'verify_parent',side_effect=ValueError('parent unit still owns processes')), \
             patch.object(m.core,'clean_source',return_value='rev'), \
             patch.object(m.Path,'cwd',return_value=Path(m.__file__).resolve().parents[1]), \
             patch.object(m.core,'load_release',return_value={'source_sha256':{}}):
            with self.assertRaisesRegex(ValueError,'parent unit'):
                m.source_barrier(Path(m.__file__).resolve().parents[1]/'release.json','a'*64)


class RecoveryObserverTests(unittest.TestCase):
    def test_unverified_recovery_certificate_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp);root=project/'outputs'/observer.RECOVERY_FAMILY
            root.mkdir(parents=True)
            (root/'COORDINATOR.json').write_text(json.dumps({'release_sha256':'a'*64}))
            (root/'VERIFIED_COMPLETE.json').write_text(json.dumps({'status':'complete','phases':{}}))
            row=observer.remote_snapshot(project)['experiments'][-1]
            self.assertEqual(row['state'],'error')
            self.assertEqual(row['release_sha256'],'a'*64)

    def test_registered_recovery_reads_current_parent_phase_not_stale_generation(self):
        with tempfile.TemporaryDirectory() as temp:
            project=Path(temp);root=project/'outputs'/observer.RECOVERY_FAMILY
            (root/'generation-v1').mkdir(parents=True);(root/'public-v1').mkdir()
            (root/'COORDINATOR.json').write_text(json.dumps({'release_sha256':'a'*64}))
            (root/'STATUS.json').write_text(json.dumps({'phase':'public','completed_phases':['generation']}))
            (root/'generation-v1/STATUS.json').write_text(json.dumps({'phase':'generation','completed_examples':320}))
            (root/'public-v1/STATUS.json').write_text(json.dumps({'phase':'public_selection','completed_examples':12,'total_examples':320}))
            row=observer.remote_snapshot(project)['experiments'][-1]
            self.assertEqual(row['completed_examples'],12);self.assertEqual(row['phase'],'public')
            self.assertEqual(row['release_sha256'],'a'*64);self.assertEqual(row['state'],'running')
            self.assertIn('공개 샘플 선택',observer.korean_report({'checked_at':'2026-10-16T06:00:00+09:00','experiments':[row]}))


if __name__=='__main__':unittest.main()
