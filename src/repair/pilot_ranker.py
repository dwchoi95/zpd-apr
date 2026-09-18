"""Untrained, label-free engineering prototype; not an empirical repair model.

All prior transitions are retained. Caller-supplied coefficients and thresholds
are mandatory: predicted risk is NOT a guarantee of actual non-regression.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import re
from typing import Mapping

from .pilot_contracts import CandidateBank, ObservationSource, PilotObservation


def _tokens(source: bytes) -> Counter:
    # Byte lexical bags preserve undecodable source and do not execute code.
    return Counter(re.findall(rb"[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]", source))


def _edit(before: bytes, after: bytes) -> Counter:
    a, b = _tokens(before), _tokens(after)
    return Counter({("add", t): n for t, n in (b - a).items()}) + Counter(
        {("remove", t): n for t, n in (a - b).items()})


def _overlap(a: Counter, b: Counter) -> float:
    return sum((a & b).values()) / max(1, sum(a.values()))


def _reverse(edit: Counter) -> Counter:
    return Counter({("remove" if action == "add" else "add", t): n
                    for (action, t), n in edit.items()})


def features(observation: PilotObservation, candidate_source: bytes, *,
             history: tuple[ObservationSource, ...]) -> dict[str, float]:
    """Explicit history: () for C, authentic prior for H, swapped donor for U.

    IDs and verdicts are never model features. IDs validate unique observations.
    H authenticity and U donor eligibility require a caller-side sealed manifest;
    accepting a history here does not certify either condition.
    Histories must be strictly chronological
    and before current. Exact byte equality is used for repetition/reversion;
    lexical edit bags are deliberately a lossy engineering representation.
    """
    if type(observation) is not PilotObservation or type(candidate_source) is not bytes:
        raise TypeError("only typed observation and candidate bytes are accepted")
    if type(history) is not tuple or any(type(x) is not ObservationSource for x in history):
        raise TypeError("history must contain observation sources only")
    identities = [x.submission_id for x in history] + [observation.current.submission_id]
    if len(set(identities)) != len(identities):
        raise ValueError("duplicate observation identities")
    times = [x.timestamp for x in history] + [observation.current.timestamp]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("history must be strictly chronological and prior to current")
    current = observation.current.source
    edit = _edit(current, candidate_source)
    result = {
        "bias": 1.0,
        "candidate_edit_tokens": float(sum(edit.values())),
        "candidate_byte_length_delta": float(len(candidate_source) - len(current)),
        "candidate_is_noop": float(current == candidate_source),
        "history_count": float(len(history)),
        "history_candidate_exact_fraction": 0.0,
        "history_candidate_reversion_weight": 0.0,
        "history_edit_overlap": 0.0,
        "history_reverse_edit_overlap": 0.0,
    }
    if not history:
        return result
    result["history_candidate_exact_fraction"] = sum(
        x.source == candidate_source for x in history) / len(history)
    sources = [x.source for x in history] + [current]
    weights = [1.0 / (len(history) - i) for i in range(len(history))]
    weight_sum = sum(weights)
    for previous, following, weight in zip(sources, sources[1:], weights):
        transition = _edit(previous, following)
        result["history_edit_overlap"] += weight * _overlap(edit, transition) / weight_sum
        result["history_reverse_edit_overlap"] += weight * _overlap(edit, _reverse(transition)) / weight_sum
        result["history_candidate_reversion_weight"] += (
            weight * float(candidate_source == previous and previous != current) / weight_sum)
    return result


@dataclass(frozen=True)
class TwoChannelCoefficients:
    risk: Mapping[str, float]
    gain: Mapping[str, float]

    def __post_init__(self) -> None:
        # Defensive immutable copies, no default/untrained coefficient values.
        from types import MappingProxyType
        for name in ("risk", "gain"):
            values = dict(getattr(self, name))
            if not values or any(not isinstance(k, str) or not math.isfinite(v)
                                 for k, v in values.items()):
                raise ValueError("explicit finite nonempty coefficient maps required")
            object.__setattr__(self, name, MappingProxyType(values))


@dataclass(frozen=True)
class CandidateScore:
    source_sha256: str
    predicted_risk: float
    predicted_gain: float
    eligible: bool
    is_noop: bool


@dataclass(frozen=True)
class Selection:
    selected_source_sha256: str
    abstained: bool
    scores: tuple[CandidateScore, ...]


def _linear(weights: Mapping[str, float], values: Mapping[str, float]) -> float:
    if set(weights) - set(values):
        raise ValueError("unknown feature coefficient")
    value = sum(weight * values[key] for key, weight in weights.items())
    if not math.isfinite(value):
        raise ValueError("non-finite prediction")
    return value


def select(observation: PilotObservation, bank: CandidateBank, *,
           history: tuple[ObservationSource, ...], coefficients: TwoChannelCoefficients,
           risk_threshold: float, minimum_gain: float) -> Selection:
    """Highest predicted gain below supplied risk threshold, otherwise no-op.

    Scores are engineering predictions, not observed test outcomes. Risk uses a
    sigmoid linear score. Ties use exact-source SHA256, not source order or IDs.
    No-op is an abstention fallback, not a fabricated model risk/gain prediction.
    """
    if type(bank) is not CandidateBank or type(observation) is not PilotObservation:
        raise TypeError("strict observation/bank contract required")
    if bank.problem_id != observation.problem_id or bank.current_source != observation.current.source:
        raise ValueError("same problem and exact current source bank required")
    if not math.isfinite(risk_threshold) or not 0 <= risk_threshold <= 1 or not math.isfinite(minimum_gain):
        raise ValueError("finite explicit thresholds required")
    scores = []
    for candidate in bank.candidates:
        values = features(observation, candidate.source, history=history)
        logit = _linear(coefficients.risk, values)
        risk = 1 / (1 + math.exp(-logit)) if logit >= 0 else math.exp(logit) / (1 + math.exp(logit))
        gain = _linear(coefficients.gain, values)
        scores.append(CandidateScore(candidate.source_sha256, risk, gain,
                                    not candidate.is_noop and risk <= risk_threshold and gain > minimum_gain,
                                    candidate.is_noop))
    eligible = [score for score in scores if score.eligible]
    winner = (min(eligible, key=lambda s: (-s.predicted_gain, s.source_sha256)) if eligible
              else next(score for score in scores if score.is_noop))
    return Selection(winner.source_sha256, winner.is_noop, tuple(scores))
