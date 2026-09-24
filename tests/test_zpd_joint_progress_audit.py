"""Synthetic supplied certificates only: no optimizer, files or empirical data."""
import ast
import copy
from dataclasses import make_dataclass
import hashlib
import inspect
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import zpd_joint_progress_audit as audit

SPEC = dict(representation='synthetic_joint_audit', dimension=4131,
    feature_configuration_sha256='a'*64, model_kind='fixed_repair_joint_progress_newton_v1')


def array_sha(*values):
    digest = hashlib.sha256()
    for array in values:
        header = json.dumps({'shape': list(array.shape), 'dtype': array.dtype.str}, sort_keys=True, separators=(',', ':')).encode()
        body = np.ascontiguousarray(array).tobytes()
        digest.update(len(header).to_bytes(8, 'little')); digest.update(header)
        digest.update(len(body).to_bytes(8, 'little')); digest.update(body)
    return digest.hexdigest()


def seal(model):
    model['model_sha256'] = hashlib.sha256(json.dumps({k: v for k, v in model.items() if k != 'model_sha256'},
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return model


def fixture(nonzero=True):
    """Analytic stationary model, not a fit or claim of actual trace execution.

    Let z=ln3, theta=sqrt(190*z/4), x=z/theta. Then x*theta=z and
    theta=190*x/(1+exp(z)). The one recorded update is a schema-consistent toy
    trace only; validating its actual existence is explicitly outside the API.
    """
    theta = np.zeros(4131); x = np.zeros((2, 4131)); y = np.array([1, 0], dtype=np.int64); w = np.full(2, 950.)
    if nonzero:
        z = math.log(3.); theta[4115] = math.sqrt(190.*z/4.)
        x[0, 4115] = z/theta[4115]; x[1, 4115] = -x[0, 4115]
    else: z = 0.
    initial = 190.*math.log(2.); loss = 190.*math.log1p(math.exp(-z)); penalty = .5*float(theta@theta)
    gradient = np.zeros(4131)
    if nonzero: gradient[4115] = theta[4115]-190.*x[0, 4115]/(1+math.exp(z))
    norm = float(np.max(np.abs(gradient))); g2 = math.hypot(*gradient)
    updates = int(nonzero)
    trace = []
    if nonzero:
        trace.append(dict(iteration=0, objective=initial, gradient_infinity_norm=float(95.*x[0, 4115]),
            gradient_l2_norm=float(95.*x[0, 4115]), a=1., q=1., r=0., alpha=1., normalized_solve_residual=0.))
    trace.append(dict(iteration=updates, objective=loss+penalty, gradient_infinity_norm=norm, gradient_l2_norm=g2))
    matrix = sparse.csr_matrix(x); sq = float(x[0]@x[0]); weighted = 1900.*sq
    model = dict(configuration=audit.expected_configuration(SPEC), coefficients=theta.tolist(), final_gradient=gradient.tolist(),
        training=dict(rows=2, unordered_pairs=1, positive_rows=1, zero_difference_rows=0 if nonzero else 2,
            weight_mass=1900., maximum_row_squared_norm=sq, weighted_row_squared_norm_sum=weighted,
            strong_convexity_lower_bound=1., hessian_spectral_upper_bound=1.+.025*weighted,
            input_sha256=dict(features=array_sha(np.array(matrix.shape, dtype='<i8'), matrix.indptr.astype('<i8'),
                matrix.indices.astype('<i8'), matrix.data.astype('<f8')), labels=array_sha(y.astype('<i8')),
                weights=array_sha(w.astype('<f8')), base_margin=array_sha(np.zeros(2, dtype='<f8')))),
        optimization=dict(status='converged_gradient', accepted=True, updates=updates, loop_evaluations=updates+1,
            hessian_evaluations=updates, linear_solves=updates, final_checks=1, total_evaluations=updates+2,
            initial_objective=initial, objective=loss+penalty, weighted_logistic_loss=loss, l2_penalty=penalty,
            loop_gradient_infinity_norm=norm, loop_gradient_l2_norm=g2, gradient_infinity_norm=norm,
            gradient_l2_norm=g2, trace=trace),
        runtime=dict(python='synthetic', numpy='synthetic', scipy='synthetic'))
    return seal(model), x, y, w


def set_value(model, path, value):
    target = model
    for name in path[:-1]: target = target[name]
    target[path[-1]] = value
    return seal(model)


class JointProgressAuditTests(unittest.TestCase):
    def test_analytic_nonzero_and_zero_stationary_certificates_without_optimizer(self):
        for nonzero in (True, False):
            model, x, y, w = fixture(nonzero)
            result = audit.audit_model(model, x, y, w, SPEC)
            self.assertTrue(result['verified']); self.assertEqual(result['dimension'], 4131)
            self.assertLessEqual(result['recomputed']['gradient_infinity_norm'], 1e-8)
            self.assertFalse(result['input_provenance_verified'])
            self.assertFalse(result['actual_intermediate_execution_verified'])
            self.assertFalse(result['runtime_identity_verified'])
            self.assertFalse(result['fitting_authorized']); json.dumps(result, allow_nan=False)
        # Public spec fields may be supplied in a plain dataclass without an
        # import/dependency on the producer ResidualSpec implementation.
        spec_type = make_dataclass('ExternalSpec', [(key, type(value)) for key, value in SPEC.items()], frozen=True)
        model, x, y, w = fixture()
        audit.audit_model(model, x, y, w, spec_type(**SPEC))

    def test_literal_config_matches_frozen_producer_but_audit_never_calls_it(self):
        from scripts import zpd_joint_progress_newton as producer
        spec = producer.ResidualSpec(**SPEC)
        self.assertEqual(audit.expected_configuration(SPEC), producer.configuration(spec))
        model, x, y, w = fixture()
        with patch.object(producer, 'fit_joint', side_effect=AssertionError('no fit')), \
             patch.object(producer, 'validate_model', side_effect=AssertionError('independent validator')), \
             patch.object(producer, '_evaluate', side_effect=AssertionError('independent arithmetic')), \
             patch.object(producer, '_sha_arrays', side_effect=AssertionError('independent framing')):
            self.assertTrue(audit.audit_model(model, x, y, w, SPEC)['verified'])
        tree = ast.parse(inspect.getsource(audit))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and (name.startswith('scripts.') or name.startswith('src.')) for name in imports))

    def test_canonical_duplicate_zero_csr_and_different_integer_width_have_same_certificate(self):
        model, x, y, w = fixture(); value = x[0, 4115]
        raw = sparse.csr_matrix((np.array([0., value/2, value/2, -0., -value/2, -value/2]),
            np.array([2, 4115, 4115, 2, 4115, 4115], dtype=np.int64), np.array([0, 3, 6], dtype=np.int64)), shape=(2, 4131))
        raw.has_canonical_format = raw.has_sorted_indices = True
        before = raw.data.tobytes()
        a = audit.audit_model(model, raw, y.astype(np.int32), w, SPEC)
        b = audit.audit_model(model, x, y, w, SPEC)
        self.assertEqual(a, b); self.assertEqual(before, raw.data.tobytes())

    def test_resealed_model_inputs_configuration_curvature_and_ridge_fail(self):
        model, x, y, w = fixture()
        mutations = [
            (('configuration', 'dimension'), 32), (('configuration', 'C'), True),
            (('configuration', 'offset'), 'supplied'), (('configuration', 'regularization'), 'interaction_only'),
            (('coefficients', 0), 1.), (('coefficients', 1), '0'),
            (('training', 'rows'), True), (('training', 'zero_difference_rows'), 2),
            (('training', 'input_sha256', 'features'), 'b'*64),
            (('training', 'input_sha256', 'base_margin'), 'b'*64),
            (('training', 'hessian_spectral_upper_bound'), 48.5),
            (('training', 'maximum_row_squared_norm'), 0.),
            (('training', 'strong_convexity_lower_bound'), 0.),
            (('training', 'weight_mass'), 1900.+1e-7),
            (('optimization', 'final_checks'), True), (('optimization', 'linear_solves'), 2),
            (('optimization', 'weighted_logistic_loss'), 0.),
            (('optimization', 'trace', 0, 'alpha'), .1),
            (('optimization', 'trace', 0, 'normalized_solve_residual'), float(np.nextafter(1e-12, math.inf))),
        ]
        for path, value in mutations:
            with self.subTest(path=path), self.assertRaises(ValueError):
                audit.audit_model(set_value(copy.deepcopy(model), path, value), x, y, w, SPEC)
        broken = copy.deepcopy(model); broken['coefficients'][0] = .1
        with self.assertRaisesRegex(ValueError, 'checksum'): audit.audit_model(broken, x, y, w, SPEC)
        zero, zx, zy, zw = fixture(False)
        wrong = set_value(zero, ('training', 'maximum_row_squared_norm'), -1e-12)
        with self.assertRaisesRegex(ValueError, 'nonnegative'): audit.audit_model(wrong, zx, zy, zw, SPEC)

    def test_independent_gradient_and_objective_recomputation_not_saved_summary(self):
        model, x, y, w = fixture()
        model['coefficients'][4115] += .01
        # Claim a perfect gradient; none of these self-consistent self-hashes
        # authenticate the new coefficients against the unchanged supplied X.
        model['final_gradient'] = [0.]*4131
        model['optimization']['gradient_infinity_norm'] = model['optimization']['gradient_l2_norm'] = 0.
        seal(model)
        with self.assertRaises(ValueError): audit.audit_model(model, x, y, w, SPEC)

    def test_saved_and_fresh_gradient_boundaries_are_strict_not_numeric_comparison_allowance(self):
        model, x, y, w = fixture(False)
        tiny = float(np.nextafter(1e-8, math.inf))
        changed = set_value(copy.deepcopy(model), ('final_gradient', 0), tiny)
        with self.assertRaises(ValueError): audit.audit_model(changed, x, y, w, SPEC)
        for norm in (1e-8, tiny):
            recomputed = audit._recalculate(audit._matrix(x), y, w, np.zeros(4131))[0]
            recomputed['gradient_infinity_norm'] = norm
            g = np.zeros(4131); g[0] = norm
            changed = copy.deepcopy(model); changed['final_gradient'] = g.tolist()
            for key in ('gradient_infinity_norm', 'gradient_l2_norm', 'loop_gradient_infinity_norm', 'loop_gradient_l2_norm'):
                changed['optimization'][key] = norm
            changed['optimization']['trace'][0]['gradient_infinity_norm'] = norm
            changed['optimization']['trace'][0]['gradient_l2_norm'] = norm
            recomputed['gradient_l2_norm'] = norm; seal(changed)
            with patch.object(audit, '_recalculate', return_value=(recomputed, g)):
                if norm == 1e-8: self.assertTrue(audit.audit_model(changed, x, y, w, SPEC)['verified'])
                else:
                    with self.assertRaisesRegex(ValueError, 'strict.*gradient'): audit.audit_model(changed, x, y, w, SPEC)

    def test_supplied_array_scope_dtype_shape_mass_mirrors_and_nonfinite_rejected(self):
        model, x, y, w = fixture()
        for arrays in ((x[:, :144], y, w), (x.astype(np.float32), y, w), (x, y.astype(bool), w),
                (x, y.astype(float), w), (x, y, w.astype(np.float32)), (x, y, np.array([949., 951.])),
                (x, y, np.array([950., -950.])), (x, y, np.full(2, 1.)),
                (x, y, np.full(2, np.inf)), (sparse.coo_matrix(x), y, w)):
            with self.assertRaises(ValueError): audit.audit_model(model, *arrays, SPEC)
        for val in (np.nan, np.inf, x[1, 4115]+.1):
            wrong = x.copy(); wrong[1, 4115] = val
            with self.assertRaises(ValueError): audit.audit_model(model, wrong, y, w, SPEC)

    def test_independent_scores_allridge_sparse_and_exact_SHA_tiebreak(self):
        theta = np.zeros(4131); theta[0] = 3.; theta[4115] = -2.
        x = sparse.csr_matrix(([2., 1., 1., 2.], ([0, 0, 1, 2], [0, 4115, 0, 0])), shape=(3, 4131))
        ids = ('c'*64, 'b'*64, 'a'*64); scores = dict(zip(ids, (4., 3., 6.)))
        result = audit.audit_scores(theta, x, ids, scores)
        self.assertEqual(result['selected_candidate_id'], 'a'*64)
        theta[:] = 0.; tied = dict.fromkeys(ids, 0.)
        self.assertEqual(audit.audit_scores(theta, x, ids, tied)['selected_candidate_id'], 'a'*64)
        # Numeric closeness cannot rescue a different selected SHA.
        wrong = dict(tied); wrong['c'*64] = 1e-12
        with self.assertRaisesRegex(ValueError, 'selected candidate'): audit.audit_scores(theta, x, ids, wrong)
        for bad_ids, bad_scores in ((ids[::-1], scores), (('a'*64,)*3, tied), (ids, dict(tied, extra=0.)),
                (ids, {**tied, 'a'*64: True})):
            with self.assertRaises(ValueError): audit.audit_scores(theta, x, bad_ids, bad_scores)

    def test_no_io_and_no_implicit_external_runtime_or_array_authenticity_claim(self):
        model, x, y, w = fixture()
        with patch('builtins.open', side_effect=AssertionError('no I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no empirical files')):
            result = audit.audit_model(model, x, y, w, SPEC)
            audit.audit_scores(np.array(model['coefficients']), sparse.csr_matrix(x), ('a'*64, 'b'*64),
                {'a'*64: math.log(3.), 'b'*64: -math.log(3.)})
        for key in ('input_provenance_verified', 'actual_intermediate_execution_verified',
                    'runtime_identity_verified', 'complete_experiment_barriers_verified', 'fitting_authorized'):
            self.assertIs(result[key], False)


if __name__ == '__main__': unittest.main()
