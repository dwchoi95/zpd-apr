#!/usr/bin/env python3
"""Materialize isolated Java compilation units for CodeWorkout submissions."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SAFE_ID = re.compile(r"^[0-9a-f]{40}$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.input.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            submission_id = str(row["submission_id"])
            if not SAFE_ID.fullmatch(submission_id):
                raise ValueError(f"unsafe CodeStateID: {submission_id!r}")
            path = args.output_dir / f"{submission_id}.java"
            if not path.exists():
                path.write_text(
                    f"class Submission_{submission_id} {{\n{row['code']}\n}}\n",
                    encoding="utf-8",
                )
                written += 1
    total = len(list(args.output_dir.glob("*.java")))
    print(json.dumps({"written": written, "source_files": total}, sort_keys=True))


if __name__ == "__main__":
    main()
