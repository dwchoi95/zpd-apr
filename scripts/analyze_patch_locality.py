#!/usr/bin/env python3
"""Audit source preservation with token and non-empty-line retention."""

from __future__ import annotations

import argparse
import difflib
import io
import json
import random
import tokenize
from collections import defaultdict
from pathlib import Path
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def source_tokens(code: str) -> list[str]:
    ignored = {
        tokenize.ENCODING,
        tokenize.ENDMARKER,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.NEWLINE,
        tokenize.NL,
    }
    try:
        return [
            token.string
            for token in tokenize.generate_tokens(io.StringIO(code).readline)
            if token.type not in ignored and token.string.strip()
        ]
    except (IndentationError, tokenize.TokenError):
        return code.split()


def retained_fraction(source: list[str], candidate: list[str]) -> float:
    if not source:
        return 1.0 if not candidate else 0.0
    matcher = difflib.SequenceMatcher(None, source, candidate, autojunk=False)
    retained = sum(block.size for block in matcher.get_matching_blocks())
    return retained / len(source)


def locality(source: str, candidate: str) -> dict[str, float]:
    source_lines = [line.strip() for line in source.splitlines() if line.strip()]
    candidate_lines = [line.strip() for line in candidate.splitlines() if line.strip()]
    return {
        "token_retention": retained_fraction(source_tokens(source), source_tokens(candidate)),
        "line_retention": retained_fraction(source_lines, candidate_lines),
    }


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(quantile * len(ordered)))]


def paired_locality(
    left: dict[str, Row],
    right: dict[str, Row],
    source: dict[str, str],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    shared = sorted(set(left) & set(right) & set(source))
    joint = [key for key in shared if bool(left[key]["repaired"]) and bool(right[key]["repaired"])]
    values: dict[str, list[tuple[float, str]]] = {"token_retention": [], "line_retention": []}
    for key in joint:
        left_values = locality(source[key], str(left[key]["generated_code"]))
        right_values = locality(source[key], str(right[key]["generated_code"]))
        problem = str(left[key]["problem_id"])
        for metric in values:
            values[metric].append((left_values[metric] - right_values[metric], problem))
    result = {"joint_repairs": len(joint), "metrics": {}}
    for offset, (metric, pairs) in enumerate(values.items()):
        observed = sum(value for value, _problem in pairs) / len(pairs)
        by_problem: dict[str, list[float]] = defaultdict(list)
        for value, problem in pairs:
            by_problem[problem].append(value)
        problems = sorted(by_problem)
        rng = random.Random(seed + offset)
        instance_draws = []
        cluster_draws = []
        for _ in range(samples):
            instance_draws.append(
                sum(rng.choice(pairs)[0] for _item in pairs) / len(pairs)
            )
            chosen = [rng.choice(problems) for _problem in problems]
            replicated = [value for problem in chosen for value in by_problem[problem]]
            cluster_draws.append(sum(replicated) / len(replicated))
        result["metrics"][metric] = {
            "left_minus_right": observed,
            "instance_bootstrap_95ci": [
                percentile(instance_draws, 0.025),
                percentile(instance_draws, 0.975),
            ],
            "problem_cluster_bootstrap_95ci": [
                percentile(cluster_draws, 0.025),
                percentile(cluster_draws, 0.975),
            ],
        }
    return result


def resolve_generated_codes(
    evaluations: dict[str, dict[str, Row]],
    candidates: dict[str, dict[str, Row]],
    source: dict[str, str],
) -> None:
    for rows in evaluations.values():
        for example_id, row in rows.items():
            if row.get("generated_code") is not None:
                continue
            selected = str(row.get("selected_source", ""))
            if selected == "current-fallback":
                row["generated_code"] = source[example_id]
            elif selected in candidates and example_id in candidates[selected]:
                row["generated_code"] = candidates[selected][example_id]["generated_code"]
            else:
                raise ValueError(
                    f"cannot resolve generated_code for {example_id} from {selected}"
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--evaluation", action="append", required=True, help="NAME=PATH")
    parser.add_argument("--candidate", action="append", default=[], help="SOURCE=PATH")
    parser.add_argument("--pair", action="append", required=True, help="LEFT,RIGHT")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-samples", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    dataset = read_jsonl(args.dataset)
    source = {str(row["example_id"]): str(row["history"][-1]["code"]) for row in dataset}
    evaluations = {}
    for raw in args.evaluation:
        if "=" not in raw:
            parser.error("--evaluation must use NAME=PATH")
        name, path = raw.split("=", 1)
        rows = read_jsonl(Path(path))
        evaluations[name] = {str(row["example_id"]): row for row in rows}
    candidates = {}
    for raw in args.candidate:
        if "=" not in raw:
            parser.error("--candidate must use SOURCE=PATH")
        name, path = raw.split("=", 1)
        rows = read_jsonl(Path(path))
        candidates[name] = {str(row["example_id"]): row for row in rows}
    try:
        resolve_generated_codes(evaluations, candidates, source)
    except ValueError as error:
        parser.error(str(error))
    comparisons = {}
    for offset, raw in enumerate(args.pair):
        if "," not in raw:
            parser.error("--pair must use LEFT,RIGHT")
        left, right = raw.split(",", 1)
        if left not in evaluations or right not in evaluations:
            parser.error("--pair names must be declared by --evaluation")
        comparisons[f"{left}_minus_{right}"] = paired_locality(
            evaluations[left],
            evaluations[right],
            source,
            samples=args.bootstrap_samples,
            seed=args.seed + 10 * offset,
        )
    result = {
        "dataset": str(args.dataset),
        "higher_is_more_source_preservation": True,
        "comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(comparisons, sort_keys=True))


if __name__ == "__main__":
    main()
