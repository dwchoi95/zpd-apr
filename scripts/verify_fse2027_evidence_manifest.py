#!/usr/bin/env python3
"""Verify every record in a sealed FSE evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def jsonl_rows(path: Path) -> int:
    with path.open("rb") as source:
        return sum(1 for line in source if line.strip())


def checkpoint_roots(paths: list[Path]) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for path in paths:
        resolved = path.expanduser().resolve()
        label = f"checkpoints:{resolved.name}"
        if label in roots:
            raise ValueError(f"duplicate checkpoint label: {label}")
        roots[label] = resolved
    return roots


def verify_record(item: dict[str, Any], roots: dict[str, Path]) -> list[str]:
    failures: list[str] = []
    label = str(item["root"])
    if label not in roots:
        return [f"unknown root {label}: {item['path']}"]
    path = roots[label] / str(item["path"])
    if not path.is_file():
        return [f"missing: {path}"]
    if path.stat().st_size != int(item["bytes"]):
        failures.append(f"size mismatch: {path}")
    if digest(path) != str(item["sha256"]):
        failures.append(f"sha256 mismatch: {path}")
    if "rows" in item and jsonl_rows(path) != int(item["rows"]):
        failures.append(f"row mismatch: {path}")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, action="append", default=[])
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    roots = {"run": args.run_root.expanduser().resolve()}
    roots.update(checkpoint_roots(args.checkpoint_root))
    records = manifest["files"]
    identities = [(str(item["root"]), str(item["path"])) for item in records]
    if len(identities) != len(set(identities)):
        raise SystemExit("manifest contains duplicate root/path records")

    failures = [
        failure
        for item in records
        for failure in verify_record(item, roots)
    ]
    if failures:
        raise SystemExit("\n".join(failures))
    print(
        json.dumps(
            {
                "verified": len(records),
                "total_bytes": sum(int(item["bytes"]) for item in records),
                "source_revision": manifest["source_revision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
