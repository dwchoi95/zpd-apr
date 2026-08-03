"""Executable reference semantics for ZPDPatch's execution-evidence order.

Dataset materialization is optimized for streaming.  This module keeps the
mathematical relation small and explicit so that tests and artifact audits can
check the paper's propositions independently of the builder implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


VERDICT_SEVERITY = {
    "Accepted": 0,
    "Wrong Answer": 1,
    "Time Limit Exceeded": 2,
    "Memory Limit Exceeded": 2,
    "Runtime Error": 3,
    "Compilation Error": 4,
    "Compile Error": 4,
    "Internal error": 5,
    "AC": 0,
    "WA": 1,
    "TLE": 2,
    "MLE": 2,
    "RE": 3,
    "CE": 4,
}


@dataclass(frozen=True)
class ExecutionEvidence:
    """Coarse judge verdict plus outcomes for one fixed testcase universe."""

    verdict: str
    test_outcomes: Mapping[str, str]


def severity(verdict: str) -> int:
    return VERDICT_SEVERITY.get(str(verdict), 5)


def strict_improvement(before: ExecutionEvidence, after: ExecutionEvidence) -> bool:
    return severity(after.verdict) < severity(before.verdict)


def testcase_pareto_improvement(
    before: ExecutionEvidence,
    after: ExecutionEvidence,
) -> bool:
    """Return true exactly for a strict Pareto improvement on equal test keys."""

    if not before.test_outcomes or before.test_outcomes.keys() != after.test_outcomes.keys():
        return False
    improved = False
    for case_id, old_verdict in before.test_outcomes.items():
        old = severity(old_verdict)
        new = severity(after.test_outcomes[case_id])
        if new > old:
            return False
        improved = improved or new < old
    return improved


def progress_improvement(before: ExecutionEvidence, after: ExecutionEvidence) -> bool:
    return strict_improvement(before, after) or (
        after.verdict == before.verdict
        and testcase_pareto_improvement(before, after)
    )


def evidence_rank(evidence: ExecutionEvidence) -> tuple[int, int]:
    """Lexicographic rank used by the finite-chain argument in the paper."""

    return (
        severity(evidence.verdict),
        sum(severity(value) for value in evidence.test_outcomes.values()),
    )


def retained_indices(
    trajectory: Sequence[ExecutionEvidence],
    *,
    policy: str,
) -> tuple[int, ...]:
    """Return the indices retained by Strict or Progress's one-pass scan."""

    if policy not in {"strict", "progress"}:
        raise ValueError(f"unsupported policy: {policy}")
    if not trajectory:
        return ()
    keep = strict_improvement if policy == "strict" else progress_improvement
    retained = [0]
    for index in range(1, len(trajectory)):
        if keep(trajectory[retained[-1]], trajectory[index]):
            retained.append(index)
    return tuple(retained)


def first_improvement_index(
    trajectory: Sequence[ExecutionEvidence],
    start: int,
    *,
    policy: str,
) -> int | None:
    """First future state related to ``start`` under one evidence order."""

    if not 0 <= start < len(trajectory):
        raise IndexError(start)
    if policy not in {"strict", "progress"}:
        raise ValueError(f"unsupported policy: {policy}")
    keep = strict_improvement if policy == "strict" else progress_improvement
    return next(
        (index for index in range(start + 1, len(trajectory)) if keep(trajectory[start], trajectory[index])),
        None,
    )


def pass_rate_non_regression(
    baseline_pass_rate: float,
    candidate_pass_rates: Sequence[float],
) -> bool:
    """Reference certificate for selectors that include the current program."""

    selected = max((baseline_pass_rate, *candidate_pass_rates))
    return selected >= baseline_pass_rate


def first_successful_policy(
    order: Sequence[str],
    successful_policies: set[str],
) -> str | None:
    """Reference semantics for policy-ordered early stopping."""

    return next((policy for policy in order if policy in successful_policies), None)
