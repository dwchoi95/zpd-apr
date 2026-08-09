#!/usr/bin/env python3
"""Reject final evidence whose mixed and Answer selection opportunities differ."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CANDIDATES = 9
EXPECTED_PORTFOLIOS = 84


def verify_external_split(path: Path) -> None:
    summary = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "problems_by_split": {"train": 10, "valid": 3, "test": 4},
        "trajectories_by_split": {"train": 605, "valid": 216, "test": 304},
        "students_by_split": {"train": 213, "valid": 150, "test": 161},
        "problem_overlap_counts": {
            "train-valid": 0,
            "train-test": 0,
            "valid-test": 0,
        },
        "student_overlap_counts": {
            "train-valid": 147,
            "train-test": 151,
            "valid-test": 121,
        },
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ValueError(
                f"{path}: {key}={summary.get(key)!r}, expected {value!r}"
            )


def verify(path: Path) -> None:
    result = json.loads(path.read_text(encoding="utf-8"))
    audit = result.get("selection_fairness_audit")
    if not isinstance(audit, dict):
        raise ValueError(f"{path}: missing selection_fairness_audit")
    expected = {
        "mixed_candidate_checkpoint_count": EXPECTED_CANDIDATES,
        "answer_candidate_checkpoint_count": EXPECTED_CANDIDATES,
        "mixed_feasible_size_three_portfolios": EXPECTED_PORTFOLIOS,
        "answer_feasible_size_three_portfolios": EXPECTED_PORTFOLIOS,
        "candidate_pool_sizes_matched": True,
        "portfolio_search_spaces_matched": True,
    }
    for key, value in expected.items():
        if audit.get(key) != value:
            raise ValueError(
                f"{path}: {key}={audit.get(key)!r}, expected {value!r}"
            )


def verify_mechanism_ladder(path: Path) -> None:
    result = json.loads(path.read_text(encoding="utf-8"))
    expected_members = ["Answer2027", "Answer2028", "Answer2029"]
    if result.get("answer_3seed_members") != expected_members:
        raise ValueError(f"{path}: missing fixed Answer-3Seed members")
    nodes = result.get("splits")
    if isinstance(nodes, dict):
        if set(nodes) != {"seen", "unseen"}:
            raise ValueError(f"{path}: scale ladder must contain Seen and Unseen")
        labeled = list(nodes.items())
    else:
        labeled = [("test", result)]
    for label, node in labeled:
        summaries = {}
        for method in (
            "mixed_target_9choose3", "answer_9choose3", "answer_3seed", "answer_1"
        ):
            summary = node.get(method)
            if not isinstance(summary, dict):
                raise ValueError(f"{path}: {label} missing {method}")
            if not isinstance(summary.get("examples"), int) or summary["examples"] <= 0:
                raise ValueError(f"{path}: {label} {method} missing example count")
            summaries[method] = summary
            for metric_name in ("pr", "rr", "ir"):
                value = summary.get(metric_name)
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        f"{path}: {label} {method} missing numeric {metric_name}"
                    )
        if len({summary["examples"] for summary in summaries.values()}) != 1:
            raise ValueError(f"{path}: {label} ladder methods cover different examples")
        for contrast in (
            "answer_3seed_minus_answer_1",
            "answer_9choose3_minus_answer_3seed",
            "mixed_minus_answer",
        ):
            paired = node.get(contrast, {}).get("paired")
            by_metric = {
                row.get("metric"): row for row in paired or []
                if isinstance(row, dict)
            }
            for metric_name in ("pr", "rr", "ir"):
                row = by_metric.get(metric_name)
                if (
                    row is None
                    or row.get("examples") != next(iter(summaries.values()))["examples"]
                    or len(row.get("cluster_bootstrap_95ci", [])) != 2
                ):
                    raise ValueError(
                        f"{path}: {label} missing aligned clustered {metric_name.upper()} {contrast}"
                    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", action="append", type=Path, required=True)
    parser.add_argument("--ladder-analysis", action="append", type=Path, default=[])
    parser.add_argument("--external-split-summary", type=Path, required=True)
    args = parser.parse_args()
    for path in args.analysis:
        verify(path)
    for path in args.ladder_analysis:
        verify(path)
        verify_mechanism_ladder(path)
    verify_external_split(args.external_split_summary)
    print(
        json.dumps(
            {
                "verified_analyses": len(args.analysis) + len(args.ladder_analysis),
                "verified_mechanism_ladders": len(args.ladder_analysis),
                "candidate_checkpoints_per_pool": EXPECTED_CANDIDATES,
                "feasible_size_three_portfolios_per_pool": EXPECTED_PORTFOLIOS,
                "external_split_summary_verified": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
