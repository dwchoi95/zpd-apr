"""Pure native4131 joint logistic Newton; supplied arrays only, no I/O or CLI.

No learned offset or base coefficient may be supplied. All4131 coefficients
receive ridge. Source provenance and independent numerical replay are external;
convergence is not a guarantee of ranking, repair or educational benefit.
"""
from __future__ import annotations

from dataclasses import asdict
import math
import platform
import re

import numpy as np
import scipy
from scipy import sparse
from scipy.linalg import cholesky, solve_triangular
from scipy.special import expit

from scripts import zpd_repair_residual_core as core

ResidualSpec = core.ResidualSpec
JointOptimizationError = core.OffsetOptimizationError
OffsetOptimizationError = JointOptimizationError
_model_hash = core._model_hash
_sha_arrays = core._sha_arrays

KIND = 'fixed_repair_joint_progress_newton_v1'
OPTIMIZER = 'analytic_damped_newton_cholesky_v1'
DIMENSION = 4131
C = .1
MASS = 1900.
MAX_UPDATES = 2000
GRADIENT_LIMIT = 1e-8
SOLVE_RESIDUAL_LIMIT = 1e-12



# These immutable dimension-free primitives must be hash-bound by any future
# release. A wrapper must additionally bind their complete transitive imports;
# this tuple is a primitive inventory, not a claim of complete runner closure.
PRIMITIVE_SOURCE_FILES = ('scripts/zpd_repair_residual_core.py',
                          'scripts/zpd_repair_feedback_offset.py')
SOURCE_FILES = ('scripts/zpd_joint_progress_newton.py', *PRIMITIVE_SOURCE_FILES)


def _canonical_matrix(value):
    """Accept dense/CSR only; never mutate input or discard a supplied row."""
    if type(value) is np.ndarray:
        if value.dtype != np.dtype('float64') or value.ndim != 2 or not np.isfinite(value).all():
            raise ValueError('finite two-dimensional float64 dense matrix required')
        matrix = sparse.csr_matrix(value, copy=True)
    elif sparse.isspmatrix_csr(value):
        if (value.dtype != np.dtype('float64') or not np.isfinite(value.data).all()
                or value.indices.dtype.kind not in 'iu' or value.indptr.dtype.kind not in 'iu'):
            raise ValueError('finite float64 CSR and integer index arrays required')
        matrix = value.copy()
    else:
        raise ValueError('float64 ndarray or CSR matrix required')
    matrix.check_format(full_check=True)
    if matrix.shape[1] != DIMENSION or matrix.shape[0] == 0:
        raise ValueError('nonempty exact4131 matrix required')
    # Do not trust mutable SciPy cached-format flags supplied by a caller.
    matrix.has_sorted_indices = False
    matrix.has_canonical_format = False
    with np.errstate(over='ignore', invalid='ignore'):
        matrix.sum_duplicates()
    matrix.eliminate_zeros()
    matrix.sort_indices()
    matrix.check_format(full_check=True)
    if not np.isfinite(matrix.data).all() or not matrix.has_canonical_format:
        raise ValueError('finite canonical CSR required after duplicate coalescing')
    return matrix


def _prepare(x, labels, weights, spec):
    _spec(spec)
    matrix = _canonical_matrix(x)
    base = np.zeros(matrix.shape[0], dtype=np.float64)
    return core._prepare(matrix, labels, weights, base, spec)


def objective_and_gradient(theta, x, labels, weights, *, spec):
    """Evaluate the exact joint objective with a private literal-zero offset."""
    matrix, target, weight, base = _prepare(x, labels, weights, spec)
    theta = core.arithmetic._float_vector(theta, DIMENSION, 'theta')
    value, gradient, _, _, _, _ = _checked_evaluate(theta, matrix, 2.*target-1., weight, base)
    return value, gradient


def _spec(spec):
    core._spec(spec)
    if spec.dimension != DIMENSION or spec.model_kind != KIND:
        raise ValueError('externally expected joint4131 native Newton v1 spec required')
    return spec


