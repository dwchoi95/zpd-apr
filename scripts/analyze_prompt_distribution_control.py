#!/usr/bin/env python3
"""Analyze full-history versus current-only inference for matched portfolios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_fse2027_robustness import (
    paired_suite_rows,
    read_jsonl,
    summarize_method,
)
from analyze_fse2027_scale_replication import selection_audit


Rows = list[dict[str, Any]]


def contrast(
    left: Rows,
    right: Rows,
    *,
    left_label: str,
    right_label: str,
    seed: int,
    samples: int,
) -> dict[str, Any]:
    return paired_suite_rows(
        left,
        right,
        left_label=left_label,
        right_label=right_label,
        seed=seed,
        samples=samples,
    )


def analyze_split(
    *,
    current_mixed_reselected: Rows,
    current_answer_reselected: Rows,
    current_mixed_frozen: Rows,
    current_answer_frozen: Rows,
    full_mixed_frozen: Rows,
    full_answer_frozen: Rows,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "current_only_reselected": {
            "mixed_target_9choose3": summarize_method(current_mixed_reselected),
            "answer_9choose3": summarize_method(current_answer_reselected),
            "mixed_minus_answer": contrast(
                current_mixed_reselected,
                current_answer_reselected,
                left_label="Mixed-current-only-reselected",
                right_label="Answer-current-only-reselected",
                seed=seed,
                samples=samples,
            ),
        },
        "full_history_selected_members": {
            "full_history": {
                "mixed_target_9choose3": summarize_method(full_mixed_frozen),
                "answer_9choose3": summarize_method(full_answer_frozen),
                "mixed_minus_answer": contrast(
                    full_mixed_frozen,
                    full_answer_frozen,
                    left_label="Mixed-full-history-frozen",
                    right_label="Answer-full-history-frozen",
                    seed=seed + 10,
                    samples=samples,
                ),
            },
            "current_only": {
                "mixed_target_9choose3": summarize_method(current_mixed_frozen),
                "answer_9choose3": summarize_method(current_answer_frozen),
                "mixed_minus_answer": contrast(
                    current_mixed_frozen,
                    current_answer_frozen,
                    left_label="Mixed-current-only-frozen",
                    right_label="Answer-current-only-frozen",
                    seed=seed + 20,
                    samples=samples,
                ),
            },
            "prompt_context_effect": {
                "mixed_current_only_minus_full_history": contrast(
                    current_mixed_frozen,
                    full_mixed_frozen,
                    left_label="Mixed-current-only-frozen",
                    right_label="Mixed-full-history-frozen",
                    seed=seed + 30,
                    samples=samples,
                ),
                "answer_current_only_minus_full_history": contrast(
                    current_answer_frozen,
                    full_answer_frozen,
                    left_label="Answer-current-only-frozen",
                    right_label="Answer-full-history-frozen",
                    seed=seed + 40,
                    samples=samples,
                ),
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--full-eval-root", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()

    mixed_selection = json.loads(args.mixed_selection.read_text(encoding="utf-8"))
    answer_selection = json.loads(args.answer_selection.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "control": "common current-only inference with validation reselection and frozen-member replay",
        "test_outcomes_used_for_selection": False,
        "selection_fairness_audit": selection_audit(
            mixed_selection, answer_selection
        ),
        "current_only_mixed_members": mixed_selection["best_unconstrained"][
            "members"
        ],
        "current_only_answer_members": answer_selection["selected_unrestricted"][
            "members"
        ],
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        current = args.eval_root / split
        full = args.full_eval_root
        result["splits"][split] = analyze_split(
            current_mixed_reselected=read_jsonl(
                current / "mixed-reselected.evaluation.jsonl"
            ),
            current_answer_reselected=read_jsonl(
                current / "answer-reselected.evaluation.jsonl"
            ),
            current_mixed_frozen=read_jsonl(
                current / "mixed-full-selection.evaluation.jsonl"
            ),
            current_answer_frozen=read_jsonl(
                current / "answer-full-selection.evaluation.jsonl"
            ),
            full_mixed_frozen=read_jsonl(
                full
                / "selected-portfolios"
                / f"unconstrained-{split}-test.evaluation.jsonl"
            ),
            full_answer_frozen=read_jsonl(
                full
                / "answer9-control"
                / f"answer9-unrestricted-{split}-test.evaluation.jsonl"
            ),
            samples=args.samples,
            seed=2027 + offset * 100,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
