"""Pure supplied-object all-fold joint4131 audit; no I/O, CLI or optimizer.

Shared contracts: byte-preserving capsule serialization, core-label validation,
the frozen pre-joint structural raw/training reference and sklearn's original
weighted StandardScaler, old independent rational assessment, and the separate
reviewed scalar native4131 auditor. No new joint feature fitting/pair builder,
worker scoring, solver validator/evaluator or producer assessment is called.

Raw source/runtime/file authentication, accepted phi32 feedback ancestry and
the all35-predictions-before-label-opening barrier remain caller obligations.
Numeric replay uses atol=rtol=1e-10; config, identities, array hashes, Fraction
reports and selected SHA are exact. Native gradient<=1e-8 is not relaxed.
"""
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import combinations
import json
import math

import numpy as np
from scipy import sparse
from sklearn.preprocessing import StandardScaler

from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_repair_structure as structural
from scripts import zpd_joint_progress_audit as numeric
from scripts import audit_zpd_repair_progress_independent as old
from scripts.zpd_repair_feedback_labels import validate_core_labels
from src.repair.pilot_contracts import canonical_hash

ARMS = ('H', 'Jm', 'HS', 'U', 'L', 'CF', 'C_joint')
PROGRESS_ARMS = ARMS[:-1]
BASELINES = ('structural_C', 'lexical_C', 'first_attempt')
DIAGNOSTICS = ('shared_H_HS', 'shared_H_Jm', 'shared_H_CF')
METHODS = (*ARMS, *BASELINES, *DIAGNOSTICS, 'noop')
METRICS = ('ac_lower', 'ac_upper', 'regression_lower', 'regression_upper')
MODEL_KIND = 'joint_current_progress4131_fold_ranker_v1'
SCALER_KIND = 'joint_current_own_training_transform_v1'
REFERENCE_PINS = {
    'prediction_seal_sha256': '408732a885f35b629823c788fe2ddc3cc08d2ccc2e72027483419e97995a5f8f',
    'predictions_sha256': '212563ef5afe0de07d25701d90f8982dfa44f347f8f3ffc97828134f7949f394'}
IDENTITIES = ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')
RICH_FIELDS = {*IDENTITIES, 'choices', 'bank_seal_sha256', 'candidate_scores', 'shared_theta_diagnostics'}
JOINT_FLAG = 'direct_history_diagnostic_holds_all_current_coefficients_fixed'
OLD_FLAG = 'projected_zero_residual_parent_choice_parity'
_require = numeric._require


def _exact(actual, expected, name):
    """Type-exact structural equality also supporting supplied tuple label keys."""
    _require(type(actual) is type(expected), name+' type differs')
    if type(expected) is dict:
        _require(set(actual) == set(expected), name+' fields differ')
        for key in expected: _exact(actual[key], expected[key], name+'.'+repr(key))
    elif type(expected) in (list, tuple):
        _require(len(actual) == len(expected), name+' length differs')
        for a, b in zip(actual, expected, strict=True): _exact(a, b, name+' item')
    else: _require(actual == expected, name+' differs')


def feature_configuration():
    return dict(kind='joint_raw_current_progress32_features_v1', arms=list(ARMS), dimension=4131,
        numeric_names=list(structural.numeric_names('C')), numeric_dimension=3, current_dimension=4099,
        progress_dimension=32, raw_current=structural._configuration('structural'),
        progress_version='statement_sample_centered_progress32_v1',
        progress_configuration_sha256=canonical_hash(old.feature_configuration()),
        numeric_scaling='own_stable_candidates_in_informative_prefixes_equal_user_prefix_candidate',
        scaler='StandardScaler_with_mean_False_once_shared_across_seven_arms',
        appended_progress='unchanged_accepted_float64_values_and_separately_preserved_bytes',
        whole_vector_normalization=False, learned_base_input=False, base_offset_present=False,
        pair_norm_upper_bound=None, pair_weight_mass=1900.)


def expected_spec():
    return dict(representation='joint_raw_current_progress32_features_v1', dimension=4131,
        feature_configuration_sha256=canonical_hash(feature_configuration()), model_kind=numeric.KIND)


