#!/usr/bin/env python3
"""Strict targets for the paired target control.

Each example of the paired Answer dataset (current-only prompt) keeps its prompt and example id, and its target becomes
the next submission whose verdict is less severe than the current one (Strict). The trajectories are rebuilt from the
Answer rows, which hold every non-accepted submission (`<pid>:<uid>:S<source>-to-S<final>`) and the accepted one; where
the Strict dataset already pairs the current submission, its target must be the same.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.core.dataset import _VERDICT_SEVERITY

TARGET_FIELDS = ("target_position", "original_target_position", "target_submission_id", "target_verdict", "target_code")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def source_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return str(row["problem_id"]), str(row["user_id"]), str(row["history"][-1]["submission_id"])


def trajectories(answer_rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[int, dict[str, Any]]]:
    result: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in answer_rows:
        match = re.fullmatch(r".*:S(\d+)-to-S(\d+)", str(row["example_id"]))
        if match is None:
            raise ValueError(f"unexpected Answer example id: {row['example_id']}")
        source, final = int(match[1]), int(match[2])
        current = row["history"][-1]
        steps = result[(str(row["problem_id"]), str(row["user_id"]))]
        for position, entry in ((source, {"submission_id": current["submission_id"], "verdict": current["verdict"],
                                          "code": current["code"]}),
                                (final, {"submission_id": row["target_submission_id"], "verdict": row["target_verdict"],
                                         "code": row["target_code"]})):
            if position in steps and steps[position]["submission_id"] != entry["submission_id"]:
                raise ValueError(f"two submissions at S{position} of {row['problem_id']}:{row['user_id']}")
            steps.setdefault(position, {}).update(entry)
    return result


def strict_target(steps: dict[int, dict[str, Any]], submission_id: str) -> dict[str, Any] | None:
    severity = lambda verdict: _VERDICT_SEVERITY.get(str(verdict), max(_VERDICT_SEVERITY.values()) + 1)
    current = next(position for position, step in steps.items() if step["submission_id"] == submission_id)
    for position in sorted(p for p in steps if p > current):
        if severity(steps[position]["verdict"]) < severity(steps[current]["verdict"]):
            return {"position": position, **steps[position]}
    return None


def build(paired_answer: Path, answer: Path, strict: Path, output: Path) -> dict[str, Any]:
    rows = read_jsonl(paired_answer)
    traj = trajectories(read_jsonl(answer))
    strict_by_source = {source_key(row): row for row in read_jsonl(strict)}
    counts = {"examples": len(rows), "from_strict_rows": 0, "rebuilt": 0, "rebuilt_checked_against_strict_rows": 0,
              "same_target_as_answer": 0}
    out = []
    for row in rows:
        key = source_key(row)
        target = strict_target(traj[key[:2]], key[2])
        if target is None:
            raise ValueError(f"no Strict target for {key}")
        known = strict_by_source.get(key)
        if known is not None:
            if str(known["target_submission_id"]) != str(target["submission_id"]):
                raise ValueError(f"rebuilt Strict target differs from the Strict dataset: {key}")
            counts["rebuilt_checked_against_strict_rows"] += 1
            counts["from_strict_rows"] += 1
            fields = {field: known[field] for field in TARGET_FIELDS}
        else:
            counts["rebuilt"] += 1
            fields = {"target_position": target["position"], "original_target_position": target["position"],
                      "target_submission_id": target["submission_id"], "target_verdict": target["verdict"],
                      "target_code": target["code"]}
        counts["same_target_as_answer"] += str(fields["target_submission_id"]) == str(row["target_submission_id"])
        out.append({**row, **fields})
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as destination:
        for row in out:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {**counts, "paired_answer": str(paired_answer), "output": str(output),
            "target": "next submission with a less severe verdict than the current one (canonical severity)"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paired_answer", type=Path, help="the paired control's Answer dataset (current-only)")
    parser.add_argument("answer", type=Path, help="the full Answer dataset of the same split")
    parser.add_argument("strict", type=Path, help="the full Strict dataset of the same split")
    parser.add_argument("output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.paired_answer, args.answer, args.strict, args.output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
