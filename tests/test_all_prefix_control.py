from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from scripts.build_all_prefix_evaluation import phase, transform
from scripts.analyze_all_prefix_control import analyze_split


class AllPrefixControlTest(unittest.TestCase):
    def test_phase_boundaries(self) -> None:
        self.assertEqual([phase(i, 7) for i in range(1, 7)], [
            "early", "early", "middle", "middle", "last", "last"
        ])
        self.assertEqual(phase(1, 2), "last")

    def test_transform_preserves_original_position_as_metadata(self) -> None:
        row = {
            "example_id": "e",
            "problem_id": "p",
            "user_id": "u",
            "history": [{"position": 1, "code": "a"}, {"position": 2, "code": "b"}],
            "target_position": 3,
            "current_pass_rate": 0.5,
            "current_execution_verdict": "WA",
        }
        result = transform(row)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["history"][0]["position"], 1)
        self.assertEqual(result["trajectory_source_position"], 2)
        self.assertEqual(result["trajectory_phase"], "last")
        self.assertEqual(result["attempts_remaining_to_acceptance"], 1)

    def test_analysis_reports_problem_clustered_phase_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "seen").mkdir()
            dataset = root / "seen.jsonl"
            rows = [
                {"example_id": "e1", "problem_id": "p1", "trajectory_phase": "early"},
                {"example_id": "e2", "problem_id": "p2", "trajectory_phase": "last"},
            ]
            dataset.write_text("".join(json.dumps(row) + "\n" for row in rows))
            evaluations = [
                {"example_id": "e1", "problem_id": "p1", "repaired": True, "improved": True, "fixed_pass_rate": 1.0},
                {"example_id": "e2", "problem_id": "p2", "repaired": False, "improved": False, "fixed_pass_rate": 0.0},
            ]
            (root / "seen" / "answer3.evaluation.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in evaluations)
            )
            result = analyze_split(root, dataset, "seen")
            early = result["by_trajectory_phase"]["early"]["answer"]
            self.assertEqual(early["rr"], 1.0)
            self.assertEqual(early["problem_cluster_bootstrap_95ci"], [1.0, 1.0])


if __name__ == "__main__":
    unittest.main()
