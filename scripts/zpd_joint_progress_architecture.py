"""Pure non-promotable joint-H versus sealed progress32-H paired diagnostic.

No I/O, model fitting, execution, selection or assessment release. The caller
must authenticate the fixed old raw prediction/seal bytes and all 35 joint
models/predictions BEFORE supplying these labels. Literal reference identities
are necessary but cannot prove which bytes produced a supplied Python object.
The future guard owns raw-SHA/source/runtime authentication and final rechecks.

This is not a fifteenth scored method, a success gate or causal identification
of fixed-base failure. It compares two adaptively developed architectures on
the unchanged complete development cohort, retaining unknowns and negatives.
"""
from fractions import Fraction
import math
import re

from scripts import zpd_repair_feedback_assessment as core
from scripts import zpd_repair_progress_assessment as progress
from scripts import zpd_joint_progress_assessment as joint
from src.repair.pilot_contracts import canonical_hash

KIND = 'joint_vs_sealed_progress32_H_diagnostic_v1'
REFERENCE_PINS = {
    'prediction_seal_sha256': '408732a885f35b629823c788fe2ddc3cc08d2ccc2e72027483419e97995a5f8f',
    'predictions_sha256': '212563ef5afe0de07d25701d90f8982dfa44f347f8f3ffc97828134f7949f394',
}
ARCHITECTURES = ('joint_H', 'progress32_H')
IDENTITIES = ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')
SHARED = ('HS', 'Jm', 'CF')
RICH_COMMON = {*core.PREDICTION_FIELDS, 'bank_seal_sha256', 'candidate_scores', 'shared_theta_diagnostics'}
OLD_FLAG = 'projected_zero_residual_parent_choice_parity'
JOINT_FLAG = 'direct_history_diagnostic_holds_all_current_coefficients_fixed'


def _require(condition, message):
    if not condition: raise ValueError(message)


def _sha(value): return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None
def _real(value): return type(value) in (int, float) and math.isfinite(value)


def _score_map(scores, ids):
    _require(type(scores) is dict and set(scores) == set(ids)
        and all(_real(v) for v in scores.values()), 'exact all-candidate finite score map required')


def _rich(cohort, predictions, methods, flag, labels):
    _require(type(predictions) is list, 'complete rich prediction list required')
    expected = {r['example_id']: r for r in cohort}
    projected = []
    for pred in predictions:
        _require(type(pred) is dict and set(pred) == RICH_COMMON | {flag} and pred[flag] is True,
            'strict sealed rich prediction schema and diagnostic flag required')
        _require(pred['example_id'] in expected and _sha(pred['bank_seal_sha256']),
            'known recipient and exact bank seal required')
        row = expected[pred['example_id']]; ids = row['candidate_ids']
        _require(type(pred['choices']) is dict and set(pred['choices']) == set(methods)
            and all(type(cid) is str and cid in ids for cid in pred['choices'].values()),
            'exact original architecture method roster and candidate choices required')
        scores = pred['candidate_scores']
        _require(type(scores) is dict and set(scores) == set(methods), 'exact architecture score roster required')
        for name in methods:
            _score_map(scores[name], ids)
            _require(pred['choices'][name] == min(scores[name], key=lambda cid: (-scores[name][cid], cid)),
                'selected candidate must match finite score SHA argmax')
        diagnostics = pred['shared_theta_diagnostics']
        _require(type(diagnostics) is dict and set(diagnostics) == set(SHARED), 'exact original shared-control diagnostics required')
        for arm in SHARED:
            detail = diagnostics[arm]; control = 'shared_H_' + arm
            _require(type(detail) is dict and set(detail) ==
                {'features_identical_exact', 'choice_changed', 'transition', 'score_difference'}
                and type(detail['features_identical_exact']) is bool and type(detail['choice_changed']) is bool,
                'strict supplied shared-control diagnostic schema required')
            _score_map(detail['score_difference'], ids)
            a, b, noop = (pred['choices'][name] for name in ('H', control, 'noop'))
            transition = 'same' if a == b else 'to_noop' if a == noop else 'from_noop' if b == noop else 'edited_to_edited'
            _require(detail['choice_changed'] == (a != b) and detail['transition'] == transition
                and all(detail['score_difference'][cid] == scores['H'][cid] - scores[control][cid] for cid in ids),
                'supplied shared-control arithmetic/choice diagnostics disagree')
            _require(not detail['features_identical_exact'] or (scores['H'] == scores[control] and a == b),
                'claimed identical features must preserve shared-H scores')
        projected.append({**{key: pred[key] for key in IDENTITIES},
            'choices': {name: pred['choices'][name] for name in core.METHODS}})
    # Reuse only unchanged strict population/label validator, not its gates.
    core._validate(cohort, projected, labels)
    return {pred['example_id']: pred for pred in predictions}


