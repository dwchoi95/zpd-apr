#!/usr/bin/env python3
"""Verify the FSE 2027 10-page body and 2-page reference boundary."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

PAGE_LIMIT = 12               # 10 body pages plus up to 2 reference pages
BODY_LAST_PAGE = 10
BODY_HEADINGS = (
    "Introduction",
    "Preliminaries",
    "Our Approach",
    "Experiments",
    "Related Work",
    "Conclusion",
    "Ethics and Research Transparency",
    "Data and Artifact Availability",
)


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
    """The first line that is neither a running head, a line number, nor blank."""
    for raw in text.splitlines():
        line = re.sub(r"^\d+\s+", "", raw.strip())          # review line-number gutter
        line = re.sub(r"\s{2,}.*$", "", line).strip()        # neighbouring column or gutter
        if not line or line in {"Anon.", "Anonymous Author(s)"} or re.fullmatch(r"\d+", line):
            continue
        if not line.startswith("FSE ’27") and not line.startswith("FSE '27"):
            return line
    raise ValueError("page has no content line")


def heading_page(pages: dict[int, str], heading: str) -> int | None:
    for number in sorted(pages):
        if heading in pages[number]:
            return number
    return None


def verify(pdf: Path) -> dict[str, object]:
    for tool in ("pdfinfo", "pdftotext"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"required tool not found: {tool}")
    pages = page_count(pdf)
    if pages > PAGE_LIMIT:
        raise ValueError(f"FSE page limit exceeded: {pages} > {PAGE_LIMIT}")
    text = {number: page_text(pdf, number) for number in range(1, pages + 1)}

    located = {heading: heading_page(text, heading) for heading in BODY_HEADINGS}
    missing = [heading for heading, page in located.items() if page is None]
    if missing:
        raise ValueError(f"body headings absent from the PDF: {missing}")
    late = {heading: page for heading, page in located.items() if page > BODY_LAST_PAGE}
    if late:
        raise ValueError(f"body content after page {BODY_LAST_PAGE}: {late}")

    references_first_page = heading_page(text, "References")
    if references_first_page is None:
        raise ValueError("the PDF has no reference list")
    if references_first_page > BODY_LAST_PAGE:
        raise ValueError(
            f"references begin on page {references_first_page}, "
            f"so the body exceeds {BODY_LAST_PAGE} pages"
        )
    body_last_page = max(located.values())
    if references_first_page < body_last_page:
        raise ValueError("references begin before the last body section")
    return {
        "schema_version": 2,
        "pdf": str(pdf),
        "page_limit": PAGE_LIMIT,
        "total_pages": pages,
        "body_last_page": body_last_page,
        "references_first_page": references_first_page,
        "references_last_page": pages,
        "reference_span_pages": pages - references_first_page + 1,
        "extra_reference_pages": pages - BODY_LAST_PAGE,
        "references_page_first_content": first_content_line(text[references_first_page]),
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
