from __future__ import annotations

import unittest

from scripts.analyze_difficulty_matched_holdout import analyze


def dataset(problem: str, pass_rate: float, size: int) -> dict:
    code = "x=1\n" * size
    return {
        "example_id": f"{problem}:e", "problem_id": problem,
        "problem_description": "task " * size,
        "history": [{"code": code, "pass_rate": pass_rate, "tc_outcomes": {"a": "WA"}}],
        "current_pass_rate": pass_rate, "current_tc_outcomes": {"a": "WA"},
    }


def evaluation(problem: str, repaired: bool) -> dict:
    return {"example_id": f"{problem}:e", "problem_id": problem, "repaired": repaired}


class DifficultyMatchedHoldoutTest(unittest.TestCase):
    def test_matching_never_uses_repair_outcome(self) -> None:
        result = analyze(
            [dataset("s1", 0.1, 1), dataset("s2", 0.9, 4)],
            [dataset("u1", 0.1, 1)],
            [evaluation("s1", False), evaluation("s2", True)],
            [evaluation("u1", True)], samples=50, seed=7,
        )
        self.assertFalse(result["repair_outcomes_used_for_matching"])
        self.assertEqual(result["matched_pairs"][0]["seen_problem"], "s1")
        self.assertEqual(result["unseen_minus_matched_seen"], 1.0)


if __name__ == "__main__":
    unittest.main()
