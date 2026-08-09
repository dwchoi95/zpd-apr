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


def paired_row(mixed: float, answer: float, key: str = "mixed_minus_answer") -> dict:
    return {
        "mixed_target_9choose3": {"rr": mixed},
        "answer_9choose3": {"rr": answer},
        key: {
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": mixed - answer,
                    "cluster_bootstrap_95ci": [-0.01, 0.03],
                }
            ]
        },
    }


class ResultBridgeTest(unittest.TestCase):
    def test_canonical_values_and_macros(self) -> None:
        answer9 = {"splits": {"seen": split_row(0.6, 0.59), "unseen": split_row(0.7, 0.68)}}
        stability = {"problem_bootstrap": {"full_selection_fraction": 0.44}}
        answer_stability = {"problem_bootstrap": {"full_selection_fraction": 0.25}}
        problem_disjoint = {
            "selection": {"validation_problems": 138},
            "summary": {"rr": 0.58},
        }
        answer_problem_disjoint = {
            "summary": {"rr": 0.57},
            "problem_disjoint_minus_references": {
                "Mixed-target-problem-disjoint": {
                    "paired": [
                        {
                            "metric": "rr",
                            "left_minus_right_instance_weighted": -0.01,
                            "cluster_bootstrap_95ci": [-0.03, 0.01],
                        }
                    ]
                }
            },
        }
        hidden = {
            "methods": {
                "ZPDPatch": {"joint_repair_rate": 0.75},
                "Answer-9Choose3": {"joint_repair_rate": 0.72},
            },
            "comparison": {"left_minus_right": 0.03},
        }
        codeworkout = paired_row(0.84, 0.85, "zpdpatch_minus_answer_9choose3")
        codeworkout["zpdpatch"] = {"rr": 0.84}
        scale = {
            "splits": {
                "seen": paired_row(0.55, 0.53),
                "unseen": paired_row(0.65, 0.62),
            }
        }
        problem_holdout = paired_row(0.71, 0.68)
        result = build(
            answer9,
            hidden,
            codeworkout,
            scale,
            problem_holdout,
            stability,
            answer_stability,
            problem_disjoint,
            answer_problem_disjoint,
        )
        self.assertAlmostEqual(result["canonical"]["unseen"]["rr_difference"], 0.02)
        rendered = macros(result)
        self.assertIn(r"\newcommand{\AnswerNineSeenRR}{59.0}", rendered)
        self.assertIn(r"\newcommand{\MixedMinusAnswerNineUnseen}{2.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointSeenRR}{58.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointAnswerNineRR}{57.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointMixedMinusAnswerNine}{1.0}", rendered)
        self.assertIn(r"\newcommand{\AnswerNineSelectionBootstrapFrequency}{25.0}", rendered)
        self.assertIn(r"\newcommand{\HiddenMixedJointRR}{75.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutStudentAnswerNineRR}{85.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleMixedMinusAnswerNineSeen}{2.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemMixedRR}{71.0}", rendered)


if __name__ == "__main__":
    unittest.main()
