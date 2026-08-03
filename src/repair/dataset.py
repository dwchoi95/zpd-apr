from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm


_VERDICT_SEVERITY = {
    "Accepted": 0,
    "Wrong Answer": 1,
    "Time Limit Exceeded": 2,
    "Memory Limit Exceeded": 2,
    "Runtime Error": 3,
    "Compilation Error": 4,
    "Compile Error": 4,
    "Internal error": 5,
}


@dataclass(frozen=True)
class RepairDatasetSummary:
    split: str
    target_mode: str
    exclude_accepted_targets: bool
    outcome_cache_used: bool
    outcome_cache_complete: bool
    problems: int
    trajectories: int
    candidate_transitions: int
    written_examples: int
    history_entries_before_filtering: int
    history_entries_after_filtering: int
    removed_non_improving_history_entries: int
    removed_worsening_trajectory_submissions: int
    removed_non_productive_trajectory_submissions: int
    excluded_worsening_transitions: int
    excluded_non_productive_transitions: int
    excluded_accepted_targets: int
    excluded_missing_outcomes: int
    output_path: Path


@dataclass(frozen=True)
class SampleDatasetSummary:
    source_examples: int
    selected_examples: int
    selected_problems: int
    max_examples_per_problem: int
    seed: int
    output_path: Path


@dataclass(frozen=True)
class CurrentCodeOnlyDatasetSummary:
    examples: int
    reset_positions: int
    input_path: Path
    output_path: Path


class _DescriptionParser(HTMLParser):
    _BLOCKS = {"p", "pre", "div", "section", "h1", "h2", "h3", "li", "br"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in self._BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line).strip()


