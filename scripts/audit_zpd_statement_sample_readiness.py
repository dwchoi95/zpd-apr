"""Separately released observation-only progress32 readiness audit.

No label/model/assessment loader, candidate execution, fit, retry or fallback.
The absent external release refuses before any empirical body is opened.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
from itertools import combinations
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys

# This sets the released controller environment before NumPy/sklearn/Arrow can
# be imported transitively. The native identity is checked before body access.
from scripts import run_zpd_statement_sample_replay as launcher

import numpy as np

from scripts import audit_zpd_repair_feedback_support as observed
from scripts import prepare_zpd_statement_samples as preparation
from scripts import zpd_statement_sample_replay_inputs as bridge
from scripts import zpd_statement_sample_progress as progress
from scripts import zpd_statement_sample_readiness as readiness

ROOT=Path(__file__).resolve().parents[1]
PROJECT=Path('/home/cdw/VSCode/zpd-apr')
OUTPUT='outputs/zpd-statement-sample-feedback-20260924/readiness-v1'
RELEASE='analysis_protocols/zpd-statement-sample-readiness-release-20260924.json'
SIDECAR=RELEASE+'.sha256'
OLD_SUPPORT='outputs/zpd-repair-feedback-20260924/support-v1'
# Previously frozen external pin: scripts/zpd_repair_feedback_inputs.py:19.
# That module's model/baseline loader is deliberately NOT imported or called.
OLD_SUPPORT_SHA='64d8f2a11de01ee08a2ed0ac51ac44b1ad4ec56281eaac971eadbb88cc4270d0'
OLD_FILES=('manifest.json','folds.json','report.json','STATUS.json')
ARTIFACTS=('manifest.json','folds.json','features.jsonl','report.json','STATUS.json')
PROTOCOLS=(preparation.PROTOCOL,bridge.launcher.PROTOCOL,readiness.PROTOCOL)
SOURCE_FILES=tuple(sorted(set((*bridge.SOURCE_FILES,*observed.SOURCE_FILES,*PROTOCOLS,
    'scripts/zpd_repair_feedback_inputs.py','scripts/zpd_statement_sample_readiness.py',
    'tests/test_zpd_statement_sample_readiness.py','scripts/audit_zpd_statement_sample_readiness.py',
    'tests/test_zpd_statement_sample_readiness_driver.py'))))
NORM_ALLOWANCE=1e-12
require=bridge.require
same=bridge.same
encoded=bridge.encoded
digest=bridge.replay.sha
canonical=preparation.canonical
file_sha=bridge.launcher.sha_file


def configuration():
    return dict(kind='observed_statement_sample_progress32_readiness_v1',output=OUTPUT,
        cohort=readiness.COUNTS,progress=progress.configuration(),readiness_kind=readiness.VERSION,
        geometry_tau=readiness.TOLERANCE,geometry_comparison='strict_greater_than',
        norm_reduction='sqrt_math.fsum_float64_coordinate_squares',norm_roundoff_allowance=NORM_ALLOWANCE,
        candidate_l2_bound=2.**-.5,pair_l2_bound=1.,old_support=OLD_SUPPORT,
        old_support_complete_sha256=OLD_SUPPORT_SHA,old18_parity='exact_values_masks_candidate_order',
        recipient_order='original_observed_loader_order; exact_per_ID_prepared_comparison',
        observation_feedback_accessed=True,repair_labels_accessed=False,model_predictions_accessed=False,
        candidate_execution=False,fitting_authorized=False,automatic_retries=0,overwrite=False)


def source_state():
    canonical(ROOT)
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True).strip(),
            'clean committed consumer snapshot required')
    return {k:subprocess.check_output(['git','rev-parse',v],cwd=ROOT,text=True).strip()
            for k,v in (('revision','HEAD'),('tree','HEAD^{tree}'))}


def check_sources(approval):
    expected=set(SOURCE_FILES)|{RELEASE,SIDECAR}
    tracked=subprocess.check_output(['git','ls-files','--error-unmatch','-z','--',*sorted(expected)],cwd=ROOT)
    require(set(tracked.decode('utf-8',errors='strict').rstrip('\0').split('\0'))==expected,
            'every consumer source/protocol/release must be tracked')
    require(type(approval['source_sha256']) is dict and set(approval['source_sha256'])==set(SOURCE_FILES),
            'exact consumer source closure required')
    for name,pin in approval['source_sha256'].items():
        require(preparation.is_sha(pin) and file_sha(ROOT/name)==pin,'released consumer source drift: '+name)
        if name.endswith('.py'):
            module=sys.modules.get(name[:-3].replace('/','.'))
            if module is not None:require(canonical(module.__file__)==ROOT/name,'imported dependency outside released snapshot')


def runtime_identity():return launcher.probe.runtime_identity()
def controller_runtime():return preparation.runtime()
def controller_native_identity():return launcher.controller_native_identity()


def _old_header(marker,manifest,approval):
    bridge.replay.exact_fields(marker,('status','files_sha256','fitting_performed'))
    require(marker['status']=='complete' and marker['fitting_performed'] is False
        and type(marker['files_sha256']) is dict and set(marker['files_sha256'])==set(OLD_FILES)
        and all(preparation.is_sha(v) for v in marker['files_sha256'].values()),'exact completed old source-only support required')
    bridge.replay.exact_fields(manifest,('source','source_root','source_sha256','input_sha256','runtime',
        'parent_complete_sha256','source_coverage','fitting_performed'))
    require(manifest['parent_complete_sha256']==observed.PARENT_SHA and manifest['fitting_performed'] is False
        and same(manifest['runtime'],{k:v for k,v in preparation.RUNTIME.items() if k!='tqdm'})
        and type(manifest['source_sha256']) is dict and set(manifest['source_sha256'])==set(observed.SOURCE_FILES)
        and all(approval['source_sha256'][n]==v for n,v in manifest['source_sha256'].items()),
        'old source-only support source/runtime/parent differs')
    allowed=observed.ObservedReader(PROJECT).allowed
    require(type(manifest['input_sha256']) is dict and set(manifest['input_sha256'])<=allowed
        and all(preparation.is_sha(v) for v in manifest['input_sha256'].values()),'old support has forbidden input bindings')


def preflight(project):
    """Release/source/runtime and fixed prerequisite metadata only."""
    project=canonical(project)
    require(project==PROJECT and canonical(ROOT).is_relative_to(project/'.runtime') and ROOT!=project/'.runtime',
            'fixed canonical project/consumer runtime snapshot required')
    output=canonical(project/OUTPUT);require(not output.exists(),'new fixed output required; no overwrite or retry')
    release=canonical(ROOT/RELEASE);sidecar=canonical(ROOT/SIDECAR)
    require(release.is_file() and sidecar.is_file(),'separate observed-readiness release required')
    raw=release.read_bytes();side=sidecar.read_bytes()
    require(re.fullmatch(b'[0-9a-f]{64}\n',side) is not None and digest(raw)==side[:-1].decode('ascii'),
            'strict external release SHA sidecar mismatch')
    approval=bridge.replay.decode_json(raw)
    bridge.replay.exact_fields(approval,('kind','project','output','configuration','source_sha256','protocol_sha256',
        'controller_runtime','controller_native','replay_runtime','replay_runtime_sha256','replay_authority','old_support_complete_sha256',
        'readiness_audit_authorized','execution_authorized','fitting_authorized','decision_reason'))
    require(approval['kind']=='statement_sample_readiness_release_v1' and approval['project']==str(PROJECT)
        and approval['output']==OUTPUT and same(approval['configuration'],configuration())
        and approval['old_support_complete_sha256']==OLD_SUPPORT_SHA
        and approval['readiness_audit_authorized'] is True and approval['execution_authorized'] is False
        and approval['fitting_authorized'] is False and type(approval['decision_reason']) is str
        and bool(approval['decision_reason'].strip()),'fixed readiness-only release contract required')
    bridge.replay.exact_fields(approval['replay_authority'],tuple(bridge.ReplayAuthority.__dataclass_fields__))
    authority=bridge.ReplayAuthority(**approval['replay_authority'])
    require(authority.runtime_sha256==approval['replay_runtime_sha256']
        ==digest(encoded(approval['replay_runtime'])) and same(approval['controller_runtime'],preparation.RUNTIME),
        'exact released runtime authority required')
    state=source_state();check_sources(approval)
    require(type(approval['protocol_sha256']) is dict and set(approval['protocol_sha256'])==set(PROTOCOLS)
        and all(approval['protocol_sha256'][p]==approval['source_sha256'][p] for p in PROTOCOLS),
        'exact frozen protocol source pins required')
    require(same(controller_runtime(),preparation.RUNTIME) and same(runtime_identity(),approval['replay_runtime'])
        and same(controller_native_identity(),approval['controller_native']),
            'consumer/runtime differs from accepted replay environment')
    reader=preparation.BoundReader(project,[OLD_SUPPORT+'/'+n for n in ('COMPLETE.json',*OLD_FILES)])
    def read(name,pin):return bridge.replay.decode_json(reader.read(OLD_SUPPORT+'/'+name,pin))
    marker=read('COMPLETE.json',OLD_SUPPORT_SHA)
    require(type(marker) is dict and type(marker.get('files_sha256')) is dict
        and set(marker['files_sha256'])==set(OLD_FILES),'old support exact fixed inventory required')
    manifest=read('manifest.json',marker['files_sha256']['manifest.json']);_old_header(marker,manifest,approval)
    folds=read('folds.json',marker['files_sha256']['folds.json'])
    # Only authenticate outer metadata here. Full body loading belongs to the
    # reviewed bridge after this independently supplied authority is accepted.
    outer_reader=preparation.BoundReader(project,[bridge.OUTER+'/COMPLETE.json'])
    outer=bridge.replay.decode_json(outer_reader.read(bridge.OUTER+'/COMPLETE.json',authority.outer_complete_sha256))
    bridge._outer_marker(outer,authority)
    context=dict(project=project,output=output,approval=approval,authority=authority,state=state,
        old_reader=reader,outer_reader=outer_reader,old_marker=marker,old_manifest=manifest,old_folds=folds,
        release_sha256=digest(raw),release_bindings={str(release):digest(raw),str(sidecar):digest(side)})
    recheck(context)
    return context


def _reject_flags(context):
    for base in (OLD_SUPPORT,bridge.PREPARED,bridge.INNER,bridge.OUTER):
        for name in ('FAILED.json','REJECTED_COMPLETE.json'):
            require(not (context['project']/base/name).exists(),'rejected prerequisite cannot supply readiness')


def recheck(context):
    _reject_flags(context)
    require(same(source_state(),context['state']) and same(controller_runtime(),preparation.RUNTIME)
        and same(runtime_identity(),context['approval']['replay_runtime'])
        and same(controller_native_identity(),context['approval']['controller_native']),'consumer Git/runtime changed')
    check_sources(context['approval'])
    require(all(file_sha(path)==pin for path,pin in context['release_bindings'].items()),'consumed readiness release changed')
    context['old_reader'].recheck();context['outer_reader'].recheck()
    if 'observed_reader' in context:context['observed_reader'].recheck()
    if 'loaded_replay' in context:context['loaded_replay'].recheck()
    if 'input_fingerprint' in context:
        require(input_fingerprint(context)==context['input_fingerprint'],'in-memory observed input identity changed')
    _reject_flags(context)


def _merge(*maps):
    result={}
    for mapping in maps:
        for key,value in mapping.items():
            require(key not in result or result[key]==value,'conflicting consumed input binding')
            result[key]=value
    return result


def input_fingerprint(context):
    return digest(encoded(dict(observations=context['observations'],assignment=context['assignment'],coverage=context['coverage'],
        banks={k:dict(seal_sha256=b.seal_sha256,candidate_ids=[c.candidate_id for c in b.candidates])
               for k,b in context['banks'].items()},replay_bindings=context['loaded_replay'].feedback.bindings_json.decode('ascii'))))


def align_inputs(observations,banks,assignment,coverage,feedback,observed_bindings,old_manifest,old_folds,old_report,prepared_manifest):
    """Exact original observed rows and saved source-only parity, no model path."""
    require(type(observations) is list and len(observations)==readiness.COUNTS['examples']
        and all(type(o) is dict and set(o)==observed.OBSERVATION_FIELDS for o in observations),'all320 exact observed-only rows required')
    ids=[o['example_id'] for o in observations]
    require(len(set(ids))==len(ids) and len({o['user_id'] for o in observations})==320
        and len({o['problem_id'] for o in observations})==23 and set(banks)=={o['bank_id'] for o in observations},
        'original full recipient/problem/bank coverage required')
    prepared_rows=feedback.observations()
    require(len(prepared_rows)==len(observations) and same(sorted(observations,key=lambda o:o['example_id']),
        sorted(prepared_rows,key=lambda o:o['example_id'])),'prepared observed/current/prior/donor identities or ordered source contents differ')
    require(same(preparation.roster.build_roster(observations).to_json(),feedback.roster()),'prepared full roster/memberships differ')
    require(same(assignment,feedback.folds()) and same(assignment,old_folds),'exact original/prepared fold assignment differs')
    require(same(coverage,old_manifest['source_coverage']) and same(coverage,prepared_manifest['source_coverage']),
            'original/prepared source-language coverage differs')
    require(same(observed_bindings,old_manifest['input_sha256']),'observed fixed input bindings differ from original support')
    allowed=observed.ObservedReader(PROJECT).allowed
    require(same(observed_bindings,{n:v for n,v in prepared_manifest['input_sha256'].items() if n in allowed}),
            'prepared observed input binding subset differs')
    require(type(old_report) is dict and old_report.get('kind')=='observed_only_repair_feedback_support_v1'
        and all(old_report.get(n) is False for n in ('fitting_performed','outcomes_opened','successors_opened',
            'models_opened','predictions_opened','fit_release_authorized')),'old comparison must be source-only support')
    rows=old_report.get('rows');require(type(rows) is list and len(rows)==320,'all original support rows required')
    old={r['example_id']:r for r in rows};require(len(old)==320 and set(old)==set(ids),'old support exact example identity required')
    require(set(feedback.universes)=={o['problem_id'] for o in observations},'all original problem universes required')
    for o in observations:
        bank=banks[o['bank_id']];saved=old[o['example_id']]
        require(type(bank) is observed.CandidateBank and bank.problem_id==o['problem_id']
            and observed._exact_text(bank.current_source)==o['current_code']
            and observed.source_hash(bank.current_source)==o['current_source_sha256'],'exact observed bank source identity required')
        expected={k:o[k] for k in ('example_id','user_id','problem_id','bank_id','fold','donor_example_id','donor_user_id')}
        expected.update(bank_seal_sha256=bank.seal_sha256,prior_count=len(o['history']),candidate_count=len(bank.candidates),
                        prior_languages=dict(Counter(h['language'] for h in o['history'])))
        require(all(same(saved.get(k),v) for k,v in expected.items()),'frozen bank/candidate/source support identity differs')
        candidates=saved.get('candidates')
        require(type(candidates) is list and [c.get('candidate_id') for c in candidates]==[c.candidate_id for c in bank.candidates],
                'frozen deduplicated candidate order differs')
        for c,row in zip(bank.candidates,candidates,strict=True):
            require(row.get('is_noop') is c.is_noop,'frozen no-op identity differs')
    require(sum(len(b.candidates) for b in banks.values())==2544,'all2544 frozen candidates required')
    return old


def norm_certificate(matrices):
    result={}
    for arm in progress.ARMS:
        x=matrices[arm]
        require(type(x) is np.ndarray and x.ndim==2 and x.shape[1]==32 and x.dtype==np.float64
            and np.isfinite(x).all(),'finite float64 source32 matrices required')
        lengths=[math.sqrt(math.fsum(float(v*v) for v in row)) for row in x]
        pairs=[math.sqrt(math.fsum(float(v*v) for v in (x[a]-x[b]))) for a,b in combinations(range(len(x)),2)]
        require(max(lengths,default=0.)<=2.**-.5+NORM_ALLOWANCE
            and max(pairs,default=0.)<=1.+NORM_ALLOWANCE,'prospective candidate/pair analytic norm bound violated')
        result[arm]=dict(candidates=len(x),unordered_pairs=len(pairs),max_candidate_l2=max(lengths,default=0.),
                        max_pair_l2=max(pairs,default=0.))
    return result


def _json_value(value):
    if type(value) is np.ndarray:return value.tolist()
    if isinstance(value,dict) or hasattr(value,'items'):return {k:_json_value(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [_json_value(v) for v in value]
    if type(value) in (progress.ProgressFeatures,progress.Moments):
        return {k:_json_value(getattr(value,k)) for k in value.__dataclass_fields__}
    return value


def encode_bank(observation,bank,feedback,saved):
    universe=feedback.universes[observation['problem_id']]
    features=[];values=[];masks=[]
    for candidate,previous in zip(bank.candidates,saved['candidates'],strict=True):
        code=observed._exact_text(candidate.source)
        old_value,old_mask=observed.semantic.encode_edit(observation['current_code'],code,'Python','Python')
        require(same(previous.get('values'),old_value.tolist()) and same(previous.get('masks'),old_mask.tolist()),
                'frozen old18 values/masks differ from exact original/candidate sources')
        value=progress.candidate_features(observation['current_code'],code,observation['current_verdict'],
            observation['history'],observation['current_timestamp'],universe=universe,vectors=feedback.vectors,
            donor_history=observation['donor_history'],shuffle_key=observation['example_id'])
        features.append(value);values.append(old_value);masks.append(old_mask)
    ids=tuple(c.candidate_id for c in bank.candidates)
    spec=readiness.BankSpec(observation['example_id'],observation['user_id'],observation['problem_id'],observation['fold'],
        observation['bank_id'],bank.seal_sha256,ids,observed.source_hash(bank.current_source),
        tuple(h['verdict'] for h in observation['history'])+(observation['current_verdict'],),len(universe.case_ids))
    block=readiness.BankFeatures(ids,np.asarray(values,dtype=np.float64),np.asarray(masks,dtype=bool),tuple(features))
    # Validate source/mask/centered arithmetic before the streamed feature row.
    readiness.bank_record(spec,block)
    norms=norm_certificate({arm:np.stack([c.arms[arm] for c in features]) for arm in progress.ARMS})
    row=dict(spec=_json_value(asdict(spec)),current_source_sha256=observation['current_source_sha256'],
        observed_source_ids=observation['observed_source_ids'],donor_source_ids=observation['donor_source_ids'],
        donor_example_id=observation['donor_example_id'],donor_user_id=observation['donor_user_id'],
        sample_set_sha256=universe.sample_set_sha256,runtime_sha256=universe.runtime_sha256,case_ids=list(universe.case_ids),
        candidate_ids=list(ids),old_event_values=block.old_event_values.tolist(),old_event_masks=block.old_event_masks.tolist(),
        candidates=[_json_value(c) for c in features],norms=norms)
    return spec,block,row


class Ledger:
    def __init__(self,output):self.output=output;self.expected={}
    def write(self,name,value,*,replace=False):
        require(name in (*ARTIFACTS,'COMPLETE.json','FAILED.json'),'fixed new audit output name required')
        path=canonical(self.output/name);data=encoded(value)+b'\n'
        if replace:
            require(name=='STATUS.json' and name in self.expected and file_sha(path)==self.expected[name],
                    'only own unchanged status may be replaced')
            temp=canonical(self.output/'STATUS.json.partial')
            with temp.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            temp.replace(path)
        else:
            with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        self.expected[name]=digest(data);return self.expected[name]
    def verify(self):
        require({p.name for p in self.output.iterdir()}==set(ARTIFACTS),'unexpected readiness output inventory')
        require(set(self.expected)==set(ARTIFACTS) and all(file_sha(self.output/n)==p for n,p in self.expected.items()),
                'written readiness artifact drift')


def audit(project):
    context=preflight(project);output=context['output'];output.mkdir(parents=True,exist_ok=False);ledger=Ledger(output)
    try:
        ledger.write('STATUS.json',dict(phase='binding_inputs',completed_examples=0,total_examples=320))
        loaded=bridge.load_feedback(context['project'],context['authority'],source_sha256={n:context['approval']['source_sha256'][n]
            for n in bridge.SOURCE_FILES});context['loaded_replay']=loaded
        observations,banks,assignment,coverage,reader=observed.load_inputs(context['project'])
        context.update(observations=observations,banks=banks,assignment=assignment,coverage=coverage,observed_reader=reader)
        old=context['old_reader'];marker=context['old_marker']
        report=bridge.replay.decode_json(old.read(OLD_SUPPORT+'/report.json',marker['files_sha256']['report.json']))
        status=bridge.replay.decode_json(old.read(OLD_SUPPORT+'/STATUS.json',marker['files_sha256']['STATUS.json']))
        require(same(status,dict(phase='complete',completed_examples=320,total_examples=320)),'old full support did not complete')
        prep_name=bridge.PREPARED+'/manifest.json'
        prepared=bridge.replay.decode_json(loaded.reader.read(prep_name,loaded.reader.bindings[prep_name]))
        saved=align_inputs(observations,banks,assignment,coverage,loaded.feedback,reader.bindings,
            context['old_manifest'],context['old_folds'],report,prepared)
        context['input_fingerprint']=input_fingerprint(context);recheck(context)
        bindings=_merge(reader.bindings,loaded.reader.bindings,old.bindings,context['outer_reader'].bindings)
        ledger.write('manifest.json',dict(kind='statement_sample_progress32_readiness_manifest_v1',configuration=configuration(),
            source=context['state'],source_root=str(ROOT),source_sha256=context['approval']['source_sha256'],
            controller_runtime=preparation.RUNTIME,controller_native=context['approval']['controller_native'],
            replay_runtime=context['approval']['replay_runtime'],driver_feature_generation_performed=True,
            replay_authority=asdict(context['authority']),release_sha256=context['release_sha256'],
            release_file_bindings=context['release_bindings'],input_sha256=bindings,input_fingerprint=context['input_fingerprint'],
            old_support_complete_sha256=OLD_SUPPORT_SHA,source_coverage=coverage,observation_feedback_accessed=True,
            repair_labels_accessed=False,model_predictions_accessed=False,fitting_authorized=False))
        ledger.write('folds.json',assignment)
        specs=[];all_features={};journal_hash=hashlib.sha256();candidate_count=0
        with canonical(output/'features.jsonl').open('xb') as journal:
            for completed,o in enumerate(observations,1):
                spec,block,row=encode_bank(o,banks[o['bank_id']],loaded.feedback,saved[o['example_id']])
                specs.append(spec);all_features[o['example_id']]=block
                data=encoded(row)+b'\n';journal.write(data);journal.flush();os.fsync(journal.fileno());journal_hash.update(data)
                candidate_count+=len(spec.candidate_ids)
                progress_state=dict(phase='features',completed_examples=completed,total_examples=320,
                                    completed_candidates=candidate_count,total_candidates=2544)
                ledger.write('STATUS.json',progress_state,replace=True)
                if completed%25==0 or completed==320:print(json.dumps(progress_state,sort_keys=True),flush=True)
        ledger.expected['features.jsonl']=journal_hash.hexdigest()
        result=readiness.assess_readiness(tuple(specs),all_features)
        result.update(driver_feature_generation_performed=True,
            feature_generation_metadata_scope='feature_generation_performed describes the pure supplied-feature gate; '
                'driver_feature_generation_performed describes this authenticated source-to-feature driver')
        ledger.write('report.json',result)
        ledger.write('STATUS.json',dict(phase='complete',completed_examples=320,total_examples=320,
            completed_candidates=2544,total_candidates=2544,readiness_passed=result['readiness_passed']),replace=True)
        ledger.verify();recheck(context);ledger.verify();recheck(context)
        ledger.write('COMPLETE.json',dict(status='complete',kind='statement_sample_progress32_readiness_complete_v1',
            files_sha256=dict(ledger.expected),readiness_passed=result['readiness_passed'],completed_examples=320,
            completed_candidates=2544,observation_feedback_accessed=True,repair_labels_accessed=False,
            fitting_authorized=False,automatic_retries=0))
        return result
    except BaseException as exc:
        marker=output/'COMPLETE.json'
        if marker.exists():
            rejected=canonical(output/'REJECTED_COMPLETE.json');require(not rejected.exists(),'rejected readiness marker already exists')
            canonical(marker).rename(rejected)
        ledger.write('FAILED.json',dict(error_type=type(exc).__name__,error=bridge.replay.diagnostic_summary(str(exc)),
            fitting_authorized=False,readiness_available=False,automatic_retries=0))
        raise


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--project',type=Path,required=True)
    args=parser.parse_args()
    try:audit(args.project)
    except Exception as exc:
        print(json.dumps(dict(error_type=type(exc).__name__,error=bridge.replay.diagnostic_summary(str(exc))),ensure_ascii=True),file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__':main()
