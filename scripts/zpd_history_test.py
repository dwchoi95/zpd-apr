"""One-time frozen held-out prediction. No fitting, selection, or retry path."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import time

import numpy as np

from scripts.audit_zpd_history_support import digest_file, rows, match_donors
from scripts.zpd_history_power import summaries
from scripts.zpd_history_predictor import ARMS, LABELS, SEEDS, features, validate_rows
from scripts.zpd_history_selection import verified_files, verify_power


def consume_lock(path, record):
    """Durable exclusive reservation; never remove this file after failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(dict(record, state='consumed', automatic_retry=False, consumed_at=time.time()), handle)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def reconstruct_models(path, dimension):
    from sklearn.linear_model import SGDClassifier
    models = []
    with np.load(path, allow_pickle=False) as archive:
        expected = {f'{kind}_{seed}' for seed in SEEDS for kind in ('coef', 'intercept', 'classes')}
        if set(archive.files) != expected:
            raise ValueError('model archive keys mismatch')
        for seed in SEEDS:
            coef, intercept, classes = [archive[f'{kind}_{seed}'].copy()
                                       for kind in ('coef', 'intercept', 'classes')]
            if (coef.shape != (6, dimension) or intercept.shape != (6,) or
                    coef.dtype != np.float64 or intercept.dtype != np.float64 or
                    not np.array_equal(classes, np.arange(6)) or
                    not np.isfinite(coef).all() or not np.isfinite(intercept).all()):
                raise ValueError('invalid frozen model')
            model = SGDClassifier(loss='log_loss')
            model.coef_, model.intercept_, model.classes_ = coef, intercept, classes
            model.n_features_in_ = dimension
            models.append(model)
    return models


def dimensions(arm, n_features=2**18):
    return 2*n_features + 10 + (2*n_features + 48 if arm[0] in 'HU' else 9 if arm[0] == 'S' else 0)


def verify_selection(selection, input_root, protocol, power_root=None):
    sealed = json.loads((selection / 'selection.json').read_text())
    if digest_file(selection / 'selection.json') != (selection / 'COMPLETE').read_text().strip():
        raise ValueError('selection completion mismatch')
    if sealed.get('test_opened') is not False or set(sealed['arms']) != set(ARMS):
        raise ValueError('incomplete or already opened selection')
    required = {'metadata.json'} | {f'{a}-{s}' for a in ARMS for s in
                                   ('models.npz', 'validation.npz', 'selection.json')}
    if not required <= sealed['file_sha256'].keys():
        raise ValueError('unsealed selection artifacts')
    for name, expected in sealed['file_sha256'].items():
        if Path(name).name != name or digest_file(selection / name) != expected:
            raise ValueError('selection artifact hash mismatch')
    meta = json.loads((selection / 'metadata.json').read_text())
    if meta.get('test_opened') is not False or meta.get('allowed_label_files') != [
            'labels-train.jsonl', 'labels-valid.jsonl']:
        raise ValueError('selection label boundary violation')
    expected_files = {p.name: p for p in [Path('scripts') / n for n in
                     ('zpd_history_selection.py', 'zpd_history_predictor.py',
                      'zpd_history_power.py', 'audit_zpd_history_support.py')] +
                     [input_root / n for n in ('manifest.json', 'features.jsonl', 'codes.jsonl',
                                               'labels-train.jsonl', 'labels-valid.jsonl')] + [protocol]}
    checked = set()
    for old_path, expected in meta['input_source_sha256'].items():
        name = Path(old_path).name
        if name in expected_files:
            if name in checked or digest_file(expected_files[name]) != expected:
                raise ValueError('selection source/input/protocol mismatch: ' + name)
            checked.add(name)
    if checked != expected_files.keys():
        raise ValueError('missing selection provenance')
    if power_root is not None:
        power_checked = set()
        for old_path, expected in meta['input_source_sha256'].items():
            p = Path(old_path)
            if p.parent.name == 'power-results-v1':
                if p.name not in ('power.json', 'metadata.json', 'COMPLETE') or p.name in power_checked:
                    raise ValueError('unexpected power provenance')
                if digest_file(power_root / p.name) != expected:
                    raise ValueError('selection power artifact mismatch')
                power_checked.add(p.name)
        if power_checked != {'power.json', 'metadata.json', 'COMPLETE'}:
            raise ValueError('missing selection power provenance')
        verify_power(power_root, input_root, protocol)
    return sealed, meta


