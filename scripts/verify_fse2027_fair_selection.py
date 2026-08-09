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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", action="append", type=Path, required=True)
    parser.add_argument("--external-split-summary", type=Path, required=True)
    args = parser.parse_args()
    for path in args.analysis:
        verify(path)
    verify_external_split(args.external_split_summary)
    print(
        json.dumps(
            {
                "verified_analyses": len(args.analysis),
                "candidate_checkpoints_per_pool": EXPECTED_CANDIDATES,
                "feasible_size_three_portfolios_per_pool": EXPECTED_PORTFOLIOS,
                "external_split_summary_verified": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
