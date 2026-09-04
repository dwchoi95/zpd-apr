#!/usr/bin/env python3
"""Analyze the recommended Answer-3Seed portfolio over all trajectory prefixes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import read_jsonl, summarize_method
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import read_jsonl, summarize_method


def analyze_split(root: Path, dataset: Path, split: str) -> dict[str, Any]:
    records = read_jsonl(dataset)
    metadata = {str(row["example_id"]): row for row in records}
    answer = read_jsonl(root / split / "answer3.evaluation.jsonl")
    answer_by_id = {str(row["example_id"]): row for row in answer}
    if set(metadata) != set(answer_by_id):
        raise ValueError(f"{split}: dataset and evaluation IDs differ")

    def subset(rows: dict[str, dict[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
        return [rows[example_id] for example_id in ids]

    strata: dict[str, Any] = {}
    for phase_name in ("early", "middle", "last"):
        ids = sorted(
            example_id
            for example_id, row in metadata.items()
            if row["trajectory_phase"] == phase_name
        )
        selected = subset(answer_by_id, ids)
        strata[phase_name] = {
            "examples": len(ids),
            "problems": len({str(metadata[example_id]["problem_id"]) for example_id in ids}),
            "answer": summarize_method(selected) if ids else None,
        }
    return {
        "overall": summarize_method(answer),
        "by_trajectory_phase": strata,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seen-dataset", type=Path, required=True)
    parser.add_argument("--unseen-dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result = {
        "design": "All locally non-AC prefixes from eventually accepted held-out trajectories, current-only prompts, and the three independently trained full-Answer checkpoints used by the recommended deployment.",
        "splits": {
            "seen": analyze_split(args.root, args.seen_dataset, "seen"),
            "unseen": analyze_split(args.root, args.unseen_dataset, "unseen"),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
