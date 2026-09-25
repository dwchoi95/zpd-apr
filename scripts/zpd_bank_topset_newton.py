"""Pure native4131 Newton for the fixed bank top-set objective; no I/O/CLI.

Raw Banks remain the input identity. All numerical products use their common
first-row-centered design. A small score covariance per bank is assembled in
one sparse block diagonal matrix, then one X.T @ S @ X forms the native dense
Hessian. No learned offset, pair logistic Hessian, line search or fallback.

The directional bound is max range({0} U {x_n.p-x_t.p}), not max absolute
direction. Each log-sum-exp's third central moment is bounded by its slope
range times its variance; nonnegative summation and unit ridge preserve this
bound. The fixed analytic damping follows from that bound. Convergence does
not establish top-one accuracy, repair improvement or source authenticity.
"""
from __future__ import annotations

import math
import platform
import re

import numpy as np
import scipy
from scipy import sparse

from scripts import zpd_bank_topset_objective as objective
from scripts import zpd_joint_progress_newton as primitives

KIND = 'fixed_repair_bank_topset_newton_v1'
DIMENSION = 4131
C = .1
MASS = 1900.
MAX_UPDATES = 2000
GRADIENT_LIMIT = 1e-8
SOLVE_RESIDUAL_LIMIT = 1e-12
OptimizationError = primitives.JointOptimizationError
_direction = primitives._direction
_alpha = primitives._alpha
_updated = primitives._updated
_model_hash = primitives._model_hash
_sha_arrays = primitives._sha_arrays
PRIMITIVE_SOURCE_FILES = ('scripts/zpd_bank_topset_objective.py',
    'scripts/zpd_joint_progress_newton.py', *primitives.PRIMITIVE_SOURCE_FILES)
SOURCE_FILES = ('scripts/zpd_bank_topset_newton.py', *PRIMITIVE_SOURCE_FILES)


def configuration():
    return dict(kind=KIND, dimension=DIMENSION, C=C, bank_weight_mass=MASS,
        mass_rtol=1e-12, mass_atol=1e-12, objective=objective.configuration(),
        offset='absent', intercept='not_added', initialization='all_zero',
        regularization='half_squared_L2_all_4131_coefficients',
        design='first_row_centered_per_bank_raw_inputs_preserved',
        hessian='I_plus_XT_blockdiag_CW_score_covariances_X',
        hessian_symmetrization='0.5_times_H_plus_0.5_times_H_transpose',
        linear_solver='Cholesky_lower_then_two_triangular_solves_no_inverse',
        damping='min_1_log1p_r_times_a_div_q_div_r_else_min_1_a_div_q',
        r='max_positive_weight_nonempty_rest_top_slope_range_including_zero',
        max_updates=MAX_UPDATES, max_loop_evaluations=MAX_UPDATES+1,
        max_hessian_evaluations=MAX_UPDATES, max_linear_solves=MAX_UPDATES,
        max_final_checks=1, max_total_evaluations=MAX_UPDATES+2,
        loop_gradient_infinity_limit=GRADIENT_LIMIT, final_gradient_infinity_limit=GRADIENT_LIMIT,
        normalized_solve_residual_limit=SOLVE_RESIDUAL_LIMIT,
        objective_end_check_relative_allowance=1e-12,
        line_search=False, jitter=False, iterative_refinement=False, retries=0,
        primitive_source_files=list(PRIMITIVE_SOURCE_FILES))


def _validate_inputs(banks, weights):
    objective._coefficient_inputs(np.zeros(DIMENSION), banks, weights)


def input_hash(banks, weights):
    """Exact raw bank rows/top-index order/weights, not a provenance proof."""
    _validate_inputs(banks, weights)
    return dict(features=_sha_arrays(*(b.features.astype('<f8') for b in banks)),
        top_indices=_sha_arrays(*(np.asarray(b.top_indices, dtype='<i8') for b in banks)),
        weights=_sha_arrays(weights.astype('<f8')))


