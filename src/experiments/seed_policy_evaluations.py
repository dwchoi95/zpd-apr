#!/usr/bin/env python3
"""Seed individual-policy outcomes from an earlier sequential evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def seed_rows(
    dataset: list[Row],
    generations: list[Row],
    existing: list[Row],
    *,
    method: str,
    source: str,
    sequential: list[Row],
    flat: list[Row] | None = None,
) -> list[Row]:
    records = {str(row["example_id"]): row for row in dataset}
    generation_by_id = {str(row["example_id"]): row for row in generations}
    sequential_by_id = {str(row["example_id"]): row for row in sequential}
    if len(records) != len(dataset) or len(generation_by_id) != len(generations):
        raise ValueError("duplicate example_id")

    result = {str(row["example_id"]): row for row in existing}
    if len(result) != len(existing):
        raise ValueError("duplicate existing evaluation")
    flat_seeded_ids: set[str] = set()
    for row in flat or []:
        example_id = str(row["example_id"])
        generation = generation_by_id.get(example_id)
        if generation is None or str(row.get("generated_code", "")) != str(
            generation.get("generated_code", "")
        ):
            continue
        if example_id in flat_seeded_ids:
            continue
        result[example_id] = {**row, **generation, "method": method}
        flat_seeded_ids.add(example_id)
    for example_id, generation in generation_by_id.items():
        if example_id in result:
            if str(result[example_id].get("generated_code", "")) != str(
                generation.get("generated_code", "")
            ):
                raise ValueError(f"generated code changed for {example_id}")
            continue
        parent = sequential_by_id.get(example_id)
        if parent is None:
            continue
        matches = [
            candidate
            for candidate in parent.get("candidate_outcomes", [])
            if candidate.get("source") == source
            and str(candidate.get("generated_code", ""))
            == str(generation.get("generated_code", ""))
        ]
        if len(matches) > 1:
            raise ValueError(f"multiple matching {source} candidates for {example_id}")
        if not matches:
            continue
        candidate = matches[0]
        record = records[example_id]
        buggy_code = str(record["history"][-1]["code"])
        fixed_code = str(generation.get("generated_code", ""))
        buggy_pass_rate = float(parent["buggy_pass_rate"])
        fixed_pass_rate = float(candidate["fixed_pass_rate"])
        generation_time = float(generation.get("generation_time_sec", 0.0))
        fixed_execution_time = float(candidate.get("execution_time_sec", 0.0))
        result[example_id] = {
            **generation,
            "method": method,
            "problem_id": parent["problem_id"],
            "user_id": parent["user_id"],
            "buggy_execution_time_sec": 0.0,
            "fixed_execution_time_sec": fixed_execution_time,
            "execution_time_sec": fixed_execution_time,
            "online_time_sec": generation_time + fixed_execution_time,
            "buggy_verdict": parent.get("buggy_verdict"),
            "fixed_verdict": candidate.get("fixed_verdict"),
            "buggy_pass_rate": buggy_pass_rate,
            "fixed_pass_rate": fixed_pass_rate,
            "repaired": fixed_code.strip() != buggy_code.strip()
            and fixed_pass_rate == 1.0,
            "improved": fixed_pass_rate > buggy_pass_rate,
            "ted_buggy_fixed": None,
            "ted_fixed_oracle": None,
            "tree_edit_distance": None,
            "fixed_tc_outcomes": candidate.get("fixed_tc_outcomes", {}),
            "execution_reused_from": str(source),
        }
    return [result[key] for key in sorted(result)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("generations", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--method", required=True)
    parser.add_argument("--source", required=True, help="NAME=SEQUENTIAL_EVALUATION")
    parser.add_argument(
        "--flat",
        type=Path,
        action="append",
        default=[],
        help="Compatible individual evaluation; may be repeated",
    )
    args = parser.parse_args()
    if "=" not in args.source:
        parser.error("--source must use NAME=PATH")
    source, raw_path = args.source.split("=", 1)
    existing = read_jsonl(args.output) if args.output.is_file() else []
    rows = seed_rows(
        read_jsonl(args.dataset),
        read_jsonl(args.generations),
        existing,
        method=args.method,
        source=source,
        sequential=read_jsonl(Path(raw_path)),
        flat=[row for path in args.flat for row in read_jsonl(path)],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".seed.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(args.output)
    print(json.dumps({"requested": len(read_jsonl(args.generations)), "seeded": len(rows)}))


if __name__ == "__main__":
    main()
