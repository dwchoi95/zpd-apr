"""Fixed post-verification C1 diagnosis; never refit or change an outcome gate."""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

from scripts.supervise_zpd_history_action import read, sha, verify_marker, write

ARMS = ('C0', 'Cn', 'H', 'U', 'HS', 'L')
CONTROLS = ('Cn', 'U', 'HS', 'L')
FLAGS = ('current_seen_in_fold_training',
         'within_held_cross_user_distinct_history_collision',
         'hs_prior_length_one', 'hs_permutation_identity', 'hs_hashed_features_equal')


def losses(row, events):
    values, masks = row['values'], row['mask']
    if len(values) != len(events) or len(masks) != len(events):
        raise ValueError('fixed event shape required')
    available = [i for i, mask in enumerate(masks) if mask]
    if not available:
        return None
    result = {}
    for arm in ARMS:
        probabilities = row['probabilities'][arm]
        if len(probabilities) != len(events):
            raise ValueError('fixed probability shape required')
        event_losses = {}
        for i in available:
            p, y = probabilities[i], values[i]
            if not math.isfinite(p) or not 0 <= p <= 1 or y not in (0, 1):
                raise ValueError('invalid binary probability/label')
            p = min(1 - 1e-12, max(1e-12, p))
            event_losses[events[i]] = -(y * math.log(p) + (1 - y) * math.log1p(-p))
        result[arm] = {'prefix_loss': sum(event_losses.values()) / len(event_losses),
                       'event_losses': event_losses}
    return result


def summarize(records, events):
    by_user = {arm: defaultdict(list) for arm in ARMS}
    event_user = {arm: {event: defaultdict(list) for event in events} for arm in ARMS}
    positive = dict.fromkeys(events, 0)
    support = dict.fromkeys(events, 0)
    all_masked = 0
    for row in records:
        result = losses(row, events)
        if result is None:
            all_masked += 1
            continue
        for i, name in enumerate(events):
            if row['mask'][i]:
                support[name] += 1
                positive[name] += int(row['values'][i])
        for arm, cell in result.items():
            by_user[arm][row['user_id']].append(cell['prefix_loss'])
            for event, value in cell['event_losses'].items():
                event_user[arm][event][row['user_id']].append(value)

    def user_mean(mapping):
        return (sum(sum(v) / len(v) for v in mapping.values()) / len(mapping)
                if mapping else None)

    aggregate = {arm: user_mean(by_user[arm]) for arm in ARMS}
    event_results = {}
    for name in events:
        values = {arm: user_mean(event_user[arm][name]) for arm in ARMS}
        event_results[name] = {'prefixes': support[name], 'positive_prefixes': positive[name],
            'users': len(event_user['H'][name]), 'loss': values,
            'H_minus_control': {c: values['H'] - values[c] if values['H'] is not None else None
                                for c in CONTROLS}}
    return {'prefixes': len(records), 'evaluable_prefixes': len(records) - all_masked,
            'all_masked_prefixes': all_masked, 'users': len(by_user['H']), 'loss': aggregate,
            'H_minus_control': {c: aggregate['H'] - aggregate[c] if aggregate['H'] is not None else None
                                for c in CONTROLS}, 'events': event_results}


def route(decision):
    failed = {}
    for control in CONTROLS:
        check = decision['checks'][control]
        reasons = [key for key in ('aggregate_strictly_better', 'at_least_four_folds',
                                   'simultaneous_upper_below_zero') if not check[key]]
        if reasons:
            failed[control] = reasons
    if bool(decision['gate_passed']) != (not failed):
        raise ValueError('decision checks contradict gate')
    return {'action': 'freeze_and_audit_repair_integration' if not failed else
            'diagnose_failed_history_controls_before_next_hypothesis',
            'failed_checks': failed, 'user_reapproval_required_within_existing_scope': False,
            'new_protocol_and_code_audit_required': True,
            'automatic_model_promotion': False, 'hidden_test_access': False,
            'repair_improvement_established': False, 'educational_learning_established': False}


