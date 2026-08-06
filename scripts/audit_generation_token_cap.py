#!/usr/bin/env python3
"""Fail closed when any saved model completion exceeds the declared token cap."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def completion_texts(row: dict[str, Any]) -> Iterable[str]:
    raw = row.get("raw_generation")
    if isinstance(raw, str) and raw:
        yield raw
    for key in ("patches", "candidate_outcomes"):
        for candidate in row.get(key, []):
            raw = candidate.get("raw_generation")
            if isinstance(raw, str) and raw:
                yield raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, action="append", required=True)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--cap", type=int, required=True)
    parser.add_argument("--decoded-slack", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.cap < 1:
        parser.error("--cap must be positive")

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, use_fast=True)
    unique: dict[str, str] = {}
    locations: dict[str, list[dict[str, str]]] = {}
    roots = [root.resolve() for root in args.input_root]
    files = sorted(path for root in roots for path in root.rglob("*.jsonl"))
    occurrences = 0
    for path in files:
        for row in iter_jsonl(path):
            for text in completion_texts(row):
                occurrences += 1
                digest = hashlib.sha256(text.encode()).hexdigest()
                unique.setdefault(digest, text)
                if len(locations.setdefault(digest, [])) < 20:
                    locations[digest].append(
                        {
                            "path": next(
                                f"{root.name}/{path.relative_to(root)}"
                                for root in roots
                                if path.is_relative_to(root)
                            ),
                            "example_id": str(row.get("example_id", "")),
                            "method": str(row.get("method", "")),
                        }
                    )
    lengths = {
        digest: len(tokenizer(text, add_special_tokens=False)["input_ids"])
        for digest, text in unique.items()
    }
    decoded_limit = args.cap + args.decoded_slack
    over = sorted(
        ((digest, length) for digest, length in lengths.items() if length > decoded_limit),
        key=lambda item: item[1],
        reverse=True,
    )
    report = {
        "input_roots": [str(root) for root in roots],
        "jsonl_files_scanned": len(files),
        "completion_occurrences": occurrences,
        "unique_completions": len(unique),
        "tokenizer": args.tokenizer,
        "cap_new_tokens": args.cap,
        "decoded_retokenization_slack": args.decoded_slack,
        "decoded_token_limit": decoded_limit,
        "maximum_completion_tokens": max(lengths.values(), default=0),
        "completions_at_or_above_cap_within_slack": sum(
            args.cap <= length <= decoded_limit for length in lengths.values()
        ),
        "completions_over_decoded_limit": len(over),
        "over_cap": [
            {
                "sha256": digest,
                "tokens": length,
                "locations": locations[digest],
            }
            for digest, length in over
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    if over:
        raise SystemExit(
            f"{len(over)} saved completions exceed decoded token limit {decoded_limit}"
        )


if __name__ == "__main__":
    main()
