"""Independent evidence-contract checks; synthetic fixtures are not experiment data."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_zpd_evidence import relation_axes, run, verify_cache_record


def cache_record(submission="s1", outcomes=None, verdict="WA"):
    outcomes = {"a": "WA", "b": "AC"} if outcomes is None else outcomes
    passed = [key for key, value in outcomes.items() if value == "AC"]
    return {"problem_id": "p00001", "submission_id": submission,
            "execution_verdict": verdict, "tc_outcomes": outcomes,
            "testcase_count": len(outcomes), "passed_testcases": passed,
            "pass_rate": len(passed) / len(outcomes) if outcomes else 0.}


class CacheContractTests(unittest.TestCase):
    def test_valid_observed_vector(self):
        self.assertEqual(verify_cache_record(cache_record(), ["a", "b"]), [])

    def test_matching_partial_vectors_are_not_full_universe(self):
        row = cache_record(outcomes={"a": "WA"})
        self.assertIn("testcase_universe_mismatch", verify_cache_record(row, ["a", "b"]))

    def test_absent_universe_is_not_certified(self):
        self.assertIn("testcase_universe_mismatch", verify_cache_record(cache_record(), []))

    def test_wrong_case_count_rejected(self):
        row = cache_record()
        row["testcase_count"] = 3
        self.assertIn("testcase_count_mismatch", verify_cache_record(row, ["a", "b"]))

    def test_boolean_case_count_rejected(self):
        row = cache_record(outcomes={"a": "WA"})
        row["testcase_count"] = True
        self.assertTrue(verify_cache_record(row, ["a"]))

    def test_unknown_or_absent_aggregate_rejected(self):
        for value in ("UNKNOWN", None):
            row = cache_record()
            if value is None:
                del row["execution_verdict"]
            else:
                row["execution_verdict"] = value
            with self.subTest(value=value):
                self.assertTrue(verify_cache_record(row, ["a", "b"]))

    def test_aggregate_acceptance_matches_case_acceptance(self):
        for outcomes, verdict in (({"a": "WA"}, "AC"), ({"a": "AC"}, "WA")):
            with self.subTest(outcomes=outcomes, verdict=verdict):
                self.assertTrue(verify_cache_record(cache_record(outcomes=outcomes, verdict=verdict), ["a"]))

    def test_bad_rates_and_passed_key_lists_rejected(self):
        for value in (True, float("nan"), float("inf"), -.5, 1.5, .6):
            row = cache_record()
            row["pass_rate"] = value
            with self.subTest(value=value):
                self.assertIn("pass_rate_mismatch", verify_cache_record(row, ["a", "b"]))
        row = cache_record()
        row["passed_testcases"] = ["a"]
        self.assertIn("passed_keys_mismatch", verify_cache_record(row, ["a", "b"]))

    def test_cache_error_is_never_a_negative_execution(self):
        row = cache_record()
        row["cache_error"] = "runner failed"
        self.assertEqual(verify_cache_record(row, ["a", "b"]), ["cache_error"])

    def test_counterfactual_is_separate_and_non_mutating(self):
        before = cache_record(outcomes={"a": "RE", "b": "TLE"}, verdict="TLE")
        after = cache_record("s2", {"a": "RE", "b": "WA"}, "RE")
        original = copy.deepcopy((before, after))
        axes = relation_axes(before, after)
        self.assertFalse(axes["legacy_replay_relation"])
        self.assertTrue(axes["coherent_severity_relation"])
        self.assertTrue(axes["current_aggregate_rank_conflict"])
        self.assertEqual((before, after), original)

    def test_gain_and_loss_can_coexist(self):
        before = cache_record(outcomes={"a": "AC", "b": "WA"})
        after = cache_record("s2", {"a": "WA", "b": "AC"})
        axes = relation_axes(before, after)
        self.assertEqual((axes["gained_passes"], axes["lost_passes"]), (1, 1))
        self.assertFalse(axes["pass_set_growth_without_losses"])


class AuditIntegrationTests(unittest.TestCase):
    def make_inputs(self, root):
        def write_rows(path, rows):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))
        write_rows(root / "testcases/p00001/testcases.jsonl", [{"case_id": "a"}, {"case_id": "b"}])
        write_rows(root / "all-original-submissions.jsonl", [cache_record(), cache_record("s2", {"a": "AC", "b": "AC"}, "AC")])
        (root / "all-original-submissions.summary.json").write_text(json.dumps({"outcome_cache_complete": True}))
        row = {"example_id": "x", "problem_id": "p00001", "user_id": "u1",
               "history": [{"submission_id": "s1", "code": "bad", "verdict": "WA"}],
               "target_submission_id": "s2", "target_code": "fixed", "target_verdict": "AC"}
        for split in ("train", "valid"):
            for policy in ("progress", "strict", "answer"):
                write_rows(root / "canonical-datasets" / f"{split}-{policy}.jsonl", [row])

    def test_linked_audit_hashes_all_inputs_without_rewriting_them(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "input"
            self.make_inputs(root)
            before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}
            result = run(root, Path(directory) / "audit.json")
            self.assertEqual(result["cache_invalid_rows"], 0)
            self.assertEqual(len(result["datasets"]), 6)
            for item in result["datasets"].values():
                self.assertEqual(item["integrity"]["verified_observed_pair"], 1)
                self.assertEqual(item["cache_linked"]["counts"]["target_all_tests_pass"], 1)
            for path, digest in before.items():
                self.assertEqual(result["input_sha256"][path], digest)
                self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), digest)

    def test_duplicate_cache_identity_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "input"
            self.make_inputs(root)
            cache = root / "all-original-submissions.jsonl"
            with cache.open("a") as stream:
                stream.write(json.dumps(cache_record()) + "\n")
            with self.assertRaisesRegex(ValueError, "duplicate cache key"):
                run(root, Path(directory) / "audit.json")

    def test_programmatic_run_cannot_overwrite_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "input"
            self.make_inputs(root)
            cache = root / "all-original-submissions.jsonl"
            before = cache.read_bytes()
            with self.assertRaises(ValueError):
                run(root, cache)
            self.assertEqual(cache.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
