"""Outcome-blind preparation of a bounded, already-exposed development pilot."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.zpd_history_predictor import lexical_tokens
from src.repair.dataset import _load_problem_context


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def prepare(root, data_root, output):
    if output.exists():
        raise ValueError('output already exists')
    manifest = json.loads((root / 'manifest.json').read_text())
    for name in ('features.jsonl', 'codes.jsonl'):
        if sha((root / name).read_bytes()) != manifest['file_sha256'][name]:
            raise ValueError('input manifest mismatch')
    rows = [r for r in read(root / 'features.jsonl') if r['split'] in ('train', 'valid')]
    indexed = {r['example_id']: r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError('duplicate example')
    codes = {r['code_id']: r for r in read(root / 'codes.jsonl')}
    def code(key):
        value = codes[key]
        if sha(value['code'].encode()) != value['source_sha256']:
            raise ValueError('source SHA mismatch')
        return value['code']
    def source(key, timestamp, verdict):
        value = code(key)
        return dict(submission_id=key, timestamp=timestamp, verdict=verdict,
                    source=value, source_sha256=sha(value.encode()))
    def history(row):
        return [source(h['code_id'], h['timestamp'], h['verdict']) for h in row['history']]
    def match_key(row):
        return (row['problem_id'], row['matching_current_verdict'], len(row['history']),
                sum(len(lexical_tokens(code(h['code_id']))[0]) for h in row['history']))
    selected, seen_users, train_codes, stats, exclusions = [], set(), set(), Counter(), []
    for split, limit in (('train', 64), ('valid', 32)):
        count = 0
        candidates = sorted((r for r in rows if r['split'] == split and r.get('donor_example_id')),
                            key=lambda r: sha(('repair-dev-20260918-v1|' + r['example_id']).encode()))
        stats[split + '_eligible'] = len(candidates)
        for row in candidates:
            if count == limit:
                break
            if row['user_id'] in seen_users:
                stats[split + '_duplicate_user'] += 1
                exclusions.append(dict(example_id=row['example_id'],split=split,reason='duplicate selected user'))
                continue
            current = source(row['current_code_id'], row['timestamp'], row['current_verdict'])
            if split == 'valid' and current['source_sha256'] in train_codes:
                stats['valid_current_overlap'] += 1
                exclusions.append(dict(example_id=row['example_id'],split=split,reason='selected train current SHA overlap'))
                continue
            donor = indexed[row['donor_example_id']]
            if donor['split'] != 'train' or donor['user_id'] == row['user_id'] or donor['timestamp'] >= row['timestamp'] or match_key(row) != match_key(donor):
                raise ValueError('donor mismatch')
            bank_id = sha((row['problem_id'] + '|' + current['source_sha256']).encode())
            selected.append(dict(example_id=row['example_id'], user_id=row['user_id'], split=split,
                bank_id=bank_id, observation=dict(problem_id=row['problem_id'], current=current, prior=history(row)),
                donor_history=history(donor), donor_user_id=donor['user_id'], donor_example_id=donor['example_id']))
            seen_users.add(row['user_id'])
            if split == 'train':
                train_codes.add(current['source_sha256'])
            count += 1
        if count != limit:
            raise ValueError('insufficient fixed sample; no replacement family')
        stats[split + '_selected'] = count
    requests, hashes = {}, {}
    for row in selected:
        obs = row['observation']
        pid = obs['problem_id']
        problem = data_root / pid
        for name in ('description.html', 'metadata.json', 'testcases.jsonl'):
            hashes[f'{pid}/{name}'] = sha((problem / name).read_bytes())
        # Only context is serialized for generation. Testcases are only hashed.
        context = _load_problem_context(problem)
        requests[row['bank_id']] = dict(bank_id=row['bank_id'], problem_id=pid,
            current_source=obs['current']['source'], problem_description=context['problem_description'],
            time_limit=context.get('time_limit'), memory_limit=context.get('memory_limit'))
    output.mkdir(parents=True)
    for name, values in (('observations.jsonl', selected), ('requests.jsonl', list(requests.values())), ('exclusions.jsonl', exclusions)):
        (output / name).write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values))
    result = dict(scope='development-only; no labels/test read', counts=dict(stats),
        input_sha256={name: manifest['file_sha256'][name] for name in ('features.jsonl','codes.jsonl')},
        data_sha256=hashes, selection_salt='repair-dev-20260918-v1', selected_order=[r['example_id'] for r in selected],
        output_sha256={name: sha((output/name).read_bytes()) for name in ('observations.jsonl','requests.jsonl','exclusions.jsonl')})
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(counts=dict(stats), banks=len(requests))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--data-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.input, args.data_root, args.output)
