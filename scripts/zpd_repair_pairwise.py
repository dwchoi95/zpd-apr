"""Train-only pairwise repair ranking; exposed validation is development only.

This module neither generates nor executes candidate code. Prediction accepts no
execution labels and never fits a transformer. All history transitions reach the
existing history/candidate feature extractor without truncation. Lexical bags are
lossy representations, not semantic or pedagogical evidence.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
import math
import re

import numpy as np
from scipy import sparse
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, normalize

from scripts.zpd_repair_fit import evaluate, history
from src.repair.pilot_contracts import CandidateBank, PilotObservation, canonical_hash, source_hash
from src.repair.pilot_ranker import features

CONDITIONS = ('C', 'H', 'U')
VARIANTS = ('compact', 'lexical')
REGULARIZATIONS = (.1, 1., 10.)
HASH_DIMENSION = 4096
MODEL_KIND = 'pairwise_repair_ranker_v1_development_only'


def numeric_names(condition):
    if condition not in CONDITIONS:
        raise ValueError('condition must be C, H, or U')
    names = ['candidate_byte_length_delta', 'candidate_edit_tokens', 'candidate_is_noop']
    if condition != 'C':
        names += ['history_candidate_exact_fraction', 'history_candidate_reversion_weight',
                  'history_count', 'history_edit_overlap', 'history_reverse_edit_overlap']
    return sorted(names)


def _tokens(source):
    if type(source) is not bytes:
        raise TypeError('exact source bytes required')
    return Counter(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]', source))


def lexical_features(current, candidate):
    """Unambiguous hex-encoded byte tokens; separate candidate/add/remove bags.

    Counts are log1p-transformed before signed hashing and candidate-wise L2
    normalization. No cross-product vocabulary or data-derived vocabulary exists.
    """
    before, after = _tokens(current), _tokens(candidate)
    return {prefix + ':' + token.hex(): math.log1p(count)
            for prefix, counts in [('candidate', after), ('add', after-before), ('remove', before-after)]
            for token, count in counts.items()}


def _history(condition, observation, supplied):
    if condition == 'C' and supplied != ():
        raise ValueError('C must receive empty history')
    if condition == 'H' and supplied != observation.prior:
        raise ValueError('H must receive exact authentic prior history')
    # Donor matching/authenticity is checked by the input manifest, not inferred.
    return supplied


def _raw(observation, supplied, bank, condition, variant):
    if type(observation) is not PilotObservation or type(bank) is not CandidateBank:
        raise TypeError('strict observation and candidate-bank contracts required')
    if bank.problem_id != observation.problem_id or bank.current_source != observation.current.source:
        raise ValueError('observation-bank mismatch')
    if variant not in VARIANTS:
        raise ValueError('unknown feature variant')
    names = numeric_names(condition)
    supplied = _history(condition, observation, supplied)
    candidates = bank.candidates
    values = [features(observation, candidate.source, history=supplied) for candidate in candidates]
    numeric = sparse.csr_matrix([[row[name] for name in names] for row in values], dtype=float)
    lexical = None
    if variant == 'lexical':
        bags = [lexical_features(bank.current_source, candidate.source) for candidate in candidates]
        lexical = FeatureHasher(n_features=HASH_DIMENSION, input_type='dict', alternate_sign=True).transform(bags)
        lexical = normalize(lexical, norm='l2', axis=1, copy=False)
    return numeric, lexical


def preference(label):
    """Stable-only lexicographic correctness, non-regression, then net gain."""
    if label['status'] == 'unknown':
        if any(label[k] is not None for k in ('gain', 'loss', 'all_ac')):
            raise ValueError('unknown preference evidence must remain null')
        return None
    if label['status'] != 'stable':
        raise ValueError('unknown execution evidence status')
    if type(label['all_ac']) is not bool or any(
            type(label[k]) not in (int, float) or not math.isfinite(label[k]) or not 0 <= label[k] <= 1
            for k in ('gain', 'loss')) or label['gain'] + label['loss'] > 1 + 1e-12:
        raise ValueError('stable preference requires finite normalized execution evidence')
    if label['all_ac'] and label['loss'] != 0:
        raise ValueError('all-AC candidate cannot lose a previously passing testcase')
    return (int(label['all_ac']), int(label['loss'] == 0), label['gain']-label['loss'])


def training_data(examples, banks, labels, condition, variant):
    """Freeze train-only transform and mirrored unequal-candidate preferences.

    Scales use stable training candidates in informative prefixes, weighted
    equally by user, prefix, candidate. Pair loss uses equal-user/prefix/pair
    weights normalized to mean one. Uninformative prefixes are documented and
    excluded: they cannot supply a pairwise preference. No validation label is
    accessed by this function.
    """
    numeric_names(condition)
    if variant not in VARIANTS:
        raise ValueError('unknown feature variant')
    records = []
    train = [ex for ex in examples if ex.split == 'train']
    if any(ex.split not in ('train', 'valid') for ex in examples):
        raise ValueError('only train and exposed valid are allowed')
    if len({ex.example_id for ex in train}) != len(train):
        raise ValueError('duplicate training example')
    for ex in train:
        bank = banks[ex.bank_id]
        numeric, lexical = _raw(ex.observation, history(ex, condition), bank, condition, variant)
        ranked = [(i, preference(labels[ex.bank_id, c.candidate_id])) for i, c in enumerate(bank.candidates)]
        stable = [i for i, key in ranked if key is not None]
        keys = dict(ranked)
        pairs = [(a, b, int(keys[a] > keys[b])) for a, b in combinations(stable, 2) if keys[a] != keys[b]]
        if pairs:
            records.append((ex, numeric, lexical, stable, pairs))
    if not records:
        raise ValueError('no unequal stable training candidate pairs')
    prefixes = Counter(ex.user_id for ex, *_ in records)
    numeric = sparse.vstack([x[stable] for _, x, _, stable, _ in records], format='csr')
    candidate_weights = np.array([1/(prefixes[ex.user_id]*len(stable))
                                 for ex, _, _, stable, _ in records for _ in stable])
    scaler = StandardScaler(with_mean=False).fit(numeric, sample_weight=candidate_weights)
    matrices, outcomes, weights, pair_examples = [], [], [], []
    for ex, raw, lexical, _, pairs in records:
        x = scaler.transform(raw)
        if lexical is not None:
            x = sparse.hstack([x, lexical], format='csr')
        for a, b, target in pairs:
            difference = x[a] - x[b]
            matrices.extend((difference, -difference))
            outcomes.extend((target, 1-target))
            weights.extend([1/(prefixes[ex.user_id]*len(pairs)*2)]*2)
            pair_examples.extend([ex.example_id]*2)
    weights = np.asarray(weights)
    weights *= len(weights)/weights.sum()
    all_users = {ex.user_id for ex in train}
    metadata = dict(train_prefixes=len(train), train_users=len(all_users), informative_train_prefixes=len(records),
                    uninformative_train_prefixes=len(train)-len(records), users=len(prefixes),
                    users_without_informative_prefix=len(all_users-set(prefixes)),
                    ordered_pairs=len(weights), pair_example_ids=pair_examples,
                    informative_train_example_ids=[ex.example_id for ex, *_ in records],
                    uninformative_train_example_ids=sorted(set(ex.example_id for ex in train)
                        - set(ex.example_id for ex, *_ in records)),
                    stable_train_candidates=sum(len(stable) for _, _, _, stable, _ in records))
    return sparse.vstack(matrices, format='csr'), np.array(outcomes), weights, scaler.scale_, metadata


def train_model(examples, banks, labels, condition, variant, C):
    if C not in REGULARIZATIONS:
        raise ValueError('C outside frozen grid')
    x, y, weights, scale, metadata = training_data(examples, banks, labels, condition, variant)
    fitted = LogisticRegression(C=C, fit_intercept=False, solver='liblinear',
                                max_iter=2000, random_state=2027).fit(x, y, sample_weight=weights)
    if max(fitted.n_iter_) >= 2000:
        raise ValueError('pairwise solver did not converge')
    if not np.isfinite(fitted.coef_).all():
        raise ValueError('non-finite fitted coefficients')
    return dict(kind=MODEL_KIND, condition=condition, variant=variant, C=float(C),
                numeric_names=numeric_names(condition), numeric_scale=scale.tolist(),
                lexical_hash_dimension=HASH_DIMENSION if variant == 'lexical' else 0,
                lexical_alternate_sign=True, lexical_normalization='candidate_l2_after_log1p',
                coefficients=fitted.coef_[0].tolist(), intercept=0., random_state=2027,
                training=metadata)


def _validate_model(model):
    required = {'kind', 'condition', 'variant', 'C', 'numeric_names', 'numeric_scale',
                'lexical_hash_dimension', 'lexical_alternate_sign', 'lexical_normalization',
                'coefficients', 'intercept', 'random_state', 'training'}
    if set(model) != required or model['kind'] != MODEL_KIND:
        raise ValueError('strict serialized pairwise model required')
    names = numeric_names(model['condition'])
    variant = model['variant']
    if variant not in VARIANTS or model['numeric_names'] != names or model['C'] not in REGULARIZATIONS:
        raise ValueError('model feature configuration mismatch')
    dimension = HASH_DIMENSION if variant == 'lexical' else 0
    if model['lexical_hash_dimension'] != dimension or model['lexical_alternate_sign'] is not True or model['lexical_normalization'] != 'candidate_l2_after_log1p' or model['intercept'] != 0 or model['random_state'] != 2027:
        raise ValueError('model transform mismatch')
    scale = np.asarray(model['numeric_scale'], dtype=float)
    coef = np.asarray(model['coefficients'], dtype=float)
    if scale.shape != (len(names),) or not np.isfinite(scale).all() or not (scale > 0).all() or coef.shape != (len(names)+dimension,) or not np.isfinite(coef).all():
        raise ValueError('invalid model coefficients or numeric scale')
    return scale, coef


def score_model(model, observation, supplied_history, bank):
    """Label-blind serialized prediction; no fit and no execution calls."""
    scale, coefficient = _validate_model(model)
    numeric, lexical = _raw(observation, supplied_history, bank, model['condition'], model['variant'])
    x = numeric.multiply(1/scale).tocsr()
    if lexical is not None:
        x = sparse.hstack([x, lexical], format='csr')
    scores = np.asarray(x @ coefficient).ravel()
    if not np.isfinite(scores).all():
        raise ValueError('non-finite candidate scores')
    return {candidate.candidate_id: float(value) for candidate, value in zip(bank.candidates, scores)}


def select_model(model, observation, supplied_history, bank):
    scores = score_model(model, observation, supplied_history, bank)
    return min(scores, key=lambda candidate: (-scores[candidate], candidate))


def selection_key(cell):
    m = cell['metrics']
    return (m['rr_lower_bound'], -m['regression_rate_upper_bound'], m['utility'],
            int(cell['variant'] == 'compact'), -cell['C'])


def fit_report(examples, banks, labels):
    """18 fits, original train only; every original-valid grid cell retained."""
    if {ex.split for ex in examples} != {'train', 'valid'}:
        raise ValueError('nonempty original train and valid required')
    report = dict(kind='pairwise_exposed_validation_development_only', confirmatory=False,
                  fresh_test_opened=False, grid=[], selected={}, baselines={},
                  selection_rule='RR lower bound desc; regression upper bound asc; net utility desc; compact; lower C',
                  note='Train/validation development only; improvements are not held-out scientific evidence.')
    for condition in CONDITIONS:
        cells = []
        for variant in VARIANTS:
            for C in REGULARIZATIONS:
                model = train_model(examples, banks, labels, condition, variant, C)
                candidate_scores = []
                def choose(ex, bank):
                    scores = score_model(model, ex.observation, history(ex, condition), bank)
                    candidate_scores.append(dict(example_id=ex.example_id, bank_id=ex.bank_id, scores=scores))
                    return min(scores, key=lambda candidate: (-scores[candidate], candidate))
                evaluation = evaluate(examples, banks, labels, choose)
                cell = dict(condition=condition, variant=variant, C=C, model=model,
                            model_sha256=canonical_hash(model), validation_candidate_scores=candidate_scores,
                            **evaluation)
                cells.append(cell)
                report['grid'].append(cell)
        report['selected'][condition] = max(cells, key=selection_key)
    def first(ex, bank):
        attempt = bank.attempts[0]
        return source_hash(attempt.source if attempt.status == 'success' else bank.current_source)
    report['baselines']['first_attempt'] = evaluate(examples, banks, labels, first)
    report['baselines']['noop'] = evaluate(examples, banks, labels, lambda ex, bank: source_hash(bank.current_source))
    return report