def _group(rows, labels):
    by_problem = {pid: [row for row in rows if row['problem_id'] == pid]
        for pid in sorted({row['problem_id'] for row in rows})}
    results = {name: core._metrics(rows, labels, name) for name in ARCHITECTURES}
    problems = {pid: {name: core._metrics(group, labels, name) for name in ARCHITECTURES}
        for pid, group in by_problem.items()}
    equal = {name: {metric: sum((r[name]['fractions'][metric] for r in problems.values()), Fraction(0)) / len(problems)
        for metric in core.METRICS} for name in ARCHITECTURES} if problems else None
    delta = None if not rows else dict(
        pooled={metric: results['joint_H']['fractions'][metric] - results['progress32_H']['fractions'][metric]
            for metric in core.METRICS},
        equal_problem={metric: equal['joint_H'][metric] - equal['progress32_H'][metric] for metric in core.METRICS})
    return dict(examples=len(rows), problems=len(problems), results=results, problem_results=problems,
        equal_problem=equal, delta_joint_minus_progress32=delta,
        paired_switches=core._switches(rows, labels, 'progress32_H'))


def report(cohort, joint_predictions, old_predictions, labels, *, reference_pins, synthetic=False):
    """Whole-cohort post-prediction diagnostic, with no change to primary gates."""
    _require(type(synthetic) is bool, 'explicit synthetic boolean required')
    _require(type(reference_pins) is dict and set(reference_pins) == set(REFERENCE_PINS)
        and all(_sha(pin) for pin in reference_pins.values()), 'exact old prediction/seal reference pins required')
    _require(synthetic or reference_pins == REFERENCE_PINS, 'fixed production progress32 reference required')
    _require(type(cohort) is list and bool(cohort), 'complete nonempty cohort required')
    # Check basic cohort shape before indexing; full semantics are validated below.
    for row in cohort:
        _require(type(row) is dict and set(row) == core.COHORT_FIELDS
            and type(row['example_id']) is str and type(row['candidate_ids']) is list
            and all(_sha(cid) for cid in row['candidate_ids']) and _sha(row['noop_candidate_id']),
            'strict exact-candidate-SHA cohort required')
    new = _rich(cohort, joint_predictions, joint.METHODS, JOINT_FLAG, labels)
    old = _rich(cohort, old_predictions, progress.METHODS, OLD_FLAG, labels)
    if not synthetic:
        _require(len(cohort) == 320 and len({row['problem_id'] for row in cohort}) == 23
            and sum(len(row['candidate_ids']) for row in cohort) == 2544,
            'unchanged complete320/23/2544 production population required')
    paired = []; references = []
    for row in cohort:
        a, b = new[row['example_id']], old[row['example_id']]
        _require(a['bank_seal_sha256'] == b['bank_seal_sha256'], 'old/new exact bank seal mismatch')
        paired.append({**{key: row[key] for key in IDENTITIES}, 'choices': dict(
            H=a['choices']['H'], joint_H=a['choices']['H'], progress32_H=b['choices']['H'], noop=row['noop_candidate_id'])})
        references.append({**{key: row[key] for key in IDENTITIES}, 'bank_seal_sha256': a['bank_seal_sha256'],
            'candidate_ids': list(row['candidate_ids']), 'noop_candidate_id': row['noop_candidate_id'],
            'joint_H': dict(choice=a['choices']['H'], candidate_scores=dict(a['candidate_scores']['H'])),
            'progress32_H': dict(choice=b['choices']['H'], candidate_scores=dict(b['candidate_scores']['H']))})
    groups = {name: [] for name in ('known_ac', 'known_nonac', 'unknown')}
    for row in paired:
        current = labels[row['bank_id'], row['choices']['noop']]
        name = 'unknown' if current['status'] == 'unknown' else 'known_ac' if current['all_ac'] else 'known_nonac'
        groups[name].append(row)
    value = dict(kind=KIND, gate_effect='none', primary_gate_effect='none', model_promotion=False,
        confirmatory=False, causal_base_failure_established=False, educational_benefit_established=False,
        synthetic=synthetic, exclusions=0, architecture_columns=list(ARCHITECTURES),
        original_primary_method_count=14, additional_scored_primary_methods=0,
        population=dict(examples=len(cohort), problems=len({row['problem_id'] for row in cohort}),
            candidates=sum(len(row['candidate_ids']) for row in cohort), folds=5),
        reference_pins=dict(reference_pins),
        supplied_joint_predictions_canonical_content_sha256=canonical_hash(joint_predictions),
        supplied_old_predictions_canonical_content_sha256=canonical_hash(old_predictions),
        external_raw_reference_authentication='caller_required_not_established_by_this_pure_function',
        full=_group(paired, labels),
        folds={str(f): _group([row for row in paired if row['fold'] == f], labels) for f in range(5)},
        current_status_subgroups={name: _group(rows, labels) for name, rows in groups.items()},
        current_status_subgroup_folds={name: {str(f): _group([row for row in rows if row['fold'] == f], labels)
            for f in range(5)} for name, rows in groups.items()}, score_references=references,
        note='Non-promotable paired architecture diagnostic on all retained recipients. Joint changes current '
            'coefficients and the regularized parameter space; differences do not identify why the earlier '
            'fixed-offset model failed. Unknown bounds are not confidence intervals. No gate is replaced.')
    return core._serialize(value)
