#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().resolve().open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON at {path}:{line_number}") from error


def _cache_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["problem_id"]), str(row["submission_id"])


def _required_keys(data_root: Path) -> set[tuple[str, str]]:
    data_root = data_root.expanduser().resolve()
    split_root = data_root / "splits"
    required: set[tuple[str, str]] = set()
    for split in ("seen_train", "seen_valid", "seen_test", "unseen_test"):
        manifest = split_root / f"{split}.jsonl"
        for trajectory in _iter_jsonl(manifest):
            problem_id = str(trajectory["problem_id"])
            user_id = str(trajectory["user_id"])
            trajectory_path = (
                data_root / problem_id / "submissions" / f"{user_id}.jsonl"
            )
            for submission in _iter_jsonl(trajectory_path):
                required.add(
                    (problem_id, str(submission["submission_id"]))
                )
    return required


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge complete testcase outcome caches, reject conflicting duplicates, "
            "and verify coverage of the active Seen/Unseen split."
        )
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()

    inputs = [path.expanduser().resolve() for path in args.inputs]
    rows: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_rows = 0
    for path in inputs:
        summary_path = path.with_suffix(".summary.json")
        if not summary_path.is_file():
            raise FileNotFoundError(f"Missing cache summary: {summary_path}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("outcome_cache_complete") is not True:
            raise ValueError(f"Outcome cache is not complete: {path}")
        for row in _iter_jsonl(path):
            key = _cache_key(row)
            existing = rows.get(key)
            if existing is None:
                rows[key] = row
                continue
            duplicate_rows += 1
            if existing != row:
                raise ValueError(
                    "Conflicting duplicate outcome cache entry: "
                    f"{key[0]}:{key[1]}"
                )

    required = _required_keys(args.data_root)
    missing = sorted(required - rows.keys())
    if missing:
        preview = ", ".join(f"{problem}:{submission}" for problem, submission in missing[:10])
        raise ValueError(
            f"Merged cache misses {len(missing)} required submissions: {preview}"
        )

    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    with temporary.open("w", encoding="utf-8") as destination:
        for key in sorted(rows):
            destination.write(json.dumps(rows[key], ensure_ascii=False) + "\n")
    temporary.replace(output)

    summary = {
        "split": "canonical-v5-all",
        "input_caches": [str(path) for path in inputs],
        "input_cache_count": len(inputs),
        "merged_submissions": len(rows),
        "duplicate_rows": duplicate_rows,
        "required_split_submissions": len(required),
        "extra_cached_submissions": len(rows.keys() - required),
        "missing_required_submissions": 0,
        "failures": 0,
        "outcome_cache_complete": True,
        "output_path": str(output),
    }
    output.with_suffix(".summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
