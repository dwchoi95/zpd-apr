from __future__ import annotations

import ast
from collections import Counter
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any


PROMPT_ROOT = Path(__file__).resolve().parents[1] / "prompts"


def build_messages(
    record: dict[str, Any],
    prompt_style: str,
    *,
    repair_attempts: list[dict[str, Any]] | None = None,
) -> list[dict[str, str]]:
    style = prompt_style.upper()
    if style not in {"A", "B", "C", "D"}:
        raise ValueError(f"Unknown prompt style: {prompt_style}")

    history = [dict(item) for item in record["history"]]
    if history:
        current = history[-1]
        for target_key, source_key in (
            ("execution_verdict", "current_execution_verdict"),
            ("pass_rate", "current_pass_rate"),
            ("passed_testcases", "current_passed_testcases"),
            ("tc_outcomes", "current_tc_outcomes"),
            ("execution_complete", "current_execution_complete"),
        ):
            if source_key in record:
                current[target_key] = record[source_key]
    description = str(record["problem_description"]).strip()
    time_limit = _display_constraint(record.get("time_limit"))
    memory_limit = _display_constraint(record.get("memory_limit"))
    submission_messages = []
    for index, submission in enumerate(history):
        previous = history[index - 1] if index else None
        submission_messages.append(
            _render_submission(style, submission, previous_submission=previous)
        )

    system = _template(style, "system.md")
    if style == "A":
        user = _template(style, "user.md")
        user = user.replace("{{problem_description}}", description)
        user = user.replace("{{time_limit}}", time_limit)
        user = user.replace("{{memory_limit}}", memory_limit)
        user = user.replace("{{submission_trajectory}}", "\n\n".join(submission_messages))
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    system = system.replace("{{problem_description}}", description)
    system = system.replace("{{time_limit}}", time_limit)
    system = system.replace("{{memory_limit}}", memory_limit)
    messages = [{"role": "system", "content": system}]
    messages.extend({"role": "user", "content": item} for item in submission_messages)
    messages.extend(
        {
            "role": "user",
            "content": _render_repair_attempt(attempt),
        }
        for attempt in (repair_attempts or [])
    )
    return messages


def render_generation_prompt(tokenizer: Any, messages: list[dict[str, str]]) -> str:
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


def _render_submission(
    style: str,
    submission: dict[str, Any],
    *,
    previous_submission: dict[str, Any] | None,
) -> str:
    # Prompt A serializes the same submission block into one user message.
    template = _template("B" if style == "A" else style, "user.md")
    template = template.replace("{{position}}", str(submission["position"]))
    template = template.replace("{{verdict}}", str(submission["verdict"]))
    template = template.replace(
        "{{execution_feedback}}",
        _execution_feedback(submission),
    )
    template = template.replace(
        "{{edit_summary}}",
        _edit_summary(previous_submission, submission),
    )
    return template.replace("{{source_code}}", str(submission["code"]).rstrip())


def _execution_feedback(submission: dict[str, Any]) -> str:
    pass_rate = submission.get("pass_rate")
    tc_outcomes = submission.get("tc_outcomes")
    execution_verdict = submission.get("execution_verdict")
    execution_complete = submission.get("execution_complete")
    if pass_rate is None and not isinstance(tc_outcomes, dict):
        return ""

    lines = ["### Observed Execution"]
    if execution_verdict is not None:
        lines.append(f"Execution verdict: {execution_verdict}")
    if isinstance(tc_outcomes, dict) and tc_outcomes:
        passed = sum(str(value) == "AC" for value in tc_outcomes.values())
        coverage = "Pass rate" if execution_complete is True else "Observed test-subset pass rate"
        lines.append(
            f"{coverage}: {passed}/{len(tc_outcomes)} "
            f"({100 * passed / len(tc_outcomes):.1f}%)"
        )
        failures: dict[str, list[str]] = {}
        for case_id, verdict in tc_outcomes.items():
            if str(verdict) != "AC":
                failures.setdefault(str(verdict), []).append(str(case_id))
        if failures:
            signature = "; ".join(
                f"{verdict}: {', '.join(case_ids)}"
                for verdict, case_ids in sorted(failures.items())
            )
            lines.append(f"Failure signature: {signature}")
    elif pass_rate is not None:
        coverage = "Pass rate" if execution_complete is True else "Observed pass rate"
        lines.append(f"{coverage}: {100 * float(pass_rate):.1f}%")
    return "\n".join(lines)


