#!/usr/bin/env python3
"""Bind candidate evaluations to one canonical current-program baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.repair.evaluate import _evaluation_summary


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def canonical_baseline(reference: Row) -> tuple[float, Any, str]:
    """Read a baseline from either an evaluation or a cached dataset row."""
    if reference.get("buggy_pass_rate") is not None:
        return (
            float(reference["buggy_pass_rate"]),
            reference.get("buggy_verdict"),
            "canonical-split-baseline",
        )
    if reference.get("current_pass_rate") is not None:
        return (
            float(reference["current_pass_rate"]),
            reference.get("current_execution_verdict"),
            "canonical-dataset-cache",
        )
    raise ValueError("reference row has no canonical baseline pass rate")


def normalize(rows: list[Row], references: list[Row]) -> tuple[list[Row], int]:
    reference_by_id = {str(row["example_id"]): row for row in references}
    if len(reference_by_id) != len(references):
        raise ValueError("duplicate reference example_id")
    if {str(row["example_id"]) for row in rows} != set(reference_by_id):
        raise ValueError("evaluation and baseline must cover identical examples")
    changed = 0
    result = []
    for row in rows:
        updated = dict(row)
        reference = reference_by_id[str(row["example_id"])]
        baseline, verdict, provenance = canonical_baseline(reference)
        if float(row["buggy_pass_rate"]) != baseline or row.get("buggy_verdict") != verdict:
            changed += 1
        updated["buggy_pass_rate"] = baseline
        updated["buggy_verdict"] = verdict
        updated["improved"] = float(updated["fixed_pass_rate"]) > baseline
        updated["buggy_baseline_reused_from"] = provenance
        result.append(updated)
    result.sort(key=lambda row: str(row["example_id"]))
    return result, changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evaluation", type=Path)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    rows, changed = normalize(read_jsonl(args.evaluation), read_jsonl(args.reference))
    temporary = args.evaluation.with_suffix(args.evaluation.suffix + ".baseline.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    temporary.replace(args.evaluation)
    summary = _evaluation_summary(rows, args.evaluation.resolve())
    print(json.dumps({"examples": len(rows), "changed": changed, "repair_rate": summary.repair_rate}))


if __name__ == "__main__":
    main()
