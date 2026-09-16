"""Bounded v2 development features. Frozen v1 encoding is imported unchanged.

No label access or estimator fitting. Every arm uses the fixed matched cohort.
Only a small 12-column numeric array is dense; code/history pooling stays sparse.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json

import numpy as np

from scripts.zpd_history_predictor import features, code_vectors, structural, validate_rows


ARMS = ('C_R', 'C_Z', 'H_PR', 'U_PR', 'H_PZ', 'U_PZ',
        'H_IR', 'U_IR', 'H_IZ', 'U_IZ', 'S_MR', 'S_MZ')
NUMERIC_NAMES = ('log1p_code_characters', 'log1p_prior_count', 'log1p_elapsed_seconds',
                 'log1p_repeated_current_verdict', 'log1p_adjacent_verdict_changes',
                 'log1p_trailing_exact_code_repeats', 'log1p_mean_token_edit',
                 'log1p_max_token_edit', 'log1p_last_token_edit',
                 'log1p_mean_time_gap', 'log1p_max_time_gap', 'log1p_last_time_gap')


def dimensions(arm, n_features=2**18):
    if arm not in ARMS:
        raise ValueError('unknown v2 condition')
    base = 2*n_features+10
    if arm[0] in 'HU':
        base += 2*n_features+48
        if arm[2] == 'I':
            base += 4*n_features+2
    elif arm[0] == 'S':
        base += 9
    return base


def reciprocal_weights(count):
    if not isinstance(count, int) or count < 1:
        raise ValueError('nonempty history required')
    weights = 1/np.arange(count, 0, -1, dtype=np.float64)
    return weights/weights.sum()


def numeric_values(rows):
    return np.asarray([list(np.log1p([len(r['current_code']), len(r['history']),
                          r['timestamp']-r['history'][0]['timestamp']])) + list(structural(r))
                       for r in rows], dtype=np.float64)


def numeric_columns(arm, n_features):
    columns = list(range(2*n_features+7, 2*n_features+10))
    if arm[0] == 'S':
        columns.extend(range(2*n_features+10, 2*n_features+19))
    return columns


def validate_development(rows, train_only=False):
    if not rows:
        raise ValueError('empty matched cohort')
    if any(r['split'] != 'train' if train_only else r['split'] not in ('train','valid') for r in rows):
        raise ValueError('train-only scaler' if train_only else 'v2 rejects test rows')
    if any(r.get('donor_history') is None for r in rows):
        raise ValueError('all v2 conditions require fixed matched rows')
    validate_rows(rows)


def recency_blocks(rows, current, condition, n_features):
    """Return normalized r/product blocks plus UNNORMALIZED geometric distances."""
    from scipy.sparse import csr_matrix, hstack
    from sklearn.preprocessing import normalize
    if condition not in ('H','U'):
        raise ValueError('history condition required')
    histories = [r['history'] if condition == 'H' else r['donor_history'] for r in rows]
    lookup = {code:i for i,code in enumerate(dict.fromkeys(h['code'] for hs in histories for h in hs))}
    rr, cc, values = [], [], []
    for index, history in enumerate(histories):
        pooled = {}
        for h, weight in zip(history, reciprocal_weights(len(history))):
            key = lookup[h['code']]
            pooled[key] = pooled.get(key,0.)+weight
        for key, weight in pooled.items():
            rr.append(index)
            cc.append(key)
            values.append(weight)
    pooling = csr_matrix((values,(rr,cc)),shape=(len(rows),len(lookup)),dtype=np.float64)
    recency = pooling @ code_vectors(list(lookup),n_features)
    normalized_r, products, distances = [], [], []
    for start in (0,n_features):
        x = current[:,start:start+n_features]
        r = recency[:,start:start+n_features]
        difference = x-r
        # Raw pre-normalization recency defines the distance, in [0,2].
        distance = np.sqrt(np.asarray(difference.multiply(difference).sum(axis=1)).reshape(-1))
        distances.append(distance)
        normalized_r.append(normalize(r,norm='l2',copy=True))
        products.append(normalize(x.multiply(r),norm='l2',copy=True))
    return hstack(normalized_r+products+[csr_matrix(np.column_stack(distances))],format='csr')


class HistoryV2Encoder:
    def __init__(self,n_features=2**18):
        if not isinstance(n_features,int) or n_features < 1:
            raise ValueError('positive hashing dimension required')
        self.n_features = n_features
        self.fitted = False

    def fit(self,trainrows,weights):
        if self.fitted:
            raise RuntimeError('scaler already frozen; no refitting')
        validate_development(trainrows,train_only=True)
        weights = np.asarray(weights,dtype=np.float64)
        if weights.shape != (len(trainrows),) or not np.isfinite(weights).all() or (weights <= 0).any():
            raise ValueError('positive finite training weights required')
        weights = weights/weights.sum()
        counts = Counter(r['user_id'] for r in trainrows)
        expected = np.asarray([1/counts[r['user_id']] for r in trainrows],dtype=np.float64)
        expected /= expected.sum()
        if not np.allclose(weights,expected,rtol=1e-12,atol=1e-15):
            raise ValueError('weights must be user-equal on fixed matched train cohort')
        values = numeric_values(trainrows)
        self.mean = np.sum(weights[:,None]*values,axis=0)
        self.variance = np.sum(weights[:,None]*(values-self.mean)**2,axis=0)
        constant = np.ptp(values,axis=0) == 0
        self.mean[constant] = values[0,constant]
        self.variance[constant] = 0
        self.scale = np.sqrt(self.variance)
        self.scale[self.scale == 0] = 1
        if not all(np.isfinite(x).all() for x in (self.mean,self.variance,self.scale)):
            raise ValueError('nonfinite numerical scaler')
        self.training_example_ids_sha256 = hashlib.sha256(json.dumps(
            [r['example_id'] for r in trainrows],separators=(',',':')).encode()).hexdigest()
        self.training_rows = len(trainrows)
        self.training_users = len(counts)
        self.fitted = True
        return self

    def transform(self,rows,arm):
        from scipy.sparse import csr_matrix, hstack
        if not self.fitted:
            raise RuntimeError('fit training scaler first, including raw arms')
        if arm not in ARMS:
            raise ValueError('unknown v2 condition')
        validate_development(rows)
        matrix = features(rows,arm[0],self.n_features)
        if arm[0] in 'HU' and arm[2] == 'I':
            matrix = hstack([matrix,recency_blocks(rows,matrix[:,:2*self.n_features],
                                                  arm[0],self.n_features)],format='csr')
        if arm.endswith('Z'):
            columns = numeric_columns(arm,self.n_features)
            # Columns are contiguous; no dense copy of the full feature matrix.
            start,end = columns[0],columns[-1]+1
            numeric = matrix[:,start:end].toarray()
            numeric = (numeric-self.mean[:len(columns)])/self.scale[:len(columns)]
            matrix = hstack([matrix[:,:start],csr_matrix(numeric),matrix[:,end:]],format='csr')
        if matrix.shape != (len(rows),dimensions(arm,self.n_features)) or not np.isfinite(matrix.data).all():
            raise ValueError('invalid v2 features')
        return matrix

    def state_dict(self):
        if not self.fitted:
            raise RuntimeError('scaler not fitted')
        return {'version':'history-v2-numeric-scaler-v1','n_features':self.n_features,
                'numeric_allowlist':list(NUMERIC_NAMES),'mean':self.mean.tolist(),
                'variance_ddof0':self.variance.tolist(),'scale':self.scale.tolist(),
                'training_rows':self.training_rows,'training_users':self.training_users,
                'training_example_ids_sha256':self.training_example_ids_sha256,
                'columns':{arm:numeric_columns(arm,self.n_features) for arm in ARMS},
                'distance_scaling':'none; raw pre-normalization per-block distance',
                'weighting':'normalized inverse matched-training user frequency'}

    @classmethod
    def from_state_dict(cls,state):
        if state.get('version') != 'history-v2-numeric-scaler-v1' or state.get('numeric_allowlist') != list(NUMERIC_NAMES):
            raise ValueError('unknown scaler schema or numeric allowlist')
        result = cls(state['n_features'])
        if state['columns'] != {arm:numeric_columns(arm,result.n_features) for arm in ARMS}:
            raise ValueError('invalid numerical columns')
        result.mean = np.asarray(state['mean'],dtype=np.float64)
        result.variance = np.asarray(state['variance_ddof0'],dtype=np.float64)
        result.scale = np.asarray(state['scale'],dtype=np.float64)
        if any(x.shape != (12,) or not np.isfinite(x).all() for x in (result.mean,result.variance,result.scale)):
            raise ValueError('invalid numerical scaler arrays')
        if (result.variance < 0).any():
            raise ValueError('negative variance')
        expected = np.sqrt(result.variance)
        expected[expected == 0] = 1
        if (result.variance < 0).any() or (result.scale <= 0).any() or not np.array_equal(result.scale,expected):
            raise ValueError('invalid variance/scale')
        result.training_rows = state['training_rows']
        result.training_users = state['training_users']
        result.training_example_ids_sha256 = state['training_example_ids_sha256']
        result.fitted = True
        return result