def _edit_summary(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
) -> str:
    if previous is None:
        return ""
    before = str(previous.get("code", ""))
    after = str(current.get("code", ""))
    try:
        before_nodes = Counter(_ast_labels(ast.parse(before)))
        after_nodes = Counter(_ast_labels(ast.parse(after)))
    except (SyntaxError, ValueError, TypeError):
        return (
            "### Change from Previous Shown Submission\n"
            "AST change summary unavailable."
        )

    added = after_nodes - before_nodes
    removed = before_nodes - after_nodes
    line_matcher = SequenceMatcher(
        None,
        before.splitlines(),
        after.splitlines(),
        autojunk=False,
    )
    inserted = deleted = replaced = 0
    for tag, i1, i2, j1, j2 in line_matcher.get_opcodes():
        if tag == "insert":
            inserted += j2 - j1
        elif tag == "delete":
            deleted += i2 - i1
        elif tag == "replace":
            replaced += max(i2 - i1, j2 - j1)

    def display(counter: Counter[str]) -> str:
        if not counter:
            return "none"
        return ", ".join(
            f"{label} x{count}"
            for label, count in counter.most_common()
        )

    return "\n".join(
        [
            "### Change from Previous Shown Submission",
            f"AST nodes added: {display(added)}",
            f"AST nodes removed: {display(removed)}",
            (
                "Changed lines: "
                f"{inserted} inserted, {deleted} deleted, {replaced} replaced"
            ),
        ]
    )


def _ast_labels(tree: ast.AST) -> list[str]:
    labels: list[str] = []
    for node in ast.walk(tree):
        label = node.__class__.__name__
        if isinstance(node, ast.Name):
            label += f":{node.id}"
        elif isinstance(node, ast.arg):
            label += f":{node.arg}"
        elif isinstance(node, ast.Constant):
            label += f":{node.value!r}"
        labels.append(label)
    return labels


def _render_repair_attempt(attempt: dict[str, Any]) -> str:
    source = str(attempt.get("source", "previous"))
    code = str(attempt.get("generated_code", "")).rstrip()
    verdict = str(attempt.get("fixed_verdict", "unknown"))
    pass_rate = float(attempt.get("fixed_pass_rate", 0.0))
    tc_outcomes = attempt.get("fixed_tc_outcomes")
    status = str(attempt.get("repair_status", "unaccepted"))
    baseline_pass_rate = float(attempt.get("baseline_pass_rate", 0.0))
    feedback = _execution_feedback(
        {
            "execution_verdict": verdict,
            "pass_rate": pass_rate,
            "tc_outcomes": tc_outcomes,
            "execution_complete": True,
        }
    )
    parts = [
        "## Previous Repair Attempt",
        (
            f"Stage: {source}\n"
            f"Outcome relative to current program: {status}\n"
            f"Current program pass rate: {100 * baseline_pass_rate:.1f}%\n"
            f"{feedback}"
        ),
    ]
    if (
        status not in {"no-op", "regression"}
        and attempt.get("include_generated_code", True) is not False
    ):
        parts.append("### Generated Program\n```python\n" + code + "\n```")
    parts.append(
        "Do not repeat an unchanged or regressive modification. "
        "Revise this attempted repair using its execution result. "
        "Return a complete improved program, not an explanation."
    )
    return "\n\n".join(parts)


@lru_cache(maxsize=None)
def _template(style: str, filename: str) -> str:
    return (PROMPT_ROOT / style / filename).read_text(encoding="utf-8").strip()


def _display_constraint(value: Any) -> str:
    if value is None or value == "":
        return "Not specified"
    return str(value)
