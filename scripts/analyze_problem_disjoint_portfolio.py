#!/usr/bin/env python3
"""Evaluate a portfolio selected only on validation problems absent from test."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
    from compose_answer_seed_control import compose
except ModuleNotFoundError:
    from scripts.analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
    from scripts.compose_answer_seed_control import compose


def relation_order(name: str) -> tuple[int, str]:
    for index, prefix in enumerate(("Progress", "Strict", "Answer")):
        if name.startswith(prefix):
            return index, name
    raise ValueError(f"unknown policy relation: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stability", type=Path, required=True)
    parser.add_argument("--member", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--full-selection", type=Path, required=True)
    parser.add_argument("--answer3", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    stability = json.loads(args.stability.read_text(encoding="utf-8"))
    selected = stability["selected_problem_disjoint_validation"]
    if not selected:
        raise ValueError("no validation problems remain after test-problem exclusion")
    member_rows = {}
    for raw in args.member:
        if "=" not in raw:
            parser.error("--member must use NAME=PATH")
        name, path = raw.split("=", 1)
        member_rows[name] = read_jsonl(Path(path))
    names = sorted(selected["members"], key=relation_order)
    if any(name not in member_rows for name in names):
        raise ValueError("missing selected member test evaluation")
    stages = [(name, member_rows[name]) for name in names]
    rows = compose(stages[0][1], stages)
    for row in rows:
        row["method"] = "Problem-Disjoint-Validation-Portfolio"
    full = read_jsonl(args.full_selection)
    answer3 = read_jsonl(args.answer3)
    result = {
        "selection": selected,
        "validation_test_problem_overlap": stability["validation_test_problem_overlap"],
        "summary": summarize_method(rows),
        "problem_disjoint_minus_full_selection": paired_suite_rows(
            rows,
            full,
            left_label="Problem-disjoint validation portfolio",
            right_label="Full validation portfolio",
            samples=args.bootstrap_samples,
            seed=args.seed,
        ),
        "problem_disjoint_minus_answer3": paired_suite_rows(
            rows,
            answer3,
            left_label="Problem-disjoint validation portfolio",
            right_label="Answer-3Seed",
            samples=args.bootstrap_samples,
            seed=args.seed + 10,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"members": names, "summary": result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
