#!/usr/bin/env python3
"""Audit how retained Strict/Progress labels depend on verdict ordering."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ORDERS = {
    "canonical": {"AC": 0, "WA": 1, "TLE": 2, "MLE": 2, "RE": 3, "CE": 4},
    "runtime_before_wrong": {"AC": 0, "RE": 1, "WA": 2, "TLE": 3, "MLE": 3, "CE": 4},
    "accepted_vs_failure": {"AC": 0, "WA": 1, "TLE": 1, "MLE": 1, "RE": 1, "CE": 1},
}

ALIASES = {
    "Accepted": "AC",
    "Wrong Answer": "WA",
    "Time Limit Exceeded": "TLE",
    "Memory Limit Exceeded": "MLE",
    "Runtime Error": "RE",
    "Compile Error": "CE",
}


def verdict(value: Any) -> str:
    text = str(value)
    return ALIASES.get(text, text)


def score(value: Any, order: dict[str, int]) -> int:
    return order.get(verdict(value), max(order.values()) + 1)


def pareto(before: dict[str, Any], after: dict[str, Any], order: dict[str, int]) -> bool:
    if not before or set(before) != set(after):
        return False
    comparisons = [(score(after[key], order), score(before[key], order)) for key in before]
    return all(new <= old for new, old in comparisons) and any(
        new < old for new, old in comparisons
    )


def valid(row: dict[str, Any], mode: str, order: dict[str, int]) -> bool:
    # Label construction uses the recorded online-judge verdict for the coarse
    # order and re-executed outcomes only for equal-verdict testcase progress.
    current = row["history"][-1]["verdict"]
    target = row["target_verdict"]
    if score(target, order) < score(current, order):
        return True
    if mode == "strict" or verdict(target) != verdict(current):
        return False
    before = row.get("current_tc_outcomes", row["history"][-1].get("tc_outcomes", {}))
    after = row.get("target_tc_outcomes", {})
    return pareto(before, after, order)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def require_all_valid(result: dict[str, Any], order_name: str) -> None:
    invalid = {
        name: row[order_name]
        for name, row in result["datasets"].items()
        if row[order_name]["valid"] != row[order_name]["total"]
    }
    if invalid:
        raise ValueError(f"invalid labels under {order_name}: {invalid}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-order", choices=sorted(ORDERS))
    args = parser.parse_args()
    result: dict[str, Any] = {"orders": ORDERS, "datasets": {}}
    for partition in ("train", "valid"):
        for mode in ("strict", "progress"):
            rows = read_jsonl(args.dataset_root / f"{partition}-{mode}.jsonl")
            result["datasets"][f"{partition}-{mode}"] = {
                name: {
                    "valid": sum(valid(row, mode, order) for row in rows),
                    "total": len(rows),
                    "fraction": sum(valid(row, mode, order) for row in rows) / len(rows),
                }
                for name, order in ORDERS.items()
            }
    if args.require_order:
        try:
            require_all_valid(result, args.require_order)
        except ValueError as error:
            parser.error(str(error))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
