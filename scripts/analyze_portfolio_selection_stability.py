#!/usr/bin/env python3
"""Audit problem-level stability of validation-frozen size-three selection."""

from __future__ import annotations

import argparse
import itertools
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from select_execution_portfolio import read_jsonl
except ModuleNotFoundError:  # Imported as scripts.analyze_portfolio_selection_stability.
    from scripts.select_execution_portfolio import read_jsonl


Row = dict[str, Any]


def problem_keyed(rows: list[Row]) -> dict[str, Row]:
    result = {str(row["problem_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("stability audit requires one validation example per problem")
    return result


def deterministic_key(names: tuple[str, ...]) -> tuple[int, ...]:
    return tuple(-sum(ord(char) for char in name) for name in names)


def analyze(
    evaluations: dict[str, list[Row]],
    *,
    test_rows: list[Row] | None,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    maps = {name: problem_keyed(rows) for name, rows in evaluations.items()}
    problems = sorted(next(iter(maps.values())))
    if any(set(candidate) != set(problems) for candidate in maps.values()):
        raise ValueError("candidate evaluations cover different validation problems")
    portfolios = list(itertools.combinations(sorted(maps), 3))
    per_problem: dict[tuple[str, ...], list[tuple[int, float, int]]] = {}
    totals: dict[tuple[str, ...], tuple[int, float, int]] = {}
    for names in portfolios:
        values = []
        for problem in problems:
            rows = [maps[name][problem] for name in names]
            baseline_value = rows[0].get("buggy_pass_rate", rows[0].get("current_pass_rate"))
            if baseline_value is None:
                raise ValueError("candidate evaluation lacks current/buggy pass rate")
            baseline = float(baseline_value)
            best_pass = max([baseline] + [float(row["fixed_pass_rate"]) for row in rows])
            values.append((int(any(bool(row["repaired"]) for row in rows)), best_pass, int(best_pass > baseline)))
        per_problem[names] = values
        totals[names] = tuple(sum(value[index] for value in values) for index in range(3))

    def select_from_scores(scores: dict[tuple[str, ...], tuple[int, float, int]]) -> tuple[str, ...]:
        return max(
            portfolios,
            key=lambda names: (*scores[names], deterministic_key(names)),
        )

    selected = select_from_scores(totals)
    ranked = sorted(
        portfolios,
        key=lambda names: (*totals[names], deterministic_key(names)),
        reverse=True,
    )
    jackknife = Counter()
    for index in range(len(problems)):
        scores = {
            names: tuple(totals[names][field] - per_problem[names][index][field] for field in range(3))
            for names in portfolios
        }
        jackknife[select_from_scores(scores)] += 1

    rng = random.Random(seed)
    bootstrap = Counter()
    for _ in range(samples):
        counts = Counter(rng.randrange(len(problems)) for _ in problems)
        scores = {}
        for names in portfolios:
            values = per_problem[names]
            scores[names] = tuple(
                sum(count * values[index][field] for index, count in counts.items())
                for field in range(3)
            )
        bootstrap[select_from_scores(scores)] += 1

    test_problems = {str(row["problem_id"]) for row in test_rows or []}
    overlap = sorted(set(problems) & test_problems)
    disjoint_indices = [
        index for index, problem in enumerate(problems) if problem not in test_problems
    ]
    disjoint_scores = {
        names: tuple(
            sum(per_problem[names][index][field] for index in disjoint_indices)
            for field in range(3)
        )
        for names in portfolios
    }
    selected_disjoint = select_from_scores(disjoint_scores) if disjoint_indices else None

    def frequencies(counter: Counter, denominator: int) -> list[dict[str, Any]]:
        return [
            {"members": list(names), "count": count, "fraction": count / denominator}
            for names, count in counter.most_common()
        ]

    return {
        "selection_partition": "Seen validation, one trajectory per problem",
        "test_outcomes_used_for_selection": False,
        "candidate_checkpoints": sorted(maps),
        "candidate_count": len(maps),
        "portfolio_size": 3,
        "feasible_portfolios": len(portfolios),
        "validation_problems": len(problems),
        "test_problems": len(test_problems),
        "validation_test_problem_overlap": len(overlap),
        "selected_full_validation": {
            "members": list(selected),
            "repaired_problems": totals[selected][0],
            "pass_rate_sum": totals[selected][1],
            "improved_problems": totals[selected][2],
        },
        "selected_problem_disjoint_validation": (
            {
                "members": list(selected_disjoint),
                "validation_problems": len(disjoint_indices),
                "repaired_problems": disjoint_scores[selected_disjoint][0],
                "pass_rate_sum": disjoint_scores[selected_disjoint][1],
                "improved_problems": disjoint_scores[selected_disjoint][2],
            }
            if selected_disjoint is not None
            else None
        ),
        "runner_up_full_validation": {
            "members": list(ranked[1]),
            "repaired_problems": totals[ranked[1]][0],
            "coverage_margin_problems": totals[selected][0] - totals[ranked[1]][0],
        },
        "leave_one_problem_out": {
            "replicates": len(problems),
            "full_selection_fraction": jackknife[selected] / len(problems),
            "selection_frequencies": frequencies(jackknife, len(problems)),
        },
        "problem_bootstrap": {
            "samples": samples,
            "seed": seed,
            "full_selection_fraction": bootstrap[selected] / samples,
            "selection_frequencies": frequencies(bootstrap, samples),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--test-evaluation", type=Path)
    parser.add_argument("--bootstrap-samples", type=int, default=2_000)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluations = {}
    for raw in args.evaluation:
        if "=" not in raw:
            parser.error("--evaluation must use NAME=PATH")
        name, path = raw.split("=", 1)
        evaluations[name] = read_jsonl(Path(path))
    result = analyze(
        evaluations,
        test_rows=read_jsonl(args.test_evaluation) if args.test_evaluation else None,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["selected_full_validation"], sort_keys=True))


if __name__ == "__main__":
    main()
