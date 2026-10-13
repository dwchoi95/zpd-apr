"""Missing-only full-suite diagnostic replay; no generation or policy changes.

Execute only source keys absent from the certified selected-source cache, under
the same frozen runner/universe/runtime contract. The new orchestration is
separately sealed. Existing vectors and selected choices are never overwritten.
"""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PROJECT = Path('/home/cdw/VSCode/zpd-apr')
ORIGINAL = PROJECT/'.runtime/transition-generation-20261012-v1'
ORIGINAL_OUTPUT = PROJECT/'outputs/zpd-transition-generation-20261012'
ROOT = PROJECT/'outputs/zpd-transition-diagnosis-20261013'
UNIT = 'zpd-transition-missing-20261013-v1.service'
SECONDS = 21600
VECTOR_SHA = '55ec803749b985627999198b4e93efc43381cdde66cb3de1e71b79262e98ea8c'


def require(value, message):
    if not value:
        raise ValueError(message)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def frozen(own_root):
    recovery = load_module('_replay_terminal_checks', own_root/'scripts/recover_zpd_transition_evaluation.py')
    core = recovery.load_original()
    from scripts import zpd_transition_private as private
    require(Path(private.__file__).resolve() == ORIGINAL/'scripts/zpd_transition_private.py', 'frozen private implementation required')
    return core, private, recovery


