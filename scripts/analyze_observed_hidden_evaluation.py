#!/usr/bin/env python3
"""Analyze selection-test and independent hidden-test repair outcomes."""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_keyed(path: Path) -> dict[str, Row]:
    with path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    keyed = {str(row["example_id"]): row for row in rows}
    if len(keyed) != len(rows):
        raise ValueError(f"duplicate example_id in {path}")
    return keyed


def method_rows(
    selected_path: Path,
    hidden_paths: dict[str, Path],
) -> list[Row]:
    selected = read_keyed(selected_path)
    hidden = {name: read_keyed(path) for name, path in hidden_paths.items()}
    rows: list[Row] = []
    for example_id, choice in selected.items():
        source = str(choice.get("selected_source", "current-fallback"))
        observed_repaired = bool(choice.get("repaired"))
        hidden_row = hidden.get(source, {}).get(example_id)
        hidden_repaired = bool(hidden_row and hidden_row.get("repaired"))
        rows.append(
            {
                "example_id": example_id,
                "problem_id": str(choice["problem_id"]),
                "selected_source": source,
                "observed_repaired": observed_repaired,
                "hidden_repaired": hidden_repaired,
                "jointly_repaired": observed_repaired and hidden_repaired,
            }
        )
    return rows


def summarize(rows: list[Row]) -> dict[str, Any]:
    observed = sum(row["observed_repaired"] for row in rows)
    hidden = sum(row["hidden_repaired"] for row in rows)
    joint = sum(row["jointly_repaired"] for row in rows)
    return {
        "examples": len(rows),
        "problems": len({row["problem_id"] for row in rows}),
        "observed_repairs": observed,
        "hidden_repairs": hidden,
        "joint_repairs": joint,
        "observed_repair_rate": observed / len(rows),
        "hidden_repair_rate": hidden / len(rows),
        "joint_repair_rate": joint / len(rows),
        "joint_repair_rate_wilson_95_ci": wilson(joint, len(rows)),
        "hidden_confirmation_given_observed": joint / observed if observed else None,
        "hidden_confirmation_wilson_95_ci": (
            wilson(joint, observed) if observed else None
        ),
        "selected_source_counts": dict(
            sorted(Counter(row["selected_source"] for row in rows).items())
        ),
    }


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        raise ValueError("Wilson interval needs a positive denominator")
    rate = successes / total
    scale = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / scale
    radius = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / scale
    return [max(0.0, center - radius), min(1.0, center + radius)]


def exact_mcnemar(left: list[Row], right: list[Row]) -> dict[str, Any]:
    left_by_id = {row["example_id"]: row for row in left}
    right_by_id = {row["example_id"]: row for row in right}
    if set(left_by_id) != set(right_by_id):
        raise ValueError("methods cover different examples")
    left_only = sum(
        left_by_id[key]["jointly_repaired"]
        and not right_by_id[key]["jointly_repaired"]
        for key in left_by_id
    )
    right_only = sum(
        right_by_id[key]["jointly_repaired"]
        and not left_by_id[key]["jointly_repaired"]
        for key in left_by_id
    )
    discordant = left_only + right_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, k) for k in range(min(left_only, right_only) + 1)
        ) / (2**discordant)
        p_value = min(1.0, 2 * tail)
    return {
        "left_only_joint_repairs": left_only,
        "right_only_joint_repairs": right_only,
        "exact_mcnemar_p": p_value,
    }


def clustered_difference(
    left: list[Row], right: list[Row], *, samples: int, seed: int
) -> dict[str, Any]:
    left_by_id = {row["example_id"]: row for row in left}
    right_by_id = {row["example_id"]: row for row in right}
    if set(left_by_id) != set(right_by_id):
        raise ValueError("methods cover different examples")
    by_problem: dict[str, list[str]] = defaultdict(list)
    for example_id, row in left_by_id.items():
        by_problem[row["problem_id"]].append(example_id)
    problems = sorted(by_problem)

    def difference(sampled: list[str]) -> float:
        values = []
        for problem_id in sampled:
            ids = by_problem[problem_id]
            left_rate = sum(left_by_id[i]["jointly_repaired"] for i in ids) / len(ids)
            right_rate = sum(right_by_id[i]["jointly_repaired"] for i in ids) / len(ids)
            values.append(left_rate - right_rate)
        return sum(values) / len(values)

    estimate = difference(problems)
    rng = random.Random(seed)
    draws = sorted(
        difference([rng.choice(problems) for _ in problems]) for _ in range(samples)
    )
    lo = draws[int(0.025 * samples)]
    hi = draws[min(samples - 1, int(0.975 * samples))]
    return {
        "estimand": "equal-problem-weight joint repair-rate difference",
        "left_minus_right": estimate,
        "problem_cluster_95_ci": [lo, hi],
        "bootstrap_samples": samples,
        "seed": seed,
    }


def parse_method(value: str) -> tuple[str, Path, dict[str, Path]]:
    parts = value.split(",")
    if len(parts) < 3 or "=" not in parts[0] or "=" not in parts[1]:
        raise ValueError(
            "--method must be NAME=SELECTED,SOURCE=HIDDEN_EVAL[,SOURCE=HIDDEN_EVAL...]"
        )
    name, selected = parts[0].split("=", 1)
    hidden: dict[str, Path] = {}
    for part in parts[1:]:
        source, path = part.split("=", 1)
        hidden[source] = Path(path)
    return name, Path(selected), hidden


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--method", action="append", required=True)
    parser.add_argument("--compare", help="LEFT,RIGHT")
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    results: dict[str, list[Row]] = {}
    summaries: dict[str, Any] = {}
    for value in args.method:
        name, selected, hidden = parse_method(value)
        results[name] = method_rows(selected, hidden)
        summaries[name] = summarize(results[name])
    report: dict[str, Any] = {"methods": summaries}
    if args.compare:
        left, right = args.compare.split(",", 1)
        report["comparison"] = {
            "left": left,
            "right": right,
            **clustered_difference(
                results[left],
                results[right],
                samples=args.bootstrap_samples,
                seed=args.seed,
            ),
            **exact_mcnemar(results[left], results[right]),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
