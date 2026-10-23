#!/usr/bin/env python3
"""Remove legacy runaway completions before capped deterministic regeneration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--cap", type=int, required=True)
    parser.add_argument("--decoded-slack", type=int, default=128)
    args = parser.parse_args()
    if not args.path.exists():
        print(json.dumps({"path": str(args.path), "rows": 0, "removed": 0}))
        return

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, use_fast=True)
    rows = [json.loads(line) for line in args.path.read_text(encoding="utf-8").splitlines() if line.strip()]
    retained = []
    removed = []
    limit = args.cap + args.decoded_slack
    for row in rows:
        raw = str(row.get("raw_generation", ""))
        length = len(tokenizer(raw, add_special_tokens=False)["input_ids"])
        if length > limit:
            removed.append({"example_id": str(row["example_id"]), "decoded_tokens": length})
        else:
            retained.append(row)
    temporary = args.path.with_suffix(args.path.suffix + ".cap-filter.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        for row in retained:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(args.path)
    print(
        json.dumps(
            {
                "path": str(args.path),
                "rows": len(rows),
                "retained": len(retained),
                "removed": len(removed),
                "removed_rows": removed,
                "decoded_token_limit": limit,
            }
        )
    )


if __name__ == "__main__":
    main()
