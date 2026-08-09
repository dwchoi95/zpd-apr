#!/usr/bin/env python3
"""Exploratory, outcome-blind strata for Seen repair-effect heterogeneity."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_fse2027_robustness import (
    keyed,
    paired_suite_rows,
    read_jsonl,
    summarize_method,
)


Row = dict[str, Any]


def ast_nodes(code: str) -> int | None:
    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError, ValueError):
        return None
    return sum(1 for _ in ast.walk(tree))


def pass_rate_bin(value: float) -> str:
    if value < 0.25:
        return "[0,.25)"
    if value < 0.50:
        return "[.25,.50)"
    if value < 0.75:
        return "[.50,.75)"
    return "[.75,1)"


def trajectory_length_bin(value: int) -> str:
    if value <= 1:
        return "1"
    if value == 2:
        return "2"
    if value <= 4:
        return "3-4"
    return "5+"


def program_size_bin(value: int | None) -> str:
    if value is None:
        return "unparseable"
    if value <= 74:
        return "<=74"
    if value <= 110:
        return "75-110"
    if value <= 190:
        return "111-190"
    return ">190"


def metadata(dataset: list[Row]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in dataset:
        example_id = str(row["example_id"])
        history = row["history"]
        current = history[-1]
        result[example_id] = {
            "current_verdict": str(
                row.get("current_execution_verdict", current.get("execution_verdict", "unknown"))
            ),
            "current_pass_rate": pass_rate_bin(
                float(row.get("current_pass_rate", current["pass_rate"]))
            ),
            "trajectory_length": trajectory_length_bin(len(history)),
            "current_ast_nodes": program_size_bin(ast_nodes(str(current["code"]))),
        }
    return result


def analyze(
    dataset: list[Row],
    mixed: list[Row],
    answer: list[Row],
    zero_shot: list[Row],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    methods = {
        "mixed": keyed(mixed),
        "answer9": keyed(answer),
        "zero_shot": keyed(zero_shot),
    }
    data_by_id = keyed(dataset)
    expected = set(data_by_id)
    if any(set(rows) != expected for rows in methods.values()):
        raise ValueError("dataset and evaluation example IDs differ")
    labels = metadata(dataset)
    dimensions: dict[str, dict[str, list[str]]] = {}
    for dimension in (
        "current_verdict",
        "current_pass_rate",
        "trajectory_length",
        "current_ast_nodes",
    ):
        groups: dict[str, list[str]] = defaultdict(list)
        for example_id, values in labels.items():
            groups[values[dimension]].append(example_id)
        dimensions[dimension] = dict(sorted(groups.items()))

    output: dict[str, Any] = {
        "analysis_status": "post-review exploratory",
        "strata_fixed_before_reading_method_outcomes": True,
        "program_size_cutpoints": [74, 110, 190],
        "program_size_cutpoint_provenance": (
            "rounded quartiles already reported by the normalized-TED audit"
        ),
        "multiple_testing_note": (
            "Intervals describe heterogeneity and are not confirmatory subgroup claims."
        ),
        "dimensions": {},
    }
    comparison_index = 0
    for dimension, groups in dimensions.items():
        dimension_rows = {}
        for label, ids in groups.items():
            selected = {
                name: [rows[example_id] for example_id in ids]
                for name, rows in methods.items()
            }
            dimension_rows[label] = {
                "examples": len(ids),
                "problems": len({str(data_by_id[item]["problem_id"]) for item in ids}),
                "mixed": summarize_method(selected["mixed"]),
                "answer9": summarize_method(selected["answer9"]),
                "zero_shot": summarize_method(selected["zero_shot"]),
                "mixed_minus_answer9": paired_suite_rows(
                    selected["mixed"],
                    selected["answer9"],
                    left_label="Mixed-target-9Choose3",
                    right_label="Answer-9Choose3",
                    samples=samples,
                    seed=seed + comparison_index * 10,
                ),
                "mixed_minus_zero_shot": paired_suite_rows(
                    selected["mixed"],
                    selected["zero_shot"],
                    left_label="Mixed-target-9Choose3",
                    right_label="Zero-shot",
                    samples=samples,
                    seed=seed + comparison_index * 10 + 1,
                ),
            }
            comparison_index += 1
        output["dimensions"][dimension] = dimension_rows
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--mixed", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--zero-shot", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(
        read_jsonl(args.dataset),
        read_jsonl(args.mixed),
        read_jsonl(args.answer9),
        read_jsonl(args.zero_shot),
        samples=args.samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dimensions": sorted(result["dimensions"])}, sort_keys=True))


if __name__ == "__main__":
    main()
