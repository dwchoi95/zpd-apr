#!/usr/bin/env python3
"""Collect isolated CodeWorkout Java outcomes into standard repair metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def collect(manifest: list[Row], status_root: Path) -> tuple[list[Row], Row]:
    rows = []
    for record in manifest:
        path = status_root / f'{record["slug"]}.txt'
        if not path.is_file():
            raise ValueError(f"missing status: {record['slug']}")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        status = lines[0] if lines else "runner-error"
        observed = {}
        for line in lines[1:]:
            if not line.startswith("__ZPD_CASE_") or "__" not in line[11:]:
                continue
            marker, value = line.split("__", 2)[1:]
            observed[int(marker.removeprefix("ZPD_CASE_"))] = value
        expected = [str(value) for value in record["expected"]]
        passed = [
            status == "ok" and observed.get(index, "") == value
            for index, value in enumerate(expected, start=1)
        ]
        current_pass_rate = float(record["current_pass_rate"])
        fixed_pass_rate = sum(passed) / len(passed)
        rows.append(
            {
                **record,
                "execution_status": status,
                "fixed_tc_outcomes": {
                    f"case_{index:03d}": "AC" if value else "WA"
                    for index, value in enumerate(passed, start=1)
                },
                "fixed_pass_rate": fixed_pass_rate,
                "repaired": all(passed),
                "improved": fixed_pass_rate > current_pass_rate,
                "nonregressive_improvement": all(
                    value or str(record["current_tc_outcomes"].get(f"case_{index:03d}")) != "AC"
                    for index, value in enumerate(passed, start=1)
                ) and fixed_pass_rate > current_pass_rate,
            }
        )
    n = len(rows)
    summary = {
        "examples": n,
        "problem_count": len({row["problem_id"] for row in rows}),
        "student_count": len({row["user_id"] for row in rows}),
        "program_rate": sum(row["execution_status"] == "ok" for row in rows) / n,
        "repair_rate": sum(row["repaired"] for row in rows) / n,
        "improvement_rate": sum(row["improved"] for row in rows) / n,
        "nonregressive_improvement_rate": sum(row["nonregressive_improvement"] for row in rows) / n,
        "mean_pass_rate": sum(row["fixed_pass_rate"] for row in rows) / n,
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("status_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    rows, summary = collect(read_jsonl(args.manifest), args.status_root)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
