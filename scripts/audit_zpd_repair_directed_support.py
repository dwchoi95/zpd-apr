"""Source-only feasibility for directed local-edit history; no fit or outcomes.

Reuses the reviewed, fixed observed-source filename allowlist. Every bank and
candidate is retained. The CLI requires a clean source snapshot and a new output.
"""
from __future__ import annotations

import argparse
from collections import Counter
from importlib.metadata import version
from itertools import combinations
from pathlib import Path
import platform

import numpy as np

from scripts import audit_zpd_repair_feedback_support as observed
from scripts import zpd_repair_directed_history as directed

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'outputs/zpd-repair-directed-history-20260924'
ARMS = ('H', 'Jm', 'HS', 'U', 'L')
TOLERANCE = 1e-12
SOURCE_FILES = tuple(dict.fromkeys((*observed.SOURCE_FILES,
    'scripts/zpd_repair_directed_history.py',
    'scripts/audit_zpd_repair_directed_support.py',
    'scripts/supervise_zpd_history_action.py',
    'tests/test_zpd_repair_directed_history.py',
    'tests/test_zpd_repair_directed_support.py',
    'analysis_protocols/zpd-repair-directed-history-prospective-20260924.md')))
RUNTIME = {'python': '3.13.11', 'numpy': '2.5.2', 'scipy': '1.18.1', 'scikit-learn': '1.9.0'}


def runtime_versions():
    return dict(python=platform.python_version(), **{n: version(n) for n in ('numpy', 'scipy', 'scikit-learn')})


def geometry(matrices, old_matrix, old_effective_events, noop):
    """All-pair contrasts, not common shifts; no labels or optimization."""
    if type(matrices) is not dict or set(matrices) != set(ARMS):
        raise ValueError('all five directed arms required')
    n = len(matrices['H'])
    if type(noop) is not int or not 0 <= noop < n:
        raise ValueError('exact no-op index required')
    if (any(type(x) is not np.ndarray or x.shape != (n, 144) or not np.isfinite(x).all()
            for x in matrices.values()) or old_matrix.shape != (n, 1296)
            or old_effective_events.shape != (n, 18) or not np.isfinite(old_matrix).all()
            or not np.isfinite(old_effective_events).all()):
        raise ValueError('finite exact candidate matrices required')
    pairs = list(combinations(range(n), 2))
    variations = {arm: [float(np.max(np.abs(x[a] - x[b]))) for a, b in pairs]
                  for arm, x in matrices.items()}
    contrasts = {arm: [float(np.max(np.abs((matrices['H'][a] - matrices['H'][b])
                    - (matrices[arm][a] - matrices[arm][b])))) for a, b in pairs]
                 for arm in ARMS if arm != 'H'}

    def group(indices):
        old_event_equal = [np.array_equal(old_effective_events[a], old_effective_events[b])
                           for a, b in pairs]
        old_equal = [np.array_equal(old_matrix[a], old_matrix[b]) for a, b in pairs]
        old_distinct = [np.max(np.abs(old_matrix[a] - old_matrix[b])) > TOLERANCE for a, b in pairs]
        return dict(pairs=len(indices),
            varying_pairs={arm: sum(variations[arm][i] > TOLERANCE for i in indices) for arm in ARMS},
            contrast_pairs={arm: sum(contrasts[arm][i] > TOLERANCE for i in indices) for arm in contrasts},
            max_variation={arm: max((variations[arm][i] for i in indices), default=0.) for arm in ARMS},
            max_contrast={arm: max((contrasts[arm][i] for i in indices), default=0.) for arm in contrasts},
            old_equal_event_pairs=sum(bool(old_event_equal[i]) for i in indices),
            old_equal_event_new_distinct=sum(bool(old_event_equal[i] and variations['H'][i] > TOLERANCE) for i in indices),
            old_equal_interaction_pairs=sum(bool(old_equal[i]) for i in indices),
            old_equal_interaction_new_distinct=sum(bool(old_equal[i] and variations['H'][i] > TOLERANCE) for i in indices),
            old_distinct_new_nondistinct=sum(bool(old_distinct[i] and variations['H'][i] <= TOLERANCE) for i in indices))

    return dict(all=group(range(len(pairs))), edited=group([i for i, p in enumerate(pairs) if noop not in p]))


