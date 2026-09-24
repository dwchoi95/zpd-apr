"""Observed-only existing-bank feedback support. Never loads repair outcomes.

The CLI requires a clean snapshot. Pure joins/support helpers and a source-only
loader are exposed for synthetic testing. No fitting, generation or execution.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from importlib.metadata import version
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import re
import subprocess

import numpy as np

from scripts import zpd_history_action_encoder as semantic
from scripts import zpd_history_feedback_coupling as coupling
from scripts.zpd_history_predictor import lexical_tokens
from src.repair.pilot_contracts import (CandidateAttempt, CandidateBank,
    ObservationSource, PilotObservation, canonical_hash, source_hash)

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'outputs/zpd-repair-feedback-20260924'
PARENT = 'outputs/zpd-repair-structure-cv-20260923/run-v1'
PARENT_SHA = 'b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f'
OBSERVED = 'outputs/zpd-history-gate-20260915'
PREPARED_SHA = '4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d'
GROUPS = (('outputs/zpd-repair-development-20260918', 'prepared-v2', True),
          ('outputs/zpd-repair-risk-development-20260923', 'prepared-v1', False))
ARMS = ('H', 'Jm', 'HS', 'L', 'U')
EVENTS = semantic.EVENTS
TOLERANCE = 1e-12
FEATURE_FIELDS = {'example_id','user_id','problem_id','split','timestamp',
    'current_code_id','current_verdict','matching_current_verdict','history','donor_example_id'}
GENERATOR_SOURCES = {
    'scripts/generate_zpd_repair_banks.py': '3705c545e4c03aaabcfe9ee550df8068b58a7b63200b42c0e88a5e5726f4a691',
    'src/repair/prompts.py': '09d16af33a986f9314cb468754f67241b0d1e2e53ebe9b27bbfb33381bbebdea',
    'src/repair/inference.py': '6a7c6883dd590c5f739e7760ff2a097f07f8cce3e563712dae7518c4f9c03d4b'}
FROZEN_FEATURES = {
    'scripts/zpd_history_feedback_coupling.py': '83d8f512520254da9eec73b4e5210b57b037beed83b83bcb4ca40b383e7e32b3',
    'scripts/zpd_history_action_encoder.py': '14323b45cb9ddeec41c8ed237d244a0353f846c90afd58e4c7c4a7f96fc300bd',
    'scripts/zpd_history_action_blocked.py': '127250de384b26dc11dff3481444552777c9ee474c4b224a9b79f34e02af9c13'}
OBSERVATION_FIELDS = {'example_id','user_id','problem_id','bank_id','fold','current_code',
    'current_verdict','current_timestamp','current_source_sha256','history','donor_history',
    'donor_example_id','donor_user_id','observed_source_ids','donor_source_ids'}
SOURCE_FILES = (
    'scripts/audit_zpd_repair_feedback_support.py', 'scripts/zpd_history_feedback_coupling.py',
    'scripts/zpd_history_action_encoder.py', 'scripts/zpd_history_action_blocked.py',
    'scripts/run_zpd_history_action_cv.py', 'scripts/audit_zpd_history_support.py',
    'scripts/prepare_zpd_train_successors.py', 'scripts/build_zpd_original_prefixes.py',
    'scripts/zpd_history_predictor.py', 'src/repair/pilot_contracts.py',
    *GENERATOR_SOURCES, 'analysis_protocols/zpd-feedback-to-repair-design-20260924.md',
    'analysis_protocols/zpd-repair-feedback-support-preflight-20260924.md',
    'analysis_protocols/zpd-repair-feedback-prospective-contract-20260924.md')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _canonical(path):
    value = Path(path).absolute()
    if value.resolve() != value:
        raise ValueError('canonical nonsymlink path required')
    return value


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _exact_text(source):
    if type(source) is not bytes:
        raise ValueError('immutable exact source bytes required')
    text=source.decode('utf-8',errors='strict')
    if text.encode('utf-8')!=source:
        raise ValueError('source UTF-8 roundtrip changed bytes')
    return text


class ObservedReader:
    """Explicit fixed filename allowlist; never follow arbitrary manifest paths."""
    def __init__(self, project):
        self.project = _canonical(project)
        self.bindings = {}
        self.allowed = {PARENT+'/'+n for n in ('COMPLETE.json','manifest.json','folds.json')}
        self.allowed |= {OBSERVED+'/original-prefixes/manifest.json',
                         *[OBSERVED+'/prepared-inputs/'+n for n in ('manifest.json','features.jsonl','codes.jsonl')]}
        for family,prep,original in GROUPS:
            names = ['manifest.json','observations.jsonl','requests.jsonl','exclusions.jsonl']
            if not original:
                names += [f'requests-{i}.jsonl' for i in range(4)]
            self.allowed |= {family+'/'+prep+'/'+n for n in names}
            dirs = ['generation'] if original else [f'generation-{i}' for i in range(4)]
            self.allowed |= {family+'/run-v1/'+d+'/'+n for d in dirs for n in ('manifest.json','COMPLETE','banks.jsonl')}
            if not original:
                self.allowed |= {family+'/run-v1/'+n for n in ('banks.jsonl','BANKS_COMPLETE.json')}

    def bind(self, relative, expected=None):
        if relative not in self.allowed:
            raise ValueError('not an explicitly allowed observed artifact: '+str(relative))
        path = self.project/relative
        if path.resolve() != path or not path.is_file():
            raise ValueError('missing or noncanonical observed artifact: '+relative)
        digest = sha(path)
        if expected is not None and digest != expected:
            raise ValueError('observed artifact SHA mismatch: '+relative)
        if relative in self.bindings and self.bindings[relative] != digest:
            raise ValueError('observed input changed: '+relative)
        self.bindings[relative] = digest
        return path

    def json(self, relative, expected=None):
        return _read(self.bind(relative,expected))

    def rows(self, relative, expected=None):
        path = self.bind(relative,expected)
        with path.open(encoding='utf-8') as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def recheck(self):
        for name,digest in list(self.bindings.items()):
            self.bind(name,digest)


def parse_bank(row):
    """Source-only strict parser using bank contracts, not evaluator imports."""
    if type(row) is not dict or set(row) != {'bank_id','problem_id','current_source','generator_config_sha256','seeds','attempts'}:
        raise ValueError('strict source-only bank schema required')
    if type(row['current_source']) is not str or type(row['attempts']) is not list or type(row['seeds']) is not list:
        raise ValueError('bank source/ledger types invalid')
    pid = row['problem_id']
    if type(pid) is not str or re.fullmatch(r'p[0-9]+',pid) is None:
        raise ValueError('canonical problem ID required')
    code = row['current_source'].encode('utf-8')
    ident = hashlib.sha256((pid+'|'+source_hash(code)).encode()).hexdigest()
    if row['bank_id'] != ident:
        raise ValueError('bank ID does not bind problem/current source')
    attempts = []
    for item in row['attempts']:
        if type(item) is not dict or set(item) != {'index','seed','status','source','error'}:
            raise ValueError('strict terminal attempt schema required')
        if item['source'] is not None and type(item['source']) is not str:
            raise ValueError('candidate exact text required')
        attempts.append(CandidateAttempt(**dict(item,source=None if item['source'] is None else item['source'].encode('utf-8'))))
    return CandidateBank(pid,code,row['generator_config_sha256'],tuple(row['seeds']),tuple(attempts))


def generation_config(config):
    """The pinned generator requests Python; this is not language detection."""
    if (type(config) is not dict or config.get('prompt') != 'D current only; verdict Unknown'
            or config.get('seeds') != list(range(2027,2035))):
        raise ValueError('unrecognized declared-Python generation recipe')
    normalized = {}
    for name,digest in config.get('source_sha256',{}).items():
        key = 'scripts/generate_zpd_repair_banks.py' if Path(name).name == 'generate_zpd_repair_banks.py' else name
        if key in normalized:
            raise ValueError('duplicate normalized generator source')
        normalized[key] = digest
    if normalized != GENERATOR_SOURCES:
        raise ValueError('generator/default-language/extractor source provenance missing')
    return dict(config,source_sha256=normalized)


def verify_generation(reader, family, preparation, original, expected_inputs):
    def get(name, rows=False):
        if name not in expected_inputs:
            raise ValueError('generation input missing frozen parent binding')
        return (reader.rows if rows else reader.json)(name,expected_inputs[name])
    requests = get(preparation+'/requests.jsonl',True)
    chunks = [('generation', 'requests.jsonl')] if original else [(f'generation-{i}',f'requests-{i}.jsonl') for i in range(4)]
    generated=[]; request_sequence=[]; configs=[]
    for directory,request_name in chunks:
        base=family+'/run-v1/'+directory
        marker=get(base+'/COMPLETE'); manifest=get(base+'/manifest.json')
        raw=get(base+'/banks.jsonl',True); chunk=get(preparation+'/'+request_name,True)
        if (marker.get('banks_sha256') != reader.bindings[base+'/banks.jsonl']
                or marker.get('manifest_sha256') != reader.bindings[base+'/manifest.json']
                or manifest.get('requests_sha256') != reader.bindings[preparation+'/'+request_name]):
            raise ValueError('generation seal/request mismatch')
        config=manifest['config']; config_hash=canonical_hash(config)
        if config_hash != manifest.get('generator_config_sha256') or marker.get('attempts') != 8*len(chunk):
            raise ValueError('generator configuration/attempt count mismatch')
        configs.append(generation_config(config))
        req={r['bank_id']:r for r in chunk}
        if len(req)!=len(chunk) or len(raw)!=len(chunk) or {r['bank_id'] for r in raw}!=set(req):
            raise ValueError('exact generated/request bank coverage required')
        for row in raw:
            bank=parse_bank(row); request=req[row['bank_id']]
            if set(request)!={'bank_id','problem_id','current_source','problem_description','time_limit','memory_limit'}:
                raise ValueError('strict outcome-free request schema required')
            seeds=tuple(int(hashlib.sha256(f'{s}|{row["bank_id"]}'.encode()).hexdigest()[:8],16) for s in config['seeds'])
            if (bank.problem_id!=request['problem_id'] or bank.current_source.decode('utf-8')!=request['current_source']
                    or bank.generator_config_sha256!=config_hash or bank.seeds!=seeds):
                raise ValueError('bank/current/config/seed mismatch')
        generated.extend(raw);request_sequence.extend(chunk)
    if request_sequence != requests or any(c!=configs[0] for c in configs):
        raise ValueError('generation chunk recipe/request order mismatch')
    if not original:
        merged=get(family+'/run-v1/banks.jsonl',True)
        marker=get(family+'/run-v1/BANKS_COMPLETE.json')
        if merged!=generated or marker.get('banks_sha256')!=reader.bindings[family+'/run-v1/banks.jsonl']:
            raise ValueError('merged generation bank seal mismatch')
    return generated,configs[0]


def original_languages(original, needed):
    """Exact identity+SHA join; never parse or guess a source language."""
    joined={}
    for raw_path,digest in original['source_sha256'].items():
        p=Path(raw_path)
        if not p.is_absolute() or '..' in p.parts or len(p.parts)<4:
            raise ValueError('invalid original source path')
        pid,language,filename=p.parts[-3:]
        ident=pid+':'+filename.rsplit('.',1)[0]
        if ident not in needed:
            continue
        if ident in joined or not language or digest != needed[ident]:
            raise ValueError('ambiguous or mismatched original source-language join')
        joined[ident]=language
    if set(joined)!=set(needed):
        raise ValueError('missing original source-language provenance')
    return joined


def _source(raw, problem):
    if type(raw) is not dict or set(raw)!=set(ObservationSource.__dataclass_fields__) or type(raw['source']) is not str:
        raise ValueError('strict observed source allowlist required')
    value=ObservationSource.from_mapping(dict(raw,source=raw['source'].encode('utf-8')))
    if not value.submission_id.startswith(problem+':') or value.submission_id.count(':')!=1:
        raise ValueError('source/problem identity mismatch')
    return value


def join_observations(selected, feature_rows, original, bank_rows, assignment):
    """Pure exact selected rows, original donors, original languages and banks."""
    ids=[r['example_id'] for r in selected]
    if not selected or len(set(ids))!=len(ids) or len({r['user_id'] for r in selected})!=len(ids):
        raise ValueError('unique selected train users/examples required')
    needed_features=set(ids)|{r['donor_example_id'] for r in selected}
    features={}
    for f in feature_rows:
        if f.get('example_id') not in needed_features:
            continue
        if set(f)!=FEATURE_FIELDS or f['split']!='train' or f['example_id'] in features:
            raise ValueError('strict unique train observed feature join required')
        nominal={'Accepted':'AC','Wrong Answer':'WA','Compile Error':'CE','Compilation Error':'CE',
                 'Runtime Error':'RE','Time Limit Exceeded':'RESOURCE','Memory Limit Exceeded':'RESOURCE'}
        if (type(f['timestamp']) not in (int,float) or not math.isfinite(f['timestamp'])
                or type(f['matching_current_verdict']) is not str or not f['matching_current_verdict']
                or f['current_verdict']!=nominal.get(f['matching_current_verdict'],'OTHER')
                or f['current_code_id']!=f['example_id'] or not f['example_id'].startswith(f['problem_id']+':')
                or type(f['user_id']) is not str or not f['user_id']):
            raise ValueError('invalid original observed current metadata')
        features[f['example_id']]=f
    if set(features)!=needed_features:
        raise ValueError('missing recipient/donor observed metadata')
    banks={row['bank_id']:parse_bank(row) for row in bank_rows}
    if len(banks)!=len(bank_rows) or set(banks)!={r['bank_id'] for r in selected}:
        raise ValueError('exact unique selected bank coverage required')
    staged=[];source_shas={}
    for row in selected:
        if set(row)!={'example_id','user_id','split','bank_id','observation','donor_history','donor_user_id','donor_example_id'} or row['split']!='train':
            raise ValueError('strict source-only train repair row required')
        raw=row['observation']
        if set(raw)!={'problem_id','current','prior'}:
            raise ValueError('observation fields differ')
        pid=raw['problem_id']; current=_source(raw['current'],pid)
        prior=tuple(_source(h,pid) for h in raw['prior'])
        donor=tuple(_source(h,pid) for h in row['donor_history'])
        observation=PilotObservation(pid,current,prior)
        PilotObservation(pid,current,donor)  # validates strict past identities/time
        if not prior or len(prior)!=len(donor):
            raise ValueError('nonempty equal donor/prior length required')
        f=features[row['example_id']];d=features[row['donor_example_id']]
        def meta(history):return [dict(code_id=s.submission_id,timestamp=s.timestamp,verdict=s.verdict) for s in history]
        if (f['current_code_id']!=current.submission_id or f['example_id']!=current.submission_id
                or f['user_id']!=row['user_id'] or f['timestamp']!=current.timestamp
                or f['current_verdict']!=current.verdict or f['history']!=meta(prior)
                or f['donor_example_id']!=row['donor_example_id'] or f['problem_id']!=pid
                or d['problem_id']!=pid or d['user_id']!=row['donor_user_id']
                or d['user_id']==row['user_id'] or d['timestamp']>=current.timestamp
                or d['history']!=meta(donor) or d['matching_current_verdict']!=f['matching_current_verdict']):
            raise ValueError('original recipient/donor provenance or matching mismatch')
        if any(s.timestamp>=d['timestamp'] for s in donor):
            raise ValueError('donor prior is not strictly before donor current')
        counts=[sum(len(lexical_tokens(_exact_text(s.source))[0]) for s in chain) for chain in (prior,donor)]
        if counts[0]!=counts[1]:
            raise ValueError('frozen exact donor prior-token match differs')
        bank=banks[row['bank_id']]
        if bank.problem_id!=pid or bank.current_source!=current.source:
            raise ValueError('observation/bank source mismatch')
        for s in (current,*prior,*donor):
            if s.submission_id in source_shas and source_shas[s.submission_id]!=s.source_sha256:
                raise ValueError('source identity has conflicting exact bytes')
            source_shas[s.submission_id]=s.source_sha256
        staged.append((row,observation,donor))
    languages=original_languages(original,source_shas)
    required={'example_fold','fold_sizes','folds','problem_counts','problem_fold','salt'}
    if set(assignment)!=required or assignment['folds']!=5 or set(assignment['example_fold'])!=set(ids):
        raise ValueError('exact original five problem folds required')
    pc=Counter(o.problem_id for _,o,_ in staged)
    if assignment['problem_counts']!=dict(pc) or set(assignment['problem_fold'])!=set(pc):
        raise ValueError('problem fold coverage differs')
    if any(type(v)is not int or v not in range(5) for v in assignment['problem_fold'].values()):
        raise ValueError('integer problem folds required')
    output=[];foldcounts=Counter()
    for row,o,donor in staged:
        fold=assignment['example_fold'][row['example_id']]
        if type(fold)is not int or fold!=assignment['problem_fold'][o.problem_id]:
            raise ValueError('recipient problem-fold membership differs')
        if languages[o.current.submission_id]!='Python':
            raise ValueError('current source is not certified Python')
        foldcounts[fold]+=1
        def h(chain):return [dict(code=_exact_text(s.source),verdict=s.verdict,timestamp=s.timestamp,
                                 language=languages[s.submission_id]) for s in chain]
        output.append(dict(example_id=row['example_id'],user_id=row['user_id'],problem_id=o.problem_id,
            bank_id=row['bank_id'],fold=fold,current_code=_exact_text(o.current.source),
            current_verdict=o.current.verdict,current_timestamp=o.current.timestamp,
            current_source_sha256=o.current.source_sha256,history=h(o.prior),donor_history=h(donor),
            donor_example_id=row['donor_example_id'],donor_user_id=row['donor_user_id'],
            observed_source_ids=[s.submission_id for s in (o.current,*o.prior)],
            donor_source_ids=[s.submission_id for s in donor]))
    if [foldcounts[i] for i in range(5)]!=assignment['fold_sizes'] or not all(foldcounts[i] for i in range(5)):
        raise ValueError('frozen nonempty fold sizes differ')
    return output,banks,dict(source_ids=len(source_shas),languages=dict(Counter(languages.values())))


def load_inputs(project, *, production=True):
    """No label/evaluation/model loader import, call or pathname is used."""
    reader=ObservedReader(project)
    seal=reader.json(PARENT+'/COMPLETE.json',PARENT_SHA if production else None)
    if seal.get('status')!='complete':raise ValueError('complete frozen structure parent required')
    manifest=reader.json(PARENT+'/manifest.json',seal['files_sha256']['manifest.json'])
    assignment=reader.json(PARENT+'/folds.json',seal['files_sha256']['folds.json'])
    parent_inputs={}
    for name,digest in manifest['provenance']['input_sha256'].items():
        # Inspect hash metadata only. Never open the parent's outcome files.
        prefix='/home/cdw/VSCode/zpd-apr/'
        if not name.startswith(prefix):raise ValueError('unrecognized parent input root')
        relative=name[len(prefix):]
        if relative in parent_inputs:raise ValueError('duplicate normalized parent input')
        parent_inputs[relative]=digest
    prep=reader.json(OBSERVED+'/prepared-inputs/manifest.json',PREPARED_SHA if production else None)
    original=reader.json(OBSERVED+'/original-prefixes/manifest.json',prep['source_manifest_sha256'])
    for name in ('features.jsonl','codes.jsonl'):
        reader.bind(OBSERVED+'/prepared-inputs/'+name,prep['file_sha256'][name])
    feature_rows=reader.rows(OBSERVED+'/prepared-inputs/features.jsonl')
    selected=[];selected_banks=[];configs=[]
    for family,directory,is_original in GROUPS:
        base=family+'/'+directory
        p=reader.json(base+'/manifest.json',parent_inputs[base+'/manifest.json'])
        if p['input_sha256']!={n:prep['file_sha256'][n] for n in ('features.jsonl','codes.jsonl')}:
            raise ValueError('repair preparation uses different observed corpus')
        required={'observations.jsonl','requests.jsonl','exclusions.jsonl'}|({f'requests-{i}.jsonl' for i in range(4)} if not is_original else set())
        if set(p['output_sha256'])!=required:raise ValueError('unexpected preparation file set')
        for name,digest in p['output_sha256'].items():
            if parent_inputs.get(base+'/'+name)!=digest:raise ValueError('preparation differs from frozen parent')
            reader.bind(base+'/'+name,digest)
        observed=reader.rows(base+'/observations.jsonl')
        if any(r['split'] not in ('train','valid') for r in observed):raise ValueError('unexpected repair split')
        if production and Counter(r['split'] for r in observed)!=(Counter(train=64,valid=32) if is_original else Counter(train=256)):
            raise ValueError('frozen64/32/256 preparation required')
        if p['selected_order']!=[r['example_id'] for r in observed]:raise ValueError('selected order drift')
        bank_rows,config=verify_generation(reader,family,base,is_original,parent_inputs)
        train=[r for r in observed if r['split']=='train'];wanted={r['bank_id'] for r in train}
        selected.extend(train);selected_banks.extend(r for r in bank_rows if r['bank_id'] in wanted);configs.append(config)
    if configs[0]!=configs[1]:raise ValueError('generation recipe differs across train cohorts')
    if production and len(selected)!=320:raise ValueError('frozen320 recipients required')
    observations,banks,coverage=join_observations(selected,feature_rows,original,selected_banks,assignment)
    reader.recheck()
    return observations,banks,assignment,coverage,reader


def _history_diagnostics(observation, arm, supplied, moments):
    """Observed mask-conditional strata, not future labels or feature changes."""
    o=observation
    prior=[supplied[i] for i in semantic.permutation_indices(len(supplied),o['example_id'])] if arm=='HS' else supplied
    sequence=[*prior,dict(code=o['current_code'],verdict=o['current_verdict'],timestamp=o['current_timestamp'],language='Python')]
    counts=np.zeros(18,dtype=int);positives=np.zeros(18,dtype=int);pairs=[set() for _ in EVENTS]
    for before,after in zip(sequence,sequence[1:]):
        _,values,masks=semantic._transition(before['code'],after['code'],before['language'],after['language'])
        pair=(semantic._verdict(before['verdict']),semantic._verdict(after['verdict']))
        for j,available in enumerate(masks):
            if available:
                counts[j]+=1;positives[j]+=int(values[j]);pairs[j].add(pair)
    if moments.transition_count!=len(supplied) or not np.array_equal(counts,moments.applicable_counts):
        raise ValueError('historical diagnostic mask differs from coupling mask')
    distinct=[len(v) for v in pairs]
    return dict(transition_count=moments.transition_count,applicable_counts=counts.tolist(),
        applicable_positive_counts=positives.tolist(),applicable_verdict_pair_counts=distinct,
        uniform_opportunity=moments.opportunity[0].tolist(),recency_opportunity=moments.opportunity[1].tolist(),
        zero_opportunity=(counts==0).tolist(),one_applicable=(counts==1).tolist(),
        observed_event_zero=((counts>0)&(positives==0)).tolist(),
        constant_event=((counts>0)&((positives==0)|(positives==counts))).tolist(),
        constant_feedback=[bool(n>0 and kinds==1) for n,kinds in zip(counts,distinct)])


def interaction_matrices(observation, bank, *, with_history_support=False):
    """All candidates × fixed 1296 coordinates for each pure observed arm."""
    o=observation
    if type(o) is not dict or set(o)!=OBSERVATION_FIELDS or type(bank) is not CandidateBank:
        raise ValueError('strict joined observed-only interaction schema required')
    if _exact_text(bank.current_source)!=o['current_code'] or bank.problem_id!=o['problem_id']:
        raise ValueError('interaction bank/observation mismatch')
    values=[];masks=[]
    for candidate in bank.candidates:
        y,m=semantic.encode_edit(o['current_code'],_exact_text(candidate.source),'Python','Python')
        values.append(y);masks.append(m)
    values=np.asarray(values);masks=np.asarray(masks)
    if type(with_history_support) is not bool:
        raise ValueError('explicit history diagnostic flag required')
    result={};historical={}
    for arm in ARMS:
        supplied=o['donor_history'] if arm=='U' else o['history'][-1:] if arm=='L' else o['history']
        c=coupling.coupling_features(o['current_code'],o['current_verdict'],supplied,o['current_timestamp'],
                                     shuffled=arm=='HS',shuffle_key=o['example_id'])
        moments=c.marginal if arm=='Jm' else c.joint
        result[arm]=(moments[None,:,:,:]*(values*masks)[:,None,:,None]/6.).reshape(len(values),1296)
        if with_history_support:historical[arm]=_history_diagnostics(o,arm,supplied,c)
    return (values,masks,result,historical) if with_history_support else (values,masks,result)


def pairwise_geometry(matrices, noop):
    """True all-pair maxima/counts; valid even beyond binary-gated features."""
    if set(matrices)!=set(ARMS):raise ValueError('all fixed interaction arms required')
    count=len(matrices['H'])
    if type(noop) is not int or not 0<=noop<count:
        raise ValueError('valid exact no-op index required')
    if any(x.shape!=(count,1296) or not np.isfinite(x).all() for x in matrices.values()):
        raise ValueError('finite common interaction dimensions required')
    pairs=list(combinations(range(count),2));edited=[p for p in pairs if noop not in p]
    byarm={arm:[float(np.max(np.abs(x[a]-x[b]))) for a,b in pairs] for arm,x in matrices.items()}
    contrast={arm:[float(np.max(np.abs((matrices['H'][a]-matrices['H'][b])-(matrices[arm][a]-matrices[arm][b]))))
              for a,b in pairs] for arm in ARMS if arm!='H'}
    edited_indices=[i for i,p in enumerate(pairs) if noop not in p]
    anchor={arm:x-x[noop] for arm,x in matrices.items()}
    covariance=np.zeros(18)
    for a,b in pairs:
        d=(matrices['H'][a]-matrices['H'][b])-(matrices['Jm'][a]-matrices['Jm'][b])
        covariance=np.maximum(covariance,np.max(np.abs(d.reshape(2,18,36)),axis=(0,2)))
    return dict(unordered_candidate_pairs=len(pairs),unordered_edited_candidate_pairs=len(edited),
        within_bank_max_abs={arm:max(v,default=0.) for arm,v in byarm.items()},
        pairwise_contrast_max_abs={arm:max(v,default=0.) for arm,v in contrast.items()},
        noop_anchor_max_abs={arm:float(np.max(np.abs(d))) for arm,d in anchor.items()},
        noop_anchor_contrast_max_abs={arm:float(np.max(np.abs(anchor['H']-anchor[arm]))) for arm in ARMS if arm!='H'},
        geometrically_varying_pair_counts={arm:sum(v>TOLERANCE for v in values) for arm,values in byarm.items()},
        pairwise_contrast_pair_counts={arm:sum(v>TOLERANCE for v in values) for arm,values in contrast.items()},
        edited_geometrically_varying_pair_counts={arm:sum(values[i]>TOLERANCE for i in edited_indices) for arm,values in byarm.items()},
        edited_pairwise_contrast_pair_counts={arm:sum(values[i]>TOLERANCE for i in edited_indices) for arm,values in contrast.items()},
        joint_covariance_with_candidate_variation_by_event=(covariance>TOLERANCE).tolist())


def support_summary(observations,banks,assignment, *, callback=None):
    if not observations or any(type(o) is not dict or set(o)!=OBSERVATION_FIELDS for o in observations):
        raise ValueError('nonempty strict joined observed-only support rows required')
    if len({o['example_id'] for o in observations})!=len(observations) or set(banks)!={o['bank_id'] for o in observations}:
        raise ValueError('exact unique support coverage required')
    if set(assignment['example_fold'])!={o['example_id'] for o in observations}:
        raise ValueError('support fold identity coverage differs')
    if any(type(o['fold']) is not int or o['fold'] not in range(5) or
           o['fold']!=assignment['example_fold'][o['example_id']] for o in observations):
        raise ValueError('support fold membership differs')
    records=[]
    for i,o in enumerate(observations,1):
        bank=banks[o['bank_id']];values,masks,x,historical=interaction_matrices(o,bank,with_history_support=True)
        ids=[c.candidate_id for c in bank.candidates];noop=ids.index(source_hash(bank.current_source))
        geometry=pairwise_geometry(x,noop)
        groups={};effective_groups={}
        for j,cid in enumerate(ids):
            groups.setdefault((tuple(values[j]),tuple(masks[j])),[]).append(cid)
            effective_groups.setdefault(tuple(values[j]*masks[j]),[]).append(cid)
        edited_interaction_groups={}
        for arm,matrix in x.items():
            classes={}
            for j,cid in enumerate(ids):
                if j!=noop:classes.setdefault(tuple(matrix[j]),[]).append(cid)
            edited_interaction_groups[arm]=list(classes.values())
        candidates=[]
        for j,c in enumerate(bank.candidates):
            candidates.append(dict(candidate_id=c.candidate_id,is_noop=c.is_noop,values=values[j].tolist(),masks=masks[j].tolist(),
                interaction_sha256={arm:hashlib.sha256(np.asarray(matrix[j],dtype='<f8').tobytes()).hexdigest() for arm,matrix in x.items()}))
        records.append(dict(example_id=o['example_id'],user_id=o['user_id'],problem_id=o['problem_id'],bank_id=o['bank_id'],fold=o['fold'],
            bank_seal_sha256=bank.seal_sha256,prior_count=len(o['history']),candidate_count=len(ids),
            donor_example_id=o['donor_example_id'],donor_user_id=o['donor_user_id'],
            prior_languages=dict(Counter(h['language'] for h in o['history'])),
            candidate_signature_count=len(groups),candidate_signature_groups=list(groups.values()),
            effective_event_signature_groups=list(effective_groups.values()),historical_support=historical,
            edited_candidate_signature_groups=[[cid for cid in group if cid!=ids[noop]] for group in groups.values()
                                               if any(cid!=ids[noop] for cid in group)],
            edited_interaction_groups=edited_interaction_groups,candidates=candidates,**geometry))
        if callback and (i%25==0 or i==len(observations)):callback(dict(completed_examples=i,total_examples=len(observations)))
    def aggregate(group):
        return dict(prefixes=len(group),users=len({r['user_id'] for r in group}),problems=len({r['problem_id'] for r in group}),
            candidates=sum(r['candidate_count'] for r in group),prior_one=sum(r['prior_count']==1 for r in group),
            single_candidate_banks=sum(r['candidate_count']==1 for r in group),
            unordered_candidate_pairs=sum(r['unordered_candidate_pairs'] for r in group),
            unordered_edited_candidate_pairs=sum(r['unordered_edited_candidate_pairs'] for r in group),
            edited_geometrically_varying_pairs={arm:sum(r['edited_geometrically_varying_pair_counts'][arm] for r in group) for arm in ARMS},
            edited_pairwise_contrast_pairs={arm:sum(r['edited_pairwise_contrast_pair_counts'][arm] for r in group) for arm in ARMS if arm!='H'},
            banks_with_multiple_edited_interaction_classes={arm:sum(len(r['edited_interaction_groups'][arm])>1 for r in group) for arm in ARMS},
            same_signature_pairs=sum(len(g)*(len(g)-1)//2 for r in group for g in r['candidate_signature_groups']),
            same_effective_event_signature_pairs=sum(len(g)*(len(g)-1)//2 for r in group for g in r['effective_event_signature_groups']),
            geometrically_varying_pairs={arm:sum(r['geometrically_varying_pair_counts'][arm] for r in group) for arm in ARMS},
            pairwise_contrast_pairs={arm:sum(r['pairwise_contrast_pair_counts'][arm] for r in group) for arm in ARMS if arm!='H'},
            varying_banks={arm:sum(r['within_bank_max_abs'][arm]>TOLERANCE for r in group) for arm in ARMS},
            distinct_pairwise_contrasts={arm:sum(r['pairwise_contrast_max_abs'][arm]>TOLERANCE for r in group) for arm in ARMS if arm!='H'},
            historical_support={arm:dict(transition_count=sum(r['historical_support'][arm]['transition_count'] for r in group),
                events={event:dict(
                    applicable_transitions=sum(r['historical_support'][arm]['applicable_counts'][j] for r in group),
                    positive_transitions=sum(r['historical_support'][arm]['applicable_positive_counts'][j] for r in group),
                    uniform_opportunity_sum=sum(r['historical_support'][arm]['uniform_opportunity'][j] for r in group),
                    recency_opportunity_sum=sum(r['historical_support'][arm]['recency_opportunity'][j] for r in group),
                    **{flag+'_banks':sum(r['historical_support'][arm][flag][j] for r in group)
                       for flag in ('zero_opportunity','one_applicable','observed_event_zero','constant_event','constant_feedback')})
                    for j,event in enumerate(EVENTS)}) for arm in ARMS},
            events={event:dict(available_candidates=sum(c['masks'][j] for r in group for c in r['candidates']),
                positive_candidates=sum(c['masks'][j] and c['values'][j]==1 for r in group for c in r['candidates']),
                joint_covariance_with_candidate_variation_banks=sum(r['joint_covariance_with_candidate_variation_by_event'][j] for r in group)) for j,event in enumerate(EVENTS)})
    folds={str(f):dict(train=aggregate([r for r in records if r['fold']!=f]),held=aggregate([r for r in records if r['fold']==f])) for f in range(5)}
    total=aggregate(records)
    return dict(kind='observed_only_repair_feedback_support_v1',events=list(EVENTS),arms=list(ARMS),rows=records,totals=total,folds=folds,
        excluded_prefixes=0,tolerance=TOLERANCE,tolerance_units='scaled candidate interaction coordinate; descriptive only',
        feature_dimension=1296,scale_divisor=6.,fitting_performed=False,
        outcomes_opened=False,successors_opened=False,models_opened=False,predictions_opened=False,fit_release_authorized=False,
        variation_prerequisite=bool(total['distinct_pairwise_contrasts']['Jm'] and all(folds[str(f)]['train']['varying_banks']['H'] for f in range(5))),
        donor_boundary='frozen external same-problem observed donor, not problem-fold-training-only',
        note='Source-only feasibility; no correctness or learning-effectiveness result.')


def _write(path,value):
    temporary=path.with_name(path.name+'.partial')
    temporary.write_text(json.dumps(value,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def _source_state():
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean committed source snapshot required; no dirty-checkout audit')
    return dict(revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                tree=subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip())


def audit(project,output):
    project=_canonical(project);output=_canonical(output)
    if output.parent!=project/FAMILY or output.exists():raise ValueError('new direct repair-feedback family child required')
    state=_source_state()
    sources={name:sha(ROOT/name) for name in SOURCE_FILES}
    if any(sources[name]!=digest for name,digest in {**GENERATOR_SOURCES,**FROZEN_FEATURES}.items()):
        raise ValueError('pinned generation/feature source drift')
    output.mkdir(parents=True)
    try:
        observations,banks,assignment,coverage,reader=load_inputs(project)
        _write(output/'manifest.json',dict(source=state,source_root=str(ROOT),source_sha256=sources,input_sha256=reader.bindings,
            runtime=dict(python=platform.python_version(),**{n:version(n) for n in ('numpy','scipy','scikit-learn')}),
            parent_complete_sha256=PARENT_SHA,source_coverage=coverage,fitting_performed=False))
        _write(output/'folds.json',assignment)
        result=support_summary(observations,banks,assignment,callback=lambda value:_write(output/'STATUS.json',dict(phase='observed_support',**value)))
        _write(output/'report.json',result)
        _write(output/'STATUS.json',dict(phase='complete',completed_examples=len(observations),total_examples=len(observations)))
        # Completion-state writes precede the final provenance barrier.
        reader.recheck()
        if _source_state()!=state or any(sha(ROOT/name)!=digest for name,digest in sources.items()):
            raise ValueError('support source changed before completion')
        _write(output/'COMPLETE.json',dict(status='complete',fitting_performed=False,
            files_sha256={n:sha(output/n) for n in ('manifest.json','folds.json','report.json','STATUS.json')}))
        return result
    except BaseException as exc:
        _write(output/'FAILED.json',dict(error_type=type(exc).__name__,error=str(exc)))
        raise


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();audit(args.project,args.output)


if __name__=='__main__':
    main()
