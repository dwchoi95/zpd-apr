#!/usr/bin/env python3
"""Compare CodeWorkout ZPDPatch with selection-matched Answer-9Choose3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zpdpatch", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    zpdpatch = read_jsonl(args.zpdpatch)
    answer9 = read_jsonl(args.answer9)
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    result = {
        "dataset": "CodeWorkout student-held-out Java test",
        "selection_partition": "CodeWorkout student-held-out validation",
        "test_outcomes_used_for_selection": False,
        "answer_candidate_checkpoints": selection["candidate_checkpoint_count"],
        "answer_feasible_portfolios": selection["feasible_portfolios"],
        "answer_selected_members": selection["selected_unrestricted"]["members"],
        "zpdpatch": summarize_method(zpdpatch),
        "answer_9choose3": summarize_method(answer9),
        "zpdpatch_minus_answer_9choose3": paired_suite_rows(
            zpdpatch,
            answer9,
            left_label="ZPDPatch",
            right_label="Answer-9Choose3",
            samples=args.samples,
            seed=args.seed,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
