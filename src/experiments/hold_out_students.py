#!/usr/bin/env python3
"""Drop from a training or validation dataset every (problem, student) pair listed in a test split (e.g. the RQ1 benchmark's)."""
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("test_split", type=Path, help="splits/test.jsonl written by build-data")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.test_split.open(encoding="utf-8") as f:
        held_out = {(row["problem_id"], row["user_id"]) for row in map(json.loads, f)}
    kept = 0
    with args.dataset.open(encoding="utf-8") as source, args.output.open("w", encoding="utf-8") as output:
        for line in source:
            row = json.loads(line)
            if (row["problem_id"], row["user_id"]) not in held_out:
                output.write(line)
                kept += 1
    print(json.dumps({"output": str(args.output), "kept": kept}))


if __name__ == "__main__":
    main()
