"""Fresh-holdout stage D power: train-only crossfit with the final P·Z estimator.

No valid/eval labels are read. The projected matched eval user count is derived
from verdict-blind structural counts and the valid donor match rate.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from statistics import NormalDist
import time

import numpy as np

from scripts.audit_zpd_history_support import digest_file, match_donors
from scripts.zpd_history_power import summaries
from scripts.zpd_history_predictor import LABELS, SEEDS
from scripts.zpd_history_v2_development import training_weights

SPEC = {'folds': 5, 'salt': 'zpd-fresh-power-20260917', 'alpha': 1e-4, 'seeds': list(SEEDS), 'epochs': 20,
        'arms': ['C_Z', 'H_PZ', 'U_PZ'], 'one_sided_alpha': .025, 'power': .80,
        'go_thresholds': {'U_H': .0159, 'C_H': .0096}}


def user_fold(user):
    return int(hashlib.sha256(f"{SPEC['salt']}:{user}".encode()).hexdigest(), 16) % SPEC['folds']


def mde(user_means, n):
    values = np.asarray(list(user_means.values()), dtype=np.float64)
    z = NormalDist().inv_cdf(1 - SPEC['one_sided_alpha']) + NormalDist().inv_cdf(SPEC['power'])
    variance = float(values.var(ddof=1))
    return {'user_count': len(values), 'mean_difference': float(values.mean()), 'sample_variance': variance,
            'projected_matched_eval_users': n, 'detectable_nll_difference': float(z * np.sqrt(variance / n))}


def go_decision(results):
    passed = {c: results[c]['detectable_nll_difference'] <= t for c, t in SPEC['go_thresholds'].items()}
    return {'per_contrast': passed, 'proceed_to_stage_e': all(passed.values()),
            'if_false': 'confirmation blocked (underpowered); eval verdicts stay closed; no rule changes'}


def ensemble_nll(train, held, arm, encoder, model_class, callback, fold):
    xt, xh = encoder.transform(train, arm), encoder.transform(held, arm)
    yt = np.asarray([LABELS.index(r['next_label']) for r in train])
    yh = np.asarray([LABELS.index(r['next_label']) for r in held])
    weights = training_weights(train)
    probabilities = []
    for seed in SPEC['seeds']:
        model = model_class(loss='log_loss', penalty='l2', alpha=SPEC['alpha'],
                            learning_rate='optimal', shuffle=False, random_state=seed)
        rng = np.random.default_rng(seed)
        for epoch in range(SPEC['epochs']):
            order = rng.permutation(len(train))
            model.partial_fit(xt[order], yt[order], classes=np.arange(len(LABELS)), sample_weight=weights[order])
        callback({'fold': fold, 'arm': arm, 'seed': seed, 'train_rows': len(train)})
        probabilities.append(model.predict_proba(xh))
    p = np.mean(probabilities, axis=0)
    return -np.log(np.clip(p[np.arange(len(held)), yh], 1e-15, 1))


def estimate(rows, projected_n, *, n_features=2**18, encoder_class=None, model_class=None, callback=print):
    if encoder_class is None:
        from scripts.zpd_history_v2_features import HistoryV2Encoder as encoder_class
    if model_class is None:
        from sklearn.linear_model import SGDClassifier as model_class
    if any(r['split'] != 'train' for r in rows):
        raise ValueError('power accepts train rows only')
    by_id, records = {r['example_id']: r for r in rows}, summaries(rows)
    differences, folds = {'C_H': defaultdict(list), 'U_H': defaultdict(list)}, []
    for fold in range(SPEC['folds']):
        allowed = {r['user_id'] for r in rows if user_fold(r['user_id']) != fold}
        mapping = match_donors(records, allowed_donor_users=allowed)
        matched = {True: [], False: []}
        for r in rows:
            donor = mapping[r['example_id']]
            if donor is None:
                continue
            d = by_id[donor]
            if d['user_id'] not in allowed or d['user_id'] == r['user_id'] or d['timestamp'] >= r['timestamp']:
                raise ValueError('invalid fold donor')
            matched[r['user_id'] in allowed].append(dict(r, donor_history=d['history']))
        train, held = matched[True], matched[False]
        folds.append({'fold': fold, 'matched_train_rows': len(train), 'matched_held_rows': len(held),
                      'held_users': len({r['user_id'] for r in held})})
        encoder = encoder_class(n_features=n_features).fit(train, training_weights(train))
        nll = {arm: ensemble_nll(train, held, arm, encoder, model_class, callback, fold) for arm in SPEC['arms']}
        for i, r in enumerate(held):
            differences['C_H'][r['user_id']].append(nll['C_Z'][i] - nll['H_PZ'][i])
            differences['U_H'][r['user_id']].append(nll['U_PZ'][i] - nll['H_PZ'][i])
    results = {c: mde({u: float(np.mean(v)) for u, v in d.items()}, projected_n) for c, d in differences.items()}
    return {'spec': SPEC, 'folds': folds, **results, 'decision': go_decision(results),
            'scope': 'train-only planning for fresh-holdout stage E; valid/eval labels not read'}


def run(input_root, support, staging, protocol, output):
    from scripts.run_zpd_history_gate import load_training
    import scipy
    import sklearn
    versions = {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    if versions != {'numpy': '2.5.2', 'scipy': '1.18.1', 'sklearn': '1.9.0'}:
        raise ValueError(f'wrong frozen runtime: {versions}')
    if output.exists():
        raise ValueError('output already exists')
    partition, report = json.loads((staging / 'partition.json').read_text()), json.loads((support / 'report.json').read_text())
    valid_ratio = report['splits']['valid']['donor_available_users'] / partition['structural_upper_bound_users']['valid']
    projected = int(round(partition['structural_upper_bound_users']['eval'] * valid_ratio))
    tracked = [protocol, staging / 'partition.json', support / 'report.json', input_root / 'manifest.json'] + \
        [Path('scripts') / n for n in ('zpd_fresh_power.py', 'zpd_history_power.py', 'zpd_history_v2_features.py',
                                       'zpd_history_v2_development.py', 'zpd_history_predictor.py',
                                       'audit_zpd_history_support.py', 'run_zpd_history_gate.py')]
    hashes = {str(p): digest_file(p) for p in tracked}
    output.mkdir(parents=True)
    started = time.monotonic()
    (output / 'metadata.json').write_text(json.dumps({'versions': versions, 'source_input_sha256': hashes,
        'allowed_label_files': ['labels-train.jsonl'], 'valid_match_ratio': valid_ratio,
        'projected_matched_eval_users': projected, 'eval_verdicts_opened': False}, indent=2) + '\n')
    rows, _ = load_training(input_root)
    with (output / 'progress.jsonl').open('x') as stream:
        def callback(event):
            line = json.dumps(dict(event, elapsed_sec=time.monotonic() - started))
            stream.write(line + '\n')
            stream.flush()
            print(line, flush=True)
        result = estimate(rows, projected, callback=callback)
    if any(digest_file(Path(p)) != h for p, h in hashes.items()):
        raise ValueError('inputs or sources changed during power estimation')
    result.update(elapsed_sec=time.monotonic() - started, valid_match_ratio=valid_ratio, eval_verdicts_opened=False)
    (output / 'power.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'power.json') + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'support', 'staging', 'protocol', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input, args.support, args.staging, args.protocol, args.output)
    print(json.dumps({k: result[k] for k in ('C_H', 'U_H', 'decision')}, indent=1))
