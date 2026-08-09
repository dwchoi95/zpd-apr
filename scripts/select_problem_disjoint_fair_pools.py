#!/usr/bin/env python3
"""Select matched mixed and Answer pools after excluding every test problem."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from select_answer_seed_portfolio import select as select_answer
    from select_execution_portfolio import read_jsonl, select_portfolios
except ModuleNotFoundError:
    from scripts.select_answer_seed_portfolio import select as select_answer
    from scripts.select_execution_portfolio import read_jsonl, select_portfolios


Row = dict[str, Any]


def parse_mixed(values: list[str]) -> tuple[dict[str, list[Row]], dict[str, str]]:
    evaluations: dict[str, list[Row]] = {}
    relations: dict[str, str] = {}
    for raw in values:
        if "=" not in raw or ":" not in raw.split("=", 1)[0]:
            raise ValueError("mixed evaluation must use NAME:RELATION=PATH")
        spec, path = raw.split("=", 1)
        name, relation = spec.split(":", 1)
        evaluations[name] = read_jsonl(Path(path))
        relations[name] = relation
    return evaluations, relations


def parse_answer(values: list[str]) -> dict[str, list[Row]]:
    evaluations: dict[str, list[Row]] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError("Answer evaluation must use NAME=PATH")
        name, path = raw.split("=", 1)
        if not name.startswith("Answer"):
            raise ValueError("Answer pool contains a non-Answer checkpoint")
        evaluations[name] = read_jsonl(Path(path))
    return evaluations


def select_disjoint(
    mixed: dict[str, list[Row]],
    relations: dict[str, str],
    answer: dict[str, list[Row]],
    test_rows: list[Row],
) -> dict[str, Any]:
    test_problems = {str(row["problem_id"]) for row in test_rows}

    def filtered(pool: dict[str, list[Row]]) -> dict[str, list[Row]]:
        result = {
            name: [row for row in rows if str(row["problem_id"]) not in test_problems]
            for name, rows in pool.items()
        }
        sizes = {len(rows) for rows in result.values()}
        problem_sets = [
            {str(row["problem_id"]) for row in rows} for rows in result.values()
        ]
        if len(sizes) != 1 or not problem_sets or any(
            problems != problem_sets[0] for problems in problem_sets[1:]
        ):
            raise ValueError("filtered candidates do not cover identical validation problems")
        if len(problem_sets[0]) != next(iter(sizes)):
            raise ValueError("selection requires one validation row per problem")
        return result

    mixed_filtered = filtered(mixed)
    answer_filtered = filtered(answer)
    mixed_problems = {
        str(row["problem_id"]) for row in next(iter(mixed_filtered.values()))
    }
    answer_problems = {
        str(row["problem_id"]) for row in next(iter(answer_filtered.values()))
    }
    if mixed_problems != answer_problems:
        raise ValueError("mixed and Answer pools use different validation problems")
    mixed_selection = select_portfolios(mixed_filtered, relations)
    answer_selection = select_answer(answer_filtered)
    for selection in (mixed_selection, answer_selection):
        selection["selection_partition"] = (
            "Seen validation problems excluding every Seen test problem"
        )
        selection["test_split_outcomes_used"] = False
    return {
        "test_problems_excluded": len(test_problems),
        "validation_problems": len(mixed_problems),
        "validation_test_problem_overlap": 0,
        "mixed": mixed_selection,
        "answer": answer_selection,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mixed-evaluation", action="append", required=True)
    parser.add_argument("--answer-evaluation", action="append", required=True)
    parser.add_argument("--test-evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        mixed, relations = parse_mixed(args.mixed_evaluation)
        answer = parse_answer(args.answer_evaluation)
    except ValueError as error:
        parser.error(str(error))
    result = select_disjoint(
        mixed,
        relations,
        answer,
        read_jsonl(args.test_evaluation),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "validation_problems": result["validation_problems"],
                "mixed_unrestricted": result["mixed"]["best_unconstrained"]["members"],
                "answer_unrestricted": result["answer"]["selected_unrestricted"]["members"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
