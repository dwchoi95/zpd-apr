"""Bounded, completion-triggered C1 execution; no unattended hypothesis search.

The supervisor owns its children only. A successful process exit must also have
a valid completion seal before the next stage can start. It never opens a shell,
retries a failed experiment, modifies the evaluator, or promotes a model.
The three fixed stage modules are synchronous and must not spawn detached
workers; this is not a general daemon/process-tree reaper after a leader exits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'outputs/zpd-history-action-20260923'
HEARTBEAT_SECONDS = 30
CROSS_FIT_SECONDS = 8 * 60 * 60
FOLLOWUP_SECONDS = 60 * 60
MEMORY_BYTES = 32 * 1024**3


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def write(path, value):
    """Atomic durable status replacement, with no shell or truncate-in-place."""
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def event(output, **fields):
    value = {'timestamp_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **fields}
    write(Path(output) / 'STATUS.json', value)
    with (Path(output) / 'events.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(value, sort_keys=True, allow_nan=False), flush=True)


def verify_marker(directory, *, required_files=()):
    """Validate every sealed relative artifact, rejecting traversal/symlinks."""
    directory = Path(directory).absolute()
    if directory.resolve() != directory:
        raise ValueError('symlink stage directory or ancestor rejected')
    marker_path = directory / 'COMPLETE.json'
    if marker_path.is_symlink():
        raise ValueError('symlink completion marker rejected')
    marker = read(marker_path)
    bindings = marker.get('files_sha256')
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError('nonempty completion artifact bindings required')
    if not set(required_files).issubset(bindings):
        raise ValueError('consumed artifact missing from completion bindings')
    for relative, expected in bindings.items():
        path = Path(relative)
        if (path.is_absolute() or '..' in path.parts or str(path) != relative
                or path.name == 'COMPLETE.json' and path.parent == Path('.')):
            raise ValueError('invalid completion-relative artifact')
        actual = directory / path
        if actual.resolve() != actual or not actual.is_file():
            raise ValueError('unsafe or missing sealed artifact')
        if sha(actual) != expected:
            raise ValueError('completion artifact hash mismatch: ' + relative)
    if marker.get('status') != 'complete':
        raise ValueError('explicit complete status required')
    return {'complete_sha256': sha(marker_path), 'files_verified': len(bindings)}


def verify_previous_stages(results):
    for result in results:
        actual = verify_marker(result['output'], required_files=('report.json',))
        if actual['complete_sha256'] != result['complete_sha256']:
            raise ValueError('previous stage completion changed before continuation')


def _child_limits(memory_bytes):
    if memory_bytes is not None:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))


def _stop_owned_process(process):
    """Terminate only the process group created for this exact child."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=10)


def child_progress(directory):
    path = Path(directory) / 'STATUS.json'
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 1024 * 1024:
        return None
    try:
        value = read(path)
        return {'status': value, 'age_seconds': max(0, time.time() - path.stat().st_mtime)}
    except (OSError, ValueError):
        return None  # A missing/in-flight status is not an experiment result.


def run_stage(command, *, name, cwd, stage_output, output, timeout_seconds,
              heartbeat_seconds=HEARTBEAT_SECONDS, memory_bytes=MEMORY_BYTES):
    """Wait on real completion, emitting heartbeats during the bounded wait."""
    if timeout_seconds <= 0 or heartbeat_seconds <= 0:
        raise ValueError('positive timeout and heartbeat required')
    if Path(stage_output).exists() or Path(stage_output).is_symlink():
        raise ValueError('stage output must be new; no implicit retry/resume')
    environment = dict(os.environ)
    environment.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                       MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', PYTHONUNBUFFERED='1')
    started = time.monotonic()
    log_path = Path(output) / (name + '.log')
    process = None
    with log_path.open('x', encoding='utf-8') as log:
        try:
            process = subprocess.Popen(command, cwd=cwd, env=environment,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                preexec_fn=lambda: _child_limits(memory_bytes))
            while True:
                elapsed = time.monotonic() - started
                event(output, phase='running', stage=name, child_pid=process.pid,
                      elapsed_seconds=elapsed, timeout_seconds=timeout_seconds,
                      child_progress=child_progress(stage_output), log_bytes=log_path.stat().st_size)
                remaining = timeout_seconds - elapsed
                if remaining <= 0:
                    raise TimeoutError(name + ' exceeded fixed resource budget')
                try:
                    returncode = process.wait(timeout=min(heartbeat_seconds, remaining))
                    break
                except subprocess.TimeoutExpired:
                    continue
            if returncode != 0:
                raise RuntimeError(f'{name} child exited {returncode}; no next-stage release')
            seal = verify_marker(stage_output, required_files=('report.json',))
            result = {'name': name, 'returncode': returncode,
                      'elapsed_seconds': time.monotonic() - started,
                      'output': str(Path(stage_output).resolve()),
                      'log_sha256': sha(log_path), **seal}
            event(output, phase='stage_complete', stage=name, result=result)
            return result
        except BaseException:
            if process is not None:
                _stop_owned_process(process)
            raise