def configuration(spec):
    _spec(spec)
    return dict(kind=KIND, dimension=DIMENSION, representation=asdict(spec), C=C,
        mirrored_row_mass=MASS, mass_rtol=1e-12, mass_atol=1e-12,
        intercept=0., offset='internally_fixed_literal_zero',
        labels='integer_0_1_signed_as_2y_minus_1',
        row_contract='adjacent_exact_feature_label_mirrors_equal_positive_weights',
        matrix_arithmetic='canonical_float64_CSR',
        csr_canonicalization='copy_validate_coalesce_duplicates_eliminate_zeros_sort_indices_validate',
        regularization='half_squared_L2_all_4131_coefficients',
        initialization='all_zero', optimizer=OPTIMIZER,
        hessian='I_plus_C_XT_diag_w_sigmoid_z_sigmoid_minus_z_X',
        hessian_symmetrization='0.5_times_H_plus_0.5_times_H_transpose',
        linear_solver='Cholesky_lower_then_two_triangular_solves_no_inverse',
        damping='min_1_log1p_r_times_a_div_q_div_r_else_min_1_a_div_q',
        max_updates=MAX_UPDATES, max_loop_evaluations=MAX_UPDATES+1,
        max_hessian_evaluations=MAX_UPDATES, max_linear_solves=MAX_UPDATES,
        max_final_checks=1, max_total_evaluations=MAX_UPDATES+2,
        loop_gradient_infinity_limit=GRADIENT_LIMIT, final_gradient_infinity_limit=GRADIENT_LIMIT,
        normalized_solve_residual_limit=SOLVE_RESIDUAL_LIMIT,
        objective_end_check_relative_allowance=1e-12,
        line_search=False, jitter=False, iterative_refinement=False, retries=0,
        base_margin_optimized=False, supplied_offset_permitted=False,
        primitive_source_files=list(PRIMITIVE_SOURCE_FILES))


def _evaluate(theta, x, signed, weights, base):
    # Separate calls are intentional: final acceptance cannot reuse cached g.
    return core.arithmetic._evaluate(theta, x, signed, weights, base)


def _checked_evaluate(theta, x, signed, weights, base):
    """Check the helper boundary before retaining any trace/JSON diagnostics."""
    value, gradient, data, penalty = _evaluate(theta, x, signed, weights, base)
    if any(type(v) not in (int, float, np.float64) or not math.isfinite(v) or v < 0. for v in (value, data, penalty)):
        raise FloatingPointError('finite nonnegative objective/loss/penalty required')
    if (type(gradient) is not np.ndarray or gradient.dtype != np.dtype('float64')
            or gradient.shape != (DIMENSION,) or not np.isfinite(gradient).all()):
        raise FloatingPointError('finite exact float64(4131,) gradient required')
    norm = float(np.max(np.abs(gradient))); norm2 = math.hypot(*map(float, gradient))
    if not math.isfinite(norm) or not math.isfinite(norm2):
        raise FloatingPointError('finite gradient norms required')
    return float(value), gradient, float(data), float(penalty), norm, norm2


def _hessian(theta, x, signed, weights, base):
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        z = signed*(np.asarray(x@theta).ravel()+base)
        curvature = C*weights*expit(z)*expit(-z)
        hessian = np.eye(DIMENSION, dtype=np.float64)+(x.T@x.multiply(curvature[:, None])).toarray()
    if not np.isfinite(z).all() or not np.isfinite(curvature).all() or not np.isfinite(hessian).all():
        raise FloatingPointError('nonfinite analytic Hessian assembly')
    hessian = .5*hessian+.5*hessian.T
    if not np.isfinite(hessian).all() or not np.array_equal(hessian, hessian.T):
        raise FloatingPointError('finite exactly symmetric Hessian required')
    return hessian


def _direction(hessian, gradient):
    """One linear solve means one Cholesky plus exactly two triangular solves."""
    if (type(hessian) is not np.ndarray or hessian.dtype != np.dtype('float64')
            or hessian.shape != (DIMENSION, DIMENSION) or not np.isfinite(hessian).all()
            or not np.array_equal(hessian, hessian.T)):
        raise ValueError('finite symmetric4131 Hessian required')
    if (type(gradient) is not np.ndarray or gradient.dtype != np.dtype('float64')
            or gradient.shape != (DIMENSION,) or not np.isfinite(gradient).all()):
        raise ValueError('finite exact float64(4131,) solve gradient required')
    factor = cholesky(hessian, lower=True, check_finite=True, overwrite_a=False)
    if (type(factor) is not np.ndarray or factor.dtype != np.dtype('float64')
            or factor.shape != (DIMENSION, DIMENSION) or not np.isfinite(factor).all()):
        raise FloatingPointError('finite exact float64(4131,4131) Cholesky factor required')
    intermediate = solve_triangular(factor, -gradient, lower=True, check_finite=True, overwrite_b=False)
    if (type(intermediate) is not np.ndarray or intermediate.dtype != np.dtype('float64')
            or intermediate.shape != (DIMENSION,) or not np.isfinite(intermediate).all()):
        raise FloatingPointError('finite exact float64(4131,) intermediate required')
    direction = solve_triangular(factor.T, intermediate, lower=False, check_finite=True, overwrite_b=False)
    if (type(direction) is not np.ndarray or direction.dtype != np.dtype('float64')
            or direction.shape != (DIMENSION,) or not np.isfinite(direction).all()):
        raise FloatingPointError('finite exact float64(4131,) Cholesky direction required')
    return direction


