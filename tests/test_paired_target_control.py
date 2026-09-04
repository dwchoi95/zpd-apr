from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "paired_target", Path("scripts/build_paired_target_control.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)

sys.path.insert(0, str(Path("scripts").resolve()))
ANALYSIS_SPEC = importlib.util.spec_from_file_location(
    "paired_target_analysis", Path("scripts/analyze_paired_target_control.py")
)
ANALYSIS = importlib.util.module_from_spec(ANALYSIS_SPEC)
assert ANALYSIS_SPEC.loader is not None
ANALYSIS_SPEC.loader.exec_module(ANALYSIS)


def row(example: str, source: str, target: str, code: str = "x=1") -> dict:
    return {
        "example_id": example,
        "problem_id": "p",
        "user_id": "u",
        "history": [{"submission_id": source, "position": 4, "code": code}],
        "target_submission_id": target,
        "target_code": "x=2",
    }


class PairedTargetControlTest(unittest.TestCase):
    def test_exact_source_pairing_excludes_identical_targets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            progress = root / "progress.jsonl"
            answer = root / "answer.jsonl"
            progress.write_text(
                json.dumps(row("p1", "s1", "s2")) + "\n"
                + json.dumps(row("p2", "s3", "s4")) + "\n",
                encoding="utf-8",
            )
            answer.write_text(
                json.dumps(row("a1", "s1", "s9")) + "\n"
                + json.dumps(row("a2", "s3", "s4")) + "\n",
                encoding="utf-8",
            )
            po, ao = root / "po.jsonl", root / "ao.jsonl"
            result = MODULE.build(progress, answer, po, ao)
            self.assertEqual(result["paired_target_divergent_examples"], 1)
            self.assertEqual(result["identical_target_examples_excluded"], 1)
            p = json.loads(po.read_text())
            a = json.loads(ao.read_text())
            self.assertEqual(p["example_id"], a["example_id"])
            self.assertEqual(p["history"], a["history"])
            self.assertEqual(p["history"][0]["position"], 1)

    def test_remote_runner_waits_for_breadth_and_matches_three_seeds(self) -> None:
        runner = Path("scripts/run_fse2027_paired_target_control_remote.sh").read_text()
        self.assertIn("breadth-extension/COMPLETE", runner)
        self.assertIn("for seed in 2027 2028 2029", runner)
        self.assertIn("--max-ted", runner)

    def test_analysis_includes_source_preservation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evaluation_root = root / "eval" / "seen"
            dataset_root = root / "datasets"
            evaluation_root.mkdir(parents=True)
            dataset_root.mkdir()
            dataset = {
                "example_id": "e",
                "problem_id": "p",
                "history": [{"code": "a = 1\nb = 2"}],
            }
            (dataset_root / "seen-test.jsonl").write_text(
                json.dumps(dataset) + "\n", encoding="utf-8"
            )
            progress = {
                "example_id": "e", "problem_id": "p", "repaired": True,
                "improved": True, "fixed_pass_rate": 1.0,
                "ted_buggy_fixed": 1, "ted_fixed_oracle": 1,
                "generated_code": "a = 1\nb = 3",
            }
            answer = dict(progress, generated_code="c = 9")
            for name, value in (("progress3", progress), ("answer3", answer)):
                composed = dict(value)
                composed.pop("generated_code")
                composed["selected_source"] = name.removesuffix("3") + "-2027"
                (evaluation_root / f"{name}.evaluation.jsonl").write_text(
                    json.dumps(composed) + "\n", encoding="utf-8"
                )
                for budget in ANALYSIS.BUDGETS:
                    (evaluation_root / f"{name}.max-ted-{budget}.evaluation.jsonl").write_text(
                        json.dumps(value) + "\n", encoding="utf-8"
                    )
            for relation, value in (("progress", progress), ("answer", answer)):
                for member_seed in (2027, 2028, 2029):
                    (evaluation_root / f"{relation}-{member_seed}.evaluation.jsonl").write_text(
                        json.dumps(value) + "\n", encoding="utf-8"
                    )
            result = ANALYSIS.analyze_split(
                root / "eval", dataset_root, "seen", samples=10, seed=1
            )
            retention = result["source_preservation_on_joint_repairs"]
            self.assertEqual(retention["joint_repairs"], 1)
            self.assertGreater(
                retention["metrics"]["token_retention"]["left_minus_right"], 0
            )


if __name__ == "__main__":
    unittest.main()
