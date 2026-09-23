"""Independent, no-refit verification of the frozen C1 crossfit artifacts.

The audited train-only loader and pure versioned encoder define input/event
semantics. Donors, cohorts, model metadata, coefficient scoring, estimands and
advancement decisions are reconstructed here, not with driver result helpers.
This does not establish optimizer correctness, repair benefit or learner benefit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import heapq
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.feature_extraction import FeatureHasher
from sklearn.preprocessing import normalize

ROOT = Path(__file__).resolve().parents[1]
ARMS = ('C0', 'Cn', 'H', 'U', 'HS', 'L')
CONTROLS = ('Cn', 'U', 'HS', 'L')
FOLD_SALT = 'history-action-cv-20260923-v1'
STRATA = ('current_seen_in_fold_training', 'within_held_cross_user_distinct_history_collision',
          'hs_prior_length_one', 'hs_permutation_identity', 'hs_hashed_features_equal')
MODEL_FILES = ['cohort.json', *[a+'.json' for a in ARMS], 'predictions.jsonl', 'summary.json']
SOURCES = {'scripts/run_zpd_history_action_cv.py', 'scripts/zpd_history_action_encoder.py',
           'scripts/audit_zpd_history_support.py', 'scripts/prepare_zpd_train_successors.py',
           'scripts/build_zpd_original_prefixes.py', 'scripts/zpd_history_predictor.py',
           'scripts/zpd_repair_structure.py', 'scripts/zpd_repair_pairwise.py',
           'analysis_protocols/zpd-history-action-cv-20260923.md'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.partial')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


def equal(actual, expected, where='value'):
    """Strict shape/types/keys, with tiny tolerance for floating point reductions."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(where+': dictionary keys differ')
        for key in expected:
            equal(actual[key], expected[key], where+'.'+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(where+': list shape differs')
        for i, (a, b) in enumerate(zip(actual, expected)):
            equal(a, b, where+f'[{i}]')
    elif isinstance(expected, float):
        if (type(actual) not in (int, float) or not math.isfinite(actual)
                or not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=2e-12)):
            raise ValueError(where+': numeric value differs')
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(where+': value/type differs')


def seal(directory, required):
    directory = Path(directory).resolve()
    marker_path = directory/'COMPLETE.json'
    if marker_path.is_symlink():
        raise ValueError('symlink marker')
    marker = read(marker_path)
    if marker.get('status') != 'complete' or set(marker.get('files_sha256', {})) != set(required):
        raise ValueError('complete exact artifact inventory required')
    for name, digest in marker['files_sha256'].items():
        relative = Path(name); path = directory/relative
        if (relative.is_absolute() or '..' in relative.parts or str(relative) != name
                or path.resolve() != path or not path.is_file() or sha(path) != digest):
            raise ValueError('unsafe or changed artifact: '+name)
    return marker


def verify_seals(run):
    run = Path(run).resolve()
    required = ['manifest.json', 'folds.json', 'COHORTS_COMPLETE.json', 'target-coverage.json', 'report.json', 'events.jsonl', 'STATUS.json']
    required += [f'fold-{f}/'+name for f in range(5) for name in [*MODEL_FILES, 'COMPLETE.json']]
    marker = seal(run, required)
    if (marker.get('completed_folds') != 5 or marker.get('completed_arms') != 30
            or marker.get('confirmatory') is not False):
        raise ValueError('all five folds and thirty arms required')
    if {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()} != set(required+['COMPLETE.json']):
        raise ValueError('unexpected run file; no extra model/refit permitted')
    for fold in range(5):
        nested = seal(run/f'fold-{fold}', MODEL_FILES)
        if nested.get('fold') != fold:
            raise ValueError('fold seal identity mismatch')
    return marker


def expected_folds(observations):
    users = {o['user_id'] for o in observations}
    mapping = {u: int(hashlib.sha256((FOLD_SALT+'|'+u).encode()).hexdigest(), 16) % 5 for u in sorted(users)}
    return {'salt': FOLD_SALT, 'user_fold': mapping,
            'example_fold': {o['example_id']: mapping[o['user_id']] for o in observations}}


def donor_keys(observations):
    from scripts.zpd_history_predictor import lexical_tokens
    counts = {}
    result = {}
    for o in observations:
        total = 0
        for h in o['history']:
            if h['code'] not in counts:
                counts[h['code']] = len(lexical_tokens(h['code'])[0])
            total += counts[h['code']]
        result[o['example_id']] = (o['problem_id'], o['matching_current_verdict'], len(o['history']), total)
    return result