def _step_quantities(x, hessian, gradient, direction):
    with np.errstate(over='ignore', invalid='ignore', under='ignore'):
        hp = hessian@direction
        a = float(-gradient@direction); q = float(direction@hp)
        denominator = float(np.linalg.norm(hessian, ord=np.inf))*float(np.max(np.abs(direction)))+float(np.max(np.abs(gradient)))
        residual = float(np.max(np.abs(hp+gradient)))
        xp = np.asarray(x@direction).ravel()
    if (not np.isfinite(hp).all() or not np.isfinite(xp).all()
            or not all(math.isfinite(v) for v in (a, q, denominator, residual))
            or a <= 0. or q <= 0. or denominator <= 0.):
        raise FloatingPointError('finite positive descent/curvature/solve denominator required')
    normalized = residual/denominator
    if not math.isfinite(normalized) or normalized > SOLVE_RESIDUAL_LIMIT:
        raise FloatingPointError('normalized linear solve residual exceeds fixed1e-12')
    r = float(np.max(np.abs(xp)))
    alpha = _alpha(a, q, r)
    return dict(a=a, q=q, r=r, alpha=alpha, normalized_solve_residual=normalized)


def _alpha(a, q, r):
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (a, q, r)) or a <= 0 or q <= 0 or r < 0:
        raise ValueError('finite positive a/q and nonnegative r required')
    ratio = a/q
    if not math.isfinite(ratio) or ratio <= 0.: raise FloatingPointError('finite positive damping ratio required')
    if r > 0.:
        argument = r*ratio
        if not math.isfinite(argument): raise FloatingPointError('finite log1p damping argument required')
        uncapped = math.log1p(argument)/r
    else: uncapped = ratio
    alpha = min(1., uncapped)
    if not math.isfinite(uncapped) or not math.isfinite(alpha) or not 0. < alpha <= 1.:
        raise FloatingPointError('finite analytic damping alpha in(0,1] required')
    return alpha


def _updated(theta, direction, alpha):
    with np.errstate(over='ignore', invalid='ignore'): updated = theta+alpha*direction
    if not np.isfinite(updated).all(): raise FloatingPointError('nonfinite Newton iterate')
    if np.array_equal(updated, theta): raise FloatingPointError('unchanged Newton iterate before gradient convergence')
    return updated


