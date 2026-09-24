"""Independent supplied-array joint4131 numerical audit; no I/O, CLI or fit.

No producer solver, feature builder, validation, evaluation or hash function is
imported. Scalar fsum reductions independently check final logistic/ridge loss,
all4131 gradients, curvature metadata and scores. Numeric reassociation uses the
prospectively fixed atol=rtol=1e-10 comparison; saved, declared AND recomputed
gradient-infinity norms must separately be <=1e-8, without an allowance. Score
SHA selection must match exactly, including near ties; there is no tie rescue.

Caller responsibilities: authenticate source/runtime/files and supplied arrays,
independently reconstruct own-training membership/scaler/feature/pair weights,
verify all35 models/320 predictions and label-opening barriers. This module
checks trace schema/arithmetic consistency, not actual intermediate Newton
execution or source provenance. A PASS grants no empirical release.
"""
from dataclasses import fields, is_dataclass
import hashlib
import json
import math
import re

import numpy as np
from scipy import sparse

DIMENSION = 4131
C = .1
MASS = 1900.
KIND = 'fixed_repair_joint_progress_newton_v1'
ATOL = RTOL = 1e-10
GRADIENT_LIMIT = 1e-8
SOLVE_LIMIT = 1e-12
SPEC_FIELDS = {'representation', 'dimension', 'feature_configuration_sha256', 'model_kind'}
MODEL_FIELDS = {'configuration', 'coefficients', 'final_gradient', 'training', 'optimization', 'runtime', 'model_sha256'}


def _require(condition, message):
    if not condition: raise ValueError(message)


def _number(value): return type(value) in (int, float) and math.isfinite(value)
def _sha(value): return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def _fields(value, expected, name):
    _require(type(value) is dict and set(value) == set(expected), 'strict '+name+' fields required')


def _exact(actual, expected, name):
    _require(type(actual) is type(expected), name+' type differs')
    if type(expected) is dict:
        _require(set(actual) == set(expected), name+' keys differ')
        for key in expected: _exact(actual[key], expected[key], name+'.'+key)
    elif type(expected) in (list, tuple):
        _require(len(actual) == len(expected), name+' length differs')
        for a, b in zip(actual, expected, strict=True): _exact(a, b, name+' item')
    else: _require(actual == expected, name+' differs')


def _close(actual, expected, name, *, atol=ATOL, rtol=RTOL):
    _require(_number(actual) and _number(expected)
        and math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol), name+' numerical mismatch')


def _spec(value):
    if is_dataclass(value) and not isinstance(value, type):
        _require({f.name for f in fields(value)} == SPEC_FIELDS, 'exact external specification fields required')
        value = {name: getattr(value, name) for name in SPEC_FIELDS}
    _fields(value, SPEC_FIELDS, 'external specification')
    _require(type(value['dimension']) is int and value['dimension'] == DIMENSION
        and value['model_kind'] == KIND and type(value['model_kind']) is str
        and type(value['representation']) is str and bool(value['representation'])
        and _sha(value['feature_configuration_sha256']), 'exact externally expected native4131 specification required')
    return dict(value)


def expected_configuration(expected_spec):
    """Independent literal contract, not an import of the producer config."""
    spec = _spec(expected_spec)
    return dict(kind=KIND, dimension=4131, representation=spec, C=.1,
        mirrored_row_mass=1900., mass_rtol=1e-12, mass_atol=1e-12,
        intercept=0., offset='internally_fixed_literal_zero', labels='integer_0_1_signed_as_2y_minus_1',
        row_contract='adjacent_exact_feature_label_mirrors_equal_positive_weights',
        matrix_arithmetic='canonical_float64_CSR',
        csr_canonicalization='copy_validate_coalesce_duplicates_eliminate_zeros_sort_indices_validate',
        regularization='half_squared_L2_all_4131_coefficients', initialization='all_zero',
        optimizer='analytic_damped_newton_cholesky_v1',
        hessian='I_plus_C_XT_diag_w_sigmoid_z_sigmoid_minus_z_X',
        hessian_symmetrization='0.5_times_H_plus_0.5_times_H_transpose',
        linear_solver='Cholesky_lower_then_two_triangular_solves_no_inverse',
        damping='min_1_log1p_r_times_a_div_q_div_r_else_min_1_a_div_q',
        max_updates=2000, max_loop_evaluations=2001, max_hessian_evaluations=2000,
        max_linear_solves=2000, max_final_checks=1, max_total_evaluations=2002,
        loop_gradient_infinity_limit=1e-8, final_gradient_infinity_limit=1e-8,
        normalized_solve_residual_limit=1e-12, objective_end_check_relative_allowance=1e-12,
        line_search=False, jitter=False, iterative_refinement=False, retries=0,
        base_margin_optimized=False, supplied_offset_permitted=False,
        primitive_source_files=['scripts/zpd_repair_residual_core.py', 'scripts/zpd_repair_feedback_offset.py'])


