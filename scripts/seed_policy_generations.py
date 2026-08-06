#!/usr/bin/env python3
"""Seed a generation JSONL from compatible batch-1 experiment artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def add_candidate(candidates: dict[str, Row], row: Row) -> None:
    example_id = str(row["example_id"])
    previous = candidates.get(example_id)
    if previous is not None and previous["generated_code"] != row["generated_code"]:
        raise ValueError(f"conflicting batch-1 candidates for {example_id}")
    candidates[example_id] = row


def seed_rows(
    dataset: list[Row],
    *,
    method: str,
    generation_sources: list[list[Row]],
    sequential_sources: list[tuple[str, list[Row]]],
) -> list[Row]:
    requested = {str(row["example_id"]): row for row in dataset}
    candidates: dict[str, Row] = {}
    for rows in generation_sources:
        for row in rows:
            example_id = str(row["example_id"])
            if example_id in requested:
                add_candidate(candidates, dict(row))
    for source, rows in sequential_sources:
        for row in rows:
            example_id = str(row["example_id"])
            if example_id not in requested:
                continue
            matches = [
                candidate
                for candidate in row.get("candidate_outcomes", [])
                if candidate.get("source") == source
            ]
            if len(matches) > 1:
                raise ValueError(f"multiple {source} candidates for {example_id}")
            if not matches:
                continue
            candidate = matches[0]
            add_candidate(
                candidates,
                {
                    "example_id": example_id,
                    "problem_id": row["problem_id"],
                    "user_id": row["user_id"],
                    "method": method,
                    "prompt_style": str(row.get("prompt_style", "D")),
                    "generation_time_sec": float(
                        candidate.get("generation_time_sec", 0.0)
                    ),
                    "generated_code": candidate["generated_code"],
                    "raw_generation": candidate.get(
                        "raw_generation", candidate["generated_code"]
                    ),
                    "reused_from_sequential_evaluation": True,
                },
            )
    result = []
    for row in dataset:
        example_id = str(row["example_id"])
        if example_id not in candidates:
            continue
        candidate = dict(candidates[example_id])
        candidate["method"] = method
        result.append(candidate)
    return result


def parse_source(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ValueError("sequential source must use SOURCE=PATH")
    source, raw_path = value.split("=", 1)
    return source, Path(raw_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--method", required=True)
    parser.add_argument("--generations", type=Path, action="append", default=[])
    parser.add_argument("--sequential-evaluation", action="append", default=[])
    args = parser.parse_args()
    dataset = read_jsonl(args.dataset)
    rows = seed_rows(
        dataset,
        method=args.method,
        generation_sources=[read_jsonl(path) for path in args.generations],
        sequential_sources=[
            (source, read_jsonl(path))
            for source, path in map(parse_source, args.sequential_evaluation)
        ],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"requested": len(dataset), "reused": len(rows)}))


if __name__ == "__main__":
    main()
