#!/usr/bin/env python3
"""Exactly select a relation-constrained portfolio on validation execution."""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any


Row = dict[str, Any]
BUDGETS = (5, 10, 20, 40, 80, 160)


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def keyed(rows: list[Row]) -> dict[str, Row]:
    result = {str(row["example_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate example_id")
    return result


def portfolio_score(candidates: list[dict[str, Row]]) -> dict[str, Any]:
    example_ids = sorted(candidates[0])
    if any(set(candidate) != set(example_ids) for candidate in candidates[1:]):
        raise ValueError("candidate evaluations do not cover identical examples")
    repaired = 0
    improved = 0
    pass_rate_sum = 0.0
    repair_ted_sum = 0.0
    repair_ted_count = 0
    budget_repairs = {budget: 0 for budget in BUDGETS}
    for example_id in example_ids:
        rows = [candidate[example_id] for candidate in candidates]
        baseline_value = rows[0].get("buggy_pass_rate", rows[0].get("current_pass_rate"))
        if baseline_value is None:
            raise ValueError("candidate evaluation lacks current/buggy pass rate")
        baseline = float(baseline_value)
        repaired_rows = [row for row in rows if bool(row["repaired"])]
        repaired += bool(repaired_rows)
        best_pass_rate = max([baseline] + [float(row["fixed_pass_rate"]) for row in rows])
        pass_rate_sum += best_pass_rate
        improved += best_pass_rate > baseline
        if repaired_rows:
            teds = [
                float(row["ted_buggy_fixed"])
                for row in repaired_rows
                if row.get("ted_buggy_fixed") is not None
            ]
            if teds:
                repair_ted_sum += min(teds)
                repair_ted_count += 1
                minimum_ted = min(teds)
                for budget in BUDGETS:
                    budget_repairs[budget] += minimum_ted <= budget
    n = len(example_ids)
    return {
        "examples": n,
        "repaired": repaired,
        "repair_rate": repaired / n,
        "pass_rate": pass_rate_sum / n,
        "improved": improved,
        "improvement_rate": improved / n,
        "mean_min_ted_on_repaired": (
            repair_ted_sum / repair_ted_count if repair_ted_count else None
        ),
        "repaired_with_ted": repair_ted_count,
        "repair_rate_by_max_ted": {
            str(budget): budget_repairs[budget] / n for budget in BUDGETS
        },
        "mean_budgeted_repair_rate": sum(budget_repairs.values())
        / (n * len(BUDGETS)),
    }


def objective(score: dict[str, Any], names: tuple[str, ...]) -> tuple[Any, ...]:
    return (
        score["repaired"],
        score["pass_rate"],
        score["improved"],
        tuple(-sum(ord(char) for char in name) for name in names),
    )


def budget_objective(score: dict[str, Any], names: tuple[str, ...]) -> tuple[Any, ...]:
    return (
        sum(
            score["repair_rate_by_max_ted"][str(budget)] for budget in BUDGETS
        ),
        score["repaired"],
        score["pass_rate"],
        score["improved"],
        tuple(-sum(ord(char) for char in name) for name in names),
    )


def single_budget_objective(
    score: dict[str, Any], names: tuple[str, ...], budget: int
) -> tuple[Any, ...]:
    return (
        score["repair_rate_by_max_ted"][str(budget)],
        score["repaired"],
        score["pass_rate"],
        score["improved"],
        tuple(-sum(ord(char) for char in name) for name in names),
    )


def select_portfolios(
    evaluations: dict[str, list[Row]],
    relations: dict[str, str],
    *,
    include_budget_objective: bool = True,
) -> dict[str, Any]:
    maps = {name: keyed(rows) for name, rows in evaluations.items()}
    relation_names = sorted(set(relations.values()))
    if relation_names != ["Answer", "Progress", "Strict"]:
        raise ValueError("Answer, Progress, and Strict candidates are required")
    by_relation = {
        relation: sorted(name for name, value in relations.items() if value == relation)
        for relation in relation_names
    }
    if any(len(names) != 3 for names in by_relation.values()):
        raise ValueError("exactly three candidates are required per relation")

    feasible = []
    for names in itertools.product(*(by_relation[relation] for relation in relation_names)):
        score = portfolio_score([maps[name] for name in names])
        feasible.append({"members": list(names), "score": score})
    selected = max(
        feasible,
        key=lambda item: objective(item["score"], tuple(item["members"])),
    )
    selected_budget_aware = (
        max(
            feasible,
            key=lambda item: budget_objective(
                item["score"], tuple(item["members"])
            ),
        )
        if include_budget_objective
        else None
    )

    unconstrained = []
    for names in itertools.combinations(sorted(maps), 3):
        score = portfolio_score([maps[name] for name in names])
        unconstrained.append({"members": list(names), "score": score})
    best_unconstrained = max(
        unconstrained,
        key=lambda item: objective(item["score"], tuple(item["members"])),
    )
    answer_names = tuple(by_relation["Answer"])
    answer_control = {
        "members": list(answer_names),
        "score": portfolio_score([maps[name] for name in answer_names]),
    }
    selected_relation_by_budget = (
        {
            str(budget): max(
                feasible,
                key=lambda item: single_budget_objective(
                    item["score"], tuple(item["members"]), budget
                ),
            )
            for budget in BUDGETS
        }
        if include_budget_objective
        else None
    )
    selected_unconstrained_by_budget = (
        {
            str(budget): max(
                unconstrained,
                key=lambda item: single_budget_objective(
                    item["score"], tuple(item["members"]), budget
                ),
            )
            for budget in BUDGETS
        }
        if include_budget_objective
        else None
    )
    return {
        "selection_partition": "training validation split",
        "test_outcomes_used": False,
        "primary_objective": "repair coverage",
        "budget_aware_objective": (
            "mean repair coverage at predeclared AST TED budgets 5,10,20,40,80,160"
            if include_budget_objective
            else None
        ),
        "tie_breakers": [
            "pass rate",
            "improvement coverage",
            "deterministic candidate-name order",
        ],
        "constraint": "exactly one checkpoint from each relation",
        "feasible_relation_constrained_portfolios": len(feasible),
        "feasible_unconstrained_size_three_portfolios": len(unconstrained),
        "selected_relation_constrained": selected,
        "selected_budget_aware_relation_constrained": selected_budget_aware,
        "selected_relation_constrained_by_budget": selected_relation_by_budget,
        "best_unconstrained": best_unconstrained,
        "selected_unconstrained_by_budget": selected_unconstrained_by_budget,
        "answer_3seed_control": answer_control,
        "all_relation_constrained": sorted(
            feasible,
            key=lambda item: objective(item["score"], tuple(item["members"])),
            reverse=True,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation", action="append", required=True, help="NAME:RELATION=PATH"
    )
    parser.add_argument(
        "--skip-budget-objective",
        action="store_true",
        help="Do not define AST-TED budget selection (for non-Python external data).",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluations = {}
    relations = {}
    for raw in args.evaluation:
        try:
            name_relation, raw_path = raw.split("=", 1)
            name, relation = name_relation.split(":", 1)
        except ValueError:
            parser.error("--evaluation must use NAME:RELATION=PATH")
        evaluations[name] = read_jsonl(Path(raw_path))
        relations[name] = relation
    report = select_portfolios(
        evaluations,
        relations,
        include_budget_objective=not args.skip_budget_objective,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["selected_relation_constrained"], sort_keys=True))


if __name__ == "__main__":
    main()