def load_observed(input_root):
    """No label reads: original donor recomputation uses training users only."""
    manifest = verified_files(input_root, ['features.jsonl', 'codes.jsonl'])
    codes = {}
    for r in rows(input_root / 'codes.jsonl'):
        if r['code_id'] in codes:
            raise ValueError('duplicate code id')
        codes[r['code_id']] = r['code']
    data, declared = [], {}
    for r in rows(input_root / 'features.jsonl'):
        item = {k: r[k] for k in ('example_id', 'user_id', 'problem_id', 'split', 'timestamp',
                                  'current_verdict', 'matching_current_verdict')}
        item.update(current_code=codes[r['current_code_id']], history=[
            {'code': codes[h['code_id']], 'timestamp': h['timestamp'], 'verdict': h['verdict']}
            for h in r['history']])
        data.append(item)
        declared[r['example_id']] = r['donor_example_id']
    validate_rows(data)
    if dict(Counter(r['split'] for r in data)) != manifest['counts']:
        raise ValueError('input denominator mismatch')
    records = summaries(data)
    for record, item in zip(records, data):
        record['split'] = item['split']
    if match_donors(records) != declared:
        raise ValueError('donor mapping mismatch')
    by_id = {r['example_id']: r for r in data}
    for r in data:
        donor = declared[r['example_id']]
        r['donor_history'] = None if donor is None else by_id[donor]['history']
    validate_rows(data)
    return data, manifest


def arm_rows(data, arm, split):
    return [r for r in data if r['split'] == split and
            (not arm.endswith('_M') or r['donor_history'] is not None)]


def predict(models, x):
    ps = np.stack([m.predict_proba(x) for m in models])
    if not np.isfinite(ps).all() or (ps < 0).any() or not np.allclose(ps.sum(axis=2), 1):
        raise ValueError('invalid predicted probabilities')
    return ps


def load_test_labels(input_root, expected_ids):
    verified_files(input_root, ['labels-test.jsonl'])
    labels = {}
    for r in rows(input_root / 'labels-test.jsonl'):
        if r['example_id'] in labels or r['next_label'] not in LABELS:
            raise ValueError('invalid test labels')
        labels[r['example_id']] = LABELS.index(r['next_label'])
    if labels.keys() != set(expected_ids):
        raise ValueError('test label coverage mismatch')
    return labels


