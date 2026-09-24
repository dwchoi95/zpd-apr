"""Externally SHA-authorized own-fold joint4131 worker entry point.

Only the fixed own job is decoded. Its source map is authority supplied by the
trusted coordinator, not a worker-created release or an independently discovered
closure. The worker checks its exact provided map against permitted tracked code
and protocol files. It never reads/hashes a global release, preparation marker,
readiness body, parent artifact, sibling job/model or previous-stage wrapper.

The coordinator separately authenticates those roots and the complete source
closure before supplying the command's expected job SHA. These I/O contracts
are not an OS access-control or protection against a malicious trusted caller.
A syntactically valid opaque release hash alone does not prove that a release
was issued. Only the independently authenticated coordinator may supply the
external command SHA; this module deliberately cannot inspect global release
contents or issue production authorization itself. No production job is created
or released by importing this entry point.
"""
from __future__ import annotations

# Set all six fixed native/thread environment values before transitive third-
# party imports; the exact loaded native identity is subsequently authenticated.
from scripts import run_zpd_statement_sample_replay as launcher

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys

from scripts import prepare_zpd_statement_samples as preparation
from scripts import run_zpd_joint_progress_cv as worker
from scripts import zpd_joint_progress_capsule as capsule

ROOT=Path(__file__).resolve().parents[1]
PROJECT=Path('/home/cdw/VSCode/zpd-apr')
FAMILY='outputs/zpd-repair-joint-progress-20260925'
LABELS='outputs/zpd-repair-feedback-20260924/prepared-v1'
JOB_KIND='joint_progress4131_own_fold_job_v1'
READINESS_COMPLETE_SHA256='e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad'
PARENT_COMPLETE_SHA256='b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f'
CHILD_MEMORY_BYTES=32*1024**3
JOB_FIELDS={'kind','fold','inputs','own_label_contract','source_state','source_root','source_sha256',
    'runtime','controller_native','authority'}
AUTHORITY_FIELDS={'release_sha256','initialization_sha256','readiness_complete_sha256','parent_complete_sha256'}
PREFIX_SUFFIX={'scripts':'.py','src':'.py','tests':'.py','analysis_protocols':'.md'}


@dataclass(frozen=True)
class JobContext:
    project:Path
    fold:int
    job_path:Path
    output:Path
    label_directory:Path
    expected_capsule_sha256:str
    inputs:capsule.FoldInputs
    contract:worker.LabelContract
    authority:dict
    source_state:dict
    source_sha256:dict
    runtime:dict
    controller_native:dict
    input_fingerprint:str
    metadata_fingerprint:str


def require(condition,message):
    if not condition:raise ValueError(message)


def canonical(path):return preparation.canonical(path)
def sha(path):return launcher.sha_file(path)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def same(a,b):return launcher.core.encoded(a)==launcher.core.encoded(b)
def _fields(value,fields,name):
    require(type(value) is dict and set(value)==set(fields),'exact '+name+' schema required')


def _metadata_fingerprint(source,source_pins,runtime_value,native,authority,contract):
    return digest(launcher.core.encoded(dict(source_state=source,source_sha256=source_pins,runtime=runtime_value,
        controller_native=native,authority=authority,own_label_contract=vars(contract))))


def source_state():
    canonical(ROOT)
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True).strip(),
        'clean committed dedicated worker snapshot required')
    return {name:subprocess.check_output(['git','rev-parse',arg],cwd=ROOT,text=True).strip()
        for name,arg in (('revision','HEAD'),('tree','HEAD^{tree}'))}


def runtime():return preparation.runtime()
def controller_native():return launcher.controller_native_identity()


def verify_child_boundary():
    """Read only: supervisor must already have applied the fixed envelope."""
    limits=resource.getrlimit(resource.RLIMIT_AS)
    require(type(limits) is tuple and len(limits)==2 and all(type(v) is int for v in limits)
        and limits==(CHILD_MEMORY_BYTES,CHILD_MEMORY_BYTES),'exact soft/hard32GiB RLIMIT_AS worker boundary required')
    require(all(os.environ.get(k)==v for k,v in launcher.ENVIRONMENT.items()),
        'fixed single-thread and Arrow allocator environment required')


def validate_source_map(mapping):
    """Only canonical tracked code/protocol names, never metadata/data routes."""
    require(type(mapping) is dict and bool(mapping),'nonempty externally authorized source closure required')
    for name,pin in mapping.items():
        require(type(name) is str and preparation.is_sha(pin),'canonical source name and SHA required')
        p=Path(name)
        require(not p.is_absolute() and '..' not in p.parts and len(p.parts)>=2 and str(p)==name
            and p.parts[0] in PREFIX_SUFFIX and p.suffix==PREFIX_SUFFIX.get(p.parts[0]),
            'only scripts/src/tests .py and analysis_protocols .md are allowed source bindings')


