#!/usr/bin/env python3
"""Build first-AC, user-held-out CodeWorkout trajectories."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def split_users(users: list[str], seed: int) -> dict[str, str]:
    ordered = sorted(
        users,
        key=lambda user: hashlib.sha256(f"{seed}:{user}".encode()).hexdigest(),
    )
    train_end = round(len(ordered) * 0.70)
    valid_end = train_end + round(len(ordered) * 0.15)
    return {
        user: (
            "train" if index < train_end else "valid" if index < valid_end else "test"
        )
        for index, user in enumerate(ordered)
    }


def normalized(code: str) -> str:
    return "\n".join(line.rstrip() for line in code.replace("\r", "").strip().splitlines())


def build(submissions: list[Row], compile_rows: list[Row], seed: int) -> tuple[list[Row], Row]:
    compile_by_id = {str(row["submission_id"]): row for row in compile_rows}
    if len(compile_by_id) != len(compile_rows):
        raise ValueError("duplicate compile-cache submission_id")
    missing = {str(row["submission_id"]) for row in submissions} - set(compile_by_id)
    if missing:
        raise ValueError(f"compile cache missing {len(missing)} submissions")
    user_split = split_users(sorted({str(row["user_id"]) for row in submissions}), seed)
    grouped: dict[tuple[str, int], list[Row]] = defaultdict(list)
    for row in submissions:
        grouped[(str(row["user_id"]), int(row["problem_id"]))].append(row)

    trajectories = []
    excluded = Counter()
    for (user, problem), rows in sorted(grouped.items()):
        rows.sort(
            key=lambda row: (
                str(row["timestamp"]), int(row["timestep"]), str(row["submission_id"])
            )
        )
        deduplicated = []
        for row in rows:
            if deduplicated and normalized(str(row["code"])) == normalized(
                str(deduplicated[-1]["code"])
            ):
                continue
            deduplicated.append(row)
        first_ac = next(
            (index for index, row in enumerate(deduplicated) if all(row["testcase_pass"])),
            None,
        )
        if first_ac is None:
            excluded["no_accepted_submission"] += 1
            continue
        retained = deduplicated[: first_ac + 1]
        if len(retained) < 3:
            excluded["fewer_than_three_submissions"] += 1
            continue
        if all(all(row["testcase_pass"]) for row in retained[:-1]):
            excluded["no_failed_source"] += 1
            continue
        sequence = []
        for position, row in enumerate(retained, start=1):
            cached = compile_by_id[str(row["submission_id"])]
            verdict = (
                "AC"
                if all(row["testcase_pass"])
                else "CE"
                if not bool(cached["compiles"])
                else "WA"
            )
            sequence.append(
                {
                    "position": position,
                    "submission_id": row["submission_id"],
                    "timestamp": row["timestamp"],
                    "code": row["code"],
                    "verdict": verdict,
                    "testcase_pass": row["testcase_pass"],
                    "score": row["score"],
                }
            )
        trajectories.append(
            {
                "trajectory_id": f"cw:{problem}:{user}",
                "user_id": user,
                "problem_id": f"cw{problem:03d}",
                "assignment_id": int(retained[0]["assignment_id"]),
                "prompt": retained[0]["prompt"],
                "split": user_split[user],
                "submissions": sequence,
            }
        )

    split_users_count = {
        split: len({row["user_id"] for row in trajectories if row["split"] == split})
        for split in ("train", "valid", "test")
    }
    split_problems = {
        split: len({row["problem_id"] for row in trajectories if row["split"] == split})
        for split in ("train", "valid", "test")
    }
    summary = {
        "schema_version": 1,
        "seed": seed,
        "split_unit": "student",
        "input_submissions": len(submissions),
        "input_trajectories": len(grouped),
        "retained_trajectories": len(trajectories),
        "retained_submissions": sum(len(row["submissions"]) for row in trajectories),
        "retained_students": len({row["user_id"] for row in trajectories}),
        "retained_problems": len({row["problem_id"] for row in trajectories}),
        "trajectories_by_split": dict(Counter(row["split"] for row in trajectories)),
        "students_by_split": split_users_count,
        "problems_by_split": split_problems,
        "excluded_trajectories": dict(excluded),
        "user_overlap_across_splits": 0,
    }
    return trajectories, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("submissions", type=Path)
    parser.add_argument("compile_cache", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    trajectories, summary = build(
        read_jsonl(args.submissions), read_jsonl(args.compile_cache), args.seed
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in trajectories:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
