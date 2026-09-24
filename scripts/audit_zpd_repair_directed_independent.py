"""Pure independent directed144 repair audit; no I/O, fitting or release.

Only AST signature/delta primitives and the previously independent base-score
and exact assessment routines are shared. Directional matching, conditional
moments, pair enumeration/weights, CSR hashes, loss/gradient/curvature and all
residual scores are reconstructed here, without the producer core or driver.

Source moments use scalar fsum and fixed atol=rtol=2e-14. Once checked, supplied
float64 matrices are the exact consumed arrays for byte hashes and optimization
replay: scalar reassociation is not expected to reproduce their bytes. Numeric
certificate comparisons use atol=rtol=1e-10; convergence remains <=1e-6 and
selected SHA identities are exact. None of these tolerances is outcome-tuned.

The caller owns clean-source/runtime/input seals, source-language/donor ancestry,
label-envelope authentication and the prediction-before-label opening barrier.
This object-only API does not establish those external facts or grant release.
"""
from collections import Counter
import hashlib
import json
import math
import random
import re

import numpy as np
from scipy import sparse

from scripts.zpd_repair_directed_history import signature, delta_signatures
from scripts.audit_zpd_repair_feedback_cv import frozen_base_scores, verify_assessment
from scripts.zpd_repair_feedback_labels import validate_core_labels
from src.repair.pilot_contracts import canonical_hash

ARMS = ('H', 'Jm', 'HS', 'U', 'L')
BASELINES = ('structural_C', 'lexical_C', 'first_attempt')
METHODS = (*ARMS, *BASELINES, 'shared_H_HS', 'shared_H_Jm', 'noop')
VERDICTS = ('AC', 'CE', 'OTHER', 'RE', 'RESOURCE', 'WA')
DIMENSION = 144
ATOL = RTOL = 1e-10
FEATURE_TOL = 2e-14
GRADIENT_LIMIT = 1e-6
OBSERVATION_FIELDS = {'example_id', 'user_id', 'problem_id', 'bank_id', 'fold',
    'current_code', 'current_verdict', 'current_timestamp', 'current_source_sha256',
    'history', 'donor_history', 'donor_example_id', 'donor_user_id',
    'observed_source_ids', 'donor_source_ids'}


def _require(condition, message):
    if not condition: raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _equal(actual, expected, where='value'):
    if type(expected) is dict:
        _require(type(actual) is dict and set(actual) == set(expected), where+' dictionary differs')
        for key, value in expected.items(): _equal(actual[key], value, where+'.'+str(key))
    elif type(expected) in (tuple, list):
        _require(type(actual) is type(expected) and len(actual) == len(expected), where+' sequence differs')
        for i, value in enumerate(expected): _equal(actual[i], value, where+f'[{i}]')
    elif type(expected) is float:
        _require(_number(actual) and math.isclose(actual, expected, rel_tol=RTOL, abs_tol=ATOL), where+' number differs')
    else: _require(type(actual) is type(expected) and actual == expected, where+' differs')


def _exact(actual, expected, where='value'):
    """Fixed configuration is type- and value-exact, not a numeric estimate."""
    _require(type(actual) is type(expected), where+' type differs')
    if type(expected) is dict:
        _require(set(actual) == set(expected), where+' keys differ')
        for key, value in expected.items(): _exact(actual[key], value, where+'.'+str(key))
    elif type(expected) in (tuple, list):
        _require(len(actual) == len(expected), where+' length differs')
        for i, value in enumerate(expected): _exact(actual[i], value, where+f'[{i}]')
    else: _require(actual == expected, where+' differs')


def _array(value, shape, dtype, name):
    _require(type(value) is np.ndarray and value.shape == shape and value.dtype == np.dtype(dtype)
        and np.isfinite(value).all(), name+' array invalid')


def _vector(value, size, name):
    _require(type(value) is list and len(value) == size and all(_number(v) for v in value), name+' vector invalid')
    return np.asarray(value, dtype=np.float64)


def _sha_arrays(*arrays):
    digest = hashlib.sha256()
    for array in arrays:
        array = np.ascontiguousarray(array)
        header = json.dumps(dict(shape=list(array.shape), dtype=array.dtype.str), sort_keys=True, separators=(',', ':')).encode()
        for block in (header, array.tobytes(order='C')):
            digest.update(len(block).to_bytes(8, 'little')); digest.update(block)
    return digest.hexdigest()


