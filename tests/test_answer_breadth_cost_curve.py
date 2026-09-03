from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "breadth_curve", Path("scripts/analyze_answer_breadth_cost_curve.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class AnswerBreadthCostCurveTest(unittest.TestCase):
    def test_fixed_k_curve_and_early_stop_cost(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            split = root / "seen"
            split.mkdir()
            for seed in MODULE.SEEDS:
                rows = [
                    {"example_id": "a", "problem_id": "p1", "repaired": seed == 4101},
                    {"example_id": "b", "problem_id": "p2", "repaired": seed == 4105},
                ]
                (split / f"sample-{seed}.evaluation.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
                )
                generations = [
                    {
                        "example_id": row["example_id"],
                        "problem_id": row["problem_id"],
                        "generation_time_sec": 0.25,
                    }
                    for row in rows
                ]
                (split / f"sample-{seed}.generations.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in generations),
                    encoding="utf-8",
                )
            curve = MODULE.analyze_split(root, "seen", samples=100, seed=1)
            self.assertEqual(curve["1"]["union_repair_rate"], 0.5)
            self.assertEqual(curve["5"]["union_repair_rate"], 1.0)
            self.assertEqual(curve["5"]["newly_repaired_since_previous_k"], 1)
            self.assertEqual(curve["5"]["mean_sequential_candidates_invoked"], 3.0)
            self.assertEqual(curve["5"]["mean_amortized_generation_sec"], 0.75)

    def test_runner_freezes_full_curve_and_temperature_extension(self) -> None:
        runner = Path("scripts/run_fse2027_breadth_extension_remote.sh").read_text()
        for seed in (4101, 4103, 4104, 4120):
            self.assertIn(str(seed), runner)
        self.assertIn("for temperature in 1.2 1.5", runner)


if __name__ == "__main__":
    unittest.main()