def _close_tree(actual, expected, name):
    """Only numerical recomputations get1e-10; structural types stay strict."""
    _require(type(actual) is type(expected), name+' type differs')
    if type(expected) is float:
        numeric._close(actual, expected, name)
    elif type(expected) is dict:
        _require(set(actual) == set(expected), name+' fields differ')
        for key in expected: _close_tree(actual[key], expected[key], name+'.'+key)
    elif type(expected) in (list, tuple):
        _require(len(actual) == len(expected), name+' length differs')
        for a, b in zip(actual, expected, strict=True): _close_tree(a, b, name+' item')
    else: _require(actual == expected, name+' differs')


def input_fingerprint(inputs):
    body = capsule.encode_inputs(inputs)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
        allow_nan=False).encode('ascii')).hexdigest()


def _matrix_equal(a, b, name):
    """Exact canonical current-feature/pair values, including nonzero bits."""
    _require(sparse.isspmatrix_csr(a) and sparse.isspmatrix_csr(b) and a.shape == b.shape, name+' CSR shape differs')
    for attr in ('indptr', 'indices'):
        _require(np.array_equal(getattr(a, attr), getattr(b, attr)), name+' coordinates differ')
    _require(a.data.astype('<f8', copy=False).tobytes() == b.data.astype('<f8', copy=False).tobytes(), name+' data bytes differ')


def reconstruct(inputs, labels):
    """Own-training legacy reference plus independently enumerated progress pairs.

    The old training_data reference fits only its original three-column scaler;
    no ranking optimizer is invoked. Its4099/y/weights/scale/metadata are checked
    against separate enumeration before32 progress differences are appended.
    """
    train, held = capsule.scope(inputs)
    banks = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
    _require(type(labels) is dict, 'exact own labels mapping required')
    _exact(validate_core_labels(list(labels.values()), banks), labels, 'own labels')
    reference_x, reference_y, reference_w, reference_scale, reference_info = structural.training_data(
        list(train), banks, labels, 'C', 'structural', reference_pair_weight=1900.)
    raw = {}; rows = []; scaler_ids = []; records = []
    for ex in inputs.examples:
        n, h = structural.raw_features(ex.observation, (), inputs.banks[ex.bank_id], 'C', 'structural')
        supplied = inputs.raw_current[ex.bank_id]
        _matrix_equal(supplied.numeric, n, 'raw numeric'); _matrix_equal(supplied.hashed, h, 'raw hashed')
        raw[ex.bank_id] = (n, h)
    for ex in train:
        bank = banks[ex.bank_id]; ids = tuple(c.candidate_id for c in bank.candidates)
        keys = []
        for cid in ids:
            label = labels[ex.bank_id, cid]
            keys.append(None if label['status'] == 'unknown' else
                (int(label['all_ac']), int(label['loss'] == 0), label['gain']-label['loss']))
        stable = [i for i, key in enumerate(keys) if key is not None]
        pairs = [(a, b, int(keys[a] > keys[b])) for a, b in combinations(stable, 2) if keys[a] != keys[b]]
        if pairs: records.append((ex, ids, stable, pairs))
    _require(records, 'at least one original informative prefix required')
    per_user = Counter(ex.user_id for ex, *_ in records)
    scaler_weights = np.array([1/(per_user[ex.user_id]*len(stable))
        for ex, _, stable, _ in records for _ in stable], dtype=np.float64)
    scaler_raw = sparse.vstack([raw[ex.bank_id][0][stable] for ex, _, stable, _ in records], format='csr')
    legacy_scaler = StandardScaler(with_mean=False).fit(scaler_raw, sample_weight=scaler_weights)
    _require(np.array_equal(reference_scale, legacy_scaler.scale_), 'separate original scaler reference differs')
    current = {bid: sparse.hstack([legacy_scaler.transform(n), h], format='csr') for bid, (n, h) in raw.items()}
    targets = []; weights = []; current_rows = []; example_pairs = []
    progress_rows = {arm: [] for arm in ARMS}
    for ex, ids, stable, pairs in records:
        scaler_ids.extend((ex.bank_id, ids[i]) for i in stable)
        for a, b, target in pairs:
            rows.extend(((ex.bank_id, ids[a], ids[b]), (ex.bank_id, ids[b], ids[a])))
            example_pairs.extend((ex.example_id, ex.example_id)); targets.extend((target, 1-target))
            weights.extend([1/(per_user[ex.user_id]*len(pairs)*2)]*2)
            difference = current[ex.bank_id][a]-current[ex.bank_id][b]
            current_rows.extend((difference, -difference))
            for arm in ARMS:
                phi = np.zeros((len(ids), 32), dtype=np.float64) if arm == 'C_joint' else inputs.interactions[arm][ex.bank_id].matrix
                delta = phi[a]-phi[b]
                progress_rows[arm].extend((delta, -delta))
    y = np.asarray(targets, dtype=np.int64); w = np.asarray(weights, dtype=np.float64)
    w *= len(w)/w.sum(); old_mass = float(w.sum()); w = w*(1900./old_mass)
    current_pairs = sparse.vstack(current_rows, format='csr')
    _matrix_equal(current_pairs, reference_x, 'old current4099 pair reference')
    _require(y.tobytes() == reference_y.astype(np.int64).tobytes()
        and w.tobytes() == reference_w.tobytes(), 'exact original pair targets/weight bytes differ')
    users = {ex.user_id for ex in train}
    info = dict(train_prefixes=len(train), train_users=len(users), informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(train)-len(records), users=len(per_user),
        users_without_informative_prefix=len(users-set(per_user)), ordered_pairs=len(w), pair_example_ids=example_pairs,
        informative_train_example_ids=[ex.example_id for ex, *_ in records],
        uninformative_train_example_ids=sorted(set(ex.example_id for ex in train)-{ex.example_id for ex, *_ in records}),
        stable_train_candidates=len(scaler_ids), weight_normalization='fixed_reference_total_pair_weight',
        reference_pair_weight=1900., sample_weight_sum=float(w.sum()), prior_mean_one_weight_sum=old_mass)
    _exact(info, reference_info, 'independent natural metadata'); _exact(info, inputs.parent_training, 'own parent accounting')
    payload = dict(kind=SCALER_KIND, numeric_scale=reference_scale.tolist(), numeric_mean=legacy_scaler.mean_.tolist(),
        numeric_variance=legacy_scaler.var_.tolist(), scaler_candidate_ids=[list(k) for k in scaler_ids],
        scaler_weights=scaler_weights.tolist(), bank_candidate_ids=[[ex.bank_id, [c.candidate_id for c in banks[ex.bank_id].candidates]] for ex in train],
        row_keys=[list(k) for k in rows], y=y.tolist(), weights=w.tolist(), training=info)
    matrices = {arm: sparse.hstack([current_pairs, sparse.csr_matrix(np.asarray(progress_rows[arm]))], format='csr') for arm in ARMS}
    return dict(scaler=payload, current=current, matrices=matrices, y=y, weights=w, training=info,
        train=train, held=held, row_keys=rows)