def feature_configuration():
    return dict(version='candidate_directed_exact_ast_history_v1', dimension=144,
        weightings=['uniform', 'reciprocal_recency'], directions=['same', 'reverse'],
        verdict_pairs=[a+'=>'+b for a in VERDICTS for b in VERDICTS],
        flatten_order='weight_direction_verdict_pair_C', scale_divisor=2.,
        signature='exact_typed_field_list_index_path_node_class_immediate_scalar',
        endpoint_parse='ast.parse_exact_utf8_bytes_declared_Python_only', ast_feature_version=[3, 10],
        delta='after_counter_minus_before_counter_common_cancelled',
        similarity='signed_Dice_same_and_reversed_history_delta',
        conditioning='candidate_and_history_endpoints_AST_available_including_zero_mass',
        recency='inverse_transition_distance_in_supplied_sequence_before_mask_conditioning',
        shuffle='frozen_prior_only_permutation_current_anchored',
        marginal='conditional_similarity_mean_times_conditional_verdict_pair_mean',
        final_normalization=False, fitted_transform=False, future_targets_used=False,
        semantic_alignment_claim=False, maximum_vector_l2=2.**-.5, maximum_pair_difference_l2=1.)


def expected_spec():
    return dict(representation='candidate_directed_exact_ast_history_v1', dimension=144,
        feature_configuration_sha256=canonical_hash(feature_configuration()),
        model_kind='fixed_repair_directed_offset_logistic_v1')


def expected_configuration():
    return dict(kind='fixed_repair_directed_offset_logistic_v1', dimension=144, representation=expected_spec(),
        C=.1, mirrored_row_mass=1900., intercept=0., fixed_base_margin_coefficient=1.,
        labels='integer_0_1_signed_as_2y_minus_1',
        row_contract='adjacent_exact_feature_offset_label_mirrors_equal_positive_weights',
        matrix_arithmetic='canonical_float64_CSR', regularization='half_squared_L2_interaction_only',
        initialization='all_zero', optimizer='scipy.optimize.minimize_L-BFGS-B', analytic_jacobian=True,
        bounds=None, maxiter=2000, ftol=1e-12, gtol=1e-8, maxcor=10, maxls=20, maxfun=15000,
        final_gradient_infinity_limit=1e-6, mass_rtol=1e-12, mass_atol=1e-12, retries=0, base_margin_optimized=False)


def _nominal(value):
    _require(type(value) is str and bool(value), 'explicit nominal verdict required')
    if value in VERDICTS: return value
    return {'Accepted': 'AC', 'Wrong Answer': 'WA', 'Compile Error': 'CE', 'Compilation Error': 'CE',
        'Runtime Error': 'RE', 'Time Limit Exceeded': 'RESOURCE', 'Memory Limit Exceeded': 'RESOURCE'}.get(value, 'OTHER')


def _history(history, timestamp):
    _require(type(history) is list and _number(timestamp), 'explicit observed history and timestamp required')
    times = []
    for row in history:
        _require(type(row) is dict and set(row) == {'code', 'verdict', 'timestamp', 'language'}, 'observed-only history schema differs')
        _require(type(row['code']) is str and type(row['language']) is str and row['language']
            and _number(row['timestamp']), 'history source/time/language invalid')
        row['code'].encode('utf-8'); _nominal(row['verdict']); times.append(row['timestamp'])
    _require(all(a < b for a, b in zip(times, [*times[1:], timestamp])), 'authentic chronology differs before permutation')


def _permutation(n, key):
    seed = int.from_bytes(hashlib.sha256(('zpd-history-action-order-20260923-v1|'+key).encode()).digest(), 'big')
    order = list(range(n)); random.Random(seed).shuffle(order)
    return order


def _signed_match(candidate, historical):
    if not candidate.available or not historical.available: return False, (0., 0.)
    if not candidate.mass or not historical.mass: return True, (0., 0.)
    same = reverse = 0
    for key in set(candidate.additions) | set(candidate.removals) | set(historical.additions) | set(historical.removals):
        a, r = candidate.additions.get(key, 0), candidate.removals.get(key, 0)
        b, s = historical.additions.get(key, 0), historical.removals.get(key, 0)
        same += min(a, b)+min(r, s); reverse += min(a, s)+min(r, b)
    denominator = candidate.mass+historical.mass
    _require(2*(same+reverse) <= denominator, 'invalid signed delta overlap')
    return True, (2.*same/denominator, 2.*reverse/denominator)


