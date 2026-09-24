"""Pure own-fold progress32 input projection; no I/O, fit, labels or release.

The coordinator must authenticate the original observations, readiness result,
same-fold frozen base model and exact projected base scores. This module checks
only supplied objects and their lossless JSON representation. A self-consistent
capsule does not establish that provenance: the worker additionally requires an
externally supplied capsule SHA and its separate own-label contract.

No global parent/model manifest, sibling training metadata, readiness body or
label-contract map is part of this schema. History language is intentionally
not guessed from the historical Example type; certified language/feedback and
feature reconstruction remain the coordinator's separately audited boundary.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
from itertools import combinations
import json
import math
import re

import numpy as np

from scripts import zpd_repair_progress_newton as newton
from scripts import zpd_statement_sample_progress as progress
from scripts.run_zpd_repair_structure_cv import assign_folds
from scripts.zpd_repair_fit import Example
from src.repair.pilot_contracts import (
    CandidateAttempt, CandidateBank, ObservationSource, PilotObservation,
    canonical_hash, source_hash)

VERSION='repair_progress_own_fold_capsule_v1'
SPEC=newton.ResidualSpec(progress.VERSION,32,canonical_hash(progress.configuration()),newton.KIND)
ARMS=('H','Jm','HS','U','L','CF')
BASELINES=('structural_C','lexical_C')
PARENT_METHODS=(*BASELINES,'first_attempt','noop')
PREDICTION_FIELDS={'example_id','user_id','bank_id','problem_id','fold','bank_seal_sha256','choices','candidate_scores'}
TRAINING_FIELDS={'train_prefixes','train_users','informative_train_prefixes','uninformative_train_prefixes',
    'users','users_without_informative_prefix','ordered_pairs','pair_example_ids','informative_train_example_ids',
    'uninformative_train_example_ids','stable_train_candidates','weight_normalization','reference_pair_weight',
    'sample_weight_sum','prior_mean_one_weight_sum'}
NORM_ALLOWANCE=1e-12  # Analytic bound roundoff only, never Newton acceptance.


@dataclass(frozen=True)
class FoldInputs:
    fold:int
    examples:tuple[Example,...]
    banks:dict[str,CandidateBank]
    assignment:dict
    interactions:dict[str,dict[str,newton.CandidateBlock]]
    base_scores:dict[str,dict[str,float]]
    parent_predictions:tuple[dict,...]
    parent_training:dict
    parent_structure_model_sha256:str
    fold_assignment_sha256:str
    readiness_complete_sha256:str
    synthetic:bool=False


def require(condition,message):
    if not condition:raise ValueError(message)


def _text(value):return type(value) is str and bool(value)
def _sha(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def _real(value):return type(value) in (int,float) and math.isfinite(value)
def _fields(value,fields,name):
    require(type(value) is dict and set(value)==set(fields),'strict '+name+' fields required')
def _json(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)
def _same(a,b):return _json(a)==_json(b)
def _clone(value):return json.loads(_json(value))


def _typed(value,cls,name):
    require(type(value) is cls and set(vars(value))==set(cls.__dataclass_fields__),
        'exact '+name+' object without extra payload required')


def _source(source):
    _typed(source,ObservationSource,'observation source')
    require(_text(source.submission_id) and _text(source.verdict) and _real(source.timestamp)
        and type(source.source) is bytes and _sha(source.source_sha256)
        and source_hash(source.source)==source.source_sha256,'exact source bytes/SHA/time/verdict required')
    source.__post_init__()


def scope(inputs):
    """Pure original-order own training/held scopes; validate_inputs first."""
    return tuple(ex for ex in inputs.examples if inputs.assignment['example_fold'][ex.example_id]!=inputs.fold),\
        tuple(ex for ex in inputs.examples if inputs.assignment['example_fold'][ex.example_id]==inputs.fold)


def _training(info,train,banks):
    _fields(info,TRAINING_FIELDS,'own-parent training metadata')
    counts=('train_prefixes','train_users','informative_train_prefixes','uninformative_train_prefixes',
        'users','users_without_informative_prefix','ordered_pairs','stable_train_candidates')
    require(all(type(info[k]) is int and info[k]>=0 for k in counts),'strict own-parent training integer counts required')
    for key in ('pair_example_ids','informative_train_example_ids','uninformative_train_example_ids'):
        require(type(info[key]) is list and all(_text(v) for v in info[key]),'own-parent identity lists required')
    ids=[ex.example_id for ex in train];users={ex.user_id for ex in train}
    positive=info['informative_train_example_ids'];empty=info['uninformative_train_example_ids'];pairs=info['pair_example_ids']
    require(len(positive)==len(set(positive)) and len(empty)==len(set(empty))
        and not set(positive)&set(empty) and set(positive)|set(empty)==set(ids)
        and positive==[eid for eid in ids if eid in set(positive)] and empty==sorted(empty)
        and info['train_prefixes']==len(train) and info['train_users']==len(users)
        and info['informative_train_prefixes']==len(positive) and info['uninformative_train_prefixes']==len(empty)
        and info['users']==len({ex.user_id for ex in train if ex.example_id in set(positive)})
        and info['users_without_informative_prefix']==len(users)-info['users']
        and info['ordered_pairs']==len(pairs)>0 and len(pairs)%2==0 and set(pairs)==set(positive)
        and pairs[::2]==pairs[1::2],'own-parent training membership/order/counts differ from this fold')
    grouped=Counter(pairs)
    require(pairs==[eid for eid in positive for _ in range(grouped[eid])]
        and all(0<grouped[eid]<=len(banks[ex.bank_id].candidates)*(len(banks[ex.bank_id].candidates)-1)
                for ex in train for eid in (ex.example_id,) if eid in grouped)
        and 2*len(positive)<=info['stable_train_candidates']<=sum(len(banks[ex.bank_id].candidates)
                for ex in train if ex.example_id in set(positive)),
        'own-parent stable-pair/candidate accounting invalid')
    require(info['weight_normalization']=='fixed_reference_total_pair_weight'
        and _real(info['reference_pair_weight']) and info['reference_pair_weight']==1900.
        and _real(info['sample_weight_sum']) and math.isclose(info['sample_weight_sum'],1900.,rel_tol=1e-12)
        and _real(info['prior_mean_one_weight_sum'])
        and math.isclose(info['prior_mean_one_weight_sum'],len(pairs),rel_tol=1e-12),
        'unchanged own-parent mass1900 and original two normalizations required')


def _scores(value,ids,name):
    require(type(value) is dict and set(value)==set(ids) and all(_real(v) for v in value.values()),
        'exact finite '+name+' candidate score map required')


def validate_inputs(inputs):
    """Validate supplied own-fold projection; never authenticate files or fit."""
    _typed(inputs,FoldInputs,'own-fold capsule')
    require(type(inputs.fold) is int and inputs.fold in range(5) and type(inputs.synthetic) is bool,
        'strict own fold0..4 and synthetic flag required')
    require(all(_sha(getattr(inputs,k)) for k in ('parent_structure_model_sha256','fold_assignment_sha256','readiness_complete_sha256')),
        'exact external parent/fold/readiness SHA identities required')
    require(type(inputs.examples) is tuple and bool(inputs.examples),'nonempty immutable examples required')
    for ex in inputs.examples:
        _typed(ex,Example,'Example')
        require(all(_text(getattr(ex,k)) for k in ('example_id','user_id','bank_id')) and ex.split=='train',
            'strict original training example required')
        obs=ex.observation;_typed(obs,PilotObservation,'PilotObservation')
        require(_text(obs.problem_id) and type(obs.prior) is tuple and bool(obs.prior)
            and type(ex.donor_history) is tuple and len(ex.donor_history)==len(obs.prior),
            'complete nonempty authentic and matched donor histories required')
        for source in (*obs.prior,obs.current,*ex.donor_history):_source(source)
        obs.__post_init__();PilotObservation(obs.problem_id,obs.current,ex.donor_history)
        require(ex.example_id==obs.current.submission_id,'example must identify exact current source')
    for key in ('example_id','user_id','bank_id'):
        require(len({getattr(ex,key) for ex in inputs.examples})==len(inputs.examples),'unique original '+key+' required')
    require(type(inputs.assignment) is dict and _same(inputs.assignment,assign_folds(inputs.examples)),
        'exact frozen balanced problem-fold assignment required')
    require(set(inputs.assignment['example_fold'].values())==set(range(5)),'all five nonempty held folds required')
    ids={ex.bank_id for ex in inputs.examples}
    require(type(inputs.banks) is dict and set(inputs.banks)==ids and type(inputs.base_scores) is dict
        and set(inputs.base_scores)==ids and type(inputs.interactions) is dict and set(inputs.interactions)==set(ARMS),
        'all original banks/base maps and exactly six arms required')
    for arm in ARMS:
        require(type(inputs.interactions[arm]) is dict and set(inputs.interactions[arm])==ids,'complete arm bank scope required')
    candidate_count=0
    for ex in inputs.examples:
        bank=inputs.banks[ex.bank_id];_typed(bank,CandidateBank,'CandidateBank')
        require(type(bank.current_source) is bytes and type(bank.attempts) is tuple
            and bank.problem_id==ex.observation.problem_id and bank.current_source==ex.observation.current.source,
            'exact original observation-bank identity required')
        for attempt in bank.attempts:
            _typed(attempt,CandidateAttempt,'CandidateAttempt');attempt.__post_init__()
            require(attempt.source is None or type(attempt.source) is bytes,'exact attempt bytes required')
        bank.__post_init__();candidates=tuple(c.candidate_id for c in bank.candidates);candidate_count+=len(candidates)
        _scores(inputs.base_scores[ex.bank_id],candidates,'own-fold structural-C')
        shared=None;noop=candidates.index(source_hash(bank.current_source))
        for arm in ARMS:
            block=inputs.interactions[arm][ex.bank_id];_typed(block,newton.CandidateBlock,'CandidateBlock')
            x=block.matrix
            require(block.candidate_ids==candidates and type(x) is np.ndarray and x.dtype==np.dtype('float64')
                and x.shape==(len(candidates),32) and np.isfinite(x).all(),'exact ordered signed32 candidate matrix required')
            require(not np.any(x[noop]),'literal zero no-op32 required')
            require(all(math.sqrt(math.fsum(float(v*v) for v in row))<=2.**-.5+NORM_ALLOWANCE for row in x)
                and all(math.sqrt(math.fsum(float(v*v) for v in (x[a]-x[b])))<=1.+NORM_ALLOWANCE
                    for a,b in combinations(range(len(x)),2)),'fixed candidate/pair analytic norm bound required')
            if shared is None:shared=x[:,:16]
            require(np.array_equal(x[:,:16],shared),'authentic current block must be identical across all six arms')
            if arm=='CF':require(not np.any(x[:,16:]),'CF residual tail must be literal zero')
    if not inputs.synthetic:
        require(len(inputs.examples)==320 and len({ex.observation.problem_id for ex in inputs.examples})==23
            and candidate_count==2544,'full frozen320/23/2544 population required; no exclusion')
    train,held=scope(inputs);_training(inputs.parent_training,train,inputs.banks)
    require(type(inputs.parent_predictions) is tuple and len(inputs.parent_predictions)==len(held),
        'only complete own-held parent prediction tuple required')
    for ex,prediction in zip(held,inputs.parent_predictions,strict=True):
        _fields(prediction,PREDICTION_FIELDS,'own-held parent prediction')
        bank=inputs.banks[ex.bank_id];candidates=tuple(c.candidate_id for c in bank.candidates)
        expected=dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,
            problem_id=bank.problem_id,fold=inputs.fold,bank_seal_sha256=bank.seal_sha256)
        require(all(type(prediction[k]) is type(v) and prediction[k]==v for k,v in expected.items()),
            'own-held parent identities/order/seals required')
        require(type(prediction['choices']) is dict and set(prediction['choices'])==set(PARENT_METHODS)
            and all(type(v) is str and v in candidates for v in prediction['choices'].values())
            and type(prediction['candidate_scores']) is dict and set(prediction['candidate_scores'])==set(BASELINES),
            'only projected baseline choices and two score maps permitted')
        for name in BASELINES:
            scores=prediction['candidate_scores'][name];_scores(scores,candidates,name)
            require(prediction['choices'][name]==min(scores,key=lambda cid:(-scores[cid],cid)),
                'frozen baseline SHA tie-breaking differs')
        require(_same(prediction['candidate_scores']['structural_C'],inputs.base_scores[ex.bank_id]),
            'own-held base map differs from frozen structural-C projection')
        noop=source_hash(bank.current_source);attempt=bank.attempts[0]
        require(prediction['choices']['noop']==noop and prediction['choices']['first_attempt']==
            (source_hash(attempt.source) if attempt.status=='success' else noop),'deterministic baseline projection differs')
    return [dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,problem_id=ex.observation.problem_id,
        fold=inputs.assignment['example_fold'][ex.example_id],candidate_ids=[c.candidate_id for c in inputs.banks[ex.bank_id].candidates],
        noop_candidate_id=source_hash(inputs.banks[ex.bank_id].current_source)) for ex in inputs.examples]


def _source_json(source):
    return dict(submission_id=source.submission_id,timestamp=source.timestamp,source_hex=source.source.hex(),
        source_sha256=source.source_sha256,verdict=source.verdict)


def encode_inputs(inputs):
    """Detached JSON-safe exact schema; immutable source/matrix bytes as hex."""
    validate_inputs(inputs)
    examples=[];banks={};interactions={arm:{} for arm in ARMS}
    for ex in inputs.examples:
        examples.append(dict(example_id=ex.example_id,user_id=ex.user_id,split=ex.split,bank_id=ex.bank_id,
            observation=dict(problem_id=ex.observation.problem_id,current=_source_json(ex.observation.current),
                prior=[_source_json(s) for s in ex.observation.prior]),donor_history=[_source_json(s) for s in ex.donor_history]))
        bank=inputs.banks[ex.bank_id]
        banks[ex.bank_id]=dict(problem_id=bank.problem_id,current_source_hex=bank.current_source.hex(),
            generator_config_sha256=bank.generator_config_sha256,seeds=list(bank.seeds),
            attempts=[dict(index=a.index,seed=a.seed,status=a.status,source_hex=None if a.source is None else a.source.hex(),
                error=a.error) for a in bank.attempts],bank_seal_sha256=bank.seal_sha256,
            candidate_ids=[c.candidate_id for c in bank.candidates])
        for arm in ARMS:
            block=inputs.interactions[arm][ex.bank_id]
            interactions[arm][ex.bank_id]=dict(candidate_ids=list(block.candidate_ids),dtype='<f8',
                shape=list(block.matrix.shape),data_hex=block.matrix.astype('<f8',copy=False).tobytes(order='C').hex())
    return dict(kind=VERSION,spec=asdict(SPEC),arms=list(ARMS),fold=inputs.fold,examples=examples,banks=banks,
        assignment=_clone(inputs.assignment),interactions=interactions,base_scores=_clone(inputs.base_scores),
        parent_predictions=_clone(list(inputs.parent_predictions)),parent_training=_clone(inputs.parent_training),
        parent_structure_model_sha256=inputs.parent_structure_model_sha256,fold_assignment_sha256=inputs.fold_assignment_sha256,
        readiness_complete_sha256=inputs.readiness_complete_sha256,synthetic=inputs.synthetic)


def fingerprint(inputs):
    """Bind every permitted projected value; not an external authenticity seal."""
    return hashlib.sha256(_json(encode_inputs(inputs)).encode('ascii')).hexdigest()


def _hex(value):
    require(type(value) is str and len(value)%2==0 and re.fullmatch('[0-9a-f]*',value) is not None,
        'canonical lowercase exact byte hex required')
    return bytes.fromhex(value)


def _decode_source(value):
    _fields(value,('submission_id','timestamp','source_hex','source_sha256','verdict'),'serialized observed source')
    source=ObservationSource(value['submission_id'],value['timestamp'],_hex(value['source_hex']),value['source_sha256'],value['verdict'])
    _source(source);return source


def decode_inputs(value):
    """Strict supplied-JSON reconstruction. Caller checks raw external SHA."""
    _fields(value,{'kind','spec','arms',*FoldInputs.__dataclass_fields__},'serialized own-fold capsule')
    require(value['kind']==VERSION and _same(value['spec'],asdict(SPEC)) and _same(value['arms'],list(ARMS)),
        'fixed progress32 representation/model/arm identity required')
    require(type(value['examples']) is list and type(value['banks']) is dict
        and type(value['interactions']) is dict and set(value['interactions'])==set(ARMS)
        and type(value['parent_predictions']) is list,'exact serialized sequence/maps required')
    examples=[];banks={};interactions={a:{} for a in ARMS}
    for row in value['examples']:
        _fields(row,Example.__dataclass_fields__,'serialized Example')
        obs=row['observation'];_fields(obs,('problem_id','current','prior'),'serialized observation')
        require(type(obs['prior']) is list and type(row['donor_history']) is list,'full serialized history lists required')
        examples.append(Example(row['example_id'],row['user_id'],row['split'],row['bank_id'],
            PilotObservation(obs['problem_id'],_decode_source(obs['current']),tuple(_decode_source(s) for s in obs['prior'])),
            tuple(_decode_source(s) for s in row['donor_history'])))
    for bid,row in value['banks'].items():
        _fields(row,('problem_id','current_source_hex','generator_config_sha256','seeds','attempts','bank_seal_sha256','candidate_ids'),
            'serialized CandidateBank')
        require(type(row['seeds']) is list and type(row['attempts']) is list,'exact serialized bank ledger lists required')
        attempts=[]
        for a in row['attempts']:
            _fields(a,('index','seed','status','source_hex','error'),'serialized CandidateAttempt')
            attempts.append(CandidateAttempt(a['index'],a['seed'],a['status'],None if a['source_hex'] is None else _hex(a['source_hex']),a['error']))
        bank=CandidateBank(row['problem_id'],_hex(row['current_source_hex']),row['generator_config_sha256'],tuple(row['seeds']),tuple(attempts))
        require(row['bank_seal_sha256']==bank.seal_sha256 and _same(row['candidate_ids'],[c.candidate_id for c in bank.candidates]),
            'serialized exact bank seal/candidate order differs')
        banks[bid]=bank
    for arm in ARMS:
        require(type(value['interactions'][arm]) is dict,'serialized arm bank map required')
        for bid,row in value['interactions'][arm].items():
            _fields(row,('candidate_ids','dtype','shape','data_hex'),'serialized CandidateBlock')
            require(type(row['candidate_ids']) is list and type(row['shape']) is list and len(row['shape'])==2
                and all(type(v) is int and v>0 for v in row['shape']) and row['shape']==[len(row['candidate_ids']),32]
                and row['dtype']=='<f8','exact little-endian float64[n,32] block required')
            raw=_hex(row['data_hex']);require(len(raw)==row['shape'][0]*32*8,'exact matrix byte length required')
            matrix=np.frombuffer(raw,dtype='<f8').reshape(tuple(row['shape'])).astype(np.float64,copy=False)
            interactions[arm][bid]=newton.CandidateBlock(tuple(row['candidate_ids']),matrix)
    inputs=FoldInputs(value['fold'],tuple(examples),banks,_clone(value['assignment']),interactions,_clone(value['base_scores']),
        tuple(_clone(value['parent_predictions'])),_clone(value['parent_training']),value['parent_structure_model_sha256'],
        value['fold_assignment_sha256'],value['readiness_complete_sha256'],value['synthetic'])
    validate_inputs(inputs)
    return inputs
