#!/usr/bin/env python3
"""Report normal-approximation MDEs from frozen clustered intervals."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CONTRASTS = {
    "primary_crossfit_seen_m9_minus_a9": (
        "CrossFitMixedMinusAnswerNineSeen",
        "CrossFitMixedMinusAnswerNineSeenCI",
    ),
    "secondary_budget_seen_m9_minus_a9": (
        "BudgetMixedMinusAnswerNineSeen",
        "BudgetMixedMinusAnswerNineSeenCI",
    ),
    "secondary_budget_unseen_m9_minus_a9": (
        "BudgetMixedMinusAnswerNineUnseen",
        "BudgetMixedMinusAnswerNineUnseenCI",
    ),
    "scale_1_5b_seen_m9_minus_a9": (
        "ScaleMixedMinusAnswerNineSeen",
        "ScaleMixedMinusAnswerNineSeenCI",
    ),
    "codeworkout_student_m9_minus_a9": (
        "CodeWorkoutStudentMixedMinusAnswerNine",
        "CodeWorkoutStudentMixedMinusAnswerNineStudentCI",
    ),
    "checkpoint_diversity_seen": (
        "CheckpointStochasticMinusSameCheckpointSeen",
        "CheckpointStochasticMinusSameCheckpointSeenCI",
    ),
    "checkpoint_diversity_unseen": (
        "CheckpointStochasticMinusSameCheckpointUnseen",
        "CheckpointStochasticMinusSameCheckpointUnseenCI",
    ),
}


def macros(path: Path) -> dict[str, str]:
    pattern = re.compile(r"\\newcommand\{\\([^}]+)\}\{([^}]*)\}")
    return dict(pattern.findall(path.read_text(encoding="utf-8")))


def interval(value: str) -> tuple[float, float]:
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", value.replace("--", "-"))
    if len(numbers) != 2:
        raise ValueError(f"cannot parse interval: {value}")
    return float(numbers[0]), float(numbers[1])


def analyze(path: Path) -> dict[str, Any]:
    values = macros(path)
    result: dict[str, Any] = {}
    for label, (effect_macro, ci_macro) in CONTRASTS.items():
        effect = float(values[effect_macro])
        lower, upper = interval(values[ci_macro])
        standard_error = (upper - lower) / (2 * 1.96)
        mde = (1.96 + 0.8416212335729143) * standard_error
        result[label] = {
            "effect_percentage_points": effect,
            "cluster_bootstrap_95ci_percentage_points": [lower, upper],
            "ci_width_derived_standard_error_percentage_points": standard_error,
            "two_sided_alpha_0_05_power_0_80_mde_percentage_points": mde,
            "absolute_effect_over_mde": abs(effect) / mde,
        }
    return {
        "method": "MDE=(z_0.975+z_0.80)*SE, with SE estimated from the width of the frozen clustered 95% interval.",
        "interpretation": "This is an approximate design-sensitivity diagnostic, not evidence that a null effect is exactly zero.",
        "contrasts": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bridge", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = analyze(args.bridge)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
