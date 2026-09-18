import dataclasses
import unittest

from src.repair.pilot_contracts import (
    CandidateAttempt, CandidateBank, ExecutionBlock, ExecutionVector,
    ObservationSource, PilotObservation, canonical_hash, compare_execution,
    source_hash, RankingExample, compare_bank_candidate,
)


def observation_source(sid="s1", timestamp=1, source=b"x", verdict="WA"):
    return ObservationSource(sid, timestamp, source, source_hash(source), verdict)


def bank():
    attempts = (
        CandidateAttempt(0, 0, "success", b"x"),
        CandidateAttempt(1, 1, "success", b" x"),
        CandidateAttempt(2, 2, "success", b" x"),
    ) + tuple(CandidateAttempt(i, i, "unknown_failure", error="missing generator response") for i in range(3, 8))
    return CandidateBank("p", b"x", canonical_hash({"fixture": True}), tuple(range(8)), attempts)


def vector(outcomes=(("a", "WA"), ("b", "AC")), source=b"x"):
    universe = canonical_hash({"tests": ["a", "b"], "expected": ["0", "1"]})
    runtime = canonical_hash({"runtime": "fixture-only"})
    blocks = tuple(ExecutionBlock(w, universe, runtime, outcomes, True, source_hash(source)) for w in (1, 8, 8, 1))
    return ExecutionVector(source_hash(source), universe, runtime, ("a", "b"), blocks)


class ObservationTests(unittest.TestCase):
    def test_exact_hash_and_mapping_allowlist(self):
        obs = PilotObservation("p", observation_source("s2", 2), (observation_source(),))
        self.assertEqual(obs, PilotObservation.from_mapping(dataclasses.asdict(obs)))
        for key in ("future_code", "final_ac", "next_verdict", "labels"):
            raw = dataclasses.asdict(obs)
            raw[key] = "hidden"
            with self.assertRaises(ValueError):
                PilotObservation.from_mapping(raw)
            raw = dataclasses.asdict(obs)
            raw["prior"][0][key] = "hidden"
            with self.assertRaises(ValueError):
                PilotObservation.from_mapping(raw)
        with self.assertRaises(ValueError):
            dataclasses.replace(obs.current, source=b" x")

    def test_chronology_ids_and_immutable(self):
        for prior in ((observation_source("s2"),), (observation_source(timestamp=2),), (observation_source(timestamp=3),)):
            with self.assertRaises(ValueError):
                PilotObservation("p", observation_source("s2", 2), prior)
        with self.assertRaises(ValueError):
            PilotObservation("p", observation_source(), [])
        obs = PilotObservation("p", observation_source(), ())
        with self.assertRaises(dataclasses.FrozenInstanceError):
            obs.problem_id = "changed"
        with self.assertRaises(ValueError):
            observation_source(timestamp=float("nan"))


class BankTests(unittest.TestCase):
    def test_exact_dedup_noop_and_full_ledger(self):
        value = bank()
        self.assertEqual([v.source for v in value.candidates], [b"x", b" x"])
        self.assertTrue(value.candidates[0].is_noop)
        self.assertFalse(value.candidates[1].is_noop)
        self.assertEqual(len(value.attempts), 8)
        self.assertEqual(value.key, ("p", source_hash(b"x"), value.generator_config_sha256))
        self.assertNotEqual(value.seal_sha256, dataclasses.replace(value, attempts=value.attempts[:7] + (CandidateAttempt(7, 7, "format_failure", error="bad format"),)).seal_sha256)

    def test_no_retryfill_pending_or_partial_source(self):
        value = bank()
        for attempts in (value.attempts[:7], value.attempts + (value.attempts[-1],), value.attempts[::-1]):
            with self.assertRaises(ValueError):
                dataclasses.replace(value, attempts=attempts)
        with self.assertRaises(ValueError):
            CandidateAttempt(0, 0, "pending")
        with self.assertRaises(ValueError):
            CandidateAttempt(0, 0, "resource_failure", b"truncated", "length limit")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            value.current_source = b"changed"


