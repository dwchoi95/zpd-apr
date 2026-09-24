"""Read-only paired and linear-margin accounting for the sealed failed stage.

This describes already observed predictions. It does not fit, execute, rerank,
change a threshold/coefficient, select another arm, or redefine the gate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import math
from pathlib import Path

from scripts.audit_zpd_repair_preservation_cv import CELLS, read, sha, verify_new_seals, write

PRIMARY = 'refined_balanced'
FIELDS = ('prefixes', 'jointly_known', 'not_jointly_known', 'ac_lost', 'ac_gained',
          'regression_prevented', 'regression_introduced')


def paired_record(row, left, right, original):
    same = left['candidate_id'] == right['candidate_id']
    category = ('same' if same else 'to_noop' if left['noop'] else
                'from_noop' if right['noop'] else 'nonnoop_change')
    known = not (left['unknown'] or right['unknown'])
    return dict(example_id=row['example_id'], fold=row['fold'], problem_id=row['problem_id'],
        original_status='unknown' if original['unknown'] else 'known_ac' if original['rr_lower_bound'] else 'known_nonac',
        category=category, prefixes=1, jointly_known=int(known), not_jointly_known=int(not known),
        ac_lost=int(known and right['rr_lower_bound'] and not left['rr_lower_bound']),
        ac_gained=int(known and left['rr_lower_bound'] and not right['rr_lower_bound']),
        regression_prevented=int(known and right['regression_rate_lower_bound'] and not left['regression_rate_lower_bound']),
        regression_introduced=int(known and left['regression_rate_lower_bound'] and not right['regression_rate_lower_bound']))


def aggregate(records):
    def sums(items): return {k: sum(r[k] for r in items) for k in FIELDS}
    result = dict(overall=sums(records), records=records)
    for name, keys in (('by_category', ('category',)), ('by_status', ('original_status',)),
                       ('by_fold', ('fold',)), ('by_category_status', ('category', 'original_status')),
                       ('by_fold_category', ('fold', 'category'))):
        groups = defaultdict(list)
        for r in records: groups['|'.join(str(r[k]) for k in keys)].append(r)
        result[name] = {k: sums(v) for k, v in sorted(groups.items())}
        for field in FIELDS:
            assert sum(v[field] for v in result[name].values()) == result['overall'][field]
    return result


def margin_decomposition(old_scores, new_scores, noop, old_choice, old_effect, new_effect):
    """An algebraic two-fitted-model contrast, not coefficient intervention."""
    before = old_scores[noop]-old_scores[old_choice]
    after = new_scores[noop]-new_scores[old_choice]
    shift = new_effect-old_effect
    return dict(old_margin=before, new_margin=after, total_margin_change=after-before,
                noop_coordinate_change=shift, other_coordinate_change=after-before-shift)


def diagnose(predictions, report, models):
    methods = report['results']
    outcomes = {method: {r['example_id']: r for r in data['predictions']} for method, data in methods.items()}
    ids = {r['example_id'] for r in predictions}
    if len(ids) != len(predictions) or any(set(r) != ids for r in outcomes.values()):
        raise ValueError('exact unique prediction/outcome IDs required')
    for row in predictions:
        if any(outcomes[m][row['example_id']]['candidate_id'] != cid for m, cid in row['choices'].items()):
            raise ValueError('saved selected outcome and choice disagree')
    pairs = [(PRIMARY, c) for c in ('structural_C', 'legacy_balanced', 'refined_natural', 'lexical_C', 'first_attempt')]
    pairs += [(c, 'structural_C') for c in ('legacy_balanced', 'refined_natural')]
    contrasts = {left+'-'+right: aggregate([paired_record(r, outcomes[left][r['example_id']],
        outcomes[right][r['example_id']], outcomes['noop'][r['example_id']]) for r in predictions]) for left, right in pairs}
    coefficient_cells = {}; margins = []
    for fold, cells in models.items():
        coefficient_cells[str(fold)] = {}
        reference_scale = cells['legacy_natural']['numeric_scale']
        for cell in CELLS:
            model = cells[cell]
            if model['numeric_scale'] != reference_scale:
                raise ValueError('common fold transform changed')
            index = model['numeric_names'].index('candidate_is_noop')
            coefficient_cells[str(fold)][cell] = dict(coefficient=model['coefficients'][index],
                scale=model['numeric_scale'][index], effect=model['coefficients'][index]/model['numeric_scale'][index],
                training_support=model['training']['informative_stratum_prefixes'],
                training_coverage=model['training']['stratum_prefixes'],
                training_mass=model['training']['stratum_mass'], pairs=model['training']['ordered_pairs'])
    for row in predictions:
        if row['choices'][PRIMARY] != row['choices']['noop']: continue
        if row['choices']['structural_C'] == row['choices']['noop']:
            raise ValueError('diagnosed frozen control is expected never to choose no-op')
        cells = coefficient_cells[str(row['fold'])]
        ledger = margin_decomposition(row['candidate_scores']['structural_C'], row['candidate_scores'][PRIMARY],
            row['choices']['noop'], row['choices']['structural_C'], cells['legacy_natural']['effect'], cells[PRIMARY]['effect'])
        margins.append(dict(example_id=row['example_id'], fold=row['fold'], **ledger))
    def margin_summary(group):
        names = ('old_margin', 'new_margin', 'total_margin_change', 'noop_coordinate_change', 'other_coordinate_change')
        sums = {k: math.fsum(v[k] for v in group) for k in names}
        return dict(prefixes=len(group), sums=sums,
            means={k: v/len(group) if group else None for k, v in sums.items()},
            noop_coordinate_share_of_total_margin_change=(sums['noop_coordinate_change']/sums['total_margin_change']
                if sums['total_margin_change'] else None))
    return dict(kind='posthoc_failed_preservation_diagnosis_v1', contrasts=contrasts,
        coefficients=coefficient_cells, observed_margin_ledger=dict(records=margins, overall=margin_summary(margins),
            folds={str(f): margin_summary([r for r in margins if r['fold'] == f]) for f in range(5)}),
        result_counts={m: v['counts'] for m, v in methods.items()},
        fold_counts={f: {m: v['counts'] for m, v in cells.items()} for f, cells in report['fold_results'].items()},
        unchanged_decision=report['decision'], confirmatory=False, causal_attribution=False,
        sampling_intervals_computed=False, reranked=False, new_outcomes=False)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run.resolve(), args.output.resolve()
    if output.exists() or output == run or run in output.parents or output in run.parents:
        raise ValueError('new nonoverlapping diagnostic output required')
    marker = verify_new_seals(run); bound = sha(run/'COMPLETE.json')
    report = diagnose(read(run/'predictions.json'), read(run/'report.json'),
        {f: {c: read(run/f'fold-{f}/{c}.json') for c in CELLS} for f in range(5)})
    verify_new_seals(run)
    if sha(run/'COMPLETE.json') != bound: raise ValueError('input changed during diagnosis')
    output.mkdir(parents=True)
    write(output/'report.json', report)
    write(output/'manifest.json', dict(input_complete_sha256=bound, input_files_sha256=marker['files_sha256'],
        script_sha256=sha(__file__), no_fit=True, no_reranking=True, no_gate_change=True))
    write(output/'COMPLETE.json', dict(status='complete', input_complete_sha256=bound,
        files_sha256={name: sha(output/name) for name in ('report.json', 'manifest.json')}))
    print(str(output/'report.json'))


if __name__ == '__main__':
    main()
