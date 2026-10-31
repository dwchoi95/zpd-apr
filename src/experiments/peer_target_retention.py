#!/usr/bin/env python3
"""Token retention of each Answer training target: the student's own accepted program and the two peer replacements.

Writes one row per training example with the share of the current submission's tokens that each target keeps (the
paper's token retention), so the targets can be compared without the student programs.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.core.retention import _python_tokens, _retained_fraction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("own", type=Path, help="Answer training dataset")
    parser.add_argument("closest", type=Path, help="the same dataset with closest peer targets")
    parser.add_argument("random", type=Path, help="the same dataset with random peer targets")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    load = lambda path: {row["example_id"]: row for row in map(json.loads, path.open(encoding="utf-8"))}
    own, closest, random = load(args.own), load(args.closest), load(args.random)
    with args.output.open("w", encoding="utf-8") as output:
        for key, row in closest.items():
            source = row["history"][-1]["code"]
            assert own[key]["history"][-1]["code"] == source == random[key]["history"][-1]["code"]
            kept = {name: _retained_fraction(_python_tokens(source), _python_tokens(rows[key]["target_code"]))
                    for name, rows in (("own", own), ("closest", closest), ("random", random))}
            output.write(json.dumps({"example_id": key, "problem_id": row["problem_id"], **kept}) + "\n")


if __name__ == "__main__":
    main()
