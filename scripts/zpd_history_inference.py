"""Frozen history-gate inference. Reading predictions explicitly opens test outcomes.

No fitting, selection, threshold tuning, or feedback into model training. All
primary effects are baseline minus authentic-history user-equal NLL.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.zpd_history_predictor import ARMS, LABELS, SEEDS


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def user_means(values, users):
    users, inverse = np.unique(np.asarray(users, dtype=str), return_inverse=True)
    return users, np.bincount(inverse, weights=values) / np.bincount(inverse)


def row_weights(users):
    _, inverse, counts = np.unique(np.asarray(users, dtype=str), return_inverse=True, return_counts=True)
    return 1.0 / (len(counts) * counts[inverse])


def validate_probabilities(probabilities, n):
    p = np.asarray(probabilities, dtype=np.float64)
    if p.shape != (n, len(LABELS)) or not np.isfinite(p).all():
        raise ValueError('invalid probability shape or nonfinite values')
    if (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-10, rtol=1e-10):
        raise ValueError('invalid probability simplex')
    return p


def nll(y, p):
    # Match the engine's explicit floating point floor, not sklearn clipping.
    return -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))


def metrics(y, p, users):
    if not len(y):
        return {'status': 'not_measured', 'reason': 'empty subset'}
    p = validate_probabilities(p, len(y))
    weights = row_weights(users)
    correct = (p.argmax(axis=1) == y).astype(float)
    confidence = p.max(axis=1)
    bins = np.minimum((confidence * 10).astype(int), 9)
    calibration, ece = [], 0.0
    for index in range(10):
        take = bins == index
        mass = float(weights[take].sum())
        acc = float(weights[take] @ correct[take] / mass) if mass else None
        conf = float(weights[take] @ confidence[take] / mass) if mass else None
        if mass:
            ece += mass * abs(acc - conf)
        calibration.append({'bin': index, 'left': index / 10, 'right': (index + 1) / 10,
                            'rows': int(take.sum()), 'user_weight_mass': mass,
                            'accuracy': acc, 'confidence': conf})
    one_hot = np.eye(len(LABELS))[y]
    return {'rows': len(y), 'users': len(set(users)),
            'label_counts': {label: int((y == i).sum()) for i, label in enumerate(LABELS)},
            'user_equal_nll': float(weights @ nll(y, p)),
            'user_equal_accuracy': float(weights @ correct),
            'user_equal_brier_sum_classes': float(weights @ np.square(p - one_hot).sum(axis=1)),
            'user_equal_ece_10': float(ece), 'calibration': calibration}


def paired_user_inference(delta, users, *, bootstrap_reps=10000, signflip_reps=100000, batch=256):
    """Fixed seeds; Monte Carlo +1 correction; users are paired exchange units."""
    ids, means = user_means(np.asarray(delta, dtype=float), users)
    if not len(ids):
        return {'status': 'not_evaluable', 'reason': 'no paired users'}
    if bootstrap_reps < 1 or signflip_reps < 1 or batch < 1:
        raise ValueError('resampling counts must be positive')
    observed = float(means.mean())
    rng = np.random.default_rng(91015)
    draws = np.empty(bootstrap_reps)
    for start in range(0, bootstrap_reps, batch):
        count = min(batch, bootstrap_reps - start)
        draws[start:start+count] = means[rng.integers(len(means), size=(count, len(means)))].mean(axis=1)
    rng = np.random.default_rng(91016)
    extreme = 0
    for start in range(0, signflip_reps, batch):
        count = min(batch, signflip_reps - start)
        signs = rng.integers(0, 2, size=(count, len(means))) * 2 - 1
        null = (signs * means).mean(axis=1)
        extreme += int((null >= observed - 1e-14).sum())
    return {'status': 'evaluated', 'users': len(ids), 'rows': len(delta),
            'improvement_nll': observed, 'ci95': np.quantile(draws, [.025, .975]).tolist(),
            'one_sided_p': (extreme + 1) / (signflip_reps + 1),
            'bootstrap_reps': bootstrap_reps, 'bootstrap_seed': 91015,
            'signflip_reps': signflip_reps, 'signflip_seed': 91016,
            'assumption': 'User-level paired differences are independent and sign-symmetric under the null; shared problems can violate independence.'}


def problem_sensitivity(delta, users, problems, *, reps=10000, batch=256):
    """Problem-cluster multiplicities reweight rows inside each user, then users.

    A user absent from the sampled problems is omitted in that replicate. This
    ratio bootstrap preserves the user-equal functional on each empirical
    resample, unlike a problem-equal mean. It is NOT a problem-held-out refit or
    a two-way-cluster robust interval.
    """
    _, ui = np.unique(np.asarray(users, str), return_inverse=True)
    problem_ids, pi = np.unique(np.asarray(problems, str), return_inverse=True)
    if len(problem_ids) < 2:
        return {'status': 'not_measured', 'reason': 'fewer than two problem clusters'}
    shape = (ui.max() + 1, len(problem_ids))
    sums, counts = np.zeros(shape), np.zeros(shape)
    np.add.at(sums, (ui, pi), delta)
    np.add.at(counts, (ui, pi), 1)
    rng = np.random.default_rng(91015)
    draws = np.empty(reps)
    for start in range(0, reps, batch):
        count = min(batch, reps - start)
        multiplicities = rng.multinomial(len(problem_ids), np.full(len(problem_ids), 1 / len(problem_ids)), count)
        denominators = multiplicities @ counts.T
        numerators = multiplicities @ sums.T
        represented = denominators > 0
        means = np.divide(numerators, denominators, out=np.zeros_like(numerators), where=represented)
        draws[start:start+count] = means.sum(axis=1) / represented.sum(axis=1)
    return {'status': 'evaluated', 'problem_clusters': len(problem_ids),
            'ci95': np.quantile(draws, [.025, .975]).tolist(), 'bootstrap_reps': reps,
            'seed': 91015, 'estimand': 'Mean across represented users of within-user row means, recomputed with sampled-problem multiplicities',
            'limitation': 'Sensitivity only; few shared problems, not two-way cluster robust and not problem-held-out generalization.'}


def holm(p_values):
    order = sorted(range(len(p_values)), key=lambda i: p_values[i])
    adjusted, running = [0.] * len(p_values), 0.
    for rank, index in enumerate(order):
        running = max(running, min(1., (len(order) - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def load_predictions(path):
    with np.load(path, allow_pickle=False) as data:
        ids = data['example_ids'].astype(str)
        labels = data['labels']
        if labels.dtype.kind in 'US':
            labels = np.asarray([LABELS.index(str(x)) for x in labels])
        if labels.dtype.kind not in 'iu' or labels.shape != (len(ids),) or (labels < 0).any() or (labels >= len(LABELS)).any():
            raise ValueError('invalid labels')
        if len(ids) != len(set(ids)) or ids.ndim != 1:
            raise ValueError('duplicate or malformed prediction ids')
        p = validate_probabilities(data['probabilities'], len(ids))
        seeds = np.asarray(data['seed_probabilities'], dtype=float)
        if seeds.shape != (len(SEEDS), len(ids), len(LABELS)):
            raise ValueError('seed predictions shape mismatch')
        for seed in seeds:
            validate_probabilities(seed, len(ids))
        if not np.allclose(seeds.mean(axis=0), p, atol=1e-12, rtol=1e-12):
            raise ValueError('ensemble is not mean of all three seeds')
        return {'ids': ids, 'labels': labels, 'p': p, 'seeds': seeds}


def strata(features, code_hashes):
    train = {(r['problem_id'], code_hashes[r['current_code_id']]) for r in features if r['split'] == 'train'}
    test = [r for r in features if r['split'] == 'test']
    groups = defaultdict(list)
    for row in test:
        groups[(row['problem_id'], code_hashes[row['current_code_id']])].append(row)
    collision_keys = set()
    for key, members in groups.items():
        histories = [(r['user_id'], tuple((code_hashes[h['code_id']], h['verdict']) for h in r['history'])) for r in members]
        # Require the differing histories to belong to different users, not
        # merely multiple histories within one user plus a second user.
        if any(u != v and h != j for i, (u, h) in enumerate(histories) for v, j in histories[i+1:]):
            collision_keys.add(key)
    result = {'train_code_seen': set(), 'train_code_unseen': set(), 'within_test_crossuser_distinct_history': set()}
    for row in test:
        key = row['problem_id'], code_hashes[row['current_code_id']]
        result['train_code_seen' if key in train else 'train_code_unseen'].add(row['example_id'])
        if key in collision_keys:
            result['within_test_crossuser_distinct_history'].add(row['example_id'])
    return result, collision_keys


def verify_seals(predictions, prepared, test_labels):
    report_path = predictions / 'test.json'
    if (predictions / 'COMPLETE').read_text().strip() != sha(report_path):
        raise ValueError('test prediction completion seal mismatch')
    report = json.loads(report_path.read_text())
    if report.get('test_opened') is not True or report.get('state') != 'complete' or report.get('automatic_retry') is not False:
        raise ValueError('test prediction report not sealed complete')
    for name in [arm + '-test.npz' for arm in ARMS] + ['metadata.json']:
        if sha(predictions / name) != report['file_sha256'][name]:
            raise ValueError('test prediction sealed hash mismatch')
    metadata = json.loads((predictions / 'metadata.json').read_text())
    frozen_sources = [digest for path, digest in metadata['source_sha256'].items()
                      if Path(path).name == Path(__file__).name]
    if frozen_sources != [sha(Path(__file__))]:
        raise ValueError('analysis source is not uniquely bound before test opening')
    if metadata['input_manifest_sha256'] != sha(prepared / 'manifest.json'):
        raise ValueError('test prediction prepared manifest binding mismatch')
    manifest = json.loads((prepared / 'manifest.json').read_text())
    for name, path in [('features.jsonl', prepared / 'features.jsonl'), ('codes.jsonl', prepared / 'codes.jsonl'), ('labels-test.jsonl', test_labels)]:
        if sha(path) != manifest['file_sha256'][name]:
            raise ValueError('prepared input hash mismatch')


def analyze(predictions, prepared, output, test_labels=None):
    test_labels = test_labels or prepared / 'labels-test.jsonl'
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (predictions, prepared)):
        raise ValueError('output must be a new directory outside input directories')
    verify_seals(predictions, prepared, test_labels)
    paths = [prepared / 'features.jsonl', prepared / 'codes.jsonl', prepared / 'manifest.json', test_labels,
             predictions / 'test.json', predictions / 'metadata.json', predictions / 'COMPLETE'] + [predictions / (arm + '-test.npz') for arm in ARMS]
    input_hashes = {str(p): sha(p) for p in paths}
    features = list(jsonl(prepared / 'features.jsonl'))
    by_id = {r['example_id']: r for r in features}
    if len(by_id) != len(features):
        raise ValueError('duplicate feature ids')
    code_hashes = {}
    for row in jsonl(prepared / 'codes.jsonl'):
        value = hashlib.sha256(row['code'].encode('utf-8')).hexdigest()
        if row.get('source_sha256', value) != value or row['code_id'] in code_hashes:
            raise ValueError('code hash mismatch or duplicate code id')
        code_hashes[row['code_id']] = value
    arms = {arm: load_predictions(predictions / (arm + '-test.npz')) for arm in ARMS}
    expected = {r['example_id'] for r in features if r['split'] == 'test'}
    expected_matched = {r['example_id'] for r in features if r['split'] == 'test' and r.get('donor_example_id') is not None}
    truth = {}
    for row in jsonl(test_labels):
        if row['example_id'] in truth:
            raise ValueError('duplicate test label')
        truth[row['example_id']] = LABELS.index(row['next_label'])
    if set(truth) != expected:
        raise ValueError('sealed test label coverage mismatch')
    for arm, data in arms.items():
        if set(data['ids']) != (expected_matched if arm.endswith('_M') else expected):
            raise ValueError('prediction cohort does not equal fixed eligible cohort')
    anchor_labels = dict(zip(arms['C_F']['ids'], arms['C_F']['labels']))
    if anchor_labels != truth:
        raise ValueError('prediction labels differ from sealed test labels')
    for data in arms.values():
        if any(anchor_labels[i] != y for i, y in zip(data['ids'], data['labels'])):
            raise ValueError('arm label mismatch')
    subsets, collision_keys = strata(features, code_hashes)
    report = {'version': 'frozen-history-inference-v1', 'input_sha256': input_hashes,
              'analysis_source_sha256': sha(Path(__file__)), 'numpy_version': np.__version__,
              'arms': {}, 'primary': {}, 'secondary': {},
              'limitations': ['Observational next-submission prediction, not learning or intervention efficacy.',
                             'Shared problems induce residual dependence across users.',
                             'Problem-held-out refitting and user-purged problem-held-out refitting are not measured by this analysis.']}
    for arm, data in arms.items():
        users = [by_id[i]['user_id'] for i in data['ids']]
        report['arms'][arm] = {'ensemble': metrics(data['labels'], data['p'], users),
            'seeds': {str(seed): metrics(data['labels'], p, users) for seed, p in zip(SEEDS, data['seeds'])}, 'strata': {}}
        report['arms'][arm]['problems'] = len({by_id[i]['problem_id'] for i in data['ids']})
        for name, ids in subsets.items():
            mask = np.asarray([i in ids for i in data['ids']])
            part = metrics(data['labels'][mask], data['p'][mask], np.asarray(users)[mask])
            part['problems'] = len({by_id[i]['problem_id'] for i in data['ids'][mask]})
            part['exact_code_groups'] = len({(by_id[i]['problem_id'], code_hashes[by_id[i]['current_code_id']]) for i in data['ids'][mask]})
            report['arms'][arm]['strata'][name] = part
    for baseline, history in [('C_F', 'H_F'), ('U_M', 'H_M'), ('C_F', 'S_F')]:
        a, b = arms[baseline], arms[history]
        lookup = {key: index for index, key in enumerate(b['ids'])}
        aligned = np.asarray([lookup[key] for key in a['ids']])
        delta = nll(a['labels'], a['p']) - nll(b['labels'][aligned], b['p'][aligned])
        users = np.asarray([by_id[i]['user_id'] for i in a['ids']])
        problems = np.asarray([by_id[i]['problem_id'] for i in a['ids']])
        result = paired_user_inference(delta, users)
        result['seed_improvement_nll'] = {str(seed): float(user_means(
            nll(a['labels'], pa) - nll(b['labels'][aligned], pb[aligned]), users)[1].mean())
            for seed, pa, pb in zip(SEEDS, a['seeds'], b['seeds'])} if len(users) else {}
        result['problem_cluster_sensitivity'] = problem_sensitivity(delta, users, problems)
        result['descriptive_strata'] = {}
        for name, ids in subsets.items():
            mask = np.asarray([i in ids for i in a['ids']])
            result['descriptive_strata'][name] = {'rows': int(mask.sum()), 'users': len(set(users[mask])),
                'improvement_nll': float(user_means(delta[mask], users[mask])[1].mean()) if mask.any() else None,
                'status': 'descriptive_only' if mask.any() else 'not_measured'}
        report['secondary' if history == 'S_F' else 'primary'][baseline + '-' + history] = result
    contrasts = list(report['primary'].values())
    if all(r['status'] == 'evaluated' for r in contrasts):
        for r, p in zip(contrasts, holm([r['one_sided_p'] for r in contrasts])):
            r['holm_adjusted_p'] = p
        report['gate_passed'] = all(r['improvement_nll'] > 0 and r['ci95'][0] > 0 and r['holm_adjusted_p'] < .05 for r in contrasts)
        report['gate_status'] = 'passed_predictive_signal_only' if report['gate_passed'] else 'not_passed'
    else:
        report['gate_passed'] = False
        report['gate_status'] = 'not_evaluable'
    report['within_test_collision_groups'] = len(collision_keys)
    collision_labels = defaultdict(set)
    for key in subsets['within_test_crossuser_distinct_history']:
        row = by_id[key]
        collision_labels[(row['problem_id'], code_hashes[row['current_code_id']])].add(truth[key])
    report['within_test_collision_label_diversity'] = {
        'groups_by_number_of_distinct_labels': {str(n): sum(len(v) == n for v in collision_labels.values()) for n in range(1, len(LABELS) + 1)},
        'groups_with_multiple_labels': sum(len(v) > 1 for v in collision_labels.values())}
    if any(sha(Path(path)) != digest for path, digest in input_hashes.items()):
        raise ValueError('inputs changed during analysis')
    if sha(Path(__file__)) != report['analysis_source_sha256']:
        raise ValueError('analysis source changed during execution')
    output.mkdir(parents=True)
    (output / 'inference.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    (output / 'manifest.json').write_text(json.dumps({'state': 'complete', 'test_opened': True,
        'input_sha256': input_hashes, 'analysis_source_sha256': report['analysis_source_sha256'],
        'file_sha256': {'inference.json': sha(output / 'inference.json')}}, indent=2) + '\n')
    (output / 'COMPLETE').write_text(sha(output / 'manifest.json') + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--test-labels', type=Path)
    args = parser.parse_args()
    result = analyze(args.predictions, args.prepared, args.output, args.test_labels)
    print(json.dumps({'gate_status': result['gate_status'], 'primary': result['primary']}, indent=2))
