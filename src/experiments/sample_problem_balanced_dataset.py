#!/usr/bin/env python3
"""Select one deterministic validation example per problem."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def select(rows: list[Row], seed: int) -> list[Row]:
    grouped: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        grouped[str(row["problem_id"])].append(row)

    def key(row: Row) -> str:
        payload = f"{seed}:{row['example_id']}".encode()
        return hashlib.sha256(payload).hexdigest()

    return [min(grouped[problem], key=key) for problem in sorted(grouped)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    selected = select(rows, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in selected:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "input_examples": len(rows),
                "selected_examples": len(selected),
                "problems": len({row["problem_id"] for row in selected}),
                "seed": args.seed,
                "rule": "minimum sha256(seed:example_id) within problem",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
