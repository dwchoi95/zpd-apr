#!/usr/bin/env python3
"""Analyze RQ2 on behavior-matched, near-duplicate current programs."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import keyed, paired_suite_rows, read_jsonl
except ModuleNotFoundError:  # Imported as scripts.analyze_history_matched_rq2.
    from scripts.analyze_fse2027_robustness import keyed, paired_suite_rows, read_jsonl


Row = dict[str, Any]


def normalize(code: str) -> str:
    return re.sub(r"\s+", " ", code).strip()


def matched_ids(
    dataset: list[Row], evaluation: list[Row], *, similarity: float
) -> tuple[set[str], dict[str, int]]:
    eval_by_id = keyed(evaluation)
    groups: dict[tuple[str, str, float], list[Row]] = defaultdict(list)
    for row in dataset:
        example_id = str(row["example_id"])
        peer = eval_by_id[example_id]
        groups[
            (
                str(row["problem_id"]),
                str(peer["buggy_verdict"]),
                round(float(peer["buggy_pass_rate"]), 12),
            )
        ].append(row)
    selected: set[str] = set()
    matched_pairs = 0
    different_target_pairs = 0
    for rows in groups.values():
        for left, right in combinations(rows, 2):
            if str(left["user_id"]) == str(right["user_id"]):
                continue
            if len(left["history"]) < 2 or len(right["history"]) < 2:
                continue
            left_code = normalize(str(left["history"][-1]["code"]))
            right_code = normalize(str(right["history"][-1]["code"]))
            if left_code == right_code:
                ratio = 1.0
            else:
                ratio = difflib.SequenceMatcher(None, left_code, right_code).ratio()
            if ratio < similarity:
                continue
            matched_pairs += 1
            selected.update((str(left["example_id"]), str(right["example_id"])))
            if normalize(str(left["target_code"])) != normalize(str(right["target_code"])):
                different_target_pairs += 1
    return selected, {
        "matched_pairs": matched_pairs,
        "different_target_pairs": different_target_pairs,
        "matched_examples": len(selected),
    }


def analyze_case(
    dataset_path: Path,
    full_path: Path,
    current_path: Path,
    *,
    similarity: float,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    dataset = read_jsonl(dataset_path)
    full = read_jsonl(full_path)
    current = read_jsonl(current_path)
    selected, audit = matched_ids(dataset, full, similarity=similarity)
    full_subset = [row for row in full if str(row["example_id"]) in selected]
    current_subset = [row for row in current if str(row["example_id"]) in selected]
    result: dict[str, Any] = {
        "dataset_examples": len(dataset),
        "similarity_threshold": similarity,
        **audit,
    }
    if selected:
        result["full_minus_current"] = paired_suite_rows(
            full_subset,
            current_subset,
            left_label="Full trajectory",
            right_label="Current code only",
            samples=samples,
            seed=seed,
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--similarity", type=float, default=0.8)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    result: dict[str, Any] = {
        "definition": (
            "different users on the same problem; identical buggy verdict and pass "
            "rate; both have prior submissions; normalized current-code SequenceMatcher "
            f"ratio >= {args.similarity}"
        ),
        "cases": {},
    }
    offset = 0
    for split in ("seen", "unseen"):
        for adapter in ("strict", "progress"):
            prefix = f"rq2-{split}-test-{adapter}"
            result["cases"][f"{split}-{adapter}"] = analyze_case(
                args.run_root / "datasets" / f"{prefix}-full.jsonl",
                args.run_root / "eval" / f"{prefix}-comparison" / "full-eval.jsonl",
                args.run_root / "eval" / f"{prefix}-comparison" / "current-eval.jsonl",
                similarity=args.similarity,
                samples=args.samples,
                seed=args.seed + offset,
            )
            offset += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
