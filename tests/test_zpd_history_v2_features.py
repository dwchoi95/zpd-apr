import copy
import importlib.util
import json
import unittest

import numpy as np

from scripts.zpd_history_predictor import features, code_vectors
from scripts.zpd_history_v2_features import (ARMS, HistoryV2Encoder, dimensions,
                                            reciprocal_weights, numeric_values)


def fixture():
    history = [{'code':'print(1)','verdict':'WA','timestamp':1},
               {'code':'print(2)','verdict':'WA','timestamp':2}]
    donor = [{'code':'print(3)','verdict':'RE','timestamp':1},
             {'code':'print(4)','verdict':'WA','timestamp':2}]
    return {'example_id':'a','user_id':'u','problem_id':'p','split':'train',
            'timestamp':3,'current_code':'print(2)','current_verdict':'WA',
            'history':history,'donor_history':donor,'next_label':'AC'}


class NumericV2Tests(unittest.TestCase):
    def test_reciprocal_weights(self):
        np.testing.assert_array_equal(reciprocal_weights(1),[1.])
        np.testing.assert_allclose(reciprocal_weights(2),[1/3,2/3])
        with self.assertRaises(ValueError):
            reciprocal_weights(0)

    def test_weighted_scaler_and_constant_columns(self):
        rows=[fixture(),dict(fixture(),example_id='b'),
              dict(fixture(),example_id='c',user_id='v',current_code='print(1234567)',timestamp=10)]
        weights=np.array([.25,.25,.5])
        encoder=HistoryV2Encoder(16).fit(rows,weights)
        values=numeric_values(rows)
        expected=(weights[:,None]*values).sum(axis=0)
        np.testing.assert_allclose(encoder.mean,expected)
        np.testing.assert_allclose(encoder.variance,(weights[:,None]*(values-expected)**2).sum(axis=0),atol=1e-28)
        self.assertEqual(encoder.scale[1],1)
        self.assertEqual(encoder.variance[1],0)
        with self.assertRaises(RuntimeError):
            encoder.fit(rows,weights)
        with self.assertRaises(ValueError):
            HistoryV2Encoder().fit(rows,[1,1,1])

    def test_scaler_train_only_and_json_roundtrip(self):
        encoder=HistoryV2Encoder(16).fit([fixture()],[1])
        state=json.loads(json.dumps(encoder.state_dict()))
        recovered=HistoryV2Encoder.from_state_dict(state)
        self.assertEqual(recovered.state_dict(),state)
        for split in ('valid','test'):
            with self.assertRaises(ValueError):
                HistoryV2Encoder().fit([dict(fixture(),split=split)],[1])
        with self.assertRaises(ValueError):
            HistoryV2Encoder().fit([dict(fixture(),donor_history=None)],[1])

    def test_dimensions_and_allowlist(self):
        self.assertEqual(dimensions('C_R',16),42)
        self.assertEqual(dimensions('H_PR',16),122)
        self.assertEqual(dimensions('H_IR',16),188)
        self.assertEqual(dimensions('S_MZ',16),51)
        encoder=HistoryV2Encoder(16).fit([fixture()],[1])
        self.assertEqual(encoder.state_dict()['columns']['H_IZ'],[39,40,41])