def _matrix(value):
    if type(value) is np.ndarray:
        _require(value.dtype == np.dtype('float64') and value.ndim == 2
            and np.isfinite(value).all(), 'finite float64 dense matrix required')
        matrix = sparse.csr_matrix(value, copy=True)
    elif sparse.isspmatrix_csr(value):
        _require(value.dtype == np.dtype('float64') and np.isfinite(value.data).all()
            and value.indices.dtype.kind in 'iu' and value.indptr.dtype.kind in 'iu', 'finite float64 CSR required')
        matrix = value.copy()
    else: raise ValueError('dense float64 or CSR required')
    matrix.check_format(full_check=True)
    _require(matrix.shape[1] == DIMENSION and matrix.shape[0] > 0, 'nonempty exact4131 matrix required')
    matrix.has_sorted_indices = False; matrix.has_canonical_format = False
    with np.errstate(over='ignore', invalid='ignore'): matrix.sum_duplicates()
    matrix.eliminate_zeros(); matrix.sort_indices(); matrix.check_format(full_check=True)
    _require(np.isfinite(matrix.data).all() and matrix.has_canonical_format, 'finite canonicalized CSR required')
    for lo, hi in zip(matrix.indptr, matrix.indptr[1:]):
        _require(not np.any(np.diff(matrix.indices[lo:hi]) <= 0), 'unique increasing CSR coordinates required')
    return matrix


def _array(value, size, name):
    _require(type(value) is np.ndarray and value.dtype == np.dtype('float64')
        and value.shape == (size,) and np.isfinite(value).all(), 'finite float64 '+name+' required')
    return value.copy()


def _serialized_vector(value, name):
    _require(type(value) is list and len(value) == DIMENSION and all(_number(v) for v in value),
        'finite strict4131 '+name+' list required')
    return np.asarray(value, dtype=np.float64)


def _arrays(X, y, weights):
    matrix = _matrix(X); n = matrix.shape[0]
    _require(n % 2 == 0 and type(y) is np.ndarray and y.dtype.kind in 'iu'
        and y.shape == (n,) and np.isin(y, [0, 1]).all(), 'integer binary even mirrored targets required')
    target = y.astype(np.int64, copy=True); weight = _array(weights, n, 'weights')
    _require((weight > 0).all() and math.isclose(math.fsum(map(float, weight)), MASS, rel_tol=1e-12, abs_tol=1e-12),
        'positive mirrored weight mass1900 required')
    _require(np.array_equal(target[1::2], 1-target[::2]) and np.array_equal(weight[::2], weight[1::2]),
        'exact adjacent target and weight mirrors required')
    for i in range(0, n, 2):
        a, b, c = matrix.indptr[i:i+3]
        _require(np.array_equal(matrix.indices[a:b], matrix.indices[b:c])
            and np.array_equal(matrix.data[a:b], -matrix.data[b:c]), 'exact adjacent feature mirrors required')
    return matrix, target, weight


def _hash_arrays(*arrays):
    digest = hashlib.sha256()
    for value in arrays:
        value = np.ascontiguousarray(value)
        header = json.dumps({'shape': list(value.shape), 'dtype': value.dtype.str}, sort_keys=True, separators=(',', ':')).encode()
        for block in (header, value.tobytes(order='C')):
            digest.update(len(block).to_bytes(8, 'little')); digest.update(block)
    return digest.hexdigest()


