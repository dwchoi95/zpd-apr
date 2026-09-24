"""Prospective staged repair-offset engine. NO production CLI or release.

The future reviewed guard supplies label-free inputs and independently verifies
their original parent/support artifact chains. This module does not load a
corpus, baseline artifacts, generation outputs or evaluator caches. Preparation,
each fold worker and final assessment are separate entry points and must run in
separate processes in the future orchestrator. There is deliberately no run-all
API. Synthetic tests may call the stages sequentially, without claiming process
isolation. Hashes and schemas are engineering checks, not an OS sandbox.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import scipy
import sklearn

from scripts import zpd_repair_feedback_assessment as assessment
from scripts import zpd_repair_feedback_labels as label_provider
from scripts import zpd_repair_feedback_offset as offset
from scripts import zpd_repair_feedback_pairs as pairs
from scripts import zpd_repair_structure as structural
from scripts.run_zpd_repair_structure_cv import assign_folds
from scripts.zpd_repair_fit import Example
from src.repair.pilot_contracts import CandidateBank, canonical_hash, source_hash

ARMS = ('H', 'Jm', 'HS', 'U', 'L')
METHODS = assessment.METHODS
BASELINES = ('structural_C', 'lexical_C')
SUPPORT_COMPLETE_SHA256 = '64d8f2a11de01ee08a2ed0ac51ac44b1ad4ec56281eaac971eadbb88cc4270d0'
PARENT_COMPLETE_SHA256 = 'b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f'
OLD_METHODS = tuple(v+'_'+c for v in ('lexical', 'structural') for c in ('C', 'H', 'U'))
PARENT_PREDICTION_FIELDS = {'example_id', 'user_id', 'bank_id', 'fold', 'problem_id',
    'bank_seal_sha256', 'choices', 'candidate_scores', 'candidate_edit_tokens'}


@dataclass(frozen=True)
class ParentFold:
    fold: int
    train_example_ids: tuple[str, ...]
    held_example_ids: tuple[str, ...]
    models: dict
    predictions: tuple[dict, ...]


@dataclass(frozen=True)
class PreparedInputs:
    examples: tuple[Example, ...]
    banks: dict[str, CandidateBank]
    assignment: dict
    interactions: dict[str, dict[str, pairs.CandidateInteractions]]
    parent_folds: dict[int, ParentFold]
    fold_assignment_sha256: str
    support_complete_sha256: str = SUPPORT_COMPLETE_SHA256
    parent_complete_sha256: str = PARENT_COMPLETE_SHA256
    synthetic: bool = False


@dataclass(frozen=True)
class LabelContract:
    expected_sha256: str
    expected_fold_assignment_sha256: str
    expected_source_binding_sha256: str


def _sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('strict SHA256 required')
    return value


def _canonical(path):
    path = Path(path).absolute()
    if path.resolve() != path:
        raise ValueError('canonical nonsymlink stage path required')
    return path


def _write(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False)
        stream.write('\n')


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _runtime():
    return dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__, sklearn=sklearn.__version__)


def _status(directory, **value):
    path = directory/'STATUS.json'; temporary = directory/'STATUS.json.partial'
    _write(temporary, value)
    temporary.replace(path)


def _failed(directory, error, **counts):
    body = dict(status='failed', error_type=type(error).__name__, error=str(error),
                retry_authorized=False, **counts)
    if hasattr(error, 'diagnostics'): body['diagnostics'] = error.diagnostics
    if isinstance(error, pairs.NoInformativePairs): body['pair_metadata'] = error.metadata
    _write(directory/'FAILED.json', body)
    _status(directory, **body)


def _bindings(provenance):
    if type(provenance) is not dict or set(provenance) != {'source_sha256', 'input_sha256'}:
        raise ValueError('explicit source and allowed-input binding maps required')
    all_paths = set()
    for field, mapping in provenance.items():
        if type(mapping) is not dict:
            raise ValueError('binding map must be a dictionary')
        for raw, expected in mapping.items():
            if type(raw) is not str or raw != str(_canonical(raw)) or raw in all_paths:
                raise ValueError('unique absolute canonical binding paths required')
            all_paths.add(raw); _hash(expected)
            # Fit bindings must be label-free. The own fold label is addressed
            # ONLY via LabelContract, not a general input-file dictionary.
            if field == 'input_sha256' and any('label' in p.lower() or p == 'evaluation' for p in Path(raw).parts):
                raise ValueError('general input bindings must exclude label/evaluation paths')
            if _sha(raw) != expected:
                raise ValueError('source/input binding changed: '+raw)


def _seal(directory, names, **metadata):
    final = directory/'COMPLETE.json'; temporary = directory/'COMPLETE.json.partial'
    if final.exists(): raise ValueError('completion seal already exists; no overwrite')
    _write(temporary, dict(status='complete', files_sha256={name: _sha(directory/name) for name in names}, **metadata))
    # No complete marker can survive a failure while writing/closing its bytes.
    # Rename is the final operation; failed stages retain their partial file.
    temporary.rename(final)


def _verify_files(directory, files):
    if type(files) is not dict or not files:
        raise ValueError('nonempty sealed file inventory required')
    for relative, expected in files.items():
        path = Path(relative)
        if (type(relative) is not str or path.is_absolute() or '..' in path.parts
                or str(path) != relative or str(_canonical(directory/path)) != str(directory/path)):
            raise ValueError('unsafe sealed artifact path')
        if _sha(directory/path) != _hash(expected):
            raise ValueError('sealed artifact hash mismatch: '+relative)


def _scope(inputs, fold):
    train = tuple(ex for ex in inputs.examples if inputs.assignment['example_fold'][ex.example_id] != fold)
    held = tuple(ex for ex in inputs.examples if inputs.assignment['example_fold'][ex.example_id] == fold)
    return train, held


def _parent_training(model, train):
    scale, coefficient = structural._validate_model(model)
    if model['condition'] != 'C' or scale.shape != (3,) or coefficient.shape != (4099,):
        raise ValueError('frozen same-fold C model with all4099 coefficients and3 scales required')
    info = model['training']; ids = [ex.example_id for ex in train]
    informative = info['informative_train_example_ids']; uninformative = info['uninformative_train_example_ids']
    if (set(informative) & set(uninformative) or len(informative) != len(set(informative))
            or len(uninformative) != len(set(uninformative)) or set(informative) | set(uninformative) != set(ids)
            or informative != [eid for eid in ids if eid in set(informative)] or uninformative != sorted(uninformative)
            or info['train_prefixes'] != len(train) or info['train_users'] != len({ex.user_id for ex in train})
            or set(info['pair_example_ids']) != set(informative)):
        raise ValueError('parent model exact training membership differs from fold')


def _cohort(inputs):
    return [dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
        problem_id=ex.observation.problem_id, fold=inputs.assignment['example_fold'][ex.example_id],
        candidate_ids=[c.candidate_id for c in inputs.banks[ex.bank_id].candidates],
        noop_candidate_id=source_hash(inputs.banks[ex.bank_id].current_source)) for ex in inputs.examples]


def validate_inputs(inputs):
    """Source-only validation; no label, evaluation or parent-artifact reads."""
    if type(inputs) is not PreparedInputs or type(inputs.synthetic) is not bool:
        raise ValueError('strict prepared input contract required')
    if (type(inputs.examples) is not tuple or any(type(ex) is not Example for ex in inputs.examples)
            or not inputs.examples or not inputs.synthetic and len(inputs.examples) != 320):
        raise ValueError('frozen train320 or explicitly synthetic typed examples required')
    if inputs.support_complete_sha256 != SUPPORT_COMPLETE_SHA256 or inputs.parent_complete_sha256 != PARENT_COMPLETE_SHA256:
        raise ValueError('fixed support and original structure parent pins required')
    _hash(inputs.fold_assignment_sha256)
    if inputs.assignment != assign_folds(inputs.examples):
        raise ValueError('frozen problem-fold assignment not reproduced')
    ids = {ex.bank_id for ex in inputs.examples}
    if (type(inputs.banks) is not dict or set(inputs.banks) != ids or type(inputs.interactions) is not dict
            or set(inputs.interactions) != set(ARMS) or type(inputs.parent_folds) is not dict
            or set(inputs.parent_folds) != set(range(5)) or any(type(f) is not int for f in inputs.parent_folds)):
        raise ValueError('exact all-bank, five-arm and five-fold scope required')
    for arm in ARMS:
        if type(inputs.interactions[arm]) is not dict or set(inputs.interactions[arm]) != ids:
            raise ValueError('interaction bank scope differs')
        for ex in inputs.examples:
            bank = inputs.banks[ex.bank_id]
            if type(bank) is not CandidateBank or bank.problem_id != ex.observation.problem_id or bank.current_source != ex.observation.current.source:
                raise ValueError('observation-bank identity mismatch')
            pairs._candidate_inputs(bank, inputs.interactions[arm][ex.bank_id], {c.candidate_id: 0. for c in bank.candidates})
            other = inputs.interactions['H'][ex.bank_id]; current = inputs.interactions[arm][ex.bank_id]
            if not np.array_equal(current.event_values, other.event_values) or not np.array_equal(current.event_masks, other.event_masks):
                raise ValueError('candidate events/masks must be arm invariant')
    for fold in range(5):
        parent = inputs.parent_folds[fold]; train, held = _scope(inputs, fold)
        if (type(parent) is not ParentFold or type(parent.fold) is not int or parent.fold != fold
                or parent.train_example_ids != tuple(ex.example_id for ex in train)
                or parent.held_example_ids != tuple(ex.example_id for ex in held)
                or type(parent.models) is not dict or set(parent.models) != set(BASELINES)
                or type(parent.predictions) is not tuple or len(parent.predictions) != len(held)):
            raise ValueError('parent fold exact train/held/model membership differs')
        for name, model in parent.models.items():
            _parent_training(model, train)
            if model['variant'] != name.split('_')[0]: raise ValueError('parent baseline variant mismatch')
        for ex, prediction in zip(held, parent.predictions):
            bank = inputs.banks[ex.bank_id]
            if type(prediction) is not dict or set(prediction) != PARENT_PREDICTION_FIELDS:
                raise ValueError('strict label-free original parent prediction schema required')
            expected = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
                problem_id=bank.problem_id, fold=fold, bank_seal_sha256=bank.seal_sha256)
            if any(type(prediction[k]) is not type(v) or prediction[k] != v for k, v in expected.items()):
                raise ValueError('parent held prediction identity differs')
            candidate_ids = {c.candidate_id for c in bank.candidates}
            if (type(prediction['choices']) is not dict or set(prediction['choices']) != set(OLD_METHODS) | {'noop', 'first_attempt'}
                    or type(prediction['candidate_scores']) is not dict or set(prediction['candidate_scores']) != set(OLD_METHODS)
                    or type(prediction['candidate_edit_tokens']) is not dict or set(prediction['candidate_edit_tokens']) != candidate_ids
                    or any(type(v) not in (int, float) or not np.isfinite(v) or v < 0 for v in prediction['candidate_edit_tokens'].values())):
                raise ValueError('parent predictions missing fixed candidate/method coverage')
            for name, scores in prediction['candidate_scores'].items():
                if (type(scores) is not dict or set(scores) != candidate_ids or any(type(v) not in (int, float) or not np.isfinite(v) for v in scores.values())
                        or prediction['choices'][name] != min(scores, key=lambda cid: (-scores[cid], cid))):
                    raise ValueError('parent candidate scores or choices invalid')
            noop = source_hash(bank.current_source); first = bank.attempts[0]
            if prediction['choices']['noop'] != noop or prediction['choices']['first_attempt'] != (source_hash(first.source) if first.status == 'success' else noop):
                raise ValueError('parent deterministic baseline differs')
            for name, model in parent.models.items():
                actual = structural.score_model(model, ex.observation, (), bank)
                if not np.array_equal([actual[c.candidate_id] for c in bank.candidates],
                        [prediction['candidate_scores'][name][c.candidate_id] for c in bank.candidates]):
                    raise ValueError('parent raw score replay differs; no precision relaxation')
                if min(actual, key=lambda cid: (-actual[cid], cid)) != prediction['choices'][name]:
                    raise ValueError('zero-residual parent choice parity failed')
    return _cohort(inputs)


def input_fingerprint(inputs):
    matrices = {}
    for arm in ARMS:
        matrices[arm] = {}
        for bid, block in inputs.interactions[arm].items():
            arrays = {}
            for name in ('matrix', 'event_values', 'event_masks'):
                array = getattr(block, name)
                arrays[name] = dict(dtype=array.dtype.str, shape=list(array.shape),
                    sha256=hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest())
            matrices[arm][bid] = dict(candidate_ids=block.candidate_ids, **arrays)
    return canonical_hash(dict(examples=inputs.examples, banks=inputs.banks, assignment=inputs.assignment,
        interactions=matrices, parent_folds=inputs.parent_folds, fold_assignment_sha256=inputs.fold_assignment_sha256,
        support_complete_sha256=inputs.support_complete_sha256, parent_complete_sha256=inputs.parent_complete_sha256,
        synthetic=inputs.synthetic))


def prepare_labels(blobs, output):
    """Preparation-process entry; supplied exact bytes only, no source loading."""
    # Public provider verifies the raw source chain before materialization;
    # a self-resealed caller-created intermediate bundle is never sufficient.
    return label_provider.materialize_fold_labels(blobs, output)


def _label_contracts(inputs, contracts):
    if type(contracts) is not dict or set(contracts) != {*range(5), None} or any(type(k) is not int for k in contracts if k is not None):
        raise ValueError('all five training and separate assessment label contracts required')
    result = {str(fold) if fold is not None else 'assessment': dict(_contract(contract, inputs)) for fold, contract in contracts.items()}
    if len({row['expected_source_binding_sha256'] for row in result.values()}) != 1:
        raise ValueError('all fold/assessment labels must share one frozen source binding')
    return result


def initialize(inputs, output, *, provenance, label_contracts):
    """Write the label-free fixed cohort and stage plan, never fitting."""
    output = _canonical(output)
    if output.exists(): raise ValueError('new run output required; no overwrite or resume')
    output.mkdir(parents=True)
    try:
        cohort = validate_inputs(inputs); _bindings(provenance)
        contracts = _label_contracts(inputs, label_contracts)
        fingerprint = input_fingerprint(inputs); runtime = _runtime()
        _write(output/'manifest.json', dict(kind='prospective_repair_feedback_cv_staged_v1',
            input_fingerprint=fingerprint, provenance=provenance, runtime=runtime, label_contracts=contracts,
            synthetic=inputs.synthetic, production_cli_released=False, support_complete_sha256=SUPPORT_COMPLETE_SHA256,
            parent_complete_sha256=PARENT_COMPLETE_SHA256, fold_assignment_sha256=inputs.fold_assignment_sha256,
            arms=list(ARMS), methods=list(METHODS), fits=25, full_train_refits=0,
            score_semantics={m: 'fixed_indicator_utility_not_confidence' if m in ('first_attempt', 'noop') else 'raw_additive_score' for m in METHODS}))
        _write(output/'cohort.json', cohort); _write(output/'folds.json', inputs.assignment)
        _bindings(provenance)
        if input_fingerprint(inputs) != fingerprint: raise ValueError('input objects changed during initialization')
        if _runtime() != runtime: raise ValueError('runtime changed during initialization')
        _write(output/'FOLDS_COMPLETE.json', dict(files_sha256={n: _sha(output/n) for n in ('manifest.json', 'cohort.json', 'folds.json')}))
        return fingerprint
    except BaseException as error:
        _failed(output, error, completed_fits=0)
        raise


def _run_state(inputs, run):
    run = _canonical(run)
    if (run/'FAILED.json').exists() or (run/'COMPLETE.json').exists():
        raise ValueError('failed or completed run cannot resume')
    marker = _read(run/'FOLDS_COMPLETE.json')
    if set(marker) != {'files_sha256'} or set(marker['files_sha256']) != {'manifest.json', 'cohort.json', 'folds.json'}:
        raise ValueError('fixed initialization seal required')
    _verify_files(run, marker['files_sha256'])
    manifest = _read(run/'manifest.json')
    if type(manifest) is not dict or set(manifest) != {'kind', 'input_fingerprint', 'provenance', 'runtime',
            'label_contracts', 'synthetic', 'production_cli_released', 'support_complete_sha256',
            'parent_complete_sha256', 'fold_assignment_sha256', 'arms', 'methods', 'fits',
            'full_train_refits', 'score_semantics'}:
        raise ValueError('strict label-free initialization manifest schema required')
    saved_contracts = manifest['label_contracts']
    if (type(saved_contracts) is not dict or set(saved_contracts) != {'0', '1', '2', '3', '4', 'assessment'}
            or _label_contracts(inputs, {None if k == 'assessment' else int(k): LabelContract(**v) for k, v in saved_contracts.items()}) != saved_contracts):
        raise ValueError('fixed preparation label contracts required in initialization seal')
    if (manifest['kind'] != 'prospective_repair_feedback_cv_staged_v1' or manifest['arms'] != list(ARMS)
            or manifest['methods'] != list(METHODS) or type(manifest['fits']) is not int or manifest['fits'] != 25
            or type(manifest['full_train_refits']) is not int or manifest['full_train_refits'] != 0
            or manifest['production_cli_released'] is not False or manifest['synthetic'] is not inputs.synthetic
            or manifest['score_semantics'] != {m: 'fixed_indicator_utility_not_confidence' if m in ('first_attempt', 'noop') else 'raw_additive_score' for m in METHODS}
            or manifest['support_complete_sha256'] != SUPPORT_COMPLETE_SHA256 or manifest['parent_complete_sha256'] != PARENT_COMPLETE_SHA256
            or manifest['fold_assignment_sha256'] != inputs.fold_assignment_sha256
            or manifest['input_fingerprint'] != input_fingerprint(inputs) or manifest['runtime'] != _runtime()):
        raise ValueError('stage supplied inputs/runtime differ from initialization')
    if _read(run/'cohort.json') != _cohort(inputs) or _read(run/'folds.json') != inputs.assignment:
        raise ValueError('cohort/folds changed')
    _bindings(manifest['provenance'])
    return run, manifest


def _terminal_state(inputs, manifest):
    _bindings(manifest['provenance'])
    if _runtime() != manifest['runtime']:
        raise ValueError('runtime changed before terminal seal')
    if input_fingerprint(inputs) != manifest['input_fingerprint']:
        raise ValueError('input objects changed before terminal seal')


def _contract(contract, inputs):
    if type(contract) is not LabelContract or contract.expected_fold_assignment_sha256 != inputs.fold_assignment_sha256:
        raise ValueError('exact materialized label contract/fold SHA required')
    for value in vars(contract).values(): _hash(value)
    return vars(contract)


def _model(arm, fold, train, held, data, fitted, inputs, contract):
    value = dict(kind='repair_feedback_fold_offset_v1', arm=arm, fold=fold,
        train_example_ids=[ex.example_id for ex in train], held_example_ids=[ex.example_id for ex in held],
        input_fingerprint=input_fingerprint(inputs), label_contract=vars(contract),
        parent_structure_model_sha256=inputs.parent_folds[fold].models['structural_C']['model_sha256'],
        pair_metadata=data.metadata, offset_model=fitted)
    value['model_sha256'] = canonical_hash(value)
    return value


def _validate_model(model, inputs, fold, arm):
    fields = {'kind', 'arm', 'fold', 'train_example_ids', 'held_example_ids', 'input_fingerprint',
        'label_contract', 'parent_structure_model_sha256', 'pair_metadata', 'offset_model', 'model_sha256'}
    train, held = _scope(inputs, fold)
    if (type(model) is not dict or set(model) != fields or model['kind'] != 'repair_feedback_fold_offset_v1'
            or type(model['fold']) is not int or model['fold'] != fold or model['arm'] != arm
            or model['train_example_ids'] != [ex.example_id for ex in train] or model['held_example_ids'] != [ex.example_id for ex in held]
            or model['input_fingerprint'] != input_fingerprint(inputs)
            or model['parent_structure_model_sha256'] != inputs.parent_folds[fold].models['structural_C']['model_sha256']
            or model['model_sha256'] != canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})):
        raise ValueError('strict sealed fold-offset model identity mismatch')
    _contract(LabelContract(**model['label_contract']), inputs)
    if model['pair_metadata']['training'] != inputs.parent_folds[fold].models['structural_C']['training']:
        raise ValueError('pair target membership/weighting differs from frozen parent')
    offset.validate_model(model['offset_model'])
    if model['offset_model']['training']['rows'] != model['pair_metadata']['training']['ordered_pairs']:
        raise ValueError('numerical model pair count differs from construction metadata')


def predict_fold(inputs, fold, models):
    """Pure label-blind all-method held scoring, including shared H theta."""
    if type(fold) is not int or fold not in range(5) or type(models) is not dict or set(models) != set(ARMS):
        raise ValueError('exact five fixed fold models required')
    for arm in ARMS: _validate_model(models[arm], inputs, fold, arm)
    predictions = []; _, held = _scope(inputs, fold)
    for ex, parent in zip(held, inputs.parent_folds[fold].predictions):
        bank = inputs.banks[ex.bank_id]; cid = [c.candidate_id for c in bank.candidates]
        base = parent['candidate_scores']['structural_C']; scores = {}
        for arm in ARMS:
            scores[arm] = pairs.score_candidates(models[arm]['offset_model'], bank, inputs.interactions[arm][ex.bank_id], base)
        for name, arm in (('shared_H_HS', 'HS'), ('shared_H_Jm', 'Jm')):
            scores[name] = pairs.score_candidates(models['H']['offset_model'], bank, inputs.interactions[arm][ex.bank_id], base)
        for name in BASELINES: scores[name] = dict(parent['candidate_scores'][name])
        for name in ('first_attempt', 'noop'):
            scores[name] = {c: float(c == parent['choices'][name]) for c in cid}
        choices = {name: min(scores[name], key=lambda c: (-scores[name][c], c)) for name in METHODS}
        diagnostics = {}
        for arm in ('HS', 'Jm'):
            name = 'shared_H_'+arm
            identical = np.array_equal(inputs.interactions['H'][ex.bank_id].matrix, inputs.interactions[arm][ex.bank_id].matrix)
            if identical and (scores['H'] != scores[name] or choices['H'] != choices[name]):
                raise ValueError('identical features under same theta must exactly reproduce scores and choices')
            diagnostics[arm] = dict(features_identical_exact=identical,
                choice_changed=choices['H'] != choices[name],
                transition='same' if choices['H'] == choices[name] else 'to_noop' if choices['H'] == choices['noop']
                    else 'from_noop' if choices[name] == choices['noop'] else 'edited_to_edited',
                score_difference={c: scores['H'][c]-scores[name][c] for c in cid})
        predictions.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            problem_id=bank.problem_id, fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices,
            candidate_scores=scores, shared_theta_diagnostics=diagnostics, zero_residual_parent_choice_parity=True))
    return predictions


def fit_fold(inputs, fold, label_directory, contract, run):
    """ONE worker: read only its exact train label file; fit exactly five cells."""
    if type(fold) is not int or fold not in range(5): raise ValueError('explicit fixed fold required')
    run, manifest = _run_state(inputs, run); directory = run/f'fold-{fold}'
    if directory.exists() or (run/'PREDICTIONS_COMPLETE.json').exists(): raise ValueError('new unfinished fold required; no retry')
    directory.mkdir(); fitted = 0
    try:
        validate_inputs(inputs); fingerprint = manifest['input_fingerprint']
        contract_args = _contract(contract, inputs); train, held = _scope(inputs, fold)
        if contract_args != manifest['label_contracts'][str(fold)]:
            raise ValueError('worker label contract differs from trusted initialization')
        train_banks = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
        label_directory = _canonical(label_directory)
        label_path = _canonical(label_directory/f'fold-{fold}/train-labels.json')
        train_labels = label_provider.load_fold_labels(label_directory, fold, train_banks,
            {ex.example_id: ex.bank_id for ex in train}, **contract_args)
        base = {ex.bank_id: structural.score_model(inputs.parent_folds[fold].models['structural_C'], ex.observation, (), train_banks[ex.bank_id]) for ex in train}
        models = {}
        for arm in ARMS:
            data = pairs.build_pairs(train, train_banks, train_labels,
                {ex.bank_id: inputs.interactions[arm][ex.bank_id] for ex in train}, base)
            if data.metadata['training'] != inputs.parent_folds[fold].models['structural_C']['training']:
                raise ValueError('legacy pair membership/weighting mismatch with same-fold parent')
            fitted_model = offset.fit_offset(data.matrix, data.y, data.weights, data.base_margin)
            models[arm] = _model(arm, fold, train, held, data, fitted_model, inputs, contract)
            _validate_model(models[arm], inputs, fold, arm)
            _write(directory/(arm+'.json'), models[arm]); fitted += 1
            _status(directory, phase='fitting', fold=fold, completed_fits=fitted, total_fits=5)
        _write(directory/'MODELS_COMPLETE.json', dict(fold=fold, model_files_sha256={arm+'.json': _sha(directory/(arm+'.json')) for arm in ARMS},
            train_example_ids=[ex.example_id for ex in train], held_example_ids=[ex.example_id for ex in held],
            input_fingerprint=fingerprint, label_contract=vars(contract)))
        # Explicitly discard worker labels before the label-blind scoring call.
        del train_labels
        predictions = predict_fold(inputs, fold, models)
        _write(directory/'predictions.json', predictions)
        _status(directory, phase='complete', fold=fold, completed_fits=5, predicted_examples=len(held))
        _terminal_state(inputs, manifest)
        if _sha(label_path) != contract.expected_sha256:
            raise ValueError('worker input or own-label file changed before completion')
        _seal(directory, [*(arm+'.json' for arm in ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'],
            fold=fold, completed_fits=5, predicted_examples=len(held), input_fingerprint=fingerprint)
        return predictions
    except BaseException as error:
        _failed(directory, error, completed_fits=fitted)
        if not (run/'FAILED.json').exists(): _failed(run, error, failed_fold=fold, completed_fits_in_failed_fold=fitted)
        raise


def _fold_outputs(inputs, run, expected_contracts):
    predictions = []; markers = {}
    expected_names = {*(arm+'.json' for arm in ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'}
    for fold in range(5):
        directory = run/f'fold-{fold}'
        if (directory/'FAILED.json').exists(): raise ValueError('failed fold forbids scientific assessment')
        marker = _read(directory/'COMPLETE.json'); markers[str(fold)] = _sha(directory/'COMPLETE.json')
        if (marker.get('status') != 'complete' or type(marker.get('fold')) is not int or marker['fold'] != fold
                or type(marker.get('completed_fits')) is not int or marker['completed_fits'] != 5
                or marker.get('input_fingerprint') != input_fingerprint(inputs) or set(marker['files_sha256']) != expected_names):
            raise ValueError('all25 fixed fold cells required')
        _verify_files(directory, marker['files_sha256'])
        models_marker = _read(directory/'MODELS_COMPLETE.json'); train, held = _scope(inputs, fold)
        if (set(models_marker) != {'fold', 'model_files_sha256', 'train_example_ids', 'held_example_ids', 'input_fingerprint', 'label_contract'}
                or type(models_marker['fold']) is not int or models_marker['fold'] != fold
                or set(models_marker['model_files_sha256']) != {arm+'.json' for arm in ARMS}
                or models_marker['train_example_ids'] != [ex.example_id for ex in train]
                or models_marker['held_example_ids'] != [ex.example_id for ex in held]
                or models_marker['input_fingerprint'] != input_fingerprint(inputs)
                or models_marker['label_contract'] != expected_contracts[str(fold)]):
            raise ValueError('fold model seal membership mismatch')
        _verify_files(directory, models_marker['model_files_sha256'])
        models = {arm: _read(directory/(arm+'.json')) for arm in ARMS}
        if any(model['label_contract'] != models_marker['label_contract'] for model in models.values()):
            raise ValueError('model seal label contracts differ across arms')
        actual = _read(directory/'predictions.json')
        if actual != predict_fold(inputs, fold, models): raise ValueError('sealed held scores differ from label-blind model replay')
        predictions.extend(actual)
    return sorted(predictions, key=lambda p: p['example_id']), markers


def finalize_predictions(inputs, run):
    """Label-free barrier: verify all25 fits and seal all OOF choices first."""
    run, manifest = _run_state(inputs, run)
    if (run/'PREDICTIONS_COMPLETE.json').exists(): raise ValueError('predictions already sealed; no overwrite')
    try:
        predictions, markers = _fold_outputs(inputs, run, manifest['label_contracts'])
        if len(predictions) != len(inputs.examples) or {p['example_id'] for p in predictions} != {ex.example_id for ex in inputs.examples}:
            raise ValueError('exact complete OOF population required')
        _write(run/'predictions.json', predictions)
        _terminal_state(inputs, manifest)
        _write(run/'PREDICTIONS_COMPLETE.json', dict(status='all_folds_label_blind_predictions_complete',
            completed_fits=25, recipients=len(predictions), methods=list(METHODS), input_fingerprint=manifest['input_fingerprint'],
            predictions_sha256=_sha(run/'predictions.json'), fold_complete_sha256=markers))
        return predictions
    except BaseException as error:
        _failed(run, error)
        raise


def _prediction_barrier(inputs, run, expected_contracts):
    marker = _read(run/'PREDICTIONS_COMPLETE.json')
    predictions, fold_markers = _fold_outputs(inputs, run, expected_contracts)
    expected = dict(status='all_folds_label_blind_predictions_complete', completed_fits=25,
        recipients=len(inputs.examples), methods=list(METHODS), input_fingerprint=input_fingerprint(inputs),
        predictions_sha256=_sha(run/'predictions.json'), fold_complete_sha256=fold_markers)
    if marker != expected or _read(run/'predictions.json') != predictions:
        raise ValueError('all-fold prediction barrier invalid')
    return predictions


def assess_predictions(inputs, run, label_directory, contract):
    """SEPARATE assessment process: all prediction seals precede label access."""
    run, manifest = _run_state(inputs, run); directory = run/'assessment'
    if directory.exists(): raise ValueError('new assessment stage required; no overwrite')
    directory.mkdir()
    try:
        _contract(contract, inputs)
        if vars(contract) != manifest['label_contracts']['assessment']:
            raise ValueError('assessment label contract differs from trusted initialization')
        predictions = _prediction_barrier(inputs, run, manifest['label_contracts'])  # MUST precede read below
        prediction_seal = _sha(run/'PREDICTIONS_COMPLETE.json')
        label_path = _canonical(_canonical(label_directory)/'assessment/all320-labels.json')
        data = label_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != contract.expected_sha256: raise ValueError('assessment label SHA mismatch')
        labels = label_provider.validate_assessment_envelope(json.loads(data.decode('utf-8')), inputs.banks,
            {ex.example_id: ex.bank_id for ex in inputs.examples},
            expected_fold_assignment_sha256=contract.expected_fold_assignment_sha256,
            expected_source_binding_sha256=contract.expected_source_binding_sha256)
        choices = [{k: p[k] for k in assessment.PREDICTION_FIELDS} for p in predictions]
        report = assessment.assess(_cohort(inputs), choices, labels)
        report.update(completed_fits=25, full_train_refits=0, model_promotion=False,
            predictions_complete_sha256=prediction_seal,
            shared_theta_diagnostics={arm: {stratum: dict(examples=sum(p['shared_theta_diagnostics'][arm]['features_identical_exact'] == equal for p in predictions),
                choices_changed=sum(p['shared_theta_diagnostics'][arm]['choice_changed'] for p in predictions if p['shared_theta_diagnostics'][arm]['features_identical_exact'] == equal),
                **{transition: sum(p['shared_theta_diagnostics'][arm]['transition'] == transition for p in predictions if p['shared_theta_diagnostics'][arm]['features_identical_exact'] == equal)
                   for transition in ('same', 'edited_to_edited', 'to_noop', 'from_noop')})
                for stratum, equal in [('identical_features', True), ('different_features', False)]} for arm in ('HS', 'Jm')})
        _write(directory/'report.json', report)
        _write(directory/'next_action.json', dict(action='independent_audit_then_separately_freeze_next_development',
            gate_passed=report['gate']['passed'], full_train_refit_authorized=False, control_promotion_authorized=False))
        _status(directory, phase='complete', assessed_examples=len(predictions))
        _prediction_barrier(inputs, run, manifest['label_contracts']); _terminal_state(inputs, manifest)
        if (_sha(label_path) != contract.expected_sha256
                or _sha(run/'PREDICTIONS_COMPLETE.json') != prediction_seal):
            raise ValueError('assessment inputs changed before completion')
        _seal(directory, ['report.json', 'next_action.json', 'STATUS.json'], assessed_examples=len(predictions),
            predictions_complete_sha256=prediction_seal, assessment_label_sha256=contract.expected_sha256)
        names = ['manifest.json', 'cohort.json', 'folds.json', 'FOLDS_COMPLETE.json', 'predictions.json', 'PREDICTIONS_COMPLETE.json',
            'assessment/report.json', 'assessment/next_action.json', 'assessment/STATUS.json', 'assessment/COMPLETE.json']
        for fold in range(5):
            names += [f'fold-{fold}/'+name for name in [*(arm+'.json' for arm in ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json', 'COMPLETE.json']]
        _seal(run, names, completed_fits=25, recipients=len(inputs.examples), full_train_refits=0, model_promotion=False)
        return report
    except BaseException as error:
        _failed(directory, error)
        if not (run/'FAILED.json').exists(): _failed(run, error)
        raise


def main(argv=None):
    raise RuntimeError('Production repair-feedback execution is NOT released; use reviewed synthetic stage APIs only.')


if __name__ == '__main__':
    main()