@unittest.skipUnless(importlib.util.find_spec('sklearn'), 'requires frozen sklearn/scipy')
class SparseV2Tests(unittest.TestCase):
    def setUp(self):
        self.row=fixture()
        self.n=32
        self.encoder=HistoryV2Encoder(self.n).fit([self.row],[1])

    def test_raw_pooled_conditions_identical_to_frozen(self):
        for arm,base in [('C_R','C'),('H_PR','H'),('U_PR','U'),('S_MR','S')]:
            np.testing.assert_array_equal(self.encoder.transform([self.row],arm).toarray(),
                                          features([self.row],base,self.n).toarray())

    def test_recency_order_sensitive_pooled_invariant(self):
        altered=copy.deepcopy(self.row)
        altered['history'][0]['code'],altered['history'][1]['code']=altered['history'][1]['code'],altered['history'][0]['code']
        np.testing.assert_allclose(self.encoder.transform([self.row],'H_PR').toarray(),
                                   self.encoder.transform([altered],'H_PR').toarray())
        self.assertGreater(np.max(np.abs((self.encoder.transform([self.row],'H_IR')-
                                          self.encoder.transform([altered],'H_IR')).toarray())),1e-6)

    def test_raw_distance_and_normalized_additional_blocks(self):
        matrix=self.encoder.transform([self.row],'H_IR').toarray()[0]
        current=code_vectors([self.row['current_code']],self.n).toarray()[0]
        prior=code_vectors([h['code'] for h in self.row['history']],self.n).toarray()
        recency=(prior*np.array([1/3,2/3])[:,None]).sum(axis=0)
        expected=[np.linalg.norm(current[s:s+self.n]-recency[s:s+self.n]) for s in (0,self.n)]
        np.testing.assert_allclose(matrix[-2:],expected)
        offset=dimensions('H_PR',self.n)
        for start in range(offset,offset+4*self.n,self.n):
            norm=np.linalg.norm(matrix[start:start+self.n])
            self.assertTrue(abs(norm-1)<1e-12 or norm==0)
        np.testing.assert_allclose(matrix[-2:],self.encoder.transform([self.row],'H_IZ').toarray()[0,-2:])

    def test_identical_and_zero_distance_finite(self):
        for code in ('print(2)',''):
            row=copy.deepcopy(self.row)
            row['current_code']=code
            for h in row['history']:
                h['code']=code
            matrix=self.encoder.transform([row],'H_IR')
            self.assertTrue(np.isfinite(matrix.data).all())
            np.testing.assert_allclose(matrix.toarray()[0,-2:],0,atol=1e-14)

    def test_u_all_history_blocks_replaced_current_unchanged(self):
        altered=copy.deepcopy(self.row)
        altered['history']=copy.deepcopy(self.row['donor_history'])
        # Identical history depth/first timestamp retain common recipient nuisance.
        u=self.encoder.transform([self.row],'U_IR').toarray()
        h=self.encoder.transform([altered],'H_IR').toarray()
        np.testing.assert_array_equal(u,h)
        np.testing.assert_array_equal(u[:,:2*self.n+10],features([self.row],'C',self.n).toarray())

    def test_scaling_only_allowlist_no_validation_fit_or_label_features(self):
        valid=dict(self.row,split='valid',example_id='new',user_id='newuser',next_label='OTHER',future_code='secret')
        before=self.encoder.state_dict()
        for arm in ARMS:
            self.assertEqual(self.encoder.transform([valid],arm).shape,(1,dimensions(arm,self.n)))
        extreme=dict(valid,timestamp=10**9,current_code='print(999999999999999999999999)')
        self.encoder.transform([extreme],'C_Z')
        self.encoder.transform([extreme],'S_MZ')
        self.assertEqual(self.encoder.state_dict(),before)
        raw=self.encoder.transform([valid],'H_IR').toarray()
        scaled=self.encoder.transform([valid],'H_IZ').toarray()
        mask=np.ones(raw.shape[1],dtype=bool)
        mask[2*self.n+7:2*self.n+10]=False
        np.testing.assert_array_equal(raw[:,mask],scaled[:,mask])
        original=self.encoder.transform([self.row],'H_IR').toarray()
        np.testing.assert_array_equal(raw,original)
        recovered=HistoryV2Encoder.from_state_dict(json.loads(json.dumps(before)))
        np.testing.assert_array_equal(scaled,recovered.transform([valid],'H_IZ').toarray())
        with self.assertRaises(ValueError):
            self.encoder.transform([dict(valid,split='test')],'C_R')


if __name__=='__main__':
    unittest.main()
