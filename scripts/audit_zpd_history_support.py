"""Label-blind donor/collision feasibility checks for original prefixes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from scripts.zpd_history_predictor import lexical_tokens


def digest_file(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rows(path):
    with path.open(encoding='utf-8') as stream:
        yield from (json.loads(line) for line in stream if line.strip())


def donor_score(row):
    return hashlib.sha256(('zpd-history-donor-v1:' + row['example_id']).encode()).hexdigest()


def match_donors(records, allowed_donor_users=None):
    """Train-only, different-user, strictly-past exact matching; no labels read.

    allowed_donor_users further restricts the pool for fold-held-out power checks.
    Caller must pass only observed-feature summaries and auditable identities.
    """
    buckets = defaultdict(list)
    for row in records:
        buckets[(row['problem_id'], row['current_verdict'], row['prior_count'], row['prior_tokens'])].append(row)
    result = {}
    for group in buckets.values():
        donors = sorted((r for r in group if r['split'] == 'train'
                         and (allowed_donor_users is None or r['user_id'] in allowed_donor_users)),
                        key=lambda r: (r['timestamp'], r['example_id']))
        index, top = 0, []
        for recipient in sorted(group, key=lambda r: (r['timestamp'], r['example_id'])):
            while index < len(donors) and donors[index]['timestamp'] < recipient['timestamp']:
                donor = donors[index]
                candidate = (donor_score(donor), donor['example_id'], donor['user_id'])
                distinct = []
                for item in sorted(top + [candidate]):
                    if item[2] not in {x[2] for x in distinct}:
                        distinct.append(item)
                top = distinct[:2]
                index += 1
            choice = next((d for d in top if d[2] != recipient['user_id']), None)
            result[recipient['example_id']] = choice[1] if choice else None
    return result


def audit(root, output):
    if output.exists() or output.resolve().is_relative_to(root.resolve()):
        raise ValueError('output must be a new directory outside inputs')
    manifest = json.loads((root / 'manifest.json').read_text())
    if not (root / 'COMPLETE').exists():
        raise ValueError('original inventory incomplete')
    names = ('features.jsonl', 'references.jsonl', 'codes.jsonl')
    for name in names:
        if digest_file(root / name) != manifest['output_sha256'][name]:
            raise ValueError('inventory hash mismatch')
    code_info = {}
    for row in rows(root / 'codes.jsonl'):
        if row['code_id'] in code_info:
            raise ValueError('duplicate code identity')
        if hashlib.sha256(row['code'].encode('utf-8')).hexdigest() != row['source_sha256']:
            raise ValueError('code hash mismatch')
        token_list, failed = lexical_tokens(row['code'])
        code_info[row['code_id']] = (len(token_list), row['source_sha256'], failed)
    references = {}
    for row in rows(root / 'references.jsonl'):
        if row['example_id'] in references:
            raise ValueError('duplicate reference identity')
        references[row['example_id']] = row
    records, seen, user_splits = [], set(), {}
    for feature in rows(root / 'features.jsonl'):
        key = feature['example_id']
        if key in seen:
            raise ValueError('duplicate feature identity')
        seen.add(key)
        ref = references[key]
        if not ref['primary_eligible']:
            continue
        history = feature['observed_history']
        current, prior = history[-1], history[:-1]
        if not prior or any(h['timestamp'] >= current['timestamp'] for h in prior):
            raise ValueError('invalid observed time order')
        if user_splits.setdefault(ref['user_id'], ref['split']) != ref['split']:
            raise ValueError('user split leakage')
        records.append({'example_id': key, 'user_id': ref['user_id'], 'problem_id': ref['problem_id'],
                        'split': ref['split'], 'timestamp': current['timestamp'],
                        'current_verdict': current['verdict'], 'prior_count': len(prior),
                        'prior_tokens': sum(code_info[h['code_id']][0] for h in prior),
                        'history_content_sha256': hashlib.sha256(json.dumps(
                            [(code_info[h['code_id']][1], h['verdict']) for h in prior],
                            separators=(',', ':')).encode()).hexdigest(),
                        'current_code_sha256': code_info[current['code_id']][1],
                        'prior_tokenization_failures': sum(code_info[h['code_id']][2] for h in prior)})
    if len(records) != manifest['counts']['primary_eligible_prefixes']:
        raise ValueError('eligible feature coverage mismatch')
    assignments = match_donors(records)
    by_id = {r['example_id']: r for r in records}
    for recipient, donor in assignments.items():
        if donor is None:
            continue
        r, d = by_id[recipient], by_id[donor]
        if d['split'] != 'train' or d['user_id'] == r['user_id'] or d['timestamp'] >= r['timestamp']:
            raise ValueError('invalid donor assignment')
    report = {'scope': 'label-value-blind feasibility conditional on observed-next eligibility; no fitting or test performance',
              'labels_opened': False, 'splits': {}, 'cross_code': {},
              'source_manifest_sha256': digest_file(root / 'manifest.json'),
              'source_sha256': {str(p): digest_file(p) for p in
                               [Path(__file__), Path('scripts/zpd_history_predictor.py')]}}
    groups = defaultdict(list)
    for row in records:
        groups[(row['problem_id'], row['current_code_sha256'])].append(row)
    train_keys = {k for k, g in groups.items() if any(r['split'] == 'train' for r in g)}
    collision_keys = {k for k, g in groups.items() if len({r['user_id'] for r in g}) > 1}
    for split in ('train', 'valid', 'test'):
        group = [r for r in records if r['split'] == split]
        matched = [r for r in group if assignments[r['example_id']] is not None]
        within = defaultdict(list)
        for row in group:
            within[(row['problem_id'], row['current_code_sha256'])].append(row)
        within_distinct = {k for k, members in within.items()
                           if len({r['user_id'] for r in members}) > 1
                           and len({r['history_content_sha256'] for r in members}) > 1}
        report['splits'][split] = {'rows': len(group), 'users': len({r['user_id'] for r in group}),
            'problems': len({r['problem_id'] for r in group}), 'donor_available_rows': len(matched),
            'donor_available_users': len({r['user_id'] for r in matched}),
            'donor_available_problems': len({r['problem_id'] for r in matched}),
            'current_verdicts': dict(Counter(r['current_verdict'] for r in group)),
            'rows_with_prior_tokenization_failure': sum(r['prior_tokenization_failures'] > 0 for r in group),
            'all_splits_cross_user_code_collision_rows': sum((r['problem_id'], r['current_code_sha256']) in collision_keys for r in group),
            'within_split_cross_user_distinct_history_groups': len(within_distinct),
            'within_split_cross_user_distinct_history_rows': sum(len(within[k]) for k in within_distinct),
            'current_code_seen_in_train_rows': sum((r['problem_id'], r['current_code_sha256']) in train_keys for r in group)}
    report['cross_code']['cross_user_groups_all_splits'] = len(collision_keys)
    report['donor_comparison_defined'] = all(v['donor_available_rows'] > 0 for v in report['splits'].values())
    output.mkdir(parents=True)
    with (output / 'observed-summaries.jsonl').open('x') as stream:
        for row in records:
            stream.write(json.dumps(row) + '\n')
    with (output / 'donors.jsonl').open('x') as stream:
        for key, donor in assignments.items():
            stream.write(json.dumps({'example_id': key, 'donor_example_id': donor}) + '\n')
    report['output_sha256'] = {p.name: digest_file(p) for p in output.glob('*.jsonl')}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.input, args.output), indent=2))
