#!/usr/bin/env python3
"""Consolidate post-review experiment JSONs into paper-ready macros."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def metric(contrast: dict[str, Any], name: str = "rr") -> dict[str, Any]:
    return next(row for row in contrast["paired"] if row["metric"] == name)


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def ci(row: dict[str, Any]) -> str:
    lo, hi = row["cluster_bootstrap_95ci"]
    return f"[{100 * lo:.2f}, {100 * hi:.2f}]"


def interval(values: list[float]) -> str:
    lo, hi = values
    return f"[{100 * lo:.2f}, {100 * hi:.2f}]"


def members(values: list[str]) -> str:
    return "--".join(values)


def build(
    answer9: dict[str, Any],
    hidden: dict[str, Any],
    codeworkout: dict[str, Any],
    scale: dict[str, Any],
    problem_holdout: dict[str, Any],
    selection_stability: dict[str, Any],
    answer_selection_stability: dict[str, Any],
    problem_disjoint: dict[str, Any],
    answer_problem_disjoint: dict[str, Any],
    problem_disjoint_budget: dict[str, Any],
    patch_locality: dict[str, Any],
    normalized_ted: dict[str, Any],
    operational_cost: dict[str, Any],
    prompt_distribution: dict[str, Any],
    problem_crossfit: dict[str, Any],
    verdict_order: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "canonical": {},
        "hidden": hidden,
        "codeworkout_student": codeworkout,
        "scale_1_5b": scale,
        "codeworkout_problem": problem_holdout,
        "selection_stability": selection_stability,
        "answer_selection_stability": answer_selection_stability,
        "problem_disjoint_selection": problem_disjoint,
        "answer_problem_disjoint_selection": answer_problem_disjoint,
        "problem_disjoint_budget_fair_pools": problem_disjoint_budget,
        "patch_locality": patch_locality,
        "normalized_ted_frontier": normalized_ted,
        "operational_cost": operational_cost,
        "prompt_distribution": prompt_distribution,
        "problem_crossfit": problem_crossfit,
        "verdict_order_model_sensitivity": verdict_order,
    }
    for split in ("seen", "unseen"):
        row = answer9["splits"][split]
        rr = metric(row["zpdpatch_minus_answer_9choose3"])
        a3_minus_a1 = metric(row["answer_3seed_minus_answer_1"])
        a9_minus_a3 = metric(row["answer_9choose3_minus_answer_3seed"])
        budget = row["budget_indexed_zpdpatch_minus_answer_9choose3"][
            "mean_over_predeclared_budgets"
        ]
        result["canonical"][split] = {
            "mixed_rr": row["zpdpatch"]["rr"],
            "answer_rr": row["answer_9choose3"]["rr"],
            "answer_3seed_rr": row["answer_3seed"]["rr"],
            "answer_1_rr": row["answer_1"]["rr"],
            "answer_3seed_minus_answer_1": a3_minus_a1[
                "left_minus_right_instance_weighted"
            ],
            "answer_3seed_minus_answer_1_cluster_95ci": a3_minus_a1[
                "cluster_bootstrap_95ci"
            ],
            "answer_9choose3_minus_answer_3seed": a9_minus_a3[
                "left_minus_right_instance_weighted"
            ],
            "answer_9choose3_minus_answer_3seed_cluster_95ci": a9_minus_a3[
                "cluster_bootstrap_95ci"
            ],
            "rr_difference": rr["left_minus_right_instance_weighted"],
            "rr_cluster_95ci": rr["cluster_bootstrap_95ci"],
            "rr_mcnemar_p": row["zpdpatch_minus_answer_9choose3"][
                "exact_mcnemar_two_sided_p"
            ],
            "mean_budget_difference": budget["difference"],
            "mean_budget_cluster_95ci": budget["problem_cluster_95ci"],
        }
    return result


def macros(result: dict[str, Any]) -> str:
    values: dict[str, str] = {}
    for split, prefix in (("seen", "Seen"), ("unseen", "Unseen")):
        row = result["canonical"][split]
        values[f"AnswerNine{prefix}RR"] = pct(row["answer_rr"])
        values[f"AnswerThree{prefix}RR"] = pct(row["answer_3seed_rr"])
        values[f"AnswerOne{prefix}RR"] = pct(row["answer_1_rr"])
        values[f"AnswerThreeMinusOne{prefix}"] = pct(
            row["answer_3seed_minus_answer_1"]
        )
        values[f"AnswerThreeMinusOne{prefix}CI"] = interval(
            row["answer_3seed_minus_answer_1_cluster_95ci"]
        )
        values[f"AnswerNineMinusThree{prefix}"] = pct(
            row["answer_9choose3_minus_answer_3seed"]
        )
        values[f"AnswerNineMinusThree{prefix}CI"] = interval(
            row["answer_9choose3_minus_answer_3seed_cluster_95ci"]
        )
        values[f"Mixed{prefix}RR"] = pct(row["mixed_rr"])
        values[f"MixedMinusAnswerNine{prefix}"] = pct(row["rr_difference"])
        values[f"MixedMinusAnswerNine{prefix}CI"] = (
            f"[{100 * row['rr_cluster_95ci'][0]:.2f}, "
            f"{100 * row['rr_cluster_95ci'][1]:.2f}]"
        )
        values[f"MixedMinusAnswerNine{prefix}P"] = f"{row['rr_mcnemar_p']:.4g}"
        values[f"BudgetMixedMinusAnswerNine{prefix}"] = pct(
            row["mean_budget_difference"]
        )
        values[f"BudgetMixedMinusAnswerNine{prefix}CI"] = interval(
            row["mean_budget_cluster_95ci"]
        )
    stability = result["selection_stability"]
    disjoint = result["problem_disjoint_selection"]
    values["SelectionBootstrapFrequency"] = pct(
        stability["problem_bootstrap"]["full_selection_fraction"]
    )
    values["AnswerNineSelectionBootstrapFrequency"] = pct(
        result["answer_selection_stability"]["problem_bootstrap"][
            "full_selection_fraction"
        ]
    )
    values["ProblemDisjointValidationCount"] = str(
        disjoint["selection"]["validation_problems"]
    )
    values["ProblemDisjointSeenRR"] = pct(disjoint["summary"]["rr"])
    answer_disjoint = result["answer_problem_disjoint_selection"]
    values["ProblemDisjointAnswerNineRR"] = pct(answer_disjoint["summary"]["rr"])
    fair_pool_rr = metric(
        answer_disjoint["problem_disjoint_minus_references"][
            "Mixed-target-problem-disjoint"
        ]
    )
    values["ProblemDisjointMixedMinusAnswerNine"] = pct(
        -fair_pool_rr["left_minus_right_instance_weighted"]
    )
    values["ProblemDisjointMixedMinusAnswerNineCI"] = interval(
        [-value for value in reversed(fair_pool_rr["cluster_bootstrap_95ci"])]
    )
    disjoint_budget = result["problem_disjoint_budget_fair_pools"][
        "mixed_minus_answer"
    ]
    values["ProblemDisjointBudgetMixedMinusAnswerNine"] = pct(
        disjoint_budget["mean_over_predeclared_budgets"]["difference"]
    )
    values["ProblemDisjointBudgetMixedMinusAnswerNineCI"] = interval(
        disjoint_budget["mean_over_predeclared_budgets"]["problem_cluster_95ci"]
    )
    for budget in (10, 40):
        budget_row = disjoint_budget["per_budget"][str(budget)]
        values[f"ProblemDisjointTED{budget}MixedMinusAnswerNine"] = pct(
            budget_row["difference"]
        )
        values[f"ProblemDisjointTED{budget}MixedMinusAnswerNineCI"] = interval(
            budget_row["problem_cluster_95ci"]
        )
    locality = result["patch_locality"]["comparisons"]
    for comparison, prefix in (
        ("Progress_minus_Answer", "ProgressMinusAnswer"),
        ("Mixed9_minus_Answer9", "MixedMinusAnswerNine"),
    ):
        for locality_metric, suffix in (
            ("token_retention", "TokenRetention"),
            ("line_retention", "LineRetention"),
        ):
            values[f"{prefix}{suffix}"] = pct(
                locality[comparison]["metrics"][locality_metric]["left_minus_right"]
            )
            values[f"{prefix}{suffix}CI"] = interval(
                locality[comparison]["metrics"][locality_metric][
                    "problem_cluster_bootstrap_95ci"
                ]
            )

    hidden = result["hidden"]
    values["HiddenMixedJointRR"] = pct(
        hidden["methods"]["ZPDPatch"]["joint_repair_rate"]
    )
    values["HiddenAnswerNineJointRR"] = pct(
        hidden["methods"]["Answer-9Choose3"]["joint_repair_rate"]
    )
    values["HiddenMixedMinusAnswerNine"] = pct(
        hidden["comparison"]["left_minus_right"]
    )
    values["HiddenMixedMinusAnswerNineCI"] = interval(
        hidden["comparison"]["problem_cluster_95_ci"]
    )

    codeworkout = result["codeworkout_student"]
    codeworkout_rr = metric(codeworkout["zpdpatch_minus_answer_9choose3"])
    values["CodeWorkoutStudentMixedRR"] = pct(codeworkout["zpdpatch"]["rr"])
    values["CodeWorkoutStudentAnswerNineRR"] = pct(
        codeworkout["answer_9choose3"]["rr"]
    )
    values["CodeWorkoutStudentMixedMinusAnswerNine"] = pct(
        codeworkout_rr["left_minus_right_instance_weighted"]
    )
    values["CodeWorkoutStudentMixedMinusAnswerNineCI"] = ci(codeworkout_rr)
    values["CodeWorkoutStudentMixedMinusAnswerNineExerciseCI"] = ci(
        codeworkout_rr
    )
    values["CodeWorkoutStudentMixedMinusAnswerNineStudentCI"] = interval(
        codeworkout["zpdpatch_minus_answer_9choose3"]["student_cluster_rr_95ci"]
    )

    scale = result["scale_1_5b"]
    values["ScaleMixedMembers"] = members(scale["mixed_members"])
    values["ScaleAnswerNineMembers"] = members(scale["answer_members"])
    for split, prefix in (("seen", "Seen"), ("unseen", "Unseen")):
        row = scale["splits"][split]
        scale_rr = metric(row["mixed_minus_answer"])
        for method, method_prefix in (
            ("mixed_target_9choose3", "Mixed"),
            ("answer_9choose3", "AnswerNine"),
            ("answer_3seed", "AnswerThree"),
            ("answer_1", "AnswerOne"),
        ):
            for metric_name in ("pr", "rr", "ir"):
                values[f"Scale{method_prefix}{prefix}{metric_name.upper()}"] = pct(
                    row[method][metric_name]
                )
        scale_a3_a1 = metric(row["answer_3seed_minus_answer_1"])
        scale_a9_a3 = metric(row["answer_9choose3_minus_answer_3seed"])
        values[f"ScaleAnswerThreeMinusOne{prefix}"] = pct(
            scale_a3_a1["left_minus_right_instance_weighted"]
        )
        values[f"ScaleAnswerThreeMinusOne{prefix}CI"] = ci(scale_a3_a1)
        values[f"ScaleAnswerNineMinusThree{prefix}"] = pct(
            scale_a9_a3["left_minus_right_instance_weighted"]
        )
        values[f"ScaleAnswerNineMinusThree{prefix}CI"] = ci(scale_a9_a3)
        values[f"ScaleMixedMinusAnswerNine{prefix}"] = pct(
            scale_rr["left_minus_right_instance_weighted"]
        )
        values[f"ScaleMixedMinusAnswerNine{prefix}CI"] = ci(scale_rr)
        values[f"ScaleMixedMinusAnswerNine{prefix}P"] = (
            f"{row['mixed_minus_answer']['exact_mcnemar_two_sided_p']:.4g}"
        )
        scale_budget = row["budget_indexed_mixed_minus_answer"][
            "mean_over_predeclared_budgets"
        ]
        values[f"ScaleBudgetMixedMinusAnswerNine{prefix}"] = pct(
            scale_budget["difference"]
        )
        values[f"ScaleBudgetMixedMinusAnswerNine{prefix}CI"] = interval(
            scale_budget["problem_cluster_95ci"]
        )

    problem = result["codeworkout_problem"]
    values["CodeWorkoutProblemMixedMembers"] = members(problem["mixed_members"])
    values["CodeWorkoutProblemAnswerNineMembers"] = members(
        problem["answer_members"]
    )
    problem_rr = metric(problem["mixed_minus_answer"])
    for method, method_prefix in (
        ("mixed_target_9choose3", "Mixed"),
        ("answer_9choose3", "AnswerNine"),
        ("answer_3seed", "AnswerThree"),
        ("answer_1", "AnswerOne"),
    ):
        for metric_name in ("pr", "rr", "ir"):
            values[f"CodeWorkoutProblem{method_prefix}{metric_name.upper()}"] = pct(
                problem[method][metric_name]
            )
    problem_a3_a1 = metric(problem["answer_3seed_minus_answer_1"])
    problem_a9_a3 = metric(problem["answer_9choose3_minus_answer_3seed"])
    values["CodeWorkoutProblemAnswerThreeMinusOne"] = pct(
        problem_a3_a1["left_minus_right_instance_weighted"]
    )
    values["CodeWorkoutProblemAnswerThreeMinusOneCI"] = ci(problem_a3_a1)
    values["CodeWorkoutProblemAnswerNineMinusThree"] = pct(
        problem_a9_a3["left_minus_right_instance_weighted"]
    )
    values["CodeWorkoutProblemAnswerNineMinusThreeCI"] = ci(problem_a9_a3)
    values["CodeWorkoutProblemMixedMinusAnswerNine"] = pct(
        problem_rr["left_minus_right_instance_weighted"]
    )
    values["CodeWorkoutProblemMixedMinusAnswerNineCI"] = ci(problem_rr)
    values["CodeWorkoutProblemMixedMinusAnswerNineP"] = (
        f"{problem['mixed_minus_answer']['exact_mcnemar_two_sided_p']:.4g}"
    )
    values["CodeWorkoutProblemMixedMinusAnswerNineExerciseCI"] = ci(problem_rr)
    values["CodeWorkoutProblemMixedMinusAnswerNineStudentCI"] = interval(
        problem["mixed_minus_answer"]["student_cluster_rr_95ci"]
    )
    normalized = result["normalized_ted_frontier"]
    values["NormalizedTEDExamples"] = str(normalized["examples_parseable_current"])
    values["NormalizedTEDExcluded"] = str(
        normalized["examples_excluded_unparseable_current"]
    )
    ast_distribution = normalized["current_ast_node_distribution"]
    values["CurrentASTNodesMedian"] = f"{ast_distribution['median']:.0f}"
    values["CurrentASTNodesPFirst"] = f"{ast_distribution['p25']:.0f}"
    values["CurrentASTNodesPThird"] = f"{ast_distribution['p75']:.0f}"
    for budget in (5, 10, 20, 40):
        context = normalized["absolute_budget_context"][str(budget)]
        values[f"TED{budget}MedianASTFraction"] = pct(
            context["fraction_of_current_ast_median"]
        )
        values[f"TED{budget}AtMostTenPercentInputs"] = pct(
            context["fraction_where_budget_is_at_most_10pct"]
        )
    for budget, suffix in (("0.1", "Ten"), ("0.2", "Twenty"), ("0.4", "Forty")):
        row = normalized["per_budget"][budget]
        values[f"NormalizedTED{suffix}MixedMinusAnswerNine"] = pct(
            row["mixed_minus_answer"]
        )
        values[f"NormalizedTED{suffix}MixedMinusAnswerNineCI"] = interval(
            row["problem_cluster_95ci"]
        )
    for name in ("A1", "A3", "A9", "M9"):
        row = result["operational_cost"]["mechanism_ladder_seen"][name]
        values[f"Cost{name}TrainHours"] = f"{row['train_gpu_hours']:.1f}"
        values[f"Cost{name}ValidationExecutions"] = str(
            row["portfolio_selection_validation_executions"]
        )
        values[f"Cost{name}SeenRR"] = pct(row["repair_rate"])
        values[f"Cost{name}MeanCalls"] = f"{row['mean_candidates_invoked']:.2f}"

    prompt = result["prompt_distribution"]
    values["PromptCurrentMixedMembers"] = members(
        prompt["current_only_mixed_members"]
    )
    values["PromptCurrentAnswerNineMembers"] = members(
        prompt["current_only_answer_members"]
    )
    for split, prefix in (("seen", "Seen"), ("unseen", "Unseen")):
        row = prompt["splits"][split]
        reselected = row["current_only_reselected"]
        reselected_rr = metric(reselected["mixed_minus_answer"])
        values[f"PromptCurrentMixed{prefix}RR"] = pct(
            reselected["mixed_target_9choose3"]["rr"]
        )
        values[f"PromptCurrentAnswerNine{prefix}RR"] = pct(
            reselected["answer_9choose3"]["rr"]
        )
        values[f"PromptCurrentMixedMinusAnswerNine{prefix}"] = pct(
            reselected_rr["left_minus_right_instance_weighted"]
        )
        values[f"PromptCurrentMixedMinusAnswerNine{prefix}CI"] = ci(
            reselected_rr
        )
        effects = row["full_history_selected_members"]["prompt_context_effect"]
        for method, method_prefix in (("mixed", "Mixed"), ("answer", "AnswerNine")):
            effect = metric(
                effects[f"{method}_current_only_minus_full_history"]
            )
            values[f"PromptFrozen{method_prefix}CurrentMinusFull{prefix}"] = pct(
                effect["left_minus_right_instance_weighted"]
            )
            values[f"PromptFrozen{method_prefix}CurrentMinusFull{prefix}CI"] = ci(
                effect
            )

    crossfit = result["problem_crossfit"]
    crossfit_rr = metric(crossfit["mixed_minus_answer"])
    values["CrossFitFolds"] = str(crossfit["folds"])
    values["CrossFitMixedSeenRR"] = pct(crossfit["mixed"]["rr"])
    values["CrossFitAnswerNineSeenRR"] = pct(crossfit["answer"]["rr"])
    values["CrossFitMixedMinusAnswerNineSeen"] = pct(
        crossfit_rr["left_minus_right_instance_weighted"]
    )
    values["CrossFitMixedMinusAnswerNineSeenCI"] = ci(crossfit_rr)
    values["CrossFitMixedMinusAnswerNineSeenP"] = (
        f"{crossfit['mixed_minus_answer']['exact_mcnemar_two_sided_p']:.4g}"
    )
    crossfit_budget = crossfit["budget"]["mixed_minus_answer"]
    values["CrossFitBudgetMixedMinusAnswerNineSeen"] = pct(
        crossfit_budget["mean_over_predeclared_budgets"]["difference"]
    )
    values["CrossFitBudgetMixedMinusAnswerNineSeenCI"] = interval(
        crossfit_budget["mean_over_predeclared_budgets"]["problem_cluster_95ci"]
    )
    for budget in (10, 40):
        budget_row = crossfit_budget["per_budget"][str(budget)]
        values[f"CrossFitTED{budget}MixedMinusAnswerNineSeen"] = pct(
            budget_row["difference"]
        )
        values[f"CrossFitTED{budget}MixedMinusAnswerNineSeenCI"] = interval(
            budget_row["problem_cluster_95ci"]
        )

    verdict = result["verdict_order_model_sensitivity"]
    for relation, relation_prefix in (("progress", "Progress"), ("strict", "Strict")):
        values[f"VerdictOrder{relation_prefix}TrainExamples"] = str(
            verdict["dataset_summaries"][f"train-{relation}"]["written_examples"]
        )
        for split, split_prefix in (("seen", "Seen"), ("unseen", "Unseen")):
            row = verdict["relations"][relation]["splits"][split]
            effect = metric(row["canonical_minus_alternative"])
            values[f"VerdictOrder{relation_prefix}Canonical{split_prefix}RR"] = pct(
                row["canonical"]["rr"]
            )
            values[f"VerdictOrder{relation_prefix}Alternative{split_prefix}RR"] = pct(
                row["alternative"]["rr"]
            )
            values[f"VerdictOrder{relation_prefix}CanonicalMinusAlternative{split_prefix}"] = pct(
                effect["left_minus_right_instance_weighted"]
            )
            values[f"VerdictOrder{relation_prefix}CanonicalMinusAlternative{split_prefix}CI"] = ci(
                effect
            )
            values[f"VerdictOrder{relation_prefix}Agreement{split_prefix}"] = pct(
                row["repair_agreement"]["decision_agreement"]
            )
    return "".join(
        f"\\newcommand{{\\{name}}}{{{value}}}\n" for name, value in sorted(values.items())
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--hidden", type=Path, required=True)
    parser.add_argument("--codeworkout", type=Path, required=True)
    parser.add_argument("--scale", type=Path, required=True)
    parser.add_argument("--problem-holdout", type=Path, required=True)
    parser.add_argument("--selection-stability", type=Path, required=True)
    parser.add_argument("--answer-selection-stability", type=Path, required=True)
    parser.add_argument("--problem-disjoint", type=Path, required=True)
    parser.add_argument("--answer-problem-disjoint", type=Path, required=True)
    parser.add_argument("--problem-disjoint-budget", type=Path, required=True)
    parser.add_argument("--patch-locality", type=Path, required=True)
    parser.add_argument("--normalized-ted", type=Path, required=True)
    parser.add_argument("--operational-cost", type=Path, required=True)
    parser.add_argument("--prompt-distribution", type=Path, required=True)
    parser.add_argument("--problem-crossfit", type=Path, required=True)
    parser.add_argument("--verdict-order", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-tex", type=Path, required=True)
    args = parser.parse_args()
    result = build(
        read(args.answer9),
        read(args.hidden),
        read(args.codeworkout),
        read(args.scale),
        read(args.problem_holdout),
        read(args.selection_stability),
        read(args.answer_selection_stability),
        read(args.problem_disjoint),
        read(args.answer_problem_disjoint),
        read(args.problem_disjoint_budget),
        read(args.patch_locality),
        read(args.normalized_ted),
        read(args.operational_cost),
        read(args.prompt_distribution),
        read(args.problem_crossfit),
        read(args.verdict_order),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_tex.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.output_tex.write_text(macros(result), encoding="utf-8")


if __name__ == "__main__":
    main()
