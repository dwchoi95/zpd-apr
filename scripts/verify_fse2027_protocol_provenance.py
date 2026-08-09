#!/usr/bin/env python3
"""Verify that declared FSE protocol files remain at their frozen Git blobs."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


def git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=check, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(manifest_path: Path, repo: Path, head: str = "HEAD") -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("unsupported protocol manifest schema")
    resolved_head = git("rev-parse", head, cwd=repo).stdout.strip()
    rows: list[dict[str, Any]] = []
    for experiment, spec in manifest["experiments"].items():
        files = spec.get("files")
        if not isinstance(files, dict) or not files:
            raise ValueError(f"{experiment}: files must be a non-empty mapping")
        for relative, revision in files.items():
            path = repo / relative
            if not path.is_file():
                raise FileNotFoundError(f"missing protocol file: {relative}")
            ancestry = git(
                "merge-base", "--is-ancestor", revision, resolved_head,
                cwd=repo, check=False,
            )
            if ancestry.returncode != 0:
                raise RuntimeError(
                    f"{experiment}: {revision} is not an ancestor of {resolved_head}"
                )
            frozen = subprocess.run(
                ["git", "show", f"{revision}:{relative}"], cwd=repo,
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).stdout
            current = path.read_bytes()
            if frozen != current:
                raise RuntimeError(
                    f"{experiment}: {relative} differs from frozen revision {revision}"
                )
            committed_at = git(
                "show", "-s", "--format=%cI", revision, cwd=repo
            ).stdout.strip()
            rows.append({
                "experiment": experiment,
                "path": relative,
                "frozen_revision": revision,
                "committed_at": committed_at,
                "sha256": sha256(current),
                "unchanged_at_head": True,
            })
    return {
        "schema_version": 1,
        "scope": manifest["scope"],
        "head_revision": resolved_head,
        "verified_files": len(rows),
        "all_frozen_blobs_unchanged": True,
        "files": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.manifest, args.repo.resolve(), args.head)
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
