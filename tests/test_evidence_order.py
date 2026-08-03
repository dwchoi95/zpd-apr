from __future__ import annotations

import random
from itertools import permutations

from src.repair.evidence_order import (
    ExecutionEvidence,
    evidence_rank,
    first_successful_policy,
    first_improvement_index,
    pass_rate_non_regression,
    progress_improvement,
    retained_indices,
    strict_improvement,
)


VERDICTS = (
    "Accepted",
    "Wrong Answer",
    "Time Limit Exceeded",
    "Memory Limit Exceeded",
    "Runtime Error",
    "Compilation Error",
)


def evidence(verdict: str, outcomes: tuple[str, ...]) -> ExecutionEvidence:
    return ExecutionEvidence(
        verdict=verdict,
        test_outcomes={str(index): value for index, value in enumerate(outcomes)},
    )


def test_progress_relation_strictly_decreases_lexicographic_rank() -> None:
    rng = random.Random(2027)
    for _ in range(10_000):
        before = evidence(
            rng.choice(VERDICTS),
            tuple(rng.choice(VERDICTS) for _ in range(5)),
        )
        after = evidence(
            rng.choice(VERDICTS),
            tuple(rng.choice(VERDICTS) for _ in range(5)),
        )
        if progress_improvement(before, after):
            assert evidence_rank(after) < evidence_rank(before)


def test_strict_retained_events_are_included_by_progress() -> None:
    rng = random.Random(2027)
    for _ in range(2_000):
        trajectory = [
            evidence(
                rng.choice(VERDICTS),
                tuple(rng.choice(VERDICTS) for _ in range(4)),
            )
            for _ in range(rng.randint(1, 20))
        ]
        strict = set(retained_indices(trajectory, policy="strict"))
        progress = set(retained_indices(trajectory, policy="progress"))
        assert strict <= progress


def test_retained_chains_satisfy_their_policy() -> None:
    trajectory = [
        evidence("Runtime Error", ("RE", "RE", "RE")),
        evidence("Wrong Answer", ("AC", "WA", "WA")),
        evidence("Wrong Answer", ("AC", "AC", "WA")),
        evidence("Wrong Answer", ("AC", "WA", "WA")),
        evidence("Accepted", ("AC", "AC", "AC")),
    ]
    strict = retained_indices(trajectory, policy="strict")
    progress = retained_indices(trajectory, policy="progress")
    assert strict == (0, 1, 4)
    assert progress == (0, 1, 2, 4)
    assert all(
        strict_improvement(trajectory[left], trajectory[right])
        for left, right in zip(strict, strict[1:])
    )
    assert all(
        progress_improvement(trajectory[left], trajectory[right])
        for left, right in zip(progress, progress[1:])
    )


def test_current_program_makes_pass_rate_selection_non_regressive() -> None:
    assert pass_rate_non_regression(0.75, (0.0, 0.5, 0.74))
    assert pass_rate_non_regression(0.25, (0.0, 1.0))


def test_increasing_breadth_order_selects_the_narrowest_success() -> None:
    policies = ("Progress", "Strict", "Answer")
    breadth = {policy: index for index, policy in enumerate(policies, start=1)}
    for mask in range(1, 1 << len(policies)):
        successful = {
            policy for index, policy in enumerate(policies) if mask & (1 << index)
        }
        selected = first_successful_policy(policies, successful)
        assert selected is not None
        assert breadth[selected] == min(breadth[policy] for policy in successful)
        assert all(
            breadth[selected]
            <= breadth[first_successful_policy(order, successful)]
            for order in permutations(policies)
        )


def test_assistance_horizons_are_nested_before_terminal_acceptance() -> None:
    rng = random.Random(2027)
    for _ in range(2_000):
        trajectory = [
            evidence(
                rng.choice(VERDICTS[1:]),
                tuple(rng.choice(VERDICTS) for _ in range(4)),
            )
            for _ in range(rng.randint(1, 20))
        ]
        trajectory.append(evidence("Accepted", ("AC",) * 4))
        for start in range(len(trajectory) - 1):
            progress = first_improvement_index(trajectory, start, policy="progress")
            strict = first_improvement_index(trajectory, start, policy="strict")
            assert progress is not None and strict is not None
            assert progress <= strict <= len(trajectory) - 1