def independent_interactions(observed, bank):
    """Rebuild five matrices with scalar conditional moments, not producer calls."""
    o = observed
    _require(type(o) is dict and set(o) == OBSERVATION_FIELDS, 'exact observed-only row required')
    _require(type(o['current_code']) is str and bank.current_source == o['current_code'].encode('utf-8')
        and bank.problem_id == o['problem_id'] and hashlib.sha256(bank.current_source).hexdigest() == o['current_source_sha256'],
        'current source/bank identity differs')
    _nominal(o['current_verdict'])
    for history in (o['history'], o['donor_history']): _history(history, o['current_timestamp'])
    current = signature(o['current_code'], 'Python')
    candidate_deltas = [delta_signatures(current, signature(c.source.decode('utf-8', errors='strict'), 'Python')) for c in bank.candidates]
    result = {}
    for arm in ARMS:
        history = o['donor_history'] if arm == 'U' else o['history'][-1:] if arm == 'L' else o['history']
        if arm == 'HS': history = [history[i] for i in _permutation(len(history), o['example_id'])]
        sequence = [*history, dict(code=o['current_code'], verdict=o['current_verdict'], language='Python')]
        source_signatures = [signature(row['code'], row['language']) for row in sequence]
        transitions = [delta_signatures(a, b) for a, b in zip(source_signatures, source_signatures[1:])]
        pairs = [VERDICTS.index(_nominal(a['verdict']))*6+VERDICTS.index(_nominal(b['verdict'])) for a, b in zip(sequence, sequence[1:])]
        matrix = np.zeros((len(candidate_deltas), DIMENSION), dtype=np.float64)
        for row, candidate in enumerate(candidate_deltas):
            matches = [_signed_match(candidate, t) for t in transitions]
            active = [i for i, (available, _) in enumerate(matches) if available]
            for weighting in range(2):
                weights = {i: 1. if weighting == 0 else 1./(len(transitions)-i) for i in active}
                denominator = math.fsum(weights.values())
                if not denominator: continue
                for direction in range(2):
                    mean = math.fsum(weights[i]*matches[i][1][direction] for i in active)/denominator
                    for pair in range(36):
                        selected = [i for i in active if pairs[i] == pair]
                        moment = (mean*math.fsum(weights[i] for i in selected)/denominator if arm == 'Jm' else
                            math.fsum(weights[i]*matches[i][1][direction] for i in selected)/denominator)
                        matrix[row, (weighting*2+direction)*36+pair] = moment/2.
        result[arm] = matrix
    return result


def verify_interactions(observed, bank, supplied):
    expected = independent_interactions(observed, bank)
    ids = tuple(c.candidate_id for c in bank.candidates)
    _require(type(supplied) is dict and set(supplied) == set(ARMS), 'five exact interaction arms required')
    for arm, block in supplied.items():
        _require(block.candidate_ids == ids, 'candidate order differs')
        _array(block.matrix, (len(ids), DIMENSION), 'float64', 'interaction')
        _require(np.allclose(block.matrix, expected[arm], atol=FEATURE_TOL, rtol=FEATURE_TOL), 'independent directed interaction differs')
        _require(np.all(block.matrix >= 0.) and np.all(np.linalg.norm(block.matrix, axis=1) <= 2.**-.5+FEATURE_TOL), 'directed nonnegative norm bound differs')
        for i, candidate in enumerate(bank.candidates):
            if candidate.is_noop: _require(not np.any(block.matrix[i]), 'no-op interaction must be exactly zero')
    return True


