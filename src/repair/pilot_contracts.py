"""Engineering-only repair-pilot contracts. Never executes submitted source.

Hash integrity is not evidence of repair or learner benefit. These contracts do
not authorize generation, execution, training, or opening held-out outcomes.
"""
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
import re
from typing import Mapping


def source_hash(source: bytes) -> str:
    if not isinstance(source, bytes):
        raise ValueError("source must be immutable exact bytes")
    return hashlib.sha256(source).hexdigest()


def canonical_hash(value) -> str:
    def encode(obj):
        if is_dataclass(obj):
            return encode(asdict(obj))
        if isinstance(obj, bytes):
            return {"exact_bytes_hex": obj.hex()}
        if isinstance(obj, Mapping):
            return {key: encode(val) for key, val in obj.items()}
        if isinstance(obj, (tuple, list)):
            return [encode(val) for val in obj]
        return obj
    return hashlib.sha256(json.dumps(encode(value), sort_keys=True,
        separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("expected lowercase SHA256")


def _fields(value, required):
    if not isinstance(value, Mapping) or set(value) != set(required):
        raise ValueError("observation allowlist violation or missing fields")


@dataclass(frozen=True)
class ObservationSource:
    submission_id: str
    timestamp: float
    source: bytes
    source_sha256: str
    verdict: str

    def __post_init__(self):
        if not isinstance(self.submission_id, str) or not self.submission_id:
            raise ValueError("submission ID required")
        if isinstance(self.timestamp, bool) or not isinstance(self.timestamp, (int, float)) or not math.isfinite(self.timestamp):
            raise ValueError("finite timestamp required")
        if source_hash(self.source) != self.source_sha256:
            raise ValueError("source hash mismatch")
        if not isinstance(self.verdict, str) or not self.verdict:
            raise ValueError("nominal verdict required")

    @classmethod
    def from_mapping(cls, value):
        _fields(value, cls.__dataclass_fields__)
        return cls(**value)


@dataclass(frozen=True)
class PilotObservation:
    problem_id: str
    current: ObservationSource
    prior: tuple[ObservationSource, ...]

    def __post_init__(self):
        if not isinstance(self.problem_id, str) or not self.problem_id:
            raise ValueError("problem ID required")
        if not isinstance(self.prior, tuple) or not all(isinstance(v, ObservationSource) for v in (*self.prior, self.current)):
            raise ValueError("immutable observed sources required")
        rows = (*self.prior, self.current)
        if len({v.submission_id for v in rows}) != len(rows):
            raise ValueError("duplicate observation ID")
        if any(a.timestamp >= b.timestamp for a, b in zip(rows, rows[1:])):
            raise ValueError("strictly increasing past/current timestamps required")

    @classmethod
    def from_mapping(cls, value):
        _fields(value, cls.__dataclass_fields__)
        return cls(value["problem_id"], ObservationSource.from_mapping(value["current"]),
                   tuple(ObservationSource.from_mapping(v) for v in value["prior"]))

    @property
    def observation_sha256(self):
        return canonical_hash(self)


TERMINAL_ATTEMPT_STATUSES = frozenset({"success", "generation_failure", "format_failure", "resource_failure", "unknown_failure"})


@dataclass(frozen=True)
class CandidateAttempt:
    index: int
    seed: int
    status: str
    source: bytes | None = None
    error: str | None = None

    def __post_init__(self):
        if type(self.index) is not int or type(self.seed) is not int or not 0 <= self.index < 8:
            raise ValueError("fixed attempt index/seed required")
        if self.status not in TERMINAL_ATTEMPT_STATUSES:
            raise ValueError("attempt must be terminal; no retry-fill")
        if self.status == "success":
            source_hash(self.source)
            if self.error is not None:
                raise ValueError("successful attempt cannot have an error")
        elif self.source is not None or not isinstance(self.error, str) or not self.error:
            raise ValueError("failure requires reason and no executable partial source")


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    source: bytes
    source_sha256: str
    is_noop: bool

    def __post_init__(self):
        if type(self.is_noop) is not bool:
            raise ValueError("is_noop must be boolean")
        if source_hash(self.source) != self.source_sha256 or self.candidate_id != self.source_sha256:
            raise ValueError("candidate identity must bind exact source")


@dataclass(frozen=True)
class CandidateBank:
    problem_id: str
    current_source: bytes
    generator_config_sha256: str
    seeds: tuple[int, ...]
    attempts: tuple[CandidateAttempt, ...]

    def __post_init__(self):
        if not isinstance(self.problem_id, str) or not self.problem_id:
            raise ValueError("problem ID required")
        source_hash(self.current_source)
        _sha(self.generator_config_sha256)
        if not isinstance(self.seeds, tuple) or len(self.seeds) != 8 or any(type(v) is not int for v in self.seeds):
            raise ValueError("exactly eight predeclared seeds required")
        if not isinstance(self.attempts, tuple) or len(self.attempts) != 8:
            raise ValueError("exactly eight terminal attempts required for sealing")
        for i, attempt in enumerate(self.attempts):
            if not isinstance(attempt, CandidateAttempt) or attempt.index != i or attempt.seed != self.seeds[i]:
                raise ValueError("attempt order/seed differs from fixed ledger")

    @property
    def key(self):
        return (self.problem_id, source_hash(self.current_source), self.generator_config_sha256)

    @property
    def seal_sha256(self):
        return canonical_hash(self)

    @property
    def candidates(self):
        # Deduplicate exact bytes, not normalization or stripped text. The full
        # attempts ledger remains in the seal, including duplicates/failures.
        unique = {self.current_source: True}
        for attempt in self.attempts:
            if attempt.status == "success":
                unique.setdefault(attempt.source, False)
        return tuple(Candidate(source_hash(src), src, source_hash(src), noop)
                     for src, noop in unique.items())


KNOWN_OUTCOMES = frozenset({"AC", "WA", "CE", "RE", "TLE", "MLE", "OLE"})


@dataclass(frozen=True)
class ExecutionBlock:
    workers: int
    universe_sha256: str
    runtime_sha256: str
    outcomes: tuple[tuple[str, str], ...]
    complete: bool
    source_sha256: str

    def __post_init__(self):
        _sha(self.universe_sha256)
        _sha(self.runtime_sha256)
        _sha(self.source_sha256)
        if type(self.workers) is not int or self.workers not in (1, 8) or type(self.complete) is not bool:
            raise ValueError("invalid execution block")
        if not isinstance(self.outcomes, tuple) or any(not isinstance(v, tuple) or len(v) != 2 or not all(isinstance(x, str) and x for x in v) for v in self.outcomes):
            raise ValueError("immutable testcase outcome pairs required")
        if len({k for k, _ in self.outcomes}) != len(self.outcomes):
            raise ValueError("duplicate testcase ID")


@dataclass(frozen=True)
class ExecutionVector:
    source_sha256: str
    universe_sha256: str
    runtime_sha256: str
    testcase_ids: tuple[str, ...]
    blocks: tuple[ExecutionBlock, ...]

    def __post_init__(self):
        for value in (self.source_sha256, self.universe_sha256, self.runtime_sha256):
            _sha(value)
        if not isinstance(self.testcase_ids, tuple) or not self.testcase_ids or any(not isinstance(x, str) or not x for x in self.testcase_ids) or len(set(self.testcase_ids)) != len(self.testcase_ids):
            raise ValueError("nonempty unique testcase universe required")
        if not isinstance(self.blocks, tuple) or len(self.blocks) > 4:
            raise ValueError("at most four replay blocks required")
        for i, block in enumerate(self.blocks):
            if not isinstance(block, ExecutionBlock) or block.workers != (1, 8, 8, 1)[i]:
                raise ValueError("replay worker order must be 1,8,8,1")
            if block.universe_sha256 != self.universe_sha256 or block.runtime_sha256 != self.runtime_sha256:
                raise ValueError("inconsistent universe/runtime")
            if block.source_sha256 != self.source_sha256:
                raise ValueError("replay source differs from vector source")
            if not set(dict(block.outcomes)) <= set(self.testcase_ids):
                raise ValueError("testcase outside declared universe")

    @property
    def stable_outcomes(self):
        if len(self.blocks) != 4:
            return None
        normalized = []
        for block in self.blocks:
            outcomes = dict(block.outcomes)
            if not block.complete or set(outcomes) != set(self.testcase_ids) or any(v not in KNOWN_OUTCOMES for v in outcomes.values()):
                return None
            normalized.append(tuple(outcomes[k] for k in self.testcase_ids))
        return normalized[0] if all(v == normalized[0] for v in normalized) else None

    @property
    def seal_sha256(self):
        return canonical_hash(self)


@dataclass(frozen=True)
class GainLossEvidence:
    status: str
    gained_testcases: tuple[str, ...] | None
    lost_testcases: tuple[str, ...] | None
    candidate_all_ac: bool | None
    current_vector_sha256: str
    candidate_vector_sha256: str


def compare_execution(current: ExecutionVector, candidate: ExecutionVector) -> GainLossEvidence:
    """Compare supplied vectors, not bank membership or execution authenticity.

    The external evaluator must verify that declared universe/runtime hashes
    bind the actual inputs, expected outputs, limits, normalizer and runner.
    """
    if (current.universe_sha256, current.runtime_sha256, current.testcase_ids) != (candidate.universe_sha256, candidate.runtime_sha256, candidate.testcase_ids):
        raise ValueError("current/candidate execution contexts must match")
    before, after = current.stable_outcomes, candidate.stable_outcomes
    hashes = (current.seal_sha256, candidate.seal_sha256)
    if before is None or after is None or (current.source_sha256 == candidate.source_sha256 and before != after):
        return GainLossEvidence("unknown", None, None, None, *hashes)
    gain = tuple(k for k, a, b in zip(current.testcase_ids, before, after) if a != "AC" and b == "AC")
    loss = tuple(k for k, a, b in zip(current.testcase_ids, before, after) if a == "AC" and b != "AC")
    return GainLossEvidence("stable", gain, loss, all(v == "AC" for v in after), *hashes)


@dataclass(frozen=True)
class RankingExample:
    """Label-free binding of one observation to its common candidate bank."""
    observation: PilotObservation
    bank: CandidateBank

    def __post_init__(self):
        if self.observation.problem_id != self.bank.problem_id or self.observation.current.source != self.bank.current_source:
            raise ValueError("observation does not match common bank")

    @property
    def seal_sha256(self):
        return canonical_hash({"observation": self.observation.observation_sha256,
                               "bank": self.bank.seal_sha256})


def compare_bank_candidate(bank: CandidateBank, candidate_id: str,
                           current: ExecutionVector, candidate: ExecutionVector) -> GainLossEvidence:
    candidates = {c.candidate_id: c for c in bank.candidates}
    if candidate_id not in candidates:
        raise ValueError("candidate not in sealed bank")
    if current.source_sha256 != source_hash(bank.current_source) or candidate.source_sha256 != candidates[candidate_id].source_sha256:
        raise ValueError("execution source does not match bank member")
    return compare_execution(current, candidate)
