#!/usr/bin/env python3
"""Build a leakage-auditable observed/hidden testcase evaluation split.

The generated dataset exposes execution feedback for the observed testcase
partition only.  Candidate selection must use the observed data root; the
hidden root is reserved for the final, independently executed assessment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


Row = dict[str, Any]
VERDICT_ORDER = ("CE", "TLE", "RE", "WA")
DISPLAY_VERDICT = {
    "AC": "Accepted",
    "WA": "Wrong Answer",
    "RE": "Runtime Error",
    "TLE": "Time Limit Exceeded",
    "CE": "Compilation Error",
}


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def write_jsonl(path: Path, rows: list[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as destination:
        for row in rows:
            destination.write(json.dumps(row, ensure_ascii=False) + "\n")


def partition_testcases(
    rows: list[Row], *, problem_id: str, seed: int
) -> tuple[list[Row], list[Row]]:
    if len(rows) < 2:
        raise ValueError(f"{problem_id} needs at least two testcases")
    ordered = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f"{seed}:{problem_id}:{row['case_id']}".encode()
        ).digest(),
    )
    observed_count = (len(ordered) + 1) // 2
    return ordered[:observed_count], ordered[observed_count:]


def aggregate_verdict(outcomes: dict[str, Any]) -> str:
    values = {str(value) for value in outcomes.values()}
    for verdict in VERDICT_ORDER:
        if verdict in values:
            return verdict
    return "AC"


def restrict_execution_feedback(row: Row, observed_ids: set[str]) -> None:
    outcomes = row.get("tc_outcomes")
    if not isinstance(outcomes, dict):
        return
    restricted = {
        str(case_id): str(verdict)
        for case_id, verdict in outcomes.items()
        if str(case_id) in observed_ids
    }
    if not restricted:
        raise ValueError("execution feedback has no observed testcase")
    passed = sorted(
        case_id for case_id, verdict in restricted.items() if verdict == "AC"
    )
    row["tc_outcomes"] = restricted
    row["passed_testcases"] = passed
    row["pass_rate"] = len(passed) / len(restricted)
    execution_verdict = aggregate_verdict(restricted)
    row["execution_verdict"] = execution_verdict
    # The prompt renders this field separately from execution_verdict. Leaving
    # the original online-judge verdict would leak an aggregate of hidden cases.
    row["verdict"] = DISPLAY_VERDICT[execution_verdict]
    row["execution_complete"] = False


def restrict_record(record: Row, observed_ids: set[str]) -> Row:
    result = json.loads(json.dumps(record))
    for submission in result.get("history", []):
        restrict_execution_feedback(submission, observed_ids)
    for prefix in ("current", "target"):
        outcomes_key = f"{prefix}_tc_outcomes"
        outcomes = result.get(outcomes_key)
        if not isinstance(outcomes, dict):
            continue
        restricted = {
            str(case_id): str(verdict)
            for case_id, verdict in outcomes.items()
            if str(case_id) in observed_ids
        }
        passed = sorted(
            case_id for case_id, verdict in restricted.items() if verdict == "AC"
        )
        result[outcomes_key] = restricted
        result[f"{prefix}_passed_testcases"] = passed
        result[f"{prefix}_pass_rate"] = len(passed) / len(restricted)
        result[f"{prefix}_execution_verdict"] = aggregate_verdict(restricted)
    result["execution_complete"] = False
    result["evaluation_test_partition"] = "observed"
    result["original_coarse_verdict_hidden"] = True
    return result


def build(
    data_root: Path,
    dataset_path: Path,
    output_dataset: Path,
    observed_root: Path,
    hidden_root: Path,
    manifest_path: Path,
    *,
    seed: int,
) -> dict[str, Any]:
    records = read_jsonl(dataset_path)
    problem_ids = sorted({str(row["problem_id"]) for row in records})
    manifest: list[Row] = []
    observed_by_problem: dict[str, set[str]] = {}
    total_observed = total_hidden = 0
    for problem_id in problem_ids:
        source_dir = data_root / problem_id
        testcases = read_jsonl(source_dir / "testcases.jsonl")
        observed, hidden = partition_testcases(
            testcases, problem_id=problem_id, seed=seed
        )
        observed_ids = {str(row["case_id"]) for row in observed}
        hidden_ids = {str(row["case_id"]) for row in hidden}
        if observed_ids & hidden_ids or observed_ids | hidden_ids != {
            str(row["case_id"]) for row in testcases
        }:
            raise AssertionError(f"invalid partition for {problem_id}")
        observed_by_problem[problem_id] = observed_ids
        write_jsonl(observed_root / problem_id / "testcases.jsonl", observed)
        write_jsonl(hidden_root / problem_id / "testcases.jsonl", hidden)
        for name in ("metadata.json", "description.html"):
            source = source_dir / name
            if source.is_file():
                for destination_root in (observed_root, hidden_root):
                    destination = destination_root / problem_id / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
        manifest.append(
            {
                "problem_id": problem_id,
                "seed": seed,
                "observed_case_ids": sorted(observed_ids),
                "hidden_case_ids": sorted(hidden_ids),
                "observed_count": len(observed),
                "hidden_count": len(hidden),
            }
        )
        total_observed += len(observed)
        total_hidden += len(hidden)

    restricted = [
        restrict_record(row, observed_by_problem[str(row["problem_id"])])
        for row in records
    ]
    write_jsonl(output_dataset, restricted)
    write_jsonl(manifest_path, manifest)
    summary = {
        "source_dataset": str(dataset_path),
        "output_dataset": str(output_dataset),
        "seed": seed,
        "examples": len(records),
        "problems": len(problem_ids),
        "observed_testcases": total_observed,
        "hidden_testcases": total_hidden,
        "minimum_observed_per_problem": min(row["observed_count"] for row in manifest),
        "minimum_hidden_per_problem": min(row["hidden_count"] for row in manifest),
        "partition_hash": hashlib.sha256(
            "\n".join(
                f"{row['problem_id']}:{','.join(row['observed_case_ids'])}|{','.join(row['hidden_case_ids'])}"
                for row in manifest
            ).encode()
        ).hexdigest(),
        "observed_feedback_only": True,
        "coarse_verdict_recomputed_from_observed": True,
    }
    manifest_path.with_suffix(".summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("data_root", type=Path)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_dataset", type=Path)
    parser.add_argument("observed_root", type=Path)
    parser.add_argument("hidden_root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--seed", type=int, default=2027)
    args = parser.parse_args()
    summary = build(
        args.data_root,
        args.dataset,
        args.output_dataset,
        args.observed_root,
        args.hidden_root,
        args.manifest,
        seed=args.seed,
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
