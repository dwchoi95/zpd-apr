#!/usr/bin/env python3
"""Verify split-specific 1.5B member evidence needed to replay portfolios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_ids(path: Path) -> list[str]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    ids = [str(row["example_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate example_id")
    return ids


def selected_members(mixed: dict[str, Any], answer: dict[str, Any]) -> list[str]:
    names = set(mixed["best_unconstrained"]["members"])
    names.update(answer["selected_unrestricted"]["members"])
    for row in mixed["selected_unconstrained_by_budget"].values():
        names.update(row["members"])
    for row in answer["selected_by_budget"].values():
        names.update(row["members"])
    names.update(("Answer2027", "Answer2028", "Answer2029"))
    return sorted(names)


def verify(
    eval_root: Path,
    datasets: dict[str, Path],
    mixed_selection: Path,
    answer_selection: Path,
) -> dict[str, Any]:
    mixed = json.loads(mixed_selection.read_text(encoding="utf-8"))
    answer = json.loads(answer_selection.read_text(encoding="utf-8"))
    members = selected_members(mixed, answer)
    result: dict[str, Any] = {"members": members, "splits": {}}
    for split, dataset in datasets.items():
        expected_ids = read_ids(dataset)
        expected = set(expected_ids)
        for member in members:
            evaluation = eval_root / "members" / split / f"{member}.evaluation.jsonl"
            summary = evaluation.with_suffix("").with_suffix(".evaluation.summary.json")
            if not evaluation.is_file() or not summary.is_file():
                raise FileNotFoundError(f"missing {split} evidence for {member}")
            observed_ids = read_ids(evaluation)
            if set(observed_ids) != expected or len(observed_ids) != len(expected_ids):
                raise ValueError(f"{evaluation}: evaluation IDs do not match {dataset}")
        result["splits"][split] = {
            "examples": len(expected_ids),
            "verified_members": len(members),
            "complete": True,
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--seen-dataset", type=Path, required=True)
    parser.add_argument("--unseen-dataset", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(
        args.eval_root,
        {"seen": args.seen_dataset, "unseen": args.unseen_dataset},
        args.mixed_selection,
        args.answer_selection,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
