"""Train/validation-only, label-free representation diagnosis; no fitting."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from scripts.audit_zpd_history_support import digest_file, rows
from scripts.zpd_history_predictor import LABELS


def describe(row, code_hashes):
    if row['split'] not in ('train', 'valid'):
        raise ValueError('diagnosis rejects test rows')
    history = row['history']
    if not history or row['current_verdict'] not in LABELS or row['current_verdict'] == 'AC':
        raise ValueError('invalid current or history')
    times = [h['timestamp'] for h in history] + [row['timestamp']]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError('non-strict history chronology')
    if any(h['verdict'] not in LABELS for h in history):
        raise ValueError('noncanonical history verdict')
    codes = [code_hashes[h['code_id']] for h in history]
    current = code_hashes[row['current_code_id']]
    trailing = 0
    for code in reversed(codes):
        if code != current:
            break
        trailing += 1
    homogeneous = len({h['verdict'] for h in history}) == 1
    eligible = len(history) >= 2 and len(set(codes)) >= 2 and homogeneous
    return {'example_id': row['example_id'], 'user_id': row['user_id'],
            'problem_id': row['problem_id'], 'split': row['split'],
            'history_depth': len(history), 'distinct_prior_exact_codes': len(set(codes)),
            'homogeneous_prior_verdict': homogeneous,
            'permutation_invariant_nontrivial_history': eligible,
            'last_code_changed_from_current': codes[-1] != current,
            'prior_current_code_repetitions': sum(code == current for code in codes),
            'trailing_current_code_repetitions': trailing}


def summarize(records):
    users = defaultdict(list)
    for r in records:
        users[r['user_id']].append(r)
    eligible = [r for r in records if r['permutation_invariant_nontrivial_history']]
    eligible_users = {r['user_id'] for r in eligible}
    def details(group):
        return {'rows': len(group), 'users': len({r['user_id'] for r in group}),
                'problems': len({r['problem_id'] for r in group}),
                'history_depth_counts': dict(sorted(Counter(str(r['history_depth']) for r in group).items(), key=lambda x:int(x[0]))),
                'last_code_changed_from_current_rows': sum(r['last_code_changed_from_current'] for r in group),
                'any_prior_current_code_repeat_rows': sum(r['prior_current_code_repetitions'] > 0 for r in group),
                'prior_current_code_repeat_count': sum(r['prior_current_code_repetitions'] for r in group),
                'trailing_current_code_repeat_count': sum(r['trailing_current_code_repetitions'] for r in group)}
    return {'all': details(records), 'invariant_nontrivial': details(eligible),
            'invariant_row_fraction': len(eligible)/len(records) if records else None,
            'users_with_any_invariant_row_fraction': len(eligible_users)/len(users) if users else None,
            'user_equal_invariant_row_fraction': sum(
                sum(r['permutation_invariant_nontrivial_history'] for r in rs)/len(rs)
                for rs in users.values())/len(users) if users else None,
            'history_depth_at_least_two_rows': sum(r['history_depth'] >= 2 for r in records),
            'distinct_prior_codes_at_least_two_rows': sum(r['distinct_prior_exact_codes'] >= 2 for r in records),
            'homogeneous_prior_verdict_rows': sum(r['homogeneous_prior_verdict'] for r in records)}


def run(input_root, output):
    if output.exists() or output.resolve().is_relative_to(input_root.resolve()):
        raise ValueError('new output directory outside inputs required')
    manifest = json.loads((input_root/'manifest.json').read_text())
    tracked = {str(p): digest_file(p) for p in [input_root/'manifest.json', Path(__file__),
        Path('scripts/zpd_history_predictor.py'), Path('scripts/audit_zpd_history_support.py')]}
    for name in ('features.jsonl', 'codes.jsonl'):
        digest = digest_file(input_root/name)
        if digest != manifest['file_sha256'][name]:
            raise ValueError('input hash mismatch: '+name)
        tracked[str(input_root/name)] = digest
    # Skip test rows before resolving their code IDs. No label file is opened.
    selected, wanted, seen, user_splits = [], set(), set(), {}
    for row in rows(input_root/'features.jsonl'):
        if row['split'] == 'test':
            continue
        if row['split'] not in ('train', 'valid') or row['example_id'] in seen:
            raise ValueError('invalid split or duplicate selected example')
        seen.add(row['example_id'])
        if user_splits.setdefault(row['user_id'], row['split']) != row['split']:
            raise ValueError('train/validation user leakage')
        selected.append(row)
        wanted.add(row['current_code_id'])
        wanted.update(h['code_id'] for h in row['history'])
    hashes = {}
    for code in rows(input_root/'codes.jsonl'):
        if code['code_id'] not in wanted:
            continue
        if code['code_id'] in hashes:
            raise ValueError('duplicate selected code identity')
        digest = hashlib.sha256(code['code'].encode('utf-8')).hexdigest()
        if digest != code['source_sha256']:
            raise ValueError('selected source hash mismatch')
        hashes[code['code_id']] = digest
    if hashes.keys() != wanted:
        raise ValueError('missing selected observed source')
    counts = Counter(r['split'] for r in selected)
    if any(counts[s] != manifest['counts'][s] for s in ('train', 'valid')):
        raise ValueError('train/validation coverage mismatch')
    records = [describe(r, hashes) for r in selected]
    report = {'scope': 'post-test, train/validation-only label-free representation diagnosis',
              'test_rows_analyzed': 0, 'label_files_opened': [], 'fits_performed': 0,
              'definition': 'depth >=2 AND >=2 distinct exact prior codes AND all prior nominal verdicts equal',
              'invariance': 'Permuting only past code assignments at fixed timestamps leaves mean code blocks and all nominal history blocks unchanged; current code, verdict, prefix count and first timestamp remain fixed, so C nuisance is unchanged. Floating summation can differ at roundoff level.',
              'limitation': 'Constructed feature invariance is not model-performance, causal failure, learning-effect or redesign efficacy evidence. Counts refer to observed eligible train/validation prefixes.',
              'input_source_sha256': tracked,
              'splits': {s:summarize([r for r in records if r['split']==s]) for s in ('train','valid')}}
    if any(digest_file(Path(p)) != h for p,h in tracked.items()):
        raise ValueError('source/input changed during diagnosis')
    output.mkdir(parents=True)
    with (output/'rows.jsonl').open('x') as stream:
        for row in records:
            stream.write(json.dumps(row)+'\n')
    report['output_sha256'] = {'rows.jsonl':digest_file(output/'rows.jsonl')}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'COMPLETE').write_text(digest_file(output/'report.json')+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('input','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.input,args.output),indent=2))
