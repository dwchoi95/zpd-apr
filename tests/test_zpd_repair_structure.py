"""Synthetic representation checks, never empirical performance evidence."""
import copy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts.zpd_repair_fit import history, load_inputs
from scripts.zpd_repair_pairwise import lexical_features, score_model as old_scores
from scripts.zpd_repair_risk import train_fixed_ranker
from scripts.zpd_repair_structure import (
    HASH_DIMENSION, raw_features, score_model, select_model, structural_features,
    structure_counts, train_model, training_data)
from src.repair.pilot_contracts import CandidateAttempt, canonical_hash, source_hash
from src.repair.pilot_ranker import features
from tests.test_zpd_repair_pairwise import fixture


def rebound(model):
    model['model_sha256'] = canonical_hash({key: value for key, value in model.items()
                                          if key != 'model_sha256'})
    return model


class StructureTests(unittest.TestCase):
    def data(self):
        return load_inputs(*fixture())

    def test_lexical_control_exact_fixed_ranker_parity(self):
        examples, banks, labels = self.data()
        for condition in ('C', 'H', 'U'):
            prior = train_fixed_ranker(examples, banks, labels, condition, 1900)
            new = train_model(examples, banks, labels, condition, 'lexical')
            self.assertEqual(prior['coefficients'], new['coefficients'])
            self.assertEqual(prior['numeric_scale'], new['numeric_scale'])
            self.assertEqual(prior['training'], new['training'])
            for ex in examples:
                supplied = history(ex, condition)
                self.assertEqual(old_scores(prior, ex.observation, supplied, banks[ex.bank_id]),
                                 score_model(new, ex.observation, supplied, banks[ex.bank_id]))

    def test_order_breaks_same_bag_numeric_collision(self):
        examples, banks, _ = self.data()
        ex = examples[0]
        left = b'ans *= value\nif ans > 10**18:\n    exit()\n'
        right = b'if ans > 10**18:\n    exit()\nans *= value\n'
        self.assertEqual(features(ex.observation, left, history=()),
                         features(ex.observation, right, history=()))
        self.assertEqual(lexical_features(ex.observation.current.source, left),
                         lexical_features(ex.observation.current.source, right))
        self.assertNotEqual(structural_features(ex.observation.current.source, left),
                            structural_features(ex.observation.current.source, right))
        counts = structure_counts(left)
        self.assertIn('adjacent:Module.body:AugAssign:Mult|value=Name=>If|test=Compare:Gt', counts)
        bank = replace(banks[ex.bank_id], attempts=tuple(CandidateAttempt(i, i, 'success',
            left if i % 2 else right) for i in range(8)))
        numeric, lexical = raw_features(ex.observation, (), bank, 'C', 'lexical')
        structural_numeric, structural = raw_features(ex.observation, (), bank, 'C', 'structural')
        np.testing.assert_array_equal(numeric.toarray(), structural_numeric.toarray())
        np.testing.assert_array_equal(lexical[1].toarray(), lexical[2].toarray())
        self.assertGreater((structural[1]-structural[2]).nnz, 0)

    def test_ast_local_field_and_condition_operations_are_present(self):
        counts = structure_counts(b'while x < 3:\n    x += 1\n')
        self.assertIn('field:Module.body[0]=>While|test=Compare:Lt', counts)
        self.assertIn('field:While.body[0]=>AugAssign:Add|value=Constant', counts)
        self.assertIn('field:Compare.ops[0]=>Lt', counts)
        self.assertNotEqual(counts, structure_counts(b'while x > 3:\n    x -= 1\n'))

    def test_same_hash_capacity_and_candidate_l2(self):
        examples, banks, labels = self.data()
        for condition in ('C', 'H', 'U'):
            shapes = []
            for variant in ('lexical', 'structural'):
                ex = examples[0]
                _, hashed = raw_features(ex.observation, history(ex, condition), banks[ex.bank_id], condition, variant)
                self.assertEqual(hashed.shape[1], HASH_DIMENSION)
                np.testing.assert_allclose(np.asarray(hashed.multiply(hashed).sum(axis=1)).ravel(), 1.)
                model = train_model(examples, banks, labels, condition, variant)
                shapes.append(len(model['coefficients']))
                self.assertEqual(model['feature_config']['hash_dimension'], 4096)
            self.assertEqual(shapes[0], shapes[1])

    def test_deterministic_syntax_encoding_fallback_retains_order(self):
        for source in (b'if (:\n\xffa b\n', b'# coding: absent-encoding\nx=1\n', b'\x00x = 1\n'):
            with self.subTest(source=source):
                first = structure_counts(source)
                self.assertEqual(first['parse:byte_fallback'], 1)
                self.assertEqual(first, structure_counts(source))
                features_before = structural_features(b'x=0\n', source)
                self.assertTrue(all(np.isfinite(v) and v > 0 for v in features_before.values()))
                first['injected'] = 10
                self.assertNotIn('injected', structure_counts(source))
        left, right = b'if (:\n\xffa b\n', b'if (:\nb \xffa\n'
        self.assertEqual(lexical_features(b'', left), lexical_features(b'', right))
        self.assertNotEqual(structural_features(b'', left), structural_features(b'', right))
        self.assertTrue(any(':ff:' in name or name.endswith(':ff') for name in structure_counts(left)))

    def test_fallback_covers_entire_token_stream_and_empty_code(self):
        source = b'if (: ' + b'x ' * 500 + b'last_token\xff'
        counts = structure_counts(source)
        self.assertTrue(any('6c6173745f746f6b656e:ff:EOS' in name for name in counts))
        self.assertEqual(counts['fallback:3:78:78:78'], 498)
        self.assertEqual(structure_counts(b'')['parse:ast'], 1)
        with self.assertRaises(TypeError):
            structural_features('text', b'x=1')
        with self.assertRaises(TypeError):
            structural_features(b'x=0', bytearray(b'x=1'))

    def test_arbitrary_candidate_bytes_are_kept_in_scores(self):
        examples, banks, labels = self.data()
        model = train_model(examples, banks, labels, 'C', 'structural')
        ex = examples[-1]
        candidate = b'\xff\x00if (:\r\n'
        bank = replace(banks[ex.bank_id], attempts=tuple(CandidateAttempt(i, i, 'success', candidate)
                                                       for i in range(8)))
        before = bank.seal_sha256
        scores = score_model(model, ex.observation, (), bank)
        self.assertEqual(set(scores), {source_hash(bank.current_source), source_hash(candidate)})
        self.assertTrue(all(np.isfinite(value) for value in scores.values()))
        self.assertEqual(bank.seal_sha256, before)
        self.assertEqual(bank.attempts[0].source, candidate)

    def test_train_only_labels_codes_and_scaler(self):
        examples, banks, labels = self.data()
        train_labels = {key: value for key, value in labels.items() if key[0] != 'b2'}
        train_banks = {key: value for key, value in banks.items() if key != 'b2'}
        for condition in ('C', 'H', 'U'):
            for variant in ('lexical', 'structural'):
                first = train_model(examples, banks, labels, condition, variant)
                second = train_model(examples, train_banks, train_labels, condition, variant)
                third = train_model(examples[:2], train_banks, train_labels, condition, variant)
                self.assertEqual(first, second)
                self.assertEqual(first, third)

    def test_equal_user_weights_fixed_total_and_mirrored_pairs(self):
        examples, banks, labels = self.data()
        labels['b0', source_hash(b'x = 2\n')]['loss'] = 0.
        extra = copy.copy(examples[0]); extra.example_id = 'extra'
        examples.append(extra)
        for variant in ('lexical', 'structural'):
            x, y, weights, _, meta = training_data(examples, banks, labels, 'H', variant)
            np.testing.assert_allclose(x[0::2].toarray(), -x[1::2].toarray())
            np.testing.assert_array_equal(y[0::2], 1-y[1::2])
            users = {ex.example_id: ex.user_id for ex in examples}
            totals = {user: 0. for user in ('u0', 'u1')}
            for ident, weight in zip(meta['pair_example_ids'], weights):
                totals[users[ident]] += weight
            self.assertAlmostEqual(totals['u0'], 950.)
            self.assertAlmostEqual(totals['u1'], 950.)
            self.assertAlmostEqual(float(weights.sum()), 1900.)
            self.assertAlmostEqual(meta['sample_weight_sum'], 1900.)

    def test_unknown_candidates_pairless_prefixes_and_no_pairs(self):
        examples, banks, labels = self.data()
        for (bid, _), label in labels.items():
            if bid == 'b0': label.update(status='unknown', gain=None, loss=None, all_ac=None)
        for variant in ('lexical', 'structural'):
            model = train_model(examples, banks, labels, 'H', variant)
            self.assertEqual(model['training']['uninformative_train_prefixes'], 1)
            self.assertEqual(model['training']['stable_train_candidates'], 3)
            self.assertEqual(model['training']['informative_train_example_ids'], ['e1'])
        for (bid, _), label in labels.items():
            if bid == 'b1': label.update(status='unknown', gain=None, loss=None, all_ac=None)
        with self.assertRaisesRegex(ValueError, 'no unequal'):
            train_model(examples, banks, labels, 'H', 'structural')

    def test_prediction_never_fits_and_roundtrip_preserves_scores(self):
        examples, banks, labels = self.data()
        model = train_model(examples, banks, labels, 'H', 'structural')
        ex = examples[-1]
        bank = banks[ex.bank_id]
        expected = score_model(model, ex.observation, ex.observation.prior, bank)
        with patch.object(LogisticRegression, 'fit', side_effect=AssertionError('fit called')), \
             patch.object(StandardScaler, 'fit', side_effect=AssertionError('scaler fit called')):
            actual = score_model(json.loads(json.dumps(model)), ex.observation, ex.observation.prior, bank)
            chosen = select_model(model, ex.observation, ex.observation.prior, bank)
        self.assertEqual(actual, expected)
        self.assertEqual(chosen, min(expected, key=lambda key: (-expected[key], key)))

    def test_hash_schema_and_rehashed_configuration_tamper_rejected(self):
        examples, banks, labels = self.data()
        ex = examples[-1]
        model = train_model(examples, banks, labels, 'C', 'structural')
        for mutation in ('hash', 'extra', 'dimension', 'scale', 'type', 'config', 'config_type', 'mass', 'C', 'metadata'):
            bad = copy.deepcopy(model)
            if mutation == 'hash': bad['coefficients'][0] += 1
            if mutation == 'extra': bad['labels'] = {}
            if mutation == 'dimension': bad['coefficients'].pop()
            if mutation == 'scale': bad['numeric_scale'][0] = 0
            if mutation == 'type': bad['intercept'] = False
            if mutation == 'config': bad['feature_config']['fallback_ngram_lengths'] = [2]
            if mutation == 'config_type': bad['feature_config']['hash_dimension'] = 4096.
            if mutation == 'mass': bad['training']['sample_weight_sum'] = 1.
            if mutation == 'C': bad['C'] = 1.
            if mutation == 'metadata': bad['training']['ignored_labels'] = {}
            if mutation not in ('hash', 'extra'): rebound(bad)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                score_model(bad, ex.observation, (), banks[ex.bank_id])

    def test_fixed_reference_and_split_contracts(self):
        examples, banks, labels = self.data()
        for value in (0, 1, -1, float('nan'), float('inf'), True, '1900'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                train_model(examples, banks, labels, 'C', 'structural', value)
        invalid = copy.copy(examples[-1]); invalid.split = 'test'
        with self.assertRaisesRegex(ValueError, 'train and exposed valid'):
            train_model(examples+[invalid], banks, labels, 'C', 'structural')
        with self.assertRaisesRegex(ValueError, 'variant'):
            train_model(examples, banks, labels, 'C', 'other')

    def test_authentic_history_and_current_only_contracts(self):
        examples, banks, labels = self.data()
        ex = examples[-1]; bank = banks[ex.bank_id]
        model = train_model(examples, banks, labels, 'C', 'structural')
        with self.assertRaisesRegex(ValueError, 'empty history'):
            score_model(model, ex.observation, ex.observation.prior, bank)
        model = train_model(examples, banks, labels, 'H', 'structural')
        with self.assertRaisesRegex(ValueError, 'authentic'):
            score_model(model, ex.observation, ex.donor_history, bank)

    def test_complete_long_history_reaches_unchanged_numeric_features(self):
        examples, banks, _ = self.data()
        ex = examples[0]; bank = banks[ex.bank_id]
        prior = tuple(replace(ex.observation.prior[0], timestamp=i+1, submission_id='long-'+str(i))
                      for i in range(100))
        observation = replace(ex.observation, prior=prior,
            current=replace(ex.observation.current, timestamp=101))
        from scripts.zpd_repair_pairwise import numeric_names
        index = numeric_names('H').index('history_count')
        for variant in ('lexical', 'structural'):
            numeric, _ = raw_features(observation, observation.prior, bank, 'H', variant)
            np.testing.assert_array_equal(numeric[:, index].toarray().ravel(), 100.)

    def test_metadata_ids_hashes_verdicts_and_paths_not_features(self):
        examples, banks, _ = self.data()
        ex = examples[0]; bank = banks[ex.bank_id]
        current = replace(ex.observation.current, submission_id='/changed/current', verdict='AC')
        prior = tuple(replace(item, submission_id='/changed/prior/'+str(i), verdict='TLE')
                      for i, item in enumerate(ex.observation.prior))
        other = replace(ex.observation, problem_id='/changed/problem', current=current, prior=prior)
        other_bank = replace(bank, problem_id=other.problem_id, generator_config_sha256='b'*64)
        for variant in ('lexical', 'structural'):
            first = raw_features(ex.observation, ex.observation.prior, bank, 'H', variant)
            second = raw_features(other, other.prior, other_bank, 'H', variant)
            for left, right in zip(first, second):
                np.testing.assert_array_equal(left.toarray(), right.toarray())


if __name__ == '__main__':
    unittest.main()
