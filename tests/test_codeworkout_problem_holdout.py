import sys
import unittest
from pathlib import Path

from scripts.split_codeworkout_problems import apply_split

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from analyze_codeworkout_problem_holdout import analyze  # noqa: E402


class CodeWorkoutProblemHoldoutTest(unittest.TestCase):
    def test_problem_assignment_is_disjoint_and_deterministic(self) -> None:
        rows = [
            {"problem_id": f"p{problem}", "user_id": f"u{user}", "split": "old"}
            for problem in range(10)
            for user in range(2)
        ]
        first, summary = apply_split(rows, 2027)
        second, _ = apply_split(rows, 2027)
        self.assertEqual(first, second)
        assignment = {}
        for row in first:
            assignment.setdefault(row["problem_id"], set()).add(row["split"])
        self.assertTrue(all(len(splits) == 1 for splits in assignment.values()))
        self.assertEqual(set(summary["problems_by_split"]), {"train", "valid", "test"})
        self.assertEqual(summary["problem_overlap_counts"], {
            "train-valid": 0,
            "train-test": 0,
            "valid-test": 0,
        })
        self.assertEqual(set(summary["students_by_split"]), {"train", "valid", "test"})
        self.assertEqual(
            set(summary["student_overlap_counts"]),
            {"train-valid", "train-test", "valid-test"},
        )

    def test_reports_answer_mechanism_ladder(self) -> None:
        def row(example: str, repaired: bool) -> dict:
            return {
                "example_id": example,
                "problem_id": "exercise-1",
                "user_id": "student-1",
                "fixed_pass_rate": float(repaired),
                "repaired": repaired,
                "improved": repaired,
                "ted_buggy_fixed": 1 if repaired else None,
                "ted_fixed_oracle": 0 if repaired else None,
            }

        mixed = [row("e1", True), row("e2", True)]
        answer9 = [row("e1", True), row("e2", False)]
        answer3 = [row("e1", False), row("e2", True)]
        answer1 = [row("e1", False), row("e2", False)]
        mixed_selection = {
            "candidate_checkpoint_count": 9,
            "feasible_unconstrained_size_three_portfolios": 84,
            "best_unconstrained": {"members": ["Progress2027", "Strict2028", "Answer2029"]},
        }
        answer_selection = {
            "candidate_checkpoint_count": 9,
            "feasible_portfolios": 84,
            "selected_unrestricted": {"members": ["Answer2030", "Answer2031", "Answer2032"]},
        }
        result = analyze(
            mixed, answer9, answer3, answer1,
            mixed_selection, answer_selection, samples=20,
        )
        self.assertEqual(result["answer_1"]["rr"], 0.0)
        self.assertEqual(result["answer_3seed"]["rr"], 0.5)
        self.assertIn("answer_3seed_minus_answer_1", result)
        self.assertIn("answer_9choose3_minus_answer_3seed", result)


if __name__ == "__main__":
    unittest.main()
