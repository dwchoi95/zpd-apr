"""Pure independent progress32 audit; no I/O, fitting, execution or release.

The already independently audited readiness vectors are external authority,
not recomputed from samples here. Capsule serialization/structural validation,
core-label validation, and dimension-free OLD INDEPENDENT audit helpers are
shared. Producer pair builders, numerical objectives/solvers/scorers, and
assessment functions are never called. The caller authenticates artifact bytes,
readiness/base projection, label envelopes, and the all30 prediction barrier.

Scalar loss/gradient use fsum; numerical metadata tolerance is 1e-10, while all
hashes, rational numerators/denominators, choices, and the <=1e-8 convergence
boundary are exact. Unrecorded Newton iterate vectors cannot be replayed.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
import re

import numpy as np
from scipy import sparse

from scripts.zpd_repair_progress_capsule import FoldInputs, encode_inputs
from scripts.zpd_repair_feedback_labels import validate_core_labels
from scripts.audit_zpd_repair_directed_independent import (
    _require, _number, _equal, _exact, _array, _vector, _sha_arrays)
from scripts.audit_zpd_repair_feedback_cv import independent_assessment as old_independent_assessment
from src.repair.pilot_contracts import canonical_hash

ARMS = ('H', 'Jm', 'HS', 'U', 'L', 'CF')
BASELINES = ('structural_C', 'lexical_C', 'first_attempt')
DIAGNOSTICS = ('shared_H_HS', 'shared_H_Jm', 'shared_H_CF')
METHODS = (*ARMS, *BASELINES, *DIAGNOSTICS, 'noop')
OLD_METHODS = tuple(m for m in METHODS if m not in ('CF', 'shared_H_CF'))
METRICS = ('ac_lower', 'ac_upper', 'regression_lower', 'regression_upper')
DIMENSION = 32
ATOL = RTOL = 1e-10
GRADIENT_LIMIT = 1e-8
MODEL_KIND = 'statement_progress32_fold_offset_v1'


def feature_configuration():
    return dict(version='statement_sample_centered_progress32_v1', dimension=32,
        arms=list(ARMS), states=['00', '01', '10', '11'],
        scale_divisor='binary64_math.sqrt(12.0)', layout='concat_current16_centered16_C_order',
        weightings=['uniform', 'reciprocal_recency'], directions=['same', 'reverse'],
        arithmetic='signed_integer_counts_then_float64_division_math.fsum_binary64_terms',
        masks='full_sample_stable_current_and_both_endpoints_and_AST_available',
        current_control='common_authentic_static_alignment_current_feedback_G_plus_zero_tail',
        unknown='unavailable_never_zero_test_failure', maximum_candidate_l2=2.**-.5,
        maximum_pair_l2=1.0, fitting_performed=False, execution_performed=False,
        feature_authority='caller_must_authenticate_separate_replay_seals')


def expected_spec():
    return dict(representation='statement_sample_centered_progress32_v1', dimension=32,
        feature_configuration_sha256=canonical_hash(feature_configuration()),
        model_kind='fixed_repair_progress_offset_newton_v1')


def expected_configuration():
    return dict(kind='fixed_repair_progress_offset_newton_v1', dimension=32, representation=expected_spec(),
        C=.1, mirrored_row_mass=1900., mass_rtol=1e-12, mass_atol=1e-12,
        intercept=0., fixed_base_margin_coefficient=1., labels='integer_0_1_signed_as_2y_minus_1',
        row_contract='adjacent_exact_feature_offset_label_mirrors_equal_positive_weights',
        matrix_arithmetic='canonical_float64_CSR', regularization='half_squared_L2_interaction_only',
        initialization='all_zero', optimizer='analytic_damped_newton_cholesky_v1',
        hessian='I_plus_C_XT_diag_w_sigmoid_z_sigmoid_minus_z_X',
        hessian_symmetrization='0.5_times_H_plus_0.5_times_H_transpose',
        linear_solver='Cholesky_lower_then_two_triangular_solves_no_inverse',
        damping='min_1_log1p_r_times_a_div_q_div_r_else_min_1_a_div_q',
        max_updates=2000, max_loop_evaluations=2001, max_hessian_evaluations=2000,
        max_linear_solves=2000, max_final_checks=1, max_total_evaluations=2002,
        loop_gradient_infinity_limit=1e-8, final_gradient_infinity_limit=1e-8,
        normalized_solve_residual_limit=1e-12, objective_end_check_relative_allowance=1e-12,
        line_search=False, jitter=False, iterative_refinement=False, retries=0, base_margin_optimized=False)


def _digest(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def input_fingerprint(inputs):
    # Shared byte-preserving capsule serialization only, never fitted arithmetic.
    return hashlib.sha256(json.dumps(encode_inputs(inputs), sort_keys=True,
        separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


def reconstruct_pairs(examples, banks, labels, interactions, base_scores):
    """Independent legacy preference, candidate order and natural mass1900."""
    ids = [e.example_id for e in examples]; bids = [e.bank_id for e in examples]
    _require(examples and len(ids) == len(set(ids)) and len(bids) == len(set(bids))
        and all(e.split == 'train' for e in examples), 'unique training prefixes required')
    for mapping in (banks, interactions, base_scores):
        _require(type(mapping) is dict and set(mapping) == set(bids), 'exact training bank scope required')
    _require(type(labels) is dict and all(type(v) is dict and (v.get('bank_id'), v.get('candidate_id')) == k
        for k, v in labels.items()), 'core label identity differs')
    core = validate_core_labels(list(labels.values()), banks)
    _exact(labels, core, 'exact own training labels')
    records = []; diagnostics = []
    for ex in examples:
        bank = banks[ex.bank_id]; block = interactions[ex.bank_id]; candidates = bank.candidates
        cids = tuple(c.candidate_id for c in candidates)
        _require(bank.current_source == ex.observation.current.source and bank.problem_id == ex.observation.problem_id,
            'training observation-bank identity differs')
        _require(block.candidate_ids == cids and type(base_scores[ex.bank_id]) is dict
            and set(base_scores[ex.bank_id]) == set(cids) and all(_number(v) for v in base_scores[ex.bank_id].values()),
            'exact candidate order and finite fixed base scores required')
        _array(block.matrix, (len(cids), 32), 'float64', 'interaction')
        preference = []
        for cid in cids:
            lab = core[ex.bank_id, cid]
            preference.append(None if lab['status'] == 'unknown' else
                (int(lab['all_ac']), int(lab['loss'] == 0), lab['gain']-lab['loss']))
        stable = sum(p is not None for p in preference)
        pairs = [(i, j, int(preference[i] > preference[j])) for i in range(len(cids)) for j in range(i+1, len(cids))
            if preference[i] is not None and preference[j] is not None and preference[i] != preference[j]]
        if pairs: records.append((ex, pairs, stable))
        row = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            bank_seal_sha256=bank.seal_sha256, problem_id=bank.problem_id, candidate_ids=list(cids),
            is_noop=[c.is_noop for c in candidates], candidate_statuses=[core[ex.bank_id, cid]['status'] for cid in cids],
            candidate_count=len(cids), stable_candidates=stable, unknown_candidates=len(cids)-stable,
            pairs_with_unknown=len(cids)*(len(cids)-1)//2-stable*(stable-1)//2,
            stable_tied_pairs=stable*(stable-1)//2-len(pairs), informative_unordered_pairs=len(pairs))
        informative = {(i, j) for i, j, _ in pairs}
        for name, filtered in (('all_pair_counts', False), ('informative_pair_counts', True)):
            counts = dict(unordered_pairs=0, noop_edited_pairs=0, edited_edited_pairs=0,
                interaction_varying_pairs=0, zero_interaction_pairs=0, nonzero_base_margin_pairs=0)
            for i in range(len(cids)):
                for j in range(i+1, len(cids)):
                    if filtered and (i, j) not in informative: continue
                    diff = block.matrix[i]-block.matrix[j]
                    counts['unordered_pairs'] += 1
                    counts['noop_edited_pairs' if candidates[i].is_noop or candidates[j].is_noop else 'edited_edited_pairs'] += 1
                    counts['interaction_varying_pairs'] += int(np.max(np.abs(diff)) > 1e-12)
                    counts['zero_interaction_pairs'] += int(not np.any(diff))
                    counts['nonzero_base_margin_pairs'] += int(float(base_scores[ex.bank_id][cids[i]]) != float(base_scores[ex.bank_id][cids[j]]))
            row[name] = counts
        diagnostics.append(row)
    _require(records, 'no informative stable pairs')
    prefixes = Counter(e.user_id for e, _, _ in records)
    x = []; y = []; w = []; margin = []; pair_examples = []; pair_candidates = []
    for ex, pairs, _ in records:
        block = interactions[ex.bank_id]; base = base_scores[ex.bank_id]
        for i, j, target in pairs:
            a, b = block.candidate_ids[i], block.candidate_ids[j]
            diff = block.matrix[i]-block.matrix[j]; offset = float(base[a])-float(base[b])
            x.extend((diff, -diff)); y.extend((target, 1-target)); margin.extend((offset, -offset))
            w.extend([1/(prefixes[ex.user_id]*len(pairs)*2)]*2)
            pair_examples.extend([ex.example_id]*2); pair_candidates.extend([[a, b], [b, a]])
    weights = np.asarray(w, dtype=np.float64)
    weights *= len(weights)/weights.sum(); old_mass = float(weights.sum()); weights = weights*(1900./old_mass)
    informative = [e.example_id for e, _, _ in records]; users = {e.user_id for e in examples}
    training = dict(train_prefixes=len(examples), train_users=len(users), informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(examples)-len(records), users=len(prefixes), users_without_informative_prefix=len(users-set(prefixes)),
        ordered_pairs=len(weights), pair_example_ids=pair_examples, informative_train_example_ids=informative,
        uninformative_train_example_ids=sorted(set(ids)-set(informative)), stable_train_candidates=sum(n for _, _, n in records),
        weight_normalization='fixed_reference_total_pair_weight', reference_pair_weight=1900.,
        sample_weight_sum=float(weights.sum()), prior_mean_one_weight_sum=old_mass)
    metadata = dict(kind='fixed_train_only_residual_pairs_v1', preference='legacy_stable_lexicographic_all_ac_loss_zero_net_gain',
        no_pair_filter_by_feature_variation=True, fixed_base_coefficient=1., intercept=0., training=training,
        banks=diagnostics, pair_candidate_ids=pair_candidates, spec=expected_spec(), diagnostic_variation_tolerance=1e-12)
    for name in ('all_pair_counts', 'informative_pair_counts'):
        metadata[name] = {k: sum(row[name][k] for row in diagnostics) for k in diagnostics[0][name]}
    matrix = np.stack(x); zero = ~np.any(matrix != 0., axis=1)
    summary = dict(mirrored_rows=len(y), stable_unequal_pairs=len(y)//2,
        exact_zero_difference_rows=int(zero.sum()), exact_zero_difference_natural_weight_mass=math.fsum(map(float, weights[zero])),
        natural_weight_mass=math.fsum(map(float, weights)), zero_difference_pairs_retained=True)
    return dict(matrix=matrix, y=np.asarray(y, dtype=np.int64), weights=weights,
        base_margin=np.asarray(margin, dtype=np.float64), metadata=metadata, summary=summary, training=training)


def numerical_reference(theta, x, y, weights, offset):
    """Scalar stable logistic objective/gradient; no producer numerical calls."""
    _array(theta, (32,), 'float64', 'theta')
    _require(type(x) is np.ndarray and x.ndim == 2 and len(x) > 0, 'nonempty matrix required')
    n = len(x); _array(x, (n, 32), 'float64', 'matrix')
    _array(y, (n,), 'int64', 'labels'); _array(weights, (n,), 'float64', 'weights'); _array(offset, (n,), 'float64', 'offset')
    _require(n % 2 == 0 and np.isin(y, [0, 1]).all() and (weights > 0).all()
        and math.isclose(math.fsum(weights), 1900., rel_tol=1e-12, abs_tol=1e-12), 'invalid pair labels/mass')
    _require(np.array_equal(x[::2], -x[1::2]) and np.array_equal(y[::2], 1-y[1::2])
        and np.array_equal(weights[::2], weights[1::2]) and np.array_equal(offset[::2], -offset[1::2]), 'mirrored pair contract differs')
    csr = sparse.csr_matrix(x); csr.eliminate_zeros(); csc = csr.tocsc()
    factors = []; losses = []; initial_losses = []
    for i in range(n):
        lo, hi = csr.indptr[i:i+2]
        dot = math.fsum(float(v)*float(theta[j]) for v, j in zip(csr.data[lo:hi], csr.indices[lo:hi]))
        sign = 2*int(y[i])-1; z = sign*(float(offset[i])+dot)
        _require(math.isfinite(z), 'nonfinite scalar margin')
        sigmoid = math.exp(-z)/(1+math.exp(-z)) if z >= 0 else 1/(1+math.exp(z))
        factors.append(.1*float(weights[i])*sign*sigmoid)
        losses.append(.1*float(weights[i])*(max(0., -z)+math.log1p(math.exp(-abs(z)))))
        z0 = sign*float(offset[i]); initial_losses.append(.1*float(weights[i])*(max(0., -z0)+math.log1p(math.exp(-abs(z0)))))
    gradient = np.empty(32, dtype=np.float64)
    for j in range(32):
        lo, hi = csc.indptr[j:j+2]
        gradient[j] = float(theta[j])-math.fsum(float(v)*factors[i] for v, i in zip(csc.data[lo:hi], csc.indices[lo:hi]))
    squares = [math.fsum(float(v)*float(v) for v in row) for row in x]
    weighted = math.fsum(float(w)*q for w, q in zip(weights, squares)); penalty = .5*math.fsum(float(t)*float(t) for t in theta)
    training = dict(rows=n, unordered_pairs=n//2, positive_rows=int(y.sum()), zero_difference_rows=int((np.diff(csr.indptr) == 0).sum()),
        weight_mass=math.fsum(weights), maximum_row_squared_norm=max(squares), weighted_row_squared_norm_sum=weighted,
        strong_convexity_lower_bound=1., hessian_spectral_upper_bound=1.+.025*weighted,
        input_sha256=dict(features=_sha_arrays(np.asarray(csr.shape, dtype='<i8'), csr.indptr.astype('<i8'), csr.indices.astype('<i8'), csr.data.astype('<f8')),
            labels=_sha_arrays(y.astype('<i8')), weights=_sha_arrays(weights.astype('<f8')), base_margin=_sha_arrays(offset.astype('<f8'))))
    data_loss = math.fsum(losses)
    return dict(initial_objective=math.fsum(initial_losses), objective=data_loss+penalty, weighted_logistic_loss=data_loss,
        l2_penalty=penalty, gradient_infinity_norm=float(np.max(np.abs(gradient))), gradient_l2_norm=math.hypot(*map(float, gradient))), gradient, training


def _verify_trace(opt):
    trace = opt['trace']; _require(type(trace) is list and len(trace) == opt['loop_evaluations'], 'native trace count differs')
    common = {'iteration', 'objective', 'gradient_infinity_norm', 'gradient_l2_norm'}
    update = {'a', 'q', 'r', 'alpha', 'normalized_solve_residual'}
    for i, row in enumerate(trace):
        terminal = i == len(trace)-1
        _require(type(row) is dict and set(row) == (common if terminal else common|update)
            and type(row['iteration']) is int and row['iteration'] == i, 'native trace index/schema differs')
        _require(all(_number(v) and v >= 0. for k, v in row.items() if k != 'iteration'), 'finite nonnegative trace required')
        g, g2 = row['gradient_infinity_norm'], row['gradient_l2_norm']
        _require(g <= g2+ATOL and g2 <= math.sqrt(32.)*g+ATOL, 'trace32 gradient norms inconsistent')
        if terminal:
            _require(g <= GRADIENT_LIMIT, 'terminal trace gradient exceeds strict1e-8')
            _equal(row['objective'], opt['objective'], 'terminal objective')
            _exact(g, opt['loop_gradient_infinity_norm'], 'loop gradient')
            _exact(g2, opt['loop_gradient_l2_norm'], 'loop gradient2')
        else:
            _require(g > GRADIENT_LIMIT and row['a'] > 0. and row['q'] > 0.
                and 0. < row['alpha'] <= 1. and row['normalized_solve_residual'] <= 1e-12, 'invalid Newton update/descent/residual')
            ratio = row['a']/row['q']; r = row['r']
            _require(math.isfinite(ratio) and ratio > 0. and math.isfinite(r*ratio), 'invalid damping argument')
            alpha = min(1., math.log1p(r*ratio)/r) if r else min(1., ratio)
            _equal(row['alpha'], alpha, 'analytic damping')
    _exact(trace[0]['objective'], opt['initial_objective'], 'initial trace')


def verify_offset_certificate(model, data):
    _require(type(model) is dict and set(model) == {'configuration', 'coefficients', 'final_gradient', 'training', 'optimization', 'runtime', 'model_sha256'}, 'strict offset fields required')
    _exact(model['configuration'], expected_configuration(), 'fixed native32 configuration')
    _require(model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'offset checksum differs')
    theta = _vector(model['coefficients'], 32, 'theta'); saved = _vector(model['final_gradient'], 32, 'gradient')
    numbers, gradient, training = numerical_reference(theta, data['matrix'], data['y'], data['weights'], data['base_margin'])
    _equal(model['training'], training, 'independent arrays and curvature')
    _exact(model['training']['strong_convexity_lower_bound'], 1., 'strong convexity bound')
    _require(np.allclose(saved, gradient, atol=ATOL, rtol=RTOL), 'independent gradient differs')
    _require(numbers['gradient_infinity_norm'] <= GRADIENT_LIMIT and np.max(np.abs(saved)) <= GRADIENT_LIMIT,
        'independent or saved gradient exceeds strict1e-8')
    opt = model['optimization']; counters = ('updates', 'loop_evaluations', 'hessian_evaluations', 'linear_solves', 'final_checks', 'total_evaluations')
    fields = set(numbers)|set(counters)|{'status', 'accepted', 'loop_gradient_infinity_norm', 'loop_gradient_l2_norm', 'trace'}
    _require(type(opt) is dict and set(opt) == fields and type(opt['status']) is str
        and opt['status'] == 'converged_gradient' and opt['accepted'] is True, 'native optimization schema/status differs')
    _require(all(type(opt[k]) is int for k in counters) and 0 <= opt['updates'] <= 2000
        and opt['loop_evaluations'] == opt['updates']+1 and opt['hessian_evaluations'] == opt['updates']
        and opt['linear_solves'] == opt['updates'] and opt['final_checks'] == 1
        and opt['total_evaluations'] == opt['loop_evaluations']+1, 'native Newton counts differ')
    _require(opt['updates'] != 0 or not np.any(theta), 'zero updates require exact zero theta')
    for key, value in numbers.items():
        _require(_number(opt[key]) and opt[key] >= 0., 'finite nonnegative optimization summary required')
        _equal(opt[key], value, 'optimization.'+key)
    for name in ('infinity', 'l2'):
        key = 'loop_gradient_'+name+'_norm'
        _require(_number(opt[key]) and opt[key] >= 0., 'finite loop gradient required')
        _equal(opt[key], numbers['gradient_'+name+'_norm'], key)
    _require(opt['gradient_infinity_norm'] <= GRADIENT_LIMIT and opt['loop_gradient_infinity_norm'] <= GRADIENT_LIMIT,
        'reported gradient exceeds strict1e-8')
    _verify_trace(opt)
    _require(numbers['objective'] <= numbers['initial_objective']+1e-12*max(1., abs(numbers['initial_objective'])), 'objective exceeds zero initialization')
    _require(type(model['runtime']) is dict and set(model['runtime']) == {'python', 'numpy', 'scipy'}
        and all(type(v) is str and v for v in model['runtime'].values()), 'runtime schema differs')
    return theta


def _contract(value, inputs):
    _require(type(value) is dict and set(value) == {'expected_sha256', 'expected_fold_assignment_sha256', 'expected_source_binding_sha256'}
        and all(_digest(v) for v in value.values()) and value['expected_fold_assignment_sha256'] == inputs.fold_assignment_sha256,
        'exact external own label contract required')


def verify_fold(inputs, models, predictions, train_labels, *, expected_input_fingerprint, expected_label_contract, expected_runtime):
    _require(type(inputs) is FoldInputs, 'exact own FoldInputs required')
    body = encode_inputs(inputs); _exact(body['spec'], expected_spec(), 'capsule native32 spec')
    _require(_digest(expected_input_fingerprint) and input_fingerprint(inputs) == expected_input_fingerprint, 'external own input fingerprint differs')
    _contract(expected_label_contract, inputs)
    _require(type(expected_runtime) is dict and set(expected_runtime) == {'python', 'numpy', 'scipy'}
        and all(type(v) is str and v for v in expected_runtime.values()), 'external numerical runtime required')
    _require(type(models) is dict and set(models) == set(ARMS), 'all six own-fold models required')
    fold = inputs.fold; train = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] != fold]
    held = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] == fold]
    _require(train and held and {e.observation.problem_id for e in train}.isdisjoint({e.observation.problem_id for e in held}), 'problem fold isolation differs')
    banks = {e.bank_id: inputs.banks[e.bank_id] for e in train}; coefficients = {}
    fields = {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint', 'label_contract',
        'parent_structure_model_sha256', 'readiness_complete_sha256', 'pair_metadata', 'pair_summary', 'offset_model', 'model_sha256'}
    for arm in ARMS:
        m = models[arm]
        _require(type(m) is dict and set(m) == fields and m['kind'] == MODEL_KIND and m['arm'] == arm
            and type(m['fold']) is int and m['fold'] == fold and m['input_fingerprint'] == expected_input_fingerprint
            and m['train_example_ids'] == [e.example_id for e in train] and m['held_example_ids'] == [e.example_id for e in held]
            and m['parent_structure_model_sha256'] == inputs.parent_structure_model_sha256
            and m['readiness_complete_sha256'] == inputs.readiness_complete_sha256
            and m['model_sha256'] == canonical_hash({k: v for k, v in m.items() if k != 'model_sha256'}), 'own model identity differs')
        _exact(m['label_contract'], expected_label_contract, 'externally pinned own label contract')
        _exact(m['offset_model']['runtime'], expected_runtime, 'external runtime')
        data = reconstruct_pairs(train, banks, train_labels, {e.bank_id: inputs.interactions[arm][e.bank_id] for e in train},
            {e.bank_id: inputs.base_scores[e.bank_id] for e in train})
        _equal(m['pair_metadata'], data['metadata'], 'all pair metadata')
        _equal(m['pair_summary'], data['summary'], 'retained zero-pair mass')
        _equal(inputs.parent_training, data['training'], 'frozen own base training population')
        coefficients[arm] = verify_offset_certificate(m['offset_model'], data)
        if arm == 'CF':
            _require(not np.any(coefficients[arm][16:]) and not np.any(m['offset_model']['final_gradient'][16:]), 'CF tail must remain exact zero')
    _require(type(predictions) is list and len(predictions) == len(held)
        and [p['example_id'] for p in predictions] == [e.example_id for e in held], 'exact own held prediction coverage/order required')
    for ex, pred, parent in zip(held, predictions, inputs.parent_predictions, strict=True):
        bank = inputs.banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]; base = inputs.base_scores[ex.bank_id]
        scores = {m: dict(parent['candidate_scores'][m]) for m in BASELINES[:2]}
        _exact(scores['structural_C'], base, 'same-fold structural base projection')
        for method, arm, fitted in [*((a, a, a) for a in ARMS), *((m, a, 'H') for m, a in zip(DIAGNOSTICS, ('HS', 'Jm', 'CF')))]:
            residual = inputs.interactions[arm][ex.bank_id].matrix@coefficients[fitted]
            scores[method] = {cid: float(base[cid]+residual[i]) for i, cid in enumerate(ids)}
        noop = next(c.candidate_id for c in bank.candidates if c.is_noop); first = bank.attempts[0]
        first_id = hashlib.sha256(first.source).hexdigest() if first.status == 'success' else noop
        _require(parent['choices']['noop'] == noop and parent['choices']['first_attempt'] == first_id, 'deterministic baseline differs')
        for m, cid in (('noop', noop), ('first_attempt', first_id)): scores[m] = {c: float(c == cid) for c in ids}
        _require(all(_number(v) for cell in scores.values() for v in cell.values()), 'nonfinite held scores')
        choices = {m: min(ids, key=lambda cid: (-scores[m][cid], cid)) for m in METHODS}
        for m in BASELINES[:2]: _require(choices[m] == parent['choices'][m], 'zero-residual base choice differs')
        diagnostics = {}
        for arm in ('HS', 'Jm', 'CF'):
            name = 'shared_H_'+arm; equal = np.array_equal(inputs.interactions['H'][ex.bank_id].matrix, inputs.interactions[arm][ex.bank_id].matrix)
            _require(not equal or scores['H'] == scores[name] and choices['H'] == choices[name], 'identical-feature shared-H invariant differs')
            diagnostics[arm] = dict(features_identical_exact=equal, choice_changed=choices['H'] != choices[name],
                transition='same' if choices['H'] == choices[name] else 'to_noop' if choices['H'] == noop else 'from_noop' if choices[name] == noop else 'edited_to_edited',
                score_difference={cid: scores['H'][cid]-scores[name][cid] for cid in ids})
        expected = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, problem_id=bank.problem_id,
            fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices, candidate_scores=scores,
            shared_theta_diagnostics=diagnostics, projected_zero_residual_parent_choice_parity=True)
        _equal(pred, expected, 'held prediction32')  # SHA choices are exact strings, never tolerance-relaxed.
    return dict(fold=fold, verified_models=6, held_prefixes=len(held), train_prefixes=len(train))


def _serialize(value):
    if isinstance(value, Fraction): return dict(numerator=value.numerator, denominator=value.denominator, value=float(value))
    if type(value) is dict: return {k: _serialize(v) for k, v in value.items()}
    return value


def independent_assessment(cohort, predictions, labels):
    """Exact rational13 reports plus old independent gate AND independent CF."""
    _require(type(predictions) is list and all(type(p) is dict and type(p.get('choices')) is dict
        and set(p['choices']) == set(METHODS) for p in predictions), 'strict thirteen choices required')
    projected = [{**p, 'choices': {m: p['choices'][m] for m in OLD_METHODS}} for p in predictions]
    old = old_independent_assessment(cohort, projected, labels)
    by_id = {r['example_id']: r for r in cohort}
    for p in predictions:
        _require(all(type(cid) is str and cid in by_id[p['example_id']]['candidate_ids'] for cid in p['choices'].values()), 'foreign/nonstring added choice')
    def cell(rows, method):
        n = len(rows); vals = [labels[p['bank_id'], p['choices'][method]] for p in rows]
        a = sum(v['status'] == 'stable' and v['all_ac'] for v in vals)
        r = sum(v['status'] == 'stable' and v['loss'] > 0 for v in vals); u = sum(v['status'] == 'unknown' for v in vals)
        return dict(examples=n, evaluable=bool(n), counts=dict(stable_ac=a, stable_regression=r, unknown=u,
            noop_selected=sum(p['choices'][method] == p['choices']['noop'] for p in rows)),
            fractions=dict(zip(METRICS, (Fraction(v, n) for v in (a, a+u, r, r+u)))) if n else None)
    def group(rows):
        pids = sorted({p['problem_id'] for p in rows})
        problems = {pid: {m: cell([p for p in rows if p['problem_id'] == pid], m) for m in METHODS} for pid in pids}
        equal = {m: {k: sum((problems[pid][m]['fractions'][k] for pid in pids), Fraction())/len(pids) for k in METRICS} for m in METHODS} if pids else None
        return dict(examples=len(rows), problems=len(pids), results={m: cell(rows, m) for m in METHODS}, problem_results=problems, equal_problem=equal)
    def compare(g, strict=True):
        if not g['examples']: return dict(evaluable=False, passed=False, checks={})
        checks = {}
        for key, values in (('pooled', {m: c['fractions'] for m, c in g['results'].items()}), ('equal_problem', g['equal_problem'])):
            h, c = values['H'], values['CF']
            checks[key+'_ac'] = h['ac_lower'] > c['ac_lower'] if strict else h['ac_lower'] >= c['ac_lower']
            for name in ('regression_lower', 'regression_upper'): checks[key+'_'+name] = h[name] <= c[name]
        return dict(evaluable=True, passed=all(checks.values()), checks=checks)
    full = group(predictions); folds = {str(f): group([p for p in predictions if p['fold'] == f]) for f in range(5)}
    rows = {k: [] for k in ('known_ac', 'known_nonac', 'unknown')}
    for p in predictions:
        lab = labels[p['bank_id'], p['choices']['noop']]
        rows['unknown' if lab['status'] == 'unknown' else 'known_ac' if lab['all_ac'] else 'known_nonac'].append(p)
    groups = {k: group(v) for k, v in rows.items()}
    subfolds = {k: {str(f): group([p for p in v if p['fold'] == f]) for f in range(5)} for k, v in rows.items()}
    cf_full = compare(full); cf_nonac = compare(groups['known_nonac']); cf_ac = compare(groups['known_ac'], False)
    nonworse = sum(f['results']['H']['fractions']['ac_lower'] >= f['results']['CF']['fractions']['ac_lower'] for f in folds.values())
    cf = dict(full_check=cf_full, known_nonac_check=cf_nonac, known_ac_check=cf_ac, nonworse_full_folds=nonworse,
        required_nonworse_folds=4, passed=bool(cf_full['passed'] and cf_nonac['passed'] and cf_ac['passed'] and nonworse >= 4))
    gate = dict(old['gate'], original_gates_passed=old['gate']['passed'], current_feedback_contribution=cf['passed'],
        current_feedback_check=cf); gate['passed'] = bool(old['gate']['passed'] and cf['passed'])
    switches = {}
    for m in METHODS[1:]:
        out = dict(examples=len(predictions), selected_candidate_changed=0, ac_gained=0, ac_lost=0,
            regression_prevented=0, regression_introduced=0, not_jointly_known=0, edited_to_edited=0, to_noop=0, from_noop=0)
        for p in predictions:
            h, c, noop = (p['choices'][k] for k in ('H', m, 'noop'))
            if h != c:
                out['selected_candidate_changed'] += 1; out['to_noop' if h == noop else 'from_noop' if c == noop else 'edited_to_edited'] += 1
            a, b = labels[p['bank_id'], h], labels[p['bank_id'], c]
            if a['status'] == 'unknown' or b['status'] == 'unknown': out['not_jointly_known'] += 1
            else:
                out['ac_gained'] += a['all_ac'] and not b['all_ac']; out['ac_lost'] += b['all_ac'] and not a['all_ac']
                out['regression_prevented'] += a['loss'] == 0 and b['loss'] > 0; out['regression_introduced'] += a['loss'] > 0 and b['loss'] == 0
        switches[m] = out
    return _serialize(dict(kind='prospective_statement_progress32_repair_gate_v1', primary='H', methods=list(METHODS), full=full,
        folds=folds, current_status_subgroups=groups, current_status_subgroup_folds=subfolds, primary_transitions=switches,
        gate=gate, original_gate=old['gate'], exclusions=0, note='Adaptive fixed-bank development; all original gates AND the prospective CF gate; '
        'statement-sample feedback is a new observation, not learner-outcome evidence.'))


def shared_diagnostics(predictions):
    result = {}
    for arm in ('HS', 'Jm', 'CF'):
        result[arm] = {}
        for name, same in (('identical_features', True), ('different_features', False)):
            rows = [p['shared_theta_diagnostics'][arm] for p in predictions if p['shared_theta_diagnostics'][arm]['features_identical_exact'] is same]
            result[arm][name] = dict(examples=len(rows), choices_changed=sum(r['choice_changed'] for r in rows),
                **{k: sum(r['transition'] == k for r in rows) for k in ('same', 'edited_to_edited', 'to_noop', 'from_noop')})
    return result


def audit_run(fold_inputs, fold_models, predictions, train_labels_by_fold, assessment_labels, report, *,
              expected_input_fingerprint, expected_label_contracts, expected_runtime):
    """All320/all30/all13 after external prediction/label-authentication barrier.

    ``expected_input_fingerprint`` is a five-fold map, not a global manifest.
    Raw features and base scores are externally authenticated projections, not
    freshly observed sources or empirical labels opened by this pure function.
    """
    for mapping in (fold_inputs, fold_models, train_labels_by_fold, expected_input_fingerprint, expected_label_contracts):
        _require(type(mapping) is dict and set(mapping) == set(range(5)) and all(type(k) is int for k in mapping), 'all five exact fold mappings required')
    first = fold_inputs[0]; _require(type(first) is FoldInputs, 'typed fold inputs required')
    common = encode_inputs(first); examples = first.examples; ids = [e.example_id for e in examples]
    _require(len(ids) == len(set(ids)) == 320 and len({e.user_id for e in examples}) == 320
        and len({e.bank_id for e in examples}) == 320 and len({e.observation.problem_id for e in examples}) == 23
        and sum(len(b.candidates) for b in first.banks.values()) == 2544, 'exact320/23/2544 assessment population required')
    _require(type(predictions) is list and len(predictions) == 320 and len({p['example_id'] for p in predictions}) == 320
        and {p['example_id'] for p in predictions} == set(ids), 'all320 unique held predictions required')
    _require(type(assessment_labels) is dict, 'exact assessment label mapping required')
    _exact(validate_core_labels(list(assessment_labels.values()), first.banks), assessment_labels, 'full assessment core coverage')
    indexed = {p['example_id']: p for p in predictions}; folds = []
    for fold in range(5):
        inputs = fold_inputs[fold]; _require(type(inputs) is FoldInputs and inputs.fold == fold, 'capsule fold mismatch')
        body = encode_inputs(inputs)
        for key in ('examples', 'banks', 'assignment', 'interactions', 'fold_assignment_sha256', 'readiness_complete_sha256', 'synthetic', 'spec', 'arms'):
            _exact(body[key], common[key], 'shared projected cohort/features.'+key)
        _contract(expected_label_contracts[fold], inputs)
        _require(expected_label_contracts[fold]['expected_source_binding_sha256'] == expected_label_contracts[0]['expected_source_binding_sha256'], 'common label ancestry differs')
        train_bids = {e.bank_id for e in examples if inputs.assignment['example_fold'][e.example_id] != fold}
        _exact(train_labels_by_fold[fold], {k: v for k, v in assessment_labels.items() if k[0] in train_bids}, 'own train and sealed assessment labels disagree')
        held = [indexed[e.example_id] for e in examples if inputs.assignment['example_fold'][e.example_id] == fold]
        folds.append(verify_fold(inputs, fold_models[fold], held, train_labels_by_fold[fold],
            expected_input_fingerprint=expected_input_fingerprint[fold], expected_label_contract=expected_label_contracts[fold], expected_runtime=expected_runtime))
    cohort = [dict(example_id=e.example_id, user_id=e.user_id, bank_id=e.bank_id, problem_id=e.observation.problem_id,
        fold=first.assignment['example_fold'][e.example_id], candidate_ids=[c.candidate_id for c in first.banks[e.bank_id].candidates],
        noop_candidate_id=next(c.candidate_id for c in first.banks[e.bank_id].candidates if c.is_noop)) for e in examples]
    expected = independent_assessment(cohort, predictions, assessment_labels)
    extras = {'completed_fits', 'full_train_refits', 'model_promotion', 'predictions_complete_sha256', 'shared_theta_diagnostics'}
    _require(type(report) is dict and set(report) == set(expected)|extras, 'exact assessment and five stage fields required')
    _require(_digest(report['predictions_complete_sha256']), 'externally authenticated prediction barrier SHA required')
    _exact({k: report[k] for k in expected}, expected, 'exact rational assessment')
    _require(type(report.get('completed_fits')) is int and report['completed_fits'] == 30
        and type(report.get('full_train_refits')) is int and report['full_train_refits'] == 0
        and report.get('model_promotion') is False, 'fixed fit/no-promotion bookkeeping differs')
    _exact(report.get('shared_theta_diagnostics'), shared_diagnostics(predictions), 'shared H full diagnostics')
    return dict(verified=True, recipients=320, models=30, methods=13, folds=folds, gate=expected['gate'], feature_dimension=32,
        pair_metadata_verified=True, fitting_performed=False, external_provenance_guard_required=True,
        features='externally_authenticated_previously_independently_audited_readiness_vectors_not_recomputed_here',
        guard_owned_checks=['raw_artifact_seals', 'clean_source_and_runtime_ancestry', 'readiness_feature_authority',
            'same_fold_original_base_score_projection', 'label_envelope_provenance', 'all30_prediction_before_label_barrier',
            'report.predictions_complete_sha256'], not_reconstructed=['Newton_iterate_vectors_and_Hessians_not_serialized'],
        floating_tolerance=dict(atol=ATOL, rtol=RTOL, gradient_limit=GRADIENT_LIMIT))


if __name__ == '__main__':
    raise SystemExit('Pure independent audit only; no production I/O or fitting release.')