class ExecutionTests(unittest.TestCase):
    def test_nominal_transition_and_separate_gain_loss(self):
        current = vector()
        after = vector((("a", "AC"), ("b", "WA")), b"y")
        result = compare_execution(current, after)
        self.assertEqual(result.status, "stable")
        self.assertEqual(result.gained_testcases, ("a",))
        self.assertEqual(result.lost_testcases, ("b",))
        self.assertFalse(result.candidate_all_ac)
        nominal = compare_execution(vector((("a", "CE"), ("b", "RE"))), vector((("a", "WA"), ("b", "TLE")), b"y"))
        self.assertEqual(nominal.gained_testcases, ())
        self.assertEqual(nominal.lost_testcases, ())

    def test_missing_partial_unknown_unstable_never_zero(self):
        full = vector()
        cases = [dataclasses.replace(full, blocks=()), dataclasses.replace(full, blocks=full.blocks[:3])]
        for changes in ({"complete": False}, {"outcomes": (("a", "WA"),)},
                        {"outcomes": (("a", "runner_failure"), ("b", "AC"))},
                        {"outcomes": (("a", "TLE"), ("b", "AC"))}):
            cases.append(dataclasses.replace(full, blocks=(dataclasses.replace(full.blocks[0], **changes),) + full.blocks[1:]))
        for incomplete in cases:
            with self.subTest(incomplete=incomplete):
                result = compare_execution(full, incomplete)
                self.assertEqual(result.status, "unknown")
                self.assertIsNone(result.gained_testcases)
                self.assertIsNone(result.lost_testcases)
                self.assertIsNone(result.candidate_all_ac)

    def test_context_integrity_worker_order_duplicates(self):
        full = vector()
        for changes in ({"workers": 8}, {"runtime_sha256": "0" * 64}, {"universe_sha256": "0" * 64},
                        {"outcomes": (("unknown-case", "AC"),)}):
            with self.assertRaises(ValueError):
                dataclasses.replace(full, blocks=(dataclasses.replace(full.blocks[0], **changes),) + full.blocks[1:])
        with self.assertRaises(ValueError):
            dataclasses.replace(full.blocks[0], outcomes=(("a", "AC"), ("a", "WA")))
        with self.assertRaises(ValueError):
            compare_execution(full, dataclasses.replace(full, testcase_ids=("b", "a")))

    def test_hash_chain_changes_on_source_and_execution(self):
        first = vector()
        second = vector(source=b" x")
        self.assertNotEqual(first.seal_sha256, second.seal_sha256)
        evidence = compare_execution(first, second)
        self.assertEqual(evidence.current_vector_sha256, first.seal_sha256)
        self.assertEqual(evidence.candidate_vector_sha256, second.seal_sha256)

    def test_source_mixup_and_bank_binding_rejected(self):
        first = vector()
        with self.assertRaises(ValueError):
            dataclasses.replace(first, blocks=(dataclasses.replace(first.blocks[0], source_sha256=source_hash(b"different")),) + first.blocks[1:])
        with self.assertRaises(ValueError):
            compare_bank_candidate(bank(), source_hash(b" x"), first, vector(source=b"different"))
        self.assertEqual(compare_bank_candidate(bank(), source_hash(b" x"), first, vector(source=b" x")).status, "stable")
        observation = PilotObservation("p", observation_source(), ())
        self.assertEqual(len(RankingExample(observation, bank()).seal_sha256), 64)
        with self.assertRaises(ValueError):
            RankingExample(dataclasses.replace(observation, problem_id="other"), bank())

    def test_noop_cross_vector_disagreement_is_unknown(self):
        result = compare_bank_candidate(bank(), source_hash(b"x"), vector(), vector((("a", "AC"), ("b", "AC"))))
        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.gained_testcases)
        self.assertIsNone(result.lost_testcases)


if __name__ == "__main__":
    unittest.main()
