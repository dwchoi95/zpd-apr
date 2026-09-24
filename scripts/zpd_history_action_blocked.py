"""C2 observation-only block representation and fixed, strictly sealed heads.

The frozen semantic encoder is unchanged. Current columns exactly retain C1 C0;
four recipient nuisances and full-history state cannot collide with or renorm
those columns. No fitted transform, target access or history restriction.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import normalize

from scripts import run_zpd_history_action_cv as legacy
from scripts import zpd_history_action_encoder as semantic

VERSION = 'current_preserving_blocks_v1'
CURRENT_DIMENSION = HISTORY_DIMENSION = 4096
FEATURE_DIMENSION = 8196
CURRENT_SLICE = slice(0, 4096)
NUISANCE_SLICE = slice(4096, 4100)
HISTORY_SLICE = slice(4100, 8196)
ARMS = ('C0', 'Cn', 'H', 'U', 'HS', 'L')
SEED, EPOCHS, ALPHA = 2027, 20, 1e-4
WEIGHTING = 'user_equal_prefix_mean_event_mask_no_head_renormalization'


def configuration():
    return dict(version=VERSION, feature_dimension=FEATURE_DIMENSION,
        current=dict(offset=0, dimension=4096, hashing='FeatureHasher_dict_float64_alternate_sign', normalization='row_L2'),
        nuisance=dict(offset=4096, dimension=4, keys=list(semantic.NUISANCE_KEYS), normalization='v_over_sqrt_1_plus_squared_L2'),
        history=dict(offset=4100, dimension=4096, hashing='FeatureHasher_dict_float64_alternate_sign', normalization='v_over_sqrt_1_plus_squared_L2'),
        final_normalization=False, semantic_encoder_version=semantic.ENCODER_VERSION)


def _identical_configuration(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(_identical_configuration(actual[k],v) for k,v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_identical_configuration(a,b) for a,b in zip(actual,expected))
    return actual == expected


def radial(matrix):
    """R(v)=v/sqrt(1+||v||²), with stable scaling for extreme finite inputs."""
    result = sparse.csr_matrix(matrix, dtype=np.float64, copy=True)
    result.sum_duplicates(); result.eliminate_zeros(); result.sort_indices()
    if not np.isfinite(result.data).all():
        raise ValueError('finite block required')
    for row in range(result.shape[0]):
        values = result.data[result.indptr[row]:result.indptr[row+1]]
        if not len(values):
            continue
        maximum = float(np.abs(values).max())
        if maximum >= 1.:
            values /= maximum
            values /= math.hypot(1./maximum, float(np.linalg.norm(values)))
        else:
            values /= math.sqrt(1. + float(values @ values))
    return result


def transform_bags(bags, arm):
    if arm not in ARMS:
        raise ValueError('unknown blocked arm')
    current, nuisance, history = [], [], []
    required = set(semantic.NUISANCE_KEYS)
    for bag in bags:
        if type(bag) is not dict or any(type(k) is not str or type(v) not in (int, float)
                or not math.isfinite(v) for k, v in bag.items()):
            raise ValueError('finite feature dictionary required')
        if any(not k.startswith(('current:', 'nuisance:', 'history:')) for k in bag):
            raise ValueError('unknown feature namespace')
        c = {k:v for k,v in bag.items() if k.startswith('current:')}
        n = {k:v for k,v in bag.items() if k.startswith('nuisance:')}
        h = {k:v for k,v in bag.items() if k.startswith('history:')}
        if not c or (arm == 'C0' and (n or h)) or (arm != 'C0' and set(n) != required):
            raise ValueError('exact current/nuisance arm contract required')
        if arm == 'Cn' and h:
            raise ValueError('Cn may not contain history state')
        if any(v < 0 for v in n.values()):
            raise ValueError('nonnegative authentic log nuisances required')
        current.append(c); nuisance.append([n.get(k, 0.) for k in semantic.NUISANCE_KEYS]); history.append(h)
    if not current:
        return sparse.csr_matrix((0, FEATURE_DIMENSION), dtype=np.float64)
    hasher = FeatureHasher(n_features=4096, input_type='dict', alternate_sign=True, dtype=np.float64)
    c = hasher.transform(current)
    if not np.isfinite(c.data).all():
        raise ValueError('nonfinite current hash sum')
    c = normalize(c, norm='l2', axis=1, copy=False)
    n = radial(sparse.csr_matrix(np.asarray(nuisance, dtype=np.float64)))
    h = radial(hasher.transform(history))
    result = sparse.hstack((c,n,h), format='csr')
    if result.shape != (len(bags), FEATURE_DIMENSION) or not np.isfinite(result.data).all():
        raise ValueError('invalid blocked matrix')
    return result


def encode_matrix(observations, indices, arm, encoder=semantic, *, donors=None, callback=None):
    if arm not in ARMS:
        raise ValueError('unknown blocked arm')
    indexed = {o['example_id']:o for o in observations}
    blocks, bags = [], []
    for done, i in enumerate(indices, 1):
        o = observations[int(i)]
        args = (o['current_code'], o['current_verdict'], o['history'], o['timestamp'])
        if arm in ('U', 'L'):
            if arm == 'U':
                if donors is None or donors.get(o['example_id']) not in indexed:
                    raise ValueError('U requires matched donor')
                history = indexed[donors[o['example_id']]]['history']
            else:
                history = o['history'][-1:]
            bag = encoder.encode_observation(o['current_code'], o['current_verdict'], history, o['timestamp'], 'H')
            bag.update(encoder.encode_observation(*args, 'Cn'))
        else:
            bag = encoder.encode_observation(*args, arm, shuffle_key=o['example_id'])
        bags.append(bag)
        if len(bags) == 1000 or done == len(indices):
            blocks.append(transform_bags(bags, arm)); bags = []
            if callback:
                callback(dict(phase='encoding_observations', arm=arm, completed_examples=done, total_examples=len(indices)))
    return sparse.vstack(blocks, format='csr') if blocks else sparse.csr_matrix((0, FEATURE_DIMENSION))


def fit_heads(x, y, mask, users, events, *, callback=None):
    if (x.shape != (len(users), FEATURE_DIMENSION) or y.shape != mask.shape
            or y.shape != (len(users),len(events)) or list(events) != list(semantic.EVENTS)
            or mask.dtype != bool or not np.isfinite(x.data).all()
            or not np.isfinite(y).all() or not np.isin(y[mask], [0.,1.]).all()):
        raise ValueError('strict fixed blocked head input required')
    weights = legacy.label_weights(users, mask); heads = []
    for event, name in enumerate(events):
        chosen = np.flatnonzero(mask[:,event]); yy, ww = y[chosen,event], weights[chosen]
        metadata = dict(event=name, observed_prefixes=len(chosen), observed_users=len(set(users[i] for i in chosen)),
            positive_prefixes=int(yy.sum()), total_weight=float(ww.sum()), positive_weight=float(ww @ yy))
        if not len(chosen) or len(np.unique(yy)) == 1:
            heads.append(dict(kind='laplace_constant', probability=(float(ww @ yy)+1.)/(float(ww.sum())+2.), **metadata))
            if callback:
                callback(dict(phase='head_complete', event=name, training='constant', completed_train_prefix_event_exposures=0))
            continue
        xx = x[chosen]
        fitted = SGDClassifier(loss='log_loss', penalty='l2', alpha=ALPHA,
            learning_rate='optimal', shuffle=False, random_state=SEED, average=False)
        rng = np.random.default_rng(SEED)
        for epoch in range(EPOCHS):
            order = rng.permutation(len(chosen))
            fitted.partial_fit(xx[order], yy[order], classes=np.array([0.,1.]), sample_weight=ww[order])
            if callback:
                callback(dict(phase='training', event=name, epoch=epoch+1, epochs=EPOCHS,
                    completed_train_prefix_event_exposures=(epoch+1)*len(chosen),
                    total_train_prefix_event_exposures=EPOCHS*len(chosen), unique_train_prefixes=len(chosen)))
        heads.append(dict(kind='linear_logistic', coefficients=fitted.coef_[0].tolist(),
                          intercept=float(fitted.intercept_[0]), **metadata))
    model = dict(events=list(events), feature_dimension=FEATURE_DIMENSION, representation=configuration(),
        alpha=ALPHA, seed=SEED, epochs=EPOCHS, weighting=WEIGHTING, heads=heads)
    validate_model(model)
    return model


def validate_model(model):
    expected = {'events','feature_dimension','representation','alpha','seed','epochs','weighting','heads'}
    annotated = {'arm','fold','train_example_ids'}
    if type(model) is not dict or set(model) not in (expected, expected | annotated):
        raise ValueError('exact model schema required')
    if (model['events'] != list(semantic.EVENTS) or model['feature_dimension'] != FEATURE_DIMENSION
            or not _identical_configuration(model['representation'],configuration()) or model['alpha'] != ALPHA
            or model['seed'] != SEED or model['epochs'] != EPOCHS or model['weighting'] != WEIGHTING
            or type(model['heads']) is not list or len(model['heads']) != len(semantic.EVENTS)):
        raise ValueError('fixed blocked model configuration mismatch')
    if annotated <= set(model) and (model['arm'] not in ARMS or type(model['fold']) is not int
            or model['fold'] not in range(5) or type(model['train_example_ids']) is not list
            or any(type(i) is not str for i in model['train_example_ids'])
            or len(set(model['train_example_ids'])) != len(model['train_example_ids'])):
        raise ValueError('invalid model cohort annotation')
    common = {'event','kind','observed_prefixes','observed_users','positive_prefixes','total_weight','positive_weight'}
    for event, head in zip(semantic.EVENTS, model['heads']):
        if type(head) is not dict or head.get('event') != event:
            raise ValueError('event head mismatch')
        kind = head.get('kind')
        extra = {'probability'} if kind == 'laplace_constant' else {'coefficients','intercept'} if kind == 'linear_logistic' else set()
        if not extra or set(head) != common | extra:
            raise ValueError('exact head schema required')
        if any(type(head[k]) is not int or head[k] < 0 for k in ('observed_prefixes','observed_users','positive_prefixes')):
            raise ValueError('invalid head support')
        if (head['observed_users'] > head['observed_prefixes'] or head['positive_prefixes'] > head['observed_prefixes']
                or any(type(head[k]) not in (int,float) or not math.isfinite(head[k]) or head[k] < 0
                       for k in ('total_weight','positive_weight')) or head['positive_weight'] > head['total_weight']):
            raise ValueError('invalid head weights/support')
        if kind == 'laplace_constant':
            p = head['probability']
            if type(p) not in (int,float) or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError('invalid constant probability')
        elif (type(head['coefficients']) is not list or len(head['coefficients']) != FEATURE_DIMENSION
                or any(type(value) not in (int,float) for value in head['coefficients'])
                or not np.isfinite(np.asarray(head['coefficients'], dtype=float)).all()
                or type(head['intercept']) not in (int,float) or not math.isfinite(head['intercept'])):
            raise ValueError('invalid linear coefficients')
    return model


def predict_heads(model, x):
    validate_model(model)
    if x.shape[1] != FEATURE_DIMENSION or not np.isfinite(x.data).all():
        raise ValueError('finite blocked prediction matrix required')
    probabilities = []
    for head in model['heads']:
        p = (np.full(x.shape[0], head['probability'], dtype=float) if head['kind'] == 'laplace_constant'
             else expit(x @ np.asarray(head['coefficients'], dtype=float) + head['intercept']))
        if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
            raise ValueError('invalid predicted probability')
        probabilities.append(p)
    return np.column_stack(probabilities)
