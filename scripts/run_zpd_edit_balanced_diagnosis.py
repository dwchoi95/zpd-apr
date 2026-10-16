"""Missing-only candidate/safety diagnosis of the completed balanced objective.

No fitting, new generation, selector change, or retry of existing vectors.
The original sealed selected results and gate remain invariant.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import subprocess

from scripts import run_zpd_anchored_diagnosis as previous
from scripts import run_zpd_paired_history as paired
from scripts import run_zpd_transition_missing_replay as replay
from scripts import recover_zpd_transition_evaluation as recovery
from scripts import zpd_transition_private as private
from scripts import diagnose_zpd_transition_failure as diag

core = paired.core
PROJECT = core.PROJECT
PARENT = PROJECT/'outputs/zpd-edit-balanced-20261016'
ROOT = PROJECT/'outputs/zpd-edit-balanced-diagnosis-20261017'
UNIT_PREFIX = 'zpd-edit-balanced-diagnosis-20261017-v1'
UNIT = UNIT_PREFIX+'-worker.service'
VERSION = 'edit_balanced_missing_candidate_diagnosis_v1'
PARENT_RELEASE = 'eb63d2ba4983554651c00a2ad4889c7e94c72d8dbbccc6071b1d72e5661add72'
PARENT_COMPLETE = 'e34d8affde319e3595b07c5860cbfa95e36ef0806b7c121737ad7032ffdfe31e'
PHASES = paired.PHASES[1:]
SELECTED = dict(C=195,H=200,HS=197,U=193)
UNKNOWN = dict(C=15,H=16,HS=16,U=17)
REGRESSIONS = dict(C=15,H=17,HS=17,U=25)
MISSING, EXISTING, CASES = 1071, 1089, 90024
REQUIRED = {'scripts/run_zpd_edit_balanced_diagnosis.py','tests/test_zpd_edit_balanced_diagnosis.py',
            'analysis_protocols/zpd-edit-balanced-diagnosis-20261017.md'}
BASE_COMMAND = replay.command


def verify_selected(report):
    core.require({a:report['per_arm'][a]['selected_stable_ac'] for a in diag.ARMS}==SELECTED
        and {a:report['per_arm'][a]['selected_unknown'] for a in diag.ARMS}==UNKNOWN,
        'original selected AC/unknown changed')


def safety_diagnosis(loaded, vectors):
    """Hindsight alternatives, never a public policy or a new selected result."""
    inputs, attempts, predictions = (loaded[k] for k in ('inputs','attempts','predictions'))
    roster, membership, _, sources, selected, _ = diag._inventory(inputs,attempts,predictions)
    diag._vectors(vectors,sources,roster)
    prediction={(r['example_id'],r['arm']):r for r in predictions}
    fields=('selected_regressions','selected_unknown','selected_stable_ac',
        'regression_with_known_nonnoop_safe_alternative','regression_with_known_ac_alternative',
        'regression_with_public_top_safe_alternative','regression_with_public_top_ac_alternative',
        'regression_with_unknown_nonnoop_alternative','regression_public_fallback')
    counts={a:Counter({f:0 for f in fields}) for a in diag.ARMS};rows=[]
    for eid in sorted(roster):
        r=roster[eid];pid=r['problem_id'];cur=r['current_source_sha256'];current=vectors[pid,cur]
        for arm in diag.ARMS:
            owned=membership[eid,arm];chosen=selected[eid,arm]
            evidence=diag.compare_execution(current,vectors[pid,chosen])
            regression=evidence.status=='stable' and bool(evidence.lost_testcases)
            safe=[];ac=[];unknown=[]
            for cid in sorted(owned-{cur,chosen}):
                if (pid,cid) not in vectors:unknown.append(cid);continue
                e=diag.compare_execution(current,vectors[pid,cid])
                if e.status=='unknown':unknown.append(cid)
                elif not e.lost_testcases:safe.append(cid)
                if e.status=='stable' and e.candidate_all_ac:ac.append(cid)
            public=prediction[eid,arm]['diagnostic'];top=set(public['top'])
            core.require(top<=owned,'public top outside owned candidates')
            flags=dict(selected_regressions=regression,selected_unknown=evidence.status=='unknown',
                selected_stable_ac=evidence.status=='stable' and evidence.candidate_all_ac,
                regression_with_known_nonnoop_safe_alternative=regression and bool(safe),
                regression_with_known_ac_alternative=regression and bool(ac),
                regression_with_public_top_safe_alternative=regression and bool(top&set(safe)),
                regression_with_public_top_ac_alternative=regression and bool(top&set(ac)),
                regression_with_unknown_nonnoop_alternative=regression and bool(unknown),
                regression_public_fallback=regression and public['fallback'])
            counts[arm].update({k:int(v) for k,v in flags.items()})
            rows.append(dict(example_id=eid,problem_id=pid,fold=r['fold'],arm=arm,
                selected_source_sha256=chosen,**flags,known_nonnoop_safe_alternative_ids=safe,
                known_ac_alternative_ids=ac,unknown_nonnoop_alternative_ids=unknown,
                public_top_ids=sorted(top)))
    return dict(per_arm={a:dict(c) for a,c in counts.items()},rows=rows,
        excludes_current_and_selected_from_alternatives=True,
        unknown_is_not_safe=True,retrospective_only=True,selection_changes_authorized=False)


def load_parent(root, live=False):
    outer=core.read_pinned(root/'VERIFIED_COMPLETE.json',PARENT_COMPLETE)
    core.require(outer['status']=='complete' and outer['release_sha256']==PARENT_RELEASE
        and set(outer['phases'])==set(PHASES) and outer['development_decision']=='hold', 'parent identity/gate differs')
    dynamic=core.read_pinned(root/'inference-release.json',outer['inference_release_sha256'])
    core.require(dynamic['parent_release_sha256']==PARENT_RELEASE,'dynamic parent differs')
    marker=diag._read(root/'INFERENCE_RELEASE_COMPLETE.json')
    core.require(marker['parent_release_sha256']==PARENT_RELEASE
        and marker['inference_release_sha256']==outer['inference_release_sha256'],'dynamic seal differs')
    for phase,pin in outer['phases'].items():
        expected=outer['inference_release_sha256'] if phase in core.PHASES else PARENT_RELEASE
        cert=core.read_pinned(root/(phase+'-VERIFIED_COMPLETE.json'),pin)
        core.require(core.normal_exit(cert['exit']) and cert['cleanup_verified'] is True
            and cert['parent_release_sha256']==PARENT_RELEASE and cert['release_sha256']==expected
            and cert['complete_sha256']==core.sha_file(root/(phase+'-v1/STAGE_COMPLETE.json')),
            'parent normal exit/hash differs')
        core.verify_stage(root/(phase+'-v1'),phase,expected)
    for name,pin in outer['files_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts,'unsafe parent path')
        core.read_pinned(root/name,pin)
    if live:
        for phase in ('coordinator',*PHASES):
            values=core.props('zpd-edit-balanced-20261016-v1-'+phase+'.service')
            core.require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
                and values.get('Result')=='success' and values.get('ExecMainStatus')=='0'
                and values.get('SubState') in ('dead','exited'),'parent still active or abnormal')
    paths=dict(attempts='generation-v1/attempts.json',predictions='public-v1/predictions.json',
        public_masks='public-v1/public-vectors.json',scoring='public-v1/scoring.json',
        vectors='private-v1/evaluation/vectors.json',manifest='private-v1/evaluation/manifest.json')
    loaded={k:diag._read(root/n) for k,n in paths.items()}
    core.require(dynamic['inputs_path']==str(paired.INPUTS),'frozen evaluation path differs')
    loaded['inputs']=core.read_pinned(paired.INPUTS,dynamic['inputs_sha256'])
    loaded['pins']={n:core.sha_file(root/n) for n in paths.values()}
    loaded['pins']['inputs.json']=dynamic['inputs_sha256']
    loaded['vector_map']=diag.deserialize_vectors(loaded['vectors'])
    # Recompute the original public choice without looking at supplementary labels.
    from scripts.zpd_public_candidate_selection import choose
    roster,membership,_,_,_,_=diag._inventory(loaded['inputs'],loaded['attempts'],loaded['predictions'])
    for row in loaded['predictions']:
        eid,arm,pid=row['example_id'],row['arm'],row['problem_id'];owned=membership[eid,arm]
        scores={cid:loaded['scoring'][eid][cid] for cid in owned}
        masks={cid:loaded['public_masks'][pid+'|'+cid] for cid in owned}
        cid,details=choose(scores,masks,roster[eid]['current_source_sha256'],min(scores,key=lambda c:(-scores[c],c)))
        core.require(cid==row['selected_source_sha256'] and details==row['diagnostic'],'original selector replay differs')
    loaded['report']=diag.assess(loaded['inputs'],loaded['attempts'],loaded['predictions'],loaded['vector_map'],loaded['public_masks'])
    verify_selected(loaded['report'])
    safety=safety_diagnosis(loaded,loaded['vector_map'])
    core.require({a:safety['per_arm'][a]['selected_regressions'] for a in diag.ARMS}==REGRESSIONS,'selected regression changed')
    loaded['report']['safety_diagnosis']=safety
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
    parent_release=core.read_pinned(own_root/'analysis_protocols/zpd-edit-balanced-release-20261016.json',PARENT_RELEASE)
    for name,pin in parent_release['source_sha256'].items():
        # Old observer fixtures now address their family by ID, not last-row position.
        if name not in ('scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py',
                        'tests/test_zpd_edit_balanced.py'):
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
    cmd[index:index+1]=['-m','scripts.run_zpd_edit_balanced_diagnosis']
    return cmd


def finalize(_core,own_root,release,digest):
    loaded=load_parent(PARENT,live=True);replay.verify_result(core,ROOT/'run-v1',digest)
    fresh=diag._read(ROOT/'run-v1/vectors.json');vectors=diag.deserialize_vectors(loaded['vectors']+fresh)
    report=diag.assess(loaded['inputs'],loaded['attempts'],loaded['predictions'],vectors,loaded['public_masks'])
    core.require(len(fresh)==MISSING and len(vectors)==MISSING+EXISTING
        and report['coverage']['missing_unique_source_tasks']==0,'full source coverage required')
    verify_selected(report);safety=safety_diagnosis(loaded,vectors)
    core.require({a:safety['per_arm'][a]['selected_regressions'] for a in diag.ARMS}==REGRESSIONS,'selected safety changed')
    report.update(diagnostic_version=VERSION,parent_complete_sha256=PARENT_COMPLETE,safety_diagnosis=safety,
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