def build_repair_dataset(
    data_root: Path,
    *,
    split: str,
    output_path: Path,
    target_mode: str | None = None,
    exclude_accepted_targets: bool = False,
    outcome_cache_path: Path | None = None,
) -> RepairDatasetSummary:
    """Materialize all-prefix train examples or final-step evaluation examples."""

    data_root = data_root.expanduser().resolve()
    split = split.lower()
    if split not in {
        "train",
        "valid",
        "test",
        "seen_train",
        "seen_valid",
        "seen_test",
        "unseen_test",
    }:
        raise ValueError(f"Unsupported split: {split}")
    target_mode = target_mode or (
        "productive" if split in {"train", "seen_train"} else "final"
    )
    if target_mode not in {
        "all",
        "non-worsening",
        "strict-improvement",
        "hybrid-productive",
        "productive",
        "same-severity-productive",
        "progress",
        "strict",
        "answer",
        "final",
        "final-accepted",
    }:
        raise ValueError(f"Unsupported target mode: {target_mode}")
    outcomes: dict[tuple[str, str], dict[str, Any]] = {}
    outcome_cache_complete = False
    requires_outcomes = target_mode in {
        "productive",
        "hybrid-productive",
        "same-severity-productive",
        "progress",
    }
    if outcome_cache_path is None and requires_outcomes:
        raise ValueError(f"{target_mode} target mode requires outcome_cache_path")
    if outcome_cache_path is not None:
        from .outcomes import load_outcome_cache

        outcomes = load_outcome_cache(outcome_cache_path)
        summary_path = outcome_cache_path.expanduser().resolve().with_suffix(
            ".summary.json"
        )
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            outcome_cache_complete = summary.get("outcome_cache_complete") is True
        if target_mode == "progress" and not outcome_cache_complete:
            raise ValueError(
                "progress target mode requires a complete all-testcase outcome cache"
            )

    problem_ids = load_split_problem_ids(data_root, split)
    trajectory_ids = load_split_trajectory_ids(data_root, split)
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[str] = Counter()

    with output_path.open("w", encoding="utf-8") as output:
        for problem_id in tqdm(problem_ids, desc=f"Build {split} repair data", unit="problem"):
            problem_dir = data_root / problem_id
            context = _load_problem_context(problem_dir)
            for trajectory_path in sorted((problem_dir / "submissions").glob("*.jsonl")):
                if (
                    trajectory_ids is not None
                    and trajectory_path.stem not in trajectory_ids[problem_id]
                ):
                    continue
                submissions = list(_iter_jsonl(trajectory_path))
                if len(submissions) < 2:
                    continue
                counts["trajectories"] += 1
                indexed_submissions = list(enumerate(submissions, start=1))
                special_mode = target_mode in {"progress", "strict", "answer"}
                if special_mode:
                    examples = _build_adapter_examples(
                        indexed_submissions,
                        target_mode=target_mode,
                        problem_id=problem_id,
                        outcomes=outcomes,
                        counts=counts,
                    )
                else:
                    target_indexes = (
                        [len(submissions) - 1]
                        if target_mode in {"final", "final-accepted"}
                        else range(1, len(submissions))
                    )
                    examples = [
                        (
                            indexed_submissions[:target_index],
                            indexed_submissions[target_index],
                            target_index,
                            f"S{target_index + 1}",
                        )
                        for target_index in target_indexes
                    ]

                for (
                    indexed_history,
                    (target_position, target),
                    history_entries_before_filtering,
                    example_suffix,
                ) in examples:
                    if not special_mode:
                        counts["candidate_transitions"] += 1
                    current = indexed_history[-1][1]
                    if (
                        target_mode == "final-accepted"
                        and str(target.get("verdict")) != "Accepted"
                    ):
                        counts["excluded_non_productive_transitions"] += 1
                        continue
                    if (
                        exclude_accepted_targets
                        and str(target.get("verdict")) == "Accepted"
                    ):
                        counts["excluded_accepted_targets"] += 1
                        continue
                    if target_mode == "non-worsening" and not _is_non_worsening(
                        current.get("verdict"), target.get("verdict")
                    ):
                        counts["excluded_worsening_transitions"] += 1
                        continue
                    if target_mode == "strict-improvement" and not _is_strict_improvement(
                        current.get("verdict"), target.get("verdict")
                    ):
                        counts["excluded_non_productive_transitions"] += 1
                        continue
                    current_outcome = outcomes.get(
                        (problem_id, str(current.get("submission_id")))
                    )
                    target_outcome = outcomes.get(
                        (problem_id, str(target.get("submission_id")))
                    )
                    if (
                        target_mode == "strict-improvement"
                        and outcome_cache_path is not None
                    ):
                        if current_outcome is None or target_outcome is None:
                            counts["excluded_missing_outcomes"] += 1
                            continue
                        if not _is_productive(current_outcome, target_outcome):
                            counts["excluded_non_productive_transitions"] += 1
                            continue
                    if target_mode == "productive":
                        if current_outcome is None or target_outcome is None:
                            counts["excluded_missing_outcomes"] += 1
                            continue
                        if not _is_productive(current_outcome, target_outcome):
                            counts["excluded_non_productive_transitions"] += 1
                            continue
                    if target_mode == "same-severity-productive":
                        if not _has_same_verdict_severity(
                            current.get("verdict"),
                            target.get("verdict"),
                        ):
                            counts["excluded_non_productive_transitions"] += 1
                            continue
                        if current_outcome is None or target_outcome is None:
                            counts["excluded_missing_outcomes"] += 1
                            continue
                        if not _is_productive(current_outcome, target_outcome):
                            counts["excluded_non_productive_transitions"] += 1
                            continue
                    if target_mode == "hybrid-productive":
                        strict = _is_strict_improvement(
                            current.get("verdict"), target.get("verdict")
                        )
                        if not strict and not _is_non_worsening(
                            current.get("verdict"), target.get("verdict")
                        ):
                            counts["excluded_non_productive_transitions"] += 1
                            continue
                        if not strict:
                            if current_outcome is None or target_outcome is None:
                                counts["excluded_missing_outcomes"] += 1
                                continue
                            if not _is_productive(current_outcome, target_outcome):
                                counts["excluded_non_productive_transitions"] += 1
                                continue
                    if target_mode in {"progress", "strict"}:
                        displayed_history = [
                            (filtered_position, item)
                            for filtered_position, (_position, item) in enumerate(
                                indexed_history,
                                start=1,
                            )
                        ]
                        displayed_target_position = len(displayed_history) + 1
                    else:
                        displayed_history = indexed_history
                        displayed_target_position = target_position
                    history = [
                        _history_item(
                            problem_id,
                            position,
                            item,
                            outcomes=outcomes,
                            outcome_cache_complete=outcome_cache_complete,
                        )
                        for position, item in displayed_history
                    ]
                    counts["history_entries_before_filtering"] += (
                        history_entries_before_filtering
                    )
                    counts["history_entries_after_filtering"] += len(history)
                    counts["removed_non_improving_history_entries"] += (
                        history_entries_before_filtering - len(history)
                    )
                    payload = {
                        "example_id": (
                            f"{problem_id}:{trajectory_path.stem}:{example_suffix}"
                        ),
                        "problem_id": problem_id,
                        "user_id": trajectory_path.stem,
                        **context,
                        "history": history,
                        "target_position": displayed_target_position,
                        "original_target_position": target_position,
                        "target_submission_id": target.get("submission_id"),
                        "target_verdict": target.get("verdict"),
                        "target_code": target.get("code", ""),
                    }
                    if (
                        current_outcome is not None
                        and target_outcome is not None
                    ):
                        payload.update(
                            {
                                "current_execution_verdict": current_outcome[
                                    "execution_verdict"
                                ],
                                "target_execution_verdict": target_outcome[
                                    "execution_verdict"
                                ],
                                "current_pass_rate": current_outcome["pass_rate"],
                                "target_pass_rate": target_outcome["pass_rate"],
                                "current_passed_testcases": current_outcome[
                                    "passed_testcases"
                                ],
                                "target_passed_testcases": target_outcome[
                                    "passed_testcases"
                                ],
                                "current_tc_outcomes": current_outcome[
                                    "tc_outcomes"
                                ],
                                "current_execution_complete": outcome_cache_complete,
                                "target_tc_outcomes": target_outcome[
                                    "tc_outcomes"
                                ],
                            }
                        )
                    output.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    counts["written_examples"] += 1

    return RepairDatasetSummary(
        split=split,
        target_mode=target_mode,
        exclude_accepted_targets=exclude_accepted_targets,
        outcome_cache_used=outcome_cache_path is not None,
        outcome_cache_complete=outcome_cache_complete,
        problems=len(problem_ids),
        trajectories=counts["trajectories"],
        candidate_transitions=counts["candidate_transitions"],
        written_examples=counts["written_examples"],
        history_entries_before_filtering=counts[
            "history_entries_before_filtering"
        ],
        history_entries_after_filtering=counts[
            "history_entries_after_filtering"
        ],
        removed_non_improving_history_entries=counts[
            "removed_non_improving_history_entries"
        ],
        removed_worsening_trajectory_submissions=counts[
            "removed_worsening_trajectory_submissions"
        ],
        removed_non_productive_trajectory_submissions=counts[
            "removed_non_productive_trajectory_submissions"
        ],
        excluded_worsening_transitions=counts["excluded_worsening_transitions"],
        excluded_non_productive_transitions=counts[
            "excluded_non_productive_transitions"
        ],
        excluded_accepted_targets=counts["excluded_accepted_targets"],
        excluded_missing_outcomes=counts["excluded_missing_outcomes"],
        output_path=output_path,
    )


