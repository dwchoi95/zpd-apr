"""One frozen train-only, user-grouped history-action crossfit; never repair code.

No held-out outcome files, generation, execution or hyperparameter search. The
future target store is used only by encode_edit, never by observation/donor APIs.
All six arms share each fold's donor-supported training and scoring populations.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
from scipy import sparse
from scipy.special import expit
from sklearn.feature_extraction import FeatureHasher
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import normalize

from scripts.audit_zpd_history_support import match_donors
from scripts.prepare_zpd_train_successors import FEATURE_FIELDS, category
from scripts.zpd_history_predictor import lexical_tokens

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'analysis_protocols/zpd-history-action-cv-20260923.md'
PREPARED_MANIFEST_SHA = '4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d'
SUCCESSOR_COMPLETE_SHA = '40b25a7ff27664cd88b0b83d9d4ed87f74c2a12c649493dfeca7b8994e950932'
ARMS = ('C0', 'Cn', 'H', 'U', 'HS', 'L')
CONTROLS = ('Cn', 'U', 'HS', 'L')
FOLDS = 5
FOLD_SALT = 'history-action-cv-20260923-v1'
HASH_DIMENSION = 4096
SEED = 2027
EPOCHS = 20
ALPHA = 1e-4
BOOTSTRAP_DRAWS = 5000
TARGET_FIELDS = {'current_nominal_verdict', 'current_submission_id', 'current_timestamp',
    'example_id', 'legacy_next_label', 'missing_reason', 'next_code', 'next_filename_ext',
    'next_label', 'next_language', 'next_nominal_verdict', 'next_source_bytes',
    'next_source_path_relative', 'next_source_sha256', 'next_submission_id', 'next_timestamp',
    'problem_id', 'split', 'target_status', 'user_id'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def rows(path):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    with partial.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, ensure_ascii=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    os.replace(partial, path)


def atomic_rows(path, values):
    path = Path(path); partial = path.with_name(path.name + '.partial')
    with partial.open('w', encoding='utf-8') as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False) + '\n')
        stream.flush(); os.fsync(stream.fileno())
    os.replace(partial, path)


def _check(bindings):
    for path, expected in bindings.items():
        if sha(path) != expected:
            raise ValueError('input/source seal mismatch: ' + str(path))


def load_inputs(project, *, production=True):
    """Join only allowed observed code IDs; never open any verdict label file."""
    project = Path(project)
    prepared = project / 'outputs/zpd-history-gate-20260915/prepared-inputs'
    original = project / 'outputs/zpd-history-gate-20260915/original-prefixes'
    successors = project / 'outputs/zpd-train-successors-20260923/prepared-train-v1'
    bindings = {p: sha(p) for p in (prepared/'manifest.json', original/'manifest.json',
                                   successors/'manifest.json', successors/'COMPLETE.json')}
    if production and (bindings[prepared/'manifest.json'] != PREPARED_MANIFEST_SHA or
                       bindings[successors/'COMPLETE.json'] != SUCCESSOR_COMPLETE_SHA):
        raise ValueError('wrong frozen prepared or successor family')
    prep, orig, target_manifest, complete = [read(p) for p in
        (prepared/'manifest.json', original/'manifest.json', successors/'manifest.json', successors/'COMPLETE.json')]
    if (complete.get('status') != 'complete' or complete.get('fitting_performed') is not False or
        complete.get('manifest_sha256') != bindings[successors/'manifest.json'] or
        complete.get('output_sha256') != target_manifest.get('output_sha256') or
        set(complete.get('output_sha256', {})) != {'targets-train.jsonl'} or
        complete.get('protocol_sha256') != target_manifest.get('protocol_sha256') or
        target_manifest.get('kind') != 'label_only_immediate_training_successors' or
        target_manifest.get('valid_test_labels_opened') is not False or
        target_manifest.get('combined_original_labels_opened') is not False or
        target_manifest.get('prepared_manifest_sha256') != bindings[prepared/'manifest.json'] or
        target_manifest.get('original_manifest_sha256') != bindings[original/'manifest.json'] or
        prep.get('source_manifest_sha256') != bindings[original/'manifest.json']):
        raise ValueError('strict sealed C0 ancestry required')
    for name in ('features.jsonl', 'codes.jsonl'):
        bindings[prepared/name] = prep['file_sha256'][name]
    bindings[successors/'targets-train.jsonl'] = complete['output_sha256']['targets-train.jsonl']
    _check(bindings)
    features = {}; all_ids = set(); splits = {}; split_counts = Counter()
    for row in rows(prepared/'features.jsonl'):
        if set(row) != FEATURE_FIELDS or row['split'] not in ('train', 'valid', 'test'):
            raise ValueError('strict prepared feature schema required')
        if row['example_id'] in all_ids or splits.setdefault(row['user_id'], row['split']) != row['split']:
            raise ValueError('duplicate ID or split-crossing user')
        all_ids.add(row['example_id']); split_counts[row['split']] += 1
        if row['split'] != 'train':
            continue
        if (row['current_code_id'] != row['example_id'] or not row['history'] or
                category(row['matching_current_verdict']) != row['current_verdict']):
            raise ValueError('invalid training current/history')
        chain = row['history'] + [{'code_id':row['current_code_id'], 'verdict':row['current_verdict'], 'timestamp':row['timestamp']}]
        if any(set(p) != {'code_id', 'verdict', 'timestamp'} for p in chain):
            raise ValueError('observed history allowlist violation')
        times = [p['timestamp'] for p in chain]
        if any(type(t) not in (int, float) or not math.isfinite(t) for t in times) or any(a >= b for a,b in zip(times,times[1:])):
            raise ValueError('strict observed chronology required')
        if len({p['code_id'] for p in chain}) != len(chain):
            raise ValueError('duplicate observed submission identity')
        features[row['example_id']] = row
    if dict(split_counts) != prep['counts'] or not features:
        raise ValueError('prepared counts mismatch')
    needed = {key for r in features.values() for key in [r['current_code_id'], *[p['code_id'] for p in r['history']]]}
    language = {}; raw_shas = {}
    for path, digest in orig['source_sha256'].items():
        value = Path(path); pid, lang, filename = value.parts[-3:]
        ident = pid + ':' + filename.rsplit('.', 1)[0]
        if ident not in needed:
            continue
        if ident in language and (language[ident] != lang or raw_shas[ident] != digest):
            raise ValueError('conflicting observed source binding')
        language[ident], raw_shas[ident] = lang, digest
    codes = {}
    for row in rows(prepared/'codes.jsonl'):
        if row['code_id'] not in needed:
            continue  # No non-observed code is retained or passed to an encoder.
        ident = row['code_id']
        if ident in codes or set(row) != {'code_id', 'code', 'source_sha256'} or type(row['code']) is not str:
            raise ValueError('strict unique observed code schema required')
        digest = hashlib.sha256(row['code'].encode('utf-8')).hexdigest()
        if digest != row['source_sha256'] or raw_shas.get(ident) != digest:
            raise ValueError('observed exact-source SHA mismatch')
        codes[ident] = row['code']
    if set(codes) != needed or set(language) != needed:
        raise ValueError('observed source/language coverage incomplete')
    observations = []
    for ident, f in sorted(features.items()):
        if language[f['current_code_id']] != 'Python':
            raise ValueError('current source must be Python')
        observations.append(dict(example_id=ident, user_id=f['user_id'], problem_id=f['problem_id'], split='train',
            timestamp=f['timestamp'], current_code=codes[f['current_code_id']], current_verdict=f['current_verdict'],
            matching_current_verdict=f['matching_current_verdict'],
            current_source_sha256=raw_shas[f['current_code_id']],
            history=[dict(code=codes[h['code_id']], verdict=h['verdict'], timestamp=h['timestamp'],
                          language=language[h['code_id']]) for h in f['history']]))
    targets = {}; coverage = Counter()
    for target in rows(successors/'targets-train.jsonl'):
        ident = target.get('example_id')
        if set(target) != TARGET_FIELDS or ident not in features or ident in targets or target['split'] != 'train':
            raise ValueError('strict full training successor schema required')
        f = features[ident]
        if (target['user_id'] != f['user_id'] or target['problem_id'] != f['problem_id'] or
            target['current_timestamp'] != f['timestamp'] or target['current_nominal_verdict'] != f['matching_current_verdict'] or
            ident != target['problem_id'] + ':' + target['current_submission_id']):
            raise ValueError('successor current binding mismatch')
        if target['target_status'] == 'available':
            code = target['next_code']
            if (type(code) is not str or target['missing_reason'] is not None or
                type(target['next_timestamp']) not in (int, float) or target['next_timestamp'] <= f['timestamp'] or
                target['next_submission_id'] == target['current_submission_id'] or not target['next_language'] or
                len(code.encode('utf-8')) != target['next_source_bytes'] or
                hashlib.sha256(code.encode('utf-8')).hexdigest() != target['next_source_sha256']):
                raise ValueError('available successor bytes/time mismatch')
            coverage['python_available' if target['next_language'] == 'Python' else 'nonpython_available'] += 1
        elif target['target_status'] == 'unavailable' and target['next_code'] is None and target['missing_reason']:
            coverage['unavailable'] += 1
        else:
            raise ValueError('unknown successor availability status')
        targets[ident] = target
    if set(targets) != set(features) or complete['train_prefixes'] != len(features):
        raise ValueError('full training successor coverage required')
    if production and (len(features) != 71191 or len({o['user_id'] for o in observations}) != 8473 or
                       len({o['problem_id'] for o in observations}) != 23):
        raise ValueError('frozen71191/8473/23 training population required')
    coverage.update(prefixes=len(observations), users=len({o['user_id'] for o in observations}),
                    problems=len({o['problem_id'] for o in observations}), observed_source_ids=len(needed))
    return observations, targets, dict(coverage), bindings


def assign_folds(observations):
    if not observations or any(o['split'] != 'train' for o in observations):
        raise ValueError('nonempty train-only observations required')
    if len({o['example_id'] for o in observations}) != len(observations):
        raise ValueError('duplicate observation')
    user_fold = {user:int(hashlib.sha256((FOLD_SALT+'|'+user).encode()).hexdigest(), 16) % FOLDS
                 for user in sorted({o['user_id'] for o in observations})}
    return dict(salt=FOLD_SALT, user_fold=user_fold,
                example_fold={o['example_id']:user_fold[o['user_id']] for o in observations})


@lru_cache(maxsize=131072)
def _token_count(code):
    return len(lexical_tokens(code)[0])


def fold_cohorts(observations, assignment, fold):
    """Feature-only donor assignment BEFORE any target/mask availability check."""
    summaries = [dict(example_id=o['example_id'], user_id=o['user_id'], problem_id=o['problem_id'],
        split='train', timestamp=o['timestamp'], current_verdict=o['matching_current_verdict'],
        prior_count=len(o['history']), prior_tokens=sum(_token_count(h['code']) for h in o['history']))
        for o in observations]
    allowed = {o['user_id'] for o in observations if assignment['user_fold'][o['user_id']] != fold}
    donors = match_donors(summaries, allowed_donor_users=allowed)
    index = {o['example_id']:i for i,o in enumerate(observations)}
    train, held = [], []
    for i, o in enumerate(observations):
        donor = donors[o['example_id']]
        if donor is None:
            continue
        d = observations[index[donor]]
        if d['user_id'] not in allowed or d['user_id'] == o['user_id'] or d['timestamp'] >= o['timestamp']:
            raise ValueError('fold donor leakage')
        (held if o['user_id'] not in allowed else train).append(i)
    return np.asarray(train, dtype=int), np.asarray(held, dtype=int), donors


def encode_targets(observations, targets, encoder, *, callback=None):
    y = np.zeros((len(observations), len(encoder.EVENTS)), dtype=float)
    mask = np.zeros_like(y, dtype=bool)
    for i,o in enumerate(observations):
        target = targets[o['example_id']]
        if target['target_status'] == 'available':
            values, available = encoder.encode_edit(o['current_code'], target['next_code'], 'Python', target['next_language'])
            y[i], mask[i] = values, available
        if callback and ((i+1)%1000 == 0 or i+1 == len(observations)):
            callback(dict(phase='encoding_targets', completed_examples=i+1,total_examples=len(observations)))
    if not np.isfinite(y).all() or not np.isin(y[mask], [0., 1.]).all():
        raise ValueError('binary observed event labels required')
    return y, mask


def encode_matrix(observations, indices, arm, encoder, *, donors=None, callback=None):
    if arm not in ARMS:
        raise ValueError('unknown arm')
    indexed = {o['example_id']:o for o in observations}
    hasher = FeatureHasher(n_features=HASH_DIMENSION, input_type='dict', alternate_sign=True, dtype=np.float64)
    blocks = []; bags = []
    for done, i in enumerate(indices, 1):
        o = observations[int(i)]
        args = (o['current_code'], o['current_verdict'], o['history'], o['timestamp'])
        if arm == 'U':
            if donors is None or donors[o['example_id']] is None:
                raise ValueError('U requires matched donor')
            donor = indexed[donors[o['example_id']]]
            bag = encoder.encode_observation(o['current_code'], o['current_verdict'], donor['history'], o['timestamp'], 'H')
            bag.update(encoder.encode_observation(*args, 'Cn'))
        elif arm == 'L':
            bag = encoder.encode_observation(o['current_code'], o['current_verdict'], o['history'][-1:], o['timestamp'], 'H')
            bag.update(encoder.encode_observation(*args, 'Cn'))
        else:
            bag = encoder.encode_observation(*args, arm, shuffle_key=o['example_id'])
        if any(type(k) is not str or not math.isfinite(v) for k,v in bag.items()):
            raise ValueError('finite observation-only feature dictionary required')
        bags.append(bag)
        if len(bags) == 1000 or done == len(indices):
            blocks.append(normalize(hasher.transform(bags), norm='l2', axis=1, copy=False)); bags=[]
            if callback:
                callback(dict(phase='encoding_observations', arm=arm, completed_examples=done, total_examples=len(indices)))
    return sparse.vstack(blocks, format='csr') if blocks else sparse.csr_matrix((0,HASH_DIMENSION))


def label_weights(users, mask):
    """Same fixed weight for a prefix/event in every head; no head renormalizing."""
    counts = np.asarray(mask.sum(axis=1), dtype=int)
    evaluable = counts > 0
    per_user = Counter(user for user, ok in zip(users,evaluable) if ok)
    weights = np.zeros(len(users), dtype=float)
    for i, user in enumerate(users):
        if evaluable[i]:
            weights[i] = 1. / (per_user[user] * counts[i])
    if per_user:
        weights *= int(evaluable.sum()) / len(per_user)
    if not np.isclose(float(np.sum(weights*counts)), int(evaluable.sum())):
        raise ValueError('user/event weight mass mismatch')
    return weights


def fit_heads(x, y, mask, users, events, *, callback=None):
    if x.shape != (len(users), HASH_DIMENSION) or y.shape != mask.shape or y.shape != (len(users),len(events)):
        raise ValueError('head training shape mismatch')
    weights = label_weights(users, mask); heads=[]
    for event, name in enumerate(events):
        chosen = np.flatnonzero(mask[:,event]); yy=y[chosen,event]; ww=weights[chosen]
        metadata = dict(event=name, observed_prefixes=len(chosen), observed_users=len(set(users[i] for i in chosen)),
            positive_prefixes=int(yy.sum()), total_weight=float(ww.sum()), positive_weight=float(ww@yy))
        if not len(chosen) or len(np.unique(yy)) == 1:
            probability=(float(ww@yy)+1.)/(float(ww.sum())+2.)
            heads.append(dict(kind='laplace_constant', probability=probability, **metadata))
            if callback:
                callback(dict(phase='head_complete', event=name, training='constant', completed_train_prefix_event_exposures=0))
            continue
        xx=x[chosen]; model=SGDClassifier(loss='log_loss', penalty='l2', alpha=ALPHA,
            learning_rate='optimal', shuffle=False, random_state=SEED, average=False)
        rng=np.random.default_rng(SEED)
        for epoch in range(EPOCHS):
            order=rng.permutation(len(chosen))
            model.partial_fit(xx[order], yy[order], classes=np.array([0.,1.]), sample_weight=ww[order])
            if callback:
                callback(dict(phase='training', event=name, epoch=epoch+1, epochs=EPOCHS,
                    completed_train_prefix_event_exposures=(epoch+1)*len(chosen),
                    total_train_prefix_event_exposures=EPOCHS*len(chosen), unique_train_prefixes=len(chosen)))
        if not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all():
            raise ValueError('nonfinite fitted head')
        heads.append(dict(kind='linear_logistic', coefficients=model.coef_[0].tolist(),
            intercept=float(model.intercept_[0]), **metadata))
    return dict(events=list(events), hash_dimension=HASH_DIMENSION, alpha=ALPHA, seed=SEED,
                epochs=EPOCHS, weighting='user_equal_prefix_mean_event_mask_no_head_renormalization', heads=heads)


def predict_heads(model, x):
    if x.shape[1] != model['hash_dimension'] or len(model['events']) != len(model['heads']):
        raise ValueError('prediction/model shape mismatch')
    probabilities=[]
    for name, head in zip(model['events'],model['heads']):
        if head['event'] != name:
            raise ValueError('head event order mismatch')
        if head['kind'] == 'laplace_constant':
            p=np.full(x.shape[0],head['probability'], dtype=float)
        elif head['kind'] == 'linear_logistic':
            coefficients=np.asarray(head['coefficients'], dtype=float)
            if coefficients.shape != (model['hash_dimension'],):
                raise ValueError('head coefficient shape mismatch')
            p=expit(x@coefficients+head['intercept'])
        else:
            raise ValueError('unknown head kind')
        if not np.isfinite(p).all() or (p<0).any() or (p>1).any():
            raise ValueError('invalid predicted probability')
        probabilities.append(p)
    return np.column_stack(probabilities)


def summarize_predictions(predictions, events):
    """Prefix masked mean -> mean prefixes per user -> equal mean users."""
    output={}; user_losses={}
    for arm in ARMS:
        by_user=defaultdict(list); event_users={name:defaultdict(list) for name in events}
        event_rows=Counter(); event_positive=Counter(); all_masked=0
        for row in predictions:
            y=np.asarray(row['values'], dtype=float); mask=np.asarray(row['mask'], dtype=bool)
            p=np.asarray(row['probabilities'][arm], dtype=float)
            if (y.shape != (len(events),) or mask.shape != y.shape or p.shape != y.shape or
                not np.isfinite(p).all() or (p<0).any() or (p>1).any() or not np.isin(y[mask],[0.,1.]).all()):
                raise ValueError('strict finite masked prediction schema required')
            p=np.clip(p,1e-12,1.-1e-12)
            loss=-(y*np.log(p)+(1-y)*np.log1p(-p))
            if mask.any():
                by_user[row['user_id']].append(float(loss[mask].mean()))
            else:
                all_masked+=1
            for j,name in enumerate(events):
                if mask[j]:
                    event_users[name][row['user_id']].append(float(loss[j])); event_rows[name]+=1; event_positive[name]+=int(y[j])
        user_losses[arm]={user:float(np.mean(values)) for user,values in sorted(by_user.items())}
        output[arm]=dict(user_equal_masked_nll=float(np.mean(list(user_losses[arm].values()))) if by_user else None,
            users=len(by_user), evaluable_prefixes=len(predictions)-all_masked, all_masked_prefixes=all_masked,
            events={name:dict(prefixes=event_rows[name], users=len(event_users[name]), positive_prefixes=event_positive[name],
                user_equal_nll=float(np.mean([np.mean(v) for v in event_users[name].values()])) if event_users[name] else None)
                for name in events})
    return output, user_losses


def bootstrap_contrasts(user_losses, *, draws=BOOTSTRAP_DRAWS):
    users=sorted(user_losses['H'])
    if any(set(user_losses[c]) != set(users) for c in CONTROLS):
        raise ValueError('paired user coverage mismatch')
    if len(users)<2:
        return {c:dict(status='insufficient_users', users=len(users), upper=None, lower=None) for c in CONTROLS}
    differences=np.asarray([[user_losses['H'][u]-user_losses[c][u] for c in CONTROLS] for u in users])
    rng=np.random.default_rng(SEED); samples=[]
    for begin in range(0,draws,100):
        indices=rng.integers(0,len(users),size=(min(100,draws-begin),len(users)))
        samples.append(differences[indices].mean(axis=1))
    distribution=np.vstack(samples); lower,upper=np.quantile(distribution,[.05/(2*len(CONTROLS)),1-.05/(2*len(CONTROLS))],axis=0)
    return {c:dict(status='descriptive_crossfit_bootstrap', users=len(users), draws=draws, seed=SEED,
        mean=float(differences[:,j].mean()), lower=float(lower[j]), upper=float(upper[j]),
        interval='two-sided Bonferroni98.75percent percentile; four prespecified contrasts; not confirmatory')
        for j,c in enumerate(CONTROLS)}


def decision(overall, folds, intervals):
    checks={}
    h=overall['H']['user_equal_masked_nll']
    for c in CONTROLS:
        lower=sum(f['H']['user_equal_masked_nll'] is not None and f[c]['user_equal_masked_nll'] is not None and
                  f['H']['user_equal_masked_nll'] < f[c]['user_equal_masked_nll'] for f in folds.values())
        other=overall[c]['user_equal_masked_nll']; upper=intervals[c]['upper']
        checks[c]=dict(aggregate_strictly_better=h is not None and other is not None and h<other,
            strictly_better_folds=lower, at_least_four_folds=lower>=4,
            simultaneous_upper_below_zero=upper is not None and upper<0)
    passed=len(folds)==FOLDS and all(v['aggregate_strictly_better'] and v['at_least_four_folds'] and
                                   v['simultaneous_upper_below_zero'] for v in checks.values())
    return dict(gate_passed=passed, checks=checks, confirmatory=False, learner_benefit_established=False,
                next_action='independent_result_audit_then_separately_frozen_repair_integration' if passed else
                'retain_negative_result_and_diagnose_train_only', full_train_refit_authorized=False)


def run_data(observations, targets, output, encoder, *, manifest, bindings=None):
    """Synthetic-testable engine. Real runs call run_cv for provenance checks."""
    output=Path(output)
    if output.exists():
        raise FileExistsError('new output required; no automatic resume of partial runs')
    output.mkdir(parents=True); started=time.time(); bindings=bindings or {}
    def event(value):
        value=dict(value, elapsed_seconds=time.time()-started, timestamp=time.time())
        with (output/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n'); stream.flush(); os.fsync(stream.fileno())
        atomic_json(output/'STATUS.json',value)
        print(json.dumps(value,sort_keys=True),flush=True)
    atomic_json(output/'manifest.json',manifest)
    assignment=assign_folds(observations); atomic_json(output/'folds.json',assignment)
    # Matching is sealed before even encoding future targets. It depends on the
    # full observed training population, not source/event/target availability.
    cohorts={fold:fold_cohorts(observations,assignment,fold) for fold in range(FOLDS)}
    total_oof_supported=sum(len(value[1]) for value in cohorts.values())
    cohort_seals={}
    for fold,(train,held,donors) in cohorts.items():
        frozen=dict(train_example_ids=[observations[i]['example_id'] for i in train],
                    held_example_ids=[observations[i]['example_id'] for i in held],donor_assignments=donors)
        cohort_seals[str(fold)]=hashlib.sha256(json.dumps(frozen,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    atomic_json(output/'COHORTS_COMPLETE.json',dict(status='observed_only_cohorts_sealed_before_target_encoding',
        fold_cohort_sha256=cohort_seals,total_oof_supported=total_oof_supported))
    event(dict(phase='encode_training_targets', total_examples=len(observations)))
    y,mask=encode_targets(observations,targets,encoder,callback=event)
    atomic_json(output/'target-coverage.json',dict(prefixes=len(observations),all_masked=int((~mask.any(axis=1)).sum()),
        next_languages=dict(Counter(targets[o['example_id']]['next_language'] or 'unavailable' for o in observations)),
        target_status=dict(Counter(targets[o['example_id']]['target_status'] for o in observations)),
        mask_patterns=dict(Counter(''.join('1' if v else '0' for v in row) for row in mask)),
        events={name:dict(observed=int(mask[:,i].sum()),positive=int(y[mask[:,i],i].sum())) for i,name in enumerate(encoder.EVENTS)}))
    # Pure observation features can be shared across folds: no fitted transform,
    # labels, vocabulary, corpus frequencies or normalization across rows exist.
    cache={arm:encode_matrix(observations,np.arange(len(observations)),arm,encoder,callback=event)
           for arm in ('C0','Cn','H','HS','L')}
    equal_history_features=np.asarray((cache['H']-cache['HS']).getnnz(axis=1)==0).reshape(-1)
    all_predictions=[]; fold_summaries={}; fold_coverage={}; artifacts=['manifest.json','folds.json','COHORTS_COMPLETE.json','target-coverage.json']
    for fold in range(FOLDS):
        directory=output/f'fold-{fold}'; directory.mkdir()
        train,held,donors=cohorts[fold]
        if not len(train) or not len(held):
            raise ValueError('empty fold donor-supported train/held cohort; no substitution')
        cohort=dict(fold=fold,train_example_ids=[observations[i]['example_id'] for i in train],
            held_example_ids=[observations[i]['example_id'] for i in held],donor_assignments=donors,
            original_train_prefixes=sum(v!=fold for v in assignment['example_fold'].values()),
            original_held_prefixes=sum(v==fold for v in assignment['example_fold'].values()),
            train_prefixes=len(train),held_prefixes=len(held),
            train_all_masked=int((~mask[train].any(axis=1)).sum()),held_all_masked=int((~mask[held].any(axis=1)).sum()))
        atomic_json(directory/'cohort.json',cohort); fold_coverage[str(fold)]={k:v for k,v in cohort.items() if k not in ('train_example_ids','held_example_ids','donor_assignments')}
        probabilities={}; files=['cohort.json']
        for arm in ARMS:
            event(dict(phase='arm_start',fold=fold,arm=arm,train_prefixes=len(train),held_prefixes=len(held)))
            if arm=='U':
                joined=np.concatenate([train,held])
                x=encode_matrix(observations,joined,arm,encoder,donors=donors,
                    callback=lambda v:event(dict(v,fold=fold)))
                xt,xh=x[:len(train)],x[len(train):]
            else:
                xt,xh=cache[arm][train],cache[arm][held]
            model=fit_heads(xt,y[train],mask[train],[observations[i]['user_id'] for i in train],encoder.EVENTS,
                            callback=lambda v:event(dict(v,fold=fold,arm=arm)))
            model.update(arm=arm,fold=fold,train_example_ids=cohort['train_example_ids'])
            atomic_json(directory/f'{arm}.json',model); files.append(f'{arm}.json')
            probabilities[arm]=predict_heads(model,xh)
        train_keys={(observations[i]['problem_id'],observations[i]['current_source_sha256']) for i in train}
        collision=defaultdict(list)
        for i in held:
            o=observations[i]
            hist=hashlib.sha256(json.dumps([(h['code'],h['verdict']) for h in o['history']],separators=(',',':')).encode()).hexdigest()
            collision[o['problem_id'],o['current_source_sha256']].append((o['user_id'],hist))
        distinct={key for key,values in collision.items() if len({u for u,h in values})>1 and len({h for u,h in values})>1}
        predictions=[]
        for j,i in enumerate(held):
            o=observations[i]; key=(o['problem_id'],o['current_source_sha256'])
            predictions.append(dict(example_id=o['example_id'],user_id=o['user_id'],problem_id=o['problem_id'],fold=fold,
                donor_example_id=donors[o['example_id']],values=y[i].tolist(),mask=mask[i].tolist(),
                target_status=targets[o['example_id']]['target_status'],next_language=targets[o['example_id']]['next_language'],
                current_source_sha256=o['current_source_sha256'],current_seen_in_fold_training=key in train_keys,
                within_held_cross_user_distinct_history_collision=key in distinct,
                hs_prior_length_one=len(o['history'])==1,
                hs_permutation_identity=tuple(encoder.permutation_indices(len(o['history']),o['example_id']))==tuple(range(len(o['history']))),
                hs_hashed_features_equal=bool(equal_history_features[i]),
                probabilities={arm:probabilities[arm][j].tolist() for arm in ARMS}))
        atomic_rows(directory/'predictions.jsonl',predictions);files.append('predictions.jsonl')
        summary,_=summarize_predictions(predictions,encoder.EVENTS); fold_summaries[str(fold)]=summary
        atomic_json(directory/'summary.json',summary);files.append('summary.json')
        atomic_json(directory/'COMPLETE.json',dict(status='complete',fold=fold,files_sha256={f:sha(directory/f) for f in files}))
        artifacts += [f'fold-{fold}/'+f for f in files+['COMPLETE.json']]
        all_predictions.extend(predictions)
        _check(bindings)
        event(dict(phase='fold_complete',fold=fold,completed_folds=fold+1,total_folds=FOLDS,
                   completed_oof_prefixes=len(all_predictions),total_oof_supported=total_oof_supported,
                   total_training_prefixes=len(observations)))
    if len({p['example_id'] for p in all_predictions})!=len(all_predictions):
        raise ValueError('OOF prefix predicted twice')
    overall,user_losses=summarize_predictions(all_predictions,encoder.EVENTS)
    intervals=bootstrap_contrasts(user_losses)
    strata={name:summarize_predictions([p for p in all_predictions if p[name]],encoder.EVENTS)[0]
            for name in ('current_seen_in_fold_training','within_held_cross_user_distinct_history_collision',
                         'hs_prior_length_one','hs_permutation_identity','hs_hashed_features_equal')}
    report=dict(kind='train_only_history_action_cv_v1',confirmatory=False,fresh_test_opened=False,
        events=list(encoder.EVENTS),results=overall,fold_results=fold_summaries,fold_coverage=fold_coverage,
        bootstrap_contrasts=intervals,decision=decision(overall,fold_summaries,intervals),strata=strata,
        source_population=len(observations),oof_donor_supported_prefixes=len(all_predictions),
        oof_users=len({p['user_id'] for p in all_predictions}),total_oof_supported=total_oof_supported,
        note='Observed next-action prediction only; no repair or educational-learning superiority claim.')
    _check(bindings)
    atomic_json(output/'report.json',report); artifacts.append('report.json')
    event(dict(phase='complete',completed_folds=FOLDS,completed_oof_prefixes=len(all_predictions),
               total_oof_supported=total_oof_supported,gate_passed=report['decision']['gate_passed']))
    artifacts += ['events.jsonl','STATUS.json']
    atomic_json(output/'COMPLETE.json',dict(status='complete',gate_passed=report['decision']['gate_passed'],
        files_sha256={f:sha(output/f) for f in artifacts},confirmatory=False,completed_folds=FOLDS,completed_arms=FOLDS*len(ARMS)))
    return report


def verify_run_artifacts(output):
    output=Path(output); marker=read(output/'COMPLETE.json')
    if marker.get('status')!='complete' or marker.get('completed_folds')!=FOLDS or marker.get('completed_arms')!=FOLDS*len(ARMS):
        raise ValueError('complete fixed30arm run required')
    for name,digest in marker['files_sha256'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or sha(output/name)!=digest:
            raise ValueError('run artifact seal mismatch')
    report=read(output/'report.json')
    if report['decision']['gate_passed'] != marker['gate_passed']:
        raise ValueError('gate/complete mismatch')
    return marker


def run_cv(project, output):
    from scripts import zpd_history_action_encoder as encoder
    project,output=Path(project).resolve(),Path(output).resolve()
    if output.parent!=project/'outputs/zpd-history-action-20260923':
        raise ValueError('canonical action output parent required')
    if output.exists():
        raise FileExistsError(output)
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed source checkout required')
    if not PROTOCOL.is_file():
        raise ValueError('frozen action CV protocol missing')
    versions={name:version(name) for name in ('numpy','scipy','scikit-learn')}
    if versions!={'numpy':'2.5.2','scipy':'1.18.1','scikit-learn':'1.9.0'}:
        raise ValueError('frozen numerical runtime mismatch')
    observations,targets,coverage,bindings=load_inputs(project)
    sources=[Path(__file__),Path(encoder.__file__),ROOT/'scripts/audit_zpd_history_support.py',
        ROOT/'scripts/prepare_zpd_train_successors.py',ROOT/'scripts/build_zpd_original_prefixes.py',ROOT/'scripts/zpd_history_predictor.py',
        ROOT/'scripts/zpd_repair_structure.py',ROOT/'scripts/zpd_repair_pairwise.py',PROTOCOL]
    bindings.update({path:sha(path) for path in sources})
    manifest=dict(kind='train_only_history_action_cv_v1',confirmatory=False,fresh_test_opened=False,
        source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_sha256={str(path.relative_to(ROOT)):sha(path) for path in sources},
        input_sha256={str(path):digest for path,digest in bindings.items() if path not in sources},
        protocol_sha256=sha(PROTOCOL),runtime=dict(versions,python=platform.python_version()),
        coverage=coverage,configuration=dict(arms=list(ARMS),events=list(encoder.EVENTS),folds=FOLDS,fold_salt=FOLD_SALT,
            hash_dimension=HASH_DIMENSION,normalization='signedhash_then_per_row_L2',seed=SEED,alpha=ALPHA,epochs=EPOCHS,
            controls=list(CONTROLS),probability_clip=1e-12,
            weighting='user_equal_prefix_mean_event_mask_no_head_renormalization',
            bootstrap_draws=BOOTSTRAP_DRAWS,bootstrap_quantiles=[.05/(2*len(CONTROLS)),1-.05/(2*len(CONTROLS))]),
        feature_target_boundary='Observed-code whitelist only; immediate future code enters encode_edit labels only.')
    try:
        report=run_data(observations,targets,output,encoder,manifest=manifest,bindings=bindings)
    except Exception as error:
        if output.is_dir() and not (output/'COMPLETE.json').exists():
            atomic_json(output/'STATUS.json',dict(phase='failed',error_type=type(error).__name__,error=str(error),timestamp=time.time()))
        raise
    verify_run_artifacts(output)
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    report=run_cv(args.project,args.output)
    print(json.dumps(report['decision'],sort_keys=True))
    return report


if __name__=='__main__':
    main()
