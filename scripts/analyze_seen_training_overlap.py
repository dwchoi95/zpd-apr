#!/usr/bin/env python3
"""Aggregate same-problem training-target overlap without emitting source code."""

from __future__ import annotations

import argparse
import ast
import difflib
import io
import json
import tokenize
import warnings
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any


Row = dict[str, Any]


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def keyed(rows: list[Row]) -> dict[str, Row]:
    result = {str(row["example_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError("duplicate example_id")
    return result


def structural_form(code: str) -> str:
    code = code.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(code)
        return ast.dump(tree, annotate_fields=True, include_attributes=False)
    except (SyntaxError, ValueError, TypeError):
        return " ".join(code.split())


def lexical_tokens(code: str) -> tuple[str, ...]:
    try:
        return tuple(
            token.string
            for token in tokenize.generate_tokens(io.StringIO(code).readline)
            if token.type
            not in {
                tokenize.COMMENT,
                tokenize.NL,
                tokenize.NEWLINE,
                tokenize.INDENT,
                tokenize.DEDENT,
                tokenize.ENDMARKER,
                tokenize.ENCODING,
            }
        )
    except (IndentationError, tokenize.TokenError):
        return tuple(" ".join(code.split()).split(" "))


def summarize(rows: list[Row]) -> dict[str, Any]:
    if not rows:
        return {"examples": 0}
    similarities = [float(row["max_same_problem_token_similarity"]) for row in rows]
    return {
        "examples": len(rows),
        "repaired": sum(bool(row["repaired"]) for row in rows),
        "repair_rate": sum(bool(row["repaired"]) for row in rows) / len(rows),
        "exact_same_problem_train_target": sum(
            bool(row["exact_same_problem_train_target"]) for row in rows
        ),
        "exact_same_problem_train_target_rate": sum(
            bool(row["exact_same_problem_train_target"]) for row in rows
        )
        / len(rows),
        "exact_other_user_train_target": sum(
            bool(row["exact_other_user_train_target"]) for row in rows
        ),
        "exact_own_heldout_oracle": sum(bool(row["exact_own_heldout_oracle"]) for row in rows),
        "token_similarity_at_least_0_90": sum(value >= 0.90 for value in similarities),
        "token_similarity_at_least_0_95": sum(value >= 0.95 for value in similarities),
        "median_max_same_problem_token_similarity": median(similarities),
        "mean_max_same_problem_token_similarity": sum(similarities) / len(similarities),
    }


def audit(
    training: list[Row],
    dataset: list[Row],
    selected: list[Row],
    sources: dict[str, list[Row]],
) -> dict[str, Any]:
    selected_map = keyed(selected)
    source_maps = {name: keyed(rows) for name, rows in sources.items()}
    if set(selected_map) != {str(row["example_id"]) for row in dataset}:
        raise ValueError("selected portfolio does not cover the dataset")
    pools: dict[str, list[tuple[str, str, tuple[str, ...]]]] = defaultdict(list)
    for row in training:
        code = str(row["target_code"])
        pools[str(row["problem_id"])].append(
            (str(row["user_id"]), structural_form(code), lexical_tokens(code))
        )
    details: list[Row] = []
    for record in dataset:
        example_id = str(record["example_id"])
        choice = selected_map[example_id]
        source = str(choice.get("selected_source", "current-fallback"))
        generated = source != "current-fallback"
        if generated:
            if source not in source_maps or example_id not in source_maps[source]:
                raise ValueError(f"missing selected source {source} for {example_id}")
            code = str(source_maps[source][example_id]["generated_code"])
        else:
            code = str(record["history"][-1]["code"])
        problem_id = str(record["problem_id"])
        user_id = str(record["user_id"])
        pool = pools.get(problem_id, [])
        if not pool:
            raise ValueError(f"Seen problem has no Answer training target: {problem_id}")
        form = structural_form(code)
        tokens = lexical_tokens(code)
        ratios = [
            difflib.SequenceMatcher(None, tokens, train_tokens, autojunk=False).ratio()
            for _train_user, _train_form, train_tokens in pool
        ]
        details.append(
            {
                "example_id": example_id,
                "problem_id": problem_id,
                "selected_source": source,
                "selected_generated_candidate": generated,
                "repaired": bool(choice["repaired"]),
                "exact_same_problem_train_target": any(form == item[1] for item in pool),
                "exact_other_user_train_target": any(
                    form == train_form and user_id != train_user
                    for train_user, train_form, _tokens in pool
                ),
                "exact_own_heldout_oracle": form
                == structural_form(str(record["target_code"])),
                "max_same_problem_token_similarity": max(ratios),
            }
        )
    generated_rows = [row for row in details if row["selected_generated_candidate"]]
    exact = [row for row in generated_rows if row["exact_same_problem_train_target"]]
    nonexact = [row for row in generated_rows if not row["exact_same_problem_train_target"]]
    near = [row for row in generated_rows if row["max_same_problem_token_similarity"] >= 0.95]
    nonnear = [row for row in generated_rows if row["max_same_problem_token_similarity"] < 0.95]
    return {
        "scope": "aggregate code-overlap audit; no source code is emitted",
        "interpretation": "overlap is compatible with memorization but cannot distinguish memorization from convergent solutions",
        "training_examples": len(training),
        "training_problems": len(pools),
        "all_returned": summarize(details),
        "selected_generated": summarize(generated_rows),
        "selected_generated_repaired": summarize(
            [row for row in generated_rows if row["repaired"]]
        ),
        "selected_generated_unrepaired": summarize(
            [row for row in generated_rows if not row["repaired"]]
        ),
        "current_fallback": summarize(
            [row for row in details if not row["selected_generated_candidate"]]
        ),
        "repair_rate_by_exact_overlap": {
            "exact": summarize(exact),
            "nonexact": summarize(nonexact),
        },
        "repair_rate_by_near_overlap_0_95": {
            "near": summarize(near),
            "nonnear": summarize(nonnear),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("train_answer", type=Path)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("selected", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", action="append", required=True)
    args = parser.parse_args()
    sources: dict[str, list[Row]] = {}
    for value in args.source:
        if "=" not in value:
            parser.error("--source must use NAME=PATH")
        name, path = value.split("=", 1)
        sources[name] = read_jsonl(Path(path))
    result = audit(
        read_jsonl(args.train_answer),
        read_jsonl(args.dataset),
        read_jsonl(args.selected),
        sources,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
