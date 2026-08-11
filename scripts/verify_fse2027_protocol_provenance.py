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
    amendment_rows: list[dict[str, Any]] = []
    final_replacement: dict[str, tuple[str, bytes]] = {}
    for amendment in manifest.get("amendments", []):
        original = amendment.get("original_files", {})
        replacement = amendment.get("replacement_files", {})
        if not original or set(original) != set(replacement):
            raise ValueError("protocol amendment file maps must be non-empty and identical")
        for relative in sorted(original):
            original_revision = str(original[relative])
            replacement_revision = str(replacement[relative])
            if relative in final_replacement:
                preceding_revision, preceding_blob = final_replacement[relative]
                if original_revision != preceding_revision:
                    raise RuntimeError(
                        f"amendment chain for {relative} starts at "
                        f"{original_revision}, expected {preceding_revision}"
                    )
            for revision in (original_revision, replacement_revision):
                ancestry = git(
                    "merge-base", "--is-ancestor", revision, resolved_head,
                    cwd=repo, check=False,
                )
                if ancestry.returncode != 0:
                    raise RuntimeError(
                        f"amendment revision {revision} is not an ancestor of {resolved_head}"
                    )
            before = subprocess.run(
                ["git", "show", f"{original_revision}:{relative}"], cwd=repo,
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).stdout
            after = subprocess.run(
                ["git", "show", f"{replacement_revision}:{relative}"], cwd=repo,
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).stdout
            if relative in final_replacement and before != preceding_blob:
                raise RuntimeError(f"amendment chain blob mismatch for {relative}")
            final_replacement[relative] = (replacement_revision, after)
            amendment_rows.append({
                "amendment": amendment["id"],
                "path": relative,
                "original_revision": original_revision,
                "replacement_revision": replacement_revision,
                "original_sha256": sha256(before),
                "replacement_sha256": sha256(after),
                "content_changed": before != after,
            })
    for relative, (replacement_revision, final_blob) in final_replacement.items():
        if (repo / relative).read_bytes() != final_blob:
            raise RuntimeError(
                f"amended file {relative} differs from final replacement "
                f"revision {replacement_revision}"
            )
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
        "declared_amendments": len(manifest.get("amendments", [])),
        "verified_amended_files": len(amendment_rows),
        "all_declared_amendments_verified": True,
        "amendments": amendment_rows,
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
