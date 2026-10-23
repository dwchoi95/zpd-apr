#!/usr/bin/env python3
"""Create a current-only evaluation set spanning all failed trajectory prefixes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def phase(source_position: int, target_position: int) -> str:
    failures = target_position - 1
    if failures < 1 or not 1 <= source_position <= failures:
        raise ValueError((source_position, target_position))
    fraction = source_position / failures
    if fraction <= 1 / 3:
        return "early"
    if fraction <= 2 / 3:
        return "middle"
    return "last"


def transform(row: dict[str, Any]) -> dict[str, Any]:
    history = list(row.get("history", []))
    if not history:
        raise ValueError(f"empty history: {row.get('example_id')}")
    current = dict(history[-1])
    source_position = int(current["position"])
    target_position = int(row.get("original_target_position", row["target_position"]))
    current["position"] = 1
    result = dict(row)
    result["history"] = [current]
    result["trajectory_source_position"] = source_position
    result["trajectory_target_position"] = target_position
    result["trajectory_phase"] = phase(source_position, target_position)
    result["attempts_remaining_to_acceptance"] = target_position - source_position
    return result


def build(source: Path, output: Path, baseline_output: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    phases: Counter[str] = Counter()
    problems: set[str] = set()
    trajectories: set[tuple[str, str]] = set()
    with source.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = transform(json.loads(line))
            rows.append(row)
            phases[str(row["trajectory_phase"])] += 1
            problems.add(str(row["problem_id"]))
            trajectories.add((str(row["problem_id"]), str(row["user_id"])))
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline_output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as destination, baseline_output.open(
        "w", encoding="utf-8"
    ) as baseline:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
            baseline.write(
                json.dumps(
                    {
                        "example_id": row["example_id"],
                        "problem_id": row["problem_id"],
                        "user_id": row["user_id"],
                        "buggy_pass_rate": row["current_pass_rate"],
                        "buggy_verdict": row["current_execution_verdict"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return {
        "examples": len(rows),
        "problems": len(problems),
        "trajectories": len(trajectories),
        "phase_examples": dict(sorted(phases.items())),
        "output": str(output),
        "baseline_output": str(baseline_output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("baseline_output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.source, args.output, args.baseline_output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
