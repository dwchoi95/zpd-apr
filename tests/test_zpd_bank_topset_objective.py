"""Pure synthetic score/feature tests; no labels, artifacts or optimizers."""
from dataclasses import FrozenInstanceError
import math
import unittest

import numpy as np
from scipy.special import expit

from scripts import zpd_bank_topset_objective as top


def numeric_gradient(function, point, step=1e-6):
    result=np.zeros_like(point)
    for i in range(len(point)):
        offset=np.zeros_like(point);offset[i]=step
        result[i]=(function(point+offset)-function(point-offset))/(2*step)
    return result


class BankTopsetObjectiveTests(unittest.TestCase):
    def test_one_rest_is_mean_pair_logistic(self):
        scores=np.array([2.,-.5,1.])
        loss,g=top.bank_loss_gradient(scores,(0,1))
        expected=np.logaddexp(0.,scores[2]-scores[:2]).mean()
        self.assertAlmostEqual(loss,float(expected),places=15)
        np.testing.assert_allclose(g[:2],-expit(scores[2]-scores[:2])/2,rtol=0,atol=1e-15)
        self.assertAlmostEqual(g.sum(),0.,places=15)

    def test_zero_scores_log2_independent_of_top_and_rest_sizes(self):
        for n in (2,3,7,15):
            for k in range(1,n):
                loss,g=top.bank_loss_gradient(np.zeros(n),(tuple(range(k))))
                self.assertAlmostEqual(loss,math.log(2),places=14)
                np.testing.assert_allclose(g[:k],-.5/k,atol=1e-15,rtol=0)
                np.testing.assert_allclose(g[k:],.5/(n-k),atol=1e-15,rtol=0)

    def test_empty_rest_zero_and_no_top_tie_equalization(self):
        scores=np.array([5.,0.,-2.]);loss,g=top.bank_loss_gradient(scores,(0,1))
        self.assertGreater(loss,0);self.assertLess(g[0],0);self.assertLess(g[1],0)
        self.assertGreater(g[0],g[1])  # Already high top is never pushed down to match another top.
        loss,g=top.bank_loss_gradient(scores,(2,0,1))
        self.assertEqual(loss,0.);np.testing.assert_array_equal(g,np.zeros(3))
        np.testing.assert_array_equal(top.bank_hvp(scores,(0,1,2),np.ones(3)),np.zeros(3))

    def test_translation_and_candidate_permutation_invariance(self):
        s=np.array([-2.,.3,4.,1.5]);v=np.array([.3,-1.,2.,.6]);indices=(0,2)
        a,ga=top.bank_loss_gradient(s,indices);b,gb=top.bank_loss_gradient(s+100.,indices)
        self.assertAlmostEqual(a,b,places=13);np.testing.assert_allclose(ga,gb,atol=2e-15,rtol=1e-13)
        np.testing.assert_allclose(top.bank_hvp(s,indices,v),top.bank_hvp(s+100.,indices,v),atol=2e-15,rtol=1e-13)
        np.testing.assert_allclose(top.bank_hvp(s,indices,np.ones(4)),np.zeros(4),atol=1e-15)
        order=np.array([2,0,3,1]);c,gc=top.bank_loss_gradient(s[order],(0,1))
        self.assertAlmostEqual(a,c,places=14);np.testing.assert_allclose(ga[order],gc,rtol=0,atol=1e-15)

    def test_large_common_score_preserves_log_mean_correction(self):
        large=1e100;s=np.array([large,large,np.nextafter(large,-np.inf)])
        loss,g=top.bank_loss_gradient(s,(0,))
        self.assertAlmostEqual(loss,math.log(1.5),places=14)
        np.testing.assert_allclose(g,[-1/3,1/3,0],rtol=0,atol=1e-15)
        loss,g=top.bank_loss_gradient(np.array([1e308,-1e308]),(0,))
        self.assertEqual(loss,0.);np.testing.assert_array_equal(g,np.zeros(2))
        with self.assertRaises(FloatingPointError):top.bank_loss_gradient(np.array([-1e308,1e308]),(0,))

    def test_score_gradient_and_hvp_finite_differences(self):
        s=np.array([-.8,.2,1.1,-.3,2.]);v=np.array([.4,-.5,.7,1.3,-.9]);indices=(0,2)
        loss,g=top.bank_loss_gradient(s,indices)
        numerical=numeric_gradient(lambda x:top.bank_loss_gradient(x,indices)[0],s)
        np.testing.assert_allclose(g,numerical,atol=3e-10,rtol=2e-7)
        h=1e-6;observed=(top.bank_loss_gradient(s+h*v,indices)[1]-top.bank_loss_gradient(s-h*v,indices)[1])/(2*h)
        np.testing.assert_allclose(top.bank_hvp(s,indices,v),observed,atol=3e-10,rtol=2e-7)

    def test_score_hessian_psd_symmetry_and_saturation(self):
        rng=np.random.default_rng(2027)
        for _ in range(20):
            s=rng.normal(size=6);v=rng.normal(size=6)
            matrix=np.column_stack([top.bank_hvp(s,(0,2),e) for e in np.eye(6)])
            np.testing.assert_allclose(matrix,matrix.T,atol=1e-14,rtol=1e-13)
            self.assertGreaterEqual(float(v@matrix@v),-1e-13)
            self.assertGreaterEqual(float(np.linalg.eigvalsh(matrix).min()),-1e-13)
        loss,g=top.bank_loss_gradient(np.array([1000.,0.,-1000.]),(0,))
        self.assertEqual(loss,0.);np.testing.assert_array_equal(g,np.zeros(3))

    def test_small_positive_curvature_not_lost_to_one_minus_sigmoid(self):
        curvature=float(expit(40.)*expit(-40.))
        self.assertEqual(float(expit(40.)),1.)
        self.assertGreater(curvature,0.)
        hv=top.bank_hvp(np.array([0.,40.]),(0,),np.array([1.,0.]))
        np.testing.assert_allclose(hv,[curvature,-curvature],atol=0,rtol=1e-15)

    def test_coefficient_gradient_hvp_and_ridge_lower_bound(self):
        banks=(top.Bank(np.array([[1.,0.,.2],[.1,-.3,.4],[-.5,.9,.2]]),(0,)),
               top.Bank(np.array([[.4,.6,-.2],[.8,-.1,.3],[.3,.2,-.9],[.7,.3,.5]]),(0,2)))
        weights=np.array([700.,1200.]);theta=np.array([.2,-.3,.4]);v=np.array([.5,-.2,.7])
        value=top.coefficient_objective(theta,banks,weights)
        numerical=numeric_gradient(lambda x:top.coefficient_objective(x,banks,weights).objective,theta)
        np.testing.assert_allclose(value.gradient,numerical,atol=2e-8,rtol=2e-7)
        step=1e-6;expected=(top.coefficient_objective(theta+step*v,banks,weights).gradient-top.coefficient_objective(theta-step*v,banks,weights).gradient)/(2*step)
        hv=top.coefficient_hvp(theta,banks,weights,v)
        np.testing.assert_allclose(hv,expected,atol=2e-8,rtol=2e-7)
        self.assertGreaterEqual(float(v@hv),float(v@v)-1e-12)
        self.assertAlmostEqual(value.objective,value.penalty+value.data_loss,places=14)
        np.testing.assert_array_equal(top.coefficient_hvp(theta,(top.Bank(np.zeros((2,3)),(0,)),),np.array([1900.]),v),v)

    def test_empty_rest_and_zero_weight_keep_explicit_banks(self):
        theta=np.array([.1,-.3]);v=np.array([.2,.4])
        banks=(top.Bank(np.ones((2,2)),(0,1)),top.Bank(np.array([[1.,0.],[0.,1.]]),(0,)))
        value=top.coefficient_objective(theta,banks,np.array([1900.,0.]))
        self.assertEqual(value.data_loss,0.);np.testing.assert_array_equal(value.gradient,theta)
        np.testing.assert_array_equal(top.coefficient_hvp(theta,banks,np.array([1900.,0.]),v),v)

    def test_common_extreme_feature_and_direction_offsets_annihilate(self):
        banks=(top.Bank(np.full((7,1),1e100),(0,)),);w=np.array([1900.])
        for theta in (np.zeros(1),np.array([.25])):
            value=top.coefficient_objective(theta,banks,w)
            np.testing.assert_array_equal(value.gradient,theta)
            self.assertAlmostEqual(value.data_loss,190*math.log(2),places=12)
            np.testing.assert_array_equal(top.coefficient_hvp(theta,banks,w,np.ones(1)),np.ones(1))
        np.testing.assert_array_equal(top.bank_hvp(np.zeros(7),(0,),np.full(7,1e100)),np.zeros(7))
        self.assertTrue(np.all(banks[0].features==1e100))

    def test_representable_feature_translation_and_overflow(self):
        x=np.array([[1.,2.],[3.,-1.],[-2.,4.]])
        theta=np.array([.2,-.3]);v=np.array([.4,.6]);w=np.array([1900.])
        a=(top.Bank(x,(0,)),);b=(top.Bank(x+2.**30,(0,)),)
        np.testing.assert_array_equal(top.centered_features(a[0]),top.centered_features(b[0]))
        self.assertEqual(top.coefficient_objective(theta,a,w).objective,top.coefficient_objective(theta,b,w).objective)
        np.testing.assert_array_equal(top.coefficient_hvp(theta,a,w,v),top.coefficient_hvp(theta,b,w,v))
        bad=top.Bank(np.array([[-1e308],[1e308]]),(0,))
        with self.assertRaises(FloatingPointError):top.centered_features(bad)
        with self.assertRaises(FloatingPointError):top.bank_hvp(np.zeros(2),(0,),np.array([-1e308,1e308]))

    def test_strict_float_arrays_indices_weights_and_dimensions(self):
        valid=np.array([0.,1.])
        for bad in ([0.,1.],np.array([False,True]),np.array([0.,1.],dtype=np.float32),np.array([0.,np.nan]),np.array([0.,np.inf])):
            with self.subTest(bad=bad),self.assertRaises(ValueError):top.bank_loss_gradient(bad,(0,))
        for indices in ((),(True,),(0,0),(-1,),(2,),[0],(0.,)):
            with self.subTest(indices=indices),self.assertRaises(ValueError):top.bank_loss_gradient(valid,indices)
        bank=top.Bank(np.eye(2),(0,));theta=np.zeros(2)
        for weights in (np.array([0.]),np.array([-1900.]),np.array([True]),np.array([np.nan]),np.array([1900.,0.])):
            with self.subTest(weights=weights),self.assertRaises(ValueError):top.coefficient_objective(theta,(bank,),weights)
        with self.assertRaises(ValueError):top.coefficient_objective(np.zeros(3),(bank,),np.array([1900.]))
        with self.assertRaises(ValueError):top.bank_hvp(valid,(0,),np.array([True,False]))
        with self.assertRaises(ValueError):top.Bank(np.empty((0,2)),())

    def test_inputs_outputs_immutable_and_caller_unknown_contract(self):
        original=np.eye(2);bank=top.Bank(original,(0,));original[0,0]=100.
        self.assertEqual(bank.features[0,0],1.)
        with self.assertRaises(ValueError):bank.features.flags.writeable=True
        with self.assertRaises(FrozenInstanceError):bank.top_indices=(1,)
        result=top.coefficient_objective(np.zeros(2),(bank,),np.array([1900.]))
        with self.assertRaises(ValueError):result.gradient[0]=0.
        self.assertEqual(top.configuration()['unknown'],'caller_must_isolate_never_inferred_negative')
        self.assertFalse(top.configuration()['fitting_performed'])


if __name__=='__main__':unittest.main()
