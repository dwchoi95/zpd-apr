"""Fixed train-only preservation supervision, not a correctness certificate.

Only relation/weights change. The legacy fold's numeric scale and structural
representation are shared by all four cells. Selection accepts no labels or
current replay stratum; unknown candidates remain selectable and uncertain.
"""
from __future__ import annotations

from collections import Counter
from itertools import combinations
import math

import numpy as np
from scipy import sparse
from sklearn.linear_model import LogisticRegression

from scripts.zpd_repair_pairwise import numeric_names, preference
from scripts.zpd_repair_structure import raw_features, _validate_model as validate_reference
from src.repair.pilot_contracts import canonical_hash, source_hash

KIND = 'replay_preservation_fixed_objective_v1'
CELLS = ('legacy_natural', 'legacy_balanced', 'refined_natural', 'refined_balanced')
STRATA = ('known_ac', 'known_nonac', 'unknown')
MASS = 1900.
C = .1


def stratum(label):
    key = preference(label)
    return 'unknown' if key is None else 'known_ac' if label['all_ac'] else 'known_nonac'


def refined_preference(label, *, current_stratum, is_noop, relation):
    if relation not in ('legacy', 'refined') or current_stratum not in STRATA or type(is_noop) is not bool:
        raise ValueError('explicit fixed preference configuration required')
    key = preference(label)
    if key is None or relation == 'legacy':
        return key
    return (*key, int(current_stratum == 'known_ac' and is_noop))


