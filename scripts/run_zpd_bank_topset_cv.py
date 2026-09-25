"""Own-fold top-set engine; no CLI, release authority or assessment-label I/O.

The caller supplies an authenticated original own-training transform and only
the matching training envelope. Source/runtime authorization and global sealing
remain coordinator duties. No candidate generation or execution occurs here.
"""
from __future__ import annotations

import json
import numpy as np

from scripts import run_zpd_joint_progress_cv as previous
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from scripts import zpd_joint_progress_assessment as assessment
from scripts import zpd_repair_feedback_labels as labels
from scripts import zpd_bank_topset_plan as planner
from scripts import zpd_bank_topset_newton as solver
from scripts.run_zpd_repair_progress_cv import canonical, sha, write, contract_values
from src.repair.pilot_contracts import canonical_hash

ARMS = features.ARMS
METHODS = assessment.METHODS
MODEL_KIND = 'bank_topset4131_own_fold_model_v1'
COMPLETE_KIND = 'bank_topset4131_own_fold_complete_v1'
FILES = (*(arm+'.json' for arm in ARMS), 'SCALER.json', 'PLAN.json',
         'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json')


def require(value, message):
    if not value: raise ValueError(message)


def _model(inputs, arm, fitted, transform, contract, plan):
    train, held = capsule.scope(inputs)
    result = dict(kind=MODEL_KIND, arm=arm, fold=inputs.fold,
        train_example_ids=[ex.example_id for ex in train],
        held_example_ids=[ex.example_id for ex in held],
        input_fingerprint=capsule.fingerprint(inputs),
        label_contract=contract_values(contract, inputs),
        transform_sha256=previous.validate_transform(transform, inputs),
        plan_sha256=canonical_hash(plan), top_model=fitted)
    result['model_sha256'] = canonical_hash(result)
    return result


def validate_model(model, inputs, arm, transform, plan):
    train, held = capsule.scope(inputs)
    fields = {'kind','arm','fold','train_example_ids','held_example_ids',
              'input_fingerprint','label_contract','transform_sha256',
              'plan_sha256','top_model','model_sha256'}
    require(type(model) is dict and set(model) == fields
        and model['kind'] == MODEL_KIND and arm in ARMS and model['arm'] == arm
        and type(model['fold']) is int and model['fold'] == inputs.fold
        and model['train_example_ids'] == [ex.example_id for ex in train]
        and model['held_example_ids'] == [ex.example_id for ex in held]
        and model['input_fingerprint'] == capsule.fingerprint(inputs)
        and model['transform_sha256'] == previous.validate_transform(transform, inputs)
        and model['plan_sha256'] == canonical_hash(plan)
        and model['model_sha256'] == canonical_hash({k:v for k,v in model.items() if k != 'model_sha256'}),
        'exact top-set own-model identity required')
    contract_values(previous.LabelContract(**model['label_contract']), inputs)
    theta = solver.validate_model(model['top_model'])
    start = 4099 if arm == 'C_joint' else 4115 if arm == 'CF' else 4131
    require(not np.any(theta[start:]) and not np.any(model['top_model']['final_gradient'][start:]),
        'nested absent coordinates require exact zero coefficients/gradient')
    return theta


def predict_fold(inputs, models, transform, plan):
    """Raw original held features; full bank including unknowns, label-blind argmax."""
    capsule.validate_inputs(inputs)
    require(type(models) is dict and set(models) == set(ARMS), 'all seven own models required')
    theta = {arm:validate_model(models[arm], inputs, arm, transform, plan) for arm in ARMS}
    require(all(capsule._same(models[arm]['label_contract'], models['H']['label_contract']) for arm in ARMS),
        'all arms must share own labels')
    predictions = []
    for ex, parent in zip(capsule.scope(inputs)[1], inputs.parent_predictions, strict=True):
        bank = inputs.banks[ex.bank_id]; ids = tuple(c.candidate_id for c in bank.candidates)
        blocks = features.compose_blocks(inputs.raw_current[ex.bank_id], transform,
            {arm:inputs.interactions[arm][ex.bank_id] for arm in features.PROGRESS_ARMS})
        def score(arm, coefficients):
            values = np.asarray(blocks[arm].matrix@coefficients).ravel()
            require(np.isfinite(values).all(), 'finite held scores required')
            return dict(zip(ids, map(float, values), strict=True))
        scores = {arm:score(arm, theta[arm]) for arm in ARMS}
        for arm in ('HS','Jm','CF'): scores['shared_H_'+arm] = score(arm, theta['H'])
        for name in ('structural_C','lexical_C'): scores[name] = dict(parent['candidate_scores'][name])
        for name in ('first_attempt','noop'):
            scores[name] = {cid:float(cid == parent['choices'][name]) for cid in ids}
        choices = {name:min(scores[name], key=lambda cid:(-scores[name][cid],cid)) for name in METHODS}
        diagnostics = {}
        for arm in ('HS','Jm','CF'):
            name = 'shared_H_'+arm
            identical = np.array_equal(blocks['H'].progress, blocks[arm].progress)
            if identical:
                require(scores['H'] == scores[name] and choices['H'] == choices[name],
                    'identical features and coefficients must have identical scores')
            diagnostics[arm] = dict(features_identical_exact=identical,
                choice_changed=choices['H'] != choices[name],
                transition='same' if choices['H'] == choices[name] else
                    'to_noop' if choices['H'] == choices['noop'] else
                    'from_noop' if choices[name] == choices['noop'] else 'edited_to_edited',
                score_difference={cid:scores['H'][cid]-scores[name][cid] for cid in ids})
        predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id,
            bank_id=ex.bank_id, problem_id=bank.problem_id, fold=inputs.fold,
            bank_seal_sha256=bank.seal_sha256, choices=choices, candidate_scores=scores,
            shared_theta_diagnostics=diagnostics,
            direct_history_diagnostic_holds_all_current_coefficients_fixed=True))
    return predictions


