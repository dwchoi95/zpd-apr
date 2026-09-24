"""Pure fixed-cohort progress32 feasibility gate; no I/O, execution or fit.

Caller must authenticate the frozen metadata, candidate features and replay.
This module cannot establish those authorities from self-supplied hashes. All
six prospective conditions are necessary in EACH original training-fold union.
A positive decision is not repair success or authorization to fit a model.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import math
import re
from collections.abc import Mapping

import numpy as np

from scripts import zpd_statement_sample_progress as progress

VERSION='statement_sample_progress32_readiness_v1'
PROTOCOL='analysis_protocols/zpd-statement-sample-progress-prospective-20260924.md'
ARMS=progress.ARMS
CONTROLS=('Jm','HS','U','L')
MOMENT_ARMS=('H','HS','U','L')
# The unchanged descriptive final-coordinate tolerance used by directed support.
TOLERANCE=1e-12
COUNTS=dict(examples=320,users=320,problems=23,candidates=2544,folds=5)


def require(condition,message):
    if not condition:raise ValueError(message)


def _text(value):return type(value) is str and bool(value)
def _sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


@dataclass(frozen=True)
class BankSpec:
    """Externally authenticated original metadata, not a new sample selector."""
    example_id: str
    user_id: str
    problem_id: str
    fold: int
    bank_id: str
    bank_seal_sha256: str
    candidate_ids: tuple[str,...]
    noop_candidate_id: str
    original_nominal_sequence: tuple[str,...]
    sample_count: int

    def __post_init__(self):
        require(all(_text(v) for v in (self.example_id,self.user_id,self.problem_id,self.bank_id))
            and _sha(self.bank_seal_sha256),'exact original bank identities required')
        require(type(self.fold) is int and self.fold in range(5),'strict original held-fold index required')
        require(type(self.candidate_ids) is tuple and self.candidate_ids
            and all(_sha(v) for v in self.candidate_ids) and len(set(self.candidate_ids))==len(self.candidate_ids)
            and self.noop_candidate_id in self.candidate_ids,'exact unique candidate order and no-op required')
        require(type(self.original_nominal_sequence) is tuple and self.original_nominal_sequence
            and all(_text(v) for v in self.original_nominal_sequence),'authentic prior-through-current nominal sequence required')
        require(type(self.sample_count) is int and self.sample_count>=0,'full declared sample count required')


@dataclass(frozen=True)
class BankFeatures:
    candidate_ids: tuple[str,...]
    old_event_values: np.ndarray
    old_event_masks: np.ndarray
    candidates: tuple[progress.ProgressFeatures,...]


def _array(value,shape,dtype=np.float64):
    require(type(value) is np.ndarray and value.shape==shape and value.dtype==np.dtype(dtype)
        and np.isfinite(value).all(),'finite exact array shape/dtype required')
    return value


def _counts(value,k):
    require(type(value) is tuple and len(value)==4 and all(type(v) is int and v>=0 for v in value)
        and sum(value)==k,'full-case nonnegative integer paired counts required')


def _moment(moment,n,k,current_available):
    require(type(moment) is progress.Moments,'precomputed typed progress moments required')
    for field in ('current','joint','marginal','residual','marginal_residual','wa_offdiagonal'):
        _array(getattr(moment,field),(2,2,4))
    mask=_array(moment.mask,(n,),np.bool_)
    weights=_array(moment.weights,(2,n));opportunity=_array(moment.opportunity,(2,))
    similarities=_array(moment.similarities,(n,2))
    require(np.all(similarities>=0) and np.all(similarities<=1)
        and np.all(np.sum(similarities,axis=1)<=1),'fixed same/reverse similarity simplex required')
    expected_weights,expected_opportunity=progress.conditional_weights(mask)
    require(np.array_equal(weights,expected_weights) and np.array_equal(opportunity,expected_opportunity),
            'original full-position conditional weights required; no subset reweighting')
    require(type(moment.candidate_available) is bool and type(moment.candidate_mass) is int and moment.candidate_mass>=0
        and type(moment.history_masses) is tuple and len(moment.history_masses)==n
        and all(type(v) is int and v>=0 for v in moment.history_masses),'strict original edit availability/masses required')
    require(type(moment.permutation_indices) is tuple and len(moment.permutation_indices)==n
        and all(type(v) is int for v in moment.permutation_indices)
        and set(moment.permutation_indices)==set(range(n)),'exact supplied-history permutation required')
    require(type(moment.source_feedback_reasons) is tuple and len(moment.source_feedback_reasons)==n+1
        and all(v is None or _text(v) for v in moment.source_feedback_reasons),'explicit all-source feedback reasons required')
    require(type(moment.paired_counts) is tuple and len(moment.paired_counts)==n,'full transition count coverage required')
    if current_available:
        require(k>0,'known current feedback requires nonempty full suite')
        _counts(moment.current_counts,k)
        require(moment.current_counts[1:3]==(0,0),'current feedback must have diagonal counts only')
    else:
        require(moment.current_counts is None and not mask.any(),'unavailable current cannot supply conditional feedback')
    if not moment.candidate_available:require(not mask.any(),'AST-unavailable candidate cannot have eligible transitions')
    for t,pair in enumerate(moment.paired_counts):
        if mask[t]:
            _counts(pair,k)
            require(moment.source_feedback_reasons[t] is None and moment.source_feedback_reasons[t+1] is None,
                    'eligible transition has unavailable endpoint feedback')
        else:require(pair is None,'ineligible transition cannot expose paired counts')
    if not mask.any():
        require(all(not getattr(moment,field).any() for field in ('current','joint','marginal','residual',
            'marginal_residual','wa_offdiagonal')),'zero opportunity must have literal zero moments')


def _offdiagonal(spec,moment):
    """Scalar contribution using the ORIGINAL H weights; never renormalize WA."""
    nominal=[progress.directed.semantic._verdict(v) for v in spec.original_nominal_sequence]
    n=len(nominal)-1;witnesses=[];selected=[]
    for t in range(n):
        if moment.mask[t] and nominal[t:t+2]==['WA','WA']:
            pair=moment.paired_counts[t]
            if pair[1]+pair[2]>0:witnesses.append(t);selected.append(t)
    raw=np.zeros((2,2,4),dtype=np.float64)
    for w in range(2):
        for d in range(2):
            for state in (1,2):
                raw[w,d,state]=math.fsum(float(moment.weights[w,t]*moment.similarities[t,d]
                    *(moment.paired_counts[t][state]/spec.sample_count)) for t in selected)
    value=np.concatenate((np.zeros(16,dtype=np.float64),raw.reshape(-1)))/progress.SCALE
    require(np.array_equal(raw,moment.wa_offdiagonal),'WA off-diagonal moment differs from scalar original-weight decomposition')
    return value,tuple(witnesses)


def _candidate(spec,value):
    require(type(value) is progress.ProgressFeatures and isinstance(value.arms,Mapping) and set(value.arms)==set(ARMS)
        and isinstance(value.moments,Mapping) and set(value.moments)==set(MOMENT_ARMS),'all six precomputed arms/four moment scopes required')
    require(type(value.current_feedback_available) is bool and (value.current_feedback_reason is None
        if value.current_feedback_available else _text(value.current_feedback_reason)),'explicit current-feedback availability required')
    h=value.moments['H'];n=len(spec.original_nominal_sequence)-1
    for arm in MOMENT_ARMS:
        moment=value.moments[arm]
        count=n if arm in ('H','HS') else min(n,1) if arm=='L' else len(moment.mask)
        _moment(moment,count,spec.sample_count,value.current_feedback_available)
        require(moment.source_feedback_reasons[-1]==value.current_feedback_reason,'current feedback reason differs across scopes')
        require(moment.current_counts==h.current_counts,'current sample counts differ across scopes')
        require(moment.candidate_available==h.candidate_available and moment.candidate_mass==h.candidate_mass,
                'candidate edit availability/mass cannot differ across history scopes')
        if arm!='HS':require(moment.permutation_indices==tuple(range(count)),'authentic/donor/latest scope cannot be shuffled')
    for arm in ARMS:
        matrix=_array(value.arms[arm],(32,))
        residual=(np.zeros((2,2,4),dtype=np.float64) if arm=='CF' else
                  h.marginal_residual if arm=='Jm' else value.moments[arm].residual)
        expected=np.concatenate((h.current.reshape(-1),residual.reshape(-1)))/progress.SCALE
        require(np.array_equal(matrix,expected),'scaled arm differs from shared authentic G and its prescribed residual')
        if not value.current_feedback_available or not h.candidate_available:
            require(not matrix.any(),'unknown current or unavailable candidate must retain all-zero features')
    offdiag,witnesses=_offdiagonal(spec,h)
    require(np.array_equal(_array(value.wa_offdiagonal_contribution,(32,)),offdiag),
            'serialized WA contribution differs from original full-history scalar weights')
    return offdiag,witnesses


def _diagnostics(moment,k):
    eligible=[t for t,v in enumerate(moment.mask) if v]
    mass=[[math.fsum(float(moment.weights[w,t]*(moment.paired_counts[t][state]/k)) for t in eligible)
           for state in range(4)] for w in range(2)]
    return dict(transitions=len(moment.mask),eligible_transitions=len(eligible),
        opportunity=moment.opportunity.tolist(),candidate_available=moment.candidate_available,
        zero_opportunity=not eligible,singleton_opportunity=len(eligible)==1,
        constant_paired_distribution=bool(eligible) and len({moment.paired_counts[t] for t in eligible})==1,
        conditional_paired_state_mass=mass,source_feedback_reasons=list(moment.source_feedback_reasons))


def pair_geometry(matrices,old_values,old_masks,noop,offdiagonal):
    """All unordered candidate pairs; edited means neither endpoint is no-op."""
    require(isinstance(matrices,Mapping) and set(matrices)==set(ARMS),'all six candidate matrices required')
    n=len(matrices['H']);require(type(noop) is int and 0<=noop<n,'strict no-op index required')
    for value in matrices.values():_array(value,(n,32))
    _array(old_values,(n,18));_array(old_masks,(n,18),np.bool_);_array(offdiagonal,(n,32))
    require(np.all((old_values==0)|(old_values==1)),'old18 event values must be binary')
    effective=old_values*old_masks
    pairs=list(combinations(range(n),2));rows=[]
    for a,b in pairs:
        diffs={arm:matrices[arm][a]-matrices[arm][b] for arm in ARMS}
        variation={arm:float(np.max(np.abs(d))) for arm,d in diffs.items()}
        contrast={arm:float(np.max(np.abs(diffs['H']-diffs[arm]))) for arm in (*CONTROLS,'CF')}
        rows.append(dict(variation=variation,contrast=contrast,old_tie=bool(np.array_equal(effective[a],effective[b])),
            offdiagonal=float(np.max(np.abs(offdiagonal[a]-offdiagonal[b])))))
    def group(indices):
        chosen=[rows[i] for i in indices]
        return dict(pairs=len(chosen),varying_pairs={arm:sum(r['variation'][arm]>TOLERANCE for r in chosen) for arm in ARMS},
            contrast_pairs={arm:sum(r['contrast'][arm]>TOLERANCE for r in chosen) for arm in (*CONTROLS,'CF')},
            max_variation={arm:max((r['variation'][arm] for r in chosen),default=0.) for arm in ARMS},
            max_contrast={arm:max((r['contrast'][arm] for r in chosen),default=0.) for arm in (*CONTROLS,'CF')},
            old_masked18_tied_pairs=sum(r['old_tie'] for r in chosen),
            old_masked18_tie_H_split_pairs=sum(r['old_tie'] and r['variation']['H']>TOLERANCE for r in chosen),
            wa_offdiagonal_varying_pairs=sum(r['offdiagonal']>TOLERANCE for r in chosen),
            wa_offdiagonal_max_variation=max((r['offdiagonal'] for r in chosen),default=0.))
    return dict(all=group(range(len(pairs))),edited=group(i for i,(a,b) in enumerate(pairs) if noop not in (a,b)))


def bank_record(spec,features):
    require(type(spec) is BankSpec and type(features) is BankFeatures,'strict metadata/features records required')
    require(features.candidate_ids==spec.candidate_ids and type(features.candidates) is tuple
        and len(features.candidates)==len(spec.candidate_ids),'exact frozen candidate order/coverage required')
    offdiag=[];witnesses=[]
    for value in features.candidates:
        contribution,eligible=_candidate(spec,value);offdiag.append(contribution);witnesses.append(eligible)
    matrices={arm:np.stack([c.arms[arm] for c in features.candidates]) for arm in ARMS}
    noop=spec.candidate_ids.index(spec.noop_candidate_id)
    require(all(not x[noop].any() for x in matrices.values()),'original no-op must have exact zero32 vector')
    require(not offdiag[noop].any(),'no-op cannot discriminate progress')
    # Available parsed candidates have the same historical conditioning mask.
    for arm in MOMENT_ARMS:
        all_moments=[c.moments[arm] for c in features.candidates];first=all_moments[0]
        require(all(m.current_counts==first.current_counts and m.source_feedback_reasons==first.source_feedback_reasons
            and m.history_masses==first.history_masses and m.permutation_indices==first.permutation_indices
            for m in all_moments),'candidate-specific current/history source facts are forbidden')
        available=[c.moments[arm] for c in features.candidates if c.moments[arm].candidate_available]
        if available:require(all(np.array_equal(m.mask,available[0].mask)
            and m.paired_counts==available[0].paired_counts for m in available),
            'candidate-dependent historical eligibility or paired feedback is forbidden')
    progress_transitions=sorted({t for i,ts in enumerate(witnesses) if i!=noop for t in ts})
    geometry=pair_geometry(matrices,features.old_event_values,features.old_event_masks,noop,np.stack(offdiag))
    classes={arm:{} for arm in ARMS}
    for arm in ARMS:
        for cid,value in zip(spec.candidate_ids,matrices[arm],strict=True):classes[arm].setdefault(tuple(value),[]).append(cid)
    current=features.candidates[0]
    require(all(c.current_feedback_available==current.current_feedback_available and c.current_feedback_reason==current.current_feedback_reason
        for c in features.candidates),'bank candidates cannot alter current availability')
    return dict(example_id=spec.example_id,user_id=spec.user_id,problem_id=spec.problem_id,fold=spec.fold,
        bank_id=spec.bank_id,bank_seal_sha256=spec.bank_seal_sha256,candidate_ids=list(spec.candidate_ids),
        noop_candidate_id=spec.noop_candidate_id,sample_count=spec.sample_count,
        current_feedback_available=current.current_feedback_available,current_feedback_reason=current.current_feedback_reason,
        geometry=geometry,equivalence_classes={arm:list(groups.values()) for arm,groups in classes.items()},
        all_zero={arm:not bool(x.any()) for arm,x in matrices.items()},
        feature_equal_H={arm:bool(np.array_equal(matrices['H'],matrices[arm])) for arm in (*CONTROLS,'CF')},
        eligible_authentic_WA_WA_offdiagonal_transition_indices=progress_transitions,
        edited_candidate_progress_witnesses=[dict(candidate_id=spec.candidate_ids[i],transition_indices=list(ts))
            for i,ts in enumerate(witnesses) if i!=noop and ts],
        candidate_diagnostics=[dict(candidate_id=cid,arms={arm:_diagnostics(c.moments['H' if arm in ('Jm','CF') else arm],
            spec.sample_count) for arm in ARMS})
            for cid,c in zip(spec.candidate_ids,features.candidates,strict=True)])


def _aggregate(rows):
    groups={}
    for scope in ('all','edited'):
        values=[r['geometry'][scope] for r in rows]
        groups[scope]={key:sum(v[key] for v in values) for key in ('pairs','old_masked18_tied_pairs',
            'old_masked18_tie_H_split_pairs','wa_offdiagonal_varying_pairs')}
        groups[scope].update(varying_pairs={arm:sum(v['varying_pairs'][arm] for v in values) for arm in ARMS},
            contrast_pairs={arm:sum(v['contrast_pairs'][arm] for v in values) for arm in (*CONTROLS,'CF')},
            max_variation={arm:max((v['max_variation'][arm] for v in values),default=0.) for arm in ARMS},
            max_contrast={arm:max((v['max_contrast'][arm] for v in values),default=0.) for arm in (*CONTROLS,'CF')},
            wa_offdiagonal_max_variation=max((v['wa_offdiagonal_max_variation'] for v in values),default=0.))
    diagnostics={}
    for arm in ARMS:
        values=[c['arms'][arm] for r in rows for c in r['candidate_diagnostics']]
        diagnostics[arm]={key:sum(v[key] for v in values) for key in ('transitions','eligible_transitions',
            'candidate_available','zero_opportunity','singleton_opportunity','constant_paired_distribution')}
        diagnostics[arm].update(opportunity_sum=[math.fsum(v['opportunity'][w] for v in values) for w in range(2)],
            conditional_paired_state_mass_sum=[[math.fsum(v['conditional_paired_state_mass'][w][s] for v in values)
                for s in range(4)] for w in range(2)],
            unavailable_source_reason_instances=dict(Counter(reason for v in values
                for reason in v['source_feedback_reasons'] if reason is not None)))
    return dict(examples=len(rows),users=len({r['user_id'] for r in rows}),problems=len({r['problem_id'] for r in rows}),
        candidates=sum(len(r['candidate_ids']) for r in rows),example_ids=[r['example_id'] for r in rows],pairs=groups,
        current_feedback_available=sum(r['current_feedback_available'] for r in rows),
        current_unavailable_reasons=dict(Counter(r['current_feedback_reason'] for r in rows if not r['current_feedback_available'])),
        all_zero_banks={arm:sum(r['all_zero'][arm] for r in rows) for arm in ARMS},
        feature_equal_H_banks={arm:sum(r['feature_equal_H'][arm] for r in rows) for arm in (*CONTROLS,'CF')},
        banks_with_eligible_authentic_WA_WA_progress=sum(bool(r['eligible_authentic_WA_WA_offdiagonal_transition_indices']) for r in rows),
        authentic_WA_WA_progress_transitions=sum(len(r['eligible_authentic_WA_WA_offdiagonal_transition_indices']) for r in rows),
        candidate_diagnostics=diagnostics)


def _training_checks(train):
    allpairs=train['pairs']['all'];edited=train['pairs']['edited']
    return dict(condition1_edited_H_varies=edited['varying_pairs']['H']>0,
        condition2_old_masked18_edited_tie_split=edited['old_masked18_tie_H_split_pairs']>0,
        **{'condition3_contrast_'+arm:allpairs['contrast_pairs'][arm]>0 for arm in CONTROLS},
        condition4_edited_H_CF=edited['contrast_pairs']['CF']>0,
        condition5_eligible_edited_authentic_WA_WA_progress=train['authentic_WA_WA_progress_transitions']>0,
        condition6_edited_WA_WA_contribution_varies=edited['wa_offdiagonal_varying_pairs']>0)


def assess_readiness(frozen_specs,features_by_example):
    """Exact320 report; caller authenticates inputs, no fit release is granted."""
    require(type(frozen_specs) is tuple and len(frozen_specs)==COUNTS['examples']
        and all(type(s) is BankSpec for s in frozen_specs),'all original320 metadata records required')
    for field,count in (('example_id',320),('user_id',320),('bank_id',320),('problem_id',23)):
        require(len({getattr(s,field) for s in frozen_specs})==count,'fixed original '+field+' coverage differs')
    require(sum(len(s.candidate_ids) for s in frozen_specs)==COUNTS['candidates'],'all original2544 candidates required')
    require({s.fold for s in frozen_specs}==set(range(5)) and all(len({s.fold for s in frozen_specs if s.problem_id==p})==1
        for p in {s.problem_id for s in frozen_specs}),'five nonempty original problem-held folds required')
    require(all(len({s.sample_count for s in frozen_specs if s.problem_id==p})==1
        for p in {s.problem_id for s in frozen_specs}),'one complete sample universe size per problem required')
    require(isinstance(features_by_example,Mapping) and set(features_by_example)=={s.example_id for s in frozen_specs},
        'exact features-to-original-cohort equality required; no exclusions or additions')
    rows=[bank_record(s,features_by_example[s.example_id]) for s in frozen_specs]
    folds={str(f):dict(train=_aggregate([r for r in rows if r['fold']!=f]),
                      held=_aggregate([r for r in rows if r['fold']==f])) for f in range(5)}
    checks={}
    for f,parts in folds.items():
        checks[f]=_training_checks(parts['train'])
    return dict(kind=VERSION,protocol=PROTOCOL,arms=list(ARMS),dimension=32,tolerance=TOLERANCE,
        tolerance_units='scaled final coordinates; strict greater-than; descriptive only',rows=rows,totals=_aggregate(rows),
        folds=folds,prerequisites=checks,readiness_passed=all(all(c.values()) for c in checks.values()),
        excluded_examples=0,excluded_candidates=0,repair_labels_accessed=False,feature_generation_performed=False,
        execution_performed=False,fitting_performed=False,fit_release_authorized=False,
        authority='caller must authenticate original metadata, candidate features and accepted observed-only replay')
