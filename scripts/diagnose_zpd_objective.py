"""Read-only exploratory v5 objective/failure audit; never modifies inputs."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from src.repair.evidence_order import ExecutionEvidence, progress_improvement, severity


def read_rows(path):
    with path.open(encoding='utf-8') as source:
        rows = [json.loads(line) for line in source if line.strip()]
    keyed = {row['example_id']: row for row in rows}
    if len(keyed) != len(rows):
        raise ValueError(f'duplicate IDs: {path}')
    return keyed


def rate(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('missing/non-numeric rate')
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('invalid rate')
    return value


def delta_class(before, after):
    return 'increase' if after > before else 'decrease' if after < before else 'tie'


def checked_outcomes(row, before_key, after_key, before_rate, after_rate):
    left, right = row.get(before_key), row.get(after_key)
    if not left or not right or left.keys() != right.keys():
        return None
    for outcomes, stored in ((left, before_rate), (right, after_rate)):
        if any(value not in {'AC', 'WA', 'TLE', 'MLE', 'RE', 'CE'} for value in outcomes.values()):
            raise ValueError('unknown testcase verdict')
        observed = sum(value == 'AC' for value in outcomes.values()) / len(outcomes)
        if not math.isclose(observed, rate(row[stored]), abs_tol=1e-12):
            raise ValueError('testcase/rate mismatch')
    return left, right


def target_summary(rows):
    counts, original, executed, transitions = Counter(), Counter(), Counter(), Counter()
    for row in rows.values():
        current = row['history'][-1]
        counts['examples'] += 1
        original[row['target_verdict']] += 1
        counts['historical_target_ac'] += severity(row['target_verdict']) == 0
        counts['exact_unchanged_target'] += current['code'] == row['target_code']
        counts['historical_order_improved'] += progress_improvement(
            ExecutionEvidence(current['verdict'], row.get('current_tc_outcomes', {})),
            ExecutionEvidence(row['target_verdict'], row.get('target_tc_outcomes', {})))
        evidence = checked_outcomes(row, 'current_tc_outcomes', 'target_tc_outcomes',
                                    'current_pass_rate', 'target_pass_rate')
        if evidence is None:
            counts['replay_unknown_or_incomparable'] += 1
            continue
        counts['replay_comparable'] += 1
        before, after = row['current_pass_rate'], row['target_pass_rate']
        counts['target_all_tests_pass'] += after == 1
        counts['target_zero_pass'] += after == 0
        counts['pass_rate_' + delta_class(before, after)] += 1
        executed[row['target_execution_verdict']] += 1
        transitions[f"{row['current_execution_verdict']}->{row['target_execution_verdict']}"] += 1
        counts['historical_replay_target_severity_disagrees'] += (
            severity(row['target_verdict']) != severity(row['target_execution_verdict']))
        counts['replay_order_improved'] += progress_improvement(
            ExecutionEvidence(row['current_execution_verdict'], evidence[0]),
            ExecutionEvidence(row['target_execution_verdict'], evidence[1]))
    return {'counts': dict(counts), 'historical_target_verdicts': dict(original),
            'replay_target_verdicts': dict(executed), 'replay_transitions': dict(transitions)}


def assert_paired(left, right):
    if left.keys() != right.keys():
        raise ValueError('paired ID coverage mismatch')
    for key in left:
        a, b = left[key], right[key]
        for field in ('problem_id', 'user_id'):
            if a[field] != b[field]:
                raise ValueError('paired identity mismatch')
        for field in ('submission_id', 'code'):
            if a['history'][-1][field] != b['history'][-1][field]:
                raise ValueError('paired current source mismatch')


def output_summary(rows, sources, *, controller=False):
    if rows.keys() != sources.keys():
        raise ValueError('evaluation ID coverage mismatch')
    counts, verdicts = Counter(), Counter()
    execution_disagreements = []
    baseline_disagreements = []
    for key, row in rows.items():
        source = sources[key]
        if row['problem_id'] != source['problem_id'] or row['user_id'] != source['user_id']:
            raise ValueError('evaluation identity mismatch')
        before, after = rate(row['buggy_pass_rate']), rate(row['fixed_pass_rate'])
        if not math.isclose(before, rate(source['current_pass_rate']), abs_tol=1e-12):
            baseline_disagreements.append({'example_id': key, 'source_rate': source['current_pass_rate'],
                                           'evaluation_rate': before})
        if before == 1:
            raise ValueError('expected non-AC source')
        if bool(row['repaired']) != (after == 1):
            raise ValueError('repair flag mismatch')
        counts['examples'] += 1
        if controller:
            counts['ac' if after == 1 else 'non_ac_' + delta_class(before, after)] += 1
            continue
        joined = {**row, 'current_tc_outcomes': source['current_tc_outcomes'],
                  'source_pass_rate': source['current_pass_rate']}
        if checked_outcomes(joined, 'current_tc_outcomes', 'fixed_tc_outcomes',
                            'source_pass_rate', 'fixed_pass_rate') is None:
            raise ValueError('incomplete member evidence')
        unchanged = row['generated_code'] == source['history'][-1]['code']
        if unchanged and after != before:
            execution_disagreements.append({'example_id': key, 'before': before, 'after': after,
                                            'buggy_verdict': row['buggy_verdict'],
                                            'fixed_verdict': row['fixed_verdict']})
            counts['unchanged_execution_disagreement'] += 1
            verdicts[row['fixed_verdict']] += 1
            continue
        label = ('ac' if after == 1 else 'unchanged_non_ac' if unchanged else
                 'changed_non_ac_' + delta_class(before, after))
        counts[label] += 1
        verdicts[row['fixed_verdict']] += 1
    return {'counts': dict(counts), 'fixed_verdicts': dict(verdicts),
            'unchanged_execution_disagreements': execution_disagreements,
            'source_evaluation_baseline_disagreements': baseline_disagreements,
            'delta_reference': 'recorded common evaluation baseline, not source-file replay'}


def run(root, output):
    inputs = {}

    def load(path):
        inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return read_rows(path)

    data = root / 'datasets/paired-target-control'
    evaluations = root / 'eval/paired-target-control-corrected'
    result = {'status': 'exploratory_phase_A', 'population': 'source-matched target-divergent Python pairs',
              'learning_effect': None, 'training': {}, 'evaluation': {}}
    for split in ('train', 'valid'):
        pairs = {name: load(data / f'{split}-{name}.jsonl') for name in ('progress', 'answer')}
        assert_paired(pairs['progress'], pairs['answer'])
        result['training'][split] = {name: target_summary(rows) for name, rows in pairs.items()}
    for split in ('seen', 'unseen'):
        sources = load(data / f'{split}-test.jsonl')
        methods, comparisons = {}, {}
        common_baseline = None
        for seed in (2027, 2028, 2029, 'controller'):
            members = {}
            for name in ('progress', 'answer'):
                stem = f'{name}3' if seed == 'controller' else f'{name}-{seed}'
                members[name] = load(evaluations / split / f'{stem}.evaluation.jsonl')
                baseline = {k: row['buggy_pass_rate'] for k, row in members[name].items()}
                if common_baseline is not None and baseline != common_baseline:
                    raise ValueError('baselines differ across evaluation conditions')
                common_baseline = baseline
                methods[stem] = output_summary(members[name], sources, controller=seed == 'controller')
            joint = Counter()
            for key in sources:
                p, a = (members[name][key]['fixed_pass_rate'] == 1 for name in ('progress', 'answer'))
                joint['both' if p and a else 'progress_only' if p else 'answer_only' if a else 'neither'] += 1
            comparisons[str(seed)] = {'counts': dict(joint), 'progress_minus_answer_rr_pp':
                                      100 * (joint['progress_only'] - joint['answer_only']) / len(sources)}
        result['evaluation'][split] = {'methods': methods, 'paired': comparisons}
    for path in (Path(__file__), Path('src/repair/evidence_order.py'),
                 Path('analysis_protocols/zpd-mechanism-diagnosis-20260915.md')):
        inputs[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    result['input_sha256'] = inputs
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.root.resolve()):
        raise ValueError('diagnostic output must be outside the preserved baseline')
    run(args.root, args.output)
    print(args.output)
