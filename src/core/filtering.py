from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .outcomes import load_outcome_cache


@dataclass(frozen=True)
class RQ1FilterSummary:
    input_examples: int
    written_examples: int
    excluded_missing_outcome: int
    excluded_buggy_already_accepted: int
    excluded_oracle_not_accepted: int
    output_path: Path


@dataclass(frozen=True)
class RepairSampleSummary:
    input_examples: int
    input_problems: int
    written_examples: int
    written_problems: int
    size: int
    seed: int
    output_path: Path


def sample_repair_examples(
    dataset_path: Path,
    output_path: Path,
    *,
    size: int,
    seed: int = 2027,
) -> RepairSampleSummary:
    if size < 1:
        raise ValueError("size must be positive")
    records = list(_iter_jsonl(dataset_path))
    by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_problem[str(record["problem_id"])].append(record)

    rng = random.Random(seed)
    problems = sorted(by_problem)
    rng.shuffle(problems)
    for problem_records in by_problem.values():
        problem_records.sort(key=lambda item: str(item["example_id"]))
        rng.shuffle(problem_records)

    selected: list[dict[str, Any]] = []
    active = list(problems)
    while active and len(selected) < size:
        remaining: list[str] = []
        for problem_id in active:
            if len(selected) >= size:
                break
            problem_records = by_problem[problem_id]
            if problem_records:
                selected.append(problem_records.pop())
            if problem_records:
                remaining.append(problem_id)
        active = remaining

    selected.sort(key=lambda item: (str(item["problem_id"]), str(item["example_id"])))
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for record in selected:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary = RepairSampleSummary(
        input_examples=len(records),
        input_problems=len(by_problem),
        written_examples=len(selected),
        written_problems=len({str(item["problem_id"]) for item in selected}),
        size=size,
        seed=seed,
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def filter_rq1_examples(
    dataset_path: Path,
    outcome_cache_path: Path,
    output_path: Path,
) -> RQ1FilterSummary:
    outcomes = load_outcome_cache(outcome_cache_path)
    execution_complete = _is_complete_outcome_cache(outcome_cache_path)
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = {
        "input": 0,
        "written": 0,
        "missing": 0,
        "buggy_ac": 0,
        "oracle_non_ac": 0,
    }
    with output_path.open("w", encoding="utf-8") as output:
        for record in _iter_jsonl(dataset_path):
            counts["input"] += 1
            problem_id = str(record["problem_id"])
            buggy_id = str(record["history"][-1]["submission_id"])
            oracle_id = str(record["target_submission_id"])
            buggy = outcomes.get((problem_id, buggy_id))
            oracle = outcomes.get((problem_id, oracle_id))
            if buggy is None or oracle is None:
                counts["missing"] += 1
                continue
            if str(buggy.get("execution_verdict")) == "AC":
                counts["buggy_ac"] += 1
                continue
            if str(oracle.get("execution_verdict")) != "AC":
                counts["oracle_non_ac"] += 1
                continue
            enriched = dict(record)
            enriched.update(
                {
                    "current_execution_verdict": buggy["execution_verdict"],
                    "current_pass_rate": buggy["pass_rate"],
                    "current_passed_testcases": buggy["passed_testcases"],
                    "current_tc_outcomes": buggy["tc_outcomes"],
                    "current_execution_complete": execution_complete,
                    "target_execution_verdict": oracle["execution_verdict"],
                    "target_pass_rate": oracle["pass_rate"],
                    "target_passed_testcases": oracle["passed_testcases"],
                    "target_tc_outcomes": oracle["tc_outcomes"],
                }
            )
            output.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            counts["written"] += 1

    summary = RQ1FilterSummary(
        input_examples=counts["input"],
        written_examples=counts["written"],
        excluded_missing_outcome=counts["missing"],
        excluded_buggy_already_accepted=counts["buggy_ac"],
        excluded_oracle_not_accepted=counts["oracle_non_ac"],
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _is_complete_outcome_cache(path: Path) -> bool:
    summary_path = path.expanduser().resolve().with_suffix(".summary.json")
    if not summary_path.is_file():
        return False
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return summary.get("outcome_cache_complete") is True


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