def fit_joint(x, labels, weights, *, spec):
    """One zero-initialized solve, no offset/configuration/retry argument."""
    matrix, y, weight, base = _prepare(x, labels, weights, spec)
    theta = np.zeros(DIMENSION, dtype=np.float64); signed = 2.*y-1.
    trace = []; initial = None
    counts = dict(updates=0, loop_evaluations=0, hessian_evaluations=0, linear_solves=0, final_checks=0, total_evaluations=0)
    status = 'training_metadata_failed'
    try:
        training = core.arithmetic._training_metadata(matrix, y, weight, base)
        for iteration in range(MAX_UPDATES+1):
            status = 'loop_evaluation_failed'; counts['loop_evaluations'] += 1; counts['total_evaluations'] += 1
            value, gradient, data, penalty, norm, norm2 = _checked_evaluate(theta, matrix, signed, weight, base)
            if initial is None: initial = value
            row = dict(iteration=iteration, objective=value, gradient_infinity_norm=norm, gradient_l2_norm=norm2)
            trace.append(row)
            if norm <= GRADIENT_LIMIT:
                status = 'final_check_failed'; counts['final_checks'] += 1; counts['total_evaluations'] += 1
                final_value, final_gradient, final_data, final_penalty, final_norm, final_norm2 = _checked_evaluate(theta, matrix, signed, weight, base)
                if final_norm > GRADIENT_LIMIT: raise FloatingPointError('fresh final gradient exceeds fixed1e-8')
                if final_value > initial+1e-12*max(1., abs(initial)):
                    raise FloatingPointError('final objective exceeds frozen zero-initialized end check')
                optimization = dict(status='converged_gradient', accepted=True, **counts,
                    initial_objective=initial, objective=final_value, weighted_logistic_loss=final_data,
                    l2_penalty=final_penalty, loop_gradient_infinity_norm=norm, loop_gradient_l2_norm=norm2,
                    gradient_infinity_norm=final_norm, gradient_l2_norm=final_norm2, trace=trace)
                model = dict(configuration=configuration(spec), coefficients=theta.tolist(), final_gradient=final_gradient.tolist(),
                    training=training, optimization=optimization,
                    runtime=dict(numpy=np.__version__, scipy=scipy.__version__, python=platform.python_version()))
                model['model_sha256'] = _model_hash(model)
                status = 'certificate_validation_failed'; validate_model(model, expected_spec=spec)
                return model
            if iteration == MAX_UPDATES:
                status = 'update_budget_exhausted'; raise FloatingPointError('maximum2000 Newton updates without gradient convergence')
            status = 'hessian_failed'; counts['hessian_evaluations'] += 1
            hessian = _hessian(theta, matrix, signed, weight, base)
            status = 'linear_solve_failed'; counts['linear_solves'] += 1
            direction = _direction(hessian, gradient)
            status = 'descent_or_solve_residual_failed'
            step = _step_quantities(matrix, hessian, gradient, direction)
            status = 'iterate_update_failed'
            updated = _updated(theta, direction, step['alpha'])
            row.update(step); theta = updated; counts['updates'] += 1
    except Exception as error:
        # Only previously verified finite iterates/scalars enter JSON. Failed
        # transient Hessians/directions/nonfinite candidates are never serialized.
        raise JointOptimizationError('fixed joint analytic Newton failed; no retry', dict(status=status, accepted=False,
            **counts, initial_objective=initial, final_theta=theta.tolist(), trace=trace,
            error_type=type(error).__name__, reason=str(error))) from error
    raise AssertionError('unreachable fixed Newton loop')


def _number(value, *, nonnegative=False): return core.arithmetic._number(value, nonnegative=nonnegative)


