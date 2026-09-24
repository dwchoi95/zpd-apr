"""Independent C3 coefficient replay, coupling formula and seven-arm statistics.

No fit or driver report helper is called. Frozen input/event semantics and C2
independent base-matrix construction are reused; J/Jm, cohorts, statistics,
model contracts, parent parity and all completion inventories are rechecked.
Production fails closed until an explicit support/release pin is frozen.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
from scipy import sparse
from sklearn.feature_extraction import FeatureHasher
from sklearn.preprocessing import normalize

from scripts.audit_zpd_history_action_cv import (
    sha, read, rows, write, equal, seal, expected_folds, donor_keys,
    expected_donors, event_arrays, probabilities, FOLD_SALT, STRATA)
from scripts.audit_zpd_history_action_blocked_cv import (
    matrix as base_matrix, representation as base_representation,
    verify_seals as verify_parent_seals)

ROOT = Path(__file__).resolve().parents[1]
KIND = 'train_only_history_feedback_coupling_cv_v1'
ARMS = ('C0','Cn','H','U','HS','L','Jm')
CONTROLS = ('Cn','U','HS','L','Jm')
MODEL_FILES = ['cohort.json', *[a+'.json' for a in ARMS], 'predictions.jsonl', 'summary.json']
VERDICTS = ('AC','CE','OTHER','RE','RESOURCE','WA')
SUPPORT_COMPLETE_SHA = '106bd5a07b8c262d0fddbf780ccd998bb859582e1811affa1c299bb8bcc15dc3'
RELEASE_SHA = '0882ff57ffa3fd4db498a0a391f924f0ec6c223c43258e2828727bb23817a619'
SUPPORT_PARENT = 'outputs/zpd-history-feedback-coupling-20260924/support-v1'
RELEASE_RELATIVE = 'analysis_protocols/zpd-history-feedback-fit-release-20260924.json'
PROTOCOL = ROOT/'analysis_protocols/zpd-history-next-mechanism-design-20260924.md'
RUN_PARENT = 'outputs/zpd-history-feedback-coupling-20260924'
C2_PARENT = 'outputs/zpd-history-action-blocked-20260924/run-v1'
C2_COMPLETE_SHA = '3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690'
SOURCES = {
    'scripts/run_zpd_history_feedback_cv.py','scripts/zpd_history_feedback_coupling.py',
    'scripts/zpd_history_feedback_heads.py','scripts/audit_zpd_history_feedback_cv.py',
    'scripts/audit_zpd_history_action_blocked_cv.py','scripts/audit_zpd_history_action_cv.py',
    'scripts/audit_zpd_history_feedback_support.py','scripts/supervise_zpd_history_action.py',
    'scripts/run_zpd_history_action_cv.py','scripts/zpd_history_action_encoder.py',
    'scripts/zpd_history_action_blocked.py','scripts/audit_zpd_history_support.py',
    'scripts/prepare_zpd_train_successors.py','scripts/build_zpd_original_prefixes.py',
    'scripts/zpd_history_predictor.py','scripts/zpd_repair_structure.py',
    'scripts/zpd_repair_pairwise.py','analysis_protocols/zpd-history-next-mechanism-design-20260924.md',
    'scripts/zpd_history_feedback_release.py','scripts/supervise_zpd_history_feedback.py', RELEASE_RELATIVE}
SUPPORT_SOURCES = {
    'scripts/audit_zpd_history_feedback_support.py','scripts/zpd_history_feedback_coupling.py',
    'scripts/zpd_history_action_encoder.py','scripts/zpd_history_action_blocked.py',
    'scripts/run_zpd_history_action_cv.py','scripts/audit_zpd_history_support.py',
    'scripts/prepare_zpd_train_successors.py','scripts/zpd_history_predictor.py',
    'scripts/build_zpd_original_prefixes.py','scripts/supervise_zpd_history_action.py',
    'analysis_protocols/zpd-history-next-mechanism-design-20260924.md'}

NUISANCE_KEYS = ('nuisance:prior_count_log1p','nuisance:elapsed_seconds_log1p',
    'nuisance:prior_source_bytes_log1p','nuisance:prior_token_count_log1p')


def representation():
    from scripts.zpd_history_action_encoder import EVENTS
    return dict(version='applicable_observed_transition_coupling_v1',base=base_representation(),
        feature_dimension=9492,offset=8196,dimension=1296,weightings=['uniform','reciprocal_recency'],
        events=list(EVENTS),verdict_pairs=[a+'=>'+b for a in VERDICTS for b in VERDICTS],
        flatten_order='weight_event_verdict_pair_C',conditioning='each_event_applicable_observed_transitions_only',
        scale_divisor=6.,final_normalization=False,support_tolerance=1e-12,
        future_targets_used=False,fitted_transform=False)


def fixed_equal(actual, expected, where):
    """Configuration is exact; only numerical reductions use audit.equal."""
    # JSON serializers may write an integral-valued real as 6 rather than 6.0.
    # Permit that exact numeric identity, never tolerances or boolean aliases.
    if type(expected) is float and type(actual) in (int,float):
        if not math.isfinite(actual) or actual != expected:
            raise ValueError(where+': fixed configuration value differs')
        return
    if type(actual) is not type(expected):
        raise ValueError(where+': fixed configuration type differs')
    if isinstance(expected,dict):
        if set(actual) != set(expected):
            raise ValueError(where+': fixed configuration keys differ')
        for key,value in expected.items():
            fixed_equal(actual[key],value,where+'.'+key)
    elif isinstance(expected,list):
        if len(actual) != len(expected):
            raise ValueError(where+': fixed configuration list shape differs')
        for a,b in zip(actual,expected):
            fixed_equal(a,b,where)
    elif actual != expected:
        raise ValueError(where+': fixed configuration value differs')


def coupling_array(current, verdict, history, timestamp, encoder, *, arm, key, exact_flag=False):
    """Direct weighted conditional tables; no production coupling helper."""
    if arm in ('C0','Cn'):
        return np.zeros(1296)
    prior = [history[i] for i in encoder.permutation_indices(len(history),key)] if arm == 'HS' else history
    sequence = [*prior,dict(code=current,verdict=verdict,timestamp=timestamp,language='Python')]
    n = len(prior)
    if n == 0:
        return np.zeros(1296)
    values, masks, pairs = [], [], []
    for before,after in zip(sequence,sequence[1:]):
        _, value, mask = encoder._transition(before['code'],after['code'],before['language'],after['language'])
        values.append(value); masks.append(mask)
        pairs.append(6*VERDICTS.index(encoder._verdict(before['verdict']))+VERDICTS.index(encoder._verdict(after['verdict'])))
    values=np.asarray(values,dtype=float); masks=np.asarray(masks,dtype=bool); pairs=np.asarray(pairs)
    if exact_flag:
        # The diagnostic is exact float64 equality, not scientific approximate
        # equality. Reproduce the frozen reduction order only for this flag;
        # saved-coefficient scoring below uses separate fsum reductions.
        numerator=np.zeros((2,18,36)); opportunity=np.zeros((2,18))
        recency=1./np.arange(n,0,-1,dtype=float); recency/=recency.sum()
        for i in range(n):
            weighted_mask=np.asarray([1./n,recency[i]])[:,None]*masks[i][None,:]
            opportunity+=weighted_mask
            numerator[:,:,pairs[i]]+=weighted_mask*values[i][None,:]
        result=np.divide(numerator,opportunity[:,:,None],out=np.zeros_like(numerator),where=opportunity[:,:,None]>0)
        return result.reshape(-1)/6.
    result=np.zeros((2,18,36))
    raw_weights=(np.ones(n),1./np.arange(n,0,-1,dtype=float))
    for w,weight in enumerate(raw_weights):
        # Common normalization cancels in each applicability-conditional row.
        for event in range(18):
            eligible=masks[:,event]; denominator=math.fsum(weight[eligible])
            if denominator == 0:
                continue
            positive=math.fsum(weight[eligible]*values[eligible,event])/denominator
            chosen_weight=(weight[eligible] if arm == 'Jm' else weight[eligible]*values[eligible,event])
            result[w,event]=np.bincount(pairs[eligible],weights=chosen_weight,minlength=36)/denominator
            if arm == 'Jm':
                result[w,event]*=positive
    if not np.isfinite(result).all():
        raise ValueError('nonfinite independent coupling')
    return result.reshape(-1)/6.


def matrix(observations, held, arm, donors, encoder, *, return_flag_matrix=False):
    if arm not in ARMS:
        raise ValueError('unknown C3 arm')
    base_arm='H' if arm == 'Jm' else arm
    if return_flag_matrix:
        base,flag=base_matrix(observations,held,base_arm,donors,encoder,return_flag_matrix=True)
    else:
        base=base_matrix(observations,held,base_arm,donors,encoder)
    indexed={o['example_id']:o for o in observations}
    extra=[]; exact_extra=[]
    for i in held:
        o=observations[i]
        prior=(indexed[donors[o['example_id']]]['history'] if arm == 'U' else
               o['history'][-1:] if arm == 'L' else o['history'])
        extra.append(coupling_array(o['current_code'],o['current_verdict'],prior,o['timestamp'],encoder,arm=arm,key=o['example_id']))
        if return_flag_matrix:
            exact_extra.append(coupling_array(o['current_code'],o['current_verdict'],prior,o['timestamp'],encoder,arm=arm,key=o['example_id'],exact_flag=True))
    block=sparse.csr_matrix(np.asarray(extra)) if extra else sparse.csr_matrix((0,1296))
    result=sparse.hstack([base,block],format='csr')
    if return_flag_matrix:
        # Exact C2 H/HS equality uses frozen reduction order. Coupling equality
        # is checked independently below from the underlying transition tables.
        exact_block=sparse.csr_matrix(np.asarray(exact_extra)) if exact_extra else sparse.csr_matrix((0,1296))
        return result,sparse.hstack([flag,exact_block],format='csr')
    return result


def verify_seals(run):
    run=Path(run).absolute()
    if run.resolve() != run:
        raise ValueError('canonical run required')
    required=['manifest.json','folds.json','COHORTS_COMPLETE.json','target-coverage.json','report.json','events.jsonl','STATUS.json']
    required += [f'fold-{f}/'+name for f in range(5) for name in [*MODEL_FILES,'COMPLETE.json']]
    marker=seal(run,required)
    if (marker.get('completed_folds') != 5 or marker.get('completed_arms') != 35 or
            marker.get('confirmatory') is not False):
        raise ValueError('all five folds and thirty-five arms required')
    if {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()} != set(required+['COMPLETE.json']):
        raise ValueError('unexpected run artifact or full refit')
    for fold in range(5):
        nested=seal(run/f'fold-{fold}',MODEL_FILES)
        if type(nested.get('fold')) is not int or nested['fold'] != fold:
            raise ValueError('fold seal identity mismatch')
    return marker


def losses(predictions, events):
    result = {}; means = {}
    for arm in ARMS:
        by_user = defaultdict(list); by_event = {e:defaultdict(list) for e in events}
        support = Counter(); positives = Counter(); empty = 0
        for row in predictions:
            y = np.asarray(row['values']); mask = np.asarray(row['mask'], dtype=bool)
            p = np.asarray(row['probabilities'][arm], dtype=float)
            if (p.shape != (len(events),) or not np.isfinite(p).all() or np.any((p < 0)|(p > 1))):
                raise ValueError('invalid prediction vector')
            p = np.clip(p, 1e-12, 1-1e-12)
            nll = np.where(y == 1, -np.log(p), -np.log1p(-p))
            if mask.any():
                by_user[row['user_id']].append(float(np.mean(nll[mask])))
            else:
                empty += 1
            for j, event in enumerate(events):
                if mask[j]:
                    by_event[event][row['user_id']].append(float(nll[j])); support[event] += 1; positives[event] += int(y[j])
        means[arm] = {u:float(np.mean(v)) for u,v in sorted(by_user.items())}
        result[arm] = dict(user_equal_masked_nll=float(np.mean(list(means[arm].values()))) if means[arm] else None,
            users=len(means[arm]), evaluable_prefixes=len(predictions)-empty, all_masked_prefixes=empty,
            events={e:dict(prefixes=support[e], users=len(by_event[e]), positive_prefixes=positives[e],
                user_equal_nll=float(np.mean([np.mean(v) for v in by_event[e].values()])) if by_event[e] else None) for e in events})
    return result, means


def contrasts(means):
    users = sorted(means['H'])
    if any(set(means[c]) != set(users) for c in CONTROLS):
        raise ValueError('nonpaired user losses')
    if len(users) < 2:
        return {c:dict(status='insufficient_users', users=len(users), upper=None, lower=None) for c in CONTROLS}
    differences = np.array([[means['H'][u]-means[c][u] for c in CONTROLS] for u in users])
    rng = np.random.default_rng(2027)
    distribution = np.empty((5000, len(CONTROLS)))
    for draw in range(5000):
        distribution[draw] = np.mean(differences[rng.integers(len(users), size=len(users))], axis=0)
    bounds = np.quantile(distribution, [.005, .995], axis=0)
    return {c:dict(status='descriptive_crossfit_bootstrap', users=len(users), draws=5000, seed=2027,
                  mean=float(np.mean(differences[:,j])), lower=float(bounds[0,j]), upper=float(bounds[1,j]),
                  interval='two-sided Bonferroni99percent percentile; five prespecified contrasts; not confirmatory')
            for j,c in enumerate(CONTROLS)}


def gate(overall, folds, intervals):
    checks = {}
    for control in CONTROLS:
        h = overall['H']['user_equal_masked_nll']; c = overall[control]['user_equal_masked_nll']
        wins = 0
        for fold in folds.values():
            a = fold['H']['user_equal_masked_nll']; b = fold[control]['user_equal_masked_nll']
            wins += a is not None and b is not None and a < b
        upper = intervals[control]['upper']
        checks[control] = dict(aggregate_strictly_better=h is not None and c is not None and h < c,
            strictly_better_folds=wins, at_least_four_folds=wins >= 4,
            simultaneous_upper_below_zero=upper is not None and upper < 0)
    passed = len(folds) == 5 and all(v['aggregate_strictly_better'] and v['at_least_four_folds'] and
                                    v['simultaneous_upper_below_zero'] for v in checks.values())
    return dict(gate_passed=passed, checks=checks, confirmatory=False, learner_benefit_established=False,
                next_action='independent_result_audit_then_separately_frozen_repair_integration' if passed else
                'retain_negative_result_and_diagnose_train_only', full_train_refit_authorized=False)


def check_exposure_log(run, models, oof_count, passed):
    events = rows(Path(run)/'events.jsonl')
    expected_starts = [(fold,arm) for fold in range(5) for arm in ARMS]
    if [(e.get('fold'),e.get('arm')) for e in events if e.get('phase') == 'arm_start'] != expected_starts:
        raise ValueError('fixed thirty-five-arm execution log required')
    for (fold,arm), model in models.items():
        for head in model['heads']:
            trace = [e for e in events if e.get('fold') == fold and e.get('arm') == arm
                     and e.get('event') == head['event'] and e.get('phase') in ('training','head_complete')]
            if head['kind'] == 'laplace_constant':
                if (len(trace) != 1 or trace[0].get('phase') != 'head_complete'
                        or trace[0].get('training') != 'constant'
                        or trace[0].get('completed_train_prefix_event_exposures') != 0):
                    raise ValueError('constant-head execution log mismatch')
            else:
                expected = [(epoch,20,epoch*head['observed_prefixes'],20*head['observed_prefixes'],head['observed_prefixes'])
                            for epoch in range(1,21)]
                actual = [(e.get('epoch'),e.get('epochs'),e.get('completed_train_prefix_event_exposures'),
                           e.get('total_train_prefix_event_exposures'),e.get('unique_train_prefixes')) for e in trace]
                equal(actual, expected, 'twenty-epoch exposure trace')
    completed = [e for e in events if e.get('phase') == 'fold_complete']
    if [e.get('fold') for e in completed] != list(range(5)):
        raise ValueError('five fold-completion log required')
    terminal = events[-1]
    if (terminal.get('phase') != 'complete' or terminal.get('completed_folds') != 5
            or terminal.get('completed_oof_prefixes') != oof_count or terminal.get('gate_passed') != passed):
        raise ValueError('terminal execution log mismatch')
    equal(read(Path(run)/'STATUS.json'), terminal, 'terminal status')


def diagnostics(predictions, events):
    user_vectors = {arm:defaultdict(list) for arm in ARMS}
    for p in predictions:
        enabled = [j for j,bit in enumerate(p['mask']) if bit]
        if not enabled:
            continue
        for arm in ARMS:
            terms = np.zeros(len(events))
            for j in enabled:
                probability = min(1-1e-12,max(1e-12,p['probabilities'][arm][j]))
                terms[j] = (-math.log(probability) if p['values'][j] == 1 else -math.log1p(-probability))/len(enabled)
            user_vectors[arm][p['user_id']].append(terms)
    totals = {a:np.mean([np.mean(v,axis=0) for v in users.values()],axis=0).tolist()
              if users else [None]*len(events) for a,users in user_vectors.items()}
    contributions = {e:{a:totals[a][j] for a in ARMS} for j,e in enumerate(events)}
    contrasts_out = {c:{e:(totals['H'][j]-totals[c][j]) if totals['H'][j] is not None else None
                      for j,e in enumerate(events)} for c in ('C0','HS','Jm')}
    groups = {}
    for name, members in [('non_language_residual_16',set(events)-{'language_switch','other_lexical_change'}),
                          ('language_residual_2',{'language_switch','other_lexical_change'})]:
        indices = [j for j,e in enumerate(events) if e in members]
        reduced = [dict(p,values=[p['values'][j] for j in indices],mask=[p['mask'][j] for j in indices],
                        probabilities={a:[p['probabilities'][a][j] for j in indices] for a in ARMS}) for p in predictions]
        groups[name] = dict(events=[events[j] for j in indices],results=losses(reduced,[events[j] for j in indices])[0],
            additive_primary_mass={a:sum(totals[a][j] for j in indices) if totals[a][0] is not None else None for a in ARMS})
    return dict(kind='post_C2_diagnostic_not_advancement_endpoint',
        contribution_mass='all18_masked_prefix_mean_then_equal_user; contributions_sum_to_primary',
        events=contributions,H_minus_control_event_contributions=contrasts_out,groups=groups)


def check_parent(run, parent):
    parent = Path(parent)
    start = sha(parent/'COMPLETE.json')
    verify_parent_seals(parent)
    for name in ('folds.json','COHORTS_COMPLETE.json','target-coverage.json'):
        equal(read(Path(run)/name),read(parent/name),'C2 exact '+name)
    maximum = {arm:0. for arm in ('C0','Cn')}; checked = 0
    for fold in range(5):
        equal(read(Path(run)/f'fold-{fold}/cohort.json'),read(parent/f'fold-{fold}/cohort.json'),'C2 cohort')
        new = rows(Path(run)/f'fold-{fold}/predictions.jsonl')
        old = rows(parent/f'fold-{fold}/predictions.jsonl')
        if len(new) != len(old):
            raise ValueError('C2 prediction cohort length')
        for a,b in zip(new,old):
            for key in ('example_id','user_id','fold','donor_example_id','values','mask','target_status','next_language'):
                equal(a[key],b[key],'C2 prediction '+key)
            for arm in maximum:
                one,two = np.asarray(a['probabilities'][arm]),np.asarray(b['probabilities'][arm])
                if not np.allclose(one,two,rtol=1e-10,atol=2e-12):
                    raise ValueError('C2 '+arm+' prediction negative control failed')
                maximum[arm] = max(maximum[arm],float(np.max(np.abs(one-two))))
            checked += 1
        for arm in maximum:
            new_model=read(Path(run)/f'fold-{fold}/{arm}.json')
            old_model=read(parent/f'fold-{fold}/{arm}.json')
            if len(new_model['heads']) != len(old_model['heads']):
                raise ValueError('C2 head count differs')
            for new_head,old_head in zip(new_model['heads'],old_model['heads']):
                if new_head['kind'] == 'linear_logistic':
                    coefficients=np.asarray(new_head['coefficients'],dtype=float)
                    if coefficients.shape != (9492,) or np.any(coefficients[8196:] != 0.):
                        raise ValueError('C0/Cn appended model coefficients must be zero')
                    converted=dict(new_head,coefficients=new_head['coefficients'][:8196])
                else:
                    converted=new_head
                equal(converted,old_head,'C2 '+arm+' frozen head parity')
    verify_parent_seals(parent)
    if sha(parent/'COMPLETE.json') != start:
        raise ValueError('C2 parent changed during parity check')
    return dict(checked=True,complete_sha256=start,cohort_and_mask_exact=True,
                prediction_parity_arms=['C0','Cn'],predictions_checked_per_arm=checked,
                maximum_absolute_difference=maximum,zero_appended_coefficients=True,rtol=1e-10,atol=2e-12)


def check_model(model, arm, fold, train, observations, values, masks, events):
    ids = [observations[i]['example_id'] for i in train]
    expected = dict(events=list(events), feature_dimension=9492, representation=representation(), alpha=1e-4, seed=2027, epochs=20,
        weighting='user_equal_prefix_mean_event_mask_no_head_renormalization', arm=arm, fold=fold, train_example_ids=ids)
    fixed_equal({k:v for k,v in model.items() if k != 'heads'}, expected, 'model configuration')
    if type(model['heads']) is not list or len(model['heads']) != len(events):
        raise ValueError('missing/extra head')
    local_mask = masks[train]; local_y = values[train]
    event_counts = local_mask.sum(axis=1)
    user_counts = Counter(observations[i]['user_id'] for i, count in zip(train, event_counts) if count)
    factor = int(np.count_nonzero(event_counts))/len(user_counts) if user_counts else 0.
    weights = np.array([factor/(user_counts[observations[i]['user_id']]*count) if count else 0.
                        for i, count in zip(train, event_counts)])
    for j, head in enumerate(model['heads']):
        included = local_mask[:, j]; yy = local_y[included, j]; ww = weights[included]
        meta = dict(event=events[j], observed_prefixes=int(included.sum()),
                    observed_users=len({observations[i]['user_id'] for i, ok in zip(train, included) if ok}),
                    positive_prefixes=int(yy.sum()), total_weight=float(ww.sum()), positive_weight=float(ww@yy))
        equal({k:head.get(k) for k in meta}, meta, 'head support/weights')
        if len(set(yy)) <= 1:
            equal(head, dict(meta, kind='laplace_constant', probability=(float(ww@yy)+1)/(float(ww.sum())+2)), 'constant head')
        else:
            if set(head) != set(meta)|{'kind', 'coefficients', 'intercept'} or head['kind'] != 'linear_logistic':
                raise ValueError('two-class linear head required')
            coefficients = np.asarray(head['coefficients'], dtype=float)
            if (type(head['coefficients']) is not list or any(type(v) not in (int,float) for v in head['coefficients'])
                    or type(head['intercept']) not in (int,float)
                    or coefficients.shape != (9492,) or not np.isfinite(coefficients).all() or not math.isfinite(head['intercept'])):
                raise ValueError('invalid model coefficients')


def audit_data(run, observations, targets, encoder, *, progress=None, parent_run=None):
    """No fit: independently reconstruct all saved quantities from supplied inputs."""
    run = Path(run); marker = verify_seals(run); start_sha = sha(run/'COMPLETE.json')
    assignment = expected_folds(observations)
    equal(read(run/'folds.json'), assignment, 'fold assignment')
    values, masks = event_arrays(observations, targets, encoder)
    target_coverage = dict(prefixes=len(observations), all_masked=int((~masks.any(axis=1)).sum()),
        next_languages=dict(Counter(targets[o['example_id']]['next_language'] or 'unavailable' for o in observations)),
        target_status=dict(Counter(targets[o['example_id']]['target_status'] for o in observations)),
        mask_patterns=dict(Counter(''.join('1' if bit else '0' for bit in row) for row in masks)),
        events={e:dict(observed=int(masks[:,j].sum()), positive=int(values[masks[:,j],j].sum())) for j,e in enumerate(encoder.EVENTS)})
    equal(read(run/'target-coverage.json'), target_coverage, 'all-population event coverage')
    keys = donor_keys(observations); combined = []; summaries = {}; coverages = {}; cohort_shas = {}; models = {}
    for fold in range(5):
        directory = run/f'fold-{fold}'
        donors = expected_donors(observations, assignment['user_fold'], fold, keys)
        train = [i for i,o in enumerate(observations) if donors[o['example_id']] is not None and assignment['user_fold'][o['user_id']] != fold]
        held = [i for i,o in enumerate(observations) if donors[o['example_id']] is not None and assignment['user_fold'][o['user_id']] == fold]
        if not train or not held:
            raise ValueError('empty required donor cohort')
        cohort = dict(fold=fold, train_example_ids=[observations[i]['example_id'] for i in train],
            held_example_ids=[observations[i]['example_id'] for i in held], donor_assignments=donors,
            original_train_prefixes=sum(f != fold for f in assignment['example_fold'].values()),
            original_held_prefixes=sum(f == fold for f in assignment['example_fold'].values()),
            train_prefixes=len(train), held_prefixes=len(held), train_all_masked=int((~masks[train].any(axis=1)).sum()),
            held_all_masked=int((~masks[held].any(axis=1)).sum()))
        equal(read(directory/'cohort.json'), cohort, 'fold cohort')
        frozen = {k:cohort[k] for k in ('train_example_ids','held_example_ids','donor_assignments')}
        cohort_shas[str(fold)] = hashlib.sha256(json.dumps(frozen, sort_keys=True, separators=(',',':')).encode()).hexdigest()
        coverages[str(fold)] = {k:v for k,v in cohort.items() if k not in ('train_example_ids','held_example_ids','donor_assignments')}
        predictions = rows(directory/'predictions.jsonl')
        equal([r['example_id'] for r in predictions], cohort['held_example_ids'], 'prediction recipient order')
        current_keys = {(observations[i]['problem_id'], observations[i]['current_source_sha256']) for i in train}
        collision = defaultdict(list)
        for i in held:
            o = observations[i]
            history = hashlib.sha256(json.dumps([(h['code'], h['verdict']) for h in o['history']], separators=(',',':')).encode()).hexdigest()
            collision[o['problem_id'],o['current_source_sha256']].append((o['user_id'],history))
        distinct = {k for k,v in collision.items() if len({u for u,h in v}) > 1 and len({h for u,h in v}) > 1}
        for i, prediction in zip(held, predictions):
            o = observations[i]; key = (o['problem_id'],o['current_source_sha256'])
            expected = dict(example_id=o['example_id'], user_id=o['user_id'], problem_id=o['problem_id'], fold=fold,
                donor_example_id=donors[o['example_id']], values=values[i].tolist(), mask=masks[i].tolist(),
                target_status=targets[o['example_id']]['target_status'], next_language=targets[o['example_id']]['next_language'],
                current_source_sha256=o['current_source_sha256'], current_seen_in_fold_training=key in current_keys,
                within_held_cross_user_distinct_history_collision=key in distinct, hs_prior_length_one=len(o['history']) == 1,
                hs_permutation_identity=tuple(encoder.permutation_indices(len(o['history']),o['example_id'])) == tuple(range(len(o['history']))))
            equal({k:v for k,v in prediction.items() if k not in ('probabilities','hs_hashed_features_equal')}, expected, 'prediction metadata/masks')
            if set(prediction['probabilities']) != set(ARMS):
                raise ValueError('all seven arm probabilities required')
            if any(type(p) is not list or any(type(v) not in (int,float) for v in p)
                   for p in prediction['probabilities'].values()):
                raise ValueError('strict numeric probability vectors required')
        h_matrix = None
        for arm in ARMS:
            model = read(directory/(arm+'.json'))
            check_model(model, arm, fold, train, observations, values, masks, encoder.EVENTS)
            models[fold,arm] = model
            if arm in ('H','HS'):
                x, flag_matrix = matrix(observations,held,arm,donors,encoder,return_flag_matrix=True)
            else:
                x = matrix(observations,held,arm,donors,encoder)
            predicted = probabilities(model, x)
            actual = np.array([p['probabilities'][arm] for p in predictions], dtype=float)
            if actual.shape != predicted.shape or not np.allclose(actual, predicted, rtol=1e-10, atol=2e-12):
                raise ValueError('saved-coefficient prediction mismatch: '+arm)
            if arm == 'H':
                h_matrix = flag_matrix
            elif arm == 'HS':
                equality = np.asarray((h_matrix-flag_matrix).getnnz(axis=1) == 0).reshape(-1)
                equal([p['hs_hashed_features_equal'] for p in predictions], equality.tolist(), 'H/HS hashed equality')
            if progress:
                progress(dict(phase='verify_model', fold=fold, arm=arm, verified_held_prefixes=len(held)))
        summary, _ = losses(predictions, encoder.EVENTS)
        equal(read(directory/'summary.json'), summary, 'fold summary')
        summaries[str(fold)] = summary; combined.extend(predictions)
    if len({p['example_id'] for p in combined}) != len(combined):
        raise ValueError('duplicate OOF prediction')
    equal(read(run/'COHORTS_COMPLETE.json'), dict(status='observed_only_cohorts_sealed_before_target_encoding',
        fold_cohort_sha256=cohort_shas, total_oof_supported=len(combined)), 'observed-only cohort seal')
    overall, means = losses(combined, encoder.EVENTS); intervals = contrasts(means)
    decision = gate(overall, summaries, intervals)
    expected_report = dict(kind=KIND, confirmatory=False, fresh_test_opened=False,
        events=list(encoder.EVENTS), results=overall, fold_results=summaries, fold_coverage=coverages,
        bootstrap_contrasts=intervals, decision=decision,
        representation=representation(), event_diagnostics=diagnostics(combined,encoder.EVENTS),
        strata={name:losses([p for p in combined if p[name]], encoder.EVENTS)[0] for name in STRATA},
        source_population=len(observations), total_oof_supported=len(combined),
        oof_donor_supported_prefixes=len(combined), oof_users=len({p['user_id'] for p in combined}),
        note='Observed next-action prediction only; no repair or educational-learning superiority claim.')
    equal(read(run/'report.json'), expected_report, 'full independent report')
    equal(marker['gate_passed'], decision['gate_passed'], 'terminal gate')
    check_exposure_log(run, models, len(combined), decision['gate_passed'])
    parent_parity = check_parent(run, parent_run) if parent_run is not None else {'checked':False,'reason':'synthetic_without_parent'}
    verify_seals(run)
    if sha(run/'COMPLETE.json') != start_sha:
        raise ValueError('run seal changed during verification')
    return dict(verified=True, experiment_complete_sha256=start_sha, model_folds_verified=35,
        source_population=len(observations), oof_prefixes=len(combined), oof_users=len(means['H']),
        target_coverage=target_coverage, decision=decision, results=overall, bootstrap_contrasts=intervals,
        parent_c2_negative_controls=parent_parity, event_diagnostics=diagnostics(combined,encoder.EVENTS),
        refitting_performed=False, raw_release_opened=False, heldout_labels_opened=False,
        limitations=['Shared audited input loader and pure encoder define input/event semantics.',
                     'Coefficient rescoring verifies saved predictions, not an independent optimizer refit.',
                     'Developmental behavioral prediction is not repair or learner-benefit evidence.'])



def expected_configuration(encoder):
    return dict(arms=list(ARMS),events=list(encoder.EVENTS),folds=5,fold_salt=FOLD_SALT,
        representation=representation(),seed=2027,alpha=1e-4,epochs=20,controls=list(CONTROLS),probability_clip=1e-12,
        weighting='user_equal_prefix_mean_event_mask_no_head_renormalization',bootstrap_draws=5000,
        bootstrap_quantiles=[.005,.995])


def check_configuration(manifest, encoder):
    fixed_equal(manifest['configuration'],expected_configuration(encoder),'fixed feedback configuration')
    if (manifest.get('kind') != KIND or manifest.get('confirmatory') is not False
            or manifest.get('fresh_test_opened') is not False or set(manifest['source_sha256']) != SOURCES):
        raise ValueError('fixed feedback source closure required')


def source_state():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed verifier source required')
    return {key:subprocess.check_output(['git','rev-parse',spec],cwd=ROOT,text=True).strip()
            for key,spec in (('revision','HEAD'),('tree','HEAD^{tree}'))}


def check_release(project, manifest, encoder):
    """Independent approval validation, not the production release helper."""
    if SUPPORT_COMPLETE_SHA is None or RELEASE_SHA is None:
        raise ValueError('C3 production unreleased: support/release decision not frozen')
    support=canonical(Path(project)/SUPPORT_PARENT);release=canonical(ROOT/RELEASE_RELATIVE)
    if sha(support/'COMPLETE.json') != SUPPORT_COMPLETE_SHA or sha(release) != RELEASE_SHA:
        raise ValueError('wrong pinned support/release')
    marker=seal(support,('manifest.json','report.json','STATUS.json','events.jsonl'))
    if marker.get('fitting_performed') is not False:
        raise ValueError('observation-only support marker required')
    report=read(support/'report.json');support_manifest=read(support/'manifest.json')
    if (report.get('kind') != 'observed_only_feedback_coupling_support_v1' or
            any(report.get(key) is not False for key in ('successor_files_opened','outcome_files_opened',
                'model_files_opened','fitting_performed','future_targets_opened','fit_release_authorized')) or
            report.get('usable_joint_variation_anywhere') is not True or report.get('excluded_prefixes') != 0):
        raise ValueError('support evidence must be observed-only and retain all prefixes')
    equal(report['coverage'],dict(prefixes=71191,users=8473,problems=23,observed_source_ids=103775),'support coverage')
    fixed_equal(report['configuration'],representation(),'support representation')
    count=report['totals']['joint_marginal_distinct']['prefixes']
    if type(count) is not int or count <= 0:
        raise ValueError('no usable coupling variation')
    if report.get('parent_c2_complete_sha256') != C2_COMPLETE_SHA:
        raise ValueError('support parent mismatch')
    if set(support_manifest['source_sha256']) != SUPPORT_SOURCES:
        raise ValueError('exact support source inventory required')
    for name in SUPPORT_SOURCES:
        if support_manifest['source_sha256'].get(name) != sha(ROOT/name):
            raise ValueError('support/current observation, donor, feature or protocol source mismatch')
    decision=read(release)
    reason=decision.get('support_decision_reason')
    if type(reason) is not str or not reason.strip():
        raise ValueError('explicit support decision reason required')
    fixed_equal(decision,dict(kind='feedback_coupling_fit_release_v1',support_complete_sha256=SUPPORT_COMPLETE_SHA,
        fit_release_authorized=True,parent_c2_complete_sha256=C2_COMPLETE_SHA,protocol_sha256=sha(PROTOCOL),
        configuration=expected_configuration(encoder),support_decision_reason=reason,
        confirmatory=False,fresh_test_opened=False),'frozen release decision')
    equal(manifest['support_release'],dict(support_path=str(support),support_complete_sha256=SUPPORT_COMPLETE_SHA,
        release_path=str(release),release_sha256=RELEASE_SHA),'support release binding')
    bindings={support/'COMPLETE.json':SUPPORT_COMPLETE_SHA,release:RELEASE_SHA,
              **{support/name:digest for name,digest in marker['files_sha256'].items()}}
    for name,digest in support_manifest['input_sha256'].items():
        path=canonical(name)
        if not path.is_relative_to(project):
            raise ValueError('support inputs outside canonical data root')
        if sha(path) != digest:
            raise ValueError('support input changed')
        bindings[path]=digest
    return bindings


def canonical(path):
    path = Path(path).absolute()
    if path != path.resolve():
        raise ValueError('canonical path required')
    return path


def validate_paths(project, run, output):
    project,run,output = canonical(project),canonical(run),canonical(output)
    own_family = output.parent == project/RUN_PARENT
    supervised = (output.name == 'verified' and output.parent.parent == project/RUN_PARENT)
    if run.parent != project/RUN_PARENT or not (own_family or supervised):
        raise ValueError('fixed blocked feedback run/audit family required')
    if output.exists() or output.is_symlink() or output.is_relative_to(run) or run.is_relative_to(output):
        raise ValueError('new nonoverlapping audit output required')
    return project,run,output


def audit(project, run, output):
    from scripts.run_zpd_history_action_cv import load_inputs
    from scripts import zpd_history_action_encoder as encoder
    project,run,output = validate_paths(project,run,output)
    output.mkdir(parents=True); started=time.time()
    def progress(fields):
        write(output/'STATUS.json',dict(fields,elapsed_seconds=time.time()-started))
    try:
        if SUPPORT_COMPLETE_SHA is None or RELEASE_SHA is None:
            raise ValueError('C3 production unreleased: support/release decision not frozen')
        marker=verify_seals(run); manifest=read(run/'manifest.json')
        check_configuration(manifest,encoder)
        provenance=source_state()
        equal(manifest['source_revision'],provenance['revision'],'source revision')
        equal(manifest['source_tree'],provenance['tree'],'source tree')
        source_bindings={}
        for name,expected in manifest['source_sha256'].items():
            path=ROOT/name
            if path.resolve() != path or sha(path) != expected:
                raise ValueError('source/protocol mismatch')
            source_bindings[path]=expected
        if source_bindings.get(PROTOCOL) != manifest['protocol_sha256']:
            raise ValueError('protocol source binding absent')
        runtime={name:version(name) for name in ('numpy','scipy','scikit-learn')}
        equal(runtime,{'numpy':'2.5.2','scipy':'1.18.1','scikit-learn':'1.9.0'},'frozen numerical runtime')
        runtime['python']=platform.python_version()
        equal(runtime['python'],'3.13.11','frozen Python runtime')
        equal(manifest['runtime'],runtime,'runtime')
        release_bindings=check_release(project,manifest,encoder)
        parent=project/C2_PARENT
        if sha(parent/'COMPLETE.json') != C2_COMPLETE_SHA:
            raise ValueError('wrong pinned C2 parent')
        parent_marker=verify_parent_seals(parent)
        equal(manifest['parent_c2'],dict(path=str(parent),complete_sha256=C2_COMPLETE_SHA,
              prediction_parity_arms=['C0','Cn'],prediction_parity_rtol=1e-10,
              prediction_parity_atol=2e-12),'C2 negative control binding')
        # Labels are reached only after independently validating the release.
        observations,targets,coverage,bindings=load_inputs(project)
        bindings.update(release_bindings)
        bindings[parent/'COMPLETE.json']=C2_COMPLETE_SHA
        bindings.update({parent/name:digest for name,digest in parent_marker['files_sha256'].items()})
        equal(manifest['coverage'],coverage,'sealed full input coverage')
        equal(manifest['input_sha256'],{str(p):digest for p,digest in bindings.items() if p not in source_bindings},'input bindings')
        result=audit_data(run,observations,targets,encoder,progress=progress,parent_run=parent)
        for path,expected in {**bindings,**source_bindings}.items():
            if sha(path) != expected:
                raise ValueError('input/source changed during verification')
        verify_seals(run)
        if sha(run/'COMPLETE.json') != result['experiment_complete_sha256']:
            raise ValueError('run changed before audit seal')
        if source_state() != provenance:
            raise ValueError('verifier source checkout changed')
        result.update(source_revision=provenance['revision'],source_tree=provenance['tree'],
            verifier_sha256=sha(__file__),helper_sha256=sha(ROOT/'scripts/audit_zpd_history_action_cv.py'),
            elapsed_seconds=time.time()-started,experiment_report_sha256=marker['files_sha256']['report.json'],
            support_complete_sha256=SUPPORT_COMPLETE_SHA,release_sha256=RELEASE_SHA)
        write(output/'report.json',result);progress(dict(phase='complete',verified=True))
        for path,expected in {**bindings,**source_bindings}.items():
            if sha(path) != expected:
                raise ValueError('input/source changed before terminal audit seal')
        if source_state() != provenance or sha(run/'COMPLETE.json') != result['experiment_complete_sha256']:
            raise ValueError('source/run changed before terminal audit seal')
        write(output/'COMPLETE.json',dict(status='complete',verified=True,
            experiment_complete_sha256=result['experiment_complete_sha256'],
            files_sha256={name:sha(output/name) for name in ('report.json','STATUS.json')}))
        return result
    except BaseException as error:
        write(output/'FAILED.json',dict(status='failed',error_type=type(error).__name__,error=str(error)))
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--run',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    return audit(args.project,args.run,args.output)


if __name__ == '__main__':
    main()