def _candidate_matrix(inputs, data, bid, arm):
    n = data['current'][bid].shape[0]
    phi = np.zeros((n, 32), dtype=np.float64) if arm == 'C_joint' else inputs.interactions[arm][bid].matrix
    return sparse.hstack([data['current'][bid], sparse.csr_matrix(phi)], format='csr')


def _summary(matrix, weights):
    x = matrix.copy(); x.eliminate_zeros(); zero = np.asarray(x.getnnz(axis=1)).ravel() == 0
    return dict(mirrored_rows=len(weights), stable_unequal_pairs=len(weights)//2,
        exact_zero_difference_rows=int(zero.sum()), exact_zero_difference_natural_weight_mass=math.fsum(map(float, weights[zero])),
        natural_weight_mass=math.fsum(map(float, weights)), zero_difference_pairs_retained=True)


def _contract(value, inputs):
    numeric._fields(value, {'expected_sha256', 'expected_fold_assignment_sha256', 'expected_source_binding_sha256'}, 'own contract')
    _require(all(numeric._sha(v) for v in value.values()) and value['expected_fold_assignment_sha256'] == inputs.fold_assignment_sha256,
        'externally expected own label contract differs')


def verify_fold(inputs, models, scaler, predictions, labels, *, expected_input_fingerprint, expected_label_contract, expected_runtime):
    body = capsule.encode_inputs(inputs)
    _exact(body['configuration']['features'], feature_configuration(), 'independent feature configuration')
    _require(numeric._sha(expected_input_fingerprint) and input_fingerprint(inputs) == expected_input_fingerprint,
        'external own capsule fingerprint differs')
    _contract(expected_label_contract, inputs)
    _require(type(models) is dict and set(models) == set(ARMS), 'all seven models required')
    data = reconstruct(inputs, labels)
    # Saved scaling/pair plans are exact same original operations, not reassociated scores.
    _exact(scaler, data['scaler'], 'independent SCALER payload')
    transform_sha = canonical_hash(scaler); theta = {}; certificates = {}
    for arm in ARMS:
        model = models[arm]
        numeric._fields(model, {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint',
            'label_contract', 'parent_structure_model_sha256', 'readiness_complete_sha256', 'transform_sha256',
            'training', 'pair_summary', 'joint_model', 'model_sha256'}, 'own joint model')
        expected = dict(kind=MODEL_KIND, arm=arm, fold=inputs.fold,
            train_example_ids=[ex.example_id for ex in data['train']], held_example_ids=[ex.example_id for ex in data['held']],
            input_fingerprint=expected_input_fingerprint, label_contract=expected_label_contract,
            parent_structure_model_sha256=inputs.parent_structure_model_sha256,
            readiness_complete_sha256=inputs.readiness_complete_sha256, transform_sha256=transform_sha, training=data['training'])
        for key in expected: _exact(model[key], expected[key], 'model.'+key)
        _require(model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'model wrapper SHA differs')
        _exact(model['pair_summary'], _summary(data['matrices'][arm], data['weights']), 'zero-pair diagnostics')
        _exact(model['joint_model']['runtime'], expected_runtime, 'external numerical runtime')
        certificates[arm] = numeric.audit_model(model['joint_model'], data['matrices'][arm], data['y'], data['weights'], expected_spec())
        theta[arm] = np.asarray(model['joint_model']['coefficients'], dtype=np.float64)
        start = 4099 if arm == 'C_joint' else 4115 if arm == 'CF' else 4131
        _require(not np.any(theta[arm][start:]) and not np.any(model['joint_model']['final_gradient'][start:]), 'nested zero columns differ')
    _require(type(predictions) is list and [p.get('example_id') for p in predictions] == [ex.example_id for ex in data['held']],
        'complete ordered own held predictions required')
    maximum_error = 0.
    for ex, prediction, parent in zip(data['held'], predictions, inputs.parent_predictions, strict=True):
        numeric._fields(prediction, RICH_FIELDS | {JOINT_FLAG}, 'rich joint prediction')
        _require(prediction[JOINT_FLAG] is True, 'full-coefficient shared diagnostic flag required')
        bank = inputs.banks[ex.bank_id]; ids = tuple(c.candidate_id for c in bank.candidates)
        for key, value in dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
                problem_id=bank.problem_id, fold=inputs.fold, bank_seal_sha256=bank.seal_sha256).items():
            _exact(prediction[key], value, 'prediction.'+key)
        numeric._fields(prediction['choices'], METHODS, 'fourteen choices')
        numeric._fields(prediction['candidate_scores'], METHODS, 'fourteen score maps')
        choices = {}; scores = {}
        for method, arm, fitted in [*((a, a, a) for a in ARMS), *((m, a, 'H') for m, a in zip(DIAGNOSTICS, ('HS', 'Jm', 'CF')))]:
            replay = numeric.audit_scores(theta[fitted], _candidate_matrix(inputs, data, ex.bank_id, arm), ids,
                prediction['candidate_scores'][method])
            choices[method] = replay['selected_candidate_id']; scores[method] = replay['recomputed_scores']
            maximum_error = max(maximum_error, replay['maximum_score_recompute_difference'])
        noop = hashlib.sha256(bank.current_source).hexdigest(); first = bank.attempts[0]
        first_id = hashlib.sha256(first.source).hexdigest() if first.status == 'success' else noop
        for method in BASELINES[:2]:
            scores[method] = dict(parent['candidate_scores'][method])
            _exact(prediction['candidate_scores'][method], scores[method], 'own held frozen baseline score')
            choices[method] = min(ids, key=lambda cid: (-scores[method][cid], cid))
            _exact(choices[method], parent['choices'][method], 'frozen baseline choice')
        for method, cid in (('noop', noop), ('first_attempt', first_id)):
            scores[method] = {c: float(c == cid) for c in ids}; choices[method] = cid
            _exact(prediction['candidate_scores'][method], scores[method], 'deterministic baseline score')
        _exact(prediction['choices'], choices, 'exact score-selected identities')
        diagnostics = {}
        for arm in ('HS', 'Jm', 'CF'):
            control = 'shared_H_'+arm
            identical = np.array_equal(inputs.interactions['H'][ex.bank_id].matrix, inputs.interactions[arm][ex.bank_id].matrix)
            _require(not identical or choices['H'] == choices[control], 'identical features changed shared choice')
            a, b = choices['H'], choices[control]
            diagnostics[arm] = dict(features_identical_exact=identical, choice_changed=a != b,
                transition='same' if a == b else 'to_noop' if a == noop else 'from_noop' if b == noop else 'edited_to_edited',
                score_difference={cid: scores['H'][cid]-scores[control][cid] for cid in ids})
        _close_tree(prediction['shared_theta_diagnostics'], diagnostics, 'shared all-H diagnostics')
    _require(math.isfinite(maximum_error), 'finite maximum score replay error required')
    return dict(fold=inputs.fold, verified_models=7, train_prefixes=len(data['train']), held_prefixes=len(data['held']),
        maximum_score_recompute_difference=maximum_error, transform_sha256=transform_sha, numerical_certificates=certificates)


