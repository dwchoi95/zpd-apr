#!/usr/bin/env python3
"""Reject final evidence whose mixed and Answer selection opportunities differ."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_CANDIDATES = 9
EXPECTED_PORTFOLIOS = 84


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
    args = parser.parse_args()
    for path in args.analysis:
        verify(path)
    print(
        json.dumps(
            {
                "verified_analyses": len(args.analysis),
                "candidate_checkpoints_per_pool": EXPECTED_CANDIDATES,
                "feasible_size_three_portfolios_per_pool": EXPECTED_PORTFOLIOS,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
