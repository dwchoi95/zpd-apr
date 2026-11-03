from __future__ import annotations

import ast
import hashlib
import io
import json
import shutil
import tokenize
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tqdm import tqdm


@dataclass(frozen=True)
class RefinementSummary:
    original_problems: int
    removed_problems_without_testcases: int
    removed_problems_without_trajectories: int
    original_trajectories_in_testable_problems: int
    removed_invalid_trajectories: int
    minimum_problems_per_user: int
    unique_users_before_minimum_filter: int
    removed_users_below_minimum: int
    removed_trajectories_below_minimum: int
    remaining_problems: int
    remaining_users: int
    remaining_trajectories: int


@dataclass(frozen=True)
class TrajectoryRefinementSummary:
    original_problems: int
    original_users: int
    original_trajectories: int
    original_submissions: int
    removed_normalized_duplicates: int
    removed_without_non_accepted_before_accepted: int
    removed_after_first_accepted: int
    removed_below_minimum_trajectories: int
    removed_with_discarded_trajectories: int
    removed_empty_problems: int
    remaining_problems: int
    remaining_users: int
    remaining_trajectories: int
    remaining_submissions: int


@dataclass(frozen=True)
class BenchmarkAcceptanceSummary:
    original_problems: int
    original_users: int
    original_trajectories: int
    original_submissions: int
    removed_trajectories_not_in_benchmark: int
    removed_submissions: int
    removed_problems_below_minimum: int
    minimum_trajectories_per_problem: int
    remaining_problems: int
    remaining_users: int
    remaining_trajectories: int
    remaining_submissions: int


def refine_dataset(data_root: Path, *, min_problems_per_user: int = 1) -> RefinementSummary:
    if min_problems_per_user < 1:
        raise ValueError("min_problems_per_user must be at least 1")
    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = _find_problem_dirs(data_root)
    removed_without_testcases = 0
    removed_without_trajectories = 0
    original_trajectories = 0
    removed_invalid_trajectories = 0

    for problem_dir in tqdm(problem_dirs, desc="Refine CodeNet dataset", unit="problem"):
        testcases_path = problem_dir / "testcases.jsonl"
        if not testcases_path.is_file():
            raise FileNotFoundError(f"Missing testcases.jsonl: {testcases_path}")
        if testcases_path.stat().st_size == 0:
            shutil.rmtree(problem_dir)
            removed_without_testcases += 1
            continue

        submissions_dir = problem_dir / "submissions"
        if not submissions_dir.is_dir():
            raise FileNotFoundError(f"Missing submissions directory: {submissions_dir}")

        kept_in_problem = 0
        user_paths = sorted(submissions_dir.glob("*.jsonl"))
        original_trajectories += len(user_paths)
        for user_path in user_paths:
            if _is_valid_trajectory(user_path):
                kept_in_problem += 1
            else:
                user_path.unlink()
                removed_invalid_trajectories += 1

        if kept_in_problem == 0:
            shutil.rmtree(problem_dir)
            removed_without_trajectories += 1

    remaining_problem_dirs = _find_problem_dirs(data_root)
    user_problem_counts: Counter[str] = Counter()
    for problem_dir in remaining_problem_dirs:
        for user_path in (problem_dir / "submissions").glob("*.jsonl"):
            user_problem_counts[user_path.stem] += 1

    ineligible_users = {
        user_id
        for user_id, problem_count in user_problem_counts.items()
        if problem_count < min_problems_per_user
    }
    removed_below_minimum = 0
    for problem_dir in tqdm(
        remaining_problem_dirs,
        desc=f"Filter users with <{min_problems_per_user} problems",
        unit="problem",
    ):
        submissions_dir = problem_dir / "submissions"
        for user_path in submissions_dir.glob("*.jsonl"):
            if user_path.stem in ineligible_users:
                user_path.unlink()
                removed_below_minimum += 1
        if not any(submissions_dir.glob("*.jsonl")):
            shutil.rmtree(problem_dir)
            removed_without_trajectories += 1

    remaining_problems = (
        len(problem_dirs) - removed_without_testcases - removed_without_trajectories
    )
    remaining_trajectories = (
        original_trajectories
        - removed_invalid_trajectories
        - removed_below_minimum
    )

    return RefinementSummary(
        original_problems=len(problem_dirs),
        removed_problems_without_testcases=removed_without_testcases,
        removed_problems_without_trajectories=removed_without_trajectories,
        original_trajectories_in_testable_problems=original_trajectories,
        removed_invalid_trajectories=removed_invalid_trajectories,
        minimum_problems_per_user=min_problems_per_user,
        unique_users_before_minimum_filter=len(user_problem_counts),
        removed_users_below_minimum=len(ineligible_users),
        removed_trajectories_below_minimum=removed_below_minimum,
        remaining_problems=remaining_problems,
        remaining_users=len(user_problem_counts) - len(ineligible_users),
        remaining_trajectories=remaining_trajectories,
    )


