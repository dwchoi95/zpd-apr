#!/usr/bin/env python3
"""Reject author-revealing metadata, paths, URLs, and contact details."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


FORBIDDEN = {
    "repository account": re.compile(r"dwchoi95", re.I),
    "local user path": re.compile(r"/(?:Users|home)/cdw(?:/|\b)", re.I),
    "repository URL": re.compile(r"github\.com/dwchoi95", re.I),
    "email address": re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    "ORCID": re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b", re.I),
}


def command(*args: str) -> str:
    return subprocess.run(
        args, check=True, capture_output=True, text=True
    ).stdout


def findings(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for label, pattern in FORBIDDEN.items():
        matches = sorted(set(pattern.findall(text)))
        if matches:
            result[label] = matches
    return result


def verify(pdf: Path, sources: list[Path]) -> dict[str, object]:
    metadata = command("pdfinfo", str(pdf))
    author = re.search(r"^Author:[ \t]*(.*)$", metadata, re.M)
    if author and author.group(1) and "anonymous" not in author.group(1).lower():
        raise ValueError(f"author-revealing PDF metadata: {author.group(1)!r}")
    pdf_text = command("pdftotext", str(pdf), "-")
    texts = {str(source): source.read_text() for source in sources}
    # acmart prints an anonymous marker; IEEEtran blinds by declaring no author at all.
    blinded = "ANONYMOUS AUTHOR(S)" in pdf_text.upper() or any(
        re.search(r"\\author\{", text) and not any(
            block.strip() for block in re.findall(r"\\author\{([^{}]*)\}", text)
        )
        for text in texts.values()
    )
    if not blinded:
        raise ValueError("PDF carries neither an anonymous author marker nor an empty author block")
    scanned = {str(pdf): findings(metadata + "\n" + pdf_text)}
    scanned.update({path: findings(text) for path, text in texts.items()})
    violations = {path: rows for path, rows in scanned.items() if rows}
    if violations:
        raise ValueError("author-revealing content found: " + repr(violations))
    return {
        "schema_version": 1,
        "pdf": str(pdf),
        "sources": [str(path) for path in sources],
        "anonymous_author_marker": True,
        "metadata_author": author.group(1) if author else "",
        "forbidden_pattern_matches": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.pdf, args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
