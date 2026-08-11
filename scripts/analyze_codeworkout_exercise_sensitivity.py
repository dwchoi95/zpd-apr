#!/usr/bin/env python3
"""Report per-exercise and leave-one-exercise-out mixed-vs-Answer effects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from analyze_fse2027_robustness import paired_suite_rows, read_jsonl
except ImportError:  # pragma: no cover
    from scripts.analyze_fse2027_robustness import paired_suite_rows, read_jsonl


def analyze(mixed: list[dict], answer: list[dict], *, samples: int = 10_000, seed: int = 2027) -> dict:
    mixed_by_id = {str(row["example_id"]): row for row in mixed}
    answer_by_id = {str(row["example_id"]): row for row in answer}
    if set(mixed_by_id) != set(answer_by_id):
        raise ValueError("mixed and Answer rows must cover identical examples")
    exercises = sorted({str(row["problem_id"]) for row in mixed})
    per_exercise = []
    leave_one_out = []
    for offset, exercise in enumerate(exercises):
        ids = [example_id for example_id, row in mixed_by_id.items() if str(row["problem_id"]) == exercise]
        mixed_rr = sum(bool(mixed_by_id[i]["repaired"]) for i in ids) / len(ids)
        answer_rr = sum(bool(answer_by_id[i]["repaired"]) for i in ids) / len(ids)
        per_exercise.append({
            "exercise": exercise,
            "examples": len(ids),
            "mixed_rr": mixed_rr,
            "answer_rr": answer_rr,
            "mixed_minus_answer_rr": mixed_rr - answer_rr,
            "mixed_only_repairs": sum(bool(mixed_by_id[i]["repaired"]) and not bool(answer_by_id[i]["repaired"]) for i in ids),
            "answer_only_repairs": sum(bool(answer_by_id[i]["repaired"]) and not bool(mixed_by_id[i]["repaired"]) for i in ids),
        })
        kept_mixed = [row for row in mixed if str(row["problem_id"]) != exercise]
        kept_answer = [row for row in answer if str(row["problem_id"]) != exercise]
        if not kept_mixed:
            continue
        contrast = paired_suite_rows(
            kept_mixed, kept_answer, left_label="Mixed-target-9Choose3",
            right_label="Answer-9Choose3", samples=samples, seed=seed + offset,
        )
        rr = next(row for row in contrast["paired"] if row["metric"] == "rr")
        leave_one_out.append({
            "excluded_exercise": exercise,
            "examples": len(kept_mixed),
            "mixed_minus_answer_rr": rr["left_minus_right_instance_weighted"],
            "exercise_cluster_bootstrap_95ci": rr["cluster_bootstrap_95ci"],
            "mixed_only_repairs": contrast["rr_contingency"]["left_only"],
            "answer_only_repairs": contrast["rr_contingency"]["right_only"],
            "exact_mcnemar_two_sided_p": contrast["exact_mcnemar_two_sided_p"],
        })
    return {
        "dataset": "CodeWorkout exercise-held-out Java test",
        "test_exercises": len(exercises),
        "per_exercise": per_exercise,
        "leave_one_exercise_out": leave_one_out,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mixed", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10_000)
    args = parser.parse_args()
    result = analyze(read_jsonl(args.mixed), read_jsonl(args.answer9), samples=args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