def candidate_matrices(observation, bank):
    # This also enforces the exact observed-only schema and bank/source pairing.
    old_values, old_masks, old_matrices = observed.interaction_matrices(observation, bank)
    ids = [c.candidate_id for c in bank.candidates]
    current_signature = directed.signature(observation['current_code'])
    candidate_signatures = {c.candidate_id: directed.signature(observed._exact_text(c.source)) for c in bank.candidates}
    matrices = {}; diagnostics = {cid: {} for cid in ids}
    for arm in ARMS:
        history = (observation['donor_history'] if arm == 'U' else
                   observation['history'][-1:] if arm == 'L' else observation['history'])
        order = observed.semantic.permutation_indices(len(history), observation['example_id']) if arm == 'HS' else tuple(range(len(history)))
        signatures = [directed.signature(history[i]['code'], history[i]['language']) for i in order] + [current_signature]
        transition_reasons = [None if before.available and after.available else
            '+'.join(label + str(s.reason) for label, s in (('before_', before), ('after_', after)) if not s.available)
            for before, after in zip(signatures, signatures[1:])]
        rows = []
        for candidate in bank.candidates:
            f = directed.candidate_features(observation['current_code'],
                observed._exact_text(candidate.source), observation['current_verdict'],
                history, observation['current_timestamp'], mode='marginal' if arm == 'Jm' else 'joint',
                shuffled=arm == 'HS', shuffle_key=observation['example_id'])
            rows.append(f.vector)
            applicable = np.asarray(f.applicable_mask)
            expected_available = current_signature.available and candidate_signatures[candidate.candidate_id].available
            if (f.candidate_available != expected_available or
                    not np.array_equal(applicable, [expected_available and reason is None for reason in transition_reasons])):
                raise ValueError('declared source availability differs from encoded matching mask')
            kinds = len(set(np.asarray(f.pair_indices)[applicable].tolist()))
            similarities = np.asarray(f.similarities)
            diagnostics[candidate.candidate_id][arm] = dict(
                vector=f.vector.tolist(), candidate_available=bool(f.candidate_available),
                current_source_unavailable_reason=current_signature.reason,
                candidate_source_unavailable_reason=candidate_signatures[candidate.candidate_id].reason,
                historical_transition_unavailable_reasons=transition_reasons,
                history_masses=np.asarray(f.history_masses).tolist(),
                candidate_mass=int(f.candidate_mass), transition_count=len(history),
                applicable_mask=applicable.tolist(), applicable_transitions=int(applicable.sum()),
                opportunity=f.opportunity.tolist(), similarities=similarities.tolist(),
                pair_indices=np.asarray(f.pair_indices).tolist(),
                permutation_indices=list(f.permutation_indices),
                applicable_feedback_pair_kinds=kinds,
                constant_feedback=bool(applicable.any() and kinds == 1),
                same_matches=int(np.sum(applicable & (similarities[:, 0] > 0))),
                reverse_matches=int(np.sum(applicable & (similarities[:, 1] > 0))),
                no_opportunity=bool(not applicable.any()),
                no_overlap=bool(applicable.any() and not np.any(similarities[applicable] > 0)))
        matrices[arm] = np.asarray(rows)
        if np.any(np.linalg.norm(matrices[arm], axis=1) > 1 + TOLERANCE):
            raise ValueError('analytic bounded-feature contract violated')
    noop = ids.index(observed.source_hash(bank.current_source))
    if any(np.any(x[noop]) for x in matrices.values()):
        raise ValueError('exact no-op must have zero directed residual features')
    return matrices, diagnostics, geometry(matrices, old_matrices['H'], old_values * old_masks, noop)


