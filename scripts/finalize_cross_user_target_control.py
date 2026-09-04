#!/usr/bin/env python3
"""Merge matched-control shards and jointly enforce the 4K training cap."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Callable

from src.repair.prompts import build_messages, render_generation_prompt


Row = dict[str, Any]


def read_shards(root: Path, stem: str) -> list[Row]:
    rows: list[Row] = []
    paths = sorted(
        root.glob(f"{stem}-*.jsonl"),
        key=lambda path: int(path.stem.rsplit("-", 1)[1]),
    )
    for path in paths:
        with path.open(encoding="utf-8") as source:
            rows.extend(json.loads(line) for line in source if line.strip())
    return rows


def finalize(
    shard_root: Path,
    same_output: Path,
    cross_output: Path,
    *,
    total_tokens: Callable[[Row], int],
    maximum_tokens: int = 4096,
) -> dict[str, Any]:
    same_rows = read_shards(shard_root, "same")
    cross_rows = read_shards(shard_root, "cross")
    same = {str(row["example_id"]): row for row in same_rows}
    cross = {str(row["example_id"]): row for row in cross_rows}
    if len(same) != len(same_rows) or len(cross) != len(cross_rows):
        raise ValueError("duplicate example IDs across shards")
    if set(same) != set(cross):
        raise ValueError("same-user and cross-user shard IDs differ")
    retained: list[tuple[Row, Row]] = []
    overlength = 0
    for example_id in sorted(same):
        left, right = same[example_id], cross[example_id]
        if left["history"] != right["history"]:
            raise ValueError(f"current histories differ: {example_id}")
        if total_tokens(left) > maximum_tokens or total_tokens(right) > maximum_tokens:
            overlength += 1
            continue
        retained.append((left, right))
    for path, index in ((same_output, 0), (cross_output, 1)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as destination:
            for pair in retained:
                destination.write(json.dumps(pair[index], ensure_ascii=False) + "\n")
    own = [int(left["target_token_edit_distance"]) for left, _right in retained]
    matched = [int(left["matched_target_token_edit_distance"]) for left, _right in retained]
    return {
        "matched_before_token_cap": len(same_rows),
        "overlength_pairs_excluded": overlength,
        "written_examples_per_condition": len(retained),
        "problems": len({str(left["problem_id"]) for left, _right in retained}),
        "maximum_total_tokens": maximum_tokens,
        "same_user_target_distance_mean": statistics.fmean(own) if own else None,
        "cross_user_target_distance_mean": statistics.fmean(matched) if matched else None,
        "same_user_target_distance_median": statistics.median(own) if own else None,
        "cross_user_target_distance_median": statistics.median(matched) if matched else None,
        "same_user_output": str(same_output),
        "cross_user_output": str(cross_output),
    }


def main() -> None:
    from transformers import AutoTokenizer

    parser = argparse.ArgumentParser()
    parser.add_argument("shard_root", type=Path)
    parser.add_argument("same_output", type=Path)
    parser.add_argument("cross_output", type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--prompt", default="D")
    parser.add_argument("--maximum-tokens", type=int, default=4096)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)

    def total_tokens(row: Row) -> int:
        prompt = render_generation_prompt(tokenizer, build_messages(row, args.prompt))
        return (
            len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
            + len(
                tokenizer(
                    str(row["target_code"]).rstrip(), add_special_tokens=False
                )["input_ids"]
            )
            + 1
        )

    result = finalize(
        args.shard_root,
        args.same_output,
        args.cross_output,
        total_tokens=total_tokens,
        maximum_tokens=args.maximum_tokens,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
