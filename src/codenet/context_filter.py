from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from ..repair.dataset import (
    _build_adapter_examples,
    _is_strict_improvement,
    _load_problem_context,
)
from ..repair.prompts import build_messages, render_generation_prompt


CONTEXT_WINDOW_TOKENS = 4_096
DEFAULT_CONTEXT_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
PROMPT_STYLE = "D"


@dataclass(frozen=True)
class TrajectoryContextAuditSummary:
    base_model: str
    prompt_style: str
    context_window_tokens: int
    problems: int
    trajectories: int
    eligible_trajectories: int
    excluded_trajectories: int
    excluded_by_configuration: dict[str, int]
    maximum_observed_tokens: int
    output_path: Path


def audit_trajectory_contexts(
    data_root: Path,
    output_path: Path,
    *,
    base_model: str = DEFAULT_CONTEXT_MODEL,
) -> TrajectoryContextAuditSummary:
    """Exclude a whole trajectory when any configuration exceeds 4,096 tokens."""

    from transformers import AutoTokenizer

    data_root = data_root.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    testcase_ids_by_problem = {
        problem_dir.name: [
            str(row["case_id"])
            for row in _iter_jsonl(problem_dir / "testcases.jsonl")
        ]
        for problem_dir in _problem_dirs(data_root)
    }

    rows: list[dict[str, Any]] = []
    excluded_by_configuration: Counter[str] = Counter()
    maximum_observed_tokens = 0
    problem_dirs = _problem_dirs(data_root)
    for problem_dir in tqdm(
        problem_dirs,
        desc=f"Audit {CONTEXT_WINDOW_TOKENS:,}-token trajectory contexts",
        unit="problem",
    ):
        context = _load_problem_context(problem_dir)
        for trajectory_path in sorted((problem_dir / "submissions").glob("*.jsonl")):
            submissions = list(_iter_jsonl(trajectory_path))
            lengths = _trajectory_configuration_lengths(
                tokenizer,
                problem_id=problem_dir.name,
                context=context,
                submissions=submissions,
                testcase_ids=testcase_ids_by_problem[problem_dir.name],
            )
            maximum = max(lengths.values(), default=0)
            overlength = sorted(
                mode
                for mode, tokens in lengths.items()
                if tokens > CONTEXT_WINDOW_TOKENS
            )
            for mode in overlength:
                excluded_by_configuration[mode] += 1
            maximum_observed_tokens = max(maximum_observed_tokens, maximum)
            rows.append(
                {
                    "problem_id": problem_dir.name,
                    "user_id": trajectory_path.stem,
                    "relative_path": str(trajectory_path.relative_to(data_root)),
                    "eligible": not overlength,
                    "context_window_tokens": CONTEXT_WINDOW_TOKENS,
                    "maximum_tokens": maximum,
                    "max_tokens_by_configuration": lengths,
                    "overlength_configurations": overlength,
                }
            )

    with output_path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = TrajectoryContextAuditSummary(
        base_model=base_model,
        prompt_style=PROMPT_STYLE,
        context_window_tokens=CONTEXT_WINDOW_TOKENS,
        problems=len(problem_dirs),
        trajectories=len(rows),
        eligible_trajectories=sum(bool(row["eligible"]) for row in rows),
        excluded_trajectories=sum(not bool(row["eligible"]) for row in rows),
        excluded_by_configuration=dict(sorted(excluded_by_configuration.items())),
        maximum_observed_tokens=maximum_observed_tokens,
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _trajectory_configuration_lengths(
    tokenizer: Any,
    *,
    problem_id: str,
    context: dict[str, Any],
    submissions: list[dict[str, Any]],
    testcase_ids: list[str],
) -> dict[str, int]:
    if len(submissions) < 2:
        return {}
    indexed = list(enumerate(submissions, start=1))
    configurations = {
        "answer": _build_adapter_examples(
            indexed,
            target_mode="answer",
            problem_id=problem_id,
            outcomes={},
            counts=Counter(),
        ),
        "strict": _build_adapter_examples(
            indexed,
            target_mode="strict",
            problem_id=problem_id,
            outcomes={},
            counts=Counter(),
        ),
        "progress-envelope": _progress_envelope_examples(indexed),
        "final": [
            (
                indexed[:-1],
                indexed[-1],
                len(indexed) - 1,
                f"S{len(indexed)}",
            )
        ],
    }
    maximum_by_configuration: dict[str, int] = {}
    for mode, examples in configurations.items():
        maximum = 0
        for indexed_history, (_target_position, target), _before, _suffix in examples:
            displayed_history = (
                [
                    (position, submission)
                    for position, (_original, submission) in enumerate(
                        indexed_history,
                        start=1,
                    )
                ]
                if mode in {"strict", "progress-envelope"}
                else indexed_history
            )
            history = [
                _history_item(
                    position,
                    submission,
                    testcase_ids=(
                        testcase_ids
                        if mode in {"progress-envelope", "final"}
                        else []
                    ),
                )
                for position, submission in displayed_history
            ]
            record = {
                **context,
                "history": history,
                "target_code": target.get("code", ""),
            }
            if mode == "progress-envelope" and history:
                current = history[-1]
                for key in (
                    "execution_verdict",
                    "pass_rate",
                    "passed_testcases",
                    "tc_outcomes",
                    "execution_complete",
                ):
                    record[f"current_{key}"] = current[key]
            prompt = render_generation_prompt(
                tokenizer,
                build_messages(record, PROMPT_STYLE),
            )
            prompt_tokens = len(
                tokenizer(prompt, add_special_tokens=False)["input_ids"]
            )
            target_tokens = len(
                tokenizer(
                    str(target.get("code", "")).rstrip(),
                    add_special_tokens=False,
                )["input_ids"]
            )
            maximum = max(maximum, prompt_tokens + target_tokens + 1)
        maximum_by_configuration[mode] = maximum
    return maximum_by_configuration


def _progress_envelope_examples(
    submissions: list[tuple[int, dict[str, Any]]],
) -> list[
    tuple[
        list[tuple[int, dict[str, Any]]],
        tuple[int, dict[str, Any]],
        int,
        str,
    ]
]:
    """Keep every transition that testcase evidence could possibly retain."""

    retained = [submissions[0]]
    for candidate in submissions[1:]:
        current = retained[-1][1]
        target = candidate[1]
        if _is_strict_improvement(
            current.get("verdict"),
            target.get("verdict"),
        ) or str(current.get("verdict")) == str(target.get("verdict")):
            retained.append(candidate)
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
    position: int,
    submission: dict[str, Any],
    *,
    testcase_ids: list[str],
) -> dict[str, Any]:
    item = {
        "position": position,
        "submission_id": submission.get("submission_id"),
        "verdict": submission.get("verdict"),
        "code": submission.get("code", ""),
    }
    if testcase_ids:
        failure_verdicts = ("CE", "RE", "TLE", "WA")
        tc_outcomes = {
            case_id: failure_verdicts[index % len(failure_verdicts)]
            for index, case_id in enumerate(testcase_ids)
        }
        item.update(
            {
                "execution_verdict": "CE",
                "pass_rate": 0.0,
                "passed_testcases": [],
                "tc_outcomes": tc_outcomes,
                "execution_complete": True,
            }
        )
    return item


def _problem_dirs(data_root: Path) -> list[Path]:
    return sorted(
        path
        for path in data_root.iterdir()
        if path.is_dir() and path.name.startswith("p")
    )


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
