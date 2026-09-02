#!/usr/bin/env python3
"""Render the Seen mechanism ladder as a compact vector forest plot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def paired_rr(contrast: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in contrast["paired"] if row["metric"] == "rr")


def named_rr(contrast: dict[str, Any]) -> dict[str, Any]:
    return next(row for row in contrast["metrics"] if row["metric"] == "rr")


def forest_rows(
    decomposition: dict[str, Any],
    answer9: dict[str, Any],
    crossfit: dict[str, Any],
) -> list[tuple[str, float, float, float]]:
    same = decomposition["splits"]["seen"]
    decoding = named_rr(same["stochastic_one_minus_greedy_one_expected"])
    breadth = named_rr(same["three_minus_same_draw_one"])
    checkpoints = paired_rr(
        same["checkpoint_three_minus_same_draw_stochastic_three"]
    )
    canonical = answer9["splits"]["seen"]
    pool = paired_rr(canonical["answer_9choose3_minus_answer_3seed"])
    relation = paired_rr(crossfit["mixed_minus_answer"])
    rows = [
        (
            r"Decoding: $T_1-A_1$",
            decoding["mean_single_minus_right_instance_weighted"],
            *decoding["cluster_bootstrap_95ci"],
        ),
        (
            r"Same draws: $S_3-T_1$",
            breadth["left_minus_mean_single_instance_weighted"],
            *breadth["cluster_bootstrap_95ci"],
        ),
        (
            r"Checkpoints: $A_3-S_3$",
            checkpoints["left_minus_right_instance_weighted"],
            *checkpoints["cluster_bootstrap_95ci"],
        ),
        (
            r"Answer pool: $A_9-A_3$",
            pool["left_minus_right_instance_weighted"],
            *pool["cluster_bootstrap_95ci"],
        ),
        (
            r"Mixed targets: $M_9-A_9$",
            relation["left_minus_right_instance_weighted"],
            *relation["cluster_bootstrap_95ci"],
        ),
    ]
    return [(label, 100 * value, 100 * lo, 100 * hi) for label, value, lo, hi in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--decomposition", type=Path, required=True)
    parser.add_argument("--answer9", type=Path, required=True)
    parser.add_argument("--crossfit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = forest_rows(read(args.decomposition), read(args.answer9), read(args.crossfit))

    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 7, "font.family": "serif"})
    fig, axis = plt.subplots(figsize=(3.35, 1.82))
    y = list(reversed(range(len(rows))))
    values = [row[1] for row in rows]
    lower = [row[1] - row[2] for row in rows]
    upper = [row[3] - row[1] for row in rows]
    axis.axvline(0, color="#4b5563", linewidth=0.8, linestyle="--")
    axis.errorbar(
        values,
        y,
        xerr=[lower, upper],
        fmt="o",
        markersize=4.2,
        color="#155e75",
        ecolor="#0e7490",
        capsize=2.5,
        linewidth=1.2,
    )
    axis.set_yticks(y, [row[0] for row in rows])
    axis.set_xlabel("Left minus right RR (percentage points)")
    axis.grid(axis="x", color="#d1d5db", linewidth=0.45)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)
    for yi, (_label, value, lo, hi) in zip(y, rows, strict=True):
        axis.text(hi + 0.35, yi, f"{value:+.1f}", va="center", fontsize=6.5)
    fig.tight_layout(pad=0.5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, bbox_inches="tight")


if __name__ == "__main__":
    main()
