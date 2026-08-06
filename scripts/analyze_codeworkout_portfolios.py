#!/usr/bin/env python3
"""Compare relation-selected and Answer-seed portfolios on CodeWorkout."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

from analyze_fse2027_selected_portfolios import holm_adjust


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def portfolio(evaluations: list[list[Row]]) -> tuple[list[Row], Row]:
    maps = [{str(row["example_id"]): row for row in rows} for rows in evaluations]
    if any(len(mapping) != len(rows) for mapping, rows in zip(maps, evaluations, strict=True)):
        raise ValueError("duplicate example_id in candidate evaluation")
    example_ids = sorted(maps[0])
    if any(set(candidate) != set(example_ids) for candidate in maps[1:]):
        raise ValueError("candidate evaluations cover different examples")
    output = []
    for example_id in example_ids:
        candidates = [candidate[example_id] for candidate in maps]
        identity = {
            (
                str(row["problem_id"]),
                str(row["user_id"]),
                float(row["current_pass_rate"]),
            )
            for row in candidates
        }
        if len(identity) != 1:
            raise ValueError(
                f"candidate baselines disagree for example_id={example_id}: "
                f"{sorted(identity)}"
            )
        current = float(candidates[0]["current_pass_rate"])
        fixed = max([current] + [float(row["fixed_pass_rate"]) for row in candidates])
        output.append(
            {
                "example_id": example_id,
                "problem_id": candidates[0]["problem_id"],
                "user_id": candidates[0]["user_id"],
                "current_pass_rate": current,
                "fixed_pass_rate": fixed,
                "repaired": any(bool(row["repaired"]) for row in candidates),
                "improved": fixed > current,
            }
        )
    n = len(output)
    summary = {
        "examples": n,
        "problems": len({row["problem_id"] for row in output}),
        "students": len({row["user_id"] for row in output}),
        "pass_rate": sum(row["fixed_pass_rate"] for row in output) / n,
        "repair_rate": sum(row["repaired"] for row in output) / n,
        "improvement_rate": sum(row["improved"] for row in output) / n,
    }
    return output, summary


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    lower = min(left_only, right_only)
    tail = sum(math.comb(discordant, k) for k in range(lower + 1)) / (2**discordant)
    return min(1.0, 2 * tail)


def clustered_interval(
    left: list[Row], right: list[Row], cluster_key: str, seed: int = 2027
) -> list[float]:
    paired = {str(row["example_id"]): row for row in right}
    by_cluster: dict[str, list[float]] = {}
    for row in left:
        difference = float(bool(row["repaired"])) - float(
            bool(paired[str(row["example_id"])]["repaired"])
        )
        by_cluster.setdefault(str(row[cluster_key]), []).append(difference)
    clusters = sorted(by_cluster)
    rng = random.Random(seed)
    estimates = []
    for _ in range(10_000):
        sampled = [rng.choice(clusters) for _ in clusters]
        values = [value for cluster in sampled for value in by_cluster[cluster]]
        estimates.append(sum(values) / len(values))
    estimates.sort()
    return [estimates[250], estimates[9749]]


def paired_rr_report(
    left: list[Row], right: list[Row], left_label: str, right_label: str
) -> Row:
    right_by_id = {str(row["example_id"]): row for row in right}
    if set(right_by_id) != {str(row["example_id"]) for row in left}:
        raise ValueError("paired portfolios cover different examples")
    left_only = sum(
        bool(row["repaired"])
        and not bool(right_by_id[str(row["example_id"])]["repaired"])
        for row in left
    )
    right_only = sum(
        not bool(row["repaired"])
        and bool(right_by_id[str(row["example_id"])]["repaired"])
        for row in left
    )
    return {
        "left": left_label,
        "right": right_label,
        "left_minus_right": (
            sum(bool(row["repaired"]) for row in left)
            - sum(bool(row["repaired"]) for row in right)
        )
        / len(left),
        "problem_cluster_95ci": clustered_interval(left, right, "problem_id"),
        "student_cluster_95ci": clustered_interval(left, right, "user_id"),
        "left_only": left_only,
        "right_only": right_only,
        "exact_mcnemar_two_sided_p": exact_mcnemar(left_only, right_only),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluation", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--relation-member", action="append", required=True)
    parser.add_argument("--answer-member", action="append", required=True)
    parser.add_argument("--unconstrained-member", action="append", required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    selected_members = selection["selected_relation_constrained"]["members"]
    selected_answer_members = selection["answer_3seed_control"]["members"]
    selected_unconstrained_members = selection["best_unconstrained"]["members"]
    if set(args.relation_member) != set(selected_members):
        raise ValueError("test relation members do not match validation selection")
    if set(args.answer_member) != set(selected_answer_members):
        raise ValueError("test Answer members do not match validation control")
    if set(args.unconstrained_member) != set(selected_unconstrained_members):
        raise ValueError("test unconstrained members do not match validation selection")
    evaluations = {}
    for raw in args.evaluation:
        name, path = raw.split("=", 1)
        evaluations[name] = read_jsonl(Path(path))
    relation_rows, relation_summary = portfolio(
        [evaluations[name] for name in args.relation_member]
    )
    answer_rows, answer_summary = portfolio(
        [evaluations[name] for name in args.answer_member]
    )
    unconstrained_rows, unconstrained_summary = portfolio(
        [evaluations[name] for name in args.unconstrained_member]
    )
    relation_vs_answer = paired_rr_report(
        relation_rows, answer_rows, "relation-constrained", "Answer-3Seed"
    )
    relation_vs_unconstrained = paired_rr_report(
        relation_rows,
        unconstrained_rows,
        "relation-constrained",
        "unconstrained",
    )
    unconstrained_vs_answer = paired_rr_report(
        unconstrained_rows, answer_rows, "unconstrained", "Answer-3Seed"
    )
    report = {
        "dataset": "TIKTOC CodeWorkout actual CS1 Java trajectories",
        "split": "student-held-out test",
        "validation_selection": {
            "partition": "student-disjoint validation",
            "test_outcomes_used": False,
            "constraint": "one independently trained checkpoint per relation",
            "feasible_portfolios": selection[
                "feasible_relation_constrained_portfolios"
            ],
            "selected": selection["selected_relation_constrained"],
            "answer_3seed_control": selection["answer_3seed_control"],
            "best_unconstrained": selection["best_unconstrained"],
        },
        "relation_members": args.relation_member,
        "answer_members": args.answer_member,
        "unconstrained_members": args.unconstrained_member,
        "relation_portfolio": relation_summary,
        "answer_3seed": answer_summary,
        "unconstrained_portfolio": unconstrained_summary,
        "paired_rr_relation_vs_answer": relation_vs_answer,
        "paired_rr_relation_vs_unconstrained": relation_vs_unconstrained,
        "paired_rr_unconstrained_vs_answer": unconstrained_vs_answer,
        "planned_rr_family_holm": holm_adjust(
            {
                "relation_vs_answer": relation_vs_answer[
                    "exact_mcnemar_two_sided_p"
                ],
                "relation_vs_unconstrained": relation_vs_unconstrained[
                    "exact_mcnemar_two_sided_p"
                ],
                "unconstrained_vs_answer": unconstrained_vs_answer[
                    "exact_mcnemar_two_sided_p"
                ],
            }
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
