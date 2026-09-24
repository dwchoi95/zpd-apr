"""Pure fold-training pair construction and label-blind fixed-offset scoring.

No paths, loaders, CLI, fit, feature extraction, or assessment live here. The
caller must independently certify the supplied fold IDs, observation-only
features and same-fold frozen base model. A 'train' string alone cannot prove
fold membership. Exact key equality rejects extra labels/banks; it is not an
OS sandbox or a claim that maliciously relabeled inputs can be identified.

Legacy stable preference and natural user/prefix/pair weights are unchanged.
Unknowns and ties supply no preference, but every candidate/bank is retained
in coverage and at inference. Zero interaction differences are NOT dropped.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import math

import numpy as np

from scripts.zpd_repair_fit import Example
from scripts.zpd_repair_pairwise import preference
from scripts.zpd_repair_feedback_offset import DIMENSION, MASS, validate_model
from src.repair.pilot_contracts import CandidateBank, PilotObservation

EVENT_COUNT = 18
VARIATION_TOLERANCE = 1e-12  # diagnostics only; never eligibility or loss weighting


@dataclass(frozen=True)
class CandidateInteractions:
    candidate_ids: tuple[str, ...]
    matrix: np.ndarray
    event_values: np.ndarray
    event_masks: np.ndarray


@dataclass(frozen=True)
class PairData:
    matrix: np.ndarray
    y: np.ndarray
    weights: np.ndarray
    base_margin: np.ndarray
    metadata: dict


class NoInformativePairs(ValueError):
    """Explicit failed cell, retaining the full supplied-bank diagnostics."""

    def __init__(self, metadata):
        super().__init__('no unequal stable training candidate pairs; no fit or fallback')
        self.metadata = metadata


def _exact_mapping(value, keys, name):
    # Plain dictionaries exclude objects that lazily obtain unseen file values.
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(name+' must have exactly the supplied fold/bank keys')


def _candidate_inputs(bank, interaction, base_scores):
    if type(bank) is not CandidateBank or type(interaction) is not CandidateInteractions:
        raise ValueError('exact CandidateBank and CandidateInteractions types required')
    candidates = bank.candidates
    ids = tuple(c.candidate_id for c in candidates)
    if type(interaction.candidate_ids) is not tuple or interaction.candidate_ids != ids:
        raise ValueError('candidate interaction IDs must equal exact bank candidate order')
    n = len(ids)
    for array, shape, dtype, name in (
            (interaction.matrix, (n, DIMENSION), np.dtype('float64'), 'interaction'),
            (interaction.event_values, (n, EVENT_COUNT), np.dtype('float64'), 'events'),
            (interaction.event_masks, (n, EVENT_COUNT), np.dtype('bool'), 'masks')):
        if type(array) is not np.ndarray or array.dtype != dtype or array.shape != shape or not np.isfinite(array).all():
            raise ValueError(name+' must have the fixed finite array shape/dtype')
    if not np.isin(interaction.event_values, [0., 1.]).all():
        raise ValueError('event values must be binary, with availability separately masked')
    _exact_mapping(base_scores, ids, 'base scores')
    if any(type(v) not in (int, float, np.float64) or not math.isfinite(v) for v in base_scores.values()):
        raise ValueError('base scores must be finite real scalars, not booleans or arrays')
    return candidates, np.asarray([base_scores[cid] for cid in ids], dtype=np.float64)


def _label(row, bank_id, bank, candidate):
    core = {'bank_id', 'candidate_id', 'status', 'gain', 'loss', 'all_ac'}
    extra = {'problem_id', 'is_noop', 'n_cases', 'evidence', 'bank_seal_sha256'}
    if type(row) is not dict or set(row) not in (core, core | extra):
        raise ValueError('label field allowlist violation')
    if row['bank_id'] != bank_id or row['candidate_id'] != candidate.candidate_id:
        raise ValueError('label mapping key and row identity disagree')
    key = preference(row)  # deliberately the frozen legacy relation
    if candidate.is_noop and key is not None and (row['gain'] != 0 or row['loss'] != 0):
        raise ValueError('stable no-op must retain zero gain/loss')
    if set(row) == core | extra:
        if (row['problem_id'] != bank.problem_id or row['is_noop'] is not candidate.is_noop
                or row['bank_seal_sha256'] != bank.seal_sha256
                or type(row['n_cases']) is not int or row['n_cases'] <= 0):
            raise ValueError('label bank/evidence provenance mismatch')
        ev = row['evidence']
        fields = {'status', 'gained_testcases', 'lost_testcases', 'candidate_all_ac',
                  'current_vector_sha256', 'candidate_vector_sha256'}
        if (type(ev) is not dict or set(ev) != fields or ev['status'] != row['status']
                or ev['candidate_all_ac'] is not row['all_ac']):
            raise ValueError('label evidence allowlist/status mismatch')
        for name in ('current_vector_sha256', 'candidate_vector_sha256'):
            sha = ev[name]
            if sha is not None and (type(sha) is not str or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha)):
                raise ValueError('evidence vector hash must be SHA256 or null')
        for ids, value in [('gained_testcases', 'gain'), ('lost_testcases', 'loss')]:
            seq = ev[ids]
            if key is None:
                if seq is not None:
                    raise ValueError('unknown evidence must retain null testcase lists')
            elif (type(seq) is not list or any(type(v) is not str or not v for v in seq)
                    or len(set(seq)) != len(seq)
                    or not math.isclose(len(seq)/row['n_cases'], row[value], rel_tol=0., abs_tol=1e-12)):
                raise ValueError('stable testcase evidence disagrees with label fraction')
        if key is not None and set(ev['gained_testcases']) & set(ev['lost_testcases']):
            raise ValueError('testcases cannot be both gained and lost')
    return key


def _difference(left, right):
    with np.errstate(over='ignore', invalid='ignore'):
        difference = left-right
    if not np.isfinite(difference).all():
        raise ValueError('candidate difference exceeds finite float64 arithmetic')
    return difference


def _pair_counts(indices, candidates, interaction, base):
    counts = dict(unordered_pairs=0, noop_edited_pairs=0, edited_edited_pairs=0,
        interaction_varying_pairs=0, zero_interaction_pairs=0,
        event_value_different_pairs=0, mask_different_pairs=0,
        effective_event_different_pairs=0, nonzero_base_margin_pairs=0)
    for a, b in indices:
        difference = _difference(interaction.matrix[a], interaction.matrix[b])
        offset = _difference(base[a], base[b])
        counts['unordered_pairs'] += 1
        counts['noop_edited_pairs' if candidates[a].is_noop or candidates[b].is_noop else 'edited_edited_pairs'] += 1
        counts['interaction_varying_pairs'] += int(np.max(np.abs(difference)) > VARIATION_TOLERANCE)
        counts['zero_interaction_pairs'] += int(not np.any(difference))
        counts['event_value_different_pairs'] += int(not np.array_equal(interaction.event_values[a], interaction.event_values[b]))
        counts['mask_different_pairs'] += int(not np.array_equal(interaction.event_masks[a], interaction.event_masks[b]))
        counts['effective_event_different_pairs'] += int(not np.array_equal(
            interaction.event_values[a]*interaction.event_masks[a], interaction.event_values[b]*interaction.event_masks[b]))
        counts['nonzero_base_margin_pairs'] += int(offset != 0.)
    return counts


def _sum_counts(rows, name):
    keys = rows[0][name]
    return {key: sum(row[name][key] for row in rows) for key in keys}


def build_pairs(examples, banks, labels, interactions, base_scores):
    """Construct legacy natural pairs from ONLY explicitly supplied train banks.

    The whitelist equality checks happen before any candidate label is read.
    Multiple prefixes for one user are allowed; reused example/bank IDs are not.
    Output owns its matrices and never modifies supplied arrays or dictionaries.
    """
    if type(examples) not in (list, tuple) or not examples or any(type(ex) is not Example for ex in examples):
        raise ValueError('nonempty exact Example sequence required')
    for ex in examples:
        if (ex.split != 'train' or any(type(v) is not str or not v for v in (ex.example_id, ex.bank_id, ex.user_id))
                or type(ex.observation) is not PilotObservation):
            raise ValueError('strict fold-training examples only; held/valid/test cannot enter')
    if len({ex.example_id for ex in examples}) != len(examples) or len({ex.bank_id for ex in examples}) != len(examples):
        raise ValueError('unique training example and bank IDs required')
    bank_ids = {ex.bank_id for ex in examples}
    for value, name in ((banks, 'banks'), (interactions, 'interactions'), (base_scores, 'base scores')):
        _exact_mapping(value, bank_ids, name)
    validated = {}
    for ex in examples:
        bank = banks[ex.bank_id]
        candidates, base = _candidate_inputs(bank, interactions[ex.bank_id], base_scores[ex.bank_id])
        if bank.problem_id != ex.observation.problem_id or bank.current_source != ex.observation.current.source:
            raise ValueError('training observation and bank mismatch')
        validated[ex.bank_id] = candidates, base
    required = {(bid, c.candidate_id) for bid, (candidates, _) in validated.items() for c in candidates}
    _exact_mapping(labels, required, 'labels')

    records, bank_metadata = [], []
    for ex in examples:
        bid = ex.bank_id; bank = banks[bid]; candidates, base = validated[bid]
        interaction = interactions[bid]
        keys = [_label(labels[bid, c.candidate_id], bid, bank, c) for c in candidates]
        stable = [i for i, key in enumerate(keys) if key is not None]
        stable_pairs = list(combinations(stable, 2))
        pairs = [(a, b, int(keys[a] > keys[b])) for a, b in stable_pairs if keys[a] != keys[b]]
        all_pairs = list(combinations(range(len(candidates)), 2))
        if pairs:
            records.append((ex, pairs, len(stable)))
        bank_metadata.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=bid,
            bank_seal_sha256=bank.seal_sha256, problem_id=bank.problem_id,
            candidate_ids=[c.candidate_id for c in candidates],
            candidate_statuses=[labels[bid, c.candidate_id]['status'] for c in candidates],
            candidate_count=len(candidates), stable_candidates=len(stable), unknown_candidates=len(candidates)-len(stable),
            pairs_with_unknown=len(all_pairs)-len(stable_pairs), stable_tied_pairs=len(stable_pairs)-len(pairs),
            informative_unordered_pairs=len(pairs),
            event_available_candidates=interaction.event_masks.sum(axis=0).astype(int).tolist(),
            event_positive_candidates=(interaction.event_values*interaction.event_masks).sum(axis=0).astype(int).tolist(),
            all_pair_counts=_pair_counts(all_pairs, candidates, interaction, base),
            informative_pair_counts=_pair_counts([(a, b) for a, b, _ in pairs], candidates, interaction, base)))
    prefixes = Counter(ex.user_id for ex, *_ in records)
    all_users = {ex.user_id for ex in examples}
    informative_ids = [ex.example_id for ex, *_ in records]
    legacy = dict(train_prefixes=len(examples), train_users=len(all_users), informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(examples)-len(records), users=len(prefixes),
        users_without_informative_prefix=len(all_users-set(prefixes)), ordered_pairs=0, pair_example_ids=[],
        informative_train_example_ids=informative_ids,
        uninformative_train_example_ids=sorted({ex.example_id for ex in examples}-set(informative_ids)),
        stable_train_candidates=sum(n for _, _, n in records), weight_normalization='fixed_reference_total_pair_weight',
        reference_pair_weight=MASS, sample_weight_sum=0., prior_mean_one_weight_sum=0.)
    metadata = dict(kind='fixed_train_only_feedback_pairs_v1', dimension=DIMENSION, event_count=EVENT_COUNT,
        preference='legacy_stable_lexicographic_all_ac_loss_zero_net_gain',
        diagnostic_variation_tolerance=VARIATION_TOLERANCE, no_pair_filter_by_feature_variation=True,
        fixed_base_coefficient=1., intercept=0., training=legacy, banks=bank_metadata,
        all_pair_counts=_sum_counts(bank_metadata, 'all_pair_counts'),
        informative_pair_counts=_sum_counts(bank_metadata, 'informative_pair_counts'), pair_candidate_ids=[])
    if not records:
        raise NoInformativePairs(metadata)
    matrices, outcomes, weights, offsets = [], [], [], []
    for ex, pairs, _ in records:
        candidates, base = validated[ex.bank_id]
        for a, b, target in pairs:
            difference = _difference(interactions[ex.bank_id].matrix[a], interactions[ex.bank_id].matrix[b])
            offset = _difference(base[a], base[b])
            matrices.extend((difference, -difference)); outcomes.extend((target, 1-target))
            offsets.extend((offset, -offset))
            weights.extend([1/(prefixes[ex.user_id]*len(pairs)*2)]*2)
            legacy['pair_example_ids'].extend([ex.example_id]*2)
            left, right = candidates[a].candidate_id, candidates[b].candidate_id
            metadata['pair_candidate_ids'].extend([[left, right], [right, left]])
    weights = np.asarray(weights, dtype=np.float64)
    # Preserve BOTH legacy floating-point normalization steps, not just algebra.
    weights *= len(weights)/weights.sum()
    old_mass = float(weights.sum())
    weights = weights*(MASS/old_mass)
    legacy.update(ordered_pairs=len(weights), sample_weight_sum=float(weights.sum()), prior_mean_one_weight_sum=old_mass)
    return PairData(np.stack(matrices), np.asarray(outcomes, dtype=np.int64), weights,
                    np.asarray(offsets, dtype=np.float64), metadata)


def score_candidates(model, bank, interaction, base_scores):
    """All candidate scores B + phi @ theta, with no labels or fitting access."""
    theta = validate_model(model)
    candidates, base = _candidate_inputs(bank, interaction, base_scores)
    with np.errstate(over='ignore', invalid='ignore'):
        scores = base+interaction.matrix@theta
    if not np.isfinite(scores).all():
        raise ValueError('nonfinite fixed-offset candidate scores')
    return {candidate.candidate_id: float(score) for candidate, score in zip(candidates, scores)}


def select_candidate(model, bank, interaction, base_scores):
    """Maximum score, then ascending exact candidate SHA; unknowns remain."""
    scores = score_candidates(model, bank, interaction, base_scores)
    return min(scores, key=lambda cid: (-scores[cid], cid))
