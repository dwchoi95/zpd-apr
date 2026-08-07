import unittest

from scripts.build_fse2027_result_bridge import build, macros


def split_row(mixed: float, answer: float) -> dict:
    return {
        "zpdpatch": {"rr": mixed},
        "answer_9choose3": {"rr": answer},
        "zpdpatch_minus_answer_9choose3": {
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": mixed - answer,
                    "cluster_bootstrap_95ci": [-0.01, 0.03],
                }
            ],
            "exact_mcnemar_two_sided_p": 0.5,
        },
        "budget_indexed_zpdpatch_minus_answer_9choose3": {
            "mean_over_predeclared_budgets": {
                "difference": 0.02,
                "problem_cluster_95ci": [0.0, 0.04],
            }
        },
    }


class ResultBridgeTest(unittest.TestCase):
    def test_canonical_values_and_macros(self) -> None:
        answer9 = {"splits": {"seen": split_row(0.6, 0.59), "unseen": split_row(0.7, 0.68)}}
        result = build(answer9, {"h": 1}, {"c": 1}, {"s": 1}, {"p": 1})
        self.assertAlmostEqual(result["canonical"]["unseen"]["rr_difference"], 0.02)
        rendered = macros(result)
        self.assertIn(r"\newcommand{\AnswerNineSeenRR}{59.0}", rendered)
        self.assertIn(r"\newcommand{\MixedMinusAnswerNineUnseen}{2.0}", rendered)


if __name__ == "__main__":
    unittest.main()