def _build_adapter_examples(
    submissions: list[tuple[int, dict[str, Any]]],
    *,
    target_mode: str,
    problem_id: str,
    outcomes: dict[tuple[str, str], dict[str, Any]],
    counts: Counter[str],
) -> list[
    tuple[
        list[tuple[int, dict[str, Any]]],
        tuple[int, dict[str, Any]],
        int,
        str,
    ]
]:
    """Build adapter-specific examples after filtering the trajectory itself."""

    counts["candidate_transitions"] += len(submissions) - 1
    if target_mode == "answer":
        final_position, final_submission = submissions[-1]
        if str(final_submission.get("verdict")) != "Accepted":
            counts["excluded_non_productive_transitions"] += len(submissions) - 1
            return []
        return [
            (
                [(source_position, source_submission)],
                (final_position, final_submission),
                1,
                f"S{source_position}-to-S{final_position}",
            )
            for source_position, source_submission in submissions[:-1]
            if str(source_submission.get("verdict")) != "Accepted"
        ]

    retained = [submissions[0]]
    for candidate in submissions[1:]:
        _current_position, current = retained[-1]
        _candidate_position, target = candidate
        if _is_strict_improvement(
            current.get("verdict"),
            target.get("verdict"),
        ):
            retained.append(candidate)
            continue

        if target_mode == "strict":
            if not _is_non_worsening(
                current.get("verdict"),
                target.get("verdict"),
            ):
                counts["excluded_worsening_transitions"] += 1
                counts["removed_worsening_trajectory_submissions"] += 1
            else:
                counts["excluded_non_productive_transitions"] += 1
                counts["removed_non_productive_trajectory_submissions"] += 1
            continue

        if target_mode != "progress":
            raise ValueError(f"Unsupported adapter target mode: {target_mode}")
        if str(current.get("verdict")) != str(target.get("verdict")):
            if not _is_non_worsening(
                current.get("verdict"),
                target.get("verdict"),
            ):
                counts["excluded_worsening_transitions"] += 1
                counts["removed_worsening_trajectory_submissions"] += 1
            else:
                counts["excluded_non_productive_transitions"] += 1
                counts["removed_non_productive_trajectory_submissions"] += 1
            continue

        current_outcome = outcomes.get(
            (problem_id, str(current.get("submission_id")))
        )
        target_outcome = outcomes.get(
            (problem_id, str(target.get("submission_id")))
        )
        if current_outcome is None or target_outcome is None:
            counts["excluded_missing_outcomes"] += 1
            counts["removed_non_productive_trajectory_submissions"] += 1
            continue
        if _is_testcase_verdict_improvement(current_outcome, target_outcome):
            retained.append(candidate)
        else:
            counts["excluded_non_productive_transitions"] += 1
            counts["removed_non_productive_trajectory_submissions"] += 1

    return [
        (
            retained[:target_index],
            retained[target_index],
            retained[target_index][0] - 1,
            f"S{retained[target_index][0]}",
        )
        for target_index in range(1, len(retained))
    ]


