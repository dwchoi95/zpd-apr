import unittest

from scripts.build_fse2027_result_bridge import build, macros


def split_row(mixed: float, answer: float) -> dict:
    return {
        "zpdpatch": {"rr": mixed},
        "answer_9choose3": {"rr": answer},
        "answer_3seed": {"rr": answer - 0.01},
        "answer_1": {"rr": answer - 0.05},
        "answer_3seed_minus_answer_1": {
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": 0.04,
                    "cluster_bootstrap_95ci": [0.02, 0.06],
                }
            ]
        },
        "answer_9choose3_minus_answer_3seed": {
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": 0.01,
                    "cluster_bootstrap_95ci": [-0.01, 0.03],
                }
            ]
        },
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
    result = {
        "mixed_target_9choose3": {"pr": mixed + 0.1, "rr": mixed, "ir": mixed + 0.05},
        "answer_9choose3": {"pr": answer + 0.1, "rr": answer, "ir": answer + 0.05},
        key: {
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": mixed - answer,
                    "cluster_bootstrap_95ci": [-0.01, 0.03],
                }
            ],
            "student_cluster_rr_95ci": [-0.02, 0.04],
            "exact_mcnemar_two_sided_p": 0.5,
        },
    }
    if key == "mixed_minus_answer":
        result["budget_indexed_mixed_minus_answer"] = {
            "mean_over_predeclared_budgets": {
                "difference": 0.015,
                "problem_cluster_95ci": [-0.005, 0.035],
            }
        }
    return result


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
        problem_disjoint_budget = {
            "mixed_minus_answer": {
                "mean_over_predeclared_budgets": {
                    "difference": 0.011,
                    "problem_cluster_95ci": [-0.002, 0.024],
                },
                "per_budget": {
                    "10": {
                        "difference": 0.026,
                        "problem_cluster_95ci": [0.008, 0.044],
                    },
                    "40": {
                        "difference": 0.022,
                        "problem_cluster_95ci": [0.002, 0.041],
                    },
                },
            }
        }
        patch_locality = {
            "comparisons": {
                "Progress_minus_Answer": {
                    "metrics": {
                        "token_retention": {
                            "left_minus_right": 0.013,
                            "problem_cluster_bootstrap_95ci": [0.001, 0.026],
                        },
                        "line_retention": {
                            "left_minus_right": 0.029,
                            "problem_cluster_bootstrap_95ci": [0.012, 0.047],
                        },
                    }
                },
                "Mixed9_minus_Answer9": {
                    "metrics": {
                        "token_retention": {
                            "left_minus_right": 0.026,
                            "problem_cluster_bootstrap_95ci": [0.016, 0.036],
                        },
                        "line_retention": {
                            "left_minus_right": 0.033,
                            "problem_cluster_bootstrap_95ci": [0.019, 0.048],
                        },
                    }
                },
            }
        }
        hidden = {
            "methods": {
                "ZPDPatch": {"joint_repair_rate": 0.75},
                "Answer-9Choose3": {"joint_repair_rate": 0.72},
            },
            "comparison": {
                "left_minus_right": 0.03,
                "problem_cluster_95_ci": [-0.01, 0.06],
            },
        }
        codeworkout = paired_row(0.84, 0.85, "zpdpatch_minus_answer_9choose3")
        codeworkout["zpdpatch"] = {"rr": 0.84}
        scale = {
            "mixed_members": ["Progress2027", "Strict2028", "Answer2029"],
            "answer_members": ["Answer2030", "Answer2032", "Answer2035"],
            "splits": {
                "seen": paired_row(0.55, 0.53),
                "unseen": paired_row(0.65, 0.62),
            }
        }
        for row in scale["splits"].values():
            row["answer_3seed"] = {"pr": 0.61, "rr": 0.51, "ir": 0.56}
            row["answer_1"] = {"pr": 0.55, "rr": 0.45, "ir": 0.50}
            row["answer_3seed_minus_answer_1"] = row["mixed_minus_answer"]
            row["answer_9choose3_minus_answer_3seed"] = row["mixed_minus_answer"]
        problem_holdout = paired_row(0.71, 0.68)
        problem_holdout["mixed_members"] = [
            "Progress2027",
            "Strict2028",
            "Answer2029",
        ]
        problem_holdout["answer_members"] = [
            "Answer2030",
            "Answer2032",
            "Answer2035",
        ]
        problem_holdout["answer_3seed"] = {"pr": 0.80, "rr": 0.70, "ir": 0.75}
        problem_holdout["answer_1"] = {"pr": 0.73, "rr": 0.63, "ir": 0.68}
        problem_holdout["answer_3seed_minus_answer_1"] = problem_holdout["mixed_minus_answer"]
        problem_holdout["answer_9choose3_minus_answer_3seed"] = problem_holdout["mixed_minus_answer"]
        normalized_ted = {
            "examples_parseable_current": 966,
            "examples_excluded_unparseable_current": 31,
            "current_ast_node_distribution": {
                "p25": 74.0,
                "median": 110.0,
                "p75": 190.0,
            },
            "absolute_budget_context": {
                str(budget): {
                    "fraction_of_current_ast_median": budget / 110,
                    "fraction_where_budget_is_at_most_10pct": fraction,
                }
                for budget, fraction in (
                    (5, 0.919),
                    (10, 0.568),
                    (20, 0.228),
                    (40, 0.033),
                )
            },
            "per_budget": {
                "0.1": {
                    "mixed_minus_answer": 0.028,
                    "problem_cluster_95ci": [0.0104, 0.0461],
                },
                "0.2": {
                    "mixed_minus_answer": 0.0383,
                    "problem_cluster_95ci": [0.0181, 0.0595],
                },
                "0.4": {
                    "mixed_minus_answer": 0.029,
                    "problem_cluster_95ci": [0.0061, 0.0523],
                },
            },
        }
        operational_cost = {
            "mechanism_ladder_seen": {
                "A1": {
                    "train_gpu_hours": 5.84,
                    "portfolio_selection_validation_executions": 0,
                    "repair_rate": 0.501,
                    "mean_candidates_invoked": 1.0,
                },
                "A3": {
                    "train_gpu_hours": 17.52,
                    "portfolio_selection_validation_executions": 0,
                    "repair_rate": 0.617,
                    "mean_candidates_invoked": 1.93,
                },
                "A9": {
                    "train_gpu_hours": 52.57,
                    "portfolio_selection_validation_executions": 4149,
                    "repair_rate": 0.598,
                    "mean_candidates_invoked": 1.93,
                },
                "M9": {
                    "train_gpu_hours": 37.07,
                    "portfolio_selection_validation_executions": 4149,
                    "repair_rate": 0.615,
                    "mean_candidates_invoked": 1.98,
                },
            }
        }
        prompt_distribution = {
            "current_only_mixed_members": [
                "Progress2027",
                "Strict2028",
                "Answer2029",
            ],
            "current_only_answer_members": [
                "Answer2030",
                "Answer2032",
                "Answer2035",
            ],
            "splits": {},
        }
        for split in ("seen", "unseen"):
            prompt_distribution["splits"][split] = {
                "current_only_reselected": paired_row(0.64, 0.60),
                "full_history_selected_members": {
                    "prompt_context_effect": {
                        "mixed_current_only_minus_full_history": {
                            "paired": [
                                {
                                    "metric": "rr",
                                    "left_minus_right_instance_weighted": -0.01,
                                    "cluster_bootstrap_95ci": [-0.03, 0.01],
                                }
                            ]
                        },
                        "answer_current_only_minus_full_history": {
                            "paired": [
                                {
                                    "metric": "rr",
                                    "left_minus_right_instance_weighted": 0.03,
                                    "cluster_bootstrap_95ci": [0.01, 0.05],
                                }
                            ]
                        },
                    }
                },
            }
        problem_crossfit = {
            "folds": 5,
            "mixed": {"rr": 0.61},
            "answer": {"rr": 0.59},
            "mixed_minus_answer": {
                "paired": [
                    {
                        "metric": "rr",
                        "left_minus_right_instance_weighted": 0.02,
                        "cluster_bootstrap_95ci": [-0.01, 0.05],
                    }
                ],
                "exact_mcnemar_two_sided_p": 0.4,
            },
            "budget": {
                "mixed_minus_answer": {
                    "mean_over_predeclared_budgets": {
                        "difference": 0.013,
                        "problem_cluster_95ci": [0.001, 0.025],
                    },
                    "per_budget": {
                        "10": {
                            "difference": 0.025,
                            "problem_cluster_95ci": [0.005, 0.045],
                        },
                        "40": {
                            "difference": 0.021,
                            "problem_cluster_95ci": [0.002, 0.04],
                        },
                    },
                }
            },
        }
        verdict_order = {
            "dataset_summaries": {
                "train-progress": {"written_examples": 12000},
                "valid-progress": {"written_examples": 1400},
                "train-strict": {"written_examples": 10000},
                "valid-strict": {"written_examples": 1200},
            },
            "relations": {},
        }
        for relation in ("progress", "strict"):
            verdict_order["relations"][relation] = {"splits": {}}
            for split in ("seen", "unseen"):
                verdict_order["relations"][relation]["splits"][split] = {
                    "canonical": {"rr": 0.52},
                    "alternative": {"rr": 0.50},
                    "canonical_minus_alternative": {
                        "paired": [
                            {
                                "metric": "rr",
                                "left_minus_right_instance_weighted": 0.02,
                                "cluster_bootstrap_95ci": [-0.01, 0.05],
                            }
                        ]
                    },
                    "repair_agreement": {"decision_agreement": 0.88},
                }
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
            problem_disjoint_budget,
            patch_locality,
            normalized_ted,
            operational_cost,
            prompt_distribution,
            problem_crossfit,
            verdict_order,
        )
        self.assertAlmostEqual(result["canonical"]["unseen"]["rr_difference"], 0.02)
        rendered = macros(result)
        self.assertIn(r"\newcommand{\AnswerNineSeenRR}{59.0}", rendered)
        self.assertIn(r"\newcommand{\AnswerThreeMinusOneSeen}{4.0}", rendered)
        self.assertIn(r"\newcommand{\AnswerThreeMinusOneSeenCI}{[2.00, 6.00]}", rendered)
        self.assertIn(r"\newcommand{\AnswerNineMinusThreeSeen}{1.0}", rendered)
        self.assertIn(r"\newcommand{\MixedMinusAnswerNineUnseen}{2.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointSeenRR}{58.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointAnswerNineRR}{57.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointMixedMinusAnswerNine}{1.0}", rendered)
        self.assertIn(r"\newcommand{\ProblemDisjointBudgetMixedMinusAnswerNine}{1.1}", rendered)
        self.assertIn(
            r"\newcommand{\ProblemDisjointBudgetMixedMinusAnswerNineCI}{[-0.20, 2.40]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\ProblemDisjointTED10MixedMinusAnswerNine}{2.6}", rendered)
        self.assertIn(r"\newcommand{\ProgressMinusAnswerTokenRetention}{1.3}", rendered)
        self.assertIn(
            r"\newcommand{\ProgressMinusAnswerTokenRetentionCI}{[0.10, 2.60]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\MixedMinusAnswerNineLineRetention}{3.3}", rendered)
        self.assertIn(r"\newcommand{\AnswerNineSelectionBootstrapFrequency}{25.0}", rendered)
        self.assertIn(r"\newcommand{\HiddenMixedJointRR}{75.0}", rendered)
        self.assertIn(
            r"\newcommand{\HiddenMixedMinusAnswerNineCI}{[-1.00, 6.00]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\CodeWorkoutStudentAnswerNineRR}{85.0}", rendered)
        self.assertIn(
            r"\newcommand{\CodeWorkoutStudentMixedMinusAnswerNineStudentCI}{[-2.00, 4.00]}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\CodeWorkoutStudentMixedMinusAnswerNineExerciseCI}{[-1.00, 3.00]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\ScaleMixedMinusAnswerNineSeen}{2.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleMixedSeenPR}{65.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleMixedSeenIR}{60.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerThreeSeenRR}{51.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerThreeSeenPR}{61.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerThreeSeenIR}{56.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerOneSeenRR}{45.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerOneSeenPR}{55.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerOneSeenIR}{50.0}", rendered)
        self.assertIn(r"\newcommand{\ScaleAnswerThreeMinusOneSeen}{2.0}", rendered)
        self.assertIn(
            r"\newcommand{\ScaleMixedMembers}{Progress2027--Strict2028--Answer2029}",
            rendered,
        )
        self.assertIn(r"\newcommand{\ScaleMixedMinusAnswerNineSeenP}{0.5}", rendered)
        self.assertIn(r"\newcommand{\ScaleBudgetMixedMinusAnswerNineSeen}{1.5}", rendered)
        self.assertIn(
            r"\newcommand{\ScaleBudgetMixedMinusAnswerNineSeenCI}{[-0.50, 3.50]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\CodeWorkoutProblemMixedRR}{71.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemMixedPR}{81.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemMixedIR}{76.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemAnswerThreeRR}{70.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemAnswerThreePR}{80.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemAnswerThreeIR}{75.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemAnswerOneRR}{63.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemAnswerOnePR}{73.0}", rendered)
        self.assertIn(r"\newcommand{\CodeWorkoutProblemAnswerOneIR}{68.0}", rendered)
        self.assertIn(
            r"\newcommand{\CodeWorkoutProblemAnswerNineMembers}{Answer2030--Answer2032--Answer2035}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\CodeWorkoutProblemMixedMinusAnswerNineP}{0.5}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\CodeWorkoutProblemMixedMinusAnswerNineStudentCI}{[-2.00, 4.00]}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\CodeWorkoutProblemMixedMinusAnswerNineExerciseCI}{[-1.00, 3.00]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\NormalizedTEDExamples}{966}", rendered)
        self.assertIn(r"\newcommand{\CurrentASTNodesMedian}{110}", rendered)
        self.assertIn(r"\newcommand{\TED10MedianASTFraction}{9.1}", rendered)
        self.assertIn(r"\newcommand{\TED5AtMostTenPercentInputs}{91.9}", rendered)
        self.assertIn(
            r"\newcommand{\NormalizedTEDTwentyMixedMinusAnswerNine}{3.8}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\NormalizedTEDFortyMixedMinusAnswerNineCI}{[0.61, 5.23]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\CostA9TrainHours}{52.6}", rendered)
        self.assertIn(r"\newcommand{\CostM9ValidationExecutions}{4149}", rendered)
        self.assertIn(r"\newcommand{\CostM9MeanCalls}{1.98}", rendered)
        self.assertIn(r"\newcommand{\PromptCurrentMixedSeenRR}{64.0}", rendered)
        self.assertIn(
            r"\newcommand{\PromptCurrentMixedMinusAnswerNineSeenCI}{[-1.00, 3.00]}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\PromptFrozenAnswerNineCurrentMinusFullSeen}{3.0}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\PromptFrozenMixedCurrentMinusFullUnseenCI}{[-3.00, 1.00]}",
            rendered,
        )
        self.assertIn(r"\newcommand{\CrossFitFolds}{5}", rendered)
        self.assertIn(r"\newcommand{\CrossFitMixedSeenRR}{61.0}", rendered)
        self.assertIn(
            r"\newcommand{\CrossFitMixedMinusAnswerNineSeenCI}{[-1.00, 5.00]}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\CrossFitBudgetMixedMinusAnswerNineSeen}{1.3}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\CrossFitTED40MixedMinusAnswerNineSeenCI}{[0.20, 4.00]}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\VerdictOrderProgressTrainExamples}{12000}", rendered
        )
        self.assertIn(
            r"\newcommand{\VerdictOrderStrictCanonicalMinusAlternativeSeenCI}{[-1.00, 5.00]}",
            rendered,
        )
        self.assertIn(
            r"\newcommand{\VerdictOrderProgressAgreementUnseen}{88.0}", rendered
        )


if __name__ == "__main__":
    unittest.main()