def refine_submission_trajectories(
    data_root: Path,
    *,
    minimum_submissions: int = 3,
) -> TrajectoryRefinementSummary:
    """Keep normalized, pre-acceptance trajectories suitable for next-step learning."""

    if minimum_submissions < 2:
        raise ValueError("minimum_submissions must be at least 2")
    data_root = data_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")

    problem_dirs = _find_problem_dirs(data_root)
    original_users: set[str] = set()
    remaining_users: set[str] = set()
    original_trajectories = 0
    original_submissions = 0
    removed_normalized_duplicates = 0
    removed_without_ordered_acceptance = 0
    removed_after_first_accepted = 0
    removed_below_minimum = 0
    removed_with_discarded = 0
    remaining_trajectories = 0
    remaining_submissions = 0
    removed_empty_problems = 0

    for problem_dir in tqdm(
        problem_dirs,
        desc="Refine submission trajectories",
        unit="problem",
    ):
        submissions_dir = problem_dir / "submissions"
        if not submissions_dir.is_dir():
            raise FileNotFoundError(f"Missing submissions directory: {submissions_dir}")

        kept_in_problem = 0
        for user_path in sorted(submissions_dir.glob("*.jsonl")):
            records = _read_submission_records(user_path)
            original_users.add(user_path.stem)
            original_trajectories += 1
            original_submissions += len(records)

            collapsed, duplicate_count = _collapse_consecutive_normalized(records)
            removed_normalized_duplicates += duplicate_count

            first_accepted = next(
                (
                    index
                    for index, record in enumerate(collapsed)
                    if record.get("verdict") == "Accepted"
                ),
                None,
            )
            if first_accepted is None or first_accepted == 0:
                removed_without_ordered_acceptance += 1
                removed_with_discarded += len(collapsed)
                user_path.unlink()
                continue

            truncated = collapsed[: first_accepted + 1]
            removed_after_first_accepted += len(collapsed) - len(truncated)
            if len(truncated) < minimum_submissions:
                removed_below_minimum += 1
                removed_with_discarded += len(truncated)
                user_path.unlink()
                continue

            if _submission_ids(records) != _submission_ids(truncated):
                _write_submission_records(user_path, truncated)
            kept_in_problem += 1
            remaining_users.add(user_path.stem)
            remaining_trajectories += 1
            remaining_submissions += len(truncated)

        if kept_in_problem == 0:
            shutil.rmtree(problem_dir)
            removed_empty_problems += 1

    return TrajectoryRefinementSummary(
        original_problems=len(problem_dirs),
        original_users=len(original_users),
        original_trajectories=original_trajectories,
        original_submissions=original_submissions,
        removed_normalized_duplicates=removed_normalized_duplicates,
        removed_without_non_accepted_before_accepted=removed_without_ordered_acceptance,
        removed_after_first_accepted=removed_after_first_accepted,
        removed_below_minimum_trajectories=removed_below_minimum,
        removed_with_discarded_trajectories=removed_with_discarded,
        removed_empty_problems=removed_empty_problems,
        remaining_problems=len(problem_dirs) - removed_empty_problems,
        remaining_users=len(remaining_users),
        remaining_trajectories=remaining_trajectories,
        remaining_submissions=remaining_submissions,
    )


