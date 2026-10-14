#!/usr/bin/env python3
"""Verify that the paper consumes the evidence-derived result bridge verbatim."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


REQUIRED_RESULT_PREFIXES = (
    "Scale",
    "CodeWorkoutProblem",
    "Prompt",
    "CrossFit",
    "VerdictOrder",
    "CurrentOnly",
    "ExerciseSensitivity",
    "Stochastic",
    "SeenHidden",
    "SeenOverlap",
    "Sweep",
    "CheckpointStochastic",
    "BaseStochastic",
    "DifficultyMatched",
    "CrossUserTarget",
    "AllPrefix",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def command_names(text: str) -> set[str]:
    return set(re.findall(r"\\newcommand\{\\([A-Za-z][A-Za-z0-9]*)\}", text))


def verify(expected: Path, checked_in: Path, paper: Path) -> dict[str, object]:
    expected_bytes = expected.read_bytes()
    checked_in_bytes = checked_in.read_bytes()
    if expected_bytes != checked_in_bytes:
        raise ValueError("checked-in paper result bridge differs from generated evidence")

    paper_text = paper.read_text(encoding="utf-8")
    input_stem = checked_in.stem
    input_patterns = (
        rf"\\input\{{{re.escape(input_stem)}\}}",
        rf"\\input\{{{re.escape(checked_in.name)}\}}",
    )
    embedded = re.search(r"% BEGIN GENERATED RESULT BRIDGE\n(.*?)% END GENERATED RESULT BRIDGE", paper_text, re.S)
    if embedded and embedded.group(1).encode() != expected_bytes:
        raise ValueError("embedded paper result bridge differs from generated evidence")
    literal = paper.with_suffix('.evidence-bindings.json')
    literal_names = set()
    if not embedded and not any(re.search(pattern, paper_text) for pattern in input_patterns):
        if not literal.is_file():
            raise ValueError(f"paper does not input {checked_in.name} and lacks literal evidence bindings")
        definitions = dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", expected_bytes.decode()))
        definitions.update(tool=r'\textsc{ZPDPatch}', progress=r'\textsc{Progress}', strict=r'\textsc{Strict}', answer=r'\textsc{Answer}')
        rows = json.loads(literal.read_text())['bindings']
        if not rows:
            raise ValueError('empty literal evidence bindings')
        for row in rows:
            names_in_template = set(re.findall(r'\\([A-Za-z]+)\b', row['template'])) & definitions.keys()
            if names_in_template != set(row['commands']):
                raise ValueError('literal binding command list differs from template')
            expanded = re.sub(r'\\([A-Za-z]+)\b', lambda match: definitions.get(match[1], match[0]), row['template'])
            expanded = re.sub(r'(?<=[\d\]])\{\}', '', expanded)
            if expanded not in paper_text:
                raise ValueError('literal evidence snippet differs: ' + expanded[:100])
            literal_names.update(row['commands'])
    if embedded:
        paper_text = paper_text[:embedded.start()] + paper_text[embedded.end():]

    names = command_names(expected_bytes.decode("utf-8"))
    required_prefixes = REQUIRED_RESULT_PREFIXES + tuple(
        prefix for prefix in ('Factorial', 'PairedJava')
        if any(name.startswith(prefix) for name in names)
    )
    missing_families = [
        prefix for prefix in required_prefixes
        if not any(name.startswith(prefix) for name in names)
    ]
    if missing_families:
        raise ValueError(f"result bridge lacks required families: {missing_families}")

    referenced = {
        name for name in names if name in literal_names or re.search(rf"\\{re.escape(name)}\b", paper_text)
    }
    unreferenced_families = [
        prefix for prefix in required_prefixes
        if not any(name.startswith(prefix) for name in referenced)
    ]
    if unreferenced_families:
        raise ValueError(
            "paper does not reference required result families: "
            f"{unreferenced_families}"
        )

    return {
        "schema_version": 1,
        "expected": str(expected),
        "checked_in": str(checked_in),
        "paper": str(paper),
        "sha256": sha256(expected),
        "commands": len(names),
        "referenced_commands": len(referenced),
        "required_prefixes": list(REQUIRED_RESULT_PREFIXES),
        "byte_identical": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--checked-in", type=Path, required=True)
    parser.add_argument("--paper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = verify(args.expected, args.checked_in, args.paper)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
