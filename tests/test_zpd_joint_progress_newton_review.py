"""Nonauthor synthetic-only checks of the native4131 Newton implementation.

The actual full-width factorization is intentional. Decimal reference roots and
scalar derivatives do not call the production evaluator/solver. Mocks below
exercise failure/strict-boundary paths, never substitute for that full solve.
"""
import copy
from decimal import Decimal, localcontext
import hashlib
import inspect
import json
import math
import time
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from threadpoolctl import threadpool_limits

from scripts import zpd_joint_progress_newton as solver


SPEC = solver.ResidualSpec('review_synthetic_joint4131', 4131, 'a'*64, solver.KIND)
ACTIVE = (0, 1, 4099, 4115)


def arrays():
    x = np.zeros((6, 4131), dtype=np.float64)
    x[0, 0] = x[0, 1] = .2
    x[2, 4099] = .3
    x[4, 4115] = .4
    x[1::2] = -x[::2]
    return x, np.array([1, 0]*3, dtype=np.int64), np.array([310., 310., 320., 320., 320., 320.])


def reference_theta():
    """Independent80-digit monotone-root bisection; collinear pair included."""
    result = np.zeros(4131)
    with localcontext() as ctx:
        ctx.prec = 80
        for value, mass, columns in ((.2, 620., (0, 1)), (.3, 640., (4099,)), (.4, 640., (4115,))):
            a = Decimal.from_float(value); factor = Decimal.from_float(.1)*Decimal.from_float(mass)*a
            lo, hi = Decimal(0), factor
            for _ in range(280):
                mid = (lo+hi)/2
                gradient = mid-factor/(1+(a*len(columns)*mid).exp())
                if gradient > 0: hi = mid
                else: lo = mid
            for col in columns: result[col] = float((lo+hi)/2)
    return result


def scalar_reference(theta, x, target, weights):
    """Python scalar sums, stable logistic; no producer evaluation primitive."""
    active = np.flatnonzero(np.any(x != 0., axis=0) | (theta != 0.))
    terms = []; gradients = {int(j): [float(theta[j])] for j in active}
    hessian = {(int(j), int(k)): [float(j == k)] for j in active for k in active}
    for row, stored, weight in zip(x, target, weights, strict=True):
        signed = 2*int(stored)-1
        z = signed*math.fsum(float(row[j])*float(theta[j]) for j in active)
        logistic = max(0., -z)+math.log1p(math.exp(-abs(z)))
        sigma = math.exp(-z)/(1+math.exp(-z)) if z >= 0 else 1/(1+math.exp(z))
        terms.append(.1*float(weight)*logistic)
        for j in active:
            gradients[int(j)].append(-.1*float(weight)*signed*float(row[j])*sigma)
            for k in active:
                hessian[int(j), int(k)].append(.1*float(weight)*float(row[j])*float(row[k])*sigma*(1-sigma))
    penalty = .5*math.fsum(float(v)*float(v) for v in theta)
    gradient = np.zeros(4131)
    for j, terms_j in gradients.items(): gradient[j] = math.fsum(terms_j)
    return penalty+math.fsum(terms), gradient, {key: math.fsum(values) for key, values in hessian.items()}


def hash_arrays(*arrays_to_hash):
    """Independent literal serialization from the declared legacy array format."""
    digest = hashlib.sha256()
    for array in arrays_to_hash:
        contiguous = np.ascontiguousarray(array)
        header = json.dumps({'shape': list(contiguous.shape), 'dtype': contiguous.dtype.str},
                            sort_keys=True, separators=(',', ':')).encode()
        body = contiguous.tobytes()
        digest.update(len(header).to_bytes(8, 'little')); digest.update(header)
        digest.update(len(body).to_bytes(8, 'little')); digest.update(body)
    return digest.hexdigest()


