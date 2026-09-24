"""Coordinator-only joint inputs, reusing the frozen accepted input reader.

The only artifact reader here is the explicit unchanged progress32 reader. It
authenticates source/readiness/parent ancestry; no new release, bypass, replay,
fit or worker-side reader is provided. Its old project_fold is NOT reused: that
function computes learned structural scores for training recipients as well.

This adapter computes label-blind raw4099 coordinates and transports the exact
six accepted32 arrays. It inspects only the requested parent's fold and checks
its structural-C HELD scores for baseline parity, never as joint features.
Own-held lexical scores remain authenticated, sealed metadata; that model is
not inspected. Source/input bindings returned by the frozen reader retain
their meaning. A future guard must independently bind and recheck those maps
AND the complete old+new code/protocol closure, including this adapter. These
pure projections and a self-consistent fingerprint are not external authority.
"""
from __future__ import annotations

# The frozen reader establishes the native environment before numerical imports.
from scripts import zpd_repair_progress_inputs as previous
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from scripts import zpd_repair_structure as structural

VERSION = 'joint_progress4131_accepted_input_adapter_v1'
SUPPORT_SHA = previous.SUPPORT_SHA
# Additional primitive names, not a claim of a complete transitive release.
LOCAL_SOURCES = ('scripts/zpd_joint_progress_inputs.py', 'tests/test_zpd_joint_progress_inputs.py',
    'scripts/zpd_joint_progress_capsule.py', 'scripts/zpd_joint_progress_features.py')
CORE_FIELDS = {'examples', 'banks', 'assignment', 'interactions', 'parent_folds',
    'fold_assignment_sha256', 'readiness_complete_sha256', 'synthetic'}
OPTIONAL_FIELDS = {'observations', 'parent_complete_sha256', 'feature_configuration',
    'joint_feature_configuration', 'source_bindings', 'input_bindings', 'raw_current'}
ORIGINAL_METHODS = {variant+'_'+condition for variant in ('lexical', 'structural') for condition in ('C', 'H', 'U')}
require = capsule.require


def _components(value):
    require(type(value) is dict and CORE_FIELDS <= set(value) <= CORE_FIELDS | OPTIONAL_FIELDS,
        'exact accepted coordinator components; no labels/scaler/base-score payload required')
    require(type(value['synthetic']) is bool and type(value['examples']) is tuple and bool(value['examples'])
        and type(value['banks']) is dict and type(value['assignment']) is dict,
        'typed original source-only components and explicit synthetic Boolean required')
    require(capsule._same(value['assignment'], capsule.assign_folds(value['examples'])),
        'original full balanced problem-fold assignment required')
    if 'feature_configuration' in value:
        require(capsule._same(value['feature_configuration'], previous.progress.configuration()),
            'unchanged accepted progress32 configuration required')
    if 'joint_feature_configuration' in value:
        require(capsule._same(value['joint_feature_configuration'], features.configuration()),
            'fixed separate native joint4131 configuration required')


def _raw_current(value):
    """Reuse a common map if supplied; source replay still occurs in capsule validation."""
    if 'raw_current' in value:
        require(type(value['raw_current']) is dict, 'exact common raw-current map required')
        return value['raw_current']
    return {ex.bank_id: features.raw_current(ex, value['banks'][ex.bank_id]) for ex in value['examples']}


def load_observed_components(project):
    """Authenticated coordinator assembly only; no new input authorization.

    The unchanged reader may authenticate all parent metadata in its coordinator
    role. Per-fold projection below never visits siblings. No actual reader call
    is permitted merely because this library has been imported or unit-tested.
    """
    loaded = previous.load_observed_components(project)
    _components(loaded)
    require(loaded['synthetic'] is False and 'feature_configuration' in loaded,
        'only the authenticated production reader may assemble source components')
    result = dict(loaded)
    result['raw_current'] = _raw_current(loaded)
    result['feature_configuration'] = capsule._clone(loaded['feature_configuration'])
    result['joint_feature_configuration'] = features.configuration()
    for key in ('source_bindings', 'input_bindings'):
        require(type(loaded.get(key)) is dict and bool(loaded[key]), 'authenticated input/source bindings required')
        result[key] = capsule._clone(loaded[key])
    _components(result)
    return result


def project_fold(components, fold):
    """Pure own-fold joint capsule: only held baseline-score authentication.

    No old projection, scaler fit, label reader, training learned scores, other
    fold payload or lexical model is called/read. The external loader/guard
    remains responsible for original parent and accepted vector authenticity.
    """
    require(type(fold) is int and fold in range(5), 'strict fold0..4 required')
    _components(components)
    examples = components['examples']; banks = components['banks']; assignment = components['assignment']
    train = tuple(ex for ex in examples if assignment['example_fold'][ex.example_id] != fold)
    held = tuple(ex for ex in examples if assignment['example_fold'][ex.example_id] == fold)
    parent = components['parent_folds'][fold]  # Do not iterate, hash or decode siblings.
    capsule._fields(parent, ('fold', 'train_example_ids', 'held_example_ids', 'models', 'predictions'), 'own parent fold')
    require(type(parent['fold']) is int and parent['fold'] == fold
        and type(parent['train_example_ids']) is tuple and parent['train_example_ids'] == tuple(ex.example_id for ex in train)
        and type(parent['held_example_ids']) is tuple and parent['held_example_ids'] == tuple(ex.example_id for ex in held),
        'exact own parent training/held membership and order required')
    require(type(parent['models']) is dict and set(parent['models']) == set(capsule.BASELINES),
        'only two original own-parent baseline model slots required')
    model = parent['models']['structural_C']
    structural._validate_model(model)
    require(model['condition'] == 'C' and model['variant'] == 'structural', 'frozen same-fold structural-C parent required')
    require(type(parent['predictions']) is tuple and len(parent['predictions']) == len(held),
        'complete own-held parent prediction tuple required')
    predictions = []
    for ex, row in zip(held, parent['predictions'], strict=True):
        capsule._fields(row, capsule.PREDICTION_FIELDS | {'candidate_edit_tokens'}, 'original own-held prediction')
        require(type(row['choices']) is dict and set(row['choices']) == ORIGINAL_METHODS | {'noop', 'first_attempt'}
            and type(row['candidate_scores']) is dict and set(row['candidate_scores']) == ORIGINAL_METHODS,
            'exact original baseline choice/score method inventories required')
        expected_scores = structural.score_model(model, ex.observation, (), banks[ex.bank_id])
        require(capsule._same(expected_scores, row['candidate_scores']['structural_C'])
            and row['choices']['structural_C'] == min(expected_scores, key=lambda cid: (-expected_scores[cid], cid)),
            'own-held structural-C scores/SHA-tied choice differ from frozen model')
        predictions.append(capsule._clone({
            **{key: row[key] for key in capsule.PREDICTION_FIELDS - {'choices', 'candidate_scores'}},
            'choices': {key: row['choices'][key] for key in capsule.PARENT_METHODS},
            'candidate_scores': {key: row['candidate_scores'][key] for key in capsule.BASELINES}}))
    result = capsule.FoldInputs(fold, examples, banks, capsule._clone(assignment), _raw_current(components),
        components['interactions'], tuple(predictions), capsule._clone(model['training']), model['model_sha256'],
        components['fold_assignment_sha256'], components['readiness_complete_sha256'], components['synthetic'])
    capsule.validate_inputs(result)
    return result


if __name__ == '__main__':
    raise SystemExit('Coordinator library only; a separately authenticated joint fitting release is required.')
