#!/usr/bin/env python3
"""Analyze validation-selected execution portfolios on held-out test data."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from analyze_fse2027_patch_budget import (
    clustered_difference,
    keyed,
    percentile,
)
from analyze_fse2027_robustness import paired_suite_rows, read_jsonl


BUDGETS = (5, 10, 20, 40, 80, 160)


def holm_adjust(values: dict[str, float]) -> dict[str, dict[str, float]]:
    ordered = sorted(values, key=lambda name: values[name])
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    for rank, name in enumerate(ordered):
        running = max(running, min(1.0, (total - rank) * values[name]))
        adjusted[name] = running
    return {
        name: {"raw_p": values[name], "holm_adjusted_p": adjusted[name]}
        for name in values
    }


def assert_same_answer_control(
    reproduced: list[dict[str, Any]], legacy: list[dict[str, Any]]
) -> dict[str, Any]:
    reproduced_by_id = keyed(reproduced)
    legacy_by_id = keyed(legacy)
    if set(reproduced_by_id) != set(legacy_by_id):
        raise ValueError("reproduced and legacy Answer-3Seed controls differ in coverage")
    mismatches = []
    for example_id, row in reproduced_by_id.items():
        peer = legacy_by_id[example_id]
        if (
            bool(row["repaired"]) != bool(peer["repaired"])
            or bool(row["improved"]) != bool(peer["improved"])
            or abs(float(row["fixed_pass_rate"]) - float(peer["fixed_pass_rate"]))
            > 1e-12
        ):
            mismatches.append(example_id)
    if mismatches:
        raise ValueError(
            f"reproduced Answer-3Seed differs on {len(mismatches)} outcomes"
        )
    return {
        "examples": len(reproduced),
        "outcome_mismatches": 0,
        "fields": ["repaired", "improved", "fixed_pass_rate"],
    }


def budget_contrast(
    left: dict[int, list[dict[str, Any]]],
    right: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    return {
        str(budget): {
            "difference": (
                sum(bool(row["repaired"]) for row in left[budget])
                - sum(bool(row["repaired"]) for row in right[budget])
            )
            / len(left[budget]),
            "problem_cluster_95ci": clustered_difference(
                left[budget],
                right[budget],
                budget,
                samples=10_000,
                seed=2027 + budget,
            ),
        }
        for budget in BUDGETS
    }


def clustered_mean_budget_difference(
    left: dict[int, list[dict[str, Any]]],
    right: dict[int, list[dict[str, Any]]],
    *,
    samples: int = 10_000,
    seed: int = 2027,
) -> dict[str, Any]:
    """Paired difference for the complete, predeclared budget-coverage curve."""
    left_maps = {budget: keyed(left[budget]) for budget in BUDGETS}
    right_maps = {budget: keyed(right[budget]) for budget in BUDGETS}
    example_ids = set(left_maps[BUDGETS[0]])
    if any(
        set(rows) != example_ids
        for rows in (*left_maps.values(), *right_maps.values())
    ):
        raise ValueError("budgeted portfolio evaluations do not cover identical examples")
    by_problem: dict[str, list[float]] = defaultdict(list)
    for example_id in sorted(example_ids):
        reference = left_maps[BUDGETS[0]][example_id]
        by_problem[str(reference["problem_id"])].append(
            sum(
                float(bool(left_maps[budget][example_id]["repaired"]))
                - float(bool(right_maps[budget][example_id]["repaired"]))
                for budget in BUDGETS
            )
            / len(BUDGETS)
        )
    problems = sorted(by_problem)
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        selected = [rng.choice(problems) for _ in problems]
        values = [value for problem in selected for value in by_problem[problem]]
        draws.append(sum(values) / len(values))
    observed = sum(value for values in by_problem.values() for value in values) / len(
        example_ids
    )
    return {
        "difference": observed,
        "problem_cluster_95ci": [
            percentile(draws, 0.025),
            percentile(draws, 0.975),
        ],
        "budgets": list(BUDGETS),
        "bootstrap_samples": samples,
        "bootstrap_seed": seed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "selection_partition": "Seen validation, one trajectory per problem",
        "test_outcomes_used_for_selection": False,
        "unrestricted_members": selection["selected_relation_constrained"]["members"],
        "budget_aware_members": selection[
            "selected_budget_aware_relation_constrained"
        ]["members"],
        "unconstrained_members": selection["best_unconstrained"]["members"],
        "budget_indexed_relation_members": {
            budget: row["members"]
            for budget, row in selection[
                "selected_relation_constrained_by_budget"
            ].items()
        },
        "budget_indexed_unconstrained_members": {
            budget: row["members"]
            for budget, row in selection[
                "selected_unconstrained_by_budget"
            ].items()
        },
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        answer = read_jsonl(
            args.eval_root
            / "selected-portfolios"
            / f"answer-3seed-{split}-test.evaluation.jsonl"
        )
        legacy_answer = read_jsonl(
            args.eval_root
            / "answer-seed-control"
            / f"answer-seeds-{split}-test.evaluation.jsonl"
        )
        answer_budget = {
            budget: read_jsonl(
                args.eval_root
                / "selected-portfolios"
                / f"answer-3seed-{split}-test.max-ted-{budget}.evaluation.jsonl"
            )
            for budget in BUDGETS
        }
        split_result = {
            "answer_3seed_reproduction": assert_same_answer_control(
                answer, legacy_answer
            )
        }
        budget_indexed_rows = {
            controller: {
                budget: read_jsonl(
                    args.eval_root
                    / "selected-portfolios"
                    / f"budget-indexed-{controller}-{split}-test.max-ted-{budget}.evaluation.jsonl"
                )
                for budget in BUDGETS
            }
            for controller in ("relation", "unconstrained")
        }
        split_result["budget_indexed"] = {
            controller: {
                "members_by_budget": result[
                    f"budget_indexed_{controller}_members"
                ],
                "budget_contrast_vs_answer_3seed": {
                    "per_budget": budget_contrast(rows, answer_budget),
                    "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                        rows,
                        answer_budget,
                        seed=2027 + offset * 100 + (20 if controller == "relation" else 21),
                    ),
                },
            }
            for controller, rows in budget_indexed_rows.items()
        }
        split_result["budget_indexed"]["relation_vs_unconstrained"] = {
            "per_budget": budget_contrast(
                budget_indexed_rows["relation"],
                budget_indexed_rows["unconstrained"],
            ),
            "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                budget_indexed_rows["relation"],
                budget_indexed_rows["unconstrained"],
                seed=2027 + offset * 100 + 22,
            ),
        }
        rows_by_kind = {}
        for kind in ("unrestricted", "budget-aware", "unconstrained"):
            rows = read_jsonl(
                args.eval_root
                / "selected-portfolios"
                / f"{kind}-{split}-test.evaluation.jsonl"
            )
            rows_by_kind[kind] = rows
            budget_rows = {
                budget: read_jsonl(
                    args.eval_root
                    / "selected-portfolios"
                    / f"{kind}-{split}-test.max-ted-{budget}.evaluation.jsonl"
                )
                for budget in BUDGETS
            }
            paired = paired_suite_rows(
                rows,
                answer,
                left_label=f"validation-selected-{kind}",
                right_label="Answer-3Seed",
                samples=10_000,
                seed=2027 + offset * 100,
            )
            paired["budget_contrast_vs_answer_3seed"] = {
                "per_budget": budget_contrast(budget_rows, answer_budget),
                "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                    budget_rows,
                    answer_budget,
                    seed=2027
                    + offset * 100
                    + {"unrestricted": 0, "budget-aware": 1, "unconstrained": 2}[
                        kind
                    ],
                ),
            }
            split_result[kind] = paired
            rows_by_kind[f"{kind}-budget"] = budget_rows
        primary_rows = rows_by_kind["unconstrained"]
        zero_shot = read_jsonl(args.eval_root / f"zero-shot-{split}-test.evaluation.jsonl")
        primary_comparisons = {
            "zero_shot": paired_suite_rows(
                primary_rows,
                zero_shot,
                left_label="validation-selected-unconstrained",
                right_label="Zero-shot",
                samples=10_000,
                seed=3027 + offset * 100,
            )
        }
        if split == "seen":
            primary_comparisons["legacy_lsgen"] = paired_suite_rows(
                primary_rows,
                read_jsonl(args.eval_root / "lsgen-seen-test.evaluation.jsonl"),
                left_label="validation-selected-unconstrained",
                right_label="LSGen-legacy-controller",
                samples=10_000,
                seed=3028,
            )
        split_result["primary_method"] = {
            "selection": "validation-selected unconstrained size-three portfolio",
            "members": result["unconstrained_members"],
            "test_outcomes_used_for_selection": False,
            "summary": split_result["unconstrained"]["left_summary"],
            "comparisons": primary_comparisons,
        }
        direct_constraints = {}
        for direct_offset, left_kind in enumerate(
            ("unrestricted", "budget-aware"), start=10
        ):
            left = rows_by_kind[left_kind]
            right = rows_by_kind["unconstrained"]
            left_budget = rows_by_kind[f"{left_kind}-budget"]
            right_budget = rows_by_kind["unconstrained-budget"]
            direct = paired_suite_rows(
                left,
                right,
                left_label=f"validation-selected-{left_kind}",
                right_label="validation-selected-unconstrained",
                samples=10_000,
                seed=2027 + offset * 100 + direct_offset,
            )
            direct["budget_contrast"] = {
                "per_budget": budget_contrast(left_budget, right_budget),
                "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                    left_budget,
                    right_budget,
                    seed=2027 + offset * 100 + direct_offset,
                ),
            }
            direct_constraints[f"{left_kind}_vs_unconstrained"] = direct
        split_result["direct_constraint_effects"] = direct_constraints
        planned_p = {
            f"{kind}_vs_answer_3seed": float(
                split_result[kind]["exact_mcnemar_two_sided_p"]
            )
            for kind in ("unrestricted", "budget-aware", "unconstrained")
        }
        planned_p.update(
            {
                name: float(report["exact_mcnemar_two_sided_p"])
                for name, report in direct_constraints.items()
            }
        )
        split_result["planned_rr_family_holm"] = holm_adjust(planned_p)
        result["splits"][split] = split_result
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["splits"]["seen"], sort_keys=True))


if __name__ == "__main__":
    main()
