"""Synthetic exact-overlap tests; no empirical bodies, execution or fitting."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
import hashlib
import math
from pathlib import Path
import random
from types import MappingProxyType
import unittest

from scripts import zpd_edit_kind_history as kinds
from scripts import zpd_repair_directed_history as directed


def delta(additions=None, removals=None):
    additions, removals = additions or {}, removals or {}
    return directed.Delta(True, MappingProxyType(additions), MappingProxyType(removals),
                          sum(additions.values()) + sum(removals.values()))


def covariance(values, feedback, weights):
    """Independent rational algebra, not a proposed production moment encoder."""
    return (sum(w * s * q for w, s, q in zip(weights, values, feedback, strict=True))
            - sum(w * s for w, s in zip(weights, values, strict=True))
            * sum(w * q for w, q in zip(weights, feedback, strict=True)))


class EditKindHistoryTests(unittest.TestCase):
    def test_frozen_source_pin(self):
        path = Path(directed.__file__)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), kinds.DIRECTED_SOURCE_SHA256)

    def test_operator_literal_loss_witness(self):
        history = directed.delta('x = a + 1\n', 'x = a - 2\n')
        operator = directed.delta('x = a - 2\n', 'x = a + 2\n')
        literal = directed.delta('x = a - 2\n', 'x = a - 1\n')
        a, b = (kinds.match_kinds(value, history) for value in (operator, literal))
        self.assertEqual(directed.match(operator, history), directed.match(literal, history))
        self.assertEqual(a.denominator, 6)
        self.assertEqual(a.reverse_overlap, (2, 0, 0, 0))
        self.assertEqual(b.reverse_overlap, (0, 2, 0, 0))
        self.assertEqual(a.exact_reverse, (Fraction(2, 3), 0, 0, 0))
        self.assertEqual(sum(a.exact_reverse), sum(b.exact_reverse))
        self.assertEqual(a.exact_same, (0, 0, 0, 0))

    def test_exact_key_not_kind_is_the_intersection_identity(self):
        first = directed.delta('a=1\nb=1', 'a=2\nb=1')
        other_locus = directed.delta('a=1\nb=1', 'a=1\nb=2')
        other_literal = directed.delta('a=3\nb=1', 'a=4\nb=1')
        for history in (other_locus, other_literal):
            got = kinds.match_kinds(first, history)
            self.assertEqual(got.exact_same + got.exact_reverse, (0,) * 8)
        typed = directed.delta('x=True', 'x=False')
        numeric = directed.delta('x=1', 'x=0')
        self.assertEqual(kinds.match_kinds(typed, numeric).same_overlap, (0,) * 4)

    def test_all_operator_families_identifier_and_other(self):
        source = 'def f(arg):\n return -arg + 1 if (arg and arg < 3) else 0\n'
        signature = directed.signature(source)
        classes = {key[1]: kinds.key_kind(key) for key in signature.counts}
        for name in ('USub', 'Add', 'And', 'Lt'):
            self.assertEqual(classes[name], 'operator')
        self.assertEqual(classes['Constant'], 'literal')
        for name in ('Name', 'arg'):
            self.assertEqual(classes[name], 'identifier')
        for name in ('FunctionDef', 'Return', 'IfExp', 'Load'):
            self.assertEqual(classes[name], 'other')

    def test_available_zero_unavailable_and_immutable_result(self):
        edit = directed.delta('x=1', 'x=2')
        noop = directed.delta('x=1', 'x = 1 # comment')
        unavailable = directed.delta('x=1', 'broken(', 'Python', 'Python')
        one = kinds.match_kinds(edit, noop)
        self.assertTrue(one.available)
        self.assertEqual(one.denominator, edit.mass)
        self.assertEqual(one.same + one.reverse, (0.0,) * 8)
        self.assertEqual(kinds.match_kinds(noop, noop).denominator, 0)
        missing = kinds.match_kinds(edit, unavailable)
        self.assertFalse(missing.available)
        self.assertEqual(missing.denominator, 0)
        with self.assertRaises(FrozenInstanceError):
            missing.available = True

    def test_exact_conservation_reversal_exclusivity_and_bound(self):
        key_pool = list(directed.signature('def f(x):\n return x + 2 if x < 3 else -x\n').counts)
        rng = random.Random(2027)
        for _ in range(200):
            values = []
            for _ in range(2):
                add, remove = {}, {}
                for key in key_pool:
                    sign = rng.randrange(3)
                    if sign: (add if sign == 1 else remove)[key] = rng.randint(1, 7)
                values.append(delta(add, remove))
            candidate, history = values
            got = kinds.match_kinds(candidate, history)
            denominator = candidate.mass + history.mass
            same = sum(min(n, history.additions.get(k, 0)) for k, n in candidate.additions.items())
            same += sum(min(n, history.removals.get(k, 0)) for k, n in candidate.removals.items())
            reverse = sum(min(n, history.removals.get(k, 0)) for k, n in candidate.additions.items())
            reverse += sum(min(n, history.additions.get(k, 0)) for k, n in candidate.removals.items())
            self.assertEqual(sum(got.exact_same), Fraction(2 * same, denominator))
            self.assertEqual(sum(got.exact_reverse), Fraction(2 * reverse, denominator))
            self.assertLessEqual(sum(got.exact_same + got.exact_reverse), 1)
            pooled = directed.match(candidate, history)
            self.assertLessEqual(abs(math.fsum(got.same) - pooled.same), 4 * math.ulp(1.0))
            self.assertLessEqual(abs(math.fsum(got.reverse) - pooled.reverse), 4 * math.ulp(1.0))
            backwards = kinds.match_kinds(candidate, delta(dict(history.removals), dict(history.additions)))
            self.assertEqual(got.same_overlap, backwards.reverse_overlap)
            self.assertEqual(got.reverse_overlap, backwards.same_overlap)
        self.assertEqual(kinds.match_kinds(values[0], values[0]).reverse_overlap, (0,) * 4)

    def test_malformed_signed_deltas_rejected_not_repaired(self):
        key = next(iter(directed.signature('x=1').counts))
        bad = [directed.Delta(True, {key: 1}, {key: 1}, 2),
               directed.Delta(True, {key: True}, {}, 1),
               directed.Delta(True, {key: -1}, {}, 0),
               directed.Delta(True, {key: 1}, {}, 2),
               directed.Delta(False, {key: 1}, {}, 1),
               directed.Delta(1, {}, {}, 0),
               directed.Delta(True, {('bad', 'Constant', ()): 1}, {}, 1)]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                kinds.match_kinds(value, delta())
        with self.assertRaises(TypeError):
            kinds.match_kinds({}, delta())

    def test_constant_feedback_and_singleton_covariance_invariants(self):
        candidate = directed.delta('x=a-2', 'x=a+1')
        history = [directed.delta('x=a+1', 'x=a-1'), directed.delta('x=a-1', 'x=a-2')]
        matches = [kinds.match_kinds(candidate, value) for value in history]
        for direction in ('exact_same', 'exact_reverse'):
            for group in range(4):
                values = [getattr(value, direction)[group] for value in matches]
                for weight in ((Fraction(1, 2), Fraction(1, 2)), (Fraction(1, 3), Fraction(2, 3))):
                    for q in (Fraction(0), Fraction(1, 3), Fraction(1)):
                        self.assertEqual(covariance(values, [q, q], weight), 0)
                        self.assertEqual(covariance(values[:1], [q], [Fraction(1)]), 0)

    def test_kind_covariance_can_survive_constant_pooled_similarity(self):
        # Coherent source chain, reverting both accumulated changes from current.
        candidate = directed.delta('x=a-2', 'x=a+1')
        matches = [kinds.match_kinds(candidate, directed.delta(a, b)) for a, b in
                   [('x=a+1', 'x=a-1'), ('x=a-1', 'x=a-2')]]
        weights = [Fraction(1, 3), Fraction(2, 3)]
        feedback = [Fraction(0), Fraction(1)]  # probability of paired state01
        pooled = [sum(value.exact_reverse) for value in matches]
        self.assertEqual(pooled, [Fraction(2, 3)] * 2)
        self.assertEqual(covariance(pooled, feedback, weights), 0)
        self.assertEqual(covariance([v.exact_reverse[0] for v in matches], feedback, weights), -Fraction(4, 27))
        self.assertEqual(covariance([v.exact_reverse[1] for v in matches], feedback, weights), Fraction(4, 27))


if __name__ == '__main__':
    unittest.main()
