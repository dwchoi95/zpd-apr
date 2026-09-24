"""Pure explicit-width fixed-offset residuals; no paths, CLI or release.

Only representation identity/width are parameterized. Preferences, natural
weights, mass1900, C=.1, optimizer and acceptance criteria are not configurable.
The frozen dimension-free arithmetic helpers are reused explicitly below;
their source must be in the adapter's release closure. An independent auditor
must still reconstruct arrays and certificates without reusing this producer.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from itertools import combinations
import json
import math
import platform
import re

import numpy as np
import scipy
from scipy import sparse
from scipy.optimize import minimize

from scripts import zpd_repair_feedback_offset as arithmetic
from scripts.zpd_repair_feedback_labels import validate_core_labels
from scripts.zpd_repair_fit import Example
from scripts.zpd_repair_pairwise import preference
from src.repair.pilot_contracts import CandidateBank, PilotObservation

C = .1
MASS = 1900.
GRADIENT_LIMIT = 1e-6
OPTIONS = dict(maxiter=2000, ftol=1e-12, gtol=1e-8, maxcor=10, maxls=20, maxfun=15000)
VARIATION_TOLERANCE = 1e-12  # diagnostics only, never pair inclusion
OffsetOptimizationError = arithmetic.OffsetOptimizationError
_sha_arrays = arithmetic._sha_arrays
_model_hash = arithmetic._model_hash


@dataclass(frozen=True)
class ResidualSpec:
    representation: str
    dimension: int
    feature_configuration_sha256: str
    model_kind: str

    def __post_init__(self):
        if (any(type(v) is not str or not v for v in (self.representation, self.model_kind))
                or type(self.dimension) is not int or self.dimension <= 0
                or type(self.feature_configuration_sha256) is not str
                or re.fullmatch('[0-9a-f]{64}', self.feature_configuration_sha256) is None):
            raise ValueError('explicit immutable representation, positive width, feature SHA256 and model kind required')


def _spec(value):
    if type(value) is not ResidualSpec: raise ValueError('externally expected exact ResidualSpec required')
    value.__post_init__()
    return value


def _immutable(array):
    """Bytes-backed copy: writeability cannot be re-enabled by the caller."""
    return np.frombuffer(array.tobytes(order='C'), dtype=array.dtype).reshape(array.shape)


@dataclass(frozen=True)
class CandidateBlock:
    candidate_ids: tuple[str, ...]
    matrix: np.ndarray

    def __post_init__(self):
        ids = self.candidate_ids; array = self.matrix
        if (type(ids) is not tuple or not ids or len(set(ids)) != len(ids)
                or any(type(cid) is not str or re.fullmatch('[0-9a-f]{64}', cid) is None for cid in ids)):
            raise ValueError('nonempty unique exact candidate SHA tuple required')
        if (type(array) is not np.ndarray or array.dtype != np.dtype('float64')
                or array.ndim != 2 or array.shape[0] != len(ids) or array.shape[1] <= 0
                or not np.isfinite(array).all()):
            raise ValueError('finite float64 candidate matrix with exact row coverage required')
        object.__setattr__(self, 'matrix', _immutable(array))


@dataclass(frozen=True)
class PairPlan:
    bank_candidate_ids: tuple
    row_keys: tuple  # (bank_id, left_candidate_id, right_candidate_id), mirrored adjacency
    y: np.ndarray
    weights: np.ndarray
    _metadata_json: str

    @property
    def metadata(self): return json.loads(self._metadata_json)


@dataclass(frozen=True)
class PairData:
    matrix: np.ndarray
    y: np.ndarray
    weights: np.ndarray
    base_margin: np.ndarray
    metadata: dict


class NoInformativePairs(ValueError):
    def __init__(self, metadata):
        super().__init__('no unequal stable training candidate pairs; no fit or fallback')
        self.metadata = metadata


def _exact(value, keys, name):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(name+' must have exactly the supplied fold/bank keys')


def make_pair_plan(examples, banks, labels):
    """Dimension-free legacy relation, order, and both weight normalizations.

    Exact supplied keys are validated before label values. Train membership and
    source seals must additionally be certified by the fold caller; no pure
    object function can detect a maliciously relabeled held-out example.
    """
    if type(examples) not in (list, tuple) or not examples or any(type(ex) is not Example for ex in examples):
        raise ValueError('nonempty exact Example sequence required')
    if any(ex.split != 'train' or type(ex.observation) is not PilotObservation
            or any(type(v) is not str or not v for v in (ex.example_id, ex.bank_id, ex.user_id)) for ex in examples):
        raise ValueError('strict fold-training examples required')
    if len({ex.example_id for ex in examples}) != len(examples) or len({ex.bank_id for ex in examples}) != len(examples):
        raise ValueError('unique example and bank IDs required')
    _exact(banks, {ex.bank_id for ex in examples}, 'banks')
    for ex in examples:
        bank = banks[ex.bank_id]
        if (type(bank) is not CandidateBank or bank.problem_id != ex.observation.problem_id
                or bank.current_source != ex.observation.current.source):
            raise ValueError('exact observation and candidate-bank match required')
    required = {(bid, c.candidate_id) for bid, bank in banks.items() for c in bank.candidates}
    _exact(labels, required, 'labels')
    # Check dictionary-to-row identity as well as the public core validator.
    for key, row in labels.items():
        if type(row) is not dict or (row.get('bank_id'), row.get('candidate_id')) != key:
            raise ValueError('label dictionary and row identity mismatch')
    core = validate_core_labels(list(labels.values()), banks)
    records, diagnostics = [], []
    for ex in examples:
        bank = banks[ex.bank_id]; candidates = bank.candidates
        keys = [preference(core[ex.bank_id, c.candidate_id]) for c in candidates]
        stable = [i for i, key in enumerate(keys) if key is not None]
        stable_pairs = list(combinations(stable, 2))
        pairs = [(a, b, int(keys[a] > keys[b])) for a, b in stable_pairs if keys[a] != keys[b]]
        if pairs: records.append((ex, pairs, len(stable)))
        diagnostics.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            bank_seal_sha256=bank.seal_sha256, problem_id=bank.problem_id,
            candidate_ids=[c.candidate_id for c in candidates], is_noop=[c.is_noop for c in candidates],
            candidate_statuses=[core[ex.bank_id, c.candidate_id]['status'] for c in candidates],
            candidate_count=len(candidates), stable_candidates=len(stable), unknown_candidates=len(candidates)-len(stable),
            pairs_with_unknown=len(candidates)*(len(candidates)-1)//2-len(stable_pairs),
            stable_tied_pairs=len(stable_pairs)-len(pairs), informative_unordered_pairs=len(pairs)))
    prefixes = Counter(ex.user_id for ex, *_ in records)
    users = {ex.user_id for ex in examples}; informative = [ex.example_id for ex, *_ in records]
    training = dict(train_prefixes=len(examples), train_users=len(users), informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(examples)-len(records), users=len(prefixes),
        users_without_informative_prefix=len(users-set(prefixes)), ordered_pairs=0, pair_example_ids=[],
        informative_train_example_ids=informative,
        uninformative_train_example_ids=sorted({ex.example_id for ex in examples}-set(informative)),
        stable_train_candidates=sum(count for _, _, count in records),
        weight_normalization='fixed_reference_total_pair_weight', reference_pair_weight=MASS,
        sample_weight_sum=0., prior_mean_one_weight_sum=0.)
    metadata = dict(kind='fixed_train_only_residual_pair_plan_v1',
        preference='legacy_stable_lexicographic_all_ac_loss_zero_net_gain',
        no_pair_filter_by_feature_variation=True, fixed_base_coefficient=1., intercept=0.,
        training=training, banks=diagnostics, pair_candidate_ids=[])
    if not records: raise NoInformativePairs(metadata)
    rows, outcomes, weights = [], [], []
    for ex, pairs, _ in records:
        candidates = banks[ex.bank_id].candidates
        for a, b, target in pairs:
            left, right = candidates[a].candidate_id, candidates[b].candidate_id
            rows.extend(((ex.bank_id, left, right), (ex.bank_id, right, left)))
            outcomes.extend((target, 1-target))
            weights.extend([1/(prefixes[ex.user_id]*len(pairs)*2)]*2)
            training['pair_example_ids'].extend([ex.example_id]*2)
            metadata['pair_candidate_ids'].extend([[left, right], [right, left]])
    weights = np.asarray(weights, dtype=np.float64)
    weights *= len(weights)/weights.sum()
    old_mass = float(weights.sum())
    weights = weights*(MASS/old_mass)
    training.update(ordered_pairs=len(weights), sample_weight_sum=float(weights.sum()), prior_mean_one_weight_sum=old_mass)
    return PairPlan(tuple((ex.bank_id, tuple(c.candidate_id for c in banks[ex.bank_id].candidates)) for ex in examples),
        tuple(rows), _immutable(np.asarray(outcomes, dtype=np.int64)), _immutable(weights),
        json.dumps(metadata, sort_keys=True, allow_nan=False))


def _candidate_inputs(block, base_scores, spec, *, ids=None):
    _spec(spec)
    if type(block) is not CandidateBlock: raise ValueError('exact CandidateBlock required')
    if (block.matrix.shape != (len(block.candidate_ids), spec.dimension)
            or block.matrix.dtype != np.dtype('float64') or not np.isfinite(block.matrix).all()):
        raise ValueError('candidate matrix differs from externally expected residual width')
    if ids is not None and block.candidate_ids != ids: raise ValueError('exact bank candidate order required')
    _exact(base_scores, block.candidate_ids, 'base scores')
    if any(type(v) not in (int, float, np.float64) or not math.isfinite(v) for v in base_scores.values()):
        raise ValueError('finite real base scores required, without bools or arrays')
    return np.asarray([base_scores[cid] for cid in block.candidate_ids], dtype=np.float64)


def _difference(left, right):
    with np.errstate(over='ignore', invalid='ignore'): difference = left-right
    if not np.isfinite(difference).all(): raise ValueError('nonfinite pair difference')
    return difference


def materialize_pairs(plan, blocks, base_scores, *, spec):
    _spec(spec)
    if type(plan) is not PairPlan: raise ValueError('exact PairPlan required')
    expected = dict(plan.bank_candidate_ids)
    _exact(blocks, expected, 'candidate blocks'); _exact(base_scores, expected, 'base scores')
    bases = {bid: _candidate_inputs(blocks[bid], base_scores[bid], spec, ids=ids) for bid, ids in expected.items()}
    index = {bid: {cid: i for i, cid in enumerate(ids)} for bid, ids in expected.items()}
    matrices, offsets = [], []
    if not plan.row_keys or len(plan.row_keys) % 2: raise ValueError('positive mirrored pair plan required')
    for position in range(0, len(plan.row_keys), 2):
        bid, left, right = plan.row_keys[position]
        if plan.row_keys[position+1] != (bid, right, left): raise ValueError('adjacent candidate-key mirrors required')
        a, b = index[bid][left], index[bid][right]
        difference = _difference(blocks[bid].matrix[a], blocks[bid].matrix[b])
        offset = _difference(bases[bid][a], bases[bid][b])
        # Construct the second row by negation, preserving even signed-zero
        # bytes of the frozen builder rather than recomputing right-minus-left.
        matrices.extend((difference, -difference)); offsets.extend((offset, -offset))
    matrix = np.stack(matrices); margin = np.asarray(offsets, dtype=np.float64)
    _prepare(matrix, plan.y, plan.weights, margin, spec)  # mirror, mass and shape contract
    metadata = plan.metadata
    metadata.update(kind='fixed_train_only_residual_pairs_v1', spec=asdict(spec),
                    diagnostic_variation_tolerance=VARIATION_TOLERANCE)
    informative = {(bid, left, right) for bid, left, right in plan.row_keys[::2]}
    def counts(bid, candidate_ids, noop, only_informative):
        result = dict(unordered_pairs=0, noop_edited_pairs=0, edited_edited_pairs=0,
            interaction_varying_pairs=0, zero_interaction_pairs=0, nonzero_base_margin_pairs=0)
        for a, b in combinations(range(len(candidate_ids)), 2):
            if only_informative and (bid, candidate_ids[a], candidate_ids[b]) not in informative: continue
            diff = _difference(blocks[bid].matrix[a], blocks[bid].matrix[b])
            result['unordered_pairs'] += 1
            result['noop_edited_pairs' if noop[a] or noop[b] else 'edited_edited_pairs'] += 1
            result['interaction_varying_pairs'] += int(np.max(np.abs(diff)) > VARIATION_TOLERANCE)
            result['zero_interaction_pairs'] += int(not np.any(diff))
            result['nonzero_base_margin_pairs'] += int(_difference(bases[bid][a], bases[bid][b]) != 0.)
        return result
    for bank in metadata['banks']:
        for name, only in (('all_pair_counts', False), ('informative_pair_counts', True)):
            bank[name] = counts(bank['bank_id'], bank['candidate_ids'], bank['is_noop'], only)
    for name in ('all_pair_counts', 'informative_pair_counts'):
        metadata[name] = {key: sum(bank[name][key] for bank in metadata['banks']) for key in metadata['banks'][0][name]}
    return PairData(matrix, plan.y.copy(), plan.weights.copy(), margin, metadata)


def configuration(spec):
    _spec(spec)
    value = arithmetic.configuration()
    value.update(kind=spec.model_kind, dimension=spec.dimension, representation=asdict(spec))
    return value


def _matrix(value, spec):
    _spec(spec)
    if type(value) is np.ndarray and value.dtype == np.dtype('float64') and value.ndim == 2:
        matrix = sparse.csr_matrix(value, copy=True)
    elif sparse.isspmatrix_csr(value) and value.dtype == np.dtype('float64') and value.has_canonical_format:
        matrix = value.copy()
    else: raise ValueError('finite float64 ndarray or canonical CSR required')
    matrix.check_format(full_check=True)
    if matrix.shape[1] != spec.dimension or not matrix.shape[0] or not np.isfinite(matrix.data).all():
        raise ValueError('nonempty finite matrix with externally expected width required')
    for lo, hi in zip(matrix.indptr, matrix.indptr[1:]):
        if hi-lo > 1 and np.any(matrix.indices[lo+1:hi] <= matrix.indices[lo:hi-1]):
            raise ValueError('unique sorted CSR coordinates required')
    matrix.eliminate_zeros()
    return matrix


def _prepare(x, labels, weights, base_margin, spec):
    matrix = _matrix(x, spec); n = matrix.shape[0]
    if n % 2: raise ValueError('positive even mirrored row count required')
    if (type(labels) is not np.ndarray or labels.dtype.kind not in 'iu'
            or labels.shape != (n,) or not np.isin(labels, [0, 1]).all()):
        raise ValueError('exact integer binary label vector required')
    y = labels.astype(np.int64, copy=True)
    w = arithmetic._float_vector(weights, n, 'weights')
    base = arithmetic._float_vector(base_margin, n, 'base_margin')
    try: mass = math.fsum(w)
    except OverflowError as error: raise ValueError('finite fixed weight mass required') from error
    if not (w > 0).all() or not math.isclose(mass, MASS, rel_tol=1e-12, abs_tol=1e-12):
        raise ValueError('positive fixed mirrored mass1900 required')
    if (not np.array_equal(y[1::2], 1-y[::2]) or not np.array_equal(w[1::2], w[::2])
            or not np.array_equal(base[1::2], -base[::2])):
        raise ValueError('adjacent label/weight/offset mirrors required')
    difference = matrix[::2]+matrix[1::2]; difference.eliminate_zeros()
    if difference.nnz: raise ValueError('adjacent feature mirrors required')
    return matrix, y, w, base


def objective_and_gradient(theta, x, labels, weights, base_margin, *, spec):
    matrix, y, w, base = _prepare(x, labels, weights, base_margin, spec)
    theta = arithmetic._float_vector(theta, spec.dimension, 'theta')
    value, gradient, _, _ = arithmetic._evaluate(theta, matrix, 2.*y-1., w, base)
    return value, gradient


def fit_offset(x, labels, weights, base_margin, *, spec):
    matrix, y, w, base = _prepare(x, labels, weights, base_margin, spec)
    zero = np.zeros(spec.dimension, dtype=np.float64); signed = 2.*y-1.
    initial, _, _, _ = arithmetic._evaluate(zero, matrix, signed, w, base)
    training = arithmetic._training_metadata(matrix, y, w, base)
    def objective(theta):
        value, gradient, _, _ = arithmetic._evaluate(theta, matrix, signed, w, base)
        return value, gradient
    try:
        result = minimize(objective, zero, method='L-BFGS-B', jac=True, bounds=None, options=dict(OPTIONS))
    except Exception as error:
        raise OffsetOptimizationError('fixed residual optimizer raised; no retry',
            dict(accepted=False, error_type=type(error).__name__, message=str(error))) from error
    metadata = {}
    try:
        if (type(result.success) not in (bool, np.bool_) or not isinstance(result.message, str)
                or any(isinstance(getattr(result, key), (bool, np.bool_)) or not isinstance(getattr(result, key), (int, np.integer))
                       for key in ('status', 'nit', 'nfev', 'njev'))):
            raise ValueError('strict optimizer success/status/count types required')
        metadata = dict(success=bool(result.success), status=int(result.status), message=result.message,
            iterations=int(result.nit), function_evaluations=int(result.nfev), gradient_evaluations=int(result.njev))
        theta = arithmetic._float_vector(result.x, spec.dimension, 'optimizer coefficients')
        value, gradient, data, penalty = arithmetic._evaluate(theta, matrix, signed, w, base)
        norm = float(np.max(np.abs(gradient))); norm2 = math.hypot(*map(float, gradient))
        metadata.update(initial_objective=initial, objective=value, weighted_logistic_loss=data,
            l2_penalty=penalty, gradient_infinity_norm=norm, gradient_l2_norm=norm2)
        reported = arithmetic._float_vector(np.asarray(result.jac), spec.dimension, 'optimizer gradient')
        if (type(result.fun) not in (float, np.float64) or not math.isfinite(result.fun)
                or not math.isclose(float(result.fun), value, rel_tol=1e-12, abs_tol=1e-12)
                or not np.allclose(reported, gradient, rtol=1e-10, atol=1e-12)):
            raise ValueError('reported objective/gradient differs from recomputation')
        if (not metadata['success'] or metadata['status'] != 0 or not 0 <= metadata['iterations'] <= OPTIONS['maxiter']
                or any(not 1 <= metadata[k] <= OPTIONS['maxfun'] for k in ('function_evaluations', 'gradient_evaluations'))
                or norm > GRADIENT_LIMIT or value > initial+1e-12*max(1., abs(initial))):
            raise ValueError('fixed convergence/budget/gradient criteria failed')
    except (AttributeError, TypeError, ValueError, FloatingPointError) as error:
        raise OffsetOptimizationError('fixed residual optimizer rejected; no retry',
            dict(metadata, accepted=False, error_type=type(error).__name__, reason=str(error))) from error
    model = dict(configuration=configuration(spec), coefficients=theta.tolist(), final_gradient=gradient.tolist(),
        training=training, optimization=dict(metadata, accepted=True),
        runtime=dict(numpy=np.__version__, scipy=scipy.__version__, python=platform.python_version()))
    model['model_sha256'] = _model_hash(model)
    validate_offset(model, expected_spec=spec)
    return model


def validate_offset(model, *, expected_spec):
    """Internal numerical certificate only; input/source authenticity needs replay.

    H >= I gives coefficient error <= sqrt(d)*1e-6 and objective gap <=
    d*1e-12/2 in exact arithmetic. For d=144 these are12e-6 and7.2e-11.
    No ranking, repair, or educational guarantee follows from these bounds.
    """
    spec = _spec(expected_spec)
    keys = {'configuration', 'coefficients', 'final_gradient', 'training', 'optimization', 'runtime', 'model_sha256'}
    if type(model) is not dict or set(model) != keys or not arithmetic._fixed(model['configuration'], configuration(spec)):
        raise ValueError('strict externally spec-bound residual model schema required')
    for key in ('coefficients', 'final_gradient'):
        values = model[key]
        if type(values) is not list or len(values) != spec.dimension or any(not arithmetic._number(v) for v in values):
            raise ValueError('exact expected-width finite numerical model vector required')
    theta = np.asarray(model['coefficients'], dtype=np.float64); gradient = np.asarray(model['final_gradient'], dtype=np.float64)
    meta = model['optimization']
    opt_keys = {'success', 'status', 'message', 'iterations', 'function_evaluations', 'gradient_evaluations',
        'initial_objective', 'objective', 'weighted_logistic_loss', 'l2_penalty', 'gradient_infinity_norm', 'gradient_l2_norm', 'accepted'}
    if (type(meta) is not dict or set(meta) != opt_keys or meta['success'] is not True or meta['accepted'] is not True
            or type(meta['status']) is not int or meta['status'] != 0 or type(meta['message']) is not str
            or type(meta['iterations']) is not int or not 0 <= meta['iterations'] <= OPTIONS['maxiter']
            or any(type(meta[k]) is not int or not 1 <= meta[k] <= OPTIONS['maxfun'] for k in ('function_evaluations', 'gradient_evaluations'))
            or any(not arithmetic._number(meta[k], nonnegative=True) for k in ('initial_objective', 'objective',
                'weighted_logistic_loss', 'l2_penalty', 'gradient_infinity_norm', 'gradient_l2_norm'))):
        raise ValueError('fixed accepted optimizer metadata required')
    actual = dict(l2_penalty=float((.5*theta)@theta), gradient_infinity_norm=float(np.max(np.abs(gradient))),
                  gradient_l2_norm=math.hypot(*map(float, gradient)))
    if (any(not math.isclose(meta[k], v, rel_tol=1e-12, abs_tol=1e-12) for k, v in actual.items())
            or actual['gradient_infinity_norm'] > GRADIENT_LIMIT or meta['gradient_infinity_norm'] > GRADIENT_LIMIT
            or not math.isclose(meta['objective'], meta['weighted_logistic_loss']+meta['l2_penalty'], rel_tol=1e-12, abs_tol=1e-12)
            or meta['objective'] > meta['initial_objective']+1e-12*max(1., meta['initial_objective'])):
        raise ValueError('inconsistent objective/gradient certificate')
    info = model['training']
    train_keys = {'rows', 'unordered_pairs', 'positive_rows', 'zero_difference_rows', 'weight_mass', 'maximum_row_squared_norm',
        'weighted_row_squared_norm_sum', 'strong_convexity_lower_bound', 'hessian_spectral_upper_bound', 'input_sha256'}
    if (type(info) is not dict or set(info) != train_keys
            or any(type(info[k]) is not int for k in ('rows', 'unordered_pairs', 'positive_rows', 'zero_difference_rows'))
            or info['rows'] <= 0 or info['rows'] % 2 or info['unordered_pairs'] != info['rows']//2
            or info['positive_rows'] != info['rows']//2 or not 0 <= info['zero_difference_rows'] <= info['rows']
            or info['zero_difference_rows'] % 2):
        raise ValueError('strict mirrored training counts required')
    if (any(not arithmetic._number(info[k], nonnegative=True) for k in ('weight_mass', 'maximum_row_squared_norm',
                'weighted_row_squared_norm_sum', 'strong_convexity_lower_bound', 'hessian_spectral_upper_bound'))
            or not math.isclose(info['weight_mass'], MASS, rel_tol=1e-12, abs_tol=1e-12)
            or info['strong_convexity_lower_bound'] != 1.
            or not math.isclose(info['hessian_spectral_upper_bound'], 1.+.25*C*info['weighted_row_squared_norm_sum'], rel_tol=1e-12, abs_tol=1e-12)):
        raise ValueError('invalid mass/curvature certificate')
    hashes = info['input_sha256']
    if (type(hashes) is not dict or set(hashes) != {'features', 'labels', 'weights', 'base_margin'}
            or any(type(v) is not str or re.fullmatch('[0-9a-f]{64}', v) is None for v in hashes.values())):
        raise ValueError('exact array SHA256 inventory required')
    runtime = model['runtime']
    if type(runtime) is not dict or set(runtime) != {'numpy', 'scipy', 'python'} or any(type(v) is not str or not v for v in runtime.values()):
        raise ValueError('exact numerical runtime metadata required')
    if model['model_sha256'] != _model_hash({k: v for k, v in model.items() if k != 'model_sha256'}):
        raise ValueError('residual model checksum mismatch')
    return theta


def score_candidates(model, block, base_scores, *, expected_spec):
    theta = validate_offset(model, expected_spec=expected_spec)
    base = _candidate_inputs(block, base_scores, expected_spec)
    with np.errstate(over='ignore', invalid='ignore'): scores = base+block.matrix@theta
    if not np.isfinite(scores).all(): raise ValueError('nonfinite fixed-offset candidate scores')
    return {cid: float(score) for cid, score in zip(block.candidate_ids, scores)}


def select_candidate(model, block, base_scores, *, expected_spec):
    scores = score_candidates(model, block, base_scores, expected_spec=expected_spec)
    return min(scores, key=lambda cid: (-scores[cid], cid))
