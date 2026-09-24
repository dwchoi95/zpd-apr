"""Pure synthetic fixed-offset tests; no artifacts, banks or labels are read."""
import copy
import inspect
import json
import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from scipy.special import expit

from scripts import zpd_repair_feedback_offset as solver


def cohort(n=5, seed=2027):
    rng=np.random.default_rng(seed)
    original=np.zeros((n,solver.DIMENSION),dtype=np.float64)
    original[:,:5]=rng.normal(size=(n,5))
    original/=np.maximum(1.,np.linalg.norm(original,axis=1))[:,None]
    labels=rng.integers(0,2,size=n,dtype=np.int64)
    offset=rng.normal(size=n)
    x=np.empty((2*n,solver.DIMENSION),dtype=np.float64);x[::2]=original;x[1::2]=-original
    y=np.empty(2*n,dtype=np.int64);y[::2]=labels;y[1::2]=1-labels
    base=np.empty(2*n,dtype=np.float64);base[::2]=offset;base[1::2]=-offset
    weights=np.full(2*n,solver.MASS/(2*n),dtype=np.float64)
    return x,y,weights,base


def reseal(model):
    model['model_sha256']=solver._model_hash({k:v for k,v in model.items() if k!='model_sha256'})
    return model


def orthogonal_cohort():
    x=np.zeros((10,solver.DIMENSION),dtype=np.float64)
    x[::2,:5]=np.eye(5);x[1::2]=-x[::2]
    return x,np.tile(np.array([1,0],dtype=np.int64),5),np.full(10,190.),np.zeros(10)


