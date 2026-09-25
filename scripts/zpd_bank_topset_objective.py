"""Pure top-set-versus-rest log-mean-exp objective prototype.

For supplied stable candidate scores and highest lexicographic tier T:
  L = mean_t log(1 + mean_n exp(score[n] - score[t])), n in N = rest.
An empty N has zero loss. This is an average of convex log-sum-exp losses,
not logsumexp(all) minus logsumexp(T). It is stronger than top-one success,
does not force equal scores within T, and gives no saturation/generalization
or repair-improvement guarantee.

No I/O, optimizer, source/label selection, scaler, candidate generation or
execution. The caller must authenticate stable-only rows, T and the original
own-training bank masses. Unknown rows are NEVER automatically made negatives.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.special import expit, logsumexp

VERSION = 'bank_topset_rest_logmeanexp_pure_v1'
C = .1
MASS = 1900.
MASS_ATOL = MASS_RTOL = 1e-12  # Original mirrored-weight certificate tolerance.


def _array(value, shape, name):
    if (type(value) is not np.ndarray or value.dtype != np.dtype('float64')
            or value.shape != shape or not np.isfinite(value).all()):
        raise ValueError('finite exact float64 '+name+' with shape '+str(shape)+' required')
    return value


def _finite(value, name):
    if not np.isfinite(value).all():
        raise FloatingPointError('nonfinite '+name+' arithmetic')
    return value


def _frozen(value):
    array = np.ascontiguousarray(value, dtype=np.float64)
    return np.frombuffer(array.tobytes(), dtype=np.float64).reshape(array.shape)


def _top_indices(top_indices, count):
    if (type(top_indices) is not tuple or not top_indices
            or any(type(i) is not int or i < 0 or i >= count for i in top_indices)
            or len(set(top_indices)) != len(top_indices)):
        raise ValueError('nonempty unique exact integer top indices in bank required')
    # Original row order gives a fixed reduction order, without altering scores.
    top = np.asarray(sorted(top_indices), dtype=np.int64)
    selected = set(top_indices)
    rest = np.asarray([i for i in range(count) if i not in selected], dtype=np.int64)
    return top, rest


def _terms(scores, top_indices):
    if type(scores) is not np.ndarray or scores.ndim != 1 or not len(scores):
        raise ValueError('nonempty one-dimensional score array required')
    _array(scores, (len(scores),), 'scores')
    top, rest = _top_indices(top_indices, len(scores))
    if not len(rest):
        return top, rest, None, None, 0., None
    # Do NOT form logmeanexp(scores[N])-scores[T]: a large common score
    # would erase the small log(|N|) correction. Subtract scores first.
    maximum = float(np.max(scores[rest]))
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        centered = scores[rest] - maximum
        normalizer = float(logsumexp(centered))
        probability = np.exp(centered - normalizer)
        margin = (maximum - scores[top]) + (normalizer - math.log(len(rest)))
        losses = np.logaddexp(0., margin)
        active = expit(margin)
        curvature = active*expit(-margin)  # Avoid 1-expit(z) cancellation.
    # -inf margins from finite extreme separation legitimately saturate to0.
    # Unrepresentably large positive loss is refused, never clipped/repaired.
    _finite(probability, 'rest probabilities'); _finite(active, 'top derivatives')
    _finite(losses, 'bank loss')
    loss = math.fsum(map(float, losses))/len(top)
    if not math.isfinite(loss):
        raise FloatingPointError('nonfinite mean bank loss')
    return top, rest, probability, active, loss, curvature


def bank_loss_gradient(scores, top_indices):
    """Return (finite scalar loss, immutable score-gradient), no labels used."""
    top, rest, probability, active, loss, _ = _terms(scores, top_indices)
    gradient = np.zeros(len(scores), dtype=np.float64)
    if len(rest):
        gradient[rest] = probability*(math.fsum(map(float, active))/len(top))
        gradient[top] = -active/len(top)
    return loss, _frozen(_finite(gradient, 'bank gradient'))


def bank_hvp(scores, top_indices, direction):
    """Analytic score-Hessian product; no Hessian matrix or solver is built.

H = mean_t [r_t Cov(q on N) + r_t(1-r_t) (q_N-e_t)(q_N-e_t)^T].
Both terms are PSD. This is an exact-real statement, not a floating-point
certificate or an inference about correctness/education.
"""
    top, rest, probability, active, _, curvature = _terms(scores, top_indices)
    _array(direction, (len(scores),), 'score direction')
    # H annihilates the common-score direction exactly. Remove it BEFORE
    # probability reductions so a large common offset cannot amplify roundoff.
    with np.errstate(over='ignore', invalid='ignore'):
        direction = _finite(direction-direction[0], 'centered score direction')
    result = np.zeros(len(scores), dtype=np.float64)
    if len(rest):
        with np.errstate(over='ignore', under='ignore', invalid='ignore'):
            mean_direction = float(np.dot(probability, direction[rest]))
            dq = probability*(direction[rest]-mean_direction)
            dr = curvature*(mean_direction-direction[top])
            result[rest] = dq*(math.fsum(map(float, active))/len(top)) + probability*(math.fsum(map(float, dr))/len(top))
            result[top] = -dr/len(top)
        _finite(result, 'bank Hessian-vector product')
    return _frozen(result)


@dataclass(frozen=True)
class Bank:
    """Caller-certified stable rows only; no IDs/labels/unknown inference here."""
    features: np.ndarray
    top_indices: tuple[int, ...]

    def __post_init__(self):
        x = self.features
        if type(x) is not np.ndarray or x.ndim != 2 or not all(x.shape):
            raise ValueError('nonempty two-dimensional stable feature matrix required')
        _array(x, x.shape, 'features'); _top_indices(self.top_indices, len(x))
        object.__setattr__(self, 'features', _frozen(x))


def centered_features(bank):
    """Deterministic first-row anchor; raw immutable features remain identity.

