"""Own-capsule progress32 fold engine; no direct production CLI or release.

Only this fold's externally bound training-label file is read. Source and
feature projection, capsule authentication and global prediction/assessment
barriers belong to the separately reviewed coordinator. This worker never
loads an old global parent, another fold, a release or a run-wide manifest.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np

from scripts import zpd_repair_progress_capsule as capsule
from scripts import zpd_repair_progress_newton as solver
from scripts import zpd_repair_progress_assessment as assessment
from scripts import zpd_repair_feedback_labels as labels
from scripts.run_zpd_repair_feedback_cv import LabelContract, _scope, _runtime, _hash
from src.repair.pilot_contracts import canonical_hash

SPEC = capsule.SPEC
ARMS = capsule.ARMS
METHODS = assessment.METHODS
MODEL_KIND = 'statement_progress32_fold_offset_v1'
FILES = (*(arm+'.json' for arm in ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json')


def canonical(path):
    value = Path(path).absolute()
    if value.resolve() != value: raise ValueError('canonical nonaliased path required')
    return value


def sha(path):
    with canonical(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    data = (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)+'\n').encode('ascii')
    with canonical(path).open('xb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    return hashlib.sha256(data).hexdigest()


def contract_values(contract, inputs):
    if type(contract) is not LabelContract or contract.expected_fold_assignment_sha256 != inputs.fold_assignment_sha256:
        raise ValueError('own externally authenticated fold label contract required')
    for value in vars(contract).values(): _hash(value)
    return dict(vars(contract))


def _pair_summary(data):
    zero = ~np.any(data.matrix != 0., axis=1)
    return dict(mirrored_rows=len(data.y), stable_unequal_pairs=len(data.y)//2,
                exact_zero_difference_rows=int(zero.sum()),
                exact_zero_difference_natural_weight_mass=math.fsum(map(float, data.weights[zero])),
                natural_weight_mass=math.fsum(map(float, data.weights)),
                zero_difference_pairs_retained=True)


def _model(inputs, arm, data, fitted, contract):
    train, held = _scope(inputs, inputs.fold)
    value = dict(kind=MODEL_KIND, arm=arm, fold=inputs.fold,
        train_example_ids=[ex.example_id for ex in train], held_example_ids=[ex.example_id for ex in held],
        input_fingerprint=capsule.fingerprint(inputs), label_contract=contract_values(contract, inputs),
        parent_structure_model_sha256=inputs.parent_structure_model_sha256,
        readiness_complete_sha256=inputs.readiness_complete_sha256,
        pair_metadata=data.metadata, pair_summary=_pair_summary(data), offset_model=fitted)
    value['model_sha256'] = canonical_hash(value)
    return value


def validate_model(model, inputs, arm):
    fields = {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint',
              'label_contract', 'parent_structure_model_sha256', 'readiness_complete_sha256',
              'pair_metadata', 'pair_summary', 'offset_model', 'model_sha256'}
    train, held = _scope(inputs, inputs.fold)
    if (type(model) is not dict or set(model) != fields or model['kind'] != MODEL_KIND
            or type(model['fold']) is not int or model['fold'] != inputs.fold or model['arm'] != arm or arm not in ARMS
            or model['train_example_ids'] != [e.example_id for e in train]
            or model['held_example_ids'] != [e.example_id for e in held]
            or model['input_fingerprint'] != capsule.fingerprint(inputs)
            or model['parent_structure_model_sha256'] != inputs.parent_structure_model_sha256
            or model['readiness_complete_sha256'] != inputs.readiness_complete_sha256
            or model['model_sha256'] != canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})):
        raise ValueError('exact progress32 own-fold model identity required')
    contract_values(LabelContract(**model['label_contract']), inputs)
    if model['pair_metadata']['training'] != inputs.parent_training:
        raise ValueError('own-fold pair population and weights differ from frozen base')
    theta = solver.validate_offset(model['offset_model'], expected_spec=SPEC)
    summary = model['pair_summary']; numeric = model['offset_model']['training']
    if (type(summary) is not dict or set(summary) != {'mirrored_rows', 'stable_unequal_pairs',
            'exact_zero_difference_rows', 'exact_zero_difference_natural_weight_mass', 'natural_weight_mass',
            'zero_difference_pairs_retained'}
            or any(type(summary[k]) is not int for k in ('mirrored_rows', 'stable_unequal_pairs', 'exact_zero_difference_rows'))
            or summary['mirrored_rows'] != numeric['rows']
            or summary['mirrored_rows'] != model['pair_metadata']['training']['ordered_pairs']
            or summary['stable_unequal_pairs'] != numeric['unordered_pairs']
            or summary['exact_zero_difference_rows'] != numeric['zero_difference_rows']
            or summary['zero_difference_pairs_retained'] is not True
            or any(type(summary[k]) is not float or not math.isfinite(summary[k])
                   for k in ('exact_zero_difference_natural_weight_mass', 'natural_weight_mass'))
            or not 0. <= summary['exact_zero_difference_natural_weight_mass'] <= summary['natural_weight_mass']
            or not math.isclose(summary['natural_weight_mass'], 1900., rel_tol=1e-12, abs_tol=1e-12)
            or summary['exact_zero_difference_rows'] == 0 and summary['exact_zero_difference_natural_weight_mass'] != 0.):
        raise ValueError('strict retained-pair natural-mass diagnostics required')
    if arm == 'CF' and (np.any(theta[16:]) or np.any(model['offset_model']['final_gradient'][16:])):
        raise ValueError('CF zero-tail ridge optimum must remain exactly zero')
    return theta


def predict_fold(inputs, models):
    """Pure held scoring, using own projected base and identical H coefficients."""
    if type(models) is not dict or set(models) != set(ARMS): raise ValueError('all six own-fold models required')
    for arm in ARMS: validate_model(models[arm], inputs, arm)
    _, held = _scope(inputs, inputs.fold); predictions = []
    for ex, parent in zip(held, inputs.parent_predictions):
        bank = inputs.banks[ex.bank_id]; ids = [c.candidate_id for c in bank.candidates]
        base = inputs.base_scores[ex.bank_id]; scores = {}
        for arm in ARMS:
            scores[arm] = solver.score_candidates(models[arm]['offset_model'], inputs.interactions[arm][ex.bank_id], base, expected_spec=SPEC)
        for arm in ('HS', 'Jm', 'CF'):
            scores['shared_H_'+arm] = solver.score_candidates(models['H']['offset_model'], inputs.interactions[arm][ex.bank_id], base, expected_spec=SPEC)
        for name in ('structural_C', 'lexical_C'): scores[name] = dict(parent['candidate_scores'][name])
        for name in ('first_attempt', 'noop'):
            scores[name] = {cid: float(cid == parent['choices'][name]) for cid in ids}
        choices = {m: min(scores[m], key=lambda cid: (-scores[m][cid], cid)) for m in METHODS}
        diagnostics = {}
        for arm in ('HS', 'Jm', 'CF'):
            name = 'shared_H_'+arm
            identical = np.array_equal(inputs.interactions['H'][ex.bank_id].matrix, inputs.interactions[arm][ex.bank_id].matrix)
            if identical and (scores['H'] != scores[name] or choices['H'] != choices[name]):
                raise ValueError('same features and H coefficients must reproduce scores exactly')
            diagnostics[arm] = dict(features_identical_exact=identical, choice_changed=choices['H'] != choices[name],
                transition='same' if choices['H'] == choices[name] else 'to_noop' if choices['H'] == choices['noop']
                    else 'from_noop' if choices[name] == choices['noop'] else 'edited_to_edited',
                score_difference={cid: scores['H'][cid]-scores[name][cid] for cid in ids})
        predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            problem_id=bank.problem_id, fold=inputs.fold, bank_seal_sha256=bank.seal_sha256,
            choices=choices, candidate_scores=scores, shared_theta_diagnostics=diagnostics,
            projected_zero_residual_parent_choice_parity=True))
    return predictions


def fit_fold(inputs, label_directory, contract, output, *, recheck):
    """One trusted caller, one own-label file, six fits; no resume or fallback.

    The production caller's zero-argument recheck authenticates only this worker's
    external capsule/source/runtime scope. A callback is not a release or an OS
    security boundary. This module itself supplies no production entry point.
    """
    capsule.validate_inputs(inputs)
    if not callable(recheck): raise ValueError('external worker boundary recheck required')
    args = contract_values(contract, inputs); fingerprint = capsule.fingerprint(inputs); runtime = _runtime()
    output = canonical(output)
    if output.exists(): raise ValueError('fresh own-fold output required; no overwrite or retry')
    recheck(); output.mkdir(parents=True, exist_ok=False); completed = 0; expected = {}
    def save(name, value): expected[name] = write(output/name, value)
    def input_barrier():
        recheck()
        if capsule.fingerprint(inputs) != fingerprint or _runtime() != runtime:
            raise ValueError('worker supplied inputs/runtime changed')
        if sha(label_path) != contract.expected_sha256:
            raise ValueError('own training-label file changed')
    def artifact_barrier():
        if set(p.name for p in output.iterdir()) != set(FILES) or set(expected) != set(FILES):
            raise ValueError('exact own-fold artifact inventory required')
        if any(sha(output/name) != pin for name, pin in expected.items()):
            raise ValueError('own-fold output drift before completion')
    def terminal():
        input_barrier(); artifact_barrier()
        input_barrier(); artifact_barrier(); input_barrier()
    try:
        train, held = _scope(inputs, inputs.fold)
        train_banks = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
        label_directory = canonical(label_directory)
        label_path = canonical(label_directory/f'fold-{inputs.fold}/train-labels.json')
        training = labels.load_fold_labels(label_directory, inputs.fold, train_banks,
            {ex.example_id: ex.bank_id for ex in train}, **args)
        plan = solver.make_pair_plan(train, train_banks, training)
        base = {ex.bank_id: inputs.base_scores[ex.bank_id] for ex in train}; models = {}
        for arm in ARMS:
            data = solver.materialize_pairs(plan, {ex.bank_id: inputs.interactions[arm][ex.bank_id] for ex in train}, base, spec=SPEC)
            if data.metadata['training'] != inputs.parent_training:
                raise ValueError('same-fold original pair membership/weighting mismatch')
            fitted = solver.fit_offset(data.matrix, data.y, data.weights, data.base_margin, spec=SPEC)
            models[arm] = _model(inputs, arm, data, fitted, contract)
            validate_model(models[arm], inputs, arm); save(arm+'.json', models[arm]); completed += 1
            print(json.dumps(dict(phase='fitting', fold=inputs.fold, completed_fits=completed, total_fits=6,
                                  train_examples=len(train), predicted_examples=0, total_held_examples=len(held))), flush=True)
        save('MODELS_COMPLETE.json', dict(fold=inputs.fold, model_files_sha256={a+'.json': expected[a+'.json'] for a in ARMS},
            train_example_ids=[e.example_id for e in train], held_example_ids=[e.example_id for e in held],
            input_fingerprint=fingerprint, label_contract=args))
        del training, plan, data
        predictions = predict_fold(inputs, models); save('predictions.json', predictions)
        save('STATUS.json', dict(phase='complete', fold=inputs.fold, completed_fits=6, total_fits=6,
                                predicted_examples=len(held), total_held_examples=len(held)))
        terminal()
        write(output/'COMPLETE.json', dict(status='complete', kind='statement_progress32_fold_complete_v1',
            fold=inputs.fold, completed_fits=6, predicted_examples=len(held), input_fingerprint=fingerprint,
            files_sha256=dict(expected), automatic_retries=0))
        return predictions
    except BaseException as exc:
        marker = output/'COMPLETE.json'
        if marker.exists():
            rejected = canonical(output/'REJECTED_COMPLETE.json')
            if rejected.exists(): raise ValueError('rejected marker already present') from exc
            marker.rename(rejected)
        body = dict(status='failed', error_type=type(exc).__name__, error=str(exc), completed_fits=completed,
                    retry_authorized=False)
        if hasattr(exc, 'diagnostics'): body['diagnostics'] = exc.diagnostics
        if hasattr(exc, 'metadata'): body['pair_metadata'] = exc.metadata
        write(output/'FAILED.json', body)
        raise


if __name__ == '__main__':
    raise SystemExit('No production CLI: external capsule coordinator and separate fit release required.')
