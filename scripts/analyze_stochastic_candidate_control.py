#!/usr/bin/env python3
"""Separate same-checkpoint stochastic breadth from checkpoint diversity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
except ImportError:  # pragma: no cover - package import in tests
    from scripts.analyze_fse2027_robustness import (
        paired_suite_rows,
        read_jsonl,
        summarize_method,
    )


Rows = list[dict[str, Any]]


def generation_diversity(candidate_sets: list[Rows]) -> dict[str, Any]:
    by_stage = [
        {str(row["example_id"]): str(row.get("generated_code", "")) for row in rows}
        for rows in candidate_sets
    ]
    ids = set(by_stage[0])
    if any(set(stage) != ids for stage in by_stage[1:]):
        raise ValueError("stochastic generation stages do not cover identical examples")
    unique_counts = [len({stage[example_id] for stage in by_stage}) for example_id in ids]
    return {
        "examples": len(ids),
        "mean_unique_candidates": sum(unique_counts) / len(unique_counts),
        "all_three_unique": sum(count == 3 for count in unique_counts),
        "at_least_two_unique": sum(count >= 2 for count in unique_counts),
        "all_identical": sum(count == 1 for count in unique_counts),
    }


def analyze_split(
    stochastic3: Rows,
    answer3: Rows,
    answer1: Rows,
    generations: list[Rows],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "same_checkpoint_stochastic_3": summarize_method(stochastic3),
        "independent_checkpoint_greedy_3": summarize_method(answer3),
        "single_checkpoint_greedy_1": summarize_method(answer1),
        "generation_diversity": generation_diversity(generations),
        "stochastic_3_minus_greedy_1": paired_suite_rows(
            stochastic3,
            answer1,
            left_label="Same-checkpoint-stochastic-3",
            right_label="Single-checkpoint-greedy-1",
            samples=samples,
            seed=seed,
        ),
        "checkpoint_3_minus_greedy_1": paired_suite_rows(
            answer3,
            answer1,
            left_label="Independent-checkpoint-greedy-3",
            right_label="Single-checkpoint-greedy-1",
            samples=samples,
            seed=seed + 10,
        ),
        "checkpoint_3_minus_stochastic_3": paired_suite_rows(
            answer3,
            stochastic3,
            left_label="Independent-checkpoint-greedy-3",
            right_label="Same-checkpoint-stochastic-3",
            samples=samples,
            seed=seed + 20,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()

    result: dict[str, Any] = {
        "control": "fixed Answer2027 checkpoint, three non-adaptive stochastic samples versus one and three greedy checkpoints",
        "decoding": {
            "same_checkpoint": "Answer2027",
            "sampling_seeds": [3101, 3102, 3103],
            "temperature": 0.8,
            "top_p": 0.95,
            "candidate_budget": 3,
            "prompt": "D full authentic trajectory",
        },
        "test_outcomes_used_for_configuration": False,
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        split_root = args.eval_root / split
        answer1_path = (
            args.reference_root / "answer-seen-test.evaluation.jsonl"
            if split == "seen"
            else args.reference_root
            / "answer-seed-control"
            / "answer2027-unseen-test.evaluation.jsonl"
        )
        result["splits"][split] = analyze_split(
            read_jsonl(split_root / "stochastic3.evaluation.jsonl"),
            read_jsonl(
                args.reference_root
                / "selected-portfolios"
                / f"answer-3seed-{split}-test.evaluation.jsonl"
            ),
            read_jsonl(answer1_path),
            [
                read_jsonl(split_root / f"sample-{sampling_seed}.generations.jsonl")
                for sampling_seed in (3101, 3102, 3103)
            ],
            samples=args.samples,
            seed=2027 + offset * 100,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
