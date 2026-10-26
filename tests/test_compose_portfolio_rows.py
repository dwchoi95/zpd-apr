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

    def test_forward_fallback_skips_a_candidate_that_worsens_a_test_case(self) -> None:
        dataset = [{"example_id": e, "current_execution_verdict": "WA", "current_tc_outcomes": {"t1": "AC", "t2": "WA", "t3": "WA"}}
                   for e in ("a", "b")]
        def failing(example_id: str, pass_rate: float, code: str, outcomes: dict[str, str]) -> dict[str, object]:
            return dict(_row(example_id, False, pass_rate, code, 0.5), buggy_pass_rate=1 / 3, fixed_verdict="WA", fixed_tc_outcomes=outcomes)
        # a: the most passing candidate loses t1 that the submission passed; the other one only gains t2.
        first = [failing("a", 2 / 3, "regress-a", {"t1": "WA", "t2": "AC", "t3": "AC"}),
                 failing("b", 2 / 3, "regress-b", {"t1": "WA", "t2": "AC", "t3": "AC"})]
        second = [failing("a", 2 / 3 - 0.1, "forward-a", {"t1": "AC", "t2": "AC", "t3": "WA"}),
                  failing("b", 1 / 3, "same-b", {"t1": "AC", "t2": "WA", "t3": "WA"})]
        stages = [("A", first), ("B", second)]
        by_id = {row["example_id"]: row for row in compose(dataset, stages, forward_fallback=True)}
        self.assertEqual(by_id["a"]["generated_code"], "forward-a")
        self.assertEqual(by_id["b"]["selected_source"], "current-fallback")
        # Without the gate, the candidate passing the most test cases comes back.
        self.assertEqual({row["example_id"]: row for row in compose(dataset, stages)}["a"]["generated_code"], "regress-a")


if __name__ == "__main__":
    unittest.main()
