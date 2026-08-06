#!/usr/bin/env python3
"""Export simple CodeWorkout records from the official TIKTOC pickle.

The source is a Python pickle and must only be opened in a filesystem- and
network-isolated process.  The explicit acknowledgement prevents accidental
use outside the documented bwrap conversion command.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


EXPECTED_COLUMNS = {
    "SubjectID",
    "AssignmentID",
    "ProblemID",
    "CodeStateID",
    "binary_correctness",
    "Code",
    "Code-ast",
    "code-astnn",
    "code-embedding",
    "embedding",
    "astnn",
    "prompt",
    "ServerTimestamp",
    "prompt-embedding",
    "input",
    "Score",
    "timestep",
    "SubjectID_appendix",
}


def simple_row(row: Any) -> dict[str, Any]:
    outcomes = row.binary_correctness
    if not isinstance(outcomes, list) or not outcomes or not all(
        type(value) is int and value in (0, 1) for value in outcomes
    ):
        raise ValueError(f"invalid binary_correctness for {row.CodeStateID}")
    if not all(
        isinstance(value, str)
        for value in (row.SubjectID, row.CodeStateID, row.Code, row.prompt, row.ServerTimestamp)
    ):
        raise ValueError(f"invalid string field for {row.CodeStateID}")
    return {
        "submission_id": row.CodeStateID,
        "user_id": row.SubjectID,
        "assignment_id": int(row.AssignmentID),
        "problem_id": int(row.ProblemID),
        "code": row.Code,
        "prompt": row.prompt,
        "timestamp": row.ServerTimestamp,
        "timestep": int(row.timestep),
        "testcase_pass": outcomes,
        "score": float(row.Score),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--acknowledge-trusted-pickle", action="store_true")
    args = parser.parse_args()
    if not args.acknowledge_trusted_pickle:
        parser.error("run only in isolation and pass --acknowledge-trusted-pickle")
    frame = pd.read_pickle(args.input)
    if set(frame.columns) != EXPECTED_COLUMNS:
        raise ValueError("unexpected TIKTOC dataframe schema")
    rows = [simple_row(row) for row in frame.itertuples(index=False)]
    if len({row["submission_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate CodeStateID")
    rows.sort(
        key=lambda row: (
            row["user_id"],
            row["problem_id"],
            row["timestamp"],
            row["timestep"],
            row["submission_id"],
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    trajectories = {(row["user_id"], row["problem_id"]) for row in rows}
    print(
        json.dumps(
            {
                "submissions": len(rows),
                "students": len({row["user_id"] for row in rows}),
                "problems": len({row["problem_id"] for row in rows}),
                "trajectories": len(trajectories),
                "accepted_submissions": sum(row["score"] == 1.0 for row in rows),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
