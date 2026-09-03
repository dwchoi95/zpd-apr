#!/usr/bin/env python3
"""Verify the paper's deployment-frontier table against sealed JSON evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


BUDGETS = (5, 10, 20, 40, 80, 160)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def number(value: float, *, signed: bool = False) -> str:
    rendered = f"{100 * value:+.1f}" if signed else f"{100 * value:.1f}"
    return rendered.replace("-", "--")


def expected_rows(lsgen: dict[str, Any], current_only: dict[str, Any]) -> list[str]:
    current = {
        int(row["budget"]): row["current_only_answer_3seed"]["rr"]
        for row in current_only["splits"]["seen"]["budget_frontier"]
    }
    rows = []
    for budget in BUDGETS:
        row = lsgen["per_budget"][str(budget)]
        effect = row["budget_indexed_unconstrained_minus_lsgen"]
        lo, hi = effect["problem_cluster_95ci"]
        rows.append(
            f"{budget} & "
            f"{number(row['budget_indexed_unconstrained']['repair_rate'])} & "
            f"{number(current[budget])} & "
            f"{number(row['lsgen']['repair_rate'])} & "
            f"{number(effect['rr_difference'], signed=True)} "
            f"[{number(lo)}, {number(hi)}] \\\\"
        )
    return rows


def normalize_tex_row(value: str) -> str:
    """Ignore TeX math delimiters while preserving every displayed number."""
    value = value.replace("$", "").replace("--", "-")
    return re.sub(r"\s+", " ", value.strip())


def verify(paper: Path, lsgen_path: Path, current_only_path: Path) -> dict[str, Any]:
    rows = expected_rows(read_json(lsgen_path), read_json(current_only_path))
    paper_rows = {normalize_tex_row(line) for line in paper.read_text().splitlines()}
    missing = [
        row for row in rows
        if normalize_tex_row(row) not in paper_rows
    ]
    if missing:
        raise ValueError("paper budget table differs from evidence: " + repr(missing))
    return {
        "schema_version": 2,
        "paper": str(paper),
        "budgets": list(BUDGETS),
        "verified_rows": len(rows),
        "missing_rows": 0,
        "evidence": {
            "lsgen": str(lsgen_path),
            "current_only": str(current_only_path),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--lsgen", type=Path, required=True)
    parser.add_argument("--current-only", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.paper, args.lsgen, args.current_only)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
