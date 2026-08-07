import unittest

from scripts.analyze_portfolio_selection_stability import analyze


def row(problem: str, repaired: bool, pass_rate: float) -> dict:
    return {
        "example_id": problem,
        "problem_id": problem,
        "buggy_pass_rate": 0.0,
        "fixed_pass_rate": pass_rate,
        "repaired": repaired,
    }


class PortfolioSelectionStabilityTest(unittest.TestCase):
    def test_reports_exact_selection_and_problem_overlap(self) -> None:
        evaluations = {
            "A": [row("p1", True, 1.0), row("p2", False, 0.2)],
            "B": [row("p1", False, 0.1), row("p2", True, 1.0)],
            "C": [row("p1", False, 0.2), row("p2", False, 0.3)],
            "D": [row("p1", False, 0.0), row("p2", False, 0.0)],
        }
        result = analyze(
            evaluations,
            test_rows=[row("p2", False, 0.0), row("p3", False, 0.0)],
            samples=50,
            seed=7,
        )
        self.assertEqual(result["feasible_portfolios"], 4)
        self.assertEqual(result["validation_test_problem_overlap"], 1)
        self.assertEqual(result["selected_full_validation"]["members"], ["A", "B", "C"])
        self.assertEqual(result["selected_problem_disjoint_validation"]["validation_problems"], 1)
        self.assertEqual(result["leave_one_problem_out"]["replicates"], 2)
        self.assertEqual(result["problem_bootstrap"]["samples"], 50)


if __name__ == "__main__":
    unittest.main()
