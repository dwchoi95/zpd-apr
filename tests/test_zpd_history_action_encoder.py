"""Synthetic action/state semantics and temporal isolation, not performance."""
import copy
import math
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_history_action_encoder as encoder


def prior(code, timestamp, verdict='WA', language='Python'):
    return dict(code=code, verdict=verdict, timestamp=timestamp, language=language)


class HistoryActionEncoderTests(unittest.TestCase):
    def event(self, before, after, **kwargs):
        values, mask = encoder.encode_edit(before, after, **kwargs)
        return dict(zip(encoder.EVENTS, values)), dict(zip(encoder.EVENTS, mask))

    def test_fixed_taxonomy_binary_values_and_masks(self):
        self.assertEqual(len(encoder.EVENTS), 18)
        self.assertEqual(len(set(encoder.EVENTS)), 18)
        values, mask = encoder.encode_edit('x=1\n', 'x=2\n')
        self.assertEqual(values.shape, (18,))
        self.assertEqual(mask.dtype, np.dtype(bool))
        self.assertTrue(mask.all())
        self.assertTrue(np.isin(values, (0., 1.)).all())
        self.assertEqual(encoder.AST_FEATURE_VERSION, (3, 10))

    def test_exact_repeat_and_token_equivalent_surface_change(self):
        values, mask = self.event('x = 1\n', 'x = 1\n')
        self.assertEqual(values['exact_repeat'], 1.)
        self.assertEqual(sum(values.values()), 1.)
        values, mask = self.event('x = 1\n', 'x=1  # comment\r\n')
        self.assertEqual(values['exact_repeat'], 0.)
        self.assertEqual(values['token_equivalent_surface_change'], 1.)
        self.assertEqual(values['other_lexical_change'], 0.)
        self.assertEqual(sum(values.values()), 1.)

    def test_indentation_semantics_not_surface_equivalent(self):
        before = 'if x:\n    y()\nz()\n'
        after = 'if x:\n    y()\n    z()\n'
        values, mask = self.event(before, after)
        self.assertTrue(mask['token_equivalent_surface_change'])
        self.assertEqual(values['token_equivalent_surface_change'], 0.)
        self.assertEqual(values['ordered_ast_relation_change'], 1.)

    def test_each_family_detects_explicit_synthetic_change(self):
        examples = {
            'arithmetic_edit': ('x=a+b\n', 'x=a-b\n'),
            'comparison_edit': ('x=a<b\n', 'x=a>b\n'),
            'boolean_edit': ('x=a and b\n', 'x=a or b\n'),
            'branch_edit': ('if x:\n y=1\n', 'if x:\n y=2\n'),
            'loop_edit': ('for x in a:\n y=1\n', 'for x in a:\n y=2\n'),
            'binding_edit': ('x=1\n', 'x=2\n'),
            'call_edit': ('f(1)\n', 'f(2)\n'),
            'indexing_container_edit': ('a[0]\n', 'a[1]\n'),
            'function_return_edit': ('def f():\n return 1\n', 'def f():\n return 2\n'),
            'exception_edit': ('raise ValueError("a")\n', 'raise ValueError("b")\n'),
            'import_edit': ('import os\n', 'import sys\n'),
        }
        self.assertEqual(set(examples), set(encoder.FAMILY_EVENTS))
        for family, (before, after) in examples.items():
            with self.subTest(family=family):
                values, mask = self.event(before, after)
                self.assertTrue(mask[family])
                self.assertEqual(values[family], 1.)

    def test_order_changes_same_node_and_token_bags(self):
        before = 'ans *= value\nif ans > 10**18:\n    exit()\n'
        after = 'if ans > 10**18:\n    exit()\nans *= value\n'
        values, mask = self.event(before, after)
        self.assertEqual(values['ordered_ast_relation_change'], 1.)
        self.assertTrue(mask['ordered_ast_relation_change'])
        self.assertEqual(values['arithmetic_edit'], 0.)
        left = encoder.encode_observation(before, 'WA', [], 10, 'C0')
        right = encoder.encode_observation(after, 'WA', [], 10, 'C0')
        self.assertNotEqual(left, right)
        values, _ = self.event('x=a-b\n', 'x=b-a\n')
        self.assertEqual(values['ordered_ast_relation_change'], 1.)

    def test_parse_masks_do_not_turn_unknown_into_negative_family_labels(self):
        values, mask = self.event('x=(\n', 'x=1\n')
        self.assertEqual(values['parse_recovery'], 1.)
        self.assertTrue(mask['parse_recovery'])
        self.assertFalse(mask['token_equivalent_surface_change'])
        for family in (*encoder.FAMILY_EVENTS, 'ordered_ast_relation_change'):
            self.assertFalse(mask[family])
            self.assertEqual(values[family], 0.)
        self.assertEqual(values['other_lexical_change'], 1.)
        values, mask = self.event('x=1\n', 'x=(\n')
        self.assertEqual(values['parse_loss'], 1.)
        self.assertFalse(mask['binding_edit'])

    def test_nonpython_mask_and_fallback_are_explicit(self):
        values, mask = self.event('x=1\n', 'x=2;\n', next_language='Java')
        self.assertEqual(values['language_switch'], 1.)
        self.assertEqual(values['other_lexical_change'], 1.)
        for name in ('parse_recovery', 'parse_loss', 'token_equivalent_surface_change',
                     *encoder.FAMILY_EVENTS, 'ordered_ast_relation_change'):
            self.assertFalse(mask[name])
        history = [prior('x=1;', 1, language='Java')]
        features = encoder.encode_observation('x=2\n', 'WA', history, 2, 'H')
        self.assertEqual(features['history:non_python_fraction'], 1.)
        self.assertEqual(features['history:event_observed_fraction:binding_edit'], 0.)
        self.assertEqual(features['history:event_frequency:binding_edit'], 0.)
        self.assertEqual(features['history:event_observed_fraction:language_switch'], 1.)

    def test_encoding_cookie_is_respected_by_byte_parser_and_tokenizer(self):
        bad = '# coding: ascii\nx="é"\n'
        good = '# coding: utf-8\nx="é"\n'
        values, mask = self.event(bad, good)
        self.assertEqual(values['parse_recovery'], 1.)
        self.assertFalse(mask['token_equivalent_surface_change'])
        self.assertFalse(mask['binding_edit'])
        features = encoder.encode_observation(bad, 'CE', [], 1, 'C0')
        self.assertEqual(features['current:parse_fallback'], 1.)
        self.assertEqual(features['current:tokenization_unavailable'], 1.)
        values, mask = self.event('# coding: nonexistent_codec\nx=1\n', 'x=1\n')
        self.assertEqual(values['parse_recovery'], 1.)
        self.assertFalse(mask['binding_edit'])

    def test_current_only_independent_of_history_and_absolute_timestamps(self):
        first = encoder.encode_observation('x=1\n', 'Wrong Answer', [prior('x=0\n', 1)], 4, 'C0')
        second = encoder.encode_observation('x=1\n', 'WA', [prior('z=99\n', 100), prior('q=0\n', 200)], 300, 'C0')
        self.assertEqual(first, second)
        self.assertTrue(all(key.startswith('current:') for key in first))
        history = [prior('x=0\n', 1), prior('x=1\n', 2)]
        shifted = [dict(row, timestamp=row['timestamp']+1000000) for row in history]
        self.assertEqual(encoder.encode_observation('x=2\n', 'WA', history, 3, 'H'),
                         encoder.encode_observation('x=2\n', 'WA', shifted, 1000003, 'H'))

    def test_common_nuisance_is_authentic_for_h_and_hs(self):
        history = [prior('x=0\n', 1), prior('x=1\n', 10), prior('x=2\n', 20)]
        cn = encoder.encode_observation('x=3\n', 'WA', history, 50, 'Cn')
        self.assertEqual({key for key in cn if key.startswith(encoder.NUISANCE_PREFIX)}, set(encoder.NUISANCE_KEYS))
        for arm in ('H', 'HS'):
            rich = encoder.encode_observation('x=3\n', 'WA', history, 50, arm, 'shuffle-key')
            self.assertEqual({key:rich[key] for key in cn}, cn)
            self.assertTrue(all(key in cn or key.startswith('history:') for key in rich))
        donor = [prior('q=2\n', 25), prior('q=1\n', 30), prior('q=0\n', 40)]
        u = encoder.encode_observation('x=3\n', 'WA', donor, 50, 'H')
        self.assertNotEqual(u['nuisance:elapsed_seconds_log1p'], cn['nuisance:elapsed_seconds_log1p'])
        u.update(cn)
        self.assertEqual({key:u[key] for key in cn}, cn)

    def test_complete_long_history_first_transition_is_not_dropped(self):
        count = 1200
        history = [prior('x=0\n' if index == 0 else 'x=1\n', index+1) for index in range(count)]
        features = encoder.encode_observation('x=1\n', 'WA', history, count+1, 'H')
        self.assertAlmostEqual(math.expm1(features['nuisance:prior_count_log1p']), count)
        self.assertAlmostEqual(features['history:event_frequency:binding_edit'], 1/count)
        self.assertAlmostEqual(features['history:event_frequency:exact_repeat'], (count-1)/count)
        self.assertEqual(features['history:event_observed_fraction:exact_repeat'], 1.)

    def test_repetition_return_reverse_edit_and_nominal_transitions(self):
        history = [prior('x=0\n', 1, 'WA'), prior('x=1\n', 2, 'AC'),
                   prior('x=0\n', 3, 'WA'), prior('x=1\n', 4, 'WA')]
        features = encoder.encode_observation('x=1\n', 'WA', history, 5, 'H')
        self.assertEqual(features['history:current_seen_before'], 1.)
        self.assertEqual(features['history:current_source_prior_fraction'], .5)
        self.assertEqual(features['history:current_recurrence_distance_inverse'], 1.)
        self.assertAlmostEqual(features['history:current_source_trailing_repeat_log1p'], math.log(2))
        self.assertEqual(features['history:reverse_edit_fraction'], .5)
        self.assertEqual(features['history:repeated_transition_fraction'], .25)
        self.assertEqual(features['history:verdict_transition_fraction:WA=>AC'], .25)
        self.assertEqual(features['history:verdict_transition_fraction:AC=>WA'], .25)

    def test_hs_is_deterministic_and_preserves_records_timestamps_and_nuisance(self):
        history = [prior(f'x={index}\n', index+1, 'WA' if index % 2 else 'RE') for index in range(5)]
        before = copy.deepcopy(history)
        key = next(str(index) for index in range(100) if not encoder.describe_permutation(history, str(index))['identity'])
        description = encoder.describe_permutation(history, key)
        self.assertEqual(sorted(description['indices']), list(range(5)))
        h = encoder.encode_observation('x=8\n', 'WA', history, 10, 'H')
        hs = encoder.encode_observation('x=8\n', 'WA', history, 10, 'HS', key)
        self.assertEqual(hs, encoder.encode_observation('x=8\n', 'WA', history, 10, 'HS', key))
        self.assertNotEqual(h, hs)
        self.assertEqual(history, before)
        self.assertEqual({key:hs[key] for key in encoder.NUISANCE_KEYS}, {key:h[key] for key in encoder.NUISANCE_KEYS})
        self.assertTrue(encoder.describe_permutation(history[:1], 'any')['identity'])

    def test_target_mutation_and_cached_results_cannot_change_observation_features(self):
        history = [prior('x=0\n', 1), prior('x=1\n', 2)]
        first = encoder.encode_observation('x=2\n', 'WA', history, 3, 'H')
        for future in ('x=3\n', 'import os\n', 'if (:\n', 'x="é"\n'):
            values, mask = encoder.encode_edit('x=2\n', future)
            values[:] = 999
            mask[:] = False
        self.assertEqual(first, encoder.encode_observation('x=2\n', 'WA', history, 3, 'H'))
        poisoned = copy.deepcopy(history)
        poisoned[0]['next_code'] = 'future leak'
        with self.assertRaisesRegex(ValueError, 'observed-only'):
            encoder.encode_observation('x=2\n', 'WA', poisoned, 3, 'H')

    def test_identity_and_shuffle_key_not_feature_keys_and_no_io(self):
        history = [prior('x=0\n', 1), prior('x=1\n', 2)]
        with patch('builtins.open', side_effect=AssertionError('encoder file access')):
            result = encoder.encode_observation('x=2\n', 'WA', history, 3, 'HS', 'SECRET_USER_ID')
            encoder.encode_edit('x=0\n', 'x=1\n')
        self.assertTrue(all('SECRET_USER_ID' not in key and 'timestamp' not in key and 'sha256' not in key for key in result))
        self.assertTrue(all(type(value) is float and math.isfinite(value) for value in result.values()))

    def test_strict_temporal_schema_and_missing_source_inputs(self):
        for history in ([prior('x=0\n', 3)], [prior('x=0\n', 1), prior('x=1\n', 1)],
                        [dict(prior('x=0\n', 1), timestamp=float('nan'))]):
            with self.assertRaises(ValueError):
                encoder.encode_observation('x=2\n', 'WA', history, 3, 'HS', 'key')
        with self.assertRaises(TypeError):
            encoder.encode_edit(None, 'x=1\n')
        with self.assertRaises(ValueError):
            encoder.encode_observation('x=0\n', 'WA', [], True, 'H')
        with self.assertRaises(ValueError):
            encoder.encode_observation('x=0\n', 'WA', [], 1, 'U')

    def test_empty_history_and_empty_real_source_are_finite(self):
        for arm in encoder.ARMS:
            result = encoder.encode_observation('', 'CE', [], 1, arm)
            self.assertTrue(all(math.isfinite(value) for value in result.values()))
        values, mask = self.event('', '')
        self.assertEqual(values['exact_repeat'], 1.)
        self.assertTrue(mask['binding_edit'])


if __name__ == '__main__':
    unittest.main()
