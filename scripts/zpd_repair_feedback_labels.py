"""Bounded label preparation and fold-local worker access; no production CLI.

A separately released preparer supplies the exact allowlisted source bytes to
the public materializer, which verifies their frozen ancestry before any write.
This module does not fetch those source files itself. Worker
loading opens exactly one externally hash-pinned fold-training label file.
These are auditable I/O/schema boundaries, not an operating-system sandbox.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from scripts.audit_zpd_repair_feedback_support import PARENT, PARENT_SHA, parse_bank
from src.repair.pilot_contracts import CandidateBank, canonical_hash

PARENT_COMPLETE_SHA256 = PARENT_SHA
ORIGINAL = 'outputs/zpd-repair-development-20260918'
EXPANSION = 'outputs/zpd-repair-risk-development-20260923'
EVALUATION_NAMES = ('COMPLETE.json','manifest.json','completions.jsonl','labels.jsonl')
SOURCE_PATHS = frozenset({PARENT+'/'+name for name in ('COMPLETE.json','manifest.json','folds.json')} |
    {family+'/'+prep+'/'+name for family,prep in ((ORIGINAL,'prepared-v2'),(EXPANSION,'prepared-v1'))
        for name in ('manifest.json','observations.jsonl')} |
    {ORIGINAL+'/run-v1/generation/banks.jsonl',EXPANSION+'/run-v1/banks.jsonl'} |
    {family+'/run-v1/evaluation/'+name for family in (ORIGINAL,EXPANSION) for name in EVALUATION_NAMES})
CORE = frozenset({'bank_id','candidate_id','status','gain','loss','all_ac'})
FULL = CORE | {'problem_id','is_noop','n_cases','evidence','bank_seal_sha256'}
EVIDENCE = {'status','gained_testcases','lost_testcases','candidate_all_ac','current_vector_sha256','candidate_vector_sha256'}
FOLD_KIND = 'repair_feedback_fold_training_labels_v1'
ASSESSMENT_KIND = 'repair_feedback_separate_train320_assessment_v1'


def digest(data):
    if type(data) is not bytes:raise ValueError('immutable exact artifact bytes required')
    return hashlib.sha256(data).hexdigest()


def _sha(value):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}',value) is None:
        raise ValueError('lowercase SHA256 required')
    return value


def _json(data):
    return json.loads(data.decode('utf-8',errors='strict'))


def _rows(data):
    return [json.loads(line) for line in data.decode('utf-8',errors='strict').splitlines() if line.strip()]


def _bank_map(rows):
    result={}
    for row in rows:
        bank=parse_bank(row)
        if row['bank_id'] in result:raise ValueError('duplicate source bank')
        result[row['bank_id']]=bank
    return result


def _keys(banks):
    if type(banks) is not dict or not banks or any(type(k) is not str or type(b) is not CandidateBank for k,b in banks.items()):
        raise ValueError('explicit nonempty typed bank dictionary required')
    return {(bid,c.candidate_id) for bid,b in banks.items() for c in b.candidates}


def validate_core_labels(rows,banks):
    """Exact dictionary scope; unknowns remain null and no-op is not certified."""
    required=_keys(banks);result={}
    for row in rows:
        if type(row) is not dict or set(row)!=CORE:raise ValueError('strict core-label fields required')
        key=row['bank_id'],row['candidate_id']
        if key not in required or key in result:raise ValueError('extra, duplicate or foreign candidate label')
        if row['status']=='unknown':
            if any(row[name] is not None for name in ('gain','loss','all_ac')):
                raise ValueError('unknown candidate evidence must remain null')
        elif row['status']=='stable':
            if (type(row['all_ac']) is not bool or any(type(row[name]) not in (int,float) or
                not math.isfinite(row[name]) or not 0<=row[name]<=1 for name in ('gain','loss'))
                    or row['gain']+row['loss']>1+1e-12 or row['all_ac'] and row['loss']!=0):
                raise ValueError('invalid stable candidate evidence')
            candidate=next(c for c in banks[key[0]].candidates if c.candidate_id==key[1])
            if candidate.is_noop and (row['gain']!=0 or row['loss']!=0):
                raise ValueError('stable no-op cannot gain/lose testcases')
        else:raise ValueError('unrecognized candidate evidence status')
        result[key]={name:row[name] for name in CORE}
    if set(result)!=required:raise ValueError('missing candidate labels in exact dictionary scope')
    return result


def validate_full_labels(rows,banks):
    """Validate the complete physical cache before dropping original valid32."""
    reduced=[];case_counts={}
    for row in rows:
        if type(row) is not dict or set(row)!=FULL:raise ValueError('strict evaluator-label fields required')
        bid=row['bank_id']
        if bid not in banks:raise ValueError('evaluator label outside physical source banks')
        bank=banks[bid];candidate=next((c for c in bank.candidates if c.candidate_id==row['candidate_id']),None)
        if (candidate is None or row['problem_id']!=bank.problem_id or row['is_noop'] is not candidate.is_noop
                or row['bank_seal_sha256']!=bank.seal_sha256):raise ValueError('evaluator label bank provenance mismatch')
        n=row['n_cases']
        if type(n) is not int or n<=0:raise ValueError('positive testcase count required')
        if case_counts.setdefault(bank.problem_id,n)!=n:raise ValueError('inconsistent testcase counts for problem')
        ev=row['evidence']
        if (type(ev) is not dict or set(ev)!=EVIDENCE or ev['status']!=row['status']
                or ev['candidate_all_ac'] is not row['all_ac']):raise ValueError('evaluator evidence mismatch')
        _sha(ev['current_vector_sha256']);_sha(ev['candidate_vector_sha256'])
        if row['status']=='unknown':
            if ev['gained_testcases'] is not None or ev['lost_testcases'] is not None:
                raise ValueError('unknown testcase evidence must remain null')
        elif row['status']=='stable':
            for name,field in (('gained_testcases','gain'),('lost_testcases','loss')):
                value=ev[name]
                if (type(value) is not list or any(type(v) is not str or not v for v in value)
                        or len(set(value))!=len(value) or type(row[field]) not in (int,float)
                        or not math.isclose(len(value)/n,row[field],rel_tol=0.,abs_tol=1e-12)):
                    raise ValueError('testcase fraction evidence mismatch')
            if set(ev['gained_testcases'])&set(ev['lost_testcases']):raise ValueError('overlapping gained/lost cases')
        reduced.append({name:row[name] for name in CORE})
    return validate_core_labels(reduced,banks)


def verify_evaluation_metadata(marker,manifest,banks,bank_file_sha,prepared,blob_hashes):
    """Existing frozen runtime/universe/bank contract; never opens testcases."""
    if (marker.get('status')!='fully_executed' or marker.get('development_only') is not True
            or set(marker.get('files_sha256',{}))!={'manifest.json','completions.jsonl','labels.jsonl'}
            or marker['files_sha256']!=blob_hashes):raise ValueError('complete evaluator file seals required')
    if (manifest.get('development_only') is not True or manifest.get('banks_sha256')!=bank_file_sha
            or manifest.get('bank_seals')!={bid:b.seal_sha256 for bid,b in banks.items()}):
        raise ValueError('evaluator exact bank binding mismatch')
    runtime=manifest['runtime'];runtime_hash=canonical_hash(runtime)
    if manifest.get('runtime_sha256')!=runtime_hash:raise ValueError('evaluator runtime hash mismatch')
    if (type(runtime.get('timeout_sec')) not in (int,float) or runtime['timeout_sec']!=2.5
            or type(runtime.get('memory_limit_mb')) is not int or runtime['memory_limit_mb']!=2048
            or type(runtime.get('case_workers')) is not int or runtime['case_workers']!=1
            or runtime.get('block_workers')!=[1,8,8,1] or runtime.get('injected_runner') is not False
            or type(manifest.get('max_seconds')) not in (int,float) or manifest['max_seconds']!=21600):
        raise ValueError('frozen production replay configuration mismatch')
    pids={b.problem_id for b in banks.values()}
    if set(manifest['testcase_files_sha256'])!=pids or set(manifest['universe_sha256'])!=pids:
        raise ValueError('exact evaluator universe coverage required')
    for pid in pids:
        _sha(manifest['universe_sha256'][pid]);_sha(manifest['testcase_files_sha256'][pid])
        if prepared['data_sha256'].get(pid+'/testcases.jsonl')!=manifest['testcase_files_sha256'][pid]:
            raise ValueError('evaluator/preparation testcase provenance mismatch')
    return runtime_hash


def _assignment(assignment,example_bank_ids,banks):
    fields={'example_fold','fold_sizes','folds','problem_counts','problem_fold','salt'}
    if (type(assignment) is not dict or set(assignment)!=fields or assignment['folds']!=5
            or set(assignment['example_fold'])!=set(example_bank_ids)
            or len(set(example_bank_ids.values()))!=len(example_bank_ids) or set(banks)!=set(example_bank_ids.values())):
        raise ValueError('exact selected example/bank/fold identities required')
    problem_counts=Counter(banks[bid].problem_id for bid in example_bank_ids.values());sizes=Counter()
    if dict(problem_counts)!=assignment['problem_counts'] or set(assignment['problem_fold'])!=set(problem_counts):
        raise ValueError('problem-fold identities differ')
    for eid,bid in example_bank_ids.items():
        f=assignment['example_fold'][eid];pf=assignment['problem_fold'][banks[bid].problem_id]
        if type(f) is not int or type(pf) is not int or not 0<=f<5 or f!=pf:
            raise ValueError('invalid fixed problem-fold membership')
        sizes[f]+=1
    if [sizes[i] for i in range(5)]!=assignment['fold_sizes'] or not all(sizes[i] for i in range(5)):
        raise ValueError('fixed five nonempty fold sizes differ')


def verify_source_bundle(blobs):
    """Pure preparation boundary: exact17 filenames, bytes and frozen ancestry.

    Caller-side source I/O requires a future separately reviewed release. There
    is no function here that reads production evaluator/label files itself.
    """
    if type(blobs) is not dict or set(blobs)!=SOURCE_PATHS:
        raise ValueError('exact canonical source-path inventory required; fresh outcome families forbidden')
    hashes={name:digest(data) for name,data in blobs.items()}
    if hashes[PARENT+'/COMPLETE.json']!=PARENT_COMPLETE_SHA256:
        raise ValueError('wrong pinned structure parent COMPLETE')
    seal=_json(blobs[PARENT+'/COMPLETE.json'])
    if seal.get('status')!='complete':raise ValueError('completed structure ancestor required')
    for name in ('manifest.json','folds.json'):
        if seal['files_sha256'].get(name)!=hashes[PARENT+'/'+name]:raise ValueError('parent metadata seal mismatch')
    parent=_json(blobs[PARENT+'/manifest.json']);parent_inputs={}
    for name,value in parent['provenance']['input_sha256'].items():
        prefix='/home/cdw/VSCode/zpd-apr/'
        if type(name) is not str or not name.startswith(prefix):raise ValueError('parent input path not canonical')
        relative=name[len(prefix):]
        if str(Path(relative))!=relative or '..' in Path(relative).parts or relative in parent_inputs:
            raise ValueError('duplicate or aliased parent input path')
        parent_inputs[relative]=_sha(value)
    for name,value in hashes.items():
        if name.startswith(PARENT+'/'):continue
        if parent_inputs.get(name)!=value:raise ValueError('source differs from pinned ancestor: '+name)
    selected={};selected_banks={};labels={};runtimes=[];counts={};all_users=set()
    for family,prepname,bankname,expected in ((ORIGINAL,'prepared-v2','generation/banks.jsonl',Counter(train=64,valid=32)),
                                            (EXPANSION,'prepared-v1','banks.jsonl',Counter(train=256))):
        base=family+'/'+prepname;prepared=_json(blobs[base+'/manifest.json'])
        observations=_rows(blobs[base+'/observations.jsonl'])
        if prepared['output_sha256'].get('observations.jsonl')!=hashes[base+'/observations.jsonl']:
            raise ValueError('prepared observations SHA mismatch')
        if Counter(r['split'] for r in observations)!=expected or prepared['selected_order']!=[r['example_id'] for r in observations]:
            raise ValueError('fixed original64/valid32/expansion256 preparation required')
        bankpath=family+'/run-v1/'+bankname;banks=_bank_map(_rows(blobs[bankpath]))
        if len({r['example_id'] for r in observations})!=len(observations) or {r['bank_id'] for r in observations}!=set(banks):
            raise ValueError('physical observation/bank coverage differs')
        for row in observations:
            if row['user_id'] in all_users:raise ValueError('physical preparation recipient user overlap')
            all_users.add(row['user_id']);bank=banks[row['bank_id']];obs=row['observation'];current=obs['current']
            if (obs['problem_id']!=bank.problem_id or type(current['source']) is not str
                    or current['source'].encode('utf-8')!=bank.current_source
                    or current['source_sha256']!=hashlib.sha256(bank.current_source).hexdigest()):
                raise ValueError('physical source-bank identity mismatch')
            if row['split']=='train':
                if row['example_id'] in selected or row['bank_id'] in selected_banks:raise ValueError('duplicate selected train identity')
                selected[row['example_id']]=row['bank_id'];selected_banks[row['bank_id']]=bank
        evpath=family+'/run-v1/evaluation/'
        marker=_json(blobs[evpath+'COMPLETE.json']);manifest=_json(blobs[evpath+'manifest.json'])
        runtimes.append(verify_evaluation_metadata(marker,manifest,banks,hashes[bankpath],prepared,
            {name:hashes[evpath+name] for name in ('manifest.json','completions.jsonl','labels.jsonl')}))
        physical=validate_full_labels(_rows(blobs[evpath+'labels.jsonl']),banks)
        train_banks={r['bank_id'] for r in observations if r['split']=='train'}
        labels.update({key:row for key,row in physical.items() if key[0] in train_banks})
        counts['original' if family==ORIGINAL else 'expansion']=dict(physical_prefixes=len(observations),
            train_prefixes=len(train_banks),dropped_valid_prefixes=sum(r['split']=='valid' for r in observations),physical_labels=len(physical))
    if len(set(runtimes))!=1:raise ValueError('evaluator runtime differs across frozen source cohorts')
    assignment=_json(blobs[PARENT+'/folds.json']);_assignment(assignment,selected,selected_banks)
    if len(selected)!=320:raise ValueError('exact frozen train320 required')
    core=validate_core_labels(list(labels.values()),selected_banks)
    result=dict(kind='verified_repair_feedback_train320_labels_v1',parent_complete_sha256=PARENT_COMPLETE_SHA256,
        fold_assignment_sha256=hashes[PARENT+'/folds.json'],assignment=assignment,example_bank_ids=selected,
        bank_seals={bid:b.seal_sha256 for bid,b in selected_banks.items()},core_labels=[core[key] for key in sorted(core)],
        source_sha256=hashes,source_counts=counts,runtime_sha256=runtimes[0],fresh_outcome_families_opened=False,
        original_valid32_materialized=False)
    result['verification_sha256']=canonical_hash(result)
    return result


def _verified(bundle):
    """Internal snapshot consistency only; a self-hash is not source proof."""
    fields={'kind','parent_complete_sha256','fold_assignment_sha256','assignment','example_bank_ids','bank_seals',
            'core_labels','source_sha256','source_counts','runtime_sha256','fresh_outcome_families_opened',
            'original_valid32_materialized','verification_sha256'}
    if type(bundle) is not dict or set(bundle)!=fields:raise ValueError('strict verified preparation bundle required')
    body={k:v for k,v in bundle.items() if k!='verification_sha256'}
    if (bundle['kind']!='verified_repair_feedback_train320_labels_v1' or canonical_hash(body)!=bundle['verification_sha256']
            or bundle['parent_complete_sha256']!=PARENT_COMPLETE_SHA256
            or bundle['fresh_outcome_families_opened'] is not False or bundle['original_valid32_materialized'] is not False
            or set(bundle['source_sha256'])!=SOURCE_PATHS):raise ValueError('verified preparation bundle changed')
    # Snapshot nested dictionaries so later caller mutation cannot alter writes.
    return json.loads(json.dumps(bundle,allow_nan=False))


def _canonical(path):
    p=Path(path).absolute()
    if p.resolve()!=p:raise ValueError('canonical nonsymlink path required')
    return p


def _write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,sort_keys=True,allow_nan=False);stream.write('\n')


def materialize_fold_labels(blobs,output):
    """Verify exact17 raw source blobs, then prepare separated label files.

    This intentionally runs in a preparation process, not a fit worker. No
    production CLI/release is supplied. Never overwrite an existing directory.
    A caller-supplied verified bundle is not accepted: its self-hash cannot
    establish authenticity. The pinned raw source ancestry is verified inside
    this public operation before its private writer can create any files.
    """
    if type(blobs) is not dict:raise ValueError('exact canonical source-path inventory required')
    return _materialize_verified_bundle(verify_source_bundle(dict(blobs)),output)


def _materialize_verified_bundle(bundle,output):
    """Private writer for the immediately verified, unexposed internal result.

    Not a preparation API: ``_verified`` provides snapshot consistency only.
    All external preparation callers must use ``materialize_fold_labels``.
    """
    data=_verified(bundle);output=_canonical(output)
    if output.exists():raise ValueError('new label materialization directory required')
    mapping=data['example_bank_ids'];assignment=data['assignment']
    if len(mapping)!=320 or set(mapping)!=set(assignment['example_fold']):raise ValueError('exact selected320 assignment required')
    output.mkdir(parents=True)
    paths=[]
    try:
        _write(output/'folds.json',assignment);paths.append('folds.json')
        for fold in [*range(5),None]:
            subset={eid:bid for eid,bid in mapping.items() if fold is None or assignment['example_fold'][eid]!=fold}
            selected_banks=set(subset.values())
            payload=dict(kind=ASSESSMENT_KIND if fold is None else FOLD_KIND,fold=fold,
                parent_complete_sha256=data['parent_complete_sha256'],fold_assignment_sha256=data['fold_assignment_sha256'],
                source_binding_sha256=canonical_hash(data['source_sha256']),example_bank_ids=subset,
                bank_seals={bid:data['bank_seals'][bid] for bid in sorted(selected_banks)},
                labels=[dict(row) for row in data['core_labels'] if row['bank_id'] in selected_banks])
            name='assessment/all320-labels.json' if fold is None else f'fold-{fold}/train-labels.json'
            _write(output/name,payload);paths.append(name)
        metadata={k:data[k] for k in ('parent_complete_sha256','fold_assignment_sha256','source_sha256','source_counts',
                                      'runtime_sha256','verification_sha256')}
        _write(output/'manifest.json',dict(kind='repair_feedback_fold_label_materialization_v1',train_prefixes=320,
            original_valid32_materialized=False,fitting_performed=False,**metadata));paths.append('manifest.json')
        seal=dict(status='complete',files_sha256={name:digest((output/name).read_bytes()) for name in paths},
                  parent_complete_sha256=data['parent_complete_sha256'],fold_assignment_sha256=data['fold_assignment_sha256'])
        _write(output/'COMPLETE.json',seal)
        return seal
    except BaseException as error:
        _write(output/'FAILED.json',dict(error_type=type(error).__name__,error=str(error)))
        raise


def load_fold_labels(directory,fold,banks,example_bank_ids,*,expected_sha256,expected_fold_assignment_sha256,
                     expected_source_binding_sha256):
    """Read exactly one worker fold file, pinned by externally supplied seals.

    The supervisor derives expectations from independently verified preparation
    seals/folds; this loader never reads a sibling, assessment or root manifest.
    Exact train example/bank scope must be provided, not all320 banks/labels.
    """
    if type(fold) is not int or fold not in range(5):raise ValueError('explicit fold0..4 required')
    for value in (expected_sha256,expected_fold_assignment_sha256,expected_source_binding_sha256):_sha(value)
    _provided_scope(banks,example_bank_ids)
    root=_canonical(directory);path=_canonical(root/f'fold-{fold}/train-labels.json')
    data=path.read_bytes()  # The only file read in this worker function.
    if digest(data)!=expected_sha256:raise ValueError('fold label external SHA mismatch')
    return validate_fold_envelope(_json(data),fold,banks,example_bank_ids,
        expected_fold_assignment_sha256=expected_fold_assignment_sha256,
        expected_source_binding_sha256=expected_source_binding_sha256)


def _provided_scope(banks,example_bank_ids):
    if type(example_bank_ids) is not dict or not example_bank_ids or any(type(k)is not str or type(v)is not str for k,v in example_bank_ids.items()):
        raise ValueError('exact expected training example/bank mapping required')
    _keys(banks)
    if len(set(example_bank_ids.values()))!=len(example_bank_ids) or set(example_bank_ids.values())!=set(banks):
        raise ValueError('provided bank dictionary differs from exact training example scope')


def _validate_envelope(value,fold,banks,example_bank_ids,kind,*,expected_fold_assignment_sha256,expected_source_binding_sha256):
    _provided_scope(banks,example_bank_ids)
    _sha(expected_fold_assignment_sha256);_sha(expected_source_binding_sha256)
    if type(value) is not dict or set(value)!={'kind','fold','parent_complete_sha256','fold_assignment_sha256',
            'source_binding_sha256','example_bank_ids','bank_seals','labels'}:
        raise ValueError('strict fold training file schema required')
    if (value['kind']!=kind or type(value['fold']) is not type(fold) or value['fold']!=fold
            or value['parent_complete_sha256']!=PARENT_COMPLETE_SHA256
            or value['fold_assignment_sha256']!=expected_fold_assignment_sha256
            or value['source_binding_sha256']!=expected_source_binding_sha256):
        raise ValueError('fold source/assignment/scope provenance mismatch')
    if value['example_bank_ids']!=example_bank_ids or value['bank_seals']!={bid:b.seal_sha256 for bid,b in banks.items()}:
        raise ValueError('exact expected training IDs or bank seals differ')
    return validate_core_labels(value['labels'],banks)


def validate_fold_envelope(payload,fold,banks,example_bank_ids,*,expected_fold_assignment_sha256,expected_source_binding_sha256):
    """Pure worker payload validation; caller separately pins raw file bytes."""
    if type(fold) is not int or fold not in range(5):raise ValueError('explicit fold0..4 required')
    return _validate_envelope(payload,fold,banks,example_bank_ids,FOLD_KIND,
        expected_fold_assignment_sha256=expected_fold_assignment_sha256,expected_source_binding_sha256=expected_source_binding_sha256)


def validate_assessment_envelope(payload,banks,example_bank_ids,*,expected_fold_assignment_sha256,expected_source_binding_sha256):
    """Pure assessment validation, no I/O and no prediction-opening authority.

    The separate assessor must verify all five pre-assessment prediction/model
    seals before opening its sole assessment file, then verify its external SHA.
    """
    if len(example_bank_ids)!=320:raise ValueError('exact train320 assessment expected')
    return _validate_envelope(payload,None,banks,example_bank_ids,ASSESSMENT_KIND,
        expected_fold_assignment_sha256=expected_fold_assignment_sha256,expected_source_binding_sha256=expected_source_binding_sha256)


if __name__=='__main__':
    raise SystemExit('No production CLI: separate preparation orchestration and release required.')
