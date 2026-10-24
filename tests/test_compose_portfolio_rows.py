import unittest

from src.experiments.compose_answer_seed_control import compose


def _row(example_id: str, repaired: bool, pass_rate: float, code: str, kept: float) -> dict[str, object]:
    return {
        "example_id": example_id, "problem_id": "p", "user_id": "u", "buggy_pass_rate": 0.0,
        "fixed_pass_rate": pass_rate, "repaired": repaired, "ted_buggy_fixed": 3 if repaired else None,
        "generated_code": code, "token_retention": kept, "line_retention": kept,
    }


class ComposePortfolioRowsTest(unittest.TestCase):
    def test_composed_rows_carry_the_returned_program_and_its_retention(self) -> None:
        dataset = [{"example_id": e} for e in ("a", "b")]
        first = [_row("a", False, 0.5, "first-a", 0.9), _row("b", False, 0.0, "first-b", 0.8)]
        second = [_row("a", True, 1.0, "second-a", 0.7), _row("b", False, 0.0, "second-b", 0.6)]
        by_id = {row["example_id"]: row for row in compose(dataset, [("A", first), ("B", second)])}
        self.assertEqual((by_id["a"]["generated_code"], by_id["a"]["token_retention"]), ("second-a", 0.7))
        # No candidate raises the pass fraction, so the submission comes back unchanged.
        self.assertEqual(by_id["b"]["selected_source"], "current-fallback")
        self.assertEqual((by_id["b"]["generated_code"], by_id["b"]["token_retention"]), (None, 1.0))


if __name__ == "__main__":
    unittest.main()
