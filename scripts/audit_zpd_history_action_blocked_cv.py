"""No-fit C2 verifier: separate matrix construction and saved-coefficient scoring.

Frozen C1 audit helpers reconstruct donors, cohorts, estimands and gate. This
module independently implements the new block transform/configuration and never
calls blocked driver fit, transform or prediction functions.
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
    sha, read, rows, write, equal, verify_seals, expected_folds, donor_keys,
    expected_donors, event_arrays, probabilities, losses, contrasts, gate,
    check_exposure_log, ARMS, CONTROLS, FOLD_SALT, STRATA)

ROOT = Path(__file__).resolve().parents[1]
KIND = 'train_only_history_action_blocked_cv_v1'
PROTOCOL = ROOT/'analysis_protocols/zpd-history-action-next-design-20260924.md'
RUN_PARENT = 'outputs/zpd-history-action-blocked-20260924'
C1_PARENT = 'outputs/zpd-history-action-20260923/run-v1'
C1_COMPLETE_SHA = '1d22b390dd88ee9655093c87c4f353acb1048330e542480c3f4f3f659489c07f'
SOURCES = {
    'scripts/run_zpd_history_action_blocked_cv.py','scripts/zpd_history_action_blocked.py',
    'scripts/audit_zpd_history_action_blocked_cv.py','scripts/audit_zpd_history_action_cv.py',
    'scripts/run_zpd_history_action_cv.py','scripts/zpd_history_action_encoder.py',
    'scripts/audit_zpd_history_support.py','scripts/prepare_zpd_train_successors.py',
    'scripts/build_zpd_original_prefixes.py','scripts/zpd_history_predictor.py',
    'scripts/zpd_repair_structure.py','scripts/zpd_repair_pairwise.py',
    'analysis_protocols/zpd-history-action-cv-20260923.md',
    'analysis_protocols/zpd-history-action-next-design-20260924.md'}
NUISANCE_KEYS = ('nuisance:prior_count_log1p','nuisance:elapsed_seconds_log1p',
    'nuisance:prior_source_bytes_log1p','nuisance:prior_token_count_log1p')


def representation():
    return dict(version='current_preserving_blocks_v1',feature_dimension=8196,
        current=dict(offset=0,dimension=4096,hashing='FeatureHasher_dict_float64_alternate_sign',normalization='row_L2'),
        nuisance=dict(offset=4096,dimension=4,keys=list(NUISANCE_KEYS),normalization='v_over_sqrt_1_plus_squared_L2'),
        history=dict(offset=4100,dimension=4096,hashing='FeatureHasher_dict_float64_alternate_sign',normalization='v_over_sqrt_1_plus_squared_L2'),
        final_normalization=False,semantic_encoder_version='full_history_immediate_edit_v1')


def radial_independent(x):
    result = x.tocsr(copy=True)
    result.sum_duplicates(); result.eliminate_zeros(); result.sort_indices()
    for i in range(result.shape[0]):
        lo, hi = result.indptr[i:i+2]
        values = result.data[lo:hi]
        if not len(values):
            continue
        # Stable hypot accumulation, distinct implementation from driver module.
        scale = max(1., float(np.max(np.abs(values))))
        denominator = math.hypot(1./scale, *[float(v/scale) for v in values])
        values[:] = (values/scale)/denominator
    if not np.isfinite(result.data).all():
        raise ValueError('nonfinite independently encoded block')
    return result


def radial_equality_flag(x):
    """Frozen float64 operation order, only for the exact H/HS equality flag.

    Main score verification still uses the independent hypot reduction. An
    exact-equality flag cannot use tolerance or assume norm reduction parity.
    """
    result = x.tocsr(copy=True)
    result.sum_duplicates(); result.eliminate_zeros(); result.sort_indices()
    for i in range(result.shape[0]):
        values = result.data[result.indptr[i]:result.indptr[i+1]]
        if not len(values):
            continue
        maximum = float(np.abs(values).max())
        if maximum >= 1.:
            values /= maximum
            values /= math.hypot(1./maximum,float(np.linalg.norm(values)))
        else:
            values /= math.sqrt(1.+float(values @ values))
    return result


def matrix(observations, held, arm, donors, encoder, *, return_flag_matrix=False):
    index = {o['example_id']:o for o in observations}
    blocks, bags, flag_blocks = [], [], []
    hasher = FeatureHasher(n_features=4096,input_type='dict',alternate_sign=True,dtype=np.float64)
    for position, i in enumerate(held):
        o = observations[i]
        base = encoder.encode_observation(o['current_code'],o['current_verdict'],o['history'],o['timestamp'],'Cn')
        if arm in ('U','L'):
            prior = index[donors[o['example_id']]]['history'] if arm == 'U' else o['history'][-1:]
            bag = encoder.encode_observation(o['current_code'],o['current_verdict'],prior,o['timestamp'],'H')
            bag.update(base)
        else:
            bag = encoder.encode_observation(o['current_code'],o['current_verdict'],o['history'],o['timestamp'],arm,shuffle_key=o['example_id'])
        bags.append(bag)
        if len(bags) == 512 or position == len(held)-1:
            current = [{k:v for k,v in b.items() if k.startswith('current:')} for b in bags]
            nuisance = [[b.get(k,0.) for k in NUISANCE_KEYS] for b in bags]
            history = [{k:v for k,v in b.items() if k.startswith('history:')} for b in bags]
            c = normalize(hasher.transform(current),norm='l2',axis=1,copy=False)
            n = radial_independent(sparse.csr_matrix(np.asarray(nuisance,dtype=float)))
            hashed_history = hasher.transform(history)
            h = radial_independent(hashed_history)
            if return_flag_matrix:
                flag_blocks.append(radial_equality_flag(hashed_history))
            blocks.append(sparse.hstack([c,n,h],format='csr')); bags=[]
    result = sparse.vstack(blocks,format='csr') if blocks else sparse.csr_matrix((0,8196))
    if return_flag_matrix:
        flags = sparse.vstack(flag_blocks,format='csr') if flag_blocks else sparse.csr_matrix((0,4096))
        return result,flags
    return result


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
                      for j,e in enumerate(events)} for c in ('C0','HS')}
    groups = {}
    for name, members in [('non_language_residual_16',set(events)-{'language_switch','other_lexical_change'}),
                          ('language_residual_2',{'language_switch','other_lexical_change'})]:
        indices = [j for j,e in enumerate(events) if e in members]
        reduced = [dict(p,values=[p['values'][j] for j in indices],mask=[p['mask'][j] for j in indices],
                        probabilities={a:[p['probabilities'][a][j] for j in indices] for a in ARMS}) for p in predictions]
        groups[name] = dict(events=[events[j] for j in indices],results=losses(reduced,[events[j] for j in indices])[0],
            additive_primary_mass={a:sum(totals[a][j] for j in indices) if totals[a][0] is not None else None for a in ARMS})
    return dict(kind='post_C1_diagnostic_not_advancement_endpoint',
        contribution_mass='all18_masked_prefix_mean_then_equal_user; contributions_sum_to_primary',
        events=contributions,H_minus_control_event_contributions=contrasts_out,groups=groups)


def check_parent(run, parent):
    parent = Path(parent)
    start = sha(parent/'COMPLETE.json')
    verify_seals(parent)
    for name in ('folds.json','COHORTS_COMPLETE.json','target-coverage.json'):
        equal(read(Path(run)/name),read(parent/name),'C1 exact '+name)
    maximum = 0.; checked = 0
    for fold in range(5):
        equal(read(Path(run)/f'fold-{fold}/cohort.json'),read(parent/f'fold-{fold}/cohort.json'),'C1 cohort')
        new = rows(Path(run)/f'fold-{fold}/predictions.jsonl')
        old = rows(parent/f'fold-{fold}/predictions.jsonl')
        if len(new) != len(old):
            raise ValueError('C1 prediction cohort length')
        for a,b in zip(new,old):
            for key in ('example_id','user_id','fold','donor_example_id','values','mask','target_status','next_language'):
                equal(a[key],b[key],'C1 prediction '+key)
            one,two = np.asarray(a['probabilities']['C0']),np.asarray(b['probabilities']['C0'])
            if not np.allclose(one,two,rtol=1e-10,atol=2e-12):
                raise ValueError('C1 exact-current prediction negative control failed')
            maximum = max(maximum,float(np.max(np.abs(one-two)))); checked += 1
    verify_seals(parent)
    if sha(parent/'COMPLETE.json') != start:
        raise ValueError('C1 parent changed during parity check')
    return dict(checked=True,complete_sha256=start,cohort_and_mask_exact=True,
                c0_predictions_checked=checked,c0_maximum_absolute_difference=maximum,rtol=1e-10,atol=2e-12)


def check_model(model, arm, fold, train, observations, values, masks, events):
    ids = [observations[i]['example_id'] for i in train]
    expected = dict(events=list(events), feature_dimension=8196, representation=representation(), alpha=1e-4, seed=2027, epochs=20,
        weighting='user_equal_prefix_mean_event_mask_no_head_renormalization', arm=arm, fold=fold, train_example_ids=ids)
    equal({k:v for k,v in model.items() if k != 'heads'}, expected, 'model configuration')
    if len(model['heads']) != len(events):
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
            if (any(type(v) not in (int,float) for v in head['coefficients'])
                    or type(head['intercept']) not in (int,float)
                    or coefficients.shape != (8196,) or not np.isfinite(coefficients).all() or not math.isfinite(head['intercept'])):
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
                raise ValueError('all six arm probabilities required')
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
    return dict(verified=True, experiment_complete_sha256=start_sha, model_folds_verified=30,
        source_population=len(observations), oof_prefixes=len(combined), oof_users=len(means['H']),
        target_coverage=target_coverage, decision=decision, results=overall, bootstrap_contrasts=intervals,
        parent_c1_negative_control=parent_parity, event_diagnostics=diagnostics(combined,encoder.EVENTS),
        refitting_performed=False, raw_release_opened=False, heldout_labels_opened=False,
        limitations=['Shared audited input loader and pure encoder define input/event semantics.',
                     'Coefficient rescoring verifies saved predictions, not an independent optimizer refit.',
                     'Developmental behavioral prediction is not repair or learner-benefit evidence.'])



def check_configuration(manifest, encoder):
    equal(manifest['configuration'],dict(arms=list(ARMS),events=list(encoder.EVENTS),folds=5,fold_salt=FOLD_SALT,
        representation=representation(),seed=2027,alpha=1e-4,epochs=20,controls=list(CONTROLS),probability_clip=1e-12,
        weighting='user_equal_prefix_mean_event_mask_no_head_renormalization',bootstrap_draws=5000,
        bootstrap_quantiles=[.00625,.99375]),'fixed blocked configuration')
    if (manifest.get('kind') != KIND or manifest.get('confirmatory') is not False
            or manifest.get('fresh_test_opened') is not False or set(manifest['source_sha256']) != SOURCES):
        raise ValueError('fixed blocked source closure required')


def canonical(path):
    path = Path(path).absolute()
    if path != path.resolve():
        raise ValueError('canonical path required')
    return path


def validate_paths(project, run, output):
    project,run,output = canonical(project),canonical(run),canonical(output)
    own_family = output.parent == project/RUN_PARENT
    supervised = (output.name == 'action-verified' and
        output.parent.parent == project/'outputs/zpd-method-continuation-20260924')
    if run.parent != project/RUN_PARENT or not (own_family or supervised):
        raise ValueError('fixed blocked run/audit family required')
    if output.exists() or output.is_symlink() or output.is_relative_to(run) or run.is_relative_to(output):
        raise ValueError('new nonoverlapping audit output required')
    return project,run,output


def audit(project, run, output):
    from scripts.run_zpd_history_action_cv import load_inputs
    from scripts import zpd_history_action_encoder as encoder
    project,run,output = validate_paths(project,run,output)
    marker = verify_seals(run); manifest = read(run/'manifest.json')
    check_configuration(manifest,encoder)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed verifier source required')
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if revision != manifest['source_revision']:
        raise ValueError('experiment/verifier revision mismatch')
    source_bindings = {}
    for name,expected in manifest['source_sha256'].items():
        path = ROOT/name
        if path.resolve() != path or sha(path) != expected:
            raise ValueError('source/protocol mismatch')
        source_bindings[path] = expected
    if source_bindings.get(PROTOCOL) != manifest['protocol_sha256']:
        raise ValueError('protocol source binding absent')
    runtime = {name:version(name) for name in ('numpy','scipy','scikit-learn')}
    runtime['python'] = platform.python_version()
    equal(manifest['runtime'],runtime,'runtime')
    parent = project/C1_PARENT
    if sha(parent/'COMPLETE.json') != C1_COMPLETE_SHA:
        raise ValueError('wrong pinned C1 parent')
    parent_marker = verify_seals(parent)
    equal(manifest['parent_c1'],dict(path=str(parent),complete_sha256=C1_COMPLETE_SHA,
          c0_prediction_parity_rtol=1e-10,c0_prediction_parity_atol=2e-12),'C1 negative control binding')
    observations,targets,coverage,bindings = load_inputs(project)
    bindings[parent/'COMPLETE.json'] = C1_COMPLETE_SHA
    bindings.update({parent/name:digest for name,digest in parent_marker['files_sha256'].items()})
    equal(manifest['coverage'],coverage,'sealed full input coverage')
    equal(manifest['input_sha256'],{str(p):digest for p,digest in bindings.items()},'input bindings')
    output.mkdir(parents=True); started=time.time()
    verifier_sha = sha(__file__); helper_sha = sha(ROOT/'scripts/audit_zpd_history_action_cv.py')
    def progress(fields):
        write(output/'STATUS.json',dict(fields,elapsed_seconds=time.time()-started))
    try:
        result = audit_data(run,observations,targets,encoder,progress=progress,parent_run=parent)
        for path,expected in {**bindings,**source_bindings}.items():
            if sha(path) != expected:
                raise ValueError('input/source changed during verification')
        verify_seals(run)
        if sha(run/'COMPLETE.json') != result['experiment_complete_sha256']:
            raise ValueError('run changed before audit seal')
        result.update(source_revision=revision,verifier_sha256=verifier_sha,helper_sha256=helper_sha,
                      elapsed_seconds=time.time()-started,experiment_report_sha256=marker['files_sha256']['report.json'])
        write(output/'report.json',result);progress(dict(phase='complete',verified=True))
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
