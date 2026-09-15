"""Frozen small runtime drift probe, separate from canonical experiment outputs."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

from src.runner.python_runner import PythonSubmissionRunner
from src.runner.models import TestCase


def digest(data):
    return hashlib.sha256(data).hexdigest()


def order_key(value):
    return digest(('zpd-runtime-20260915|' + value).encode())


def read(path):
    with path.open(encoding='utf-8') as source:
        return [json.loads(line) for line in source if line.strip()]


def prepare(root, output):
    if output.exists():
        raise ValueError('frozen sample already exists')
    cache_path = root / 'all-original-submissions.jsonl'
    cache_rows = read(cache_path)
    cache = {(r['problem_id'], r['submission_id']): r for r in cache_rows}
    if len(cache) != len(cache_rows):
        raise ValueError('duplicate cache identity')
    hashes = {str(cache_path): digest(cache_path.read_bytes())}
    records, counts = [], {}
    for split in ('train', 'valid'):
        path = root / 'canonical-datasets' / f'{split}-answer.jsonl'
        hashes[str(path)] = digest(path.read_bytes())
        targets = {}
        for row in read(path):
            if row['target_verdict'] != 'Accepted':
                raise ValueError('Answer target not historical AC')
            key = row['problem_id'], row['target_submission_id']
            if key in targets and targets[key]['target_code'] != row['target_code']:
                raise ValueError('same target ID has inconsistent code')
            targets[key] = row
        for verdict in ('AC', 'TLE'):
            candidates = sorted((key for key in targets if cache[key]['execution_verdict'] == verdict),
                                key=lambda k: order_key('|'.join(k)))
            selected = candidates[:4]
            counts[f'{split}-{verdict}'] = {'available': len(candidates), 'selected': len(selected)}
            for key in selected:
                path = root / 'testcases' / key[0] / 'testcases.jsonl'
                hashes[str(path)] = digest(path.read_bytes())
                cases = sorted(read(path), key=lambda r: order_key('|'.join((*key, r['case_id']))))[:3]
                records.append({'problem_id': key[0], 'submission_id': key[1], 'split': split,
                                'cached_verdict': verdict, 'code': targets[key]['target_code'],
                                'cached_tc_outcomes': {r['case_id']: cache[key]['tc_outcomes'][r['case_id']] for r in cases},
                                'testcases': cases})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'strata': counts, 'input_sha256': hashes, 'records': records}, ensure_ascii=False) + '\n')


def execute(sample_path, output):
    if output.exists():
        raise ValueError('probe output directory already exists; preserve previous run')
    sample = json.loads(sample_path.read_text())
    identities = [(r['problem_id'], r['submission_id']) for r in sample['records']]
    if not identities or len(identities) != len(set(identities)):
        raise ValueError('empty sample or duplicate submission identity')
    for row in sample['records']:
        keys = [r['case_id'] for r in row['testcases']]
        if not keys or len(keys) != len(set(keys)) or set(keys) != set(row['cached_tc_outcomes']):
            raise ValueError('invalid sample testcase identities')
    output.mkdir(parents=True)
    runner = PythonSubmissionRunner(timeout_sec=2.5, memory_limit_mb=2048, case_workers=1)
    metadata = {'sample_sha256': digest(sample_path.read_bytes()), 'python': sys.version,
                'executable': sys.executable, 'platform': platform.platform(),
                'cpu_count': os.cpu_count(), 'initial_load': os.getloadavg(),
                'source_sha256': {str(p): digest(p.read_bytes()) for p in (
                    Path(__file__), Path('src/runner/python_runner.py'),
                    Path('src/runner/models.py'), Path('src/runner/compare.py'))},
                'blocks': [1, 8, 8, 1], 'case_workers': 1, 'timeout_sec': 2.5,
                'memory_limit_mb': 2048, 'strata': sample['strata']}
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    started = time.monotonic()
    all_rows = []

    def run_one(row):
        result = runner.run_submission(problem_id=row['problem_id'], submission_id=row['submission_id'],
                                       code=row['code'], source_verdict='Accepted',
                                       testcases=[TestCase(c['case_id'], c['input'], c['expected_output']) for c in row['testcases']])
        return {'problem_id': row['problem_id'], 'submission_id': row['submission_id'],
                'split': row['split'], 'cached_verdict': row['cached_verdict'],
                'cached_tc_outcomes': row['cached_tc_outcomes'],
                'cases': [{'case_id': c.case_id, 'verdict': c.verdict.value, 'runtime_sec': c.runtime_sec}
                          for c in result.cases]}

    with (output / 'records.jsonl').open('x', encoding='utf-8') as stream:
        for block, workers in enumerate(metadata['blocks']):
            if time.monotonic() - started > 600:
                break
            with ThreadPoolExecutor(max_workers=workers) as executor:
                pending = [executor.submit(run_one, row) for row in sample['records']]
                for future in as_completed(pending):
                    row = {**future.result(), 'block': block, 'workers': workers}
                    all_rows.append(row)
                    stream.write(json.dumps(row) + '\n')
                    stream.flush()
            print(json.dumps({'block_complete': block, 'workers': workers,
                              'completed_submission_executions': len(all_rows),
                              'elapsed_sec': time.monotonic() - started}), flush=True)
    indexed = {(r['block'], r['problem_id'], r['submission_id']): r for r in all_rows}
    comparisons = {}
    for left, right in ((0, 3), (1, 2), (0, 1), (3, 2)):
        counts = Counter()
        for row in sample['records']:
            key = row['problem_id'], row['submission_id']
            a, b = indexed.get((left, *key)), indexed.get((right, *key))
            if a is None or b is None:
                continue
            for ca, cb in zip(a['cases'], b['cases'], strict=True):
                if ca['case_id'] != cb['case_id']:
                    raise ValueError('case mismatch')
                counts['cases'] += 1
                counts['disagreements'] += ca['verdict'] != cb['verdict']
                counts[f"{ca['verdict']}->{cb['verdict']}"] += 1
        comparisons[f'{left}-{right}'] = dict(counts)
    by_stratum = {}
    for block in range(4):
        for split in ('train', 'valid'):
            for verdict in ('AC', 'TLE'):
                counts = Counter()
                for row in all_rows:
                    if (row['block'], row['split'], row['cached_verdict']) != (block, split, verdict):
                        continue
                    for case in row['cases']:
                        counts[f"{row['cached_tc_outcomes'][case['case_id']]}->{case['verdict']}"] += 1
                by_stratum[f'{block}:{split}:{verdict}'] = dict(counts)
    complete = len(all_rows) == 4 * len(sample['records'])
    summary = {'complete': complete, 'records': len(all_rows), 'elapsed_sec': time.monotonic() - started,
               'paired_block_comparisons': comparisons, 'cached_to_fresh_cases': by_stratum,
               'final_load': os.getloadavg(), 'learning_effect': None}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    if complete:
        (output / 'COMPLETE').write_text(digest((output / 'records.jsonl').read_bytes()) + '\n')


def expand_full_cases(root, frozen_sample, output):
    """Keep every frozen target; expand to all current testcases without selection."""
    if output.exists():
        raise ValueError('frozen sample already exists')
    sample = json.loads(frozen_sample.read_text())
    cache_path = root / 'all-original-submissions.jsonl'
    if sample['input_sha256'][str(cache_path)] != digest(cache_path.read_bytes()):
        raise ValueError('cache changed since initial probe')
    cache_rows = read(cache_path)
    cache = {(r['problem_id'], r['submission_id']): r for r in cache_rows}
    if len(cache) != len(cache_rows):
        raise ValueError('duplicate cache identity')
    sample['parent_sample_sha256'] = digest(frozen_sample.read_bytes())
    for row in sample['records']:
        path = root / 'testcases' / row['problem_id'] / 'testcases.jsonl'
        if sample['input_sha256'][str(path)] != digest(path.read_bytes()):
            raise ValueError('testcases changed since initial probe')
        cases = sorted(read(path), key=lambda c: c['case_id'])
        expected = cache[(row['problem_id'], row['submission_id'])]['tc_outcomes']
        if set(expected) != {c['case_id'] for c in cases}:
            raise ValueError('full testcase coverage mismatch')
        row['testcases'] = cases
        row['cached_tc_outcomes'] = expected
    sample['followup'] = 'same frozen 16 targets, all testcases; no target reselection'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sample, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('mode', choices=['prepare', 'execute', 'expand'])
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frozen-sample', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare(args.input, args.output)
    elif args.mode == 'execute':
        execute(args.input, args.output)
    else:
        if args.frozen_sample is None:
            parser.error('expand requires --frozen-sample')
        expand_full_cases(args.input, args.frozen_sample, args.output)
