"""Pure observed edit/nominal-feedback coupling, with C2 columns untouched.

No target stores, fitting, execution, I/O, truncation or fitted transforms. The
extra marginal-product control has authentic H's entire existing C2 block.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy import sparse

from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_action_blocked as blocked

VERSION = 'applicable_observed_transition_coupling_v1'
EVENTS = semantic.EVENTS
VERDICTS = ('AC','CE','OTHER','RE','RESOURCE','WA')
VERDICT_PAIRS = tuple(a+'=>'+b for a in VERDICTS for b in VERDICTS)
PAIR_INDEX = {pair:i for i,pair in enumerate(VERDICT_PAIRS)}
WEIGHTINGS = ('uniform','reciprocal_recency')
ARMS = (*blocked.ARMS,'Jm')
BASE_DIMENSION = 8196
COUPLING_DIMENSION = 1296
FEATURE_DIMENSION = BASE_DIMENSION + COUPLING_DIMENSION
SCALE = 6.
SUPPORT_TOLERANCE = 1e-12
OBSERVATION_FIELDS = frozenset({'example_id','user_id','problem_id','split','timestamp',
    'current_code','current_verdict','matching_current_verdict','current_source_sha256','history'})


@dataclass(frozen=True)
class Coupling:
    joint: np.ndarray
    marginal: np.ndarray
    opportunity: np.ndarray
    applicable_counts: np.ndarray
    transition_count: int


def configuration():
    return dict(version=VERSION,base=blocked.configuration(),feature_dimension=FEATURE_DIMENSION,
        offset=BASE_DIMENSION,dimension=COUPLING_DIMENSION,weightings=list(WEIGHTINGS),
        events=list(EVENTS),verdict_pairs=list(VERDICT_PAIRS),flatten_order='weight_event_verdict_pair_C',
        conditioning='each_event_applicable_observed_transitions_only',scale_divisor=SCALE,
        final_normalization=False,support_tolerance=SUPPORT_TOLERANCE,
        future_targets_used=False,fitted_transform=False)


def _observed(observation):
    if type(observation) is not dict or set(observation) != OBSERVATION_FIELDS or observation['split'] != 'train':
        raise ValueError('strict observed-only train schema required; no future fields')


def joint_from_transitions(values, masks, pair_indices):
    """Finite past events only; helpers expose missingness, never fill negatives."""
    y = np.asarray(values)
    m = np.asarray(masks)
    pairs = np.asarray(pair_indices)
    if (y.ndim != 2 or y.shape[1] != len(EVENTS) or m.shape != y.shape or m.dtype != bool
            or pairs.shape != (len(y),) or pairs.dtype.kind not in 'iu'
            or not np.isfinite(y).all() or not np.isin(y[m],[0.,1.]).all()
            or (pairs < 0).any() or (pairs >= len(VERDICT_PAIRS)).any()):
        raise ValueError('strict finite observed-transition arrays required')
    n = len(y)
    numerator = np.zeros((2,len(EVENTS),len(VERDICT_PAIRS)),dtype=float)
    verdict_mass = np.zeros_like(numerator)
    opportunity = np.zeros((2,len(EVENTS)),dtype=float)
    positive = np.zeros_like(opportunity)
    if n:
        recency = 1./np.arange(n,0,-1,dtype=float)
        recency /= recency.sum()
        for i in range(n):
            weighted_mask = np.asarray([1./n,recency[i]])[:,None] * m[i][None,:]
            weighted_positive = weighted_mask * y[i][None,:]
            opportunity += weighted_mask; positive += weighted_positive
            verdict_mass[:,:,pairs[i]] += weighted_mask
            numerator[:,:,pairs[i]] += weighted_positive
    denominator = opportunity[:,:,None]
    joint = np.divide(numerator,denominator,out=np.zeros_like(numerator),where=denominator > 0)
    v_mean = np.divide(verdict_mass,denominator,out=np.zeros_like(verdict_mass),where=denominator > 0)
    y_mean = np.divide(positive,opportunity,out=np.zeros_like(positive),where=opportunity > 0)
    marginal = y_mean[:,:,None] * v_mean
    if not all(np.isfinite(a).all() for a in (joint,marginal,opportunity)):
        raise ValueError('nonfinite conditional coupling')
    return Coupling(joint,marginal,opportunity,m.sum(axis=0).astype(int),n)


def coupling_features(current_code, current_verdict, history, current_timestamp, *, shuffled=False, shuffle_key=''):
    if type(shuffled) is not bool or type(shuffle_key) is not str:
        raise ValueError('explicit deterministic shuffle controls required')
    semantic._validate_observation(current_code,current_verdict,history,current_timestamp,'HS' if shuffled else 'H')
    prior = [history[i] for i in semantic.permutation_indices(len(history),shuffle_key)] if shuffled else history
    sequence = [*prior,dict(code=current_code,verdict=current_verdict,timestamp=current_timestamp,language='Python')]
    values = np.zeros((len(history),len(EVENTS)))
    masks = np.zeros_like(values,dtype=bool)
    pairs = np.zeros(len(history),dtype=int)
    for i,(before,after) in enumerate(zip(sequence,sequence[1:])):
        _, observed, applicable = semantic._transition(before['code'],after['code'],before['language'],after['language'])
        values[i],masks[i] = observed,applicable
        pair = semantic._verdict(before['verdict'])+'=>'+semantic._verdict(after['verdict'])
        pairs[i] = PAIR_INDEX[pair]
    return joint_from_transitions(values,masks,pairs)


def coupling_block(current_code, current_verdict, history, current_timestamp, *, mode='joint', shuffled=False, shuffle_key=''):
    if mode not in ('joint','marginal'):
        raise ValueError('joint or marginal mode required')
    result = coupling_features(current_code,current_verdict,history,current_timestamp,
                               shuffled=shuffled,shuffle_key=shuffle_key)
    return getattr(result,mode).reshape(-1)/SCALE


def encode_matrix(observations, indices, arm, *, donors=None, callback=None):
    if arm not in ARMS:
        raise ValueError('unknown coupling arm')
    for observation in observations:
        _observed(observation)
    base_arm = 'H' if arm == 'Jm' else arm
    base = blocked.encode_matrix(observations,indices,base_arm,donors=donors,callback=callback)
    if arm in ('C0','Cn'):
        return sparse.hstack([base,sparse.csr_matrix((len(indices),COUPLING_DIMENSION))],format='csr')
    indexed = {o['example_id']:o for o in observations}
    rows = []
    for completed,i in enumerate(indices,1):
        o = observations[int(i)]
        history = (indexed[donors[o['example_id']]]['history'] if arm == 'U' else
                   o['history'][-1:] if arm == 'L' else o['history'])
        vector = coupling_block(o['current_code'],o['current_verdict'],history,o['timestamp'],
            mode='marginal' if arm == 'Jm' else 'joint',shuffled=arm == 'HS',shuffle_key=o['example_id'])
        rows.append(sparse.csr_matrix(vector.reshape(1,-1)))
        if callback and (completed % 1000 == 0 or completed == len(indices)):
            callback(dict(phase='encoding_coupling',arm=arm,completed_examples=completed,total_examples=len(indices)))
    extra = sparse.vstack(rows,format='csr') if rows else sparse.csr_matrix((0,COUPLING_DIMENSION))
    return sparse.hstack([base,extra],format='csr')


def observation_support(observation):
    """One record per original prefix; identities only label audit coverage."""
    o = observation
    _observed(o)
    args = (o['current_code'],o['current_verdict'],o['history'],o['timestamp'])
    authentic = coupling_features(*args)
    shuffled = coupling_features(*args,shuffled=True,shuffle_key=o['example_id'])
    bags = [semantic.encode_observation(*args,arm,shuffle_key=o['example_id']) for arm in ('H','HS')]
    base = blocked.transform_bags(bags,'H')
    jm = np.abs(authentic.joint-authentic.marginal)
    hs = np.abs(authentic.joint-shuffled.joint)
    return dict(example_id=o['example_id'],user_id=o['user_id'],problem_id=o['problem_id'],
        prior_count=len(o['history']),transition_count=authentic.transition_count,
        applicable_counts=authentic.applicable_counts.tolist(),hs_applicable_counts=shuffled.applicable_counts.tolist(),
        uniform_opportunity=authentic.opportunity[0].tolist(),recency_opportunity=authentic.opportunity[1].tolist(),
        joint_marginal_max_abs=float(jm.max()),joint_hs_max_abs=float(hs.max()),
        joint_marginal_distinct=bool((jm > SUPPORT_TOLERANCE).any()),
        joint_hs_distinct=bool((hs > SUPPORT_TOLERANCE).any()),
        joint_marginal_event_distinct=(jm.max(axis=(0,2)) > SUPPORT_TOLERANCE).tolist(),
        joint_hs_event_distinct=(hs.max(axis=(0,2)) > SUPPORT_TOLERANCE).tolist(),
        c2_hs_distinct=bool((base[0]-base[1]).nnz),
        hs_permutation_identity=semantic.permutation_indices(len(o['history']),o['example_id'])==tuple(range(len(o['history']))))


def _aggregate(rows):
    counts = dict(prefixes=len(rows),users=len({r['user_id'] for r in rows}),problems=len({r['problem_id'] for r in rows}),
        prior_transitions=sum(r['transition_count'] for r in rows),
        prior_length_zero=sum(r['prior_count']==0 for r in rows),prior_length_one=sum(r['prior_count']==1 for r in rows),
        prior_length_at_least_two=sum(r['prior_count']>=2 for r in rows))
    for flag in ('joint_marginal_distinct','joint_hs_distinct','c2_hs_distinct','hs_permutation_identity'):
        selected = [r for r in rows if r[flag]]
        counts[flag] = dict(prefixes=len(selected),users=len({r['user_id'] for r in selected}),
                            problems=len({r['problem_id'] for r in selected}))
    counts['events'] = {event:dict(applicable_prefixes=sum(r['applicable_counts'][j]>0 for r in rows),
        at_least_two_applicable_prefixes=sum(r['applicable_counts'][j]>=2 for r in rows),
        applicable_transitions=sum(r['applicable_counts'][j] for r in rows),
        joint_marginal_distinct_prefixes=sum(r['joint_marginal_event_distinct'][j] for r in rows),
        joint_marginal_distinct_users=len({r['user_id'] for r in rows if r['joint_marginal_event_distinct'][j]}),
        joint_hs_distinct_prefixes=sum(r['joint_hs_event_distinct'][j] for r in rows)) for j,event in enumerate(EVENTS)}
    return counts


def support_summary(observations, assignment, cohorts, *, callback=None):
    """Observed-only coverage for all folds, no labels or fitting API argument.

    Cohorts are existing fold->(train_indices,held_indices,donors). Counts do not
    make a new fitting cohort. The caller seals the observed-only loader inputs
    and independently verifies full donor problem/verdict/token/user/time rules.
    This function checks exact identities, index coverage and fold membership.
    """
    if not observations or len({o['example_id'] for o in observations}) != len(observations):
        raise ValueError('nonempty unique original observations required')
    if any(o.get('split') != 'train' for o in observations):
        raise ValueError('strict train-only observed support required')
    integer_keys = set(cohorts) == set(range(5)) and all(type(k) is int for k in cohorts)
    string_keys = set(cohorts) == set(map(str,range(5))) and all(type(k) is str for k in cohorts)
    if (set(assignment) != {'salt','user_fold','example_fold'} or len(cohorts) != 5
            or not (integer_keys or string_keys)):
        raise ValueError('complete original five-fold assignment/cohorts required')
    if (set(assignment['example_fold']) != {o['example_id'] for o in observations}
            or set(assignment['user_fold']) != {o['user_id'] for o in observations}
            or any(type(v) is not int or v not in range(5) for v in assignment['user_fold'].values())
            or any(type(v) is not int or v not in range(5) for v in assignment['example_fold'].values())
            or any(assignment['user_fold'][o['user_id']] != assignment['example_fold'][o['example_id']]
                   for o in observations)):
        raise ValueError('exact original observation/user assignment required')
    rows = []
    for completed,o in enumerate(observations,1):
        rows.append(observation_support(o))
        if callback and (completed % 1000 == 0 or completed == len(observations)):
            callback(dict(phase='observed_coupling_support',completed_examples=completed,total_examples=len(observations)))
    folds = {}
    identifiers = {r['example_id'] for r in rows}
    for fold in range(5):
        train,held,donors = cohorts[fold] if fold in cohorts else cohorts[str(fold)]
        if (type(donors) is not dict or set(donors) != identifiers
                or any(d is not None and (type(d) is not str or d not in identifiers) for d in donors.values())):
            raise ValueError('complete observed donor mapping required')
        if any(isinstance(i,(bool,np.bool_)) or not isinstance(i,(int,np.integer)) for i in [*train,*held]):
            raise ValueError('strict integer cohort indices required')
        tr,he = list(map(int,train)),list(map(int,held))
        if (len(set(tr)) != len(tr) or len(set(he)) != len(he) or set(tr)&set(he)
                or any(i<0 or i>=len(rows) for i in tr+he)):
            raise ValueError('invalid donor-supported index cohort')
        if any(assignment['example_fold'][rows[i]['example_id']] == fold for i in tr):
            raise ValueError('training recipient in held fold')
        if any(assignment['example_fold'][rows[i]['example_id']] != fold for i in he):
            raise ValueError('held recipient outside held fold')
        supported = {i for i,r in enumerate(rows) if donors[r['example_id']] is not None}
        if set(tr)|set(he) != supported:
            raise ValueError('supported recipients cannot be removed')
        folds[str(fold)] = dict(
            all_train=_aggregate([r for r in rows if assignment['example_fold'][r['example_id']] != fold]),
            all_held=_aggregate([r for r in rows if assignment['example_fold'][r['example_id']] == fold]),
            donor_supported_train=_aggregate([rows[i] for i in tr]),donor_supported_held=_aggregate([rows[i] for i in he]))
    totals = _aggregate(rows)
    return dict(kind='observed_only_feedback_coupling_support_v1',configuration=configuration(),
        events=list(EVENTS),rows=rows,totals=totals,folds=folds,excluded_prefixes=0,
        usable_joint_variation_anywhere=bool(totals['joint_marginal_distinct']['prefixes']),
        fit_release_authorized=False,fitting_performed=False,future_targets_opened=False,
        decision='no_fit_no_joint_variation' if not totals['joint_marginal_distinct']['prefixes'] else
                 'support_present_requires_independent_review_before_fit_decision')