def source_barrier(core, own_root, release, release_path, release_sha):
    require(core.sha_file(release_path) == release_sha, 'supplement release changed')
    require(core.clean_source() == 'c439dcd75728c692868c1e9c2031bcd484c07066', 'original snapshot changed')
    for name, pin in release['source_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and core.sha_file(own_root/name) == pin, 'supplement source changed: '+name)


def envelope(recovery):
    values = recovery.properties(UNIT)
    expected = dict(Id=UNIT, LoadState='loaded', ActiveState='active', SubState='running',
        MainPID=str(os.getpid()), MemoryMax=str(32*2**30), TasksMax='128', LimitAS=str(32*2**30),
        KillMode='control-group', KillSignal='9', SendSIGKILL='yes', Restart='no', OOMPolicy='stop',
        Type='exec', Delegate='no', RemainAfterExit='yes', MemoryAccounting='yes', TasksAccounting='yes')
    require(all(values.get(k) == v for k, v in expected.items()), 'effective replay envelope differs')
    from scripts.zpd_statement_sample_host import _seconds
    require(_seconds(values['RuntimeMaxUSec']) == SECONDS, 'fixed replay wall bound required')
    groups = [line.split(':', 2)[2] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::')]
    require(len(groups) == 1 and groups[0] == values['ControlGroup']
            and groups[0].endswith('/'+UNIT) and groups[0].startswith(f'/user.slice/user-{os.getuid()}.slice/'), 'bound replay cgroup required')
    root = Path('/sys/fs/cgroup')/groups[0].lstrip('/')
    require((root/'memory.max').read_text().strip() == str(32*2**30)
            and (root/'pids.max').read_text().strip() == '128', 'aggregate bounds differ')
    events = {name: dict((k, int(v)) for k, v in (line.split() for line in (root/name).read_text().splitlines()))
              for name in ('memory.events', 'pids.events')}
    require(all(v == 0 for d in events.values() for k, v in d.items() if k != 'low'), 'aggregate resource event')
    return dict(cgroup=groups[0], properties=expected, events=events)


def validate_tasks(bundle, cached_rows, expected_tasks=788):
    """No empirical code runs; reject duplicate, cached, changed, foreign tasks."""
    old = {(r['problem_id'], r['vector']['source_sha256']) for r in cached_rows}
    require(len(old) == len(cached_rows), 'duplicate existing vector identity')
    require(bundle['original_vectors_sha256'] == VECTOR_SHA, 'original vector pin differs')
    supplied_old = [tuple(k) for k in bundle['existing_task_keys']]
    require(len(supplied_old) == len(old) and set(supplied_old) == old, 'cached source inventory differs')
    tasks = {}
    for row in bundle['tasks']:
        pid, cid = row['problem_id'], row['source_sha256']
        require(pid in bundle['universes'] and type(row['source']) is str, 'problem-bound exact source required')
        raw = row['source'].encode('utf-8', errors='strict')
        require(hashlib.sha256(raw).hexdigest() == cid, 'missing source SHA differs')
        key = pid, cid
        require(key not in old and key not in tasks, 'cached or duplicate source would be reexecuted')
        tasks[key] = raw
    require(len(tasks) == expected_tasks, 'exact fixed missing source population required')
    return tasks


def recipient_memberships(bundle, tasks, expected_examples=320):
    old = {tuple(k) for k in bundle['existing_task_keys']}
    result = {}
    for row in bundle['recipients']:
        eid = row['example_id']
        all_keys = {tuple(k) for k in row['task_keys']}
        missing = {tuple(k) for k in row['missing_task_keys']}
        require(eid not in result and all_keys and all(k[0] == row['problem_id'] for k in all_keys),
                'unique problem-bound recipient required')
        require(all_keys <= old | set(tasks) and missing == all_keys - old,
                'exact recipient missing-source membership required')
        result[eid] = missing
    require(len(result) == expected_examples and set().union(*result.values()) == set(tasks),
            'complete recipient/source coverage required')
    return result


def worker(core, private, recovery, own_root, release, release_path, release_sha):
    from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector, canonical_hash
    output = ROOT/'run-v1'; require(not output.exists(), 'fresh replay output required')
    bundle = core.read_pinned(release['bundle_path'], release['bundle_sha256'])
    cached = core.read_pinned(ORIGINAL_OUTPUT/'private-v1/evaluation/vectors.json', VECTOR_SHA)
    tasks = validate_tasks(bundle, cached, release['missing_tasks'])
    missing_per_example = recipient_memberships(bundle, tasks)
    state = envelope(recovery)
    runtime = private._runtime_identity()
    require(runtime == bundle['expected_runtime'] and canonical_hash(runtime) == bundle['expected_runtime_sha256'],
            'same frozen execution context required; do not relabel different runtimes')
    cases, universes = private._read_cases(PROJECT/'data', bundle['testcase_pins'])
    for pid, expected in bundle['universes'].items():
        require(universes[pid] == expected['universe_sha256']
                and [c.case_id for c in cases[pid]] == expected['case_ids'], 'cached testcase universe differs')
    planned_cases = 4*sum(len(cases[pid]) for pid, _ in tasks)
    require(planned_cases == release['planned_case_attempts'] == bundle['total_planned_case_attempts']
            and 4*len(tasks) == bundle['total_planned_source_blocks'], 'fixed testcase budget differs')
    output.mkdir(parents=True); records = {key: [] for key in tasks}
    started = time.monotonic(); deadline = started+SECONDS; completed_cases = completed_blocks = 0
    # The fixed memberships expose only source IDs, never new choice decisions.
    def status():
        done = {key for key, blocks in records.items() if len(blocks) == 4}
        return dict(phase='missing_candidate_replay', completed_examples=sum(keys <= done for keys in missing_per_example.values()),
            total_examples=320, completed_unique_sources=len(done), total_unique_sources=len(tasks),
            completed_case_attempts=completed_cases, total_case_attempts=planned_cases,
            completed_source_blocks=completed_blocks, total_source_blocks=4*len(tasks), elapsed_seconds=time.monotonic()-started)
    try:
        core.write_new(output/'manifest.json', dict(release_sha256=release_sha, bundle_sha256=release['bundle_sha256'],
            existing_vectors_sha256=VECTOR_SHA, runtime=runtime, runtime_sha256=canonical_hash(runtime),
            envelope=state, started=time.time(), missing_only=True, original_vectors_overwritten=False,
            selected_choices_changed=False, tasks=[dict(problem_id=pid, source_sha256=cid) for pid,cid in tasks],
            source_sha256=release['source_sha256']))
        core.status_write(output/'STATUS.json', status())
        with (output/'completions.jsonl').open('xb') as journal:
            for index, workers in enumerate((1,8,8,1)):
                remaining = iter(tasks); pending = {}
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    def submit():
                        key = next(remaining, None)
                        if key is not None:
                            pending[pool.submit(private.evaluator.run_source, private.evaluator.SandboxRunner(),
                                tasks[key], cases[key[0]], deadline)] = key
                    for _ in range(workers): submit()
                    while pending:
                        require(time.monotonic() < deadline, 'missing replay wall bound exceeded'); envelope(recovery)
                        done, _ = wait(pending, timeout=10, return_when=FIRST_COMPLETED)
                        for future in done:
                            key = pending.pop(future); outcomes, details, complete = future.result()
                            require(complete, 'incomplete source replay; no synthetic failure fill')
                            block = ExecutionBlock(workers, universes[key[0]], canonical_hash(runtime), tuple(outcomes), True, key[1])
                            records[key].append(block)
                            journal.write(core.encoded(dict(problem_id=key[0], source_sha256=key[1], block_index=index,
                                block=asdict(block), cases=details))); journal.flush(); os.fsync(journal.fileno())
                            completed_cases += len(outcomes); completed_blocks += 1; submit()
                        core.status_write(output/'STATUS.json', status())
        require(completed_cases == planned_cases and completed_blocks == 4*len(tasks), 'incomplete planned work')
        vectors = []
        for (pid,cid), blocks in records.items():
            v = ExecutionVector(cid, universes[pid], canonical_hash(runtime), tuple(c.case_id for c in cases[pid]), tuple(blocks))
            vectors.append(dict(problem_id=pid, vector=asdict(v), vector_sha256=v.seal_sha256))
        core.write_new(output/'vectors.json', vectors)
        require(private._runtime_identity() == runtime, 'execution context changed during replay')
        for relative, pin in bundle['testcase_pins'].items():
            require(core.sha_file(PROJECT/'data'/relative) == pin, 'testcase drift')
        require(core.sha_file(ORIGINAL_OUTPUT/'private-v1/evaluation/vectors.json') == VECTOR_SHA, 'old vectors changed')
        envelope(recovery); source_barrier(core, own_root, release, release_path, release_sha)
        require(core.sha_file(Path(release['bundle_path'])) == release['bundle_sha256'], 'bundle drift')
        core.status_write(output/'STATUS.json', {**status(), 'phase':'complete'})
        files = {p.name:core.sha_file(p) for p in output.iterdir() if p.is_file()}
        core.write_new(output/'COMPLETE.json', dict(status='complete', files_sha256=files, release_sha256=release_sha,
            missing_sources=len(tasks), examples=320, case_attempts=planned_cases, provisional_until_normal_exit=True))
    except BaseException as exc:
        core.write_new(output/'FAILED.json', dict(error_type=type(exc).__name__, error=str(exc), valid=False))
        raise


def verify_result(core, output, release_sha):
    result = json.loads((output/'COMPLETE.json').read_bytes())
    require(result['status'] == 'complete' and result['release_sha256'] == release_sha, 'result release differs')
    files = result['files_sha256']
    require(set(files) == {'manifest.json','completions.jsonl','vectors.json','STATUS.json'}
            and {p.name for p in output.iterdir()} == set(files)|{'COMPLETE.json'}, 'replay artifact inventory differs')
    for name, pin in files.items(): require(core.sha_file(output/name) == pin, 'replay artifact drift: '+name)
    return result


def command(own_root, release_path, release_sha):
    values = dict(MemoryMax=str(32*2**30), TasksMax='128', LimitAS=str(32*2**30), RuntimeMaxSec=str(SECONDS),
        KillMode='control-group', KillSignal='SIGKILL', SendSIGKILL='yes', Restart='no', OOMPolicy='stop',
        Delegate='no', RemainAfterExit='yes', MemoryAccounting='yes', TasksAccounting='yes',
        WorkingDirectory=str(own_root), StandardOutput='append:'+str(ROOT/'worker.log'), StandardError='append:'+str(ROOT/'worker.log'))
    cmd = ['/usr/bin/systemd-run','--user','--unit='+UNIT,'--service-type=exec']
    cmd += ['--property='+k+'='+v for k,v in values.items()]
    cmd += ['--setenv='+k+'='+v for k,v in dict(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1').items()]
    return cmd+[str(PROJECT/'.runtime/fse-env/bin/python'), str(own_root/'scripts/run_zpd_transition_missing_replay.py'),
        'worker','--release',str(release_path),'--release-sha',release_sha]


def finalize(core, own_root, release, release_sha):
    """Retrospective diagnosis only, after successful execution certification."""
    diag = load_module('_completed_transition_diagnosis', own_root/'scripts/diagnose_zpd_transition_failure.py')
    inputs = core.read_pinned(PROJECT/'outputs/zpd-transition-inputs-20261012-v1/inputs.json', release['inputs_sha256'])
    core.verified_dependency('generation', 'dba5aa43b104d0c20f056cf2a71b5bbaf96a5a6b8f939f3fcab55acafec43b59')
    core.verified_dependency('public', 'dba5aa43b104d0c20f056cf2a71b5bbaf96a5a6b8f939f3fcab55acafec43b59')
    core.verified_dependency('private', 'dba5aa43b104d0c20f056cf2a71b5bbaf96a5a6b8f939f3fcab55acafec43b59')
    attempts = json.loads((ORIGINAL_OUTPUT/'generation-v1/attempts.json').read_bytes())
    predictions = json.loads((ORIGINAL_OUTPUT/'public-v1/predictions.json').read_bytes())
    cached = core.read_pinned(ORIGINAL_OUTPUT/'private-v1/evaluation/vectors.json', VECTOR_SHA)
    fresh = json.loads((ROOT/'run-v1/vectors.json').read_bytes())
    # Diagnose uses every original choice unchanged; the hindsight oracle is not a new method.
    vector_map = diag.deserialize_vectors(cached+fresh)
    report = diag.assess(inputs, attempts, predictions, vector_map)
    require(len(fresh) == release['missing_tasks'] and len(vector_map) == len(cached)+len(fresh)
            and report['coverage']['missing_unique_source_tasks'] == 0, 'full diagnostic source coverage required')
    require({a: report['per_arm'][a]['selected_stable_ac'] for a in diag.ARMS}
            == release['unchanged_selected_stable_ac'], 'original selected results changed')
    output = ROOT/'diagnosis-complete-v1'; output.mkdir(exist_ok=False)
    digest = core.write_new(output/'report.json', report)
    core.write_new(output/'COMPLETE.json', dict(status='complete', report_sha256=digest, release_sha256=release_sha,
        worker_complete_sha256=core.sha_file(ROOT/'run-v1/COMPLETE.json'),
        full_source_coverage=True, model_promotion=False, retrospective_diagnostic=True))


def supervise(core, private, recovery, own_root, release, release_path, release_sha):
    require(not (ROOT/'run-v1').exists() and not (ROOT/'COORDINATOR.json').exists()
            and recovery.properties(UNIT).get('LoadState') == 'not-found', 'duplicate supplementary replay forbidden')
    core.write_new(ROOT/'COORDINATOR.json', dict(started=time.time(), release_sha256=release_sha, retries=0))
    try:
        subprocess.run(command(own_root,release_path,release_sha), check=True, timeout=30)
        deadline = time.monotonic()+SECONDS+300
        while True:
            values = recovery.properties(UNIT)
            core.status_write(ROOT/'MONITOR_STATUS.json', dict(phase='monitoring', checked=time.time(),
                unit={k:values.get(k) for k in ('Id','ActiveState','SubState','MainPID','Result')}))
            if values.get('SubState') == 'exited' or values.get('ActiveState') in ('failed','inactive'):
                require(core.normal_exit(values), 'supplement worker did not exit normally')
                verify_result(core, ROOT/'run-v1', release_sha)
                manifest = json.loads((ROOT/'run-v1/manifest.json').read_bytes())
                group = recovery.terminal_group(values, manifest['envelope']['cgroup'], UNIT)
                core.write_new(ROOT/'WORKER_VERIFIED_COMPLETE.json', dict(status='complete', release_sha256=release_sha,
                    complete_sha256=core.sha_file(ROOT/'run-v1/COMPLETE.json'),
                    exit={k:values[k] for k in ('Result','ExecMainCode','ExecMainStatus','MainPID','SubState')}, **group))
                subprocess.run(['/usr/bin/systemctl','--user','stop',UNIT], check=True, timeout=30)
                source_barrier(core, own_root, release, release_path, release_sha)
                finalize(core, own_root, release, release_sha)
                source_barrier(core, own_root, release, release_path, release_sha)
                core.status_write(ROOT/'MONITOR_STATUS.json', dict(phase='complete', checked=time.time()))
                core.write_new(ROOT/'VERIFIED_COMPLETE.json', dict(status='complete', release_sha256=release_sha,
                    worker_certificate_sha256=core.sha_file(ROOT/'WORKER_VERIFIED_COMPLETE.json'),
                    diagnosis_complete_sha256=core.sha_file(ROOT/'diagnosis-complete-v1/COMPLETE.json'),model_promotion=False))
                return
            require(time.monotonic() < deadline, 'supplement monitor deadline'); time.sleep(20)
    except BaseException as exc:
        core.write_new(ROOT/'MONITOR_FAILED.json', dict(error_type=type(exc).__name__, error=str(exc)))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('mode', choices=('worker','supervise','preflight'))
    parser.add_argument('--release',type=Path,required=True); parser.add_argument('--release-sha',required=True)
    args = parser.parse_args(); own_root = Path(__file__).resolve().parents[1]; release_path = args.release.resolve()
    core,private,recovery = frozen(own_root); release = core.read_pinned(release_path,args.release_sha)
    require(release['missing_tasks'] == 788 and release['phase_seconds'] == SECONDS
            and release['new_generation'] is False and release['selected_choices_changed'] is False,
            'fixed diagnostic scope required')
    source_barrier(core,own_root,release,release_path,args.release_sha)
    if args.mode == 'worker': worker(core,private,recovery,own_root,release,release_path,args.release_sha)
    elif args.mode == 'supervise': supervise(core,private,recovery,own_root,release,release_path,args.release_sha)
    else:
        bundle = core.read_pinned(release['bundle_path'],release['bundle_sha256'])
        cached = core.read_pinned(ORIGINAL_OUTPUT/'private-v1/evaluation/vectors.json',VECTOR_SHA)
        tasks = validate_tasks(bundle,cached,release['missing_tasks'])
        recipient_memberships(bundle,tasks)
        require(private._runtime_identity() == bundle['expected_runtime'], 'runtime changed before launch')
        print(json.dumps(dict(preflight='passed',missing_tasks=788,old_sources_reexecuted=0)))


if __name__ == '__main__': main()
