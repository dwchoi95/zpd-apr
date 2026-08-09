#!/usr/bin/env python3
"""Verify the paper's budget-mechanism table against sealed JSON evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BUDGETS = (5, 10, 20, 40, 80, 160)
PREFIXES = {"Answer": "A", "Progress": "P", "Strict": "S"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def short_member(name: str) -> str:
    for prefix, short in PREFIXES.items():
        if name.startswith(prefix):
            return f"{short}{name.removeprefix(prefix)[-2:]}"
    raise ValueError(f"unsupported checkpoint name: {name}")


def members(names: list[str]) -> str:
    return "--".join(short_member(name) for name in names)


def number(value: float, *, signed: bool = False) -> str:
    rendered = f"{100 * value:+.2f}" if signed else f"{100 * value:.2f}"
    return rendered.replace("-", "--")


def expected_rows(
    mixed_selection: dict[str, Any],
    answer_selection: dict[str, Any],
    analysis: dict[str, Any],
) -> list[str]:
    contrast = analysis["splits"]["seen"][
        "budget_indexed_zpdpatch_minus_answer_9choose3"
    ]["per_budget"]
    rows = []
    for budget in BUDGETS:
        key = str(budget)
        row = contrast[key]
        ci = row["problem_cluster_95ci"]
        rows.append(
            f"{budget} & "
            f"{members(mixed_selection['selected_unconstrained_by_budget'][key]['members'])} & "
            f"{members(answer_selection['selected_by_budget'][key]['members'])} & "
            f"{number(row['difference'], signed=True)} "
            f"[{number(ci[0])}, {number(ci[1])}] \\\\"
        )
    return rows


def verify(
    paper: Path,
    mixed_selection_path: Path,
    answer_selection_path: Path,
    analysis_path: Path,
) -> dict[str, Any]:
    text = paper.read_text()
    rows = expected_rows(
        read_json(mixed_selection_path),
        read_json(answer_selection_path),
        read_json(analysis_path),
    )
    paper_rows = {
        re.sub(r"\s+", " ", line.strip()) for line in text.splitlines()
    }
    missing = [
        row
        for row in rows
        if re.sub(r"\s+", " ", row.strip()) not in paper_rows
    ]
    if missing:
        raise ValueError("paper budget table differs from evidence: " + repr(missing))
    return {
        "schema_version": 1,
        "paper": str(paper),
        "budgets": list(BUDGETS),
        "verified_rows": len(rows),
        "missing_rows": 0,
        "evidence": {
            "mixed_selection": str(mixed_selection_path),
            "answer_selection": str(answer_selection_path),
            "analysis": str(analysis_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path, required=True)
    parser.add_argument("--answer-selection", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(
        args.paper, args.mixed_selection, args.answer_selection, args.analysis
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
