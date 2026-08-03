#!/usr/bin/env python3
"""Mechanically audit the supervision-lattice invariants used in the paper.

Only aggregate counts are written; source programs and testcase outcomes are
never copied into the report.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


VERDICT_SEVERITY = {
    "Accepted": 0,
    "Wrong Answer": 1,
    "Time Limit Exceeded": 2,
    "Memory Limit Exceeded": 2,
    "Runtime Error": 3,
    "Compilation Error": 4,
    "Compile Error": 4,
    "Internal error": 5,
}


def rows(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def display(value: Any) -> str:
    return {
        "AC": "Accepted",
        "WA": "Wrong Answer",
        "TLE": "Time Limit Exceeded",
        "RE": "Runtime Error",
        "CE": "Compilation Error",
    }.get(str(value), str(value))


def severity(value: Any) -> int:
    return VERDICT_SEVERITY.get(display(value), 5)


def pareto_test_improvement(current: dict[str, Any], target: dict[str, Any]) -> bool:
    left = current.get("tc_outcomes")
    right = target.get("tc_outcomes")
    if not isinstance(left, dict) or not isinstance(right, dict):
        return False
    if not left or left.keys() != right.keys():
        return False
    strict = False
    for case_id, current_value in left.items():
        before = severity(current_value)
        after = severity(right[case_id])
        if after > before:
            return False
        strict = strict or after < before
    return strict


def transition_holds(current: dict[str, Any], target: dict[str, Any], policy: str) -> bool:
    before = severity(current.get("verdict"))
    after = severity(target.get("verdict"))
    if after < before:
        return True
    if policy == "strict":
        return False
    return (
        str(current.get("verdict")) == str(target.get("verdict"))
        and pareto_test_improvement(current, target)
    )


def audit(path: Path, policy: str) -> tuple[dict[str, Any], set[tuple[str, str, str]]]:
    counts: Counter[str] = Counter()
    examples: set[str] = set()
    problems: set[str] = set()
    users: set[str] = set()
    events: set[tuple[str, str, str]] = set()
    target_by_trajectory: dict[tuple[str, str], set[str]] = {}
    max_history = 0
    for row in rows(path):
        counts["examples"] += 1
        example_id = str(row["example_id"])
        if example_id in examples:
            counts["duplicate_example_ids"] += 1
        examples.add(example_id)
        problem = str(row["problem_id"])
        user = str(row["user_id"])
        problems.add(problem)
        users.add(user)
        history = list(row.get("history", []))
        max_history = max(max_history, len(history))
        if not history:
            counts["empty_histories"] += 1
            continue
        if (
            policy != "answer"
            and [item.get("position") for item in history]
            != list(range(1, len(history) + 1))
        ):
            counts["non_contiguous_display_positions"] += 1
        if policy != "answer" and int(row.get("target_position", -1)) != len(history) + 1:
            counts["target_position_mismatches"] += 1
        target = {
            "submission_id": row.get("target_submission_id"),
            "verdict": row.get("target_verdict"),
            "tc_outcomes": row.get("target_tc_outcomes"),
        }
        event = (problem, user, str(row.get("target_submission_id")))
        events.add(event)
        target_by_trajectory.setdefault((problem, user), set()).add(
            str(row.get("target_submission_id"))
        )
        if policy == "answer":
            if len(history) != 1:
                counts["answer_multistate_histories"] += 1
            if str(target["verdict"]) != "Accepted":
                counts["answer_nonaccepted_targets"] += 1
            if str(history[-1].get("verdict")) == "Accepted":
                counts["answer_accepted_sources"] += 1
            continue
        chain = history + [target]
        for current, later in zip(chain, chain[1:]):
            counts["audited_transitions"] += 1
            if not transition_holds(current, later, policy):
                counts["invalid_transitions"] += 1
    summary = {
        "policy": policy,
        "examples": counts["examples"],
        "problems": len(problems),
        "users": len(users),
        "trajectories": len(target_by_trajectory),
        "unique_target_events": len(events),
        "maximum_retained_history": max_history,
        "audited_transitions": counts["audited_transitions"],
        "violations": {
            name: value
            for name, value in counts.items()
            if name not in {"examples", "audited_transitions"} and value
        },
    }
    return summary, events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.dataset_root.expanduser().resolve()
    summaries: dict[str, dict[str, Any]] = {}
    events: dict[str, set[tuple[str, str, str]]] = {}
    for policy in ("answer", "strict", "progress"):
        summaries[policy], events[policy] = audit(root / f"train-{policy}.jsonl", policy)
    strict_missing_from_progress = events["strict"] - events["progress"]
    report = {
        "schema_version": 1,
        "datasets": summaries,
        "lattice": {
            "strict_target_events": len(events["strict"]),
            "progress_target_events": len(events["progress"]),
            "strict_events_missing_from_progress": len(strict_missing_from_progress),
            "strict_event_inclusion_holds": not strict_missing_from_progress,
        },
        "all_invariants_hold": (
            all(not summary["violations"] for summary in summaries.values())
            and not strict_missing_from_progress
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
