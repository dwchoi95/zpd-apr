#!/usr/bin/env python3
"""Analyze mixed-target versus Answer-9Choose3 at a second model scale."""

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


def selection_audit(mixed: dict, answer: dict) -> dict:
    audit = {
        "mixed_candidate_checkpoint_count": mixed["candidate_checkpoint_count"],
        "answer_candidate_checkpoint_count": answer["candidate_checkpoint_count"],
        "mixed_feasible_size_three_portfolios": mixed[
            "feasible_unconstrained_size_three_portfolios"
        ],
        "answer_feasible_size_three_portfolios": answer["feasible_portfolios"],
    }
    audit["candidate_pool_sizes_matched"] = (
        audit["mixed_candidate_checkpoint_count"]
        == audit["answer_candidate_checkpoint_count"]
    )
    audit["portfolio_search_spaces_matched"] = (
        audit["mixed_feasible_size_three_portfolios"]
        == audit["answer_feasible_size_three_portfolios"]
    )
    if not audit["candidate_pool_sizes_matched"]:
        raise ValueError("mixed and Answer candidate pool sizes differ")
    if not audit["portfolio_search_spaces_matched"]:
        raise ValueError("mixed and Answer portfolio search spaces differ")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--answer1-seen", type=Path)
    parser.add_argument("--answer1-unseen", type=Path)
    parser.add_argument("--answer3-seen", type=Path)
    parser.add_argument("--answer3-unseen", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    mixed_selection = json.loads(args.mixed_selection.read_text(encoding="utf-8"))
    answer_selection = json.loads(args.answer_selection.read_text(encoding="utf-8"))
    ladder_paths = {
        "seen": (args.answer1_seen, args.answer3_seen),
        "unseen": (args.answer1_unseen, args.answer3_unseen),
    }
    ladder_supplied = [path is not None for pair in ladder_paths.values() for path in pair]
    if any(ladder_supplied) and not all(ladder_supplied):
        parser.error("A1/A3 evaluation paths must be supplied for both splits")
    result = {
        "base_model": "Qwen2.5-Coder-1.5B-Instruct",
        "selection_partition": "Seen validation, one trajectory per problem",
        "test_outcomes_used_for_selection": False,
        "selection_fairness_audit": selection_audit(
            mixed_selection, answer_selection
        ),
        "mixed_members": mixed_selection["best_unconstrained"]["members"],
        "answer_members": answer_selection["selected_unrestricted"]["members"],
        "answer_3seed_members": ["Answer2027", "Answer2028", "Answer2029"],
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        mixed = read_jsonl(args.eval_root / f"mixed-{split}-test.evaluation.jsonl")
        answer = read_jsonl(args.eval_root / f"answer9-{split}-test.evaluation.jsonl")
        mixed_budget = {
            budget: read_jsonl(
                args.eval_root / f"mixed-budget-{budget}-{split}-test.evaluation.jsonl"
            )
            for budget in BUDGETS
        }
        answer_budget = {
            budget: read_jsonl(
                args.eval_root / f"answer9-budget-{budget}-{split}-test.evaluation.jsonl"
            )
            for budget in BUDGETS
        }
        split_result = {
            "mixed_target_9choose3": summarize_method(mixed),
            "answer_9choose3": summarize_method(answer),
            "mixed_minus_answer": paired_suite_rows(
                mixed,
                answer,
                left_label="Mixed-target-9Choose3",
                right_label="Answer-9Choose3",
                samples=args.samples,
                seed=2027 + offset,
            ),
            "budget_indexed_mixed_minus_answer": {
                "per_budget": budget_contrast(mixed_budget, answer_budget),
                "mean_over_predeclared_budgets": clustered_mean_budget_difference(
                    mixed_budget,
                    answer_budget,
                    samples=args.samples,
                    seed=2127 + offset,
                ),
            },
        }
        if all(ladder_supplied):
            answer1 = read_jsonl(ladder_paths[split][0])
            answer3 = read_jsonl(ladder_paths[split][1])
            split_result.update({
                "answer_1": summarize_method(answer1),
                "answer_3seed": summarize_method(answer3),
                "answer_3seed_minus_answer_1": paired_suite_rows(
                    answer3,
                    answer1,
                    left_label="Answer-3Seed",
                    right_label="Answer-1",
                    samples=args.samples,
                    seed=2227 + offset,
                ),
                "answer_9choose3_minus_answer_3seed": paired_suite_rows(
                    answer,
                    answer3,
                    left_label="Answer-9Choose3",
                    right_label="Answer-3Seed",
                    samples=args.samples,
                    seed=2327 + offset,
                ),
            })
        result["splits"][split] = split_result
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
