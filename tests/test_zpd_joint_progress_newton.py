"""Supplied synthetic matrices only: full4131 numerical and failure witnesses.

Run with BLAS thread environment fixed to one. The actual solver always forms
the full4131 Hessian; only independent reference mathematics is low-dimensional.
No empirical inputs, models, labels, execution artifacts or remote I/O.
"""
import copy
from dataclasses import replace
from decimal import Decimal, localcontext
import inspect
import json
import math
import resource
import sys
import time
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from scipy.optimize import brentq

from scripts import zpd_joint_progress_newton as solver
from scripts import zpd_repair_progress_newton as progress_solver
from scripts import zpd_repair_residual_newton as directed_solver


SPEC = solver.ResidualSpec('synthetic_joint_raw_current_progress_v1', 4131, 'a'*64, solver.KIND)


def arrays(arm='H'):
    x = np.zeros((8, 4131), dtype=np.float64)
    # Duplicate current columns (rank deficiency), a near-constant very small
    # numeric column, nonzero G/R, and one retained zero-difference pair.
    x[0, :3] = [1., 1., 1e-12]
    if arm != 'C_joint': x[2, 4099] = 2.
    if arm not in ('CF', 'C_joint'): x[4, 4115] = -.5
    x[1::2] = -x[::2]
    labels = np.tile(np.array([1, 0], dtype=np.int64), 4)
    weights = np.array([300., 300., 250., 250., 200., 200., 200., 200.])
    return x, labels, weights


def zero_arrays():
    return np.zeros((2, 4131)), np.array([1, 0], dtype=np.int64), np.full(2, 950.)


def reference(x, labels, weights, theta):
    """Independent scalar fsum implementation, no producer arithmetic helpers."""
    signed = [2*int(value)-1 for value in labels]
    columns = [j for j in range(4131) if np.any(x[:, j])]
    margins = [math.fsum(float(x[i, j])*float(theta[j]) for j in columns) for i in range(len(labels))]
    def logistic(value):
        return math.exp(-value)/(1.+math.exp(-value)) if value >= 0. else 1./(1.+math.exp(value))
    loss = math.fsum(.1*float(weights[i])*(max(0., -signed[i]*margins[i])
        + math.log1p(math.exp(-abs(signed[i]*margins[i])))) for i in range(len(labels)))
    gradient = np.array(theta, dtype=np.float64, copy=True)
    for j in columns:
        gradient[j] -= math.fsum(.1*float(weights[i])*signed[i]*float(x[i, j])*logistic(signed[i]*margins[i])
                                for i in range(len(labels)))
    return .5*math.fsum(float(v)*float(v) for v in theta)+loss, gradient


def scalar_optimum(arm):
    result = np.zeros(4131)
    # For disjoint feature directions v, theta=s*v and s=A/(1+exp(||v||²s)).
    s = brentq(lambda v: v-60./(1.+math.exp(2.*v)), 0., 10., xtol=1e-14)
    result[:3] = [s, s, 1e-12*s]
    if arm != 'C_joint':
        s = brentq(lambda v: v-50./(1.+math.exp(4.*v)), 0., 10., xtol=1e-14)
        result[4099] = 2.*s
    if arm not in ('CF', 'C_joint'):
        s = brentq(lambda v: v-40./(1.+math.exp(.25*v)), 0., 30., xtol=1e-14)
        result[4115] = -.5*s
    return result


def reseal(model):
    model['model_sha256'] = solver._model_hash({key: value for key, value in model.items() if key != 'model_sha256'})
    return model


class JointNewtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = {}; cls.resources = []; cls.hessian_shapes = []
        real_hessian = solver._hessian
        def observed_hessian(*args):
            result = real_hessian(*args)
            cls.hessian_shapes.append(result.shape)
            return result
        # No mocked solver arithmetic in these three actual full4131 fits.
        with patch.object(solver, '_hessian', new=observed_hessian):
            for arm in ('H', 'CF', 'C_joint'):
                started = time.perf_counter()
                cls.models[arm] = solver.fit_joint(*arrays(arm), spec=SPEC)
                usage = resource.getrusage(resource.RUSAGE_SELF)
                cls.resources.append(dict(arm=arm, elapsed_seconds=time.perf_counter()-started,
                    maxrss=usage.ru_maxrss, maxrss_units='bytes' if sys.platform == 'darwin' else 'KiB',
                    updates=cls.models[arm]['optimization']['updates']))
        cls.zero_model = solver.fit_joint(*zero_arrays(), spec=SPEC)
        print('JOINT4131_SYNTHETIC_RESOURCE '+json.dumps(cls.resources, sort_keys=True), flush=True)

    def test_actual_full4131_solve_against_independent_scalar_optima_and_full_gradient(self):
        self.assertTrue(self.hessian_shapes)
        self.assertTrue(all(shape == (4131, 4131) for shape in self.hessian_shapes))
        self.assertEqual(len(self.hessian_shapes), sum(model['optimization']['hessian_evaluations'] for model in self.models.values()))
        for arm, model in self.models.items():
            with self.subTest(arm=arm):
                theta = solver.validate_model(model, expected_spec=SPEC)
                np.testing.assert_allclose(theta, scalar_optimum(arm), rtol=0., atol=1e-8)
                objective, gradient = reference(*arrays(arm), theta)
                self.assertLessEqual(float(np.max(np.abs(gradient))), 1e-8)
                self.assertAlmostEqual(objective, model['optimization']['objective'], delta=2e-12)
                np.testing.assert_allclose(gradient, model['final_gradient'], rtol=0., atol=2e-13)
                np.testing.assert_array_equal(theta[3:4099], np.zeros(4096))
                self.assertEqual(theta[0], theta[1])
                self.assertGreater(model['optimization']['updates'], 0)

    def test_cf_and_cjoint_zero_columns_without_slicing_the_solver(self):
        np.testing.assert_array_equal(self.models['CF']['coefficients'][4115:], np.zeros(16))
        np.testing.assert_array_equal(self.models['C_joint']['coefficients'][4099:], np.zeros(32))
        self.assertNotEqual(self.models['CF']['coefficients'][4099], 0.)
        self.assertNotEqual(self.models['H']['coefficients'][4115], 0.)
        for arm in self.models:
            self.assertEqual(len(self.models[arm]['coefficients']), 4131)
            self.assertEqual(self.models[arm]['training']['rows'], 8)
            self.assertEqual(self.models[arm]['training']['zero_difference_rows'], {'H':2, 'CF':4, 'C_joint':6}[arm])
            self.assertEqual(self.models[arm]['training']['weight_mass'], 1900.)

    def test_native_counter_trace_and_explicit_unbounded_current_curvature(self):
        for model in self.models.values():
            meta = model['optimization']; updates = meta['updates']
            self.assertEqual(meta['loop_evaluations'], updates+1)
            self.assertEqual(meta['total_evaluations'], updates+2)
            self.assertEqual(meta['final_checks'], 1)
            self.assertEqual(meta['hessian_evaluations'], updates)
            self.assertEqual(meta['linear_solves'], updates)
            self.assertEqual(len(meta['trace']), updates+1)
            self.assertLessEqual(meta['gradient_infinity_norm'], 1e-8)
            for row in meta['trace'][:-1]:
                expected = min(1., math.log1p(row['r']*(row['a']/row['q']))/row['r']) if row['r'] else min(1., row['a']/row['q'])
                self.assertEqual(row['alpha'], expected)
                self.assertLessEqual(row['normalized_solve_residual'], 1e-12)
        info = self.models['H']['training']
        self.assertGreater(info['maximum_row_squared_norm'], 1.)
        self.assertGreater(info['hessian_spectral_upper_bound'], 48.5)
        self.assertAlmostEqual(info['hessian_spectral_upper_bound'], 1.+.025*info['weighted_row_squared_norm_sum'])
        self.assertNotIn('gtol', self.models['H']['configuration'])
        self.assertNotIn('ftol', self.models['H']['configuration'])

    def test_decimal_objective_gradient_and_full_hessian_finite_difference(self):
        x, labels, weights = zero_arrays(); x[0, 0] = 1.; x[1, 0] = -1.
        theta = np.zeros(4131); theta[0] = -.375
        value, gradient = solver.objective_and_gradient(theta, x, labels, weights, spec=SPEC)
        matrix, targets, w, zero = solver._prepare(x, labels, weights, SPEC)
        hessian = solver._hessian(theta, matrix, 2.*targets-1., w, zero)
        with localcontext() as context:
            context.prec = 90; t = Decimal('-.375'); e = t.exp()
            f = t*t/2+Decimal(190)*(1+(-t).exp()).ln()
            g = t-Decimal(190)/(1+e)
            h = 1+Decimal(190)*e/(1+e)**2
        self.assertAlmostEqual(value, float(f), delta=5e-14)
        self.assertAlmostEqual(gradient[0], float(g), delta=3e-14)
        self.assertAlmostEqual(hessian[0, 0], float(h), delta=2e-14)
        np.testing.assert_array_equal(hessian, hessian.T)
        np.testing.assert_array_equal(np.diag(hessian)[1:], np.ones(4130))
        for column in (0, 4130):
            plus = theta.copy(); minus = theta.copy(); plus[column] += 1e-5; minus[column] -= 1e-5
            ga = solver.objective_and_gradient(plus, x, labels, weights, spec=SPEC)[1]
            gb = solver.objective_and_gradient(minus, x, labels, weights, spec=SPEC)[1]
            np.testing.assert_allclose(hessian[:, column], (ga-gb)/2e-5, rtol=1e-9, atol=2e-9)

    def test_noncanonical_csr_coalesced_before_strict_primitive_without_input_mutation(self):
        data = np.array([0., .25, .75, -.0, -.75, -.25])
        indices = np.array([2, 0, 0, 2, 0, 0], dtype=np.int32)
        pointer = np.array([0, 3, 6], dtype=np.int32)
        x = sparse.csr_matrix((data, indices, pointer), shape=(2, 4131))
        x.has_canonical_format = True; x.has_sorted_indices = True  # hostile stale cache
        before = (x.data.copy(), x.indices.copy(), x.indptr.copy())
        _, labels, weights = zero_arrays()
        canonical, target, weight, offset = solver._prepare(x, labels, weights, SPEC)
        self.assertTrue(canonical.has_canonical_format); self.assertEqual(canonical.nnz, 2)
        self.assertEqual(canonical[0, 0], 1.); self.assertEqual(canonical[1, 0], -1.)
        for old, current in zip(before, (x.data, x.indices, x.indptr)): np.testing.assert_array_equal(old, current)
        dense = np.zeros((2, 4131)); dense[0, 0] = 1.; dense[1, 0] = -1.
        theta = np.linspace(-.01, .01, 4131)
        f1, g1 = solver.objective_and_gradient(theta, x, labels, weights, spec=SPEC)
        f2, g2 = solver.objective_and_gradient(theta, dense, labels, weights, spec=SPEC)
        self.assertEqual(f1, f2); np.testing.assert_array_equal(g1, g2)
        np.testing.assert_array_equal(offset, np.zeros(2))

    def test_canonical_array_hashes_include_private_literal_zero(self):
        matrix, labels, weights, zero = solver._prepare(*arrays(), SPEC)
        expected = solver.core.arithmetic._training_metadata(matrix, labels, weights, zero)
        self.assertEqual(expected, self.models['H']['training'])
        self.assertEqual(expected['input_sha256']['base_margin'], solver._sha_arrays(np.zeros(8, dtype='<f8')))
        copied = sparse.csr_matrix(arrays()[0])
        self.assertEqual(solver._prepare(copied, arrays()[1], arrays()[2], SPEC)[0].shape, (8, 4131))

    def test_no_offset_or_hyperparameter_argument_and_old_modules_unchanged(self):
        self.assertEqual(tuple(inspect.signature(solver.fit_joint).parameters), ('x', 'labels', 'weights', 'spec'))
        self.assertEqual(tuple(inspect.signature(solver.objective_and_gradient).parameters), ('theta', 'x', 'labels', 'weights', 'spec'))
        with self.assertRaises(TypeError): solver.fit_joint(*zero_arrays(), base=np.zeros(2), spec=SPEC)
        with self.assertRaises(TypeError): solver.fit_joint(*zero_arrays(), max_updates=3, spec=SPEC)
        self.assertEqual(progress_solver.DIMENSION, 32); self.assertEqual(directed_solver.DIMENSION, 144)
        self.assertIs(solver.ResidualSpec, solver.core.ResidualSpec)
        self.assertEqual(solver.configuration(SPEC)['primitive_source_files'], list(solver.PRIMITIVE_SOURCE_FILES))

    def test_zero_design_retains_rows_and_two_distinct_evaluations(self):
        with patch.object(solver, '_evaluate', wraps=solver._evaluate) as evaluate, \
                patch.object(solver, '_hessian', side_effect=AssertionError('must not form zero-design Hessian')):
            model = solver.fit_joint(*zero_arrays(), spec=SPEC)
        self.assertEqual(evaluate.call_count, 2)
        self.assertEqual(model['optimization']['updates'], 0)
        self.assertEqual(model['optimization']['total_evaluations'], 2)
        np.testing.assert_array_equal(model['coefficients'], np.zeros(4131))
        self.assertEqual(model['training']['zero_difference_rows'], 2)

    def test_dense_csr_wrong_types_shapes_nonfinite_and_exact_mirrors(self):
        x, y, w = zero_arrays(); x[0, 0] = 1.; x[1, 0] = -1.
        bad = [(x.astype(np.float32), y, w), (x[:, :-1], y, w), (x.tolist(), y, w),
               (sparse.csc_matrix(x), y, w), (x, y.astype(bool), w), (x, y.astype(float), w),
               (x, y.tolist(), w), (x, np.array([1, 1]), w), (x, y, np.array([949., 951.])),
               (x, y, np.full(2, 1.)), (x, y, w.astype(np.float32)),
               (x[:1], y[:1], w[:1]), (x[:0], y[:0], w[:0])]
        for replacement in (np.nan, np.inf):
            malformed = x.copy(); malformed[0, 0] = replacement; bad.append((malformed, y, w))
        broken = x.copy(); broken[1, 0] = -.9; bad.append((broken, y, w))
        for args in bad:
            with self.subTest(types=tuple(type(a).__name__ for a in args)), self.assertRaises((ValueError, TypeError)):
                solver.fit_joint(*args, spec=SPEC)
        malformed = sparse.csr_matrix(x); malformed.indices[0] = 5000
        with self.assertRaises(ValueError): solver.fit_joint(malformed, y, w, spec=SPEC)
        duplicate = sparse.csr_matrix((np.array([1e308, 1e308, -1e308, -1e308]),
            np.array([0, 0, 0, 0]), np.array([0, 2, 4])), shape=(2, 4131))
        with self.assertRaises(ValueError): solver.fit_joint(duplicate, y, w, spec=SPEC)

    def test_native_spec_and_external_feature_configuration_mismatch(self):
        for spec in (replace(SPEC, dimension=32), replace(SPEC, dimension=144), replace(SPEC, model_kind=progress_solver.KIND)):
            with self.assertRaises(ValueError): solver.fit_joint(*zero_arrays(), spec=spec)
        for spec in (replace(SPEC, feature_configuration_sha256='b'*64), replace(SPEC, representation='different')):
            with self.assertRaises(ValueError): solver.validate_model(self.models['H'], expected_spec=spec)

    def test_strict_boundary_and_fresh_final_recheck(self):
        def evaluation(norm):
            gradient = np.zeros(4131); gradient[0] = norm
            return 100., gradient, 100., 0.
        with patch.object(solver, '_evaluate', return_value=evaluation(1e-8)) as calls:
            model = solver.fit_joint(*zero_arrays(), spec=SPEC)
        self.assertEqual(calls.call_count, 2); self.assertEqual(model['optimization']['gradient_infinity_norm'], 1e-8)
        above = float(np.nextafter(1e-8, math.inf))
        with patch.object(solver, '_evaluate', side_effect=[evaluation(1e-8), evaluation(above)]):
            with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(*zero_arrays(), spec=SPEC)
        self.assertEqual(error.exception.diagnostics['status'], 'final_check_failed')
        self.assertEqual(error.exception.diagnostics['final_checks'], 1)
        with patch.object(solver, '_evaluate', return_value=evaluation(above)), \
                patch.object(solver, '_hessian', side_effect=RuntimeError('strictly above must continue')):
            with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(*zero_arrays(), spec=SPEC)
        self.assertEqual(error.exception.diagnostics['final_checks'], 0)

    def test_nonfinite_malformed_evaluation_and_overflow_have_finite_failure_json(self):
        zero = np.zeros(4131)
        bad = [(float('nan'), zero, 0., 0.), (0., zero, float('inf'), 0.), (0., zero, 0., float('nan')),
               (0., np.zeros(4130), 0., 0.), (0., np.zeros(4131, dtype=np.float32), 0., 0.),
               (0., np.full(4131, np.nan), 0., 0.), (0., np.full(4131, 1e308), 0., 0.)]
        for result in bad:
            with patch.object(solver, '_evaluate', return_value=result):
                with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(*zero_arrays(), spec=SPEC)
            body = error.exception.diagnostics; json.dumps(body, allow_nan=False)
            self.assertEqual(body['trace'], []); self.assertIsNone(body['initial_objective'])
            self.assertEqual(body['updates'], 0)
        with patch.object(solver, '_evaluate', side_effect=[(0., zero, 0., 0.), bad[0]]):
            with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(*zero_arrays(), spec=SPEC)
        json.dumps(error.exception.diagnostics, allow_nan=False)
        self.assertEqual(error.exception.diagnostics['status'], 'final_check_failed')
        x, labels, weights = zero_arrays(); x[0, 0] = 1e200; x[1, 0] = -1e200
        with np.errstate(over='ignore', invalid='ignore'):
            with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(x, labels, weights, spec=SPEC)
        self.assertEqual(error.exception.diagnostics['status'], 'training_metadata_failed')
        json.dumps(error.exception.diagnostics, allow_nan=False)

    def test_failure_before_success_has_no_retry_or_accepted_model(self):
        for helper in ('_hessian', '_direction', '_step_quantities', '_updated'):
            changes = {'_hessian': lambda *args: None, '_direction': lambda *args: np.ones(4131),
                       '_step_quantities': lambda *args: dict(a=1., q=1., r=0., alpha=1., normalized_solve_residual=0.)}
            contexts = [patch.object(solver, key, new=value) for key, value in changes.items() if key != helper]
            for context in contexts: context.start()
            try:
                with patch.object(solver, helper, side_effect=RuntimeError('injected failure')) as calls:
                    with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(*arrays(), spec=SPEC)
                self.assertEqual(calls.call_count, 1); self.assertEqual(error.exception.diagnostics['updates'], 0)
                self.assertFalse(error.exception.diagnostics['accepted']); json.dumps(error.exception.diagnostics, allow_nan=False)
            finally:
                for context in reversed(contexts): context.stop()

    def test_bad_solve_residual_spd_and_unchanged_iterate_fail_closed(self):
        # Full shape validation but no repeated full decompositions for injected failures.
        with self.assertRaises(ValueError): solver._direction(np.eye(2), np.zeros(4131))
        h = np.eye(4131); g = np.zeros(4131); g[0] = 1.
        with patch.object(solver, 'cholesky', side_effect=np.linalg.LinAlgError('not SPD')):
            with self.assertRaises(np.linalg.LinAlgError): solver._direction(h, g)
        x = sparse.csr_matrix((2, 4131)); p = -g*.5
        with self.assertRaisesRegex(FloatingPointError, 'residual'): solver._step_quantities(x, h, g, p)
        with self.assertRaises(FloatingPointError): solver._step_quantities(x, h, g, g)
        with self.assertRaisesRegex(FloatingPointError, 'unchanged'): solver._updated(np.full(4131, 1e20), np.ones(4131), 1.)
        with np.errstate(over='ignore'):
            with self.assertRaisesRegex(FloatingPointError, 'nonfinite'): solver._updated(np.full(4131, 1e308), np.full(4131, 1e308), 1.)

    def test_factor_and_both_triangular_boundaries_require_exact_shapes_and_dtype(self):
        h = np.eye(4131); g = np.ones(4131)
        for bad in (np.eye(2), np.zeros((4131, 4131), dtype=np.float32)):
            with patch.object(solver, 'cholesky', return_value=bad), \
                    patch.object(solver, 'solve_triangular', side_effect=AssertionError('bad factor used')):
                with self.assertRaises(FloatingPointError): solver._direction(h, g)
        for bad in (np.zeros(4130), np.zeros(4131, dtype=np.float32), np.zeros(4131, dtype=bool), np.full(4131, np.nan)):
            with patch.object(solver, 'cholesky', return_value=h), \
                    patch.object(solver, 'solve_triangular', return_value=bad) as calls:
                with self.assertRaises(FloatingPointError): solver._direction(h, g)
                self.assertEqual(calls.call_count, 1)
            with patch.object(solver, 'cholesky', return_value=h), \
                    patch.object(solver, 'solve_triangular', side_effect=[g, bad]) as calls:
                with self.assertRaises(FloatingPointError): solver._direction(h, g)
                self.assertEqual(calls.call_count, 2)
        for bad in (np.zeros(4130), np.zeros(4131, dtype=np.float32)):
            with self.assertRaises(ValueError): solver._direction(h, bad)

    def test_exact_update_cap_failure_and_last_allowed_update_fresh_acceptance(self):
        direction = np.zeros(4131); direction[0] = -1.
        def evaluation(theta, *args, success):
            gradient = np.zeros(4131); gradient[0] = 0. if success and theta[0] == -2000. else 1.
            penalty = float((.5*theta)@theta)
            return 1e8, gradient, 1e8-penalty, penalty
        for success in (False, True):
            with patch.object(solver, '_evaluate', new=lambda theta, *a: evaluation(theta, *a, success=success)), \
                    patch.object(solver, '_hessian', new=lambda *a: None), \
                    patch.object(solver, '_direction', new=lambda *a: direction), \
                    patch.object(solver, '_step_quantities', new=lambda *a: dict(a=1., q=1., r=0., alpha=1., normalized_solve_residual=0.)):
                if success:
                    model = solver.fit_joint(*zero_arrays(), spec=SPEC)
                    meta = model['optimization']; self.assertEqual(meta['total_evaluations'], 2002)
                    self.assertEqual(meta['final_checks'], 1); self.assertEqual(len(meta['trace']), 2001)
                else:
                    with self.assertRaises(solver.JointOptimizationError) as error: solver.fit_joint(*zero_arrays(), spec=SPEC)
                    meta = error.exception.diagnostics; self.assertEqual(meta['status'], 'update_budget_exhausted')
                    self.assertEqual(meta['total_evaluations'], 2001); self.assertEqual(meta['final_checks'], 0)
                    json.dumps(meta, allow_nan=False)
                self.assertEqual(meta['updates'], 2000); self.assertEqual(meta['hessian_evaluations'], 2000)
                self.assertEqual(meta['linear_solves'], 2000)

    def test_resealed_schema_counters_trace_and_strict_gradient_tampering_rejected(self):
        def changed(path, value):
            model = copy.deepcopy(self.models['H']); node = model
            for key in path[:-1]: node = node[key]
            node[path[-1]] = value
            return reseal(model)
        mutations = [(('optimization', 'updates'), True), (('optimization', 'total_evaluations'), 2003),
            (('optimization', 'status'), True), (('optimization', 'accepted'), 1),
            (('configuration', 'dimension'), 32), (('configuration', 'offset'), 'supplied'),
            (('optimization', 'trace', 0, 'alpha'), .000001),
            (('optimization', 'trace', 0, 'normalized_solve_residual'), np.nextafter(1e-12, math.inf)),
            (('optimization', 'gradient_infinity_norm'), np.nextafter(1e-8, math.inf)),
            (('final_gradient', 0), np.nextafter(1e-8, math.inf)),
            (('training', 'rows'), True), (('training', 'weight_mass'), 1800.),
            (('training', 'input_sha256', 'base_margin'), 'bad'),
            (('training', 'input_sha256', 'base_margin'), 'f'*64)]
        for path, value in mutations:
            with self.subTest(path=path), self.assertRaises(ValueError): solver.validate_model(changed(path, value), expected_spec=SPEC)
        model = copy.deepcopy(self.models['H']); model['coefficients'].pop()
        with self.assertRaises(ValueError): solver.validate_model(reseal(model), expected_spec=SPEC)
        model = copy.deepcopy(self.zero_model); model['coefficients'][0] = 1.
        with self.assertRaises(ValueError): solver.validate_model(reseal(model), expected_spec=SPEC)
        with self.assertRaises(ValueError): solver.validate_model(dict(self.models['H'], extra=True), expected_spec=SPEC)

    def test_alpha_overflow_nondescent_and_zero_r_explicit_branch(self):
        self.assertEqual(solver._alpha(2., 4., 0.), .5); self.assertEqual(solver._alpha(8., 4., 0.), 1.)
        for values in ((0., 1., 0.), (1., 0., 0.), (1., 1., -1.), (math.inf, 1., 0.), (True, 1., 0.)):
            with self.assertRaises(ValueError): solver._alpha(*values)
        with self.assertRaises(FloatingPointError): solver._alpha(1e308, 1e-308, 1.)
        with self.assertRaises(FloatingPointError): solver._alpha(1e308, 1., 2.)


if __name__ == '__main__':
    unittest.main()
