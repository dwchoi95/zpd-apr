#!/usr/bin/env python3
"""Fail unless the rendered paper fits the FSE 18+4 page contract."""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


def output(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def check(pdf: Path) -> dict[str, int]:
    metadata = output("pdfinfo", str(pdf))
    match = re.search(r"^Pages:\s+(\d+)$", metadata, re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo did not report a page count")
    pages = int(match.group(1))
    reference_page = None
    for page in range(1, pages + 1):
        text = output("pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-")
        if re.search(r"(?m)^\s*(?:\d+\s+)?References\s*$", text):
            reference_page = page
            break
    if reference_page is None:
        raise RuntimeError("References heading not found")
    body_pages = reference_page - 1
    reference_pages = pages - reference_page + 1
    if body_pages > 18 or reference_pages > 4:
        raise RuntimeError(
            f"page limit exceeded: body={body_pages}, references={reference_pages}, total={pages}"
        )
    return {
        "total_pages": pages,
        "body_pages": body_pages,
        "reference_pages": reference_pages,
        "references_start_page": reference_page,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    print(check(args.pdf))


if __name__ == "__main__":
    main()