def _cell(rows, labels, method):
    chosen = [labels[r['bank_id'], r['choices'][method]] for r in rows]; n = len(rows)
    a = sum(x['status'] == 'stable' and x['all_ac'] for x in chosen)
    r = sum(x['status'] == 'stable' and x['loss'] > 0 for x in chosen); u = sum(x['status'] == 'unknown' for x in chosen)
    return dict(examples=n, evaluable=bool(n), counts=dict(stable_ac=a, stable_regression=r, unknown=u,
        noop_selected=sum(row['choices'][method] == row['choices']['noop'] for row in rows)),
        fractions=dict(zip(METRICS, (Fraction(k, n) for k in (a, a+u, r, r+u)))) if n else None)


def _group(rows, labels, methods):
    pids = sorted({r['problem_id'] for r in rows})
    problems = {pid: {m: _cell([r for r in rows if r['problem_id'] == pid], labels, m) for m in methods} for pid in pids}
    return dict(examples=len(rows), problems=len(pids), results={m: _cell(rows, labels, m) for m in methods}, problem_results=problems,
        equal_problem={m: {k: sum((problems[pid][m]['fractions'][k] for pid in pids), Fraction())/len(pids) for k in METRICS}
            for m in methods} if pids else None)


def _switches(rows, labels, control):
    result = dict(examples=len(rows), selected_candidate_changed=0, ac_gained=0, ac_lost=0, regression_prevented=0,
        regression_introduced=0, not_jointly_known=0, edited_to_edited=0, to_noop=0, from_noop=0)
    for row in rows:
        a, b, noop = (row['choices'][m] for m in ('H', control, 'noop'))
        if a != b:
            result['selected_candidate_changed'] += 1
            result['to_noop' if a == noop else 'from_noop' if b == noop else 'edited_to_edited'] += 1
        la, lb = labels[row['bank_id'], a], labels[row['bank_id'], b]
        if la['status'] == 'unknown' or lb['status'] == 'unknown': result['not_jointly_known'] += 1
        else:
            result['ac_gained'] += la['all_ac'] and not lb['all_ac']; result['ac_lost'] += lb['all_ac'] and not la['all_ac']
            result['regression_prevented'] += la['loss'] == 0 and lb['loss'] > 0
            result['regression_introduced'] += la['loss'] > 0 and lb['loss'] == 0
    return result


