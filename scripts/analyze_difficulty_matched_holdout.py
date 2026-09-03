#!/usr/bin/env python3
"""Match Unseen problems to Seen problems using only pre-repair covariates."""

from __future__ import annotations

import argparse
import ast
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def current_code(row: dict[str, Any]) -> str:
    return str(row["history"][-1]["code"])


def ast_nodes(code: str) -> int:
    try:
        return sum(1 for _ in ast.walk(ast.parse(code)))
    except SyntaxError:
        return 0


def problem_features(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["problem_id"])].append(row)
    result = {}
    for problem, members in grouped.items():
        values = []
        for row in members:
            code = current_code(row)
            outcomes = row.get("current_tc_outcomes") or row["history"][-1].get("tc_outcomes", {})
            values.append((
                float(row.get("current_pass_rate", row["history"][-1].get("pass_rate", 0.0))),
                math.log1p(len(str(row["problem_description"]))),
                math.log1p(len(code)),
                math.log1p(ast_nodes(code)),
                math.log1p(len(row["history"])),
                math.log1p(len(outcomes)),
            ))
        result[problem] = [mean(column) for column in zip(*values, strict=True)]
    return result


def minimum_cost_assignment(costs: list[list[float]]) -> list[int]:
    """Return the exact rectangular Hungarian assignment for rows to columns."""
    n = len(costs)
    m = len(costs[0]) if costs else 0
    if n > m or any(len(row) != m for row in costs):
        raise ValueError("assignment requires a rectangular matrix with rows <= columns")
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minimum = [float("inf")] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = float("inf")
            j1 = 0
            for j in range(1, m + 1):
                if used[j]:
                    continue
                current = costs[i0 - 1][j - 1] - u[i0] - v[j]
                if current < minimum[j]:
                    minimum[j] = current
                    way[j] = j0
                if minimum[j] < delta:
                    delta = minimum[j]
                    j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1] * n
    for j in range(1, m + 1):
        if p[j] != 0:
            assignment[p[j] - 1] = j - 1
    if any(value < 0 for value in assignment):
        raise RuntimeError("incomplete assignment")
    return assignment


def match_problems(seen: dict[str, list[float]], unseen: dict[str, list[float]]) -> list[dict[str, Any]]:
    seen_ids = sorted(seen)
    unseen_ids = sorted(unseen)
    all_vectors = list(seen.values()) + list(unseen.values())
    centers = [mean(column) for column in zip(*all_vectors, strict=True)]
    scales = [pstdev(column) or 1.0 for column in zip(*all_vectors, strict=True)]

    def standardized(vector: list[float]) -> list[float]:
        return [(value - center) / scale for value, center, scale in zip(vector, centers, scales, strict=True)]

    seen_z = [standardized(seen[item]) for item in seen_ids]
    unseen_z = [standardized(unseen[item]) for item in unseen_ids]
    costs = [[sum((a - b) ** 2 for a, b in zip(left, right, strict=True)) ** 0.5 for right in seen_z] for left in unseen_z]
    right_indices = minimum_cost_assignment(costs)
    return [
        {
            "unseen_problem": unseen_ids[left],
            "seen_problem": seen_ids[right],
            "standardized_distance": costs[left][right],
        }
        for left, right in enumerate(right_indices)
    ]


def rr_by_problem(rows: list[dict[str, Any]]) -> dict[str, float]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        grouped[str(row["problem_id"])].append(float(bool(row["repaired"])))
    return {problem: mean(values) for problem, values in grouped.items()}


def analyze(
    seen_dataset: list[dict[str, Any]],
    unseen_dataset: list[dict[str, Any]],
    seen_eval: list[dict[str, Any]],
    unseen_eval: list[dict[str, Any]],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    matches = match_problems(problem_features(seen_dataset), problem_features(unseen_dataset))
    seen_rr = rr_by_problem(seen_eval)
    unseen_rr = rr_by_problem(unseen_eval)
    differences = [
        unseen_rr[row["unseen_problem"]] - seen_rr[row["seen_problem"]]
        for row in matches
    ]
    rng = random.Random(seed)
    draws = [mean(rng.choices(differences, k=len(differences))) for _ in range(samples)]
    draws.sort()
    return {
        "matching": "minimum-cost one-to-one assignment on six standardized pre-repair covariates",
        "repair_outcomes_used_for_matching": False,
        "features": ["current_pass_rate", "statement_chars", "current_code_chars", "current_ast_nodes", "history_length", "test_count"],
        "matched_pairs": matches,
        "mean_standardized_distance": mean(row["standardized_distance"] for row in matches),
        "matched_seen_problem_balanced_rr": mean(seen_rr[row["seen_problem"]] for row in matches),
        "unseen_problem_balanced_rr": mean(unseen_rr[row["unseen_problem"]] for row in matches),
        "unseen_minus_matched_seen": mean(differences),
        "paired_problem_bootstrap_95ci": [
            draws[int(0.025 * (len(draws) - 1))],
            draws[int(0.975 * (len(draws) - 1))],
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seen-dataset", type=Path, required=True)
    parser.add_argument("--unseen-dataset", type=Path, required=True)
    parser.add_argument("--seen-evaluation", type=Path, required=True)
    parser.add_argument("--unseen-evaluation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    result = analyze(
        read_jsonl(args.seen_dataset), read_jsonl(args.unseen_dataset),
        read_jsonl(args.seen_evaluation), read_jsonl(args.unseen_evaluation),
        samples=args.samples, seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