def support_summary(observations, banks, assignment, *, callback=None):
    if (not observations or any(type(o) is not dict or set(o) != observed.OBSERVATION_FIELDS for o in observations)
            or len({o['example_id'] for o in observations}) != len(observations)
            or len({o['user_id'] for o in observations}) != len(observations)
            or len({o['bank_id'] for o in observations}) != len(observations)
            or set(banks) != {o['bank_id'] for o in observations}):
        raise ValueError('exact unique observed-only recipients and banks required')
    if (set(assignment['example_fold']) != {o['example_id'] for o in observations}
            or any(type(o['fold']) is not int or o['fold'] not in range(5)
                   or o['fold'] != assignment['example_fold'][o['example_id']]
                   or o['fold'] != assignment['problem_fold'][o['problem_id']] for o in observations)
            or {o['fold'] for o in observations} != set(range(5))):
        raise ValueError('exact five original problem folds required')
    records = []
    for completed, o in enumerate(observations, 1):
        bank = banks[o['bank_id']]
        matrices, diagnostics, geometry_report = candidate_matrices(o, bank)
        candidates = []
        for c in bank.candidates:
            candidates.append(dict(candidate_id=c.candidate_id, is_noop=c.is_noop, arms=diagnostics[c.candidate_id]))
        classes = {}
        for arm, matrix in matrices.items():
            grouped = {}
            for c, vector in zip(bank.candidates, matrix):
                grouped.setdefault(tuple(vector), []).append(c.candidate_id)
            classes[arm] = list(grouped.values())
        records.append(dict(example_id=o['example_id'], user_id=o['user_id'], problem_id=o['problem_id'],
            fold=o['fold'], bank_id=o['bank_id'], bank_seal_sha256=bank.seal_sha256,
            prior_count=len(o['history']), prior_languages=dict(Counter(h['language'] for h in o['history'])),
            candidate_count=len(candidates), terminal_attempts=len(bank.attempts),
            failed_attempts=sum(a.status != 'success' for a in bank.attempts), candidates=candidates,
            equivalence_classes=classes, geometry=geometry_report))
        if callback and (completed % 25 == 0 or completed == len(observations)):
            callback(dict(completed_examples=completed, total_examples=len(observations)))

    def aggregate(group):
        pairs = {}
        for kind in ('all', 'edited'):
            gs = [r['geometry'][kind] for r in group]
            values = {k: sum(g[k] for g in gs) for k in (
                'pairs', 'old_equal_event_pairs', 'old_equal_event_new_distinct',
                'old_equal_interaction_pairs', 'old_equal_interaction_new_distinct', 'old_distinct_new_nondistinct')}
            values.update(varying_pairs={arm: sum(g['varying_pairs'][arm] for g in gs) for arm in ARMS},
                contrast_pairs={arm: sum(g['contrast_pairs'][arm] for g in gs) for arm in ARMS if arm != 'H'})
            pairs[kind] = values
        candidates = [c for r in group for c in r['candidates']]
        masks = {arm: {flag: sum(c['arms'][arm][flag] for c in candidates) for flag in (
            'candidate_available', 'applicable_transitions', 'same_matches', 'reverse_matches',
            'no_opportunity', 'no_overlap', 'constant_feedback')} for arm in ARMS}
        return dict(prefixes=len(group), users=len({r['user_id'] for r in group}),
            problems=len({r['problem_id'] for r in group}), candidates=len(candidates),
            prior_one=sum(r['prior_count'] == 1 for r in group),
            terminal_attempts=sum(r['terminal_attempts'] for r in group),
            failed_attempts=sum(r['failed_attempts'] for r in group), pairs=pairs, candidate_diagnostics=masks)

    folds = {str(f): dict(train=aggregate([r for r in records if r['fold'] != f]),
                          held=aggregate([r for r in records if r['fold'] == f])) for f in range(5)}
    prerequisite = {}
    for f, groups in folds.items():
        tr = groups['train']['pairs']
        prerequisite[f] = dict(edited_H_varies=tr['edited']['varying_pairs']['H'] > 0,
            old_equal_event_edited_split=tr['edited']['old_equal_event_new_distinct'] > 0,
            **{f'contrast_{arm}': tr['all']['contrast_pairs'][arm] > 0 for arm in ARMS if arm != 'H'})
    return dict(kind='observed_only_directed_history_support_v1', configuration=directed.configuration(),
        arms=list(ARMS), rows=records, totals=aggregate(records), folds=folds,
        prerequisites=prerequisite, variation_prerequisite=all(all(v.values()) for v in prerequisite.values()),
        feature_dimension=144, scale_divisor=2., tolerance=TOLERANCE,
        tolerance_units='scaled final coordinate, descriptive only', excluded_prefixes=0,
        fitting_performed=False, outcomes_opened=False, successors_opened=False,
        models_opened=False, predictions_opened=False, fit_release_authorized=False,
        donor_boundary='unchanged external same-problem observed donor; not fold-training-only',
        note='Source-only feasibility; not correctness, causal mechanism or learning benefit.')


def audit(project, output):
    project = observed._canonical(project); output = observed._canonical(output)
    if output != project / FAMILY / 'support-v1' or output.exists():
        raise ValueError('new exact directed support-v1 output required; no retry or resume')
    state = observed._source_state()
    sources = {name: observed.sha(ROOT / name) for name in SOURCE_FILES}
    if any(sources[name] != digest for name, digest in {**observed.GENERATOR_SOURCES, **observed.FROZEN_FEATURES}.items()):
        raise ValueError('pinned observed/generation feature source drift')
    runtime = runtime_versions()
    if runtime != RUNTIME:
        raise ValueError('reviewed exact server runtime required')
    output.mkdir(parents=True)
    try:
        observations, banks, assignment, coverage, reader = observed.load_inputs(project)
        observed._write(output / 'manifest.json', dict(source=state, source_root=str(ROOT),
            source_sha256=sources, input_sha256=reader.bindings, runtime=runtime,
            parent_complete_sha256=observed.PARENT_SHA, source_coverage=coverage,
            configuration=directed.configuration(), fitting_performed=False))
        observed._write(output / 'folds.json', assignment)
        result = support_summary(observations, banks, assignment,
            callback=lambda value: observed._write(output / 'STATUS.json', dict(phase='observed_support', **value)))
        observed._write(output / 'report.json', result)
        observed._write(output / 'STATUS.json', dict(phase='complete', completed_examples=len(observations), total_examples=len(observations)))
        reader.recheck()
        if observed._source_state() != state or any(observed.sha(ROOT / name) != digest for name, digest in sources.items()):
            raise ValueError('support source changed before completion')
        if runtime_versions() != runtime:
            raise ValueError('support runtime changed before completion')
        observed._write(output / 'COMPLETE.json', dict(status='complete', fitting_performed=False,
            files_sha256={n: observed.sha(output / n) for n in ('manifest.json', 'folds.json', 'report.json', 'STATUS.json')}))
        return result
    except BaseException as exc:
        observed._write(output / 'FAILED.json', dict(error_type=type(exc).__name__, error=str(exc)))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); audit(args.project, args.output)


if __name__ == '__main__':
    main()
