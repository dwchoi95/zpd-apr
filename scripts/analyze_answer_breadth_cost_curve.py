#!/usr/bin/env python3
"""Analyze a fixed-seed Answer breadth/cost curve without test-time tuning."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


SEEDS = tuple(range(4101, 4121))
K_VALUES = (1, 3, 5, 10, 20)


def read_keyed(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    result = {str(row["example_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate example_id in {path}")
    return result


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def cluster_interval(
    values: dict[str, float], problems: dict[str, str], *, samples: int, seed: int
) -> list[float]:
    by_problem: dict[str, list[str]] = defaultdict(list)
    for example_id, problem_id in problems.items():
        by_problem[problem_id].append(example_id)
    identities = sorted(by_problem)
    rng = random.Random(seed)
    draws: list[float] = []
    for _ in range(samples):
        selected = [rng.choice(identities) for _ in identities]
        observations = [
            values[example_id]
            for problem_id in selected
            for example_id in by_problem[problem_id]
        ]
        draws.append(sum(observations) / len(observations))
    return [percentile(draws, 0.025), percentile(draws, 0.975)]


def analyze_split(root: Path, split: str, *, samples: int, seed: int) -> dict[str, Any]:
    evaluations = [
        read_keyed(root / split / f"sample-{sampling_seed}.evaluation.jsonl")
        for sampling_seed in SEEDS
    ]
    generations = [
        read_keyed(root / split / f"sample-{sampling_seed}.generations.jsonl")
        for sampling_seed in SEEDS
    ]
    example_ids = sorted(evaluations[0])
    if any(set(rows) != set(example_ids) for rows in evaluations[1:]):
        raise ValueError(f"{split}: sampling seeds cover different examples")
    if any(set(rows) != set(example_ids) for rows in generations):
        raise ValueError(f"{split}: generation seeds cover different examples")
    problems = {
        example_id: str(evaluations[0][example_id]["problem_id"])
        for example_id in example_ids
    }
    previous: dict[str, float] | None = None
    curve: dict[str, Any] = {}
    for offset, k in enumerate(K_VALUES):
        repaired = {
            example_id: float(
                any(bool(rows[example_id]["repaired"]) for rows in evaluations[:k])
            )
            for example_id in example_ids
        }
        calls = {}
        amortized_generation_sec = {}
        for example_id in example_ids:
            calls[example_id] = float(k)
            amortized_generation_sec[example_id] = sum(
                float(rows[example_id]["generation_time_sec"])
                for rows in generations[:k]
            )
            for index, rows in enumerate(evaluations[:k], start=1):
                if bool(rows[example_id]["repaired"]):
                    calls[example_id] = float(index)
                    amortized_generation_sec[example_id] = sum(
                        float(generations[position][example_id]["generation_time_sec"])
                        for position in range(index)
                    )
                    break
        by_problem: dict[str, list[str]] = defaultdict(list)
        for example_id, problem_id in problems.items():
            by_problem[problem_id].append(example_id)
        marginal = repaired if previous is None else {
            example_id: repaired[example_id] - previous[example_id]
            for example_id in example_ids
        }
        curve[str(k)] = {
            "examples": len(example_ids),
            "problems": len(by_problem),
            "union_repair_rate": sum(repaired.values()) / len(repaired),
            "union_repair_rate_cluster_95ci": cluster_interval(
                repaired, problems, samples=samples, seed=seed + offset * 10
            ),
            "problem_balanced_union_repair_rate": sum(
                sum(repaired[item] for item in members) / len(members)
                for members in by_problem.values()
            ) / len(by_problem),
            "newly_repaired_since_previous_k": int(sum(marginal.values())),
            "mean_sequential_candidates_invoked": sum(calls.values()) / len(calls),
            "mean_amortized_generation_sec": sum(amortized_generation_sec.values())
            / len(amortized_generation_sec),
        }
        if previous is not None:
            curve[str(k)]["rr_gain_since_previous_k"] = sum(marginal.values()) / len(marginal)
            curve[str(k)]["rr_gain_cluster_95ci"] = cluster_interval(
                marginal, problems, samples=samples, seed=seed + offset * 10 + 1
            )
        previous = repaired
    return curve


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result = {
        "protocol": "All k cells and the fixed seed order were frozen before outcomes; no test-time k selection.",
        "temperature": 0.8,
        "top_p": 0.95,
        "generation_cost_note": "generation_time_sec is batch elapsed time divided by requests; the curve sums this amortized throughput cost only for calls before early stopping and is not interactive wall-clock latency.",
        "sampling_seeds_in_order": list(SEEDS),
        "reported_k": list(K_VALUES),
        "splits": {
            split: analyze_split(
                args.root, split, samples=args.samples, seed=7300 + index * 100
            )
            for index, split in enumerate(("seen", "unseen"))
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
