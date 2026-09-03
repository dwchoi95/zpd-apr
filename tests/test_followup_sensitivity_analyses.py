from __future__ import annotations

import unittest
from pathlib import Path

from scripts.analyze_codeworkout_exercise_sensitivity import analyze as analyze_exercises
from scripts.analyze_current_only_deployment_ladder import BUDGETS, analyze_split


def rows(values: tuple[bool, ...], problems: tuple[str, ...] | None = None) -> list[dict]:
    problems = problems or tuple(f"p{i}" for i in range(len(values)))
    return [{
        "example_id": f"e{i}", "problem_id": problems[i], "user_id": f"u{i}",
        "fixed_pass_rate": float(value), "repaired": value, "improved": value,
    } for i, value in enumerate(values)]


class FollowupSensitivityAnalysesTest(unittest.TestCase):
    def test_current_only_frontier_uses_predeclared_budgets(self) -> None:
        self.assertEqual(BUDGETS, (5, 10, 20, 40, 80, 160))
        runner = Path("scripts/run_fse2027_current_only_deployment_ladder_remote.sh").read_text()
        self.assertIn("--max-ted", runner)

    def test_current_only_ladder_reports_all_four_methods(self) -> None:
        result = analyze_split(
            rows((True, True, False, False)), rows((True, False, False, False)),
            rows((True, True, True, False)), rows((True, False, False, False)),
            samples=20, seed=7,
        )
        self.assertEqual(set(result["methods"]), {
            "answer_1", "answer_3seed", "answer_9choose3", "mixed_target_9choose3"
        })
        self.assertIn("mixed_minus_answer_3seed", result["comparisons"])

    def test_exercise_sensitivity_reports_each_exercise_and_loo(self) -> None:
        problems = ("x", "x", "y", "y")
        result = analyze_exercises(
            rows((True, True, True, False), problems),
            rows((True, False, False, False), problems),
            samples=20, seed=7,
        )
        self.assertEqual(result["test_exercises"], 2)
        self.assertEqual(len(result["per_exercise"]), 2)
        self.assertEqual(len(result["leave_one_exercise_out"]), 2)


if __name__ == "__main__":
    unittest.main()
