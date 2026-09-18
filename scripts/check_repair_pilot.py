"""Synthetic engineering smoke only; no generator, runner, training or data I/O.

Run from the repository root: python -m scripts.check_repair_pilot
Hand-set coefficients below demonstrate wiring, not a useful repair policy.
"""
from dataclasses import asdict
import json

from src.repair.pilot_contracts import (
    CandidateAttempt, CandidateBank, ExecutionBlock, ExecutionVector,
    ObservationSource, PilotObservation, RankingExample, canonical_hash,
    compare_bank_candidate, source_hash,
)
from src.repair.pilot_ranker import TwoChannelCoefficients, select


def smoke_report():
    current = b"x = 0"
    patches = (b"x = 1", b"x = 2")
    seeds = tuple(range(8))
    config = {"synthetic": True, "seeds": seeds, "history_blind": True}
    attempts = tuple(
        CandidateAttempt(i, seeds[i], "success", patches[i % 2]) if i < 6
        else CandidateAttempt(i, seeds[i], "generation_failure", error="synthetic failure")
        for i in range(8)
    )
    bank = CandidateBank("synthetic-problem", current, canonical_hash(config), seeds, attempts)
    now = ObservationSource("current", 10, current, source_hash(current), "WA")
    histories = {
        "C": (),
        "H_fixture": (ObservationSource("past-a", 1, patches[0], source_hash(patches[0]), "WA"),),
        "U_fixture": (ObservationSource("past-b", 1, patches[1], source_hash(patches[1]), "WA"),),
    }
    # Reversion is deliberately rewarded here ONLY to demonstrate sensitivity.
    coefficients = TwoChannelCoefficients({"bias": -10}, {"history_reverse_edit_overlap": 1})
    selections, seals = {}, {}
    for condition, history in histories.items():
        observation = PilotObservation(bank.problem_id, now, history)
        binding = RankingExample(observation, bank)
        selections[condition] = asdict(select(
            observation, bank, history=history, coefficients=coefficients,
            risk_threshold=.5, minimum_gain=0,
        ))
        seals[condition] = {"bank": bank.seal_sha256, "binding": binding.seal_sha256}
    assert len({item["bank"] for item in seals.values()}) == 1
    assert selections["H_fixture"]["selected_source_sha256"] != selections["U_fixture"]["selected_source_sha256"]
    assert selections["C"]["abstained"]

    # Fabricated outcome vectors never enter the ranker. Nothing is executed.
    universe, runtime = canonical_hash(["t1", "t2"]), canonical_hash("synthetic-runtime")
    def vector(code, outcomes, partial=False):
        blocks = tuple(ExecutionBlock(
            workers, universe, runtime, tuple(zip(("t1", "t2"), outcomes)),
            not partial, source_hash(code),
        ) for workers in (1, 8, 8, 1))
        return ExecutionVector(source_hash(code), universe, runtime, ("t1", "t2"), blocks)
    before = vector(current, ("AC", "WA"))
    candidate_id = source_hash(patches[0])
    stable = compare_bank_candidate(bank, candidate_id, before, vector(patches[0], ("AC", "AC")))
    unknown = compare_bank_candidate(bank, candidate_id, before, vector(patches[0], ("AC", "AC"), partial=True))
    assert stable.gained_testcases == ("t2",) and stable.lost_testcases == ()
    assert unknown.status == "unknown" and unknown.candidate_all_ac is None
    return {
        "kind": "synthetic_engineering_only", "empirical_performance_measured": False,
        "trained": False, "candidate_programs_executed": False,
        "attempts": len(attempts), "unique_candidates_including_noop": len(bank.candidates),
        "seals": seals, "selections": selections,
        "fabricated_stable_evidence": asdict(stable), "fabricated_partial_evidence": asdict(unknown),
    }


if __name__ == "__main__":
    print(json.dumps(smoke_report(), indent=2, sort_keys=True))
