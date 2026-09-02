from __future__ import annotations

import unittest

from scripts.plot_fse2027_mechanism_forest import forest_rows


class MechanismForestTest(unittest.TestCase):
    def test_extracts_five_adjacent_ladder_contrasts(self) -> None:
        def metric(key: str, value: float) -> dict:
            return {
                "metrics": [
                    {
                        "metric": "rr",
                        key: value,
                        "cluster_bootstrap_95ci": [value - 0.01, value + 0.01],
                    }
                ]
            }

        def paired(value: float) -> dict:
            return {
                "paired": [
                    {
                        "metric": "rr",
                        "left_minus_right_instance_weighted": value,
                        "cluster_bootstrap_95ci": [value - 0.01, value + 0.01],
                    }
                ]
            }

        decomposition = {
            "splits": {
                "seen": {
                    "stochastic_one_minus_greedy_one_expected": metric(
                        "mean_single_minus_right_instance_weighted", 0.01
                    ),
                    "three_minus_same_draw_one": metric(
                        "left_minus_mean_single_instance_weighted", 0.09
                    ),
                    "checkpoint_three_minus_same_draw_stochastic_three": paired(
                        0.02
                    ),
                }
            }
        }
        answer9 = {
            "splits": {
                "seen": {"answer_9choose3_minus_answer_3seed": paired(-0.01)}
            }
        }
        crossfit = {"mixed_minus_answer": paired(0.02)}
        rows = forest_rows(decomposition, answer9, crossfit)
        self.assertEqual(len(rows), 5)
        self.assertAlmostEqual(rows[1][1], 9.0)


if __name__ == "__main__":
    unittest.main()
