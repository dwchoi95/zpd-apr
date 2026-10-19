"""Missing-only candidate and reconstruction diagnosis of the completed public-feedback revision run.

No fitting, new generation, selector change, or retry of existing vectors.
The original sealed selected results and gate remain invariant.
"""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from pathlib import Path
import subprocess

from scripts import run_zpd_anchored_diagnosis as previous
from scripts import run_zpd_public_revision as parent
from scripts import run_zpd_anchor_diagnosis as anchor_diagnosis
from scripts.zpd_revision_diagnosis import assess_slots
from scripts import run_zpd_paired_history as paired
from scripts import run_zpd_transition_missing_replay as replay
from scripts import recover_zpd_transition_evaluation as recovery
from scripts import zpd_transition_private as private
from scripts import diagnose_zpd_transition_failure as diag

core = paired.core
PROJECT = core.PROJECT
PARENT = parent.FAMILY
ROOT = PROJECT/'outputs/zpd-revision-diagnosis-20261019'
UNIT_PREFIX = 'zpd-revision-diagnosis-20261019-v1'
UNIT = UNIT_PREFIX+'-worker.service'
VERSION = 'revision_missing_candidate_diagnosis_v1'
PARENT_RELEASE = '1f7b1161bcc7a21f4eded2ef67d3063e139deebdd1e3dbd890d79feef0579e56'
PARENT_COMPLETE = '64d088693dcf9392d54954f0a6e37687489a30b5028e5d4c3575f1daed0f0515'
PHASES = core.PHASES
SELECTED = dict(C=194,H=193,HS=192,U=202)
UNKNOWN = dict(C=14,H=14,HS=14,U=14)
REGRESSIONS = dict(C=12,H=10,HS=13,U=14)
MISSING, EXISTING, CASES = 644, 1069, 53772
REQUIRED = {'scripts/zpd_revision_diagnosis.py','scripts/run_zpd_revision_diagnosis.py','tests/test_zpd_revision_diagnosis.py',
            'analysis_protocols/zpd-revision-diagnosis-20261019.md'}
BASE_COMMAND = replay.command


def verify_selected(report):
    core.require({a:report['per_arm'][a]['selected_stable_ac'] for a in diag.ARMS}==SELECTED
        and {a:report['per_arm'][a]['selected_unknown'] for a in diag.ARMS}==UNKNOWN,
        'original selected AC/unknown changed')


safety_diagnosis = anchor_diagnosis.safety_diagnosis


def load_parent(root, live=False):
    outer=core.read_pinned(root/'VERIFIED_COMPLETE.json',PARENT_COMPLETE)
    core.require(outer['status']=='complete' and outer['release_sha256']==PARENT_RELEASE
        and outer['layout_variant']==parent.VARIANT and set(outer['phases'])==set(PHASES)
        and outer['development_decision']=='hold','parent identity/gate differs')
    for phase,pin in outer['phases'].items():
        cert=core.read_pinned(root/(phase+'-VERIFIED_COMPLETE.json'),pin)
        core.require(core.normal_exit(cert['exit']) and cert['cleanup_verified'] is True
            and cert['release_sha256']==PARENT_RELEASE
            and cert['complete_sha256']==core.sha_file(root/(phase+'-v1/STAGE_COMPLETE.json')),
            'parent normal exit/hash differs')
        core.verify_stage(root/(phase+'-v1'),phase,PARENT_RELEASE)
        if live:
            group=cert['recorded_control_group']
            core.require(group.startswith('/user.slice/') and '..' not in Path(group).parts
                and group.endswith('/'+parent.UNIT_PREFIX+'-'+phase+'.service')
                and not (Path('/sys/fs/cgroup')/group.lstrip('/')).exists(),'parent child cgroup not removed')
    for name,pin in outer['files_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe parent path')
        core.read_pinned(root/name,pin)
    if live:
        core.require(core.normal_exit(core.props(parent.UNIT_PREFIX+'-coordinator.service')),
            'parent coordinator normal exit required')
        for phase in ('coordinator',*PHASES):
            values=core.props(parent.UNIT_PREFIX+'-'+phase+'.service')
            core.require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
                and values.get('Result')=='success' and values.get('ExecMainStatus')=='0'
                and values.get('SubState') in ('dead','exited'),'parent still active or abnormal')
    paths=dict(inputs='generation-v1/revision-inputs.json',attempts='generation-v1/attempts.json',
        revision_audit='generation-v1/revision-audit.json',predictions='public-v1/predictions.json',
        public_masks='public-v1/public-vectors.json',scoring='public-v1/scoring.json',
        vectors='private-v1/evaluation/vectors.json',manifest='private-v1/evaluation/manifest.json')
    loaded={k:diag._read(root/n) for k,n in paths.items()}
    loaded['pins']={n:core.sha_file(root/n) for n in paths.values()}
    core.require(loaded['pins']['generation-v1/revision-inputs.json']==
        '965357b886a32067729445d55e342c3e593b57d1ad350b6cd902252747cdc5f0'
        and loaded['pins']['generation-v1/revision-audit.json']==
        '4f9e1a7928edec8aa3151e22f7bc851c551d3ed78f7edd2eb35e7797e50e7ef6',
        'frozen preparation differs')
    loaded['vector_map']=diag.deserialize_vectors(loaded['vectors'])
    from scripts.zpd_public_candidate_selection import choose
    roster,membership,_,_,_,_=diag._inventory(loaded['inputs'],loaded['attempts'],loaded['predictions'])
    for row in loaded['predictions']:
        eid,arm,pid=row['example_id'],row['arm'],row['problem_id'];owned=membership[eid,arm]
        scores={cid:loaded['scoring'][eid][cid] for cid in owned}
        masks={cid:loaded['public_masks'][pid+'|'+cid] for cid in owned}
        cid,details=choose(scores,masks,roster[eid]['current_source_sha256'],min(scores,key=lambda c:(-scores[c],c)))
        core.require(cid==row['selected_source_sha256'] and details==row['diagnostic'],'original selector replay differs')
    loaded['report']=diag.assess(loaded['inputs'],loaded['attempts'],loaded['predictions'],loaded['vector_map'],loaded['public_masks'])
    verify_selected(loaded['report']);safety=safety_diagnosis(loaded,loaded['vector_map'])
    core.require({a:safety['per_arm'][a]['selected_regressions'] for a in diag.ARMS}==REGRESSIONS,'selected regression changed')
    loaded['report']['safety_diagnosis']=safety
    loaded['report']['slot_diagnosis']=assess_slots(loaded,loaded['vector_map'])
    return loaded