def _close(a, b): return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def validate_model(model, *, expected_spec):
    """Strict native certificate, not proof that claimed input hashes are real.

    Independent execution/source provenance and objective/gradient replay remain
    mandatory. The strict g_inf<=1e-8 boundary and strong convexity are numerical
    properties of the supplied objective; neither establishes ranking or repair.
    """
    spec = _spec(expected_spec)
    if (type(model) is not dict or set(model) != {'configuration', 'coefficients', 'final_gradient', 'training', 'optimization', 'runtime', 'model_sha256'}
            or not core.arithmetic._fixed(model['configuration'], configuration(spec))):
        raise ValueError('strict native Newton model configuration/schema required')
    for name in ('coefficients', 'final_gradient'):
        if type(model[name]) is not list or len(model[name]) != DIMENSION or any(not _number(v) for v in model[name]):
            raise ValueError('finite exact4131 model vectors required')
    theta = np.asarray(model['coefficients'], dtype=np.float64); gradient = np.asarray(model['final_gradient'], dtype=np.float64)
    meta = model['optimization']
    count_keys = {'updates', 'loop_evaluations', 'hessian_evaluations', 'linear_solves', 'final_checks', 'total_evaluations'}
    numbers = {'initial_objective', 'objective', 'weighted_logistic_loss', 'l2_penalty', 'loop_gradient_infinity_norm',
               'loop_gradient_l2_norm', 'gradient_infinity_norm', 'gradient_l2_norm'}
    if (type(meta) is not dict or set(meta) != count_keys | numbers | {'status', 'accepted', 'trace'}
            or type(meta['status']) is not str or meta['status'] != 'converged_gradient' or meta['accepted'] is not True
            or any(type(meta[k]) is not int or meta[k] < 0 for k in count_keys)
            or any(not _number(meta[k], nonnegative=True) for k in numbers)):
        raise ValueError('strict accepted native Newton status/count schema required')
    updates = meta['updates']; loop = meta['loop_evaluations']
    if (not 0 <= updates <= MAX_UPDATES or loop != updates+1 or meta['hessian_evaluations'] != updates
            or meta['linear_solves'] != updates or meta['final_checks'] != 1 or meta['total_evaluations'] != loop+1):
        raise ValueError('exact bounded Newton evaluation/update/solve accounting required')
    actual = dict(l2_penalty=float((.5*theta)@theta), gradient_infinity_norm=float(np.max(np.abs(gradient))),
                  gradient_l2_norm=math.hypot(*map(float, gradient)))
    if (any(not _close(meta[k], v) for k, v in actual.items())
            or max(meta['loop_gradient_infinity_norm'], meta['gradient_infinity_norm'], actual['gradient_infinity_norm']) > GRADIENT_LIMIT
            or not _close(meta['objective'], meta['weighted_logistic_loss']+meta['l2_penalty'])
            or meta['objective'] > meta['initial_objective']+1e-12*max(1., abs(meta['initial_objective']))
            or updates == 0 and np.any(theta)):
        raise ValueError('inconsistent or above1e-8 final gradient/objective certificate')
    trace = meta['trace']; common = {'iteration', 'objective', 'gradient_infinity_norm', 'gradient_l2_norm'}
    step_fields = {'a', 'q', 'r', 'alpha', 'normalized_solve_residual'}
    if type(trace) is not list or len(trace) != loop: raise ValueError('exact visited-iterate trace length required')
    for i, row in enumerate(trace):
        expected = common | step_fields if i < updates else common
        if (type(row) is not dict or set(row) != expected or type(row['iteration']) is not int or row['iteration'] != i
                or any(not _number(row[k], nonnegative=True) for k in expected-{'iteration'})
                or row['gradient_l2_norm'] < row['gradient_infinity_norm']):
            raise ValueError('strict finite ordered native Newton trace required')
        if i < updates:
            if (row['gradient_infinity_norm'] <= GRADIENT_LIMIT or row['a'] <= 0. or row['q'] <= 0.
                    or not 0. < row['alpha'] <= 1. or row['normalized_solve_residual'] > SOLVE_RESIDUAL_LIMIT
                    or not _close(row['alpha'], _alpha(row['a'], row['q'], row['r']))):
                raise ValueError('invalid analytic damping/descent/solve trace')
        elif row['gradient_infinity_norm'] > GRADIENT_LIMIT:
            raise ValueError('terminal loop gradient exceeds strict1e-8')
    if (trace[0]['objective'] != meta['initial_objective'] or not _close(trace[-1]['objective'], meta['objective'])
            or trace[-1]['gradient_infinity_norm'] != meta['loop_gradient_infinity_norm']
            or trace[-1]['gradient_l2_norm'] != meta['loop_gradient_l2_norm']):
        raise ValueError('initial/terminal trace and optimization summary disagree')
    info = model['training']; train_keys = {'rows', 'unordered_pairs', 'positive_rows', 'zero_difference_rows', 'weight_mass',
        'maximum_row_squared_norm', 'weighted_row_squared_norm_sum', 'strong_convexity_lower_bound', 'hessian_spectral_upper_bound', 'input_sha256'}
    if (type(info) is not dict or set(info) != train_keys
            or any(type(info[k]) is not int for k in ('rows', 'unordered_pairs', 'positive_rows', 'zero_difference_rows'))
            or info['rows'] <= 0 or info['rows'] % 2 or info['unordered_pairs'] != info['rows']//2
            or info['positive_rows'] != info['rows']//2 or not 0 <= info['zero_difference_rows'] <= info['rows']
            or info['zero_difference_rows'] % 2):
        raise ValueError('strict unchanged mirrored training counts required')
    if (any(not _number(info[k], nonnegative=True) for k in ('weight_mass', 'maximum_row_squared_norm', 'weighted_row_squared_norm_sum',
                'strong_convexity_lower_bound', 'hessian_spectral_upper_bound'))
            or not math.isclose(info['weight_mass'], MASS, rel_tol=1e-12, abs_tol=1e-12)
            or info['strong_convexity_lower_bound'] != 1.
            or not _close(info['hessian_spectral_upper_bound'], 1.+.25*C*info['weighted_row_squared_norm_sum'])):
        raise ValueError('invalid unchanged mass/curvature certificate')
    hashes = info['input_sha256']
    if (type(hashes) is not dict or set(hashes) != {'features', 'labels', 'weights', 'base_margin'}
            or any(type(v) is not str or re.fullmatch('[0-9a-f]{64}', v) is None for v in hashes.values())):
        raise ValueError('exact unchanged array SHA256 inventory required')
    if hashes['base_margin'] != _sha_arrays(np.zeros(info['rows'], dtype='<f8')):
        raise ValueError('private literal-zero base margin checksum required')
    runtime = model['runtime']
    if type(runtime) is not dict or set(runtime) != {'numpy', 'scipy', 'python'} or any(type(v) is not str or not v for v in runtime.values()):
        raise ValueError('exact numerical runtime required')
    if model['model_sha256'] != _model_hash({k: v for k, v in model.items() if k != 'model_sha256'}):
        raise ValueError('native Newton model checksum mismatch')
    return theta