Subtract before scores AND coefficient products. Centering only the scores
would still amplify small sum-zero derivative errors by a huge common X.
Finite inputs whose differences overflow are refused, never clipped.
"""
    if type(bank) is not Bank:
        raise ValueError('exact Bank required')
    with np.errstate(over='ignore', invalid='ignore'):
        return _frozen(_finite(bank.features-bank.features[0], 'centered features'))


def _coefficient_inputs(theta, banks, weights):
    if type(theta) is not np.ndarray or theta.ndim != 1 or not len(theta):
        raise ValueError('nonempty coefficient vector required')
    _array(theta, (len(theta),), 'coefficients')
    if type(banks) is not tuple or not banks or any(type(b) is not Bank for b in banks):
        raise ValueError('nonempty explicit tuple of stable Banks required')
    if any(b.features.shape[1] != len(theta) for b in banks):
        raise ValueError('common feature/coefficient dimension required')
    _array(weights, (len(banks),), 'original bank weights')
    if np.any(weights < 0.) or not math.isclose(math.fsum(map(float, weights)), MASS, rel_tol=MASS_RTOL, abs_tol=MASS_ATOL):
        raise ValueError('nonnegative original bank mass summing to1900 required')


@dataclass(frozen=True)
class ObjectiveValue:
    objective: float
    data_loss: float  # Already multiplied by fixed C.
    penalty: float
    gradient: np.ndarray


def coefficient_objective(theta, banks, weights):
    """.5||theta||² + .1 sum W_b L_b and gradient, evaluated without fitting.

W is externally certified sum of each bank's OLD mirrored pair weights.
Mass validation cannot prove that ancestry. Zero-weight rows remain supplied;
no unknown-only bank can be disguised as a stable Bank with a fabricated T.
"""
    _coefficient_inputs(theta, banks, weights)
    gradient = theta.copy(); terms=[]
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        for bank, weight in zip(banks, weights, strict=True):
            x = centered_features(bank)
            scores = _finite(x@theta, 'linear scores')
            loss, ds = bank_loss_gradient(scores, bank.top_indices)
            terms.append(float(C*weight*loss))
            gradient += (C*weight)*(x.T@ds)
        penalty = .5*float(np.dot(theta, theta))
    data_loss = math.fsum(terms); objective = penalty+data_loss
    _finite(np.asarray([data_loss, penalty, objective]), 'coefficient objective')
    return ObjectiveValue(objective, data_loss, penalty, _frozen(_finite(gradient, 'coefficient gradient')))


def coefficient_hvp(theta, banks, weights, direction):
    """v + .1 sum W_b X_b^T H_b X_b v: ridge gives real lower bound1."""
    _coefficient_inputs(theta, banks, weights)
    _array(direction, theta.shape, 'coefficient direction')
    result = direction.copy()
    with np.errstate(over='ignore', under='ignore', invalid='ignore'):
        for bank, weight in zip(banks, weights, strict=True):
            x = centered_features(bank)
            scores = _finite(x@theta, 'linear scores')
            score_direction = _finite(x@direction, 'linear direction')
            hv = bank_hvp(scores, bank.top_indices, score_direction)
            result += (C*weight)*(x.T@hv)
    return _frozen(_finite(result, 'coefficient Hessian-vector product'))


def configuration():
    return dict(version=VERSION, C=C, bank_weight_mass=MASS,
        loss='mean_top_log_1_plus_mean_rest_exp_score_difference',
        empty_rest='exact_zero', top='caller_certified_highest_stable_lexicographic_tier',
        unknown='caller_must_isolate_never_inferred_negative',
        bank_weights='original_own_training_mirrored_pair_mass_by_bank',
        regularization='half_squared_L2_all_coefficients', intercept='not_added',
        coefficient_dimension='explicit_common_positive_dimension',
        derivatives='analytic_gradient_and_Hessian_vector_product',
        coefficient_arithmetic='first_row_centered_features_before_all_scores_and_products',
        fitting_performed=False, empirical_readiness_established=False,
        real_strong_convexity_lower_bound=1., top_one_equivalence_claim=False,
        generalization_or_learning_effect_guarantee=False)
