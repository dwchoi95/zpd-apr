"""Additive, no-refit diagnosis of sealed train-only history-action predictions.

Every reported contribution uses the ORIGINAL global user-equal masked NLL
weight. A subgroup's contribution is not its re-normalized conditional NLL.
No target is dropped, no new outcome is collected, and no gate is altered.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

import numpy as np

from scripts.audit_zpd_history_action_cv import read, rows, sha, verify_seals, write

ARMS = ('C0', 'Cn', 'H', 'U', 'HS', 'L')
CONTROLS = ('C0', 'Cn', 'U', 'HS', 'L')
CLIP = 1e-12
ROOT = Path(__file__).resolve().parents[1]


def order_stratum(row):
    if row['hs_prior_length_one']:
        return 'one_prior'
    if row['hs_permutation_identity']:
        return 'multiple_prior_identity_permutation'
    if row['hs_hashed_features_equal']:
        return 'nonidentity_permutation_equal_hashed_features'
    return 'nonidentity_permutation_changed_hashed_features'


def diagnose_records(records, events, prior_counts=None):
    """Pure decomposition; disjoint strata and events each sum to primary loss.

    For evaluable prefix i of user u and available event j, w_ij equals
    1/(number of evaluable users * evaluable prefixes of u * available events i).
    All-masked rows have zero contribution but remain explicit coverage records.
    """
    if not records or not events or len(set(events)) != len(events):
        raise ValueError('nonempty unique events and records required')
    ids = [r['example_id'] for r in records]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate prediction example')
    if prior_counts is not None and not set(ids).issubset(prior_counts):
        raise ValueError('missing observed prior count')
    users = [r['user_id'] for r in records]
    for row in records:
        if (len(row['mask']) != len(events) or any(type(v) is not bool for v in row['mask'])
                or len(row['values']) != len(events)
                or any(type(v) not in (int, float) or v not in (0, 1) for v in row['values'])
                or set(row['probabilities']) != set(ARMS)):
            raise ValueError('invalid events, masks or arms')
        if row['target_status'] not in ('available', 'unavailable'):
            raise ValueError('unknown target status')
        if (row['target_status'] == 'available') != any(row['mask']):
            raise ValueError('target status and event availability disagree')
        for key in ('hs_prior_length_one', 'hs_permutation_identity', 'hs_hashed_features_equal',
                    'current_seen_in_fold_training', 'within_held_cross_user_distinct_history_collision'):
            if type(row[key]) is not bool:
                raise ValueError('invalid stratum flag')
        if row['hs_prior_length_one'] and not row['hs_permutation_identity']:
            raise ValueError('one-prior permutation must be identity')
        if row['hs_permutation_identity'] and not row['hs_hashed_features_equal']:
            raise ValueError('identity permutation must have equal features')
        if prior_counts is not None:
            n = prior_counts[row['example_id']]
            if type(n) is not int or n < 1 or (n == 1) != row['hs_prior_length_one']:
                raise ValueError('prior count and flag disagree')
    masks = np.asarray([r['mask'] for r in records], dtype=bool)
    y = np.asarray([r['values'] for r in records], dtype=float)
    m = masks.sum(axis=1)
    user_counts = Counter(u for u, count in zip(users, m) if count)
    n_users = len(user_counts)
    if not n_users:
        raise ValueError('no evaluable users; primary loss is undefined')
    prefix_weight = np.array([1/(n_users*user_counts[u]) if count else 0.
                              for u, count in zip(users, m)])
    event_weight = masks * np.divide(prefix_weight, m, out=np.zeros(len(m)), where=m != 0)[:, None]
    contributions = {}
    for arm in ARMS:
        p = np.asarray([r['probabilities'][arm] for r in records], dtype=float)
        if p.shape != y.shape or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
            raise ValueError('invalid saved probability')
        p = np.clip(p, CLIP, 1-CLIP)
        contributions[arm] = (-y*np.log(p)-(1-y)*np.log1p(-p))*event_weight

    def summarize(selected):
        indices = np.flatnonzero(selected)
        arm_losses = {a: float(contributions[a][selected].sum()) for a in ARMS}
        ev = {}
        for j, event in enumerate(events):
            eligible = selected & masks[:, j]
            event_losses = {a: float(contributions[a][selected, j].sum()) for a in ARMS}
            ev[event] = dict(prefixes=int(eligible.sum()),
                users=len({users[i] for i in np.flatnonzero(eligible)}),
                positives=int(y[eligible, j].sum()),
                global_event_weight=float(event_weight[selected, j].sum()),
                nll_contribution=event_losses,
                h_minus={a: event_losses['H']-event_losses[a] for a in CONTROLS})
        return dict(prefixes=len(indices), evaluable_prefixes=int(np.count_nonzero(m[selected])),
            all_masked_prefixes=int(np.count_nonzero(m[selected] == 0)),
            users=len({users[i] for i in indices}),
            evaluable_users=len({users[i] for i in indices if m[i]}),
            global_prefix_weight=float(prefix_weight[selected].sum()),
            nll_contribution=arm_losses,
            h_minus={a: arm_losses['H']-arm_losses[a] for a in CONTROLS}, events=ev)

    partitions = {
        'order_status': [order_stratum(r) for r in records],
        'successor_language_family': [('unavailable' if r['target_status'] != 'available' else
            'Python' if r['next_language'] == 'Python' else 'nonPython') for r in records],
        'successor_language': [(r['next_language'] if r['target_status'] == 'available' else 'unavailable') for r in records],
        'current_source_overlap': ['seen_in_fold_training' if r['current_seen_in_fold_training'] else 'not_seen_in_fold_training' for r in records],
        'same_current_distinct_history': ['collision' if r['within_held_cross_user_distinct_history_collision'] else 'no_collision' for r in records],
        'fold': [str(r['fold']) for r in records],
        'available_event_count': [str(v) for v in m],
        'mask_pattern': [''.join('1' if v else '0' for v in row) for row in masks],
    }
    if prior_counts is not None:
        partitions['prior_count'] = [str(prior_counts[r['example_id']]) for r in records]
        partitions['prior_count_bucket'] = [str(min(5, prior_counts[r['example_id']]))+('+' if prior_counts[r['example_id']] >= 5 else '') for r in records]
    partitions['order_by_language'] = [a+'|'+b for a, b in zip(partitions['order_status'], partitions['successor_language_family'])]
    result = dict(kind='posthoc_additive_train_only_history_action_diagnosis_v1',
        formula='mask_ij / (N_evaluable_users * n_evaluable_prefixes_for_user * m_available_events_for_prefix)',
        probability_clip=CLIP, events=list(events),
        overall=summarize(np.ones(len(records), dtype=bool)),
        partitions={name: {value: summarize(np.array([x == value for x in labels]))
                          for value in sorted(set(labels))} for name, labels in partitions.items()},
        confirmatory=False, sampling_intervals_computed=False, new_outcomes_collected=False,
        limitations=['Descriptive decomposition of an already exposed development result; not causal attribution.',
            'Event masks are fixed. Non-Python endpoints have fewer available labels, not fabricated structural negatives.',
            'Subgroup losses retain original global weights; user counts in disjoint prefix groups may overlap.',
            'Saved model seals are checked; probability rescoring is bound to the separate independent audit.'])
    for groups in result['partitions'].values():
        for arm in ARMS:
            if not math.isclose(sum(g['nll_contribution'][arm] for g in groups.values()),
                                result['overall']['nll_contribution'][arm], abs_tol=1e-12):
                raise AssertionError('non-additive partition')
    return result


def verify_report(decomposition, report):
    for arm in ARMS:
        expected = report['results'][arm]
        actual = decomposition['overall']
        if not math.isclose(actual['nll_contribution'][arm], expected['user_equal_masked_nll'], abs_tol=1e-12, rel_tol=1e-12):
            raise ValueError('sealed primary loss differs: '+arm)
        for name in ('evaluable_prefixes', 'all_masked_prefixes', 'evaluable_users'):
            saved = expected['users'] if name == 'evaluable_users' else expected[name]
            if actual[name] != saved:
                raise ValueError('sealed loss coverage differs: '+name)


def model_inventory(run, events):
    """All 30 sealed model heads checked; norms are NOT feature-block effects."""
    result = []
    for fold in range(5):
        cohort = read(run/f'fold-{fold}/cohort.json')
        for arm in ARMS:
            model = read(run/f'fold-{fold}/{arm}.json')
            if (model['arm'] != arm or model['fold'] != fold or model['events'] != list(events)
                    or model['hash_dimension'] != 4096 or len(model['heads']) != len(events)
                    or model['train_example_ids'] != cohort['train_example_ids']):
                raise ValueError('model identity/coverage mismatch')
            for event, head in zip(events, model['heads']):
                if event != head['event']:
                    raise ValueError('model head event mismatch')
                item = dict(fold=fold, arm=arm, event=event, kind=head['kind'])
                if head['kind'] == 'linear_logistic':
                    c = np.asarray(head['coefficients'], dtype=float)
                    if c.shape != (4096,) or not np.isfinite(c).all() or not math.isfinite(head['intercept']):
                        raise ValueError('invalid coefficients')
                    item.update(coefficient_l2=float(np.linalg.norm(c)), intercept=head['intercept'])
                elif head['kind'] == 'laplace_constant':
                    p = head['probability']
                    if not math.isfinite(p) or not 0 < p < 1:
                        raise ValueError('invalid constant')
                    item['probability'] = p
                else:
                    raise ValueError('unknown model kind')
                result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=ROOT)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = args.project.resolve()
    run = (args.run or project/'outputs/zpd-history-action-20260923/run-v1').resolve()
    output = args.output.resolve()
    if output.exists() or output == run or run in output.parents:
        raise ValueError('new diagnostic output outside immutable run required')
    complete = verify_seals(run)
    manifest = read(run/'manifest.json')
    for relative, digest in manifest['source_sha256'].items():
        if sha(project/relative) != digest:
            raise ValueError('sealed source mismatch: '+relative)
    feature_path = project/'outputs/zpd-history-gate-20260915/prepared-inputs/features.jsonl'
    expected = [v for k, v in manifest['input_sha256'].items() if k.endswith('/prepared-inputs/features.jsonl')]
    if len(expected) != 1 or sha(feature_path) != expected[0]:
        raise ValueError('observed metadata hash mismatch')
    observed = [r for r in rows(feature_path) if r['split'] == 'train']
    prior_counts = {r['example_id']: len(r['history']) for r in observed}
    if len(prior_counts) != len(observed):
        raise ValueError('duplicate train observation')
    predictions = []
    for fold in range(5):
        cell = rows(run/f'fold-{fold}/predictions.jsonl')
        held = read(run/f'fold-{fold}/cohort.json')['held_example_ids']
        if [r['example_id'] for r in cell] != held or any(r['fold'] != fold for r in cell):
            raise ValueError('prediction/cohort join mismatch')
        predictions.extend(cell)
    events = manifest['configuration']['events']
    report = diagnose_records(predictions, events, prior_counts)
    sealed_report = read(run/'report.json')
    verify_report(report, sealed_report)
    report['sealed_decision_unchanged'] = sealed_report['decision']
    report['models'] = model_inventory(run, events)
    report['model_norm_note'] = 'All feature blocks share hash coordinates: coefficient norms do not identify current/history block effects.'
    report['input_complete_sha256'] = sha(run/'COMPLETE.json')
    report['input_report_sha256'] = sha(run/'report.json')
    output.mkdir(parents=True)
    write(output/'report.json', report)
    write(output/'manifest.json', dict(kind=report['kind'], input_run=str(run),
        input_complete_sha256=sha(run/'COMPLETE.json'), input_files_sha256=complete['files_sha256'],
        observed_metadata_sha256=sha(feature_path),
        source_sha256={str(Path(__file__).resolve().relative_to(project)): sha(__file__),
            'scripts/audit_zpd_history_action_cv.py': sha(project/'scripts/audit_zpd_history_action_cv.py')},
        no_fit=True, no_new_outcomes=True, gate_unchanged=True))
    write(output/'COMPLETE.json', dict(status='complete',
        files_sha256={name: sha(output/name) for name in ('report.json', 'manifest.json')},
        input_complete_sha256=sha(run/'COMPLETE.json')))
    print(json.dumps(dict(output=str(output), h_minus=report['overall']['h_minus'],
                          input_complete_sha256=report['input_complete_sha256']), sort_keys=True))


if __name__ == '__main__':
    main()
