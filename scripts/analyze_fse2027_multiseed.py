#!/usr/bin/env python3
"""Aggregate code-free multi-seed stability statistics for the FSE study."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def summarize(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    problems = {str(row["problem_id"]) for row in rows}
    return {
        "examples": len(rows),
        "problems": len(problems),
        "pr": sum(float(row["fixed_pass_rate"]) for row in rows) / len(rows),
        "rr": sum(bool(row["repaired"]) for row in rows) / len(rows),
        "ir": sum(bool(row["improved"]) for row in rows) / len(rows),
    }


def aggregate(per_seed: dict[str, dict[str, float | int]]) -> dict[str, Any]:
    result: dict[str, Any] = {"seeds": per_seed}
    for metric in ("pr", "rr", "ir"):
        values = [float(summary[metric]) for summary in per_seed.values()]
        mean = sum(values) / len(values)
        result[metric] = {
            "mean": mean,
            "sample_sd": (
                math.sqrt(sum((value - mean) ** 2 for value in values) / (len(values) - 1))
                if len(values) > 1
                else 0.0
            ),
            "minimum": min(values),
            "maximum": max(values),
            "range": max(values) - min(values),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--robustness", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", default=("2028", "2029"))
    args = parser.parse_args()

    root = args.eval_root.expanduser().resolve()
    robustness = json.loads(args.robustness.read_text(encoding="utf-8"))
    by_split: dict[str, dict[str, dict[str, float | int]]] = defaultdict(dict)
    by_split["seen"]["2027"] = robustness["comparisons"][
        "seen_no_feedback_vs_zero"
    ]["left_summary"]
    by_split["unseen"]["2027"] = robustness["comparisons"][
        "unseen_no_feedback_vs_zero"
    ]["left_summary"]

    for seed in args.seeds:
        for split in ("seen", "unseen"):
            path = root / "acceptance-seeds" / f"seed-{seed}-{split}-test.evaluation.jsonl"
            if not path.is_file():
                raise FileNotFoundError(path)
            by_split[split][str(seed)] = summarize(read_jsonl(path))

    report = {
        "schema_version": 1,
        "training_seeds": [2027, *[int(seed) for seed in args.seeds]],
        "splits": {split: aggregate(per_seed) for split, per_seed in by_split.items()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
