#!/usr/bin/env python3
"""Analyze the compute- and selection-matched Answer-9Choose3 control."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
from analyze_fse2027_selected_portfolios import (
    BUDGETS,
    budget_contrast,
    clustered_mean_budget_difference,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    result = {
        "control": "Answer-9Choose3",
        "selection_partition": selection["selection_partition"],
        "test_split_outcomes_used_for_selection": False,
        "candidate_checkpoint_count": selection["candidate_checkpoint_count"],
        "feasible_portfolios": selection["feasible_portfolios"],
        "selected_unrestricted_members": selection["selected_unrestricted"]["members"],
        "selected_by_budget_members": {
            budget: item["members"]
            for budget, item in selection["selected_by_budget"].items()
        },
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        root = args.eval_root / "answer9-control"
        answer = read_jsonl(root / f"answer9-unrestricted-{split}-test.evaluation.jsonl")
        answer3 = read_jsonl(
            args.eval_root
            / "selected-portfolios"
            / f"answer-3seed-{split}-test.evaluation.jsonl"
        )
        answer1 = read_jsonl(
            args.eval_root
            / "selected-portfolios"
            / f"Answer2027-{split}-test.evaluation.jsonl"
        )
        zpd = read_jsonl(
            args.eval_root
            / "selected-portfolios"
            / f"unconstrained-{split}-test.evaluation.jsonl"
        )
        answer_budget = {
            budget: read_jsonl(
                root / f"answer9-budget-{budget}-{split}-test.evaluation.jsonl"
            )
            for budget in BUDGETS
        }
        zpd_budget = {
            budget: read_jsonl(
                args.eval_root
                / "selected-portfolios"
                / f"budget-indexed-unconstrained-{split}-test.max-ted-{budget}.evaluation.jsonl"
            )
            for budget in BUDGETS
        }
        result["splits"][split] = {
            "zpdpatch": summarize_method(zpd),
            "answer_9choose3": summarize_method(answer),
            "answer_3seed": summarize_method(answer3),
            "answer_1": summarize_method(answer1),
            "answer_3seed_minus_answer_1": paired_suite_rows(
                answer3,
                answer1,
                left_label="Answer-3Seed",
                right_label="Answer-1",
                samples=args.samples,
                seed=args.seed + 20 + offset,
            ),
            "answer_9choose3_minus_answer_3seed": paired_suite_rows(
                answer,
                answer3,
                left_label="Answer-9Choose3",
                right_label="Answer-3Seed",
                samples=args.samples,
                seed=args.seed + 30 + offset,
            ),
            "zpdpatch_minus_answer_9choose3": paired_suite_rows(
                zpd,
                answer,
                left_label="ZPDPatch",
                right_label="Answer-9Choose3",
                samples=args.samples,
                seed=args.seed + offset,
            ),
            "budget_indexed_zpdpatch_minus_answer_9choose3": {
                "per_budget": budget_contrast(zpd_budget, answer_budget),
                "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                    zpd_budget,
                    answer_budget,
                    samples=args.samples,
                    seed=args.seed + 100 + offset,
                ),
            },
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
