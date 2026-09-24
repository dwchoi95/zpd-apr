"""Seal an exact C1/C2 additive diagnostic without fitting or new labels."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from scripts.audit_zpd_history_action_cv import read, rows, sha, write, verify_seals
from scripts.diagnose_zpd_history_action_failure import diagnose_records, verify_report
from scripts.zpd_history_action_blocked import validate_model

C1_COMPLETE = '1d22b390dd88ee9655093c87c4f353acb1048330e542480c3f4f3f659489c07f'
C2_COMPLETE = '3d69ce7329795b86a3870ac36eb3b08b5bb4bba59366254fde6e166caa46d690'
ARMS = ('C0', 'Cn', 'H', 'U', 'HS', 'L')


def compare_predictions(before, after, c1_report, c2_report):
    """Pure same-cohort comparison; source labels/masks and C0 cannot change."""
    events = c1_report['events']
    if events != c2_report['events'] or len(events) != 18 or len(set(events)) != 18:
        raise ValueError('all eighteen unchanged event labels required')
    if len(before) != len(after) or not before:
        raise ValueError('identical nonempty OOF coverage required')
    maximum = 0.
    identity = ('example_id', 'user_id', 'problem_id', 'fold', 'donor_example_id', 'values', 'mask',
                'target_status', 'next_language', 'current_source_sha256', 'current_seen_in_fold_training',
                'within_held_cross_user_distinct_history_collision', 'hs_prior_length_one', 'hs_permutation_identity')
    for old, new in zip(before, after):
        if any(old[k] != new[k] for k in identity):
            raise ValueError('unchanged prefix/label/mask/cohort identity required')
        a, b = np.asarray(old['probabilities']['C0']), np.asarray(new['probabilities']['C0'])
        if a.shape != (18,) or b.shape != (18,) or not np.allclose(a, b, rtol=1e-10, atol=2e-12):
            raise ValueError('C0 negative-control parity failed')
        maximum = max(maximum, float(np.abs(a-b).max()))
    c1 = diagnose_records(before, events); c2 = diagnose_records(after, events)
    verify_report(c1, c1_report); verify_report(c2, c2_report)
    for event, values in c2_report['event_diagnostics']['events'].items():
        expected = c2['overall']['events'][event]['nll_contribution']
        if any(not np.isclose(values[a], expected[a], rtol=1e-10, atol=2e-12) for a in ARMS):
            raise ValueError('independent event contribution differs from sealed C2 report')
    if set(c2_report['event_diagnostics']['events']) != set(events):
        raise ValueError('complete C2 event diagnostic required')
    groups = {}
    for label, chosen in (('language_residual_2', {'language_switch', 'other_lexical_change'}),
                          ('non_language_residual_16', set(events)-{'language_switch', 'other_lexical_change'})):
        groups[label] = {name: {arm: sum(d['overall']['events'][e]['nll_contribution'][arm] for e in chosen)
                               for arm in ARMS} for name, d in (('C1', c1), ('C2', c2))}
    return dict(kind='posthoc_exact_c1_c2_diagnosis_v1', c1=c1, c2=c2, event_groups_additive_mass=groups,
        c0_parity=dict(prefixes=len(after), maximum_absolute_difference=maximum, rtol=1e-10, atol=2e-12),
        c1_decision_unchanged=c1_report['decision'], c2_decision_unchanged=c2_report['decision'],
        confirmatory=False, causal_attribution=False, no_fit=True, no_new_outcomes=True,
        note='Global weighted additive contributions, not conditional-stratum NLLs or sampling intervals.')


def model_inventory(run):
    result = []
    for fold in range(5):
        train_ids = read(run/f'fold-{fold}/cohort.json')['train_example_ids']
        for arm in ARMS:
            model = validate_model(read(run/f'fold-{fold}/{arm}.json'))
            if (model['feature_dimension'] != 8196 or model['arm'] != arm or model['fold'] != fold
                    or model['train_example_ids'] != train_ids):
                raise ValueError('C2 blocked model identity/coverage mismatch')
            result.append(dict(fold=fold, arm=arm, feature_dimension=8196,
                train_prefixes=len(train_ids), heads=len(model['heads']),
                file_sha256=sha(run/f'fold-{fold}/{arm}.json')))
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--parent', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run, parent, output = (p.absolute() for p in (args.run, args.parent, args.output))
    if any(p.resolve() != p for p in (run, parent, output)):
        raise ValueError('canonical paths required')
    if (output.exists() or output.parent != run.parent or output == run or output == parent
            or output in parent.parents or parent in output.parents):
        raise ValueError('new nonoverlapping direct child of C2 family required')
    for directory, expected in ((parent, C1_COMPLETE), (run, C2_COMPLETE)):
        if sha(directory/'COMPLETE.json') != expected: raise ValueError('wrong frozen input run')
        verify_seals(directory)
    for name in ('folds.json', 'COHORTS_COMPLETE.json', 'target-coverage.json'):
        if read(run/name) != read(parent/name): raise ValueError('C1/C2 frozen cohort or coverage differs')
    for fold in range(5):
        if read(run/f'fold-{fold}/cohort.json') != read(parent/f'fold-{fold}/cohort.json'):
            raise ValueError('C1/C2 exact fold cohort differs')
    old = [r for f in range(5) for r in rows(parent/f'fold-{f}/predictions.jsonl')]
    new = [r for f in range(5) for r in rows(run/f'fold-{f}/predictions.jsonl')]
    report = compare_predictions(old, new, read(parent/'report.json'), read(run/'report.json'))
    report['c2_model_inventory'] = model_inventory(run)
    project = Path(__file__).resolve().parents[1]
    sources = ('scripts/diagnose_zpd_history_action_c2.py', 'scripts/diagnose_zpd_history_action_failure.py',
               'scripts/zpd_history_action_blocked.py', 'scripts/audit_zpd_history_action_cv.py')
    manifest = dict(c1_complete_sha256=C1_COMPLETE, c2_complete_sha256=C2_COMPLETE,
        c1_report_sha256=sha(parent/'report.json'), c2_report_sha256=sha(run/'report.json'),
        source_sha256={name: sha(project/name) for name in sources})
    for directory in (parent, run): verify_seals(directory)
    if sha(parent/'COMPLETE.json') != C1_COMPLETE or sha(run/'COMPLETE.json') != C2_COMPLETE:
        raise ValueError('diagnostic inputs changed')
    output.mkdir(parents=True)
    write(output/'report.json', report); write(output/'manifest.json', manifest)
    write(output/'COMPLETE.json', dict(status='complete', c2_complete_sha256=C2_COMPLETE,
        files_sha256={name: sha(output/name) for name in ('report.json', 'manifest.json')}))
    print(str(output/'report.json'))


if __name__ == '__main__':
    main()