def _json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _row_score(matrix, row, theta):
    lo, hi = matrix.indptr[row:row+2]
    return math.fsum(float(value)*float(theta[column]) for column, value in
                     zip(matrix.indices[lo:hi], matrix.data[lo:hi], strict=True))


def _recalculate(matrix, target, weight, theta):
    losses = []; terms = [[] for _ in range(DIMENSION)]; squared = []
    for i, (t, w) in enumerate(zip(target, weight, strict=True)):
        lo, hi = matrix.indptr[i:i+2]; values = matrix.data[lo:hi]; columns = matrix.indices[lo:hi]
        signed = 2*int(t)-1; margin = _row_score(matrix, i, theta); z = signed*margin
        _require(math.isfinite(z), 'nonfinite independently recomputed margin')
        exponential = math.exp(-abs(z))
        sigmoid = exponential/(1+exponential) if z >= 0 else 1/(1+exponential)
        losses.append(C*float(w)*(max(0., -z)+math.log1p(exponential)))
        multiplier = -C*float(w)*signed*sigmoid
        for column, value in zip(columns, values, strict=True): terms[int(column)].append(multiplier*float(value))
        squared.append(math.fsum(float(v)*float(v) for v in values))
    gradient = np.array([math.fsum([float(theta[j]), *terms[j]]) for j in range(DIMENSION)], dtype=np.float64)
    penalty = .5*math.fsum(float(v)*float(v) for v in theta); loss = math.fsum(losses)
    mass = math.fsum(map(float, weight)); weighted_squared = math.fsum(float(w)*r for w, r in zip(weight, squared, strict=True))
    result = dict(objective=penalty+loss, weighted_logistic_loss=loss, l2_penalty=penalty,
        gradient_infinity_norm=float(np.max(np.abs(gradient))), gradient_l2_norm=math.hypot(*map(float, gradient)),
        initial_objective=C*mass*math.log(2.), weight_mass=mass, maximum_row_squared_norm=max(squared),
        weighted_row_squared_norm_sum=weighted_squared, hessian_spectral_upper_bound=1.+.25*C*weighted_squared)
    _require(np.isfinite(gradient).all() and all(_number(v) and v >= 0 for v in result.values()),
        'finite independently recomputed loss/gradient/curvature required')
    return result, gradient