def reconstruct_pairs(examples, banks, labels, interactions, base_scores):
    """All stable unequal pairs, original ordering and two weight normalizations."""
    ids = [e.example_id for e in examples]; bids = [e.bank_id for e in examples]
    _require(examples and len(ids) == len(set(ids)) and len(bids) == len(set(bids))
        and all(e.split == 'train' for e in examples), 'unique training prefixes required')
    for mapping in (banks, interactions, base_scores):
        _require(type(mapping) is dict and set(mapping) == set(bids), 'exact training bank scope required')
    _require(type(labels) is dict and all(type(row) is dict and (row.get('bank_id'), row.get('candidate_id')) == key for key, row in labels.items()), 'core label identity differs')
    core = validate_core_labels(list(labels.values()), banks)
    _require(labels == core, 'exact core training labels required')
    records = []; bank_diagnostics = []
    for ex in examples:
        bank = banks[ex.bank_id]; block = interactions[ex.bank_id]; candidates = bank.candidates
        _require(bank.current_source == ex.observation.current.source and bank.problem_id == ex.observation.problem_id, 'training bank source differs')
        cids = tuple(c.candidate_id for c in candidates)
        _require(block.candidate_ids == cids and type(base_scores[ex.bank_id]) is dict and set(base_scores[ex.bank_id]) == set(cids)
            and all(_number(v) for v in base_scores[ex.bank_id].values()), 'candidate order/base scope differs')
        _array(block.matrix, (len(cids), DIMENSION), 'float64', 'training interaction')
        keys = []
        for cid in cids:
            label = core[ex.bank_id, cid]
            keys.append(None if label['status'] == 'unknown' else (int(label['all_ac']), int(label['loss'] == 0), label['gain']-label['loss']))
        stable = [i for i, key in enumerate(keys) if key is not None]
        stable_count = len(stable)*(len(stable)-1)//2
        pairs = [(i, j, int(keys[i] > keys[j])) for i in range(len(cids)) for j in range(i+1, len(cids))
                 if keys[i] is not None and keys[j] is not None and keys[i] != keys[j]]
        if pairs: records.append((ex, pairs, len(stable)))
        diagnostics = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            bank_seal_sha256=bank.seal_sha256, problem_id=bank.problem_id, candidate_ids=list(cids),
            is_noop=[c.is_noop for c in candidates], candidate_statuses=[core[ex.bank_id, c]['status'] for c in cids],
            candidate_count=len(cids), stable_candidates=len(stable), unknown_candidates=len(cids)-len(stable),
            pairs_with_unknown=len(cids)*(len(cids)-1)//2-stable_count,
            stable_tied_pairs=stable_count-len(pairs), informative_unordered_pairs=len(pairs))
        informative = {(i, j) for i, j, _ in pairs}
        for name, filtered in (('all_pair_counts', False), ('informative_pair_counts', True)):
            counts = dict(unordered_pairs=0, noop_edited_pairs=0, edited_edited_pairs=0,
                interaction_varying_pairs=0, zero_interaction_pairs=0, nonzero_base_margin_pairs=0)
            for i in range(len(cids)):
                for j in range(i+1, len(cids)):
                    if filtered and (i, j) not in informative: continue
                    difference = block.matrix[i]-block.matrix[j]
                    counts['unordered_pairs'] += 1
                    counts['noop_edited_pairs' if candidates[i].is_noop or candidates[j].is_noop else 'edited_edited_pairs'] += 1
                    counts['interaction_varying_pairs'] += int(np.max(np.abs(difference)) > 1e-12)
                    counts['zero_interaction_pairs'] += int(not np.any(difference))
                    counts['nonzero_base_margin_pairs'] += int(float(base_scores[ex.bank_id][cids[i]])-float(base_scores[ex.bank_id][cids[j]]) != 0.)
            diagnostics[name] = counts
        bank_diagnostics.append(diagnostics)
    _require(records, 'no unequal stable training pairs')
    prefixes = Counter(ex.user_id for ex, _, _ in records)
    x = []; y = []; weights = []; offsets = []; pair_ids = []; candidate_pairs = []
    for ex, pairs, _ in records:
        block = interactions[ex.bank_id]; scores = base_scores[ex.bank_id]
        for i, j, target in pairs:
            left, right = block.candidate_ids[i], block.candidate_ids[j]
            difference = block.matrix[i]-block.matrix[j]; margin = float(scores[left])-float(scores[right])
            x.extend((difference, -difference)); y.extend((target, 1-target)); offsets.extend((margin, -margin))
            weights.extend([1/(prefixes[ex.user_id]*len(pairs)*2)]*2)
            pair_ids.extend([ex.example_id]*2); candidate_pairs.extend([[left, right], [right, left]])
    w = np.asarray(weights, dtype=np.float64)
    w *= len(w)/w.sum(); old_mass = float(w.sum()); w = w*(1900./old_mass)
    informative_ids = [e.example_id for e, _, _ in records]; users = {e.user_id for e in examples}
    training = dict(train_prefixes=len(examples), train_users=len(users), informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(examples)-len(records), users=len(prefixes), users_without_informative_prefix=len(users-set(prefixes)),
        ordered_pairs=len(w), pair_example_ids=pair_ids, informative_train_example_ids=informative_ids,
        uninformative_train_example_ids=sorted(set(ids)-set(informative_ids)), stable_train_candidates=sum(n for _, _, n in records),
        weight_normalization='fixed_reference_total_pair_weight', reference_pair_weight=1900.,
        sample_weight_sum=float(w.sum()), prior_mean_one_weight_sum=old_mass)
    metadata = dict(kind='fixed_train_only_residual_pairs_v1', preference='legacy_stable_lexicographic_all_ac_loss_zero_net_gain',
        no_pair_filter_by_feature_variation=True, fixed_base_coefficient=1., intercept=0., training=training,
        banks=bank_diagnostics, pair_candidate_ids=candidate_pairs, spec=expected_spec(), diagnostic_variation_tolerance=1e-12)
    for name in ('all_pair_counts', 'informative_pair_counts'):
        metadata[name] = {key: sum(b[name][key] for b in bank_diagnostics) for key in bank_diagnostics[0][name]}
    return dict(matrix=np.stack(x), y=np.asarray(y, dtype=np.int64), weights=w,
        base_margin=np.asarray(offsets, dtype=np.float64), training=training, pair_candidate_ids=candidate_pairs, metadata=metadata)