def _training(banks, weights):
    return dict(banks=len(banks), rows=sum(len(b.features) for b in banks),
        top_rows=sum(len(b.top_indices) for b in banks),
        rest_rows=sum(len(b.features)-len(b.top_indices) for b in banks),
        positive_weight_banks=int(np.count_nonzero(weights)),
        zero_weight_banks=int(np.count_nonzero(weights == 0.)),
        empty_rest_banks=sum(len(b.features) == len(b.top_indices) for b in banks),
        weight_mass=math.fsum(map(float, weights)), strong_convexity_lower_bound=1.)


def _design(banks):
    x = sparse.vstack([sparse.csr_matrix(objective.centered_features(b)) for b in banks], format='csr')
    x.sum_duplicates(); x.eliminate_zeros(); x.sort_indices(); x.check_format(full_check=True)
    if x.dtype != np.float64 or not np.isfinite(x.data).all() or not x.has_canonical_format:
        raise FloatingPointError('finite canonical centered CSR required')
    return x


def score_hessian(scores, top_indices):
    """Small-bank analytic covariance; independent of the4131 layout."""
    top, rest, q, active, _, curvature = objective._terms(scores, top_indices)
    result = np.zeros((len(scores), len(scores)), dtype=np.float64)
    if not len(rest): return result
    mean_active = math.fsum(map(float, active))/len(top)
    mean_curvature = math.fsum(map(float, curvature))/len(top)
    outer = np.outer(q, q)
    covariance = -outer
    # Do not compute q*(1-q): retain small covariance when q rounds to1.
    for i in range(len(q)):
        covariance[i, i] = q[i]*math.fsum(float(q[j]) for j in range(len(q)) if j != i)
    result[np.ix_(rest, rest)] = mean_active*covariance+mean_curvature*outer
    cross = -q[:, None]*(curvature[None, :]/len(top))
    result[np.ix_(rest, top)] = cross
    result[np.ix_(top, rest)] = cross.T
    result[top, top] = curvature/len(top)
    if not np.isfinite(result).all(): raise FloatingPointError('finite score Hessian required')
    return .5*result+.5*result.T


def _hessian(theta, banks, weights, x):
    scores = np.asarray(x@theta).ravel()
    if not np.isfinite(scores).all(): raise FloatingPointError('nonfinite centered scores')
    blocks=[]; offset=0
    for bank, weight in zip(banks, weights, strict=True):
        n=len(bank.features)
        block=score_hessian(scores[offset:offset+n], bank.top_indices)
        with np.errstate(over='ignore', invalid='ignore'):
            block=(C*weight)*block
        if not np.isfinite(block).all(): raise FloatingPointError('nonfinite weighted score Hessian')
        blocks.append(sparse.csr_matrix(block)); offset+=n
    s=sparse.block_diag(blocks, format='csr')
    with np.errstate(over='ignore', invalid='ignore'):
        hessian=np.eye(DIMENSION, dtype=np.float64)+(x.T@s@x).toarray()
        hessian=.5*hessian+.5*hessian.T
    if not np.isfinite(hessian).all() or not np.array_equal(hessian,hessian.T):
        raise FloatingPointError('finite symmetric native4131 Hessian required')
    return hessian


def directional_range(banks, weights, score_direction):
    """LSE slope range, including zero, over every active bank/top summand."""
    _validate_inputs(banks, weights)
    rows=sum(len(b.features) for b in banks)
    objective._array(score_direction,(rows,),'centered score direction')
    largest=0.; offset=0
    for bank, weight in zip(banks, weights, strict=True):
        n=len(bank.features); v=score_direction[offset:offset+n]; offset+=n
        top, rest=objective._top_indices(bank.top_indices,n)
        if weight == 0. or not len(rest): continue
        with np.errstate(over='ignore',invalid='ignore'):
            low=float(np.min(v[rest])); high=float(np.max(v[rest]))
            for t in top:
                lower=min(0.,low-float(v[t])); upper=max(0.,high-float(v[t]))
                span=upper-lower
                if not all(math.isfinite(z) for z in (lower,upper,span)):
                    raise FloatingPointError('finite full directional slope range required')
                largest=max(largest,span)
    return largest