def _groups(predictions, labels):
    groups = {k: [] for k in ('known_ac', 'known_nonac', 'unknown')}
    for row in predictions:
        current = labels[row['bank_id'], row['choices']['noop']]
        groups['unknown' if current['status'] == 'unknown' else 'known_ac' if current['all_ac'] else 'known_nonac'].append(row)
    return groups


def independent_assessment(cohort, predictions, labels):
    _require(type(predictions) is list and all(type(p) is dict and type(p.get('choices')) is dict
        and set(p['choices']) == set(METHODS) for p in predictions), 'exact fourteen methods required')
    projected = [{**p, 'choices': {m: p['choices'][m] for m in old.METHODS}} for p in predictions]
    inherited = old.independent_assessment(cohort, projected, labels)
    by_id = {r['example_id']: r for r in cohort}
    _require(all(type(p['choices']['C_joint']) is str and p['choices']['C_joint'] in by_id[p['example_id']]['candidate_ids']
        for p in predictions), 'exact C_joint candidate required')
    full = _group(predictions, labels, METHODS)
    folds = {str(f): _group([p for p in predictions if p['fold'] == f], labels, METHODS) for f in range(5)}
    rows = _groups(predictions, labels); groups = {k: _group(v, labels, METHODS) for k, v in rows.items()}
    subfolds = {k: {str(f): _group([p for p in v if p['fold'] == f], labels, METHODS) for f in range(5)} for k, v in rows.items()}
    def compare(group, strict=True):
        if not group['examples']: return dict(evaluable=False, passed=False, checks={})
        checks = {}
        for name, view in (('pooled', {m: cell['fractions'] for m, cell in group['results'].items()}), ('equal_problem', group['equal_problem'])):
            a, b = view['H'], view['C_joint']
            checks[name+'_ac'] = a['ac_lower'] > b['ac_lower'] if strict else a['ac_lower'] >= b['ac_lower']
            for key in ('regression_lower', 'regression_upper'): checks[name+'_'+key] = a[key] <= b[key]
        return dict(evaluable=True, passed=all(checks.values()), checks=checks)
    a, b, c = compare(full), compare(groups['known_nonac']), compare(groups['known_ac'], False)
    nonworse = sum(f['results']['H']['fractions']['ac_lower'] >= f['results']['C_joint']['fractions']['ac_lower'] for f in folds.values())
    matched = dict(full_check=a, known_nonac_check=b, known_ac_check=c, nonworse_full_folds=nonworse,
        required_nonworse_folds=4, passed=bool(a['passed'] and b['passed'] and c['passed'] and nonworse >= 4))
    gate = dict(inherited['gate']); gate.update(inherited_progress_gates_passed=inherited['gate']['passed'],
        joint_current_contribution=matched['passed'], joint_current_check=matched, passed=bool(inherited['gate']['passed'] and matched['passed']))
    return old._serialize(dict(kind='joint_current_progress4131_repair_gate_v1', primary='H', methods=list(METHODS),
        full=full, folds=folds, current_status_subgroups=groups, current_status_subgroup_folds=subfolds,
        primary_transitions={m: _switches(predictions, labels, m) for m in METHODS if m != 'H'}, gate=gate,
        inherited_progress_gate=inherited['gate'], original_gate=inherited['original_gate'], exclusions=0,
        note='Adaptive fixed-bank development; all inherited repair, mechanism and CF gates '
            'AND the same-solver C_joint comparison. No causal learning benefit or fitting authorization.'))


