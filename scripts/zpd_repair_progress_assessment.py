"""Pure progress32 assessment: unchanged original gates AND the frozen CF gate.

No I/O, feature construction, execution, fitting or release. The caller must
authenticate the entire prediction barrier before supplying assessment labels.
The original eleven-method assessment runs unchanged on an exact projection;
CF and shared_H_CF are added without replacing any original comparison.
"""
from fractions import Fraction

from scripts import zpd_repair_feedback_assessment as original

PRIMARY = 'H'
ARMS = ('H', 'Jm', 'HS', 'U', 'L', 'CF')
BASELINES = original.BASELINES
DIAGNOSTICS = (*original.DIAGNOSTICS, 'shared_H_CF')
METHODS = (*ARMS, *BASELINES, *DIAGNOSTICS, 'noop')
PREDICTION_FIELDS = original.PREDICTION_FIELDS
COHORT_FIELDS = original.COHORT_FIELDS


def project_original(predictions):
    """Strict complete thirteen-method records; return a detached projection."""
    if type(predictions) is not list:
        raise ValueError('exact complete prediction list required')
    result = []
    for row in predictions:
        if (type(row) is not dict or set(row) != PREDICTION_FIELDS
                or type(row['choices']) is not dict or set(row['choices']) != set(METHODS)):
            raise ValueError('exact thirteen-method prediction schema required')
        result.append({**{k: v for k, v in row.items() if k != 'choices'},
                       'choices': {m: row['choices'][m] for m in original.METHODS}})
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
    projected = project_original(predictions)
    # Reuse the strict original population/label validation, not a weaker copy.
    expected = original._validate(cohort, projected, labels)
    for row in predictions:
        ids = expected[row['example_id']]['candidate_ids']
        if any(type(row['choices'][m]) is not str or row['choices'][m] not in ids
               for m in ('CF', 'shared_H_CF')):
            raise ValueError('new methods must select an existing exact candidate')
    old = original.assess(cohort, projected, labels)
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
    full_check = original._compare(full, 'CF')
    nonac_check = original._compare(groups['known_nonac'], 'CF')
    ac_check = original._compare(groups['known_ac'], 'CF', strict=False)
    nonworse = sum(f['results']['H']['fractions']['ac_lower'] >= f['results']['CF']['fractions']['ac_lower']
                   for f in folds.values())
    cf = dict(full_check=full_check, known_nonac_check=nonac_check,
              known_ac_check=ac_check, nonworse_full_folds=nonworse,
              required_nonworse_folds=4,
              passed=bool(full_check['passed'] and nonac_check['passed'] and ac_check['passed'] and nonworse >= 4))
    gate = dict(old['gate'])
    gate.update(original_gates_passed=old['gate']['passed'], current_feedback_contribution=cf['passed'],
                current_feedback_check=cf, passed=bool(old['gate']['passed'] and cf['passed']))
    return original._serialize(dict(kind='prospective_statement_progress32_repair_gate_v1', primary=PRIMARY,
        methods=list(METHODS), full=full, folds=folds, current_status_subgroups=groups,
        current_status_subgroup_folds=group_folds,
        primary_transitions={m: original._switches(predictions, labels, m) for m in METHODS if m != PRIMARY},
        gate=gate, original_gate=old['gate'], exclusions=0,
        note='Adaptive fixed-bank development; all original gates AND the prospective CF gate; '
             'statement-sample feedback is a new observation, not learner-outcome evidence.'))
