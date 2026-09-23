"""Fixed-mass development rank/risk fits and first-relative filtering.

Risk scores are learned estimates, not calibrated probabilities or guarantees of
actual non-regression. No generation, execution, validation selection, or file
I/O occurs here. Frozen earlier rankers and their contracts remain unchanged.
"""
from __future__ import annotations

from collections import Counter
import math

import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts.zpd_repair_fit import history
from scripts.zpd_repair_pairwise import (
    HASH_DIMENSION, MODEL_KIND, _raw, numeric_names, preference, score_model, training_data)
from src.repair.pilot_contracts import canonical_hash, source_hash

RISK_KIND = 'first_relative_regression_risk_v1_development_only'
FIXED_C = .1


def _reference(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError('positive finite explicit reference weight required')
    return float(value)


def _fixed_mass(weights, reference):
    reference = _reference(reference)
    weights = np.asarray(weights, dtype=float)
    if (weights.ndim != 1 or not len(weights) or not np.isfinite(weights).all()
            or not (weights > 0).all() or not math.isfinite(float(weights.sum()))):
        raise ValueError('nonempty positive finite sample weights required')
    return weights * (reference / float(weights.sum()))


def train_fixed_ranker(examples, banks, labels, condition, reference_pair_weight):
    """Existing lexical pairwise fit with C=.1 and fixed total pair weight."""
    reference = _reference(reference_pair_weight)
    x, y, weights, scale, metadata = training_data(examples, banks, labels, condition, 'lexical')
    old_mass = float(weights.sum())
    weights = _fixed_mass(weights, reference)
    model = LogisticRegression(C=FIXED_C, fit_intercept=False, solver='liblinear',
                               max_iter=2000, random_state=2027).fit(x, y, sample_weight=weights)
    if max(model.n_iter_) >= 2000 or not np.isfinite(model.coef_).all():
        raise ValueError('fixed ranker did not converge to finite coefficients')
    metadata = dict(metadata, weight_normalization='fixed_reference_total_pair_weight',
                    reference_pair_weight=reference, sample_weight_sum=float(weights.sum()),
                    prior_mean_one_weight_sum=old_mass)
    # Exact old score_model schema; extra provenance stays in training metadata.
    return dict(kind=MODEL_KIND, condition=condition, variant='lexical', C=FIXED_C,
        numeric_names=numeric_names(condition), numeric_scale=scale.tolist(),
        lexical_hash_dimension=HASH_DIMENSION, lexical_alternate_sign=True,
        lexical_normalization='candidate_l2_after_log1p', coefficients=model.coef_[0].tolist(),
        intercept=0., random_state=2027, training=metadata)


def train_risk_model(examples, banks, labels, condition, reference_candidate_weight):
    """Stable train candidates only; target any lost previously passing test."""
    reference = _reference(reference_candidate_weight)
    names = numeric_names(condition)
    if any(ex.split not in ('train', 'valid') for ex in examples):
        raise ValueError('only train and exposed valid are allowed')
    train = [ex for ex in examples if ex.split == 'train']
    if len({ex.example_id for ex in train}) != len(train):
        raise ValueError('duplicate training example')
    records, unknown = [], 0
    for ex in train:
        bank = banks[ex.bank_id]
        numeric, lexical = _raw(ex.observation, history(ex, condition), bank, condition, 'lexical')
        indices, outcomes = [], []
        for index, candidate in enumerate(bank.candidates):
            label = labels[ex.bank_id, candidate.candidate_id]
            if preference(label) is None:  # Also validates unknown null fields.
                unknown += 1
                continue
            indices.append(index)
            outcomes.append(int(label['loss'] > 0))
        if indices:
            records.append((ex, numeric[indices], lexical[indices], outcomes))
    if not records:
        raise ValueError('no stable training candidates for risk fit')
    user_prefixes = Counter(ex.user_id for ex, *_ in records)
    weights = _fixed_mass([1/(user_prefixes[ex.user_id]*len(targets))
                          for ex, _, _, targets in records for _ in targets], reference)
    numeric = sparse.vstack([x for _, x, _, _ in records], format='csr')
    lexical = sparse.vstack([x for _, _, x, _ in records], format='csr')
    targets = np.asarray([target for _, _, _, values in records for target in values], dtype=int)
    scaler = StandardScaler(with_mean=False).fit(numeric, sample_weight=weights)
    x = sparse.hstack([scaler.transform(numeric), lexical], format='csr')
    one_class = len(np.unique(targets)) == 1
    if one_class:
        probability = (float(weights @ targets)+1)/(float(weights.sum())+2)
        coefficients = np.zeros(x.shape[1], dtype=float)
        intercept = math.log(probability/(1-probability))
    else:
        fitted = LogisticRegression(C=FIXED_C, fit_intercept=True, solver='liblinear',
            max_iter=2000, random_state=2027).fit(x, targets, sample_weight=weights)
        if max(fitted.n_iter_) >= 2000:
            raise ValueError('risk solver did not converge')
        coefficients, intercept = fitted.coef_[0], float(fitted.intercept_[0])
    if not np.isfinite(coefficients).all() or not math.isfinite(intercept):
        raise ValueError('risk fit produced non-finite coefficients')
    users = {ex.user_id for ex in train}
    stable_ids = [ex.example_id for ex, *_ in records]
    training = dict(train_prefixes=len(train), train_users=len(users),
        stable_train_prefixes=len(records), stable_train_candidates=len(targets),
        unknown_train_candidates=unknown, users=len(user_prefixes),
        users_without_stable_candidates=len(users-set(user_prefixes)),
        train_example_ids=[ex.example_id for ex in train], stable_train_example_ids=stable_ids,
        excluded_train_example_ids=sorted(set(ex.example_id for ex in train)-set(stable_ids)),
        candidate_example_ids=[ex.example_id for ex, _, _, values in records for _ in values],
        class_counts={'non_regression': int(np.sum(targets == 0)), 'regression': int(np.sum(targets == 1))},
        class_weight_sums={'non_regression': float(weights[targets == 0].sum()),
                          'regression': float(weights[targets == 1].sum())},
        weight_normalization='fixed_reference_total_candidate_weight',
        reference_candidate_weight=reference, sample_weight_sum=float(weights.sum()),
        one_class_laplace_constant=one_class)
    result = dict(kind=RISK_KIND, condition=condition, variant='lexical', C=FIXED_C,
        numeric_names=names, numeric_scale=scaler.scale_.tolist(),
        lexical_hash_dimension=HASH_DIMENSION, lexical_alternate_sign=True,
        lexical_normalization='candidate_l2_after_log1p', coefficients=coefficients.tolist(),
        intercept=intercept, fit_intercept=True, random_state=2027, training=training)
    result['model_sha256'] = canonical_hash(result)
    return result


def _validate_risk_model(model):
    required = {'kind','condition','variant','C','numeric_names','numeric_scale',
        'lexical_hash_dimension','lexical_alternate_sign','lexical_normalization',
        'coefficients','intercept','fit_intercept','random_state','training','model_sha256'}
    if type(model) is not dict or set(model) != required or model['kind'] != RISK_KIND:
        raise ValueError('strict serialized risk model required')
    body = {key:value for key,value in model.items() if key != 'model_sha256'}
    if model['model_sha256'] != canonical_hash(body):
        raise ValueError('risk model canonical hash mismatch')
    names = numeric_names(model['condition'])
    if (model['variant'] != 'lexical' or model['C'] != FIXED_C
            or model['numeric_names'] != names or model['lexical_hash_dimension'] != HASH_DIMENSION
            or model['lexical_alternate_sign'] is not True
            or model['lexical_normalization'] != 'candidate_l2_after_log1p'
            or model['fit_intercept'] is not True or model['random_state'] != 2027):
        raise ValueError('risk model transform mismatch')
    if (type(model['intercept']) not in (int,float) or not math.isfinite(model['intercept'])
            or type(model['numeric_scale']) is not list or type(model['coefficients']) is not list
            or any(type(v) not in (int,float) for v in model['numeric_scale']+model['coefficients'])):
        raise ValueError('invalid risk model numeric values')
    scale, coefficient = np.asarray(model['numeric_scale']), np.asarray(model['coefficients'])
    if (scale.shape != (len(names),) or not np.isfinite(scale).all() or not (scale > 0).all()
            or coefficient.shape != (len(names)+HASH_DIMENSION,) or not np.isfinite(coefficient).all()):
        raise ValueError('invalid risk model dimensions or numeric scale')
    return scale, coefficient


def risk_logits(model, observation, supplied_history, bank):
    """Finite label-free logits; preserve ordering without sigmoid saturation."""
    scale, coefficient = _validate_risk_model(model)
    numeric, lexical = _raw(observation, supplied_history, bank, model['condition'], 'lexical')
    x = sparse.hstack([numeric.multiply(1/scale), lexical], format='csr')
    logits = np.asarray(x @ coefficient).ravel()+model['intercept']
    if not np.isfinite(logits).all():
        raise ValueError('non-finite risk prediction')
    return {candidate.candidate_id:float(value) for candidate,value in zip(bank.candidates,logits)}


def risk_scores(model, observation, supplied_history, bank):
    """Reporting probabilities; use risk_logits for order-sensitive decisions."""
    return {candidate:float(expit(value)) for candidate,value in
            risk_logits(model, observation, supplied_history, bank).items()}


def select_filtered(rank_model, risk_model, observation, supplied_history, bank):
    """Rank within first-relative predicted risk, always retaining baseline/noop.

    The baseline is attempt zero, not the first successful attempt. Failure uses
    exact original code. No-op is an option, not a forced zero predicted risk.
    Finite logits have the same mathematical ordering as sigmoid risk, without
    floating-point saturation merging unequal extreme risks into 0.0 or 1.0.
    """
    if (rank_model['condition'] != risk_model['condition'] or rank_model['C'] != FIXED_C
            or rank_model['variant'] != 'lexical'):
        raise ValueError('matching fixed lexical rank/risk conditions required')
    ranking = score_model(rank_model, observation, supplied_history, bank)
    risk = risk_logits(risk_model, observation, supplied_history, bank)
    noop = source_hash(bank.current_source)
    first = bank.attempts[0]
    baseline = source_hash(first.source) if first.status == 'success' else noop
    eligible = {candidate for candidate in ranking if risk[candidate] <= risk[baseline]}
    eligible.update((baseline, noop))
    return min(eligible, key=lambda candidate:(-ranking[candidate],candidate))