def independent_architecture(cohort, predictions, old_predictions, labels, pins, synthetic):
    _require(type(pins) is dict and set(pins) == set(REFERENCE_PINS) and all(numeric._sha(v) for v in pins.values())
        and (synthetic or pins == REFERENCE_PINS), 'mandatory fixed old architecture pins required')
    _require(type(old_predictions) is list, 'mandatory complete old rich predictions required')
    # Reuse independent old13 population/choice/label checks, not producer report.
    old.independent_assessment(cohort, old_predictions, labels)
    by_id = {p['example_id']: p for p in old_predictions}; new = {p['example_id']: p for p in predictions}
    paired = []; references = []
    for row in cohort:
        p, previous = new[row['example_id']], by_id[row['example_id']]
        numeric._fields(previous, RICH_FIELDS | {OLD_FLAG}, 'old rich prediction')
        _require(previous[OLD_FLAG] is True and numeric._sha(previous['bank_seal_sha256'])
            and previous['bank_seal_sha256'] == p['bank_seal_sha256'], 'exact old/new bank seal required')
        numeric._fields(previous['candidate_scores'], old.METHODS, 'old13 score maps')
        ids = row['candidate_ids']
        for method in old.METHODS:
            scores = previous['candidate_scores'][method]; numeric._fields(scores, ids, 'old full candidate score')
            _require(all(numeric._number(v) for v in scores.values())
                and previous['choices'][method] == min(ids, key=lambda cid: (-scores[cid], cid)), 'old exact SHA score choice differs')
        numeric._fields(previous['shared_theta_diagnostics'], ('HS', 'Jm', 'CF'), 'old shared diagnostics')
        for arm in ('HS', 'Jm', 'CF'):
            d = previous['shared_theta_diagnostics'][arm]; control = 'shared_H_'+arm
            numeric._fields(d, {'features_identical_exact', 'choice_changed', 'transition', 'score_difference'}, 'old shared detail')
            _require(type(d['features_identical_exact']) is bool and type(d['choice_changed']) is bool, 'old diagnostic booleans required')
            a, b = previous['choices']['H'], previous['choices'][control]
            transition = 'same' if a == b else 'to_noop' if a == row['noop_candidate_id'] else 'from_noop' if b == row['noop_candidate_id'] else 'edited_to_edited'
            _exact(d['choice_changed'], a != b, 'old change'); _exact(d['transition'], transition, 'old transition')
            numeric._fields(d['score_difference'], ids, 'old score difference')
            _require(all(numeric._number(d['score_difference'][cid]) and d['score_difference'][cid] ==
                previous['candidate_scores']['H'][cid]-previous['candidate_scores'][control][cid] for cid in ids), 'old score difference invalid')
            _require(not d['features_identical_exact'] or (previous['candidate_scores']['H'] == previous['candidate_scores'][control] and a == b),
                'old identical-feature invariant differs')
        paired.append({**{k: row[k] for k in IDENTITIES}, 'choices': dict(H=p['choices']['H'], joint_H=p['choices']['H'],
            progress32_H=previous['choices']['H'], noop=row['noop_candidate_id'])})
        references.append({**{k: row[k] for k in IDENTITIES}, 'bank_seal_sha256': p['bank_seal_sha256'],
            'candidate_ids': list(ids), 'noop_candidate_id': row['noop_candidate_id'],
            'joint_H': dict(choice=p['choices']['H'], candidate_scores=dict(p['candidate_scores']['H'])),
            'progress32_H': dict(choice=previous['choices']['H'], candidate_scores=dict(previous['candidate_scores']['H']))})
    methods = ('joint_H', 'progress32_H')
    def group(rows):
        result = _group(rows, labels, methods)
        result['delta_joint_minus_progress32'] = None if not rows else dict(
            pooled={k: result['results']['joint_H']['fractions'][k]-result['results']['progress32_H']['fractions'][k] for k in METRICS},
            equal_problem={k: result['equal_problem']['joint_H'][k]-result['equal_problem']['progress32_H'][k] for k in METRICS})
        result['paired_switches'] = _switches(rows, labels, 'progress32_H')
        return result
    groups = _groups(paired, labels)
    return old._serialize(dict(kind='joint_vs_sealed_progress32_H_diagnostic_v1', gate_effect='none', primary_gate_effect='none',
        model_promotion=False, confirmatory=False, causal_base_failure_established=False, educational_benefit_established=False,
        synthetic=synthetic, exclusions=0, architecture_columns=list(methods), original_primary_method_count=14,
        additional_scored_primary_methods=0, population=dict(examples=len(cohort), problems=len({r['problem_id'] for r in cohort}),
            candidates=sum(len(r['candidate_ids']) for r in cohort), folds=5), reference_pins=dict(pins),
        supplied_joint_predictions_canonical_content_sha256=canonical_hash(predictions),
        supplied_old_predictions_canonical_content_sha256=canonical_hash(old_predictions),
        external_raw_reference_authentication='caller_required_not_established_by_this_pure_function', full=group(paired),
        folds={str(f): group([p for p in paired if p['fold'] == f]) for f in range(5)},
        current_status_subgroups={k: group(v) for k, v in groups.items()},
        current_status_subgroup_folds={k: {str(f): group([p for p in v if p['fold'] == f]) for f in range(5)} for k, v in groups.items()},
        score_references=references, note='Non-promotable paired architecture diagnostic on all retained recipients. Joint changes current '
            'coefficients and the regularized parameter space; differences do not identify why the earlier '
            'fixed-offset model failed. Unknown bounds are not confidence intervals. No gate is replaced.'))


