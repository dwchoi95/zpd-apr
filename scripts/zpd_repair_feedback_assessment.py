"""Pure exact-fraction assessment for the prospectively fixed repair gate.

No I/O, fitting, feature extraction or candidate execution. The caller must
verify sealed all-fold predictions and label provenance before invoking this
module. Supplied core labels cover every candidate, including unknowns. This
API checks internal population/choice consistency, not external artifact seals.
"""
from collections import Counter
from fractions import Fraction
import math

PRIMARY = 'H'
CONTROLS = ('Jm', 'HS', 'U', 'L')
BASELINES = ('structural_C', 'lexical_C', 'first_attempt')
DIAGNOSTICS = ('shared_H_HS', 'shared_H_Jm')
METHODS = (PRIMARY, *CONTROLS, *BASELINES, *DIAGNOSTICS, 'noop')
METRICS = ('ac_lower', 'ac_upper', 'regression_lower', 'regression_upper')
COHORT_FIELDS = {'example_id', 'user_id', 'bank_id', 'problem_id', 'fold',
                 'candidate_ids', 'noop_candidate_id'}
PREDICTION_FIELDS = {'example_id', 'user_id', 'bank_id', 'problem_id', 'fold', 'choices'}
LABEL_FIELDS = {'bank_id', 'candidate_id', 'status', 'gain', 'loss', 'all_ac'}


