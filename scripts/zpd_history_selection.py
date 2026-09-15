"""Frozen train/validation selection. No test-label reader or test evaluation CLI."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np

from scripts.audit_zpd_history_support import digest_file, rows, match_donors
from scripts.zpd_history_power import summaries
from scripts.zpd_history_predictor import ARMS, LABELS, SEEDS, FrozenGate, features, validate_rows


def verified_files(root, names):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name in names:
        if digest_file(root / name) != manifest['file_sha256'][name]:
            raise ValueError('input hash mismatch: ' + name)
    return manifest


def verify_power(power_root, input_root, protocol):
    result = json.loads((power_root / 'power.json').read_text())
    meta = json.loads((power_root / 'metadata.json').read_text())
    if digest_file(power_root / 'power.json') != (power_root / 'COMPLETE').read_text().strip():
        raise ValueError('power completion hash mismatch')
    if meta['input_manifest_sha256'] != digest_file(input_root / 'manifest.json'):
        raise ValueError('power used different inputs')
    if meta['protocol_sha256'] != digest_file(protocol):
        raise ValueError('power used different protocol')
    for old_path, expected in meta['source_sha256'].items():
        if digest_file(Path('scripts') / Path(old_path).name) != expected:
            raise ValueError('power source differs from frozen implementation')
    if result.get('test_opened') is not False or meta.get('allowed_label_files') != ['labels-train.jsonl']:
        raise ValueError('power label access violation')
    folds = result['folds']
    if len(folds) != 5 or {f['fold'] for f in folds} != set(range(5)):
        raise ValueError('power missing folds')
    if any(f.get(c) != 'evaluated' for f in folds for c in ('C_H', 'U_H')):
        raise ValueError('power contrast unavailable')
    if any(result[c]['status'] != 'estimated' for c in ('C_H', 'U_H')):
        raise ValueError('power estimate unavailable')
    return result


def load_selection(input_root):
    names = ['features.jsonl', 'codes.jsonl', 'labels-train.jsonl', 'labels-valid.jsonl']
    manifest = verified_files(input_root, names)
    codes = {}
    for row in rows(input_root / 'codes.jsonl'):
        if row['code_id'] in codes:
            raise ValueError('duplicate code')
        codes[row['code_id']] = row['code']
    labels = {}
    label_splits = {}
    for split in ('train', 'valid'):
        for row in rows(input_root / f'labels-{split}.jsonl'):
            if row['example_id'] in labels or row['next_label'] not in LABELS:
                raise ValueError('duplicate or invalid label')
            labels[row['example_id']] = row['next_label']
            label_splits[row['example_id']] = split
    selected, declared = [], {}
    for row in rows(input_root / 'features.jsonl'):
        if row['split'] == 'test':
            continue  # Does not resolve test source IDs or read test labels.
        key = row['example_id']
        if label_splits.get(key) != row['split']:
            raise ValueError('label split mismatch')
        selected.append({k: row[k] for k in ('example_id', 'user_id', 'problem_id', 'split',
                                             'timestamp', 'current_verdict', 'matching_current_verdict')}
                        | {'current_code': codes[row['current_code_id']],
                           'history': [{'code': codes[h['code_id']], 'timestamp': h['timestamp'],
                                        'verdict': h['verdict']} for h in row['history']],
                           'next_label': labels[key]})
        declared[key] = row['donor_example_id']
    validate_rows(selected)
    if {r['example_id'] for r in selected} != labels.keys():
        raise ValueError('label coverage mismatch')
    counts = Counter(r['split'] for r in selected)
    if any(counts[s] != manifest['counts'][s] for s in ('train', 'valid')):
        raise ValueError('split denominator mismatch')
    records = summaries(selected)
    split_by_id = {r['example_id']: r['split'] for r in selected}
    for r in records:
        r['split'] = split_by_id[r['example_id']]
    recomputed = match_donors(records)
    if recomputed != declared:
        raise ValueError('donor mapping mismatch')
    by_id = {r['example_id']: r for r in selected}
    for row in selected:
        donor = declared[row['example_id']]
        row['donor_history'] = None if donor is None else by_id[donor]['history']
    validate_rows(selected)
    return selected, manifest


def fit_selection(data, output, callback=None, n_features=2**18):
    """Caller verifies frozen provenance. Write models and validation only."""
    if any(r['split'] not in ('train', 'valid') for r in data):
        raise ValueError('selection rejects test rows')
    gate = FrozenGate(data, provenance_verified=True, implementation_frozen=True,
                      train_power_recorded=True, n_features=n_features)
    report = {}
    for arm in ARMS:
        if callback:
            callback({'phase': 'arm_start', 'condition': arm})
        chosen = gate.select(arm, callback)
        valid = [r for r in data if r['split'] == 'valid' and
                 (not arm.endswith('_M') or r['donor_history'] is not None)]
        x = features(valid, arm[0], n_features)
        ps = np.stack([m.predict_proba(x) for m in gate.selected[arm]])
        if not np.isfinite(ps).all() or not np.allclose(ps.sum(axis=2), 1):
            raise ValueError('invalid validation probabilities')
        arrays = {}
        for seed, model in zip(SEEDS, gate.selected[arm]):
            arrays.update({f'coef_{seed}': model.coef_, f'intercept_{seed}': model.intercept_,
                           f'classes_{seed}': model.classes_})
        np.savez_compressed(output / f'{arm}-models.npz', **arrays)
        np.savez_compressed(output / f'{arm}-validation.npz',
                            example_ids=np.array([r['example_id'] for r in valid]),
                            labels=np.array([LABELS.index(r['next_label']) for r in valid]),
                            seed_probabilities=ps, probabilities=ps.mean(axis=0))
        report[arm] = chosen
        (output / f'{arm}-selection.json').write_text(json.dumps(chosen, indent=2) + '\n')
    return report


def run(input_root, power_root, protocol, output):
    import scipy, sklearn
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (input_root, power_root)):
        raise ValueError('use a new output outside inputs')
    if (input_root / 'labels-test.jsonl').exists():
        raise ValueError('remove test labels from selection bundle, not original inputs')
    versions = {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    if versions != {'numpy': '2.5.2', 'scipy': '1.18.1', 'sklearn': '1.9.0'}:
        raise ValueError('wrong frozen runtime')
    power_result = verify_power(power_root, input_root, protocol)
    tracked = [Path(__file__), Path('scripts/zpd_history_predictor.py'),
               Path('scripts/zpd_history_power.py'), Path('scripts/audit_zpd_history_support.py'),
               protocol, input_root / 'manifest.json', power_root / 'power.json',
               power_root / 'metadata.json', power_root / 'COMPLETE']
    tracked.extend(input_root / n for n in ('features.jsonl', 'codes.jsonl', 'labels-train.jsonl', 'labels-valid.jsonl'))
    hashes = {str(p): digest_file(p) for p in tracked}
    output.mkdir(parents=True)
    started = time.monotonic()
    meta = {'versions': versions, 'input_source_sha256': hashes, 'test_opened': False,
            'allowed_label_files': ['labels-train.jsonl', 'labels-valid.jsonl'],
            'power': {c: {k: power_result[c][k] for k in ('mean_difference', 'detectable_nll_difference')}
                      for c in ('C_H', 'U_H')},
            'scope': 'development validation selection; not a test gate decision'}
    (output / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps({'phase': 'loading_selection', 'test_opened': False}), flush=True)
    data, _ = load_selection(input_root)
    with (output / 'progress.jsonl').open('x') as progress:
        def callback(event):
            value = dict(event, elapsed_sec=time.monotonic() - started)
            progress.write(json.dumps(value) + '\n')
            progress.flush()
            print(json.dumps(value), flush=True)
        report = fit_selection(data, output, callback)
    if any(digest_file(Path(p)) != h for p, h in hashes.items()):
        raise ValueError('source/input changed during selection')
    sealed = {'arms': report, 'elapsed_sec': time.monotonic() - started, 'test_opened': False,
              'file_sha256': {p.name: digest_file(p) for p in output.iterdir() if p.is_file()}}
    (output / 'selection.json').write_text(json.dumps(sealed, indent=2) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'selection.json') + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('input', 'power', 'protocol', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.input, args.power, args.protocol, args.output)
