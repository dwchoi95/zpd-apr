"""Matched exact-content-anchor C/H fit, strict decoding, unchanged public/private gate.

Pilot data/capacity are authenticated and reused. No repeated probe or retry.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil

from scripts import run_zpd_paired_history as parent
from scripts import run_zpd_anchor_pilot as pilot
from scripts import zpd_anchor_codec as codec
from scripts import prepare_zpd_full_source as full
from scripts import run_zpd_paired_inference_recovery as ipc
from scripts import generate_zpd_paired_history as generator

core=parent.core
PROJECT=parent.PROJECT
FAMILY=PROJECT/'outputs/zpd-anchor-training-20261019'
UNIT_PREFIX='zpd-anchor-training-20261019-v1'
VERSION='anchor_paired_training_release_v1'
PHASES=parent.PHASES[1:]
PHASE_SECONDS={p:parent.PHASE_SECONDS[p] for p in PHASES}
RPC_BASE=PROJECT/'tmp/an-1019-v1'
OLD_RELEASE='2323a878e1dad79ac8bbfde048581670ca8de8c3280f6903433c8edf09b3036b'
PILOT_RELEASE='0a1d990d1f82953299e3d514d5d6a8a97eb8020de54c5f451b5cf44bdb854566'
PILOT_COMPLETE='26388b2d6e9cbf7a34c427cf162e2337ddf67f007e7ea868e6eee66d796eb415'
MATERIALIZED=pilot.ROOT/'materialize-v1/materialized'
MATERIALIZED_SHA='8fe5a8c63821d68ac68b257d8421bd7fbdaa986434171a385a28e3ef15907cdd'
CAPACITY_SHA='d05f8d8c1922a79a42637d7d9801795195735552defa12c18e2b0a2380be1fbf'
REQUIRED={'scripts/run_zpd_anchor_training.py','tests/test_zpd_anchor_training.py',
          'analysis_protocols/zpd-anchor-training-20261019.md'}
BASE_BARRIER=parent.source_barrier
BASE_EARLY=parent.run_early_phase
BASE_VALIDATE=parent.validate_phase_result
BASE_COMMAND=parent.command
BASE_SUMMARIZE=parent.summarize_private
BASE_INPUTS=core.inputs_for


def amendment():
    return dict(codec=codec.VERSION,system_sha256=core.sha(codec.SYSTEM.encode()),
        predecessor_release_sha256=PILOT_RELEASE,predecessor_complete_sha256=PILOT_COMPLETE,
        materialized_complete_sha256=MATERIALIZED_SHA,capacity_report_sha256=CAPACITY_SHA,
        uniform_anchor_target_ce=True,copy_input_records_byte_exactly=True,
        fresh_base_initialization=True,capacity_probe_repeated=False,
        malformed_output='terminal_format_failure_no_partial_source_no_retry',
        output_length_finish='terminal_resource_failure_no_partial_source',
        prompt_overflow='all_slots_retained_terminal_resource_failure',
        strict_json_no_fence_extraction=True,parameter_search=False,
        rpc_base_path=str(RPC_BASE),adaptive_development=True)


def transform_inputs(old):
    new=deepcopy(old);pins={}
    for row,original in zip(new['prompts'],old['prompts'],strict=True):
        core.require(len(row['messages'])==2 and row['messages'][0]==dict(role='system',content=full.SYSTEM)
            and full.sha(full.encoded(row['messages']))==row['prompt_sha256'],'original prompt binding differs')
        parsed=full.parse_representation(row['messages'][1]['content'])
        core.require(full.sha(parsed['sources'][-1].encode())==row['binding']['current_source_sha256'],
            'current source binding differs')
        row['messages'][0]['content']=codec.SYSTEM
        row['prompt_sha256']=full.sha(full.encoded(row['messages']));pins[row['prompt_id']]=row['prompt_sha256']
        core.require(row['messages'][1]==original['messages'][1],'user/history data changed')
    for row in new['attempts']:row['prompt_sha256']=pins[row['prompt_id']]
    return new


def inputs_for(release):
    return transform_inputs(BASE_INPUTS(release))


def terminal(row,text,reason,current):
    result=dict(index=row['draw_index'],seed=row['seed'],source=None)
    if reason=='length':return dict(result,status='resource_failure',error='output token limit')
    if reason!='stop':return dict(result,status='unknown_failure',error='unexpected finish reason')
    try:
        source=codec.decode(current,text)
        source.encode('utf-8',errors='strict')
        core.require(bool(source.strip()),'empty reconstructed program')
    except (ValueError,TypeError,RecursionError,UnicodeError) as exc:
        return dict(result,status='format_failure',error=type(exc).__name__+': '+str(exc)[:240])
    return dict(result,status='success',source=source,error=None)


def generation(inputs,release,output):
    sources={r['example_id']:r['current_source'] for r in inputs['recipients']}
    for prompt in inputs['prompts']:
        core.require(prompt['messages'][0]['content']==codec.SYSTEM
            and full.parse_representation(prompt['messages'][1]['content'])['sources'][-1]==sources[prompt['example_id']],
            'anchor generation prompt/current differs')
    generator.generation(inputs,release,output,
        terminalize=lambda row,text,reason:terminal(row,text,reason,sources[row['example_id']]))


def verify_released_child(props,cert,unit,cgroup_root=Path('/sys/fs/cgroup')):
    core.require(cert['release_sha256']==PILOT_RELEASE and cert['cleanup_verified'] is True
        and cert['cgroup_removed'] is True and cert['returned_control_group']==''
        and core.normal_exit(cert['exit']), 'pilot child exit/cleanup not certified')
    recorded=cert['recorded_control_group']
    core.require(recorded.startswith('/user.slice/') and '..' not in Path(recorded).parts
        and recorded.endswith('/'+unit), 'pilot child cgroup binding differs')
    core.require(not (cgroup_root/recorded.lstrip('/')).exists(), 'pilot child cgroup reappeared')
    core.require(props.get('MainPID')=='0' and props.get('ControlGroup')=='', 'pilot child still active')
    if props.get('LoadState')=='not-found':
        core.require(props.get('ActiveState')=='inactive' and props.get('SubState')=='dead',
            'unloaded pilot child not inactive')
    else:
        core.require(core.normal_exit(props), 'retained pilot child did not exit normally')


def verify_pilot():
    from scripts.watch_zpd_completion import verify_terminal
    outer=core.read_pinned(pilot.ROOT/'VERIFIED_COMPLETE.json',PILOT_COMPLETE)
    core.require(outer['release_sha256']==PILOT_RELEASE and outer['decision']=='ready_for_training','pilot not ready')
    verify_terminal(pilot.ROOT,outer)
    p=core.props(pilot.UNIT_PREFIX+'-coordinator.service')
    core.require(core.normal_exit(p) and p.get('ControlGroup')=='', 'pilot coordinator not normally released')
    for phase in pilot.base.PHASES:
        unit=pilot.UNIT_PREFIX+'-'+phase+'.service'
        cert=core.read_pinned(pilot.ROOT/(phase+'-VERIFIED_COMPLETE.json'),outer['phases'][phase])
        verify_released_child(core.props(unit),cert,unit)
    seal=parent.read_sealed(MATERIALIZED,MATERIALIZED_SHA)
    cap=core.read_pinned(pilot.ROOT/'capacity-v1/probe/capacity_report.json',CAPACITY_SHA)
    core.require(cap['status']=='passed' and cap['optimizer_steps']==0 and cap['actual_fit'] is False
        and cap['published_adapter'] is False,'pilot must not fit')
    return seal


def validate_amendment(release,previous,pilot_release):
    core.require(release['anchor_intervention']==amendment(),'exact anchor amendment required')
    mutable={'version','family_path','phases','phase_seconds','source_sha256','tokenization_sha256','anchor_intervention'}
    core.require({k:v for k,v in release.items() if k not in mutable}==
        {k:v for k,v in previous.items() if k not in mutable},'unrelated scientific contract changed')
    core.require(REQUIRED<=set(release['source_sha256']),'missing anchor training source pins')
    allowed={'scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'}
    for n,pin in pilot_release['source_sha256'].items():
        if n not in allowed:core.require(release['source_sha256'].get(n)==pin,'frozen source drift: '+n)


def source_barrier(path,digest,revision=None):
    current,release=BASE_BARRIER(path,digest,revision)
    old=core.read_pinned(Path('analysis_protocols/zpd-paired-history-release-20261015.json'),OLD_RELEASE)
    prior=core.read_pinned(Path('analysis_protocols/zpd-anchor-pilot-release-20261019.json'),PILOT_RELEASE)
    validate_amendment(release,old,prior);verify_pilot();ipc.validate_rpc_path(RPC_BASE)
    return current,release


def run_early_phase(phase,release,output,guard,parent_sha):
    if phase=='materialize':
        seal=verify_pilot();shutil.copytree(MATERIALIZED,output/'materialized')
        core.require(parent.read_sealed(output/'materialized',MATERIALIZED_SHA)==seal,'pilot copy differs')
        core.write_new(output/'reuse.json',dict(kind='byte_exact_pilot_materialization',pilot_complete_sha256=PILOT_COMPLETE))
    elif phase=='capacity':
        verify_pilot();(output/'probe').mkdir()
        shutil.copyfile(pilot.ROOT/'capacity-v1/probe/capacity_report.json',output/'probe/capacity_report.json')
        core.require(core.sha_file(output/'probe/capacity_report.json')==CAPACITY_SHA,'capacity reuse differs')
        core.write_new(output/'reuse.json',dict(kind='certified_no_fit_capacity_reuse',probe_repeated=False,
            pilot_complete_sha256=PILOT_COMPLETE,capacity_sha256=CAPACITY_SHA))
    else:BASE_EARLY(phase,release,output,guard,parent_sha)


def validate_phase_result(phase,release,output):
    if phase=='materialize':parent.read_sealed(output/'materialized',MATERIALIZED_SHA)
    elif phase=='capacity':
        core.require(core.sha_file(output/'probe/capacity_report.json')==CAPACITY_SHA,'capacity reuse differs')
        BASE_VALIDATE(phase,release,output)
    else:BASE_VALIDATE(phase,release,output)


@contextmanager
def configured_core():
    old=core.FAMILY,core.unit,core.generation
    core.FAMILY,core.unit,core.generation=FAMILY,parent.unit,generation
    try:yield core
    finally:core.FAMILY,core.unit,core.generation=old


def command(phase,path,digest,snapshot=None):
    cmd=BASE_COMMAND(phase,path,digest,snapshot)
    cmd=['scripts.run_zpd_anchor_training' if v=='scripts.run_zpd_paired_history' else v for v in cmd]
    if phase=='generation':
        cmd=['--setenv=TMPDIR='+str(RPC_BASE) if v.startswith('--setenv=TMPDIR=') else v for v in cmd]
        cmd.insert(cmd.index(str(PROJECT/'.runtime/fse-vllm/bin/python')),'--setenv=VLLM_RPC_BASE_PATH='+str(RPC_BASE))
    return cmd


def summarize_private(report,release_sha,report_sha,population):
    result=BASE_SUMMARIZE(report,release_sha,report_sha,population)
    result.update(intervention_kind='matched_anchor_output_representation',anchor_intervention=amendment())
    result['limitations'].append('Output/system/target representation package; not an isolated objective or history effect.')
    return result


@contextmanager
def configured():
    overrides=dict(FAMILY=FAMILY,UNIT_PREFIX=UNIT_PREFIX,VERSION=VERSION,PHASES=PHASES,
        PHASE_SECONDS=PHASE_SECONDS,source_barrier=source_barrier,run_early_phase=run_early_phase,
        validate_phase_result=validate_phase_result,configured_core=configured_core,command=command,
        summarize_private=summarize_private)
    old={k:getattr(parent,k) for k in overrides};old_inputs=core.inputs_for
    for k,v in overrides.items():setattr(parent,k,v)
    core.inputs_for=inputs_for
    try:yield
    finally:
        core.inputs_for=old_inputs
        for k,v in old.items():setattr(parent,k,v)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('verify','worker','supervise','tokenize'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha',required=True)
    a=p.parse_args()
    if a.mode=='tokenize':
        old=core.read_pinned(a.release,a.release_sha);inputs=inputs_for(old)
        _,report=core.render_inputs(inputs,old['base_model'])
        print(json.dumps(dict(tokenization_sha256=core.sha(core.encoded(report)),arms=report['arms'],
            transformed_inputs_sha256=core.sha(core.encoded(inputs)),total_attempts=len(inputs['attempts']))));return
    with configured():
        if a.mode=='verify':print(source_barrier(a.release,a.release_sha)[0])
        elif a.mode=='supervise':
            source_barrier(a.release,a.release_sha)
            core.require(not FAMILY.exists() and not RPC_BASE.exists(),'fresh run and IPC paths required')
            RPC_BASE.mkdir(parents=True,mode=0o700);parent.supervise(a.release,a.release_sha)
        else:
            if a.phase=='generation':
                old=ipc.RPC_BASE;ipc.RPC_BASE=RPC_BASE
                try:core.write_new(FAMILY/'IPC_PREFLIGHT.json',ipc.probe_ipc())
                finally:ipc.RPC_BASE=old
            parent.worker(a.phase,a.release,a.release_sha)


if __name__=='__main__':main()
