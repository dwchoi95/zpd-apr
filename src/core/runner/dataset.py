from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from .models import SubmissionOutcome, TestCase
from .python_runner import PythonSubmissionRunner


@dataclass(frozen=True)
class ProblemBundle:
    problem_id: str
    problem_dir: Path
    testcases: list[TestCase]
    submissions: dict[str, dict[str, Any]]


def load_problem_bundle(problem_dir: Path) -> ProblemBundle:
    submissions_dir = problem_dir / "submissions"
    if not submissions_dir.is_dir():
        raise FileNotFoundError(f"submissions directory not found: {submissions_dir}")

    testcases = load_testcases(problem_dir / "testcases.jsonl")
    submissions = {}
    for user_path in sorted(submissions_dir.glob("*.jsonl")):
        for record in iter_jsonl(user_path):
            submissions[record["submission_id"]] = record
    return ProblemBundle(
        problem_id=problem_dir.name,
        problem_dir=problem_dir,
        testcases=testcases,
        submissions=submissions,
    )


def load_testcases(testcase_path: Path) -> list[TestCase]:
    if not testcase_path.exists():
        raise FileNotFoundError(f"testcases.jsonl not found: {testcase_path}")
    testcases = [
        TestCase(
            case_id=record["case_id"],
            input_text=record["input"],
            expected_text=record["expected_output"],
        )
        for record in iter_jsonl(testcase_path)
    ]
    if not testcases:
        raise ValueError(f"no testcases found in {testcase_path}")
    return testcases


def run_problem_outcomes(
    problem_dir: Path,
    *,
    runner: PythonSubmissionRunner | None = None,
    output_root: Path = Path("outputs"),
    resume: bool = True,
) -> Path:
    """Run all Python submissions for one problem and write outcomes.jsonl."""

    bundle = load_problem_bundle(problem_dir)
    runner = runner or PythonSubmissionRunner()
    output_path = output_root / bundle.problem_id / "outcomes.jsonl"
    done = _read_done_submission_ids(output_path) if resume else set()

    submissions = [
        record
        for record in bundle.submissions.values()
        if record["submission_id"] not in done
    ]
    submissions.sort(key=lambda r: r["submission_id"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if resume else "w"
    with output_path.open(mode, encoding="utf-8") as out:
        for record in tqdm(submissions, desc=bundle.problem_id, unit="submission"):
            outcome = runner.run_submission(
                submission_id=record["submission_id"],
                problem_id=bundle.problem_id,
                code=record.get("code", ""),
                source_verdict=record.get("verdict"),
                testcases=bundle.testcases,
            )
            out.write(json.dumps(outcome.to_json(), ensure_ascii=False) + "\n")
            out.flush()

    return output_path


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def _read_done_submission_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done = set()
    for record in iter_jsonl(path):
        submission_id = record.get("submission_id")
        if submission_id:
            done.add(submission_id)
    return done
