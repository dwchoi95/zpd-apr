import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.zpd_repair_evaluate import evaluate, parse_bank, run_source, SandboxRunner
from src.runner.models import CaseOutcome, TestCase, Verdict


def bank(identifier="b", current="old"):
    return {"bank_id": identifier, "problem_id": "p", "current_source": current,
        "generator_config_sha256": "a" * 64, "seeds": list(range(8)),
        "attempts": [{"index": i, "seed": i, "status": "success" if i < 6 else "generation_failure",
            "source": "new" if i < 6 else None, "error": None if i < 6 else "length"} for i in range(8)]}


class FakeRunner:
    calls = []
    def run_case(self, code, case):
        self.calls.append((code, case.case_id))
        return CaseOutcome(case.case_id, Verdict.AC if code == "new" else Verdict.WA)


class EvaluatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "data/p").mkdir(parents=True)
        (self.root / "data/p/testcases.jsonl").write_text(json.dumps({"case_id": "c", "input": "", "expected_output": "x"}) + "\n")
        self.banks = self.root / "banks.jsonl"
        self.banks.write_text(json.dumps(bank()) + "\n")
        FakeRunner.calls = []

    def run_eval(self, factory=FakeRunner, **kwargs):
        return evaluate(self.banks, self.root / "data", self.root / "out", runner_factory=factory, **kwargs)

    def labels(self):
        return [json.loads(v) for v in (self.root / "out/labels.jsonl").read_text().splitlines()]

    def test_common_sources_execute_once_per_block_and_labels(self):
        self.banks.write_text(json.dumps(bank("a")) + "\n" + json.dumps(bank("b")) + "\n")
        self.assertTrue(self.run_eval())
        self.assertEqual(len(FakeRunner.calls), 8)
        labels = self.labels()
        self.assertEqual([v["gain"] for v in labels], [0, 1, 0, 1])
        self.assertEqual([v["all_ac"] for v in labels], [False, True, False, True])
        rows = [json.loads(v) for v in (self.root / "out/completions.jsonl").read_text().splitlines()]
        self.assertEqual([v["block"]["workers"] for v in rows], [1, 1, 8, 8, 8, 8, 1, 1])
        self.assertTrue((self.root / "out/COMPLETE.json").exists())
        with self.assertRaises(FileExistsError):
            self.run_eval()

    def test_resource_exception_is_unknown_not_zero(self):
        class Failed:
            def run_case(self, code, case):
                raise OSError("resource unavailable")
        self.assertTrue(self.run_eval(Failed))
        for label in self.labels():
            self.assertEqual(label["status"], "unknown")
            self.assertIsNone(label["gain"])
            self.assertIsNone(label["loss"])
            self.assertIsNone(label["all_ac"])

    def test_memoryerror_return_is_unknown(self):
        class MemoryFailure:
            def run_case(self, code, case):
                return CaseOutcome(case.case_id, Verdict.RE, stderr="Traceback (most recent call last)\nMemoryError")
        outcomes, _, complete = run_source(MemoryFailure(), b"x", [TestCase("c", "", "")], 1, lambda: 0)
        self.assertTrue(complete)
        self.assertEqual(outcomes, [("c", "UNKNOWN")])

    def test_unstable_source_unknown(self):
        counts = {}
        class Unstable:
            def run_case(self, code, case):
                counts[code] = counts.get(code, 0) + 1
                return CaseOutcome(case.case_id, Verdict.AC if counts[code] % 2 else Verdict.WA)
        self.run_eval(Unstable)
        self.assertTrue(all(v["status"] == "unknown" for v in self.labels()))

    def test_deadline_no_complete_and_unknown(self):
        ticks = iter([0, 10])
        self.assertFalse(self.run_eval(clock=lambda: next(ticks, 10), max_seconds=1))
        self.assertFalse((self.root / "out/COMPLETE.json").exists())
        self.assertTrue((self.root / "out/INCOMPLETE.json").exists())
        self.assertTrue(all(v["gain"] is None for v in self.labels()))

    def test_conflicting_bank_and_traversal_rejected(self):
        a, b = bank("a"), bank("b")
        b["attempts"][0]["source"] = "different"
        self.banks.write_text(json.dumps(a) + "\n" + json.dumps(b) + "\n")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            self.run_eval()
        a["problem_id"] = "../outside"
        with self.assertRaises(ValueError):
            parse_bank(a)

    def test_same_source_exact_whitespace_not_normalized(self):
        row = bank()
        row["attempts"][0]["source"] = "old"
        row["attempts"][1]["source"] = "old "
        self.assertEqual(len(parse_bank(row).candidates), 3)

    def test_sandbox_failure_does_not_fallback(self):
        with patch("scripts.zpd_repair_evaluate.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                SandboxRunner().run_case("x", TestCase("c", "", ""))
        with patch("scripts.zpd_repair_evaluate.sandbox_preflight", side_effect=RuntimeError("no isolation")):
            with self.assertRaises(RuntimeError):
                evaluate(self.banks, self.root / "data", self.root / "out")
        self.assertFalse((self.root / "out").exists())


if __name__ == "__main__":
    unittest.main()
