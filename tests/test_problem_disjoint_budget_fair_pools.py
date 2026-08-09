import tempfile
import unittest
from pathlib import Path

from scripts.analyze_problem_disjoint_budget_fair_pools import analyze


def rows(name: str, repaired: bool) -> list[dict]:
    return [
        {
            "example_id": "e1",
            "problem_id": "p1",
            "user_id": "u1",
            "buggy_pass_rate": 0.0,
            "fixed_pass_rate": 1.0 if repaired else 0.0,
            "repaired": repaired,
            "improved": repaired,
            "ted_buggy_fixed": 1 if repaired else None,
            "ted_fixed_oracle": 0 if repaired else None,
            "method": name,
        }
    ]


class ProblemDisjointBudgetFairPoolsTest(unittest.TestCase):
    def test_composes_all_predeclared_budgets(self) -> None:
        mixed_names = ["Progress1", "Strict1", "Answer1"]
        answer_names = ["Answer1", "Answer2", "Answer3"]
        selection = {
            "validation_problems": 1,
            "mixed": {
                "selection_partition": "disjoint",
                "selected_unconstrained_by_budget": {
                    str(b): {"members": mixed_names} for b in (5, 10, 20, 40, 80, 160)
                },
            },
            "answer": {
                "selected_by_budget": {
                    str(b): {"members": answer_names} for b in (5, 10, 20, 40, 80, 160)
                }
            },
        }
        mixed = {name: rows(name, name == "Progress1") for name in mixed_names}
        answer = {name: rows(name, name == "Answer1") for name in answer_names}
        with tempfile.TemporaryDirectory() as directory:
            result = analyze(
                selection,
                mixed,
                answer,
                output_root=Path(directory),
                samples=20,
                seed=2027,
            )
            self.assertEqual(len(result["mixed"]), 6)
            self.assertAlmostEqual(
                result["mixed_minus_answer"]["mean_over_predeclared_budgets"][
                    "difference"
                ],
                0.0,
            )


if __name__ == "__main__":
    unittest.main()
