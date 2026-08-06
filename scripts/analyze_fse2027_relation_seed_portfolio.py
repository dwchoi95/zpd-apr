#!/usr/bin/env python3
"""Compare the validation-selected relation/seed portfolio with both controls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analyze_fse2027_robustness import (
    paired_suite_rows,
    read_jsonl,
    replay_selected_rows,
)


def metric(report: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in report["paired"] if item["metric"] == name)


def conclusion(report: dict[str, Any]) -> dict[str, Any]:
    rr = metric(report, "rr")
    lower, upper = rr["cluster_bootstrap_95ci"]
    return {
        "left_minus_right_rr": rr["left_minus_right_instance_weighted"],
        "problem_cluster_95ci": [lower, upper],
        "exact_mcnemar_two_sided_p": report["exact_mcnemar_two_sided_p"],
        "left_significantly_better": lower > 0.0,
        "right_significantly_better": upper < 0.0,
    }


def build_report(eval_root: Path, *, samples: int, seed: int) -> dict[str, Any]:
    original = replay_selected_rows(eval_root, ("progress", "strict", "answer"))
    answer3_path = (
        eval_root / "answer-seed-control" / "answer-seeds-seen-test.evaluation.jsonl"
    )
    relation_path = (
        eval_root / "relation-seed-control" / "relation-seed-seen-test.evaluation.jsonl"
    )
    relation = read_jsonl(relation_path)
    comparisons = {
        "relation_seed_vs_answer_3seed": paired_suite_rows(
            relation,
            read_jsonl(answer3_path),
            left_label=str(relation_path),
            right_label=str(answer3_path),
            samples=samples,
            seed=seed,
        ),
        "relation_seed_vs_original_zpdpatch": paired_suite_rows(
            relation,
            original,
            left_label=str(relation_path),
            right_label="replayed:progress-strict-answer",
            samples=samples,
            seed=seed + 100,
        ),
    }
    return {
        "schema_version": 1,
        "portfolio": {
            "policies": ["Progress2027", "Strict2028", "Answer2029"],
            "seed_assignment_rule": "minimum validation loss per relation",
            "selection_data": "training validation split only",
            "test_outcome_used_for_assignment": False,
            "stage_feedback": False,
            "maximum_candidates": 3,
            "selection": "first-AC-else-pass-rate-then-TED-with-current-fallback",
        },
        "bootstrap": {"samples": samples, "seed": seed, "cluster": "problem_id"},
        "comparisons": comparisons,
        "primary_conclusion": conclusion(
            comparisons["relation_seed_vs_answer_3seed"]
        ),
        "secondary_conclusion": conclusion(
            comparisons["relation_seed_vs_original_zpdpatch"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    report = build_report(
        args.eval_root.expanduser().resolve(),
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["primary_conclusion"], sort_keys=True))


if __name__ == "__main__":
    main()