def expected_donors(observations, user_fold, fold, keys):
    """Independent chronological sweep + per-user ranked heap, not matcher code."""
    groups = defaultdict(list); result = {}
    for o in observations:
        groups[keys[o['example_id']]].append(o)
    for group in groups.values():
        ordered = sorted(group, key=lambda o: (o['timestamp'], o['example_id']))
        candidates = [o for o in ordered if user_fold[o['user_id']] != fold]
        position = 0; best = {}; heap = []
        for recipient in ordered:
            while position < len(candidates) and candidates[position]['timestamp'] < recipient['timestamp']:
                candidate = candidates[position]; position += 1
                key = (hashlib.sha256(('zpd-history-donor-v1:'+candidate['example_id']).encode()).hexdigest(),
                       candidate['example_id'], candidate['user_id'])
                if candidate['user_id'] not in best or key < best[candidate['user_id']]:
                    best[candidate['user_id']] = key; heapq.heappush(heap, key)
            excluded = []
            while heap:
                if best[heap[0][2]] != heap[0]:
                    heapq.heappop(heap)
                elif heap[0][2] == recipient['user_id']:
                    excluded.append(heapq.heappop(heap))
                else:
                    break
            result[recipient['example_id']] = heap[0][1] if heap else None
            for item in excluded:
                heapq.heappush(heap, item)
    return result


def event_arrays(observations, targets, encoder):
    values = np.zeros((len(observations), len(encoder.EVENTS)))
    masks = np.zeros(values.shape, dtype=bool)
    for i, o in enumerate(observations):
        target = targets[o['example_id']]
        if target['target_status'] == 'available':
            values[i], masks[i] = encoder.encode_edit(o['current_code'], target['next_code'], 'Python', target['next_language'])
    return values, masks


def matrix(observations, held, arm, donors, encoder):
    index = {o['example_id']: o for o in observations}
    bags = []; blocks = []
    hasher = FeatureHasher(n_features=4096, input_type='dict', alternate_sign=True, dtype=np.float64)
    for position, i in enumerate(held):
        o = observations[i]
        base = encoder.encode_observation(o['current_code'], o['current_verdict'], o['history'], o['timestamp'], 'Cn')
        if arm in ('U', 'L'):
            past = index[donors[o['example_id']]]['history'] if arm == 'U' else o['history'][-1:]
            bag = encoder.encode_observation(o['current_code'], o['current_verdict'], past, o['timestamp'], 'H')
            bag.update(base)
        else:
            bag = encoder.encode_observation(o['current_code'], o['current_verdict'], o['history'], o['timestamp'], arm,
                                             shuffle_key=o['example_id'])
        bags.append(bag)
        if len(bags) == 512 or position == len(held)-1:
            blocks.append(normalize(hasher.transform(bags), norm='l2', axis=1, copy=False)); bags = []
    return sparse.vstack(blocks, format='csr')


