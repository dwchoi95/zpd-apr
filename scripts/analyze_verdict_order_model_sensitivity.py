#!/usr/bin/env python3
"""Compare canonical and alternative-verdict-order trained adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_fse2027_robustness import paired_suite_rows, read_jsonl, summarize_method


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repair_agreement(left: list[dict], right: list[dict]) -> dict[str, Any]:
    left_map = {str(row["example_id"]): bool(row["repaired"]) for row in left}
    right_map = {str(row["example_id"]): bool(row["repaired"]) for row in right}
    if set(left_map) != set(right_map):
        raise ValueError("paired evaluations cover different examples")
    both = sum(left_map[key] and right_map[key] for key in left_map)
    left_only = sum(left_map[key] and not right_map[key] for key in left_map)
    right_only = sum(right_map[key] and not left_map[key] for key in left_map)
    neither = len(left_map) - both - left_only - right_only
    return {
        "examples": len(left_map),
        "both_repaired": both,
        "canonical_only": left_only,
        "alternative_only": right_only,
        "neither_repaired": neither,
        "decision_agreement": (both + neither) / len(left_map),
    }


def analyze(
    evaluations: dict[tuple[str, str, str], list[dict]],
    dataset_summaries: dict[tuple[str, str], dict[str, Any]],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "alternative_order": "accepted-vs-failure",
        "model_level_retraining": True,
        "seed": 2027,
        "dataset_summaries": {
            f"{partition}-{relation}": summary
            for (partition, relation), summary in sorted(dataset_summaries.items())
        },
        "relations": {},
    }
    for relation_index, relation in enumerate(("progress", "strict")):
        relation_result = {"splits": {}}
        for split_index, split in enumerate(("seen", "unseen")):
            canonical = evaluations[(relation, split, "canonical")]
            alternative = evaluations[(relation, split, "alternative")]
            relation_result["splits"][split] = {
                "canonical": summarize_method(canonical),
                "alternative": summarize_method(alternative),
                "canonical_minus_alternative": paired_suite_rows(
                    canonical,
                    alternative,
                    left_label=f"{relation}-canonical-order",
                    right_label=f"{relation}-accepted-vs-failure",
                    samples=samples,
                    seed=seed + relation_index * 100 + split_index * 10,
                ),
                "repair_agreement": repair_agreement(canonical, alternative),
            }
        result["relations"][relation] = relation_result
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evaluation",
        action="append",
        required=True,
        help="RELATION:SPLIT:ORDER=PATH",
    )
    parser.add_argument(
        "--dataset-summary",
        action="append",
        required=True,
        help="PARTITION:RELATION=PATH",
    )
    parser.add_argument("--samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluations = {}
    for raw in args.evaluation:
        try:
            key, path = raw.split("=", 1)
            relation, split, order = key.split(":", 2)
        except ValueError:
            parser.error("--evaluation must use RELATION:SPLIT:ORDER=PATH")
        evaluations[(relation, split, order)] = read_jsonl(Path(path))
    summaries = {}
    for raw in args.dataset_summary:
        try:
            key, path = raw.split("=", 1)
            partition, relation = key.split(":", 1)
        except ValueError:
            parser.error("--dataset-summary must use PARTITION:RELATION=PATH")
        summaries[(partition, relation)] = read(Path(path))
    expected_evaluations = {
        (relation, split, order)
        for relation in ("progress", "strict")
        for split in ("seen", "unseen")
        for order in ("canonical", "alternative")
    }
    expected_summaries = {
        (partition, relation)
        for partition in ("train", "valid")
        for relation in ("progress", "strict")
    }
    if set(evaluations) != expected_evaluations:
        parser.error("evaluation matrix is incomplete")
    if set(summaries) != expected_summaries:
        parser.error("dataset-summary matrix is incomplete")
    result = analyze(evaluations, summaries, samples=args.samples, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