def check_sources(mapping):
    validate_source_map(mapping)
    tracked=subprocess.check_output(['git','ls-files','--error-unmatch','-z','--',*sorted(mapping)],cwd=ROOT)
    require(set(tracked.decode('utf-8',errors='strict').rstrip('\0').split('\0'))==set(mapping),
        'exact supplied source closure must be tracked')
    for name,pin in mapping.items():
        require(sha(canonical(ROOT/name))==pin,'bound worker code/protocol changed: '+name)
        if name.endswith('.py'):
            module=sys.modules.get(name[:-3].replace('/','.'))
            if module is not None:require(canonical(module.__file__)==ROOT/name,'imported code outside worker snapshot')


def _own_job(path,expected):
    # Retain the SHA of exactly the consumed bytes, not a later fresh hash.
    raw=canonical(path).read_bytes()
    require(digest(raw)==expected,'externally expected own job SHA mismatch')
    return launcher.core.decode_json(raw)


def preflight(project,fold,expected_capsule_sha):
    project=canonical(project)
    require(project==PROJECT and type(fold) is int and fold in range(5)
        and preparation.is_sha(expected_capsule_sha),'fixed project/fold and external own-job SHA required')
    require(canonical(ROOT).is_relative_to(project/'.runtime') and ROOT!=project/'.runtime',
        'canonical dedicated runtime source snapshot required')
    verify_child_boundary()
    output=canonical(project/FAMILY/'run-v1'/f'fold-{fold}')
    require(not output.exists(),'new own-fold output required; no overwrite or retry')
    path=canonical(project/FAMILY/'jobs'/f'fold-{fold}.json')
    job=_own_job(path,expected_capsule_sha);_fields(job,JOB_FIELDS,'own fold job')
    require(job['kind']==JOB_KIND and type(job['fold']) is int and job['fold']==fold
        and type(job['source_root']) is str and job['source_root']==str(ROOT),'own job identity/source root differs')
    _fields(job['source_state'],('revision','tree'),'source Git state')
    require(all(type(v) is str and re.fullmatch('[0-9a-f]{40}',v) is not None for v in job['source_state'].values()),
        'exact committed revision/tree identities required')
    validate_source_map(job['source_sha256'])
    _fields(job['authority'],AUTHORITY_FIELDS,'opaque coordinator authority')
    require(all(preparation.is_sha(v) for v in job['authority'].values())
        and job['authority']['readiness_complete_sha256']==READINESS_COMPLETE_SHA256
        and job['authority']['parent_complete_sha256']==PARENT_COMPLETE_SHA256,
        'fixed independently accepted readiness and original-parent pins required')
    require(same(job['runtime'],preparation.RUNTIME),'fixed full controller runtime required')
    _fields(job['own_label_contract'],worker.LabelContract.__dataclass_fields__,'own label contract')
    inputs=capsule.decode_inputs(job['inputs'])
    require(inputs.synthetic is False and inputs.fold==fold
        and inputs.readiness_complete_sha256==READINESS_COMPLETE_SHA256,'production own fold/full readiness identity required')
    contract=worker.LabelContract(**job['own_label_contract']);worker.contract_values(contract,inputs)
    context=JobContext(project,fold,path,output,canonical(project/LABELS),expected_capsule_sha,inputs,contract,
        dict(job['authority']),dict(job['source_state']),dict(job['source_sha256']),dict(job['runtime']),
        job['controller_native'],capsule.fingerprint(inputs),_metadata_fingerprint(job['source_state'],job['source_sha256'],
            job['runtime'],job['controller_native'],job['authority'],contract))
    recheck(context)
    return context


def recheck(context):
    """Never widen to the opaque authority's global children or sibling hashes."""
    require(type(context) is JobContext,'authenticated own-job context required')
    verify_child_boundary()
    require(_metadata_fingerprint(context.source_state,context.source_sha256,context.runtime,context.controller_native,
        context.authority,context.contract)==context.metadata_fingerprint,'decoded own authorization metadata changed')
    require(same(source_state(),context.source_state) and same(runtime(),context.runtime)
        and same(controller_native(),context.controller_native),'worker source/runtime/native identity changed')
    check_sources(context.source_sha256)
    require(sha(context.job_path)==context.expected_capsule_sha256,'consumed own job changed')
    require(capsule.fingerprint(context.inputs)==context.input_fingerprint,'decoded own inputs changed')


