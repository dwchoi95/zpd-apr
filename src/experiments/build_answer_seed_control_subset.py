#!/usr/bin/env python3
"""Keep only examples not repaired by any earlier Answer-seed stage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--previous-evaluation", type=Path, action="append", default=[])
    args = parser.parse_args()

    records = read_jsonl(args.dataset)
    by_id = {str(row["example_id"]): row for row in records}
    if len(by_id) != len(records):
        raise ValueError("dataset contains duplicate example_id values")

    repaired: set[str] = set()
    for path in args.previous_evaluation:
        rows = read_jsonl(path)
        for row in rows:
            example_id = str(row["example_id"])
            if example_id not in by_id:
                raise ValueError(f"evaluation ID absent from dataset: {example_id}")
            if bool(row["repaired"]):
                repaired.add(example_id)

    retained = [row for row in records if str(row["example_id"]) not in repaired]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in retained:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "input_examples": len(records),
                "previously_repaired": len(repaired),
                "retained_examples": len(retained),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
