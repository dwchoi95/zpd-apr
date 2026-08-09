#!/usr/bin/env python3
"""Audit fixed portfolio coverage under AST-size-normalized edit budgets."""

from __future__ import annotations

import argparse
import ast
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parse_evaluation(value: str) -> tuple[str, Path]:
    try:
        name, path = value.split("=", 1)
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected NAME=PATH") from error
    if not name or not path:
        raise argparse.ArgumentTypeError("expected non-empty NAME=PATH")
    return name, Path(path)


def ast_nodes(code: str) -> int | None:
    try:
        return sum(1 for _ in ast.walk(ast.parse(code)))
    except (SyntaxError, ValueError, TypeError):
        return None


def current_code(row: dict[str, Any]) -> str:
    history = row.get("history")
    if not isinstance(history, list) or not history:
        raise ValueError(f"missing history for {row.get('example_id')}")
    code = history[-1].get("code")
    if not isinstance(code, str):
        raise ValueError(f"missing current code for {row.get('example_id')}")
    return code


def load_method(
    evaluations: list[tuple[str, Path]],
    expected_ids: set[str],
) -> tuple[list[str], dict[str, list[dict[str, Any]]]]:
    if len(evaluations) != 3:
        raise ValueError("a frozen portfolio must contain exactly three evaluations")
    members: list[str] = []
    by_example: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, path in evaluations:
        members.append(name)
        rows = read_jsonl(path)
        keyed = {str(row["example_id"]): row for row in rows}
        if len(keyed) != len(rows) or set(keyed) != expected_ids:
            raise ValueError(f"evaluation coverage mismatch: {name}")
        for example_id, row in keyed.items():
            by_example[example_id].append(row)
    return members, dict(by_example)


def minimum_normalized_ted(
    rows: list[dict[str, Any]],
    denominator: int,
) -> float | None:
    eligible = [
        float(row["tree_edit_distance"]) / denominator
        for row in rows
        if bool(row.get("repaired")) and row.get("tree_edit_distance") is not None
    ]
    return min(eligible) if eligible else None


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def clustered_interval(
    records: list[dict[str, Any]],
    budget: float,
    *,
    samples: int,
    seed: int,
) -> list[float]:
    by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        by_problem[str(row["problem_id"])].append(row)
    problems = sorted(by_problem)
    randomizer = random.Random(seed)
    draws: list[float] = []
    for _ in range(samples):
        sampled = [randomizer.choice(problems) for _ in problems]
        numerator = 0.0
        denominator = 0
        for problem in sampled:
            for row in by_problem[problem]:
                numerator += float(
                    row["mixed_min_normalized_ted"] is not None
                    and row["mixed_min_normalized_ted"] <= budget
                ) - float(
                    row["answer_min_normalized_ted"] is not None
                    and row["answer_min_normalized_ted"] <= budget
                )
                denominator += 1
        draws.append(numerator / denominator)
    return [percentile(draws, 0.025), percentile(draws, 0.975)]


def analyze(
    dataset: list[dict[str, Any]],
    mixed_evaluations: list[tuple[str, Path]],
    answer_evaluations: list[tuple[str, Path]],
    budgets: list[float],
    *,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    dataset_by_id = {str(row["example_id"]): row for row in dataset}
    if len(dataset_by_id) != len(dataset):
        raise ValueError("duplicate dataset example IDs")
    expected_ids = set(dataset_by_id)
    mixed_members, mixed = load_method(mixed_evaluations, expected_ids)
    answer_members, answer = load_method(answer_evaluations, expected_ids)
    records: list[dict[str, Any]] = []
    excluded: list[str] = []
    for example_id, row in dataset_by_id.items():
        denominator = ast_nodes(current_code(row))
        if denominator is None:
            excluded.append(example_id)
            continue
        records.append(
            {
                "example_id": example_id,
                "problem_id": str(row["problem_id"]),
                "current_ast_nodes": denominator,
                "mixed_min_normalized_ted": minimum_normalized_ted(
                    mixed[example_id], denominator
                ),
                "answer_min_normalized_ted": minimum_normalized_ted(
                    answer[example_id], denominator
                ),
            }
        )
    per_budget: dict[str, Any] = {}
    for index, budget in enumerate(budgets):
        mixed_success = [
            row["mixed_min_normalized_ted"] is not None
            and row["mixed_min_normalized_ted"] <= budget
            for row in records
        ]
        answer_success = [
            row["answer_min_normalized_ted"] is not None
            and row["answer_min_normalized_ted"] <= budget
            for row in records
        ]
        mixed_rr = sum(mixed_success) / len(records)
        answer_rr = sum(answer_success) / len(records)
        per_budget[f"{budget:g}"] = {
            "mixed_rr": mixed_rr,
            "answer_rr": answer_rr,
            "mixed_minus_answer": mixed_rr - answer_rr,
            "problem_cluster_95ci": clustered_interval(
                records,
                budget,
                samples=bootstrap_samples,
                seed=seed + index,
            ),
        }
    return {
        "analysis_status": "post-hoc robustness audit",
        "estimand": "repair rate on parseable-current inputs with TED/current AST nodes at or below budget",
        "portfolio_selection": "validation-frozen unrestricted portfolios; no test outcome used for member selection",
        "mixed_members": mixed_members,
        "answer_members": answer_members,
        "examples_total": len(dataset),
        "examples_parseable_current": len(records),
        "examples_excluded_unparseable_current": len(excluded),
        "budgets": budgets,
        "per_budget": per_budget,
        "bootstrap": {
            "cluster": "problem_id",
            "samples": bootstrap_samples,
            "seed": seed,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--mixed", type=parse_evaluation, action="append", required=True)
    parser.add_argument("--answer", type=parse_evaluation, action="append", required=True)
    parser.add_argument("--budgets", default="0.05,0.1,0.2,0.4,0.8,1.6")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze(
        read_jsonl(args.dataset),
        args.mixed,
        args.answer,
        [float(value) for value in args.budgets.split(",")],
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["per_budget"], sort_keys=True))


if __name__ == "__main__":
    main()
