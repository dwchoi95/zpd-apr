#!/usr/bin/env python3
"""Analyze exercise-held-out CodeWorkout fair-pool replication."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
from analyze_codeworkout_portfolios import clustered_interval
from analyze_fse2027_scale_replication import selection_audit


def analyze(
    mixed: list[dict],
    answer: list[dict],
    answer3: list[dict] | None,
    answer1: list[dict] | None,
    mixed_selection: dict,
    answer_selection: dict,
    *,
    samples: int = 10_000,
    seed: int = 2027,
) -> dict:
    comparison = paired_suite_rows(
        mixed,
        answer,
        left_label="Mixed-target-9Choose3",
        right_label="Answer-9Choose3",
        samples=samples,
        seed=seed,
    )
    comparison["student_cluster_rr_95ci"] = clustered_interval(
        mixed, answer, "user_id", seed=seed
    )
    result = {
        "dataset": "CodeWorkout exercise-held-out Java test",
        "split": {"train_exercises": 10, "validation_exercises": 3, "test_exercises": 4},
        "test_outcomes_used_for_selection": False,
        "selection_fairness_audit": selection_audit(
            mixed_selection, answer_selection
        ),
        "mixed_members": mixed_selection["best_unconstrained"]["members"],
        "answer_members": answer_selection["selected_unrestricted"]["members"],
        "answer_3seed_members": ["Answer2027", "Answer2028", "Answer2029"],
        "mixed_target_9choose3": summarize_method(mixed),
        "answer_9choose3": summarize_method(answer),
        "mixed_minus_answer": comparison,
    }
    if (answer3 is None) != (answer1 is None):
        raise ValueError("Answer-1 and Answer-3Seed must be supplied together")
    if answer3 is not None and answer1 is not None:
        a3_a1 = paired_suite_rows(
            answer3, answer1, left_label="Answer-3Seed", right_label="Answer-1",
            samples=samples, seed=seed + 100,
        )
        a9_a3 = paired_suite_rows(
            answer, answer3, left_label="Answer-9Choose3", right_label="Answer-3Seed",
            samples=samples, seed=seed + 200,
        )
        a3_a1["student_cluster_rr_95ci"] = clustered_interval(
            answer3, answer1, "user_id", seed=seed + 100
        )
        a9_a3["student_cluster_rr_95ci"] = clustered_interval(
            answer, answer3, "user_id", seed=seed + 200
        )
        result.update({
            "answer_1": summarize_method(answer1),
            "answer_3seed": summarize_method(answer3),
            "answer_3seed_minus_answer_1": a3_a1,
            "answer_9choose3_minus_answer_3seed": a9_a3,
        })
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mixed", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--answer3", type=Path)
    parser.add_argument("--answer1", type=Path)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    mixed = read_jsonl(args.mixed)
    answer = read_jsonl(args.answer9)
    answer3 = read_jsonl(args.answer3) if args.answer3 else None
    answer1 = read_jsonl(args.answer1) if args.answer1 else None
    mixed_selection = json.loads(args.mixed_selection.read_text(encoding="utf-8"))
    answer_selection = json.loads(args.answer_selection.read_text(encoding="utf-8"))
    result = analyze(
        mixed,
        answer,
        answer3,
        answer1,
        mixed_selection,
        answer_selection,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
