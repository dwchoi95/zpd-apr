"""Synthetic action-crossfit accounting, leakage and sealed-artifact tests."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import run_zpd_history_action_cv as cv
from scripts import zpd_history_action_encoder as encoder


def fixture(n=40):
    observations=[]; targets={}
    for i in range(n):
        code='x = 0\n'; ident=f'p1:s{i}'
        observations.append(dict(example_id=ident,user_id='u'+str(i),problem_id='p1',split='train',timestamp=100+i*10,
            current_code=code,current_verdict='WA',matching_current_verdict='Wrong Answer',
            current_source_sha256=hashlib.sha256(code.encode()).hexdigest(),
            history=[dict(code='x = 2\n',verdict='WA',timestamp=90+i*10,language='Python')]))
        targets[ident]=dict(target_status='available',next_code=code if i%3==0 else 'x = 1\n',next_language='Python')
    return observations,targets


class ActionCVTests(unittest.TestCase):
    def make_input_tree(self, root):
        prepared=root/'outputs/zpd-history-gate-20260915/prepared-inputs'
        original=root/'outputs/zpd-history-gate-20260915/original-prefixes'
        successors=root/'outputs/zpd-train-successors-20260923/prepared-train-v1'
        for path in (prepared,original,successors):path.mkdir(parents=True)
        features=[]; codes=[]; bindings={}; targets=[]
        for i,split in enumerate(('train','train','valid','test')):
            ident=f'p1:s{i}';prior=f'p1:h{i}';code=f'x = {i}\n'
            f=dict(example_id=ident,user_id=f'u{i}',problem_id='p1',split=split,timestamp=20,
                current_code_id=ident,current_verdict='WA',matching_current_verdict='Wrong Answer',
                history=[dict(code_id=prior,verdict='WA',timestamp=10)],donor_example_id=None)
            features.append(f)
            for key,text in [(ident,code),(prior,'x = -1\n')]:
                digest=hashlib.sha256(text.encode()).hexdigest()
                codes.append(dict(code_id=key,code=text,source_sha256=digest))
                bindings['/raw/p1/Python/'+key.split(':')[1]+'.py']=digest
            if split!='train':continue
            target={key:None for key in cv.TARGET_FIELDS}
            target.update(example_id=ident,user_id=f'u{i}',problem_id='p1',split='train',
                current_submission_id=f's{i}',current_timestamp=20,current_nominal_verdict='Wrong Answer',
                legacy_next_label='AC',next_submission_id=f'n{i}',next_timestamp=30,next_nominal_verdict='Accepted',
                next_label='AC',next_language='Python',next_filename_ext='py',next_source_path_relative=f'p1/Python/n{i}.py',
                next_source_sha256=hashlib.sha256(b'x = 9\n').hexdigest(),next_source_bytes=6,
                next_code='x = 9\n',target_status='available')
            targets.append(target)
        cv.atomic_rows(prepared/'features.jsonl',features);cv.atomic_rows(prepared/'codes.jsonl',codes)
        cv.atomic_json(original/'manifest.json',dict(source_sha256=bindings))
        cv.atomic_json(prepared/'manifest.json',dict(counts={'train':2,'valid':1,'test':1},
            source_manifest_sha256=cv.sha(original/'manifest.json'),file_sha256={name:cv.sha(prepared/name)
                for name in ('features.jsonl','codes.jsonl')}))
        cv.atomic_rows(successors/'targets-train.jsonl',targets)
        manifest=dict(kind='label_only_immediate_training_successors',valid_test_labels_opened=False,
            combined_original_labels_opened=False,prepared_manifest_sha256=cv.sha(prepared/'manifest.json'),
            original_manifest_sha256=cv.sha(original/'manifest.json'),protocol_sha256='f'*64,
            output_sha256={'targets-train.jsonl':cv.sha(successors/'targets-train.jsonl')})
        cv.atomic_json(successors/'manifest.json',manifest)
        cv.atomic_json(successors/'COMPLETE.json',dict(status='complete',fitting_performed=False,
            manifest_sha256=cv.sha(successors/'manifest.json'),output_sha256=manifest['output_sha256'],
            protocol_sha256='f'*64,train_prefixes=2))
        return prepared,original,successors

    def test_loader_never_opens_any_label_or_raw_source_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prepared,original,successors=self.make_input_tree(root)
            original_open=Path.open
            def guarded(path,*args,**kwargs):
                self.assertFalse(path.name.startswith('labels'))
                self.assertFalse(str(path).startswith('/raw/'))
                return original_open(path,*args,**kwargs)
            with patch.object(Path,'open',guarded):
                observations,targets,coverage,bindings=cv.load_inputs(root,production=False)
            self.assertEqual(len(observations),2)
            self.assertEqual(set(targets),{'p1:s0','p1:s1'})
            self.assertTrue(all(set(h)=={'code','verdict','timestamp','language'} for o in observations for h in o['history']))
            self.assertFalse(any(key.startswith('next_') for o in observations for key in o))
            self.assertEqual(coverage['python_available'],2)
            self.assertEqual(coverage['observed_source_ids'],4)

    def test_loader_fails_on_seal_change_and_wrong_production_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,_,successors=self.make_input_tree(root)
            with self.assertRaisesRegex(ValueError,'frozen'):
                cv.load_inputs(root)
            with (successors/'targets-train.jsonl').open('a') as stream:stream.write(' ')
            with self.assertRaisesRegex(ValueError,'seal'):
                cv.load_inputs(root,production=False)

    def test_user_fold_and_donors_ignore_targets_and_are_training_only(self):
        observations,_=fixture(); assignment=cv.assign_folds(observations)
        self.assertEqual(assignment,cv.assign_folds(copy.deepcopy(observations)))
        for fold in range(cv.FOLDS):
            train,held,donors=cv.fold_cohorts(observations,assignment,fold)
            lookup={o['example_id']:o for o in observations}
            self.assertTrue(len(train) and len(held))
            for i in np.concatenate([train,held]):
                row=observations[i]; donor=lookup[donors[row['example_id']]]
                self.assertNotEqual(assignment['user_fold'][donor['user_id']],fold)
                self.assertNotEqual(donor['user_id'],row['user_id'])
                self.assertLess(donor['timestamp'],row['timestamp'])
            self.assertFalse({observations[i]['user_id'] for i in train}&{observations[i]['user_id'] for i in held})

    def test_fixed_common_label_weights_no_head_renormalization(self):
        users=['a','a','b','c']; mask=np.array([[1,1],[1,0],[0,1],[0,0]],dtype=bool)
        w=cv.label_weights(users,mask)
        np.testing.assert_allclose(w,[.375,.75,1.5,0.])
        self.assertAlmostEqual(float(np.sum(w[:,None]*mask)),3.)
        self.assertAlmostEqual(float(np.sum(w[:2,None]*mask[:2])),1.5)
        x=sparse.csr_matrix((4,cv.HASH_DIMENSION)); y=np.zeros_like(mask,dtype=float);y[0,0]=1.
        with patch.object(cv,'EPOCHS',1):
            model=cv.fit_heads(x,y,mask,users,['mixed','constant'])
        self.assertAlmostEqual(model['heads'][0]['total_weight'],1.125)
        self.assertAlmostEqual(model['heads'][1]['total_weight'],1.875)
        self.assertAlmostEqual(model['heads'][1]['probability'],1/3.875)

    def test_zero_and_one_class_priors_and_serialized_prediction(self):
        x=sparse.csr_matrix((3,cv.HASH_DIMENSION));y=np.array([[1,0],[1,0],[1,0]],dtype=float)
        mask=np.array([[1,0],[1,0],[1,0]],dtype=bool)
        model=cv.fit_heads(x,y,mask,['a','b','c'],['one','zero'])
        self.assertEqual(model['heads'][0]['probability'],4/5)
        self.assertEqual(model['heads'][1]['probability'],.5)
        roundtrip=json.loads(json.dumps(model))
        with patch.object(cv.SGDClassifier,'partial_fit',side_effect=AssertionError('prediction fit')):
            np.testing.assert_allclose(cv.predict_heads(roundtrip,x),[[.8,.5]]*3)

    def test_masked_nll_is_prefix_then_user_equal_not_micro(self):
        predictions=[]
        for i,(user,mask,p) in enumerate([('a',[True,True],[.9,.8]),('a',[True,False],[.5,.9]),('b',[False,True],[.1,.4]),('c',[False,False],[.1,.1])]):
            predictions.append(dict(example_id=str(i),user_id=user,values=[1.,1.],mask=mask,
                probabilities={arm:p for arm in cv.ARMS}))
        result,users=cv.summarize_predictions(predictions,['x','y'])
        a=((-np.log(.9)-np.log(.8))/2-np.log(.5))/2
        expected=(a-np.log(.4))/2
        self.assertAlmostEqual(result['H']['user_equal_masked_nll'],expected)
        self.assertEqual(result['H']['all_masked_prefixes'],1)
        self.assertEqual(set(users['H']),{'a','b'})

    def test_bootstrap_shared_resamples_and_four_contrast_gate(self):
        users={arm:{'a':1.,'b':2.,'c':3.} for arm in cv.ARMS}
        users['H']={key:value-.2 for key,value in users['H'].items()}
        intervals=cv.bootstrap_contrasts(users,draws=100)
        self.assertEqual(set(intervals),set(('Cn','U','HS','L')))
        for value in intervals.values():
            self.assertAlmostEqual(value['upper'],-.2)
        overall={arm:dict(user_equal_masked_nll=.8 if arm=='H' else 1.) for arm in cv.ARMS}
        folds={str(i):copy.deepcopy(overall) for i in range(cv.FOLDS)}
        self.assertTrue(cv.decision(overall,folds,intervals)['gate_passed'])
        folds['0']['H']['user_equal_masked_nll']=1.
        self.assertTrue(cv.decision(overall,folds,intervals)['gate_passed'])
        folds['1']['H']['user_equal_masked_nll']=1.
        self.assertFalse(cv.decision(overall,folds,intervals)['gate_passed'])
        intervals['L']['upper']=0.
        self.assertFalse(cv.decision(overall,{str(i):overall for i in range(5)},intervals)['gate_passed'])

    def test_u_and_l_keep_all_authentic_nuisance_without_target_access(self):
        observations,_=fixture(3)
        observations[2]['history'].insert(0,dict(code='x = 7\n',verdict='WA',timestamp=1,language='Python'))
        received=[]
        class RecordingEncoder:
            @staticmethod
            def encode_observation(code,verdict,history,timestamp,arm,shuffle_key=''):
                self.assertNotIn('next_code',history[0])
                bag={'current:x':1.,'nuisance:count':float(len(history)),'nuisance:elapsed':float(timestamp-history[0]['timestamp'])}
                if arm=='H':bag['history:value']=float(history[0]['timestamp'])
                received.append((arm,len(history),dict(bag)))
                return bag
        l=cv.encode_matrix(observations,[2],'L',RecordingEncoder)
        self.assertEqual([(a,n) for a,n,_ in received],[('H',1),('Cn',2)])
        expected=dict(received[0][2]);expected.update(received[1][2])
        want=cv.normalize(cv.FeatureHasher(n_features=cv.HASH_DIMENSION,input_type='dict',alternate_sign=True).transform([expected]))
        np.testing.assert_array_equal(l.toarray(),want.toarray())
        received.clear()
        cv.encode_matrix(observations,[2],'U',RecordingEncoder,donors={observations[2]['example_id']:observations[0]['example_id']})
        self.assertEqual([(a,n) for a,n,_ in received],[('H',1),('Cn',2)])

    def test_missing_target_masks_do_not_remove_prefix_or_change_features(self):
        observations,targets=fixture(3)
        before=cv.encode_matrix(observations,np.arange(3),'H',encoder)
        targets[observations[1]['example_id']]=dict(target_status='unavailable',next_code=None,next_language=None)
        values,mask=cv.encode_targets(observations,targets,encoder)
        self.assertEqual(values.shape,(3,len(encoder.EVENTS)))
        self.assertFalse(mask[1].any())
        after=cv.encode_matrix(observations,np.arange(3),'H',encoder)
        self.assertEqual((before!=after).nnz,0)

    def test_extreme_probability_clipping_matches_protocol(self):
        row=dict(user_id='a',values=[1.,0.],mask=[True,True],probabilities={arm:[0.,1.] for arm in cv.ARMS})
        result,_=cv.summarize_predictions([row],['x','y'])
        expected=(-np.log(1e-12)-np.log(1-(1-1e-12)))/2
        self.assertAlmostEqual(result['H']['user_equal_masked_nll'],expected)

    def test_complete_synthetic_run_seals_and_rejects_reuse(self):
        observations,targets=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'run'
            # Smaller synthetic budget only; production constants are unchanged.
            with patch.object(cv,'EPOCHS',1),patch.object(cv,'bootstrap_contrasts',wraps=lambda users: original_bootstrap(users,draws=50)),contextlib.redirect_stdout(io.StringIO()):
                report=cv.run_data(observations,targets,output,encoder,manifest={'synthetic':True})
            marker=cv.verify_run_artifacts(output)
            self.assertEqual(marker['completed_arms'],30)
            self.assertEqual(report['decision']['gate_passed'],False)  # H == L for one prior record.
            predictions=[r for fold in range(5) for r in cv.rows(output/f'fold-{fold}/predictions.jsonl')]
            self.assertTrue(all(set(r['probabilities'])==set(cv.ARMS) for r in predictions))
            self.assertTrue(all(r['hs_prior_length_one'] and r['hs_permutation_identity'] and r['hs_hashed_features_equal'] for r in predictions))
            with self.assertRaises(FileExistsError):
                cv.run_data(observations,targets,output,encoder,manifest={})
            (output/'fold-0/summary.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'seal'):
                cv.verify_run_artifacts(output)


original_bootstrap=cv.bootstrap_contrasts


if __name__=='__main__':
    unittest.main()
