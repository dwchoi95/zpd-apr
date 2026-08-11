from __future__ import annotations

import unittest

from scripts.analyze_stochastic_candidate_control import analyze_split, generation_diversity


def evaluation(example_id: str, repaired: bool, method: str) -> dict:
    return {
        "example_id": example_id,
        "problem_id": f"p-{example_id}",
        "user_id": f"u-{example_id}",
        "method": method,
        "buggy_pass_rate": 0.0,
        "current_pass_rate": 0.0,
        "fixed_pass_rate": float(repaired),
        "repaired": repaired,
        "improved": repaired,
        "candidate_count": 3,
        "selected_source": method,
    }


class StochasticCandidateControlTest(unittest.TestCase):
    @staticmethod
    def rr_difference(contrast: dict) -> float:
        return next(
            row["left_minus_right_instance_weighted"]
            for row in contrast["paired"]
            if row["metric"] == "rr"
        )

    def test_generation_diversity_counts_unique_candidates(self) -> None:
        stages = [
            [
                {"example_id": "a", "generated_code": code_a},
                {"example_id": "b", "generated_code": code_b},
            ]
            for code_a, code_b in (("x", "q"), ("y", "q"), ("z", "q"))
        ]
        result = generation_diversity(stages)
        self.assertEqual(result["all_three_unique"], 1)
        self.assertEqual(result["all_identical"], 1)
        self.assertEqual(result["mean_unique_candidates"], 2.0)

    def test_analysis_separates_sampling_and_checkpoint_breadth(self) -> None:
        stochastic = [evaluation("a", True, "s"), evaluation("b", False, "s")]
        answer3 = [evaluation("a", True, "a3"), evaluation("b", True, "a3")]
        answer1 = [evaluation("a", False, "a1"), evaluation("b", False, "a1")]
        generations = [
            [
                {"example_id": "a", "generated_code": f"x{stage}"},
                {"example_id": "b", "generated_code": f"y{stage}"},
            ]
            for stage in range(3)
        ]
        result = analyze_split(
            stochastic, answer3, answer1, generations, samples=20, seed=7
        )
        self.assertEqual(
            self.rr_difference(result["stochastic_3_minus_greedy_1"]),
            0.5,
        )
        self.assertEqual(
            self.rr_difference(result["checkpoint_3_minus_stochastic_3"]),
            0.5,
        )


if __name__ == "__main__":
    unittest.main()
