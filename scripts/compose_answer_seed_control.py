#!/usr/bin/env python3
"""Compose three sparse evaluations into one sequential portfolio."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def keyed(rows: list[Row]) -> dict[str, Row]:
    result = {str(row["example_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate example_id")
    return result


def ted_key(row: Row) -> float:
    value = row.get("ted_buggy_fixed")
    return float(value) if value is not None else float("inf")


def baseline_pass_rate(row: Row) -> float:
    values = [
        float(row[key])
        for key in ("buggy_pass_rate", "current_pass_rate")
        if row.get(key) is not None
    ]
    if not values:
        raise ValueError("evaluation row has no baseline pass rate")
    if any(value != values[0] for value in values[1:]):
        raise ValueError("baseline pass-rate fields disagree")
    return values[0]


def compose(
    dataset: list[Row],
    stages: list[tuple[str, list[Row]]],
    *,
    max_ted: float | None = None,
) -> list[Row]:
    dataset_by_id = keyed(dataset)
    stage_maps = [(name, keyed(rows)) for name, rows in stages]
    if set(stage_maps[0][1]) != set(dataset_by_id):
        raise ValueError("the first stage must cover the complete dataset")

    results: list[Row] = []
    for example_id in sorted(dataset_by_id):
        reference = stage_maps[0][1][example_id]
        baseline = baseline_pass_rate(reference)
        available: list[tuple[str, Row]] = [
            (name, rows[example_id])
            for name, rows in stage_maps
            if example_id in rows
        ]
        if any(baseline_pass_rate(row) != baseline for _name, row in available):
            raise ValueError(f"stage baselines disagree for {example_id}")
        def within_budget(candidate: Row) -> bool:
            if max_ted is None:
                return True
            ted = candidate.get("ted_buggy_fixed")
            return ted is not None and float(ted) <= max_ted

        eligible = [(name, row) for name, row in available if within_budget(row)]
        selected_name = "current-fallback"
        selected: Row | None = None
        early_stop_stage: str | None = None
        for name, candidate in eligible:
            if bool(candidate["repaired"]):
                selected_name = name
                selected = candidate
                early_stop_stage = name
                break
        if selected is None:
            best_pass_rate = max(
                [baseline] + [float(row["fixed_pass_rate"]) for _name, row in eligible]
            )
            if best_pass_rate > baseline:
                selected_name, selected = min(
                    (
                        (name, row)
                        for name, row in eligible
                        if float(row["fixed_pass_rate"]) == best_pass_rate
                    ),
                    key=lambda item: ted_key(item[1]),
                )
        fixed_pass_rate = baseline if selected is None else float(selected["fixed_pass_rate"])
        results.append(
            {
                "example_id": example_id,
                "problem_id": reference["problem_id"],
                "user_id": reference["user_id"],
                "method": "Answer-3Seed",
                "buggy_pass_rate": baseline,
                "current_pass_rate": baseline,
                "fixed_pass_rate": fixed_pass_rate,
                "repaired": bool(selected is not None and selected["repaired"]),
                "improved": fixed_pass_rate > baseline,
                "selected_source": selected_name,
                "early_stop_stage": early_stop_stage,
                "candidate_count": len(available),
                "budget_eligible_candidate_count": len(eligible),
                "max_ted": max_ted,
                "ted_buggy_fixed": (
                    None if selected is None else selected.get("ted_buggy_fixed")
                ),
                "ted_fixed_oracle": (
                    None if selected is None else selected.get("ted_fixed_oracle")
                ),
            }
        )
    return results


def summarize(rows: list[Row], *, method: str = "Answer-3Seed") -> dict[str, Any]:
    sources = Counter(str(row["selected_source"]) for row in rows)
    return {
        "method": method,
        "examples": len(rows),
        "problems": len({str(row["problem_id"]) for row in rows}),
        "pass_rate": sum(float(row["fixed_pass_rate"]) for row in rows) / len(rows),
        "repair_rate": sum(bool(row["repaired"]) for row in rows) / len(rows),
        "improvement_rate": sum(bool(row["improved"]) for row in rows) / len(rows),
        "mean_candidates": sum(int(row["candidate_count"]) for row in rows) / len(rows),
        "selected_source_counts": dict(sorted(sources.items())),
        "stage_feedback": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stage", action="append", required=True)
    parser.add_argument("--method", default="Answer-3Seed")
    parser.add_argument(
        "--max-ted",
        type=float,
        help="Continue past over-budget candidates and select only candidates at or below this AST TED.",
    )
    args = parser.parse_args()

    stages: list[tuple[str, list[Row]]] = []
    for value in args.stage:
        if "=" not in value:
            parser.error("--stage must use NAME=PATH")
        name, path = value.split("=", 1)
        stages.append((name, read_jsonl(Path(path))))
    if len(stages) != 3:
        parser.error("exactly three stages are required")

    results = compose(read_jsonl(args.dataset), stages, max_ted=args.max_ted)
    for row in results:
        row["method"] = args.method
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in results:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = summarize(results, method=args.method)
    args.output.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
