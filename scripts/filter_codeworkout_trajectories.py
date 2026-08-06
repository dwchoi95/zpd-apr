#!/usr/bin/env python3
"""Exclude whole CodeWorkout trajectories whose largest configuration exceeds a token budget."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from transformers import AutoTokenizer

from scripts.build_codeworkout_repair_datasets import canonical_submission, payload
from scripts.build_codeworkout_trajectories import split_users
from src.repair.prompts import build_messages, render_generation_prompt


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def total_tokens(trajectory: Row, tokenizer: Any, prompt_style: str) -> int:
    submissions = [
        (index, canonical_submission(item))
        for index, item in enumerate(trajectory["submissions"], start=1)
    ]
    record = payload(trajectory, submissions[:-1], submissions[-1], "final")
    prompt = render_generation_prompt(tokenizer, build_messages(record, prompt_style))
    prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    target_ids = tokenizer(str(record["target_code"]).rstrip(), add_special_tokens=False)[
        "input_ids"
    ]
    return len(prompt_ids) + len(target_ids) + 1


def filter_trajectories(
    trajectories: list[Row], tokenizer: Any, max_tokens: int, seed: int
) -> tuple[list[Row], Row]:
    retained = []
    excluded = []
    for trajectory in trajectories:
        length = total_tokens(trajectory, tokenizer, "D")
        if length > max_tokens:
            excluded.append(
                {"trajectory_id": trajectory["trajectory_id"], "total_tokens": length}
            )
        else:
            retained.append(dict(trajectory))
    assignments = split_users(
        sorted({str(row["user_id"]) for row in retained}), seed
    )
    for row in retained:
        row["split"] = assignments[str(row["user_id"])]
    summary = {
        "schema_version": 1,
        "max_total_tokens": max_tokens,
        "split_unit": "student",
        "input_trajectories": len(trajectories),
        "retained_trajectories": len(retained),
        "excluded_trajectories": len(excluded),
        "excluded": excluded,
        "trajectories_by_split": {
            split: sum(row["split"] == split for row in retained)
            for split in ("train", "valid", "test")
        },
        "students_by_split": {
            split: len({row["user_id"] for row in retained if row["split"] == split})
            for split in ("train", "valid", "test")
        },
        "problems_by_split": {
            split: len({row["problem_id"] for row in retained if row["split"] == split})
            for split in ("train", "valid", "test")
        },
        "student_overlap": 0,
    }
    return retained, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--max-total-tokens", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    retained, summary = filter_trajectories(
        read_jsonl(args.input), tokenizer, args.max_total_tokens, args.seed
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in retained:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
