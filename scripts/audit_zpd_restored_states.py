"""Validate the isolated prefix-state prototype on archived observed prefixes."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.build_zpd_legacy_prefix_inventory import rows
from src.repair.zpd_state import build_observed_prefix_state


def audit(root, output):
    if output.resolve().is_relative_to(root.resolve()):
        raise ValueError('state audit output must be outside input inventory')
    manifest = json.loads((root / 'manifest.json').read_text())
    if not (root / 'COMPLETE').exists():
        raise ValueError('inventory incomplete')
    # Never open labels/references: only explicitly observed code IDs are joined.
    files = [root / 'codes.jsonl', root / 'features.jsonl']
    for path in files:
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['output_sha256'][path.name]:
            raise ValueError('inventory hash mismatch')
    codes = {}
    for row in rows(files[0]):
        # CodeNet submission IDs are global; enforce instead of assuming.
        key = row['submission_id']
        if key in codes:
            raise ValueError('duplicate global code identity')
        if hashlib.sha256(row['code'].encode()).hexdigest() != row['code_sha256']:
            raise ValueError('code hash mismatch')
        codes[key] = row
    counts, unique = Counter(), set()
    for feature in rows(files[1]):
        if set(feature) != {'example_id', 'current_submission_id', 'observed_history'}:
            raise ValueError('unexpected feature fields')
        if feature['example_id'] in unique:
            raise ValueError('duplicate example ID')
        unique.add(feature['example_id'])
        prefix = []
        for item in feature['observed_history']:
            if set(item) != {'submission_id', 'timestamp', 'verdict', 'code_sha256'}:
                raise ValueError('unexpected observed item fields')
            code = codes[item['submission_id']]
            if code['code_sha256'] != item['code_sha256']:
                raise ValueError('observed code hash mismatch')
            prefix.append({k: item[k] for k in ('submission_id', 'timestamp', 'verdict')}
                          | {'code': code['code']})
        if prefix[-1]['submission_id'] != feature['current_submission_id']:
            raise ValueError('current not final observed item')
        state = build_observed_prefix_state(prefix)
        counts['prefixes'] += 1
        counts['prefixes_with_prior_history'] += bool(state['history']['observed_prior_submissions'])
        counts['prefixes_with_exact_current_code_seen_before'] += bool(state['current_vs_history']['prior_exact_code_matches'])
        counts['prefixes_with_prior_adjacent_exact_repeats'] += bool(state['history']['adjacent_exact_code_repeats'])
        counts['prefixes_with_repeated_prior_failed_verdict'] += bool(state['history']['adjacent_same_failed_verdict'])
        counts['prefixes_with_unknown_current_execution'] += state['current']['execution']['status'] == 'unknown'
        counts['prefixes_with_timestamp_ties'] += bool(state['audit']['timestamp_ties'])
    if counts['prefixes'] != manifest['counts']['prefixes']:
        raise ValueError('prefix coverage mismatch')
    result = {'task': 'state extraction feasibility, not prediction or learning evaluation',
              'counts': dict(counts), 'labels_opened': False,
              'original_completeness': manifest['original_completeness'],
              'eventual_ac_only': manifest['eventual_ac_only'], 'learning_effect': None,
              'inputs_and_source_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in [*files, root / 'manifest.json', Path(__file__), Path('src/repair/zpd_state.py')]}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.input, args.output)
    print(json.dumps(result['counts']))
