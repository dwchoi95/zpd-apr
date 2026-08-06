#!/usr/bin/env python3
"""Compute repair coverage under predeclared AST edit budgets."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from analyze_fse2027_robustness import read_jsonl, replay_selected_rows


Row = dict[str, Any]


def keyed(rows: list[Row]) -> dict[str, Row]:
    result = {str(row["example_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate example_id")
    return result


def budget_success(row: Row, budget: float) -> bool:
    ted = row.get("ted_buggy_fixed")
    return bool(row.get("repaired")) and ted is not None and float(ted) <= budget


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def clustered_difference(
    left: list[Row], right: list[Row], budget: float, *, samples: int, seed: int
) -> list[float]:
    right_by_id = keyed(right)
    by_problem: dict[str, list[tuple[bool, bool]]] = defaultdict(list)
    for row in left:
        peer = right_by_id[str(row["example_id"])]
        by_problem[str(row["problem_id"])].append(
            (budget_success(row, budget), budget_success(peer, budget))
        )
    problems = sorted(by_problem)
    rng = random.Random(seed)
    draws = []
    for _ in range(samples):
        selected = [rng.choice(problems) for _problem in problems]
        pairs = [pair for problem in selected for pair in by_problem[problem]]
        draws.append(sum(left_ok - right_ok for left_ok, right_ok in pairs) / len(pairs))
    return [percentile(draws, 0.025), percentile(draws, 0.975)]


def summarize(rows: list[Row], budgets: list[float]) -> dict[str, Any]:
    repaired = [row for row in rows if bool(row.get("repaired"))]
    parseable = [row for row in repaired if row.get("ted_buggy_fixed") is not None]
    return {
        "examples": len(rows),
        "unconstrained_repair_rate": len(repaired) / len(rows),
        "repaired_with_ted": len(parseable),
        "ted_coverage_among_repairs": len(parseable) / len(repaired),
        "repair_rate_by_max_ted": {
            str(int(budget)): sum(budget_success(row, budget) for row in rows) / len(rows)
            for budget in budgets
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budgets", default="5,10,20,40,80,160")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    budgets = [float(value) for value in args.budgets.split(",")]
    eval_root = args.eval_root.expanduser().resolve()
    methods = {
        "ZPDPatch": replay_selected_rows(eval_root, ("progress", "strict", "answer")),
        "Zero-shot": read_jsonl(eval_root / "zero-shot-seen-test.evaluation.jsonl"),
        "LSGen": read_jsonl(eval_root / "lsgen-seen-test.evaluation.jsonl"),
    }
    expected = set(keyed(methods["ZPDPatch"]))
    if any(set(keyed(rows)) != expected for rows in methods.values()):
        raise ValueError("methods do not cover identical examples")
    contrasts = {}
    for right_name in ("Zero-shot", "LSGen"):
        right = methods[right_name]
        contrasts[f"ZPDPatch_minus_{right_name}"] = {
            str(int(budget)): {
                "difference": (
                    sum(budget_success(row, budget) for row in methods["ZPDPatch"])
                    - sum(budget_success(row, budget) for row in right)
                )
                / len(right),
                "problem_cluster_95ci": clustered_difference(
                    methods["ZPDPatch"],
                    right,
                    budget,
                    samples=args.bootstrap_samples,
                    seed=args.seed + int(budget),
                ),
            }
            for budget in budgets
        }
    report = {
        "schema_version": 1,
        "estimand": "repair rate with successful patch AST TED at or below budget",
        "missing_ted_policy": "counted as not within budget (conservative lower bound)",
        "budgets": [int(value) for value in budgets],
        "methods": {name: summarize(rows, budgets) for name, rows in methods.items()},
        "contrasts": contrasts,
        "bootstrap": {
            "samples": args.bootstrap_samples,
            "seed": args.seed,
            "cluster": "problem_id",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(contrasts, sort_keys=True))


if __name__ == "__main__":
    main()
