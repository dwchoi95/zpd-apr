"""Verdict-blind fresh-holdout audit, stage A.

Reads only identity/time/language columns of CodeNet metadata and source
directory listings. No verdict, resource, or source content enters the report.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

from scripts.audit_zpd_history_support import digest_file, rows

KEEP = ('submission_id', 'problem_id', 'user_id', 'date', 'language', 'filename_ext')
PROBLEM = re.compile(r'p\d{5}')


def blind_rows(path):
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream)
        header = next(reader)
        index = [header.index(name) for name in KEEP]
        for raw in reader:
            yield dict(zip(KEEP, (raw[i] for i in index)))


def exposure_registry(repo, original, remote_list):
    benchmark = original / 'derived' / 'benchmarks' / 'Project_CodeNet_Python800'
    local = {p.name for p in (repo / 'data').iterdir() if p.is_dir() and PROBLEM.fullmatch(p.name)}
    remote = set(remote_list.read_text().split())
    rosters = sorted((repo / 'data').glob('splits*/problem_split.jsonl'))
    gate_manifest = repo / 'outputs/zpd-history-gate-20260915/original-prefixes/manifest.json'
    sources = {
        'python800_benchmark': {p.name for p in benchmark.iterdir() if PROBLEM.fullmatch(p.name)},
        'local_data': local,
        'remote_data': remote,
        'split_rosters': {r['problem_id'] for p in rosters for r in rows(p)},
        'history_gate_roster': set(json.loads(gate_manifest.read_text())['problem_roster']),
    }
    hashes = {str(p.relative_to(repo)): digest_file(p) for p in rosters + [gate_manifest]}
    hashes['remote_problem_list'] = digest_file(remote_list)
    return sources, hashes, local == remote


def exposure_user_tiers(original, exposed_problems, gate_problems):
    broad, gate = set(), set()
    for problem in exposed_problems:
        for row in blind_rows(original / 'metadata' / f'{problem}.csv'):
            broad.add(row['user_id'])
            if problem in gate_problems:
                gate.add(row['user_id'])
    salt = 'zpd-history-gate-20260915-v1'
    test = {u for u in gate if int(hashlib.sha256(f'{salt}:{u}'.encode()).hexdigest(), 16) / 2**256 >= .85}
    return {'python800_any': broad, 'history_gate_any': gate, 'history_gate_test_split': test}


def summarize_problem(original, problem, tiers):
    groups = defaultdict(list)
    for row in blind_rows(original / 'metadata' / f'{problem}.csv'):
        groups[row['user_id']].append(row)
    listings = {}
    stats = defaultdict(int)
    users = {name: set() for name in tiers}
    for user, group in groups.items():
        dates = [int(r['date']) for r in group]
        first = min(dates)
        stats['rows'] += len(group)
        for row, date in zip(group, dates):
            if row['language'] != 'Python':
                continue
            stats['python_rows'] += 1
            if date <= first:
                continue
            stats['structural_prefix_upper_bound'] += 1
            for name, exposed in tiers.items():
                if user not in exposed:
                    users[name].add(user)
                    stats[f'upper_bound_outside_{name}'] += 1
            if dates.count(date) > 1:
                stats['tie_rows'] += 1
            folder = original / 'data' / problem / row['language']
            if folder not in listings:
                listings[folder] = {p.name for p in folder.iterdir()} if folder.is_dir() else set()
            if f"{row['submission_id']}.{row['filename_ext']}" in listings[folder]:
                stats['source_available'] += 1
    stats['user_problem_groups'] = len(groups)
    return dict(stats), users


def audit(repo, original, remote_list, output):
    if output.exists():
        raise ValueError('output already exists')
    if not output.resolve().is_relative_to(repo.resolve()):
        raise ValueError('output must remain in project')
    sources, input_hashes, local_equals_remote = exposure_registry(repo, original, remote_list)
    exposed = set().union(*sources.values())
    metadata_ids = {p.stem for p in (original / 'metadata').glob('p?????.csv') if PROBLEM.fullmatch(p.stem)}
    python_dirs = {p for p in metadata_ids if (original / 'data' / p / 'Python').is_dir()}
    candidates = sorted(python_dirs - exposed)
    tiers = exposure_user_tiers(original, sorted(exposed & metadata_ids), sources['history_gate_roster'])
    datasets = {r['id']: r['dataset'] for r in csv.DictReader((original / 'metadata/problem_list.csv').open())}
    per_problem, totals = {}, defaultdict(int)
    all_users = {name: set() for name in tiers}
    for problem in candidates:
        stats, users = summarize_problem(original, problem, tiers)
        stats['dataset'] = datasets.get(problem)
        per_problem[problem] = stats
        for key, value in stats.items():
            if isinstance(value, int):
                totals[key] += value
        for kind in all_users:
            all_users[kind] |= users[kind]
    for name, found in all_users.items():
        totals[f'prefix_users_outside_{name}'] = len(found)
    report = {
        'scope': 'verdict-blind stage A audit; not fresh-holdout certification',
        'kept_metadata_columns': list(KEEP),
        'verdicts_opened': False, 'source_contents_opened': False,
        'exposure_sources': {k: sorted(v) for k, v in sources.items()},
        'exposure_counts': {k: len(v) for k, v in sources.items()} | {'union': len(exposed)},
        'local_equals_remote_data': local_equals_remote,
        'exposure_user_tier_counts': {k: len(v) for k, v in tiers.items()},
        'exposure_user_tiers': {
            'python800_any': 'user_id in any language row of any exposed problem',
            'history_gate_any': 'user_id in any row of the 23 v1 history-gate problems',
            'history_gate_test_split': 'history_gate_any users with SHA256(v1 salt:user)/2**256 >= .85'},
        'population_counts': {'metadata_problems': len(metadata_ids),
                              'python_directory_problems': len(python_dirs),
                              'candidate_problems': len(candidates)},
        'totals': dict(sorted(totals.items())),
        'by_dataset': {},
        'per_problem': per_problem,
        'input_sha256': input_hashes,
        'candidate_metadata_sha256': {p: digest_file(original / 'metadata' / f'{p}.csv') for p in candidates},
        'script_sha256': digest_file(Path(__file__)),
        'original_root': str(original),
        'fresh_holdout_certified': False,
    }
    for stats in per_problem.values():
        bucket = report['by_dataset'].setdefault(stats['dataset'], defaultdict(int))
        bucket['problems'] += 1
        for key, value in stats.items():
            if isinstance(value, int) and key.startswith(('structural', 'upper_bound', 'source')):
                bucket[key] += value
    output.mkdir(parents=True)
    (output / 'report.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    (output / 'COMPLETE').write_text(digest_file(output / 'report.json') + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'original', 'remote_problem_list', 'output'):
        parser.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.repo, args.original, args.remote_problem_list, args.output)
    print(json.dumps({k: result[k] for k in ('exposure_counts', 'exposure_user_tier_counts',
                                             'population_counts', 'totals', 'by_dataset')}, indent=1))
