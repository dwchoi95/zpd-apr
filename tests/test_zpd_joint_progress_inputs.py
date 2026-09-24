"""Synthetic source-only adapter tests; no empirical reader, labels or fitting."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_joint_progress_inputs as inputs
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_repair_progress_inputs import parent_components


def reseal(model):
    model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})


class OwnOnly:
    """Even visiting the sibling map inventory is an access violation."""
    def __init__(self, fold, parent): self.fold, self.parent, self.accesses = fold, parent, []
    def __getitem__(self, fold):
        if fold != self.fold: raise AssertionError('sibling parent accessed')
        self.accesses.append(fold)
        return self.parent
    def __iter__(self): raise AssertionError('sibling inventory inspected')
    def items(self): raise AssertionError('sibling metadata read')
    def values(self): raise AssertionError('sibling metadata read')


class Poison:
    def __getitem__(self, _): raise AssertionError('unused parent payload accessed')
    def __iter__(self): raise AssertionError('unused parent payload inspected')
    def __repr__(self): raise AssertionError('unused parent payload serialized')
    def __deepcopy__(self, _): raise AssertionError('unused parent payload copied')


class JointInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.small = parent_components()
        cls.small['raw_current'] = inputs._raw_current(cls.small)

    def small_copy(self): return copy.deepcopy(self.small)

    def test_only_own_held_structural_scores_no_training_scores_sibling_or_lexical(self):
        data = self.small_copy(); fold = 2; own = data['parent_folds'][fold]
        guarded = OwnOnly(fold, own); data['parent_folds'] = guarded
        own['models']['lexical_C'] = Poison()
        for row in own['predictions']:
            row['candidate_edit_tokens'] = Poison()
            for method in inputs.ORIGINAL_METHODS - set(inputs.capsule.BASELINES):
                row['candidate_scores'][method] = Poison(); row['choices'][method] = Poison()
        with (patch.object(Path, 'read_bytes', side_effect=AssertionError('no files')),
             patch('builtins.open', side_effect=AssertionError('no files')),
             patch.object(inputs.previous, 'project_fold', side_effect=AssertionError('no old projection')),
             patch.object(inputs.features, 'fit_own_scaler', side_effect=AssertionError('no scaler fit')),
             patch.object(inputs.features.StandardScaler, 'fit', side_effect=AssertionError('no fit')),
             patch.object(inputs.structural, 'score_model', wraps=inputs.structural.score_model) as scorer):
            projected = inputs.project_fold(data, fold)
        train, held = inputs.capsule.scope(projected)
        self.assertEqual(guarded.accesses, [fold])
        self.assertEqual(scorer.call_count, len(held))
        self.assertEqual([call.args[1].current.submission_id for call in scorer.call_args_list],
            [ex.example_id for ex in held])
        self.assertTrue(all(call.args[0] is own['models']['structural_C'] and call.args[2] == ()
            for call in scorer.call_args_list))
        self.assertTrue(set(ex.example_id for ex in train).isdisjoint(
            call.args[1].current.submission_id for call in scorer.call_args_list))
        self.assertEqual(set(vars(projected)), set(inputs.capsule.FoldInputs.__dataclass_fields__))
        for row in projected.parent_predictions:
            self.assertEqual(set(row), inputs.capsule.PREDICTION_FIELDS)
            self.assertEqual(set(row['choices']), set(inputs.capsule.PARENT_METHODS))
            self.assertEqual(set(row['candidate_scores']), set(inputs.capsule.BASELINES))

    def test_full320_all_five_folds_raw_and_accepted_bytes_roundtrip_without_exclusion(self):
        data = parent_components(320); data['synthetic'] = False
        data['raw_current'] = inputs._raw_current(data)
        covered = []
        for fold in range(5):
            projected = inputs.project_fold(data, fold)
            self.assertIs(projected.raw_current, data['raw_current'])
            train, held = inputs.capsule.scope(projected)
            covered.extend(ex.example_id for ex in held)
            self.assertEqual(set(projected.parent_training), inputs.capsule.TRAINING_FIELDS)
            self.assertEqual(projected.parent_training['informative_train_example_ids'], [e.example_id for e in train])
            for arm in inputs.capsule.ARMS:
                for bid, block in data['interactions'][arm].items():
                    self.assertEqual(projected.interactions[arm][bid].matrix.tobytes(), block.matrix.tobytes())
            self.assertEqual(projected.examples, data['examples'])
        self.assertEqual(sorted(covered), sorted(e.example_id for e in data['examples']))
        self.assertEqual((len(projected.examples), len({e.observation.problem_id for e in projected.examples}),
            sum(len(b.candidates) for b in projected.banks.values())), (320, 23, 2544))
        body = inputs.capsule.encode_inputs(projected)
        decoded = inputs.capsule.decode_inputs(json.loads(json.dumps(body, allow_nan=False)))
        self.assertEqual(decoded.examples, projected.examples)
        for bid, raw in data['raw_current'].items():
            for name in ('numeric', 'hashed'):
                self.assertEqual(inputs.capsule._encode_csr(getattr(raw, name)),
                    inputs.capsule._encode_csr(getattr(decoded.raw_current[bid], name)))
        for arm in inputs.capsule.ARMS:
            for bid, block in data['interactions'][arm].items():
                self.assertEqual(block.matrix.tobytes(), decoded.interactions[arm][bid].matrix.tobytes())
                self.assertTrue(np.signbit(decoded.interactions[arm][bid].matrix[0, 5]))
        text = json.dumps(body)
        for forbidden in ('base_scores', 'parent_folds', 'numeric_scale', 'coefficients', 'label_contract', 'source_bindings'):
            self.assertNotIn('"'+forbidden+'"', text)

    def test_metadata_is_detached_from_original_parent_and_assignment(self):
        data = self.small_copy(); projected = inputs.project_fold(data, 0)
        saved_training = copy.deepcopy(projected.parent_training)
        saved_predictions = copy.deepcopy(projected.parent_predictions)
        saved_assignment = copy.deepcopy(projected.assignment)
        own = data['parent_folds'][0]
        own['models']['structural_C']['training']['pair_example_ids'].clear()
        own['predictions'][0]['choices'].clear()
        own['predictions'][0]['candidate_scores']['structural_C'].clear()
        data['assignment']['example_fold'].clear()
        self.assertEqual(projected.parent_training, saved_training)
        self.assertEqual(projected.parent_predictions, saved_predictions)
        self.assertEqual(projected.assignment, saved_assignment)
        self.assertEqual(projected.parent_structure_model_sha256, own['models']['structural_C']['model_sha256'])

    def test_wrapper_only_delegates_auth_reader_preserves_two_configs_and_binding_maps(self):
        # A mocked return value, not an invocation of any actual artifact reader.
        data = parent_components(320); data['synthetic'] = False
        data['feature_configuration'] = inputs.previous.progress.configuration()
        data['source_bindings'] = {'/synthetic/source.py': 'a'*64}
        data['input_bindings'] = {'/synthetic/accepted/COMPLETE.json': 'b'*64}
        with (patch.object(inputs.previous, 'load_observed_components', return_value=data) as reader,
             patch.object(inputs.previous, 'project_fold', side_effect=AssertionError('no old projection')),
             patch.object(inputs.features, 'fit_own_scaler', side_effect=AssertionError('no scaler')),
             patch.object(inputs.structural, 'score_model', side_effect=AssertionError('no model scoring in assembly')),
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no actual reader'))):
            result = inputs.load_observed_components(Path('/synthetic/project'))
        reader.assert_called_once_with(Path('/synthetic/project'))
        self.assertEqual(result['feature_configuration'], inputs.previous.progress.configuration())
        self.assertEqual(result['joint_feature_configuration'], inputs.features.configuration())
        self.assertNotEqual(result['feature_configuration'], result['joint_feature_configuration'])
        self.assertEqual(len(result['raw_current']), 320)
        self.assertEqual(sum(len(v.candidate_ids) for v in result['raw_current'].values()), 2544)
        self.assertNotIn('raw_current', data); self.assertNotIn('joint_feature_configuration', data)
        for key in ('source_bindings', 'input_bindings', 'feature_configuration'):
            self.assertEqual(result[key], data[key]); self.assertIsNot(result[key], data[key])
        result['source_bindings'].clear(); self.assertTrue(data['source_bindings'])

    def test_auth_reader_failure_and_incomplete_or_synthetic_return_have_no_fallback(self):
        with (patch.object(inputs.previous, 'load_observed_components', side_effect=ValueError('unavailable readiness')),
             patch.object(inputs.features, 'raw_current', side_effect=AssertionError('no fallback')) as raw,
             self.assertRaisesRegex(ValueError, 'unavailable readiness')):
            inputs.load_observed_components(Path('/synthetic/project'))
        raw.assert_not_called()
        for missing in ('feature_configuration', 'source_bindings', 'input_bindings', 'synthetic_false'):
            data = self.small_copy(); data['synthetic'] = False
            data.update(feature_configuration=inputs.previous.progress.configuration(),
                source_bindings={'/synthetic/source.py': 'a'*64}, input_bindings={'/synthetic/input.json': 'b'*64})
            if missing == 'synthetic_false': data['synthetic'] = True
            else: data.pop(missing)
            with (self.subTest(missing=missing), patch.object(inputs.previous, 'load_observed_components', return_value=data),
                 self.assertRaises(ValueError)): inputs.load_observed_components(Path('/synthetic/project'))

    def test_reject_forbidden_coordinator_fields_or_drifted_configs(self):
        for key in ('base_scores', 'labels', 'label_contracts', 'scaler', 'coefficients', 'all_training_labels'):
            data = self.small_copy(); data[key] = Poison()
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exact accepted coordinator'):
                inputs.project_fold(data, 0)
        for key in ('feature_configuration', 'joint_feature_configuration'):
            data = self.small_copy(); data[key] = {'changed': True}
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'configuration'):
                inputs.project_fold(data, 0)

    def test_strict_fold_synthetic_and_original_assignment(self):
        for fold in (True, 0., -1, 5, '0'):
            with self.subTest(fold=fold), self.assertRaises(ValueError): inputs.project_fold(self.small, fold)
        for mode in ('bool', 'small_production', 'changed_assignment', 'missing_bank', 'extra_bank'):
            data = self.small_copy()
            if mode == 'bool': data['synthetic'] = 1
            elif mode == 'small_production': data['synthetic'] = False
            elif mode == 'changed_assignment': data['assignment']['example_fold'][data['examples'][0].example_id] = 99
            elif mode == 'missing_bank': data['banks'].pop(data['examples'][-1].bank_id)
            else: data['banks']['foreign'] = data['banks'][data['examples'][0].bank_id]
            with self.subTest(mode=mode), self.assertRaises((ValueError, KeyError)): inputs.project_fold(data, 0)

    def test_cached_raw_is_replayed_and_never_accepts_scaled_or_foreign_features(self):
        for mode in ('numeric', 'hashed', 'extra', 'missing', 'order'):
            data = self.small_copy(); bid = data['examples'][0].bank_id; block = data['raw_current'][bid]
            if mode in ('numeric', 'hashed'):
                matrix = getattr(block, mode).copy(); matrix.data[0] += .5
                data['raw_current'][bid] = replace(block, **{mode: matrix})
            elif mode == 'extra': data['raw_current']['foreign'] = block
            elif mode == 'missing': data['raw_current'].pop(bid)
            else: data['raw_current'][bid] = replace(block, candidate_ids=tuple(reversed(block.candidate_ids)))
            with self.subTest(mode=mode), self.assertRaises(ValueError): inputs.project_fold(data, 0)

    def test_held_model_auth_and_exact_scores_or_sha_tie_are_required(self):
        for mode in ('unsealed', 'resealed_coef', 'score', 'tie', 'extra_score', 'wrong_model'):
            data = self.small_copy(); own = data['parent_folds'][0]
            model = own['models']['structural_C']; row = own['predictions'][0]
            if mode in ('unsealed', 'resealed_coef'):
                # Use an actually nonzero held coordinate. Changing a zero
                # column cannot falsify score parity; external parent byte
                # authentication is the unchanged reader's responsibility.
                coordinate = 3 + int(data['raw_current'][row['bank_id']].hashed.nonzero()[1][0])
                model['coefficients'][coordinate] = 1.
                if mode == 'resealed_coef': reseal(model)
            elif mode == 'score': row['candidate_scores']['structural_C'][next(iter(row['candidate_scores']['structural_C']))] = .5
            elif mode == 'tie': row['choices']['structural_C'] = max(row['candidate_scores']['structural_C'])
            elif mode == 'extra_score': row['candidate_scores']['structural_C']['f'*64] = 0.
            else: model['variant'] = 'lexical'; reseal(model)
            with self.subTest(mode=mode), self.assertRaises(ValueError): inputs.project_fold(data, 0)

    def test_own_parent_scope_and_training_or_held_extras_fail_closed(self):
        for mode in ('train_order', 'held_order', 'fold_bool', 'missing_predictions', 'foreign_prediction',
                     'held_in_training', 'extra_model', 'training_label_hash', 'prediction_label_hash'):
            data = self.small_copy(); own = data['parent_folds'][0]; model = own['models']['structural_C']
            if mode == 'train_order': own['train_example_ids'] = tuple(reversed(own['train_example_ids']))
            elif mode == 'held_order': own['held_example_ids'] = tuple(reversed(own['held_example_ids']))
            elif mode == 'fold_bool': own['fold'] = False
            elif mode == 'missing_predictions': own['predictions'] = own['predictions'][:-1]
            elif mode == 'foreign_prediction': own['predictions'][0]['example_id'] = own['train_example_ids'][0]
            elif mode == 'held_in_training':
                model['training']['pair_example_ids'][0] = own['held_example_ids'][0]; reseal(model)
            elif mode == 'extra_model': own['models']['foreign'] = Poison()
            elif mode == 'training_label_hash': model['training']['labels_sha256'] = 'e'*64; reseal(model)
            else: own['predictions'][0]['labels_sha256'] = 'e'*64
            with self.subTest(mode=mode), self.assertRaises(ValueError): inputs.project_fold(data, 0)


if __name__ == '__main__': unittest.main()
