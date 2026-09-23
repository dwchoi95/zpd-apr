"""Capacity-matched ordered-structure development ranker.

Only the representation changes: both variants retain the frozen numeric C/H/U
features and 4,096 signed-hash columns, candidate-wise L2 normalization, stable
pair preferences, equal-user/prefix/pair weighting, and total pair weight 1,900.
The lexical control delegates to the prior training-data implementation exactly.
The structural variant adds syntax-derived ordered features in the *same* hash
space. This is not a semantic equivalence analysis or a learner-benefit model.

No candidate is executed, normalized, truncated, or discarded by this module.
Parsing failures retain all byte tokens through an ordered n-gram fallback.
Prediction is label-blind and never fits a vocabulary or transformer.
"""
from __future__ import annotations

import ast
from collections import Counter
from functools import lru_cache
from itertools import combinations
import math
import re

import numpy as np
from scipy import sparse
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, normalize

from scripts.zpd_repair_fit import history
from scripts.zpd_repair_pairwise import (
    HASH_DIMENSION, _raw as lexical_raw, lexical_features, numeric_names,
    preference, training_data as lexical_training_data)
from src.repair.pilot_contracts import canonical_hash

MODEL_KIND = 'ordered_structure_pairwise_ranker_v1_train_only_development'
VARIANTS = ('lexical', 'structural')
FIXED_C = .1
REFERENCE_PAIR_WEIGHT = 1900.
AST_FEATURE_VERSION = (3, 10)
TRAINING_FIELDS = frozenset({
    'train_prefixes', 'train_users', 'informative_train_prefixes', 'uninformative_train_prefixes',
    'users', 'users_without_informative_prefix', 'ordered_pairs', 'pair_example_ids',
    'informative_train_example_ids', 'uninformative_train_example_ids', 'stable_train_candidates',
    'weight_normalization', 'reference_pair_weight', 'sample_weight_sum', 'prior_mean_one_weight_sum'})


def _configuration(variant):
    if variant not in VARIANTS:
        raise ValueError('variant must be lexical or structural')
    return dict(hash_dimension=HASH_DIMENSION, alternate_sign=True,
        normalization='candidate_l2_after_log1p', lexical='existing_byte_bags_v1',
        structure='ordered_ast_and_byte_fallback_v1' if variant == 'structural' else None,
        ast_feature_version=list(AST_FEATURE_VERSION) if variant == 'structural' else None,
        fallback_ngram_lengths=[2, 3] if variant == 'structural' else [],
        solver='liblinear', max_iter=2000, fit_intercept=False, random_state=2027,
        reference_pair_weight=REFERENCE_PAIR_WEIGHT)


