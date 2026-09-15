"""Adversarial semantics checks for the exploratory ZPD objective audit.

Matched observed vectors are not a certificate of full testcase execution.
These tests deliberately do not turn their completeness into an assumption.
"""
import unittest

from scripts.diagnose_zpd_objective import checked_outcomes, delta_class
from src.repair.evidence_order import ExecutionEvidence, progress_improvement
from src.runner.models import CaseOutcome, Verdict
from src.runner.python_runner import _overall_verdict


class DiagnosticAdversarialTests(unittest.TestCase):
    def test_legacy_aggregate_priority_can_reverse_casewise_improvement(self):
        # Reproduce legacy semantics, not a recommended new aggregation rule.
        before_cases = [CaseOutcome("a", Verdict.RE), CaseOutcome("b", Verdict.TLE)]
        after_cases = [CaseOutcome("a", Verdict.RE), CaseOutcome("b", Verdict.WA)]
        before = ExecutionEvidence(_overall_verdict(before_cases).value,
                                   {c.case_id: c.verdict.value for c in before_cases})
        after = ExecutionEvidence(_overall_verdict(after_cases).value,
                                  {c.case_id: c.verdict.value for c in after_cases})
        self.assertEqual((before.verdict, after.verdict), ("TLE", "RE"))
        self.assertFalse(progress_improvement(before, after))
        self.assertTrue(progress_improvement(after, before))

    def test_coarse_improvement_can_lose_a_previously_passed_case(self):
        before = ExecutionEvidence("TLE", {"a": "AC", "b": "TLE"})
        after = ExecutionEvidence("WA", {"a": "WA", "b": "WA"})
        self.assertTrue(progress_improvement(before, after))
        self.assertEqual(delta_class(.5, 0.), "decrease")

    def test_zero_pass_tie_can_be_valid_progress(self):
        before = ExecutionEvidence("CE", {"a": "CE", "b": "CE"})
        after = ExecutionEvidence("RE", {"a": "RE", "b": "RE"})
        self.assertTrue(progress_improvement(before, after))
        self.assertEqual(delta_class(0., 0.), "tie")

    def test_same_coarse_verdict_requires_casewise_non_regression(self):
        before = ExecutionEvidence("TLE", {"a": "AC", "b": "TLE"})
        after = ExecutionEvidence("TLE", {"a": "TLE", "b": "AC"})
        self.assertFalse(progress_improvement(before, after))

    def test_aggregate_pass_gain_is_not_casewise_progress(self):
        before = ExecutionEvidence("TLE", {"a": "AC", "b": "TLE", "c": "TLE"})
        after = ExecutionEvidence("TLE", {"a": "TLE", "b": "AC", "c": "AC"})
        self.assertFalse(progress_improvement(before, after))
        self.assertEqual(delta_class(1 / 3, 2 / 3), "increase")

    def test_same_rates_do_not_make_different_test_universes_comparable(self):
        row = {"before": {"a": "WA"}, "after": {"b": "WA"},
               "before_rate": 0., "after_rate": 0.}
        self.assertIsNone(checked_outcomes(row, "before", "after", "before_rate", "after_rate"))

    def test_empty_observed_vectors_remain_unknown(self):
        row = {"before": {}, "after": {}, "before_rate": 0., "after_rate": 0.}
        self.assertIsNone(checked_outcomes(row, "before", "after", "before_rate", "after_rate"))

    def test_unknown_case_outcome_is_not_a_negative_verdict(self):
        row = {"before": {"a": "CACHE_ERROR"}, "after": {"a": "WA"},
               "before_rate": 0., "after_rate": 0.}
        with self.assertRaisesRegex(ValueError, "unknown testcase verdict"):
            checked_outcomes(row, "before", "after", "before_rate", "after_rate")


if __name__ == "__main__":
    unittest.main()