def _trace(meta, recomputed, theta, saved_gradient):
    counts = {'updates', 'loop_evaluations', 'hessian_evaluations', 'linear_solves', 'final_checks', 'total_evaluations'}
    numbers = {'initial_objective', 'objective', 'weighted_logistic_loss', 'l2_penalty',
        'loop_gradient_infinity_norm', 'loop_gradient_l2_norm', 'gradient_infinity_norm', 'gradient_l2_norm'}
    _fields(meta, counts | numbers | {'status', 'accepted', 'trace'}, 'native optimization')
    _require(meta['accepted'] is True and type(meta['status']) is str and meta['status'] == 'converged_gradient'
        and all(type(meta[k]) is int and meta[k] >= 0 for k in counts)
        and all(_number(meta[k]) and meta[k] >= 0. for k in numbers), 'accepted finite native certificate required')
    updates = meta['updates']; loops = meta['loop_evaluations']
    _require(0 <= updates <= 2000 and loops == updates+1 and meta['hessian_evaluations'] == updates
        and meta['linear_solves'] == updates and meta['final_checks'] == 1 and meta['total_evaluations'] == loops+1,
        'fixed exact bounded Newton counters required')
    norms = [meta['loop_gradient_infinity_norm'], meta['gradient_infinity_norm'],
        float(np.max(np.abs(saved_gradient))), recomputed['gradient_infinity_norm']]
    _require(max(norms) <= GRADIENT_LIMIT, 'strict stored/declared/recomputed gradient1e-8 limit exceeded')
    _close(meta['gradient_infinity_norm'], float(np.max(np.abs(saved_gradient))), 'stored gradient infinity norm', atol=1e-12, rtol=1e-12)
    _close(meta['gradient_l2_norm'], math.hypot(*map(float, saved_gradient)), 'stored gradient L2 norm', atol=1e-12, rtol=1e-12)
    _close(meta['objective'], meta['weighted_logistic_loss']+meta['l2_penalty'],
        'serialized objective decomposition', atol=1e-12, rtol=1e-12)
    for key in numbers-{'loop_gradient_infinity_norm', 'loop_gradient_l2_norm'}: _close(meta[key], recomputed[key], key)
    _require(meta['objective'] <= meta['initial_objective']+1e-12*max(1., abs(meta['initial_objective'])),
        'frozen final objective end check failed')
    _require(recomputed['objective'] <= recomputed['initial_objective']+1e-12*max(1., abs(recomputed['initial_objective'])),
        'independent final objective end check failed')
    _require(updates != 0 or not np.any(theta), 'zero-update initialization must be literal zero')
    trace = meta['trace']; common = {'iteration', 'objective', 'gradient_infinity_norm', 'gradient_l2_norm'}
    step_fields = {'a', 'q', 'r', 'alpha', 'normalized_solve_residual'}
    _require(type(trace) is list and len(trace) == loops, 'exact native trace length required')
    for i, row in enumerate(trace):
        expected = common | step_fields if i < updates else common
        _fields(row, expected, 'trace row')
        _require(type(row['iteration']) is int and row['iteration'] == i
            and all(_number(row[k]) and row[k] >= 0. for k in expected-{'iteration'}), 'strict ordered finite trace required')
        g, g2 = row['gradient_infinity_norm'], row['gradient_l2_norm']
        _require(g2 >= g and g2 <= math.sqrt(DIMENSION)*g+ATOL, 'trace4131 gradient norms inconsistent')
        if i < updates:
            a, q, r = row['a'], row['q'], row['r']
            _require(g > GRADIENT_LIMIT and a > 0 and q > 0 and 0 < row['alpha'] <= 1
                and row['normalized_solve_residual'] <= SOLVE_LIMIT, 'strict preconvergence/descent/solve trace required')
            ratio = a/q
            _require(math.isfinite(ratio) and ratio > 0 and math.isfinite(r*ratio), 'finite damping ratio/argument required')
            alpha = min(1., math.log1p(r*ratio)/r) if r > 0 else min(1., ratio)
            _require(math.isfinite(alpha) and alpha > 0, 'finite positive damping required')
            _close(row['alpha'], alpha, 'analytic damping', atol=1e-12, rtol=1e-12)
        else: _require(g <= GRADIENT_LIMIT, 'terminal loop gradient exceeds1e-8')
    _require(trace[0]['objective'] == meta['initial_objective']
        and trace[-1]['gradient_infinity_norm'] == meta['loop_gradient_infinity_norm']
        and trace[-1]['gradient_l2_norm'] == meta['loop_gradient_l2_norm'], 'trace/summary exact identities differ')
    _close(trace[-1]['objective'], meta['objective'], 'terminal loop objective', atol=1e-12, rtol=1e-12)


