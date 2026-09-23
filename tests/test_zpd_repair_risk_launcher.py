import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_zpd_repair_risk_development import verify_generator_config, verify_prepared
from scripts.run_zpd_repair_replication import verify_files
from scripts.run_zpd_repair_pairwise_replication import FROZEN_SOURCE


class RiskLauncherTests(unittest.TestCase):
    def preparation(self):
        base = Path('/fixture')
        prepared, data = base/'prepared', base/'data'
        parents = {k:base/k for k in ('original','replication','next')}
        manifests, contents = {}, {}
        for index,(name,path) in enumerate(parents.items()):
            manifests[path/'manifest.json'] = {'output_sha256':{'observations.jsonl':'fixture'},'input_sha256':{'codes':'same'}}
            size = 96 if index == 0 else 128
            contents[path/'observations.jsonl'] = [dict(user_id=f'{name}{i}',observation={
                'current':{'source_sha256':f'{name}{i}'},'prior':[]},donor_history=[]) for i in range(size)]
        new = [dict(user_id=f'new{i}',split='train',bank_id=f'b{i}',observation={
            'problem_id':'p','current':{'source_sha256':f'new{i}','source':f'new code {i}'}}) for i in range(256)]
        requests = [dict(bank_id=r['bank_id'],problem_id='p',current_source=r['observation']['current']['source']) for r in new]
        contents[prepared/'observations.jsonl'] = new
        contents[prepared/'requests.jsonl'] = requests
        for i in range(4):contents[prepared/f'requests-{i}.jsonl'] = requests[i*64:(i+1)*64]
        manifests[prepared/'manifest.json'] = dict(split='train',sample_size=256,
            previous_selected_rows=352,previous_users=352,selection_salt='repair-training-20260923-v1',
            request_batch_size=64,request_banks=256,input_sha256={'codes':'same'},data_sha256={'p/testcases.jsonl':'fixture'},
            previous_manifest_sha256={k:str(v/'manifest.json') for k,v in parents.items()},
            previous_output_sha256={k:manifests[v/'manifest.json']['output_sha256'] for k,v in parents.items()},
            output_sha256={k:'fixture' for k in ('observations.jsonl','requests.jsonl','exclusions.jsonl',
                                                'requests-0.jsonl','requests-1.jsonl','requests-2.jsonl','requests-3.jsonl')})
        return prepared,data,parents,manifests,contents

    def check_prepared(self, fixture):
        prepared,data,parents,manifests,contents = fixture
        module = 'scripts.run_zpd_repair_risk_development.'
        with patch(module+'read',side_effect=lambda p:manifests[p]), patch(module+'rows',side_effect=lambda p:contents[p]), \
             patch(module+'sha',side_effect=str), patch(module+'verify_files') as checksums:
            try:
                return verify_prepared(prepared,parents,data)
            finally:
                self.checksum_reads = checksums.call_count

    def test_training_chunks_and_fixed_sample(self):
        f = self.preparation()
        self.assertEqual(self.check_prepared(f)[1],4)
        f[3][f[0]/'manifest.json']['split'] = 'valid'
        with self.assertRaisesRegex(ValueError,'contract'):
            self.check_prepared(f)

    def test_previous_user_and_source_overlap_rejected(self):
        f = self.preparation()
        f[4][f[0]/'observations.jsonl'][0]['user_id'] = 'original0'
        with self.assertRaisesRegex(ValueError,'user exclusion'):
            self.check_prepared(f)
        f = self.preparation()
        f[4][f[0]/'observations.jsonl'][0]['observation']['current']['source_sha256'] = 'next0'
        with self.assertRaisesRegex(ValueError,'source/new current'):
            self.check_prepared(f)

    def test_bad_chunk_or_ancestor_rejected(self):
        f = self.preparation()
        f[4][f[0]/'requests-0.jsonl'] = f[4][f[0]/'requests-0.jsonl'][:-1]
        with self.assertRaisesRegex(ValueError,'chunk coverage'):
            self.check_prepared(f)
        f = self.preparation()
        f[3][f[0]/'manifest.json']['previous_manifest_sha256']['next'] = 'wrong'
        with self.assertRaisesRegex(ValueError,'ancestor manifest'):
            self.check_prepared(f)

    def test_outcome_path_rejected_before_checksumming(self):
        f = self.preparation()
        f[3][f[0]/'manifest.json']['output_sha256']['labels.jsonl'] = 'bad'
        with self.assertRaisesRegex(ValueError,'preparation artifacts'):
            self.check_prepared(f)
        self.assertEqual(self.checksum_reads,0)

    def test_request_source_mismatch_rejected(self):
        f = self.preparation()
        f[4][f[0]/'requests.jsonl'][0]['current_source'] = 'wrong source'
        with self.assertRaisesRegex(ValueError,'source mismatch'):
            self.check_prepared(f)

    def test_frozen_implementations_remain_unchanged(self):
        verify_files(Path(__file__).resolve().parents[1], FROZEN_SOURCE)

    def test_only_generator_source_root_is_normalized(self):
        previous = {'budget':8,'weights':{'model':'sha'},'source_sha256':{
            '/old/scripts/generate_zpd_repair_banks.py':'abc','src/repair/prompts.py':'def'}}
        current = copy.deepcopy(previous)
        current['source_sha256']['/new/scripts/generate_zpd_repair_banks.py'] = current['source_sha256'].pop('/old/scripts/generate_zpd_repair_banks.py')
        verify_generator_config(current, previous)
        current['budget'] = 9
        with self.assertRaisesRegex(ValueError, 'config drift'):
            verify_generator_config(current, previous)

    def test_changed_source_or_missing_field_rejected(self):
        previous = {'budget':8,'source_sha256':{'src/a.py':'old'}}
        with self.assertRaisesRegex(ValueError,'source drift'):
            verify_generator_config({'budget':8,'source_sha256':{'src/a.py':'new'}}, previous)
        with self.assertRaisesRegex(ValueError,'fields changed'):
            verify_generator_config({'budget':8}, previous)


if __name__ == '__main__':
    unittest.main()
