from __future__ import annotations

import unittest
from pathlib import Path

from scripts.analyze_stochastic_one_decomposition import analyze_split


def row(example: str, problem: str, repaired: bool) -> dict:
    return {
        "example_id": example,
        "problem_id": problem,
        "repaired": repaired,
        "improved": repaired,
        "fixed_pass_rate": float(repaired),
    }


class StochasticOneDecompositionTest(unittest.TestCase):
    def test_runner_uses_fixed_lower_memory_fraction(self) -> None:
        runner = Path(
            "scripts/run_fse2027_stochastic_one_decomposition_remote.sh"
        ).read_text()
        self.assertIn("--sampling-seed 4101 --sampling-seed 4102", runner)
        self.assertIn("--gpu-memory-utilization 0.82", runner)

    def test_same_draw_union_decomposes_candidate_breadth(self) -> None:
        singles = [
            [row("a", "p", True), row("b", "q", False)],
            [row("a", "p", False), row("b", "q", True)],
            [row("a", "p", False), row("b", "q", False)],
        ]
        union = [row("a", "p", True), row("b", "q", True)]
        greedy = [row("a", "p", False), row("b", "q", False)]
        checkpoint3 = [row("a", "p", True), row("b", "q", False)]
        result = analyze_split(
            union, singles, greedy, checkpoint3, samples=50, seed=7
        )
        self.assertAlmostEqual(result["stochastic_one_expectation"]["mean_rr"], 1 / 3)
        rr = next(
            item
            for item in result["three_minus_same_draw_one"]["metrics"]
            if item["metric"] == "rr"
        )
        self.assertAlmostEqual(rr["left_minus_mean_single_instance_weighted"], 2 / 3)
        decoding_rr = next(
            item
            for item in result["stochastic_one_minus_greedy_one_expected"]["metrics"]
            if item["metric"] == "rr"
        )
        self.assertAlmostEqual(
            decoding_rr["mean_single_minus_right_instance_weighted"], 1 / 3
        )
        self.assertEqual(len(result["stochastic_one_minus_greedy_one"]), 3)
        checkpoint_rr = next(
            item
            for item in result[
                "checkpoint_three_minus_same_draw_stochastic_three"
            ]["paired"]
            if item["metric"] == "rr"
        )
        self.assertAlmostEqual(checkpoint_rr["left_minus_right_instance_weighted"], -0.5)


if __name__ == "__main__":
    unittest.main()
