"""Pure candidate-directed AST-local history/nominal-feedback representation.

No fitting, I/O, execution, target access, hashing into a feature space, source
normalization, semantic alignment, or history truncation. Exact typed AST paths
retain list positions, identifiers and literal values. They are syntactic loci,
not claims that a moved node or a similar program has the same semantic role.
"""
from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

import numpy as np

from scripts import zpd_history_action_encoder as semantic

VERSION = 'candidate_directed_exact_ast_history_v1'
VERDICTS = ('AC', 'CE', 'OTHER', 'RE', 'RESOURCE', 'WA')
VERDICT_PAIRS = tuple(a+'=>'+b for a in VERDICTS for b in VERDICTS)
PAIR_INDEX = {pair: i for i, pair in enumerate(VERDICT_PAIRS)}
WEIGHTINGS = ('uniform', 'reciprocal_recency')
DIRECTIONS = ('same', 'reverse')
DIMENSION = 144
SCALE = 2.
AST_FEATURE_VERSION = (3, 10)


@dataclass(frozen=True)
class Signature:
    available: bool
    counts: Mapping
    reason: str | None


@dataclass(frozen=True)
class Delta:
    available: bool
    additions: Mapping
    removals: Mapping
    mass: int


@dataclass(frozen=True)
class Match:
    available: bool
    same: float
    reverse: float


@dataclass(frozen=True)
class DirectedFeatures:
    vector: np.ndarray
    joint: np.ndarray
    marginal: np.ndarray
    opportunity: np.ndarray
    applicable_mask: np.ndarray
    similarities: np.ndarray
    pair_indices: np.ndarray
    permutation_indices: tuple[int, ...]
    candidate_available: bool
    candidate_mass: int
    history_masses: np.ndarray
    transition_count: int
    applicable_count: int


def configuration():
    return dict(version=VERSION, dimension=DIMENSION, weightings=list(WEIGHTINGS),
        directions=list(DIRECTIONS), verdict_pairs=list(VERDICT_PAIRS),
        flatten_order='weight_direction_verdict_pair_C', scale_divisor=SCALE,
        signature='exact_typed_field_list_index_path_node_class_immediate_scalar',
        endpoint_parse='ast.parse_exact_utf8_bytes_declared_Python_only',
        ast_feature_version=list(AST_FEATURE_VERSION),
        delta='after_counter_minus_before_counter_common_cancelled',
        similarity='signed_Dice_same_and_reversed_history_delta',
        conditioning='candidate_and_history_endpoints_AST_available_including_zero_mass',
        recency='inverse_transition_distance_in_supplied_sequence_before_mask_conditioning',
        shuffle='frozen_prior_only_permutation_current_anchored',
        marginal='conditional_similarity_mean_times_conditional_verdict_pair_mean',
        final_normalization=False, fitted_transform=False, future_targets_used=False,
        semantic_alignment_claim=False, maximum_vector_l2=2.**-.5,
        maximum_pair_difference_l2=1.)


def _atom(value):
    """Typed exact AST scalar identity; no repr of a subtree is ever built."""
    if value is None: return ('None', '')
    if value is Ellipsis: return ('Ellipsis', '')
    if type(value) is bool: return ('bool', str(value))
    # Hex is exact and is not subject to Python's decimal int-to-string cap.
    if type(value) is int: return ('int', hex(value))
    if type(value) is float: return ('float', value.hex())
    if type(value) is complex: return ('complex', value.real.hex(), value.imag.hex())
    if type(value) is str: return ('str', value)
    if type(value) is bytes: return ('bytes', value)
    raise ValueError('unsupported AST scalar type: '+type(value).__name__)


def signature(code: str, language: str = 'Python') -> Signature:
    """Iterative local-node walk; positions/comments/formatting are not keys.

    Path tuples contain typed field and list-index steps, not subtree dumps.
    Storage is proportional to the sum of explicit path lengths, not to copies
    of complete subtrees. A parse failure is unavailable, never lexical fallback.
    """
    data = semantic._code_bytes(code)
    semantic._language(language)
    if language != 'Python':
        return Signature(False, MappingProxyType({}), 'non_python')
    try:
        tree = ast.parse(data, mode='exec', feature_version=AST_FEATURE_VERSION)
    except (SyntaxError, ValueError, UnicodeError, LookupError, RecursionError):
        return Signature(False, MappingProxyType({}), 'parse_unavailable')
    counts = Counter()
    stack = [(tree, ())]
    while stack:
        node, path = stack.pop()
        scalars = []
        for field, value in ast.iter_fields(node):
            child_path = path+(('field', type(node).__name__, field),)
            if isinstance(value, ast.AST):
                stack.append((value, child_path))
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    if isinstance(child, ast.AST):
                        stack.append((child, child_path+(('index', index),)))
                    else:
                        scalars.append((field, ('index', index), _atom(child)))
            else:
                scalars.append((field, ('scalar',), _atom(value)))
        counts[(path, type(node).__name__, tuple(scalars))] += 1
    return Signature(True, MappingProxyType(dict(counts)), None)


