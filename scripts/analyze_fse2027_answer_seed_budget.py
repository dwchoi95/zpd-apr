#!/usr/bin/env python3
"""Compare P/S/A and Answer-3Seed under structural edit budgets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_patch_budget import (
    budget_success,
    clustered_difference,
    summarize,
)
from analyze_fse2027_robustness import read_jsonl, replay_selected_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budgets", default="5,10,20,40,80,160")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    budgets = [float(value) for value in args.budgets.split(",")]
    left = replay_selected_rows(args.eval_root, ("progress", "strict", "answer"))
    right = read_jsonl(
        args.eval_root
        / "answer-seed-control"
        / "answer-seeds-seen-test.evaluation.jsonl"
    )
    if {row["example_id"] for row in left} != {row["example_id"] for row in right}:
        raise ValueError("portfolio evaluations cover different examples")
    contrasts = {
        str(int(budget)): {
            "difference": (
                sum(budget_success(row, budget) for row in left)
                - sum(budget_success(row, budget) for row in right)
            )
            / len(left),
            "problem_cluster_95ci": clustered_difference(
                left,
                right,
                budget,
                samples=args.bootstrap_samples,
                seed=args.seed + int(budget),
            ),
        }
        for budget in budgets
    }
    report = {
        "estimand": "repair rate with AST TED at or below budget",
        "budgets": [int(value) for value in budgets],
        "independent_policies": summarize(left, budgets),
        "answer_3seed": summarize(right, budgets),
        "independent_policies_minus_answer_3seed": contrasts,
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
