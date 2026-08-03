from __future__ import annotations

import json
import math
import random
import statistics
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


def compare_rq1(
    evaluations: dict[str, Path],
    output_path: Path,
) -> dict[str, Any]:
    rows_by_method = {
        method: {
            str(row["example_id"]): row for row in _iter_jsonl(path)
        }
        for method, path in evaluations.items()
    }
    if not rows_by_method:
        raise ValueError("At least one evaluation must be provided.")

    expected_ids = next(iter(rows_by_method.values())).keys()
    for method, rows in rows_by_method.items():
        if rows.keys() != expected_ids:
            raise ValueError(f"Evaluation IDs do not match for method {method}.")

    methods = {
        method: _summarize(rows.values()) for method, rows in rows_by_method.items()
    }
    pairwise = []
    for left, right in combinations(rows_by_method, 2):
        left_rows = rows_by_method[left]
        right_rows = rows_by_method[right]
        left_only = sum(
            bool(left_rows[item_id]["repaired"])
            and not bool(right_rows[item_id]["repaired"])
            for item_id in expected_ids
        )
        right_only = sum(
            not bool(left_rows[item_id]["repaired"])
            and bool(right_rows[item_id]["repaired"])
            for item_id in expected_ids
        )
        both = sum(
            bool(left_rows[item_id]["repaired"])
            and bool(right_rows[item_id]["repaired"])
            for item_id in expected_ids
        )
        neither = len(left_rows) - left_only - right_only - both
        pairwise.append(
            {
                "left": left,
                "right": right,
                "left_only_repaired": left_only,
                "right_only_repaired": right_only,
                "both_repaired": both,
                "neither_repaired": neither,
                "mcnemar_exact_p": _mcnemar_exact(left_only, right_only),
                "paired_ted_on_joint_repairs": {
                    "buggy_fixed": _paired_ted(
                        left_rows,
                        right_rows,
                        expected_ids,
                        metric="ted_buggy_fixed",
                    ),
                    "fixed_oracle": _paired_ted(
                        left_rows,
                        right_rows,
                        expected_ids,
                        metric="ted_fixed_oracle",
                    ),
                },
            }
        )

    result = {
        "methods": methods,
        "pairwise_repair_rate": pairwise,
        "output_path": str(output_path.expanduser().resolve()),
    }
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def _summarize(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(rows)
    repaired = sum(bool(row["repaired"]) for row in rows)
    improved = sum(bool(row["improved"]) for row in rows)
    repaired_buggy_fixed_distances = [
        float(row["ted_buggy_fixed"])
        for row in rows
        if row.get("repaired") and row.get("ted_buggy_fixed") is not None
    ]
    repaired_fixed_oracle_distances = [
        float(row["ted_fixed_oracle"])
        for row in rows
        if row.get("repaired") and row.get("ted_fixed_oracle") is not None
    ]
    rr_low, rr_high = _wilson_interval(repaired, len(rows))
    ir_low, ir_high = _wilson_interval(improved, len(rows))
    generation_times = [
        float(row.get("generation_time_sec", 0.0)) for row in rows
    ]
    execution_times = [
        float(row.get("execution_time_sec", 0.0)) for row in rows
    ]
    problem_times = _problem_level_times(rows)
    return {
        "examples": len(rows),
        "repaired": repaired,
        "improved": improved,
        "repair_rate": repaired / len(rows) if rows else 0.0,
        "repair_rate_wilson_95ci": [rr_low, rr_high],
        "improvement_rate": improved / len(rows) if rows else 0.0,
        "improvement_rate_wilson_95ci": [ir_low, ir_high],
        "average_time_taken_sec": (
            sum(item["elapsed_sec"] for item in problem_times)
            / sum(item["buggy_count"] for item in problem_times)
            if problem_times
            else 0.0
        ),
        "mean_generation_time_sec": (
            sum(generation_times) / len(rows) if rows else 0.0
        ),
        "mean_execution_time_sec": (
            sum(execution_times) / len(rows) if rows else 0.0
        ),
        "mean_ted_buggy_fixed_on_repaired": _mean(
            repaired_buggy_fixed_distances
        ),
        "median_ted_buggy_fixed_on_repaired": _median(
            repaired_buggy_fixed_distances
        ),
        "mean_ted_fixed_oracle_on_repaired": _mean(
            repaired_fixed_oracle_distances
        ),
        "median_ted_fixed_oracle_on_repaired": _median(
            repaired_fixed_oracle_distances
        ),
        "parseable_repaired_for_buggy_fixed_ted": len(
            repaired_buggy_fixed_distances
        ),
        "parseable_repaired_for_fixed_oracle_ted": len(
            repaired_fixed_oracle_distances
        ),
        "mean_fixed_pass_rate": (
            sum(float(row.get("fixed_pass_rate", 0.0)) for row in rows) / len(rows)
            if rows
            else 0.0
        ),
    }


def _problem_level_times(
    rows: list[dict[str, Any]],
) -> list[dict[str, float | int | str]]:
    timings: dict[str, dict[str, float | int | str]] = {}
    for row in rows:
        problem_id = str(row.get("problem_id", ""))
        elapsed = row.get("problem_repair_time_sec")
        buggy_count = row.get("problem_buggy_count")
        if elapsed is None or buggy_count is None:
            continue
        timing = {
            "problem_id": problem_id,
            "elapsed_sec": float(elapsed),
            "buggy_count": int(buggy_count),
        }
        previous = timings.get(problem_id)
        if previous is not None and previous != timing:
            raise ValueError(f"Inconsistent problem timing for {problem_id}")
        timings[problem_id] = timing
    if timings:
        return list(timings.values())

    elapsed = sum(
        float(
            row.get(
                "online_time_sec",
                float(row.get("generation_time_sec", 0.0))
                + float(row.get("execution_time_sec", 0.0)),
            )
        )
        for row in rows
    )
    return [
        {
            "problem_id": "__legacy_aggregate__",
            "elapsed_sec": elapsed,
            "buggy_count": len(rows),
        }
    ] if rows else []


def _wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    z = 1.959963984540054
    ratio = successes / total
    denominator = 1 + z * z / total
    center = (ratio + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(ratio * (1 - ratio) / total + z * z / (4 * total * total))
        / denominator
    )
    return center - margin, center + margin


def _mcnemar_exact(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(left_only, right_only) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def _paired_ted(
    left_rows: dict[str, dict[str, Any]],
    right_rows: dict[str, dict[str, Any]],
    example_ids: Iterable[str],
    *,
    metric: str,
) -> dict[str, Any]:
    pairs = [
        (
            float(left_rows[example_id][metric]),
            float(right_rows[example_id][metric]),
        )
        for example_id in example_ids
        if left_rows[example_id].get("repaired")
        and right_rows[example_id].get("repaired")
        and left_rows[example_id].get(metric) is not None
        and right_rows[example_id].get(metric) is not None
    ]
    if not pairs:
        return {
            "examples": 0,
            "left_mean": None,
            "right_mean": None,
            "mean_difference_left_minus_right": None,
            "bootstrap_95ci": [None, None],
            "left_smaller": 0,
            "equal": 0,
            "right_smaller": 0,
        }
    left = [pair[0] for pair in pairs]
    right = [pair[1] for pair in pairs]
    differences = [left_value - right_value for left_value, right_value in pairs]
    return {
        "examples": len(pairs),
        "left_mean": _mean(left),
        "left_median": _median(left),
        "right_mean": _mean(right),
        "right_median": _median(right),
        "mean_difference_left_minus_right": _mean(differences),
        "bootstrap_95ci": list(_bootstrap_mean_ci(differences)),
        "left_smaller": sum(value < 0 for value in differences),
        "equal": sum(value == 0 for value in differences),
        "right_smaller": sum(value > 0 for value in differences),
    }


def _bootstrap_mean_ci(
    values: list[float],
    *,
    samples: int = 10_000,
    seed: int = 2027,
) -> tuple[float, float]:
    generator = random.Random(seed)
    count = len(values)
    means = sorted(
        sum(values[generator.randrange(count)] for _ in range(count)) / count
        for _ in range(samples)
    )
    return means[int(samples * 0.025)], means[int(samples * 0.975)]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
