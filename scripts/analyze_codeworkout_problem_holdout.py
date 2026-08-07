#!/usr/bin/env python3
"""Analyze exercise-held-out CodeWorkout fair-pool replication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mixed", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mixed = read_jsonl(args.mixed)
    answer = read_jsonl(args.answer9)
    mixed_selection = json.loads(args.mixed_selection.read_text(encoding="utf-8"))
    answer_selection = json.loads(args.answer_selection.read_text(encoding="utf-8"))
    result = {
        "dataset": "CodeWorkout exercise-held-out Java test",
        "split": {"train_exercises": 10, "validation_exercises": 3, "test_exercises": 4},
        "test_outcomes_used_for_selection": False,
        "mixed_members": mixed_selection["best_unconstrained"]["members"],
        "answer_members": answer_selection["selected_unrestricted"]["members"],
        "mixed_target_9choose3": summarize_method(mixed),
        "answer_9choose3": summarize_method(answer),
        "mixed_minus_answer": paired_suite_rows(
            mixed,
            answer,
            left_label="Mixed-target-9Choose3",
            right_label="Answer-9Choose3",
            samples=10_000,
            seed=2027,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
