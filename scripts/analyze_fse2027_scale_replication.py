#!/usr/bin/env python3
"""Analyze mixed-target versus Answer-9Choose3 at a second model scale."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    mixed_selection = json.loads(args.mixed_selection.read_text(encoding="utf-8"))
    answer_selection = json.loads(args.answer_selection.read_text(encoding="utf-8"))
    result = {
        "base_model": "Qwen2.5-Coder-1.5B-Instruct",
        "selection_partition": "Seen validation, one trajectory per problem",
        "test_outcomes_used_for_selection": False,
        "mixed_members": mixed_selection["best_unconstrained"]["members"],
        "answer_members": answer_selection["selected_unrestricted"]["members"],
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        mixed = read_jsonl(args.eval_root / f"mixed-{split}-test.evaluation.jsonl")
        answer = read_jsonl(args.eval_root / f"answer9-{split}-test.evaluation.jsonl")
        result["splits"][split] = {
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
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