def _history_item(
    problem_id: str,
    position: int,
    submission: dict[str, Any],
    *,
    outcomes: dict[tuple[str, str], dict[str, Any]],
    outcome_cache_complete: bool,
) -> dict[str, Any]:
    item = {
        "position": position,
        "submission_id": submission.get("submission_id"),
        "verdict": submission.get("verdict"),
        "code": submission.get("code", ""),
    }
    outcome = outcomes.get(
        (problem_id, str(submission.get("submission_id")))
    )
    if outcome is not None:
        item.update(
            {
                "execution_verdict": outcome["execution_verdict"],
                "pass_rate": outcome["pass_rate"],
                "passed_testcases": outcome["passed_testcases"],
                "tc_outcomes": outcome["tc_outcomes"],
                "execution_complete": outcome_cache_complete,
            }
        )
    return item


def sample_repair_dataset(
    dataset_path: Path,
    output_path: Path,
    *,
    size: int,
    max_examples_per_problem: int = 4,
    seed: int = 2027,
) -> SampleDatasetSummary:
    if size <= 0:
        raise ValueError("size must be positive")
    if max_examples_per_problem <= 0:
        raise ValueError("max_examples_per_problem must be positive")

    dataset_path = dataset_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    by_problem: dict[str, list[dict[str, Any]]] = {}
    source_examples = 0
    for row in _iter_jsonl(dataset_path):
        source_examples += 1
        by_problem.setdefault(str(row["problem_id"]), []).append(row)

    def rank(value: str) -> str:
        return sha256(f"{seed}:{value}".encode()).hexdigest()

    selected: list[dict[str, Any]] = []
    for problem_id in sorted(by_problem, key=rank):
        problem_rows = sorted(
            by_problem[problem_id],
            key=lambda row: rank(str(row["example_id"])),
        )
        selected.extend(problem_rows[:max_examples_per_problem])
        if len(selected) >= size:
            break
    selected = selected[:size]
    selected.sort(key=lambda row: str(row["example_id"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for row in selected:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")

    return SampleDatasetSummary(
        source_examples=source_examples,
        selected_examples=len(selected),
        selected_problems=len({str(row["problem_id"]) for row in selected}),
        max_examples_per_problem=max_examples_per_problem,
        seed=seed,
        output_path=output_path,
    )


def build_current_code_only_dataset(
    input_path: Path,
    output_path: Path,
) -> CurrentCodeOnlyDatasetSummary:
    """Remove prior submissions and trajectory-length leakage for RQ2."""

    input_path = input_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    examples = 0
    reset_positions = 0

    with output_path.open("w", encoding="utf-8") as output:
        for record in _iter_jsonl(input_path):
            history = list(record.get("history", []))
            if not history:
                raise ValueError(
                    f"Example {record.get('example_id')} has no submission history."
                )
            current = dict(history[-1])
            if current.get("position") != 1:
                reset_positions += 1
            current["position"] = 1
            transformed = dict(record)
            transformed["history"] = [current]
            output.write(json.dumps(transformed, ensure_ascii=False) + "\n")
            examples += 1

    return CurrentCodeOnlyDatasetSummary(
        examples=examples,
        reset_positions=reset_positions,
        input_path=input_path,
        output_path=output_path,
    )


def load_split_problem_ids(data_root: Path, split: str) -> list[str]:
    manifest = _split_manifest_path(data_root, split)
    if not manifest.is_file():
        raise FileNotFoundError(f"Split manifest not found: {manifest}")
    return list(dict.fromkeys(str(record["problem_id"]) for record in _iter_jsonl(manifest)))


def load_split_trajectory_ids(
    data_root: Path,
    split: str,
) -> dict[str, set[str]] | None:
    manifest = _split_manifest_path(data_root, split)
    records = list(_iter_jsonl(manifest))
    if not records or any("user_id" not in record for record in records):
        return None
    result: dict[str, set[str]] = {}
    for record in records:
        result.setdefault(str(record["problem_id"]), set()).add(str(record["user_id"]))
    return result


def _split_manifest_path(data_root: Path, split: str) -> Path:
    return data_root / "splits" / f"{split}.jsonl"


def summary_json(summary: RepairDatasetSummary) -> str:
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str)


def _load_problem_context(problem_dir: Path) -> dict[str, Any]:
    parser = _DescriptionParser()
    parser.feed((problem_dir / "description.html").read_text(encoding="utf-8", errors="replace"))
    metadata = json.loads((problem_dir / "metadata.json").read_text(encoding="utf-8"))
    return {
        "problem_description": parser.text(),
        "time_limit": metadata.get("time_limit"),
        "memory_limit": metadata.get("memory_limit"),
    }


def _is_non_worsening(current: Any, target: Any) -> bool:
    current_score = _VERDICT_SEVERITY.get(str(current), 5)
    target_score = _VERDICT_SEVERITY.get(str(target), 5)
    return target_score <= current_score


def _has_same_verdict_severity(current: Any, target: Any) -> bool:
    current_score = _VERDICT_SEVERITY.get(str(current), 5)
    target_score = _VERDICT_SEVERITY.get(str(target), 5)
    return current_score == target_score


def _is_strict_improvement(current: Any, target: Any) -> bool:
    current_score = _VERDICT_SEVERITY.get(str(current), 5)
    target_score = _VERDICT_SEVERITY.get(str(target), 5)
    return target_score < current_score


def filter_adapter_history(
    history: list[dict[str, Any]],
    adapter_name: str,
    *,
    preserve_current: bool = True,
) -> list[dict[str, Any]]:
    """Apply an adapter's trajectory rule while preserving the repair target."""

    if len(history) <= 1:
        return history
    mode = adapter_name.strip().lower()
    if mode not in {"progress", "strict"}:
        return history

    candidates = history[:-1] if preserve_current else history
    retained = [candidates[0]]
    for target in candidates[1:]:
        current = retained[-1]
        if mode == "strict":
            keep = _is_strict_improvement(
                current.get("verdict"),
                target.get("verdict"),
            )
        else:
            keep = _is_strict_improvement(
                current.get("verdict"),
                target.get("verdict"),
            ) or (
                str(current.get("verdict")) == str(target.get("verdict"))
                and _has_execution_evidence(current)
                and _has_execution_evidence(target)
                and _is_testcase_verdict_improvement(current, target)
            )
        if keep:
            retained.append(target)

    if preserve_current:
        retained.append(history[-1])
    for position, submission in enumerate(retained, start=1):
        submission = dict(submission)
        submission["position"] = position
        retained[position - 1] = submission
    return retained


def _has_execution_evidence(submission: dict[str, Any]) -> bool:
    return isinstance(
        submission.get("tc_outcomes"),
        dict,
    )


def _is_productive(
    current: dict[str, Any],
    target: dict[str, Any],
) -> bool:
    """Require monotonic test progress or strict verdict progress at equal coverage."""

    current_passed = set(map(str, current.get("passed_testcases", [])))
    target_passed = set(map(str, target.get("passed_testcases", [])))
    if current_passed < target_passed:
        return True
    if current_passed != target_passed:
        return False
    current_score = _VERDICT_SEVERITY.get(
        _display_execution_verdict(current.get("execution_verdict")), 5
    )
    target_score = _VERDICT_SEVERITY.get(
        _display_execution_verdict(target.get("execution_verdict")), 5
    )
    return target_score < current_score


def _is_testcase_verdict_improvement(
    current: dict[str, Any],
    target: dict[str, Any],
) -> bool:
    """Require Pareto improvement over the same non-empty testcase set."""

    current_outcomes = current.get("tc_outcomes")
    target_outcomes = target.get("tc_outcomes")
    if not isinstance(current_outcomes, dict) or not isinstance(target_outcomes, dict):
        return False
    if not current_outcomes or current_outcomes.keys() != target_outcomes.keys():
        return False

    improved = False
    for case_id, current_verdict in current_outcomes.items():
        current_score = _VERDICT_SEVERITY.get(
            _display_execution_verdict(current_verdict),
            5,
        )
        target_score = _VERDICT_SEVERITY.get(
            _display_execution_verdict(target_outcomes[case_id]),
            5,
        )
        if target_score > current_score:
            return False
        improved = improved or target_score < current_score
    return improved


def _display_execution_verdict(value: Any) -> str:
    return {
        "AC": "Accepted",
        "WA": "Wrong Answer",
        "TLE": "Time Limit Exceeded",
        "RE": "Runtime Error",
        "CE": "Compilation Error",
    }.get(str(value), str(value))


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
