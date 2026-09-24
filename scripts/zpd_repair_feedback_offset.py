"""Pure, fixed offset-logistic optimization over supplied pair matrices only.

No paths, banks, sources, labels from files, generation, execution or fitting
release exist in this module. Labels are supplied 0/1; their signed form is
2*y-1. Adjacent mirrored rows and mass1900 are mandatory, not constructed here.
The frozen base margin has coefficient ONE and the intercept is ZERO. Only
1296 interaction coefficients are optimized. All numerical settings are fixed.

For z=y_signed*(base+X@theta), the Hessian is
I + .1 X.T diag(w*sigmoid(z)*sigmoid(-z)) X. Hence H >= I and
H <= [1+.025*sum(w*||X_row||^2)] I. The objective is coercive and
1-strongly convex, so it has exactly one finite minimizer for finite inputs.
This regularized uniqueness is not data-identifiability of unsupported columns.
For the proposed same-bank binary gating of a common state vector with norm<=1,
each difference row also has norm<=1, giving L<=48.5. This pure solver cannot
certify that upstream feature provenance; it reports only the supplied-matrix
bound. A gradient infinity norm<=1e-6 implies coefficient L2 error<=36e-6
and objective gap<=6.48e-10, assuming exact arithmetic and this objective.
Neither a unique minimizer nor numerical convergence ensures repair correctness,
ranking stability, nonregression, generalization or educational benefit.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform

import numpy as np
import scipy
from scipy import sparse
from scipy.optimize import minimize
from scipy.special import expit

KIND = 'fixed_repair_feedback_offset_logistic_v1'
DIMENSION = 1296
C = .1
MASS = 1900.
MASS_RTOL = 1e-12
MASS_ATOL = 1e-12
MAX_ITERATIONS = 2000
FTOL = 1e-12
GTOL = 1e-8
GRADIENT_LIMIT = 1e-6
MAX_CORRECTIONS = 10
MAX_LINE_SEARCH = 20
MAX_FUNCTION_EVALUATIONS = 15000


class OffsetOptimizationError(RuntimeError):
    """A failed numerical cell, with diagnostics; no model or retry fallback."""

    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def configuration():
    return dict(kind=KIND,dimension=DIMENSION,C=C,mirrored_row_mass=MASS,
        intercept=0.,fixed_base_margin_coefficient=1.,labels='integer_0_1_signed_as_2y_minus_1',
        row_contract='adjacent_exact_feature_offset_label_mirrors_equal_positive_weights',
        matrix_arithmetic='canonical_float64_CSR',regularization='half_squared_L2_interaction_only',
        initialization='all_zero',optimizer='scipy.optimize.minimize_L-BFGS-B',
        analytic_jacobian=True,bounds=None,maxiter=MAX_ITERATIONS,ftol=FTOL,gtol=GTOL,
        maxcor=MAX_CORRECTIONS,maxls=MAX_LINE_SEARCH,maxfun=MAX_FUNCTION_EVALUATIONS,
        final_gradient_infinity_limit=GRADIENT_LIMIT,mass_rtol=MASS_RTOL,mass_atol=MASS_ATOL,
        retries=0,base_margin_optimized=False)


def _matrix(value):
    if type(value) is np.ndarray:
        if value.dtype != np.dtype('float64') or value.ndim != 2:
            raise ValueError('X must be a two-dimensional float64 ndarray or CSR matrix')
        matrix=sparse.csr_matrix(value,copy=True)
    elif sparse.isspmatrix_csr(value):
        if value.dtype != np.dtype('float64') or not value.has_canonical_format:
            raise ValueError('CSR X must have float64 values and unique sorted coordinates')
        matrix=value.copy()
    else:
        raise ValueError('X must be a float64 ndarray or CSR matrix')
    matrix.check_format(full_check=True)
    for lo,hi in zip(matrix.indptr,matrix.indptr[1:]):
        if hi-lo>1 and np.any(matrix.indices[lo+1:hi] <= matrix.indices[lo:hi-1]):
            raise ValueError('CSR rows require unique sorted coordinates')
    if matrix.shape[1] != DIMENSION or matrix.shape[0] == 0 or not np.isfinite(matrix.data).all():
        raise ValueError('nonempty finite 1296-column matrix required')
    matrix.eliminate_zeros()
    return matrix


def _float_vector(value, length, name):
    if (type(value) is not np.ndarray or value.dtype != np.dtype('float64') or
            value.shape != (length,) or not np.isfinite(value).all()):
        raise ValueError(name+' must be a finite float64 vector of exact length')
    return value.copy()


def _prepare(x, labels, weights, base_margin):
    matrix=_matrix(x); n=matrix.shape[0]
    if n % 2:
        raise ValueError('adjacent mirrored rows require a positive even row count')
    if (type(labels) is not np.ndarray or labels.dtype.kind not in 'iu' or
            labels.shape != (n,) or not np.isin(labels,[0,1]).all()):
        raise ValueError('labels must be a 0/1 integer vector of exact row length')
    y=labels.astype(np.int64,copy=True)
    weight=_float_vector(weights,n,'weights'); offset=_float_vector(base_margin,n,'base_margin')
    try:
        weight_mass=math.fsum(weight)
    except OverflowError as error:
        raise ValueError('finite fixed weight mass required') from error
    if not (weight > 0).all() or not math.isclose(weight_mass,MASS,rel_tol=MASS_RTOL,abs_tol=MASS_ATOL):
        raise ValueError('positive weights with fixed mirrored-row mass1900 required')
    if (not np.array_equal(y[1::2],1-y[::2]) or
            not np.array_equal(weight[1::2],weight[::2]) or
            not np.array_equal(offset[1::2],-offset[::2])):
        raise ValueError('adjacent label/weight/base-margin mirror contract violated')
    difference=matrix[::2]+matrix[1::2];difference.eliminate_zeros()
    if difference.nnz:
        raise ValueError('adjacent feature rows must be exact negatives')
    return matrix,y,weight,offset


def _evaluate(theta, x, signed, weights, base_margin):
    """Stable analytic objective/gradient; no input or coefficient mutation."""
    with np.errstate(over='ignore',invalid='ignore',under='ignore'):
        margins=np.asarray(x@theta).reshape(-1)+base_margin
        z=signed*margins
        scaled_weights=C*weights
        data=float(scaled_weights@np.logaddexp(0.,-z))
        penalty=float((.5*theta)@theta)
        value=penalty+data
        gradient=theta-np.asarray(x.T@(scaled_weights*signed*expit(-z))).reshape(-1)
    if (not np.isfinite(margins).all() or not np.isfinite(z).all() or not math.isfinite(value)
            or not math.isfinite(data) or not math.isfinite(penalty) or not np.isfinite(gradient).all()):
        raise FloatingPointError('offset objective or gradient exceeds finite float64 arithmetic')
    return value,gradient,data,penalty


def objective_and_gradient(theta, x, labels, weights, base_margin):
    """Evaluate the fixed objective on a fully validated mirrored cohort."""
    matrix,y,weight,offset=_prepare(x,labels,weights,base_margin)
    theta=_float_vector(theta,DIMENSION,'theta')
    value,gradient,_,_=_evaluate(theta,matrix,2.*y-1.,weight,offset)
    return value,gradient


def _sha_arrays(*arrays):
    digest=hashlib.sha256()
    for array in arrays:
        array=np.ascontiguousarray(array)
        header=json.dumps(dict(shape=list(array.shape),dtype=array.dtype.str),sort_keys=True,separators=(',',':')).encode()
        digest.update(len(header).to_bytes(8,'little'));digest.update(header)
        data=array.tobytes(order='C');digest.update(len(data).to_bytes(8,'little'));digest.update(data)
    return digest.hexdigest()


def _training_metadata(x, labels, weights, offset):
    with np.errstate(over='ignore',invalid='ignore'):
        squared=np.asarray(x.multiply(x).sum(axis=1)).ravel()
        weighted_squared=float(weights@squared)
        bound=1.+.25*C*weighted_squared
    if not np.isfinite(squared).all() or not math.isfinite(bound):
        raise FloatingPointError('finite float64 supplied-matrix curvature bound required')
    return dict(rows=x.shape[0],unordered_pairs=x.shape[0]//2,positive_rows=int(labels.sum()),
        zero_difference_rows=int((np.diff(x.indptr)==0).sum()),weight_mass=math.fsum(weights),
        maximum_row_squared_norm=float(squared.max()),weighted_row_squared_norm_sum=weighted_squared,
        strong_convexity_lower_bound=1.,hessian_spectral_upper_bound=bound,
        input_sha256=dict(features=_sha_arrays(np.asarray(x.shape,dtype='<i8'),x.indptr.astype('<i8'),
            x.indices.astype('<i8'),x.data.astype('<f8')),labels=_sha_arrays(labels.astype('<i8')),
            weights=_sha_arrays(weights.astype('<f8')),base_margin=_sha_arrays(offset.astype('<f8'))))


def _model_hash(model):
    return hashlib.sha256(json.dumps(model,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def fit_offset(x, labels, weights, base_margin):
    """One fixed optimization, or an explicit failure. No tuning parameters."""
    matrix,y,weight,offset=_prepare(x,labels,weights,base_margin)
    zero=np.zeros(DIMENSION,dtype=np.float64);signed=2.*y-1.
    initial,_,_,_=_evaluate(zero,matrix,signed,weight,offset)
    training=_training_metadata(matrix,y,weight,offset)
    def objective(theta):
        value,gradient,_,_=_evaluate(theta,matrix,signed,weight,offset)
        return value,gradient
    options=dict(maxiter=MAX_ITERATIONS,ftol=FTOL,gtol=GTOL,maxcor=MAX_CORRECTIONS,
                 maxls=MAX_LINE_SEARCH,maxfun=MAX_FUNCTION_EVALUATIONS)
    try:
        result=minimize(objective,zero,method='L-BFGS-B',jac=True,bounds=None,options=options)
    except Exception as error:
        raise OffsetOptimizationError('fixed offset optimizer raised; no retry',
            dict(accepted=False,error_type=type(error).__name__,message=str(error))) from error
    try:
        if (type(result.success) not in (bool,np.bool_) or not isinstance(result.message,str) or
                any(isinstance(getattr(result,key),(bool,np.bool_)) or
                    not isinstance(getattr(result,key),(int,np.integer)) for key in ('status','nit','nfev','njev'))):
            raise ValueError('strict optimizer success/status/count types required')
        metadata=dict(success=bool(result.success),status=int(result.status),message=result.message,
            iterations=int(result.nit),function_evaluations=int(result.nfev),gradient_evaluations=int(result.njev))
    except (AttributeError,TypeError,ValueError) as error:
        raise OffsetOptimizationError('malformed optimizer result; no retry',
            dict(accepted=False,error_type=type(error).__name__,reason=str(error))) from error
    try:
        theta=_float_vector(result.x,DIMENSION,'optimizer coefficients')
        value,gradient,data,penalty=_evaluate(theta,matrix,signed,weight,offset)
        norm=float(np.max(np.abs(gradient)))
        norm2=math.hypot(*map(float,gradient))
        metadata.update(initial_objective=initial,objective=value,weighted_logistic_loss=data,
            l2_penalty=penalty,gradient_infinity_norm=norm,gradient_l2_norm=norm2)
        reported_gradient=_float_vector(np.asarray(result.jac),DIMENSION,'optimizer gradient')
        if (type(result.fun) not in (float,np.float64) or not math.isfinite(result.fun) or
                not math.isclose(float(result.fun),value,rel_tol=1e-12,abs_tol=1e-12) or
                not np.allclose(reported_gradient,gradient,rtol=1e-10,atol=1e-12)):
            raise ValueError('optimizer-returned objective/gradient disagrees with recomputation')
        if (not metadata['success'] or metadata['status'] != 0 or
                not 0 <= metadata['iterations'] <= MAX_ITERATIONS or
                not 1 <= metadata['function_evaluations'] <= MAX_FUNCTION_EVALUATIONS or
                not 1 <= metadata['gradient_evaluations'] <= MAX_FUNCTION_EVALUATIONS or norm > GRADIENT_LIMIT):
            raise ValueError('fixed optimizer success/status/budget/final-gradient criteria not satisfied')
        if value > initial+1e-12*max(1.,abs(initial)):
            raise ValueError('final objective exceeds the zero-initialized objective')
    except (AttributeError,ValueError,FloatingPointError,TypeError) as error:
        raise OffsetOptimizationError('fixed offset optimization rejected; no retry',
            dict(metadata,accepted=False,error_type=type(error).__name__,reason=str(error))) from error
    model=dict(configuration=configuration(),coefficients=theta.tolist(),final_gradient=gradient.tolist(),
        training=training,optimization=dict(metadata,accepted=True),
        runtime=dict(numpy=np.__version__,scipy=scipy.__version__,python=platform.python_version()))
    model['model_sha256']=_model_hash(model)
    validate_model(model)
    return model


def _fixed(actual,expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected,dict):
        return set(actual)==set(expected) and all(_fixed(actual[k],v) for k,v in expected.items())
    return actual==expected


def _number(value, *, nonnegative=False):
    return type(value) in (int,float) and math.isfinite(value) and (not nonnegative or value>=0)


def validate_model(model):
    """Strict serialized numerical certificate; array provenance needs replay.

    This checks internal consistency, not that input hashes correspond to any
    particular bank or fold. An independent future auditor must load its allowed
    matrices, reproduce their hashes, and recompute objective/gradient itself.
    """
    keys={'configuration','coefficients','final_gradient','training','optimization','runtime','model_sha256'}
    if type(model) is not dict or set(model)!=keys or not _fixed(model['configuration'],configuration()):
        raise ValueError('strict fixed offset model configuration/schema required')
    for key in ('coefficients','final_gradient'):
        values=model[key]
        if type(values) is not list or len(values)!=DIMENSION or any(not _number(v) for v in values):
            raise ValueError('finite 1296-value model vectors required')
    theta=np.asarray(model['coefficients'],dtype=float);gradient=np.asarray(model['final_gradient'],dtype=float)
    meta=model['optimization']
    opt_keys={'success','status','message','iterations','function_evaluations','gradient_evaluations',
        'initial_objective','objective','weighted_logistic_loss','l2_penalty','gradient_infinity_norm',
        'gradient_l2_norm','accepted'}
    if (type(meta) is not dict or set(meta)!=opt_keys or meta['success'] is not True or meta['accepted'] is not True
            or type(meta['status']) is not int or meta['status'] != 0 or type(meta['message']) is not str):
        raise ValueError('accepted fixed optimizer metadata required')
    if (type(meta['iterations']) is not int or not 0<=meta['iterations']<=MAX_ITERATIONS or
            any(type(meta[k]) is not int or not 1<=meta[k]<=MAX_FUNCTION_EVALUATIONS
                for k in ('function_evaluations','gradient_evaluations')) or
            any(not _number(meta[k],nonnegative=True) for k in ('initial_objective','objective',
                'weighted_logistic_loss','l2_penalty','gradient_infinity_norm','gradient_l2_norm')) or
            meta['gradient_infinity_norm']>GRADIENT_LIMIT):
        raise ValueError('fixed iteration/budget/gradient limits violated')
    actual=dict(l2_penalty=float((.5*theta)@theta),gradient_infinity_norm=float(np.max(np.abs(gradient))),
        gradient_l2_norm=math.hypot(*map(float,gradient)))
    if (any(not math.isclose(meta[k],v,rel_tol=1e-12,abs_tol=1e-12) for k,v in actual.items()) or
            actual['gradient_infinity_norm']>GRADIENT_LIMIT or
            not math.isclose(meta['objective'],meta['weighted_logistic_loss']+meta['l2_penalty'],rel_tol=1e-12,abs_tol=1e-12)
            or meta['objective']>meta['initial_objective']+1e-12*max(1.,meta['initial_objective'])):
        raise ValueError('inconsistent objective or gradient certificate')
    info=model['training'];train_keys={'rows','unordered_pairs','positive_rows','zero_difference_rows','weight_mass',
        'maximum_row_squared_norm','weighted_row_squared_norm_sum','strong_convexity_lower_bound',
        'hessian_spectral_upper_bound','input_sha256'}
    if (type(info) is not dict or set(info)!=train_keys or
            any(type(info[k]) is not int for k in ('rows','unordered_pairs','positive_rows','zero_difference_rows')) or
            info['rows']<=0 or info['rows']%2 or info['unordered_pairs']!=info['rows']//2 or
            info['positive_rows']!=info['rows']//2 or not 0<=info['zero_difference_rows']<=info['rows'] or
            info['zero_difference_rows']%2):
        raise ValueError('strict mirrored training counts required')
    if (any(not _number(info[k],nonnegative=True) for k in ('weight_mass','maximum_row_squared_norm',
            'weighted_row_squared_norm_sum','strong_convexity_lower_bound','hessian_spectral_upper_bound')) or
            not math.isclose(info['weight_mass'],MASS,rel_tol=MASS_RTOL,abs_tol=MASS_ATOL) or
            info['strong_convexity_lower_bound']!=1. or
            not math.isclose(info['hessian_spectral_upper_bound'],1.+.25*C*info['weighted_row_squared_norm_sum'],rel_tol=1e-12,abs_tol=1e-12)):
        raise ValueError('invalid supplied-matrix curvature/mass certificate')
    hashes=info['input_sha256']
    if (type(hashes) is not dict or set(hashes)!={'features','labels','weights','base_margin'} or
            any(type(v) is not str or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for v in hashes.values())):
        raise ValueError('exact matrix/label/weight/offset SHA256 inventory required')
    runtime=model['runtime']
    if (type(runtime) is not dict or set(runtime)!={'numpy','scipy','python'} or
            any(type(v) is not str or not v for v in runtime.values())):
        raise ValueError('numerical runtime metadata required')
    if model['model_sha256']!=_model_hash({k:v for k,v in model.items() if k!='model_sha256'}):
        raise ValueError('offset model checksum mismatch')
    return theta
