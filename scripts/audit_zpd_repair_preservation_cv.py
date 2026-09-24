"""Independent no-fit audit of the fixed preservation-objective experiment.

The old train-only input loader and source-only feature primitives are shared.
No preservation fitter, driver, scorer, supervision or summary is imported.
All pair targets/weights, scales, scores, bounds and gate are reconstructed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from importlib.metadata import version
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import subprocess

import numpy as np
from scipy import sparse

from scripts.audit_zpd_history_action_cv import read, sha, write
from scripts.zpd_repair_structure import raw_features
from src.repair.pilot_contracts import canonical_hash, source_hash
from src.repair.pilot_ranker import features

ROOT = Path(__file__).resolve().parents[1]
CELLS = ('legacy_natural', 'legacy_balanced', 'refined_natural', 'refined_balanced')
PRIMARY = 'refined_balanced'
CONTROLS = ('structural_C', 'lexical_C', 'first_attempt')
STRATA = ('known_ac', 'known_nonac', 'unknown')
NAMES = ['candidate_byte_length_delta', 'candidate_edit_tokens', 'candidate_is_noop']
COUNT_FIELDS = ('rr_lower_bound', 'rr_upper_bound', 'regression_rate_lower_bound',
                'regression_rate_upper_bound', 'unknown', 'noop')
METRICS = ('utility', 'utility_upper_bound', 'rr_lower_bound', 'rr_upper_bound',
           'loss_fraction_lower_bound', 'regression_rate_lower_bound',
           'regression_rate_upper_bound', 'edit_tokens', 'unknown', 'noop')
SALT = 'structure-cv-20260923-v1'
BASELINE_COMPLETE = 'b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f'


def equal(actual, expected, where='value'):
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(where+': different keys')
        for key, value in expected.items(): equal(actual[key], value, where+'.'+key)
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(where+': different list shape')
        for i, (a, e) in enumerate(zip(actual, expected)): equal(a, e, where+f'[{i}]')
    elif type(expected) in (int, float):
        if type(actual) not in (int, float) or not math.isfinite(actual) or not math.isclose(actual, expected, abs_tol=2e-11, rel_tol=2e-10):
            raise ValueError(where+': different numeric value')
    elif type(actual) is not type(expected) or actual != expected:
        raise ValueError(where+': different value/type')


def verify_files(directory, mapping):
    directory = Path(directory).resolve()
    if not mapping: raise ValueError('empty file seal')
    for relative, digest in mapping.items():
        name = Path(relative); file = directory/name
        if (name.is_absolute() or '..' in name.parts or str(name) != relative
                or file.resolve() != file or not file.is_file() or sha(file) != digest):
            raise ValueError('unsafe or changed artifact '+relative)


def folds_for(examples):
    if not examples or any(e.split != 'train' for e in examples):
        raise ValueError('train-only examples required')
    for attr in ('example_id', 'user_id', 'bank_id'):
        if len({getattr(e, attr) for e in examples}) != len(examples):
            raise ValueError('unique examples, users and banks required')
    counts = Counter(e.observation.problem_id for e in examples)
    if len(counts) < 5: raise ValueError('five problem groups required')
    sizes = [0]*5; mapping = {}
    for pid in sorted(counts, key=lambda p: (-counts[p], hashlib.sha256((SALT+'|'+p).encode()).hexdigest(), p)):
        fold = min(range(5), key=lambda i: (sizes[i], i))
        mapping[pid] = fold; sizes[fold] += counts[pid]
    return dict(salt=SALT, folds=5, problem_fold=mapping, fold_sizes=sizes,
        problem_counts=dict(sorted(counts.items())),
        example_fold={e.example_id: mapping[e.observation.problem_id] for e in examples})


def preference(label):
    if label['status'] == 'unknown':
        if any(label[k] is not None for k in ('gain', 'loss', 'all_ac')):
            raise ValueError('unknown evidence must be null')
        return None
    if (label['status'] != 'stable' or type(label['all_ac']) is not bool
            or any(type(label[k]) not in (int, float) or not math.isfinite(label[k])
                   or not 0 <= label[k] <= 1 for k in ('gain', 'loss'))
            or label['gain']+label['loss'] > 1+1e-12
            or label['all_ac'] and label['loss'] != 0):
        raise ValueError('invalid stable execution label')
    return (int(label['all_ac']), int(label['loss'] == 0), label['gain']-label['loss'])


def original_stratum(label):
    return 'unknown' if preference(label) is None else 'known_ac' if label['all_ac'] else 'known_nonac'


def supervision(examples, banks, labels, cell):
    if cell not in CELLS: raise ValueError('fixed four cells required')
    required = {(e.bank_id, c.candidate_id) for e in examples for c in banks[e.bank_id].candidates}
    if (set(labels) != required or set(banks) != {e.bank_id for e in examples}
            or any(e.split != 'train' for e in examples)):
        raise ValueError('exact train-only whitelist required')
    relation, weighting = cell.split('_')
    records = []
    for e in examples:
        bank = banks[e.bank_id]; noop = source_hash(bank.current_source)
        stratum = original_stratum(labels[e.bank_id, noop])
        keys = []
        for candidate in bank.candidates:
            key = preference(labels[e.bank_id, candidate.candidate_id])
            if key is not None and relation == 'refined':
                key += (int(stratum == 'known_ac' and candidate.candidate_id == noop),)
            keys.append(key)
        pairs = []
        for i, j in combinations(range(len(keys)), 2):
            if keys[i] is not None and keys[j] is not None and keys[i] != keys[j]:
                pairs.append([bank.candidates[i].candidate_id, bank.candidates[j].candidate_id, int(keys[i] > keys[j])])
        records.append(dict(example_id=e.example_id, user_id=e.user_id, bank_id=e.bank_id,
            stratum=stratum, stable_candidate_ids=[c.candidate_id for c, k in zip(bank.candidates, keys) if k is not None],
            unknown_candidate_ids=[c.candidate_id for c, k in zip(bank.candidates, keys) if k is None],
            pairs=pairs, natural_row_weight=0., row_weight=0.))
    informative = [r for r in records if r['pairs']]
    if not informative: raise ValueError('no informative pairs')
    counts = Counter(r['user_id'] for r in informative)
    for r in informative:
        r['natural_row_weight'] = 1900/(len(counts)*counts[r['user_id']]*2*len(r['pairs']))
    natural = {s: math.fsum(2*len(r['pairs'])*r['natural_row_weight'] for r in informative if r['stratum'] == s) for s in STRATA}
    desired = dict(natural)
    group_users = {s: Counter(r['user_id'] for r in informative if r['stratum'] == s) for s in STRATA}
    if weighting == 'balanced':
        if not group_users['known_ac'] or not group_users['known_nonac']:
            raise ValueError('both known strata need informative support')
        desired['known_ac'] = desired['known_nonac'] = (1900-natural['unknown'])/2
    for r in informative:
        s = r['stratum']
        r['row_weight'] = (r['natural_row_weight'] if weighting == 'natural' else
            desired[s]/(len(group_users[s])*group_users[s][r['user_id']]*2*len(r['pairs'])))
    realized = {s: math.fsum(2*len(r['pairs'])*r['row_weight'] for r in informative if r['stratum'] == s) for s in STRATA}
    pair_ids = [r['example_id'] for r in informative for _ in range(2*len(r['pairs']))]
    return dict(train_example_ids=[e.example_id for e in examples], train_prefixes=len(examples),
        train_users=len({e.user_id for e in examples}), informative_train_example_ids=[r['example_id'] for r in informative],
        uninformative_train_example_ids=[r['example_id'] for r in records if not r['pairs']],
        ordered_pairs=len(pair_ids), pair_example_ids=pair_ids,
        sample_weight_sum=math.fsum(realized.values()), natural_stratum_mass=natural, stratum_mass=realized,
        stratum_prefixes=dict(Counter(r['stratum'] for r in records)),
        informative_stratum_prefixes=dict(Counter(r['stratum'] for r in informative)), prefixes=records,
        unknown_pair_policy='retain stable unequal pairs; unknown candidates incomparable')


def legacy_scale(examples, banks, labels):
    """Weighted population variance; no scaler fitting or learner call."""
    meta = supervision(examples, banks, labels, 'legacy_natural')
    info = {r['example_id']: r for r in meta['prefixes'] if r['pairs']}
    users = Counter(r['user_id'] for r in info.values())
    rows = []; weights = []
    for e in examples:
        if e.example_id not in info: continue
        record = info[e.example_id]
        sources = {c.candidate_id: c.source for c in banks[e.bank_id].candidates}
        for cid in record['stable_candidate_ids']:
            row = features(e.observation, sources[cid], history=())
            rows.append([row[name] for name in NAMES])
            weights.append(1/(users[e.user_id]*len(record['stable_candidate_ids'])))
    x = np.asarray(rows); w = np.asarray(weights)
    mean = np.average(x, axis=0, weights=w)
    variance = np.average((x-mean)**2, axis=0, weights=w)
    # Match the numerical constant-feature criterion of StandardScaler.
    eps = np.finfo(np.float64).eps; n = float(w.sum())
    constant = variance <= n*eps*variance+(n*mean*eps)**2
    scale = np.sqrt(variance); scale[constant] = 1.
    return scale.tolist(), meta


def verify_reference(model, train, banks, labels, variant):
    if model.get('model_sha256') != canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}):
        raise ValueError('baseline model hash')
    if (model['condition'] != 'C' or model['variant'] != variant or model['C'] != .1
            or model['numeric_names'] != NAMES or model['intercept'] != 0.):
        raise ValueError('baseline configuration')
    config = dict(hash_dimension=4096, alternate_sign=True, normalization='candidate_l2_after_log1p',
        lexical='existing_byte_bags_v1', structure='ordered_ast_and_byte_fallback_v1' if variant == 'structural' else None,
        ast_feature_version=[3, 10] if variant == 'structural' else None,
        fallback_ngram_lengths=[2, 3] if variant == 'structural' else [], solver='liblinear', max_iter=2000,
        fit_intercept=False, random_state=2027, reference_pair_weight=1900.)
    equal(model['feature_config'], config, 'baseline feature configuration')
    if (type(model['coefficients']) is not list or len(model['coefficients']) != 4099
            or any(type(c) not in (int, float) or not math.isfinite(c) for c in model['coefficients'])):
        raise ValueError('invalid baseline coefficients')
    scale, meta = legacy_scale(train, banks, labels)
    equal(model['numeric_scale'], scale, 'baseline legacy-only scale')
    saved = model['training']
    for name in ('informative_train_example_ids', 'train_prefixes', 'train_users', 'ordered_pairs', 'pair_example_ids'):
        equal(saved[name], meta[name], 'baseline training.'+name)
    equal(saved['uninformative_train_example_ids'], sorted(meta['uninformative_train_example_ids']), 'baseline uninformative IDs')
    equal(saved['sample_weight_sum'], 1900., 'baseline total pair weight')
    return scale


def verify_model(model, reference, train, banks, labels, cell):
    if model.get('model_sha256') != canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}):
        raise ValueError('preservation canonical model seal')
    fixed = dict(kind='replay_preservation_fixed_objective_v1', cell=cell, condition='C', variant='structural',
        C=.1, numeric_names=NAMES, numeric_scale=reference['numeric_scale'], intercept=0., hash_dimension=4096,
        normalization='candidate_l2_after_log1p', reference_pair_weight=1900., solver='liblinear',
        max_iter=2000, random_state=2027, reference_model_sha256=reference['model_sha256'],
        legacy_model_reused=cell == 'legacy_natural')
    if set(model) != set(fixed)|{'coefficients', 'iterations', 'training', 'model_sha256'}:
        raise ValueError('preservation exact model schema')
    equal({k: model[k] for k in fixed}, fixed, 'preservation fixed model')
    if type(model['coefficients']) is not list or any(type(v) not in (int, float) for v in model['coefficients']):
        raise ValueError('coefficients require numeric values, not strings/bools')
    coef = np.asarray(model['coefficients'], dtype=float)
    if coef.shape != (4099,) or not np.isfinite(coef).all(): raise ValueError('invalid finite model coefficients')
    if cell == 'legacy_natural':
        equal(model['coefficients'], reference['coefficients'], 'baseline reused coefficients')
        if model['iterations'] is not None: raise ValueError('baseline must not refit')
    elif type(model['iterations']) is not int or not 0 < model['iterations'] < 2000:
        raise ValueError('missing new-model convergence metadata')
    equal(model['training'], supervision(train, banks, labels, cell), 'independent supervision/weights')


def scores(model, observation, bank, variant='structural'):
    """No execution label or replay stratum accepted by prediction."""
    numeric, hashed = raw_features(observation, (), bank, 'C', variant)
    scale = np.asarray(model['numeric_scale'], dtype=float)
    coefficient = np.asarray(model['coefficients'], dtype=float)
    if scale.shape != (3,) or np.any(scale <= 0) or not np.isfinite(scale).all() or coefficient.shape != (4099,) or not np.isfinite(coefficient).all():
        raise ValueError('score dimensions/finite scale')
    matrix = sparse.hstack([numeric.multiply(1/scale), hashed], format='csr')
    value = np.asarray(matrix@coefficient).ravel()
    if not np.isfinite(value).all(): raise ValueError('nonfinite scores')
    return {c.candidate_id: float(v) for c, v in zip(bank.candidates, value)}


def summarize(predictions, labels):
    methods = tuple(sorted(predictions[0]['choices']))
    if len({p['user_id'] for p in predictions}) != len(predictions):
        raise ValueError('one OOF prefix per user required')
    def subset(group):
        result = {}
        for method in methods:
            values = []
            for row in group:
                cid = row['choices'][method]; lab = labels[row['bank_id'], cid]
                unknown = preference(lab) is None
                values.append(dict(example_id=row['example_id'], user_id=row['user_id'], bank_id=row['bank_id'],
                    candidate_id=cid, utility=-1. if unknown else lab['gain']-lab['loss'],
                    utility_upper_bound=1. if unknown else lab['gain']-lab['loss'],
                    rr_lower_bound=float(not unknown and lab['all_ac']), rr_upper_bound=float(unknown or lab['all_ac']),
                    loss_fraction_lower_bound=0. if unknown else lab['loss'],
                    regression_rate_lower_bound=float(not unknown and lab['loss'] > 0),
                    regression_rate_upper_bound=float(unknown or lab['loss'] > 0),
                    edit_tokens=row['candidate_edit_tokens'][cid], unknown=float(unknown),
                    noop=float(cid == row['choices']['noop'])))
            counts = {k: sum(v[k] for v in values) for k in COUNT_FIELDS}
            metrics = {k: math.fsum(v[k] for v in values)/len(values) for k in METRICS} if values else None
            if metrics is not None: metrics.update(examples=len(values), users=len(values))
            result[method] = dict(metrics=metrics, predictions=values, counts=counts, examples=len(values))
        return result
    overall = subset(predictions)
    problems = {pid: subset([p for p in predictions if p['problem_id'] == pid]) for pid in sorted({p['problem_id'] for p in predictions})}
    folds = {str(f): subset([p for p in predictions if p['fold'] == f]) for f in range(5)}
    ep = {m: {k: float(sum(Fraction(int(c[m]['counts'][k]), c[m]['examples']) for c in problems.values())/len(problems))
               for k in COUNT_FIELDS[:4]} for m in methods}
    groups = {s: [p for p in predictions if original_stratum(labels[p['bank_id'], p['choices']['noop']]) == s] for s in STRATA}
    transitions = {}
    for control in (*CONTROLS, 'legacy_balanced', 'refined_natural'):
        count = Counter()
        for row in predictions:
            p, c = (labels[row['bank_id'], row['choices'][m]] for m in (PRIMARY, control))
            count['selected_candidate_changed'] += row['choices'][PRIMARY] != row['choices'][control]
            if p['status'] == 'unknown' or c['status'] == 'unknown':
                count['not_jointly_known'] += 1
                count['primary_unknown'] += p['status'] == 'unknown'
                count['control_unknown'] += c['status'] == 'unknown'
            else:
                count['ac_gained'] += p['all_ac'] and not c['all_ac']
                count['ac_lost'] += c['all_ac'] and not p['all_ac']
                count['regression_prevented'] += p['loss'] == 0 and c['loss'] > 0
                count['regression_introduced'] += p['loss'] > 0 and c['loss'] == 0
        transitions[control] = dict(count)
    utility = {}
    for method in methods:
        if method == PRIMARY: continue
        pairs = list(zip(overall[PRIMARY]['predictions'], overall[method]['predictions']))
        bounds = [(0., 0.) if a['candidate_id'] == b['candidate_id'] else
                  (a['utility']-b['utility_upper_bound'], a['utility_upper_bound']-b['utility']) for a, b in pairs]
        utility[PRIMARY+'-'+method] = dict(net_gain_mean_lower_bound=math.fsum(b[0] for b in bounds)/len(bounds),
            net_gain_mean_upper_bound=math.fsum(b[1] for b in bounds)/len(bounds),
            conservative_scoring_difference=math.fsum(a['utility']-b['utility'] for a, b in pairs)/len(pairs),
            different_choices=sum(a['candidate_id'] != b['candidate_id'] for a, b in pairs), examples=len(pairs),
            note='Unknown-outcome bounds, not sampling confidence intervals.')
    return dict(results=overall, problem_results=problems, fold_results=folds, equal_problem_metrics=ep,
        original_status_subgroups={s: dict(examples=len(g), results=subset(g)) for s, g in groups.items()},
        primary_transitions=transitions, paired_utility_bounds=utility)


def gate(report):
    checks = {}
    def exact_problem(method, field):
        cells = report['problem_results'].values()
        return sum(Fraction(int(c[method]['counts'][field]), c[method]['examples']) for c in cells)/len(report['problem_results'])
    for control in CONTROLS:
        p = report['results'][PRIMARY]['counts']; c = report['results'][control]['counts']
        ep = {k: exact_problem(PRIMARY, k) for k in COUNT_FIELDS[:4]}
        ec = {k: exact_problem(control, k) for k in COUNT_FIELDS[:4]}
        checks[control] = dict(ac_lower_strictly_greater=p['rr_lower_bound'] > c['rr_lower_bound'],
            regression_lower_no_worse=p['regression_rate_lower_bound'] <= c['regression_rate_lower_bound'],
            regression_upper_no_worse=p['regression_rate_upper_bound'] <= c['regression_rate_upper_bound'],
            equal_problem_ac_lower_strictly_greater=ep['rr_lower_bound'] > ec['rr_lower_bound'],
            equal_problem_regression_lower_no_worse=ep['regression_rate_lower_bound'] <= ec['regression_rate_lower_bound'],
            equal_problem_regression_upper_no_worse=ep['regression_rate_upper_bound'] <= ec['regression_rate_upper_bound'])
    stable = {c: sum(f[PRIMARY]['counts']['rr_lower_bound'] >= f[c]['counts']['rr_lower_bound'] for f in report['fold_results'].values())
              for c in ('structural_C', 'lexical_C')}
    passed = all(all(v.values()) for v in checks.values()) and min(stable.values()) >= 4
    return dict(primary=PRIMARY, checks=checks, nonworse_ac_folds=stable, gate_passed=passed,
        required_nonworse_folds=4, eligible_for_separately_frozen_development_replay=passed,
        full_train_refits_authorized=False, confirmatory=False, zpd_benefit_established=False, model_promotion=False,
        next_action='separately_freeze_and_audit_next_development' if passed else 'retain_negative_result_and_train_only_diagnosis')


def output_path(project, run, output):
    """Only a new audit child or the exact supervisor audit slot is writable."""
    project, run, output = map(lambda p: Path(p).absolute(), (project, run, output))
    if any(p.resolve() != p for p in (project, run, output)):
        raise ValueError('canonical nonsymlink audit paths required')
    own = project/'outputs/zpd-repair-preservation-20260924'
    supervised = project/'outputs/zpd-method-continuation-20260924'
    if not (output.parent == own or (output.name == 'repair-verified' and output.parent.parent == supervised)):
        raise ValueError('fixed audit family or supervisor repair-verified slot required')
    if output == run or run in output.parents or output in run.parents or output.exists():
        raise ValueError('new audit output must not overlap experiment')
    return output


def verify_baseline(directory, production=True):
    directory = Path(directory)
    if production and sha(directory/'COMPLETE.json') != BASELINE_COMPLETE:
        raise ValueError('wrong frozen baseline experiment')
    complete = read(directory/'COMPLETE.json')
    if complete['status'] != 'complete' or complete['full_train_complete_sha256'] is not None:
        raise ValueError('completed no-refit baseline required')
    verify_files(directory, complete['files_sha256'])
    pre = read(directory/'PREDICTIONS_COMPLETE.json')
    equal(pre['predictions_sha256'], sha(directory/'predictions.json'), 'baseline predictions seal')
    for fold in range(5):
        root = directory/f'fold-{fold}'
        equal(pre['fold_complete_sha256'][str(fold)], sha(root/'COMPLETE.json'), 'baseline fold seal')
        marker = read(root/'COMPLETE.json')
        equal(marker['predictions_sha256'], sha(root/'predictions.json'), 'baseline fold predictions')
        equal(marker['models_complete_sha256'], sha(root/'MODELS_COMPLETE.json'), 'baseline models marker')
        models = read(root/'MODELS_COMPLETE.json')
        verify_files(root, models['model_files_sha256'])
        equal(models['folds_sha256'], sha(directory/'folds.json'), 'baseline fold membership')
    return complete


def verify_new_seals(run):
    names = ['manifest.json', 'folds.json', 'FOLDS_COMPLETE.json', 'predictions.json',
             'PREDICTIONS_COMPLETE.json', 'report.json', 'next_action.json', 'events.jsonl', 'STATUS.json']
    fold_names = ['cohort.json', 'predictions.json', *[c+'.json' for c in (*CELLS, 'structural_C', 'lexical_C')]]
    required = set(names+[f'fold-{f}/'+n for f in range(5) for n in (*fold_names, 'COMPLETE.json')])
    complete = read(run/'COMPLETE.json')
    if complete.get('status') != 'complete' or set(complete.get('files_sha256', {})) != required:
        raise ValueError('exact complete recursive experiment inventory required')
    verify_files(run, complete['files_sha256'])
    if {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()} != required|{'COMPLETE.json'}:
        raise ValueError('unexpected extra experiment artifact/refit')
    for fold in range(5):
        root = run/f'fold-{fold}'; marker = read(root/'COMPLETE.json')
        if set(marker.get('files_sha256', {})) != set(fold_names):
            raise ValueError('fold exact inventory mismatch')
        verify_files(root, marker['files_sha256'])
    return complete


def check_prediction(saved, example, bank, models, fold):
    choices = {'noop': source_hash(bank.current_source)}
    first = bank.attempts[0]
    choices['first_attempt'] = source_hash(first.source) if first.status == 'success' else choices['noop']
    all_scores = {}
    for cell, model in models.items():
        value = scores(model, example.observation, bank, 'lexical' if cell == 'lexical_C' else 'structural')
        all_scores[cell] = value
        choices[cell] = min(value, key=lambda cid: (-value[cid], cid))
    expected = dict(example_id=example.example_id, user_id=example.user_id, bank_id=example.bank_id,
        fold=fold, problem_id=bank.problem_id, bank_seal_sha256=bank.seal_sha256,
        choices=choices, candidate_scores=all_scores,
        candidate_edit_tokens={c.candidate_id: features(example.observation, c.source, history=())['candidate_edit_tokens'] for c in bank.candidates})
    equal(saved, expected, 'independent label-blind prediction')
    return expected


def verify_data(examples, banks, labels, run, baseline, production=True):
    """In-memory verified train-only inputs; all fitting is forbidden here."""
    run, baseline = Path(run), Path(baseline)
    complete = verify_new_seals(run)
    verify_baseline(baseline, production)
    assignment = folds_for(examples)
    if production and len(examples) != 320: raise ValueError('fixed train320 required')
    equal({k: complete.get(k) for k in ('completed_folds', 'completed_fits', 'reused_models',
                                      'completed_recipients', 'total_recipients', 'full_train_refits')},
        dict(completed_folds=5, completed_fits=15, reused_models=5,
             completed_recipients=len(examples), total_recipients=len(examples), full_train_refits=0), 'complete counts')
    equal(read(run/'folds.json'), assignment, 'independent problem folds')
    equal(read(baseline/'folds.json'), assignment, 'frozen baseline folds')
    fold_marker = read(run/'FOLDS_COMPLETE.json')
    equal(fold_marker['folds_sha256'], sha(run/'folds.json'), 'prefit fold seal')
    equal(fold_marker['manifest_sha256'], sha(run/'manifest.json'), 'prefit manifest seal')
    combined = []; checked_models = 0
    for fold in range(5):
        directory = run/f'fold-{fold}'; old = baseline/f'fold-{fold}'
        train = [e for e in examples if assignment['example_fold'][e.example_id] != fold]
        held = [e for e in examples if assignment['example_fold'][e.example_id] == fold]
        allowed = {e.bank_id for e in train}
        train_banks = {k: v for k, v in banks.items() if k in allowed}
        train_labels = {k: v for k, v in labels.items() if k[0] in allowed}
        cohort = read(directory/'cohort.json')
        equal(cohort['train_example_ids'], [e.example_id for e in train], 'training IDs')
        equal(cohort['held_example_ids'], [e.example_id for e in held], 'held IDs')
        old_cohort = read(old/'MODELS_COMPLETE.json')
        equal(old_cohort['train_example_ids'], cohort['train_example_ids'], 'old training IDs')
        equal(old_cohort['held_example_ids'], cohort['held_example_ids'], 'old held IDs')
        controls = {}
        for name, variant in (('structural_C', 'structural'), ('lexical_C', 'lexical')):
            control = read(old/(name+'.json'))
            equal(read(directory/(name+'.json')), control, 'copied frozen control '+name)
            verify_reference(control, train, train_banks, train_labels, variant)
            controls[name] = control
        reference = controls['structural_C']
        equal(cohort['reference_model_sha256'], {k: m['model_sha256'] for k, m in controls.items()}, 'cohort reference models')
        equal(cohort['fold'], fold, 'cohort fold')
        equal(cohort['train_problem_ids'], sorted({e.observation.problem_id for e in train}), 'training problem IDs')
        equal(cohort['held_problem_ids'], sorted({e.observation.problem_id for e in held}), 'held problem IDs')
        equal(cohort['bank_seals'], {k: v.seal_sha256 for k, v in banks.items()}, 'cohort banks')
        models = dict(controls)
        for cell in CELLS:
            model = read(directory/(cell+'.json'))
            verify_model(model, reference, train, train_banks, train_labels, cell)
            models[cell] = model; checked_models += 1
        predictions = read(directory/'predictions.json')
        if len(predictions) != len(held): raise ValueError('held prediction count')
        for row, example in zip(predictions, held):
            combined.append(check_prediction(row, example, banks[example.bank_id], models, fold))
    combined.sort(key=lambda r: r['example_id'])
    equal(read(run/'predictions.json'), combined, 'complete OOF predictions')
    prediction_marker = read(run/'PREDICTIONS_COMPLETE.json')
    equal(prediction_marker['predictions_sha256'], sha(run/'predictions.json'), 'global prediction seal')
    equal(prediction_marker['fold_complete_sha256'], {str(f): sha(run/f'fold-{f}/COMPLETE.json') for f in range(5)}, 'all fold prediction seals')
    # Check old controls against their old saved choices too, not just copied models.
    old_predictions = {r['example_id']: r for r in read(baseline/'predictions.json')}
    for row in combined:
        for method in (*CONTROLS, 'noop'):
            equal(row['choices'][method], old_predictions[row['example_id']]['choices'][method], 'frozen old choice')
        equal(row['choices']['legacy_natural'], row['choices']['structural_C'], 'reused baseline choice')
    report = summarize(combined, labels)
    saved = read(run/'report.json')
    for name in report: equal(saved[name], report[name], 'recomputed report.'+name)
    decision = gate(report)
    for name in decision: equal(saved['decision'][name], decision[name], 'independent gate.'+name)
    if saved['decision'].get('full_train_refits_authorized') is not False:
        raise ValueError('no full train refit authorized')
    equal(read(run/'next_action.json'), saved['decision'], 'unchanged next action')
    if complete.get('gate_passed') is not decision['gate_passed']:
        raise ValueError('complete gate inconsistent')
    return dict(status='verified', verified=True, checked_prefixes=len(combined), checked_objective_models=checked_models,
        new_fit_count=15, baseline_reuse_count=5, decision=decision,
        result_counts={k: v['counts'] for k, v in report['results'].items()},
        original_status_subgroups=report['original_status_subgroups'],
        primary_transitions=report['primary_transitions'],
        experiment_complete_sha256=sha(run/'COMPLETE.json'), experiment_report_sha256=sha(run/'report.json'),
        baseline_complete_sha256=sha(baseline/'COMPLETE.json'), optimizer_refit=False,
        limitations=['Audited legacy loader and source-only feature primitives are shared.',
            'Coefficients are rescored, not optimizer-refitted.',
            'Unknown-outcome bounds are not sampling confidence intervals.',
            'Exposed train-only adaptive development; no repair generalization or educational causal claim.'])


def verify_source_snapshot(source_root, provenance):
    """Source snapshot is not the canonical data project, which may be dirty."""
    root = Path(source_root).absolute()
    if root.resolve() != root: raise ValueError('canonical clean source snapshot required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
        raise ValueError('clean committed auditor source snapshot required')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    if revision != provenance['source_revision']:
        raise ValueError('auditor/experiment source revision differs')
    if provenance['python'] != platform.python_version() or provenance['libraries'] != {
            n: version(n) for n in ('numpy', 'scipy', 'scikit-learn')}:
        raise ValueError('frozen experiment numeric runtime required')
    sources = provenance['source_sha256']
    required = {'scripts/audit_zpd_repair_preservation_cv.py', 'scripts/zpd_repair_preservation.py',
                'scripts/run_zpd_repair_preservation_cv.py', 'scripts/run_zpd_repair_structure_cv.py',
                'scripts/audit_zpd_history_action_cv.py',
                'scripts/zpd_repair_structure.py', 'src/repair/pilot_contracts.py', 'src/repair/pilot_ranker.py',
                'analysis_protocols/zpd-preservation-objective-design-20260924.md'}
    if not required.issubset(sources): raise ValueError('auditor and dependency source closure required')
    if provenance['protocol_sha256'] != sources['analysis_protocols/zpd-preservation-objective-design-20260924.md']:
        raise ValueError('protocol/source seal disagreement')
    bindings = {}
    for relative, digest in sources.items():
        path = Path(relative)
        file = root/path
        if path.is_absolute() or '..' in path.parts or file.resolve() != file or sha(file) != digest:
            raise ValueError('changed/unsafe snapshot source '+relative)
        bindings[str(file)] = digest
    return bindings


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    project = args.project.absolute(); run = args.run.absolute()
    if project.resolve() != project or run.resolve() != run:
        raise ValueError('canonical nonsymlink project and experiment paths required')
    if run.parent != project/'outputs/zpd-repair-preservation-20260924':
        raise ValueError('fixed preservation experiment family required')
    output = output_path(project, run, args.output)
    # Import input loading only, never the new preservation fitter/driver.
    from scripts.run_zpd_repair_structure_cv import load_training
    examples, banks, labels, bindings = load_training(project)
    manifest = read(run/'manifest.json')
    provenance = manifest['provenance']
    source_bindings = verify_source_snapshot(ROOT, provenance)
    def relative_input(path):
        parts = Path(path).parts
        if parts.count('outputs') != 1 or '..' in parts: raise ValueError('ambiguous input path')
        return '/'.join(parts[parts.index('outputs'):])
    def normalized(mapping):
        result = {}
        for p, h in mapping.items():
            key = relative_input(p)
            if key in result: raise ValueError('duplicate normalized input path')
            result[key] = h
        return result
    if normalized(provenance['input_sha256']) != normalized(bindings):
        raise ValueError('exact consumed input set differs from experiment')
    baseline = project/'outputs/zpd-repair-structure-cv-20260923/run-v1'
    expected_sources = set(read(baseline/'manifest.json')['provenance']['source_sha256']) | {
        'scripts/zpd_repair_preservation.py', 'scripts/run_zpd_repair_preservation_cv.py',
        'scripts/audit_zpd_repair_preservation_cv.py', 'scripts/audit_zpd_history_action_cv.py',
        'analysis_protocols/zpd-preservation-objective-design-20260924.md'}
    if set(provenance['source_sha256']) != expected_sources:
        raise ValueError('exact baseline-plus-stage source closure required')
    original_seal = sha(run/'COMPLETE.json')
    report = verify_data(examples, banks, labels, run, baseline)
    for path, digest in {**bindings, **source_bindings}.items():
        if sha(path) != digest: raise ValueError('consumed source/input changed during audit')
    verify_source_snapshot(ROOT, provenance)
    verify_new_seals(run)
    verify_baseline(baseline)
    if sha(baseline/'COMPLETE.json') != report['baseline_complete_sha256']:
        raise ValueError('baseline changed during audit')
    if sha(run/'COMPLETE.json') != original_seal: raise ValueError('experiment changed during audit')
    report['auditor_source_sha256'] = sha(__file__)
    output.mkdir(parents=True)
    write(output/'report.json', report)
    write(output/'COMPLETE.json', dict(status='complete', verified=True,
        experiment_complete_sha256=sha(run/'COMPLETE.json'), gate_passed=report['decision']['gate_passed'],
        files_sha256={'report.json': sha(output/'report.json')}))
    print(json.dumps(dict(verified=True, gate_passed=report['decision']['gate_passed'], output=str(output)), sort_keys=True))


if __name__ == '__main__':
    main()
