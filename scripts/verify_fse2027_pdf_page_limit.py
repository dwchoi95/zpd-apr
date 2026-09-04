#!/usr/bin/env python3
"""Verify the FSE 2027 18-page body and 4-page reference boundary."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


def run(*args: str) -> str:
    return subprocess.run(
        args, check=True, capture_output=True, text=True
    ).stdout


def page_count(pdf: Path) -> int:
    match = re.search(r"^Pages:\s+(\d+)\s*$", run("pdfinfo", str(pdf)), re.M)
    if not match:
        raise ValueError("pdfinfo did not report a page count")
    return int(match.group(1))


def page_text(pdf: Path, page: int) -> str:
    return run(
        "pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-"
    )


def first_content_line(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line in {"Anon.", "Anonymous Author(s)"}:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if (
            "ZPDPatch: Separating Trajectory Supervision" in line
            or "Disentangling Candidate Breadth and Trajectory Supervision" in line
        ):
            continue
        line = re.sub(r"^\d+\s+", "", line)
        if line:
            return line
    raise ValueError("page has no content line")


def verify(pdf: Path) -> dict[str, object]:
    for tool in ("pdfinfo", "pdftotext"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"required tool not found: {tool}")
    pages = page_count(pdf)
    if pages > 22:
        raise ValueError(f"FSE page limit exceeded: {pages} > 22")
    body_last = page_text(pdf, 18)
    if not any(
        heading in body_last
        for heading in ("Data Availability", "Data and Artifact Availability")
    ):
        raise ValueError("data and artifact availability is not present on body page 18")
    if "References" in body_last:
        raise ValueError("references begin before the 18-page body boundary")
    references_first = page_text(pdf, 19)
    first = first_content_line(references_first)
    if first != "References":
        raise ValueError(
            "page 19 begins with non-reference body content: " + repr(first)
        )
    return {
        "schema_version": 1,
        "pdf": str(pdf),
        "total_pages": pages,
        "body_last_page": 18,
        "references_first_page": 19,
        "references_last_page": pages,
        "reference_pages": pages - 18,
        "page_19_first_content": first,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.pdf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
