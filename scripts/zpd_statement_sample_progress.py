"""Pure prospective32 statement-sample moments; no I/O, fit or execution.

Callers must independently authenticate replay artifacts before supplying
ExecutionVectors. Hashes and this pure encoder cannot certify execution. Only
observed-source vectors are consulted; candidate execution is never requested.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import re
from types import MappingProxyType
from typing import Mapping

import numpy as np

from scripts import zpd_repair_directed_history as directed
from src.repair.pilot_contracts import ExecutionVector

VERSION = 'statement_sample_centered_progress32_v1'
ARMS = ('H', 'Jm', 'HS', 'U', 'L', 'CF')
STATES = ('00', '01', '10', '11')
DIMENSION = 32
SCALE = math.sqrt(12.0)
KNOWN = frozenset(('AC', 'WA', 'CE', 'RE', 'TLE'))


def _sha(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('exact SHA256 identity required')


def _freeze(value, dtype=np.float64):
    result = np.array(value, dtype=dtype, copy=True)
    result.flags.writeable = False
    return result


@dataclass(frozen=True)
class Universe:
    problem_id: str
    sample_set_sha256: str
    runtime_sha256: str
    case_ids: tuple[str, ...]

    def __post_init__(self):
        _sha(self.sample_set_sha256); _sha(self.runtime_sha256)
        if (type(self.problem_id) is not str or not self.problem_id
                or type(self.case_ids) is not tuple
                or any(type(c) is not str or not c for c in self.case_ids)
                or len(set(self.case_ids)) != len(self.case_ids)):
            raise ValueError('explicit full problem sample universe required')


def source_key(universe, code, language):
    directed.semantic._language(language)
    source = directed.semantic._code_bytes(code)
    return universe.problem_id, hashlib.sha256(source).hexdigest(), language


def _feedback(universe, code, language, vectors):
    key = source_key(universe, code, language)
    vector = vectors.get(key)
    if not universe.case_ids:
        if vector is not None:
            raise ValueError('an unavailable empty suite cannot have an execution vector')
        return None, 'unavailable_samples'
    if vector is None:
        return None, 'unavailable_non_python' if language != 'Python' else 'missing_feedback'
    if not isinstance(vector, ExecutionVector) or language != 'Python':
        raise ValueError('only declared-Python observed ExecutionVectors are permitted')
    if (vector.source_sha256 != key[1] or vector.universe_sha256 != universe.sample_set_sha256
            or vector.runtime_sha256 != universe.runtime_sha256 or vector.testcase_ids != universe.case_ids):
        raise ValueError('observed feedback source/universe/runtime identity differs')
    for block in vector.blocks:
        if tuple(case for case, _ in block.outcomes) != universe.case_ids[:len(block.outcomes)]:
            raise ValueError('original ordered sample identities required')
        if block.complete and len(block.outcomes) != len(universe.case_ids):
            raise ValueError('claimed complete feedback must contain every sample')
        if any(verdict not in KNOWN | {'UNKNOWN'} for _, verdict in block.outcomes):
            raise ValueError('outside the released replay verdict contract')
    outcomes = vector.stable_outcomes
    if outcomes is None:
        return None, 'incomplete_unknown_or_unstable_full_vector'
    return tuple(v == 'AC' for v in outcomes), None


@dataclass(frozen=True)
class Moments:
    current: np.ndarray
    joint: np.ndarray
    marginal: np.ndarray
    residual: np.ndarray
    marginal_residual: np.ndarray
    wa_offdiagonal: np.ndarray
    mask: np.ndarray
    weights: np.ndarray
    opportunity: np.ndarray
    similarities: np.ndarray
    paired_counts: tuple[tuple[int, int, int, int] | None, ...]
    current_counts: tuple[int, int, int, int] | None
    source_feedback_reasons: tuple[str | None, ...]
    permutation_indices: tuple[int, ...]
    candidate_available: bool
    candidate_mass: int
    history_masses: tuple[int, ...]


@dataclass(frozen=True)
class ProgressFeatures:
    arms: Mapping[str, np.ndarray]
    moments: Mapping[str, Moments]
    wa_offdiagonal_contribution: np.ndarray
    current_feedback_available: bool
    current_feedback_reason: str | None


def conditional_weights(mask):
    """Normalize original full-position weights, then condition without compaction."""
    n = len(mask)
    if any(type(value) not in (bool, np.bool_) for value in mask):
        raise ValueError('explicit Boolean availability mask required')
    result = np.zeros((2, n), dtype=np.float64)
    opportunity = np.zeros(2, dtype=np.float64)
    if n:
        raw = ([1.0] * n, [1.0 / (n-t) for t in range(n)])
        for w in range(2):
            total = math.fsum(raw[w])
            original = [float(value / total) for value in raw[w]]
            active = [value if mask[t] else 0.0 for t, value in enumerate(original)]
            opportunity[w] = math.fsum(active)
            if opportunity[w]:
                result[w] = [float(value / opportunity[w]) for value in active]
    return result, opportunity


def _moments(current_code, candidate_code, current_verdict, history, current_timestamp,
             universe, vectors, current_bits, *, shuffled=False, shuffle_key=''):
    directed.semantic._validate_observation(current_code, current_verdict, history,
                                            current_timestamp, 'HS' if shuffled else 'H')
    order = (directed.semantic.permutation_indices(len(history), shuffle_key)
             if shuffled else tuple(range(len(history))))
    sequence = [history[i] for i in order] + [dict(code=current_code, verdict=current_verdict,
                                                   timestamp=current_timestamp, language='Python')]
    signatures = [directed.signature(row['code'], row['language']) for row in sequence]
    delta = directed.delta_signatures(signatures[-1], directed.signature(candidate_code))
    feedback = [_feedback(universe, row['code'], row['language'], vectors) for row in sequence]
    n, k = len(history), len(universe.case_ids)
    similarities = np.zeros((n, 2), dtype=np.float64); mask = np.zeros(n, dtype=bool)
    counts = []; masses = []; nominal_wa = []
    n0 = None if current_bits is None else (k-sum(current_bits), 0, 0, sum(current_bits))
    for t in range(n):
        hist = directed.delta_signatures(signatures[t], signatures[t+1])
        match = directed.match(delta, hist)
        similarities[t] = match.same, match.reverse; masses.append(hist.mass)
        left, right = feedback[t][0], feedback[t+1][0]
        mask[t] = current_bits is not None and left is not None and right is not None and match.available
        pair = None
        if mask[t]:
            value = [0, 0, 0, 0]
            for a, b in zip(left, right, strict=True):
                value[2*int(a)+int(b)] += 1
            pair = tuple(value)
        counts.append(pair)
        nominal_wa.append(all(directed.semantic._verdict(sequence[i]['verdict']) == 'WA'
                              for i in (t, t+1)))
    weights, opportunity = conditional_weights(mask)
    arrays = [np.zeros((2, 2, 4), dtype=np.float64) for _ in range(6)]
    current, joint, marginal, residual, marginal_residual, contribution = arrays
    if n0 is not None:
        eligible = [t for t in range(n) if mask[t]]
        for w in range(2):
            for d in range(2):
                mean_s = math.fsum(float(weights[w,t] * similarities[t,d]) for t in eligible)
                for state in range(4):
                    current[w,d,state] = float(mean_s * (n0[state] / k))
                    q = {t: counts[t][state] / k for t in eligible}
                    # Subtract signed Python integers first, not rounded moments.
                    change = {t: (counts[t][state] - n0[state]) / k for t in eligible}
                    joint[w,d,state] = math.fsum(float(weights[w,t] * similarities[t,d] * q[t]) for t in eligible)
                    marginal[w,d,state] = float(mean_s * math.fsum(float(weights[w,t] * q[t]) for t in eligible))
                    residual[w,d,state] = math.fsum(float(weights[w,t] * similarities[t,d] * change[t]) for t in eligible)
                    marginal_residual[w,d,state] = float(mean_s * math.fsum(float(weights[w,t] * change[t]) for t in eligible))
                    if state in (1, 2):
                        contribution[w,d,state] = math.fsum(float(weights[w,t] * similarities[t,d] * q[t])
                            for t in eligible if nominal_wa[t] and counts[t][1]+counts[t][2] > 0)
    return Moments(*(_freeze(value) for value in arrays), _freeze(mask, bool), _freeze(weights),
        _freeze(opportunity), _freeze(similarities), tuple(counts), n0,
        tuple(reason for _,reason in feedback), order, delta.available, delta.mass, tuple(masses))


def candidate_features(current_code, candidate_code, current_verdict, history, current_timestamp,
                       *, universe, vectors, donor_history, shuffle_key):
    """All six arms share authentic G; caller supplies unchanged certified donors.

    There is no history/sample cap, selection by labels, scorer access or fitted
    transform. The latest-only arm affects its residual, not the shared G block.
    Unknown current feedback yields every arm's exact zero vector.
    """
    if not isinstance(universe, Universe) or not isinstance(vectors, Mapping) or type(shuffle_key) is not str:
        raise ValueError('explicit universe, observed-only vectors and frozen shuffle key required')
    directed.semantic._code_bytes(candidate_code)
    directed.semantic._validate_observation(current_code,current_verdict,history,current_timestamp,'H')
    directed.semantic._validate_observation(current_code,current_verdict,donor_history,current_timestamp,'H')
    current_bits, reason = _feedback(universe,current_code,'Python',vectors)
    moments = {}
    for arm, supplied in (('H',history), ('HS',history), ('U',donor_history), ('L',history[-1:])):
        moments[arm] = _moments(current_code,candidate_code,current_verdict,supplied,current_timestamp,
            universe,vectors,current_bits,shuffled=arm=='HS',shuffle_key=shuffle_key)
    authentic = moments['H']; arms = {}
    for arm in ARMS:
        residual = (np.zeros((2,2,4), dtype=np.float64) if arm=='CF' else
                    authentic.marginal_residual if arm=='Jm' else moments[arm].residual)
        arms[arm] = _freeze(np.concatenate((authentic.current.reshape(-1),residual.reshape(-1))) / SCALE)
    contribution = _freeze(np.concatenate((np.zeros(16),authentic.wa_offdiagonal.reshape(-1))) / SCALE)
    return ProgressFeatures(MappingProxyType(arms),MappingProxyType(moments),contribution,
                            current_bits is not None,reason)


def configuration():
    return dict(version=VERSION,dimension=DIMENSION,arms=list(ARMS),states=list(STATES),
        scale_divisor='binary64_math.sqrt(12.0)',layout='concat_current16_centered16_C_order',
        weightings=list(directed.WEIGHTINGS),directions=list(directed.DIRECTIONS),
        arithmetic='signed_integer_counts_then_float64_division_math.fsum_binary64_terms',
        masks='full_sample_stable_current_and_both_endpoints_and_AST_available',
        current_control='common_authentic_static_alignment_current_feedback_G_plus_zero_tail',
        unknown='unavailable_never_zero_test_failure',maximum_candidate_l2=2.**-.5,
        maximum_pair_l2=1.0,fitting_performed=False,execution_performed=False,
        feature_authority='caller_must_authenticate_separate_replay_seals')
