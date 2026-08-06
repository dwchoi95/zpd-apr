#!/usr/bin/env python3
"""Seed always-three LSGen replay from every reusable legacy candidate prefix."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.repair.evaluate import budget_bounded_tree_edit_distance, tree_edit_distance


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def select_unrestricted(patches: list[Row]) -> Row:
    accepted = [patch for patch in patches if float(patch["fixed_pass_rate"]) == 1.0]
    if accepted:
        return accepted[0]
    return max(
        patches,
        key=lambda patch: (
            float(patch["fixed_pass_rate"]),
            -(
                float(patch["ted_buggy_fixed"])
                if patch["ted_buggy_fixed"] is not None
                else float("inf")
            ),
            -int(patch["patch_index"]),
        ),
    )


def _candidate_ted(task: tuple[str, str]) -> int | None:
    original, generated = task
    if generated.strip() == original.strip():
        return 0
    return budget_bounded_tree_edit_distance(
        original, generated, maximum_budget=160
    )


def seed_rows(
    dataset: list[Row],
    legacy: list[Row],
    *,
    completion_allowed: Callable[[str], bool] = lambda _text: True,
    workers: int = 1,
) -> list[Row]:
    legacy_by_id = {str(row["example_id"]): row for row in legacy}
    eligible: list[tuple[Row, Row]] = []
    tasks: list[tuple[str, str]] = []
    for record in dataset:
        row = legacy_by_id.get(str(record["example_id"]))
        if row is None or not 1 <= len(row.get("patches", [])) <= 3:
            continue
        if any(
            not completion_allowed(str(patch.get("raw_generation", "")))
            for patch in row["patches"]
        ):
            continue
        eligible.append((record, row))
        original = str(record["history"][-1]["code"])
        tasks.extend((original, str(patch["generated_code"])) for patch in row["patches"])
    if workers < 1:
        raise ValueError("workers must be positive")
    if workers == 1:
        ted_values = [_candidate_ted(task) for task in tasks]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            ted_values = list(executor.map(_candidate_ted, tasks, chunksize=1))

    seeded = []
    ted_offset = 0
    for record, row in eligible:
        example_id = str(record["example_id"])
        patches = copy.deepcopy(row["patches"])
        original = str(record["history"][-1]["code"])
        oracle = str(record["target_code"])
        for patch in patches:
            ted = ted_values[ted_offset]
            ted_offset += 1
            patch["ted_buggy_fixed"] = ted
            patch["tree_edit_distance"] = ted
            patch["ted_censored_above"] = 160 if ted == 161 else None
        selected = select_unrestricted(patches)
        generated = str(selected["generated_code"])
        fixed_pass_rate = float(selected["fixed_pass_rate"])
        repaired = generated.strip() != original.strip() and fixed_pass_rate == 1.0
        result = copy.deepcopy(row)
        result.update(
            {
                "generated_code": generated,
                "raw_generation": str(selected.get("raw_generation", "")),
                "fixed_verdict": selected["fixed_verdict"],
                "fixed_pass_rate": fixed_pass_rate,
                "repaired": repaired,
                "improved": fixed_pass_rate > float(row["buggy_pass_rate"]),
                "ted_buggy_fixed": selected["ted_buggy_fixed"] if repaired else None,
                "ted_fixed_oracle": (
                    tree_edit_distance(generated, oracle) if repaired else None
                ),
                "tree_edit_distance": (
                    selected["ted_buggy_fixed"] if repaired else None
                ),
                "fixed_tc_outcomes": selected["fixed_tc_outcomes"],
                "selected_patch_index": selected["patch_index"],
                "selected_source": selected["source"],
                "early_stop_stage": (
                    selected["source"] if fixed_pass_rate == 1.0 else None
                ),
                "patches": patches,
                "always_generate_max": len(patches) == 3,
                "seeded_from_legacy_candidate_prefix": True,
            }
        )
        seeded.append(result)
    return seeded


def preserve_complete_rows(seeded: list[Row], existing: list[Row]) -> list[Row]:
    """Prefer already completed always-three rows over legacy prefixes."""
    complete = {
        str(row["example_id"]): row
        for row in existing
        if len(row.get("patches", [])) >= 3
        and row.get("always_generate_max") is True
    }
    return [complete.get(str(row["example_id"]), row) for row in seeded]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tokenizer", required=True)
    parser.add_argument("--cap", type=int, default=4096)
    parser.add_argument("--decoded-slack", type=int, default=128)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument("--preserve-complete-from", type=Path)
    args = parser.parse_args()

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, use_fast=True)
    limit = args.cap + args.decoded_slack

    def allowed(text: str) -> bool:
        return len(tokenizer(text, add_special_tokens=False)["input_ids"]) <= limit

    dataset = read_jsonl(args.dataset)
    legacy = read_jsonl(args.legacy)
    rows = seed_rows(
        dataset,
        legacy,
        completion_allowed=allowed,
        workers=args.workers,
    )
    preserved = []
    if args.preserve_complete_from and args.preserve_complete_from.exists():
        preserved = [
            row
            for row in read_jsonl(args.preserve_complete_from)
            if all(
                allowed(str(patch.get("raw_generation", "")))
                for patch in row.get("patches", [])
            )
        ]
        rows = preserve_complete_rows(rows, preserved)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "dataset_examples": len(dataset),
                "legacy_examples": len(legacy),
                "seeded_examples": len(rows),
                "complete_seeded_examples": sum(
                    len(row["patches"]) == 3 for row in rows
                ),
                "completed_rows_preserved": sum(
                    len(row.get("patches", [])) >= 3
                    and row.get("always_generate_max") is True
                    for row in preserved
                ),
                "candidate_completions_reused": sum(
                    len(row["patches"]) for row in rows
                ),
                "decoded_token_limit": limit,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
