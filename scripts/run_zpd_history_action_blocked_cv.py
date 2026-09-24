"""C2 fixed blocked-representation crossfit; no frozen-module mutation."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
from scripts import zpd_history_action_blocked as blocked
from scripts import zpd_history_action_encoder as semantic
from scripts import run_zpd_history_action_cv as legacy
from scripts.run_zpd_history_action_cv import (
    sha, read, rows, atomic_json, atomic_rows, _check, load_inputs, assign_folds,
    fold_cohorts, encode_targets, summarize_predictions, bootstrap_contrasts,
    decision, ARMS, CONTROLS, FOLDS, FOLD_SALT, SEED, EPOCHS, ALPHA, BOOTSTRAP_DRAWS)
from scripts.zpd_history_action_blocked import encode_matrix, fit_heads, predict_heads

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'analysis_protocols/zpd-history-action-next-design-20260924.md'
KIND = 'train_only_history_action_blocked_cv_v1'
OUTPUT_PARENT = 'outputs/zpd-history-action-blocked-20260924'
SOURCE_FILES = (
    'scripts/run_zpd_history_action_blocked_cv.py', 'scripts/zpd_history_action_blocked.py',
    'scripts/audit_zpd_history_action_blocked_cv.py', 'scripts/audit_zpd_history_action_cv.py',
    'scripts/run_zpd_history_action_cv.py', 'scripts/zpd_history_action_encoder.py',
    'scripts/audit_zpd_history_support.py', 'scripts/prepare_zpd_train_successors.py',
    'scripts/build_zpd_original_prefixes.py', 'scripts/zpd_history_predictor.py',
    'scripts/zpd_repair_structure.py', 'scripts/zpd_repair_pairwise.py',
    'analysis_protocols/zpd-history-action-cv-20260923.md',
    'analysis_protocols/zpd-history-action-next-design-20260924.md')
C1_PARENT = 'outputs/zpd-history-action-20260923/run-v1'
C1_COMPLETE_SHA = '1d22b390dd88ee9655093c87c4f353acb1048330e542480c3f4f3f659489c07f'


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
                          for i,e in enumerate(events)} for control in ('C0','HS')}
    subgroup = {}
    for name, indices in groups.items():
        reduced = [dict(row, values=[row['values'][i] for i in indices],mask=[row['mask'][i] for i in indices],
                        probabilities={a:[row['probabilities'][a][i] for i in indices] for a in ARMS})
                   for row in predictions]
        summary,_ = summarize_predictions(reduced, [events[i] for i in indices])
        subgroup[name] = dict(events=[events[i] for i in indices], results=summary,
            additive_primary_mass={a:sum(terms[a][i] for i in indices) if terms[a][0] is not None else None for a in ARMS})
    return dict(kind='post_C1_diagnostic_not_advancement_endpoint',
        contribution_mass='all18_masked_prefix_mean_then_equal_user; contributions_sum_to_primary',
        events=contribution, H_minus_control_event_contributions=contrasts, groups=subgroup)


def run_data(observations, targets, output, encoder, *, manifest, bindings=None):
    """Synthetic-testable engine. Real runs call run_cv for provenance checks."""
    output=Path(output)
    if output.exists():
        raise FileExistsError('new output required; no automatic resume of partial runs')
    output.mkdir(parents=True); started=time.time(); bindings=bindings or {}
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
    cache={arm:encode_matrix(observations,np.arange(len(observations)),arm,encoder,callback=event)
           for arm in ('C0','Cn','H','HS','L')}
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
                x=encode_matrix(observations,joined,arm,encoder,donors=donors,
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
        representation=blocked.configuration(), event_diagnostics=event_diagnostics(all_predictions,encoder.EVENTS),
        source_population=len(observations),oof_donor_supported_prefixes=len(all_predictions),
        oof_users=len({p['user_id'] for p in all_predictions}),total_oof_supported=total_oof_supported,
        note='Observed next-action prediction only; no repair or educational-learning superiority claim.')
    _check(bindings)
    atomic_json(output/'report.json',report); artifacts.append('report.json')
    event(dict(phase='complete',completed_folds=FOLDS,completed_oof_prefixes=len(all_predictions),
               total_oof_supported=total_oof_supported,gate_passed=report['decision']['gate_passed']))
    artifacts += ['events.jsonl','STATUS.json']
    atomic_json(output/'COMPLETE.json',dict(status='complete',gate_passed=report['decision']['gate_passed'],
        files_sha256={f:sha(output/f) for f in artifacts},confirmatory=False,completed_folds=FOLDS,completed_arms=FOLDS*len(ARMS)))
    return report



def expected_configuration():
    return dict(arms=list(ARMS),events=list(semantic.EVENTS),folds=FOLDS,fold_salt=FOLD_SALT,
        representation=blocked.configuration(),seed=SEED,alpha=ALPHA,epochs=EPOCHS,
        controls=list(CONTROLS),probability_clip=1e-12,
        weighting=blocked.WEIGHTING,bootstrap_draws=BOOTSTRAP_DRAWS,
        bootstrap_quantiles=[.05/(2*len(CONTROLS)),1-.05/(2*len(CONTROLS))])


def canonical(path):
    value = Path(path).absolute()
    if value != value.resolve():
        raise ValueError('canonical path without symlink aliases required')
    return value


def verify_run_artifacts(output):
    # This helper validates inventories, not C1's 4096 model semantics.
    from scripts.audit_zpd_history_action_cv import verify_seals
    output = canonical(output)
    marker = verify_seals(output)
    report = read(output/'report.json')
    if (report.get('kind') != KIND or report.get('representation') != blocked.configuration()
            or marker.get('gate_passed') != report['decision']['gate_passed']):
        raise ValueError('blocked report/completion mismatch')
    for fold in range(FOLDS):
        for arm in ARMS:
            model = blocked.validate_model(read(output/f'fold-{fold}/{arm}.json'))
            if model['arm'] != arm or model['fold'] != fold:
                raise ValueError('model artifact identity mismatch')
    return marker


def run_cv(project, output):
    project, output = canonical(project), canonical(output)
    if output.parent != project/OUTPUT_PARENT:
        raise ValueError('canonical blocked output parent required')
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed source checkout required')
    if not PROTOCOL.is_file():
        raise ValueError('frozen blocked protocol missing')
    versions = {name:version(name) for name in ('numpy','scipy','scikit-learn')}
    if versions != {'numpy':'2.5.2','scipy':'1.18.1','scikit-learn':'1.9.0'}:
        raise ValueError('frozen numerical runtime mismatch')
    observations, targets, coverage, bindings = load_inputs(project)
    from scripts.audit_zpd_history_action_cv import verify_seals
    parent = project/C1_PARENT
    if sha(parent/'COMPLETE.json') != C1_COMPLETE_SHA:
        raise ValueError('wrong pinned C1 parent')
    parent_seal = verify_seals(parent)
    bindings[parent/'COMPLETE.json'] = C1_COMPLETE_SHA
    bindings.update({parent/name:digest for name,digest in parent_seal['files_sha256'].items()})
    sources = [ROOT/name for name in SOURCE_FILES]
    bindings.update({path:sha(path) for path in sources})
    manifest = dict(kind=KIND,confirmatory=False,fresh_test_opened=False,
        source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={str(path.relative_to(ROOT)):sha(path) for path in sources},
        input_sha256={str(path):digest for path,digest in bindings.items() if path not in sources},
        protocol_sha256=sha(PROTOCOL),runtime=dict(versions,python=platform.python_version()),
        parent_c1=dict(path=str(parent),complete_sha256=C1_COMPLETE_SHA,
            c0_prediction_parity_rtol=1e-10,c0_prediction_parity_atol=2e-12),
        coverage=coverage,configuration=expected_configuration(),
        feature_target_boundary='Observed-code whitelist only; immediate future code enters encode_edit labels only.')
    try:
        report = run_data(observations,targets,output,semantic,manifest=manifest,bindings=bindings)
    except Exception as error:
        if output.is_dir() and not (output/'COMPLETE.json').exists():
            atomic_json(output/'STATUS.json',dict(phase='failed',error_type=type(error).__name__,
                error=str(error),timestamp=time.time()))
        raise
    verify_run_artifacts(output)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args(argv)
    report = run_cv(args.project,args.output)
    print(json.dumps(report['decision'],sort_keys=True))
    return report


if __name__ == '__main__':
    main()
