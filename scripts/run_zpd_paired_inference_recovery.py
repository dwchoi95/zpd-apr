"""One prospective IPC-path amendment; reuse sealed C/H training, never refit.

The failed family remains immutable. The unchanged mixed-adapter generator and
public/private algorithms execute in a new, exclusive three-phase namespace.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path

from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_full_source as driver
from scripts import run_zpd_paired_history as parent
from scripts.generate_zpd_paired_history import generation

PROJECT = core.PROJECT
FAMILY = PROJECT / 'outputs/zpd-paired-inference-20261016'
UNIT_PREFIX = 'zpd-paired-inference-20261016-v1'
RPC_BASE = PROJECT / 'tmp/pi-1016-v1'
PARENT_SHA = '2323a878e1dad79ac8bbfde048581670ca8de8c3280f6903433c8edf09b3036b'
INFERENCE_SHA = '6ae6d0fdfecad299b2d0501cdef8413c47e0938091e9e8a7f034fbd487484d47'
FAILURE_SHA = '02c54b93f6dfb849e6d42abe2adca0d4814f00f2cb6312b2c6022d3010de526c'
COORDINATOR_FAILURE_SHA = '3142ba4f6ff74895ce8ae30415bc339a957decc989fd462cdc655c557288515d'
PHASES = core.PHASES
VARIANT = 'paired_history_ipc_recovery_v1'
BASE_COMMAND = driver.command
REQUIRED = {'scripts/run_zpd_paired_inference_recovery.py',
            'scripts/run_zpd_full_source.py', 'scripts/generate_zpd_paired_history.py',
            'scripts/run_zpd_paired_history.py', 'scripts/run_zpd_transition_generation.py',
            'scripts/recover_zpd_transition_evaluation.py', 'scripts/zpd_transition_private.py',
            'tests/test_zpd_paired_inference_recovery.py'}


def amendment():
    return dict(version=VARIANT, parent_family=str(parent.FAMILY),
        parent_release_sha256=PARENT_SHA, parent_inference_sha256=INFERENCE_SHA,
        failure_sha256=FAILURE_SHA, coordinator_failure_sha256=COORDINATOR_FAILURE_SHA,
        rpc_base_path=str(RPC_BASE), training_reused=True, generated_attempts_before_failure=0,
        training_repeated=False, retry_of_failed_family=False, scientific_changes=False)


def validate_amendment(release, previous):
    core.require(release.get('recovery') == amendment(), 'exact IPC amendment required')
    core.require(release['family_path'] == str(FAMILY) and release['phases'] == list(PHASES),
                 'new evaluation-only namespace required')
    mutable = {'family_path', 'phases', 'source_sha256', 'recovery'}
    core.require({k:v for k,v in release.items() if k not in mutable}
                 == {k:v for k,v in previous.items() if k not in mutable},
                 'scientific inference contract changed')
    core.require(REQUIRED <= set(release['source_sha256']), 'missing recovery source pins')
    # Only observer integration changes existing source bytes. Training,
    # generation, scoring, evaluation, and their tests must retain old pins.
    for name, pin in previous['source_sha256'].items():
        if name not in {'scripts/watch_zpd_completion.py', 'tests/test_watch_zpd_completion.py'}:
            core.require(release['source_sha256'].get(name) == pin, 'original algorithm pin changed: ' + name)


def validate_rpc_path(path, project=PROJECT):
    path = Path(path)
    core.require(path.is_absolute() and path.resolve() == path and path.is_relative_to(project / 'tmp'),
                 'canonical in-project IPC directory required')
    candidate = path / '00000000-0000-0000-0000-000000000000'
    core.require(len(os.fsencode(candidate)) <= 107, 'IPC socket path exceeds Linux byte limit')
    return path


def verify_parent():
    previous = core.read_pinned(parent.FAMILY / 'inference-release.json', INFERENCE_SHA)
    marker = json.loads((parent.FAMILY / 'INFERENCE_RELEASE_COMPLETE.json').read_bytes())
    core.require(marker['status'] == 'complete' and marker['parent_release_sha256'] == PARENT_SHA
                 and marker['inference_release_sha256'] == INFERENCE_SHA, 'parent inference binding differs')
    core.read_pinned(previous['parent_release_path'], PARENT_SHA)
    failure = core.read_pinned(parent.FAMILY / 'generation-v1/FAILED.json', FAILURE_SHA)
    core.require(failure['error_type'] == 'ZMQError' and 'longer than 107' in failure['error'],
                 'different failure requires a separate amendment')
    stopped = core.read_pinned(parent.FAMILY / 'COORDINATOR_FAILED.json', COORDINATOR_FAILURE_SHA)
    core.require(stopped['completed_phases'] == list(parent.PHASES[:5])
                 and stopped['exact_unit_cleanup'] == {'generation': 'stop_completed'},
                 'failed generation cleanup differs')
    files = {str(p.relative_to(parent.FAMILY / 'generation-v1'))
             for p in (parent.FAMILY / 'generation-v1').rglob('*') if p.is_file()}
    core.require(files == {'FAILED.json', 'stage-manifest.json', 'tokenization.json'}
                 and not (parent.FAMILY / 'generation-v1/attempts').exists()
                 and not (parent.FAMILY / 'public-v1').exists()
                 and not (parent.FAMILY / 'private-v1').exists(), 'prior generation/evaluation already attempted')
    for phase in parent.PHASES[:5]:
        parent.verified_dependency(phase, PARENT_SHA)
    summaries = parent.verify_training_pair(PARENT_SHA)
    for arm in ('C', 'H'):
        core.require(core.sha_file(parent.FAMILY / ('train-' + arm + '-VERIFIED_COMPLETE.json'))
                     == previous['training_certificates_sha256'][arm], 'training certificate pin differs')
        core.require(previous['adapter_' + arm] == str(parent.FAMILY / ('train-' + arm + '-v1/training/adapter')),
                     'sealed original adapter required')
    for phase in ('coordinator', *parent.PHASES):
        values = core.props(parent.UNIT_PREFIX + '-' + phase + '.service')
        core.require(values.get('MainPID') == '0' and values.get('ControlGroup') == ''
                     and values.get('ActiveState') in ('failed', 'inactive'), 'parent unit still owns processes')
    return previous, summaries


def source_barrier(path, digest, revision=None):
    current = core.clean_source()
    root = Path.cwd().resolve()
    core.require(root == Path(__file__).resolve().parents[1] == Path(core.__file__).resolve().parents[1],
                 'recovery and algorithms must share the clean snapshot')
    path = Path(path).absolute()
    core.require(path.resolve() == path and path.is_relative_to(root), 'release must belong to snapshot')
    core.require(revision is None or current == revision, 'snapshot revision changed')
    release = core.load_release(path, digest)
    for name in release['source_sha256']:
        file = Path(name)
        core.require(not file.is_absolute() and '..' not in file.parts and file.resolve() == file.absolute(),
                     'canonical source pin required')
    previous, _ = verify_parent()
    validate_amendment(release, previous)
    parent.read_sealed(parent.INPUTS.parent, release['inputs_complete_sha256'])
    core.inputs_for(release)
    validate_rpc_path(RPC_BASE)
    return current, release


def command(phase, release_path, release_sha, snapshot=None):
    cmd = BASE_COMMAND(phase, release_path, release_sha, snapshot)
    cmd = ['scripts.run_zpd_paired_inference_recovery' if x == 'scripts.run_zpd_full_source'
           else '--setenv=TMPDIR=' + str(RPC_BASE) if x.startswith('--setenv=TMPDIR=')
           else x for x in cmd]
    cmd.insert(cmd.index(str(PROJECT / ('.runtime/fse-vllm/bin/python' if phase == 'generation'
                                      else '.runtime/fse-env/bin/python'))),
               '--setenv=VLLM_RPC_BASE_PATH=' + str(RPC_BASE))
    return cmd


def probe_ipc():
    validate_rpc_path(RPC_BASE)
    core.require(RPC_BASE.is_dir() and os.environ.get('VLLM_RPC_BASE_PATH') == str(RPC_BASE),
                 'explicit IPC environment required')
    import zmq
    from vllm.utils.network_utils import get_open_zmq_ipc_path
    address = get_open_zmq_ipc_path()
    path = Path(address.removeprefix('ipc://'))
    core.require(path.parent == RPC_BASE and len(os.fsencode(path)) <= zmq.IPC_PATH_MAX_LEN,
                 'actual vLLM socket path differs')
    context = zmq.Context()
    sock = context.socket(zmq.PAIR)
    try:
        sock.bind(address)
        return dict(address_bytes=len(os.fsencode(path)), limit=zmq.IPC_PATH_MAX_LEN,
                    actual_zmq_bind_succeeded=True, rpc_base_path=str(RPC_BASE))
    finally:
        sock.close(linger=0); context.term()
        if path.exists(): path.unlink()  # Only this uniquely generated probe socket.


def summarize_private(report, release_sha, report_sha):
    population = json.loads((parent.FAMILY / 'materialize-v1/materialized/report.json').read_bytes())['counts']
    result = parent.summarize_private(report, release_sha, report_sha, population)
    result['operational_amendment'] = amendment()
    return result


@contextmanager
def configured():
    overrides = dict(FAMILY=FAMILY, UNIT_PREFIX=UNIT_PREFIX, VARIANT=VARIANT,
                     source_barrier=source_barrier, command=command, summarize_private=summarize_private)
    previous = {key:getattr(driver, key) for key in overrides}
    original_generation = core.generation
    for key, value in overrides.items(): setattr(driver, key, value)
    core.generation = generation
    try:
        with driver.configured_core(): yield
    finally:
        for key, value in previous.items(): setattr(driver, key, value)
        core.generation = original_generation


def worker(phase, path, digest):
    with configured():
        revision, _ = source_barrier(path, digest)
        if phase == 'generation':
            core.write_new(FAMILY / 'IPC_PREFLIGHT.json', probe_ipc())
        core.worker(phase, path, digest)
        source_barrier(path, digest, revision)


def supervise(path, digest):
    with configured():
        source_barrier(path, digest)
        core.require(not FAMILY.exists() and not RPC_BASE.exists(), 'fresh family and IPC namespace required')
        for phase in PHASES:
            core.require(core.props(driver.unit(phase)).get('LoadState') == 'not-found', 'duplicate recovery unit')
        RPC_BASE.mkdir(parents=True, mode=0o700, exist_ok=False)
        return driver.supervise(path, digest)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=('worker', 'supervise', 'verify'))
    parser.add_argument('--phase', choices=PHASES)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--release-sha', required=True)
    args = parser.parse_args()
    if args.command == 'worker': worker(args.phase, args.release, args.release_sha)
    elif args.command == 'supervise': supervise(args.release, args.release_sha)
    else:
        revision, _ = source_barrier(args.release, args.release_sha)
        print(json.dumps(dict(status='verified', revision=revision, parent_training_reused=True)))


if __name__ == '__main__': main()
