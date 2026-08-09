#!/usr/bin/env python3
"""Compare CodeWorkout ZPDPatch with selection-matched Answer-9Choose3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method
from analyze_codeworkout_portfolios import clustered_interval
from analyze_fse2027_scale_replication import selection_audit


def resolve_mixed_selection_path(
    answer_selection_path: Path, explicit_path: Path | None
) -> Path:
    return explicit_path or answer_selection_path.with_name(
        "fse2027-codeworkout-selection.json"
    )


def analyze(
    zpdpatch: list[dict],
    answer9: list[dict],
    mixed_selection: dict,
    selection: dict,
    *,
    samples: int,
    seed: int,
) -> dict:
    comparison = paired_suite_rows(
        zpdpatch,
        answer9,
        left_label="ZPDPatch",
        right_label="Answer-9Choose3",
        samples=samples,
        seed=seed,
    )
    comparison["student_cluster_rr_95ci"] = clustered_interval(
        zpdpatch, answer9, "user_id", seed=seed
    )
    return {
        "dataset": "CodeWorkout student-held-out Java test",
        "selection_partition": "CodeWorkout student-held-out validation",
        "test_outcomes_used_for_selection": False,
        "selection_fairness_audit": selection_audit(mixed_selection, selection),
        "answer_candidate_checkpoints": selection["candidate_checkpoint_count"],
        "answer_feasible_portfolios": selection["feasible_portfolios"],
        "answer_selected_members": selection["selected_unrestricted"]["members"],
        "zpdpatch": summarize_method(zpdpatch),
        "answer_9choose3": summarize_method(answer9),
        "zpdpatch_minus_answer_9choose3": comparison,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zpdpatch", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--mixed-selection", type=Path)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    zpdpatch = read_jsonl(args.zpdpatch)
    answer9 = read_jsonl(args.answer9)
    mixed_selection_path = resolve_mixed_selection_path(
        args.selection, args.mixed_selection
    )
    mixed_selection = json.loads(mixed_selection_path.read_text(encoding="utf-8"))
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    result = analyze(
        zpdpatch,
        answer9,
        mixed_selection,
        selection,
        samples=args.samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
