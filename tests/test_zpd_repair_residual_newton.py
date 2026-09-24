"""Pure synthetic Newton amendment tests; no empirical file/model/label access."""
import copy
from dataclasses import replace
from decimal import Decimal, localcontext
import inspect
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from scipy.optimize import brentq
from scipy.special import expit

from scripts import zpd_repair_residual_newton as solver
from scripts import zpd_repair_residual_core as old
from scripts import zpd_repair_directed_history as directed
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_repair_feedback_pairs import fixture

SPEC = solver.ResidualSpec(directed.VERSION, 144, canonical_hash(directed.configuration()), solver.KIND)


def arrays(base=0., zero=False):
    x = np.zeros((2, 144), dtype=np.float64)
    if not zero: x[0, 0] = 1.; x[1, 0] = -1.
    return x, np.array([1, 0], dtype=np.int64), np.full(2, 950.), np.array([base, -base], dtype=np.float64)


def reseal(model):
    model['model_sha256'] = solver._model_hash({key: value for key, value in model.items() if key != 'model_sha256'})
    return model


class NativeNewtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = solver.fit_offset(*arrays(), spec=SPEC)
        cls.zero_model = solver.fit_offset(*arrays(zero=True), spec=SPEC)

    def test_aliases_preserve_pair_plan_array_hashes_and_original_objective(self):
        for name in ('ResidualSpec', 'CandidateBlock', 'make_pair_plan', 'materialize_pairs', 'objective_and_gradient'):
            self.assertIs(getattr(solver, name), getattr(old, name))
        examples, banks, labels, interactions, base = fixture()
        blocks = {bid: solver.CandidateBlock(value.candidate_ids, value.matrix[:, :144]) for bid, value in interactions.items()}
        plan = solver.make_pair_plan(examples, banks, labels)
        before = old.materialize_pairs(plan, blocks, base, spec=SPEC)
        after = solver.materialize_pairs(plan, blocks, base, spec=SPEC)
        for name in ('matrix', 'y', 'weights', 'base_margin'):
            self.assertEqual(solver._sha_arrays(getattr(before, name)), solver._sha_arrays(getattr(after, name)))
        self.assertEqual(before.metadata, after.metadata)
        theta = np.linspace(-.3, .2, 144)
        first = old.objective_and_gradient(theta, *arrays(base=.4), spec=SPEC)
        second = solver.objective_and_gradient(theta, *arrays(base=.4), spec=SPEC)
        self.assertEqual(first[0], second[0]); np.testing.assert_array_equal(first[1], second[1])

    def test_scalar_high_precision_objective_gradient_and_hessian(self):
        x, y, w, base = arrays(base=.25); theta = np.zeros(144); theta[0] = -.375
        matrix, labels, weights, offset = old._prepare(x, y, w, base, SPEC)
        value, gradient = solver.objective_and_gradient(theta, x, y, w, base, spec=SPEC)
        hessian = solver._hessian(theta, matrix, 2.*labels-1., weights, offset)
        with localcontext() as context:
            context.prec = 90
            t = Decimal('-.375'); b = Decimal('.25'); exponential = (t+b).exp()
            expected_value = t*t/2+Decimal(190)*(1+(-t-b).exp()).ln()
            expected_gradient = t-Decimal(190)/(1+exponential)
            expected_hessian = 1+Decimal(190)*exponential/(1+exponential)**2
        self.assertAlmostEqual(value, float(expected_value), delta=5e-14)
        self.assertAlmostEqual(gradient[0], float(expected_gradient), delta=3e-14)
        self.assertAlmostEqual(hessian[0, 0], float(expected_hessian), delta=2e-14)
        np.testing.assert_array_equal(np.diag(hessian)[1:], np.ones(143))

    def test_finite_difference_hessian_and_symmetric_spd(self):
        x = np.zeros((6, 144)); x[::2, :3] = [[1., .3, 0.], [0., 1., -.2], [.1, .2, .5]]; x[1::2] = -x[::2]
        y = np.array([1, 0, 0, 1, 1, 0]); w = np.full(6, 1900/6); base = np.array([.5, -.5, -.2, .2, .4, -.4])
        matrix, labels, weights, offset = old._prepare(x, y, w, base, SPEC)
        theta = np.zeros(144); theta[:3] = [.1, -.2, .3]
        hessian = solver._hessian(theta, matrix, 2.*labels-1., weights, offset)
        np.testing.assert_array_equal(hessian, hessian.T)
        self.assertGreaterEqual(np.linalg.eigvalsh(hessian[:3, :3]).min(), 1.)
        for column in (0, 1, 2, 143):
            plus = theta.copy(); minus = theta.copy(); plus[column] += 1e-5; minus[column] -= 1e-5
            a = solver.objective_and_gradient(plus, x, y, w, base, spec=SPEC)[1]
            b = solver.objective_and_gradient(minus, x, y, w, base, spec=SPEC)[1]
            np.testing.assert_allclose(hessian[:, column], (a-b)/2e-5, rtol=1e-9, atol=2e-9)

    def test_analytic_damping_solve_residual_and_descent_upper_bound(self):
        x, y, w, base = arrays(base=-.5); matrix, labels, weights, offset = old._prepare(x, y, w, base, SPEC)
        theta = np.zeros(144); value, g, _, _ = solver._evaluate(theta, matrix, 2.*labels-1., weights, offset)
        hessian = solver._hessian(theta, matrix, 2.*labels-1., weights, offset)
        p = solver._direction(hessian, g); step = solver._step_quantities(matrix, hessian, g, p)
        self.assertLessEqual(step['normalized_solve_residual'], 1e-12)
        expected = min(1., math.log1p(step['r']*step['a']/step['q'])/step['r'])
        self.assertAlmostEqual(step['alpha'], expected, places=15)
        a, q, r, alpha = (step[key] for key in ('a', 'q', 'r', 'alpha'))
        bound = -alpha*a+q*(math.expm1(r*alpha)-r*alpha)/(r*r)
        changed = solver._evaluate(theta+alpha*p, matrix, 2.*labels-1., weights, offset)[0]-value
        self.assertLess(bound, 0.); self.assertLessEqual(changed, bound+1e-12)
        self.assertEqual(solver._alpha(2., 4., 0.), .5)
        self.assertEqual(solver._alpha(8., 4., 0.), 1.)

    def test_scalar_optimum_and_exact_native_accounting_no_scipy_status_fields(self):
        model = self.model; meta = model['optimization']; optimum = brentq(lambda v: v-190.*expit(-v), 0., 20.)
        self.assertAlmostEqual(model['coefficients'][0], optimum, delta=1e-8)
        np.testing.assert_array_equal(model['coefficients'][1:], np.zeros(143))
        self.assertEqual(meta['status'], 'converged_gradient')
        self.assertLessEqual(meta['gradient_infinity_norm'], 1e-8); self.assertLessEqual(meta['loop_gradient_infinity_norm'], 1e-8)
        self.assertEqual(meta['loop_evaluations'], meta['updates']+1)
        self.assertEqual(meta['hessian_evaluations'], meta['updates']); self.assertEqual(meta['linear_solves'], meta['updates'])
        self.assertEqual(meta['final_checks'], 1); self.assertEqual(meta['total_evaluations'], meta['updates']+2)
        self.assertEqual(len(meta['trace']), meta['loop_evaluations'])
        self.assertNotIn('success', meta); self.assertNotIn('ftol', model['configuration'])
        self.assertNotIn('gtol', model['configuration']); self.assertNotIn('iterations', meta)
        self.assertEqual(model['configuration']['max_total_evaluations'], 2002)
        self.assertEqual(model['configuration']['hessian_symmetrization'], '0.5_times_H_plus_0.5_times_H_transpose')

    def test_two_calls_for_zero_design_and_no_hessian_or_solve(self):
        with patch.object(solver, '_evaluate', wraps=solver._evaluate) as evaluate, \
                patch.object(solver, '_hessian', side_effect=AssertionError('zero D needs no Hessian')):
            model = solver.fit_offset(*arrays(zero=True), spec=SPEC)
        self.assertEqual(evaluate.call_count, 2)
        np.testing.assert_array_equal(model['coefficients'], np.zeros(144))
        self.assertEqual(model['optimization']['updates'], 0)
        self.assertEqual(model['optimization']['total_evaluations'], 2)
        self.assertEqual(len(model['optimization']['trace']), 1)
        self.assertEqual(model['training']['zero_difference_rows'], 2)

    def test_rank_deficient_design_extreme_offsets_and_original_hashes(self):
        for base in (-10000., 10000.):
            x, y, w, offset = arrays(base=base); x[:, 1] = x[:, 0]  # rank1, no jitter
            model = solver.fit_offset(x, y, w, offset, spec=SPEC)
            self.assertLessEqual(model['optimization']['gradient_infinity_norm'], 1e-8)
            self.assertAlmostEqual(model['coefficients'][0], model['coefficients'][1], places=12)
            matrix, labels, weights, margin = old._prepare(x, y, w, offset, SPEC)
            self.assertEqual(model['training'], old.arithmetic._training_metadata(matrix, labels, weights, margin))
        x, y, w, base = arrays()
        other = solver.fit_offset(sparse.csr_matrix(x), y, w, base, spec=SPEC)
        self.assertEqual(self.model['coefficients'], other['coefficients'])
        self.assertEqual(self.model['training']['input_sha256'], other['training']['input_sha256'])

    def test_strict_gradient_boundary_loop_and_independent_final_recheck(self):
        def evaluation(norm):
            gradient = np.zeros(144); gradient[0] = norm
            return 100., gradient, 100., 0.
        with patch.object(solver, '_evaluate', return_value=evaluation(1e-8)) as call:
            model = solver.fit_offset(*arrays(zero=True), spec=SPEC)
        self.assertEqual(call.call_count, 2); self.assertEqual(model['optimization']['gradient_infinity_norm'], 1e-8)
        above = float(np.nextafter(1e-8, math.inf))
        with patch.object(solver, '_evaluate', side_effect=[evaluation(1e-8), evaluation(above)]):
            with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(zero=True), spec=SPEC)
        self.assertEqual(error.exception.diagnostics['status'], 'final_check_failed')
        self.assertEqual(error.exception.diagnostics['final_checks'], 1)
        with patch.object(solver, '_evaluate', return_value=evaluation(above)), \
                patch.object(solver, '_hessian', side_effect=RuntimeError('must continue above strict boundary')):
            with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(zero=True), spec=SPEC)
        self.assertEqual(error.exception.diagnostics['final_checks'], 0)

    def test_nonfinite_wrong_shape_dtype_and_norm_overflow_fail_with_finite_json(self):
        zero = np.zeros(144)
        malformed = [(float('nan'), zero, 0., 0.), (0., zero, float('inf'), 0.), (0., zero, 0., float('nan')),
                     (0., np.zeros(143), 0., 0.), (0., np.zeros(144, dtype=np.float32), 0., 0.),
                     (0., np.full(144, np.nan), 0., 0.), (0., np.full(144, 1e308), 0., 0.)]
        for value in malformed:
            with self.subTest(value=type(value[0])), patch.object(solver, '_evaluate', return_value=value):
                with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(zero=True), spec=SPEC)
            body = error.exception.diagnostics
            self.assertEqual(body['trace'], []); self.assertIsNone(body['initial_objective'])
            self.assertEqual(body['loop_evaluations'], 1)
            json.dumps(body, allow_nan=False)
        with patch.object(solver, '_evaluate', side_effect=[(0., zero, 0., 0.), malformed[0]]):
            with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(zero=True), spec=SPEC)
        self.assertEqual(error.exception.diagnostics['final_checks'], 1)
        json.dumps(error.exception.diagnostics, allow_nan=False)

    def test_nonfinite_nonspd_nondescent_and_bad_solve_fail_without_retry(self):
        bad_helpers = [('_hessian', lambda *args: np.full((144, 144), np.nan)),
                       ('_hessian', lambda *args: -np.eye(144)),
                       ('_direction', lambda h, g: g),
                       ('_direction', lambda h, g: np.zeros(144))]
        actual_direction = solver._direction
        bad_helpers.append(('_direction', lambda h, g: .5*actual_direction(h, g)))
        for name, side_effect in bad_helpers:
            with self.subTest(name=name), patch.object(solver, name, side_effect=side_effect) as call:
                with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(), spec=SPEC)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(error.exception.diagnostics['updates'], 0)
            self.assertFalse(error.exception.diagnostics['accepted'])
            json.dumps(error.exception.diagnostics, allow_nan=False)

    def test_unchanged_step_and_nonfinite_update_are_not_convergence(self):
        with self.assertRaisesRegex(FloatingPointError, 'unchanged'):
            solver._updated(np.full(144, 1e20), np.ones(144), 1.)
        with self.assertRaisesRegex(FloatingPointError, 'nonfinite'):
            solver._updated(np.full(144, 1e308), np.full(144, 1e308), 1.)
        with patch.object(solver, '_updated', side_effect=FloatingPointError('unchanged Newton iterate')):
            with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(), spec=SPEC)
        self.assertEqual(error.exception.diagnostics['status'], 'iterate_update_failed')
        self.assertEqual(error.exception.diagnostics['updates'], 0)
        self.assertEqual(error.exception.diagnostics['final_checks'], 0)

    def test_exact_2000_update_budget_trace_and_no_final_or_retry(self):
        gradient = np.zeros(144); gradient[0] = 1.
        with patch.object(solver, '_evaluate', return_value=(100., gradient, 100., 0.)) as evaluate, \
                patch.object(solver, '_hessian', return_value=np.eye(144)) as hessian, \
                patch.object(solver, '_direction', return_value=-gradient) as direction:
            with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(zero=True), spec=SPEC)
        info = error.exception.diagnostics
        self.assertEqual(info['status'], 'update_budget_exhausted')
        self.assertEqual(info['updates'], 2000); self.assertEqual(info['loop_evaluations'], 2001)
        self.assertEqual(info['hessian_evaluations'], 2000); self.assertEqual(info['linear_solves'], 2000)
        self.assertEqual(info['final_checks'], 0); self.assertEqual(info['total_evaluations'], 2001)
        self.assertEqual(len(info['trace']), 2001); self.assertEqual(evaluate.call_count, 2001)
        self.assertEqual(hessian.call_count, 2000); self.assertEqual(direction.call_count, 2000)
        self.assertEqual(info['final_theta'][0], -2000.)
        json.dumps(info, allow_nan=False)

    def test_native_configuration_count_trace_and_strict_limit_tampering_rejected(self):
        changes = [lambda m: m['configuration'].update(gtol=1e-8), lambda m: m['configuration'].update(jitter=True),
            lambda m: m['optimization'].update(success=True), lambda m: m['optimization'].update(status=0),
            lambda m: m['optimization'].update(updates=True), lambda m: m['optimization'].update(final_checks=0),
            lambda m: m['optimization'].update(total_evaluations=1),
            lambda m: m['optimization']['trace'][0].update(iteration=1),
            lambda m: m['optimization']['trace'][0].update(alpha=.1),
            lambda m: m['optimization']['trace'][0].update(normalized_solve_residual=1e-11),
            lambda m: m['optimization']['trace'].pop(),
            lambda m: m['final_gradient'].__setitem__(0, float(np.nextafter(1e-8, math.inf))),
            lambda m: m['optimization'].update(loop_gradient_infinity_norm=float(np.nextafter(1e-8, math.inf)))]
        for change in changes:
            model = copy.deepcopy(self.model); change(model); reseal(model)
            with self.assertRaises((ValueError, FloatingPointError)): solver.validate_offset(model, expected_spec=SPEC)
        for spec in (replace(SPEC, dimension=1296), replace(SPEC, model_kind='fixed_repair_directed_offset_logistic_v1'),
                     replace(SPEC, feature_configuration_sha256='b'*64)):
            with self.assertRaises(ValueError): solver.validate_offset(self.model, expected_spec=spec)
        legacy = old.fit_offset(*arrays(), spec=replace(SPEC, model_kind='fixed_repair_directed_offset_logistic_v1'))
        with self.assertRaises(ValueError): solver.validate_offset(legacy, expected_spec=SPEC)

    def test_objective_end_check_and_invalid_input_are_still_enforced(self):
        zero = np.zeros(144)
        with patch.object(solver, '_evaluate', side_effect=[(100., zero, 100., 0.), (101., zero, 101., 0.)]):
            with self.assertRaises(solver.OffsetOptimizationError) as error: solver.fit_offset(*arrays(zero=True), spec=SPEC)
        self.assertIn('end check', error.exception.diagnostics['reason'])
        x, y, w, base = arrays()
        with self.assertRaises(ValueError): solver.fit_offset(x[:, :-1], y, w, base, spec=SPEC)
        with self.assertRaises(ValueError): solver.fit_offset(x, y.astype(bool), w, base, spec=SPEC)
        with self.assertRaises(ValueError): solver.fit_offset(x, y, w-1., base, spec=SPEC)
        x[1, 0] = .5
        with self.assertRaises(ValueError): solver.fit_offset(x, y, w, base, spec=SPEC)

    def test_no_io_native_scorer_fixed_base_sha_tie_and_shared_theta(self):
        ids = ('b'*64, 'a'*64, 'c'*64); block = solver.CandidateBlock(ids, np.zeros((3, 144)))
        base = dict(zip(ids, [.5, .5, -.2]))
        with patch.object(Path, 'open', side_effect=AssertionError('no source/data I/O')):
            self.assertEqual(solver.score_candidates(self.model, block, base, expected_spec=SPEC), base)
            self.assertEqual(solver.select_candidate(self.model, block, base, expected_spec=SPEC), 'a'*64)
            for _arm in ('HS', 'Jm'):
                self.assertEqual(solver.score_candidates(self.model, solver.CandidateBlock(ids, block.matrix), base, expected_spec=SPEC), base)
        self.assertEqual(set(inspect.signature(solver.fit_offset).parameters), {'x', 'labels', 'weights', 'base_margin', 'spec'})
        solver.validate_offset(json.loads(json.dumps(self.model)), expected_spec=SPEC)


if __name__ == '__main__': unittest.main()
