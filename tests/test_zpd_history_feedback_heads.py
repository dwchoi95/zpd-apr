"""Synthetic fixed-optimizer, serialization and C2 zero-embedding checks."""
import copy
import json
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_action_blocked as blocked
from scripts import zpd_history_feedback_coupling as coupling
from scripts import zpd_history_feedback_heads as heads
from scripts import run_zpd_history_action_cv as legacy
from tests.test_zpd_history_action_blocked import fixture


class FeedbackHeadTests(unittest.TestCase):
    def test_c0_cn_zero_embedding_and_optimizer_prediction_parity(self):
        observations, targets = fixture(8)
        y, mask = legacy.encode_targets(observations, targets, semantic)
        users = [o['user_id'] for o in observations]
        for arm in ('C0','Cn'):
            x2 = blocked.encode_matrix(observations,np.arange(8),arm)
            x3 = coupling.encode_matrix(observations,np.arange(8),arm)
            self.assertEqual(x3.shape,(8,9492))
            self.assertEqual((x3[:,:8196] != x2).nnz,0)
            self.assertEqual(x3[:,8196:].nnz,0)
            before = blocked.fit_heads(x2,y,mask,users,semantic.EVENTS)
            after = heads.fit_heads(x3,y,mask,users,semantic.EVENTS)
            np.testing.assert_allclose(blocked.predict_heads(before,x2), heads.predict_heads(after,x3),rtol=1e-10,atol=2e-12)

    def test_equal_user_masked_weight_mass_and_twenty_exposures(self):
        x = sparse.csr_matrix(np.eye(4,9492)); y=np.zeros((4,18)); mask=np.zeros_like(y,dtype=bool)
        mask[0,:]=True;mask[1,:3]=True;mask[2,:7]=True;y[1,:3]=1.;y[2,0]=1.
        users=['a','a','b','c']; trace=[]
        weights=legacy.label_weights(users,mask)
        self.assertAlmostEqual(float(weights[0]*18+weights[1]*3),float(weights[2]*7))
        model=heads.fit_heads(x,y,mask,users,semantic.EVENTS,callback=trace.append)
        self.assertAlmostEqual(sum(h['total_weight'] for h in model['heads']),3.)
        for h in model['heads']:
            events=[e for e in trace if e['event']==h['event']]
            if h['kind']=='linear_logistic':
                self.assertEqual([e['epoch'] for e in events],list(range(1,21)))
                self.assertEqual(events[-1]['completed_train_prefix_event_exposures'],20*h['observed_prefixes'])
            else:
                self.assertEqual(len(events),1)
                self.assertEqual(events[0]['completed_train_prefix_event_exposures'],0)

    def test_missing_constant_and_prediction_never_fits(self):
        x=sparse.csr_matrix((2,9492));y=np.zeros((2,18));mask=np.zeros_like(y,dtype=bool)
        model=heads.fit_heads(x,y,mask,['a','b'],semantic.EVENTS)
        self.assertTrue(all(h['probability']==.5 for h in model['heads']))
        with patch.object(heads.SGDClassifier,'partial_fit',side_effect=AssertionError('prediction fit')):
            p=heads.predict_heads(json.loads(json.dumps(model)),x)
        np.testing.assert_array_equal(p,np.full((2,18),.5))

    def test_strict_configuration_and_coefficients_reject_tamper(self):
        x=sparse.csr_matrix((2,9492));y=np.zeros((2,18));mask=np.ones_like(y,dtype=bool)
        baseline=heads.fit_heads(x,y,mask,['a','b'],semantic.EVENTS)
        alterations = [lambda m:m.update(feature_dimension=9492.), lambda m:m.update(epochs=20.),
            lambda m:m.update(seed=2027.),lambda m:m.update(events=list(reversed(m['events']))),
            lambda m:m.update(unknown=True),lambda m:m['representation'].update(scale_divisor=7.),
            lambda m:m['representation'].update(final_normalization=True),
            lambda m:m['heads'][0].update(probability=True),
            lambda m:m['heads'][0].update(observed_users=True)]
        for alter in alterations:
            value=copy.deepcopy(baseline);alter(value)
            with self.assertRaises(ValueError):heads.validate_model(value)
        for bad in ('0',True,float('nan'),float('inf')):
            value=copy.deepcopy(baseline);h=value['heads'][0];h.pop('probability')
            h.update(kind='linear_logistic',coefficients=[0.]*9492,intercept=0.)
            h['coefficients'][0]=bad
            with self.assertRaises(ValueError):heads.validate_model(value)

    def test_bad_shapes_masks_source_users_and_values(self):
        x=sparse.csr_matrix((2,9492));y=np.zeros((2,18));mask=np.ones_like(y,dtype=bool)
        for xx,yy,mm,users in [(x[:,:8196],y,mask,['a','b']), (x,y,mask.astype(int),['a','b']),
                (x,y,mask,['a',3]),(x,np.ones_like(y)*2,mask,['a','b']),
                (x,np.full_like(y,np.nan),mask,['a','b'])]:
            with self.assertRaises(ValueError):heads.fit_heads(xx,yy,mm,users,semantic.EVENTS)

    def test_frozen_globals_unchanged(self):
        self.assertEqual(blocked.FEATURE_DIMENSION,8196)
        self.assertEqual(legacy.HASH_DIMENSION,4096)
        self.assertEqual(blocked.ARMS,('C0','Cn','H','U','HS','L'))


if __name__=='__main__':unittest.main()
