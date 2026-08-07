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
    content_before_references = None
    for page in range(1, pages + 1):
        text = output("pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-")
        heading = re.search(r"(?m)^\s*(?:\d+\s+)?References\s*$", text)
        if heading:
            reference_page = page
            prefix_lines = [line.strip() for line in text[: heading.start()].splitlines() if line.strip()]
            # ACM pages contain one running-header line before the first content line.  A
            # conclusion (or any other body text) sharing the References page violates
            # the 18-page body limit even when References itself starts on page 19.
            content_before_references = max(0, len(prefix_lines) - 1)
            break
    if reference_page is None:
        raise RuntimeError("References heading not found")
    body_pages = reference_page - 1
    reference_pages = pages - reference_page + 1
    if body_pages > 18 or reference_pages > 4 or content_before_references:
        raise RuntimeError(
            "page limit exceeded: "
            f"body={body_pages}, references={reference_pages}, total={pages}, "
            f"body_lines_on_reference_page={content_before_references}"
        )
    return {
        "total_pages": pages,
        "body_pages": body_pages,
        "reference_pages": reference_pages,
        "references_start_page": reference_page,
        "body_lines_on_reference_page": content_before_references,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    print(check(args.pdf))


if __name__ == "__main__":
    main()
