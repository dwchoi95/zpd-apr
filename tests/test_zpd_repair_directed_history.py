"""Pure synthetic directed-history tests; no data, source execution or fit."""
import ast
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_repair_directed_history as directed
from scripts import zpd_history_action_encoder as semantic


def record(code, verdict='WA', timestamp=1, language='Python'):
    return dict(code=code, verdict=verdict, timestamp=timestamp, language=language)


class DirectedHistoryTests(unittest.TestCase):
    def test_exact_typed_local_paths_identifiers_literals_and_no_subtree_dump(self):
        with patch.object(ast, 'dump', side_effect=AssertionError('no subtree serialization')):
            first = directed.signature('global x, y\nx = [1, 2]\n')
            second = directed.signature('global x, z\nx = [1, 2]\n')
        self.assertTrue(first.available)
        self.assertNotEqual(first.counts, second.counts)
        keys = list(first.counts)
        self.assertTrue(any(('index', 1) in key[0] for key in keys))
        self.assertTrue(any(key[1] == 'Global' and ('names', ('index', 1), ('str', 'y')) in key[2] for key in keys))
        self.assertNotEqual(directed.signature('x=True').counts, directed.signature('x=1').counts)
        self.assertNotEqual(directed.signature('x=1').counts, directed.signature('x=1.0').counts)
        self.assertNotEqual(directed.signature('x=0.0').counts, directed.signature('x=-0.0').counts)
        self.assertEqual(directed.signature('x=1 # ignored comment\n').counts,
                         directed.signature('x = 1\n\n').counts)
        with self.assertRaises(TypeError): first.counts['mutated'] = 1

    def test_signed_delta_common_cancellation_and_direction_reversal(self):
        forward = directed.delta('x=1', 'x=2')
        backward = directed.delta('x=2', 'x=1')
        self.assertEqual(forward.mass, 2)
        self.assertFalse(set(forward.additions) & set(forward.removals))
        self.assertEqual(forward.additions, backward.removals)
        self.assertEqual(directed.match(forward, forward), directed.Match(True, 1., 0.))
        self.assertEqual(directed.match(forward, backward), directed.Match(True, 0., 1.))
        zero = directed.delta('x=1', 'x = 1 # comment\n')
        self.assertEqual(zero.mass, 0)
        self.assertEqual(directed.match(forward, zero), directed.Match(True, 0., 0.))
        self.assertEqual(directed.match(zero, zero), directed.Match(True, 0., 0.))

    def test_exact_locus_and_direction_disambiguate_identical_eighteen_bits(self):
        current = 'x=1\ny=1\n'
        undo = 'x=2\ny=1\n'
        other_locus = 'x=1\ny=2\n'
        alternative = 'x=0\ny=1\n'
        encodings = [semantic.encode_edit(current, code, 'Python', 'Python') for code in (undo, other_locus, alternative)]
        for values, masks in encodings[1:]:
            np.testing.assert_array_equal(encodings[0][0], values)
            np.testing.assert_array_equal(encodings[0][1], masks)
        history = [record(undo, 'RE')]
        results = [directed.candidate_features(current, code, 'WA', history, 2) for code in (undo, other_locus, alternative)]
        np.testing.assert_array_equal(results[0].similarities, [[0., 1.]])
        np.testing.assert_array_equal(results[1].similarities, [[0., 0.]])
        np.testing.assert_array_equal(results[2].similarities, [[0., .5]])
        self.assertFalse(np.array_equal(results[0].vector, results[1].vector))
        self.assertFalse(np.array_equal(results[0].vector, results[2].vector))

    def test_list_position_is_exact_not_semantic_alignment(self):
        left = directed.delta('a=1\nb=1\n', 'a=2\nb=1\n')
        right = directed.delta('a=1\nb=1\n', 'a=1\nb=2\n')
        self.assertEqual(directed.match(left, right), directed.Match(True, 0., 0.))
        inserted = directed.delta('a=1\n', 'pass\na=1\n')
        self.assertGreater(inserted.mass, 1)  # shifted position is intentionally not aligned

    def test_typed_ancestor_context_prevents_if_while_test_locus_collision(self):
        if_source = directed.signature('if x == 1:\n pass\n')
        while_source = directed.signature('while x == 1:\n pass\n')
        if_literal = next(key for key in if_source.counts if key[1] == 'Constant')
        while_literal = next(key for key in while_source.counts if key[1] == 'Constant')
        self.assertEqual(if_literal[1:], while_literal[1:])
        self.assertNotEqual(if_literal[0], while_literal[0])
        self.assertIn(('field', 'If', 'test'), if_literal[0])
        self.assertIn(('field', 'While', 'test'), while_literal[0])
        if_edit = directed.delta('if x == 1:\n pass\n', 'if x == 2:\n pass\n')
        while_edit = directed.delta('while x == 1:\n pass\n', 'while x == 2:\n pass\n')
        self.assertEqual(directed.match(if_edit, while_edit), directed.Match(True, 0., 0.))

    def test_same_plus_reverse_and_analytic_feature_norm_bounds(self):
        programs = ['x=0\ny=0', 'x=1\ny=0', 'x=2\ny=1', 'x=0\ny=2', 'x=1\ny=1', 'x=0\ny=0\npass']
        deltas = [directed.delta(a, b) for a in programs for b in programs]
        for first in deltas:
            for second in deltas:
                match = directed.match(first, second)
                self.assertGreaterEqual(match.same, 0.)
                self.assertGreaterEqual(match.reverse, 0.)
                self.assertLessEqual(match.same+match.reverse, 1.)
        history = [record(code, directed.VERDICTS[i], i) for i, code in enumerate(programs)]
        vectors = []
        for mode in ('joint', 'marginal'):
            for candidate in programs:
                result = directed.candidate_features('x=7\ny=3', candidate, 'WA', history, 7, mode=mode)
                self.assertEqual(result.vector.shape, (144,))
                self.assertEqual(result.vector.dtype, np.float64)
                self.assertTrue(np.isfinite(result.vector).all())
                np.testing.assert_array_equal(result.vector, getattr(result, mode).reshape(-1)/2)
                self.assertLessEqual(np.linalg.norm(result.vector), 2**-.5+1e-15)
                self.assertTrue(np.all(result.joint.sum(axis=(1, 2)) <= 1.+1e-15))
                vectors.append(result.vector)
        for first in vectors:
            for second in vectors: self.assertLessEqual(np.linalg.norm(first-second), 1.+1e-15)

    def test_empty_one_transition_and_constant_feedback_joint_marginal_equal(self):
        empty = directed.candidate_features('x=1', 'x=2', 'WA', [], 3)
        self.assertEqual(empty.transition_count, 0)
        self.assertEqual(empty.applicable_count, 0)
        np.testing.assert_array_equal(empty.vector, np.zeros(144))
        np.testing.assert_array_equal(empty.opportunity, np.zeros(2))
        for history in ([record('x=0', 'CE')], [record('x=0', timestamp=1), record('x=2', timestamp=2)]):
            value = directed.candidate_features('x=1', 'x=2', 'WA', history, 3)
            np.testing.assert_array_equal(value.joint, value.marginal)

    def test_joint_differs_from_marginal_with_same_conditional_denominator(self):
        history = [record('x=0', 'CE', 1), record('x=1', 'RE', 2)]
        value = directed.candidate_features('x=2', 'x=1', 'WA', history, 3)
        self.assertGreater(np.max(np.abs(value.joint-value.marginal)), .01)
        np.testing.assert_allclose(value.joint.sum(axis=2), value.marginal.sum(axis=2), atol=1e-16)
        np.testing.assert_allclose(value.opportunity, [1., 1.], atol=1e-16)

    def test_nonpython_and_unparsable_are_unavailable_not_lexical_fallback(self):
        history = [record('class X {}', 'WA', 0, 'Java'), record('x=(', 'CE', 1), record('x=0', 'WA', 2)]
        value = directed.candidate_features('x=1', 'x=0', 'RE', history, 3)
        np.testing.assert_array_equal(value.applicable_mask, [False, False, True])
        self.assertEqual(value.applicable_count, 1)
        self.assertEqual(value.transition_count, 3)
        np.testing.assert_allclose(value.opportunity, [1/3, 6/11])
        np.testing.assert_array_equal(value.joint, value.marginal)
        for current, candidate in [('x=(', 'x=1'), ('x=1', 'x=(')]:
            bad = directed.candidate_features(current, candidate, 'CE', history, 3)
            self.assertFalse(bad.candidate_available)
            self.assertEqual(bad.applicable_count, 0)
            self.assertEqual(np.count_nonzero(bad.vector), 0)
        self.assertFalse(directed.signature('x=1', 'Java').available)

    def test_zero_mass_retained_in_denominator_and_candidate_noop_is_zero(self):
        history = [record('x=0', 'CE', 1), record('x=0', 'CE', 2)]
        result = directed.candidate_features('x=1', 'x=0', 'WA', history, 3)
        np.testing.assert_array_equal(result.applicable_mask, [True, True])
        np.testing.assert_array_equal(result.history_masses, [0, 2])
        np.testing.assert_array_equal(result.similarities, [[0, 0], [0, 1]])
        self.assertEqual(result.joint[0, 1, directed.PAIR_INDEX['CE=>WA']], .5)
        self.assertAlmostEqual(result.joint[1, 1, directed.PAIR_INDEX['CE=>WA']], 2/3)
        noop = directed.candidate_features('x=1', 'x = 1 # comment', 'WA', history, 3)
        self.assertTrue(noop.candidate_available)
        self.assertEqual(noop.candidate_mass, 0)
        self.assertEqual(noop.applicable_count, 2)
        np.testing.assert_array_equal(noop.vector, np.zeros(144))
        np.testing.assert_array_equal(noop.opportunity, [1, 1])

    def test_hs_fixed_prior_permutation_current_anchored_bookkeeping(self):
        history = [record('x='+str(i), directed.VERDICTS[i], i) for i in range(5)]
        original = copy.deepcopy(history)
        order = semantic.permutation_indices(5, 'directed-test')
        actual = directed.candidate_features('x=5', 'x=3', 'WA', history, 5, shuffled=True, shuffle_key='directed-test')
        expected_pairs = [directed.PAIR_INDEX[history[a]['verdict']+'=>'+history[b]['verdict']] for a, b in zip(order, order[1:])]
        expected_pairs.append(directed.PAIR_INDEX[history[order[-1]]['verdict']+'=>WA'])
        np.testing.assert_array_equal(actual.pair_indices, expected_pairs)
        self.assertEqual(actual.permutation_indices, order)
        self.assertEqual(history, original)
        # Uniform aggregation of already computed (similarity, feedback, mask)
        # tuples is invariant to their bookkeeping order. HS, by contrast,
        # rebuilds adjacent AST deltas and feedback pairs after permuting nodes.
        reversed_rows = np.arange(len(history)-1, -1, -1)
        joint, marginal, _ = directed._aggregate(actual.similarities[reversed_rows], actual.applicable_mask[reversed_rows], actual.pair_indices[reversed_rows])
        np.testing.assert_allclose(joint[0], actual.joint[0], atol=1e-16)
        np.testing.assert_allclose(marginal[0], actual.marginal[0], atol=1e-16)
        again = directed.candidate_features('x=5', 'x=3', 'WA', history, 5, shuffled=True, shuffle_key='directed-test')
        np.testing.assert_array_equal(actual.vector, again.vector)

    def test_all_history_including_earliest_and_last_only_is_explicit_caller_control(self):
        history = [record('x=0', timestamp=i) for i in range(1200)]
        original = directed.candidate_features('x=0', 'x=1', 'WA', history, 1200)
        history[0]['code'] = 'x=1'
        changed = directed.candidate_features('x=0', 'x=1', 'WA', history, 1200)
        self.assertEqual(changed.transition_count, 1200)
        self.assertGreater(np.max(np.abs(changed.vector-original.vector)), 0.)
        last = directed.candidate_features('x=0', 'x=1', 'WA', history[-1:], 1200)
        self.assertEqual(last.transition_count, 1)
        np.testing.assert_array_equal(last.vector, original.vector)

    def test_exact_utf8_bytes_encoding_cookies_and_iterative_local_walk(self):
        self.assertFalse(directed.signature('# coding: ascii\nx="é"\n').available)
        self.assertFalse(directed.signature('# coding: no_such_codec\nx=1\n').available)
        latin = '# coding: latin-1\nx="é"\n'
        self.assertEqual(directed.signature(latin).counts, directed.signature('x="Ã©"\n').counts)
        with self.assertRaises(ValueError): directed.signature('x="\ud800"')
        with patch.object(ast, 'dump', side_effect=AssertionError('no full-tree dump')):
            large = directed.signature('\n'.join('x'+str(i)+'='+str(i) for i in range(3000)))
        self.assertTrue(large.available)
        self.assertGreater(len(large.counts), 12000)

    def test_frozen_python310_ast_grammar_and_exact_byte_parser_contract(self):
        code = 'x="é"\n'
        with patch.object(ast, 'parse', wraps=ast.parse) as parse:
            self.assertTrue(directed.signature(code).available)
            parse.assert_called_once_with(code.encode('utf-8'), mode='exec', feature_version=(3, 10))
        self.assertFalse(directed.signature('try:\n pass\nexcept* Exception:\n pass\n').available)
        self.assertEqual(directed.configuration()['ast_feature_version'], [3, 10])

    def test_parsable_huge_integer_and_nonfinite_literal_values_stay_exact(self):
        # Hexadecimal literals are parsable beyond Python's decimal conversion
        # cap; no stringification failure may silently discard such a source.
        huge = 'x=0x'+'f'*5000
        self.assertTrue(directed.signature(huge).available)
        self.assertEqual(directed.delta(huge, huge).mass, 0)
        for code in ('x=1e999', 'x=1e999j', 'x=...', 'x=b"\\xff"'):
            self.assertTrue(directed.signature(code).available)
            self.assertEqual(directed.delta(code, code).mass, 0)

    def test_strict_chronology_schema_no_future_fields_or_silent_coercion(self):
        good = [record('x=0', timestamp=1), record('x=1', timestamp=2)]
        for mutation in ('future', 'extra', 'missing', 'reverse', 'booltime', 'badlanguage', 'nonecode'):
            history = copy.deepcopy(good)
            if mutation == 'future': history[-1]['timestamp'] = 4
            if mutation == 'extra': history[0]['next_code'] = 'x=8'
            if mutation == 'missing': history[0].pop('code')
            if mutation == 'reverse': history.reverse()
            if mutation == 'booltime': history[0]['timestamp'] = True
            if mutation == 'badlanguage': history[0]['language'] = ''
            if mutation == 'nonecode': history[0]['code'] = None
            with self.subTest(mutation=mutation), self.assertRaises((TypeError, ValueError)):
                directed.candidate_features('x=2', 'x=3', 'WA', history, 3, shuffled=True)
        with self.assertRaises(ValueError): directed.candidate_features('x=2', 'x=3', 'WA', tuple(good), 3)
        with self.assertRaises(TypeError): directed.candidate_features('x=2', 'x=3', 'WA', good, 3, next_code='future')
        with self.assertRaises(ValueError): directed.candidate_features('x=2', 'x=3', 'WA', good, 3, mode='fit')

    def test_pure_no_source_execution_io_or_mutable_output(self):
        # Parsing a malicious-looking program must not execute it.
        with patch.object(Path, 'open', side_effect=AssertionError('no source I/O')):
            result = directed.candidate_features('open("never", "w").write("x")', 'raise RuntimeError("never")', 'WA', [record('x=0')], 2)
        for value in (result.vector, result.joint, result.marginal, result.opportunity, result.applicable_mask, result.similarities, result.pair_indices, result.history_masses):
            self.assertFalse(value.flags.writeable)
        self.assertFalse(directed.configuration()['semantic_alignment_claim'])
        self.assertFalse(directed.configuration()['future_targets_used'])


if __name__ == '__main__':
    unittest.main()
