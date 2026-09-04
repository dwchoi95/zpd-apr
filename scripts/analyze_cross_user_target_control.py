#!/usr/bin/env python3
"""Analyze same-user versus outcome-and-distance-matched cross-user targets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method


def analyze_split(root: Path, split: str, *, samples: int, seed: int) -> dict[str, Any]:
    same = read_jsonl(root / split / "same-user3.evaluation.jsonl")
    cross = read_jsonl(root / split / "cross-user3.evaluation.jsonl")
    return {
        "same_user": summarize_method(same),
        "cross_user": summarize_method(cross),
        "same_user_minus_cross_user": paired_suite_rows(
            same,
            cross,
            left_label="Same-user-Progress3",
            right_label="Cross-user-matched-Progress3",
            samples=samples,
            seed=seed,
        ),
        "per_seed": {
            str(member_seed): paired_suite_rows(
                read_jsonl(root / split / f"same-user-{member_seed}.evaluation.jsonl"),
                read_jsonl(root / split / f"cross-user-{member_seed}.evaluation.jsonl"),
                left_label=f"Same-user-Progress-{member_seed}",
                right_label=f"Cross-user-matched-Progress-{member_seed}",
                samples=samples,
                seed=seed + member_seed,
            )
            for member_seed in (2027, 2028, 2029)
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--train-summary", type=Path, required=True)
    parser.add_argument("--valid-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result = {
        "design": "Exact current-source, target testcase-outcome, and token-distance-caliper control; only target user provenance differs.",
        "train_dataset": json.loads(args.train_summary.read_text()),
        "validation_dataset": json.loads(args.valid_summary.read_text()),
        "splits": {
            split: analyze_split(
                args.root, split, samples=args.samples, seed=9500 + index * 100
            )
            for index, split in enumerate(("seen", "unseen"))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
