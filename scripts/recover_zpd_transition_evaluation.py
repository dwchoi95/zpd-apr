"""One explicitly authorized continuation of the completed generation stage.

Run public/private workers from the ORIGINAL clean, hashed snapshot. This
outside coordinator fixes only terminal systemd collection; no generation,
retry-fill, model/scorer/protocol change, or mutation of old evidence exists.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

PROJECT = Path('/home/cdw/VSCode/zpd-apr')
ORIGINAL = PROJECT/'.runtime/transition-generation-20261012-v1'
FAMILY = PROJECT/'outputs/zpd-transition-generation-20261012'
REMAINING = ('public', 'private')
ORIGINAL_RELEASE = ORIGINAL/'analysis_protocols/zpd-transition-generation-release-20261012.json'
ORIGINAL_RELEASE_SHA = 'dba5aa43b104d0c20f056cf2a71b5bbaf96a5a6b8f939f3fcab55acafec43b59'
ORIGINAL_SOURCE_SHA = '2a35a0cf0396bb8ba26bc107d38b649364da81fbe586afa90153c2326f572b39'
ORIGINAL_REVISION = 'c439dcd75728c692868c1e9c2031bcd484c07066'
GENERATION_SHA = '0e309b224bfce72995888b02853c7e1aaa785d09000caacf154bed25b343ca6e'
SECONDS = 21600


def require(value, message):
    if not value:
        raise ValueError(message)


def properties(name):
    # Explicit `--all` distinguishes an empty, removed cgroup from no evidence.
    raw = subprocess.check_output(['/usr/bin/systemctl', '--user', 'show', '--all', name], text=True, timeout=10)
    return dict(line.split('=', 1) for line in raw.splitlines() if '=' in line)


def terminal_group(values, recorded, name, cgroup_root=Path('/sys/fs/cgroup'), uid=None):
    uid = os.getuid() if uid is None else uid
    require(values.get('Id') == name and values.get('LoadState') == 'loaded', 'wrong or unavailable terminal unit')
    require(type(recorded) is str and recorded.startswith(f'/user.slice/user-{uid}.slice/')
            and recorded.endswith('/'+name) and str(Path(recorded)) == recorded
            and '..' not in Path(recorded).parts, 'invalid recorded cgroup binding')
    require('ControlGroup' in values and values['ControlGroup'] in ('', recorded), 'terminal cgroup changed or absent evidence')
    root = cgroup_root/recorded.lstrip('/')
    if root.exists():
        require(not (root/'cgroup.procs').read_text().strip()
                and 'populated 0' in (root/'cgroup.events').read_text().splitlines(), 'worker descendants remain')
        for name in ('memory.events', 'pids.events'):
            events = dict((k, int(v)) for k, v in (line.split() for line in (root/name).read_text().splitlines()))
            require(all(v == 0 for k, v in events.items() if k != 'low'), 'terminal resource event')
    return dict(recorded_control_group=recorded, returned_control_group=values['ControlGroup'],
                cgroup_removed=not root.exists(), cleanup_verified=True)


def load_original():
    import hashlib
    path = ORIGINAL/'scripts/run_zpd_transition_generation.py'
    require(hashlib.sha256(path.read_bytes()).hexdigest() == ORIGINAL_SOURCE_SHA, 'original driver changed')
    sys.path.insert(0, str(ORIGINAL))
    spec = importlib.util.spec_from_file_location('_frozen_transition_driver', path)
    core = importlib.util.module_from_spec(spec); spec.loader.exec_module(core)
    os.chdir(ORIGINAL)
    require(core.clean_source() == ORIGINAL_REVISION, 'original snapshot changed')
    core.load_release(ORIGINAL_RELEASE, ORIGINAL_RELEASE_SHA)
    return core


def certify(core, phase, recovery_sha):
    name = core.unit(phase); values = properties(name)
    require(core.normal_exit(values), 'normal worker exit required: '+phase)
    output = FAMILY/(phase+'-v1')
    core.verify_stage(output, phase, ORIGINAL_RELEASE_SHA)
    manifest = json.loads((output/'stage-manifest.json').read_bytes())
    require(manifest['revision'] == ORIGINAL_REVISION and manifest['release_sha256'] == ORIGINAL_RELEASE_SHA,
            'worker source/release binding changed')
    group = terminal_group(values, manifest['envelope']['cgroup'], name)
    certificate = dict(status='complete', release_sha256=ORIGINAL_RELEASE_SHA,
        complete_sha256=core.sha_file(output/'STAGE_COMPLETE.json'),
        exit={k: values[k] for k in ('Result', 'ExecMainCode', 'ExecMainStatus', 'MainPID', 'SubState')},
        recovery_release_sha256=recovery_sha, systemd_properties=values, **group)
    core.write_new(FAMILY/(phase+'-VERIFIED_COMPLETE.json'), certificate)
    subprocess.run(['/usr/bin/systemctl', '--user', 'stop', name], check=True, timeout=30)
    return certificate


def command(core, phase):
    require(phase in REMAINING, 'recovery cannot launch generation')
    memory, tasks, address = core.limits(phase)
    values = dict(MemoryMax=str(memory), TasksMax=str(tasks), LimitAS=address, RuntimeMaxSec=str(SECONDS),
        KillMode='control-group', KillSignal='SIGKILL', SendSIGKILL='yes', Restart='no', OOMPolicy='stop',
        Delegate='no', RemainAfterExit='yes', MemoryAccounting='yes', TasksAccounting='yes',
        WorkingDirectory=str(ORIGINAL), StandardOutput='append:'+str(FAMILY/(phase+'.log')),
        StandardError='append:'+str(FAMILY/(phase+'.log')))
    cmd = ['/usr/bin/systemd-run', '--user', '--unit='+core.unit(phase), '--service-type=exec']
    cmd += ['--property='+k+'='+v for k, v in values.items()]
    env = dict(PYTHONDONTWRITEBYTECODE='1', TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='1',
        OPENBLAS_NUM_THREADS='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        HF_HOME=str(PROJECT/'.cache/huggingface'), TORCH_HOME=str(PROJECT/'.cache/torch'),
        XDG_CACHE_HOME=str(PROJECT/'.cache'), TRITON_CACHE_DIR=str(PROJECT/'.cache/triton'),
        TMPDIR=str(PROJECT/'.runtime/transition-tmp-20261012'))
    cmd += ['--setenv='+k+'='+v for k, v in env.items()]
    return cmd + [str(PROJECT/'.runtime/fse-env/bin/python'), '-m', 'scripts.run_zpd_transition_generation',
        'worker', '--phase', phase, '--release', str(ORIGINAL_RELEASE), '--release-sha', ORIGINAL_RELEASE_SHA]


def preflight(core, release):
    require(release['original_release_sha256'] == ORIGINAL_RELEASE_SHA
            and release['generation_complete_sha256'] == GENERATION_SHA
            and release['remaining_phases'] == list(REMAINING) and release['generation_reexecution'] is False,
            'exact continuation scope required')
    for name, pin in release['preserved_evidence_sha256'].items():
        require(Path(name).name == name and core.sha_file(FAMILY/name) == pin, 'old evidence changed: '+name)
    failure = json.loads((FAMILY/'COORDINATOR_FAILED.json').read_bytes())
    require(failure == dict(completed_phases=[], error='terminal cgroup changed', error_type='ValueError'),
            'different failure requires separate diagnosis')
    old = properties('zpd-transition-20261012-v1-coordinator.service')
    require(old.get('MainPID') == '0' and old.get('ActiveState') == 'failed'
            and old.get('Result') == 'exit-code' and old.get('ExecMainStatus') == '1', 'old coordinator state changed')
    require(core.sha_file(FAMILY/'generation-v1/STAGE_COMPLETE.json') == GENERATION_SHA, 'generation seal changed')
    core.verify_stage(FAMILY/'generation-v1', 'generation', ORIGINAL_RELEASE_SHA)
    for phase in REMAINING:
        require(not (FAMILY/(phase+'-v1')).exists()
                and properties(core.unit(phase)).get('LoadState') == 'not-found', 'later phase exists; refuse duplicate execution')
    require(not any((FAMILY/name).exists() for name in ('RECOVERY-v1.json', 'generation-VERIFIED_COMPLETE.json',
            'public-VERIFIED_COMPLETE.json', 'private-VERIFIED_COMPLETE.json', 'VERIFIED_COMPLETE.json')), 'continuation already attempted')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--release', type=Path, required=True); parser.add_argument('--release-sha', required=True)
    args = parser.parse_args()
    release_path = args.release.resolve(); own_root = Path(__file__).resolve().parents[1]
    core = load_original(); release = core.read_pinned(release_path, args.release_sha)
    for name, pin in release['recovery_source_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and core.sha_file(own_root/name) == pin, 'recovery source changed')
    preflight(core, release)
    core.write_new(FAMILY/'RECOVERY-v1.json', dict(started=time.time(), release_sha256=args.release_sha,
        original_release_sha256=ORIGINAL_RELEASE_SHA, generation_reexecution=False,
        remaining_phases=list(REMAINING), preserved_failure_sha256=release['preserved_evidence_sha256']['COORDINATOR_FAILED.json']))
    completed = []
    try:
        certify(core, 'generation', args.release_sha); completed.append('generation')
        for phase in REMAINING:
            require(not (FAMILY/(phase+'-v1')).exists()
                    and properties(core.unit(phase)).get('LoadState') == 'not-found', 'duplicate next phase')
            subprocess.run(command(core, phase), check=True, timeout=30)
            deadline = time.monotonic()+SECONDS+300
            while True:
                values = properties(core.unit(phase))
                core.status_write(FAMILY/'STATUS.json', dict(phase=phase, completed_phases=completed, checked=time.time(),
                    recovery_release_sha256=args.release_sha, unit={k: values.get(k) for k in ('Id','ActiveState','SubState','MainPID','Result')}))
                if values.get('SubState') == 'exited' or values.get('ActiveState') in ('failed', 'inactive'):
                    certify(core, phase, args.release_sha); completed.append(phase); break
                require(time.monotonic() < deadline, 'phase monitor deadline exceeded')
                time.sleep(20)
        require(core.clean_source() == ORIGINAL_REVISION, 'source changed during continuation')
        core.load_release(ORIGINAL_RELEASE, ORIGINAL_RELEASE_SHA)
        for name, pin in release['recovery_source_sha256'].items():
            require(core.sha_file(own_root/name) == pin, 'recovery source changed during continuation')
        core.status_write(FAMILY/'STATUS.json', dict(phase='complete', completed_phases=completed, checked=time.time(),
                                                   recovery_release_sha256=args.release_sha))
        core.write_new(FAMILY/'VERIFIED_COMPLETE.json', dict(status='complete', release_sha256=ORIGINAL_RELEASE_SHA,
            recovery_release_sha256=args.release_sha, prior_coordinator_failure_preserved=True,
            phases={phase: core.sha_file(FAMILY/(phase+'-VERIFIED_COMPLETE.json')) for phase in completed},
            model_promotion=False, historical_gates_passed=False, confirmatory=False))
    except BaseException as exc:
        core.write_new(FAMILY/'RECOVERY_FAILED-v1.json', dict(error_type=type(exc).__name__, error=str(exc), completed_phases=completed))
        raise


if __name__ == '__main__': main()
