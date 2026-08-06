#!/usr/bin/env python3
"""Replay the declared per-candidate TED controller over always-three LSGen outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_fse2027_patch_budget import clustered_difference, keyed
from analyze_fse2027_selected_portfolios import (
    BUDGETS,
    clustered_mean_budget_difference,
)


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def choose_budgeted(row: Row, budget: int) -> Row:
    baseline = float(row["buggy_pass_rate"])
    eligible = [
        patch
        for patch in row["patches"]
        if patch.get("ted_buggy_fixed") is not None
        and float(patch["ted_buggy_fixed"]) <= budget
    ]
    accepted = [
        patch for patch in eligible if float(patch["fixed_pass_rate"]) == 1.0
    ]
    if accepted:
        selected = accepted[0]
    elif eligible:
        selected = max(
            eligible,
            key=lambda patch: (
                float(patch["fixed_pass_rate"]),
                -float(patch["ted_buggy_fixed"]),
                -int(patch["patch_index"]),
            ),
        )
        if float(selected["fixed_pass_rate"]) <= baseline:
            selected = None
    else:
        selected = None
    fixed_pass_rate = baseline if selected is None else float(selected["fixed_pass_rate"])
    repaired = selected is not None and fixed_pass_rate == 1.0
    return {
        "example_id": row["example_id"],
        "problem_id": row["problem_id"],
        "user_id": row["user_id"],
        "method": f"LSGen-Always3-TED-{budget}",
        "buggy_pass_rate": baseline,
        "fixed_pass_rate": fixed_pass_rate,
        "repaired": repaired,
        "improved": fixed_pass_rate > baseline,
        "ted_buggy_fixed": None if selected is None else selected["ted_buggy_fixed"],
        "selected_source": (
            "current-fallback" if selected is None else selected["source"]
        ),
        "max_ted": budget,
        "candidate_count": len(row["patches"]),
        "budget_eligible_candidate_count": len(eligible),
    }


def summarize(rows: list[Row]) -> Row:
    return {
        "examples": len(rows),
        "repair_rate": sum(bool(row["repaired"]) for row in rows) / len(rows),
        "pass_rate": sum(float(row["fixed_pass_rate"]) for row in rows) / len(rows),
        "improvement_rate": sum(bool(row["improved"]) for row in rows) / len(rows),
    }


def assert_unrestricted_reproduction(always_three: list[Row], legacy: list[Row]) -> Row:
    always_by_id = keyed(always_three)
    legacy_by_id = keyed(legacy)
    if set(always_by_id) != set(legacy_by_id):
        raise ValueError("always-three and legacy LSGen cover different examples")
    repair_mismatches = [
        example_id
        for example_id, row in always_by_id.items()
        if bool(row["repaired"]) != bool(legacy_by_id[example_id]["repaired"])
    ]
    pass_rate_mismatches = [
        example_id
        for example_id, row in always_by_id.items()
        if abs(
            float(row["fixed_pass_rate"])
            - float(legacy_by_id[example_id]["fixed_pass_rate"])
        )
        > 1e-12
    ]
    if repair_mismatches:
        raise ValueError(
            "always-three LSGen fails unrestricted RR reproduction on "
            f"{len(repair_mismatches)} examples"
        )
    return {
        "examples": len(always_three),
        "repair_outcome_mismatches": 0,
        "partial_pass_rate_mismatches_from_nonregressive_fallback": len(
            pass_rate_mismatches
        ),
    }


def write_jsonl(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--always-three", type=Path, required=True)
    parser.add_argument("--legacy", type=Path, required=True)
    parser.add_argument("--selected-root", type=Path, required=True)
    parser.add_argument("--budget-output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    always_three = read_jsonl(args.always_three)
    legacy = read_jsonl(args.legacy)
    if any(
        row.get("always_generate_max") is not True or len(row.get("patches", [])) != 3
        for row in always_three
    ):
        raise ValueError("LSGen budget replay requires exactly three stored candidates per example")
    reproduction = assert_unrestricted_reproduction(always_three, legacy)
    lsgen_budget = {
        budget: [choose_budgeted(row, budget) for row in always_three]
        for budget in BUDGETS
    }
    selected_budget = {
        "budget_agnostic_relation": {
            budget: read_jsonl(
                args.selected_root
                / f"budget-aware-seen-test.max-ted-{budget}.evaluation.jsonl"
            )
            for budget in BUDGETS
        },
        "budget_indexed_relation": {
            budget: read_jsonl(
                args.selected_root
                / f"budget-indexed-relation-seen-test.max-ted-{budget}.evaluation.jsonl"
            )
            for budget in BUDGETS
        },
        "budget_indexed_unconstrained": {
            budget: read_jsonl(
                args.selected_root
                / f"budget-indexed-unconstrained-seen-test.max-ted-{budget}.evaluation.jsonl"
            )
            for budget in BUDGETS
        },
    }
    for budget, rows in lsgen_budget.items():
        write_jsonl(
            args.budget_output_root
            / f"lsgen-seen-test.max-ted-{budget}.evaluation.jsonl",
            rows,
        )
    per_budget = {}
    for budget in BUDGETS:
        entry = {"lsgen": summarize(lsgen_budget[budget])}
        for method_index, (method, rows_by_budget) in enumerate(
            selected_budget.items()
        ):
            selected_rows = rows_by_budget[budget]
            entry[method] = summarize(selected_rows)
            entry[f"{method}_minus_lsgen"] = {
                "rr_difference": (
                    sum(bool(row["repaired"]) for row in selected_rows)
                    - sum(bool(row["repaired"]) for row in lsgen_budget[budget])
                )
                / len(always_three),
                "problem_cluster_95ci": clustered_difference(
                    selected_rows,
                    lsgen_budget[budget],
                    budget,
                    samples=10_000,
                    seed=4040 + budget + 100 * method_index,
                ),
            }
        per_budget[str(budget)] = entry
    report = {
        "dataset": "canonical-v5 Seen test",
        "examples": len(always_three),
        "test_outcomes_used_for_portfolio_selection": False,
        "lsgen_generation_budget": 3,
        "lsgen_budget_replay": "continue after over-budget acceptance; first budget-eligible acceptance; non-regressive fallback",
        "unrestricted_reproduction": reproduction,
        "per_budget": per_budget,
        "mean_over_predeclared_budgets": {
            method: clustered_mean_budget_difference(
                rows_by_budget, lsgen_budget, seed=6067 + method_index
            )
            for method_index, (method, rows_by_budget) in enumerate(
                selected_budget.items()
            )
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
