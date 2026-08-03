from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from ..runner.dataset import load_testcases
from ..runner.python_runner import PythonSubmissionRunner
from .dataset import load_split_problem_ids, load_split_trajectory_ids


@dataclass(frozen=True)
class OutcomeCacheSummary:
    split: str
    problems: int
    submissions: int
    cached_before_run: int
    executed: int
    failures: int
    workers: int
    case_workers: int
    outcome_cache_complete: bool
    output_path: Path


def build_outcome_cache(
    data_root: Path,
    *,
    split: str,
    output_path: Path,
    workers: int = 24,
    case_workers: int = 1,
    timeout_sec: float = 2.5,
    resume: bool = True,
) -> OutcomeCacheSummary:
    """Execute each unique submission once and cache compact per-test outcomes."""

    data_root = data_root.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path = output_path.with_suffix(".summary.json")
    if resume and output_path.is_file() and summary_path.is_file():
        previous_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if previous_summary.get("outcome_cache_complete") is not True:
            raise ValueError(
                "Refusing to resume a legacy or incomplete testcase-limited cache; "
                "use a new output path."
            )
    problem_ids = load_split_problem_ids(data_root, split)
    trajectory_ids = load_split_trajectory_ids(data_root, split)
    loaded_existing = _load_existing(output_path) if resume else {}
    existing = {
        key: value
        for key, value in loaded_existing.items()
        if "cache_error" not in value
    }
    cached_before_run = len(existing)
    total_submissions = 0
    pending_groups: list[
        list[tuple[str, list[Any], dict[str, Any]]]
    ] = []
    for problem_id in problem_ids:
        problem_dir = data_root / problem_id
        testcases = load_testcases(problem_dir / "testcases.jsonl")
        if not testcases:
            continue
        submissions = _load_problem_submissions(
            problem_dir,
            allowed_user_ids=(
                trajectory_ids[problem_id] if trajectory_ids is not None else None
            ),
        )
        total_submissions += len(submissions)
        problem_pending = [
            (problem_id, testcases, record)
            for submission_id, record in submissions.items()
            if _cache_key(problem_id, submission_id) not in existing
        ]
        if problem_pending:
            pending_groups.append(problem_pending)
    pending: list[tuple[str, list[Any], dict[str, Any]]] = []
    active_groups = [iter(group) for group in pending_groups]
    while active_groups:
        next_groups = []
        for group in active_groups:
            try:
                pending.append(next(group))
            except StopIteration:
                continue
            next_groups.append(group)
        active_groups = next_groups
    pending_submissions = len(pending)

    runner = PythonSubmissionRunner(
        timeout_sec=timeout_sec,
        memory_limit_mb=2048,
        case_workers=case_workers,
    )

    def run_one(
        task: tuple[str, list[Any], dict[str, Any]],
    ) -> dict[str, Any]:
        problem_id, testcases, record = task
        submission_id = str(record["submission_id"])
        try:
            outcome = runner.run_submission(
                submission_id=submission_id,
                problem_id=problem_id,
                code=str(record.get("code", "")),
                source_verdict=str(record.get("verdict", "")),
                testcases=testcases,
            )
        except Exception as exc:  # keep a resumable record of rare runner failures
            return {
                "problem_id": problem_id,
                "submission_id": submission_id,
                "source_verdict": record.get("verdict"),
                "cache_error": f"{exc.__class__.__name__}: {exc}",
            }
        passed = [
            case.case_id for case in outcome.cases if case.verdict.value == "AC"
        ]
        return {
            "problem_id": problem_id,
            "submission_id": submission_id,
            "source_verdict": record.get("verdict"),
            "execution_verdict": outcome.verdict.value,
            "testcase_count": len(outcome.cases),
            "passed_testcases": passed,
            "pass_rate": len(passed) / len(outcome.cases) if outcome.cases else 0.0,
            "tc_outcomes": {
                case.case_id: case.verdict.value for case in outcome.cases
            },
        }

    executed = 0
    failures = 0
    mode = "a" if resume and output_path.exists() else "w"
    with output_path.open(mode, encoding="utf-8") as output, tqdm(
        total=pending_submissions,
        desc=f"Execute {split} submissions",
        unit="submission",
    ) as progress:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(run_one, task) for task in pending]
            for future in as_completed(futures):
                item = future.result()
                output.write(json.dumps(item, ensure_ascii=False) + "\n")
                output.flush()
                key = _cache_key(
                    str(item["problem_id"]),
                    str(item["submission_id"]),
                )
                existing[key] = item
                executed += 1
                failures += int("cache_error" in item)
                progress.update()

    summary = OutcomeCacheSummary(
        split=split,
        problems=len(problem_ids),
        submissions=total_submissions,
        cached_before_run=cached_before_run,
        executed=executed,
        failures=failures,
        workers=workers,
        case_workers=case_workers,
        outcome_cache_complete=True,
        output_path=output_path,
    )
    summary_path.write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def load_outcome_cache(path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    cache = _load_existing(path.expanduser().resolve())
    return {
        tuple(key.split(":", 1)): value
        for key, value in cache.items()
        if "cache_error" not in value
    }


def _load_problem_submissions(
    problem_dir: Path,
    *,
    allowed_user_ids: set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    submissions: dict[str, dict[str, Any]] = {}
    for trajectory_path in sorted((problem_dir / "submissions").glob("*.jsonl")):
        if (
            allowed_user_ids is not None
            and trajectory_path.stem not in allowed_user_ids
        ):
            continue
        records = list(_iter_jsonl(trajectory_path))
        for record in records:
            submissions[str(record["submission_id"])] = record
    return submissions


def _load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return {
        _cache_key(str(item["problem_id"]), str(item["submission_id"])): item
        for item in _iter_jsonl(path)
    }


def _cache_key(problem_id: str, submission_id: str) -> str:
    return f"{problem_id}:{submission_id}"


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
