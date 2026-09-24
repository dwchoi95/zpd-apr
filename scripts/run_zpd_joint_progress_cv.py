"""Own-fold joint4131 engine, without a production CLI or empirical release.

Only the externally pinned own training-label envelope is opened. Source-only
capsule authentication, clean-source/runtime checks, global prediction sealing
and assessment are separate trusted-coordinator duties. The shared scaler is
fit once from own training candidates and never from held candidates/labels.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from scripts import zpd_joint_progress_newton as solver
from scripts import zpd_joint_progress_assessment as assessment
from scripts import zpd_repair_feedback_labels as labels
from scripts.run_zpd_repair_feedback_cv import LabelContract, _runtime
from scripts.run_zpd_repair_progress_cv import canonical, sha, write, contract_values
from src.repair.pilot_contracts import canonical_hash

SPEC = solver.ResidualSpec(features.VERSION, features.DIMENSION,
    canonical_hash(features.configuration()), solver.KIND)
ARMS = features.ARMS
METHODS = assessment.METHODS
MODEL_KIND = 'joint_current_progress4131_fold_ranker_v1'
SCALER_KIND = 'joint_current_own_training_transform_v1'
FILES = (*(arm+'.json' for arm in ARMS), 'SCALER.json', 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json')
TRANSFORM_FIELDS = {'kind', 'numeric_scale', 'numeric_mean', 'numeric_variance', 'scaler_candidate_ids',
    'scaler_weights', 'bank_candidate_ids', 'row_keys', 'y', 'weights', 'training'}


def _require(condition, message):
    if not condition: raise ValueError(message)


def transform_payload(transform):
    """Detached own-training transform; never part of a source-only input job."""
    _require(type(transform) is features.OwnTransform, 'exact own transform required')
    transform.__post_init__()
    return dict(kind=SCALER_KIND, numeric_scale=transform.numeric_scale.tolist(),
        numeric_mean=transform.numeric_mean.tolist(), numeric_variance=transform.numeric_variance.tolist(),
        scaler_candidate_ids=[list(key) for key in transform.scaler_candidate_ids],
        scaler_weights=transform.scaler_weights.tolist(),
        bank_candidate_ids=[[bid, list(ids)] for bid, ids in transform.bank_candidate_ids],
        row_keys=[list(key) for key in transform.row_keys], y=transform.y.tolist(),
        weights=transform.weights.tolist(), training=transform.training)


def decode_transform(value):
    _require(type(value) is dict and set(value) == TRANSFORM_FIELDS and value['kind'] == SCALER_KIND,
        'strict saved own transform schema required')
    for name in ('numeric_scale', 'numeric_mean', 'numeric_variance', 'scaler_weights', 'weights'):
        _require(type(value[name]) is list and all(type(v) is float and math.isfinite(v) for v in value[name]),
            'exact finite float lists required')
    for name, width in (('scaler_candidate_ids', 2), ('row_keys', 3)):
        _require(type(value[name]) is list and all(type(row) is list and len(row) == width
            and all(type(v) is str and v for v in row) for row in value[name]), 'strict own row identities required')
    _require(type(value['bank_candidate_ids']) is list and all(type(row) is list and len(row) == 2
        and type(row[0]) is str and row[0] and type(row[1]) is list
        and all(type(v) is str for v in row[1]) for row in value['bank_candidate_ids']), 'strict bank scopes required')
    _require(type(value['y']) is list and all(type(v) is int and v in (0, 1) for v in value['y']),
        'strict mirrored integer targets required')
    result = features.OwnTransform(*(np.asarray(value[name], dtype=np.float64)
        for name in ('numeric_scale', 'numeric_mean', 'numeric_variance')),
        tuple(tuple(row) for row in value['scaler_candidate_ids']), np.asarray(value['scaler_weights'], dtype=np.float64),
        tuple((bid, tuple(ids)) for bid, ids in value['bank_candidate_ids']),
        tuple(tuple(row) for row in value['row_keys']), np.asarray(value['y'], dtype=np.int64),
        np.asarray(value['weights'], dtype=np.float64), json.dumps(value['training'], sort_keys=True, allow_nan=False))
    _require(canonical_hash(transform_payload(result)) == canonical_hash(value), 'lossless own transform required')
    return result


def validate_transform(transform, inputs):
    """Scope/parity only; independent audit must replay own-label scaler fitting."""
    payload = transform_payload(transform); train, _ = capsule.scope(inputs)
    _require(transform.bank_candidate_ids == tuple((ex.bank_id,
        tuple(c.candidate_id for c in inputs.banks[ex.bank_id].candidates)) for ex in train),
        'exact original own-training bank/candidate order required')
    _require(capsule._same(transform.training, inputs.parent_training),
        'own-fold original pair membership and weighting parity required')
    return canonical_hash(payload)


def _pair_summary(matrix, weights):
    numeric = matrix.copy(); numeric.eliminate_zeros()
    zero = np.asarray(numeric.getnnz(axis=1)).ravel() == 0
    return dict(mirrored_rows=matrix.shape[0], stable_unequal_pairs=matrix.shape[0]//2,
        exact_zero_difference_rows=int(zero.sum()),
        exact_zero_difference_natural_weight_mass=math.fsum(map(float, weights[zero])),
        natural_weight_mass=math.fsum(map(float, weights)), zero_difference_pairs_retained=True)


def _model(inputs, arm, matrix, weights, fitted, contract, transform):
    train, held = capsule.scope(inputs)
    value = dict(kind=MODEL_KIND, arm=arm, fold=inputs.fold,
        train_example_ids=[ex.example_id for ex in train], held_example_ids=[ex.example_id for ex in held],
        input_fingerprint=capsule.fingerprint(inputs), label_contract=contract_values(contract, inputs),
        parent_structure_model_sha256=inputs.parent_structure_model_sha256,
        readiness_complete_sha256=inputs.readiness_complete_sha256,
        transform_sha256=validate_transform(transform, inputs), training=transform.training,
        pair_summary=_pair_summary(matrix, weights), joint_model=fitted)
    value['model_sha256'] = canonical_hash(value)
    return value


def validate_model(model, inputs, arm, transform):
    fields = {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint',
        'label_contract', 'parent_structure_model_sha256', 'readiness_complete_sha256',
        'transform_sha256', 'training', 'pair_summary', 'joint_model', 'model_sha256'}
    train, held = capsule.scope(inputs)
    _require(type(model) is dict and set(model) == fields and model['kind'] == MODEL_KIND
        and type(model['fold']) is int and model['fold'] == inputs.fold and arm in ARMS and model['arm'] == arm
        and model['train_example_ids'] == [ex.example_id for ex in train]
        and model['held_example_ids'] == [ex.example_id for ex in held]
        and model['input_fingerprint'] == capsule.fingerprint(inputs)
        and model['parent_structure_model_sha256'] == inputs.parent_structure_model_sha256
        and model['readiness_complete_sha256'] == inputs.readiness_complete_sha256
        and model['transform_sha256'] == validate_transform(transform, inputs)
        and capsule._same(model['training'], transform.training)
        and model['model_sha256'] == canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'}),
        'exact own joint model, transform and source identity required')
    contract_values(LabelContract(**model['label_contract']), inputs)
    theta = solver.validate_model(model['joint_model'], expected_spec=SPEC)
    info = model['pair_summary']; numeric = model['joint_model']['training']
    _require(type(info) is dict and set(info) == {'mirrored_rows', 'stable_unequal_pairs',
        'exact_zero_difference_rows', 'exact_zero_difference_natural_weight_mass', 'natural_weight_mass',
        'zero_difference_pairs_retained'}
        and all(type(info[key]) is int for key in ('mirrored_rows', 'stable_unequal_pairs', 'exact_zero_difference_rows'))
        and info['mirrored_rows'] == numeric['rows'] == transform.training['ordered_pairs']
        and info['stable_unequal_pairs'] == numeric['unordered_pairs']
        and info['exact_zero_difference_rows'] == numeric['zero_difference_rows']
        and info['zero_difference_pairs_retained'] is True
        and all(type(info[key]) is float and math.isfinite(info[key]) for key in
            ('natural_weight_mass', 'exact_zero_difference_natural_weight_mass'))
        and 0. <= info['exact_zero_difference_natural_weight_mass'] <= info['natural_weight_mass']
        and math.isclose(info['natural_weight_mass'], 1900., rel_tol=1e-12, abs_tol=1e-12)
        and (info['exact_zero_difference_rows'] != 0 or info['exact_zero_difference_natural_weight_mass'] == 0.),
        'strict original mirrored-pair mass and zero-row diagnostics required')
    start = 4099 if arm == 'C_joint' else 4115 if arm == 'CF' else 4131
    _require(not np.any(theta[start:]) and not np.any(model['joint_model']['final_gradient'][start:]),
        'nested zero columns must have exact zero optimum/gradient')
    return theta


def predict_fold(inputs, models, transform):
    """Held source-only scores; shared controls fix every H coefficient."""
    capsule.validate_inputs(inputs)
    _require(type(models) is dict and set(models) == set(ARMS), 'all seven own models required')
    thetas = {arm: validate_model(models[arm], inputs, arm, transform) for arm in ARMS}
    _require(all(capsule._same(models[arm]['label_contract'], models['H']['label_contract']) for arm in ARMS),
        'all seven models must share the same own training-label contract')
    _, held = capsule.scope(inputs); predictions = []
    for ex, parent in zip(held, inputs.parent_predictions, strict=True):
        bank = inputs.banks[ex.bank_id]; ids = tuple(c.candidate_id for c in bank.candidates)
        blocks = features.compose_blocks(inputs.raw_current[ex.bank_id], transform,
            {arm: inputs.interactions[arm][ex.bank_id] for arm in features.PROGRESS_ARMS})
        def score(arm, theta):
            values = np.asarray(blocks[arm].matrix@theta).ravel()
            _require(np.isfinite(values).all(), 'finite joint candidate scores required')
            return {cid: float(v) for cid, v in zip(ids, values, strict=True)}
        scores = {arm: score(arm, thetas[arm]) for arm in ARMS}
        for arm in ('HS', 'Jm', 'CF'): scores['shared_H_'+arm] = score(arm, thetas['H'])
        for name in ('structural_C', 'lexical_C'): scores[name] = dict(parent['candidate_scores'][name])
        for name in ('first_attempt', 'noop'): scores[name] = {cid: float(cid == parent['choices'][name]) for cid in ids}
        choices = {name: min(scores[name], key=lambda cid: (-scores[name][cid], cid)) for name in METHODS}
        diagnostics = {}
        for arm in ('HS', 'Jm', 'CF'):
            name = 'shared_H_'+arm
            identical = np.array_equal(blocks['H'].progress, blocks[arm].progress)
            if identical:
                _require(scores['H'] == scores[name] and choices['H'] == choices[name],
                    'identical inputs and full H coefficients must reproduce scores')
            diagnostics[arm] = dict(features_identical_exact=identical, choice_changed=choices['H'] != choices[name],
                transition='same' if choices['H'] == choices[name] else 'to_noop' if choices['H'] == choices['noop']
                    else 'from_noop' if choices[name] == choices['noop'] else 'edited_to_edited',
                score_difference={cid: scores['H'][cid]-scores[name][cid] for cid in ids})
        predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            problem_id=bank.problem_id, fold=inputs.fold, bank_seal_sha256=bank.seal_sha256,
            choices=choices, candidate_scores=scores, shared_theta_diagnostics=diagnostics,
            direct_history_diagnostic_holds_all_current_coefficients_fixed=True))
    return predictions


def fit_fold(inputs, label_directory, contract, output, *, recheck):
    """One own envelope, one scaler, seven fits; no resume, retries or fallback."""
    capsule.validate_inputs(inputs)
    _require(callable(recheck), 'external own-worker authority recheck required')
    args = contract_values(contract, inputs); fingerprint = capsule.fingerprint(inputs); runtime = _runtime()
    output = canonical(output)
    _require(not output.exists(), 'fresh own-fold output required; no overwrite or retry')
    recheck(); output.mkdir(parents=True, exist_ok=False); completed = 0; expected = {}
    def save(name, value): expected[name] = write(output/name, value)
    def input_barrier():
        recheck()
        _require(capsule.fingerprint(inputs) == fingerprint and _runtime() == runtime, 'own inputs/runtime changed')
        _require(sha(label_path) == contract.expected_sha256, 'own training-label file changed')
    def artifact_barrier(complete_sha=None):
        inventory = set(FILES) | ({'COMPLETE.json'} if complete_sha is not None else set())
        _require({p.name for p in output.iterdir()} == inventory and set(expected) == set(FILES),
            'exact own output inventory required')
        _require(all(sha(output/name) == pin for name, pin in expected.items()), 'own output changed before completion')
        if complete_sha is not None:
            _require(sha(output/'COMPLETE.json') == complete_sha, 'consumed own completion marker changed')
    try:
        train, held = capsule.scope(inputs); train_banks = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
        label_directory = canonical(label_directory); label_path = canonical(label_directory/f'fold-{inputs.fold}/train-labels.json')
        own_labels = labels.load_fold_labels(label_directory, inputs.fold, train_banks,
            {ex.example_id: ex.bank_id for ex in train}, **args)
        transform = features.fit_own_scaler(train, train_banks,
            {ex.bank_id: inputs.raw_current[ex.bank_id] for ex in train}, own_labels)
        validate_transform(transform, inputs); save('SCALER.json', transform_payload(transform))
        train_blocks = {ex.bank_id: features.compose_blocks(inputs.raw_current[ex.bank_id], transform,
            {arm: inputs.interactions[arm][ex.bank_id] for arm in features.PROGRESS_ARMS}) for ex in train}
        del own_labels
        models = {}
        for arm in ARMS:
            input_barrier()
            matrix, y, weights, _ = features.mirrored_pairs(transform,
                {ex.bank_id: train_blocks[ex.bank_id][arm] for ex in train})
            fitted = solver.fit_joint(matrix, y, weights, spec=SPEC)
            model = _model(inputs, arm, matrix, weights, fitted, contract, transform)
            validate_model(model, inputs, arm, transform); models[arm] = model
            save(arm+'.json', model); completed += 1
            print(json.dumps(dict(phase='fitting', fold=inputs.fold, completed_fits=completed, total_fits=7,
                train_examples=len(train), predicted_examples=0, total_held_examples=len(held))), flush=True)
        save('MODELS_COMPLETE.json', dict(fold=inputs.fold,
            model_files_sha256={arm+'.json': expected[arm+'.json'] for arm in ARMS},
            scaler_file_sha256=expected['SCALER.json'], transform_sha256=validate_transform(transform, inputs),
            train_example_ids=[ex.example_id for ex in train], held_example_ids=[ex.example_id for ex in held],
            input_fingerprint=fingerprint, label_contract=args))
        del train_blocks, matrix, y, weights
        input_barrier()
        predictions = predict_fold(inputs, models, transform); save('predictions.json', predictions)
        save('STATUS.json', dict(phase='complete', fold=inputs.fold, completed_fits=7, total_fits=7,
            predicted_examples=len(held), total_held_examples=len(held)))
        input_barrier(); artifact_barrier(); input_barrier(); artifact_barrier(); input_barrier(); artifact_barrier()
        complete_sha = write(output/'COMPLETE.json', dict(status='complete', kind='joint_progress4131_fold_complete_v1',
            fold=inputs.fold, completed_fits=7, predicted_examples=len(held), input_fingerprint=fingerprint,
            files_sha256=dict(expected), automatic_retries=0))
        input_barrier(); artifact_barrier(complete_sha); input_barrier(); artifact_barrier(complete_sha)
        return predictions
    except BaseException as error:
        marker = output/'COMPLETE.json'
        if marker.exists():
            rejected = canonical(output/'REJECTED_COMPLETE.json')
            _require(not rejected.exists(), 'rejected own completion already exists')
            marker.rename(rejected)
        body = dict(status='failed', error_type=type(error).__name__, error=str(error), completed_fits=completed,
            retry_authorized=False)
        if hasattr(error, 'diagnostics'): body['diagnostics'] = error.diagnostics
        if hasattr(error, 'metadata'): body['pair_metadata'] = error.metadata
        write(output/'FAILED.json', body)
        raise


if __name__ == '__main__':
    raise SystemExit('No production CLI: an independently reviewed fixed release and coordinator are required.')