def fit_fold(inputs, label_directory, contract, transform, output, *, recheck):
    """Seven one-shot fits; original transform is supplied, never refitted here."""
    capsule.validate_inputs(inputs); previous.validate_transform(transform, inputs)
    require(callable(recheck), 'external authority recheck required')
    args = contract_values(contract, inputs); fingerprint = capsule.fingerprint(inputs)
    transform_pin = canonical_hash(previous.transform_payload(transform))
    output = canonical(output); require(not output.exists(), 'new output required; no retry/overwrite')
    label_directory = canonical(label_directory)
    label_path = canonical(label_directory/f'fold-{inputs.fold}'/'train-labels.json')
    completed = 0; expected = {}
    def save(name, value): expected[name] = write(output/name, value)
    def check():
        recheck()
        require(capsule.fingerprint(inputs) == fingerprint, 'source-only capsule changed')
        require(canonical_hash(previous.transform_payload(transform)) == transform_pin, 'own transform changed')
        require(sha(label_path) == contract.expected_sha256, 'own label envelope changed')
    def artifacts(complete_pin=None):
        require(set(expected) == set(FILES)
            and {p.name for p in output.iterdir()} == set(FILES) | ({'COMPLETE.json'} if complete_pin else set())
            and all(sha(output/name) == pin for name,pin in expected.items()), 'own output inventory/pins changed')
        if complete_pin: require(sha(output/'COMPLETE.json') == complete_pin, 'own completion changed')
    check(); output.mkdir(parents=True, exist_ok=False)
    try:
        train, held = capsule.scope(inputs)
        train_banks = {ex.bank_id:inputs.banks[ex.bank_id] for ex in train}
        own_labels = labels.load_fold_labels(label_directory, inputs.fold, train_banks,
            {ex.example_id:ex.bank_id for ex in train}, **args)
        plan = planner.build_plan(inputs, transform, own_labels); payload = plan.payload()
        del own_labels
        save('SCALER.json', previous.transform_payload(transform)); save('PLAN.json', payload)
        models = {}
        for arm in ARMS:
            check(); banks, weights = plan.banks(arm)
            fitted = solver.fit(banks, weights)
            require(fitted['input_sha256'] == solver.input_hash(banks, weights), 'fitted objective inputs differ')
            model = _model(inputs, arm, fitted, transform, contract, payload)
            validate_model(model, inputs, arm, transform, payload)
            models[arm] = model; save(arm+'.json', model); completed += 1
            print(json.dumps(dict(phase='fitting', fold=inputs.fold,
                completed_model_fits=completed, total_model_fits=7,
                completed_training_example_model_incidences=len(train)*completed,
                total_training_example_model_incidences=len(train)*7,
                predicted_examples=0, total_held_examples=len(held))), flush=True)
        save('MODELS_COMPLETE.json', dict(fold=inputs.fold,
            model_files_sha256={arm+'.json':expected[arm+'.json'] for arm in ARMS},
            scaler_file_sha256=expected['SCALER.json'], plan_file_sha256=expected['PLAN.json'],
            input_fingerprint=fingerprint, label_contract=args))
        del plan, banks, weights
        check(); predictions = predict_fold(inputs, models, transform, payload)
        save('predictions.json', predictions)
        save('STATUS.json', dict(phase='complete', fold=inputs.fold,
            completed_model_fits=7, total_model_fits=7,
            completed_training_example_model_incidences=len(train)*7,
            total_training_example_model_incidences=len(train)*7,
            predicted_examples=len(held), total_held_examples=len(held)))
        check(); artifacts()
        complete_pin = write(output/'COMPLETE.json', dict(status='complete', kind=COMPLETE_KIND,
            fold=inputs.fold, completed_fits=7, predicted_examples=len(held),
            input_fingerprint=fingerprint, files_sha256=expected, automatic_retries=0))
        check(); artifacts(complete_pin)
        return predictions
    except BaseException as error:
        marker = output/'COMPLETE.json'
        if marker.exists(): marker.rename(output/'REJECTED_COMPLETE.json')
        body = dict(status='failed', error_type=type(error).__name__, error=str(error),
            completed_fits=completed, retry_authorized=False)
        if hasattr(error, 'diagnostics'): body['diagnostics'] = error.diagnostics
        write(output/'FAILED.json', body)
        raise