def make_bundle(loaded):
    bundle=previous.make_bundle(loaded)
    bundle['version']=VERSION
    return bundle


def prepare(output):
    loaded=load_parent(PARENT,live=True);bundle=make_bundle(loaded)
    core.require(len(bundle['tasks'])==MISSING and len(bundle['existing_task_keys'])==EXISTING
        and bundle['total_planned_case_attempts']==CASES,'fixed missing inventory differs')
    core.require(output.absolute()==ROOT/'prepared-v1' and output.resolve()==output.absolute(),'exclusive preparation path required')
    output.mkdir(parents=True,exist_ok=False)
    files={n:core.write_new(output/n,v) for n,v in [('missing-tasks.json',bundle),('report.json',loaded['report'])]}
    core.write_new(output/'COMPLETE.json',dict(status='complete',version=VERSION,files_sha256=files,
        parent_complete_sha256=PARENT_COMPLETE,execution_performed=False,model_promotion=False))
    return bundle


def validate_release(release,bundle,loaded):
    core.require(release['version']==VERSION and release['family_path']==str(ROOT)
        and release['original_release_sha256']==PARENT_RELEASE and release['original_complete_sha256']==PARENT_COMPLETE,
        'fixed diagnostic identity differs')
    core.require(release['missing_tasks']==MISSING and release['existing_tasks_reused']==EXISTING
        and release['planned_case_attempts']==CASES and release['phase_seconds']==21600 and release['examples']==320
        and release['block_workers']==[1,8,8,1] and release['unchanged_selected_stable_ac']==SELECTED
        and release['unchanged_selected_unknown']==UNKNOWN and release['unchanged_selected_regressions']==REGRESSIONS,
        'fixed diagnostic population differs')
    for key in ('new_generation','new_training','selected_choices_changed','scorer_changes','testcase_changes',
                'retry_existing_vectors','implicit_retry','overwrite','confirmatory','model_promotion'):
        core.require(release[key] is False,'diagnostic scope expanded: '+key)
    core.require(bundle==make_bundle(loaded) and release['original_vectors_sha256']==bundle['original_vectors_sha256']
        and release['expected_runtime_sha256']==bundle['expected_runtime_sha256']
        and REQUIRED<=set(release['source_sha256']),'bundle/runtime/source identity differs')


def source_barrier(_core,own_root,release,path,digest):
    core.require(Path.cwd().resolve()==own_root==Path(__file__).resolve().parents[1]
        and path.resolve()==path and path.is_relative_to(own_root),'clean shared snapshot required')
    core.clean_source();core.require(core.sha_file(path)==digest,'release drift')
    for name,pin in release['source_sha256'].items():
        p=own_root/name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts and p.resolve()==p
            and core.sha_file(p)==pin,'source drift: '+name)
    parent_release=core.read_pinned(own_root/'analysis_protocols/zpd-public-revision-release-20261019.json',PARENT_RELEASE)
    for name,pin in parent_release['source_sha256'].items():
        # Old observer fixtures now address their family by ID, not last-row position.
        if name not in ('scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'):
            core.require(release['source_sha256'].get(name)==pin,'frozen algorithm changed: '+name)
    loaded=load_parent(PARENT,live=True)
    core.require(release['bundle_path']==str(ROOT/'prepared-v1/missing-tasks.json'),'exclusive bundle required')
    bundle=core.read_pinned(release['bundle_path'],release['bundle_sha256'])
    prepared=paired.read_sealed(ROOT/'prepared-v1',release['prepared_complete_sha256'])
    core.require(prepared['parent_complete_sha256']==PARENT_COMPLETE
        and prepared['files_sha256']['missing-tasks.json']==release['bundle_sha256'],'prepared seal differs')
    validate_release(release,bundle,loaded)


