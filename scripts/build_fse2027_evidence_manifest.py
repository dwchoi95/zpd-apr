#!/usr/bin/env python3
"""Seal the canonical FSE 2027 evidence graph without embedding source code."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def line_count(path: Path) -> int | None:
    if path.suffix != ".jsonl":
        return None
    with path.open("rb") as source:
        return sum(1 for _ in source)


def record(path: Path, root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }
    lines = line_count(path)
    if lines is not None:
        result["rows"] = lines
    return result


def selected_files(run_root: Path, checkpoint_roots: list[Path]) -> list[tuple[Path, Path]]:
    patterns = (
        "split-summary.json",
        "dataset-token-audit.json",
        "datasets/*.build-summary.json",
        "datasets/*-final.summary.json",
        "datasets/*-final.filter-summary.json",
        "datasets/train-*.jsonl",
        "datasets/valid-*.jsonl",
        "datasets/*-test-final.jsonl",
        "outcomes/all-original-submissions.summary.json",
        "outcomes/all-original-submissions.jsonl",
        "eval/*.evaluation.jsonl",
        "eval/*.evaluation.summary.json",
        "eval/*comparison.json",
        "eval/rq2-*-comparison/*-eval.jsonl",
        "eval/rq2-*-comparison/*-eval.summary.json",
        "eval/acceptance-ablations/*.evaluation.jsonl",
        "eval/acceptance-ablations/*.evaluation.summary.json",
        "eval/acceptance-seeds/*.evaluation.jsonl",
        "eval/acceptance-seeds/*.evaluation.summary.json",
        "analysis/*.json",
    )
    found: list[tuple[Path, Path]] = []
    for pattern in patterns:
        found.extend((path, run_root) for path in run_root.glob(pattern) if path.is_file())
    for checkpoint_root in checkpoint_roots:
        for path in checkpoint_root.glob("**/training_summary.json"):
            found.append((path, checkpoint_root))
        for path in checkpoint_root.glob("**/adapter_config.json"):
            found.append((path, checkpoint_root))
    unique = {(str(path), str(root)): (path, root) for path, root in found}
    return sorted(unique.values(), key=lambda item: (str(item[1]), str(item[0])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument(
        "--checkpoint-root", type=Path, action="append", required=True,
        help="Checkpoint tree to hash metadata from; may be repeated.",
    )
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_root = args.run_root.expanduser().resolve()
    checkpoint_roots = [path.expanduser().resolve() for path in args.checkpoint_root]
    files = []
    for path, logical_root in selected_files(run_root, checkpoint_roots):
        item = record(path, logical_root)
        item["root"] = (
            "run" if logical_root == run_root else f"checkpoints:{logical_root.name}"
        )
        files.append(item)
    manifest = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_revision": args.source_revision,
        "run_root_name": run_root.name,
        "checkpoint_root_names": [path.name for path in checkpoint_roots],
        "files": files,
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
