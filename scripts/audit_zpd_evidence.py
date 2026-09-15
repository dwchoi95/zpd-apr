"""Full-population, cache-linked exploratory audit; never rewrites v5 inputs."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from scripts.diagnose_zpd_objective import read_rows, target_summary, delta_class
from src.repair.evidence_order import ExecutionEvidence, progress_improvement, severity


def jsonl(path):
    with path.open(encoding='utf-8') as stream:
        yield from (json.loads(line) for line in stream if line.strip())


def verify_cache_record(row, keys):
    """Verify observed coverage, not execution stability or historical code identity."""
    errors = []
    if 'cache_error' in row:
        return ['cache_error']
    outcomes = row.get('tc_outcomes', {})
    if not keys or set(outcomes) != set(keys):
        errors.append('testcase_universe_mismatch')
    if (type(row.get('testcase_count')) is not int
            or row.get('testcase_count') != len(outcomes)):
        errors.append('testcase_count_mismatch')
    if row.get('execution_verdict') not in {'AC', 'WA', 'TLE', 'MLE', 'RE', 'CE'}:
        errors.append('invalid_aggregate_verdict')
    if any(v not in {'AC', 'WA', 'TLE', 'MLE', 'RE', 'CE'} for v in outcomes.values()):
        errors.append('unknown_case_verdict')
    passed = sorted(k for k, v in outcomes.items() if v == 'AC')
    if outcomes and (row.get('execution_verdict') == 'AC') != (len(passed) == len(outcomes)):
        errors.append('aggregate_acceptance_mismatch')
    if sorted(row.get('passed_testcases', [])) != passed:
        errors.append('passed_keys_mismatch')
    stored = row.get('pass_rate')
    if (isinstance(stored, bool) or not isinstance(stored, (float, int))
            or not math.isfinite(stored) or not outcomes
            or not math.isclose(stored, len(passed) / len(outcomes), abs_tol=1e-12)):
        errors.append('pass_rate_mismatch')
    return errors


def relation_axes(before, after):
    a, b = before['tc_outcomes'], after['tc_outcomes']
    gained = sum(a[k] != 'AC' and b[k] == 'AC' for k in a)
    lost = sum(a[k] == 'AC' and b[k] != 'AC' for k in a)
    rank_before, rank_after = max(map(severity, a.values())), max(map(severity, b.values()))
    # Diagnostic counterfactual only: max severity, with same-rank MLE/TLE
    # canonicalized as TLE. This does NOT rewrite cached aggregate verdicts.
    by_rank = {0: 'AC', 1: 'WA', 2: 'TLE', 3: 'RE', 4: 'CE', 5: 'UNKNOWN'}
    legacy = progress_improvement(ExecutionEvidence(before['execution_verdict'], a),
                                  ExecutionEvidence(after['execution_verdict'], b))
    coherent = progress_improvement(ExecutionEvidence(by_rank[rank_before], a),
                                    ExecutionEvidence(by_rank[rank_after], b))
    return {
        'legacy_replay_relation': legacy,
        'coherent_severity_relation': coherent,
        'pass_delta': delta_class(before['pass_rate'], after['pass_rate']),
        'gained_passes': gained, 'lost_passes': lost,
        'pass_set_growth_without_losses': gained > 0 and lost == 0,
        'current_aggregate_rank_conflict': rank_before != severity(before['execution_verdict']),
        'target_aggregate_rank_conflict': rank_after != severity(after['execution_verdict']),
    }


def run(input_root, output):
    if output.resolve().is_relative_to(input_root.resolve()):
        raise ValueError('output cannot overwrite input files')
    digests = {}

    def record(path):
        digests[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return path

    universe = {}
    for path in sorted((input_root / 'testcases').glob('p*/testcases.jsonl')):
        rows = list(jsonl(record(path)))
        keys = [r['case_id'] for r in rows]
        if len(keys) != len(set(keys)) or not keys:
            raise ValueError(f'duplicate or empty testcase universe: {path}')
        universe[path.parent.name] = keys
    cache, errors = {}, {}
    for row in jsonl(record(input_root / 'all-original-submissions.jsonl')):
        key = (row['problem_id'], row['submission_id'])
        if key in cache:
            raise ValueError(f'duplicate cache key: {key}')
        cache[key] = row
        errors[key] = verify_cache_record(row, universe.get(key[0], []))
    summary = input_root / 'all-original-submissions.summary.json'
    result = {'scope': 'full canonical training/validation audit, exploratory',
              'cache_summary': json.loads(record(summary).read_text()),
              'cache_rows': len(cache), 'testcase_problems': len(universe),
              'cache_invalid_rows': sum(bool(v) for v in errors.values()),
              'cache_error_counts': dict(Counter(e for values in errors.values() for e in values)),
              'datasets': {},
              'limitations': ['Current testcase files verify key coverage, not original execution provenance.',
                              'Legacy cache lacks source/test hashes and per-record runtime provenance.',
                              'Order counterfactual uses max severity and same-rank MLE/TLE canonicalization; it is not a corrected v5 result.',
                              'No educational or causal effects are measured.']}
    for split in ('train', 'valid'):
        for policy in ('progress', 'strict', 'answer'):
            path = input_root / 'canonical-datasets' / f'{split}-{policy}.jsonl'
            rows = read_rows(record(path))
            native = target_summary(rows)
            linked, count, cross, transitions = {}, Counter(), Counter(), Counter()
            unique_targets = {}
            for example_id, row in rows.items():
                current = row['history'][-1]
                keys = [(row['problem_id'], current['submission_id']),
                        (row['problem_id'], row['target_submission_id'])]
                if any(k not in cache for k in keys):
                    count['missing_cache_pair'] += 1
                    continue
                if any(errors[k] for k in keys):
                    count['invalid_cache_pair'] += 1
                    continue
                before, after = (cache[k] for k in keys)
                count['current_historical_cache_verdict_disagrees'] += (
                    before.get('source_verdict') != current['verdict'])
                count['target_historical_cache_verdict_disagrees'] += (
                    after.get('source_verdict') != row['target_verdict'])
                if before['tc_outcomes'].keys() != after['tc_outcomes'].keys():
                    raise ValueError('verified pair universes differ')
                for prefix, evidence in (('current', before), ('target', after)):
                    if prefix + '_tc_outcomes' in row:
                        if row[prefix + '_tc_outcomes'] != evidence['tc_outcomes']:
                            count[prefix + '_embedded_cache_disagrees'] += 1
                linked[example_id] = {**row, 'current_execution_verdict': before['execution_verdict'],
                                     'target_execution_verdict': after['execution_verdict'],
                                     'current_pass_rate': before['pass_rate'], 'target_pass_rate': after['pass_rate'],
                                     'current_tc_outcomes': before['tc_outcomes'],
                                     'target_tc_outcomes': after['tc_outcomes']}
                axes = relation_axes(before, after)
                count['verified_observed_pair'] += 1
                count['replay_current_all_pass'] += before['pass_rate'] == 1
                for name in ('pass_set_growth_without_losses', 'current_aggregate_rank_conflict',
                             'target_aggregate_rank_conflict'):
                    count[name] += axes[name]
                count['relation_changes_under_coherent_rank'] += (
                    axes['legacy_replay_relation'] != axes['coherent_severity_relation'])
                cross[f"legacy_relation={axes['legacy_replay_relation']};pass_delta={axes['pass_delta']}"] += 1
                transitions[f"{current['verdict']}->{row['target_verdict']}|{before['execution_verdict']}->{after['execution_verdict']}"] += 1
                unique_targets[keys[1]] = after
            result['datasets'][f'{split}-{policy}'] = {
                'native_fields': native, 'cache_linked': target_summary(linked),
                'integrity': dict(count), 'relation_pass_cross_table': dict(cross),
                'historical_replay_transitions': dict(transitions),
                'unique_targets': len(unique_targets),
                'unique_target_replay_verdicts': dict(Counter(r['execution_verdict'] for r in unique_targets.values())),
            }
    record(Path(__file__))
    record(Path('scripts/diagnose_zpd_objective.py'))
    record(Path('src/repair/evidence_order.py'))
    result['input_sha256'] = digests
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.input.resolve()):
        raise ValueError('output cannot overwrite input files')
    run(args.input, args.output)
    print(args.output)