def training_data(examples, banks, labels, reference, cell):
    if cell not in CELLS:
        raise ValueError('fixed four objective cells only')
    scale, _ = validate_reference(reference)
    if reference['condition'] != 'C' or reference['variant'] != 'structural':
        raise ValueError('structural current-only reference required')
    if not examples or any(ex.split != 'train' for ex in examples):
        raise ValueError('strict nonempty fold-training examples required')
    if len({ex.example_id for ex in examples}) != len(examples) or len({ex.bank_id for ex in examples}) != len(examples):
        raise ValueError('unique training example and bank required')
    required = {(ex.bank_id,c.candidate_id) for ex in examples for c in banks[ex.bank_id].candidates}
    if set(banks) != {ex.bank_id for ex in examples} or set(labels) != required:
        raise ValueError('exact fold-training label/bank whitelist required')
    relation, weighting = cell.split('_')
    records = []; coverage = []; all_pairs = []
    for ex in examples:
        bank = banks[ex.bank_id]; noop = source_hash(bank.current_source)
        group = stratum(labels[ex.bank_id,noop])
        numeric, hashed = raw_features(ex.observation, (), bank, 'C', 'structural')
        x = sparse.hstack([numeric.multiply(1/scale), hashed], format='csr')
        candidates = bank.candidates
        keys = {j:refined_preference(labels[ex.bank_id,c.candidate_id], current_stratum=group,
                                     is_noop=c.candidate_id == noop, relation=relation)
                for j,c in enumerate(candidates)}
        stable = [j for j in keys if keys[j] is not None]
        pairs = [(a,b,int(keys[a] > keys[b])) for a,b in combinations(stable,2) if keys[a] != keys[b]]
        info = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, stratum=group,
            stable_candidate_ids=[candidates[j].candidate_id for j in stable],
            unknown_candidate_ids=[candidates[j].candidate_id for j in keys if keys[j] is None],
            pairs=[[candidates[a].candidate_id,candidates[b].candidate_id,target] for a,b,target in pairs],
            natural_row_weight=0., row_weight=0.)
        coverage.append(info)
        if pairs:
            records.append((ex,group,x,pairs,info))
    if not records:
        raise ValueError('no informative stable training pairs')
    per_user = Counter(ex.user_id for ex,*_ in records)
    for ex,group,x,pairs,info in records:
        info['natural_row_weight'] = MASS/(len(per_user)*per_user[ex.user_id]*len(pairs)*2)
    natural_mass = {s:float(sum(info['natural_row_weight']*2*len(pairs)
        for ex,g,x,pairs,info in records if g == s)) for s in STRATA}
    per_group = {s:Counter(ex.user_id for ex,g,*_ in records if g == s) for s in STRATA}
    desired_mass = dict(natural_mass)
    if weighting == 'balanced':
        if not per_group['known_ac'] or not per_group['known_nonac']:
            raise ValueError('both known strata require informative support; no redistribution')
        remainder = MASS-natural_mass['unknown']
        desired_mass.update(known_ac=remainder/2, known_nonac=remainder/2)
    matrices = []; outcomes = []; weights = []
    for ex,group,x,pairs,info in records:
        weight = (info['natural_row_weight'] if weighting == 'natural' else
                  desired_mass[group]/(len(per_group[group])*per_group[group][ex.user_id]*len(pairs)*2))
        info['row_weight'] = float(weight)
        for a,b,target in pairs:
            difference = x[a]-x[b]
            matrices.extend((difference,-difference)); outcomes.extend((target,1-target)); weights.extend((weight,weight))
            all_pairs.extend((ex.example_id,ex.example_id))
    weights = np.asarray(weights, dtype=float)
    realized_mass = {s:float(sum(info['row_weight']*2*len(pairs)
        for ex,g,x,pairs,info in records if g == s)) for s in STRATA}
    if (not np.isfinite(weights).all() or not (weights > 0).all()
            or not math.isclose(float(weights.sum()), MASS, rel_tol=1e-12)
            or any(not math.isclose(realized_mass[s], desired_mass[s], rel_tol=1e-12,abs_tol=1e-12) for s in STRATA)):
        raise ValueError('fixed stratum/total weight accounting failed')
    informative = [ex.example_id for ex,*_ in records]
    reference_ids = reference['training']['informative_train_example_ids']+reference['training']['uninformative_train_example_ids']
    if (set(reference_ids) != {ex.example_id for ex in examples} or len(reference_ids) != len(examples)):
        raise ValueError('reference scale training membership differs')
    metadata = dict(train_example_ids=[ex.example_id for ex in examples], train_prefixes=len(examples),
        train_users=len({ex.user_id for ex in examples}), informative_train_example_ids=informative,
        uninformative_train_example_ids=[ex.example_id for ex in examples if ex.example_id not in set(informative)],
        ordered_pairs=len(weights), pair_example_ids=all_pairs, sample_weight_sum=float(weights.sum()),
        natural_stratum_mass=natural_mass, stratum_mass=realized_mass,
        stratum_prefixes=dict(Counter(row['stratum'] for row in coverage)),
        informative_stratum_prefixes=dict(Counter(group for _,group,*_ in records)),
        prefixes=coverage, unknown_pair_policy='retain stable unequal pairs; unknown candidates incomparable')
    return sparse.vstack(matrices,format='csr'), np.asarray(outcomes), weights, scale, metadata


def train_model(examples, banks, labels, reference, cell):
    x,y,weights,scale,metadata = training_data(examples,banks,labels,reference,cell)
    reused = cell == 'legacy_natural'
    if reused:
        # This cell is a sealed baseline, not another optimization opportunity.
        coef = reference['coefficients']
        if metadata['informative_train_example_ids'] != reference['training']['informative_train_example_ids']:
            raise ValueError('legacy baseline informative order mismatch')
        iterations = None
    else:
        fitted = LogisticRegression(C=C,fit_intercept=False,solver='liblinear',max_iter=2000,
                                    random_state=2027).fit(x,y,sample_weight=weights)
        if max(fitted.n_iter_) >= 2000 or not np.isfinite(fitted.coef_).all():
            raise ValueError('preservation learner failed convergence/finite checks')
        coef = fitted.coef_[0].tolist(); iterations = int(max(fitted.n_iter_))
    model = dict(kind=KIND,cell=cell,condition='C',variant='structural',C=C,
        numeric_names=numeric_names('C'),numeric_scale=scale.tolist(),coefficients=coef,intercept=0.,
        hash_dimension=4096,normalization='candidate_l2_after_log1p',reference_pair_weight=MASS,
        solver='liblinear',max_iter=2000,random_state=2027,
        reference_model_sha256=reference['model_sha256'],legacy_model_reused=reused,iterations=iterations,training=metadata)
    model['model_sha256'] = canonical_hash(model)
    return model