def reseal(model):
    model['model_sha256'] = hashlib.sha256(json.dumps({k: v for k, v in model.items() if k != 'model_sha256'},
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return model


class JointNewtonReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x, cls.y, cls.w = arrays()
        begin = time.monotonic()
        with threadpool_limits(limits=1):
            cls.model = solver.fit_joint(cls.x, cls.y, cls.w, spec=SPEC)
        cls.full_width_seconds = time.monotonic()-begin
        cls.theta_ref = reference_theta()

    def test_actual4131_full_cholesky_matches_independent_decimal_root(self):
        theta = np.asarray(self.model['coefficients']); gradient = np.asarray(self.model['final_gradient'])
        objective, independent_gradient, _ = scalar_reference(theta, self.x, self.y, self.w)
        np.testing.assert_allclose(theta, self.theta_ref, rtol=0., atol=1e-8)
        inactive = np.ones(4131, dtype=bool); inactive[list(ACTIVE)] = False
        self.assertFalse(theta[inactive].any()); self.assertFalse(gradient[inactive].any())
        self.assertLessEqual(float(np.max(np.abs(independent_gradient))), 1e-8)
        np.testing.assert_allclose(gradient, independent_gradient, rtol=0., atol=2e-14)
        self.assertAlmostEqual(self.model['optimization']['objective'], objective, places=12)
        self.assertEqual(theta[0], theta[1])
        meta = self.model['optimization']
        self.assertGreater(meta['updates'], 0)
        self.assertEqual(meta['loop_evaluations'], meta['updates']+1)
        self.assertEqual(meta['linear_solves'], meta['updates'])
        self.assertEqual(meta['hessian_evaluations'], meta['updates'])
        self.assertEqual(meta['final_checks'], 1)
        self.assertLessEqual(meta['total_evaluations'], 2002)
        self.assertTrue(all(r['normalized_solve_residual'] <= 1e-12 for r in meta['trace'][:-1]))

    def test_independent_scalar_derivatives_and_zero_offset(self):
        theta = np.zeros(4131); theta[list(ACTIVE)] = [.5, -.2, 1.3, -.7]
        value, g = solver.objective_and_gradient(theta, self.x, self.y, self.w, spec=SPEC)
        expected, scalar_g, scalar_h = scalar_reference(theta, self.x, self.y, self.w)
        self.assertAlmostEqual(value, expected, places=12)
        np.testing.assert_allclose(g, scalar_g, rtol=0., atol=2e-14)
        with threadpool_limits(limits=1):
            h = solver._hessian(theta, sparse.csr_matrix(self.x), 2.*self.y-1., self.w, np.zeros(6))
        for (j, k), number in scalar_h.items(): self.assertAlmostEqual(float(h[j, k]), number, places=12)
        for j in ACTIVE:
            delta = np.zeros(4131); delta[j] = 1e-5
            a = scalar_reference(theta+delta, self.x, self.y, self.w)[0]
            b = scalar_reference(theta-delta, self.x, self.y, self.w)[0]
            self.assertAlmostEqual(float(g[j]), (a-b)/2e-5, places=8)
        for function in (solver.fit_joint, solver.objective_and_gradient):
            self.assertNotIn('base_margin', inspect.signature(function).parameters)
            self.assertNotIn('offset', inspect.signature(function).parameters)
        self.assertEqual(self.model['training']['input_sha256']['base_margin'], hash_arrays(np.zeros(6, dtype='<f8')))
        with self.assertRaises(TypeError): solver.fit_joint(self.x, self.y, self.w, spec=SPEC, base_margin=np.ones(6))

    def test_noncanonical_duplicates_explicit_zeros_dense_parity_and_hashes(self):
        # Same matrix through duplicated, reversed and explicit-zero CSR entries.
        values = []; indices = []; pointers = [0]
        for row in self.x:
            for j in reversed(np.flatnonzero(row)):
                values.extend((row[j]/2, row[j]/2)); indices.extend((int(j), int(j)))
            values.append(-0.); indices.append(4130); pointers.append(len(values))
        supplied = sparse.csr_matrix((np.array(values), np.array(indices), np.array(pointers)), shape=self.x.shape)
        supplied.has_sorted_indices = supplied.has_canonical_format = True  # Untrusted cached flags.
        before = supplied.data.tobytes()
        canonical, y, weights, offset = solver._prepare(supplied, self.y, self.w, SPEC)
        self.assertEqual(supplied.data.tobytes(), before)
        np.testing.assert_array_equal(canonical.toarray(), self.x)
        self.assertTrue(canonical.has_canonical_format); self.assertFalse(np.any(canonical.data == 0.))
        expected = hash_arrays(np.array(canonical.shape, dtype='<i8'), canonical.indptr.astype('<i8'),
            canonical.indices.astype('<i8'), canonical.data.astype('<f8'))
        self.assertEqual(expected, self.model['training']['input_sha256']['features'])
        self.assertEqual(hash_arrays(y.astype('<i8')), self.model['training']['input_sha256']['labels'])
        self.assertEqual(hash_arrays(weights.astype('<f8')), self.model['training']['input_sha256']['weights'])
        # Coalescing is not permission to hide nonfinite input or overflow.
        supplied.data[0] = np.inf
        with self.assertRaises(ValueError): solver._prepare(supplied, self.y, self.w, SPEC)

    def test_input_contract_rejects_wrong_dimension_types_mirrors_and_mass(self):
        for x, y, w in ((self.x[:, :32], self.y, self.w), (self.x.astype(np.float32), self.y, self.w),
                (sparse.coo_matrix(self.x), self.y, self.w), (self.x, self.y.astype(bool), self.w),
                (self.x, self.y.astype(float), self.w), (self.x, np.ones(6, dtype=int), self.w),
                (self.x, self.y, self.w.astype(bool)), (self.x, self.y, self.w+1),
                (self.x, self.y, np.full(6, np.nan)), (self.x[::2], self.y[::2], self.w[::2])):
            with self.assertRaises(ValueError): solver._prepare(x, y, w, SPEC)
        broken = self.x.copy(); broken[1, 0] += .01
        with self.assertRaises(ValueError): solver._prepare(broken, self.y, self.w, SPEC)

    def test_strict_loop_and_separate_final_check_without_acceptance_allowance(self):
        x = np.zeros((2, 4131)); y = np.array([1, 0]); weights = np.array([950., 950.])
        def evaluation(norm):
            g = np.zeros(4131); g[0] = norm
            return 190.*math.log(2.), g, 190.*math.log(2.), 0.
        with patch.object(solver, '_evaluate', side_effect=[evaluation(1e-8), evaluation(1e-8)]) as calls:
            model = solver.fit_joint(x, y, weights, spec=SPEC)
            self.assertEqual(calls.call_count, 2); self.assertEqual(model['optimization']['updates'], 0)
        with patch.object(solver, '_evaluate', side_effect=[evaluation(1e-8), evaluation(np.nextafter(1e-8, math.inf))]):
            with self.assertRaises(solver.JointOptimizationError) as caught: solver.fit_joint(x, y, weights, spec=SPEC)
        self.assertEqual(caught.exception.diagnostics['status'], 'final_check_failed')
        json.dumps(caught.exception.diagnostics, allow_nan=False)
        with patch.object(solver, '_evaluate', return_value=evaluation(np.nextafter(1e-8, math.inf))), \
             patch.object(solver, '_hessian', side_effect=RuntimeError('must continue, not accept')) as h:
            with self.assertRaises(solver.JointOptimizationError): solver.fit_joint(x, y, weights, spec=SPEC)
        self.assertEqual(h.call_count, 1)

    def test_fixed2000_update_budget_no_finalcheck_retry_or_fallback(self):
        zero = np.zeros((2, 4131)); y = np.array([1, 0]); w = np.array([950., 950.])
        g = np.zeros(4131); g[0] = 1.
        direction = np.zeros(4131); direction[0] = .001
        evaluated = (1., g, 1., 0., 1., 1.)
        with patch.object(solver, '_checked_evaluate', return_value=evaluated), \
             patch.object(solver, '_hessian', return_value=None), \
             patch.object(solver, '_direction', return_value=direction), \
             patch.object(solver, '_step_quantities', return_value=dict(a=1., q=1., r=0., alpha=1., normalized_solve_residual=0.)):
            with self.assertRaises(solver.JointOptimizationError) as caught: solver.fit_joint(zero, y, w, spec=SPEC)
        d = caught.exception.diagnostics
        self.assertEqual(d['status'], 'update_budget_exhausted')
        self.assertEqual((d['updates'], d['loop_evaluations'], d['hessian_evaluations'], d['linear_solves'], d['final_checks'], d['total_evaluations']),
            (2000, 2001, 2000, 2000, 0, 2001))
        self.assertEqual(len(d['trace']), 2001)
        self.assertEqual(len(d['final_theta']), 4131); json.dumps(d, allow_nan=False)

    def test_resealed_model_schema_gradient_hash_and_zero_offset_tampering(self):
        mutators = (
            lambda m: m['configuration'].__setitem__('dimension', 32),
            lambda m: m['configuration'].__setitem__('kind', 'fixed_repair_progress_offset_newton_v1'),
            lambda m: m['optimization'].__setitem__('final_checks', True),
            lambda m: m['optimization'].__setitem__('linear_solves', m['optimization']['linear_solves']+1),
            lambda m: m['final_gradient'].__setitem__(0, float(np.nextafter(1e-8, math.inf))),
            lambda m: m['coefficients'].__setitem__(0, '0'),
            lambda m: m['training']['input_sha256'].__setitem__('features', 'not-sha'),
            lambda m: m['training']['input_sha256'].__setitem__('base_margin', 'b'*64),
            lambda m: m['optimization']['trace'][0].__setitem__('normalized_solve_residual', float(np.nextafter(1e-12, math.inf))),
        )
        for i, mutate in enumerate(mutators):
            with self.subTest(mutation=i):
                model = copy.deepcopy(self.model); mutate(model); reseal(model)
                with self.assertRaises(ValueError): solver.validate_model(model, expected_spec=SPEC)
        model = copy.deepcopy(self.model); model['model_sha256'] = '0'*64
        with self.assertRaises(ValueError): solver.validate_model(model, expected_spec=SPEC)

    def test_exact_norm_residual_boundary_and_no_non_descent_step(self):
        # A controlled norm consumer isolates the strict <= predicate; actual
        # Cholesky residual arithmetic is independently covered by the full fit.
        h = np.eye(4131); g = np.zeros(4131); g[0] = -.5
        p = np.zeros(4131); p[0] = 1.; x = sparse.csr_matrix((2, 4131))
        norm = 5e11-.5
        with patch.object(solver.np.linalg, 'norm', return_value=norm):
            result = solver._step_quantities(x, h, g, p)
        self.assertEqual(result['normalized_solve_residual'], 1e-12)
        self.assertEqual(result['alpha'], .5)
        with patch.object(solver.np.linalg, 'norm', return_value=np.nextafter(norm, 0.)):
            with self.assertRaises(FloatingPointError): solver._step_quantities(x, h, g, p)
        with self.assertRaises(FloatingPointError): solver._step_quantities(x, h, -g, p)


if __name__ == '__main__': unittest.main()
