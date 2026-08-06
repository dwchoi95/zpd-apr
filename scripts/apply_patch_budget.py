#!/usr/bin/env python3
"""Apply a deployment AST-edit budget by abstaining on oversized repairs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def apply_budget(row: Row, budget: int) -> Row:
    result = dict(row)
    ted = row.get("ted_buggy_fixed")
    within_budget = bool(row.get("repaired")) and ted is not None and int(ted) <= budget
    result["pre_budget_repaired"] = bool(row.get("repaired"))
    result["max_ted_budget"] = budget
    result["within_ted_budget"] = within_budget
    if bool(row.get("repaired")) and not within_budget:
        result["repaired"] = False
        result["improved"] = False
        result["fixed_pass_rate"] = float(row["buggy_pass_rate"])
        result["selected_source"] = "current-fallback:patch-budget"
        result["ted_buggy_fixed"] = 0
        result["tree_edit_distance"] = 0
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-ted", type=int, required=True)
    args = parser.parse_args()
    if args.max_ted < 0:
        parser.error("--max-ted must be non-negative")
    with args.input.open(encoding="utf-8") as source:
        rows = [apply_budget(json.loads(line), args.max_ted) for line in source if line.strip()]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "examples": len(rows),
                "max_ted_budget": args.max_ted,
                "repairs_before_budget": sum(row["pre_budget_repaired"] for row in rows),
                "repairs_within_budget": sum(row["repaired"] for row in rows),
                "abstained_oversized_or_missing_ted": sum(
                    row["pre_budget_repaired"] and not row["within_ted_budget"]
                    for row in rows
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
