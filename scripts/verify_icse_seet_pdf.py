#!/usr/bin/env python3
"""Read-only ICSE-SEET 2027 Research Paper format audit (10 + 2 pages).

The manuscript deliberately starts references on a new page. This stronger
local contract makes the body/reference boundary auditable without inferring
which paragraphs are references from their wording. It is not a CFP requirement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BODY_LIMIT = 10
REFERENCE_LIMIT = 2
CFP = "https://conf.researchr.org/track/icse-2027/icse-2027-software-engineering-education-and-training--seet-"
HEADINGS = ("Introduction", "Preliminaries", "Our Approach", "Experiments", "Related Work", "Conclusion", "Data Availability")


def run(*args: str) -> str:
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout


def normalize(text: str) -> str:
    return re.sub(r"[^a-z]", "", text.lower())


def heading_page(pages: list[str], heading: str) -> int | None:
    key = normalize(heading)
    for number, page in enumerate(pages, 1):
        for line in page.splitlines():
            line = re.sub(r"^[IVX]+\.\s*", "", line.strip())
            if normalize(line) == key:
                return number
    return None


def check_pages(pages: list[str]) -> dict:
    if len(pages) > BODY_LIMIT + REFERENCE_LIMIT:
        raise ValueError(f"total page limit exceeded: {len(pages)} > 12")
    first = heading_page(pages, "References")
    if first is None:
        raise ValueError("References heading missing")
    first_line = next((line for line in pages[first - 1].splitlines() if line.strip()), "")
    if normalize(first_line) != "references":
        raise ValueError("local boundary contract: references must start a fresh page")
    body = first - 1
    references = len(pages) - first + 1
    if body > BODY_LIMIT:
        raise ValueError(f"body page limit exceeded: {body} > 10")
    if references > REFERENCE_LIMIT:
        raise ValueError(f"reference page limit exceeded: {references} > 2")
    locations = {heading: heading_page(pages, heading) for heading in HEADINGS}
    if any(number is None or number > body for number in locations.values()):
        raise ValueError(f"missing or late body headings: {locations}")
    return {"body_pages": body, "reference_pages": references,
            "total_pages": len(pages), "references_first_page": first,
            "heading_pages": locations}


def check_source(source: str) -> None:
    source = re.sub(r"(?<!\\)%[^\n]*", "", source)
    if not re.search(r"\\documentclass\[10pt,conference\]\{IEEEtran\}", source):
        raise ValueError("required IEEEtran class/options missing")
    if r"\bibliographystyle{IEEEtran}" not in source:
        raise ValueError("IEEE reference style missing")
    forbidden = r"\\(?:geometry|fontsize|baselinestretch|newcommand|resizebox|tiny|vspace|enlargethispage)\b|compsoc|\\(?:setlength|addtolength)\s*\{?\\(?:textwidth|textheight|columnsep|baselineskip|topmargin|oddsidemargin)"
    if re.search(forbidden, source):
        raise ValueError("nonstandard layout/font override or user macro found")
    if any(tag in source for tag in (r"\acmConference", r"\ccsdesc", r"\settopmatter")):
        raise ValueError("stale ACM metadata found")
    if not re.search(r"\\author\{\s*\}", source):
        raise ValueError("anonymous submission must omit author names")


def check_float_order(pdf: Path) -> dict:
    """Check first references in two-column reading order using Poppler boxes."""
    # pdftotext -bbox-layout aborts in the installed Poppler build on this PDF.
    # pdftohtml XML supplies the same required page/text coordinates reliably.
    root = ET.fromstring(run("pdftohtml", "-xml", "-i", "-zoom", "1", "-stdout", str(pdf)))
    lines = []
    for page_number, page in enumerate(root.findall("page"), 1):
        middle = float(page.get("width")) / 2
        groups = []
        for node in sorted(page.findall("text"), key=lambda n: float(n.get("top"))):
            x, y = float(node.get("left")), float(node.get("top"))
            column = int(x >= middle)
            group = next((g for g in groups if g[0] == column and abs(g[1] - y) <= 2), None)
            if group is None:
                group = [column, y, []]
                groups.append(group)
            group[2].append((x, "".join(node.itertext())))
        for column, y, nodes in groups:
            nodes.sort()
            content = " ".join(text for _, text in nodes)
            lines.append((content, (page_number, column, y), (nodes[0][0], y)))
    result = {}
    for kind, numbers in (("Table", ("I", "II", "III", "IV", "V", "VI", "VII")), ("Figure", ("1",)), ("Algorithm", ("1", "2"))):
        for number in numbers:
            if kind == "Table":
                caption = re.compile(rf"^TABLE\s+{number}$")
            elif kind == "Figure":
                caption = re.compile(rf"^Fig\.\s+{number}\.")
            else:
                caption = re.compile(rf"^Algorithm\s+{number}:")
            mention = re.compile(rf"\b{kind}\s+{number}\b(?!:)")
            captions = [row for row in lines if caption.search(row[0])]
            references = [row for row in lines if mention.search(row[0]) and not caption.search(row[0])]
            if not captions or not references:
                raise ValueError(f"missing caption or reference for {kind} {number}")
            cap, ref = min(captions, key=lambda r: r[1]), min(references, key=lambda r: r[1])
            if cap[1] >= ref[1]:
                raise ValueError(f"{kind} {number} appears after its first reference: {cap[1]}, {ref[1]}")
            result[f"{kind} {number}"] = {"caption_page_column_y": cap[1], "first_reference_page_column_y": ref[1], "caption_xy": cap[2], "first_reference_xy": ref[2]}
    return result


def verify(pdf: Path, source: Path) -> dict:
    check_source(source.read_text())
    info = run("pdfinfo", str(pdf))
    count = int(re.search(r"^Pages:\s+(\d+)", info, re.M)[1])
    pages = [run("pdftotext", "-f", str(n), "-l", str(n), "-raw", str(pdf), "-") for n in range(1, count + 1)]
    result = check_pages(pages)
    result["float_order"] = check_float_order(pdf)
    xml = ET.fromstring(run("pdftohtml", "-xml", "-i", "-zoom", "1", "-stdout", str(pdf)))
    fonts = {node.get("id"): float(node.get("size")) for node in xml.iter("fontspec")}
    title_nodes = [node for node in xml.find("page").findall("text") if "ZPDPatch: Evaluating" in "".join(node.itertext())]
    if not title_nodes or any(fonts[node.get("font")] != 24 for node in title_nodes):
        raise ValueError("title not rendered in 24pt")
    body_nodes = [node for node in xml.iter("text") if "Automated program repair (APR)" in "".join(node.itertext())]
    if not body_nodes or any(fonts[node.get("font")] != 10 for node in body_nodes):
        raise ValueError("body sample not rendered in 10pt")
    font_lines = run("pdffonts", str(pdf)).splitlines()[2:]
    if not font_lines or any("Type 3" in line or line.split()[-5] != "yes" for line in font_lines):
        raise ValueError("unembedded or Type-3 font detected")
    author = re.search(r"^Author:[ \t]*(.*)$", info, re.M)
    if author and author[1].strip():
        raise ValueError("PDF author metadata is not anonymous")
    result.update(schema_version=1, venue="ICSE-SEET 2027 Research Paper", cfp=CFP,
                  pdf=str(pdf), source=str(source), title_pt=24, body_pt=10,
                  font_count=len(font_lines), embedded_fonts=True, type3_fonts=False,
                  sha256=hashlib.sha256(pdf.read_bytes()).hexdigest(),
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=Path("paper/main.pdf"))
    parser.add_argument("--source", type=Path, default=Path("paper/main.tex"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.pdf, args.source)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