def command(own_root,path,digest):
    cmd=BASE_COMMAND(own_root,path,digest)
    index=cmd.index(str(own_root/'scripts/run_zpd_transition_missing_replay.py'))
    cmd[index:index+1]=['-m','scripts.run_zpd_revision_diagnosis']
    return cmd


def finalize(_core,own_root,release,digest):
    loaded=load_parent(PARENT,live=True);replay.verify_result(core,ROOT/'run-v1',digest)
    fresh=diag._read(ROOT/'run-v1/vectors.json');vectors=diag.deserialize_vectors(loaded['vectors']+fresh)
    report=diag.assess(loaded['inputs'],loaded['attempts'],loaded['predictions'],vectors,loaded['public_masks'])
    core.require(len(fresh)==MISSING and len(vectors)==MISSING+EXISTING
        and report['coverage']['missing_unique_source_tasks']==0,'full source coverage required')
    verify_selected(report);safety=safety_diagnosis(loaded,vectors)
    core.require({a:safety['per_arm'][a]['selected_regressions'] for a in diag.ARMS}==REGRESSIONS,'selected safety changed')
    report.update(slot_diagnosis=assess_slots(loaded,vectors),diagnostic_version=VERSION,parent_complete_sha256=PARENT_COMPLETE,safety_diagnosis=safety,
        selected_choices_changed=False,original_unstable_vectors_preserved=True,original_gate='HOLD',
        claim_limit='Hindsight candidate/safety availability, not a deployable selector or measured improvement.')
    output=ROOT/'diagnosis-complete-v1';output.mkdir(exist_ok=False)
    pin=core.write_new(output/'report.json',report)
    core.write_new(output/'COMPLETE.json',dict(status='complete',report_sha256=pin,release_sha256=digest,
        worker_complete_sha256=core.sha_file(ROOT/'run-v1/COMPLETE.json'),full_source_coverage=True,
        model_promotion=False,retrospective_diagnostic=True))


@contextmanager
def configured(release):
    overrides=dict(PROJECT=PROJECT,ROOT=ROOT,ORIGINAL_OUTPUT=PARENT,UNIT=UNIT,
        VECTOR_SHA=release['original_vectors_sha256'],source_barrier=source_barrier,command=command,finalize=finalize)
    old={k:getattr(replay,k) for k in overrides}
    for k,v in overrides.items():setattr(replay,k,v)
    try:yield
    finally:
        for k,v in old.items():setattr(replay,k,v)


def supervise(own_root,release,path,digest):
    core.require(not (ROOT/'COORDINATOR.json').exists() and not (ROOT/'run-v1').exists()
        and recovery.properties(UNIT).get('LoadState')=='not-found','duplicate diagnostic forbidden')
    try:replay.supervise(core,private,recovery,own_root,release,path,digest)
    except BaseException:
        marker=ROOT/'COORDINATOR.json'
        if marker.is_file() and diag._read(marker).get('release_sha256')==digest:
            subprocess.run(['/usr/bin/systemctl','--user','stop',UNIT],check=True,timeout=30)
        raise


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('prepare','preflight','worker','supervise'))
    p.add_argument('--output',type=Path);p.add_argument('--release',type=Path);p.add_argument('--release-sha');args=p.parse_args()
    if args.mode=='prepare':
        core.clean_source();b=prepare(args.output)
        print(dict(missing_tasks=len(b['tasks']),case_attempts=b['total_planned_case_attempts']));return
    own_root=Path(__file__).resolve().parents[1];path=args.release.resolve();r=core.read_pinned(path,args.release_sha)
    source_barrier(core,own_root,r,path,args.release_sha)
    with configured(r):
        if args.mode=='supervise':supervise(own_root,r,path,args.release_sha)
        elif args.mode=='worker':replay.worker(core,private,recovery,own_root,r,path,args.release_sha)
        else:
            b=core.read_pinned(r['bundle_path'],r['bundle_sha256'])
            old=core.read_pinned(PARENT/'private-v1/evaluation/vectors.json',r['original_vectors_sha256'])
            tasks=replay.validate_tasks(b,old,MISSING);replay.recipient_memberships(b,tasks)
            core.require(private._runtime_identity()==b['expected_runtime'],'original runtime required')
            print(dict(preflight='passed',missing_tasks=MISSING,old_sources_reexecuted=0))


if __name__=='__main__':main()
