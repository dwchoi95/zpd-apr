#!/usr/bin/env python3
"""Decompose stochastic decoding from candidate breadth on identical draws."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    from analyze_fse2027_robustness import (
        keyed,
        metric,
        paired_suite_rows,
        percentile,
        read_jsonl,
        summarize_method,
    )
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import (
        keyed,
        metric,
        paired_suite_rows,
        percentile,
        read_jsonl,
        summarize_method,
    )


Row = dict[str, Any]


def mean_single_summary(replicates: list[list[Row]]) -> dict[str, Any]:
    if not replicates:
        raise ValueError("at least one single-sample replicate is required")
    maps = [keyed(rows) for rows in replicates]
    ids = set(maps[0])
    if any(set(rows) != ids for rows in maps[1:]):
        raise ValueError("single-sample replicates cover different examples")
    problems = {str(maps[0][item]["problem_id"]) for item in ids}
    return {
        "replicates": len(replicates),
        "examples_per_replicate": len(ids),
        "problems": len(problems),
        "replicate_summaries": [summarize_method(rows) for rows in replicates],
        "mean_pr": sum(metric(rows[item], "pr") for rows in maps for item in ids)
        / (len(maps) * len(ids)),
        "mean_rr": sum(metric(rows[item], "rr") for rows in maps for item in ids)
        / (len(maps) * len(ids)),
        "mean_ir": sum(metric(rows[item], "ir") for rows in maps for item in ids)
        / (len(maps) * len(ids)),
    }


def contrast_against_mean_single(
    left: list[Row],
    single_replicates: list[list[Row]],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    left_map = keyed(left)
    single_maps = [keyed(rows) for rows in single_replicates]
    ids = set(left_map)
    if not single_maps or any(set(rows) != ids for rows in single_maps):
        raise ValueError("contrast inputs cover different examples")
    by_problem: dict[str, list[str]] = defaultdict(list)
    for item, row in left_map.items():
        by_problem[str(row["problem_id"])].append(item)
    problems = sorted(by_problem)
    result: dict[str, Any] = {
        "left": "three-sample union",
        "right": "mean of the same three candidates used one at a time",
        "replicate_paired_contrasts": [
            paired_suite_rows(
                left,
                rows,
                left_label="Stochastic-3",
                right_label=f"Stochastic-1-replicate-{index + 1}",
                samples=samples,
                seed=seed + index * 10,
            )
            for index, rows in enumerate(single_replicates)
        ],
        "metrics": [],
    }
    rng = random.Random(seed + 100)
    for metric_name in ("rr", "ir", "pr"):
        differences = {
            item: metric(left_map[item], metric_name)
            - sum(metric(rows[item], metric_name) for rows in single_maps)
            / len(single_maps)
            for item in ids
        }
        problem_means = {
            problem: sum(differences[item] for item in members) / len(members)
            for problem, members in by_problem.items()
        }
        instance_draws: list[float] = []
        problem_draws: list[float] = []
        for _ in range(samples):
            sampled = [rng.choice(problems) for _ in problems]
            values = [differences[item] for problem in sampled for item in by_problem[problem]]
            instance_draws.append(sum(values) / len(values))
            problem_draws.append(
                sum(problem_means[problem] for problem in sampled) / len(sampled)
            )
        result["metrics"].append(
            {
                "metric": metric_name,
                "left_minus_mean_single_instance_weighted": sum(differences.values())
                / len(differences),
                "cluster_bootstrap_95ci": [
                    percentile(instance_draws, 0.025),
                    percentile(instance_draws, 0.975),
                ],
                "left_minus_mean_single_problem_balanced": sum(problem_means.values())
                / len(problem_means),
                "problem_bootstrap_95ci": [
                    percentile(problem_draws, 0.025),
                    percentile(problem_draws, 0.975),
                ],
            }
        )
    return result


def contrast_mean_single_against_right(
    single_replicates: list[list[Row]],
    right: list[Row],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    right_map = keyed(right)
    single_maps = [keyed(rows) for rows in single_replicates]
    ids = set(right_map)
    if not single_maps or any(set(rows) != ids for rows in single_maps):
        raise ValueError("contrast inputs cover different examples")
    by_problem: dict[str, list[str]] = defaultdict(list)
    for item, row in right_map.items():
        by_problem[str(row["problem_id"])].append(item)
    problems = sorted(by_problem)
    result: dict[str, Any] = {
        "left": "mean of three fixed stochastic one-candidate draws",
        "right": "greedy one-candidate output",
        "metrics": [],
    }
    rng = random.Random(seed)
    for metric_name in ("rr", "ir", "pr"):
        differences = {
            item: sum(metric(rows[item], metric_name) for rows in single_maps)
            / len(single_maps)
            - metric(right_map[item], metric_name)
            for item in ids
        }
        problem_means = {
            problem: sum(differences[item] for item in members) / len(members)
            for problem, members in by_problem.items()
        }
        instance_draws: list[float] = []
        problem_draws: list[float] = []
        for _ in range(samples):
            sampled = [rng.choice(problems) for _ in problems]
            values = [differences[item] for problem in sampled for item in by_problem[problem]]
            instance_draws.append(sum(values) / len(values))
            problem_draws.append(
                sum(problem_means[problem] for problem in sampled) / len(sampled)
            )
        result["metrics"].append(
            {
                "metric": metric_name,
                "mean_single_minus_right_instance_weighted": sum(differences.values())
                / len(differences),
                "cluster_bootstrap_95ci": [
                    percentile(instance_draws, 0.025),
                    percentile(instance_draws, 0.975),
                ],
                "mean_single_minus_right_problem_balanced": sum(problem_means.values())
                / len(problem_means),
                "problem_bootstrap_95ci": [
                    percentile(problem_draws, 0.025),
                    percentile(problem_draws, 0.975),
                ],
            }
        )
    return result


def analyze_split(
    stochastic3: list[Row],
    stochastic1: list[list[Row]],
    greedy1: list[Row],
    checkpoint3: list[Row],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    return {
        "stochastic_three_union": summarize_method(stochastic3),
        "stochastic_one_expectation": mean_single_summary(stochastic1),
        "greedy_one": summarize_method(greedy1),
        "independent_checkpoint_three": summarize_method(checkpoint3),
        "three_minus_same_draw_one": contrast_against_mean_single(
            stochastic3, stochastic1, samples=samples, seed=seed
        ),
        "stochastic_one_minus_greedy_one_expected": contrast_mean_single_against_right(
            stochastic1, greedy1, samples=samples, seed=seed + 500
        ),
        "stochastic_one_minus_greedy_one": [
            paired_suite_rows(
                rows,
                greedy1,
                left_label=f"Stochastic-1-replicate-{index + 1}",
                right_label="Greedy-1",
                samples=samples,
                seed=seed + 1000 + index * 10,
            )
            for index, rows in enumerate(stochastic1)
        ],
        "checkpoint_three_minus_same_draw_stochastic_three": paired_suite_rows(
            checkpoint3,
            stochastic3,
            left_label="Independent-checkpoint-greedy-3",
            right_label="Same-draw-stochastic-3",
            samples=samples,
            seed=seed + 2000,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--reference-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    seeds = (4101, 4102, 4103)
    result: dict[str, Any] = {
        "control": "same three stochastic draws evaluated singly and as an execution union",
        "estimand": "S3 union minus the expected success of one uniformly selected draw from the identical fixed candidate set",
        "decoding": {
            "checkpoint": "Answer2027",
            "sampling_seeds": list(seeds),
            "temperature": 0.8,
            "top_p": 0.95,
            "prompt": "D full authentic trajectory",
        },
        "test_outcomes_used_for_configuration": False,
        "splits": {},
    }
    for offset, split in enumerate(("seen", "unseen")):
        split_root = args.eval_root / split
        greedy_path = (
            args.reference_root / "answer-seen-test.evaluation.jsonl"
            if split == "seen"
            else args.reference_root / "answer-seed-control" / "answer2027-unseen-test.evaluation.jsonl"
        )
        result["splits"][split] = analyze_split(
            read_jsonl(split_root / "stochastic3.evaluation.jsonl"),
            [read_jsonl(split_root / f"sample-{seed}.evaluation.jsonl") for seed in seeds],
            read_jsonl(greedy_path),
            read_jsonl(
                args.reference_root
                / "selected-portfolios"
                / f"answer-3seed-{split}-test.evaluation.jsonl"
            ),
            samples=args.samples,
            seed=2027 + offset * 100,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