def run(input_root, selection, protocol, lock, output, power_root, test_protocol):
    import scipy, sklearn
    versions = {'numpy': np.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    if versions != {'numpy': '2.5.2', 'scipy': '1.18.1', 'sklearn': '1.9.0'}:
        raise ValueError('wrong frozen runtime')
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (input_root, selection, power_root)):
        raise ValueError('new output outside inputs required')
    # Lock is global to the input cohort, not inside disposable run directories.
    allowed_locks = {Path('/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json').resolve()}
    if lock.resolve() not in allowed_locks or lock.resolve().is_relative_to(output.resolve()):
        raise ValueError('fixed global cohort TEST_CONSUMED.json lock required')
    if lock.exists():
        raise FileExistsError('test cohort already consumed')
    sealed, meta = verify_selection(selection, input_root, protocol, power_root)
    tracked = {str(p): digest_file(p) for p in
               [Path(__file__), protocol, test_protocol, input_root / 'manifest.json', selection / 'selection.json',
                selection / 'COMPLETE'] + [Path('scripts') / n for n in
                ('zpd_history_predictor.py', 'zpd_history_power.py', 'audit_zpd_history_support.py',
                 'zpd_history_selection.py', 'zpd_history_inference.py')]}
    reservation = {'input_manifest_sha256': digest_file(input_root / 'manifest.json'),
                   'selection_sha256': digest_file(selection / 'selection.json'),
                   'protocol_sha256': digest_file(protocol), 'source_sha256': tracked,
                   'test_protocol_sha256': digest_file(test_protocol),
                   'output': str(output.resolve()), 'pid': os.getpid(), 'timestamp': time.time()}
    output.mkdir(parents=True)
    (output / 'metadata.json').write_text(json.dumps(dict(reservation, versions=versions,
        source_sha256=tracked, lock=str(lock.resolve()), scope='observed-next prediction, not learning'), indent=2)+'\n')
    data, manifest = load_observed(input_root)
    models = {}
    for arm in ARMS:
        models[arm] = reconstruct_models(selection / f'{arm}-models.npz', dimensions(arm))
        valid = arm_rows(data, arm, 'valid')
        if not valid:
            raise ValueError('empty validation arm')
        with np.load(selection / f'{arm}-validation.npz', allow_pickle=False) as saved:
            if not np.array_equal(saved['example_ids'], [r['example_id'] for r in valid]):
                raise ValueError('validation row identity mismatch')
            ps = predict(models[arm], features(valid, arm[0]))
            if not np.allclose(ps, saved['seed_probabilities'], rtol=1e-12, atol=1e-14):
                raise ValueError('reconstructed model does not reproduce validation')
        for split in ('train', 'valid'):
            if sealed['arms'][arm][f'{split}_example_ids'] != [r['example_id'] for r in arm_rows(data, arm, split)]:
                raise ValueError('selection cohort mismatch')
        print(json.dumps({'phase': 'model_validated', 'arm': arm}), flush=True)
        if not arm_rows(data, arm, 'test'):
            raise ValueError('empty test arm; not evaluable before opening')
    # All selected models and provenance are validated before consuming the cohort.
    verify_selection(selection, input_root, protocol, power_root)
    verified_files(input_root, ['features.jsonl', 'codes.jsonl'])
    if any(digest_file(Path(p)) != h for p, h in tracked.items()):
        raise ValueError('inputs/source changed during preflight')
    consume_lock(lock, reservation)
    labels = load_test_labels(input_root, [r['example_id'] for r in data if r['split'] == 'test'])
    for arm in ARMS:
        test = arm_rows(data, arm, 'test')
        if not test:
            raise ValueError('empty test arm; consumed but not evaluable')
        ps = predict(models[arm], features(test, arm[0]))
        np.savez_compressed(output / f'{arm}-test.npz',
                            example_ids=np.array([r['example_id'] for r in test]),
                            user_ids=np.array([r['user_id'] for r in test]),
                            problem_ids=np.array([r['problem_id'] for r in test]),
                            labels=np.array([labels[r['example_id']] for r in test]),
                            seed_probabilities=ps, probabilities=ps.mean(axis=0))
        print(json.dumps({'phase': 'predicted', 'arm': arm, 'examples': len(test)}), flush=True)
    verify_selection(selection, input_root, protocol, power_root)
    verified_files(input_root, ['features.jsonl', 'codes.jsonl', 'labels-test.jsonl'])
    if any(digest_file(Path(p)) != h for p, h in tracked.items()):
        raise ValueError('inputs/source changed during test')
    report = {'test_opened': True, 'state': 'complete', 'automatic_retry': False,
              'file_sha256': {p.name: digest_file(p) for p in output.iterdir() if p.is_file()}}
    (output / 'test.json').write_text(json.dumps(report, indent=2)+'\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'test.json')+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('input', 'selection', 'protocol', 'lock', 'output', 'power', 'test-protocol'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    run(args.input, args.selection, args.protocol, args.lock, args.output, args.power, args.test_protocol)
