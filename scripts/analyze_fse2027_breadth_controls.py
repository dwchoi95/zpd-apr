#!/usr/bin/env python3
"""Analyze decoding-matched checkpoint diversity, temperature, and base breadth."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
    from analyze_stochastic_one_decomposition import mean_single_summary
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
    from scripts.analyze_stochastic_one_decomposition import mean_single_summary


TEMPERATURES = ("0.2", "0.4", "0.6", "0.8", "1.0")
EXTRA_TEMPERATURES = ("1.2", "1.5")
SEEDS = (4101, 4102, 4103)


def stochastic_family(root: Path) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
    union = read_jsonl(root / "stochastic3.evaluation.jsonl")
    singles = [read_jsonl(root / f"sample-{seed}.evaluation.jsonl") for seed in SEEDS]
    return union, singles


def analyze_split(root: Path, reference_root: Path, split: str, *, samples: int, seed: int,
                  extra_temperature_root: Path | None = None) -> dict[str, Any]:
    sweep: dict[str, Any] = {}
    for offset, temperature in enumerate(TEMPERATURES):
        union, singles = stochastic_family(root / "temperature" / temperature / split)
        sweep[temperature] = {
            "union": summarize_method(union),
            "single_draw_expectation": mean_single_summary(singles),
        }
    if extra_temperature_root is not None:
        for temperature in EXTRA_TEMPERATURES:
            union, singles = stochastic_family(
                extra_temperature_root / temperature / split
            )
            sweep[temperature] = {
                "union": summarize_method(union),
                "single_draw_expectation": mean_single_summary(singles),
            }

    same_checkpoint, _ = stochastic_family(root / "temperature" / "0.8" / split)
    checkpoint_stochastic = read_jsonl(
        root / "checkpoint-stochastic" / split / "stochastic3.evaluation.jsonl"
    )
    base_union, base_singles = stochastic_family(root / "base-stochastic" / split)
    greedy_three = read_jsonl(
        reference_root
        / "answer-seed-control"
        / f"answer-seeds-{split}-test.evaluation.jsonl"
    )
    return {
        "temperature_sweep": sweep,
        "decoding_matched_checkpoint_diversity": {
            "three_checkpoint_stochastic": summarize_method(checkpoint_stochastic),
            "one_checkpoint_stochastic": summarize_method(same_checkpoint),
            "three_checkpoint_minus_one_checkpoint": paired_suite_rows(
                checkpoint_stochastic,
                same_checkpoint,
                left_label="Three-checkpoint-stochastic-3",
                right_label="One-checkpoint-stochastic-3",
                samples=samples,
                seed=seed,
            ),
            "three_checkpoint_stochastic_minus_greedy": paired_suite_rows(
                checkpoint_stochastic,
                greedy_three,
                left_label="Three-checkpoint-stochastic-3",
                right_label="Three-checkpoint-greedy-3",
                samples=samples,
                seed=seed + 1,
            ),
        },
        "sft_free_breadth": {
            "base_three_draw_union": summarize_method(base_union),
            "base_single_draw_expectation": mean_single_summary(base_singles),
            "answer_three_draw_union": summarize_method(same_checkpoint),
            "answer_minus_base_three_draw": paired_suite_rows(
                same_checkpoint,
                base_union,
                left_label="Answer-SFT-stochastic-3",
                right_label="Base-stochastic-3",
                samples=samples,
                seed=seed + 2,
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extra-temperature-root", type=Path)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result = {
        "protocol": "test outcomes never tune temperature or choose a checkpoint; all fixed cells are reported",
        "temperatures": [
            float(value)
            for value in (
                TEMPERATURES
                if args.extra_temperature_root is None
                else TEMPERATURES + EXTRA_TEMPERATURES
            )
        ],
        "sampling_seeds": list(SEEDS),
        "top_p": 0.95,
        "splits": {
            split: analyze_split(
                args.root,
                args.reference_root,
                split,
                samples=args.samples,
                seed=6200 + offset * 100,
                extra_temperature_root=args.extra_temperature_root,
            )
            for offset, split in enumerate(("seen", "unseen"))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
