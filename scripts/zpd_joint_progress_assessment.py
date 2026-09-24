"""Pure fourteen-method joint assessment; all old gates AND matched C_joint.

No files, fitting, feature extraction or release. A trusted caller must seal all
35 models and all held predictions before providing authenticated label bodies.
This module checks supplied population/choice consistency, not artifact seals.
"""
from fractions import Fraction

from scripts import zpd_repair_feedback_assessment as original
from scripts import zpd_repair_progress_assessment as progress

PRIMARY = 'H'
ARMS = (*progress.ARMS, 'C_joint')
BASELINES = progress.BASELINES
DIAGNOSTICS = progress.DIAGNOSTICS
METHODS = (*ARMS, *BASELINES, *DIAGNOSTICS, 'noop')
PREDICTION_FIELDS = original.PREDICTION_FIELDS
COHORT_FIELDS = original.COHORT_FIELDS


def project_progress(predictions):
    """Detached exact thirteen-method projection; no dropped recipient."""
    if type(predictions) is not list:
        raise ValueError('exact complete prediction list required')
    result = []
    for row in predictions:
        if (type(row) is not dict or set(row) != PREDICTION_FIELDS
                or type(row['choices']) is not dict or set(row['choices']) != set(METHODS)):
            raise ValueError('exact fourteen-method prediction schema required')
        result.append({**{k: row[k] for k in row if k != 'choices'},
                       'choices': {m: row['choices'][m] for m in progress.METHODS}})
    return result


def _group(rows, labels):
    by_problem = {pid: [p for p in rows if p['problem_id'] == pid]
                  for pid in sorted({p['problem_id'] for p in rows})}
    results = {m: original._metrics(rows, labels, m) for m in METHODS}
    problems = {pid: {m: original._metrics(group, labels, m) for m in METHODS}
                for pid, group in by_problem.items()}
    equal = {m: {k: sum((v[m]['fractions'][k] for v in problems.values()), Fraction(0)) / len(problems)
                 for k in original.METRICS} for m in METHODS} if problems else None
    return dict(examples=len(rows), problems=len(problems), results=results,
                problem_results=problems, equal_problem=equal)


def assess(cohort, predictions, labels):
    # Inherit all original identity, label, fold, unknown and population checks.
    inherited = progress.assess(cohort, project_progress(predictions), labels)
    expected = {row['example_id']: row for row in cohort}
    for row in predictions:
        choice = row['choices']['C_joint']
        if type(choice) is not str or choice not in expected[row['example_id']]['candidate_ids']:
            raise ValueError('C_joint must select an existing exact candidate')
    full = _group(predictions, labels)
    folds = {str(f): _group([p for p in predictions if p['fold'] == f], labels) for f in range(5)}
    rows = {name: [] for name in ('known_ac', 'known_nonac', 'unknown')}
    for p in predictions:
        current = labels[p['bank_id'], p['choices']['noop']]
        group = 'unknown' if current['status'] == 'unknown' else 'known_ac' if current['all_ac'] else 'known_nonac'
        rows[group].append(p)
    groups = {name: _group(group, labels) for name, group in rows.items()}
    group_folds = {name: {str(f): _group([p for p in group if p['fold'] == f], labels)
                          for f in range(5)} for name, group in rows.items()}
    full_check = original._compare(full, 'C_joint')
    nonac_check = original._compare(groups['known_nonac'], 'C_joint')
    ac_check = original._compare(groups['known_ac'], 'C_joint', strict=False)
    nonworse = sum(f['results']['H']['fractions']['ac_lower'] >= f['results']['C_joint']['fractions']['ac_lower']
                   for f in folds.values())
    matched = dict(full_check=full_check, known_nonac_check=nonac_check,
                   known_ac_check=ac_check, nonworse_full_folds=nonworse,
                   required_nonworse_folds=4,
                   passed=bool(full_check['passed'] and nonac_check['passed'] and ac_check['passed'] and nonworse >= 4))
    gate = dict(inherited['gate'])
    gate.update(inherited_progress_gates_passed=inherited['gate']['passed'],
                joint_current_contribution=matched['passed'], joint_current_check=matched,
                passed=bool(inherited['gate']['passed'] and matched['passed']))
    return original._serialize(dict(kind='joint_current_progress4131_repair_gate_v1', primary=PRIMARY,
        methods=list(METHODS), full=full, folds=folds, current_status_subgroups=groups,
        current_status_subgroup_folds=group_folds,
        primary_transitions={m: original._switches(predictions, labels, m) for m in METHODS if m != PRIMARY},
        gate=gate, inherited_progress_gate=inherited['gate'], original_gate=inherited['original_gate'],
        exclusions=0, note='Adaptive fixed-bank development; all inherited repair, mechanism and CF gates '
            'AND the same-solver C_joint comparison. No causal learning benefit or fitting authorization.'))
