#!/usr/bin/env python3
"""Report 1.5B replication training progress in examples, not optimizer steps."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


PLAN = {
    "progress": (2027, 2028, 2029),
    "strict": (2027, 2028, 2029),
    "answer": (2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035),
}
EFFECTIVE_BATCH_SIZE = 16
HEADER = re.compile(
    r"\[([^\]]+)\] Training 1\.5B (progress|strict|answer) seed (\d+)"
)
UPDATE = re.compile(r"(\d+)/(\d+)")


def line_count(path: Path) -> int:
    with path.open("rb") as source:
        return sum(1 for line in source if line.strip())


def has_summary(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def summarize(
    log: Path,
    checkpoint_root: Path,
    dataset_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    examples = {
        mode: line_count(dataset_root / f"train-{mode}.jsonl") for mode in PLAN
    }
    planned = [(mode, seed) for mode, seeds in PLAN.items() for seed in seeds]
    total_examples = sum(examples[mode] for mode, _ in planned)
    completed = {
        (mode, seed)
        for mode, seed in planned
        if has_summary(
            checkpoint_root / f"seed-{seed}" / mode / "training_summary.json"
        )
    }
    completed_examples = sum(examples[mode] for mode, seed in completed)

    normalized = log.read_text(encoding="utf-8", errors="replace").replace("\r", "\n")
    headers = list(HEADER.finditer(normalized))
    active: dict[str, Any] | None = None
    throughput: float | None = None
    eta: datetime | None = None
    if headers:
        latest = headers[-1]
        started_text, mode, seed_text = latest.groups()
        seed = int(seed_text)
        expected_updates = math.ceil(examples[mode] / EFFECTIVE_BATCH_SIZE)
        # Trainer emits nested tqdm bars for validation after the training bar.
        # Only accept the denominator implied by the training example count so
        # that a validation bar cannot make a finished epoch look restarted.
        updates = [
            match
            for match in UPDATE.finditer(normalized[latest.end() :])
            if int(match.group(2)) == expected_updates
        ]
        if (mode, seed) not in completed and updates:
            done_updates, total_updates = map(int, updates[-1].groups())
            active_examples = min(done_updates * EFFECTIVE_BATCH_SIZE, examples[mode])
            completed_examples += active_examples
            active = {
                "mode": mode,
                "seed": seed,
                "examples_completed": active_examples,
                "examples_total": examples[mode],
                "optimizer_updates_observed": done_updates,
                "optimizer_updates_total": total_updates,
            }
            started = datetime.fromisoformat(started_text)
            observed_at = now or datetime.now(tz=started.tzinfo)
            elapsed = (observed_at - started).total_seconds()
            if elapsed > 0 and active_examples > 0:
                throughput = active_examples / elapsed
                eta = observed_at + timedelta(
                    seconds=(total_examples - completed_examples) / throughput
                )

    return {
        "planned_adapters": len(planned),
        "completed_adapters": len(completed),
        "completed_adapter_ids": [
            f"{mode}:{seed}" for mode, seed in sorted(completed)
        ],
        "active_adapter": active,
        "examples_completed": completed_examples,
        "examples_total": total_examples,
        "percent_complete": 100.0 * completed_examples / total_examples,
        "effective_batch_size": EFFECTIVE_BATCH_SIZE,
        "dataset_examples": examples,
        "throughput_examples_per_second": throughput,
        "estimated_completion_time": eta.isoformat() if eta else None,
        "eta_assumption": (
            "current active-adapter throughput remains constant"
            if eta
            else None
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(summarize(args.log, args.checkpoint_root, args.dataset_root)))


if __name__ == "__main__":
    main()
