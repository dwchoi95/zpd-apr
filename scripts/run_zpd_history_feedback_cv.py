"""Fixed C3 coupling crossfit with a separately pinned production release.

The supplied-input engine is independently testable. The CLI delegates all
real-data provenance and release checks to the reviewed production guard.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
from scripts import zpd_history_feedback_coupling as coupling
from scripts import zpd_history_feedback_heads as heads
from scripts import zpd_history_action_encoder as semantic
from scripts.run_zpd_history_action_cv import (
    sha, read, rows, atomic_json, atomic_rows, _check, load_inputs, assign_folds,
    fold_cohorts, encode_targets, FOLDS, FOLD_SALT, SEED, EPOCHS, ALPHA, BOOTSTRAP_DRAWS)
from scripts.zpd_history_feedback_coupling import encode_matrix
from scripts.zpd_history_feedback_heads import fit_heads, predict_heads

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'analysis_protocols/zpd-history-next-mechanism-design-20260924.md'
KIND = 'train_only_history_feedback_coupling_cv_v1'
OUTPUT_PARENT = 'outputs/zpd-history-feedback-coupling-20260924'
ARMS = ('C0','Cn','H','U','HS','L','Jm')
CONTROLS = ('Cn','U','HS','L','Jm')
SUPPORT_COMPLETE_SHA = '106bd5a07b8c262d0fddbf780ccd998bb859582e1811affa1c299bb8bcc15dc3'
RELEASE_RELATIVE = 'analysis_protocols/zpd-history-feedback-fit-release-20260924.json'
C2_PARENT = 'outputs/zpd-history-action-blocked-20260924/run-v1'
C2_COMPLETE_SHA = '3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690'
SOURCE_FILES = (
    'scripts/run_zpd_history_feedback_cv.py','scripts/zpd_history_feedback_coupling.py',
    'scripts/zpd_history_feedback_heads.py','scripts/audit_zpd_history_feedback_cv.py',
    'scripts/audit_zpd_history_action_blocked_cv.py','scripts/audit_zpd_history_action_cv.py',
    'scripts/audit_zpd_history_feedback_support.py','scripts/supervise_zpd_history_action.py',
    'scripts/run_zpd_history_action_cv.py','scripts/zpd_history_action_encoder.py',
    'scripts/zpd_history_action_blocked.py','scripts/audit_zpd_history_support.py',
    'scripts/prepare_zpd_train_successors.py','scripts/build_zpd_original_prefixes.py',
    'scripts/zpd_history_predictor.py','scripts/zpd_repair_structure.py',
    'scripts/zpd_repair_pairwise.py','analysis_protocols/zpd-history-next-mechanism-design-20260924.md',
    RELEASE_RELATIVE)


def summarize_predictions(predictions, events):
    """Prefix masked mean -> mean prefixes per user -> equal mean users."""
    output={}; user_losses={}
    for arm in ARMS:
        by_user=defaultdict(list); event_users={name:defaultdict(list) for name in events}
        event_rows=Counter(); event_positive=Counter(); all_masked=0
        for row in predictions:
            y=np.asarray(row['values'], dtype=float); mask=np.asarray(row['mask'], dtype=bool)
            p=np.asarray(row['probabilities'][arm], dtype=float)
            if (y.shape != (len(events),) or mask.shape != y.shape or p.shape != y.shape or
                not np.isfinite(p).all() or (p<0).any() or (p>1).any() or not np.isin(y[mask],[0.,1.]).all()):
                raise ValueError('strict finite masked prediction schema required')
            p=np.clip(p,1e-12,1.-1e-12)
            loss=-(y*np.log(p)+(1-y)*np.log1p(-p))
            if mask.any():
                by_user[row['user_id']].append(float(loss[mask].mean()))
            else:
                all_masked+=1
            for j,name in enumerate(events):
                if mask[j]:
                    event_users[name][row['user_id']].append(float(loss[j])); event_rows[name]+=1; event_positive[name]+=int(y[j])
        user_losses[arm]={user:float(np.mean(values)) for user,values in sorted(by_user.items())}
        output[arm]=dict(user_equal_masked_nll=float(np.mean(list(user_losses[arm].values()))) if by_user else None,
            users=len(by_user), evaluable_prefixes=len(predictions)-all_masked, all_masked_prefixes=all_masked,
            events={name:dict(prefixes=event_rows[name], users=len(event_users[name]), positive_prefixes=event_positive[name],
                user_equal_nll=float(np.mean([np.mean(v) for v in event_users[name].values()])) if event_users[name] else None)
                for name in events})
    return output, user_losses


def bootstrap_contrasts(user_losses):
    draws = BOOTSTRAP_DRAWS
    users=sorted(user_losses['H'])
    if any(set(user_losses[c]) != set(users) for c in CONTROLS):
        raise ValueError('paired user coverage mismatch')
    if len(users)<2:
        return {c:dict(status='insufficient_users', users=len(users), upper=None, lower=None) for c in CONTROLS}
    differences=np.asarray([[user_losses['H'][u]-user_losses[c][u] for c in CONTROLS] for u in users])
    rng=np.random.default_rng(SEED); samples=[]
    for begin in range(0,draws,100):
        indices=rng.integers(0,len(users),size=(min(100,draws-begin),len(users)))
        samples.append(differences[indices].mean(axis=1))
    distribution=np.vstack(samples); lower,upper=np.quantile(distribution,[.05/(2*len(CONTROLS)),1-.05/(2*len(CONTROLS))],axis=0)
    return {c:dict(status='descriptive_crossfit_bootstrap', users=len(users), draws=draws, seed=SEED,
        mean=float(differences[:,j].mean()), lower=float(lower[j]), upper=float(upper[j]),
        interval='two-sided Bonferroni99percent percentile; five prespecified contrasts; not confirmatory')
        for j,c in enumerate(CONTROLS)}


def decision(overall, folds, intervals):
    checks={}
    h=overall['H']['user_equal_masked_nll']
    for c in CONTROLS:
        lower=sum(f['H']['user_equal_masked_nll'] is not None and f[c]['user_equal_masked_nll'] is not None and
                  f['H']['user_equal_masked_nll'] < f[c]['user_equal_masked_nll'] for f in folds.values())
        other=overall[c]['user_equal_masked_nll']; upper=intervals[c]['upper']
        checks[c]=dict(aggregate_strictly_better=h is not None and other is not None and h<other,
            strictly_better_folds=lower, at_least_four_folds=lower>=4,
            simultaneous_upper_below_zero=upper is not None and upper<0)
    passed=len(folds)==FOLDS and all(v['aggregate_strictly_better'] and v['at_least_four_folds'] and
                                   v['simultaneous_upper_below_zero'] for v in checks.values())
    return dict(gate_passed=passed, checks=checks, confirmatory=False, learner_benefit_established=False,
                next_action='independent_result_audit_then_separately_frozen_repair_integration' if passed else
                'retain_negative_result_and_diagnose_train_only', full_train_refit_authorized=False)



def event_diagnostics(predictions, events):
    """Same all-event prefix/user mass: event contributions sum to primary NLL."""
    per_arm = {arm:defaultdict(list) for arm in ARMS}
    for row in predictions:
        y = np.asarray(row['values'], dtype=float)
        mask = np.asarray(row['mask'], dtype=bool)
        if not mask.any():
            continue
        for arm in ARMS:
            p = np.clip(np.asarray(row['probabilities'][arm],dtype=float), 1e-12, 1-1e-12)
            terms = -(y*np.log(p)+(1-y)*np.log1p(-p))*mask/int(mask.sum())
            per_arm[arm][row['user_id']].append(terms)
    terms = {arm:np.mean([np.mean(v,axis=0) for v in users.values()],axis=0).tolist()
             if users else [None]*len(events) for arm,users in per_arm.items()}
    groups = {'non_language_residual_16':[i for i,e in enumerate(events)
                  if e not in ('language_switch','other_lexical_change')],
              'language_residual_2':[i for i,e in enumerate(events)
                  if e in ('language_switch','other_lexical_change')]}
    contribution = {e:{arm:terms[arm][i] for arm in ARMS} for i,e in enumerate(events)}
    contrasts = {control:{e:(terms['H'][i]-terms[control][i]) if terms['H'][i] is not None else None
                          for i,e in enumerate(events)} for control in ('C0','HS','Jm')}
    subgroup = {}
    for name, indices in groups.items():
        reduced = [dict(row, values=[row['values'][i] for i in indices],mask=[row['mask'][i] for i in indices],
                        probabilities={a:[row['probabilities'][a][i] for i in indices] for a in ARMS})
                   for row in predictions]
        summary,_ = summarize_predictions(reduced, [events[i] for i in indices])
        subgroup[name] = dict(events=[events[i] for i in indices], results=summary,
            additive_primary_mass={a:sum(terms[a][i] for i in indices) if terms[a][0] is not None else None for a in ARMS})
    return dict(kind='post_C2_diagnostic_not_advancement_endpoint',
        contribution_mass='all18_masked_prefix_mean_then_equal_user; contributions_sum_to_primary',
        events=contribution, H_minus_control_event_contributions=contrasts, groups=subgroup)


def run_data(observations, targets, output, encoder=semantic, *, manifest, bindings=None):
    """Supplied-input engine; production authorization belongs to frozen entrypoint."""
    output=Path(output)
    if output.exists():
        raise FileExistsError('new output required; no automatic resume of partial runs')
    if encoder is not semantic:
        raise ValueError('frozen semantic encoder required')
    if list(encoder.EVENTS) != list(semantic.EVENTS):
        raise ValueError('all eighteen fixed events required')
    bindings=bindings or {}
    _check(bindings)
    output.mkdir(parents=True); started=time.time()
    def event(value):
        value=dict(value, elapsed_seconds=time.time()-started, timestamp=time.time())
        with (output/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n'); stream.flush(); os.fsync(stream.fileno())
        atomic_json(output/'STATUS.json',value)
        print(json.dumps(value,sort_keys=True),flush=True)
    atomic_json(output/'manifest.json',manifest)
    assignment=assign_folds(observations); atomic_json(output/'folds.json',assignment)
    # Matching is sealed before even encoding future targets. It depends on the
    # full observed training population, not source/event/target availability.
    cohorts={fold:fold_cohorts(observations,assignment,fold) for fold in range(FOLDS)}
    total_oof_supported=sum(len(value[1]) for value in cohorts.values())
    cohort_seals={}
    for fold,(train,held,donors) in cohorts.items():
        frozen=dict(train_example_ids=[observations[i]['example_id'] for i in train],
                    held_example_ids=[observations[i]['example_id'] for i in held],donor_assignments=donors)
        cohort_seals[str(fold)]=hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    atomic_json(output/'COHORTS_COMPLETE.json',dict(status='observed_only_cohorts_sealed_before_target_encoding',
        fold_cohort_sha256=cohort_seals,total_oof_supported=total_oof_supported))
    event(dict(phase='encode_training_targets', total_examples=len(observations)))
    y,mask=encode_targets(observations,targets,encoder,callback=event)
    atomic_json(output/'target-coverage.json',dict(prefixes=len(observations),all_masked=int((~mask.any(axis=1)).sum()),
        next_languages=dict(Counter(targets[o['example_id']]['next_language'] or 'unavailable' for o in observations)),
        target_status=dict(Counter(targets[o['example_id']]['target_status'] for o in observations)),
        mask_patterns=dict(Counter(''.join('1' if v else '0' for v in row) for row in mask)),
        events={name:dict(observed=int(mask[:,i].sum()),positive=int(y[mask[:,i],i].sum())) for i,name in enumerate(encoder.EVENTS)}))
    # Pure observation features can be shared across folds: no fitted transform,
    # labels, vocabulary, corpus frequencies or normalization across rows exist.
    cache={arm:encode_matrix(observations,np.arange(len(observations)),arm,callback=event)
           for arm in ('C0','Cn','H','HS','L','Jm')}
    equal_history_features=np.asarray((cache['H']-cache['HS']).getnnz(axis=1)==0).reshape(-1)
    all_predictions=[]; fold_summaries={}; fold_coverage={}; artifacts=['manifest.json','folds.json','COHORTS_COMPLETE.json','target-coverage.json']
    for fold in range(FOLDS):
        directory=output/f'fold-{fold}'; directory.mkdir()
        train,held,donors=cohorts[fold]
        if not len(train) or not len(held):
            raise ValueError('empty fold donor-supported train/held cohort; no substitution')
        cohort=dict(fold=fold,train_example_ids=[observations[i]['example_id'] for i in train],
            held_example_ids=[observations[i]['example_id'] for i in held],donor_assignments=donors,
            original_train_prefixes=sum(v!=fold for v in assignment['example_fold'].values()),
            original_held_prefixes=sum(v==fold for v in assignment['example_fold'].values()),
            train_prefixes=len(train),held_prefixes=len(held),
            train_all_masked=int((~mask[train].any(axis=1)).sum()),held_all_masked=int((~mask[held].any(axis=1)).sum()))
        atomic_json(directory/'cohort.json',cohort); fold_coverage[str(fold)]={k:v for k,v in cohort.items() if k not in ('train_example_ids','held_example_ids','donor_assignments')}
        probabilities={}; files=['cohort.json']
        for arm in ARMS:
            event(dict(phase='arm_start',fold=fold,arm=arm,train_prefixes=len(train),held_prefixes=len(held)))
            if arm=='U':
                joined=np.concatenate([train,held])
                x=encode_matrix(observations,joined,arm,donors=donors,
                    callback=lambda v:event(dict(v,fold=fold)))
                xt,xh=x[:len(train)],x[len(train):]
            else:
                xt,xh=cache[arm][train],cache[arm][held]
            model=fit_heads(xt,y[train],mask[train],[observations[i]['user_id'] for i in train],encoder.EVENTS,
                            callback=lambda v:event(dict(v,fold=fold,arm=arm)))
            model.update(arm=arm,fold=fold,train_example_ids=cohort['train_example_ids'])
            atomic_json(directory/f'{arm}.json',model); files.append(f'{arm}.json')
            probabilities[arm]=predict_heads(model,xh)
        train_keys={(observations[i]['problem_id'],observations[i]['current_source_sha256']) for i in train}
        collision=defaultdict(list)
        for i in held:
            o=observations[i]
            hist=hashlib.sha256(json.dumps([(h['code'],h['verdict']) for h in o['history']],separators=(',',':')).encode()).hexdigest()
            collision[o['problem_id'],o['current_source_sha256']].append((o['user_id'],hist))
        distinct={key for key,values in collision.items() if len({u for u,h in values})>1 and len({h for u,h in values})>1}
        predictions=[]
        for j,i in enumerate(held):
            o=observations[i]; key=(o['problem_id'],o['current_source_sha256'])
            predictions.append(dict(example_id=o['example_id'],user_id=o['user_id'],problem_id=o['problem_id'],fold=fold,
                donor_example_id=donors[o['example_id']],values=y[i].tolist(),mask=mask[i].tolist(),
                target_status=targets[o['example_id']]['target_status'],next_language=targets[o['example_id']]['next_language'],
                current_source_sha256=o['current_source_sha256'],current_seen_in_fold_training=key in train_keys,
                within_held_cross_user_distinct_history_collision=key in distinct,
                hs_prior_length_one=len(o['history'])==1,
                hs_permutation_identity=tuple(encoder.permutation_indices(len(o['history']),o['example_id']))==tuple(range(len(o['history']))),
                hs_hashed_features_equal=bool(equal_history_features[i]),
                probabilities={arm:probabilities[arm][j].tolist() for arm in ARMS}))
        atomic_rows(directory/'predictions.jsonl',predictions);files.append('predictions.jsonl')
        summary,_=summarize_predictions(predictions,encoder.EVENTS); fold_summaries[str(fold)]=summary
        atomic_json(directory/'summary.json',summary);files.append('summary.json')
        atomic_json(directory/'COMPLETE.json',dict(status='complete',fold=fold,files_sha256={f:sha(directory/f) for f in files}))
        artifacts += [f'fold-{fold}/'+f for f in files+['COMPLETE.json']]
        all_predictions.extend(predictions)
        _check(bindings)
        event(dict(phase='fold_complete',fold=fold,completed_folds=fold+1,total_folds=FOLDS,
                   completed_oof_prefixes=len(all_predictions),total_oof_supported=total_oof_supported,
                   total_training_prefixes=len(observations)))
    if len({p['example_id'] for p in all_predictions})!=len(all_predictions):
        raise ValueError('OOF prefix predicted twice')
    overall,user_losses=summarize_predictions(all_predictions,encoder.EVENTS)
    intervals=bootstrap_contrasts(user_losses)
    strata={name:summarize_predictions([p for p in all_predictions if p[name]],encoder.EVENTS)[0]
            for name in ('current_seen_in_fold_training','within_held_cross_user_distinct_history_collision',
                         'hs_prior_length_one','hs_permutation_identity','hs_hashed_features_equal')}
    report=dict(kind=KIND,confirmatory=False,fresh_test_opened=False,
        events=list(encoder.EVENTS),results=overall,fold_results=fold_summaries,fold_coverage=fold_coverage,
        bootstrap_contrasts=intervals,decision=decision(overall,fold_summaries,intervals),strata=strata,
        representation=coupling.configuration(), event_diagnostics=event_diagnostics(all_predictions,encoder.EVENTS),
        source_population=len(observations),oof_donor_supported_prefixes=len(all_predictions),
        oof_users=len({p['user_id'] for p in all_predictions}),total_oof_supported=total_oof_supported,
        note='Observed next-action prediction only; no repair or educational-learning superiority claim.')
    _check(bindings)
    atomic_json(output/'report.json',report); artifacts.append('report.json')
    event(dict(phase='complete',completed_folds=FOLDS,completed_oof_prefixes=len(all_predictions),
               total_oof_supported=total_oof_supported,gate_passed=report['decision']['gate_passed']))
    artifacts += ['events.jsonl','STATUS.json']
    _check(bindings)
    atomic_json(output/'COMPLETE.json',dict(status='complete',gate_passed=report['decision']['gate_passed'],
        files_sha256={f:sha(output/f) for f in artifacts},confirmatory=False,completed_folds=FOLDS,completed_arms=FOLDS*len(ARMS)))
    return report



def expected_configuration():
    return dict(arms=list(ARMS),events=list(semantic.EVENTS),folds=FOLDS,fold_salt=FOLD_SALT,
        representation=coupling.configuration(),seed=SEED,alpha=ALPHA,epochs=EPOCHS,
        controls=list(CONTROLS),probability_clip=1e-12,
        weighting=heads.WEIGHTING,bootstrap_draws=BOOTSTRAP_DRAWS,
        bootstrap_quantiles=[.05/(2*len(CONTROLS)),1-.05/(2*len(CONTROLS))])


def canonical(path):
    value = Path(path).absolute()
    if value != value.resolve():
        raise ValueError('canonical path without symlink aliases required')
    return value


def verify_run_artifacts(output):
    # The separate verifier owns exact seven-arm artifact inventories.
    from scripts.audit_zpd_history_feedback_cv import verify_seals
    output = canonical(output)
    marker = verify_seals(output)
    report = read(output/'report.json')
    if (report.get('kind') != KIND or report.get('representation') != coupling.configuration()
            or marker.get('gate_passed') != report['decision']['gate_passed']):
        raise ValueError('feedback report/completion mismatch')
    for fold in range(FOLDS):
        for arm in ARMS:
            model = heads.validate_model(read(output/f'fold-{fold}/{arm}.json'))
            if model['arm'] != arm or model['fold'] != fold:
                raise ValueError('model artifact identity mismatch')
    return marker


def run_cv(project, output, *, support, support_complete_sha256, release):
    """No caller checksum or command-line flag can replace the frozen release."""
    from scripts.zpd_history_feedback_release import run_released_cv
    return run_released_cv(project,output,support=support,
        support_complete_sha256=support_complete_sha256,release=release)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--support',required=True,type=Path)
    parser.add_argument('--support-complete-sha256',required=True)
    parser.add_argument('--release',required=True,type=Path)
    args = parser.parse_args(argv)
    return run_cv(args.project,args.output,support=args.support,
        support_complete_sha256=args.support_complete_sha256,release=args.release)


if __name__ == '__main__':
    main()
