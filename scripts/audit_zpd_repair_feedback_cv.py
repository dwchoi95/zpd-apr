"""Independent pure repair-feedback audit; no file I/O, optimizer or release.

The execution guard must verify source closure, pinned parent/support ancestry,
all artifact byte seals and the all-five-fold prediction barrier BEFORE opening
the exact authorized assessment/train labels. This module takes those already
verified objects, does not certify their external origin, and never loads them.
No producer pair builder, offset solver, driver or assessor is imported/called.

Pre-data tolerances: scalar fsum vs BLAS/CSR arithmetic uses atol=rtol=1e-10;
independent conditional moment reconstruction uses atol=rtol=2e-14. Counts,
IDs, array hashes, pair order, choices and rational gates are exact. A numerical
gradient limit of 1e-6 is NOT relaxed by the comparison tolerance. These fixed
roundoff allowances are not learned or changed after an empirical audit failure.
Coefficient optimality is not correctness, ranking stability or causal benefit.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math

import numpy as np
from scipy import sparse

from scripts import zpd_history_action_encoder as semantic
from scripts.zpd_repair_structure import raw_features
from scripts.zpd_repair_feedback_labels import validate_core_labels
from src.repair.pilot_contracts import canonical_hash

ARMS = ('H', 'Jm', 'HS', 'U', 'L')
BASELINES = ('structural_C', 'lexical_C', 'first_attempt')
METHODS = (*ARMS, *BASELINES, 'shared_H_HS', 'shared_H_Jm', 'noop')
METRICS = ('ac_lower', 'ac_upper', 'regression_lower', 'regression_upper')
DIMENSION = 1296
ATOL = RTOL = 1e-10
FEATURE_TOL = 2e-14
GRADIENT_LIMIT = 1e-6
VERDICTS = ('AC', 'CE', 'OTHER', 'RE', 'RESOURCE', 'WA')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _equal(actual, expected, where='value'):
    """Strict types/keys/counts; only floating recomputations get tolerance."""
    if type(expected) is dict:
        _require(type(actual) is dict and set(actual) == set(expected), where+' dictionary differs')
        for k, v in expected.items(): _equal(actual[k], v, where+'.'+str(k))
    elif type(expected) is list:
        _require(type(actual) is list and len(actual) == len(expected), where+' list differs')
        for i, v in enumerate(expected): _equal(actual[i], v, where+f'[{i}]')
    elif type(expected) is float:
        _require(_number(actual) and math.isclose(actual, expected, rel_tol=RTOL, abs_tol=ATOL), where+' number differs')
    else:
        _require(type(actual) is type(expected) and actual == expected, where+' differs')


def _vector(value, n, name):
    _require(type(value) is list and len(value) == n and all(_number(v) for v in value), name+' vector invalid')
    return np.asarray(value, dtype=np.float64)


def _array(value, shape, dtype, name):
    _require(type(value) is np.ndarray and value.shape == shape and value.dtype == np.dtype(dtype)
             and np.isfinite(value).all(), name+' array invalid')


def _sha_arrays(*arrays):
    digest = hashlib.sha256()
    for value in arrays:
        arr = np.ascontiguousarray(value)
        head = json.dumps({'shape': list(arr.shape), 'dtype': arr.dtype.str}, sort_keys=True, separators=(',', ':')).encode()
        for block in (head, arr.tobytes(order='C')):
            digest.update(len(block).to_bytes(8, 'little')); digest.update(block)
    return digest.hexdigest()


def independent_interactions(observed, bank):
    """Observed sources only; exact source-language join is guard-certified.

    The frozen generator declares the current and generated text Python; prior
    languages remain the actual joined language. This is not language detection.
    Semantic edit/mask primitives and deterministic permutation are shared; the
    conditional moments, gating, and flattening are independently reconstructed.
    """
    o = observed
    _require(bank.current_source.decode('utf-8', errors='strict') == o['current_code']
             and bank.problem_id == o['problem_id'], 'observed bank source differs')
    candidate_events = [semantic.encode_edit(o['current_code'], c.source.decode('utf-8', errors='strict'),
                                             'Python', 'Python') for c in bank.candidates]
    values = np.stack([v for v, _ in candidate_events]); masks = np.stack([m for _, m in candidate_events])
    result = {}
    for arm in ARMS:
        history = o['donor_history'] if arm == 'U' else o['history'][-1:] if arm == 'L' else o['history']
        if arm == 'HS': history = [history[i] for i in semantic.permutation_indices(len(history), o['example_id'])]
        sequence = [*history, dict(code=o['current_code'], verdict=o['current_verdict'], language='Python')]
        transitions = []
        for before, after in zip(sequence, sequence[1:]):
            v, m = semantic.encode_edit(before['code'], after['code'], before['language'], after['language'])
            pair = VERDICTS.index(semantic._verdict(before['verdict']))*6 + VERDICTS.index(semantic._verdict(after['verdict']))
            transitions.append((v, m, pair))
        moments = np.zeros((2, 18, 36), dtype=np.float64)
        for weighting in range(2):
            # Conditioning cancels the original global normalization. Original
            # recency positions are retained, including unavailable transitions.
            for event in range(18):
                available = [(i, v[event], pair) for i, (v, m, pair) in enumerate(transitions) if m[event]]
                weights = [1. if weighting == 0 else 1./(len(history)-i) for i, _, _ in available]
                denominator = math.fsum(weights)
                if not denominator: continue
                ymean = math.fsum(w*y for w, (_, y, _) in zip(weights, available))/denominator
                for pair in range(36):
                    if arm == 'Jm':
                        moments[weighting, event, pair] = ymean*math.fsum(w for w, (_, _, p) in zip(weights, available) if p == pair)/denominator
                    else:
                        moments[weighting, event, pair] = math.fsum(w*y for w, (_, y, p) in zip(weights, available) if p == pair)/denominator
        gated = np.zeros((len(values), DIMENSION), dtype=np.float64)
        for i in range(len(values)):
            gated[i] = (moments*(values[i]*masks[i])[None, :, None]/6.).reshape(-1)
        result[arm] = gated
    return values, masks, result


def verify_interactions(observed, bank, supplied):
    values, masks, expected = independent_interactions(observed, bank)
    _require(type(supplied) is dict and set(supplied) == set(ARMS), 'five interaction arms required')
    ids = tuple(c.candidate_id for c in bank.candidates)
    for arm, interaction in supplied.items():
        _require(interaction.candidate_ids == ids, 'interaction candidate order differs')
        _array(interaction.matrix, (len(ids), DIMENSION), 'float64', 'interaction')
        _array(interaction.event_values, (len(ids), 18), 'float64', 'events')
        _array(interaction.event_masks, (len(ids), 18), 'bool', 'masks')
        _require(np.array_equal(values, interaction.event_values) and np.array_equal(masks, interaction.event_masks), 'candidate event/mask differs')
        _require(np.allclose(expected[arm], interaction.matrix, atol=FEATURE_TOL, rtol=FEATURE_TOL), 'history interaction differs')
    return True


def reconstruct_pairs(examples, banks, labels, interactions, base_scores):
    """Independently enumerate ALL stable unequal pairs, including zero phi."""
    ids = [e.example_id for e in examples]; bids = [e.bank_id for e in examples]
    _require(examples and len(ids) == len(set(ids)) and len(bids) == len(set(bids))
             and all(e.split == 'train' for e in examples), 'unique training prefixes required')
    for mapping in (banks, interactions, base_scores):
        _require(type(mapping) is dict and set(mapping) == set(bids), 'exact training bank scope required')
    core = validate_core_labels(list(labels.values()), banks)
    _require(set(labels) == set(core) and labels == core, 'exact core training labels required')
    records = []
    for ex in examples:
        bank = banks[ex.bank_id]; block = interactions[ex.bank_id]; candidates = bank.candidates
        _require(bank.current_source == ex.observation.current.source and bank.problem_id == ex.observation.problem_id,
                 'training bank source differs')
        cids = tuple(c.candidate_id for c in candidates)
        _require(block.candidate_ids == cids and set(base_scores[ex.bank_id]) == set(cids), 'candidate order/base scope differs')
        _array(block.matrix, (len(cids), DIMENSION), 'float64', 'training interaction')
        keys = []
        for cid in cids:
            r = core[ex.bank_id, cid]
            keys.append(None if r['status'] == 'unknown' else (int(r['all_ac']), int(r['loss'] == 0), r['gain']-r['loss']))
        pairs = [(i, j, int(keys[i] > keys[j])) for i in range(len(cids)) for j in range(i+1, len(cids))
                 if keys[i] is not None and keys[j] is not None and keys[i] != keys[j]]
        if pairs: records.append((ex, pairs, sum(k is not None for k in keys)))
    _require(records, 'no unequal stable training pairs')
    prefixes = Counter(ex.user_id for ex, _, _ in records)
    x = []; y = []; weights = []; base = []; pair_ids = []; pair_candidates = []
    for ex, pairs, _ in records:
        block = interactions[ex.bank_id]; scores = base_scores[ex.bank_id]
        for i, j, target in pairs:
            left, right = block.candidate_ids[i], block.candidate_ids[j]
            delta = block.matrix[i]-block.matrix[j]; margin = float(scores[left])-float(scores[right])
            x.extend((delta, -delta)); y.extend((target, 1-target)); base.extend((margin, -margin))
            weights.extend([1/(prefixes[ex.user_id]*len(pairs)*2)]*2)
            pair_ids.extend([ex.example_id]*2); pair_candidates.extend([[left, right], [right, left]])
    w = np.asarray(weights, dtype=np.float64)
    # Both historical floating operations are intentionally reproduced, not
    # algebraically reduced, because the exact weights bytes are certified.
    w *= len(w)/w.sum(); old_mass = float(w.sum()); w = w*(1900./old_mass)
    informative = [e.example_id for e, _, _ in records]; users = {e.user_id for e in examples}
    training = dict(train_prefixes=len(examples), train_users=len(users), informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(examples)-len(records), users=len(prefixes),
        users_without_informative_prefix=len(users-set(prefixes)), ordered_pairs=len(w), pair_example_ids=pair_ids,
        informative_train_example_ids=informative, uninformative_train_example_ids=sorted(set(ids)-set(informative)),
        stable_train_candidates=sum(n for _, _, n in records), weight_normalization='fixed_reference_total_pair_weight',
        reference_pair_weight=1900., sample_weight_sum=float(w.sum()), prior_mean_one_weight_sum=old_mass)
    return dict(matrix=np.stack(x), y=np.asarray(y, dtype=np.int64), weights=w,
                base_margin=np.asarray(base, dtype=np.float64), training=training, pair_candidate_ids=pair_candidates)


def expected_configuration():
    return dict(kind='fixed_repair_feedback_offset_logistic_v1', dimension=1296, C=.1, mirrored_row_mass=1900.,
        intercept=0., fixed_base_margin_coefficient=1., labels='integer_0_1_signed_as_2y_minus_1',
        row_contract='adjacent_exact_feature_offset_label_mirrors_equal_positive_weights',
        matrix_arithmetic='canonical_float64_CSR', regularization='half_squared_L2_interaction_only',
        initialization='all_zero', optimizer='scipy.optimize.minimize_L-BFGS-B', analytic_jacobian=True,
        bounds=None, maxiter=2000, ftol=1e-12, gtol=1e-8, maxcor=10, maxls=20, maxfun=15000,
        final_gradient_infinity_limit=1e-6, mass_rtol=1e-12, mass_atol=1e-12, retries=0, base_margin_optimized=False)


def numerical_reference(theta, x, y, weights, offset):
    """Scalar stable softplus, sigmoid, fsum gradient; no solver invocation."""
    _array(theta, (DIMENSION,), 'float64', 'theta')
    _require(type(x) is np.ndarray and x.ndim == 2 and x.shape[0] > 0, 'nonempty dense raw pair matrix required')
    n = len(x); _array(x, (n, DIMENSION), 'float64', 'matrix')
    _array(y, (n,), 'int64', 'labels'); _array(weights, (n,), 'float64', 'weights'); _array(offset, (n,), 'float64', 'offset')
    _require(n % 2 == 0 and np.isin(y, [0, 1]).all() and (weights > 0).all()
        and math.isclose(math.fsum(weights), 1900., rel_tol=1e-12, abs_tol=1e-12), 'invalid pair labels/mass')
    _require(np.array_equal(x[::2], -x[1::2]) and np.array_equal(y[::2], 1-y[1::2])
        and np.array_equal(weights[::2], weights[1::2]) and np.array_equal(offset[::2], -offset[1::2]), 'pair mirrors differ')
    csr = sparse.csr_matrix(x); csr.eliminate_zeros(); csc = csr.tocsc()
    z = []; factors = []; loss = []; zero_loss = []
    for i in range(n):
        lo, hi = csr.indptr[i:i+2]
        dot = math.fsum(float(v)*float(theta[j]) for v, j in zip(csr.data[lo:hi], csr.indices[lo:hi]))
        signed = 2*int(y[i])-1; margin = signed*(float(offset[i])+dot)
        _require(math.isfinite(margin), 'nonfinite scalar margin')
        sigmoid = math.exp(-margin)/(1+math.exp(-margin)) if margin >= 0 else 1/(1+math.exp(margin))
        factors.append(.1*float(weights[i])*signed*sigmoid)
        loss.append(.1*float(weights[i])*(max(0., -margin)+math.log1p(math.exp(-abs(margin)))))
        initial = signed*float(offset[i]); zero_loss.append(.1*float(weights[i])*(max(0., -initial)+math.log1p(math.exp(-abs(initial)))))
        z.append(margin)
    gradient = np.empty(DIMENSION, dtype=np.float64)
    for j in range(DIMENSION):
        lo, hi = csc.indptr[j:j+2]
        gradient[j] = float(theta[j])-math.fsum(float(v)*factors[i] for v, i in zip(csc.data[lo:hi], csc.indices[lo:hi]))
    squared = [math.fsum(float(v)*float(v) for v in x[i]) for i in range(n)]
    weighted = math.fsum(float(w)*s for w, s in zip(weights, squared))
    data = math.fsum(loss); penalty = .5*math.fsum(float(t)*float(t) for t in theta)
    training = dict(rows=n, unordered_pairs=n//2, positive_rows=int(y.sum()), zero_difference_rows=int((np.diff(csr.indptr) == 0).sum()),
        weight_mass=math.fsum(weights), maximum_row_squared_norm=max(squared), weighted_row_squared_norm_sum=weighted,
        strong_convexity_lower_bound=1., hessian_spectral_upper_bound=1.+.025*weighted,
        input_sha256=dict(features=_sha_arrays(np.asarray(csr.shape, dtype='<i8'), csr.indptr.astype('<i8'),
            csr.indices.astype('<i8'), csr.data.astype('<f8')), labels=_sha_arrays(y.astype('<i8')),
            weights=_sha_arrays(weights.astype('<f8')), base_margin=_sha_arrays(offset.astype('<f8'))))
    return dict(initial_objective=math.fsum(zero_loss), objective=data+penalty, weighted_logistic_loss=data,
        l2_penalty=penalty, gradient_infinity_norm=float(np.max(np.abs(gradient))),
        gradient_l2_norm=math.hypot(*map(float, gradient))), gradient, training


def verify_offset_certificate(model, data):
    fields = {'configuration', 'coefficients', 'final_gradient', 'training', 'optimization', 'runtime', 'model_sha256'}
    _require(type(model) is dict and set(model) == fields, 'offset certificate fields differ')
    _equal(model['configuration'], expected_configuration(), 'configuration')
    _require(model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'offset model hash differs')
    theta = _vector(model['coefficients'], DIMENSION, 'coefficients'); saved_gradient = _vector(model['final_gradient'], DIMENSION, 'gradient')
    meta, gradient, training = numerical_reference(theta, data['matrix'], data['y'], data['weights'], data['base_margin'])
    _equal(model['training'], training, 'training arrays and curvature')
    _require(np.allclose(saved_gradient, gradient, atol=ATOL, rtol=RTOL), 'recomputed final gradient differs')
    _require(meta['gradient_infinity_norm'] <= GRADIENT_LIMIT and np.max(np.abs(saved_gradient)) <= GRADIENT_LIMIT,
             'gradient convergence limit exceeded')
    opt = model['optimization']
    _require(type(opt) is dict and set(opt) == set(meta)|{'success', 'status', 'message', 'iterations', 'function_evaluations', 'gradient_evaluations', 'accepted'}, 'optimization schema differs')
    _require(opt['success'] is True and opt['accepted'] is True and type(opt['status']) is int and opt['status'] == 0
        and type(opt['message']) is str and type(opt['iterations']) is int and 0 <= opt['iterations'] <= 2000
        and all(type(opt[k]) is int and 1 <= opt[k] <= 15000 for k in ('function_evaluations', 'gradient_evaluations')), 'optimizer status/budget differs')
    for key, value in meta.items(): _equal(opt[key], value, 'optimization.'+key)
    _require(meta['objective'] <= meta['initial_objective']+1e-12*max(1., abs(meta['initial_objective'])), 'objective exceeds zero initialization')
    _require(type(model['runtime']) is dict and set(model['runtime']) == {'python', 'numpy', 'scipy'}
        and all(type(v) is str and v for v in model['runtime'].values()), 'runtime metadata differs')
    return theta


def frozen_base_scores(model, example, bank):
    """Only the frozen pure feature encoder is shared, not producer scoring."""
    _require(model['condition'] == 'C' and model['variant'] in ('lexical', 'structural')
        and model['intercept'] == 0 and model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'frozen C base binding differs')
    numeric, hashed = raw_features(example.observation, (), bank, 'C', model['variant'])
    scale = _vector(model['numeric_scale'], numeric.shape[1], 'base scale')
    _require((scale > 0).all(), 'positive frozen scales required')
    coefficient = _vector(model['coefficients'], numeric.shape[1]+hashed.shape[1], 'base coefficients')
    matrix = sparse.hstack([numeric.multiply(1/scale), hashed], format='csr')
    scores = np.asarray(matrix@coefficient).ravel()
    _require(np.isfinite(scores).all(), 'nonfinite frozen base scores')
    return {c.candidate_id: float(v) for c, v in zip(bank.candidates, scores)}


def verify_fold(inputs, fold, models, predictions, train_labels, *, expected_input_fingerprint,
                expected_label_contract, expected_runtime):
    """One complete five-arm fold. External frozen parent seals are guard-owned.

    ``inputs`` is the label-free prepared object; no producer methods are called.
    The caller separately invokes ``verify_interactions`` on certified observed
    language-bearing rows before this function. All training labels must cover
    exactly the non-held banks; unknown/tied/zero-feature pairs are not hidden.
    """
    _require(type(fold) is int and fold in range(5) and type(models) is dict and set(models) == set(ARMS), 'five exact arm cells required')
    train = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] != fold]
    held = [e for e in inputs.examples if inputs.assignment['example_fold'][e.example_id] == fold]
    parent = inputs.parent_folds[fold]
    _require(list(parent.train_example_ids) == [e.example_id for e in train]
        and list(parent.held_example_ids) == [e.example_id for e in held], 'parent fold training membership differs')
    banks = {e.bank_id: inputs.banks[e.bank_id] for e in train}
    base = {e.bank_id: frozen_base_scores(parent.models['structural_C'], e, banks[e.bank_id]) for e in train}
    coefficients = {}
    for arm in ARMS:
        model = models[arm]
        fields = {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint',
            'label_contract', 'parent_structure_model_sha256', 'pair_metadata', 'offset_model', 'model_sha256'}
        _require(type(model) is dict and set(model) == fields and model['kind'] == 'repair_feedback_fold_offset_v1'
            and model['arm'] == arm and type(model['fold']) is int and model['fold'] == fold
            and model['train_example_ids'] == [e.example_id for e in train] and model['held_example_ids'] == [e.example_id for e in held]
            and model['input_fingerprint'] == expected_input_fingerprint
            and model['parent_structure_model_sha256'] == parent.models['structural_C']['model_sha256']
            and model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}), 'fold model identity/source binding differs')
        _equal(model['label_contract'], expected_label_contract, 'external training label contract')
        _equal(model['offset_model']['runtime'], expected_runtime, 'numerical runtime')
        data = reconstruct_pairs(train, banks, train_labels,
            {e.bank_id: inputs.interactions[arm][e.bank_id] for e in train}, base)
        _equal(model['pair_metadata']['training'], data['training'], 'legacy pair metadata')
        _equal(parent.models['structural_C']['training'], data['training'], 'parent training pairs')
        _equal(model['pair_metadata']['pair_candidate_ids'], data['pair_candidate_ids'], 'pair candidate order')
        # Auxiliary pair geometry/coverage is producer diagnostics, not used to
        # establish the objective or gate. Its exact raw arrays are certified.
        coefficients[arm] = verify_offset_certificate(model['offset_model'], data)
    _require(len(predictions) == len(held) and [p['example_id'] for p in predictions] == [e.example_id for e in held], 'held prediction order/coverage differs')
    _require(len(parent.predictions) == len(held) and [p['example_id'] for p in parent.predictions] == [e.example_id for e in held], 'parent prediction order differs')
    for ex, pred, old in zip(held, predictions, parent.predictions):
        bank = inputs.banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]
        bases = {m: frozen_base_scores(parent.models[m], ex, bank) for m in BASELINES[:2]}
        for m in bases: _equal(old['candidate_scores'][m], bases[m], 'parent raw-feature score')
        scores = dict(bases)
        for method, arm, theta_arm in [*((a, a, a) for a in ARMS), ('shared_H_HS', 'HS', 'H'), ('shared_H_Jm', 'Jm', 'H')]:
            matrix = inputs.interactions[arm][ex.bank_id].matrix
            # Same specified float64 dense dot primitive; no producer scorer.
            residual = matrix@coefficients[theta_arm]
            scores[method] = {cid: float(bases['structural_C'][cid]+residual[i]) for i, cid in enumerate(ids)}
        noop = next(c.candidate_id for c in bank.candidates if c.is_noop)
        # Exactly attempt zero; a failed first attempt falls back to no-op,
        # even when a later generation succeeds. Never first successful search.
        first_attempt = bank.attempts[0]
        first = hashlib.sha256(first_attempt.source).hexdigest() if first_attempt.status == 'success' else noop
        _require(first in ids and old['choices']['first_attempt'] == first and old['choices']['noop'] == noop, 'first/noop source identity differs')
        scores['noop'] = {cid: float(cid == noop) for cid in ids}
        scores['first_attempt'] = {cid: float(cid == first) for cid in ids}
        choices = {m: min(ids, key=lambda cid: (-scores[m][cid], cid)) for m in METHODS}
        diagnostics = {}
        for arm in ('HS', 'Jm'):
            shared = 'shared_H_'+arm; same = np.array_equal(inputs.interactions['H'][ex.bank_id].matrix, inputs.interactions[arm][ex.bank_id].matrix)
            _require(not same or scores['H'] == scores[shared] and choices['H'] == choices[shared], 'same-feature shared-theta invariant failed')
            diagnostics[arm] = dict(features_identical_exact=same, choice_changed=choices['H'] != choices[shared],
                transition='same' if choices['H'] == choices[shared] else 'to_noop' if choices['H'] == noop
                    else 'from_noop' if choices[shared] == noop else 'edited_to_edited',
                score_difference={cid: scores['H'][cid]-scores[shared][cid] for cid in ids})
        expected = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, problem_id=bank.problem_id,
            fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices, candidate_scores=scores,
            shared_theta_diagnostics=diagnostics, zero_residual_parent_choice_parity=True)
        # Score tolerances never alter choice checking: chosen SHA is exact.
        _equal(pred, expected, 'held prediction')
        for m in BASELINES[:2]: _require(choices[m] == old['choices'][m], 'zero-residual parent choice differs')
    return dict(fold=fold, verified_models=5, held_prefixes=len(held), train_prefixes=len(train))


def audit_run(inputs, observations, fold_models, predictions, train_labels_by_fold, assessment_labels, report, *,
              expected_input_fingerprint, expected_label_contracts, expected_runtime):
    """Pure complete320/all25/all11 audit after the external opening barrier.

    Raw model/prediction/source byte seals, original parent configuration/seals,
    authentic fold assignment/source-language/donor joins, exact label-envelope
    validation, and process opening order are the production guard's obligations.
    This function is not a production loader or permission to open new outcomes.
    """
    examples = inputs.examples; ids = [e.example_id for e in examples]
    _require(len(ids) == 320 and len(set(ids)) == 320 and len({e.user_id for e in examples}) == 320
        and len({e.bank_id for e in examples}) == 320 and all(e.split == 'train' for e in examples), 'unchanged320 train recipients required')
    _require(type(observations) in (list, tuple) and len(observations) == 320, 'all certified language-bearing observations required')
    observed = {r['example_id']: r for r in observations}
    _require(set(observed) == set(ids) and set(inputs.banks) == {e.bank_id for e in examples}, 'exact observation/bank coverage required')
    for mapping in (fold_models, train_labels_by_fold, expected_label_contracts, inputs.parent_folds):
        _require(type(mapping) is dict and set(mapping) == set(range(5)) and all(type(k) is int for k in mapping), 'all five exact fold keys required')
    _require(set(inputs.interactions) == set(ARMS) and all(set(v) == set(inputs.banks) for v in inputs.interactions.values()), 'all5 arm/bank coverage required')
    assignment = inputs.assignment['example_fold']
    _require(set(assignment) == set(ids) and set(assignment.values()) == set(range(5))
        and all(type(v) is int for v in assignment.values()), 'exact full fold membership required')
    cohort = []
    for ex in examples:
        row = observed[ex.example_id]; bank = inputs.banks[ex.bank_id]
        _require(row['user_id'] == ex.user_id and row['bank_id'] == ex.bank_id and row['problem_id'] == bank.problem_id, 'observed recipient differs')
        verify_interactions(row, bank, {a: inputs.interactions[a][ex.bank_id] for a in ARMS})
        cohort.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, problem_id=bank.problem_id,
            fold=assignment[ex.example_id], candidate_ids=[c.candidate_id for c in bank.candidates],
            noop_candidate_id=next(c.candidate_id for c in bank.candidates if c.is_noop)))
    _require(type(predictions) is list and len(predictions) == 320 and {p['example_id'] for p in predictions} == set(ids), 'all320 predictions required')
    indexed = {p['example_id']: p for p in predictions}; folds = []
    for f in range(5):
        held_predictions = [indexed[e.example_id] for e in examples if assignment[e.example_id] == f]
        folds.append(verify_fold(inputs, f, fold_models[f], held_predictions, train_labels_by_fold[f],
            expected_input_fingerprint=expected_input_fingerprint, expected_label_contract=expected_label_contracts[f], expected_runtime=expected_runtime))
    _require(validate_core_labels(list(assessment_labels.values()), inputs.banks) == assessment_labels, 'assessment core scope differs')
    gate = verify_assessment(cohort, predictions, assessment_labels, report)
    _require(report.get('completed_fits') == 25 and type(report.get('completed_fits')) is int
        and report.get('full_train_refits') == 0 and type(report.get('full_train_refits')) is int
        and report.get('model_promotion') is False, 'no-refit/no-promotion bookkeeping differs')
    shared = {}
    for arm in ('HS', 'Jm'):
        shared[arm] = {}
        for name, equal in (('identical_features', True), ('different_features', False)):
            selected = [p['shared_theta_diagnostics'][arm] for p in predictions
                        if p['shared_theta_diagnostics'][arm]['features_identical_exact'] is equal]
            shared[arm][name] = dict(examples=len(selected), choices_changed=sum(d['choice_changed'] for d in selected),
                **{transition: sum(d['transition'] == transition for d in selected)
                   for transition in ('same', 'edited_to_edited', 'to_noop', 'from_noop')})
    _equal(report.get('shared_theta_diagnostics'), shared, 'shared-theta full diagnostics')
    return dict(verified=True, recipients=320, models=25, methods=11, folds=folds, gate=gate,
        external_provenance_guard_required=True, fitting_performed=False,
        unverified_auxiliary_fields=['pair_metadata.banks', 'pair_metadata.all_pair_counts', 'pair_metadata.informative_pair_counts'],
        floating_tolerance=dict(atol=ATOL, rtol=RTOL, feature_tolerance=FEATURE_TOL, gradient_limit=GRADIENT_LIMIT))


def _fraction(f):
    return dict(numerator=f.numerator, denominator=f.denominator, value=float(f))


def _serialize(value):
    if isinstance(value, Fraction): return _fraction(value)
    if isinstance(value, dict): return {k: _serialize(v) for k, v in value.items()}
    return value


def independent_assessment(cohort, predictions, labels):
    """Recompute all 11 methods and the exact rational frozen repair gate."""
    required = {'example_id', 'user_id', 'bank_id', 'problem_id', 'fold', 'candidate_ids', 'noop_candidate_id'}
    _require(type(cohort) is list and cohort and all(type(r) is dict and set(r) == required for r in cohort), 'cohort schema differs')
    by_id = {r['example_id']: r for r in cohort}
    _require(len(by_id) == len(cohort) and len({r['bank_id'] for r in cohort}) == len(cohort)
        and len({r['user_id'] for r in cohort}) == len(cohort), 'duplicate cohort identity')
    _require({r['fold'] for r in cohort} == set(range(5)) and all(type(r['fold']) is int for r in cohort), 'five exact folds required')
    problem_fold = {}
    for row in cohort:
        _require(problem_fold.setdefault(row['problem_id'], row['fold']) == row['fold'], 'problem crosses folds')
        _require(type(row['candidate_ids']) is list and len(set(row['candidate_ids'])) == len(row['candidate_ids'])
            and row['noop_candidate_id'] in row['candidate_ids'], 'candidate coverage differs')
    _require(type(labels) is dict and set(labels) == {(r['bank_id'], c) for r in cohort for c in r['candidate_ids']}, 'exact full label scope required')
    for key, label in labels.items():
        _require(type(label) is dict and set(label) == {'bank_id', 'candidate_id', 'status', 'gain', 'loss', 'all_ac'}
            and (label['bank_id'], label['candidate_id']) == key, 'label identity differs')
        if label['status'] == 'unknown': _require(all(label[k] is None for k in ('gain', 'loss', 'all_ac')), 'unknown lost')
        else: _require(label['status'] == 'stable' and type(label['all_ac']) is bool
            and all(_number(label[k]) and 0 <= label[k] <= 1 for k in ('gain', 'loss'))
            and label['gain']+label['loss'] <= 1+1e-12 and (not label['all_ac'] or label['loss'] == 0), 'invalid stable label')
    pred_ids = [p['example_id'] for p in predictions]
    _require(len(pred_ids) == len(set(pred_ids)) and set(pred_ids) == set(by_id), 'prediction cohort differs')
    for p in predictions:
        row = by_id[p['example_id']]
        _require(all(type(p[k]) is type(row[k]) and p[k] == row[k] for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold'))
            and set(p['choices']) == set(METHODS) and all(c in row['candidate_ids'] for c in p['choices'].values())
            and p['choices']['noop'] == row['noop_candidate_id'], 'prediction identity/choice differs')
        noop = labels[row['bank_id'], row['noop_candidate_id']]
        _require(noop['status'] == 'unknown' or noop['gain'] == noop['loss'] == 0, 'stable no-op evidence differs')
    def summarize(rows):
        def cell(rows, method):
            chosen = [labels[p['bank_id'], p['choices'][method]] for p in rows]
            n = len(rows); a = sum(r['status'] == 'stable' and r['all_ac'] for r in chosen)
            u = sum(r['status'] == 'unknown' for r in chosen); reg = sum(r['status'] == 'stable' and r['loss'] > 0 for r in chosen)
            return dict(examples=n, evaluable=bool(n), counts=dict(stable_ac=a, stable_regression=reg, unknown=u,
                noop_selected=sum(p['choices'][method] == p['choices']['noop'] for p in rows)),
                fractions=dict(zip(METRICS, map(lambda k: Fraction(k, n), (a, a+u, reg, reg+u)))) if n else None)
        pids = sorted({p['problem_id'] for p in rows})
        per_problem = {pid: {m: cell([p for p in rows if p['problem_id'] == pid], m) for m in METHODS} for pid in pids}
        return dict(examples=len(rows), problems=len(pids), results={m: cell(rows, m) for m in METHODS},
            problem_results=per_problem, equal_problem={m: {k: sum((per_problem[p][m]['fractions'][k] for p in pids), Fraction())/len(pids)
                for k in METRICS} for m in METHODS} if pids else None)
    def compare(group, control, strict=True, equal=True):
        if not group['examples']: return dict(evaluable=False, passed=False, checks={})
        views = {'pooled': {m: group['results'][m]['fractions'] for m in METHODS}}
        if equal: views['equal_problem'] = group['equal_problem']
        checks = {}
        for key, values in views.items():
            h, other = values['H'], values[control]
            checks[key+'_ac'] = h['ac_lower'] > other['ac_lower'] if strict else h['ac_lower'] >= other['ac_lower']
            for k in ('regression_lower', 'regression_upper'): checks[key+'_'+k] = h[k] <= other[k]
        return dict(evaluable=True, passed=all(checks.values()), checks=checks)
    full = summarize(predictions); folds = {str(f): summarize([p for p in predictions if p['fold'] == f]) for f in range(5)}
    groups = {name: [] for name in ('known_ac', 'known_nonac', 'unknown')}
    for p in predictions:
        row = labels[p['bank_id'], p['choices']['noop']]
        groups['unknown' if row['status'] == 'unknown' else 'known_ac' if row['all_ac'] else 'known_nonac'].append(p)
    subgroup = {k: summarize(v) for k, v in groups.items()}
    subgroup_folds = {k: {str(f): summarize([p for p in v if p['fold'] == f]) for f in range(5)} for k, v in groups.items()}
    nonworse = {m: sum(f['results']['H']['fractions']['ac_lower'] >= f['results'][m]['fractions']['ac_lower'] for f in folds.values())
                for m in (*BASELINES[:2], *ARMS[1:])}
    baseline = {m: compare(full, m) for m in BASELINES}; mechanism = {m: compare(full, m, equal=False) for m in ARMS[1:]}
    nonac = compare(subgroup['known_nonac'], 'structural_C'); ac = compare(subgroup['known_ac'], 'structural_C', strict=False)
    improvement = all(c['passed'] for c in baseline.values()) and nonac['passed'] and ac['passed'] and all(nonworse[m] >= 4 for m in BASELINES[:2])
    contribution = all(c['passed'] and nonworse[m] >= 4 for m, c in mechanism.items())
    transitions = {}
    for method in METHODS[1:]:
        counts = dict(examples=len(predictions), selected_candidate_changed=0, ac_gained=0, ac_lost=0,
            regression_prevented=0, regression_introduced=0, not_jointly_known=0, edited_to_edited=0, to_noop=0, from_noop=0)
        for p in predictions:
            h, c, noop = (p['choices'][k] for k in ('H', method, 'noop'))
            if h != c:
                counts['selected_candidate_changed'] += 1; counts['to_noop' if h == noop else 'from_noop' if c == noop else 'edited_to_edited'] += 1
            a, b = labels[p['bank_id'], h], labels[p['bank_id'], c]
            if a['status'] == 'unknown' or b['status'] == 'unknown': counts['not_jointly_known'] += 1
            else:
                counts['ac_gained'] += a['all_ac'] and not b['all_ac']; counts['ac_lost'] += b['all_ac'] and not a['all_ac']
                counts['regression_prevented'] += a['loss'] == 0 and b['loss'] > 0; counts['regression_introduced'] += a['loss'] > 0 and b['loss'] == 0
        transitions[method] = counts
    return _serialize(dict(kind='prospective_feedback_repair_gate_v1', primary='H', methods=list(METHODS), full=full,
        folds=folds, current_status_subgroups=subgroup, current_status_subgroup_folds=subgroup_folds,
        primary_transitions=transitions, gate=dict(actual_repair_improvement=bool(improvement), mechanism_contribution=bool(contribution),
            passed=bool(improvement and contribution), baseline_checks=baseline, known_nonac_check=nonac, known_ac_check=ac,
            mechanism_checks=mechanism, nonworse_full_folds=nonworse, required_nonworse_folds=4,
            learned_controls_may_replace_primary=False, confirmatory=False, educational_benefit_established=False,
            unknown_bounds_are_confidence_intervals=False), exclusions=0,
        note='Adaptive fixed-bank development; exact fractions gate all retained recipients.'))


def verify_assessment(cohort, predictions, labels, report):
    expected = independent_assessment(cohort, predictions, labels)
    _require(set(expected).issubset(report), 'assessment required fields missing')
    # Fractions numerator/denominator and gate booleans are compared exactly.
    _equal({k: report[k] for k in expected}, expected, 'assessment')
    return expected['gate']


if __name__ == '__main__':
    raise SystemExit('Pure audit API only: no production artifact reading or execution release.')