def numerical_reference(theta, x, y, weights, offset):
    """Scalar stable softplus/sigmoid and fsum reductions; no optimizer call."""
    _array(theta, (DIMENSION,), 'float64', 'theta')
    _require(type(x) is np.ndarray and x.ndim == 2 and len(x) > 0, 'nonempty dense raw pair matrix required')
    n = len(x); _array(x, (n, DIMENSION), 'float64', 'matrix')
    _array(y, (n,), 'int64', 'labels'); _array(weights, (n,), 'float64', 'weights'); _array(offset, (n,), 'float64', 'offset')
    _require(n % 2 == 0 and np.isin(y, [0, 1]).all() and (weights > 0).all()
        and math.isclose(math.fsum(weights), 1900., rel_tol=1e-12, abs_tol=1e-12), 'invalid pair labels/mass')
    _require(np.array_equal(x[::2], -x[1::2]) and np.array_equal(y[::2], 1-y[1::2])
        and np.array_equal(weights[::2], weights[1::2]) and np.array_equal(offset[::2], -offset[1::2]), 'pair mirrors differ')
    csr = sparse.csr_matrix(x); csr.eliminate_zeros(); csc = csr.tocsc()
    factors = []; losses = []; initial_losses = []
    for i in range(n):
        lo, hi = csr.indptr[i:i+2]
        dot = math.fsum(float(v)*float(theta[j]) for v, j in zip(csr.data[lo:hi], csr.indices[lo:hi]))
        signed = 2*int(y[i])-1; margin = signed*(float(offset[i])+dot)
        _require(math.isfinite(margin), 'nonfinite scalar margin')
        sigmoid = math.exp(-margin)/(1+math.exp(-margin)) if margin >= 0 else 1/(1+math.exp(margin))
        factors.append(.1*float(weights[i])*signed*sigmoid)
        losses.append(.1*float(weights[i])*(max(0., -margin)+math.log1p(math.exp(-abs(margin)))))
        initial = signed*float(offset[i])
        initial_losses.append(.1*float(weights[i])*(max(0., -initial)+math.log1p(math.exp(-abs(initial)))))
    gradient = np.empty(DIMENSION, dtype=np.float64)
    for j in range(DIMENSION):
        lo, hi = csc.indptr[j:j+2]
        gradient[j] = float(theta[j])-math.fsum(float(v)*factors[i] for v, i in zip(csc.data[lo:hi], csc.indices[lo:hi]))
    squared = [math.fsum(float(v)*float(v) for v in row) for row in x]
    weighted = math.fsum(float(w)*v for w, v in zip(weights, squared))
    penalty = .5*math.fsum(float(t)*float(t) for t in theta); data_loss = math.fsum(losses)
    training = dict(rows=n, unordered_pairs=n//2, positive_rows=int(y.sum()), zero_difference_rows=int((np.diff(csr.indptr) == 0).sum()),
        weight_mass=math.fsum(weights), maximum_row_squared_norm=max(squared), weighted_row_squared_norm_sum=weighted,
        strong_convexity_lower_bound=1., hessian_spectral_upper_bound=1.+.025*weighted,
        input_sha256=dict(features=_sha_arrays(np.asarray(csr.shape, dtype='<i8'), csr.indptr.astype('<i8'), csr.indices.astype('<i8'), csr.data.astype('<f8')),
            labels=_sha_arrays(y.astype('<i8')), weights=_sha_arrays(weights.astype('<f8')), base_margin=_sha_arrays(offset.astype('<f8'))))
    return dict(initial_objective=math.fsum(initial_losses), objective=data_loss+penalty, weighted_logistic_loss=data_loss,
        l2_penalty=penalty, gradient_infinity_norm=float(np.max(np.abs(gradient))), gradient_l2_norm=math.hypot(*map(float, gradient))), gradient, training


