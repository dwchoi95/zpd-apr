#!/usr/bin/env python3
"""Report sequential online cost and selector parseability invariants."""

from __future__ import annotations

import argparse
import ast
import json
import statistics
from pathlib import Path
from typing import Any


Row = dict[str, Any]

# Sums of Trainer's logged train_runtime for the exact checkpoint families.
# A1 is Answer2027; A3 adds Answer2028/2029; A9 adds Answer2030--2035.
# M9 is Progress/Strict/Answer for seeds 2027--2029.
MEASURED_TRAIN_GPU_HOURS = {
    "A1": 21000.8524 / 3600,
    "A3": (21000.8524 + 21038.9459 + 21018.9971) / 3600,
    "A9": (
        21000.8524
        + 21038.9459
        + 21018.9971
        + 21023.8731
        + 21031.8538
        + 21035.9668
        + 21041.9141
        + 21032.1562
        + 21041.7397
    )
    / 3600,
    "M9": (
        14160.9376
        + 9294.9917
        + 21000.8524
        + 14171.404
        + 9298.7135
        + 21038.9459
        + 14161.9486
        + 9294.5675
        + 21018.9971
    )
    / 3600,
}


def read_keyed(path: Path) -> dict[str, Row]:
    with path.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    result = {str(row["example_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate example_id in {path}")
    return result


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, min(len(ordered) - 1, int(probability * len(ordered)) - 1))]


def parseable(code: str) -> bool:
    try:
        ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        return False
    return True


def sequence_cost(
    evaluations: dict[str, dict[str, Row]], order: list[str]
) -> dict[str, Any]:
    example_ids = sorted(set.intersection(*(set(evaluations[name]) for name in order)))
    calls: list[int] = []
    generation: list[float] = []
    execution: list[float] = []
    online: list[float] = []
    repaired = 0
    for example_id in example_ids:
        invoked = 0
        generated = 0.0
        # Current-program outcomes are already cached when the repair request is
        # formed. Count only candidate execution, matching the LSGen artifact.
        executed = 0.0
        for name in order:
            row = evaluations[name][example_id]
            invoked += 1
            generated += float(row.get("generation_time_sec", 0.0))
            executed += float(row.get("fixed_execution_time_sec", 0.0))
            if bool(row.get("repaired")):
                repaired += 1
                break
        calls.append(invoked)
        generation.append(generated)
        execution.append(executed)
        online.append(generated + executed)
    return {
        "examples": len(example_ids),
        "order": order,
        "mean_candidates_invoked": statistics.mean(calls),
        "repair_rate": repaired / len(example_ids),
        "mean_generation_sec": statistics.mean(generation),
        "mean_execution_sec": statistics.mean(execution),
        "mean_online_sec": statistics.mean(online),
        "median_online_sec": statistics.median(online),
        "p95_online_sec": percentile(online, 0.95),
    }


def lsgen_cost(path: Path) -> dict[str, Any]:
    rows = list(read_keyed(path).values())
    online = [float(row["online_time_sec"]) for row in rows]
    return {
        "examples": len(rows),
        "mean_candidates_invoked": statistics.mean(
            len(row.get("patches", [])) for row in rows
        ),
        "mean_generation_sec": statistics.mean(
            float(row["generation_time_sec"]) for row in rows
        ),
        "mean_execution_sec": statistics.mean(
            float(row["execution_time_sec"]) for row in rows
        ),
        "mean_online_sec": statistics.mean(online),
        "median_online_sec": statistics.median(online),
        "p95_online_sec": percentile(online, 0.95),
    }


def parse_audit(
    dataset_path: Path,
    selected_path: Path,
    evaluations: dict[str, dict[str, Row]],
) -> dict[str, Any]:
    dataset = read_keyed(dataset_path)
    selected = read_keyed(selected_path)
    unparseable_current = sum(
        not parseable(str(row["history"][-1]["code"])) for row in dataset.values()
    )
    changed = unparseable_selected = 0
    for example_id, row in selected.items():
        source = str(row.get("selected_source", "current-fallback"))
        if source not in evaluations:
            continue
        changed += 1
        candidate = evaluations[source][example_id]
        if not parseable(str(candidate.get("generated_code", ""))):
            unparseable_selected += 1
    return {
        "examples": len(dataset),
        "unparseable_current": unparseable_current,
        "selected_changed": changed,
        "unparseable_selected_changed": unparseable_selected,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-root", type=Path, required=True)
    parser.add_argument("--answer9-root", type=Path, required=True)
    parser.add_argument("--seen-dataset", type=Path, required=True)
    parser.add_argument("--unseen-dataset", type=Path, required=True)
    parser.add_argument("--lsgen", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    methods = ["Progress2027", "Answer2027", "Answer2028", "Answer2029"]
    report: dict[str, Any] = {"splits": {}}
    for split, dataset in (("seen", args.seen_dataset), ("unseen", args.unseen_dataset)):
        evaluations = {
            name: read_keyed(
                args.selected_root / f"{name}-{split}-test.evaluation.jsonl"
            )
            for name in methods
        }
        report["splits"][split] = {
            "zpdpatch": sequence_cost(
                evaluations, ["Progress2027", "Answer2027", "Answer2028"]
            ),
            "answer_3seed": sequence_cost(
                evaluations, ["Answer2027", "Answer2028", "Answer2029"]
            ),
            "parse_audit": parse_audit(
                dataset,
                args.selected_root / f"unconstrained-{split}-test.evaluation.jsonl",
                evaluations,
            ),
        }
    report["lsgen_seen"] = lsgen_cost(args.lsgen)
    seen_evaluations = {
        name: read_keyed(
            args.selected_root / f"{name}-seen-test.evaluation.jsonl"
        )
        for name in methods
    }
    answer9_evaluations = {
        name: read_keyed(args.answer9_root / f"{name}-seen-test.evaluation.jsonl")
        for name in ("Answer2032", "Answer2033", "Answer2034")
    }
    ladder_sequences = {
        "A1": sequence_cost(seen_evaluations, ["Answer2027"]),
        "A3": sequence_cost(
            seen_evaluations, ["Answer2027", "Answer2028", "Answer2029"]
        ),
        "A9": sequence_cost(
            answer9_evaluations, ["Answer2032", "Answer2033", "Answer2034"]
        ),
        "M9": sequence_cost(
            seen_evaluations, ["Progress2027", "Answer2027", "Answer2028"]
        ),
    }
    report["mechanism_ladder_seen"] = {
        name: {
            "trained_adapters": {"A1": 1, "A3": 3, "A9": 9, "M9": 9}[name],
            "train_gpu_hours": MEASURED_TRAIN_GPU_HOURS[name],
            "portfolio_selection_validation_executions": (
                0 if name in {"A1", "A3"} else 9 * 461
            ),
            "repair_rate": ladder_sequences[name]["repair_rate"],
            "mean_candidates_invoked": ladder_sequences[name][
                "mean_candidates_invoked"
            ],
        }
        for name in ("A1", "A3", "A9", "M9")
    }
    report["mechanism_ladder_seen"]["runtime_provenance"] = {
        "unit": "RTX 5090 GPU-hours",
        "source": "Trainer train_runtime entries in gpu-pipeline.log, multiseed.log, and answer9-control.log",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
