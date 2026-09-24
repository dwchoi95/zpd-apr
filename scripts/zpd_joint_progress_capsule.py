"""Pure own-fold joint inputs: exact raw current and accepted progress32.

No file access, labels, scaler, learned base offset, model coefficients or CLI.
The coordinator supplies externally certified sources/readiness and own-held
baseline projections. Raw current features are replayed from those supplied
source bytes; accepted progress32 and baseline authenticity still require the
external capsule SHA, runtime/source authority and separate own-label contract.
A self-consistent capsule is not a provenance certificate.

CSR wire arrays use canonical little-endian int64 indices/indptr and float64
data without coordinate/zero elimination. Source replay must match those exact
canonical bytes. Dense progress32 has a separate exact float64 representation,
including signed zero, and is never recovered from sparse arithmetic. No
learned/global/sibling-fold metadata is permitted. The opaque own-parent SHA
and own training accounting are parity references, never prediction inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from itertools import combinations
import math

import numpy as np
from scipy import sparse

from scripts import zpd_joint_progress_features as features
from scripts import zpd_repair_progress_capsule as original
from scripts.run_zpd_repair_structure_cv import assign_folds
from scripts.zpd_repair_fit import Example
from scripts.zpd_repair_residual_core import CandidateBlock
from src.repair.pilot_contracts import CandidateAttempt, CandidateBank, PilotObservation, source_hash

VERSION = 'repair_joint_progress_own_fold_capsule_v1'
ARMS = features.PROGRESS_ARMS
BASELINES = original.BASELINES
PARENT_METHODS = original.PARENT_METHODS
PREDICTION_FIELDS = original.PREDICTION_FIELDS
TRAINING_FIELDS = original.TRAINING_FIELDS
NORM_ALLOWANCE = 1e-12  # Progress32 only, not the unscaled/current/joint vector.
require = original.require
_fields = original._fields
_typed = original._typed
_same = original._same
_clone = original._clone
_json = original._json


@dataclass(frozen=True)
class FoldInputs:
    fold: int
    examples: tuple[Example, ...]
    banks: dict[str, CandidateBank]
    assignment: dict
    raw_current: dict[str, features.RawCurrent]
    interactions: dict[str, dict[str, CandidateBlock]]
    parent_predictions: tuple[dict, ...]
    parent_training: dict
    parent_structure_model_sha256: str
    fold_assignment_sha256: str
    readiness_complete_sha256: str
    synthetic: bool = False


def configuration():
    return dict(kind=VERSION, features=features.configuration(),
        supplied_progress_arms=list(ARMS), csr_format='csr', csr_index_dtype='<i8', csr_data_dtype='<f8',
        progress_dtype='<f8', raw_source_replay=True, scaler_in_payload=False,
        learned_base_input=False, parent_scope='own_held_four_baselines_and_own_training_parity_only')


def scope(inputs):
    """Original-order own train/held scopes, after validate_inputs."""
    return original.scope(inputs)


def _csr(value, rows, width):
    """Check before SciPy can silently coerce malformed sparse index arrays."""
    require(type(value) is sparse.csr_matrix and value.dtype == np.dtype('float64')
        and value.shape == (rows, width), 'exact float64 CSR dimensions required')
    for name in ('indices', 'indptr'):
        array = getattr(value, name)
        require(type(array) is np.ndarray and array.ndim == 1
            and array.dtype in (np.dtype('int32'), np.dtype('int64')), 'strict CSR integer buffers required')
    require(type(value.data) is np.ndarray and value.data.dtype == np.dtype('float64')
        and value.data.ndim == 1 and np.isfinite(value.data).all(), 'finite float64 CSR data required')
    require(len(value.indptr) == rows + 1 and value.indptr[0] == 0
        and value.indptr[-1] == len(value.data) == len(value.indices)
        and np.all(value.indptr[1:] >= value.indptr[:-1])
        and np.all((value.indices >= 0) & (value.indices < width)), 'exact CSR buffer lengths/ranges required')
    for lo, hi in zip(value.indptr, value.indptr[1:]):
        require(not np.any(np.diff(value.indices[lo:hi]) <= 0), 'unique sorted canonical CSR coordinates required')
    value.copy().check_format(full_check=True)


def _encode_csr(value):
    return dict(format='csr', shape=list(value.shape), data_dtype='<f8', index_dtype='<i8',
        data_hex=value.data.astype('<f8', copy=False).tobytes(order='C').hex(),
        indices_hex=value.indices.astype('<i8', copy=False).tobytes(order='C').hex(),
        indptr_hex=value.indptr.astype('<i8', copy=False).tobytes(order='C').hex())


def validate_inputs(inputs):
    """Strict supplied-value/source replay; no external file authentication."""
    _typed(inputs, FoldInputs, 'joint own-fold capsule')
    require(type(inputs.fold) is int and inputs.fold in range(5) and type(inputs.synthetic) is bool,
        'strict fold0..4 and explicit synthetic boolean required')
    require(all(original._sha(getattr(inputs, key)) for key in
        ('parent_structure_model_sha256', 'fold_assignment_sha256', 'readiness_complete_sha256')),
        'external own-parent/fold/readiness SHA identities required')
    require(type(inputs.examples) is tuple and bool(inputs.examples), 'complete immutable example tuple required')
    for ex in inputs.examples:
        _typed(ex, Example, 'Example')
        require(all(original._text(getattr(ex, key)) for key in ('example_id', 'user_id', 'bank_id'))
            and ex.split == 'train', 'original training Example required')
        obs = ex.observation
        _typed(obs, PilotObservation, 'PilotObservation')
        require(original._text(obs.problem_id) and type(obs.prior) is tuple and bool(obs.prior)
            and type(ex.donor_history) is tuple and len(ex.donor_history) == len(obs.prior),
            'all authentic and matched donor history records required')
        for source in (*obs.prior, obs.current, *ex.donor_history): original._source(source)
        obs.__post_init__()
        PilotObservation(obs.problem_id, obs.current, ex.donor_history)
        require(ex.example_id == obs.current.submission_id, 'example must identify exact current source')
    for key in ('example_id', 'user_id', 'bank_id'):
        require(len({getattr(ex, key) for ex in inputs.examples}) == len(inputs.examples),
            'unique original ' + key + ' required')
    require(type(inputs.assignment) is dict and _same(inputs.assignment, assign_folds(inputs.examples))
        and set(inputs.assignment['example_fold'].values()) == set(range(5)),
        'exact original five nonempty problem-held folds required')
    bank_ids = {ex.bank_id for ex in inputs.examples}
    require(type(inputs.banks) is dict and set(inputs.banks) == bank_ids
        and type(inputs.raw_current) is dict and set(inputs.raw_current) == bank_ids
        and type(inputs.interactions) is dict and set(inputs.interactions) == set(ARMS),
        'complete original banks/raw-current and six progress arms required')
    for arm in ARMS:
        require(type(inputs.interactions[arm]) is dict and set(inputs.interactions[arm]) == bank_ids,
            'complete progress arm bank scope required')
    candidate_count = 0
    for ex in inputs.examples:
        bank = inputs.banks[ex.bank_id]
        _typed(bank, CandidateBank, 'CandidateBank')
        require(type(bank.current_source) is bytes and type(bank.attempts) is tuple
            and bank.problem_id == ex.observation.problem_id and bank.current_source == ex.observation.current.source,
            'exact original observation/bank bytes and identity required')
        for attempt in bank.attempts:
            _typed(attempt, CandidateAttempt, 'CandidateAttempt')
            attempt.__post_init__()
            require(attempt.source is None or type(attempt.source) is bytes, 'exact candidate source bytes required')
        bank.__post_init__()
        ids = tuple(c.candidate_id for c in bank.candidates)
        candidate_count += len(ids)
        raw = inputs.raw_current[ex.bank_id]
        _typed(raw, features.RawCurrent, 'RawCurrent')
        require(raw.bank_id == ex.bank_id and raw.bank_seal_sha256 == bank.seal_sha256
            and type(raw.candidate_ids) is tuple and raw.candidate_ids == ids, 'exact raw-current bank/order/seal required')
        for name, width in (('numeric', 3), ('hashed', 4096)):
            _csr(getattr(raw, name), len(ids), width)
        replay = features.raw_current(ex, bank)
        require(all(_encode_csr(getattr(raw, key)) == _encode_csr(getattr(replay, key))
            for key in ('numeric', 'hashed')), 'raw current differs from exact supplied-source replay')
        noop = ids.index(source_hash(bank.current_source))
        shared = None
        for arm in ARMS:
            block = inputs.interactions[arm][ex.bank_id]
            _typed(block, CandidateBlock, 'CandidateBlock')
            x = block.matrix
            require(type(block.candidate_ids) is tuple and block.candidate_ids == ids
                and type(x) is np.ndarray and x.dtype == np.dtype('float64')
                and x.shape == (len(ids), 32) and np.isfinite(x).all(), 'exact ordered float64 progress32 required')
            require(not np.any(x[noop]), 'literal zero no-op progress32 required')
            require(all(math.sqrt(math.fsum(float(v * v) for v in row)) <= 2. ** -.5 + NORM_ALLOWANCE for row in x)
                and all(math.sqrt(math.fsum(float(v * v) for v in x[a] - x[b])) <= 1. + NORM_ALLOWANCE
                    for a, b in combinations(range(len(x)), 2)), 'unchanged progress32 candidate/pair bounds required')
            if shared is None: shared = x[:, :16]
            require(np.array_equal(x[:, :16], shared), 'common authentic current-feedback block required')
            if arm == 'CF': require(not np.any(x[:, 16:]), 'literal zero CF residual tail required')
    if not inputs.synthetic:
        require(len(inputs.examples) == 320 and len({ex.observation.problem_id for ex in inputs.examples}) == 23
            and candidate_count == 2544, 'full frozen320/23/2544 population required; no exclusion')
    train, held = scope(inputs)
    original._training(inputs.parent_training, train, inputs.banks)
    require(type(inputs.parent_predictions) is tuple and len(inputs.parent_predictions) == len(held),
        'only complete original-order own-held baseline projections required')
    for ex, prediction in zip(held, inputs.parent_predictions, strict=True):
        _fields(prediction, PREDICTION_FIELDS, 'own-held baseline prediction')
        bank = inputs.banks[ex.bank_id]
        ids = tuple(c.candidate_id for c in bank.candidates)
        expected = dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            problem_id=bank.problem_id, fold=inputs.fold, bank_seal_sha256=bank.seal_sha256)
        require(all(type(prediction[k]) is type(v) and prediction[k] == v for k, v in expected.items()),
            'exact own-held baseline identity/order/seal required')
        require(type(prediction['choices']) is dict and set(prediction['choices']) == set(PARENT_METHODS)
            and all(type(v) is str and v in ids for v in prediction['choices'].values())
            and type(prediction['candidate_scores']) is dict and set(prediction['candidate_scores']) == set(BASELINES),
            'only four frozen choices and two own-held baseline score maps permitted')
        for name in BASELINES:
            scores = prediction['candidate_scores'][name]
            original._scores(scores, ids, name)
            require(prediction['choices'][name] == min(scores, key=lambda cid: (-scores[cid], cid)),
                'frozen baseline SHA tie-breaking differs')
        attempt = bank.attempts[0]
        noop = source_hash(bank.current_source)
        require(prediction['choices']['noop'] == noop and prediction['choices']['first_attempt'] ==
            (source_hash(attempt.source) if attempt.status == 'success' else noop), 'deterministic baseline projection differs')
    return [dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id, problem_id=ex.observation.problem_id,
        fold=inputs.assignment['example_fold'][ex.example_id], candidate_ids=[c.candidate_id for c in inputs.banks[ex.bank_id].candidates],
        noop_candidate_id=source_hash(inputs.banks[ex.bank_id].current_source)) for ex in inputs.examples]


def encode_inputs(inputs):
    """Detached, JSON-safe values; no references to caller arrays or mappings."""
    validate_inputs(inputs)
    examples = []; banks = {}; raw_current = {}; interactions = {arm: {} for arm in ARMS}
    for ex in inputs.examples:
        examples.append(dict(example_id=ex.example_id, user_id=ex.user_id, split=ex.split, bank_id=ex.bank_id,
            observation=dict(problem_id=ex.observation.problem_id, current=original._source_json(ex.observation.current),
                prior=[original._source_json(s) for s in ex.observation.prior]),
            donor_history=[original._source_json(s) for s in ex.donor_history]))
        bank = inputs.banks[ex.bank_id]
        banks[ex.bank_id] = dict(problem_id=bank.problem_id, current_source_hex=bank.current_source.hex(),
            generator_config_sha256=bank.generator_config_sha256, seeds=list(bank.seeds),
            attempts=[dict(index=a.index, seed=a.seed, status=a.status,
                source_hex=None if a.source is None else a.source.hex(), error=a.error) for a in bank.attempts],
            bank_seal_sha256=bank.seal_sha256, candidate_ids=[c.candidate_id for c in bank.candidates])
        raw = inputs.raw_current[ex.bank_id]
        raw_current[ex.bank_id] = dict(bank_id=raw.bank_id, bank_seal_sha256=raw.bank_seal_sha256,
            candidate_ids=list(raw.candidate_ids), numeric=_encode_csr(raw.numeric), hashed=_encode_csr(raw.hashed))
        for arm in ARMS:
            block = inputs.interactions[arm][ex.bank_id]
            interactions[arm][ex.bank_id] = dict(candidate_ids=list(block.candidate_ids), dtype='<f8',
                shape=list(block.matrix.shape), data_hex=block.matrix.astype('<f8', copy=False).tobytes(order='C').hex())
    return dict(kind=VERSION, configuration=configuration(), fold=inputs.fold, examples=examples, banks=banks,
        assignment=_clone(inputs.assignment), raw_current=raw_current, interactions=interactions,
        parent_predictions=_clone(list(inputs.parent_predictions)), parent_training=_clone(inputs.parent_training),
        parent_structure_model_sha256=inputs.parent_structure_model_sha256, fold_assignment_sha256=inputs.fold_assignment_sha256,
        readiness_complete_sha256=inputs.readiness_complete_sha256, synthetic=inputs.synthetic)


def fingerprint(inputs):
    """Exact supplied-content hash, subordinate to external job authority."""
    return hashlib.sha256(_json(encode_inputs(inputs)).encode('ascii')).hexdigest()


def _decode_csr(row, rows, width):
    _fields(row, ('format', 'shape', 'data_dtype', 'index_dtype', 'data_hex', 'indices_hex', 'indptr_hex'), 'serialized CSR')
    require(row['format'] == 'csr' and row['data_dtype'] == '<f8' and row['index_dtype'] == '<i8'
        and type(row['shape']) is list and len(row['shape']) == 2 and all(type(v) is int for v in row['shape'])
        and row['shape'] == [rows, width] and rows > 0, 'exact canonical CSR wire format/dtypes/shape required')
    raw = {key: original._hex(row[key + '_hex']) for key in ('data', 'indices', 'indptr')}
    require(len(raw['data']) % 8 == 0 and len(raw['indices']) == len(raw['data'])
        and len(raw['indptr']) == (rows + 1) * 8, 'exact CSR wire byte lengths required')
    data = np.frombuffer(raw['data'], dtype='<f8')
    indices = np.frombuffer(raw['indices'], dtype='<i8')
    indptr = np.frombuffer(raw['indptr'], dtype='<i8')
    # Validate before SciPy can truncate trailing bytes or coerce bad indices.
    require(indptr[0] == 0 and indptr[-1] == len(data) and np.all(indptr[1:] >= indptr[:-1])
        and np.all((indices >= 0) & (indices < width)) and np.isfinite(data).all(),
        'strict serialized CSR ranges/terminal pointer/finite values required')
    for lo, hi in zip(indptr, indptr[1:]):
        require(not np.any(np.diff(indices[lo:hi]) <= 0), 'strict serialized sorted unique CSR coordinates required')
    matrix = sparse.csr_matrix((data, indices, indptr), shape=(rows, width), copy=False)
    # SciPy may select int32 for small matrices. Restore the defined wire type.
    matrix.data = data; matrix.indices = indices; matrix.indptr = indptr
    _csr(matrix, rows, width)
    return matrix


def decode_inputs(value):
    """Strict JSON object decoder; requires separately authenticated raw SHA."""
    _fields(value, {'kind', 'configuration', *FoldInputs.__dataclass_fields__}, 'serialized joint capsule')
    require(value['kind'] == VERSION and _same(value['configuration'], configuration()), 'fixed joint feature configuration required')
    require(type(value['examples']) is list and type(value['banks']) is dict and type(value['raw_current']) is dict
        and type(value['interactions']) is dict and set(value['interactions']) == set(ARMS)
        and type(value['parent_predictions']) is list, 'strict serialized capsule sequence/maps required')
    examples = []; banks = {}; raw_current = {}; interactions = {arm: {} for arm in ARMS}
    for row in value['examples']:
        _fields(row, Example.__dataclass_fields__, 'serialized Example')
        obs = row['observation']; _fields(obs, ('problem_id', 'current', 'prior'), 'serialized observation')
        require(type(obs['prior']) is list and type(row['donor_history']) is list, 'complete serialized history lists required')
        examples.append(Example(row['example_id'], row['user_id'], row['split'], row['bank_id'],
            PilotObservation(obs['problem_id'], original._decode_source(obs['current']),
                tuple(original._decode_source(s) for s in obs['prior'])),
            tuple(original._decode_source(s) for s in row['donor_history'])))
    for bid, row in value['banks'].items():
        _fields(row, ('problem_id', 'current_source_hex', 'generator_config_sha256', 'seeds', 'attempts', 'bank_seal_sha256', 'candidate_ids'),
            'serialized CandidateBank')
        require(type(row['seeds']) is list and type(row['attempts']) is list, 'exact bank ledger lists required')
        attempts = []
        for attempt in row['attempts']:
            _fields(attempt, ('index', 'seed', 'status', 'source_hex', 'error'), 'serialized CandidateAttempt')
            attempts.append(CandidateAttempt(attempt['index'], attempt['seed'], attempt['status'],
                None if attempt['source_hex'] is None else original._hex(attempt['source_hex']), attempt['error']))
        bank = CandidateBank(row['problem_id'], original._hex(row['current_source_hex']), row['generator_config_sha256'],
            tuple(row['seeds']), tuple(attempts))
        require(row['bank_seal_sha256'] == bank.seal_sha256 and _same(row['candidate_ids'], [c.candidate_id for c in bank.candidates]),
            'exact bank seal/candidate order required')
        banks[bid] = bank
    for bid, row in value['raw_current'].items():
        _fields(row, features.RawCurrent.__dataclass_fields__, 'serialized RawCurrent')
        require(type(row['candidate_ids']) is list, 'ordered raw-current candidate list required')
        ids = tuple(row['candidate_ids'])
        raw_current[bid] = features.RawCurrent(row['bank_id'], row['bank_seal_sha256'], ids,
            _decode_csr(row['numeric'], len(ids), 3), _decode_csr(row['hashed'], len(ids), 4096))
    for arm in ARMS:
        require(type(value['interactions'][arm]) is dict, 'serialized progress bank map required')
        for bid, row in value['interactions'][arm].items():
            _fields(row, ('candidate_ids', 'dtype', 'shape', 'data_hex'), 'serialized progress32 block')
            require(type(row['candidate_ids']) is list and type(row['shape']) is list and len(row['shape']) == 2
                and all(type(v) is int and v > 0 for v in row['shape'])
                and row['shape'] == [len(row['candidate_ids']), 32] and row['dtype'] == '<f8', 'exact float64[n,32] wire format required')
            raw = original._hex(row['data_hex'])
            require(len(raw) == row['shape'][0] * 32 * 8, 'exact progress matrix byte length required')
            x = np.frombuffer(raw, dtype='<f8').reshape(tuple(row['shape'])).astype(np.float64, copy=False)
            interactions[arm][bid] = CandidateBlock(tuple(row['candidate_ids']), x)
    inputs = FoldInputs(value['fold'], tuple(examples), banks, _clone(value['assignment']), raw_current, interactions,
        tuple(_clone(value['parent_predictions'])), _clone(value['parent_training']), value['parent_structure_model_sha256'],
        value['fold_assignment_sha256'], value['readiness_complete_sha256'], value['synthetic'])
    validate_inputs(inputs)
    return inputs
