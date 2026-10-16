"""Two-slot current-anchored routing from sealed draws; no new generation."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import time

from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_full_source as driver
from scripts import run_zpd_crossed_inference as crossed

PROJECT = core.PROJECT
FAMILY = PROJECT / 'outputs/zpd-anchored-routing-20261016'
UNIT_PREFIX = 'zpd-anchored-routing-20261016-v1'
VARIANT = 'current_anchored_equal_budget_routing_v1'
PHASES = core.PHASES
CROSSED_RELEASE = PROJECT / '.runtime/crossed-inference-20261016-v1/analysis_protocols/zpd-crossed-inference-release-20261016.json'
CROSSED_SHA = 'e0c46e37550cc9bffaedf15c6732751281fa902a62edd7507e03155b514eed3c'
CROSSED_COMPLETE = '506cb413609698fac4585c6b3d8d8975f7050938b8272340718c44d566f4b23d'
ORIGINS = {'original':dict(family=crossed.previous.FAMILY,attempts_sha256='294eca31854a53d72ac30f11a0cac8f738fc78d39d1d094855bd1fcd0c7d04c7'),
           'crossed':dict(family=crossed.FAMILY,attempts_sha256='62619e61b32243497609c99646785b5a6874114652f85e88a4f41ddb9ac5c8f1')}
BASE_INPUTS = core.inputs_for
BASE_COMMAND = driver.command
PLAN_SHA = '90839d9a29cff7d15d5eacbf97eda321b5267e9180c3ea9ada8b3f150cf4c648'
ROWS_SHA = '76bb0897bb92f789ce547bffb78c4da8964a8fe3f71ba2959de6fb68d20242c3'
REQUIRED = crossed.REQUIRED | {'scripts/run_zpd_anchored_routing.py','tests/test_zpd_anchored_routing.py',
                               'analysis_protocols/zpd-anchored-routing-20261016.md'}
OBSERVER_CHANGES = crossed.OBSERVER_CHANGES | {'tests/test_zpd_crossed_inference.py'}


def routing_contract():
    return dict(version=VARIANT, predecessor_release_sha256=CROSSED_SHA,
        predecessor_complete_sha256=CROSSED_COMPLETE,
        origin_ledgers={k:dict(family=str(v['family']),attempts_sha256=v['attempts_sha256']) for k,v in ORIGINS.items()},
        anchor=dict(origin='original',arm='C',draw_index=0,adapter='C'),
        secondary={a:dict(origin='crossed' if a=='C' else 'original',arm=a,draw_index=1,adapter='H') for a in core.ARMS},
        slots_per_arm=2, unique_origin_attempts=1600, arm_slot_references=2560,
        new_generation=False, fitting=False, private_labels_used_for_routing=False,
        adaptive_replay=True, confirmatory=False, model_promotion=False)


def route_inputs(original):
    """Pure fixed transform; no generated source, verdict or score is available."""
    result=deepcopy(original)
    index={(r['example_id'],r['arm'],r['draw_index']):r for r in original['attempts']}
    core.require(len(index)==len(original['attempts'])==2560,'full unique origin plan required')
    rows=[]
    for destination in original['attempts']:
        eid,arm,draw=destination['example_id'],destination['arm'],destination['draw_index']
        core.require(arm in core.ARMS and draw in (0,1),'fixed arm and slot required')
        source=index[eid,'C' if draw==0 else arm,draw]
        row=deepcopy(source)
        row.update(arm=arm,attempt_id=destination['attempt_id'],
            origin=dict(ledger='crossed' if draw==1 and arm=='C' else 'original',
                        attempt_id=source['attempt_id'],prompt_arm=source['arm']))
        rows.append(row)
    result['attempts']=rows
    result['routing']=routing_contract()
    return result


def routed_inputs(release):
    return route_inputs(BASE_INPUTS(release))


def assemble(inputs, ledgers, release):
    """Retain exact terminal bytes/failures and actual generating-input identity."""
    original=deepcopy(inputs)
    # The only valid routed plan is reconstructed from the frozen original plan
    # by the caller. Do not infer a route from candidate quality or label files.
    core.require(inputs.get('routing')==routing_contract(),'fixed routing metadata required')
    maps={name:{r['attempt_id']:r for r in values} for name,values in ledgers.items()}
    core.require(set(maps)==set(ORIGINS) and all(len(maps[k])==len(ledgers[k])==2560 for k in maps),
                 'complete unique origin ledgers required')
    completed=[]
    for planned in original['attempts']:
        origin=planned['origin'];source=maps[origin['ledger']][origin['attempt_id']]
        draw=planned['draw_index'];arm=planned['arm']
        core.require(origin==dict(ledger='crossed' if draw==1 and arm=='C' else 'original',
                     attempt_id=source['attempt_id'],prompt_arm='C' if draw==0 else arm), 'fixed origin route differs')
        for key,value in planned.items():
            if key not in ('arm','attempt_id','origin'):
                core.require(source.get(key)==value,'actual generating input differs: '+key)
        role='C' if draw==0 else 'H'
        core.require(source['arm']==origin['prompt_arm'] and source['adapter_role']==role
                     and source['adapter_model_sha256']==release['model_sha256'][
                         str(Path(release['adapter_'+role])/'adapter_model.safetensors')], 'origin adapter/prompt differs')
        core.require(source['attempt']['index']==draw and source['attempt']['seed']==planned['seed'],
                     'origin terminal slot or seed differs')
        row=deepcopy(source);row.update(deepcopy(planned))
        row['origin_row_sha256']=core.sha(core.encoded(source));completed.append(row)
    core.require(len(completed)==2560 and len({r['attempt_id'] for r in completed})==2560,'exact routed slot coverage required')
    core.require(len({(r['origin']['ledger'],r['origin']['attempt_id']) for r in completed})==1600,
                 'exact unique origin coverage required')
    # Check the unchanged selector sees only two slots per arm plus current.
    core.candidate_banks(inputs,completed,'0'*64)
    return completed


def verify_predecessor():
    crossed.verify_predecessor()
    old=core.read_pinned(CROSSED_RELEASE,CROSSED_SHA)
    outer=core.read_pinned(crossed.FAMILY/'VERIFIED_COMPLETE.json',CROSSED_COMPLETE)
    core.require(outer['status']=='complete' and outer['release_sha256']==CROSSED_SHA
                 and set(outer['phases'])==set(PHASES),'crossed completion identity differs')
    for phase,pin in outer['phases'].items():
        cert=core.read_pinned(crossed.FAMILY/(phase+'-VERIFIED_COMPLETE.json'),pin)
        core.require(core.normal_exit(cert['exit']) and cert['cleanup_verified'] is True
            and cert['release_sha256']==CROSSED_SHA and cert['complete_sha256']
            ==core.sha_file(crossed.FAMILY/(phase+'-v1/STAGE_COMPLETE.json')),'crossed exit/seal differs')
        core.verify_stage(crossed.FAMILY/(phase+'-v1'),phase,CROSSED_SHA)
    for name,pin in outer['files_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe final pin')
        core.read_pinned(crossed.FAMILY/name,pin)
    for phase in ('coordinator',*PHASES):
        values=core.props(crossed.UNIT_PREFIX+'-'+phase+'.service')
        core.require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
            and values.get('Result')=='success' and values.get('ExecMainStatus')=='0'
            and values.get('SubState') in ('dead','exited'),'crossed predecessor still active or abnormal')
    for source in ORIGINS.values():
        core.require(core.sha_file(source['family']/'generation-v1/attempts.json')==source['attempts_sha256'],
                     'origin ledger drift')
    return old


def validate_release(release,old):
    core.require(release.get('routing')==routing_contract() and 'adapter_arm_map' not in release
                 and 'diagnostic' not in release,'exact routing contract required')
    core.require(release['family_path']==str(FAMILY) and release['overflow_attempts']==9,
                 'exclusive routing namespace and routed overflow count required')
    mutable={'family_path','source_sha256','diagnostic','adapter_arm_map','routing','overflow_attempts'}
    core.require({k:v for k,v in release.items() if k not in mutable}==
                 {k:v for k,v in old.items() if k not in mutable},'frozen evaluation/model/gate fields changed')
    core.require(REQUIRED<=set(release['source_sha256']),'missing routing source pins')
    for name,pin in old['source_sha256'].items():
        if name not in OBSERVER_CHANGES:
            core.require(release['source_sha256'].get(name)==pin,'original algorithm source drift: '+name)


def source_barrier(path,digest,revision=None):
    current=core.clean_source();root=Path.cwd().resolve();path=Path(path).absolute()
    core.require(root==Path(__file__).resolve().parents[1]==Path(core.__file__).resolve().parents[1]
        and path.resolve()==path and path.is_relative_to(root),'shared clean snapshot release required')
    core.require(revision is None or current==revision,'snapshot revision changed')
    release=core.load_release(path,digest)
    for name in release['source_sha256']:
        p=Path(name);core.require(not p.is_absolute() and '..' not in p.parts and p.resolve()==p.absolute(),'unsafe source pin')
    validate_release(release,verify_predecessor())
    core.require(core.sha(core.encoded(routed_inputs(release)))==PLAN_SHA,'frozen routed plan differs')
    return current,release


def generation(inputs,release,output):
    """Driver-compatible phase name; consumes CPU and never imports a model."""
    started=time.monotonic()
    ledgers={name:core.read_pinned(v['family']/'generation-v1/attempts.json',v['attempts_sha256']) for name,v in ORIGINS.items()}
    rows=assemble(inputs,ledgers,release)
    core.require(core.sha(core.encoded(inputs))==PLAN_SHA and core.sha(core.encoded(rows))==ROWS_SHA,
                 'preselection routed ledger pin differs')
    core.write_new(output/'routed-input-plan.json',inputs)
    core.write_new(output/'attempts.json',rows)
    core.write_new(output/'routing-provenance.json',dict(**routing_contract(),
        failed_slots=sum(r['attempt']['status']!='success' for r in rows),
        generated_during_this_run=0, old_private_labels_consumed=False))
    core.status_write(output/'STATUS.json',dict(phase='bank_assembly',completed_examples=320,total_examples=320,
        completed_attempts=2560,total_attempts=2560,elapsed_seconds=time.monotonic()-started,
        attempt_statuses=dict(Counter(r['attempt']['status'] for r in rows))))


def command(phase,path,digest,snapshot=None):
    cmd=BASE_COMMAND(phase,path,digest,snapshot)
    return ['scripts.run_zpd_anchored_routing' if x=='scripts.run_zpd_full_source'
            else str(PROJECT/'.runtime/fse-env/bin/python') if x==str(PROJECT/'.runtime/fse-vllm/bin/python')
            else x for x in cmd]


def summarize_private(report,digest,report_sha):
    core.require(report['execution_complete'] is True and report['full']['examples']==320
                 and report['confirmatory'] is False and report['model_promotion'] is False,
                 'complete nonconfirmatory report required')
    result=deepcopy(report)
    result.update(version=VARIANT,layout_variant=VARIANT,release_sha256=digest,
        private_report_sha256=report_sha,routing=routing_contract(),examples=320,
        counts={a:deepcopy(report['full']['results'][a]['counts']) for a in report['methods']},
        intervention_kind='current_anchored_two_slot_routing',historical_gates_passed=False,
        generated_during_this_run=0,adaptive_replay=True,
        prior_single_policy_C_reference=dict(stable_ac=209,examples=320,stable_regression=10,unknown=10,
            contemporaneous=False,gate=False),
        limitations=['Retrospective candidate-bank development on an exposed adaptive cohort.',
                    'Fixed two-slot assignment, one shared anchor; not a fresh-generation replication.',
                    'Equal adapter composition and budget across C/H/HS/U; public selection does not guarantee private correctness.',
                    'Unchanged gates; a pass does not imply model promotion, educational benefit or confirmation.'])
    return result


@contextmanager
def configured():
    overrides=dict(FAMILY=FAMILY,UNIT_PREFIX=UNIT_PREFIX,VARIANT=VARIANT,source_barrier=source_barrier,
                   command=command,summarize_private=summarize_private)
    saved={k:getattr(driver,k) for k in overrides};gen,inputs=core.generation,core.inputs_for
    for k,v in overrides.items():setattr(driver,k,v)
    core.generation,core.inputs_for=generation,routed_inputs
    try:
        with driver.configured_core():yield
    finally:
        for k,v in saved.items():setattr(driver,k,v)
        core.generation,core.inputs_for=gen,inputs


def worker(phase,path,digest):
    with configured():
        revision,_=source_barrier(path,digest);core.worker(phase,path,digest);source_barrier(path,digest,revision)


def supervise(path,digest):
    with configured():return driver.supervise(path,digest)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('command',choices=('verify','worker','supervise'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True)
    p.add_argument('--release-sha',required=True);a=p.parse_args()
    if a.command=='worker':worker(a.phase,a.release,a.release_sha)
    elif a.command=='supervise':supervise(a.release,a.release_sha)
    else:
        revision,_=source_barrier(a.release,a.release_sha)
        print(json.dumps(dict(status='verified',revision=revision,new_generation=False)))


if __name__=='__main__':main()
