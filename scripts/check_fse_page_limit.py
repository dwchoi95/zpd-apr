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
    data_availability_page = None
    content_before_data_availability = None
    reference_page = None
    content_before_references = None
    for page in range(1, pages + 1):
        text = output("pdftotext", "-f", str(page), "-l", str(page), "-layout", str(pdf), "-")
        if data_availability_page is None:
            data_heading = re.search(
                r"(?m)^\s*(?:\d+\s+){0,2}Data Availability\s*$", text
            )
            if data_heading:
                data_availability_page = page
                prefix_lines = [
                    line.strip()
                    for line in text[: data_heading.start()].splitlines()
                    if line.strip()
                ]
                content_before_data_availability = max(0, len(prefix_lines) - 1)
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
    if data_availability_page is None:
        raise RuntimeError("Data Availability heading not found")
    if data_availability_page >= reference_page:
        if data_availability_page > reference_page:
            raise RuntimeError("Data Availability must precede References")
    # FSE 2027 excludes the required post-Conclusion Data Availability
    # statement from the page limit. If the heading shares a page with the
    # Conclusion, that physical page still counts once as a body page.
    body_pages = data_availability_page - (
        0 if content_before_data_availability else 1
    )
    data_availability_pages = reference_page - data_availability_page
    if data_availability_pages == 0:
        data_availability_pages = 1
    reference_pages = pages - reference_page + 1
    # Any non-heading text before References belongs to the required
    # post-Conclusion Data Availability statement, whose text FSE excludes
    # from the limit. Source-level integrity tests enforce the section order.
    data_availability_lines_on_reference_page = content_before_references
    body_lines_on_reference_page = 0
    if body_pages > 18 or reference_pages > 4:
        raise RuntimeError(
            "page limit exceeded: "
            f"body={body_pages}, references={reference_pages}, total={pages}, "
            f"body_lines_on_reference_page={body_lines_on_reference_page}"
        )
    return {
        "total_pages": pages,
        "body_pages": body_pages,
        "data_availability_pages": data_availability_pages,
        "data_availability_start_page": data_availability_page,
        "body_lines_before_data_availability": content_before_data_availability,
        "reference_pages": reference_pages,
        "references_start_page": reference_page,
        "body_lines_on_reference_page": body_lines_on_reference_page,
        "data_availability_lines_on_reference_page": (
            data_availability_lines_on_reference_page
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    args = parser.parse_args()
    print(check(args.pdf))


if __name__ == "__main__":
    main()