def audit_run(fold_inputs, fold_models, scaler_payloads, predictions, train_labels_by_fold, assessment_labels, report, *,
              old_predictions, reference_pins, expected_input_fingerprint, expected_label_contracts, expected_runtime,
              expected_predictions_complete_sha256, synthetic=False):
    """All35/14 complete reconstruction; absence of any obligation fails closed."""
    _require(type(synthetic) is bool, 'explicit synthetic boolean required')
    numeric._fields(expected_runtime, {'python', 'numpy', 'scipy'}, 'external runtime')
    _require(all(type(v) is str and v for v in expected_runtime.values()), 'runtime strings required')
    _require(numeric._sha(expected_predictions_complete_sha256), 'external all35 prediction barrier pin required')
    for mapping in (fold_inputs, fold_models, scaler_payloads, train_labels_by_fold, expected_input_fingerprint, expected_label_contracts):
        _require(type(mapping) is dict and set(mapping) == set(range(5)) and all(type(k) is int for k in mapping), 'exact all-five-fold maps required')
    first = fold_inputs[0]; common = capsule.encode_inputs(first)
    _require(first.synthetic is synthetic, 'capsule and audit synthetic scope differ')
    cohort = capsule.validate_inputs(first); ids = [r['example_id'] for r in cohort]
    if not synthetic:
        _require(len(cohort) == 320 and len({r['problem_id'] for r in cohort}) == 23
            and sum(len(r['candidate_ids']) for r in cohort) == 2544, 'unchanged320/23/2544 required')
    _require(type(predictions) is list and all(type(p) is dict and 'example_id' in p for p in predictions)
        and len(predictions) == len(ids) and len({p['example_id'] for p in predictions}) == len(ids)
        and {p['example_id'] for p in predictions} == set(ids), 'complete unique held predictions required')
    _require(type(assessment_labels) is dict, 'all-candidate assessment mapping required')
    _exact(validate_core_labels(list(assessment_labels.values()), first.banks), assessment_labels, 'full assessment labels')
    by_id = {p['example_id']: p for p in predictions}; results = []
    for f in range(5):
        inputs = fold_inputs[f]
        _require(type(inputs) is capsule.FoldInputs and type(inputs.fold) is int and inputs.fold == f, 'own capsule fold differs')
        body = capsule.encode_inputs(inputs)
        for key in set(common)-{'fold', 'parent_predictions', 'parent_training', 'parent_structure_model_sha256'}:
            _exact(body[key], common[key], 'common source-only projection.'+key)
        _contract(expected_label_contracts[f], inputs)
        _require(expected_label_contracts[f]['expected_source_binding_sha256'] == expected_label_contracts[0]['expected_source_binding_sha256'],
            'common label provenance differs')
        train, held = capsule.scope(inputs); bids = {ex.bank_id for ex in train}
        _exact(train_labels_by_fold[f], {k: v for k, v in assessment_labels.items() if k[0] in bids}, 'own training/assessment label equality')
        results.append(verify_fold(inputs, fold_models[f], scaler_payloads[f], [by_id[ex.example_id] for ex in held], train_labels_by_fold[f],
            expected_input_fingerprint=expected_input_fingerprint[f], expected_label_contract=expected_label_contracts[f], expected_runtime=expected_runtime))
    expected = independent_assessment(cohort, predictions, assessment_labels)
    extras = {'completed_fits', 'full_train_refits', 'model_promotion', 'predictions_complete_sha256',
        'shared_theta_diagnostics', 'architecture_diagnostic'}
    numeric._fields(report, set(expected) | extras, 'complete joint assessment report')
    _exact({k: report[k] for k in expected}, expected, 'exact Fraction primary assessment')
    _exact(report['completed_fits'], 35, 'fit count'); _exact(report['full_train_refits'], 0, 'no full refit')
    _exact(report['model_promotion'], False, 'no promotion')
    _exact(report['predictions_complete_sha256'], expected_predictions_complete_sha256, 'external prediction barrier')
    _exact(report['shared_theta_diagnostics'], old.shared_diagnostics(predictions), 'all shared-coefficient strata')
    architecture = independent_architecture(cohort, predictions, old_predictions, assessment_labels, reference_pins, synthetic)
    _exact(report['architecture_diagnostic'], architecture, 'mandatory non-promotable old-H diagnostic')
    maximum = max(r['maximum_score_recompute_difference'] for r in results)
    _require(math.isfinite(maximum), 'finite reported maximum error required')
    return dict(verified=True, recipients=len(cohort), models=35, methods=14, feature_dimension=4131, folds=results,
        gate=expected['gate'], architecture_verified=True, scaler_and_pair_metadata_verified=True,
        maximum_score_recompute_difference=maximum, synthetic=synthetic, fitting_performed=False, fitting_authorized=False,
        model_optimization_performed=False, own_training_scaler_reconstruction_performed=True,
        external_provenance_guard_required=True, source_runtime_raw_artifact_provenance_verified=False,
        accepted_progress32_feedback_ancestry_verified=False, actual_intermediate_newton_execution_verified=False,
        complete_experiment_label_opening_barrier_verified=False,
        numerical_tolerance=dict(atol=1e-10, rtol=1e-10, strict_gradient_limit=1e-8, selected_SHA_exact=True),
        reuse=dict(capsule='serialization_and_structural_contract_only', current='frozen_prejoint_structural_reference',
            scaler='original_weighted_sklearn_StandardScaler', numerical='separate_scalar_4131_auditor',
            primary_gate='old_independent13_plus_independently_recomputed_C_joint', architecture='separate_fraction_reconstruction'))
