#!/usr/bin/env python3
"""Cross-fit mixed and Answer portfolios across Seen test-problem folds."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
from analyze_fse2027_selected_portfolios import (
    BUDGETS,
    budget_contrast,
    clustered_mean_budget_difference,
)
from compose_answer_seed_control import compose
from select_answer_seed_portfolio import select as select_answer
from select_execution_portfolio import select_portfolios


Row = dict[str, Any]


def parse_named(values: list[str]) -> dict[str, list[Row]]:
    result: dict[str, list[Row]] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("member must use NAME=PATH")
        name, path = raw.split("=", 1)
        if name in result:
            raise ValueError(f"duplicate member: {name}")
        result[name] = read_jsonl(Path(path))
    return result


def relation(name: str) -> str:
    for value in ("Progress", "Strict", "Answer"):
        if name.startswith(value):
            return value
    raise ValueError(f"unknown relation for {name}")


def relation_order(name: str) -> tuple[int, str]:
    return (("Progress", "Strict", "Answer").index(relation(name)), name)


def fold_for(problem_id: str, *, folds: int, seed: int) -> int:
    digest = hashlib.sha256(f"{seed}:{problem_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % folds


def subset(rows: list[Row], problems: set[str], *, include: bool) -> list[Row]:
    return [
        row
        for row in rows
        if (str(row["problem_id"]) in problems) is include
    ]


def aligned_example_ids(members: dict[str, list[Row]], *, label: str) -> set[str]:
    """Require every candidate in a selection family to cover one unique cohort."""
    if not members:
        raise ValueError(f"{label} has no members")
    expected: set[str] | None = None
    for name, rows in members.items():
        ids = [str(row["example_id"]) for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{label} member {name} has duplicate example IDs")
        current = set(ids)
        if expected is None:
            expected = current
        elif current != expected:
            raise ValueError(f"{label} members do not cover identical examples")
    assert expected is not None
    return expected


def compose_selected(
    members: dict[str, list[Row]],
    names: list[str],
    problems: set[str],
    *,
    mixed: bool,
    max_ted: float | None = None,
) -> list[Row]:
    ordered = sorted(names, key=relation_order if mixed else None)
    stages = [(name, subset(members[name], problems, include=True)) for name in ordered]
    if not stages or not stages[0][1]:
        raise ValueError("selected fold has no test rows")
    return compose(stages[0][1], stages, max_ted=max_ted)


def write_rows(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row) + "\n")


def analyze(
    mixed_validation: dict[str, list[Row]],
    mixed_test: dict[str, list[Row]],
    answer_validation: dict[str, list[Row]],
    answer_test: dict[str, list[Row]],
    *,
    folds: int,
    fold_seed: int,
    bootstrap_samples: int,
    bootstrap_seed: int,
    output_root: Path | None = None,
) -> dict[str, Any]:
    if folds < 2:
        raise ValueError("folds must be at least two")
    if set(mixed_validation) != set(mixed_test):
        raise ValueError("mixed validation and test members differ")
    if set(answer_validation) != set(answer_test):
        raise ValueError("Answer validation and test members differ")
    mixed_validation_ids = aligned_example_ids(
        mixed_validation, label="mixed validation"
    )
    answer_validation_ids = aligned_example_ids(
        answer_validation, label="Answer validation"
    )
    mixed_test_ids = aligned_example_ids(mixed_test, label="mixed test")
    answer_test_ids = aligned_example_ids(answer_test, label="Answer test")
    if mixed_validation_ids != answer_validation_ids:
        raise ValueError("mixed and Answer validation cohorts differ")
    if mixed_test_ids != answer_test_ids:
        raise ValueError("mixed and Answer test cohorts differ")
    relations = {name: relation(name) for name in mixed_validation}
    test_problems = {
        str(row["problem_id"])
        for rows in mixed_test.values()
        for row in rows
    }
    if any(
        {str(row["problem_id"]) for row in rows} != test_problems
        for rows in list(mixed_test.values()) + list(answer_test.values())
    ):
        raise ValueError("test members do not cover identical problem sets")

    fold_problems = {
        fold: {
            problem
            for problem in test_problems
            if fold_for(problem, folds=folds, seed=fold_seed) == fold
        }
        for fold in range(folds)
    }
    if any(not problems for problems in fold_problems.values()):
        raise ValueError("at least one cross-fit fold has no test problems")

    mixed_rows: list[Row] = []
    answer_rows: list[Row] = []
    mixed_budget_rows = {budget: [] for budget in BUDGETS}
    answer_budget_rows = {budget: [] for budget in BUDGETS}
    audits = []
    for fold, held_out in fold_problems.items():
        mixed_fit = {
            name: subset(rows, held_out, include=False)
            for name, rows in mixed_validation.items()
        }
        answer_fit = {
            name: subset(rows, held_out, include=False)
            for name, rows in answer_validation.items()
        }
        mixed_selection = select_portfolios(mixed_fit, relations)
        answer_selection = select_answer(answer_fit)
        mixed_names = mixed_selection["best_unconstrained"]["members"]
        answer_names = answer_selection["selected_unrestricted"]["members"]
        fold_mixed = compose_selected(
            mixed_test, mixed_names, held_out, mixed=True
        )
        fold_answer = compose_selected(
            answer_test, answer_names, held_out, mixed=False
        )
        for row in fold_mixed:
            row["method"] = "Mixed-Problem-CrossFit"
            row["crossfit_fold"] = fold
        for row in fold_answer:
            row["method"] = "Answer9-Problem-CrossFit"
            row["crossfit_fold"] = fold
        mixed_rows.extend(fold_mixed)
        answer_rows.extend(fold_answer)
        budget_members = {"mixed": {}, "answer": {}}
        for budget in BUDGETS:
            key = str(budget)
            selected_mixed = mixed_selection["selected_unconstrained_by_budget"][key][
                "members"
            ]
            selected_answer = answer_selection["selected_by_budget"][key]["members"]
            fold_mixed_budget = compose_selected(
                mixed_test,
                selected_mixed,
                held_out,
                mixed=True,
                max_ted=float(budget),
            )
            fold_answer_budget = compose_selected(
                answer_test,
                selected_answer,
                held_out,
                mixed=False,
                max_ted=float(budget),
            )
            for row in fold_mixed_budget:
                row["method"] = f"Mixed-Problem-CrossFit-TED-{budget}"
                row["crossfit_fold"] = fold
            for row in fold_answer_budget:
                row["method"] = f"Answer9-Problem-CrossFit-TED-{budget}"
                row["crossfit_fold"] = fold
            mixed_budget_rows[budget].extend(fold_mixed_budget)
            answer_budget_rows[budget].extend(fold_answer_budget)
            budget_members["mixed"][key] = selected_mixed
            budget_members["answer"][key] = selected_answer
        validation_problems = {
            str(row["problem_id"])
            for row in next(iter(mixed_fit.values()))
        }
        audits.append(
            {
                "fold": fold,
                "test_problems": len(held_out),
                "validation_problems": len(validation_problems),
                "validation_test_problem_overlap": len(validation_problems & held_out),
                "mixed_members": mixed_names,
                "answer_members": answer_names,
                "budget_members": budget_members,
            }
        )

    mixed_rows.sort(key=lambda row: str(row["example_id"]))
    answer_rows.sort(key=lambda row: str(row["example_id"]))
    for budget in BUDGETS:
        mixed_budget_rows[budget].sort(key=lambda row: str(row["example_id"]))
        answer_budget_rows[budget].sort(key=lambda row: str(row["example_id"]))
    if output_root is not None:
        write_rows(output_root / "mixed-seen-test.evaluation.jsonl", mixed_rows)
        write_rows(output_root / "answer9-seen-test.evaluation.jsonl", answer_rows)
        for budget in BUDGETS:
            write_rows(
                output_root / f"mixed-budget-{budget}-seen-test.evaluation.jsonl",
                mixed_budget_rows[budget],
            )
            write_rows(
                output_root / f"answer9-budget-{budget}-seen-test.evaluation.jsonl",
                answer_budget_rows[budget],
            )
    return {
        "design": "problem-level cross-fitting with fold-specific validation exclusion",
        "folds": folds,
        "fold_seed": fold_seed,
        "test_outcomes_used_for_selection": False,
        "cohort_audit": {
            "validation_examples": len(mixed_validation_ids),
            "test_examples": len(mixed_test_ids),
            "unique_examples_per_member": True,
            "mixed_answer_validation_examples_identical": True,
            "mixed_answer_test_examples_identical": True,
        },
        "fold_audit": audits,
        "mixed": summarize_method(mixed_rows),
        "answer": summarize_method(answer_rows),
        "mixed_minus_answer": paired_suite_rows(
            mixed_rows,
            answer_rows,
            left_label="Mixed-problem-crossfit",
            right_label="Answer9-problem-crossfit",
            samples=bootstrap_samples,
            seed=bootstrap_seed,
        ),
        "budget": {
            "mixed": {
                str(budget): summarize_method(mixed_budget_rows[budget])
                for budget in BUDGETS
            },
            "answer": {
                str(budget): summarize_method(answer_budget_rows[budget])
                for budget in BUDGETS
            },
            "mixed_minus_answer": {
                "per_budget": budget_contrast(mixed_budget_rows, answer_budget_rows),
                "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                    mixed_budget_rows,
                    answer_budget_rows,
                    samples=bootstrap_samples,
                    seed=bootstrap_seed + 100,
                ),
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mixed-validation", action="append", required=True)
    parser.add_argument("--mixed-test", action="append", required=True)
    parser.add_argument("--answer-validation", action="append", required=True)
    parser.add_argument("--answer-test", action="append", required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--fold-seed", type=int, default=2027)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=2027)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = analyze(
            parse_named(args.mixed_validation),
            parse_named(args.mixed_test),
            parse_named(args.answer_validation),
            parse_named(args.answer_test),
            folds=args.folds,
            fold_seed=args.fold_seed,
            bootstrap_samples=args.bootstrap_samples,
            bootstrap_seed=args.bootstrap_seed,
            output_root=args.output_root,
        )
    except ValueError as error:
        parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["mixed_minus_answer"], sort_keys=True))


if __name__ == "__main__":
    main()
