#!/usr/bin/env python3
"""Compare matched budget-indexed pools selected without test-problem overlap."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_fse2027_robustness import read_jsonl, summarize_method
from analyze_fse2027_selected_portfolios import (
    BUDGETS,
    budget_contrast,
    clustered_mean_budget_difference,
)
from compose_answer_seed_control import compose


Row = dict[str, Any]


def relation_order(name: str) -> tuple[int, str]:
    for index, prefix in enumerate(("Progress", "Strict", "Answer")):
        if name.startswith(prefix):
            return index, name
    raise ValueError(f"unknown relation: {name}")


def parse_members(values: list[str]) -> dict[str, list[Row]]:
    result = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("member must use NAME=PATH")
        name, path = raw.split("=", 1)
        result[name] = read_jsonl(Path(path))
    return result


def write_rows(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row) + "\n")


def analyze(
    selection: dict[str, Any],
    mixed_members: dict[str, list[Row]],
    answer_members: dict[str, list[Row]],
    *,
    output_root: Path,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    mixed_rows: dict[int, list[Row]] = {}
    answer_rows: dict[int, list[Row]] = {}
    selected = {"mixed": {}, "answer": {}}
    for budget in BUDGETS:
        key = str(budget)
        mixed_names = selection["mixed"]["selected_unconstrained_by_budget"][key][
            "members"
        ]
        answer_names = selection["answer"]["selected_by_budget"][key]["members"]
        if any(name not in mixed_members for name in mixed_names):
            raise ValueError(f"missing mixed member for TED {budget}")
        if any(name not in answer_members for name in answer_names):
            raise ValueError(f"missing Answer member for TED {budget}")
        mixed_stages = [
            (name, mixed_members[name]) for name in sorted(mixed_names, key=relation_order)
        ]
        answer_stages = [(name, answer_members[name]) for name in sorted(answer_names)]
        mixed_rows[budget] = compose(
            mixed_stages[0][1], mixed_stages, max_ted=float(budget)
        )
        answer_rows[budget] = compose(
            answer_stages[0][1], answer_stages, max_ted=float(budget)
        )
        for row in mixed_rows[budget]:
            row["method"] = f"Mixed-ProblemDisjoint-TED-{budget}"
        for row in answer_rows[budget]:
            row["method"] = f"Answer9-ProblemDisjoint-TED-{budget}"
        write_rows(output_root / f"mixed-budget-{budget}-seen-test.evaluation.jsonl", mixed_rows[budget])
        write_rows(output_root / f"answer9-budget-{budget}-seen-test.evaluation.jsonl", answer_rows[budget])
        selected["mixed"][key] = mixed_names
        selected["answer"][key] = answer_names
    return {
        "selection_partition": selection["mixed"]["selection_partition"],
        "validation_problems": selection["validation_problems"],
        "validation_test_problem_overlap": 0,
        "selected_members": selected,
        "mixed": {str(b): summarize_method(mixed_rows[b]) for b in BUDGETS},
        "answer": {str(b): summarize_method(answer_rows[b]) for b in BUDGETS},
        "mixed_minus_answer": {
            "per_budget": budget_contrast(mixed_rows, answer_rows),
            "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                mixed_rows,
                answer_rows,
                samples=samples,
                seed=seed,
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--mixed-member", action="append", required=True)
    parser.add_argument("--answer-member", action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    try:
        mixed_members = parse_members(args.mixed_member)
        answer_members = parse_members(args.answer_member)
    except ValueError as error:
        parser.error(str(error))
    result = analyze(
        json.loads(args.selection.read_text(encoding="utf-8")),
        mixed_members,
        answer_members,
        output_root=args.output_root,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["mixed_minus_answer"], sort_keys=True))


if __name__ == "__main__":
    main()