def verify_offset_certificate(model, data):
    fields = {'configuration', 'coefficients', 'final_gradient', 'training', 'optimization', 'runtime', 'model_sha256'}
    _require(type(model) is dict and set(model) == fields, 'offset certificate fields differ')
    _exact(model['configuration'], expected_configuration(), 'configuration')
    _require(model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'offset model hash differs')
    theta = _vector(model['coefficients'], DIMENSION, 'coefficients'); saved_gradient = _vector(model['final_gradient'], DIMENSION, 'gradient')
    metadata, gradient, training = numerical_reference(theta, data['matrix'], data['y'], data['weights'], data['base_margin'])
    _equal(model['training'], training, 'training arrays and curvature')
    _exact(model['training']['strong_convexity_lower_bound'], 1., 'fixed strong convexity bound')
    _require(np.allclose(saved_gradient, gradient, atol=ATOL, rtol=RTOL), 'recomputed final gradient differs')
    _require(metadata['gradient_infinity_norm'] <= GRADIENT_LIMIT and np.max(np.abs(saved_gradient)) <= GRADIENT_LIMIT,
        'gradient convergence limit exceeded')
    opt = model['optimization']
    _require(type(opt) is dict and set(opt) == set(metadata)|{'success', 'status', 'message', 'iterations', 'function_evaluations', 'gradient_evaluations', 'accepted'}, 'optimization schema differs')
    _require(opt['success'] is True and opt['accepted'] is True and type(opt['status']) is int and opt['status'] == 0
        and type(opt['message']) is str and type(opt['iterations']) is int and 0 <= opt['iterations'] <= 2000
        and all(type(opt[k]) is int and 1 <= opt[k] <= 15000 for k in ('function_evaluations', 'gradient_evaluations')), 'optimizer status/budget differs')
    for key, value in metadata.items():
        _require(_number(opt[key]) and opt[key] >= 0., 'negative/nonfinite numerical certificate')
        _equal(opt[key], value, 'optimization.'+key)
    _require(opt['gradient_infinity_norm'] <= GRADIENT_LIMIT, 'reported gradient convergence limit exceeded')
    _require(metadata['objective'] <= metadata['initial_objective']+1e-12*max(1., abs(metadata['initial_objective'])), 'objective exceeds zero initialization')
    _require(type(model['runtime']) is dict and set(model['runtime']) == {'python', 'numpy', 'scipy'}
        and all(type(v) is str and v for v in model['runtime'].values()), 'runtime metadata differs')
    return theta