def _validate(cohort, predictions, labels):
    if type(cohort) is not list or not cohort or type(predictions) is not list or type(labels) is not dict:
        raise ValueError('nonempty cohort, prediction list and exact label mapping required')
    expected = {}; bank_ids = set(); users = set(); problems = {}; keys = set()
    for row in cohort:
        if type(row) is not dict or set(row) != COHORT_FIELDS:
            raise ValueError('strict outcome-free cohort row required')
        if any(type(row[k]) is not str or not row[k] for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'noop_candidate_id')):
            raise ValueError('nonempty exact identity strings required')
        if row['example_id'] in expected or row['bank_id'] in bank_ids or row['user_id'] in users:
            raise ValueError('unique recipients, examples and banks required')
        if type(row['fold']) is not int or row['fold'] not in range(5):
            raise ValueError('integer five-fold membership required')
        if problems.setdefault(row['problem_id'], row['fold']) != row['fold']:
            raise ValueError('problem cannot cross folds')
        ids = row['candidate_ids']
        if (type(ids) is not list or not ids or len(set(ids)) != len(ids)
                or any(type(cid) is not str or not cid for cid in ids) or row['noop_candidate_id'] not in ids):
            raise ValueError('exact deduplicated candidates including no-op required')
        expected[row['example_id']] = row; bank_ids.add(row['bank_id']); users.add(row['user_id'])
        keys.update((row['bank_id'], cid) for cid in ids)
    if {row['fold'] for row in cohort} != set(range(5)) or set(labels) != keys:
        raise ValueError('all five folds and exact all-candidate label coverage required')
    for key, value in labels.items():
        if type(value) is not dict or set(value) != LABEL_FIELDS or (value['bank_id'], value['candidate_id']) != key:
            raise ValueError('strict core execution label identity required')
        if value['status'] == 'unknown':
            if any(value[k] is not None for k in ('gain', 'loss', 'all_ac')):
                raise ValueError('unknown evidence must remain null')
        elif value['status'] == 'stable':
            if (type(value['all_ac']) is not bool or any(type(value[k]) not in (int, float)
                    or not math.isfinite(value[k]) or not 0 <= value[k] <= 1 for k in ('gain', 'loss'))
                    or value['gain'] + value['loss'] > 1 + 1e-12
                    or value['all_ac'] and value['loss'] != 0):
                raise ValueError('valid stable correctness and normalized evidence required')
        else:
            raise ValueError('unknown label status')
    for row in cohort:
        lab = labels[row['bank_id'], row['noop_candidate_id']]
        if lab['status'] == 'stable' and (lab['gain'] != 0 or lab['loss'] != 0):
            raise ValueError('stable exact no-op cannot gain or lose a testcase')
    seen = set()
    for pred in predictions:
        if type(pred) is not dict or set(pred) != PREDICTION_FIELDS:
            raise ValueError('strict sealed choice record required')
        ident = pred['example_id']
        if ident in seen or ident not in expected:
            raise ValueError('duplicate or extra prediction recipient')
        row = expected[ident]; seen.add(ident)
        if any(type(pred[k]) is not type(row[k]) or pred[k] != row[k]
               for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')):
            raise ValueError('prediction membership mismatch')
        choices = pred['choices']
        if (type(choices) is not dict or set(choices) != set(METHODS)
                or any(type(cid) is not str or cid not in row['candidate_ids'] for cid in choices.values())
                or choices['noop'] != row['noop_candidate_id']):
            raise ValueError('all fixed methods must select an existing candidate')
    if seen != set(expected):
        raise ValueError('missing sealed prediction recipient')
    return expected


def _fraction(value):
    return dict(numerator=value.numerator, denominator=value.denominator, value=float(value))


def _metrics(group, labels, method):
    n = len(group)
    counts = Counter(stable_ac=0, stable_regression=0, unknown=0, noop_selected=0)
    for pred in group:
        chosen = pred['choices'][method]; lab = labels[pred['bank_id'], chosen]
        counts['unknown'] += lab['status'] == 'unknown'
        counts['stable_ac'] += lab['status'] == 'stable' and lab['all_ac']
        counts['stable_regression'] += lab['status'] == 'stable' and lab['loss'] > 0
        counts['noop_selected'] += chosen == pred['choices']['noop']
    if not n:
        return dict(examples=0, evaluable=False, counts=dict(counts), fractions=None)
    a, r, u = (counts[k] for k in ('stable_ac', 'stable_regression', 'unknown'))
    fractions = dict(zip(METRICS, (Fraction(a, n), Fraction(a + u, n), Fraction(r, n), Fraction(r + u, n))))
    return dict(examples=n, evaluable=True, counts=dict(counts), fractions=fractions)


def _group(group, labels):
    by_problem = {pid: [p for p in group if p['problem_id'] == pid]
                  for pid in sorted({p['problem_id'] for p in group})}
    results = {m: _metrics(group, labels, m) for m in METHODS}
    problems = {pid: {m: _metrics(rows, labels, m) for m in METHODS} for pid, rows in by_problem.items()}
    equal = {m: {k: sum((v[m]['fractions'][k] for v in problems.values()), Fraction(0)) / len(problems)
                 for k in METRICS} for m in METHODS} if problems else None
    return dict(examples=len(group), problems=len(problems), results=results,
                problem_results=problems, equal_problem=equal)


def _compare(group, control, *, strict=True, equal_problem=True):
    if not group['examples']:
        return dict(evaluable=False, passed=False, checks={})
    checks = {}
    sources = {'pooled': {m: cell['fractions'] for m, cell in group['results'].items()}}
    if equal_problem:
        sources['equal_problem'] = group['equal_problem']
    for name, cells in sources.items():
        p, c = cells[PRIMARY], cells[control]
        checks[name + '_ac'] = p['ac_lower'] > c['ac_lower'] if strict else p['ac_lower'] >= c['ac_lower']
        checks[name + '_regression_lower'] = p['regression_lower'] <= c['regression_lower']
        checks[name + '_regression_upper'] = p['regression_upper'] <= c['regression_upper']
    return dict(evaluable=True, passed=all(checks.values()), checks=checks)


def _switches(predictions, labels, control):
    values = Counter(examples=len(predictions), selected_candidate_changed=0, ac_gained=0,
        ac_lost=0, regression_prevented=0, regression_introduced=0, not_jointly_known=0,
        edited_to_edited=0, to_noop=0, from_noop=0)
    for p in predictions:
        a, b, noop = (p['choices'][key] for key in (PRIMARY, control, 'noop'))
        if a != b:
            values['selected_candidate_changed'] += 1
            values['to_noop' if a == noop else 'from_noop' if b == noop else 'edited_to_edited'] += 1
        left, right = labels[p['bank_id'], a], labels[p['bank_id'], b]
        if left['status'] == 'unknown' or right['status'] == 'unknown':
            values['not_jointly_known'] += 1
        else:
            values['ac_gained'] += left['all_ac'] and not right['all_ac']
            values['ac_lost'] += right['all_ac'] and not left['all_ac']
            values['regression_prevented'] += left['loss'] == 0 and right['loss'] > 0
            values['regression_introduced'] += left['loss'] > 0 and right['loss'] == 0
    return dict(values)


def _serialize(value):
    if isinstance(value, Fraction):
        return _fraction(value)
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def assess(cohort, predictions, labels):
    """Assess all sealed choices after prediction; no adaptive selection."""
    _validate(cohort, predictions, labels)
    full = _group(predictions, labels)
    folds = {str(f): _group([p for p in predictions if p['fold'] == f], labels) for f in range(5)}
    subgroups = {name: [] for name in ('known_ac', 'known_nonac', 'unknown')}
    for p in predictions:
        current = labels[p['bank_id'], p['choices']['noop']]
        name = 'unknown' if current['status'] == 'unknown' else 'known_ac' if current['all_ac'] else 'known_nonac'
        subgroups[name].append(p)
    groups = {name: _group(rows, labels) for name, rows in subgroups.items()}
    group_folds = {name: {str(f): _group([p for p in rows if p['fold'] == f], labels) for f in range(5)}
                   for name, rows in subgroups.items()}
    nonworse = {m: sum(f['results'][PRIMARY]['fractions']['ac_lower'] >= f['results'][m]['fractions']['ac_lower']
                       for f in folds.values()) for m in (*BASELINES[:2], *CONTROLS)}
    baseline_checks = {m: _compare(full, m) for m in BASELINES}
    known_nonac = _compare(groups['known_nonac'], 'structural_C')
    known_ac = _compare(groups['known_ac'], 'structural_C', strict=False)
    improvement = (all(c['passed'] for c in baseline_checks.values()) and known_nonac['passed'] and known_ac['passed']
                   and all(nonworse[m] >= 4 for m in BASELINES[:2]))
    mechanism_checks = {m: _compare(full, m, equal_problem=False) for m in CONTROLS}
    mechanism = all(c['passed'] and nonworse[m] >= 4 for m, c in mechanism_checks.items())
    return _serialize(dict(kind='prospective_feedback_repair_gate_v1', primary=PRIMARY,
        methods=list(METHODS), full=full, folds=folds, current_status_subgroups=groups,
        current_status_subgroup_folds=group_folds,
        primary_transitions={m: _switches(predictions, labels, m) for m in METHODS if m != PRIMARY},
        gate=dict(actual_repair_improvement=bool(improvement), mechanism_contribution=bool(mechanism),
            passed=bool(improvement and mechanism), baseline_checks=baseline_checks,
            known_nonac_check=known_nonac, known_ac_check=known_ac, mechanism_checks=mechanism_checks,
            nonworse_full_folds=nonworse, required_nonworse_folds=4,
            learned_controls_may_replace_primary=False, confirmatory=False,
            educational_benefit_established=False, unknown_bounds_are_confidence_intervals=False),
        exclusions=0, note='Adaptive fixed-bank development; exact fractions gate all retained recipients.'))