class OffsetSolverTests(unittest.TestCase):
    def test_analytic_gradient_matches_independent_finite_difference(self):
        x,y,w,base=cohort();theta=np.zeros(solver.DIMENSION);theta[:8]=np.linspace(-.2,.3,8)
        value,gradient=solver.objective_and_gradient(theta,x,y,w,base)
        z=(2*y-1)*(base+x@theta)
        reference=.5*sum(v*v for v in theta)+.1*sum(weight*np.logaddexp(0.,-zz) for weight,zz in zip(w,z))
        self.assertAlmostEqual(value,reference,places=12)
        for j in [0,1,2,3,4,5,7,1295]:
            step=1e-5;plus=theta.copy();minus=theta.copy();plus[j]+=step;minus[j]-=step
            a=solver.objective_and_gradient(plus,x,y,w,base)[0]
            b=solver.objective_and_gradient(minus,x,y,w,base)[0]
            self.assertAlmostEqual(gradient[j],(a-b)/(2*step),delta=2e-8)

    def test_mirrors_equal_undirected_weight_mass_not_double_objective(self):
        x,y,w,base=cohort();theta=np.zeros(solver.DIMENSION);theta[:5]=.2
        value,gradient=solver.objective_and_gradient(theta,x,y,w,base)
        signed=2*y[::2]-1;z=signed*(base[::2]+x[::2]@theta);combined=2*w[::2]
        reference=.5*float(theta@theta)+.1*float(combined@np.logaddexp(0.,-z))
        expected=theta-.1*x[::2].T@(combined*signed*expit(-z))
        self.assertAlmostEqual(value,reference,places=12)
        np.testing.assert_allclose(gradient,expected,atol=2e-14)
        self.assertEqual(float(combined.sum()),1900.)

    def test_stable_extreme_margins_and_finite_inputs(self):
        x,y,w,base=cohort(2);base[::2]=[10000.,-10000.];base[1::2]=-base[::2]
        value,gradient=solver.objective_and_gradient(np.zeros(solver.DIMENSION),x,y,w,base)
        self.assertTrue(math.isfinite(value));self.assertTrue(np.isfinite(gradient).all())
        x[0,0]=np.inf
        with self.assertRaises(ValueError):solver.objective_and_gradient(np.zeros(solver.DIMENSION),x,y,w,base)

    def test_fixed_solver_converges_and_dense_csr_input_hashes_agree(self):
        x,y,w,base=orthogonal_cohort();before=tuple(v.copy() for v in (x,y,w,base))
        model=solver.fit_offset(x,y,w,base)
        coef=solver.validate_model(json.loads(json.dumps(model)))
        other=solver.fit_offset(sparse.csr_matrix(x),y,w,base)
        self.assertEqual(model['training']['input_sha256'],other['training']['input_sha256'])
        np.testing.assert_array_equal(coef,other['coefficients'])
        self.assertLessEqual(model['optimization']['gradient_infinity_norm'],1e-6)
        self.assertLessEqual(model['optimization']['objective'],model['optimization']['initial_objective'])
        self.assertEqual(model['configuration']['fixed_base_margin_coefficient'],1.)
        self.assertEqual(model['configuration']['intercept'],0.)
        for original,actual in zip(before,(x,y,w,base)):np.testing.assert_array_equal(original,actual)
        self.assertEqual(set(inspect.signature(solver.fit_offset).parameters),{'x','labels','weights','base_margin'})

    def test_identical_pair_features_have_unique_zero_correction(self):
        x,y,w,base=cohort();x[:]=0.
        model=solver.fit_offset(x,y,w,base)
        np.testing.assert_array_equal(model['coefficients'],np.zeros(solver.DIMENSION))
        self.assertEqual(model['optimization']['iterations'],0)
        self.assertEqual(model['training']['zero_difference_rows'],len(y))
        self.assertEqual(model['training']['rows'],len(y))
        self.assertEqual(model['training']['hessian_spectral_upper_bound'],1.)

    def test_mixed_zero_difference_pairs_stay_in_objective_and_denominator(self):
        x,y,w,base=orthogonal_cohort();x[:2]=0.
        model=solver.fit_offset(x,y,w,base)
        self.assertEqual(model['training']['rows'],10)
        self.assertEqual(model['training']['zero_difference_rows'],2)
        self.assertEqual(model['training']['weight_mass'],1900.)
        self.assertGreater(model['optimization']['weighted_logistic_loss'],.1*380.*math.log(2.))

    def test_frozen_offset_changes_solution_without_training_its_coefficient(self):
        x=np.zeros((2,solver.DIMENSION));x[0,0]=1.;x[1,0]=-1.
        y=np.array([1,0],dtype=np.int64);w=np.array([950.,950.]);base=np.array([0.,0.])
        neutral=solver.fit_offset(x,y,w,base)
        strong=solver.fit_offset(x,y,w,np.array([8.,-8.]))
        self.assertGreater(neutral['coefficients'][0],strong['coefficients'][0]+1.)
        np.testing.assert_array_equal(strong['coefficients'][1:],np.zeros(1295))
        self.assertEqual(strong['configuration']['fixed_base_margin_coefficient'],1.)
        self.assertNotIn('base_coefficient',strong)

    def test_hessian_strong_convexity_and_same_state_gating_bound(self):
        x,y,w,base=cohort();theta=np.zeros(solver.DIMENSION)
        z=(2*y-1)*(base+x@theta);curvature=.1*w*expit(z)*expit(-z)
        hessian=np.eye(5)+x[:,:5].T@(curvature[:,None]*x[:,:5])
        eigenvalues=np.linalg.eigvalsh(hessian)
        self.assertGreaterEqual(float(eigenvalues.min()),1.-1e-12)
        bound=1.+.025*float(w@(x*x).sum(axis=1))
        self.assertLessEqual(float(eigenvalues.max()),bound+1e-12)
        rng=np.random.default_rng(4);state=rng.random(solver.DIMENSION);state/=np.linalg.norm(state)
        gates=rng.integers(0,2,size=(2,solver.DIMENSION));difference=(gates[0]-gates[1])*state
        self.assertLessEqual(float(np.linalg.norm(difference)),1.)
        self.assertLessEqual(1.+.025*1900*float(difference@difference),48.5+1e-12)

    def test_fixed_optimizer_options_zero_initialization_and_no_retry(self):
        x,y,w,base=orthogonal_cohort();actual=solver.minimize
        with patch.object(solver,'minimize',wraps=actual) as call:
            solver.fit_offset(x,y,w,base)
        self.assertEqual(call.call_count,1)
        np.testing.assert_array_equal(call.call_args.args[1],np.zeros(solver.DIMENSION))
        self.assertEqual(call.call_args.kwargs,dict(method='L-BFGS-B',jac=True,bounds=None,
            options=dict(maxiter=2000,ftol=1e-12,gtol=1e-8,maxcor=10,maxls=20,maxfun=15000)))

    def test_reported_success_cannot_hide_large_final_gradient(self):
        x,y,w,base=cohort()
        def false_convergence(fun,zero,**kwargs):
            value,gradient=fun(zero)
            return SimpleNamespace(success=True,status=0,message='injected',nit=0,nfev=1,njev=1,
                                   x=zero,fun=value,jac=gradient)
        with patch.object(solver,'minimize',side_effect=false_convergence) as call:
            with self.assertRaises(solver.OffsetOptimizationError) as caught:solver.fit_offset(x,y,w,base)
        self.assertEqual(call.call_count,1);self.assertFalse(caught.exception.diagnostics['accepted'])
        self.assertGreater(caught.exception.diagnostics['gradient_infinity_norm'],1e-6)

    def test_failed_status_even_at_zero_gradient_has_no_fallback(self):
        x,y,w,base=cohort();x[:]=0.
        def failure(fun,zero,**kwargs):
            value,gradient=fun(zero)
            return SimpleNamespace(success=False,status=1,message='injected limit',nit=2000,nfev=1,njev=1,
                                   x=zero,fun=value,jac=gradient)
        with patch.object(solver,'minimize',side_effect=failure) as call:
            with self.assertRaises(solver.OffsetOptimizationError):solver.fit_offset(x,y,w,base)
        self.assertEqual(call.call_count,1)
        with patch.object(solver,'minimize',side_effect=RuntimeError('injected crash')) as call:
            with self.assertRaises(solver.OffsetOptimizationError) as caught:solver.fit_offset(x,y,w,base)
        self.assertEqual(call.call_count,1);self.assertEqual(caught.exception.diagnostics['error_type'],'RuntimeError')

    def test_real_relative_objective_stop_is_not_automatically_accepted(self):
        # On local SciPy1.18.0 this exact fixture reports success at14iterations
        # but gradient infinity1.30131475e-6, and is correctly rejected. A patch
        # runtime can take an extra iteration; acceptance still needs the limit.
        try:
            model=solver.fit_offset(*cohort())
        except solver.OffsetOptimizationError as error:
            info=error.diagnostics
            self.assertFalse(info['accepted'])
            self.assertGreater(info['gradient_infinity_norm'],solver.GRADIENT_LIMIT)
        else:
            self.assertLessEqual(model['optimization']['gradient_infinity_norm'],solver.GRADIENT_LIMIT)

    def test_malformed_optimizer_result_is_failure_without_retry(self):
        x,y,w,base=orthogonal_cohort()
        for result in (SimpleNamespace(),SimpleNamespace(success='true',message='bad')):
            with patch.object(solver,'minimize',return_value=result) as call:
                with self.assertRaises(solver.OffsetOptimizationError):solver.fit_offset(x,y,w,base)
            self.assertEqual(call.call_count,1)

    def test_malformed_arrays_mirrors_labels_mass_and_base_are_rejected_before_fit(self):
        for mutation in ('list','float32','bool_labels','float_labels','nonbinary','weights_zero','huge_mass','wrong_mass',
                         'label_mirror','weight_mirror','feature_mirror','base_mirror','nan','width','odd','csc'):
            x,y,w,base=cohort()
            if mutation=='list':x=x.tolist()
            elif mutation=='float32':x=x.astype(np.float32)
            elif mutation=='bool_labels':y=y.astype(bool)
            elif mutation=='float_labels':y=y.astype(float)
            elif mutation=='nonbinary':y[0]=2
            elif mutation=='weights_zero':w[0]=0.
            elif mutation=='huge_mass':w[:]=1e308
            elif mutation=='wrong_mass':w*=2.
            elif mutation=='label_mirror':y[1]=y[0]
            elif mutation=='weight_mirror':w[0]+=.1;w[1]-=.1
            elif mutation=='feature_mirror':x[1,0]+=.1
            elif mutation=='base_mirror':base[1]+=.1
            elif mutation=='nan':base[0]=np.nan
            elif mutation=='width':x=x[:,:1295]
            elif mutation=='odd':x=x[:-1];y=y[:-1];w=w[:-1];base=base[:-1]
            else:x=sparse.csc_matrix(x)
            with self.subTest(mutation=mutation),patch.object(solver,'minimize') as fit:
                with self.assertRaises(ValueError):solver.fit_offset(x,y,w,base)
                fit.assert_not_called()

    def test_invalid_or_duplicate_csr_coordinates_never_reach_optimizer(self):
        _,y,w,base=orthogonal_cohort()
        duplicate=sparse.csr_matrix((np.array([1.,1.]),np.array([0,0]),np.array([0,2]+[2]*9)),shape=(10,1296))
        invalid=sparse.csr_matrix(np.eye(10,1296));invalid.indices[0]=1296
        for x in (duplicate,invalid):
            with patch.object(solver,'minimize') as fit:
                with self.assertRaises(ValueError):solver.fit_offset(x,y,w,base)
                fit.assert_not_called()

    def test_resealed_invalid_model_certificate_is_rejected(self):
        model=solver.fit_offset(*orthogonal_cohort())
        for mutation in ('dimension','base_coefficient','intercept','gradient','mass','objective','success','extra','checksum'):
            bad=copy.deepcopy(model)
            if mutation=='dimension':bad['configuration']['dimension']=1297
            elif mutation=='base_coefficient':bad['configuration']['fixed_base_margin_coefficient']=.99
            elif mutation=='intercept':bad['configuration']['intercept']=.01
            elif mutation=='gradient':bad['final_gradient'][0]=1e-3
            elif mutation=='mass':bad['training']['weight_mass']=1901.
            elif mutation=='objective':bad['optimization']['objective']+=1.
            elif mutation=='success':bad['optimization']['success']=False
            elif mutation=='extra':bad['extra']=1
            else:bad['coefficients'][0]+=.01
            if mutation!='checksum':reseal(bad)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):solver.validate_model(bad)


if __name__=='__main__':
    unittest.main()
