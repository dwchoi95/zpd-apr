#!/usr/bin/env python3
"""Compare the heterogeneous portfolio with an independent Answer-seed control."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from analyze_fse2027_robustness import (
    paired_suite_rows,
    read_jsonl,
    replay_selected_rows,
)


TRAINING_CONTROL_KEYS = (
    "dataset_path",
    "base_model",
    "prompt_style",
    "source_examples",
    "encoded_examples",
    "validation_examples",
    "encoded_validation_examples",
    "completed_steps",
    "completed_epochs",
    "per_device_batch_size",
    "gradient_accumulation_steps",
    "effective_batch_size",
    "edit_token_weight",
    "num_train_epochs",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_checkpoints(checkpoints: list[tuple[int, Path]]) -> dict[str, Any]:
    if len(checkpoints) != 3:
        raise ValueError("exactly three Answer checkpoints are required")
    records = []
    for seed, root in checkpoints:
        summary_path = root / "training_summary.json"
        weights_path = root / "adapter_model.safetensors"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        controls = {key: summary.get(key) for key in TRAINING_CONTROL_KEYS}
        records.append(
            {
                "seed": seed,
                "checkpoint": str(root),
                "training_controls": controls,
                "best_eval_loss": summary.get("best_eval_loss"),
                "adapter_sha256": sha256(weights_path),
            }
        )
    controls_match = all(
        record["training_controls"] == records[0]["training_controls"]
        for record in records[1:]
    )
    weight_hashes = [record["adapter_sha256"] for record in records]
    distinct_weights = len(set(weight_hashes)) == len(weight_hashes)
    return {
        "checkpoints": records,
        "training_controls_match": controls_match,
        "adapter_weights_are_pairwise_distinct": distinct_weights,
        "valid_independent_seed_control": controls_match and distinct_weights,
    }


def rr_contrast(report: dict[str, Any]) -> dict[str, Any]:
    rr = next(item for item in report["paired"] if item["metric"] == "rr")
    lower, upper = rr["cluster_bootstrap_95ci"]
    return {
        "zpdpatch_minus_answer_3seed_rr": rr[
            "left_minus_right_instance_weighted"
        ],
        "problem_cluster_95ci": [lower, upper],
        "exact_mcnemar_two_sided_p": report["exact_mcnemar_two_sided_p"],
        "supports_heterogeneous_target_claim": lower > 0.0,
    }


def build_report(
    eval_root: Path,
    *,
    checkpoints: list[tuple[int, Path]],
    bootstrap_samples: int,
    seed: int,
) -> dict[str, Any]:
    checkpoint_audit = audit_checkpoints(checkpoints)
    comparisons: dict[str, Any] = {}
    for offset, split in enumerate(("seen", "unseen")):
        if split == "seen":
            left_rows = replay_selected_rows(
                eval_root, ("progress", "strict", "answer")
            )
            left_label = "replayed:progress-strict-answer"
        else:
            left_path = (
                eval_root
                / "acceptance-ablations"
                / "zpdpatch-unseen-test-no-stage-feedback.evaluation.jsonl"
            )
            left_rows = read_jsonl(left_path)
            left_label = str(left_path)
        right = (
            eval_root
            / "answer-seed-control"
            / f"answer-seeds-{split}-test.evaluation.jsonl"
        )
        comparisons[split] = paired_suite_rows(
            left_rows,
            read_jsonl(right),
            left_label=left_label,
            right_label=str(right),
            samples=bootstrap_samples,
            seed=seed + offset * 100,
        )

    primary = rr_contrast(comparisons["seen"])
    return {
        "schema_version": 1,
        "control": {
            "policies": ["Answer2027", "Answer2028", "Answer2029"],
            "same_training_examples_and_targets": checkpoint_audit[
                "training_controls_match"
            ],
            "independent_training_seeds": [2027, 2028, 2029],
            "stage_feedback": False,
            "maximum_candidates": 3,
            "selection": "first-AC-else-pass-rate-then-TED-with-current-fallback",
        },
        "checkpoint_audit": checkpoint_audit,
        "bootstrap": {
            "samples": bootstrap_samples,
            "seed": seed,
            "cluster": "problem_id",
        },
        "comparisons": comparisons,
        "primary_seen_conclusion": primary,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--checkpoint",
        action="append",
        required=True,
        help="SEED=CHECKPOINT_ROOT; repeat exactly three times",
    )
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()

    checkpoints = []
    for value in args.checkpoint:
        if "=" not in value:
            parser.error("--checkpoint must use SEED=CHECKPOINT_ROOT")
        raw_seed, raw_path = value.split("=", 1)
        checkpoints.append((int(raw_seed), Path(raw_path).expanduser().resolve()))

    report = build_report(
        args.eval_root.expanduser().resolve(),
        checkpoints=checkpoints,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["primary_seen_conclusion"], sort_keys=True))


if __name__ == "__main__":
    main()
