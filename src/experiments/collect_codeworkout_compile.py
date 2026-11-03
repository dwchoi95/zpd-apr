#!/usr/bin/env python3
"""Collect per-submission container compile statuses into canonical JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("submissions", type=Path)
    parser.add_argument("status_dir", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.submissions.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    problem_by_id = {str(row["submission_id"]): row["problem_id"] for row in rows}
    if len(problem_by_id) != len(rows):
        raise ValueError("duplicate submission_id")
    statuses = {}
    for path in args.status_dir.glob("*.status"):
        submission_id, raw_compiles, raw_returncode = path.read_text(
            encoding="utf-8"
        ).strip().split("\t")
        statuses[submission_id] = {
            "submission_id": submission_id,
            "problem_id": problem_by_id[submission_id],
            "compiles": raw_compiles == "true",
            "timed_out": int(raw_returncode) == 124,
            "returncode": int(raw_returncode),
        }
    missing = set(problem_by_id) - set(statuses)
    extra = set(statuses) - set(problem_by_id)
    if missing or extra:
        raise ValueError(f"compile status mismatch: missing={len(missing)}, extra={len(extra)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for submission_id in sorted(statuses):
            destination.write(json.dumps(statuses[submission_id]) + "\n")
    print(
        json.dumps(
            {
                "submissions": len(statuses),
                "compiles": sum(row["compiles"] for row in statuses.values()),
                "compile_failures": sum(
                    not row["compiles"] for row in statuses.values()
                ),
                "timeouts": sum(row["timed_out"] for row in statuses.values()),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
