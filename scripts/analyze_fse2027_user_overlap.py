#!/usr/bin/env python3
"""Stratify paired repair effects by whether a user appears in training data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_fse2027_robustness import paired_suite_rows, replay_selected_rows


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def training_users(paths: list[Path]) -> set[str]:
    return {
        str(row["user_id"])
        for path in paths
        for row in read_jsonl(path)
    }


def stratify(rows: list[Row], known_users: set[str]) -> dict[str, list[Row]]:
    return {
        "train_user_overlap": [
            row for row in rows if str(row["user_id"]) in known_users
        ],
        "train_user_disjoint": [
            row for row in rows if str(row["user_id"]) not in known_users
        ],
    }


def build_report(
    train_datasets: list[Path],
    eval_root: Path,
    *,
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    known_users = training_users(train_datasets)
    splits = {}
    for offset, split in enumerate(("seen", "unseen")):
        if split == "seen":
            left = replay_selected_rows(
                eval_root, ("progress", "strict", "answer")
            )
        else:
            left = read_jsonl(
                eval_root
                / "acceptance-ablations"
                / "zpdpatch-unseen-test-no-stage-feedback.evaluation.jsonl"
            )
        right = read_jsonl(eval_root / f"zero-shot-{split}-test.evaluation.jsonl")
        left_groups = stratify(left, known_users)
        right_groups = stratify(right, known_users)
        split_report = {}
        for group_offset, group in enumerate(
            ("train_user_overlap", "train_user_disjoint")
        ):
            left_group = left_groups[group]
            right_group = right_groups[group]
            if not left_group:
                split_report[group] = {"examples": 0, "paired_comparison": None}
                continue
            comparison = paired_suite_rows(
                left_group,
                right_group,
                left_label=f"ZPDPatch-{split}-{group}",
                right_label=f"Zero-shot-{split}-{group}",
                samples=bootstrap_samples,
                seed=seed + offset * 100 + group_offset * 10,
            )
            split_report[group] = {
                "examples": len(left_group),
                "problems": len({str(row["problem_id"]) for row in left_group}),
                "users": len({str(row["user_id"]) for row in left_group}),
                "paired_comparison": comparison,
            }
        splits[split] = split_report
    return {
        "schema_version": 1,
        "estimand_note": (
            "Within-stratum paired method differences; overlap-vs-disjoint "
            "differences are descriptive because users were not randomized."
        ),
        "training_user_count": len(known_users),
        "training_datasets": [str(path) for path in train_datasets],
        "bootstrap": {
            "samples": bootstrap_samples,
            "seed": seed,
            "cluster": "problem_id",
        },
        "splits": splits,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-dataset", type=Path, action="append", required=True)
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    report = build_report(
        [path.expanduser().resolve() for path in args.train_dataset],
        args.eval_root.expanduser().resolve(),
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        split: {
            group: values["examples"]
            for group, values in groups.items()
        }
        for split, groups in report["splits"].items()
    }, sort_keys=True))


if __name__ == "__main__":
    main()
