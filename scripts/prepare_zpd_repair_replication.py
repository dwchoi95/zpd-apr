"""Outcome-blind, fixed-budget development replication; never opens label files."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from scripts.zpd_history_predictor import lexical_tokens
from src.repair.dataset import _load_problem_context

SALT = 'repair-replication-20260921-v1'
SAMPLE_SIZE = 128


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    with path.open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def verify_files(root, hashes):
    for name, expected in hashes.items():
        path = root / name
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError('unsafe manifest filename')
        if sha(path.read_bytes()) != expected:
            raise ValueError('manifest mismatch: ' + name)


def prepare(root, data_root, previous_prepared, output, *, sample_size=SAMPLE_SIZE, require_original_cohort=False):
    """sample_size is injectable for fixtures; the CLI always requests 128."""
    if output.exists():
        raise ValueError('output already exists')
    if not isinstance(sample_size, int) or not 1 <= sample_size <= SAMPLE_SIZE:
        raise ValueError('invalid sample size')
    manifest_bytes = (root / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    input_hashes = {name: manifest['file_sha256'][name]
                    for name in ('features.jsonl', 'codes.jsonl')}
    verify_files(root, input_hashes)
    previous_bytes = (previous_prepared / 'manifest.json').read_bytes()
    previous_manifest = json.loads(previous_bytes)
    for required in ('observations.jsonl', 'requests.jsonl', 'exclusions.jsonl'):
        if required not in previous_manifest['output_sha256']:
            raise ValueError('incomplete previous manifest')
    verify_files(previous_prepared, previous_manifest['output_sha256'])
    if previous_manifest['input_sha256'] != input_hashes:
        raise ValueError('previous preparation used different input')
    previous = read(previous_prepared / 'observations.jsonl')
    if require_original_cohort and (len(previous) != 96 or
            Counter(r['split'] for r in previous) != Counter(train=64, valid=32) or
            len({r['user_id'] for r in previous}) != 96):
        raise ValueError('previous cohort must be original 64 train / 32 valid unique users')
    old_users = {r['user_id'] for r in previous}
    old_source_hashes = set()
    old_current_hashes = set()
    for row in previous:
        obs = row['observation']
        old_current_hashes.add(obs['current']['source_sha256'])
        for source in [obs['current'], *obs['prior'], *row['donor_history']]:
            if sha(source['source'].encode()) != source['source_sha256']:
                raise ValueError('previous source SHA mismatch')
            old_source_hashes.add(source['source_sha256'])
    rows = [r for r in read(root / 'features.jsonl') if r['split'] in ('train', 'valid')]
    indexed = {r['example_id']: r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError('duplicate example')
    code_rows = read(root / 'codes.jsonl')
    codes = {r['code_id']: r for r in code_rows}
    if len(codes) != len(code_rows):
        raise ValueError('duplicate code')
    for row in code_rows:
        if sha(row['code'].encode()) != row['source_sha256']:
            raise ValueError('source SHA mismatch')

    def source(key, timestamp, verdict):
        value = codes[key]
        if isinstance(timestamp, bool) or not math.isfinite(timestamp):
            raise ValueError('invalid timestamp')
        return dict(submission_id=key, timestamp=timestamp, verdict=verdict,
                    source=value['code'], source_sha256=value['source_sha256'])

    def history(row):
        source(row['current_code_id'], row['timestamp'], row['current_verdict'])
        result = [source(h['code_id'], h['timestamp'], h['verdict']) for h in row['history']]
        timestamps = [h['timestamp'] for h in result] + [row['timestamp']]
        if any(a >= b for a, b in zip(timestamps, timestamps[1:])):
            raise ValueError('history is not strictly past and ordered')
        identities = [h['submission_id'] for h in result] + [row['current_code_id']]
        if len(set(identities)) != len(identities):
            raise ValueError('duplicate history submission')
        return result

    def match_key(row):
        return (row['problem_id'], row['matching_current_verdict'], len(row['history']),
                sum(len(lexical_tokens(codes[h['code_id']]['code'])[0]) for h in row['history']))

    candidates = sorted((r for r in rows if r['split'] == 'valid' and r.get('donor_example_id')),
                        key=lambda r: (sha((SALT + '|' + r['example_id']).encode()), r['example_id']))
    selected, exclusions, seen_users = [], [], set()
    stats = Counter(valid_eligible=len(candidates))
    for row in candidates:
        if len(selected) == sample_size:
            break
        current = source(row['current_code_id'], row['timestamp'], row['current_verdict'])
        reasons = []
        if row['user_id'] in old_users:
            reasons.append('previous_selected_user')
        if current['source_sha256'] in old_current_hashes:
            reasons.append('previous_current_source')
        if current['source_sha256'] in old_source_hashes:
            reasons.append('previous_any_source')
        if row['user_id'] in seen_users:
            reasons.append('duplicate_selected_user')
        if reasons:
            exclusions.append(dict(example_id=row['example_id'], user_id=row['user_id'], reasons=reasons))
            stats.update(reasons)
            continue
        donor = indexed[row['donor_example_id']]
        if (donor['split'] != 'train' or donor['user_id'] == row['user_id']
                or donor['timestamp'] >= row['timestamp'] or match_key(row) != match_key(donor)):
            raise ValueError('donor mismatch')
        selected.append(dict(example_id=row['example_id'], user_id=row['user_id'], split='valid',
            bank_id=sha((row['problem_id'] + '|' + current['source_sha256']).encode()),
            observation=dict(problem_id=row['problem_id'], current=current, prior=history(row)),
            donor_history=history(donor), donor_user_id=donor['user_id'], donor_example_id=donor['example_id']))
        seen_users.add(row['user_id'])
    if len(selected) != sample_size:
        raise ValueError('insufficient fixed sample; no replacement family')
    stats['valid_selected'] = len(selected)
    requests, hashes = {}, {}
    for row in selected:
        obs = row['observation']
        pid = obs['problem_id']
        if Path(pid).name != pid or pid in ('.', '..'):
            raise ValueError('unsafe problem id')
        problem = data_root / pid
        for name in ('description.html', 'metadata.json', 'testcases.jsonl'):
            hashes[f'{pid}/{name}'] = sha((problem / name).read_bytes())
        context = _load_problem_context(problem)
        requests[row['bank_id']] = dict(bank_id=row['bank_id'], problem_id=pid,
            current_source=obs['current']['source'], problem_description=context['problem_description'],
            time_limit=context.get('time_limit'), memory_limit=context.get('memory_limit'))
    request_rows = list(requests.values())
    artifacts = {'observations.jsonl': selected, 'requests.jsonl': request_rows,
                 'requests-0.jsonl': request_rows[:64], 'requests-1.jsonl': request_rows[64:],
                 'exclusions.jsonl': exclusions}
    output.mkdir(parents=True)
    for name, values in artifacts.items():
        (output / name).write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values))
    result = dict(scope='development-only frozen-model replication; no label files read',
        counts=dict(stats), selection_salt=SALT, sample_size=sample_size,
        previous_manifest_sha256=sha(previous_bytes), input_manifest_sha256=sha(manifest_bytes),
        input_sha256=input_hashes, data_sha256=hashes,
        verified_source_count=len(codes), previous_selected_rows=len(previous),
        previous_users=len(old_users), previous_source_sha_count=len(old_source_hashes),
        selected_order=[r['example_id'] for r in selected],
        output_sha256={name: sha((output / name).read_bytes()) for name in artifacts})
    (output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--previous-prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.input, args.data_root, args.previous_prepared, args.output,
                             require_original_cohort=True)))
