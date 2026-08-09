import unittest

from scripts.analyze_fse2027_effect_heterogeneity import (
    analyze,
    ast_nodes,
    pass_rate_bin,
    program_size_bin,
    trajectory_length_bin,
)


def evaluation(example_id: str, problem_id: str, repaired: bool) -> dict:
    return {
        "example_id": example_id,
        "problem_id": problem_id,
        "repaired": repaired,
        "improved": repaired,
        "fixed_pass_rate": 1.0 if repaired else 0.5,
        "ted_buggy_fixed": 1 if repaired else None,
        "ted_fixed_oracle": 1 if repaired else None,
    }


class EffectHeterogeneityTest(unittest.TestCase):
    def test_fixed_bins(self) -> None:
        self.assertEqual(pass_rate_bin(0.25), "[.25,.50)")
        self.assertEqual(trajectory_length_bin(5), "5+")
        self.assertEqual(program_size_bin(110), "75-110")
        self.assertIsNone(ast_nodes("not valid python"))

    def test_analysis_pairs_every_declared_dimension(self) -> None:
        dataset = [
            {
                "example_id": "e1",
                "problem_id": "p1",
                "current_execution_verdict": "Wrong Answer",
                "current_pass_rate": 0.2,
                "history": [{"code": "x = 1", "pass_rate": 0.2}],
            },
            {
                "example_id": "e2",
                "problem_id": "p2",
                "current_execution_verdict": "Runtime Error",
                "current_pass_rate": 0.8,
                "history": [
                    {"code": "x = 0", "pass_rate": 0.1},
                    {"code": "x = 1", "pass_rate": 0.8},
                ],
            },
        ]
        mixed = [evaluation("e1", "p1", True), evaluation("e2", "p2", True)]
        answer = [evaluation("e1", "p1", False), evaluation("e2", "p2", True)]
        zero = [evaluation("e1", "p1", False), evaluation("e2", "p2", False)]
        result = analyze(dataset, mixed, answer, zero, samples=20, seed=7)
        self.assertTrue(result["strata_fixed_before_reading_method_outcomes"])
        self.assertEqual(
            set(result["dimensions"]),
            {"current_verdict", "current_pass_rate", "trajectory_length", "current_ast_nodes"},
        )
        low = result["dimensions"]["current_pass_rate"]["[0,.25)"]
        self.assertEqual(
            low["mixed_minus_answer9"]["rr_contingency"]["left_only"], 1
        )
        self.assertEqual(
            low["mixed_minus_zero_shot"]["rr_contingency"]["left_only"], 1
        )


if __name__ == "__main__":
    unittest.main()