def check_model(model, arm, fold, train, observations, values, masks, events):
    ids = [observations[i]['example_id'] for i in train]
    expected = dict(events=list(events), hash_dimension=4096, alpha=1e-4, seed=2027, epochs=20,
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
            if coefficients.shape != (4096,) or not np.isfinite(coefficients).all() or not math.isfinite(head['intercept']):
                raise ValueError('invalid model coefficients')


def probabilities(model, x):
    columns = []
    for head in model['heads']:
        if head['kind'] == 'laplace_constant':
            columns.append(np.repeat(head['probability'], x.shape[0]))
        else:
            columns.append(expit(x.dot(np.asarray(head['coefficients']))+head['intercept']))
    return np.stack(columns, axis=1)


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
    bounds = np.quantile(distribution, [.00625, .99375], axis=0)
    return {c:dict(status='descriptive_crossfit_bootstrap', users=len(users), draws=5000, seed=2027,
                  mean=float(np.mean(differences[:,j])), lower=float(bounds[0,j]), upper=float(bounds[1,j]),
                  interval='two-sided Bonferroni98.75percent percentile; four prespecified contrasts; not confirmatory')
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
        raise ValueError('fixed thirty-arm execution log required')
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


def audit_data(run, observations, targets, encoder, *, progress=None):
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
            x = matrix(observations, held, arm, donors, encoder)
            predicted = probabilities(model, x)
            actual = np.array([p['probabilities'][arm] for p in predictions], dtype=float)
            if actual.shape != predicted.shape or not np.allclose(actual, predicted, rtol=1e-10, atol=2e-12):
                raise ValueError('saved-coefficient prediction mismatch: '+arm)
            if arm == 'H':
                h_matrix = x
            elif arm == 'HS':
                equality = np.asarray((h_matrix-x).getnnz(axis=1) == 0).reshape(-1)
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
    expected_report = dict(kind='train_only_history_action_cv_v1', confirmatory=False, fresh_test_opened=False,
        events=list(encoder.EVENTS), results=overall, fold_results=summaries, fold_coverage=coverages,
        bootstrap_contrasts=intervals, decision=decision,
        strata={name:losses([p for p in combined if p[name]], encoder.EVENTS)[0] for name in STRATA},
        source_population=len(observations), total_oof_supported=len(combined),
        oof_donor_supported_prefixes=len(combined), oof_users=len({p['user_id'] for p in combined}),
        note='Observed next-action prediction only; no repair or educational-learning superiority claim.')
    equal(read(run/'report.json'), expected_report, 'full independent report')
    equal(marker['gate_passed'], decision['gate_passed'], 'terminal gate')
    check_exposure_log(run, models, len(combined), decision['gate_passed'])
    verify_seals(run)
    if sha(run/'COMPLETE.json') != start_sha:
        raise ValueError('run seal changed during verification')
    return dict(verified=True, experiment_complete_sha256=start_sha, model_folds_verified=30,
        source_population=len(observations), oof_prefixes=len(combined), oof_users=len(means['H']),
        target_coverage=target_coverage, decision=decision, results=overall, bootstrap_contrasts=intervals,
        refitting_performed=False, raw_release_opened=False, heldout_labels_opened=False,
        limitations=['Shared audited input loader and pure encoder define input/event semantics.',
                     'Coefficient rescoring verifies saved predictions, not an independent optimizer refit.',
                     'Developmental behavioral prediction is not repair or learner-benefit evidence.'])


def check_configuration(manifest, encoder):
    equal(manifest['configuration'], dict(arms=list(ARMS), events=list(encoder.EVENTS), folds=5, fold_salt=FOLD_SALT,
        hash_dimension=4096, normalization='signedhash_then_per_row_L2', seed=2027, alpha=1e-4, epochs=20,
        controls=list(CONTROLS), probability_clip=1e-12,
        weighting='user_equal_prefix_mean_event_mask_no_head_renormalization', bootstrap_draws=5000,
        bootstrap_quantiles=[.00625,.99375]), 'fixed configuration')
    if (manifest.get('kind') != 'train_only_history_action_cv_v1' or manifest.get('confirmatory') is not False
            or manifest.get('fresh_test_opened') is not False or set(manifest['source_sha256']) != SOURCES):
        raise ValueError('fixed train-only source closure required')


def audit(run, output):
    from scripts.run_zpd_history_action_cv import load_inputs
    from scripts import zpd_history_action_encoder as encoder
    run, output = Path(run).resolve(), Path(output).resolve()
    if run.parent.name != 'zpd-history-action-20260923' or run.parent.parent.name != 'outputs':
        raise ValueError('fixed C1 run family required')
    if output.exists() or output.is_relative_to(run) or run.is_relative_to(output):
        raise ValueError('new nonoverlapping audit output required')
    project = run.parent.parent.parent
    marker = verify_seals(run); manifest = read(run/'manifest.json')
    check_configuration(manifest, encoder)
    if subprocess.check_output(['git','status','--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('clean committed verifier source required')
    revision = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    if revision != manifest['source_revision']:
        raise ValueError('experiment/verifier revision mismatch')
    source_bindings = {}
    for name, expected in manifest['source_sha256'].items():
        path = ROOT/name
        if Path(name).is_absolute() or '..' in Path(name).parts or path.resolve() != path or sha(path) != expected:
            raise ValueError('source/protocol mismatch')
        source_bindings[path] = expected
    protocol = ROOT/'analysis_protocols/zpd-history-action-cv-20260923.md'
    if source_bindings.get(protocol) != manifest['protocol_sha256']:
        raise ValueError('protocol source binding absent')
    expected_runtime = {name:version(name) for name in ('numpy','scipy','scikit-learn')}
    import platform
    expected_runtime['python'] = platform.python_version()
    equal(manifest['runtime'], expected_runtime, 'runtime')
    observations, targets, coverage, bindings = load_inputs(project)
    equal(manifest['coverage'], coverage, 'sealed full input coverage')
    equal(manifest['input_sha256'], {str(p):s for p,s in bindings.items()}, 'input bindings')
    output.mkdir(parents=True)
    started = time.time()
    def progress(fields):
        write(output/'STATUS.json', dict(fields, elapsed_seconds=time.time()-started))
    try:
        result = audit_data(run, observations, targets, encoder, progress=progress)
        for path, expected in {**bindings, **source_bindings}.items():
            if sha(path) != expected:
                raise ValueError('input/source changed during verification')
        result.update(source_revision=revision, verifier_sha256=sha(__file__), elapsed_seconds=time.time()-started,
                      experiment_report_sha256=marker['files_sha256']['report.json'])
        write(output/'report.json', result)
        progress(dict(phase='complete', verified=True))
        write(output/'COMPLETE.json', dict(status='complete', verified=True,
            experiment_complete_sha256=result['experiment_complete_sha256'],
            files_sha256={name:sha(output/name) for name in ('report.json','STATUS.json')}))
        return result
    except BaseException as exc:
        write(output/'FAILED.json', dict(status='failed', error_type=type(exc).__name__, error=str(exc)))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    return audit(args.run, args.output)


if __name__ == '__main__':
    main()