def verify_fold(inputs, fold, models, predictions, train_labels, *, expected_input_fingerprint,
                expected_label_contract, expected_runtime):
    _require(type(fold) is int and fold in range(5) and type(models) is dict and set(models) == set(ARMS), 'five exact arm cells required')
    train = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] != fold]
    held = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] == fold]
    _require(train and held and {e.observation.problem_id for e in train}.isdisjoint({e.observation.problem_id for e in held}), 'problem-held fold boundary differs')
    parent = inputs.parent_folds[fold]
    _require(list(parent.train_example_ids) == [e.example_id for e in train] and list(parent.held_example_ids) == [e.example_id for e in held], 'parent fold training membership differs')
    banks = {e.bank_id: inputs.banks[e.bank_id] for e in train}
    base = {e.bank_id: frozen_base_scores(parent.models['structural_C'], e, banks[e.bank_id]) for e in train}
    coefficients = {}
    for arm in ARMS:
        model = models[arm]
        fields = {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint',
            'label_contract', 'parent_structure_model_sha256', 'pair_metadata', 'offset_model', 'model_sha256'}
        _require(type(model) is dict and set(model) == fields and model['kind'] == 'repair_directed_fold_offset_v1'
            and model['arm'] == arm and type(model['fold']) is int and model['fold'] == fold
            and model['train_example_ids'] == [e.example_id for e in train] and model['held_example_ids'] == [e.example_id for e in held]
            and model['input_fingerprint'] == expected_input_fingerprint
            and model['parent_structure_model_sha256'] == parent.models['structural_C']['model_sha256']
            and model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'fold model identity/source binding differs')
        _equal(model['label_contract'], expected_label_contract, 'external training label contract')
        _equal(model['offset_model']['runtime'], expected_runtime, 'numerical runtime')
        data = reconstruct_pairs(train, banks, train_labels, {e.bank_id: inputs.interactions[arm][e.bank_id] for e in train}, base)
        _equal(model['pair_metadata'], data['metadata'], 'complete pair metadata')
        _equal(parent.models['structural_C']['training'], data['training'], 'parent training pairs')
        coefficients[arm] = verify_offset_certificate(model['offset_model'], data)
    _require(type(predictions) is list and len(predictions) == len(held) and [p['example_id'] for p in predictions] == [e.example_id for e in held], 'held prediction order/coverage differs')
    _require(len(parent.predictions) == len(held) and [p['example_id'] for p in parent.predictions] == [e.example_id for e in held], 'parent prediction order differs')
    for ex, pred, old in zip(held, predictions, parent.predictions):
        bank = inputs.banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]
        bases = {m: frozen_base_scores(parent.models[m], ex, bank) for m in BASELINES[:2]}
        for m in bases: _equal(old['candidate_scores'][m], bases[m], 'parent raw-feature score')
        scores = dict(bases)
        for method, arm, theta_arm in [*((a, a, a) for a in ARMS), ('shared_H_HS', 'HS', 'H'), ('shared_H_Jm', 'Jm', 'H')]:
            # Independent scorer, same fixed float64 dense dot primitive as the
            # score contract. Choice SHA checking is not softened by tolerance.
            residual = inputs.interactions[arm][ex.bank_id].matrix@coefficients[theta_arm]
            scores[method] = {cid: float(bases['structural_C'][cid]+residual[i]) for i, cid in enumerate(ids)}
        noop = next(c.candidate_id for c in bank.candidates if c.is_noop)
        first_attempt = bank.attempts[0]
        first = hashlib.sha256(first_attempt.source).hexdigest() if first_attempt.status == 'success' else noop
        _require(first in ids and old['choices']['first_attempt'] == first and old['choices']['noop'] == noop, 'first/noop source identity differs')
        for name, selected in (('noop', noop), ('first_attempt', first)): scores[name] = {cid: float(cid == selected) for cid in ids}
        _require(all(math.isfinite(v) for cell in scores.values() for v in cell.values()), 'nonfinite held score')
        choices = {m: min(ids, key=lambda cid: (-scores[m][cid], cid)) for m in METHODS}
        diagnostics = {}
        for arm in ('HS', 'Jm'):
            shared = 'shared_H_'+arm
            same = np.array_equal(inputs.interactions['H'][ex.bank_id].matrix, inputs.interactions[arm][ex.bank_id].matrix)
            _require(not same or scores['H'] == scores[shared] and choices['H'] == choices[shared], 'same-feature shared-theta invariant failed')
            diagnostics[arm] = dict(features_identical_exact=same, choice_changed=choices['H'] != choices[shared],
                transition='same' if choices['H'] == choices[shared] else 'to_noop' if choices['H'] == noop
                    else 'from_noop' if choices[shared] == noop else 'edited_to_edited',
                score_difference={cid: scores['H'][cid]-scores[shared][cid] for cid in ids})
        expected = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, problem_id=bank.problem_id,
            fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices, candidate_scores=scores,
            shared_theta_diagnostics=diagnostics, zero_residual_parent_choice_parity=True)
        _equal(pred, expected, 'held prediction')
        for method in BASELINES[:2]: _require(choices[method] == old['choices'][method], 'zero-residual parent choice differs')
    return dict(fold=fold, verified_models=5, held_prefixes=len(held), train_prefixes=len(train))


def _joined_source(row, source):
    return (row['code'].encode('utf-8') == source.source and row['timestamp'] == source.timestamp
        and row['verdict'] == source.verdict and hashlib.sha256(source.source).hexdigest() == source.source_sha256)


