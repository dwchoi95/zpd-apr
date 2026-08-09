#!/usr/bin/env python3
"""Verify that prompt-control datasets remove only earlier submissions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    ids = [str(row["example_id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate example IDs")
    return rows


def verify_pair(label: str, source_path: Path, current_path: Path) -> dict[str, Any]:
    source = {str(row["example_id"]): row for row in read(source_path)}
    current = {str(row["example_id"]): row for row in read(current_path)}
    if set(source) != set(current):
        raise ValueError(f"{label}: source and current-only example IDs differ")
    reset = 0
    for example_id, original in source.items():
        transformed = current[example_id]
        history = original.get("history")
        if not isinstance(history, list) or not history:
            raise ValueError(f"{label}: {example_id} has no source history")
        expected_last = dict(history[-1])
        expected_last["position"] = 1
        if transformed.get("history") != [expected_last]:
            raise ValueError(
                f"{label}: {example_id} current-only history is not the reset last submission"
            )
        expected = dict(original)
        expected["history"] = [expected_last]
        if transformed != expected:
            changed = sorted(
                key for key in set(expected) | set(transformed)
                if expected.get(key) != transformed.get(key)
            )
            raise ValueError(
                f"{label}: {example_id} changes non-history fields: {changed}"
            )
        reset += int(history[-1].get("position") != 1)
    return {
        "label": label,
        "source": str(source_path),
        "current_only": str(current_path),
        "examples": len(source),
        "histories_reduced_to_one": len(source),
        "positions_reset": reset,
        "non_history_field_mismatches": 0,
    }


def parse_pair(raw: str) -> tuple[str, Path, Path]:
    parts = raw.split(":", 2)
    if len(parts) != 3 or not all(parts):
        raise ValueError("pair must use LABEL:SOURCE:CURRENT")
    return parts[0], Path(parts[1]), Path(parts[2])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = [verify_pair(*parse_pair(raw)) for raw in args.pair]
    except ValueError as error:
        parser.error(str(error))
    result = {
        "audit": "current-only prompt distribution preserves every non-history field",
        "splits": rows,
        "total_examples": sum(row["examples"] for row in rows),
        "all_non_history_fields_identical": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
