"""Bounded v2 train/validation diagnostic: no test-label or prediction reader."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from scripts.audit_zpd_history_support import digest_file
from scripts.zpd_history_predictor import ALPHAS, LABELS, SEEDS, user_equal_nll, validate_rows
from scripts.zpd_history_selection import load_selection, verify_power


ARMS = ('C_R', 'C_Z', 'H_PR', 'U_PR', 'H_PZ', 'U_PZ', 'H_IR', 'U_IR', 'H_IZ', 'U_IZ', 'S_MR', 'S_MZ')
H_TIE_ORDER = ('H_PR', 'H_PZ', 'H_IR', 'H_IZ')
EPOCHS = 20
EXPECTED_MANIFEST = '4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d'
ALLOWED_INPUTS = {'manifest.json', 'features.jsonl', 'codes.jsonl', 'labels-train.jsonl', 'labels-valid.jsonl'}


def require_development_bundle(root):
    """Physical bundle allowlist; old test labels/predictions cannot coexist here."""
    present = list(root.iterdir())
    if {p.name for p in present} != ALLOWED_INPUTS or any(not p.is_file() or p.is_symlink() for p in present):
        raise ValueError('development input directory must contain only the five allowed regular files; no test artifacts')


def verify_baseline(root, input_root):
    result = json.loads((root / 'selection.json').read_text())
    if (root / 'COMPLETE').read_text().strip() != digest_file(root / 'selection.json') or result.get('test_opened') is not False:
        raise ValueError('invalid baseline selection seal')
    expected = set(result['file_sha256']) | {'selection.json', 'COMPLETE'}
    if {p.name for p in root.iterdir()} != expected or any(not p.is_file() or p.is_symlink() for p in root.iterdir()):
        raise ValueError('baseline must contain exactly the sealed selection files, no added test artifacts')
    if any('test' in name.lower() for name in expected):
        raise ValueError('baseline selection contains test artifacts')
    for name, value in result['file_sha256'].items():
        if digest_file(root / name) != value:
            raise ValueError('baseline file hash mismatch')
    metadata = json.loads((root / 'metadata.json').read_text())
    bindings = [value for path, value in metadata['input_source_sha256'].items() if Path(path).name == 'manifest.json']
    if bindings != [digest_file(input_root / 'manifest.json')] or metadata.get('test_opened') is not False:
        raise ValueError('baseline input binding mismatch')
    if metadata.get('allowed_label_files') != ['labels-train.jsonl', 'labels-valid.jsonl']:
        raise ValueError('baseline label access mismatch')
    return result


def check_pr_anchor(arm, report, output, baseline):
    previous = {'H_PR': 'H_M', 'U_PR': 'U_M'}[arm]
    expected = json.loads((baseline / f'{previous}-selection.json').read_text())
    if report['selected_alpha'] != expected['selected_alpha']:
        raise ValueError('PR anchor selected alpha drift')
    old = {candidate['alpha']: candidate['seed_nll'] for candidate in expected['candidates']}
    if set(old) != {candidate['alpha'] for candidate in report['candidates']}:
        raise ValueError('PR anchor alpha grid drift')
    for candidate in report['candidates']:
        if not np.allclose(candidate['seed_nll'], old[candidate['alpha']], atol=1e-10, rtol=0):
            raise ValueError('PR anchor all-candidate seed NLL drift')
    with np.load(baseline / f'{previous}-validation.npz', allow_pickle=False) as a, np.load(output / report['validation_file'], allow_pickle=False) as b:
        for key in ('example_ids', 'labels'):
            if not np.array_equal(a[key], b[key]):
                raise ValueError('PR anchor validation identity/label drift')
        if not np.allclose(a['seed_probabilities'], b['seed_probabilities'], atol=1e-12, rtol=0):
            raise ValueError('PR anchor selected seed probability drift')
    return {'status': 'reproduced', 'baseline_arm': previous, 'nll_atol': 1e-10,
            'probability_atol': 1e-12, 'relative_tolerance': 0}


def training_weights(train):
    counts = Counter(r['user_id'] for r in train)
    result = np.asarray([1 / counts[r['user_id']] for r in train], dtype=float)
    return result / result.mean()


def check_probabilities(p, n):
    if p.shape != (n, len(LABELS)) or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(axis=1), 1):
        raise ValueError('nonfinite or invalid validation probabilities')


def descriptive_metrics(y, p, users):
    check_probabilities(p, len(y))
    counts = Counter(users)
    weights = np.asarray([1 / (len(counts) * counts[u]) for u in users])
    confidence, correct = p.max(axis=1), (p.argmax(axis=1) == y)
    indices = np.minimum((confidence * 10).astype(int), 9)
    bins, ece = [], 0.
    for index in range(10):
        take = indices == index
        mass = float(weights[take].sum())
        acc = float(weights[take] @ correct[take] / mass) if mass else None
        conf = float(weights[take] @ confidence[take] / mass) if mass else None
        if mass:
            ece += mass * abs(acc - conf)
        bins.append({'bin': index, 'rows': int(take.sum()), 'user_weight_mass': mass,
                     'accuracy': acc, 'confidence': conf})
    return {'user_equal_nll': user_equal_nll(y, p, users),
            'user_equal_brier': float(weights @ np.square(p - np.eye(6)[y]).sum(axis=1)),
            'user_equal_accuracy': float(weights @ correct), 'user_equal_ece_10': ece,
            'calibration': bins}


def select_alpha(candidates):
    return min(candidates, key=lambda c: (c['mean_seed_valid_nll'], -c['alpha']))


def development_decision(arms):
    selected = min(H_TIE_ORDER, key=lambda arm: (arms[arm]['mean_seed_valid_nll'], H_TIE_ORDER.index(arm)))
    scale = selected[-1]
    baseline, unrelated = 'C_' + scale, 'U_' + selected[2:]
    hnll = arms[selected]['ensemble']['user_equal_nll']
    improves = all(hnll < arms[a]['ensemble']['user_equal_nll'] for a in (baseline, unrelated))
    return {'selected_h_cell': selected, 'corresponding_c': baseline, 'corresponding_u': unrelated,
            'selection_rule': 'mean-seed validation NLL; ties PR,PZ,IR,IZ; never maximize H-U gap',
            'validation_descriptive_improves_both': improves,
            'next_action': 'new_holdout_eligibility_audit_only' if improves else 'stop_this_family',
            'test_gate_evaluated': False, 'old_test_reopening_allowed': False,
            'claim': 'Development model selection only; not confirmatory evidence or learning efficacy.'}


def comparison_summary(arms):
    result = {}
    for h in H_TIE_ORDER:
        c, u = 'C_' + h[-1], 'U_' + h[2:]
        result[h] = {name: {'ensemble_nll_improvement': arms[base]['ensemble']['user_equal_nll'] - arms[h]['ensemble']['user_equal_nll'],
                           'seed_nll_improvement': [a - b for a, b in zip(arms[base]['seed_nll'], arms[h]['seed_nll'])]}
                     for name, base in [('C_minus_H', c), ('U_minus_H', u)]}
    cells = {h[2:]: arms[h]['ensemble']['user_equal_nll'] for h in H_TIE_ORDER}
    result['factorial_h_descriptive'] = {
        'representation_improvement_raw': cells['PR'] - cells['IR'],
        'representation_improvement_scaled': cells['PZ'] - cells['IZ'],
        'scaling_improvement_pooled': cells['PR'] - cells['PZ'],
        'scaling_improvement_interaction': cells['IR'] - cells['IZ'],
        'difference_in_representation_improvement_scaled_minus_raw': (cells['PZ'] - cells['IZ']) - (cells['PR'] - cells['IR']),
        'limitation': 'Descriptive validation contrasts; representation also changes dimension and regularization geometry.'}
    result['structural_scaling'] = {
        'S_R_minus_S_Z_nll': arms['S_MR']['ensemble']['user_equal_nll'] - arms['S_MZ']['ensemble']['user_equal_nll'],
        'C_R_minus_S_R_nll': arms['C_R']['ensemble']['user_equal_nll'] - arms['S_MR']['ensemble']['user_equal_nll'],
        'C_Z_minus_S_Z_nll': arms['C_Z']['ensemble']['user_equal_nll'] - arms['S_MZ']['ensemble']['user_equal_nll']}
    return result


def smoke(train, encoder_class, model_class, n_features):
    selected = sorted(train, key=lambda r: (hashlib.sha256(r['example_id'].encode()).hexdigest(), r['example_id']))[:128]
    weights = training_weights(selected)
    encoder = encoder_class(n_features=n_features).fit(selected, weights)
    y = np.asarray([LABELS.index(r['next_label']) for r in selected])
    for arm in ARMS:
        x = encoder.transform(selected, arm)
        if not np.isfinite(x.data).all():
            raise ValueError('smoke feature nonfinite')
        model = model_class(loss='log_loss', penalty='l2', alpha=1e-4,
                            learning_rate='optimal', shuffle=False, random_state=2027)
        model.partial_fit(x, y, classes=np.arange(6), sample_weight=weights)
        check_probabilities(model.predict_proba(x), len(selected))
    return {'status': 'passed', 'rows': len(selected), 'conditions': len(ARMS),
            'example_id_sha256': hashlib.sha256('\n'.join(r['example_id'] for r in selected).encode()).hexdigest(),
            'purpose': 'Finite feature/optimizer smoke only; models discarded and no outcome scores reported',
            'smoke_example_exposures': len(selected) * len(ARMS)}


def fit_development(data, output, callback=None, *, n_features=2**18, encoder_class=None, model_class=None, baseline=None):
    if encoder_class is None:
        from scripts.zpd_history_v2_features import HistoryV2Encoder
        encoder_class = HistoryV2Encoder
    if model_class is None:
        from sklearn.linear_model import SGDClassifier
        model_class = SGDClassifier
    if any(r['split'] not in ('train', 'valid') for r in data):
        raise ValueError('v2 fitting rejects all test rows')
    if len(ARMS) != 12 or len(set(ARMS)) != 12:
        raise ValueError('fixed twelve distinct arm contract changed')
    validate_rows(data)
    matched = [r for r in data if r.get('donor_history') is not None]
    train, valid = [[r for r in matched if r['split'] == split] for split in ('train', 'valid')]
    if not train or not valid:
        raise ValueError('matched train/valid empty')
    smoke_report = smoke(train, encoder_class, model_class, n_features)
    (output / 'smoke.json').write_text(json.dumps(smoke_report, indent=2) + '\n')
    weights = training_weights(train)
    encoder = encoder_class(n_features=n_features).fit(train, weights)
    (output / 'scaler.json').write_text(json.dumps(encoder.state_dict(), indent=2, allow_nan=False) + '\n')
    yt, yv = [np.asarray([LABELS.index(r['next_label']) for r in group]) for group in (train, valid)]
    users = [r['user_id'] for r in valid]
    cohorts = {split: [r['example_id'] for r in group] for split, group in [('train', train), ('valid', valid)]}
    (output / 'cohort.json').write_text(json.dumps(cohorts, indent=2) + '\n')
    total, completed, reports = len(train) * len(ARMS) * len(ALPHAS) * len(SEEDS) * EPOCHS, 0, {}
    for arm in ARMS:
        if callback:
            callback({'phase': 'feature_start', 'condition': arm, 'completed_train_example_exposures': completed,
                      'total_train_example_exposures': total})
        xt, xv = encoder.transform(train, arm), encoder.transform(valid, arm)
        if xt.shape[1] != xv.shape[1] or not np.isfinite(xt.data).all() or not np.isfinite(xv.data).all():
            raise ValueError('invalid train/valid feature matrices')
        candidates = []
        for alpha in ALPHAS:
            probabilities, seed_scores, files = [], [], []
            for seed in SEEDS:
                model = model_class(loss='log_loss', penalty='l2', alpha=alpha,
                                    learning_rate='optimal', shuffle=False, random_state=seed)
                rng = np.random.default_rng(seed)
                for epoch in range(EPOCHS):
                    order = rng.permutation(len(train))
                    model.partial_fit(xt[order], yt[order], classes=np.arange(6), sample_weight=weights[order])
                    completed += len(train)
                    if callback:
                        callback({'phase': 'fit', 'condition': arm, 'alpha': alpha, 'seed': seed, 'epoch': epoch + 1,
                                  'completed_train_example_exposures': completed, 'total_train_example_exposures': total,
                                  'unique_train_examples': len(train)})
                p = model.predict_proba(xv)
                check_probabilities(p, len(valid))
                probabilities.append(p)
                seed_scores.append(user_equal_nll(yv, p, users))
                filename = f'{arm}-alpha{alpha:g}-seed{seed}-model.npz'
                np.savez_compressed(output / filename, coef=model.coef_, intercept=model.intercept_, classes=model.classes_)
                files.append(filename)
            ps = np.stack(probabilities)
            validation_file = f'{arm}-alpha{alpha:g}-validation.npz'
            np.savez_compressed(output / validation_file, example_ids=np.asarray(cohorts['valid']), labels=yv,
                                seed_probabilities=ps, probabilities=ps.mean(axis=0))
            candidate = {'alpha': alpha, 'seed_nll': seed_scores, 'mean_seed_valid_nll': float(np.mean(seed_scores)),
                         'seed_metrics': {str(seed): descriptive_metrics(yv, p, users) for seed, p in zip(SEEDS, ps)},
                         'ensemble': descriptive_metrics(yv, ps.mean(axis=0), users), 'model_files': files,
                         'validation_file': validation_file}
            candidates.append(candidate)
            (output / f'{arm}-alpha{alpha:g}-candidate.json').write_text(json.dumps(candidate, indent=2, allow_nan=False) + '\n')
        chosen = select_alpha(candidates)
        reports[arm] = dict(chosen, candidates=candidates, feature_dimensions=xt.shape[1],
                            train_examples=len(train), valid_examples=len(valid), selected_alpha=chosen['alpha'])
        if baseline is not None and arm in ('H_PR', 'U_PR'):
            reports[arm]['v1_reproduction_anchor'] = check_pr_anchor(arm, reports[arm], output, baseline)
        name = f'{arm}-selection.json'
        (output / name).write_text(json.dumps(reports[arm], indent=2, allow_nan=False) + '\n')
        arm_files = [p for p in output.iterdir() if p.name.startswith(arm + '-') and p.is_file()]
        (output / f'{arm}-COMPLETE.json').write_text(json.dumps({'state': 'complete', 'test_opened': False,
            'file_sha256': {p.name: digest_file(p) for p in arm_files}}, indent=2) + '\n')
        del xt, xv
    if completed != total:
        raise ValueError('incomplete fixed fitting budget')
    return {'arms': reports, 'decision': development_decision(reports), 'comparisons': comparison_summary(reports),
            'completed_train_example_exposures': completed, 'total_train_example_exposures': total,
            'fit_count': len(ARMS) * len(ALPHAS) * len(SEEDS), 'smoke': smoke_report,
            'test_opened': False, 'old_test_reopening_allowed': False}


def run(input_root, protocol, output, baseline, power_root=None, power_protocol=None):
    import scipy
    import sklearn
    require_development_bundle(input_root)
    if power_root is None or power_protocol is None:
        raise ValueError('original power root and protocol provenance are required')
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (input_root, baseline, power_root)):
        raise ValueError('use new output outside inputs; automatic retry is disabled')
    versions = {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    if versions != {'numpy': '2.5.2', 'scipy': '1.18.1', 'sklearn': '1.9.0'}:
        raise ValueError('wrong frozen runtime')
    if digest_file(input_root / 'manifest.json') != EXPECTED_MANIFEST:
        raise ValueError('v2 diagnostic must use fixed v1 prepared manifest')
    verify_baseline(baseline, input_root)
    verify_power(power_root, input_root, power_protocol)
    tracked = [protocol] + [input_root / name for name in sorted(ALLOWED_INPUTS)]
    tracked += [Path('scripts') / name for name in ('zpd_history_v2_development.py', 'zpd_history_v2_features.py',
                'zpd_history_predictor.py', 'zpd_history_selection.py', 'zpd_history_power.py', 'audit_zpd_history_support.py')]
    tracked += list(baseline.iterdir())
    tracked += [power_protocol] + [power_root / name for name in ('power.json', 'metadata.json', 'COMPLETE')]
    hashes = {str(p): digest_file(p) for p in tracked}
    output.mkdir(parents=True)
    started = time.monotonic()
    metadata = {'versions': versions, 'source_input_sha256': hashes, 'test_opened': False,
                'allowed_label_files': ['labels-train.jsonl', 'labels-valid.jsonl'], 'automatic_retry': False,
                'original_power_verified': True,
                'arms': list(ARMS), 'alphas': list(ALPHAS), 'seeds': list(SEEDS), 'epochs': EPOCHS,
                'candidate_model_retention': 'All 108 archives retained; no model deletion or automatic pruning',
                'scope': 'post-v1-test bounded development diagnostic, no new holdout or test evaluation'}
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    data, _ = load_selection(input_root)
    sizes = Counter(r['split'] for r in data if r.get('donor_history') is not None)
    if sizes != {'train': 31980, 'valid': 6833}:
        raise ValueError('fixed matched population changed')
    with (output / 'progress.jsonl').open('x') as stream:
        def callback(event):
            value = dict(event, elapsed_sec=time.monotonic() - started)
            stream.write(json.dumps(value) + '\n')
            stream.flush()
            print(json.dumps(value), flush=True)
        result = fit_development(data, output, callback, baseline=baseline)
    require_development_bundle(input_root)
    verify_baseline(baseline, input_root)
    if any(digest_file(Path(path)) != value for path, value in hashes.items()):
        raise ValueError('source or inputs changed during development')
    result['elapsed_sec'] = time.monotonic() - started
    (output / 'development.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    manifest = {'state': 'complete', 'test_opened': False, 'automatic_retry': False,
                'source_input_sha256': hashes,
                'file_sha256': {p.name: digest_file(p) for p in output.iterdir() if p.is_file()}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'manifest.json') + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('input', 'protocol', 'output', 'baseline-selection'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--power', type=Path, required=True)
    parser.add_argument('--power-protocol', type=Path, required=True)
    args = parser.parse_args()
    run(args.input, args.protocol, args.output, args.baseline_selection, args.power, args.power_protocol)
