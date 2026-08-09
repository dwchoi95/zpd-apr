#!/usr/bin/env python3
"""Verify that every fair-pool replication contains independent checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Callable


CONTROL_KEYS = (
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


def checkpoint_record(path: Path, relation: str, seed: int) -> dict:
    summary_path = path / "training_summary.json"
    weights_path = path / "adapter_model.safetensors"
    if not summary_path.is_file() or not weights_path.is_file():
        raise ValueError(f"incomplete checkpoint: {path}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return {
        "relation": relation,
        "seed": seed,
        "path": str(path),
        "training_controls": {key: summary.get(key) for key in CONTROL_KEYS},
        "adapter_sha256": sha256(weights_path),
    }


def audit_family(
    name: str, resolver: Callable[[str, int], Path]
) -> dict:
    records = {
        relation: [
            checkpoint_record(resolver(relation, seed), relation, seed)
            for seed in range(2027, 2030)
        ]
        for relation in ("progress", "strict", "answer")
    }
    records["answer"].extend(
        checkpoint_record(resolver("answer", seed), "answer", seed)
        for seed in range(2030, 2036)
    )
    mixed = records["progress"] + records["strict"] + records["answer"][:3]
    answer = records["answer"]

    def controls_match(group: list[dict]) -> bool:
        return all(
            row["training_controls"] == group[0]["training_controls"]
            for row in group[1:]
        )

    relation_controls_match = {
        relation: controls_match(group) for relation, group in records.items()
    }
    mixed_hashes = [row["adapter_sha256"] for row in mixed]
    answer_hashes = [row["adapter_sha256"] for row in answer]
    result = {
        "name": name,
        "mixed_candidate_checkpoint_count": len(mixed),
        "answer_candidate_checkpoint_count": len(answer),
        "relation_training_controls_match": relation_controls_match,
        "mixed_adapter_weights_are_pairwise_distinct": len(set(mixed_hashes))
        == len(mixed_hashes),
        "answer_adapter_weights_are_pairwise_distinct": len(set(answer_hashes))
        == len(answer_hashes),
        "checkpoints": records,
    }
    result["valid_independent_checkpoint_families"] = (
        len(mixed) == 9
        and len(answer) == 9
        and all(relation_controls_match.values())
        and result["mixed_adapter_weights_are_pairwise_distinct"]
        and result["answer_adapter_weights_are_pairwise_distinct"]
    )
    if not result["valid_independent_checkpoint_families"]:
        raise ValueError(f"{name}: invalid independent checkpoint family")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-root", type=Path, required=True)
    parser.add_argument("--canonical-seed-root", type=Path, required=True)
    parser.add_argument(
        "--replication", action="append", default=[], help="NAME=CHECKPOINT_ROOT"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def canonical(relation: str, seed: int) -> Path:
        if seed == 2027:
            return args.canonical_root / relation
        return args.canonical_seed_root / f"seed-{seed}" / relation

    reports = [audit_family("canonical-7b", canonical)]
    for spec in args.replication:
        name, raw_root = spec.split("=", 1)
        root = Path(raw_root)
        reports.append(
            audit_family(
                name,
                lambda relation, seed, root=root: root
                / f"seed-{seed}"
                / relation,
            )
        )
    output = {"schema_version": 1, "families": reports}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified_families": len(reports)}, sort_keys=True))


if __name__ == "__main__":
    main()
