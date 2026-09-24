"""Nonauthor source-only adapter regressions; synthetic objects, no fits/I/O."""
import copy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_joint_progress_inputs as subject
from tests import test_zpd_joint_progress_inputs as author


class JointInputsIndependentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = author.parent_components()
        cls.data['raw_current'] = subject._raw_current(cls.data)

    def fresh(self):
        return copy.deepcopy(self.data)

    def test_every_fold_has_no_sibling_or_discarded_metadata_access(self):
        for fold in range(5):
            with self.subTest(fold=fold):
                data = self.fresh()
                own = data['parent_folds'][fold]
                own['models']['lexical_C'] = author.Poison()
                parents = author.OwnOnly(fold, own)
                data['parent_folds'] = parents
                # Coordinator-only provenance and language-bearing observations
                # are externally authenticated, not copied into an own job.
                for key in ('observations', 'parent_complete_sha256', 'source_bindings', 'input_bindings'):
                    data[key] = author.Poison()
                with (patch.object(Path, 'open', side_effect=AssertionError('no file read')),
                      patch('builtins.open', side_effect=AssertionError('no file read')),
                      patch.object(subject.previous, 'project_fold', side_effect=AssertionError('old projection')),
                      patch.object(subject.features, 'fit_own_scaler', side_effect=AssertionError('scaler')),
                      patch.object(subject.structural, 'score_model', wraps=subject.structural.score_model) as scorer):
                    value = subject.project_fold(data, fold)
                    serialized = subject.capsule.encode_inputs(value)
                self.assertEqual(parents.accesses, [fold])
                train, held = subject.capsule.scope(value)
                self.assertEqual([c.args[1].current.submission_id for c in scorer.call_args_list],
                                 [e.example_id for e in held])
                self.assertEqual(len(scorer.call_args_list), len(held))
                self.assertTrue(set(e.example_id for e in train).isdisjoint(
                    c.args[1].current.submission_id for c in scorer.call_args_list))
                self.assertEqual(value.examples, data['examples'])
                for before, after in zip(data['examples'], serialized['examples'], strict=True):
                    self.assertEqual(len(after['observation']['prior']), len(before.observation.prior))
                    self.assertEqual(len(after['donor_history']), len(before.donor_history))
                self.assertTrue(set(serialized).isdisjoint({'parent_folds', 'base_scores', 'source_bindings',
                    'input_bindings', 'observations', 'scaler', 'coefficients', 'label_contracts'}))

    def test_nonzero_parent_is_held_reference_not_current_or_progress_input(self):
        data = self.fresh()
        before = subject.project_fold(data, 3)
        parent = data['parent_folds'][3]
        model = parent['models']['structural_C']
        model['numeric_scale'] = [2., 3., 5.]
        model['coefficients'] = [float((i % 7) - 3) / 17. for i in range(4099)]
        author.reseal(model)
        held = subject.capsule.scope(before)[1]
        for ex, prediction in zip(held, parent['predictions'], strict=True):
            scores = subject.structural.score_model(model, ex.observation, (), data['banks'][ex.bank_id])
            prediction['candidate_scores']['structural_C'] = scores
            prediction['choices']['structural_C'] = min(scores, key=lambda cid: (-scores[cid], cid))
        after = subject.project_fold(data, 3)
        self.assertNotEqual(before.parent_structure_model_sha256, after.parent_structure_model_sha256)
        self.assertNotEqual(before.parent_predictions, after.parent_predictions)
        self.assertEqual(before.parent_training, after.parent_training)
        for ex in data['examples']:
            bid = ex.bank_id
            # Frozen raw primitive is the parity reference, not scaled model
            # features or old project_fold's all-recipient learned scores.
            expected = subject.structural.raw_features(ex.observation, (), data['banks'][bid], 'C', 'structural')
            for name, reference in zip(('numeric', 'hashed'), expected, strict=True):
                encode = subject.capsule._encode_csr
                self.assertEqual(encode(getattr(before.raw_current[bid], name)), encode(reference))
                self.assertEqual(encode(getattr(after.raw_current[bid], name)), encode(reference))
            for arm in subject.capsule.ARMS:
                self.assertEqual(before.interactions[arm][bid].matrix.tobytes(),
                                 after.interactions[arm][bid].matrix.tobytes())

    def test_strict_progress_checks_are_not_bypassed_by_projection(self):
        for mode in ('common_G', 'CF_tail', 'noop', 'order', 'bound', 'missing_arm'):
            with self.subTest(mode=mode):
                data = self.fresh()
                bid = data['examples'][0].bank_id
                arm = 'CF' if mode == 'CF_tail' else 'H'
                block = data['interactions'][arm][bid]
                ids = block.candidate_ids
                noop = next(i for i, candidate in enumerate(data['banks'][bid].candidates) if candidate.is_noop)
                edited = next(i for i in range(len(ids)) if i != noop)
                matrix = block.matrix.copy()
                if mode == 'common_G': matrix[edited, 0] += .01
                elif mode == 'CF_tail': matrix[edited, 17] = .01
                elif mode == 'noop': matrix[noop, 17] = .01
                elif mode == 'order': ids = tuple(reversed(ids))
                elif mode == 'bound': matrix[edited, 17] = 2.
                else: del data['interactions']['L']
                if mode != 'missing_arm':
                    data['interactions'][arm][bid] = replace(block, candidate_ids=ids, matrix=matrix)
                with self.assertRaises(ValueError): subject.project_fold(data, 1)

    def test_accepted_loader_failure_does_not_attempt_any_projection_or_raw_fallback(self):
        with (patch.object(subject.previous, 'load_observed_components', side_effect=RuntimeError('sealed reader rejected')) as reader,
              patch.object(subject.features, 'raw_current', side_effect=AssertionError('raw fallback')) as raw,
              patch.object(subject.structural, 'score_model', side_effect=AssertionError('old model score')) as score,
              patch.object(subject.previous, 'project_fold', side_effect=AssertionError('old projection')),
              patch.object(Path, 'open', side_effect=AssertionError('no file access')),
              self.assertRaisesRegex(RuntimeError, 'sealed reader rejected')):
            subject.load_observed_components(Path('/synthetic/no-artifacts'))
        reader.assert_called_once_with(Path('/synthetic/no-artifacts'))
        raw.assert_not_called(); score.assert_not_called()

    def test_loader_assembly_never_inspects_parent_models_or_fits_a_transform(self):
        data = self.fresh()
        data.update(synthetic=False, parent_folds=author.Poison(),
                    feature_configuration=subject.previous.progress.configuration(),
                    source_bindings={'/synthetic/frozen/code.py': 'a' * 64},
                    input_bindings={'/synthetic/frozen/COMPLETE.json': 'b' * 64})
        # Production completeness/authenticity is the delegated reader's job;
        # this fake small return exercises only the wrapper's assembly seam.
        with (patch.object(subject.previous, 'load_observed_components', return_value=data),
              patch.object(subject.structural, 'score_model', side_effect=AssertionError('no scoring in assembly')),
              patch.object(subject.features, 'fit_own_scaler', side_effect=AssertionError('no scaling')),
              patch.object(subject.previous, 'project_fold', side_effect=AssertionError('no old projection')),
              patch.object(Path, 'open', side_effect=AssertionError('no new file reads'))):
            result = subject.load_observed_components(Path('/synthetic/no-artifacts'))
        self.assertIs(result['parent_folds'], data['parent_folds'])
        self.assertEqual(set(result['raw_current']), set(data['banks']))
        self.assertEqual(result['readiness_complete_sha256'], subject.SUPPORT_SHA)

    def test_accepted_negative_zero_bytes_and_raw_source_drift_are_distinct(self):
        data = self.fresh()
        value = subject.project_fold(data, 4)
        for arm in subject.capsule.ARMS:
            for bid in data['banks']:
                matrix = value.interactions[arm][bid].matrix
                self.assertEqual(matrix.tobytes(), data['interactions'][arm][bid].matrix.tobytes())
                self.assertTrue(np.signbit(matrix[0, 5]))
        bid = data['examples'][0].bank_id
        raw = data['raw_current'][bid]
        edited = raw.numeric.copy()
        edited.data[0] += .125
        data['raw_current'][bid] = replace(raw, numeric=edited)
        with self.assertRaisesRegex(ValueError, 'raw current differs'):
            subject.project_fold(data, 4)


if __name__ == '__main__': unittest.main()