def source_state():
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('clean committed source snapshot required')
    return {'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()}


def supervise(project, output, run_output):
    project, output, run_output = map(lambda p: Path(p).absolute(), (project, output, run_output))
    if any(p.resolve() != p for p in (project, output, run_output)):
        raise ValueError('canonical paths without symlink aliases required')
    family = project / FAMILY
    if output.parent != family or run_output.parent != family or output == run_output:
        raise ValueError('distinct direct children of the fixed project family required')
    if output.exists() or run_output.exists():
        raise ValueError('new supervisor and experiment outputs required')
    provenance = source_state()
    commands = [
        ('crossfit', [sys.executable, '-m', 'scripts.run_zpd_history_action_cv',
                     '--project', str(project), '--output', str(run_output)], run_output, CROSS_FIT_SECONDS),
        ('verify', [sys.executable, '-m', 'scripts.audit_zpd_history_action_cv',
                   '--run', str(run_output), '--output', str(output / 'verified')], output / 'verified', FOLLOWUP_SECONDS),
        ('diagnose', [sys.executable, '-m', 'scripts.diagnose_zpd_history_action_cv',
                     '--run', str(run_output), '--audit', str(output / 'verified'),
                     '--output', str(output / 'diagnosis')], output / 'diagnosis', FOLLOWUP_SECONDS),
    ]
    output.mkdir(parents=True)
    write(output / 'manifest.json', {'kind': 'supervised_c1_bounded_continuation',
        'source': provenance, 'source_root': str(ROOT), 'project_root': str(project),
        'heartbeat_seconds': HEARTBEAT_SECONDS, 'child_memory_bytes': MEMORY_BYTES,
        'stages': [{'name': n, 'command': c, 'output': str(o), 'timeout_seconds': t}
                   for n, c, o, t in commands],
        'automatic_retries': 0, 'opens_heldout_labels': False, 'model_promotion': False})
    results = []
    try:
        for name, command, stage_output, timeout in commands:
            if source_state() != provenance:
                raise ValueError('source snapshot drift before next-stage release')
            verify_previous_stages(results)
            results.append(run_stage(command, name=name, cwd=ROOT, stage_output=stage_output,
                                     output=output, timeout_seconds=timeout))
        if source_state() != provenance:
            raise ValueError('source snapshot drift at completion')
        verify_previous_stages(results)
        write(output / 'stages.json', results)
        report = read(output / 'diagnosis' / 'report.json')
        verify_previous_stages(results)
        write(output / 'next_action.json', report['next_action'])
        event(output, phase='complete', completed_stages=len(results),
              next_action=report['next_action'])
        write(output / 'COMPLETE.json', {'status': 'complete', 'completed_stages': len(results),
            'files_sha256': {name: sha(output / name) for name in
                ('manifest.json', 'stages.json', 'next_action.json',
                 'verified/COMPLETE.json', 'diagnosis/COMPLETE.json')},
            'experiment_complete_sha256': sha(run_output / 'COMPLETE.json')})
        return report
    except BaseException as exc:
        failure = {'phase': 'failed', 'completed_stages': results,
                   'error_type': type(exc).__name__, 'error': str(exc),
                   'next_action': 'diagnose_operational_failure_without_changing_frozen_protocol'}
        write(output / 'FAILED.json', failure)
        event(output, **failure)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-output', type=Path, required=True)
    args = parser.parse_args(argv)
    return supervise(args.project, args.output, args.run_output)


if __name__ == '__main__':
    main()