def delta_signatures(before: Signature, after: Signature) -> Delta:
    if not isinstance(before, Signature) or not isinstance(after, Signature):
        raise TypeError('explicit source signatures required')
    if not before.available or not after.available:
        return Delta(False, MappingProxyType({}), MappingProxyType({}), 0)
    additions = Counter(after.counts)-Counter(before.counts)
    removals = Counter(before.counts)-Counter(after.counts)
    return Delta(True, MappingProxyType(dict(additions)), MappingProxyType(dict(removals)),
                 sum(additions.values())+sum(removals.values()))


def delta(before_code, after_code, before_language='Python', after_language='Python'):
    return delta_signatures(signature(before_code, before_language), signature(after_code, after_language))


def match(candidate: Delta, history: Delta) -> Match:
    """Signed Dice; common cancellation makes same + reverse <= 1.

    Every key has only one sign per delta. Its same/reverse overlap therefore
    occurs at most once, and min(a,b) <= (a+b)/2. Zero mass remains applicable
    when both deltas are available, but carries zero directional similarity.
    """
    if not isinstance(candidate, Delta) or not isinstance(history, Delta):
        raise TypeError('explicit signed deltas required')
    if not candidate.available or not history.available: return Match(False, 0., 0.)
    if not candidate.mass or not history.mass: return Match(True, 0., 0.)
    def overlap(a, b): return sum(min(count, b.get(key, 0)) for key, count in a.items())
    same = overlap(candidate.additions, history.additions)+overlap(candidate.removals, history.removals)
    reverse = overlap(candidate.additions, history.removals)+overlap(candidate.removals, history.additions)
    denominator = candidate.mass+history.mass
    return Match(True, 2.*same/denominator, 2.*reverse/denominator)


def _aggregate(similarities, applicable, pairs):
    n = len(pairs)
    joint = np.zeros((2, 2, 36), dtype=np.float64)
    marginal = np.zeros_like(joint)
    opportunity = np.zeros(2, dtype=np.float64)
    if n:
        weights = np.vstack((np.ones(n, dtype=np.float64), 1./np.arange(n, 0, -1, dtype=np.float64)))
        weights /= weights.sum(axis=1, keepdims=True)
        for weighting in range(2):
            active = weights[weighting]*applicable
            opportunity[weighting] = active.sum()
            if not opportunity[weighting]: continue
            conditional = active/opportunity[weighting]
            feedback_mean = np.zeros(36, dtype=np.float64)
            for i in range(n):
                joint[weighting, :, pairs[i]] += conditional[i]*similarities[i]
                feedback_mean[pairs[i]] += conditional[i]
            similarity_mean = np.sum(conditional[:, None]*similarities, axis=0)
            marginal[weighting] = similarity_mean[:, None]*feedback_mean[None, :]
    return joint, marginal, opportunity


def candidate_features(current_code, candidate_code, current_verdict, history,
                       current_timestamp, *, mode='joint', shuffled=False, shuffle_key=''):
    """All supplied observed transitions; L/U history selection is caller-owned.

    Current/candidate are explicitly declared Python. History records carry
    explicit languages. Validation precedes the frozen HS permutation; authentic
    timestamps are neither rewritten nor used to sort the counterfactual chain.
    All feature arrays are immutable snapshots and no unavailable row is dropped.
    """
    if mode not in ('joint', 'marginal') or type(shuffled) is not bool or type(shuffle_key) is not str:
        raise ValueError('fixed joint/marginal mode and explicit deterministic shuffle controls required')
    semantic._validate_observation(current_code, current_verdict, history, current_timestamp, 'HS' if shuffled else 'H')
    semantic._code_bytes(candidate_code)
    order = semantic.permutation_indices(len(history), shuffle_key) if shuffled else tuple(range(len(history)))
    prior = [history[i] for i in order]
    sequence = [*prior, dict(code=current_code, verdict=current_verdict, timestamp=current_timestamp, language='Python')]
    signatures = [signature(row['code'], row['language']) for row in sequence]
    candidate_delta = delta_signatures(signatures[-1], signature(candidate_code))
    n = len(history)
    similarities = np.zeros((n, 2), dtype=np.float64)
    applicable = np.zeros(n, dtype=bool)
    pairs = np.zeros(n, dtype=np.int64)
    masses = np.zeros(n, dtype=np.int64)
    for i, (before, after) in enumerate(zip(sequence, sequence[1:])):
        historical_delta = delta_signatures(signatures[i], signatures[i+1])
        directional = match(candidate_delta, historical_delta)
        similarities[i] = directional.same, directional.reverse
        applicable[i] = directional.available
        masses[i] = historical_delta.mass
        pairs[i] = PAIR_INDEX[semantic._verdict(before['verdict'])+'=>'+semantic._verdict(after['verdict'])]
    joint, marginal, opportunity = _aggregate(similarities, applicable, pairs)
    vector = (joint if mode == 'joint' else marginal).reshape(-1)/SCALE
    for array in (vector, joint, marginal, opportunity, applicable, similarities, pairs, masses):
        array.flags.writeable = False
    return DirectedFeatures(vector, joint, marginal, opportunity, applicable, similarities, pairs, order,
                            candidate_delta.available, candidate_delta.mass, masses, n, int(applicable.sum()))
