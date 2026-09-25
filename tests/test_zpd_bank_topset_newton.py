"""Synthetic-only native4131 tests; no empirical banks/labels/artifacts/I/O."""
import copy
import json
import math
import time
import unittest
from unittest.mock import patch

import numpy as np
from scipy.optimize import brentq

from scripts import zpd_bank_topset_objective as objective
from scripts import zpd_bank_topset_newton as solver


def banks_fixture():
    banks=[]
    for columns in ((0,1),(4099,),(4115,)):
        x=np.zeros((2,4131));x[0,list(columns)]=1.
        banks.append(objective.Bank(x,(0,)))
    return tuple(banks),np.array([600.,700.,600.])


def zero_fixture():
    return (objective.Bank(np.zeros((2,4131)),(0,)),),np.array([1900.])


def reseal(model):
    model['model_sha256']=solver._model_hash({k:v for k,v in model.items() if k != 'model_sha256'})
    return model


def scalar_score_hessian(scores,top_indices):
    """Direct softmax covariance of contrast vectors, no producer helper."""
    count=len(scores);top=set(top_indices);rest=[i for i in range(count) if i not in top]
    result=np.zeros((count,count))
    if not rest:return result
    for t in sorted(top):
        slopes=np.zeros((len(rest)+1,count));logits=[0.]
        for k,n in enumerate(rest,1):
            slopes[k,n]=1.;slopes[k,t]=-1.
            logits.append(float(scores[n]-scores[t])-math.log(len(rest)))
        maximum=max(logits);p=np.array([math.exp(a-maximum) for a in logits]);p/=math.fsum(p)
        mean=np.array([math.fsum(float(p[i])*float(slopes[i,j]) for i in range(len(p))) for j in range(count)])
        for i in range(len(p)):
            difference=slopes[i]-mean
            result+=float(p[i])*np.outer(difference,difference)/len(top)
    return result


class TopsetNewtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banks,cls.weights=banks_fixture();cls.shapes=[]
        actual=solver._hessian
        def watched(*args):
            value=actual(*args);cls.shapes.append(value.shape);return value
        started=time.monotonic()
        with patch.object(solver,'_hessian',side_effect=watched):
            cls.model=solver.fit(cls.banks,cls.weights)
        cls.seconds=time.monotonic()-started
        cls.zero=solver.fit(*zero_fixture())
        print('TOPSET4131_SYNTHETIC '+json.dumps(dict(seconds=cls.seconds,
            updates=cls.model['optimization']['updates'],hessian_shapes=cls.shapes)),flush=True)

    def test_actual_native4131_against_independent_scalar_optima(self):
        theta=solver.validate_model(self.model,expected_banks=self.banks,expected_weights=self.weights)
        expected=np.zeros(4131)
        for columns,w in zip(((0,1),(4099,),(4115,)),self.weights,strict=True):
            k=len(columns)
            s=brentq(lambda a:a-.1*float(w)/(1.+math.exp(k*a)),0.,10.,xtol=1e-14)
            expected[list(columns)]=s
        np.testing.assert_allclose(theta,expected,atol=1e-8,rtol=1e-8)
        self.assertTrue(self.shapes);self.assertTrue(all(s==(4131,4131) for s in self.shapes))
        self.assertEqual(len(self.shapes),self.model['optimization']['hessian_evaluations'])
        gradient=theta.copy();loss=0.
        for columns,w in zip(((0,1),(4099,),(4115,)),self.weights,strict=True):
            margin=math.fsum(float(theta[j]) for j in columns)
            loss+=.1*float(w)*math.log1p(math.exp(-margin))
            gradient[list(columns)]-=.1*float(w)/(1.+math.exp(margin))
        self.assertLessEqual(float(np.max(np.abs(gradient))),1e-8)
        np.testing.assert_allclose(gradient,self.model['final_gradient'],atol=1e-13,rtol=1e-10)
        self.assertAlmostEqual(self.model['optimization']['objective'],.5*float(theta@theta)+loss,places=12)
        unused=np.ones(4131,dtype=bool);unused[[0,1,4099,4115]]=False
        np.testing.assert_array_equal(theta[unused],np.zeros(int(unused.sum())))
        self.assertEqual(theta[0],theta[1])  # Rank-deficient duplicated current column.

    def test_zero_design_and_empty_rest_stop_with_fresh_check(self):
        for banks,weights in (zero_fixture(),((objective.Bank(np.ones((3,4131)),(0,1,2)),),np.array([1900.]))):
            model=solver.fit(banks,weights);meta=model['optimization']
            self.assertEqual(meta['updates'],0);self.assertEqual(meta['total_evaluations'],2)
            self.assertEqual(meta['final_checks'],1);self.assertEqual(meta['linear_solves'],0)
            np.testing.assert_array_equal(solver.validate_model(model),np.zeros(4131))

    def test_score_hessian_scalar_covariance_hvp_and_psd(self):
        rng=np.random.default_rng(2027)
        for _ in range(15):
            scores=rng.normal(size=7);top=(0,2,4);v=rng.normal(size=7)
            h=solver.score_hessian(scores,top)
            np.testing.assert_allclose(h,scalar_score_hessian(scores,top),atol=2e-16,rtol=2e-13)
            np.testing.assert_allclose(h@v,objective.bank_hvp(scores,top,v),atol=2e-16,rtol=2e-13)
            self.assertGreaterEqual(float(np.linalg.eigvalsh(h).min()),-2e-16)
        h=solver.score_hessian(np.array([0.,40.]),(0,))
        self.assertGreater(h[0,0],0.);self.assertAlmostEqual(h[0,0],math.exp(-40),places=30)

    def test_assembled_hessian_hvp_nested_zero_tail_and_common_offset(self):
        x=np.zeros((4,4131));x[:,:3]=[[1.,.3,-.1],[-.2,.1,.4],[.6,-.4,.2],[.8,.7,-.6]]
        # CF-shaped final16 zero block stays pure ridge, not removed/padded.
        x[:,4099]=[.2,.1,.7,-.2]
        bank=objective.Bank(x+2.**20,(0,2));banks=(bank,);weights=np.array([1900.])
        theta=np.zeros(4131);theta[:3]=[.2,-.3,.4];v=np.zeros(4131);v[:3]=[.5,-.2,.7];v[4115]=.8
        h=solver._hessian(theta,banks,weights,solver._design(banks))
        np.testing.assert_allclose(h@v,objective.coefficient_hvp(theta,banks,weights,v),atol=2e-13,rtol=1e-12)
        np.testing.assert_array_equal(h[4115:,4115:],np.eye(16))
        self.assertGreaterEqual(float(v@h@v),float(v@v)-1e-12)
        g0=objective.coefficient_objective(theta,banks,weights).gradient
        e=1e-6
        observed=(objective.coefficient_objective(theta+e*v,banks,weights).gradient-objective.coefficient_objective(theta-e*v,banks,weights).gradient)/(2*e)
        np.testing.assert_allclose(h@v,observed,atol=2e-8,rtol=1e-7)
        self.assertTrue(np.isfinite(g0).all())

    def test_directional_range_is_full_range_not_maxabs(self):
        x=np.zeros((3,4131));bank=objective.Bank(x,(0,))
        self.assertEqual(solver.directional_range((bank,),np.array([1900.]),np.array([0.,-1.,1.])),2.)
        banks=(bank,objective.Bank(x,(0,1,2)),bank)
        self.assertEqual(solver.directional_range(banks,np.array([1900.,0.,0.]),np.array([0.,-1.,1.,0.,-999.,999.,0.,-999.,999.])),2.)
        # A realizable LSE distribution demonstrates why maxabs=1 is invalid.
        p=np.array([1e-6,.989999,.01]);z=np.array([0.,-1.,1.]);mean=float(p@z)
        variance=float(p@((z-mean)**2));third=float(p@((z-mean)**3))
        self.assertGreater(abs(third)/variance,1.9);self.assertLessEqual(abs(third),2*variance)
        with self.assertRaises(FloatingPointError):solver.directional_range((bank,),np.array([1900.]),np.array([0.,-1e308,1e308]))

    def test_fixed_damping_and_counter_certificate(self):
        m=self.model['optimization'];updates=m['updates']
        self.assertEqual(m['loop_evaluations'],updates+1);self.assertEqual(m['total_evaluations'],updates+2)
        self.assertEqual(m['linear_solves'],updates);self.assertEqual(m['final_checks'],1)
        for row in m['trace'][:-1]:
            r=row['r'];expected=min(1.,math.log1p(r*(row['a']/row['q']))/r) if r else min(1.,row['a']/row['q'])
            self.assertEqual(row['alpha'],expected);self.assertLessEqual(row['normalized_solve_residual'],1e-12)
        self.assertEqual(solver._alpha(2.,4.,0.),.5)
        for bad in ((True,1.,1.),(1.,0.,1.),(1.,1.,-1.),(1e308,1e-308,1.)):
            with self.assertRaises((ValueError,FloatingPointError)):solver._alpha(*bad)

    def test_raw_identity_differs_even_when_centered_objective_same(self):
        banks,weights=zero_fixture();shifted=(objective.Bank(np.ones((2,4131)),(0,)),)
        self.assertNotEqual(solver.input_hash(banks,weights),solver.input_hash(shifted,weights))
        with self.assertRaises(ValueError):solver.validate_model(self.zero,expected_banks=shifted,expected_weights=weights)
        with self.assertRaises(ValueError):solver.validate_model(self.zero,expected_banks=banks)
        expected=solver.input_hash(banks,weights);self.assertEqual(self.zero['input_sha256'],expected)

    def test_resealed_schema_trace_gradient_and_kind_tampering(self):
        cases=[]
        for path,value in [(('configuration','kind'),'fixed_repair_joint_progress_newton_v1'),(('configuration','dimension'),32),
                (('optimization','total_evaluations'),True),(('optimization','final_checks'),0),
                (('training','banks'),True),(('training','weight_mass'),1800.),(('coefficients',0),'0'),(('final_gradient',0),1.0000001e-8)]:
            model=copy.deepcopy(self.zero);model[path[0]][path[1]]=value;cases.append(model)
        model=copy.deepcopy(self.model);model['optimization']['trace'][0]['r']=-1.;cases.append(model)
        model=copy.deepcopy(self.zero);model['unexpected']='offset';cases.append(model)
        for model in cases:
            with self.subTest(keys=list(model)),self.assertRaises(ValueError):solver.validate_model(reseal(model))

    def test_input_dimension_type_mass_finite_and_centering_overflow_failures(self):
        banks,weights=zero_fixture()
        for bad in (np.array([True]),np.array([1900.],dtype=np.float32),np.array([-1900.]),np.array([np.inf])):
            with self.assertRaises(ValueError):solver.fit(banks,bad)
        with self.assertRaises(ValueError):solver.fit((objective.Bank(np.zeros((2,144)),(0,)),),weights)
        x=np.zeros((2,4131));x[0,0]=-1e308;x[1,0]=1e308
        with self.assertRaises(solver.OptimizationError) as caught:solver.fit((objective.Bank(x,(0,)),),weights)
        self.assertEqual(caught.exception.diagnostics['status'],'input_metadata_failed')
        json.dumps(caught.exception.diagnostics,allow_nan=False)

    def test_fresh_check_failure_never_accepts_cached_gradient(self):
        banks,weights=zero_fixture();actual=objective.coefficient_objective;calls=[]
        def altered(*args):
            result=actual(*args);calls.append(1)
            if len(calls)==2:
                g=np.zeros(4131);g[0]=np.nextafter(1e-8,np.inf)
                return objective.ObjectiveValue(result.objective,result.data_loss,result.penalty,g)
            return result
        with patch.object(objective,'coefficient_objective',side_effect=altered),self.assertRaises(solver.OptimizationError) as caught:
            solver.fit(banks,weights)
        d=caught.exception.diagnostics;self.assertEqual(d['status'],'final_check_failed');self.assertEqual(d['total_evaluations'],2)
        self.assertFalse(d['accepted']);json.dumps(d,allow_nan=False)

    def test_nonfinite_evaluation_has_finite_failure_json(self):
        banks,weights=zero_fixture()
        for g in (np.full(4131,np.nan),np.ones(32),np.zeros(4131,dtype=np.float32)):
            value=objective.ObjectiveValue(1.,1.,0.,g)
            with patch.object(objective,'coefficient_objective',return_value=value),self.assertRaises(solver.OptimizationError) as caught:
                solver.fit(banks,weights)
            d=caught.exception.diagnostics;self.assertEqual(d['trace'],[]);self.assertIsNone(d['initial_objective'])
            json.dumps(d,allow_nan=False)

    def test_cholesky_failure_no_retry_and_fixed_budget(self):
        with patch.object(solver,'_hessian',return_value=np.eye(1)),patch.object(solver,'_direction',side_effect=np.linalg.LinAlgError('synthetic')) as direction:
            with self.assertRaises(solver.OptimizationError) as caught:solver.fit(self.banks,self.weights)
        self.assertEqual(direction.call_count,1);self.assertEqual(caught.exception.diagnostics['status'],'linear_solve_failed')
        with patch.object(solver,'MAX_UPDATES',0),self.assertRaises(solver.OptimizationError) as caught:solver.fit(self.banks,self.weights)
        d=caught.exception.diagnostics;self.assertEqual(d['status'],'update_budget_exhausted');self.assertEqual(d['updates'],0)
        self.assertEqual(d['hessian_evaluations'],0);json.dumps(d,allow_nan=False)


if __name__=='__main__':unittest.main()