def validate_model(model):
    required = {'kind','cell','condition','variant','C','numeric_names','numeric_scale','coefficients','intercept',
        'hash_dimension','normalization','reference_pair_weight','solver','max_iter','random_state',
        'reference_model_sha256','legacy_model_reused','iterations','training','model_sha256'}
    if type(model) is not dict or set(model) != required:
        raise ValueError('strict preservation model schema required')
    if model['model_sha256'] != canonical_hash({k:v for k,v in model.items() if k != 'model_sha256'}):
        raise ValueError('preservation model hash mismatch')
    fixed = dict(kind=KIND,condition='C',variant='structural',C=C,numeric_names=numeric_names('C'),
        intercept=0.,hash_dimension=4096,normalization='candidate_l2_after_log1p',reference_pair_weight=MASS,
        solver='liblinear',max_iter=2000,random_state=2027)
    if any(type(model[k]) is not type(v) or model[k] != v for k,v in fixed.items()) or model['cell'] not in CELLS:
        raise ValueError('fixed preservation configuration mismatch')
    if (model['legacy_model_reused'] is not (model['cell'] == 'legacy_natural') or
        type(model['reference_model_sha256']) is not str or len(model['reference_model_sha256']) != 64):
        raise ValueError('reference model/reuse mismatch')
    if ((model['legacy_model_reused'] and model['iterations'] is not None) or
        (not model['legacy_model_reused'] and (type(model['iterations']) is not int or not 0 < model['iterations'] < 2000))):
        raise ValueError('solver convergence metadata mismatch')
    for key in ('numeric_scale','coefficients'):
        if type(model[key]) is not list or any(type(v) not in (float,int) for v in model[key]):
            raise ValueError('finite numeric model lists required')
    scale = np.asarray(model['numeric_scale'],dtype=float); coef = np.asarray(model['coefficients'],dtype=float)
    if scale.shape != (3,) or not np.isfinite(scale).all() or not (scale > 0).all() or coef.shape != (4099,) or not np.isfinite(coef).all():
        raise ValueError('model feature dimensions/scale invalid')
    meta = model['training']
    if (type(meta) is not dict or not math.isclose(meta.get('sample_weight_sum',0),MASS,rel_tol=1e-12)
        or set(meta.get('stratum_mass',{})) != set(STRATA) or set(meta.get('natural_stratum_mass',{})) != set(STRATA)):
        raise ValueError('model mass metadata invalid')
    masses = meta['stratum_mass']; natural = meta['natural_stratum_mass']
    if (any(type(v) not in (float,int) or not math.isfinite(v) or v < 0 for v in (*masses.values(),*natural.values()))
        or not math.isclose(sum(masses.values()),MASS,rel_tol=1e-12)
        or not math.isclose(sum(natural.values()),MASS,rel_tol=1e-12)
        or not math.isclose(masses['unknown'],natural['unknown'],rel_tol=1e-12,abs_tol=1e-12)):
        raise ValueError('stratum/unknown mass invariant invalid')
    if model['cell'].endswith('_balanced') and not math.isclose(masses['known_ac'],masses['known_nonac'],rel_tol=1e-12):
        raise ValueError('known-stratum parity invalid')
    return scale,coef


def score_model(model, observation, bank):
    """All candidates, labels absent; never route by replay status or re-fit."""
    scale,coef = validate_model(model)
    numeric,hashed = raw_features(observation,(),bank,'C','structural')
    x = sparse.hstack([numeric.multiply(1/scale),hashed],format='csr')
    values = np.asarray(x@coef).ravel()
    if not np.isfinite(values).all():
        raise ValueError('nonfinite prediction')
    return {c.candidate_id:float(v) for c,v in zip(bank.candidates,values)}


def select_model(model, observation, bank):
    scores = score_model(model,observation,bank)
    return min(scores,key=lambda cid:(-scores[cid],cid))
