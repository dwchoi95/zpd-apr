"""Missing-only diagnosis of the sealed anchored candidate bank, not a new policy."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from pathlib import Path
import subprocess

from scripts import diagnose_zpd_transition_failure as diag
from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_transition_missing_replay as replay
from scripts import recover_zpd_transition_evaluation as recovery
from scripts import zpd_transition_private as private

PROJECT = core.PROJECT
PARENT = PROJECT / 'outputs/zpd-anchored-routing-20261016'
ROOT = PROJECT / 'outputs/zpd-anchored-diagnosis-20261016'
UNIT = 'zpd-anchored-diagnosis-20261016-v1-worker.service'
VERSION = 'anchored_missing_candidate_diagnosis_v1'
PARENT_RELEASE = 'f938bda53a6b21d63f87e44327d443eb44c8bc6344ada14c8d8e8f849472a512'
PARENT_COMPLETE = 'df62c38678618444b802d1e2a8b72b1953c9609c3c95f7f7fc28fba216c43272'
SELECTED = dict(C=200, H=194, HS=198, U=199)
UNKNOWN = dict(C=22, H=19, HS=19, U=20)
REQUIRED = {'scripts/run_zpd_anchored_diagnosis.py', 'tests/test_zpd_anchored_diagnosis.py',
            'analysis_protocols/zpd-anchored-diagnosis-20261016.md'}
OBSERVER_ONLY = {'scripts/watch_zpd_completion.py', 'tests/test_watch_zpd_completion.py',
                 'tests/test_zpd_anchored_routing.py'}
BASE_COMMAND = replay.command


def load_parent(root, live=False):
    outer = core.read_pinned(root/'VERIFIED_COMPLETE.json', PARENT_COMPLETE)
    core.require(outer['status']=='complete' and outer['release_sha256']==PARENT_RELEASE
                 and set(outer['phases'])==set(core.PHASES), 'anchored parent identity differs')
    for phase, pin in outer['phases'].items():
        cert = core.read_pinned(root/(phase+'-VERIFIED_COMPLETE.json'), pin)
        core.require(core.normal_exit(cert['exit']) and cert['cleanup_verified'] is True
                     and cert['release_sha256']==PARENT_RELEASE
                     and cert['complete_sha256']==core.sha_file(root/(phase+'-v1/STAGE_COMPLETE.json')),
                     'parent normal exit/seal absent')
        core.verify_stage(root/(phase+'-v1'), phase, PARENT_RELEASE)
    for name, pin in outer['files_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe parent path')
        core.read_pinned(root/name, pin)
    if live:
        for phase in ('coordinator', *core.PHASES):
            values = core.props('zpd-anchored-routing-20261016-v1-'+phase+'.service')
            core.require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
                         and values.get('Result')=='success' and values.get('ExecMainStatus')=='0'
                         and values.get('SubState') in ('dead','exited'), 'parent still running or abnormal')
    paths = dict(inputs='generation-v1/routed-input-plan.json', attempts='generation-v1/attempts.json',
                 predictions='public-v1/predictions.json', public_masks='public-v1/public-vectors.json',
                 vectors='private-v1/evaluation/vectors.json', manifest='private-v1/evaluation/manifest.json')
    loaded = {key:diag._read(root/name) for key,name in paths.items()}
    loaded['pins'] = {name:core.sha_file(root/name) for name in paths.values()}
    loaded['vector_map'] = diag.deserialize_vectors(loaded['vectors'])
    loaded['report'] = diag.assess(loaded['inputs'], loaded['attempts'], loaded['predictions'],
                                  loaded['vector_map'], loaded['public_masks'])
    verify_selected(loaded['report'])
    return loaded


def verify_selected(report):
    core.require({a:report['per_arm'][a]['selected_stable_ac'] for a in diag.ARMS}==SELECTED
                 and {a:report['per_arm'][a]['selected_unknown'] for a in diag.ARMS}==UNKNOWN,
                 'original selected results changed')


def make_bundle(loaded):
    roster, membership, _, sources, _, _ = diag._inventory(
        loaded['inputs'], loaded['attempts'], loaded['predictions'])
    vectors, manifest = loaded['vector_map'], loaded['manifest']
    tasks = [dict(problem_id=pid, source_sha256=cid, source=sources[pid,cid])
             for pid,cid in sorted(set(sources)-set(vectors))]
    universes = {pid:dict(universe_sha256=v.universe_sha256, case_ids=list(v.testcase_ids))
                 for (pid,_),v in vectors.items()}
    recipients = []
    for eid in sorted(roster):
        pid = roster[eid]['problem_id']
        keys = {(pid,cid) for arm in diag.ARMS for cid in membership[eid,arm]}
        recipients.append(dict(example_id=eid, problem_id=pid, task_keys=[list(k) for k in sorted(keys)],
                               missing_task_keys=[list(k) for k in sorted(keys-set(vectors))]))
    return dict(version=VERSION, missing_only=True, tasks=tasks,
        existing_task_keys=[list(k) for k in sorted(vectors)], recipients=recipients,
        total_planned_source_blocks=4*len(tasks),
        total_planned_case_attempts=4*sum(len(universes[t['problem_id']]['case_ids']) for t in tasks),
        expected_runtime=manifest['runtime'], expected_runtime_sha256=manifest['runtime_sha256'],
        testcase_pins=manifest['testcase_files_sha256'], universes=universes,
        input_sha256=diag.canonical_hash(tasks), original_selected_input_sha256=manifest['input_sha256'],
        input_files_sha256=loaded['pins'], original_vectors_sha256=loaded['pins']['private-v1/evaluation/vectors.json'],
        retrospective_diagnostic=True, generation_authorized=False, selection_changes_authorized=False,
        model_promotion=False, retry_existing_vectors=False)


def prepare(parent, output):
    loaded = load_parent(parent)
    bundle = make_bundle(loaded)
    core.require(len(bundle['tasks'])==544 and len(bundle['existing_task_keys'])==895,
                 'fixed anchored inventory differs')
    output.mkdir(parents=True, exist_ok=False)
    files = {name:core.write_new(output/name, value) for name,value in
             [('missing-tasks.json',bundle),('report.json',loaded['report'])]}
    core.write_new(output/'COMPLETE.json', dict(status='complete',version=VERSION,files_sha256=files,
        parent_complete_sha256=PARENT_COMPLETE, execution_performed=False, model_promotion=False))
    return bundle


def validate_release(release, bundle, loaded):
    core.require(release['version']==VERSION and release['family_path']==str(ROOT)
                 and release['original_release_sha256']==PARENT_RELEASE
                 and release['original_complete_sha256']==PARENT_COMPLETE,
                 'fixed diagnosis identity required')
    core.require(release['missing_tasks']==544 and release['existing_tasks_reused']==895
                 and release['phase_seconds']==21600 and release['examples']==320
                 and release['unchanged_selected_stable_ac']==SELECTED
                 and release['unchanged_selected_unknown']==UNKNOWN
                 and release['block_workers']==[1,8,8,1], 'fixed diagnostic population required')
    for key in ('new_generation','new_training','selected_choices_changed','scorer_changes','testcase_changes',
                'retry_existing_vectors','implicit_retry','overwrite','confirmatory','model_promotion'):
        core.require(release[key] is False, 'diagnostic scope expanded: '+key)
    core.require(bundle==make_bundle(loaded), 'missing-only bundle differs from original bank')
    core.require(release['original_vectors_sha256']==bundle['original_vectors_sha256']
                 and release['planned_case_attempts']==bundle['total_planned_case_attempts']
                 and release['expected_runtime_sha256']==bundle['expected_runtime_sha256']
                 and REQUIRED<=set(release['source_sha256']), 'required release pins differ')


def source_barrier(_core, own_root, release, release_path, release_sha):
    core.require(Path.cwd().resolve()==own_root==Path(__file__).resolve().parents[1]
                 and release_path.resolve()==release_path and release_path.is_relative_to(own_root),
                 'clean shared snapshot required')
    core.clean_source()
    core.require(core.sha_file(release_path)==release_sha, 'diagnostic release drift')
    for name,pin in release['source_sha256'].items():
        p = own_root/name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts
                     and p.resolve()==p and core.sha_file(p)==pin, 'source drift: '+name)
    parent_release = core.read_pinned(own_root/'analysis_protocols/zpd-anchored-routing-release-20261016.json',PARENT_RELEASE)
    for name,pin in parent_release['source_sha256'].items():
        if name not in OBSERVER_ONLY:
            core.require(release['source_sha256'].get(name)==pin, 'frozen source changed: '+name)
    loaded = load_parent(PARENT, live=True)
    core.require(release['bundle_path']==str(ROOT/'prepared-v1/missing-tasks.json'), 'exclusive bundle path required')
    bundle = core.read_pinned(release['bundle_path'], release['bundle_sha256'])
    prepared = core.read_pinned(ROOT/'prepared-v1/COMPLETE.json',release['prepared_complete_sha256'])
    core.require(prepared['status']=='complete' and prepared['parent_complete_sha256']==PARENT_COMPLETE
                 and prepared['files_sha256']['missing-tasks.json']==release['bundle_sha256'], 'prepared seal differs')
    for name,pin in prepared['files_sha256'].items():
        core.require(name in ('missing-tasks.json','report.json') and core.sha_file(ROOT/'prepared-v1'/name)==pin,
                     'prepared artifact changed')
    validate_release(release,bundle,loaded)


def command(own_root, release_path, release_sha):
    cmd = BASE_COMMAND(own_root,release_path,release_sha)
    index = cmd.index(str(own_root/'scripts/run_zpd_transition_missing_replay.py'))
    cmd[index:index+1] = ['-m','scripts.run_zpd_anchored_diagnosis']
    return cmd


def finalize(_core, own_root, release, release_sha):
    loaded = load_parent(PARENT, live=True)
    replay.verify_result(core,ROOT/'run-v1',release_sha)
    fresh = diag._read(ROOT/'run-v1/vectors.json')
    vectors = diag.deserialize_vectors(loaded['vectors']+fresh)
    report = diag.assess(loaded['inputs'],loaded['attempts'],loaded['predictions'],vectors,loaded['public_masks'])
    core.require(len(fresh)==544 and len(vectors)==1439
                 and report['coverage']['missing_unique_source_tasks']==0, 'full source coverage required')
    verify_selected(report)
    report.update(diagnostic_version=VERSION,parent_complete_sha256=PARENT_COMPLETE,
        selected_choices_changed=False, model_promotion=False, confirmatory=False,
        original_unstable_vectors_preserved=True, original_gate='HOLD',
        claim_limit='Hindsight candidate availability, not a deployable selector or measured method improvement.')
    output = ROOT/'diagnosis-complete-v1'; output.mkdir(exist_ok=False)
    digest = core.write_new(output/'report.json',report)
    core.write_new(output/'COMPLETE.json',dict(status='complete',report_sha256=digest,release_sha256=release_sha,
        worker_complete_sha256=core.sha_file(ROOT/'run-v1/COMPLETE.json'),
        full_source_coverage=True,model_promotion=False,retrospective_diagnostic=True))


@contextmanager
def configured(release):
    updates = dict(PROJECT=PROJECT,ROOT=ROOT,ORIGINAL_OUTPUT=PARENT,UNIT=UNIT,
                   VECTOR_SHA=release['original_vectors_sha256'],source_barrier=source_barrier,
                   command=command,finalize=finalize)
    before = {key:getattr(replay,key) for key in updates}
    try:
        for key,value in updates.items():setattr(replay,key,value)
        yield
    finally:
        for key,value in before.items():setattr(replay,key,value)


def supervise(own_root,release,release_path,release_sha):
    # Check before entering cleanup: never stop a unit owned by an earlier run.
    core.require(not (ROOT/'COORDINATOR.json').exists() and not (ROOT/'run-v1').exists()
                 and recovery.properties(UNIT).get('LoadState')=='not-found', 'duplicate diagnostic forbidden')
    try:
        replay.supervise(core,private,recovery,own_root,release,release_path,release_sha)
    except BaseException:
        marker = ROOT/'COORDINATOR.json'
        if marker.is_file() and diag._read(marker).get('release_sha256')==release_sha:
            subprocess.run(['/usr/bin/systemctl','--user','stop',UNIT],check=True,timeout=30)
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('mode', choices=('prepare','preflight','worker','supervise'))
    parser.add_argument('--parent', type=Path); parser.add_argument('--output',type=Path)
    parser.add_argument('--release', type=Path); parser.add_argument('--release-sha')
    args = parser.parse_args()
    if args.mode=='prepare':
        bundle = prepare(args.parent,args.output)
        print(dict(missing_tasks=len(bundle['tasks']),case_attempts=bundle['total_planned_case_attempts']))
        return
    own_root = Path(__file__).resolve().parents[1]
    path = args.release.resolve(); release = core.read_pinned(path,args.release_sha)
    source_barrier(core,own_root,release,path,args.release_sha)
    with configured(release):
        if args.mode=='supervise':supervise(own_root,release,path,args.release_sha)
        elif args.mode=='worker':replay.worker(core,private,recovery,own_root,release,path,args.release_sha)
        else:
            bundle = core.read_pinned(release['bundle_path'],release['bundle_sha256'])
            cached = core.read_pinned(PARENT/'private-v1/evaluation/vectors.json',release['original_vectors_sha256'])
            tasks = replay.validate_tasks(bundle,cached,544)
            replay.recipient_memberships(bundle,tasks)
            core.require(private._runtime_identity()==bundle['expected_runtime'], 'original runtime required')
            print(dict(preflight='passed',missing_tasks=544,old_sources_reexecuted=0))


if __name__=='__main__':main()
