"""One public-feedback-conditioned second draw; sealed first slots, unchanged gate."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path

from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_full_source as driver
from scripts import run_zpd_crossed_inference as origins
from scripts import run_zpd_anchor_diagnosis as diagnosis
from scripts import run_zpd_anchor_pilot as pilot
from scripts import run_zpd_paired_inference_recovery as ipc
from scripts import zpd_public_revision as representation
from scripts import generate_zpd_public_revision as generator

PROJECT=core.PROJECT
FAMILY=PROJECT/'outputs/zpd-public-revision-20261019'
UNIT_PREFIX='zpd-public-revision-20261019-v1'
RPC_BASE=PROJECT/'tmp/pr-1019-v1'
VARIANT=representation.VERSION
PHASES=core.PHASES
PARENT_SHA='02cd0b6dbe9a30c9e7eb0bda20035267c223e14ff43e30a1305b50ea788b7a49'
PARENT_COMPLETE='45f9fe3e4fbb059a19d836273c423bdade208956c5060f0e60c00e710b3a3ceb'
ORIGIN=ipc.FAMILY
ORIGIN_PINS={
    'generation-v1/attempts.json':'294eca31854a53d72ac30f11a0cac8f738fc78d39d1d094855bd1fcd0c7d04c7',
    'public-v1/public-vectors.json':'e6d68001bd9b340ef1ed8a5d6c0e66cb9d8d95e3dc251a0a7b03350e17b700c2',
    'public-v1/completions.jsonl':'c129df439fc4678ec8375303ac68b436464e39d64e047267fd61b636a9e7607e',
}
REQUIRED={'scripts/zpd_public_revision.py','scripts/generate_zpd_public_revision.py',
    'scripts/run_zpd_public_revision.py','tests/test_zpd_public_revision.py',
    'analysis_protocols/zpd-public-revision-20261019.md'}
OBSERVER_ONLY={'scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'}
BASE_INPUTS=core.inputs_for
BASE_COMMAND=driver.command


def contract():
    return dict(version=VARIANT,predecessor_release_sha256=PARENT_SHA,
        predecessor_complete_sha256=PARENT_COMPLETE,origin_release_sha256=origins.PREVIOUS_SHA,
        origin_complete_sha256=origins.PREVIOUS_COMPLETE,origin_files_sha256=ORIGIN_PINS,
        first_slot_reused_exactly=True,revised_slot=1,candidate_budget_per_arm=2,
        planned_new_slots=1280,existing_slots=1280,all_public_pass_still_revised=True,
        failed_first_slot_preserved=True,unavailable_feedback_not_failure=True,
        full_original_history_preserved=True,private_feedback_used=False,
        fitting=False,selector_changed=False,gate_changed=False,model_promotion=False,
        adaptive_development=True,rpc_base_path=str(RPC_BASE))


def public_inputs(release):
    """Only original prompts, generated sources and public executions enter here."""
    old=BASE_INPUTS(release)
    data={n:core.read_pinned(ORIGIN/n,pin) for n,pin in ORIGIN_PINS.items()}
    return representation.transform(old,data['generation-v1/attempts.json'],
        data['public-v1/public-vectors.json'],data['public-v1/completions.jsonl'])


def inputs_for(release):
    plan,_=public_inputs(release)
    core.require(core.sha(core.encoded(plan))==release['revision_inputs_sha256'], 'frozen revision plan drift')
    return plan


def predecessor():
    from scripts.watch_zpd_completion import verify_terminal
    outer=core.read_pinned(diagnosis.ROOT/'VERIFIED_COMPLETE.json',PARENT_COMPLETE)
    core.require(outer['release_sha256']==PARENT_SHA,'diagnosis release differs')
    verify_terminal(diagnosis.ROOT,outer)
    p=core.props(diagnosis.UNIT_PREFIX+'-coordinator.service')
    core.require(core.normal_exit(p) and p.get('ControlGroup')=='','diagnosis coordinator not released')
    cert=core.read_pinned(diagnosis.ROOT/'WORKER_VERIFIED_COMPLETE.json',outer['worker_certificate_sha256'])
    pilot.released(cert,diagnosis.UNIT,PARENT_SHA)
    core.require(not list(diagnosis.ROOT.rglob('*FAILED*.json')),'diagnosis failure marker')
    original=core.inputs_for
    core.inputs_for=BASE_INPUTS
    try:return origins.verify_predecessor()
    finally:core.inputs_for=original


def validate_release(release,old,latest):
    core.require(release.get('public_revision')==contract() and release['family_path']==str(FAMILY)
        and release['layout_variant']==VARIANT and 'recovery' not in release,'exact revision amendment required')
    mutable={'family_path','layout_variant','source_sha256','recovery','public_revision',
        'tokenization_sha256','revision_inputs_sha256','revision_audit_sha256','overflow_attempts'}
    core.require({k:v for k,v in release.items() if k not in mutable}==
        {k:v for k,v in old.items() if k not in mutable},'frozen model/scientific fields changed')
    core.require(REQUIRED<=set(release['source_sha256']),'missing revision source pins')
    for n,pin in latest['source_sha256'].items():
        if n not in OBSERVER_ONLY:core.require(release['source_sha256'].get(n)==pin,'existing source changed: '+n)


def source_barrier(path,digest,revision=None):
    current=core.clean_source();root=Path.cwd().resolve();path=Path(path).absolute()
    core.require(root==Path(__file__).resolve().parents[1]==Path(core.__file__).resolve().parents[1]
        and path.resolve()==path and path.is_relative_to(root),'clean shared snapshot release required')
    core.require(revision is None or current==revision,'snapshot revision drift')
    r=core.load_release(path,digest)
    for n in r['source_sha256']:
        p=Path(n);core.require(not p.is_absolute() and '..' not in p.parts and p.resolve()==p.absolute(),'unsafe source path')
    latest=core.read_pinned(root/'analysis_protocols/zpd-anchor-diagnosis-release-20261019.json',PARENT_SHA)
    validate_release(r,predecessor(),latest)
    ipc.parent.read_sealed(ipc.parent.INPUTS.parent,r['inputs_complete_sha256'])
    plan,audit=public_inputs(r)
    core.require(core.sha(core.encoded(plan))==r['revision_inputs_sha256']
        and core.sha(core.encoded(audit))==r['revision_audit_sha256'],'revision preparation drift')
    ipc.validate_rpc_path(RPC_BASE)
    return current,r


def generation(inputs,release,output):
    plan,audit=public_inputs(release);core.require(inputs==plan,'generation input differs')
    ledger=core.read_pinned(ORIGIN/'generation-v1/attempts.json',ORIGIN_PINS['generation-v1/attempts.json'])
    reused={r['attempt_id']:r for r in ledger if r['draw_index']==0}
    core.write_new(output/'revision-inputs.json',inputs);core.write_new(output/'revision-audit.json',audit)
    generator.generation(inputs,release,output,reused)


def command(phase,path,digest,snapshot=None):
    cmd=BASE_COMMAND(phase,path,digest,snapshot)
    cmd=['scripts.run_zpd_public_revision' if v=='scripts.run_zpd_full_source' else
         '--setenv=TMPDIR='+str(RPC_BASE) if v.startswith('--setenv=TMPDIR=') else v for v in cmd]
    cmd.insert(cmd.index(str(PROJECT/('.runtime/fse-vllm/bin/python' if phase=='generation' else '.runtime/fse-env/bin/python'))),
        '--setenv=VLLM_RPC_BASE_PATH='+str(RPC_BASE))
    return cmd


def summarize_private(report,digest,report_sha):
    core.require(report['execution_complete'] is True and report['full']['examples']==320,'complete 320 required')
    result=deepcopy(report)
    result.update(version=VARIANT,layout_variant=VARIANT,release_sha256=digest,private_report_sha256=report_sha,
        public_revision=contract(),examples=320,counts={a:deepcopy(report['full']['results'][a]['counts']) for a in report['methods']},
        model_promotion=False,historical_gates_passed=False,confirmatory=False,educational_benefit_established=False,
        prior_uniform_full_source_reference=dict(C=209,H=192,HS=198,U=206,examples=320,contemporaneous=False),
        limitations=['Adaptive exposed development cohort; no confirmatory or educational claim.',
            'First-slot sources and public feedback reused exactly; second slots generated in a later run block.',
            'Same two-candidate budget, but changed input length and public-feedback use; not compute-identical.',
            'Public sample agreement is not private correctness; all unknowns, overflows and gates retained.'])
    return result


@contextmanager
def configured():
    updates=dict(FAMILY=FAMILY,UNIT_PREFIX=UNIT_PREFIX,VARIANT=VARIANT,source_barrier=source_barrier,
        command=command,summarize_private=summarize_private)
    saved={k:getattr(driver,k) for k in updates};old=(core.inputs_for,core.generation)
    for k,v in updates.items():setattr(driver,k,v)
    core.inputs_for,core.generation=inputs_for,generation
    try:
        with driver.configured_core():yield
    finally:
        core.inputs_for,core.generation=old
        for k,v in saved.items():setattr(driver,k,v)


def worker(phase,path,digest):
    with configured():
        revision,_=source_barrier(path,digest)
        if phase=='generation':
            old=ipc.RPC_BASE;ipc.RPC_BASE=RPC_BASE
            try:core.write_new(FAMILY/'IPC_PREFLIGHT.json',ipc.probe_ipc())
            finally:ipc.RPC_BASE=old
        core.worker(phase,path,digest);source_barrier(path,digest,revision)


def supervise(path,digest):
    with configured():
        source_barrier(path,digest)
        core.require(not FAMILY.exists() and not RPC_BASE.exists(),'fresh family/IPC required')
        for phase in PHASES:core.require(core.props(driver.unit(phase)).get('LoadState')=='not-found','duplicate unit')
        RPC_BASE.mkdir(parents=True,mode=0o700)
        return driver.supervise(path,digest)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('verify','tokenize','worker','supervise'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha',required=True)
    a=p.parse_args()
    if a.mode=='tokenize':
        r=core.read_pinned(a.release,a.release_sha);plan,audit=public_inputs(r)
        rendered,report=core.render_inputs(plan,r['base_model'])
        print(json.dumps(dict(tokenization_sha256=core.sha(core.encoded(report)),
            revision_inputs_sha256=core.sha(core.encoded(plan)),revision_audit_sha256=core.sha(core.encoded(audit)),
            arms=report['arms'],feedback=audit['counts'],overflow_attempts=sum(not rendered[t['prompt_id']]['fits'] for t in plan['attempts']))))
    elif a.mode=='worker':worker(a.phase,a.release,a.release_sha)
    elif a.mode=='supervise':supervise(a.release,a.release_sha)
    else:print(json.dumps(dict(verified_revision=source_barrier(a.release,a.release_sha)[0])))


if __name__=='__main__':main()
