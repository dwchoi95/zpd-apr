"""Prospective C3 fixed 9492-column heads; no production fit authorization.

The optimizer and user/prefix/event weighting are exactly frozen C2's. This
module operates only on supplied matrices, never loads observations or targets.
"""
from __future__ import annotations

import math
import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.linear_model import SGDClassifier

from scripts import run_zpd_history_action_cv as legacy
from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_action_blocked as blocked
from scripts import zpd_history_feedback_coupling as coupling

FEATURE_DIMENSION = coupling.FEATURE_DIMENSION
ARMS = coupling.ARMS
SEED, EPOCHS, ALPHA = 2027, 20, 1e-4
WEIGHTING = 'user_equal_prefix_mean_event_mask_no_head_renormalization'


def configuration():
    return coupling.configuration()


def fit_heads(x, y, mask, users, events, *, callback=None):
    if (not sparse.issparse(x) or x.shape != (len(users), FEATURE_DIMENSION) or y.shape != mask.shape
            or y.shape != (len(users),len(events)) or list(events) != list(semantic.EVENTS)
            or mask.dtype != bool or any(type(u) is not str for u in users) or not np.isfinite(x.data).all()
            or not np.isfinite(y).all() or not np.isin(y[mask], [0.,1.]).all()):
        raise ValueError('strict fixed feedback head input required')
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
    if (type(model['events']) is not list or model['events'] != list(semantic.EVENTS)
            or type(model['feature_dimension']) is not int or model['feature_dimension'] != FEATURE_DIMENSION
            or not blocked._identical_configuration(model['representation'],configuration()) or model['alpha'] != ALPHA
            or type(model['alpha']) is not float or type(model['seed']) is not int
            or model['seed'] != SEED or type(model['epochs']) is not int or model['epochs'] != EPOCHS or model['weighting'] != WEIGHTING
            or type(model['heads']) is not list or len(model['heads']) != len(semantic.EVENTS)):
        raise ValueError('fixed feedback model configuration mismatch')
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
    if not sparse.issparse(x) or x.shape[1] != FEATURE_DIMENSION or not np.isfinite(x.data).all():
        raise ValueError('finite feedback prediction matrix required')
    probabilities = []
    for head in model['heads']:
        p = (np.full(x.shape[0], head['probability'], dtype=float) if head['kind'] == 'laplace_constant'
             else expit(x @ np.asarray(head['coefficients'], dtype=float) + head['intercept']))
        if not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
            raise ValueError('invalid predicted probability')
        probabilities.append(p)
    return np.column_stack(probabilities)
