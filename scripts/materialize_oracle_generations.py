#!/usr/bin/env python3
"""Materialize recorded targets as generations for evaluator validation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with args.dataset.open(encoding="utf-8") as source, args.output.open(
        "w", encoding="utf-8"
    ) as destination:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            destination.write(
                json.dumps(
                    {
                        "example_id": row["example_id"],
                        "problem_id": row["problem_id"],
                        "user_id": row["user_id"],
                        "method": "RecordedOracle",
                        "generated_code": row["target_code"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            count += 1
    print(json.dumps({"examples": count, "output": str(args.output)}))


if __name__ == "__main__":
    main()
