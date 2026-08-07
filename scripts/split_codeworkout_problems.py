#!/usr/bin/env python3
"""Create a deterministic exercise-held-out split of CodeWorkout trajectories."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def split_problems(problems: list[str], seed: int) -> dict[str, str]:
    ordered = sorted(
        problems,
        key=lambda problem: hashlib.sha256(f"{seed}:{problem}".encode()).hexdigest(),
    )
    # With only 17 exercises, 60/20/20 retains at least three independent
    # validation and test clusters while leaving most trajectories for training.
    train_end = round(len(ordered) * 0.60)
    valid_end = train_end + round(len(ordered) * 0.20)
    return {
        problem: (
            "train" if index < train_end else "valid" if index < valid_end else "test"
        )
        for index, problem in enumerate(ordered)
    }


def apply_split(rows: list[Row], seed: int) -> tuple[list[Row], Row]:
    assignment = split_problems(sorted({str(row["problem_id"]) for row in rows}), seed)
    result = [{**row, "split": assignment[str(row["problem_id"])]} for row in rows]
    summary = {
        "schema_version": 1,
        "seed": seed,
        "split_unit": "problem",
        "trajectories": len(result),
        "problems_by_split": {
            split: sum(value == split for value in assignment.values())
            for split in ("train", "valid", "test")
        },
        "trajectories_by_split": dict(Counter(row["split"] for row in result)),
        "problem_assignment": dict(sorted(assignment.items())),
    }
    if min(summary["problems_by_split"].values()) < 1:
        raise ValueError("every split must contain at least one problem")
    return result, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line]
    result, summary = apply_split(rows, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in result),
        encoding="utf-8",
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
