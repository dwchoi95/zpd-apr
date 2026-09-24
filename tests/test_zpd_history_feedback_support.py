"""Observed-only loader/cohort tests: future stores must not be opened."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_zpd_history_feedback_support as support
from scripts import run_zpd_history_action_cv as cv


def prepare(root):
    prepared=root/'outputs/zpd-history-gate-20260915/prepared-inputs'
    original=root/'outputs/zpd-history-gate-20260915/original-prefixes'
    prepared.mkdir(parents=True); original.mkdir(parents=True)
    features=[]; codes=[]; sources={}
    for i,split in enumerate(('train','train','valid','test')):
        ident=f'p1:s{i}'; prior=f'p1:h{i}'
        features.append(dict(example_id=ident,user_id=f'u{i}',problem_id='p1',split=split,
            timestamp=20,current_code_id=ident,current_verdict='WA',matching_current_verdict='Wrong Answer',
            history=[dict(code_id=prior,verdict='WA',timestamp=10)],donor_example_id=None))
        for key,code in ((ident,f'x = {i}\n'),(prior,'x = -1\n')):
            digest=hashlib.sha256(code.encode()).hexdigest()
            codes.append(dict(code_id=key,code=code,source_sha256=digest))
            sources['/raw/p1/Python/'+key.split(':')[1]+'.py']=digest
    # A code outside observed TRAIN prefixes is not an observation input.
    codes.append(dict(code_id='not-observed-future',code=None,source_sha256='bad'))
    cv.atomic_rows(prepared/'features.jsonl',features)
    cv.atomic_rows(prepared/'codes.jsonl',codes)
    cv.atomic_json(original/'manifest.json',dict(source_sha256=sources))
    cv.atomic_json(prepared/'manifest.json',dict(counts={'train':2,'valid':1,'test':1},
        source_manifest_sha256=cv.sha(original/'manifest.json'),file_sha256={name:cv.sha(prepared/name)
            for name in ('features.jsonl','codes.jsonl')}))
    return prepared,original


def observations(n=40):
    return [dict(example_id=f'p1:s{i}',user_id=f'u{i}',problem_id='p1',split='train',timestamp=100+i*10,
        current_code='x=0\n',current_verdict='WA',matching_current_verdict='Wrong Answer',
        current_source_sha256=hashlib.sha256(b'x=0\n').hexdigest(),
        history=[dict(code='x=2\n',verdict='WA',timestamp=90+i*10,language='Python')]) for i in range(n)]


def seal_cohorts(root, obs):
    parent=root/support.C2_FAMILY; parent.mkdir(parents=True)
    assignment=cv.assign_folds(obs); cv.atomic_json(parent/'folds.json',assignment)
    cohort_hashes={}; names=['folds.json','COHORTS_COMPLETE.json']
    for fold in range(5):
        train,held,donors=cv.fold_cohorts(obs,assignment,fold)
        frozen=dict(train_example_ids=[obs[i]['example_id'] for i in train],
                    held_example_ids=[obs[i]['example_id'] for i in held],donor_assignments=donors)
        cohort_hashes[str(fold)]=hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        name=f'fold-{fold}/cohort.json'; cv.atomic_json(parent/name,dict(fold=fold,**frozen));names.append(name)
    cv.atomic_json(parent/'COHORTS_COMPLETE.json',dict(fold_cohort_sha256=cohort_hashes))
    cv.atomic_json(parent/'COMPLETE.json',dict(status='complete',files_sha256={name:cv.sha(parent/name) for name in names}))
    return parent,assignment


class ObservedSupportTests(unittest.TestCase):
    def test_preflight_failure_is_recorded_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();output=root/support.FAMILY/'support-v1'
            with patch.object(support,'source_state',side_effect=ValueError('dirty snapshot')):
                with self.assertRaisesRegex(ValueError,'dirty snapshot'):
                    support.audit(root,output)
            failure=cv.read(output/'FAILED.json')
            self.assertEqual(failure,dict(error_type='ValueError',error='dirty snapshot'))
            self.assertFalse((output/'COMPLETE.json').exists())
            with self.assertRaisesRegex(ValueError,'new direct child'):
                support.audit(root,output)
            self.assertEqual(cv.read(output/'FAILED.json'),failure)

    def test_changed_inherited_c2_source_is_rejected_and_recorded(self):
        original_sha=support.sha
        def changed(path):
            if path == support.ROOT/'scripts/zpd_history_action_encoder.py':
                return '0'*64
            return original_sha(path)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();output=root/support.FAMILY/'support-v1'
            with patch.object(support,'source_state',return_value={'revision':'test','tree':'test'}), \
                    patch.object(support,'sha',side_effect=changed), \
                    patch.object(support,'load_observations') as load:
                with self.assertRaisesRegex(ValueError,'frozen C2 source mismatch'):
                    support.audit(root,output)
                load.assert_not_called()
            self.assertEqual(cv.read(output/'FAILED.json')['error'],'frozen C2 source mismatch')
            self.assertFalse((output/'COMPLETE.json').exists())

    def test_no_successor_outcome_or_raw_store_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); prepare(root); opened=[]; original_open=Path.open
            def guarded(path,*args,**kwargs):
                text=str(path); opened.append(text)
                self.assertNotIn('successor',text);self.assertNotIn('labels',text)
                self.assertNotIn('predictions',text);self.assertFalse(text.startswith('/raw/'))
                return original_open(path,*args,**kwargs)
            with patch.object(Path,'open',guarded):
                obs,coverage,bindings=support.load_observations(root,production=False)
            self.assertEqual([o['example_id'] for o in obs],['p1:s0','p1:s1'])
            self.assertEqual(coverage,dict(prefixes=2,users=2,problems=1,observed_source_ids=4))
            self.assertEqual(len(bindings),4)
            self.assertTrue(all(o['split']=='train' for o in obs))
            self.assertFalse(any(k.startswith('next_') for o in obs for k in o))
            self.assertTrue(all(set(h)=={'code','verdict','timestamp','language'} for o in obs for h in o['history']))

    def test_seals_and_production_population_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); prepared,_=prepare(root)
            with self.assertRaisesRegex(ValueError,'frozen'):
                support.load_observations(root)
            with (prepared/'codes.jsonl').open('a') as stream: stream.write(' ')
            with self.assertRaisesRegex(ValueError,'seal'):
                support.load_observations(root,production=False)

    def test_observed_join_matches_existing_supervised_observation_join_contract(self):
        # Assert the complete allowed observation keys without creating targets.
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prepare(root);obs,_,_=support.load_observations(root,production=False)
            self.assertEqual(set(obs[0]),{'example_id','user_id','problem_id','split','timestamp',
                'current_code','current_verdict','matching_current_verdict','current_source_sha256','history'})
            self.assertEqual(obs[0]['current_code'],'x = 0\n')
            self.assertEqual(obs[0]['history'][0]['code'],'x = -1\n')

    def test_cohorts_only_open_pretarget_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);obs=observations();parent,assignment=seal_cohorts(root,obs)
            original_open=Path.open
            def guarded(path,*args,**kwargs):
                self.assertIn(path.name,{'COMPLETE.json','COHORTS_COMPLETE.json','cohort.json','folds.json'})
                return original_open(path,*args,**kwargs)
            with patch.object(Path,'open',guarded):
                actual,cohorts,bindings=support.frozen_cohorts(root,obs,production=False)
            self.assertEqual(actual,assignment);self.assertEqual(len(cohorts),5)
            self.assertEqual(len(bindings),8)
            for fold,(train,held,donors) in cohorts.items():
                self.assertTrue(set(train).isdisjoint(held));self.assertTrue(donors)
                self.assertTrue(all(actual['user_fold'][obs[i]['user_id']]==fold for i in held))

    def test_resealed_changed_cohort_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);obs=observations();parent,_=seal_cohorts(root,obs)
            path=parent/'fold-0/cohort.json'; cohort=cv.read(path)
            cohort['held_example_ids']=list(reversed(cohort['held_example_ids']))
            cv.atomic_json(path,cohort);seal=cv.read(parent/'COMPLETE.json')
            seal['files_sha256']['fold-0/cohort.json']=cv.sha(path);cv.atomic_json(parent/'COMPLETE.json',seal)
            with self.assertRaisesRegex(ValueError,'cohort mismatch'):
                support.frozen_cohorts(root,obs,production=False)


if __name__=='__main__':
    unittest.main()
