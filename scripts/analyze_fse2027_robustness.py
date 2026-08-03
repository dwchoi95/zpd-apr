#!/usr/bin/env python3
"""Generate code-free robustness analyses from canonical evaluation artifacts.

The script deliberately emits only aggregate statistics.  Per-instance source
code and generated programs remain in the execution environment.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def keyed(rows: Iterable[Row]) -> dict[str, Row]:
    materialized = list(rows)
    result = {str(row["example_id"]): row for row in materialized}
    if len(result) != len(materialized):
        raise ValueError("duplicate example_id")
    return result


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def metric(row: Row, name: str) -> float:
    if name == "rr":
        return float(bool(row["repaired"]))
    if name == "ir":
        return float(bool(row["improved"]))
    if name == "pr":
        return float(row["fixed_pass_rate"])
    raise ValueError(name)


def paired_cluster_analysis(
    left_rows: list[Row],
    right_rows: list[Row],
    *,
    metric_name: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    left = keyed(left_rows)
    right = keyed(right_rows)
    if set(left) != set(right):
        raise ValueError("paired inputs have different example IDs")
    by_problem: dict[str, list[str]] = defaultdict(list)
    for example_id, row in left.items():
        by_problem[str(row["problem_id"])].append(example_id)
    problems = sorted(by_problem)
    differences = {
        example_id: metric(left[example_id], metric_name)
        - metric(right[example_id], metric_name)
        for example_id in left
    }
    observed = sum(differences.values()) / len(differences)
    problem_means = {
        problem: sum(differences[item] for item in ids) / len(ids)
        for problem, ids in by_problem.items()
    }
    problem_balanced = sum(problem_means.values()) / len(problem_means)
    rng = random.Random(seed)
    instance_weighted_draws: list[float] = []
    problem_balanced_draws: list[float] = []
    for _ in range(samples):
        sampled = [rng.choice(problems) for _ in problems]
        values = [differences[item] for problem in sampled for item in by_problem[problem]]
        instance_weighted_draws.append(sum(values) / len(values))
        problem_balanced_draws.append(
            sum(problem_means[problem] for problem in sampled) / len(sampled)
        )
    return {
        "metric": metric_name,
        "examples": len(left),
        "problems": len(problems),
        "left_minus_right_instance_weighted": observed,
        "cluster_bootstrap_95ci": [
            percentile(instance_weighted_draws, 0.025),
            percentile(instance_weighted_draws, 0.975),
        ],
        "left_minus_right_problem_balanced": problem_balanced,
        "problem_bootstrap_95ci": [
            percentile(problem_balanced_draws, 0.025),
            percentile(problem_balanced_draws, 0.975),
        ],
    }


def summarize_method(rows: list[Row]) -> dict[str, Any]:
    by_problem: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        by_problem[str(row["problem_id"])].append(row)
    buggy_fixed_ted = [
        float(row["ted_buggy_fixed"])
        for row in rows
        if bool(row["repaired"]) and row.get("ted_buggy_fixed") is not None
    ]
    fixed_oracle_ted = [
        float(row["ted_fixed_oracle"])
        for row in rows
        if bool(row["repaired"]) and row.get("ted_fixed_oracle") is not None
    ]
    return {
        "examples": len(rows),
        "problems": len(by_problem),
        "pr": sum(metric(row, "pr") for row in rows) / len(rows),
        "rr": sum(metric(row, "rr") for row in rows) / len(rows),
        "ir": sum(metric(row, "ir") for row in rows) / len(rows),
        "problem_balanced_rr": sum(
            sum(metric(row, "rr") for row in group) / len(group)
            for group in by_problem.values()
        )
        / len(by_problem),
        "mean_ted_buggy_fixed_on_repaired": (
            sum(buggy_fixed_ted) / len(buggy_fixed_ted) if buggy_fixed_ted else None
        ),
        "parseable_repaired_for_buggy_fixed_ted": len(buggy_fixed_ted),
        "mean_ted_fixed_oracle_on_repaired": (
            sum(fixed_oracle_ted) / len(fixed_oracle_ted) if fixed_oracle_ted else None
        ),
        "parseable_repaired_for_fixed_oracle_ted": len(fixed_oracle_ted),
    }


def paired_suite(
    left_path: Path,
    right_path: Path,
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    left = read_jsonl(left_path)
    right = read_jsonl(right_path)
    return paired_suite_rows(
        left,
        right,
        left_label=str(left_path),
        right_label=str(right_path),
        samples=samples,
        seed=seed,
    )


def paired_suite_rows(
    left: list[Row],
    right: list[Row],
    *,
    left_label: str,
    right_label: str,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    left_by_id = keyed(left)
    right_by_id = keyed(right)
    shared = sorted(set(left_by_id) & set(right_by_id))
    if len(shared) != len(left_by_id) or len(shared) != len(right_by_id):
        raise ValueError("paired inputs have different example IDs")
    rr_contingency = {
        "both_repaired": sum(
            bool(left_by_id[item]["repaired"]) and bool(right_by_id[item]["repaired"])
            for item in shared
        ),
        "left_only": sum(
            bool(left_by_id[item]["repaired"]) and not bool(right_by_id[item]["repaired"])
            for item in shared
        ),
        "right_only": sum(
            not bool(left_by_id[item]["repaired"]) and bool(right_by_id[item]["repaired"])
            for item in shared
        ),
        "neither": sum(
            not bool(left_by_id[item]["repaired"]) and not bool(right_by_id[item]["repaired"])
            for item in shared
        ),
    }
    discordant = rr_contingency["left_only"] + rr_contingency["right_only"]
    smaller = min(rr_contingency["left_only"], rr_contingency["right_only"])
    exact_mcnemar_p = (
        min(
            1.0,
            2.0
            * sum(math.comb(discordant, index) for index in range(smaller + 1))
            / (2**discordant),
        )
        if discordant
        else 1.0
    )
    joint_ted = [
        (
            float(left_by_id[item]["ted_buggy_fixed"]),
            float(right_by_id[item]["ted_buggy_fixed"]),
        )
        for item in shared
        if bool(left_by_id[item]["repaired"])
        and bool(right_by_id[item]["repaired"])
        and left_by_id[item].get("ted_buggy_fixed") is not None
        and right_by_id[item].get("ted_buggy_fixed") is not None
    ]
    rng = random.Random(seed + 9)
    ted_difference = None
    if joint_ted:
        observed_ted = sum(right_ted - left_ted for left_ted, right_ted in joint_ted) / len(joint_ted)
        draws = []
        for _ in range(samples):
            sample = [rng.choice(joint_ted) for _ in joint_ted]
            draws.append(sum(right_ted - left_ted for left_ted, right_ted in sample) / len(sample))
        ted_difference = {
            "joint_repairs": len(joint_ted),
            "right_minus_left_mean_ted": observed_ted,
            "instance_bootstrap_95ci": [percentile(draws, 0.025), percentile(draws, 0.975)],
        }
    return {
        "left": left_label,
        "right": right_label,
        "left_summary": summarize_method(left),
        "right_summary": summarize_method(right),
        "rr_contingency": rr_contingency,
        "exact_mcnemar_two_sided_p": exact_mcnemar_p,
        "paired_ted": ted_difference,
        "paired": [
            paired_cluster_analysis(
                left,
                right,
                metric_name=name,
                samples=samples,
                seed=seed + offset,
            )
            for offset, name in enumerate(("rr", "pr", "ir"))
        ],
    }


def replay_orders(root: Path) -> dict[str, Any]:
    names = ("progress", "strict", "answer")
    rows = {
        name: keyed(read_jsonl(root / f"{name}-seen-test.evaluation.jsonl"))
        for name in names
    }
    ids = set(rows[names[0]])
    if any(set(rows[name]) != ids for name in names[1:]):
        raise ValueError("adapter evaluations have different IDs")
    policies = {"progress": 1, "strict": 2, "answer": 3}
    results = []
    for order in itertools.permutations(names):
        repaired = 0
        improved = 0
        calls = 0
        pass_rate_sum = 0.0
        generation_time_sum = 0.0
        teds: list[float] = []
        oracle_teds: list[float] = []
        breadth: list[int] = []
        selected_counts = {name: 0 for name in names}
        selected_counts["current-fallback"] = 0
        reached_counts = {name: 0 for name in names}
        accepted_counts = {name: 0 for name in names}
        for example_id in ids:
            selected: Row | None = None
            invoked: list[tuple[str, Row]] = []
            for call_index, name in enumerate(order, start=1):
                calls += 1
                reached_counts[name] += 1
                row = rows[name][example_id]
                invoked.append((name, row))
                generation_time_sum += float(row.get("generation_time_sec", 0.0))
                if bool(row["repaired"]):
                    repaired += 1
                    accepted_counts[name] += 1
                    selected = row
                    selected_counts[name] += 1
                    breadth.append(policies[name])
                    if row.get("ted_buggy_fixed") is not None:
                        teds.append(float(row["ted_buggy_fixed"]))
                    if row.get("ted_fixed_oracle") is not None:
                        oracle_teds.append(float(row["ted_fixed_oracle"]))
                    break
            baseline = float(rows[names[0]][example_id]["buggy_pass_rate"])
            if selected is None:
                best_pass_rate = max(
                    [baseline]
                    + [float(row["fixed_pass_rate"]) for _name, row in invoked]
                )
                if baseline == best_pass_rate:
                    selected_counts["current-fallback"] += 1
                    selected_pass_rate = baseline
                else:
                    tied = [
                        (name, row)
                        for name, row in invoked
                        if float(row["fixed_pass_rate"]) == best_pass_rate
                    ]
                    name, selected = min(
                        tied,
                        key=lambda item: (
                            int(item[1]["tree_edit_distance"])
                            if item[1].get("tree_edit_distance") is not None
                            else 10**9
                        ),
                    )
                    selected_counts[name] += 1
                    selected_pass_rate = float(selected["fixed_pass_rate"])
            else:
                selected_pass_rate = float(selected["fixed_pass_rate"])
            pass_rate_sum += selected_pass_rate
            improved += int(selected_pass_rate > baseline)
        results.append(
            {
                "order": list(order),
                "repair_rate": repaired / len(ids),
                "pass_rate": pass_rate_sum / len(ids),
                "improvement_rate": improved / len(ids),
                "mean_generations": calls / len(ids),
                "mean_generation_time_sec": generation_time_sum / len(ids),
                "mean_policy_breadth_on_repairs": sum(breadth) / len(breadth),
                "mean_ted_on_parseable_repairs": sum(teds) / len(teds),
                "mean_oracle_ted_on_repairs": sum(oracle_teds) / len(oracle_teds),
                "selected_source_counts": selected_counts,
                "reached_counts": reached_counts,
                "accepted_counts": accepted_counts,
            }
        )
    return {"examples": len(ids), "static_candidate_order_replay": results}


def replay_selected_rows(root: Path, order: tuple[str, ...]) -> list[Row]:
    rows = {
        name: keyed(read_jsonl(root / f"{name}-seen-test.evaluation.jsonl"))
        for name in order
    }
    ids = sorted(rows[order[0]])
    result: list[Row] = []
    for example_id in ids:
        reference = rows[order[0]][example_id]
        baseline = float(reference["buggy_pass_rate"])
        invoked: list[tuple[str, Row]] = []
        selected: Row | None = None
        source = "current-fallback"
        for name in order:
            candidate = rows[name][example_id]
            invoked.append((name, candidate))
            if bool(candidate["repaired"]):
                selected = candidate
                source = name
                break
        if selected is None:
            best = max(
                [baseline]
                + [float(candidate["fixed_pass_rate"]) for _name, candidate in invoked]
            )
            if best > baseline:
                source, selected = min(
                    [
                        (name, candidate)
                        for name, candidate in invoked
                        if float(candidate["fixed_pass_rate"]) == best
                    ],
                    key=lambda item: (
                        int(item[1]["tree_edit_distance"])
                        if item[1].get("tree_edit_distance") is not None
                        else 10**9
                    ),
                )
        fixed_pass_rate = baseline if selected is None else float(selected["fixed_pass_rate"])
        result.append(
            {
                "example_id": example_id,
                "problem_id": reference["problem_id"],
                "user_id": reference["user_id"],
                "buggy_pass_rate": baseline,
                "fixed_pass_rate": fixed_pass_rate,
                "repaired": selected is not None and bool(selected["repaired"]),
                "improved": fixed_pass_rate > baseline,
                "selected_source": source,
                "ted_buggy_fixed": (
                    None if selected is None else selected.get("ted_buggy_fixed")
                ),
                "ted_fixed_oracle": (
                    None if selected is None else selected.get("ted_fixed_oracle")
                ),
            }
        )
    return result


def verify_selector(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    counts: dict[str, int] = defaultdict(int)
    gains: list[float] = []
    for row in rows:
        baseline = float(row["buggy_pass_rate"])
        selected = float(row["fixed_pass_rate"])
        gains.append(selected - baseline)
        if selected + 1e-12 < baseline:
            counts["pass_rate_regressions"] += 1
        if bool(row["repaired"]) != (selected == 1.0 and row["selected_source"] != "current-fallback"):
            counts["repair_flag_mismatches"] += 1
        early = row.get("early_stop_stage")
        if early is not None and selected != 1.0:
            counts["invalid_early_stops"] += 1
        candidates = row.get("candidate_outcomes", [])
        if not any(item.get("source") == "current-fallback" for item in candidates):
            counts["missing_fallback"] += 1
    return {
        "examples": len(rows),
        "violations": dict(counts),
        "minimum_selected_minus_baseline_pass_rate": min(gains),
        "fallback_certificate_holds": not counts,
    }


def verify_selected_rows(rows: list[Row]) -> dict[str, Any]:
    gains = [float(row["fixed_pass_rate"]) - float(row["buggy_pass_rate"]) for row in rows]
    regressions = sum(gain < -1e-12 for gain in gains)
    return {
        "examples": len(rows),
        "violations": {"pass_rate_regressions": regressions} if regressions else {},
        "minimum_selected_minus_baseline_pass_rate": min(gains),
        "fallback_certificate_holds": regressions == 0,
    }


def existing(path: Path) -> bool:
    return path.is_file()


def complete_eval(path: Path, expected: int) -> bool:
    if not path.is_file() or not path.with_suffix(".summary.json").is_file():
        return False
    with path.open(encoding="utf-8") as source:
        return sum(1 for line in source if line.strip()) == expected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    root = args.eval_root.expanduser().resolve()

    comparisons: dict[str, dict[str, Any]] = {
        "seen_zpdpatch_vs_zero": {
            "left": root / "zpdpatch-seen-test.evaluation.jsonl",
            "right": root / "zero-shot-seen-test.evaluation.jsonl",
        },
        "seen_zpdpatch_vs_lsgen": {
            "left": root / "zpdpatch-seen-test.evaluation.jsonl",
            "right": root / "lsgen-seen-test.evaluation.jsonl",
        },
        "unseen_zpdpatch_vs_zero": {
            "left": root / "zpdpatch-unseen-test.evaluation.jsonl",
            "right": root / "zero-shot-unseen-test.evaluation.jsonl",
        },
        "rq3_answer_vs_progress": {
            "left": root / "answer-seen-test.evaluation.jsonl",
            "right": root / "progress-seen-test.evaluation.jsonl",
        },
        "rq3_answer_vs_strict": {
            "left": root / "answer-seen-test.evaluation.jsonl",
            "right": root / "strict-seen-test.evaluation.jsonl",
        },
        "rq4_sequential_vs_progress": {
            "left": root / "zpdpatch-seen-test.evaluation.jsonl",
            "right": root / "progress-seen-test.evaluation.jsonl",
        },
        "rq4_sequential_vs_strict": {
            "left": root / "zpdpatch-seen-test.evaluation.jsonl",
            "right": root / "strict-seen-test.evaluation.jsonl",
        },
        "rq4_sequential_vs_answer": {
            "left": root / "zpdpatch-seen-test.evaluation.jsonl",
            "right": root / "answer-seen-test.evaluation.jsonl",
        },
    }
    for split in ("seen", "unseen"):
        for adapter in ("strict", "progress"):
            base = root / f"rq2-{split}-test-{adapter}-comparison"
            comparisons[f"rq2_{split}_{adapter}_full_vs_current"] = {
                "left": base / "full-eval.jsonl",
                "right": base / "current-eval.jsonl",
            }

    comparison_results = {
        name: paired_suite(
            paths["left"],
            paths["right"],
            samples=args.bootstrap_samples,
            seed=args.seed + index * 10,
        )
        for index, (name, paths) in enumerate(comparisons.items())
        if existing(paths["left"]) and existing(paths["right"])
    }
    no_feedback = replay_selected_rows(root, ("progress", "strict", "answer"))
    comparison_results["seen_no_feedback_vs_zero"] = paired_suite_rows(
        no_feedback,
        read_jsonl(root / "zero-shot-seen-test.evaluation.jsonl"),
        left_label="replayed:progress-strict-answer",
        right_label=str(root / "zero-shot-seen-test.evaluation.jsonl"),
        samples=args.bootstrap_samples,
        seed=args.seed + 1000,
    )
    comparison_results["seen_no_feedback_vs_dynamic_feedback"] = paired_suite_rows(
        no_feedback,
        read_jsonl(root / "zpdpatch-seen-test.evaluation.jsonl"),
        left_label="replayed:progress-strict-answer",
        right_label=str(root / "zpdpatch-seen-test.evaluation.jsonl"),
        samples=args.bootstrap_samples,
        seed=args.seed + 1010,
    )
    comparison_results["seen_no_feedback_vs_lsgen"] = paired_suite_rows(
        no_feedback,
        read_jsonl(root / "lsgen-seen-test.evaluation.jsonl"),
        left_label="replayed:progress-strict-answer",
        right_label=str(root / "lsgen-seen-test.evaluation.jsonl"),
        samples=args.bootstrap_samples,
        seed=args.seed + 1015,
    )
    for offset, adapter in enumerate(("progress", "strict", "answer"), start=1):
        comparison_results[f"seen_no_feedback_vs_{adapter}"] = paired_suite_rows(
            no_feedback,
            read_jsonl(root / f"{adapter}-seen-test.evaluation.jsonl"),
            left_label="replayed:progress-strict-answer",
            right_label=str(root / f"{adapter}-seen-test.evaluation.jsonl"),
            samples=args.bootstrap_samples,
            seed=args.seed + 1010 + offset * 10,
        )

    ablation_root = root / "acceptance-ablations"
    answer_seen = ablation_root / "answer-repeated-seen-test.evaluation.jsonl"
    if complete_eval(answer_seen, 997):
        comparison_results["seen_no_feedback_vs_answer_repeated"] = paired_suite_rows(
            no_feedback,
            read_jsonl(answer_seen),
            left_label="replayed:progress-strict-answer",
            right_label=str(answer_seen),
            samples=args.bootstrap_samples,
            seed=args.seed + 1100,
        )
    unseen_no_feedback = ablation_root / "zpdpatch-unseen-test-no-stage-feedback.evaluation.jsonl"
    if complete_eval(unseen_no_feedback, 250):
        comparison_results["unseen_no_feedback_vs_zero"] = paired_suite(
            unseen_no_feedback,
            root / "zero-shot-unseen-test.evaluation.jsonl",
            samples=args.bootstrap_samples,
            seed=args.seed + 1110,
        )
        comparison_results["unseen_no_feedback_vs_dynamic_feedback"] = paired_suite(
            unseen_no_feedback,
            root / "zpdpatch-unseen-test.evaluation.jsonl",
            samples=args.bootstrap_samples,
            seed=args.seed + 1120,
        )
    answer_unseen = ablation_root / "answer-repeated-unseen-test.evaluation.jsonl"
    if complete_eval(unseen_no_feedback, 250) and complete_eval(answer_unseen, 250):
        comparison_results["unseen_no_feedback_vs_answer_repeated"] = paired_suite(
            unseen_no_feedback,
            answer_unseen,
            samples=args.bootstrap_samples,
            seed=args.seed + 1130,
        )
    output = {
        "schema_version": 1,
        "bootstrap": {
            "samples": args.bootstrap_samples,
            "seed": args.seed,
            "cluster": "problem_id",
        },
        "comparisons": comparison_results,
        "portfolio_order": replay_orders(root),
        "selector_certificate": {
            "seen": verify_selected_rows(no_feedback),
            "unseen": verify_selector(
                unseen_no_feedback
                if complete_eval(unseen_no_feedback, 250)
                else root / "zpdpatch-unseen-test.evaluation.jsonl"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
