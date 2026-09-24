"""Independent diagnostic boundary witnesses; synthetic, no fit or I/O."""
from types import SimpleNamespace
import unittest

import numpy as np

from scripts import diagnose_zpd_repair_progress32 as diagnosis
from tests.test_zpd_repair_progress32_diagnosis import fixture, label


class IndependentProgress32DiagnosisTests(unittest.TestCase):
    def test_zero_gradient_can_be_cancellation_without_logistic_attenuation(self):
        x=np.zeros((4,32));x[:,0]=[1.,-1.,1.,-1.]
        result=diagnosis.logistic_statistics(x,np.array([1,0,0,1]),np.full(4,475.),
                                              np.zeros(4),np.zeros(32))
        self.assertEqual(result['weighted_mean_sigmoid_negative_signed_base'],.5)
        self.assertEqual(result['logistic_leverage_C_sum_w_sigmoid_negative_signed_base'],95.)
        self.assertEqual(result['logistic_feature_triangle_bound'],95.)
        self.assertEqual(result['gradient_at_zero_l2'],0.)
        self.assertEqual(result['gradient_to_triangle_ratio'],0.)

    def test_wrong_base_margins_increase_not_attenuate_training_leverage(self):
        x=np.zeros((2,32));x[:,0]=[1.,-1.]
        result=diagnosis.logistic_statistics(x,np.array([1,0]),np.full(2,950.),
                                              np.array([-20.,20.]),np.zeros(32))
        self.assertGreater(result['weighted_mean_sigmoid_negative_signed_base'],.999999)
        self.assertGreater(result['logistic_leverage_C_sum_w_sigmoid_negative_signed_base'],189.999)
        self.assertEqual(result['weighted_base_wrong_mass_fraction'],1.)

    def test_observed_radius_is_not_global_impossibility(self):
        x=np.zeros((3,32));x[0,0]=1.;small=np.zeros(32);small[0]=.25
        p,b,t,l=fixture(base=dict(a=0.,b=1.,n=-1.),matrix=x,theta=small)
        observed=diagnosis.bank_diagnosis(p,b,t,l)
        self.assertTrue(observed['radius_blocked_known_ac'])
        large=np.zeros(32);large[0]=2.
        p,b,t,l=fixture(base=dict(a=0.,b=1.,n=-1.),matrix=x,theta=large)
        other=diagnosis.bank_diagnosis(p,b,t,l)
        self.assertFalse(other['radius_blocked_known_ac'])
        self.assertTrue(other['H_known_ac'])
        # This is an algebraic counterexample, not permission to amplify a fit.

    def test_strict_radius_tolerance_is_not_nonstrict_or_ranking_tolerance(self):
        x=np.zeros((3,32));x[0,0]=.5;t=np.zeros(32);t[0]=.25
        for extra,blocked in ((0.,False),(.5e-12,False),(2e-12,True)):
            p,b,theta,labs=fixture(base=dict(a=0.,b=.125+extra,n=-1.),matrix=x,theta=t)
            result=diagnosis.bank_diagnosis(p,b,theta,labs)
            self.assertEqual(result['radius_blocked_known_ac'],blocked)

    def test_class_champions_need_not_be_jointly_linearly_realizable(self):
        # Bank A needs theta_0>1, bank B needs theta_0<-1; local AC classes exist.
        # Thus two class champions are not a constructive shared-model oracle.
        for sign in (1.,-1.):
            x=np.zeros((3,32));x[0,0]=sign
            p,b,t,l=fixture(base=dict(a=0.,b=1.,n=-1.),matrix=x)
            result=diagnosis.bank_diagnosis(p,b,t,l)
            self.assertTrue(result['class_champion_known_ac'])
            self.assertTrue(result['missed_known_ac'])
        self.assertFalse(any(v>1 and v<-1 for v in (-2.,-1.,0.,1.,2.)))

    def test_training_projection_keeps_zero_difference_and_never_reads_held(self):
        ids=('a','b','u');x=np.zeros((3,32))
        examples=(SimpleNamespace(example_id='train',bank_id='train-bank',user_id='u1'),
                  SimpleNamespace(example_id='held',bank_id='held-bank',user_id='u2'))
        inp=SimpleNamespace(examples=examples,fold=0,assignment={'example_fold':{'train':1,'held':0}},
            interactions={'H':{'train-bank':SimpleNamespace(candidate_ids=ids,matrix=x)}},
            base_scores={'train-bank':dict(a=2.,b=1.,u=0.)})
        class TrainingOnly(dict):
            def __getitem__(self,key):
                if key[0]=='held-bank':raise AssertionError('held label read')
                return super().__getitem__(key)
        labs=TrainingOnly({('train-bank',cid):label('train-bank',cid,ac=cid=='a',unknown=cid=='u') for cid in ids})
        matrix,y,w,b,pairs,exids=diagnosis.training_arrays(inp,labs)
        self.assertEqual(matrix.shape,(2,32));self.assertFalse(matrix.any())
        np.testing.assert_array_equal(y,[1,0]);np.testing.assert_array_equal(w,[950.,950.])
        np.testing.assert_array_equal(b,[1.,-1.])
        self.assertEqual(pairs,[['a','b'],['b','a']]);self.assertEqual(exids,['train','train'])


if __name__=='__main__':unittest.main()
