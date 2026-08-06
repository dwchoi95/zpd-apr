#!/usr/bin/env python3
"""Materialize CodeWorkout adapter and held-out repair datasets.

The adapter relations are shared with canonical-v5.  Answer pairs each failed
submission directly with the first accepted submission.  Strict filters the
trajectory to coarse-verdict improvements.  Progress additionally retains
same-verdict, testcase-wise Pareto improvements.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.repair.dataset import _build_adapter_examples


Row = dict[str, Any]
VERDICT = {"AC": "Accepted", "WA": "Wrong Answer", "CE": "Compile Error"}


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def outcome(submission: Row) -> Row:
    verdict = str(submission["verdict"])
    testcase_pass = submission["testcase_pass"]
    testcase_verdict = "CE" if verdict == "CE" else "WA"
    tc_outcomes = {
        f"case_{index:03d}": "AC" if passed else testcase_verdict
        for index, passed in enumerate(testcase_pass, start=1)
    }
    passed = [name for name, value in tc_outcomes.items() if value == "AC"]
    return {
        "execution_verdict": "AC" if len(passed) == len(tc_outcomes) else testcase_verdict,
        "passed_testcases": passed,
        "pass_rate": len(passed) / len(tc_outcomes),
        "tc_outcomes": tc_outcomes,
    }


def canonical_submission(submission: Row) -> Row:
    return {
        **submission,
        "verdict": VERDICT[str(submission["verdict"])],
    }


def payload(
    trajectory: Row,
    history: list[tuple[int, Row]],
    target: tuple[int, Row],
    suffix: str,
) -> Row:
    target_position, target_submission = target
    current = history[-1][1]
    current_outcome = outcome(current)
    target_outcome = outcome(target_submission)
    return {
        "example_id": f'{trajectory["trajectory_id"]}:{suffix}',
        "problem_id": trajectory["problem_id"],
        "user_id": trajectory["user_id"],
        "language": "Java",
        "problem_description": trajectory["prompt"],
        "time_limit": "not reported",
        "memory_limit": "not reported",
        "history": [
            {
                "position": displayed_position,
                "submission_id": item["submission_id"],
                "verdict": item["verdict"],
                "code": item["code"],
                **outcome(item),
                "execution_complete": True,
            }
            for displayed_position, (_original_position, item) in enumerate(
                history, start=1
            )
        ],
        "target_position": len(history) + 1,
        "original_target_position": target_position,
        "target_submission_id": target_submission["submission_id"],
        "target_verdict": target_submission["verdict"],
        "target_code": target_submission["code"],
        "current_execution_verdict": current_outcome["execution_verdict"],
        "target_execution_verdict": target_outcome["execution_verdict"],
        "current_pass_rate": current_outcome["pass_rate"],
        "target_pass_rate": target_outcome["pass_rate"],
        "current_passed_testcases": current_outcome["passed_testcases"],
        "target_passed_testcases": target_outcome["passed_testcases"],
        "current_tc_outcomes": current_outcome["tc_outcomes"],
        "target_tc_outcomes": target_outcome["tc_outcomes"],
        "current_execution_complete": True,
    }


def build(trajectories: list[Row]) -> tuple[dict[str, list[Row]], Row]:
    datasets: dict[str, list[Row]] = defaultdict(list)
    relation_counts: dict[str, Counter[str]] = {}
    for trajectory in trajectories:
        submissions = [
            (index, canonical_submission(item))
            for index, item in enumerate(trajectory["submissions"], start=1)
        ]
        outcomes = {
            (trajectory["problem_id"], str(item["submission_id"])): outcome(item)
            for _position, item in submissions
        }
        split = str(trajectory["split"])
        # One realistic held-out query: repair the final failed state immediately
        # before the student's first accepted submission, with all prior history.
        datasets[f"{split}-final"].append(
            payload(
                trajectory,
                submissions[:-1],
                submissions[-1],
                "final",
            )
        )
        if split not in {"train", "valid"}:
            continue
        for mode in ("answer", "strict", "progress"):
            counts: Counter[str] = Counter()
            examples = _build_adapter_examples(
                submissions,
                target_mode=mode,
                problem_id=trajectory["problem_id"],
                outcomes=outcomes,
                counts=counts,
            )
            relation_counts.setdefault(f"{split}-{mode}", Counter()).update(counts)
            for history, target, _before, suffix in examples:
                datasets[f"{split}-{mode}"].append(
                    payload(trajectory, history, target, suffix)
                )

    users_by_split = {
        split: {row["user_id"] for row in trajectories if row["split"] == split}
        for split in ("train", "valid", "test")
    }
    if any(
        users_by_split[left] & users_by_split[right]
        for left, right in (("train", "valid"), ("train", "test"), ("valid", "test"))
    ):
        raise ValueError("CodeWorkout student-held-out splits overlap")
    summary = {
        "schema_version": 1,
        "trajectories": len(trajectories),
        "relation_definition": {
            "answer": "each failed submission paired 1:1 with first AC",
            "strict": "coarse-verdict improvements only",
            "progress": "strict plus same-verdict testcase Pareto improvements",
        },
        "examples": {name: len(rows) for name, rows in sorted(datasets.items())},
        "problems": {
            name: len({row["problem_id"] for row in rows})
            for name, rows in sorted(datasets.items())
        },
        "students": {split: len(users) for split, users in users_by_split.items()},
        "student_overlap": 0,
        "filter_counts": {
            name: dict(counts) for name, counts in sorted(relation_counts.items())
        },
    }
    return dict(datasets), summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("trajectories", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    datasets, summary = build(read_jsonl(args.trajectories))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in datasets.items():
        path = args.output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as destination:
            for row in rows:
                destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
