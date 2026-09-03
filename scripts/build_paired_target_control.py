#!/usr/bin/env python3
"""Build equal-source, equal-count current-only datasets with different targets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def source_key(row: dict[str, Any]) -> tuple[str, str, str]:
    history = list(row.get("history", []))
    if not history:
        raise ValueError(f"empty history: {row.get('example_id')}")
    return (
        str(row["problem_id"]),
        str(row["user_id"]),
        str(history[-1]["submission_id"]),
    )


def current_only(row: dict[str, Any], example_id: str) -> dict[str, Any]:
    result = dict(row)
    current = dict(result["history"][-1])
    current["position"] = 1
    result["history"] = [current]
    result["example_id"] = example_id
    return result


def build(
    progress_path: Path,
    answer_path: Path,
    progress_output: Path,
    answer_output: Path,
) -> dict[str, Any]:
    progress_rows = read_jsonl(progress_path)
    answer_rows = read_jsonl(answer_path)
    answer_by_source = {source_key(row): row for row in answer_rows}
    if len(answer_by_source) != len(answer_rows):
        raise ValueError("Answer data contain duplicate current submissions")
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    identical_targets = 0
    missing = 0
    for progress in progress_rows:
        key = source_key(progress)
        answer = answer_by_source.get(key)
        if answer is None:
            missing += 1
            continue
        if str(progress["history"][-1]["code"]) != str(answer["history"][-1]["code"]):
            raise ValueError(f"paired current code differs: {key}")
        if str(progress["target_submission_id"]) == str(answer["target_submission_id"]):
            identical_targets += 1
            continue
        digest = hashlib.sha256("\0".join(key).encode()).hexdigest()[:16]
        example_id = f"paired-target:{digest}"
        pairs.append((current_only(progress, example_id), current_only(answer, example_id)))
    for path, index in ((progress_output, 0), (answer_output, 1)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as destination:
            for pair in pairs:
                destination.write(json.dumps(pair[index], ensure_ascii=False) + "\n")
    return {
        "progress_source_examples": len(progress_rows),
        "answer_source_examples": len(answer_rows),
        "paired_target_divergent_examples": len(pairs),
        "identical_target_examples_excluded": identical_targets,
        "missing_answer_sources": missing,
        "progress_output": str(progress_output),
        "answer_output": str(answer_output),
        "source_matching": "problem_id, user_id, current submission_id and exact current code",
        "history": "current-only with displayed position reset to 1",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("progress", type=Path)
    parser.add_argument("answer", type=Path)
    parser.add_argument("progress_output", type=Path)
    parser.add_argument("answer_output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.progress, args.answer, args.progress_output, args.answer_output)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