def audit_model(model, X, y, weights, expected_spec):
    """Check supplied certificate/arrays independently; no provenance claim."""
    _fields(model, MODEL_FIELDS, 'native model')
    _exact(model['configuration'], expected_configuration(expected_spec), 'fixed native configuration')
    theta = _serialized_vector(model['coefficients'], 'coefficients')
    saved_gradient = _serialized_vector(model['final_gradient'], 'final gradient')
    _require(_sha(model['model_sha256']) and model['model_sha256'] == _json_hash({k: v for k, v in model.items() if k != 'model_sha256'}),
        'native model checksum mismatch')
    _fields(model['runtime'], {'python', 'numpy', 'scipy'}, 'declared runtime')
    _require(all(type(v) is str and bool(v) for v in model['runtime'].values()), 'declared runtime version strings required')
    matrix, target, weight = _arrays(X, y, weights); n = len(target)
    info = model['training']
    counts = dict(rows=n, unordered_pairs=n//2, positive_rows=int(target.sum()),
        zero_difference_rows=sum(int(a == b) for a, b in zip(matrix.indptr, matrix.indptr[1:])))
    numeric = {'weight_mass', 'maximum_row_squared_norm', 'weighted_row_squared_norm_sum', 'strong_convexity_lower_bound', 'hessian_spectral_upper_bound'}
    _fields(info, set(counts) | numeric | {'input_sha256'}, 'training certificate')
    _require(all(_number(info[key]) and info[key] >= 0. for key in numeric),
        'nonnegative finite native training scalars required')
    for key, value in counts.items(): _exact(info[key], value, 'training.'+key)
    hashes = dict(features=_hash_arrays(np.asarray(matrix.shape, dtype='<i8'), matrix.indptr.astype('<i8'),
        matrix.indices.astype('<i8'), matrix.data.astype('<f8')), labels=_hash_arrays(target.astype('<i8')),
        weights=_hash_arrays(weight.astype('<f8')), base_margin=_hash_arrays(np.zeros(n, dtype='<f8')))
    _exact(info['input_sha256'], hashes, 'independent array SHA')
    recomputed, gradient = _recalculate(matrix, target, weight, theta)
    _require(np.allclose(saved_gradient, gradient, rtol=RTOL, atol=ATOL), 'independent final gradient vector differs')
    for key in numeric-{'strong_convexity_lower_bound'}: _close(info[key], recomputed[key], 'training.'+key)
    _require(math.isclose(info['weight_mass'], MASS, rel_tol=1e-12, abs_tol=1e-12), 'strict serialized mass1900 required')
    _close(info['hessian_spectral_upper_bound'], 1.+.25*C*info['weighted_row_squared_norm_sum'],
        'serialized curvature identity', atol=1e-12, rtol=1e-12)
    _require(_number(info['strong_convexity_lower_bound']) and info['strong_convexity_lower_bound'] == 1., 'all-coordinate unit ridge required')
    _trace(model['optimization'], recomputed, theta, saved_gradient)
    result = dict(verified=True, dimension=DIMENSION, rows=n, input_sha256=hashes, model_sha256=model['model_sha256'],
        recomputed=recomputed, maximum_gradient_recompute_difference=float(np.max(np.abs(saved_gradient-gradient))),
        tolerances=dict(atol=ATOL, rtol=RTOL, strict_gradient_limit=GRADIENT_LIMIT, strict_solve_trace_limit=SOLVE_LIMIT),
        input_provenance_verified=False, actual_intermediate_execution_verified=False,
        runtime_identity_verified=False, complete_experiment_barriers_verified=False, fitting_authorized=False)
    json.dumps(result, allow_nan=False)
    return result


def audit_scores(theta, candidateCSR, candidate_ids, reported_scores):
    """Independent scalar candidate scores and exact SHA-tie selection.

    Coefficients must first pass audit_model. This function has no label input
    and does not validate candidate source ancestry or bank coverage outside the
    exact supplied ordered IDs. Near-tie selection discrepancies fail closed.
    """
    theta = _array(theta, DIMENSION, 'audited coefficients')
    _require(sparse.isspmatrix_csr(candidateCSR), 'candidate CSR required')
    matrix = _matrix(candidateCSR)
    _require(type(candidate_ids) is tuple and len(candidate_ids) == matrix.shape[0]
        and len(set(candidate_ids)) == len(candidate_ids) and all(_sha(cid) for cid in candidate_ids),
        'exact ordered unique candidate SHA tuple required')
    _fields(reported_scores, candidate_ids, 'reported candidate scores')
    expected = {}
    for i, cid in enumerate(candidate_ids):
        score = _row_score(matrix, i, theta)
        _require(math.isfinite(score), 'finite independent candidate score required')
        _close(reported_scores[cid], score, 'candidate score '+cid)
        expected[cid] = score
    choice = min(candidate_ids, key=lambda cid: (-expected[cid], cid))
    reported_choice = min(candidate_ids, key=lambda cid: (-reported_scores[cid], cid))
    _require(choice == reported_choice, 'exact independently selected candidate SHA differs; no tie allowance')
    return dict(verified=True, candidate_count=len(candidate_ids), selected_candidate_id=choice,
        recomputed_scores=expected, maximum_score_recompute_difference=max(abs(expected[cid]-reported_scores[cid]) for cid in candidate_ids),
        selected_identity_exact=True, coefficient_authentication_required=True,
        candidate_source_provenance_verified=False, fitting_authorized=False)