def _outputs(context,predictions):
    output=context.output
    require(not (output/'FAILED.json').exists() and not (output/'REJECTED_COMPLETE.json').exists(),
        'failed own worker cannot become complete')
    require({p.name for p in output.iterdir()}=={*worker.FILES,'COMPLETE.json'},'exact completed own-worker inventory required')
    raw=canonical(output/'COMPLETE.json').read_bytes();marker=launcher.core.decode_json(raw);pin=digest(raw)
    _fields(marker,('status','kind','fold','completed_fits','predicted_examples','input_fingerprint','files_sha256','automatic_retries'),
        'own worker COMPLETE')
    held=capsule.scope(context.inputs)[1]
    require(marker['status']=='complete' and marker['kind']=='joint_progress4131_fold_complete_v1'
        and type(marker['fold']) is int and marker['fold']==context.fold
        and type(marker['completed_fits']) is int and marker['completed_fits']==7
        and type(marker['predicted_examples']) is int and marker['predicted_examples']==len(held)
        and marker['input_fingerprint']==context.input_fingerprint and type(marker['automatic_retries']) is int
        and marker['automatic_retries']==0,'fixed seven-fit own-worker completion required')
    pins=marker['files_sha256']
    require(type(pins) is dict and set(pins)==set(worker.FILES) and all(preparation.is_sha(v) for v in pins.values()),
        'exact own-worker artifact pin set required')
    require(all(sha(canonical(output/name))==expected for name,expected in pins.items()),'own-worker sealed output changed')
    saved=canonical(output/'predictions.json').read_bytes()
    require(digest(saved)==pins['predictions.json'] and same(launcher.core.decode_json(saved),predictions)
        and type(predictions) is list and len(predictions)==len(held),'returned own-held predictions differ from consumed seal')
    # The predictions reader is a semantic consumer after the first file pass.
    # Keep the original pin map: never accept fresh hashes as new authority.
    require({p.name for p in output.iterdir()}=={*worker.FILES,'COMPLETE.json'},
        'own-worker inventory changed after final prediction consumer')
    require(all(sha(canonical(output/name))==expected for name,expected in pins.items()),
        'own-worker output changed after final prediction consumer')
    require(sha(output/'COMPLETE.json')==pin,'consumed own-worker COMPLETE changed')
    return pin


def _reject(context,error):
    """Preserve only this fresh own-fold completion as unusable after failure."""
    if not context.output.exists():return
    marker=canonical(context.output/'COMPLETE.json');rejected=canonical(context.output/'REJECTED_COMPLETE.json')
    if marker.exists():
        require(not rejected.exists(),'rejected own completion already present')
        marker.rename(rejected)
    failed=canonical(context.output/'FAILED.json')
    if not failed.exists():
        worker.write(failed,dict(status='failed',kind='joint_progress4131_job_failed_v1',fold=context.fold,
            error_type=type(error).__name__,error=launcher.core.diagnostic_summary(str(error)),retry_authorized=False))


def execute(project,fold,expected_capsule_sha):
    context=preflight(project,fold,expected_capsule_sha)
    try:
        predictions=worker.fit_fold(context.inputs,context.label_directory,context.contract,context.output,
            recheck=lambda:recheck(context))
        # These consumers only revisit this job, its code and its own label/output.
        # The global coordinator still performs an independent final barrier.
        def inputs():
            recheck(context)
            require(sha(canonical(context.label_directory/f'fold-{fold}'/'train-labels.json'))==context.contract.expected_sha256,
                'own consumed training labels changed after worker completion')
        inputs();pin=_outputs(context,predictions);inputs()
        require(_outputs(context,predictions)==pin,'own completion changed at final boundary');inputs()
        require(_outputs(context,predictions)==pin,'own output changed after terminal input consumers')
        return dict(status='complete',fold=fold,completed_fits=7,predicted_examples=len(predictions),
            capsule_sha256=context.expected_capsule_sha256,complete_sha256=pin,
            initialization_sha256=context.authority['initialization_sha256'])
    except BaseException as error:
        _reject(context,error)
        raise


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--fold',type=int,required=True)
    parser.add_argument('--expected-capsule-sha',required=True)
    args=parser.parse_args()
    try:print(json.dumps(execute(args.project,args.fold,args.expected_capsule_sha),sort_keys=True),flush=True)
    except Exception as error:
        print(json.dumps(dict(error_type=type(error).__name__,error=launcher.core.diagnostic_summary(str(error))),ensure_ascii=True),file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__':main()
