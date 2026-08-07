import unittest

from scripts.select_answer_seed_portfolio import select


def row(example_id: str, repaired: bool) -> dict:
    return {
        "example_id": example_id,
        "buggy_pass_rate": 0.0,
        "fixed_pass_rate": 1.0 if repaired else 0.0,
        "repaired": repaired,
        "ted_buggy_fixed": 1 if repaired else None,
    }


class AnswerSeedPortfolioTest(unittest.TestCase):
    def test_exhaustive_choose_three(self) -> None:
        evaluations = {
            f"Answer{seed}": [row("x", seed == 1), row("y", seed == 2)]
            for seed in range(1, 10)
        }
        result = select(evaluations)
        self.assertEqual(result["feasible_portfolios"], 84)
        self.assertEqual(result["selected_unrestricted"]["score"]["repaired"], 2)
        self.assertEqual(len(result["selected_unrestricted"]["members"]), 3)


if __name__ == "__main__":
    unittest.main()
