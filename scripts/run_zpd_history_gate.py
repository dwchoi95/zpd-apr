"""Prepare split-sealed inputs and run train-only planning; test is not opened."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import time

from scripts.audit_zpd_history_support import digest_file, rows


def category(value):
    if not value:
        raise ValueError('unknown label/nominal verdict')
    return {'Accepted': 'AC', 'Wrong Answer': 'WA', 'Compile Error': 'CE',
            'Compilation Error': 'CE', 'Runtime Error': 'RE',
            'Time Limit Exceeded': 'RESOURCE', 'Memory Limit Exceeded': 'RESOURCE'}.get(value, 'OTHER')


def prepare(source, support, output):
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (source, support)):
        raise ValueError('use a new output outside input trees')
    manifest = json.loads((source / 'manifest.json').read_text())
    audit = json.loads((support / 'report.json').read_text())
    if digest_file(source / 'manifest.json') != audit['source_manifest_sha256']:
        raise ValueError('support/source mismatch')
    for name, expected in manifest['output_sha256'].items():
        if digest_file(source / name) != expected:
            raise ValueError('source hash mismatch')
    for name, expected in audit['output_sha256'].items():
        if digest_file(support / name) != expected:
            raise ValueError('support hash mismatch')
    summaries = {r['example_id']: r for r in rows(support / 'observed-summaries.jsonl')}
    donors = {r['example_id']: r['donor_example_id'] for r in rows(support / 'donors.jsonl')}
    if summaries.keys() != donors.keys():
        raise ValueError('donor coverage mismatch')
    output.mkdir(parents=True)
    counts, label_counts = Counter(), Counter()
    with (output / 'features.jsonl').open('x') as stream:
        emitted = set()
        for feature in rows(source / 'features.jsonl'):
            key = feature['example_id']
            if key not in summaries:
                continue
            observed = feature['observed_history']
            current, prior = observed[-1], observed[:-1]
            ref = summaries[key]
            row = {'example_id': key, 'user_id': ref['user_id'], 'problem_id': ref['problem_id'],
                   'split': ref['split'], 'timestamp': current['timestamp'],
                   'current_code_id': current['code_id'], 'current_verdict': category(current['verdict']),
                   'matching_current_verdict': current['verdict'],
                   'history': [{'code_id': h['code_id'], 'verdict': category(h['verdict']),
                                'timestamp': h['timestamp']} for h in prior],
                   'donor_example_id': donors[key]}
            stream.write(json.dumps(row) + '\n')
            emitted.add(key)
            counts[ref['split']] += 1
        if emitted != summaries.keys():
            raise ValueError('feature coverage mismatch')
    handles = {s: (output / f'labels-{s}.jsonl').open('x') for s in ('train', 'valid', 'test')}
    emitted = set()
    try:
        for label in rows(source / 'labels.jsonl'):
            key = label['example_id']
            if key not in summaries:
                continue
            if label['label_status'] != 'observed' or key in emitted:
                raise ValueError('invalid or duplicate observed label')
            split = summaries[key]['split']
            value = category(label['next_submission']['verdict'])
            handles[split].write(json.dumps({'example_id': key, 'next_label': value}) + '\n')
            label_counts[split] += 1
            emitted.add(key)
    finally:
        for handle in handles.values():
            handle.close()
    if emitted != summaries.keys() or counts != label_counts:
        raise ValueError('label coverage mismatch')
    shutil.copyfile(source / 'codes.jsonl', output / 'codes.jsonl')
    report = {'scope': 'prepared original-release development inputs; no fitting',
              'counts': dict(counts), 'source_manifest_sha256': digest_file(source / 'manifest.json'),
              'support_report_sha256': digest_file(support / 'report.json'),
              'test_users': audit['splits']['test']['users'],
              'matched_test_users': audit['splits']['test']['donor_available_users'],
              'file_sha256': {p.name: digest_file(p) for p in output.glob('*.jsonl')}}
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def load_training(input_root):
    manifest = json.loads((input_root / 'manifest.json').read_text())
    # Verify only the files accessed in this phase. Valid/test labels stay closed.
    for name in ('features.jsonl', 'codes.jsonl', 'labels-train.jsonl'):
        if digest_file(input_root / name) != manifest['file_sha256'][name]:
            raise ValueError('planning input changed')
    codes = {r['code_id']: r['code'] for r in rows(input_root / 'codes.jsonl')}
    labels = {r['example_id']: r['next_label'] for r in rows(input_root / 'labels-train.jsonl')}
    result = []
    for feature in rows(input_root / 'features.jsonl'):
        if feature['split'] != 'train':
            continue
        key = feature['example_id']
        result.append({k: feature[k] for k in ('example_id', 'user_id', 'problem_id', 'split',
                                              'timestamp', 'current_verdict', 'matching_current_verdict')}
                      | {'current_code': codes[feature['current_code_id']],
                         'history': [{'code': codes[h['code_id']], 'timestamp': h['timestamp'],
                                      'verdict': h['verdict']} for h in feature['history']],
                         'next_label': labels[key]})
    if len(result) != manifest['counts']['train'] or {r['example_id'] for r in result} != labels.keys():
        raise ValueError('training label coverage mismatch')
    return result, manifest


def power(input_root, protocol, output):
    from scripts.zpd_history_power import estimate_train_power
    import numpy, scipy, sklearn, sys
    if output.exists() or output.resolve().is_relative_to(input_root.resolve()):
        raise ValueError('planning output must be new and outside inputs')
    versions = {'numpy': numpy.__version__, 'scipy': scipy.__version__, 'sklearn': sklearn.__version__}
    if versions != {'numpy': '2.5.2', 'scipy': '1.18.1', 'sklearn': '1.9.0'}:
        raise ValueError(f'wrong frozen environment: {versions}')
    if not protocol.is_file():
        raise ValueError('missing implementation amendment')
    output.mkdir(parents=True)
    started = time.monotonic()
    source_files = [Path(__file__), Path('scripts/zpd_history_power.py'),
                    Path('scripts/zpd_history_predictor.py'), Path('scripts/audit_zpd_history_support.py')]
    frozen = {str(p): digest_file(p) for p in source_files}
    metadata = {'versions': versions, 'python': sys.version,
                'protocol_sha256': digest_file(protocol), 'source_sha256': frozen,
                'input_manifest_sha256': digest_file(input_root / 'manifest.json'),
                'allowed_label_files': ['labels-train.jsonl'], 'test_opened': False}
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps({'phase': 'loading_training', 'test_opened': False}), flush=True)
    train, manifest = load_training(input_root)
    print(json.dumps({'phase': 'train_only_crossfit', 'unique_train_examples': len(train)}), flush=True)
    with (output / 'progress.jsonl').open('x') as progress:
        def callback(event):
            row = dict(event, elapsed_sec=time.monotonic() - started)
            progress.write(json.dumps(row) + '\n')
            progress.flush()
            print(json.dumps(row), flush=True)
        result = estimate_train_power(train, prospective_test_users=manifest['test_users'],
                    prospective_matched_test_users=manifest['matched_test_users'],
                    provenance_verified=True, implementation_frozen=True, progress_callback=callback)
    if any(digest_file(Path(p)) != h for p, h in frozen.items()):
        raise ValueError('source changed during planning')
    if digest_file(protocol) != metadata['protocol_sha256'] or digest_file(input_root / 'manifest.json') != metadata['input_manifest_sha256']:
        raise ValueError('protocol/input manifest changed during planning')
    for name in ('features.jsonl', 'codes.jsonl', 'labels-train.jsonl'):
        if digest_file(input_root / name) != manifest['file_sha256'][name]:
            raise ValueError('planning input changed during execution')
    result['elapsed_sec'] = time.monotonic() - started
    result['test_opened'] = False
    (output / 'power.json').write_text(json.dumps(result, indent=2) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'power.json') + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('phase', choices=['prepare', 'power'])
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--support', type=Path)
    parser.add_argument('--protocol', type=Path)
    args = parser.parse_args()
    if args.phase == 'prepare':
        if args.support is None:
            parser.error('prepare requires --support')
        print(json.dumps(prepare(args.input, args.support, args.output), indent=2))
    else:
        if args.protocol is None:
            parser.error('power requires --protocol')
        power(args.input, args.protocol, args.output)
