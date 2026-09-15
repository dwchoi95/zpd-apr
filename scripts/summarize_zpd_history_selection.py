"""Descriptive validation results after model selection; not test inference."""
import argparse
from collections import defaultdict
import json
from pathlib import Path

import numpy as np

from scripts.audit_zpd_history_support import digest_file, rows
from scripts.zpd_history_predictor import ARMS, LABELS


def user_means(values, users):
    result = defaultdict(list)
    for value, user in zip(values, users):
        result[user].append(float(value))
    return {user: float(np.mean(v)) for user, v in result.items()}


def metrics(labels, probabilities, users):
    p = np.asarray(probabilities)
    y = np.asarray(labels)
    if p.shape != (len(y), 6) or len(users) != len(y) or not len(y):
        raise ValueError('metric shape mismatch')
    if not np.isfinite(p).all() or (p < 0).any() or not np.allclose(p.sum(axis=1), 1):
        raise ValueError('invalid probabilities')
    nll = -np.log(np.clip(p[np.arange(len(y)), y], 1e-15, 1))
    correct = (p.argmax(axis=1) == y).astype(float)
    brier = np.square(p - np.eye(6)[y]).sum(axis=1)
    counts = defaultdict(int)
    for u in users:
        counts[u] += 1
    weights = np.array([1 / (len(counts) * counts[u]) for u in users])
    confidence = p.max(axis=1)
    bins = np.minimum((confidence * 10).astype(int), 9)
    calibration = []
    ece = 0.0
    for i in range(10):
        mask = bins == i
        mass = float(weights[mask].sum())
        accuracy = float(np.average(correct[mask], weights=weights[mask])) if mass else None
        conf = float(np.average(confidence[mask], weights=weights[mask])) if mass else None
        if mass:
            ece += mass * abs(accuracy - conf)
        calibration.append({'bin': i, 'rows': int(mask.sum()), 'user_weight_mass': mass,
                            'accuracy': accuracy, 'confidence': conf})
    return {'rows': len(y), 'users': len(counts),
            'user_equal_nll': float(np.mean(list(user_means(nll, users).values()))),
            'user_equal_accuracy': float(np.dot(weights, correct)),
            'user_equal_multiclass_brier': float(np.dot(weights, brier)),
            'user_equal_ece_10bin': ece, 'calibration': calibration}, nll


def summarize(selection, inputs, output):
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (selection, inputs)):
        raise ValueError('new output outside inputs required')
    if digest_file(selection / 'selection.json') != (selection / 'COMPLETE').read_text().strip():
        raise ValueError('selection incomplete')
    seal = json.loads((selection / 'selection.json').read_text())
    if seal.get('test_opened') is not False or set(seal['arms']) != set(ARMS):
        raise ValueError('invalid selection seal')
    for name, expected in seal['file_sha256'].items():
        if digest_file(selection / name) != expected:
            raise ValueError('selection artifact changed')
    manifest = json.loads((inputs / 'manifest.json').read_text())
    for name in ('features.jsonl', 'labels-valid.jsonl'):
        if digest_file(inputs / name) != manifest['file_sha256'][name]:
            raise ValueError('input changed')
    metadata = json.loads((selection / 'metadata.json').read_text())
    if not any(Path(k).name == 'manifest.json' and v == digest_file(inputs / 'manifest.json')
               for k, v in metadata['input_source_sha256'].items()):
        raise ValueError('selection/input provenance mismatch')
    refs = {r['example_id']: r for r in rows(inputs / 'features.jsonl') if r['split'] == 'valid'}
    expected_labels = {r['example_id']: LABELS.index(r['next_label']) for r in rows(inputs / 'labels-valid.jsonl')}
    report, saved = {}, {}
    for arm in ARMS:
        with np.load(selection / f'{arm}-validation.npz', allow_pickle=False) as a:
            ids, labels, probs, seed_probs = a['example_ids'].tolist(), a['labels'], a['probabilities'], a['seed_probabilities']
        if ids != seal['arms'][arm]['valid_example_ids']:
            raise ValueError('validation IDs mismatch')
        if len(set(ids)) != len(ids) or labels.tolist() != [expected_labels[k] for k in ids]:
            raise ValueError('validation labels or uniqueness mismatch')
        if seed_probs.shape != (3, len(ids), 6) or not np.allclose(seed_probs.mean(axis=0), probs):
            raise ValueError('seed ensemble mismatch')
        users = [refs[k]['user_id'] for k in ids]
        summary, losses = metrics(labels, probs, users)
        summary['seed_metrics'] = [metrics(labels, p, users)[0] for p in seed_probs]
        summary['selected_alpha'] = seal['arms'][arm]['selected_alpha']
        report[arm] = summary
        saved[arm] = (ids, users, losses)
    paired = {}
    for key, baseline, history in (('C_H', 'C_F', 'H_F'), ('U_H', 'U_M', 'H_M'), ('C_S', 'C_F', 'S_F')):
        ids, users, left = saved[baseline]
        other_ids, _, right = saved[history]
        if ids != other_ids:
            raise ValueError('paired IDs mismatch')
        delta = left - right
        strata = defaultdict(list)
        for i, identity in enumerate(ids):
            strata[refs[identity]['matching_current_verdict']].append(i)
        paired[key] = {'user_equal_nll_improvement': float(np.mean(list(user_means(delta, users).values()))),
                       'by_current_verdict': {v: {'rows': len(index),
                            'user_equal_nll_improvement': float(np.mean(list(user_means(delta[index], [users[i] for i in index]).values())))}
                            for v, index in sorted(strata.items())}}
    result = {'scope': 'selected validation diagnostics; not unbiased test or inferential gate',
              'test_opened': False, 'arms': report, 'paired': paired,
              'selection_sha256': digest_file(selection / 'selection.json'),
              'script_sha256': digest_file(Path(__file__))}
    output.mkdir(parents=True)
    (output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'arms': {k: {v: r[v] for v in ('user_equal_nll', 'selected_alpha')} for k, r in report.items()},
                      'paired': paired}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('selection', 'input', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    summarize(args.selection, args.input, args.output)
