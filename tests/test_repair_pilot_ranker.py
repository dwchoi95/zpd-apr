"""Synthetic contract/mechanism checks; not empirical repair evidence."""
import hashlib
import unittest

from src.repair.pilot_contracts import (
    CandidateAttempt, CandidateBank, ObservationSource, PilotObservation,
)
from src.repair.pilot_ranker import TwoChannelCoefficients, features, select


def source(code, timestamp, submission_id=None):
    return ObservationSource(submission_id=submission_id or f"observation-{timestamp}", timestamp=timestamp, source=code,
                             source_sha256=hashlib.sha256(code).hexdigest(), verdict="Wrong Answer")


def bank(current=b"x = 0", candidates=(b"x = 1", b"x = 2")):
    attempts = tuple(CandidateAttempt(index=i, seed=i, status="success", source=candidates[i % len(candidates)], error=None)
                     for i in range(8))
    return CandidateBank(problem_id="p", current_source=current,
                         generator_config_sha256="a" * 64, seeds=tuple(range(8)), attempts=attempts)


class RepairPilotRankerTests(unittest.TestCase):
    def setUp(self):
        self.current = source(b"x = 0", 100, "now")
        self.observation = PilotObservation(problem_id="p", current=self.current, prior=())
        self.bank = bank()

    def choose(self, history, gain, risk=None, **thresholds):
        return select(self.observation, self.bank, history=history,
                      coefficients=TwoChannelCoefficients(risk={"bias": -10} if risk is None else risk, gain=gain),
                      risk_threshold=thresholds.get("risk_threshold", .5),
                      minimum_gain=thresholds.get("minimum_gain", 0.0))

    def test_history_swaps_change_relative_ranks_same_current_and_bank(self):
        a = self.choose((source(b"x = 1", 1),), {"history_reverse_edit_overlap": 1})
        b = self.choose((source(b"x = 2", 1),), {"history_reverse_edit_overlap": 1})
        self.assertEqual(a.selected_source_sha256, hashlib.sha256(b"x = 1").hexdigest())
        self.assertEqual(b.selected_source_sha256, hashlib.sha256(b"x = 2").hexdigest())
        self.assertNotEqual(a.selected_source_sha256, b.selected_source_sha256)

    def test_history_only_constant_cannot_change_relative_rank(self):
        a = self.choose((source(b"x = 1", 1),), {"bias": 1, "history_count": 1})
        b = self.choose((source(b"x = 2", 1), source(b"x = 3", 2)), {"bias": 1, "history_count": 1})
        self.assertEqual(a.selected_source_sha256, b.selected_source_sha256)
        for result in (a, b):
            scores = [s.predicted_gain for s in result.scores if not s.is_noop]
            self.assertEqual(scores[0] - scores[1], 0)

    def test_noop_fallback_and_no_false_observed_risk_field(self):
        result = self.choose((), {"bias": 1}, risk={"bias": 10})
        self.assertTrue(result.abstained)
        self.assertEqual(result.selected_source_sha256, self.current.source_sha256)
        self.assertFalse(hasattr(result.scores[0], "actual_non_regression"))
        self.assertTrue(self.choose((), {"bias": 0}).abstained)

    def test_ties_are_source_hash_deterministic_not_bank_order(self):
        result = self.choose((), {"bias": 1})
        reverse_bank = bank(candidates=(b"x = 2", b"x = 1"))
        reversed_result = select(self.observation, reverse_bank, history=(),
                                 coefficients=TwoChannelCoefficients({"bias": -10}, {"bias": 1}),
                                 risk_threshold=.5, minimum_gain=0)
        expected = min(hashlib.sha256(code).hexdigest() for code in (b"x = 1", b"x = 2"))
        self.assertEqual(result.selected_source_sha256, expected)
        self.assertEqual(reversed_result.selected_source_sha256, expected)

    def test_all_history_is_used_and_recency_depends_on_order(self):
        # Oldest transition contributes even with more than 100 prior sources.
        long = tuple(source(b"x = 1" if i == 0 else b"x = 0", i) for i in range(99))
        values = features(self.observation, b"x = 1", history=long)
        self.assertEqual(values["history_count"], 99)
        self.assertGreater(values["history_candidate_reversion_weight"], 0)
        h1 = (source(b"x = 1", 1), source(b"x = 2", 2))
        h2 = (source(b"x = 2", 1), source(b"x = 1", 2))
        self.assertNotEqual(features(self.observation, b"x = 1", history=h1),
                            features(self.observation, b"x = 1", history=h2))

    def test_exact_bytes_not_normalized_for_repetition(self):
        values = features(self.observation, b"x = 1", history=(source(b"x=1", 1),))
        self.assertEqual(values["history_candidate_exact_fraction"], 0)

    def test_ids_not_features_and_future_labels_rejected(self):
        a = features(self.observation, b"x = 1", history=(source(b"x = 1", 1, "a"),))
        b = features(self.observation, b"x = 1", history=(source(b"x = 1", 1, "b"),))
        self.assertEqual(a, b)
        with self.assertRaises(TypeError):
            features(self.observation, b"x = 1", history=({"source": b"x = 1", "next_verdict": "Accepted"},))
        with self.assertRaises(ValueError):
            features(self.observation, b"x = 1", history=(source(b"x = 1", 100),))
        with self.assertRaises(ValueError):
            features(self.observation, b"x = 1", history=(source(b"x = 1", 1, "dup"), source(b"x = 2", 2, "dup")))

    def test_wrong_current_and_unknown_weights_rejected(self):
        with self.assertRaises(ValueError):
            select(self.observation, bank(current=b"x=0"), history=(),
                   coefficients=TwoChannelCoefficients({"bias": 0}, {"bias": 1}),
                   risk_threshold=.5, minimum_gain=0)
        with self.assertRaises(ValueError):
            self.choose((), {"next_verdict": 1})
        with self.assertRaises(ValueError):
            TwoChannelCoefficients({}, {"bias": 1})


if __name__ == "__main__":
    unittest.main()
