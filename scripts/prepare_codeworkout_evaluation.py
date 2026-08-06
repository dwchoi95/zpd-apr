#!/usr/bin/env python3
"""Prepare isolated Java harnesses for CodeWorkout repair generations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


Row = dict[str, Any]
METHODS = {
    1: "sortaSum", 3: "in1To10", 5: "answerCell", 12: "squirrelPlay",
    13: "caughtSpeeding", 17: "redTicket", 20: "loneSum", 21: "luckySum",
    22: "noTeenSum", 24: "blackjack", 25: "evenlySpaced", 34: "zipZap",
    37: "endOther", 39: "xyBalance", 40: "getSandwich", 46: "isEverywhere",
    71: "canBalance",
}


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def clean_fenced(code: str) -> str:
    match = re.search(r"```(?:java)?\s*(.*?)```", code, re.DOTALL | re.IGNORECASE)
    return (match.group(1) if match else code).strip()


def official_cases(main_csv: Path, q37_csv: Path) -> dict[int, list[tuple[str, str]]]:
    cases: dict[int, list[tuple[str, str]]] = defaultdict(list)
    with main_csv.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            raw_problem = row.get("coding_prompt_id", "")
            if not raw_problem:
                continue
            problem = int(float(raw_problem))
            if problem not in METHODS or problem == 37:
                continue
            argument = row["input"]
            if problem in {34, 39, 40}:
                argument = argument.rstrip('"').replace("\\", '"')
            expected = row["expected_output"]
            if problem in {34, 40}:
                expected = expected.rstrip('"').replace("\\", "")
            cases[problem].append((argument, expected.lower() if problem == 39 else expected))
    with q37_csv.open(encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            values = [row["input_1"]]
            if row.get("input_2"):
                values.append(row["input_2"])
            joined = ", ".join(values).rstrip('"').replace("\\", "")
            cases[37].append((f'"{joined}"', row["expected_output"].lower()))
    missing = set(METHODS) - set(cases)
    if missing:
        raise ValueError(f"official test cases missing problems: {sorted(missing)}")
    return dict(cases)


def java_source(code: str, method: str, cases: list[tuple[str, str]]) -> str:
    code = clean_fenced(code)
    class_match = re.search(r"\b(?:public\s+)?class\s+([A-Za-z_$][\w$]*)", code)
    if class_match:
        original = class_match.group(1)
        candidate = re.sub(
            rf"\bpublic\s+class\s+{re.escape(original)}\b",
            "class Candidate",
            code,
            count=1,
        )
        if candidate == code:
            candidate = re.sub(
                rf"\bclass\s+{re.escape(original)}\b", "class Candidate", code, count=1
            )
        candidate = re.sub(rf"\b{re.escape(original)}\s*\(", "Candidate(", candidate)
    else:
        candidate = f"class Candidate {{\n{code}\n}}"
    calls = "\n".join(
        f'System.out.println("__ZPD_CASE_{index:04d}__" + String.valueOf(obj.{method}({argument})));'
        for index, (argument, _expected) in enumerate(cases, start=1)
    )
    return (
        f"{candidate}\n"
        "public class Main {\n"
        "  public static void main(String[] args) throws Exception {\n"
        "    Candidate obj = new Candidate();\n"
        f"    {calls}\n"
        "  }\n"
        "}\n"
    )


def prepare(dataset: list[Row], generations: list[Row], cases: dict[int, list[tuple[str, str]]], output: Path) -> Row:
    generation_by_id = {str(row["example_id"]): row for row in generations}
    if len(generation_by_id) != len(generations):
        raise ValueError("duplicate generation example_id")
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for record in dataset:
        example_id = str(record["example_id"])
        generation = generation_by_id.get(example_id)
        if generation is None:
            raise ValueError(f"missing generation: {example_id}")
        problem = int(str(record["problem_id"]).removeprefix("cw"))
        slug = hashlib.sha256(example_id.encode()).hexdigest()[:24]
        (output / f"{slug}.java").write_text(
            java_source(str(generation["generated_code"]), METHODS[problem], cases[problem]),
            encoding="utf-8",
        )
        current = record["history"][-1]
        manifest.append(
            {
                "slug": slug,
                "example_id": example_id,
                "problem_id": record["problem_id"],
                "user_id": record["user_id"],
                "expected": [expected for _argument, expected in cases[problem]],
                "current_tc_outcomes": current["tc_outcomes"],
                "current_pass_rate": current["pass_rate"],
            }
        )
    manifest_path = output.parent / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as destination:
        for row in manifest:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"examples": len(manifest), "sources": str(output), "manifest": str(manifest_path)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("generations", type=Path)
    parser.add_argument("testcases", type=Path)
    parser.add_argument("problem37_testcases", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = prepare(
        read_jsonl(args.dataset),
        read_jsonl(args.generations),
        official_cases(args.testcases, args.problem37_testcases),
        args.output,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
