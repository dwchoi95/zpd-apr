"""Pure raw-current + accepted-progress layout and own-training scaling.

No I/O, optimizer, learned base score, fold discovery or execution is provided.
The coordinator may call raw_current on authenticated source-only banks. Only
the own-fold worker may call fit_own_scaler with its exact training objects and
separately authenticated training labels. A pure function cannot authenticate
that externally supplied membership; it rejects extra banks/labels rather than
silently filtering a full-cohort label dictionary.

All seven arms share the once-fitted three-column scaler. Accepted progress32
is retained as immutable original float64 bytes in JointBlock.progress. Sparse
arithmetic can discard signed zero: its numerical zeros and exact nonzero bits,
not CSR.toarray's zero signs, must agree with those authoritative input bytes.
No whole-vector normalization, history truncation or pair-norm<=1 rule applies
to the resulting 4,131 columns.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
import json
import math
import re

import numpy as np
from scipy import sparse
from sklearn.preprocessing import StandardScaler
from sklearn.utils.sparsefuncs import inplace_column_scale

from scripts import zpd_repair_structure as structural
from scripts import zpd_statement_sample_progress as progress
from scripts.zpd_repair_fit import Example
from scripts.zpd_repair_pairwise import preference
from scripts.zpd_repair_residual_core import CandidateBlock, make_pair_plan
from src.repair.pilot_contracts import CandidateBank, canonical_hash

VERSION = 'joint_raw_current_progress32_features_v1'
ARMS = ('H', 'Jm', 'HS', 'U', 'L', 'CF', 'C_joint')
PROGRESS_ARMS = ARMS[:-1]
NUMERIC_NAMES = tuple(structural.numeric_names('C'))
NUMERIC_DIMENSION = 3
HASH_DIMENSION = 4096
CURRENT_DIMENSION = 4099
PROGRESS_DIMENSION = 32
DIMENSION = 4131
NORM_ALLOWANCE = 1e-12  # Only the unchanged progress32 analytic bound.


def configuration():
    return dict(kind=VERSION, arms=list(ARMS), dimension=DIMENSION,
        numeric_names=list(NUMERIC_NAMES), numeric_dimension=NUMERIC_DIMENSION,
        current_dimension=CURRENT_DIMENSION, progress_dimension=PROGRESS_DIMENSION,
        raw_current=structural._configuration('structural'),
        progress_version=progress.VERSION, progress_configuration_sha256=canonical_hash(progress.configuration()),
        numeric_scaling='own_stable_candidates_in_informative_prefixes_equal_user_prefix_candidate',
        scaler='StandardScaler_with_mean_False_once_shared_across_seven_arms',
        appended_progress='unchanged_accepted_float64_values_and_separately_preserved_bytes',
        whole_vector_normalization=False, learned_base_input=False, base_offset_present=False,
        pair_norm_upper_bound=None, pair_weight_mass=1900.)


def _require(value, message):
    if not value: raise ValueError(message)


def _ids(value):
    _require(type(value) is tuple and bool(value) and len(set(value)) == len(value)
        and all(type(cid) is str and re.fullmatch('[0-9a-f]{64}', cid) for cid in value),
        'nonempty unique ordered candidate SHA tuple required')


def _immutable(array):
    return np.frombuffer(array.tobytes(order='C'), dtype=array.dtype).reshape(array.shape)


def _csr(value, width, rows=None):
    _require(sparse.isspmatrix_csr(value) and value.dtype == np.dtype('float64')
        and value.ndim == 2 and value.shape[1] == width and value.shape[0] > 0
        and (rows is None or value.shape[0] == rows), 'exact nonempty float64 CSR dimensions required')
    value.check_format(full_check=True)
    _require(value.has_canonical_format and np.isfinite(value.data).all(), 'finite canonical CSR required')
    for lo, hi in zip(value.indptr, value.indptr[1:]):
        _require(not np.any(np.diff(value.indices[lo:hi]) <= 0), 'unique sorted CSR coordinates required')
    result = value.copy()
    result.data = _immutable(result.data)
    result.indices = _immutable(result.indices)
    result.indptr = _immutable(result.indptr)
    return result


def _vector(value, n, name, *, positive=False):
    _require(type(value) is np.ndarray and value.dtype == np.dtype('float64') and value.shape == (n,)
        and np.isfinite(value).all() and (not positive or (value > 0).all()), 'finite float64 '+name+' required')
    return _immutable(value)


@dataclass(frozen=True)
class RawCurrent:
    bank_id: str
    bank_seal_sha256: str
    candidate_ids: tuple[str, ...]
    numeric: sparse.csr_matrix
    hashed: sparse.csr_matrix

    def __post_init__(self):
        _ids(self.candidate_ids)
        _require(type(self.bank_id) is str and bool(self.bank_id)
            and type(self.bank_seal_sha256) is str and re.fullmatch('[0-9a-f]{64}', self.bank_seal_sha256),
            'exact bank identity/seal required')
        object.__setattr__(self, 'numeric', _csr(self.numeric, NUMERIC_DIMENSION, len(self.candidate_ids)))
        object.__setattr__(self, 'hashed', _csr(self.hashed, HASH_DIMENSION, len(self.candidate_ids)))


def raw_current(example, bank):
    """Coordinator-safe source-only parity with frozen structural C; no labels."""
    _require(type(example) is Example and type(bank) is CandidateBank, 'exact Example and CandidateBank required')
    numeric, hashed = structural.raw_features(example.observation, (), bank, 'C', 'structural')
    return RawCurrent(example.bank_id, bank.seal_sha256, tuple(c.candidate_id for c in bank.candidates), numeric, hashed)


@dataclass(frozen=True)
class OwnTransform:
    numeric_scale: np.ndarray
    numeric_mean: np.ndarray
    numeric_variance: np.ndarray
    scaler_candidate_ids: tuple  # Original bank order, then stable candidate order.
    scaler_weights: np.ndarray
    bank_candidate_ids: tuple
    row_keys: tuple  # Adjacent mirrored (bank_id, left_id, right_id).
    y: np.ndarray
    weights: np.ndarray
    _training_json: str

    @property
    def training(self): return json.loads(self._training_json)

    def __post_init__(self):
        for name in ('numeric_scale', 'numeric_mean', 'numeric_variance'):
            object.__setattr__(self, name, _vector(getattr(self, name), NUMERIC_DIMENSION, name,
                positive=name == 'numeric_scale'))
        _require((self.numeric_variance >= 0).all(), 'nonnegative numeric variance required')
        _require(type(self.scaler_candidate_ids) is tuple and bool(self.scaler_candidate_ids), 'scaler row identities required')
        object.__setattr__(self, 'scaler_weights', _vector(self.scaler_weights, len(self.scaler_candidate_ids),
            'scaler weights', positive=True))
        n = len(self.row_keys)
        _require(type(self.row_keys) is tuple and n > 0 and n % 2 == 0
            and type(self.bank_candidate_ids) is tuple and bool(self.bank_candidate_ids), 'nonempty mirrored own pair plan required')
        _require(type(self.y) is np.ndarray and self.y.dtype == np.dtype('int64')
            and self.y.shape == (n,) and np.isin(self.y, [0, 1]).all(), 'int64 binary pair labels required')
        object.__setattr__(self, 'y', _immutable(self.y))
        object.__setattr__(self, 'weights', _vector(self.weights, n, 'pair weights', positive=True))
        _require(np.array_equal(self.y[1::2], 1-self.y[::2])
            and np.array_equal(self.weights[1::2], self.weights[::2])
            and math.isclose(math.fsum(self.weights), 1900., rel_tol=1e-12, abs_tol=1e-12),
            'original adjacent mirrored labels/weights with mass1900 required')
        expected = dict(self.bank_candidate_ids)
        _require(len(expected) == len(self.bank_candidate_ids), 'unique bank pair scope required')
        for bid, ids in self.bank_candidate_ids: _ids(ids)
        bank_order = {bid: i for i, (bid, _) in enumerate(self.bank_candidate_ids)}
        candidate_order = {bid: {cid: i for i, cid in enumerate(ids)} for bid, ids in self.bank_candidate_ids}
        order = []
        for pos in range(0, n, 2):
            bid, left, right = self.row_keys[pos]
            _require(bid in expected and left in expected[bid] and right in expected[bid] and left != right
                and self.row_keys[pos+1] == (bid, right, left), 'exact adjacent row-key mirrors required')
            a, b = candidate_order[bid][left], candidate_order[bid][right]
            _require(a < b, 'original forward candidate combination order required')
            order.append((bank_order[bid], a, b))
        _require(order == sorted(set(order)), 'original unique bank/candidate combination order required')
        _require(len(set(self.scaler_candidate_ids)) == len(self.scaler_candidate_ids)
            and all(bid in expected and cid in expected[bid] for bid, cid in self.scaler_candidate_ids),
            'unique scaler candidates inside own bank scope required')
        info = self.training
        _require(type(info) is dict and set(info) == structural.TRAINING_FIELDS
            and info['ordered_pairs'] == n, 'only original training metadata, not legacy offset configuration, required')


def fit_own_scaler(train_examples, train_banks, raw_blocks, own_labels):
    """One own-fold weighted scaler + original pair plan; never accepts held keys.

    All stable candidates (including tied ones) in each informative prefix are
    scaler rows. Prefixes without stable unequal pairs contribute no scaler row.
    Their banks/candidates remain in the exact supplied scope for later scoring.
    """
    legacy = make_pair_plan(train_examples, train_banks, own_labels)
    expected = {ex.bank_id for ex in train_examples}
    _require(type(raw_blocks) is dict and set(raw_blocks) == expected, 'exact own-training raw bank scope required')
    informative = set(legacy.metadata['training']['informative_train_example_ids'])
    records = []
    for ex in train_examples:
        bank = train_banks[ex.bank_id]; block = raw_blocks[ex.bank_id]
        _require(type(block) is RawCurrent and block.bank_id == ex.bank_id
            and block.bank_seal_sha256 == bank.seal_sha256
            and block.candidate_ids == tuple(c.candidate_id for c in bank.candidates), 'raw current source/candidate identity mismatch')
        _csr(block.numeric, NUMERIC_DIMENSION, len(block.candidate_ids))
        _csr(block.hashed, HASH_DIMENSION, len(block.candidate_ids))
        if ex.example_id in informative:
            stable = [i for i, cid in enumerate(block.candidate_ids) if preference(own_labels[ex.bank_id, cid]) is not None]
            records.append((ex, block, stable))
    prefixes = Counter(ex.user_id for ex, _, _ in records)
    numeric = sparse.vstack([block.numeric[stable] for _, block, stable in records], format='csr')
    candidate_weights = np.array([1/(prefixes[ex.user_id]*len(stable))
        for ex, _, stable in records for _ in stable], dtype=np.float64)
    # Exact original sklearn weighting and near-constant-column treatment.
    scaler = StandardScaler(with_mean=False).fit(numeric, sample_weight=candidate_weights)
    return OwnTransform(scaler.scale_, scaler.mean_, scaler.var_,
        tuple((ex.bank_id, block.candidate_ids[i]) for ex, block, stable in records for i in stable),
        candidate_weights, legacy.bank_candidate_ids, legacy.row_keys, legacy.y, legacy.weights,
        json.dumps(legacy.metadata['training'], sort_keys=True, allow_nan=False))


@dataclass(frozen=True)
class JointBlock:
    candidate_ids: tuple[str, ...]
    matrix: sparse.csr_matrix
    progress: np.ndarray  # Authoritative accepted bytes; C_joint is generated all-zero.

    def __post_init__(self):
        _ids(self.candidate_ids); n = len(self.candidate_ids)
        object.__setattr__(self, 'matrix', _csr(self.matrix, DIMENSION, n))
        _require(type(self.progress) is np.ndarray and self.progress.dtype == np.dtype('float64')
            and self.progress.shape == (n, PROGRESS_DIMENSION) and np.isfinite(self.progress).all(),
            'exact finite authoritative progress32 array required')
        actual = self.matrix[:, CURRENT_DIMENSION:].toarray(); nonzero = self.progress != 0.
        _require(np.array_equal(actual, self.progress)
            and actual[nonzero].tobytes() == self.progress[nonzero].tobytes(), 'appended progress changed or rescaled')
        object.__setattr__(self, 'progress', _immutable(self.progress))


def compose_blocks(raw, transform, progress_blocks):
    """All seven candidate layouts, one scaler, no refitting or learned base.

    Caller certifies the accepted full-history phi32 ancestry. This function
    checks layout, shared current feedback, CF/no-op zeros and the existing
    progress-only bounds; it never imposes those bounds on current/joint rows.
    """
    _require(type(raw) is RawCurrent and type(transform) is OwnTransform, 'raw current and own transform required')
    transform.__post_init__()
    numeric = _csr(raw.numeric, NUMERIC_DIMENSION, len(raw.candidate_ids)).copy()
    hashed = _csr(raw.hashed, HASH_DIMENSION, len(raw.candidate_ids))
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        inplace_column_scale(numeric, 1/transform.numeric_scale)
    current = sparse.hstack([numeric, hashed], format='csr')
    _csr(current, CURRENT_DIMENSION, len(raw.candidate_ids))
    _require(type(progress_blocks) is dict and set(progress_blocks) == set(PROGRESS_ARMS), 'exact six accepted progress arms required')
    shared = None
    noop = np.flatnonzero(raw.numeric[:, NUMERIC_NAMES.index('candidate_is_noop')].toarray().ravel() == 1.)
    _require(len(noop) == 1, 'one original no-op candidate required')
    arrays = {}
    for arm in PROGRESS_ARMS:
        block = progress_blocks[arm]
        _require(type(block) is CandidateBlock and block.candidate_ids == raw.candidate_ids
            and type(block.matrix) is np.ndarray and block.matrix.dtype == np.dtype('float64')
            and block.matrix.shape == (len(raw.candidate_ids), PROGRESS_DIMENSION)
            and np.isfinite(block.matrix).all(), 'exact ordered finite accepted progress32 block required')
        x = block.matrix
        _require(not np.any(x[noop[0]]), 'unchanged progress no-op must be zero')
        _require(all(math.hypot(*row) <= 2.**-.5+NORM_ALLOWANCE for row in x)
            and all(math.hypot(*(x[a]-x[b])) <= 1.+NORM_ALLOWANCE for a, b in combinations(range(len(x)), 2)),
            'unchanged progress-only norm bound required')
        if shared is None: shared = x[:, :16]
        _require(np.array_equal(x[:, :16], shared), 'authentic current feedback must be common to six arms')
        if arm == 'CF': _require(not np.any(x[:, 16:]), 'CF residual must be zero')
        arrays[arm] = x
    arrays['C_joint'] = np.zeros((len(raw.candidate_ids), PROGRESS_DIMENSION), dtype=np.float64)
    return {arm: JointBlock(raw.candidate_ids, sparse.hstack([current, sparse.csr_matrix(arrays[arm])], format='csr'),
        arrays[arm]) for arm in ARMS}


def mirrored_pairs(transform, train_blocks):
    """Canonical sparse4131 differences; original y/weights/metadata stay fixed.

    Returns (X, y, weights, training_metadata). No offsets are accepted or
    returned. Zero differences are retained. R=max||X_i|| must be measured by
    the later numerical layer, not replaced by the old progress-only bound.
    """
    _require(type(transform) is OwnTransform, 'exact own transform required'); transform.__post_init__()
    expected = dict(transform.bank_candidate_ids)
    _require(type(train_blocks) is dict and set(train_blocks) == set(expected), 'exact own-training joint bank scope required')
    index = {}
    for bid, ids in expected.items():
        block = train_blocks[bid]
        _require(type(block) is JointBlock and block.candidate_ids == ids, 'exact joint candidate order required')
        block.__post_init__(); index[bid] = {cid: i for i, cid in enumerate(ids)}
    matrices = []
    for bid, left, right in transform.row_keys[::2]:
        x = train_blocks[bid].matrix
        difference = x[index[bid][left]]-x[index[bid][right]]
        _require(np.isfinite(difference.data).all(), 'nonfinite joint pair difference')
        matrices.extend((difference, -difference))
    matrix = _csr(sparse.vstack(matrices, format='csr'), DIMENSION, len(transform.y))
    return matrix, transform.y, transform.weights, transform.training