def _reference(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value != REFERENCE_PAIR_WEIGHT:
        raise ValueError('frozen reference pair weight must be 1900')
    return float(value)


def _local_kind(node):
    """Bounded local operation signature, without identifiers or literal data."""
    kind = type(node).__name__
    if isinstance(node, (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.AugAssign)):
        return kind + ':' + type(node.op).__name__
    if isinstance(node, ast.Compare):
        return kind + ':' + ','.join(type(op).__name__ for op in node.ops)
    return kind


def _signature(node):
    signature = _local_kind(node)
    # Preserve statement-local control/value operations in adjacency features.
    for field in ('test', 'value', 'iter'):
        child = getattr(node, field, None)
        if isinstance(child, ast.AST):
            signature += '|' + field + '=' + _local_kind(child)
    return signature


def _fallback_counts(source):
    # LF/CR are retained as tokens. Hex boundaries make arbitrary bytes safe and
    # unambiguous; no UTF-8 replacement, error text, source IDs, or paths enter.
    tokens = ['BOS'] + [token.hex() for token in
        re.findall(rb'[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[\r\n]|[^\s]', source)] + ['EOS']
    counts = Counter({'parse:byte_fallback': 1})
    for length in (2, 3):
        counts.update('fallback:' + str(length) + ':' + ':'.join(tokens[i:i+length])
                      for i in range(len(tokens)-length+1))
    return counts


@lru_cache(maxsize=4096)
def _structural_items(source):
    """Immutable cache entries avoid both repeated parsing and caller mutation."""
    if type(source) is not bytes:
        raise TypeError('exact source bytes required')
    try:
        tree = ast.parse(source, mode='exec', feature_version=AST_FEATURE_VERSION)
    except (SyntaxError, ValueError, UnicodeError, LookupError, RecursionError):
        return tuple(sorted(_fallback_counts(source).items()))
    counts = Counter({'parse:ast': 1})
    pending = [tree]
    while pending:
        node = pending.pop()
        parent = type(node).__name__
        counts['node:' + _signature(node)] += 1
        for field, value in ast.iter_fields(node):
            if isinstance(value, ast.AST):
                counts['field:' + parent + '.' + field + '=>' + _signature(value)] += 1
                pending.append(value)
            elif isinstance(value, list):
                children = [(index, child) for index, child in enumerate(value)
                            if isinstance(child, ast.AST)]
                for index, child in children:
                    counts['field:' + parent + '.' + field + '[' + str(index) + ']=>'
                           + _signature(child)] += 1
                    pending.append(child)
                # All list children retain order, not only statement lists.
                for (_, left), (_, right) in zip(children, children[1:]):
                    counts['adjacent:' + parent + '.' + field + ':'
                           + _signature(left) + '=>' + _signature(right)] += 1
    return tuple(sorted(counts.items()))


def structure_counts(source):
    """Source-only structural counts for diagnostics; a fresh mutable copy."""
    return Counter(dict(_structural_items(source)))


def structural_features(current, candidate):
    """Existing lexical bags plus ordered candidate/add/remove structural bags.

    Features depend only on the two exact byte strings, not observations, IDs,
    verdicts, problem metadata, labels, or file paths. Hashed features can still
    collide; exposing ordering does not guarantee correct repair selection.
    """
    result = lexical_features(current, candidate)
    before, after = structure_counts(current), structure_counts(candidate)
    for prefix, counts in (('candidate', after), ('add', after-before), ('remove', before-after)):
        result.update({'structure:' + prefix + ':' + name: math.log1p(count)
                       for name, count in counts.items()})
    return result


def raw_features(observation, supplied_history, bank, condition, variant):
    """Same numeric/history contracts and column counts for both variants."""
    _configuration(variant)
    numeric, lexical = lexical_raw(observation, supplied_history, bank, condition, 'lexical')
    if variant == 'lexical':
        return numeric, lexical
    bags = [structural_features(bank.current_source, candidate.source) for candidate in bank.candidates]
    hashed = FeatureHasher(n_features=HASH_DIMENSION, input_type='dict', alternate_sign=True).transform(bags)
    return numeric, normalize(hashed, norm='l2', axis=1, copy=False)


def _structural_training_data(examples, banks, labels, condition):
    """Frozen pairwise weighting/scaling algorithm with structure-only swap."""
    numeric_names(condition)
    if any(ex.split not in ('train', 'valid') for ex in examples):
        raise ValueError('only train and exposed valid are allowed')
    train = [ex for ex in examples if ex.split == 'train']
    if len({ex.example_id for ex in train}) != len(train):
        raise ValueError('duplicate training example')
    records = []
    for ex in train:
        bank = banks[ex.bank_id]
        numeric, hashed = raw_features(ex.observation, history(ex, condition), bank, condition, 'structural')
        ranked = [(i, preference(labels[ex.bank_id, c.candidate_id])) for i, c in enumerate(bank.candidates)]
        stable = [i for i, key in ranked if key is not None]
        keys = dict(ranked)
        pairs = [(a, b, int(keys[a] > keys[b])) for a, b in combinations(stable, 2) if keys[a] != keys[b]]
        if pairs:
            records.append((ex, numeric, hashed, stable, pairs))
    if not records:
        raise ValueError('no unequal stable training candidate pairs')
    prefixes = Counter(ex.user_id for ex, *_ in records)
    numeric = sparse.vstack([x[stable] for _, x, _, stable, _ in records], format='csr')
    candidate_weights = np.array([1/(prefixes[ex.user_id]*len(stable))
                                 for ex, _, _, stable, _ in records for _ in stable])
    scaler = StandardScaler(with_mean=False).fit(numeric, sample_weight=candidate_weights)
    matrices, outcomes, weights, pair_examples = [], [], [], []
    for ex, raw, hashed, _, pairs in records:
        x = sparse.hstack([scaler.transform(raw), hashed], format='csr')
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


def training_data(examples, banks, labels, condition, variant, reference_pair_weight=REFERENCE_PAIR_WEIGHT):
    """Train-only mirrored pairs, frozen scaler, and fixed-total sample weights."""
    reference = _reference(reference_pair_weight)
    _configuration(variant)
    if variant == 'lexical':
        x, y, weights, scale, metadata = lexical_training_data(examples, banks, labels, condition, 'lexical')
    else:
        x, y, weights, scale, metadata = _structural_training_data(examples, banks, labels, condition)
    old_mass = float(weights.sum())
    weights = weights * (reference / old_mass)
    metadata = dict(metadata, weight_normalization='fixed_reference_total_pair_weight',
        reference_pair_weight=reference, sample_weight_sum=float(weights.sum()),
        prior_mean_one_weight_sum=old_mass)
    return x, y, weights, scale, metadata


def train_model(examples, banks, labels, condition, variant, reference_pair_weight=REFERENCE_PAIR_WEIGHT):
    x, y, weights, scale, metadata = training_data(examples, banks, labels, condition, variant, reference_pair_weight)
    fitted = LogisticRegression(C=FIXED_C, fit_intercept=False, solver='liblinear',
        max_iter=2000, random_state=2027).fit(x, y, sample_weight=weights)
    if max(fitted.n_iter_) >= 2000 or not np.isfinite(fitted.coef_).all():
        raise ValueError('structure/control ranker did not converge to finite coefficients')
    model = dict(kind=MODEL_KIND, condition=condition, variant=variant, C=FIXED_C,
        numeric_names=numeric_names(condition), numeric_scale=scale.tolist(),
        feature_config=_configuration(variant), coefficients=fitted.coef_[0].tolist(),
        intercept=0., training=metadata)
    model['model_sha256'] = canonical_hash(model)
    return model


def _validate_model(model):
    required = {'kind', 'condition', 'variant', 'C', 'numeric_names', 'numeric_scale',
                'feature_config', 'coefficients', 'intercept', 'training', 'model_sha256'}
    if type(model) is not dict or set(model) != required or model['kind'] != MODEL_KIND:
        raise ValueError('strict serialized structure/control model required')
    body = {key: value for key, value in model.items() if key != 'model_sha256'}
    try:
        bound = canonical_hash(body)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError('invalid serialized model values') from error
    if model['model_sha256'] != bound:
        raise ValueError('model canonical hash mismatch')
    names = numeric_names(model['condition'])
    if (model['numeric_names'] != names or type(model['C']) not in (int, float) or model['C'] != FIXED_C
            or canonical_hash(model['feature_config']) != canonical_hash(_configuration(model['variant']))
            or type(model['intercept']) not in (int, float) or model['intercept'] != 0.):
        raise ValueError('model fixed feature/fit configuration mismatch')
    if (type(model['numeric_scale']) is not list or type(model['coefficients']) is not list
            or any(type(value) not in (int, float) for value in model['numeric_scale']+model['coefficients'])):
        raise ValueError('invalid model numeric values')
    scale, coefficient = np.asarray(model['numeric_scale']), np.asarray(model['coefficients'])
    if (scale.shape != (len(names),) or not np.isfinite(scale).all() or not (scale > 0).all()
            or coefficient.shape != (len(names)+HASH_DIMENSION,) or not np.isfinite(coefficient).all()):
        raise ValueError('invalid model dimensions or numeric scale')
    training = model['training']
    if (type(training) is not dict or set(training) != TRAINING_FIELDS
            or training.get('weight_normalization') != 'fixed_reference_total_pair_weight'
            or type(training.get('reference_pair_weight')) not in (int, float)
            or training['reference_pair_weight'] != REFERENCE_PAIR_WEIGHT
            or type(training.get('sample_weight_sum')) not in (int, float)
            or not math.isclose(training['sample_weight_sum'], REFERENCE_PAIR_WEIGHT, rel_tol=1e-12)):
        raise ValueError('model fixed training weight mismatch')
    count_fields = ('train_prefixes', 'train_users', 'informative_train_prefixes',
        'uninformative_train_prefixes', 'users', 'users_without_informative_prefix',
        'ordered_pairs', 'stable_train_candidates')
    if (any(type(training[key]) is not int or training[key] < 0 for key in count_fields)
            or any(type(training[key]) is not list or any(type(value) is not str for value in training[key])
                   for key in ('pair_example_ids', 'informative_train_example_ids', 'uninformative_train_example_ids'))
            or training['ordered_pairs'] <= 0 or training['ordered_pairs'] % 2
            or len(training['pair_example_ids']) != training['ordered_pairs']
            or len(training['informative_train_example_ids']) != training['informative_train_prefixes']
            or len(training['uninformative_train_example_ids']) != training['uninformative_train_prefixes']
            or training['train_prefixes'] != training['informative_train_prefixes'] + training['uninformative_train_prefixes']
            or type(training['prior_mean_one_weight_sum']) not in (int, float)
            or not math.isclose(training['prior_mean_one_weight_sum'], training['ordered_pairs'], rel_tol=1e-12)):
        raise ValueError('model training metadata mismatch')
    return scale, coefficient


def score_model(model, observation, supplied_history, bank):
    """Label-blind scoring with only the serialized training numeric scale."""
    scale, coefficient = _validate_model(model)
    numeric, hashed = raw_features(observation, supplied_history, bank, model['condition'], model['variant'])
    x = sparse.hstack([numeric.multiply(1/scale), hashed], format='csr')
    scores = np.asarray(x @ coefficient).ravel()
    if not np.isfinite(scores).all():
        raise ValueError('non-finite candidate scores')
    return {candidate.candidate_id: float(value) for candidate, value in zip(bank.candidates, scores)}


def select_model(model, observation, supplied_history, bank):
    scores = score_model(model, observation, supplied_history, bank)
    return min(scores, key=lambda candidate: (-scores[candidate], candidate))
