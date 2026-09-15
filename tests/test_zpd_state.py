import copy
import unittest

from src.repair.zpd_state import build_observed_prefix_state


def row(i, code="x", verdict="WA", outcomes=None):
    result = {"submission_id": str(i), "timestamp": i, "code": code, "verdict": verdict}
    if outcomes is not None:
        result["testcase_evidence"] = {"universe_id": "tests-sha", "protocol_id": "run-sha",
                                       "complete": True, "outcomes": outcomes}
    return result


class ObservedPrefixStateTests(unittest.TestCase):
    def test_nominal_re_tle_transition_has_no_order(self):
        state = build_observed_prefix_state([row(1, verdict="RE", outcomes={"a": "RE"}),
                                             row(2, verdict="TLE", outcomes={"a": "TLE"})])
        t = state["current_vs_history"]["last_transition"]
        self.assertEqual(t["new_passes"], [])
        self.assertEqual(t["lost_passes"], [])
        self.assertEqual(t["verdict_transition"], ("RE", "TLE"))
        self.assertEqual(t["repeated_failed_cases"], ["a"])
        self.assertTrue(t["unchanged_code_execution_disagreement"])

    def test_gains_losses_and_test_id_repetition_are_separate(self):
        state = build_observed_prefix_state([
            row(1, outcomes={"a": "WA", "b": "AC", "c": "RE"}),
            row(2, "y", outcomes={"a": "Accepted", "b": "WA", "c": "RE"})])
        t = state["current_vs_history"]["last_transition"]
        self.assertEqual(t["new_passes"], ["a"])
        self.assertEqual(t["lost_passes"], ["b"])
        self.assertEqual(t["repeated_failed_cases"], ["c"])

    def test_prior_only_and_current_boundary_are_separate(self):
        state = build_observed_prefix_state([row(1), row(2), row(3, "y", "AC")])
        self.assertEqual(state["history"]["verdict_counts"], {"WA": 2})
        self.assertEqual(state["history"]["adjacent_exact_code_repeats"], 1)
        self.assertEqual(state["history"]["adjacent_same_failed_verdict"], 1)
        self.assertEqual(len(state["history"]["transitions"]), 1)
        self.assertEqual(state["current"]["verdict"], "AC")

    def test_no_strip_or_normalized_dedup(self):
        state = build_observed_prefix_state([row(1, " x"), row(2, "x"), row(3, "x")])
        self.assertEqual(state["history"]["observed_prior_submissions"], 2)
        self.assertEqual(state["history"]["adjacent_exact_code_repeats"], 0)
        self.assertEqual(state["current_vs_history"]["prior_exact_code_matches"], 1)

    def test_unknown_evidence_never_becomes_zero(self):
        for kind in ("missing", "partial", "unknown", "empty"):
            with self.subTest(kind=kind):
                b = row(2, outcomes={"a": "WA"})
                if kind == "missing":
                    del b["testcase_evidence"]
                elif kind == "partial":
                    b["testcase_evidence"]["complete"] = False
                elif kind == "unknown":
                    b["testcase_evidence"]["outcomes"]["a"] = "timeout infrastructure error"
                else:
                    b["testcase_evidence"]["outcomes"] = {}
                a = row(1) if kind == "empty" else row(1, outcomes={"a": "WA"})
                state = build_observed_prefix_state([a, b])
                self.assertEqual(state["current"]["execution"]["status"], "unknown")
                self.assertIsNone(state["current_vs_history"]["last_transition"]["new_passes"])

    def test_inconsistent_universe_protocol_or_cases_fail(self):
        for field, value in (("universe_id", "other"), ("protocol_id", "other"),
                             ("outcomes", {"b": "WA"})):
            a, b = row(1, outcomes={"a": "WA"}), row(2, outcomes={"a": "AC"})
            b["testcase_evidence"][field] = value
            with self.assertRaises(ValueError):
                build_observed_prefix_state([a, b])

    def test_partial_outside_known_universe_fails(self):
        a, b = row(1, outcomes={"a": "WA"}), row(2, outcomes={"b": "WA"})
        b["testcase_evidence"]["complete"] = False
        with self.assertRaises(ValueError):
            build_observed_prefix_state([a, b])

    def test_future_fields_rejected(self):
        for key in ("target", "target_code", "final_ac", "label", "trajectory_length"):
            a = row(1)
            a[key] = 4
            with self.assertRaises(ValueError):
                build_observed_prefix_state([a])

    def test_timestamp_validation_and_ties(self):
        for value in (None, float("nan"), float("inf"), True, "2", 0):
            a, b = row(1), row(2)
            b["timestamp"] = value
            with self.assertRaises(ValueError):
                build_observed_prefix_state([a, b])
        a, b = row(1), row(2)
        b["timestamp"] = 1
        self.assertEqual(build_observed_prefix_state([a, b])["audit"]["timestamp_ties"], 1)

    def test_empty_and_duplicate_submission_fail(self):
        for prefix in ([], [row(1), row(1)]):
            with self.assertRaises(ValueError):
                build_observed_prefix_state(prefix)

    def test_single_current_and_no_mutation(self):
        prefix = [row(1, outcomes={"a": "Accepted"})]
        original = copy.deepcopy(prefix)
        state = build_observed_prefix_state(prefix)
        self.assertEqual(prefix, original)
        self.assertEqual(state["history"]["observed_prior_submissions"], 0)
        self.assertIsNone(state["current_vs_history"]["last_transition"])
        state["current"]["execution"]["outcomes"]["a"] = "WA"
        self.assertEqual(prefix, original)


if __name__ == "__main__":
    unittest.main()
