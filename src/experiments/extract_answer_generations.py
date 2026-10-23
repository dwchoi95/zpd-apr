#!/usr/bin/env python3
"""Extract batch-1 Answer candidates from no-feedback sequential evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def extract(
    dataset: list[Row],
    sequential_rows: list[Row],
    *,
    method: str,
) -> list[Row]:
    requested = {str(row["example_id"]): row for row in dataset}
    if len(requested) != len(dataset):
        raise ValueError("dataset contains duplicate example_id values")
    extracted: dict[str, Row] = {}
    for row in sequential_rows:
        example_id = str(row["example_id"])
        if example_id not in requested:
            continue
        candidates = [
            candidate
            for candidate in row.get("candidate_outcomes", [])
            if candidate.get("source") == "Answer"
        ]
        if len(candidates) > 1:
            raise ValueError(f"multiple Answer candidates for {example_id}")
        if not candidates:
            continue
        candidate = candidates[0]
        extracted[example_id] = {
            "example_id": example_id,
            "problem_id": row["problem_id"],
            "user_id": row["user_id"],
            "method": method,
            "prompt_style": str(row.get("prompt_style", "D")),
            "generation_time_sec": float(candidate.get("generation_time_sec", 0.0)),
            "generated_code": candidate["generated_code"],
            "raw_generation": candidate.get(
                "raw_generation", candidate["generated_code"]
            ),
            "reused_from_sequential_evaluation": True,
        }
    return [
        extracted[str(row["example_id"])]
        for row in dataset
        if str(row["example_id"]) in extracted
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("sequential_evaluation", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--method", required=True)
    args = parser.parse_args()
    rows = extract(
        read_jsonl(args.dataset),
        read_jsonl(args.sequential_evaluation),
        method=args.method,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"requested": len(read_jsonl(args.dataset)), "reused": len(rows)}))


if __name__ == "__main__":
    main()