def _step(banks, weights, x, hessian, gradient, direction):
    with np.errstate(over='ignore',invalid='ignore'):
        hp=hessian@direction
        a=float(-gradient@direction); q=float(direction@hp)
        denominator=float(np.linalg.norm(hessian,ord=np.inf))*float(np.max(np.abs(direction)))+float(np.max(np.abs(gradient)))
        residual=float(np.max(np.abs(hp+gradient)))
        xp=np.asarray(x@direction).ravel()
    if (not np.isfinite(hp).all() or not np.isfinite(xp).all()
            or not all(math.isfinite(v) for v in (a,q,denominator,residual))
            or a <= 0. or q <= 0. or denominator <= 0.):
        raise FloatingPointError('finite positive descent/curvature/solve denominator required')
    normalized=residual/denominator
    if not math.isfinite(normalized) or normalized > SOLVE_RESIDUAL_LIMIT:
        raise FloatingPointError('normalized solve residual exceeds fixed1e-12')
    r=directional_range(banks,weights,xp)
    return dict(a=a,q=q,r=r,alpha=_alpha(a,q,r),normalized_solve_residual=normalized)


def _checked_evaluate(theta,banks,weights):
    result=objective.coefficient_objective(theta,banks,weights)
    scalars=(result.objective,result.data_loss,result.penalty)
    if any(type(v) not in (int,float,np.float64) or not math.isfinite(v) or v < 0. for v in scalars):
        raise FloatingPointError('finite nonnegative objective/data/penalty required')
    g=result.gradient
    if type(g) is not np.ndarray or g.dtype != np.float64 or g.shape != (DIMENSION,) or not np.isfinite(g).all():
        raise FloatingPointError('finite exact float64(4131,) gradient required')
    norm=float(np.max(np.abs(g))); norm2=math.hypot(*map(float,g))
    if not math.isfinite(norm) or not math.isfinite(norm2): raise FloatingPointError('finite gradient norms required')
    return float(result.objective),g,float(result.data_loss),float(result.penalty),norm,norm2


def fit(banks,weights):
    """One fixed zero-initialized solve; no spec/offset/initialization override."""
    _validate_inputs(banks,weights)
    weights=objective._frozen(weights)
    theta=np.zeros(DIMENSION); trace=[]; initial=None
    counts=dict(updates=0,loop_evaluations=0,hessian_evaluations=0,linear_solves=0,final_checks=0,total_evaluations=0)
    status='input_metadata_failed'
    try:
        hashes=input_hash(banks,weights); training=_training(banks,weights); x=_design(banks)
        for iteration in range(MAX_UPDATES+1):
            status='loop_evaluation_failed';counts['loop_evaluations']+=1;counts['total_evaluations']+=1
            value,g,data,penalty,norm,norm2=_checked_evaluate(theta,banks,weights)
            if initial is None:initial=value
            row=dict(iteration=iteration,objective=value,gradient_infinity_norm=norm,gradient_l2_norm=norm2)
            trace.append(row)
            if norm <= GRADIENT_LIMIT:
                status='final_check_failed';counts['final_checks']+=1;counts['total_evaluations']+=1
                fv,fg,fd,fp,fn,fn2=_checked_evaluate(theta,banks,weights)
                if fn > GRADIENT_LIMIT:raise FloatingPointError('fresh final gradient exceeds strict1e-8')
                if fv > initial+1e-12*max(1.,abs(initial)):raise FloatingPointError('final objective exceeds zero-initialized end check')
                model=dict(configuration=configuration(),coefficients=theta.tolist(),final_gradient=fg.tolist(),
                    input_sha256=hashes,training=training,
                    optimization=dict(status='converged_gradient',accepted=True,**counts,initial_objective=initial,
                        objective=fv,weighted_bank_loss=fd,l2_penalty=fp,loop_gradient_infinity_norm=norm,
                        loop_gradient_l2_norm=norm2,gradient_infinity_norm=fn,gradient_l2_norm=fn2,trace=trace),
                    runtime=dict(numpy=np.__version__,scipy=scipy.__version__,python=platform.python_version()))
                model['model_sha256']=_model_hash(model)
                status='certificate_validation_failed';validate_model(model,expected_banks=banks,expected_weights=weights)
                return model
            if iteration == MAX_UPDATES:
                status='update_budget_exhausted';raise FloatingPointError('maximum2000 updates without convergence')
            status='hessian_failed';counts['hessian_evaluations']+=1
            hessian=_hessian(theta,banks,weights,x)
            status='linear_solve_failed';counts['linear_solves']+=1
            direction=_direction(hessian,g)
            status='descent_or_solve_residual_failed';step=_step(banks,weights,x,hessian,g,direction)
            status='iterate_update_failed';updated=_updated(theta,direction,step['alpha'])
            row.update(step);theta=updated;counts['updates']+=1
    except Exception as error:
        raise OptimizationError('fixed top-set Newton failed; no retry',dict(status=status,accepted=False,
            **counts,initial_objective=initial,final_theta=theta.tolist(),trace=trace,
            error_type=type(error).__name__,reason=str(error))) from error
    raise AssertionError('unreachable Newton loop')