def filter_by_benchmark_accepted(
    data_root: Path,
    benchmark_root: Path,
    *,
    minimum_trajectories_per_problem: int = 2,
) -> BenchmarkAcceptanceSummary:
    """Keep trajectories whose final Accepted submission is in Python800."""

    if minimum_trajectories_per_problem < 1:
        raise ValueError("minimum_trajectories_per_problem must be at least 1")
    data_root = data_root.expanduser().resolve()
    benchmark_root = benchmark_root.expanduser().resolve()
    if not data_root.is_dir():
        raise FileNotFoundError(f"Dataset directory not found: {data_root}")
    if not benchmark_root.is_dir():
        raise FileNotFoundError(f"Benchmark directory not found: {benchmark_root}")

    problem_dirs = _find_problem_dirs(data_root)
    original_users: set[str] = set()
    remaining_users: set[str] = set()
    original_trajectories = 0
    original_submissions = 0
    removed_trajectories = 0
    removed_submissions = 0
    removed_problems = 0
    remaining_trajectories = 0
    remaining_submissions = 0

    for problem_dir in tqdm(
        problem_dirs,
        desc="Filter by Python800 Accepted programs",
        unit="problem",
    ):
        benchmark_problem_dir = benchmark_root / problem_dir.name
        if not benchmark_problem_dir.is_dir():
            raise FileNotFoundError(
                f"Problem is missing from benchmark: {benchmark_problem_dir}"
            )

        submissions_dir = problem_dir / "submissions"
        kept_paths: list[Path] = []
        kept_submission_counts: list[int] = []
        for user_path in sorted(submissions_dir.glob("*.jsonl")):
            records = _read_submission_records(user_path)
            original_users.add(user_path.stem)
            original_trajectories += 1
            original_submissions += len(records)
            if not records or records[-1].get("verdict") != "Accepted":
                raise ValueError(
                    f"Trajectory does not end with Accepted: {user_path}"
                )

            accepted_id = str(records[-1].get("submission_id", ""))
            benchmark_path = benchmark_problem_dir / f"{accepted_id}.py"
            if benchmark_path.is_file():
                kept_paths.append(user_path)
                kept_submission_counts.append(len(records))
            else:
                user_path.unlink()
                removed_trajectories += 1
                removed_submissions += len(records)

        if len(kept_paths) < minimum_trajectories_per_problem:
            removed_trajectories += len(kept_paths)
            removed_submissions += sum(kept_submission_counts)
            shutil.rmtree(problem_dir)
            removed_problems += 1
            continue

        remaining_trajectories += len(kept_paths)
        remaining_submissions += sum(kept_submission_counts)
        remaining_users.update(path.stem for path in kept_paths)

    return BenchmarkAcceptanceSummary(
        original_problems=len(problem_dirs),
        original_users=len(original_users),
        original_trajectories=original_trajectories,
        original_submissions=original_submissions,
        removed_trajectories_not_in_benchmark=removed_trajectories,
        removed_submissions=removed_submissions,
        removed_problems_below_minimum=removed_problems,
        minimum_trajectories_per_problem=minimum_trajectories_per_problem,
        remaining_problems=len(problem_dirs) - removed_problems,
        remaining_users=len(remaining_users),
        remaining_trajectories=remaining_trajectories,
        remaining_submissions=remaining_submissions,
    )


def normalized_code_fingerprint(code: str) -> bytes:
    code = code.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(code)
        tree = _StripStringExpressions().visit(tree)
        ast.fix_missing_locations(tree)
        normalized = ast.dump(tree, annotate_fields=True, include_attributes=False)
    except (SyntaxError, ValueError, TypeError):
        normalized = _normalize_code_tokens(code)
    return hashlib.sha256(normalized.encode("utf-8", errors="replace")).digest()


class _StripStringExpressions(ast.NodeTransformer):
    def visit_Expr(self, node: ast.Expr) -> ast.AST | None:
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return None
        return self.generic_visit(node)


def _normalize_code_tokens(code: str) -> str:
    try:
        normalized: list[tuple[int, str]] = []
        for token in tokenize.generate_tokens(io.StringIO(code).readline):
            if token.type in {tokenize.COMMENT, tokenize.NL, tokenize.ENDMARKER}:
                continue
            if token.type == tokenize.INDENT:
                normalized.append((token.type, "<INDENT>"))
            elif token.type == tokenize.DEDENT:
                normalized.append((token.type, "<DEDENT>"))
            elif token.type == tokenize.NEWLINE:
                normalized.append((token.type, "<NEWLINE>"))
            else:
                normalized.append((token.type, token.string))
        return repr(normalized)
    except (IndentationError, tokenize.TokenError):
        lines = [line.split("#", 1)[0].strip() for line in code.splitlines()]
        return "\n".join(line for line in lines if line)


def _read_submission_records(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    records.sort(
        key=lambda record: (
            int(record.get("timestamp", 0)),
            str(record.get("submission_id", "")),
        )
    )
    return records


def _collapse_consecutive_normalized(
    records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    collapsed: list[dict[str, Any]] = []
    previous_fingerprint: bytes | None = None
    removed = 0
    for record in records:
        fingerprint = normalized_code_fingerprint(str(record.get("code", "")))
        if collapsed and fingerprint == previous_fingerprint:
            collapsed[-1] = record
            removed += 1
        else:
            collapsed.append(record)
        previous_fingerprint = fingerprint
    return collapsed, removed


def _submission_ids(records: list[dict[str, Any]]) -> list[str]:
    return [str(record.get("submission_id", "")) for record in records]


def _write_submission_records(path: Path, records: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _is_valid_trajectory(path: Path) -> bool:
    count = 0
    has_accepted = False
    has_non_accepted = False
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            record = json.loads(line)
            count += 1
            if record.get("verdict") == "Accepted":
                has_accepted = True
            else:
                has_non_accepted = True
            if count >= 2 and has_accepted and has_non_accepted:
                return True
    return False


def _find_problem_dirs(data_root: Path) -> list[Path]:
    flat = sorted(
        path for path in data_root.iterdir() if path.is_dir() and path.name.startswith("p")
    )
    nested = sorted(
        problem_dir
        for split_name in ("train", "valid", "test")
        for problem_dir in (data_root / split_name).glob("p*")
        if problem_dir.is_dir()
    )
    if flat and nested:
        raise ValueError("Mixed flat and partitioned problem directories are not supported")
    return flat or nested