def diagnose(run, audit, output):
    run, audit, output = (Path(p).absolute() for p in (run, audit, output))
    if any(p.resolve() != p for p in (run, audit, output)):
        raise ValueError('canonical paths without symlink aliases required')
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(audit):
        raise ValueError('new separate diagnosis directory required')
    run_seal = verify_marker(run, required_files=('report.json',
        *(f'fold-{fold}/predictions.jsonl' for fold in range(5))))
    audit_seal = verify_marker(audit, required_files=('report.json',))
    audit_report = read(audit / 'report.json')
    if (audit_report.get('verified') is not True or
            audit_report.get('experiment_complete_sha256') != run_seal['complete_sha256']):
        raise ValueError('independent audit must verify this exact completed experiment')
    result = read(run / 'report.json')
    records = []
    for fold in range(5):
        with (run / f'fold-{fold}/predictions.jsonl').open(encoding='utf-8') as stream:
            records.extend(json.loads(line) for line in stream if line.strip())
    if len({r['example_id'] for r in records}) != len(records):
        raise ValueError('duplicate OOF prediction')
    events = result['events']
    overall = summarize(records, events)
    for arm in ARMS:
        expected = result['results'][arm]['user_equal_masked_nll']
        actual = overall['loss'][arm]
        if actual is None and expected is None:
            continue
        if actual is None or expected is None or not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError('independently recomputed aggregate loss differs')
    strata = {}
    for field in FLAGS:
        for value in (False, True):
            strata[f'{field}={str(value).lower()}'] = summarize(
                [r for r in records if r[field] is value], events)
    for language in ('Python', 'other_language', 'unavailable'):
        subset = [r for r in records if (
            'unavailable' if r['target_status'] != 'available' else
            'Python' if r['next_language'] == 'Python' else 'other_language') == language]
        strata['target_language=' + language] = summarize(subset, events)
    report = {'kind': 'fixed_postverification_history_action_diagnosis',
        'verified_experiment_complete_sha256': run_seal['complete_sha256'],
        'independent_audit_complete_sha256': audit_seal['complete_sha256'],
        'source_population': result['source_population'], 'overall': overall,
        'fixed_strata': strata, 'frozen_gate': result['decision'],
        'next_action': route(result['decision']),
        'interpretation': 'Developmental observed-action prediction only. Strata are diagnostic, not replacement gates.',
        'no_new_fitting_or_outcomes': True}
    if (verify_marker(run)['complete_sha256'] != run_seal['complete_sha256'] or
            verify_marker(audit)['complete_sha256'] != audit_seal['complete_sha256']):
        raise ValueError('input completion changed during diagnosis')
    output.mkdir(parents=True)
    write(output / 'report.json', report)
    lines = ['# C1 automatic completion report', '',
        f"- Full training population: {result['source_population']:,} prefixes.",
        f"- Donor-supported OOF predictions: {len(records):,}; evaluable users: {overall['users']:,}.",
        f"- Fixed advancement gate: {'PASS' if result['decision']['gate_passed'] else 'FAIL'}.",
        '- No repair improvement, learning-effect claim, model replacement or hidden-test opening.', '',
        '| Arm | User-equal masked NLL |', '| --- | ---: |']
    for arm in ARMS:
        value = overall['loss'][arm]
        lines.append(f'| {arm} | {value:.8f} |' if value is not None else f'| {arm} | unevaluable |')
    lines.extend(['', '## Automatically routed next work', '', report['next_action']['action'], '',
                  'Failure checks: ' + json.dumps(report['next_action']['failed_checks'], sort_keys=True), '',
                  'The agent may implement the next in-scope protocol without another user approval; ',
                  'this script never invents a new hypothesis or tunes against exposed outcomes.', ''])
    with (output / 'report.md').open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines))
    write(output / 'COMPLETE.json', {'status': 'complete', 'files_sha256': {
        name: sha(output / name) for name in ('report.json', 'report.md')},
        'experiment_complete_sha256': run_seal['complete_sha256']})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    return diagnose(args.run, args.audit, args.output)


if __name__ == '__main__':
    main()
