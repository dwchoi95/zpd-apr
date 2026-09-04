#!/usr/bin/env python3
"""Build a same-source control whose Progress targets come from other users.

The control holds the current program and target execution evidence fixed.  It
then chooses, from another user on the same problem, the target whose semantic
token-diff distance from the focal current program is closest to the original
same-user target.  The resulting pair isolates user-trajectory provenance from
target outcome and lexical edit distance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import io
import statistics
import tokenize
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

Row = dict[str, Any]
Distance = Callable[[str, str], int | None]
TARGET_FIELDS = (
    "target_code",
    "target_submission_id",
    "target_verdict",
    "target_execution_verdict",
    "target_pass_rate",
    "target_passed_testcases",
    "target_tc_outcomes",
)


@lru_cache(maxsize=100_000)
def code_tokens(code: str) -> tuple[tuple[int, str], ...]:
    """Return semantic Python tokens while ignoring layout and comments."""

    ignored = {
        tokenize.ENCODING,
        tokenize.NL,
        tokenize.NEWLINE,
        tokenize.INDENT,
        tokenize.DEDENT,
        tokenize.ENDMARKER,
        tokenize.COMMENT,
    }
    try:
        stream = tokenize.generate_tokens(io.StringIO(code).readline)
        return tuple((item.type, item.string) for item in stream if item.type not in ignored)
    except (IndentationError, SyntaxError, tokenize.TokenError):
        # Compilation-error submissions remain valid repair sources.  A
        # deterministic character fallback keeps them in the matched design.
        return tuple((-1, character) for character in code)


def token_edit_distance(before: str, after: str) -> int:
    """Deterministic token-diff distance induced by SequenceMatcher opcodes."""

    left, right = code_tokens(before), code_tokens(after)
    distance = 0
    for tag, i1, i2, j1, j2 in SequenceMatcher(
        None, left, right, autojunk=False
    ).get_opcodes():
        if tag == "replace":
            distance += max(i2 - i1, j2 - j1)
        elif tag == "delete":
            distance += i2 - i1
        elif tag == "insert":
            distance += j2 - j1
    return distance


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def evidence_signature(row: Row) -> str:
    """Canonical target-evidence signature used for exact matching."""

    evidence = {
        "execution_verdict": row.get("target_execution_verdict"),
        "pass_rate": row.get("target_pass_rate"),
        "passed_testcases": sorted(map(str, row.get("target_passed_testcases", []))),
        "tc_outcomes": {
            str(key): str(value)
            for key, value in sorted(dict(row.get("target_tc_outcomes", {})).items())
        },
    }
    return json.dumps(evidence, sort_keys=True, separators=(",", ":"))


def current_code(row: Row) -> str:
    history = list(row.get("history", []))
    if not history:
        raise ValueError(f"empty history: {row.get('example_id')}")
    return str(history[-1]["code"])


def current_only(row: Row, example_id: str) -> Row:
    result = dict(row)
    current = dict(result["history"][-1])
    current["position"] = 1
    result["history"] = [current]
    result["target_position"] = 2
    result["example_id"] = example_id
    return result


def cross_user_record(source: Row, candidate: Row, example_id: str) -> Row:
    result = current_only(source, example_id)
    for field in TARGET_FIELDS:
        result[field] = candidate.get(field)
    result["matched_target_user_id"] = str(candidate["user_id"])
    result["matched_target_source_example_id"] = str(candidate["example_id"])
    result["matched_target_original_position"] = candidate.get(
        "original_target_position", candidate.get("target_position")
    )
    return result


def write_jsonl(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")


def build(
    source_path: Path,
    same_user_output: Path,
    cross_user_output: Path,
    *,
    maximum_target_reuse: int = 3,
    distance_fn: Distance = token_edit_distance,
    shard_count: int = 1,
    shard_index: int = 0,
    maximum_absolute_distance_difference: int = 2,
    maximum_relative_distance_difference: float = 0.10,
) -> dict[str, Any]:
    if maximum_target_reuse < 1:
        raise ValueError("maximum_target_reuse must be positive")
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("shard_index must be in [0, shard_count)")
    all_rows = read_jsonl(source_path)
    rows = [
        row
        for row in all_rows
        if int(hashlib.sha256(str(row["problem_id"]).encode()).hexdigest()[:16], 16)
        % shard_count
        == shard_index
    ]
    pools: dict[tuple[str, str], list[Row]] = defaultdict(list)
    for row in rows:
        pools[(str(row["problem_id"]), evidence_signature(row))].append(row)

    # Scarce evidence groups are matched first so that the reuse cap does not
    # preferentially remove rare execution outcomes.
    ordered = sorted(
        rows,
        key=lambda row: (
            len(pools[(str(row["problem_id"]), evidence_signature(row))]),
            str(row["problem_id"]),
            str(row["example_id"]),
        ),
    )
    reuse: Counter[str] = Counter()
    own_distance_cache: dict[str, int | None] = {}
    candidate_distance_cache: dict[tuple[str, str], int | None] = {}
    same_rows: list[Row] = []
    cross_rows: list[Row] = []
    deltas: list[int] = []
    unmatched_no_cross_user = 0
    unmatched_invalid_distance = 0
    unmatched_reuse_cap = 0
    unmatched_distance_caliper = 0

    for source in ordered:
        source_id = str(source["example_id"])
        source_code = current_code(source)
        own_distance = own_distance_cache.setdefault(
            source_id, distance_fn(source_code, str(source["target_code"]))
        )
        if own_distance is None:
            unmatched_invalid_distance += 1
            continue
        candidates = [
            candidate
            for candidate in pools[(str(source["problem_id"]), evidence_signature(source))]
            if str(candidate["user_id"]) != str(source["user_id"])
            and str(candidate["target_submission_id"])
            != str(source["target_submission_id"])
        ]
        if not candidates:
            unmatched_no_cross_user += 1
            continue
        best: tuple[int, int, str, Row] | None = None
        valid_candidate_seen = False
        for candidate in sorted(
            candidates,
            key=lambda item: (
                reuse[str(item["target_submission_id"])],
                str(item["target_submission_id"]),
            ),
        ):
            target_id = str(candidate["target_submission_id"])
            if reuse[target_id] >= maximum_target_reuse:
                continue
            cache_key = (source_id, target_id)
            if cache_key not in candidate_distance_cache:
                candidate_distance_cache[cache_key] = distance_fn(
                    source_code, str(candidate["target_code"])
                )
            candidate_distance = candidate_distance_cache[cache_key]
            if candidate_distance is None:
                continue
            valid_candidate_seen = True
            score = (
                abs(candidate_distance - own_distance),
                reuse[target_id],
                target_id,
                candidate,
            )
            if best is None or score[:3] < best[:3]:
                best = score
            # Zero is the global optimum for the distance-matching objective.
            # Stopping here avoids exhaustively comparing interchangeable
            # exact-outcome candidates in large per-problem pools.
            if score[0] == 0:
                break
        if best is None:
            if any(
                reuse[str(candidate["target_submission_id"])] >= maximum_target_reuse
                for candidate in candidates
            ) and not valid_candidate_seen:
                unmatched_reuse_cap += 1
            else:
                unmatched_invalid_distance += 1
            continue
        delta, _used, target_id, candidate = best
        matched_distance = candidate_distance_cache[(source_id, target_id)]
        assert matched_distance is not None
        if (
            delta > maximum_absolute_distance_difference
            and delta / max(1, own_distance) > maximum_relative_distance_difference
        ):
            unmatched_distance_caliper += 1
            continue
        reuse[target_id] += 1
        digest = hashlib.sha256(source_id.encode()).hexdigest()[:16]
        example_id = f"cross-user-target:{digest}"
        same = current_only(source, example_id)
        cross = cross_user_record(source, candidate, example_id)
        same["target_token_edit_distance"] = own_distance
        same["matched_target_token_edit_distance"] = matched_distance
        cross["target_token_edit_distance"] = own_distance
        cross["matched_target_token_edit_distance"] = matched_distance
        same_rows.append(same)
        cross_rows.append(cross)
        deltas.append(delta)

    # Restore a stable problem/example order for deterministic training input.
    paired = sorted(
        zip(same_rows, cross_rows),
        key=lambda pair: (str(pair[0]["problem_id"]), str(pair[0]["example_id"])),
    )
    same_rows = [pair[0] for pair in paired]
    cross_rows = [pair[1] for pair in paired]
    write_jsonl(same_user_output, same_rows)
    write_jsonl(cross_user_output, cross_rows)
    sorted_deltas = sorted(deltas)
    p95_index = max(0, int(0.95 * len(sorted_deltas) + 0.999999) - 1) if deltas else 0
    return {
        "input_examples": len(all_rows),
        "source_examples": len(rows),
        "shard_count": shard_count,
        "shard_index": shard_index,
        "matched_examples": len(same_rows),
        "matched_problems": len({str(row["problem_id"]) for row in same_rows}),
        "unmatched_no_cross_user_exact_evidence": unmatched_no_cross_user,
        "unmatched_invalid_token_distance": unmatched_invalid_distance,
        "unmatched_target_reuse_cap": unmatched_reuse_cap,
        "unmatched_distance_caliper": unmatched_distance_caliper,
        "maximum_target_reuse": maximum_target_reuse,
        "maximum_absolute_distance_difference": maximum_absolute_distance_difference,
        "maximum_relative_distance_difference": maximum_relative_distance_difference,
        "unique_cross_user_targets": len(reuse),
        "observed_maximum_target_reuse": max(reuse.values(), default=0),
        "exact_evidence_match": True,
        "exact_token_distance_matches": sum(delta == 0 for delta in deltas),
        "mean_absolute_token_distance_difference": statistics.fmean(deltas) if deltas else None,
        "median_absolute_token_distance_difference": statistics.median(deltas) if deltas else None,
        "p95_absolute_token_distance_difference": sorted_deltas[p95_index] if deltas else None,
        "same_user_output": str(same_user_output),
        "cross_user_output": str(cross_user_output),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("same_user_output", type=Path)
    parser.add_argument("cross_user_output", type=Path)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--maximum-target-reuse", type=int, default=3)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--maximum-absolute-distance-difference", type=int, default=2)
    parser.add_argument("--maximum-relative-distance-difference", type=float, default=0.10)
    args = parser.parse_args()
    result = build(
        args.source,
        args.same_user_output,
        args.cross_user_output,
        maximum_target_reuse=args.maximum_target_reuse,
        shard_count=args.shard_count,
        shard_index=args.shard_index,
        maximum_absolute_distance_difference=args.maximum_absolute_distance_difference,
        maximum_relative_distance_difference=args.maximum_relative_distance_difference,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
