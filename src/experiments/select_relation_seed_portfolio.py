#!/usr/bin/env python3
"""Select one independently trained seed per policy using validation loss only."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def select(entries: list[tuple[str, int, Path]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for relation, seed, checkpoint in entries:
        summary_path = checkpoint / "training_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        loss = summary.get("best_eval_loss")
        if loss is None:
            raise ValueError(f"missing best_eval_loss: {summary_path}")
        grouped[relation].append(
            {
                "seed": seed,
                "checkpoint": str(checkpoint),
                "best_eval_loss": float(loss),
                "validation_examples": summary.get("validation_examples"),
            }
        )
    if set(grouped) != {"Progress", "Strict", "Answer"}:
        raise ValueError("Progress, Strict, and Answer entries are required")
    if any(len(records) != 3 for records in grouped.values()):
        raise ValueError("exactly three seeds are required for every relation")

    selections = {}
    for relation, records in grouped.items():
        ordered = sorted(records, key=lambda record: (record["best_eval_loss"], record["seed"]))
        selections[relation] = ordered[0]
        grouped[relation] = sorted(records, key=lambda record: record["seed"])
    return {
        "selection_metric": "best_eval_loss",
        "selection_partition": "training validation split",
        "test_outcomes_used": False,
        "candidates": dict(sorted(grouped.items())),
        "selected": dict(sorted(selections.items())),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checkpoint",
        action="append",
        required=True,
        help="RELATION:SEED=CHECKPOINT_ROOT",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries = []
    for raw in args.checkpoint:
        try:
            relation_seed, raw_path = raw.split("=", 1)
            relation, raw_seed = relation_seed.split(":", 1)
        except ValueError:
            parser.error("--checkpoint must use RELATION:SEED=CHECKPOINT_ROOT")
        entries.append((relation, int(raw_seed), Path(raw_path).expanduser().resolve()))
    report = select(entries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["selected"], sort_keys=True))


if __name__ == "__main__":
    main()
