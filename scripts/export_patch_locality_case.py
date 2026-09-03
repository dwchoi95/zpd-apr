#!/usr/bin/env python3
"""Export a deterministic illustrative locality case; never a quantitative endpoint."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def keyed(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row["example_id"]): row for row in rows}


def select_case(
    dataset: list[dict[str, Any]],
    progress: list[dict[str, Any]],
    answer: list[dict[str, Any]],
    *,
    maximum_chars: int,
    selection: str = "largest",
) -> dict[str, Any]:
    data = keyed(dataset)
    progress_by_id = keyed(progress)
    answer_by_id = keyed(answer)
    candidates = []
    for example_id in sorted(data.keys() & progress_by_id.keys() & answer_by_id.keys()):
        current = str(data[example_id]["history"][-1]["code"])
        p = progress_by_id[example_id]
        a = answer_by_id[example_id]
        generated = (str(p.get("generated_code", "")), str(a.get("generated_code", "")))
        if not p.get("repaired") or not a.get("repaired"):
            continue
        if p.get("ted_buggy_fixed") is None or a.get("ted_buggy_fixed") is None:
            continue
        if max(map(len, (current, *generated))) > maximum_chars:
            continue
        candidates.append((
            float(a["ted_buggy_fixed"]) - float(p["ted_buggy_fixed"]),
            example_id,
        ))
    if not candidates:
        raise ValueError("no jointly repaired compact case")
    if selection == "largest":
        target_gap = max(gap for gap, _example_id in candidates)
        rule = "largest Answer-minus-Progress TED gap"
    elif selection == "median":
        target_gap = float(statistics.median(gap for gap, _example_id in candidates))
        rule = "closest to the median Answer-minus-Progress TED gap"
    else:
        raise ValueError(f"unsupported selection: {selection}")
    _distance, _gap, example_id = min(
        (abs(gap - target_gap), gap, example_id) for gap, example_id in candidates
    )
    row = data[example_id]
    p = progress_by_id[example_id]
    a = answer_by_id[example_id]
    return {
        "role": "post-hoc qualitative illustration; excluded from every estimate",
        "selection_rule": f"{rule} among jointly repaired examples with every displayed program at most the fixed character cap; ties use example_id",
        "candidate_count": len(candidates),
        "target_gap": target_gap,
        "maximum_chars": maximum_chars,
        "example_id": example_id,
        "problem_id": row["problem_id"],
        "history": [
            {
                "position": item["position"],
                "verdict": item["verdict"],
                "pass_rate": item.get("pass_rate"),
                "code": item["code"],
            }
            for item in row["history"]
        ],
        "progress": {
            "ted": p["ted_buggy_fixed"],
            "code": p["generated_code"],
            "repaired": p["repaired"],
        },
        "answer": {
            "ted": a["ted_buggy_fixed"],
            "code": a["generated_code"],
            "repaired": a["repaired"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    parser.add_argument("--answer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-chars", type=int, default=900)
    parser.add_argument("--selection", choices=("largest", "median"), default="largest")
    args = parser.parse_args()
    result = select_case(
        read_jsonl(args.dataset), read_jsonl(args.progress), read_jsonl(args.answer),
        maximum_chars=args.maximum_chars,
        selection=args.selection,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("example_id", "problem_id", "progress", "answer")}, sort_keys=True))


if __name__ == "__main__":
    main()
