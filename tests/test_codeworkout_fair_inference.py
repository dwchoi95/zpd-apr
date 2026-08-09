from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_codeworkout_answer9 import analyze as analyze_student  # noqa: E402
from analyze_codeworkout_problem_holdout import analyze as analyze_problem  # noqa: E402


def rows(repaired: tuple[bool, ...]) -> list[dict]:
    return [
        {
            "example_id": f"e{index}",
            "problem_id": f"p{index % 2}",
            "user_id": f"u{index // 2}",
            "fixed_pass_rate": float(value),
            "repaired": value,
            "improved": value,
        }
        for index, value in enumerate(repaired)
    ]


class CodeWorkoutFairInferenceTest(unittest.TestCase):
    def test_student_and_exercise_cluster_intervals_are_both_reported(self) -> None:
        mixed = rows((True, True, False, True))
        answer = rows((True, False, True, False))
        answer_selection = {
            "candidate_checkpoint_count": 9,
            "feasible_portfolios": 84,
            "selected_unrestricted": {"members": ["A1", "A2", "A3"]},
        }
        student = analyze_student(
            mixed, answer, answer_selection, samples=100, seed=2027
        )
        contrast = student["zpdpatch_minus_answer_9choose3"]
        self.assertEqual(len(contrast["student_cluster_rr_95ci"]), 2)
        self.assertEqual(
            len(next(row for row in contrast["paired"] if row["metric"] == "rr")[
                "cluster_bootstrap_95ci"
            ]),
            2,
        )

        mixed_selection = {"best_unconstrained": {"members": ["M1", "M2", "M3"]}}
        problem = analyze_problem(
            mixed,
            answer,
            mixed_selection,
            answer_selection,
            samples=100,
            seed=2027,
        )
        self.assertEqual(
            len(problem["mixed_minus_answer"]["student_cluster_rr_95ci"]), 2
        )


if __name__ == "__main__":
    unittest.main()