def audit_run(inputs, observations, fold_models, predictions, train_labels_by_fold, assessment_labels, report, *,
              expected_input_fingerprint, expected_label_contracts, expected_runtime):
    """Complete320/all25/all11 pure audit after guard-certified label opening."""
    examples = inputs.examples; ids = [e.example_id for e in examples]
    _require(len(ids) == 320 and len(set(ids)) == 320 and len({e.user_id for e in examples}) == 320
        and len({e.bank_id for e in examples}) == 320 and all(e.split == 'train' for e in examples), 'unchanged320 train recipients required')
    _require(type(observations) in (list, tuple) and len(observations) == 320, 'all certified observed rows required')
    _require(type(expected_input_fingerprint) is str and re.fullmatch('[0-9a-f]{64}', expected_input_fingerprint), 'external input fingerprint required')
    observed = {r['example_id']: r for r in observations}
    _require(set(observed) == set(ids) and type(inputs.banks) is dict and set(inputs.banks) == {e.bank_id for e in examples}, 'exact observation/bank coverage required')
    for mapping in (fold_models, train_labels_by_fold, expected_label_contracts, inputs.parent_folds):
        _require(type(mapping) is dict and set(mapping) == set(range(5)) and all(type(k) is int for k in mapping), 'all five exact fold keys required')
    _require(type(inputs.interactions) is dict and set(inputs.interactions) == set(ARMS)
        and all(type(v) is dict and set(v) == set(inputs.banks) for v in inputs.interactions.values()), 'all5 arm/bank coverage required')
    assignment = inputs.assignment['example_fold']
    _require(type(assignment) is dict and set(assignment) == set(ids) and set(assignment.values()) == set(range(5))
        and all(type(v) is int for v in assignment.values()), 'exact full fold membership required')
    cohort = []
    for ex in examples:
        row = observed[ex.example_id]; bank = inputs.banks[ex.bank_id]; current = ex.observation.current
        _require(row['user_id'] == ex.user_id and row['bank_id'] == ex.bank_id and row['problem_id'] == bank.problem_id
            and type(row['fold']) is int and row['fold'] == assignment[ex.example_id]
            and row['current_timestamp'] == current.timestamp and row['current_verdict'] == current.verdict
            and row['current_source_sha256'] == current.source_sha256 and bank.current_source == current.source, 'observed recipient differs')
        for history, sources in ((row['history'], ex.observation.prior), (row['donor_history'], ex.donor_history)):
            _require(len(history) == len(sources) and all(_joined_source(r, s) for r, s in zip(history, sources)), 'observed historical source join differs')
        _require(row['observed_source_ids'] == [s.submission_id for s in (current, *ex.observation.prior)]
            and row['donor_source_ids'] == [s.submission_id for s in ex.donor_history], 'observed source ID join differs')
        verify_interactions(row, bank, {a: inputs.interactions[a][ex.bank_id] for a in ARMS})
        cohort.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, problem_id=bank.problem_id,
            fold=assignment[ex.example_id], candidate_ids=[c.candidate_id for c in bank.candidates],
            noop_candidate_id=next(c.candidate_id for c in bank.candidates if c.is_noop)))
    _require(type(predictions) is list and len(predictions) == 320 and {p['example_id'] for p in predictions} == set(ids), 'all320 predictions required')
    indexed = {p['example_id']: p for p in predictions}; folds = []
    for fold in range(5):
        contract = expected_label_contracts[fold]
        _require(type(contract) is dict and set(contract) == {'expected_sha256', 'expected_fold_assignment_sha256', 'expected_source_binding_sha256'}
            and all(type(v) is str and re.fullmatch('[0-9a-f]{64}', v) for v in contract.values()), 'external label contract invalid')
        _require(contract['expected_fold_assignment_sha256'] == inputs.fold_assignment_sha256
            and contract['expected_source_binding_sha256'] == expected_label_contracts[0]['expected_source_binding_sha256'], 'shared original label binding differs')
        held = [indexed[e.example_id] for e in examples if assignment[e.example_id] == fold]
        folds.append(verify_fold(inputs, fold, fold_models[fold], held, train_labels_by_fold[fold],
            expected_input_fingerprint=expected_input_fingerprint, expected_label_contract=contract, expected_runtime=expected_runtime))
    _require(validate_core_labels(list(assessment_labels.values()), inputs.banks) == assessment_labels, 'assessment core scope differs')
    gate = verify_assessment(cohort, predictions, assessment_labels, report)
    _require(report.get('completed_fits') == 25 and type(report.get('completed_fits')) is int
        and report.get('full_train_refits') == 0 and type(report.get('full_train_refits')) is int
        and report.get('model_promotion') is False, 'no-refit/no-promotion bookkeeping differs')
    shared = {}
    for arm in ('HS', 'Jm'):
        shared[arm] = {}
        for name, equal in (('identical_features', True), ('different_features', False)):
            selected = [p['shared_theta_diagnostics'][arm] for p in predictions if p['shared_theta_diagnostics'][arm]['features_identical_exact'] is equal]
            shared[arm][name] = dict(examples=len(selected), choices_changed=sum(d['choice_changed'] for d in selected),
                **{key: sum(d['transition'] == key for d in selected) for key in ('same', 'edited_to_edited', 'to_noop', 'from_noop')})
    _equal(report.get('shared_theta_diagnostics'), shared, 'shared-theta full diagnostics')
    return dict(verified=True, recipients=320, models=25, methods=11, folds=folds, gate=gate,
        feature_dimension=144, pair_metadata_verified=True, external_provenance_guard_required=True,
        fitting_performed=False, unverified_auxiliary_fields=[],
        guard_owned_checks=['artifact_byte_seals', 'clean_source_and_runtime_ancestry', 'authentic_language_and_donor_join',
            'label_envelope_file_provenance', 'prediction_before_label_process_barrier', 'report.predictions_complete_sha256'],
        not_reconstructed=['optimizer_iteration_trace'],
        floating_tolerance=dict(atol=ATOL, rtol=RTOL, feature_tolerance=FEATURE_TOL, gradient_limit=GRADIENT_LIMIT))


if __name__ == '__main__':
    raise SystemExit('Pure audit API only; no production artifact reading or execution release.')
