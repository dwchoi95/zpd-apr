#!/usr/bin/env python3
"""Promote the current-only A1/A3/A9/M9 ladder to a deployment comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method


Rows = list[dict[str, Any]]
BUDGETS = (5, 10, 20, 40, 80, 160)


def analyze_split(mixed9: Rows, answer9: Rows, answer3: Rows, answer1: Rows, *, samples: int, seed: int) -> dict[str, Any]:
    methods = {
        "answer_1": summarize_method(answer1),
        "answer_3seed": summarize_method(answer3),
        "answer_9choose3": summarize_method(answer9),
        "mixed_target_9choose3": summarize_method(mixed9),
    }
    comparisons = {}
    for offset, (name, left, right, left_label, right_label) in enumerate((
        ("answer_3seed_minus_answer_1", answer3, answer1, "Current-only-Answer-3Seed", "Current-only-Answer-1"),
        ("answer_9choose3_minus_answer_3seed", answer9, answer3, "Current-only-Answer-9Choose3", "Current-only-Answer-3Seed"),
        ("mixed_minus_answer_3seed", mixed9, answer3, "Current-only-Mixed-9Choose3", "Current-only-Answer-3Seed"),
        ("mixed_minus_answer_9choose3", mixed9, answer9, "Current-only-Mixed-9Choose3", "Current-only-Answer-9Choose3"),
    )):
        comparisons[name] = paired_suite_rows(
            left, right, left_label=left_label, right_label=right_label,
            samples=samples, seed=seed + 10 * offset,
        )
    return {"methods": methods, "comparisons": comparisons}


def budget_frontier(
    eval_root: Path,
    reference_root: Path,
    split: str,
    *,
    samples: int,
    seed: int,
) -> list[dict[str, Any]]:
    rows = []
    for offset, budget in enumerate(BUDGETS):
        current = read_jsonl(
            eval_root / split / f"answer-3seed.max-ted-{budget}.evaluation.jsonl"
        )
        relation = read_jsonl(
            reference_root / "selected-portfolios"
            / f"budget-indexed-relation-{split}-test.max-ted-{budget}.evaluation.jsonl"
        )
        row: dict[str, Any] = {
            "budget": budget,
            "current_only_answer_3seed": summarize_method(current),
            "budget_selected_relation": summarize_method(relation),
            "current_only_minus_relation": paired_suite_rows(
                current, relation,
                left_label="Current-only-Answer-3Seed",
                right_label="Budget-selected-mixed-target",
                samples=samples, seed=seed + offset * 10,
            ),
        }
        if split == "seen":
            lsgen = read_jsonl(
                reference_root / "lsgen-budget-controller"
                / f"lsgen-seen-test.max-ted-{budget}.evaluation.jsonl"
            )
            row["lsgen"] = summarize_method(lsgen)
            row["current_only_minus_lsgen"] = paired_suite_rows(
                current, lsgen,
                left_label="Current-only-Answer-3Seed",
                right_label="LSGen-always-three",
                samples=samples, seed=seed + offset * 10 + 1,
            )
        rows.append(row)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result: dict[str, Any] = {
        "control": "current-code-only inference with validation-frozen A1/A3 and validation-reselected A9/M9",
        "test_outcomes_used_for_selection": False,
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        root = args.eval_root / split
        result["splits"][split] = analyze_split(
            read_jsonl(root / "mixed-reselected.evaluation.jsonl"),
            read_jsonl(root / "answer-reselected.evaluation.jsonl"),
            read_jsonl(root / "answer-3seed.evaluation.jsonl"),
            read_jsonl(root / "Answer2027.evaluation.jsonl"),
            samples=args.samples,
            seed=2027 + offset * 100,
        )
        if args.reference_root is not None:
            result["splits"][split]["budget_frontier"] = budget_frontier(
                args.eval_root, args.reference_root, split,
                samples=args.samples, seed=3027 + offset * 100,
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
