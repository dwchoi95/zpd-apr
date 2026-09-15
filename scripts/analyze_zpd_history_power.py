"""Exploratory TRAIN OOF strata; never a confirmatory gate or test reader."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import mean

from scripts.audit_zpd_history_support import digest_file, rows


def analyze(power_root, input_root, output):
    if output.exists() or any(output.resolve().is_relative_to(p.resolve()) for p in (power_root, input_root)):
        raise ValueError('new output outside inputs required')
    if digest_file(power_root / 'power.json') != (power_root / 'COMPLETE').read_text().strip():
        raise ValueError('power incomplete')
    manifest = json.loads((input_root / 'manifest.json').read_text())
    meta = json.loads((power_root / 'metadata.json').read_text())
    if digest_file(input_root / 'manifest.json') != meta['input_manifest_sha256']:
        raise ValueError('power/input mismatch')
    for name in ('features.jsonl', 'labels-train.jsonl'):
        if digest_file(input_root / name) != manifest['file_sha256'][name]:
            raise ValueError('input hash mismatch')
    features = {r['example_id']: r for r in rows(input_root / 'features.jsonl') if r['split'] == 'train'}
    labels = {r['example_id']: r['next_label'] for r in rows(input_root / 'labels-train.jsonl')}
    result = json.loads((power_root / 'power.json').read_text())
    if result.get('test_opened') is not False:
        raise ValueError('unexpected test access')
    groups = defaultdict(list)
    seen = set()
    for row in result['oof_rows']:
        key = row['example_id']
        if (row['contrast'], key) in seen:
            raise ValueError('duplicate OOF row')
        seen.add((row['contrast'], key))
        f = features[key]
        if f['user_id'] != row['user_id']:
            raise ValueError('OOF identity mismatch')
        depth = len(f['history'])
        strata = {'all': 'all', 'current_verdict': f['matching_current_verdict'],
                  'history_depth': '1' if depth == 1 else '2-4' if depth <= 4 else '5+',
                  'next_label': labels[key], 'problem': f['problem_id']}
        for dimension, level in strata.items():
            groups[row['contrast'], dimension, level].append(row)
    if {k for c, k in seen if c == 'C_H'} != features.keys():
        raise ValueError('full OOF coverage mismatch')
    report = []
    for (contrast, dimension, level), members in sorted(groups.items()):
        users = defaultdict(list)
        for row in members:
            users[row['user_id']].append(row['difference'])
        report.append({'contrast': contrast, 'dimension': dimension, 'level': level,
                       'rows': len(members), 'users': len(users),
                       'user_equal_nll_improvement': mean(mean(v) for v in users.values())})
    output.mkdir(parents=True)
    payload = {'scope': 'post-power exploratory train OOF strata; no p-values, gate or subgroup selection',
               'strata_definition': 'current raw verdict; fixed depth 1/2-4/5+; next label; each problem',
               'warning': 'Next-label strata condition on outcomes; users can occur in multiple strata.',
               'power_sha256': digest_file(power_root / 'power.json'),
               'input_manifest_sha256': digest_file(input_root / 'manifest.json'),
               'script_sha256': digest_file(Path(__file__)), 'test_opened': False, 'strata': report}
    (output / 'report.json').write_text(json.dumps(payload, indent=2) + '\n')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('input', 'power', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.power, args.input, args.output)
    print(json.dumps([r for r in result['strata'] if r['dimension'] in ('all', 'current_verdict', 'history_depth')], indent=2))
