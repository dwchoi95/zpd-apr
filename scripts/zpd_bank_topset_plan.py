"""Pure own-training top-set plan; no I/O, scaler fitting or optimization.

The original mirrored preference plan certifies each bank's mass. Stable
candidates retain their original order; every maximal lexicographic candidate
is in T and the remaining stable candidates are in N. Unknown candidates are
coverage records, never negatives. A stable all-tie bank has zero inherited
mass and is retained as a Bank; an unknown-only bank cannot supply a Bank/T.

Capsule/source replay and supplied own-label scope are checked here. External
artifact SHA authority, label provenance and worker isolation are the caller's
responsibility. Self-hashed payloads do not establish those external facts.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields, replace
import hashlib
import json
import math

import numpy as np

from scripts import zpd_bank_topset_objective as objective
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from scripts.zpd_repair_pairwise import preference
from scripts.zpd_repair_residual_core import make_pair_plan
from src.repair.pilot_contracts import canonical_hash

VERSION = 'own_training_bank_topset_plan_v1'
ARMS = features.ARMS
DIMENSION = features.DIMENSION


def _require(value, message):
    if not value:
        raise ValueError(message)


def _frozen(array):
    return np.frombuffer(array.tobytes(order='C'), dtype=array.dtype).reshape(array.shape)


def _array_sha(array):
    """Shape/dtype bound canonical little-endian bytes, not a provenance claim."""
    dtype = '<i8' if array.dtype == np.dtype('int64') else '<f8'
    return canonical_hash(dict(dtype=dtype, shape=list(array.shape),
        bytes_sha256=hashlib.sha256(array.astype(dtype, copy=False).tobytes(order='C')).hexdigest()))


@dataclass(frozen=True)
class _Rows:
    current: np.ndarray
    tails: tuple[np.ndarray, ...]
    top: tuple[int, ...]


@dataclass(frozen=True)
class Plan:
    """Detached immutable plan; dense per-arm Banks are materialized on demand.

    Store the common 4099 columns once, not seven dense copies. No caller
    dictionaries, sparse matrices, source objects or transform are retained.
    The returned arrays have immutable bytes backing (not just a writable flag).
    """
    _rows: tuple[_Rows, ...]
    _weights: np.ndarray
    _payload_json: str

    def payload(self):
        """Fresh JSON-compatible ledger, including its self-content SHA."""
        return json.loads(self._payload_json)

    def banks(self, arm):
        """Return stable-only Banks and exact inherited masses in ledger order."""
        _require(type(arm) is str and arm in ARMS, 'one fixed seven-arm name required')
        index = ARMS.index(arm)
        return tuple(objective.Bank(np.concatenate((r.current, r.tails[index]), axis=1), r.top)
                     for r in self._rows), self._weights


def configuration():
    return dict(kind=VERSION, arms=list(ARMS), dimension=DIMENSION,
        preference='legacy_stable_lexicographic_all_ac_loss_zero_net_gain',
        top='all_maximal_stable_candidates_in_original_order',
        rest='all_other_stable_candidates_in_original_order',
        unknown='ledger_only_never_negative_or_invented_top',
        all_tie='stable_Bank_with_zero_original_mass',
        bank_mass='math_fsum_original_mirrored_weights_by_bank_no_renormalization',
        features='unchanged_compose_blocks_stable_rows_no_extra_centering_or_scaling',
        original_pair_mass=objective.MASS, scaler_fitting_performed=False,
        fitting_performed=False, external_provenance_authenticated=False)


def _check_ancestry(transform, legacy, examples, banks, labels):
    _require(type(transform) is features.OwnTransform
        and set(vars(transform)) == {f.name for f in fields(features.OwnTransform)},
        'exact OwnTransform schema required')
    # Revalidate a detached copy; compose_blocks may revalidate it in turn.
    transform = replace(transform)
    for name in ('bank_candidate_ids', 'row_keys'):
        _require(getattr(transform, name) == getattr(legacy, name),
            'original pair-plan '+name+' ancestry mismatch')
    for name in ('y', 'weights'):
        actual, expected = getattr(transform, name), getattr(legacy, name)
        _require(actual.dtype == expected.dtype and actual.shape == expected.shape
            and actual.tobytes() == expected.tobytes(), 'original pair-plan '+name+' ancestry mismatch')
    _require(capsule._same(transform.training, legacy.metadata['training']),
        'original pair-plan training ancestry mismatch')
    # Check scaler row/weight ancestry without fitting/recomputing a scale.
    informative = set(legacy.metadata['training']['informative_train_example_ids'])
    counts = Counter(ex.user_id for ex in examples if ex.example_id in informative)
    identities, weights = [], []
    for ex in examples:
        if ex.example_id not in informative:
            continue
        stable = [c.candidate_id for c in banks[ex.bank_id].candidates
                  if preference(labels[ex.bank_id, c.candidate_id]) is not None]
        identities.extend((ex.bank_id, cid) for cid in stable)
        weights.extend([1 / (counts[ex.user_id] * len(stable))] * len(stable))
    expected = np.asarray(weights, dtype=np.float64)
    _require(transform.scaler_candidate_ids == tuple(identities)
        and transform.scaler_weights.tobytes() == expected.tobytes(),
        'original scaler candidate/weight ancestry mismatch')
    return transform


def build_plan(inputs: capsule.FoldInputs, transform: features.OwnTransform,
               own_labels: dict) -> Plan:
    """Validate exact own-label keys BEFORE consuming any label values.

    This reconstructs the old pair plan, not a scaler or model. The supplied
    numeric scale/mean/variance remain externally authenticated OwnTransform
    values. A wholly uninformative fold remains the original NoInformativePairs
    error: no mass1900 or artificial T is manufactured.
    """
    cohort = capsule.validate_inputs(inputs)
    train, held = capsule.scope(inputs)
    banks = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
    expected = {(bid, c.candidate_id) for bid, bank in banks.items() for c in bank.candidates}
    _require(type(own_labels) is dict and set(own_labels) == expected,
        'exact own-training bank/candidate label keys required before label values')
    # Key scope is established. make_pair_plan independently validates all core
    # rows and their dictionary identities before reconstructing the relation.
    legacy = make_pair_plan(train, banks, own_labels)
    own_labels = {key: dict(row) for key, row in own_labels.items()}
    transform = _check_ancestry(transform, legacy, train, banks, own_labels)
    bank_weights = {ex.bank_id: [] for ex in train}
    for row, weight in zip(transform.row_keys, transform.weights, strict=True):
        bank_weights[row[0]].append(float(weight))
    masses = {bid: math.fsum(values) for bid, values in bank_weights.items()}
    total = math.fsum(masses.values())
    _require(math.isclose(total, objective.MASS, rel_tol=objective.MASS_RTOL, abs_tol=objective.MASS_ATOL),
        'original bank masses must sum to1900 without renormalization')

    stored, weights, ledger, objective_ids = [], [], [], []
    original_diagnostics = {row['bank_id']: row for row in legacy.metadata['banks']}
    for ex in train:
        bid = ex.bank_id; bank = banks[bid]
        ids = tuple(c.candidate_id for c in bank.candidates)
        keys = [preference(own_labels[bid, cid]) for cid in ids]
        stable = tuple(i for i, value in enumerate(keys) if value is not None)
        unknown = tuple(i for i, value in enumerate(keys) if value is None)
        maximum = max((keys[i] for i in stable), default=None)
        top = tuple(i for i in stable if keys[i] == maximum)
        rest = tuple(i for i in stable if keys[i] != maximum)
        _require(bool(rest) == bool(bank_weights[bid]), 'stable tiers disagree with original informative pairs')
        _require(bool(rest) or masses[bid] == 0., 'uninformative bank cannot inherit nonzero pair mass')
        blocks = features.compose_blocks(inputs.raw_current[bid], transform,
            {arm: inputs.interactions[arm][bid] for arm in features.PROGRESS_ARMS})
        matrices = {arm: block.matrix[list(stable), :].toarray() for arm, block in blocks.items()}
        _require(tuple(blocks) == ARMS and all(block.candidate_ids == ids for block in blocks.values()),
            'unchanged seven-arm composition/candidate order required')
        if stable:
            top_stable = tuple(stable.index(i) for i in top)
            current = matrices['H'][:, :features.CURRENT_DIMENSION]
            _require(all(current.tobytes() == value[:, :features.CURRENT_DIMENSION].tobytes()
                for value in matrices.values()), 'joint current columns must be arm-invariant')
            stored.append(_Rows(_frozen(current), tuple(_frozen(matrices[arm][:, features.CURRENT_DIMENSION:])
                for arm in ARMS), top_stable))
            weights.append(masses[bid]); objective_ids.append(bid)
        else:
            top_stable = ()
        masks = {name: [i in indices for i in range(len(ids))]
                 for name, indices in (('stable', stable), ('top', top), ('rest', rest), ('unknown', unknown))}
        info = original_diagnostics[bid]
        ledger.append(dict(example_id=ex.example_id, user_id=ex.user_id, problem_id=bank.problem_id,
            bank_id=bid, bank_seal_sha256=bank.seal_sha256, candidate_ids=list(ids),
            is_noop=[c.is_noop for c in bank.candidates], masks=masks,
            stable_candidate_ids=[ids[i] for i in stable], top_candidate_ids=[ids[i] for i in top],
            rest_candidate_ids=[ids[i] for i in rest], unknown_candidate_ids=[ids[i] for i in unknown],
            top_indices_in_stable_rows=list(top_stable), objective_bank_index=len(stored)-1 if stable else None,
            status='informative' if rest else 'stable_all_tie' if stable else 'unknown_only',
            original_ordered_rows=len(bank_weights[bid]), original_pair_mass=masses[bid],
            original_informative_unordered_pairs=info['informative_unordered_pairs'],
            original_stable_tied_pairs=info['stable_tied_pairs'], original_pairs_with_unknown=info['pairs_with_unknown'],
            stable_features_sha256={arm: _array_sha(matrices[arm]) for arm in ARMS},
            accepted_progress32_sha256={arm: _array_sha(inputs.interactions[arm][bid].matrix)
                                       for arm in features.PROGRESS_ARMS}))

    weights = _frozen(np.asarray(weights, dtype=np.float64))
    payload = dict(kind=VERSION, configuration=configuration(), fold=inputs.fold, synthetic=inputs.synthetic,
        arms=list(ARMS), dimension=DIMENSION,
        fold_assignment_sha256=inputs.fold_assignment_sha256,
        readiness_complete_sha256=inputs.readiness_complete_sha256,
        coverage=dict(full_cohort_banks=len(cohort), full_cohort_candidates=sum(len(r['candidate_ids']) for r in cohort),
            own_training_banks=len(train), own_training_candidates=len(expected), held_banks=len(held),
            objective_banks=len(stored), stable_candidates=sum(sum(r['masks']['stable']) for r in ledger),
            unknown_candidates=sum(sum(r['masks']['unknown']) for r in ledger),
            informative_banks=sum(r['status'] == 'informative' for r in ledger),
            all_tie_banks=sum(r['status'] == 'stable_all_tie' for r in ledger),
            unknown_only_banks=sum(r['status'] == 'unknown_only' for r in ledger)),
        objective_bank_ids=objective_ids, bank_weights=weights.tolist(), original_pair_mass=total,
        original_pair_plan=dict(row_keys_sha256=canonical_hash(legacy.row_keys),
            y_sha256=_array_sha(legacy.y), weights_sha256=_array_sha(legacy.weights), training=transform.training),
        supplied_transform=dict(numeric_scale=transform.numeric_scale.tolist(), numeric_mean=transform.numeric_mean.tolist(),
            numeric_variance=transform.numeric_variance.tolist(), scaler_candidate_ids=[list(row) for row in transform.scaler_candidate_ids],
            scaler_weights_sha256=_array_sha(transform.scaler_weights)),
        own_labels_sha256=canonical_hash([own_labels[ex.bank_id, c.candidate_id]
            for ex in train for c in banks[ex.bank_id].candidates]), banks=ledger)
    payload['plan_sha256'] = canonical_hash(payload)
    return Plan(tuple(stored), weights, json.dumps(payload, sort_keys=True, allow_nan=False))
