"""Fresh-holdout stage B/D: stage dev-user metadata and build dev prefixes.

`stage` copies only train/valid user rows of the fixed AtCoder roster. Eval and
excluded users are dropped by user_id alone, so nothing else in their rows can
affect any output. `build` runs the unmodified v1 prefix builder on that staging.
"""
import argparse
import csv
from collections import defaultdict
import hashlib
import json
from pathlib import Path

from scripts.audit_zpd_fresh_holdout import blind_rows, exposure_user_tiers
from scripts.audit_zpd_history_support import digest_file

AUDIT_COMPLETE = '8cef5512f634cf4bd5f2ad196a82401dfc263a8d9fab992b3daf2b796de96593'
SALT = 'zpd-fresh-holdout-20260917-v1'
THRESHOLDS = (.50, .65)


def split_for_user(user):
    value = int(hashlib.sha256(f'{SALT}:{user}'.encode()).hexdigest(), 16) / 2**256
    return 'train' if value < THRESHOLDS[0] else 'valid' if value < THRESHOLDS[1] else 'eval'


def stage(audit_root, original, output, expected_complete=AUDIT_COMPLETE):
    if output.exists():
        raise ValueError('output already exists')
    complete = (audit_root / 'COMPLETE').read_text().strip()
    if complete != expected_complete or digest_file(audit_root / 'report.json') != complete:
        raise ValueError('stage A report is not the frozen v2 result')
    report = json.loads((audit_root / 'report.json').read_text())
    roster = sorted(p for p, s in report['per_problem'].items() if s['dataset'] == 'AtCoder')
    exposed = sorted(set().union(*map(set, report['exposure_sources'].values())))
    tiers = exposure_user_tiers(original, exposed, set(report['exposure_sources']['history_gate_roster']))
    excluded, gate_any = tiers['history_gate_test_split'], tiers['history_gate_any']
    (output / 'metadata').mkdir(parents=True)
    ub_users = {s: set() for s in ('train', 'valid', 'eval')}
    ub_rows, kept_rows = defaultdict(int), defaultdict(int)
    for problem in roster:
        (output / 'roster' / problem).mkdir(parents=True)
        source = original / 'metadata' / f'{problem}.csv'
        with source.open(encoding='utf-8', newline='') as src, \
                (output / 'metadata' / f'{problem}.csv').open('x', encoding='utf-8', newline='') as dst:
            reader, writer = csv.reader(src), csv.writer(dst, lineterminator='\n')
            header = next(reader)
            writer.writerow(header)
            user_index = header.index('user_id')
            for raw in reader:
                user = raw[user_index]
                if user not in excluded and split_for_user(user) != 'eval':
                    writer.writerow(raw)
                    kept_rows[split_for_user(user)] += 1
        groups = defaultdict(list)
        for row in blind_rows(source):
            if row['user_id'] not in excluded:
                groups[row['user_id']].append(row)
        for user, group in groups.items():
            first = min(int(r['date']) for r in group)
            count = sum(r['language'] == 'Python' and int(r['date']) > first for r in group)
            if count:
                ub_users[split_for_user(user)].add(user)
                ub_rows[split_for_user(user)] += count
    eval_users = sorted(ub_users['eval'])
    partition = {
        'protocol': 'analysis_protocols/zpd-fresh-holdout-stage-b-20260917.md',
        'salt': SALT, 'thresholds': list(THRESHOLDS),
        'excluded_rule': 'v1 history-gate test split users (SHA256(v1 salt:user)/2**256 >= .85 over gate metadata)',
        'excluded_user_count': len(excluded), 'roster': roster, 'audit_complete': complete,
        'structural_upper_bound_users': {s: len(v) for s, v in ub_users.items()},
        'structural_upper_bound_rows': dict(ub_rows), 'staged_metadata_rows': dict(kept_rows),
        'eval_structural_users': eval_users,
        'eval_structural_users_sha256': hashlib.sha256('\n'.join(eval_users).encode()).hexdigest(),
        'eval_sensitivity_users_outside_all_gate_users': sum(u not in gate_any for u in eval_users),
        'dev_user_splits': {u: split_for_user(u) for s in ('train', 'valid') for u in sorted(ub_users[s])},
        'eval_verdicts_opened': False,
        'staged_metadata_sha256': {p: digest_file(output / 'metadata' / f'{p}.csv') for p in roster},
        'script_sha256': digest_file(Path(__file__)),
    }
    (output / 'partition.json').write_text(json.dumps(partition, indent=1, sort_keys=True) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'partition.json') + '\n')
    return partition


def build(staging, original, output):
    import scripts.build_zpd_original_prefixes as builder
    if digest_file(staging / 'partition.json') != (staging / 'COMPLETE').read_text().strip():
        raise ValueError('staging incomplete or modified')
    partition = json.loads((staging / 'partition.json').read_text())
    for problem, expected in partition['staged_metadata_sha256'].items():
        if digest_file(staging / 'metadata' / f'{problem}.csv') != expected:
            raise ValueError('staged metadata changed')

    def dev_split(user):
        split = split_for_user(user)
        if split not in ('train', 'valid'):
            raise ValueError('non-development user reached the builder')
        return split

    builder.split_for_user, builder.SALT = dev_split, SALT
    manifest = builder.build(staging / 'metadata', original / 'data', staging / 'roster', output)
    manifest['split'] = {'unit': 'user_id across problems', 'salt': SALT,
                         'algorithm': 'SHA256(salt:user_id)/2**256; train < .50, valid < .65, eval otherwise (not built)',
                         'excluded': partition['excluded_rule'], 'users': manifest['split']['users'],
                         'staging_partition_sha256': digest_file(staging / 'partition.json'),
                         'wrapper_script_sha256': digest_file(Path(__file__))}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['stage', 'build'])
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--staging', type=Path)
    args = parser.parse_args()
    if args.phase == 'stage':
        result = stage(args.audit, args.original, args.output)
        print(json.dumps({k: result[k] for k in ('excluded_user_count', 'structural_upper_bound_users',
              'structural_upper_bound_rows', 'staged_metadata_rows',
              'eval_sensitivity_users_outside_all_gate_users')}, indent=1))
    else:
        result = build(args.staging, args.original, args.output)
        print(json.dumps({'counts': result['counts'], 'split': result['split']}, indent=1))
