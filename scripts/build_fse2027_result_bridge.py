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


def build(
    answer9: dict[str, Any],
    hidden: dict[str, Any],
    codeworkout: dict[str, Any],
    scale: dict[str, Any],
    problem_holdout: dict[str, Any],
    selection_stability: dict[str, Any],
    answer_selection_stability: dict[str, Any],
    problem_disjoint: dict[str, Any],
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
    }
    for split in ("seen", "unseen"):
        row = answer9["splits"][split]
        rr = metric(row["zpdpatch_minus_answer_9choose3"])
        budget = row["budget_indexed_zpdpatch_minus_answer_9choose3"][
            "mean_over_predeclared_budgets"
        ]
        result["canonical"][split] = {
            "mixed_rr": row["zpdpatch"]["rr"],
            "answer_rr": row["answer_9choose3"]["rr"],
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

    codeworkout = result["codeworkout_student"]
    codeworkout_rr = metric(codeworkout["zpdpatch_minus_answer_9choose3"])
    values["CodeWorkoutStudentMixedRR"] = pct(codeworkout["zpdpatch"]["rr"])
    values["CodeWorkoutStudentAnswerNineRR"] = pct(
        codeworkout["answer_9choose3"]["rr"]
    )
    values["CodeWorkoutStudentMixedMinusAnswerNine"] = pct(
        codeworkout_rr["left_minus_right_instance_weighted"]
    )

    scale = result["scale_1_5b"]
    for split, prefix in (("seen", "Seen"), ("unseen", "Unseen")):
        row = scale["splits"][split]
        scale_rr = metric(row["mixed_minus_answer"])
        values[f"ScaleMixed{prefix}RR"] = pct(row["mixed_target_9choose3"]["rr"])
        values[f"ScaleAnswerNine{prefix}RR"] = pct(row["answer_9choose3"]["rr"])
        values[f"ScaleMixedMinusAnswerNine{prefix}"] = pct(
            scale_rr["left_minus_right_instance_weighted"]
        )

    problem = result["codeworkout_problem"]
    problem_rr = metric(problem["mixed_minus_answer"])
    values["CodeWorkoutProblemMixedRR"] = pct(problem["mixed_target_9choose3"]["rr"])
    values["CodeWorkoutProblemAnswerNineRR"] = pct(problem["answer_9choose3"]["rr"])
    values["CodeWorkoutProblemMixedMinusAnswerNine"] = pct(
        problem_rr["left_minus_right_instance_weighted"]
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
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_tex.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.output_tex.write_text(macros(result), encoding="utf-8")


if __name__ == "__main__":
    main()
