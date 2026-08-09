#!/usr/bin/env python3
"""Reject final evidence whose mixed and Answer selection opportunities differ."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CANDIDATES = 9
EXPECTED_PORTFOLIOS = 84
EXPECTED_CROSSFIT_FOLDS = 5
EXPECTED_CROSSFIT_VALIDATION_EXAMPLES = 461
EXPECTED_CROSSFIT_TEST_EXAMPLES = 997
EXPECTED_CROSSFIT_TEST_PROBLEMS = 328


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


def verify_problem_crossfit(path: Path) -> None:
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("folds") != EXPECTED_CROSSFIT_FOLDS:
        raise ValueError(f"{path}: cross-fit must use {EXPECTED_CROSSFIT_FOLDS} folds")
    if result.get("test_outcomes_used_for_selection") is not False:
        raise ValueError(f"{path}: test outcomes must not enter cross-fit selection")
    cohort = result.get("cohort_audit")
    expected_cohort = {
        "validation_examples": EXPECTED_CROSSFIT_VALIDATION_EXAMPLES,
        "test_examples": EXPECTED_CROSSFIT_TEST_EXAMPLES,
        "unique_examples_per_member": True,
        "mixed_answer_validation_examples_identical": True,
        "mixed_answer_test_examples_identical": True,
    }
    if not isinstance(cohort, dict):
        raise ValueError(f"{path}: missing cross-fit cohort audit")
    for key, value in expected_cohort.items():
        if cohort.get(key) != value:
            raise ValueError(f"{path}: cross-fit {key}={cohort.get(key)!r}, expected {value!r}")
    folds = result.get("fold_audit")
    if not isinstance(folds, list) or len(folds) != EXPECTED_CROSSFIT_FOLDS:
        raise ValueError(f"{path}: incomplete cross-fit fold audit")
    if {row.get("fold") for row in folds} != set(range(EXPECTED_CROSSFIT_FOLDS)):
        raise ValueError(f"{path}: cross-fit fold identifiers are incomplete")
    if any(
        row.get("validation_test_problem_overlap") != 0
        or not isinstance(row.get("test_problems"), int)
        or row["test_problems"] <= 0
        or not isinstance(row.get("validation_problems"), int)
        or row["validation_problems"] <= 0
        for row in folds
    ):
        raise ValueError(f"{path}: invalid or overlapping cross-fit fold")
    if sum(row["test_problems"] for row in folds) != EXPECTED_CROSSFIT_TEST_PROBLEMS:
        raise ValueError(f"{path}: cross-fit test problems do not sum to {EXPECTED_CROSSFIT_TEST_PROBLEMS}")
    for method in ("mixed", "answer"):
        summary = result.get(method, {})
        if (
            summary.get("examples") != EXPECTED_CROSSFIT_TEST_EXAMPLES
            or summary.get("problems") != EXPECTED_CROSSFIT_TEST_PROBLEMS
        ):
            raise ValueError(f"{path}: cross-fit {method} summary has wrong cohort")
    paired = result.get("mixed_minus_answer", {}).get("paired")
    by_metric = {row.get("metric"): row for row in paired or [] if isinstance(row, dict)}
    for metric_name in ("pr", "rr", "ir"):
        row = by_metric.get(metric_name)
        if row is None or row.get("examples") != EXPECTED_CROSSFIT_TEST_EXAMPLES:
            raise ValueError(f"{path}: cross-fit missing aligned {metric_name.upper()} contrast")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", action="append", type=Path, required=True)
    parser.add_argument("--ladder-analysis", action="append", type=Path, default=[])
    parser.add_argument("--problem-crossfit", type=Path, required=True)
    parser.add_argument("--external-split-summary", type=Path, required=True)
    args = parser.parse_args()
    for path in args.analysis:
        verify(path)
    for path in args.ladder_analysis:
        verify(path)
        verify_mechanism_ladder(path)
    verify_problem_crossfit(args.problem_crossfit)
    verify_external_split(args.external_split_summary)
    print(
        json.dumps(
            {
                "verified_analyses": len(args.analysis) + len(args.ladder_analysis),
                "verified_mechanism_ladders": len(args.ladder_analysis),
                "problem_crossfit_verified": True,
                "candidate_checkpoints_per_pool": EXPECTED_CANDIDATES,
                "feasible_size_three_portfolios_per_pool": EXPECTED_PORTFOLIOS,
                "external_split_summary_verified": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