def _number(v):return type(v) in (int,float) and math.isfinite(v)
def _close(a,b):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)


def validate_model(model,*,expected_banks=None,expected_weights=None):
    """Validate the finite sealed certificate, optionally exact supplied inputs.

Not an independent gradient/Hessian/source-provenance replay. Trace iteration
claims require independent execution evidence; no repair guarantee is implied.
"""
    keys={'configuration','coefficients','final_gradient','input_sha256','training','optimization','runtime','model_sha256'}
    if type(model) is not dict or set(model) != keys or _model_hash(model['configuration']) != _model_hash(configuration()):
        raise ValueError('strict native top-set model schema/configuration required')
    for name in ('coefficients','final_gradient'):
        if type(model[name]) is not list or len(model[name]) != DIMENSION or any(not _number(v) for v in model[name]):
            raise ValueError('finite exact4131 model vectors required')
    theta=np.asarray(model['coefficients'],dtype=np.float64);g=np.asarray(model['final_gradient'],dtype=np.float64)
    hashes=model['input_sha256']
    if type(hashes) is not dict or set(hashes) != {'features','top_indices','weights'} or any(type(v) is not str or re.fullmatch('[0-9a-f]{64}',v) is None for v in hashes.values()):
        raise ValueError('exact raw bank input checksum inventory required')
    info=model['training'];integer={'banks','rows','top_rows','rest_rows','positive_weight_banks','zero_weight_banks','empty_rest_banks'}
    if (type(info) is not dict or set(info) != integer|{'weight_mass','strong_convexity_lower_bound'}
            or any(type(info[k]) is not int or info[k] < 0 for k in integer)
            or info['banks'] <= 0 or info['top_rows'] < info['banks']
            or info['rows'] != info['top_rows']+info['rest_rows']
            or info['positive_weight_banks'] <= 0 or info['positive_weight_banks']+info['zero_weight_banks'] != info['banks']
            or info['empty_rest_banks'] > info['banks']
            or not _number(info['weight_mass']) or not _close(info['weight_mass'],MASS)
            or type(info['strong_convexity_lower_bound']) is not float or info['strong_convexity_lower_bound'] != 1.):
        raise ValueError('strict bank counts/mass/unit-ridge certificate required')
    m=model['optimization'];counts={'updates','loop_evaluations','hessian_evaluations','linear_solves','final_checks','total_evaluations'}
    numbers={'initial_objective','objective','weighted_bank_loss','l2_penalty','loop_gradient_infinity_norm','loop_gradient_l2_norm','gradient_infinity_norm','gradient_l2_norm'}
    if (type(m) is not dict or set(m) != counts|numbers|{'status','accepted','trace'}
            or m['status'] != 'converged_gradient' or m['accepted'] is not True
            or any(type(m[k]) is not int or m[k] < 0 for k in counts)
            or any(not _number(m[k]) or m[k] < 0. for k in numbers)):
        raise ValueError('strict accepted Newton status/count schema required')
    updates=m['updates'];loop=m['loop_evaluations']
    if not (0 <= updates <= MAX_UPDATES and loop == updates+1 and m['hessian_evaluations'] == updates
            and m['linear_solves'] == updates and m['final_checks'] == 1 and m['total_evaluations'] == loop+1):
        raise ValueError('exact bounded evaluation/update/solve accounting required')
    actual=dict(l2_penalty=float((.5*theta)@theta),gradient_infinity_norm=float(np.max(np.abs(g))),gradient_l2_norm=math.hypot(*map(float,g)))
    if (any(not math.isfinite(v) or not _close(m[k],v) for k,v in actual.items())
            or max(m['loop_gradient_infinity_norm'],m['gradient_infinity_norm'],actual['gradient_infinity_norm']) > GRADIENT_LIMIT
            or not _close(m['objective'],m['weighted_bank_loss']+m['l2_penalty'])
            or m['objective'] > m['initial_objective']+1e-12*max(1.,abs(m['initial_objective']))
            or updates == 0 and np.any(theta)):
        raise ValueError('inconsistent or above1e-8 final certificate')
    trace=m['trace'];common={'iteration','objective','gradient_infinity_norm','gradient_l2_norm'}
    steps={'a','q','r','alpha','normalized_solve_residual'}
    if type(trace) is not list or len(trace) != loop:raise ValueError('exact trace length required')
    for i,row in enumerate(trace):
        expected=common|steps if i < updates else common
        if (type(row) is not dict or set(row) != expected or type(row['iteration']) is not int or row['iteration'] != i
                or any(not _number(row[k]) or row[k] < 0. for k in expected-{'iteration'})
                or row['gradient_l2_norm'] < row['gradient_infinity_norm']):
            raise ValueError('finite ordered Newton trace required')
        if i < updates:
            if (row['gradient_infinity_norm'] <= GRADIENT_LIMIT or row['a'] <= 0. or row['q'] <= 0.
                    or not 0. < row['alpha'] <= 1. or row['normalized_solve_residual'] > SOLVE_RESIDUAL_LIMIT
                    or not _close(row['alpha'],_alpha(row['a'],row['q'],row['r']))):raise ValueError('invalid analytic descent/damping trace')
        elif row['gradient_infinity_norm'] > GRADIENT_LIMIT:raise ValueError('above1e-8 terminal gradient')
    if (trace[0]['objective'] != m['initial_objective'] or not _close(trace[-1]['objective'],m['objective'])
            or trace[-1]['gradient_infinity_norm'] != m['loop_gradient_infinity_norm']
            or trace[-1]['gradient_l2_norm'] != m['loop_gradient_l2_norm']):raise ValueError('trace/summary mismatch')
    runtime=model['runtime']
    if type(runtime) is not dict or set(runtime) != {'numpy','scipy','python'} or any(type(v) is not str or not v for v in runtime.values()):raise ValueError('exact numerical runtime required')
    if model['model_sha256'] != _model_hash({k:v for k,v in model.items() if k != 'model_sha256'}):raise ValueError('model checksum mismatch')
    if (expected_banks is None) != (expected_weights is None):raise ValueError('expected banks and weights required together')
    if expected_banks is not None:
        if input_hash(expected_banks,expected_weights) != hashes or _training(expected_banks,expected_weights) != info:
            raise ValueError('supplied expected raw bank inputs disagree')
    return theta
