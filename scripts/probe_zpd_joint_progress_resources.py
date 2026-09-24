"""Four fixed trusted synthetic resource fixtures; never empirical fitting.

Top-level imports are stdlib only. Every child receives its address-space cap
before Python/numerical imports. No corpus, model, label or arbitrary workload
or release path is a caller input. One fixed SHA-bound prior release supplies
only native runtime configuration metadata, never empirical labels or results.
The parent authenticates all tracked Python source and prospective documents;
this probe grants no empirical fit release.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
import errno
import hashlib
import importlib.metadata
import json
import math
import mmap
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
OUTPUT = 'outputs/zpd-repair-joint-progress-20260925/resource-probe-v1'
MEMORY_BYTES = 32 * 1024**3
ENVIRONMENT = {k: '1' for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
    'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS')}
ENVIRONMENT['JE_ARROW_MALLOC_CONF'] = 'background_thread:false'
FIXTURES = ('P1', 'P2', 'P3', 'P4')
TIMEOUTS = {'P1': 3600., 'P2': 30., 'P3': .5, 'P4': 30.}
POLL_SECONDS = .02
HEARTBEAT_SECONDS = 30.
RUNTIME = dict(python='3.13.11', numpy='2.5.2', scipy='1.18.1',
    scikit_learn='1.9.0', tqdm='4.70.0', pyarrow='25.0.1')
PROTOCOLS = ('analysis_protocols/zpd-joint-progress-ranking-candidate-20260925.md',
    'analysis_protocols/zpd-joint-progress-newton-candidate-20260925.md',
    'analysis_protocols/zpd-joint-progress-prospective-20260925.md',
    'analysis_protocols/zpd-joint-progress-resources-independent-review-20260925.md')
OWN_SOURCE = 'scripts/probe_zpd_joint_progress_resources.py'
OWN_TEST = 'tests/test_zpd_joint_progress_resources.py'
NATIVE_CONFIG = 'analysis_protocols/zpd-repair-statement-progress-release-20260925.json'
NATIVE_CONFIG_SHA = '49bd8787e322c9a3c65bbc7e62c9306b360a67f1329f30a79d81738555f8aafd'
SLEEP_CODE = 'import time; time.sleep(30)'


def require(condition, message):
    if not condition: raise ValueError(message)


def canonical(path):
    path = Path(path).absolute()
    require(path == path.resolve(), 'canonical non-symlink path required')
    return path


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode('ascii')


def sha(path):
    with canonical(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value, *, replace=False):
    path = canonical(path); temporary = path.with_name(path.name+'.tmp')
    require(replace or not path.exists(), 'fresh immutable probe artifact required')
    body = encoded(value)
    with temporary.open('xb') as stream:
        stream.write(body); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)
    return hashlib.sha256(body).hexdigest()


def consume(path):
    body = canonical(path).read_bytes()
    value = json.loads(body, parse_constant=lambda value: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
    return value, hashlib.sha256(body).hexdigest()


def read(path): return consume(path)[0]


def configuration():
    return dict(kind='joint4131_trusted_resource_probe_v1', fixtures=list(FIXTURES),
        output=OUTPUT, dimension=4131, memory_bytes=MEMORY_BYTES, environment=ENVIRONMENT,
        timeout_seconds=TIMEOUTS, poll_seconds=POLL_SECONDS, heartbeat_seconds=HEARTBEAT_SECONDS, retries=0,
        empirical_inputs=False, empirical_fitting_authorized=False, model_promotion=False,
        p1='one_full_nonzero4131_Newton_and_independent_numerical_audit',
        p2='one_anonymous_reservation_limit_plus_one_page_no_page_touch',
        p3='synthetic_only_0.5_second_spawn_to_timeout_no_production_budget_change',
        p4='one_owned_grandchild_SIGTERM_wait_reap',
        p1_native_configuration=dict(path=NATIVE_CONFIG, sha256=NATIVE_CONFIG_SHA),
        other_fixtures_native_scope='stdlib_only_executable_SHA_AS_environment_process_identity',
        sleep_code_sha256=hashlib.sha256(SLEEP_CODE.encode()).hexdigest())


def runtime():
    return dict(python=platform.python_version(), **{name: importlib.metadata.version(package)
        for name, package in (('numpy', 'numpy'), ('scipy', 'scipy'), ('scikit_learn', 'scikit-learn'),
            ('tqdm', 'tqdm'), ('pyarrow', 'pyarrow'))})


def _git(*args): return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def source_state():
    require(not _git('status', '--porcelain', '--untracked-files=all'), 'clean committed source required')
    names = _git('ls-files', '-z', '--', 'scripts/*.py', 'src/*.py', 'tests/*.py').split('\0')
    names = sorted({n for n in names if n} | set(PROTOCOLS))
    require(OWN_SOURCE in names and OWN_TEST in names, 'tracked probe source and tests required')
    return dict(revision=_git('rev-parse', 'HEAD'), tree=_git('rev-parse', 'HEAD^{tree}'),
        files_sha256={name: sha(ROOT/name) for name in names})


def expected_native():
    raw = canonical(ROOT/NATIVE_CONFIG).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == NATIVE_CONFIG_SHA, 'externally frozen native configuration changed')
    return json.loads(raw)['controller_native']


def preflight(project):
    require(sys.platform == 'linux', 'actual resource probe requires Linux')
    project = canonical(project); require(project == PROJECT, 'fixed canonical project required')
    output = canonical(project/OUTPUT); require(not output.exists(), 'fresh probe output; no retry/resume')
    actual = runtime(); require(actual == RUNTIME, 'fixed production numerical runtime required')
    return dict(project=str(project), source=source_state(), runtime=actual,
        native_config_sha256=NATIVE_CONFIG_SHA, p1_expected_native=expected_native(),
        python_executable=dict(requested=sys.executable, resolved=str(Path(sys.executable).resolve()),
            sha256=sha(Path(sys.executable).resolve())), configuration=configuration())


def recheck(context):
    require(source_state() == context['source'] and runtime() == context['runtime'], 'source/runtime changed')
    require(context['native_config_sha256'] == NATIVE_CONFIG_SHA and expected_native() == context['p1_expected_native'],
        'frozen native configuration changed')
    exe = context['python_executable']
    require(str(Path(sys.executable).resolve()) == exe['resolved'] and sha(exe['resolved']) == exe['sha256'],
        'Python executable changed')


def limits(): resource.setrlimit(resource.RLIMIT_AS, (MEMORY_BYTES, MEMORY_BYTES))


def identity(pid):
    require(type(pid) is int and pid > 1, 'strict owned PID required')
    try:
        body = Path(f'/proc/{pid}/stat').read_text()
        status = Path(f'/proc/{pid}/status').read_text()
    except FileNotFoundError: return None
    tail = body[body.rfind(')')+2:].split()
    high = next((int(line.split()[1])*1024 for line in status.splitlines() if line.startswith('VmHWM:')), 0)
    return dict(pid=pid, state=tail[0], ppid=int(tail[1]), pgid=int(tail[2]), session=int(tail[3]),
        starttime=int(tail[19]), observed_peak_rss_bytes=high)


def boundary():
    require(sys.platform == 'linux' and resource.getrlimit(resource.RLIMIT_AS) == (MEMORY_BYTES, MEMORY_BYTES),
        'exact Linux child32GiB soft/hard AS boundary required')
    require(all(os.environ.get(k) == v for k, v in ENVIRONMENT.items()), 'exact six numerical environment values required')
    task_ids = sorted(int(p.name) for p in Path('/proc/self/task').iterdir())
    require(task_ids == [os.getpid()], 'single child thread required at boundary')
    return dict(address_space_limits=list(resource.getrlimit(resource.RLIMIT_AS)),
        environment={k: os.environ[k] for k in ENVIRONMENT}, tasks=task_ids,
        identity=identity(os.getpid()), python_version=platform.python_version(),
        python_executable=dict(requested=sys.executable, resolved=str(Path(sys.executable).resolve()),
            sha256=sha(Path(sys.executable).resolve())))


def synthetic_arrays():
    import numpy as np
    x = np.zeros((6, 4131), dtype=np.float64)
    x[0, 0] = x[0, 1] = .2; x[2, 4099] = .3; x[4, 4115] = .4
    x[1::2] = -x[::2]
    return x, np.array([1, 0]*3, dtype=np.int64), np.array([310., 310., 320., 320., 320., 320.])


def scalar_reference():
    """Independent80-digit monotone roots, never a production fallback fit."""
    theta = [0.]*4131
    with localcontext() as ctx:
        ctx.prec = 80
        for value, mass, columns in ((.2, 620., (0, 1)), (.3, 640., (4099,)), (.4, 640., (4115,))):
            a = Decimal.from_float(value); factor = Decimal.from_float(.1)*Decimal.from_float(mass)*a
            lo, hi = Decimal(0), factor
            for _ in range(280):
                mid = (lo+hi)/2
                if mid-factor/(1+(a*len(columns)*mid).exp()) > 0: hi = mid
                else: lo = mid
            for col in columns: theta[col] = float((lo+hi)/2)
    return theta


def numerical_fixture(directory):
    startup = boundary()
    from scripts import run_zpd_statement_sample_replay as launcher
    from scripts import zpd_joint_progress_newton as solver
    from scripts import zpd_joint_progress_audit as independent
    from threadpoolctl import threadpool_info
    import numpy as np
    before = boundary(); pools = threadpool_info()
    require(bool(pools) and all(v['num_threads'] == 1 for v in pools), 'actual numerical pools must be singleton')
    native = launcher.controller_native_identity()
    require(native == expected_native(), 'actual P1 native identity differs from fixed configuration')
    x, target, weights = synthetic_arrays()
    spec = solver.ResidualSpec('trusted_resource_probe4131', 4131,
        hashlib.sha256(encoded(dict(active=[0, 1, 4099, 4115], fixture='fixed6mirrors'))).hexdigest(), solver.KIND)
    started = time.monotonic(); model = solver.fit_joint(x, target, weights, spec=spec)
    elapsed = time.monotonic()-started
    require(model['runtime'] == {key: RUNTIME[key] for key in ('python', 'numpy', 'scipy')},
        'actual loaded numerical runtime differs')
    audit = independent.audit_model(model, x, target, weights, spec)
    require(audit.get('verified') is True and audit.get('dimension') == 4131, 'independent numerical audit required')
    theta = np.asarray(model['coefficients'], dtype=np.float64)
    difference = float(np.max(np.abs(theta-np.asarray(scalar_reference()))))
    require(difference <= 1e-8 and model['optimization']['updates'] > 0, 'nonzero full solve must match scalar reference')
    inactive = [j for j in range(4131) if j not in (0, 1, 4099, 4115)]
    require(not np.any(theta[inactive]), 'inactive full-dimensional coefficients must be exact zero')
    model_pin = write(directory/'model.json', model); audit_pin = write(directory/'audit.json', audit)
    require(launcher.controller_native_identity() == native == expected_native(), 'P1 native identity drift after computation')
    return dict(solver_seconds=elapsed, scalar_reference_max_error=difference,
        model_sha256=model_pin, audit_sha256=audit_pin, updates=model['optimization']['updates'],
        startup=startup, before=before, after=boundary(), threadpools=pools, controller_native=native)


def allocation_fixture():
    size = MEMORY_BYTES + mmap.PAGESIZE
    try:
        mapping = mmap.mmap(-1, size)
    except (MemoryError, OSError) as error:
        require(isinstance(error, MemoryError) or error.errno == errno.ENOMEM, 'only AS allocation refusal is expected')
        return dict(expected_failure=True, error_type=type(error).__name__, errno=getattr(error, 'errno', None),
            requested_bytes=size, page_touch=False, boundary=boundary())
    mapping.close()
    raise RuntimeError('reservation unexpectedly succeeded under fixed AS cap; never touch pages')


def fixture_child(project, fixture, expected_source_sha):
    require(fixture in FIXTURES, 'fixed trusted fixture required')
    project = canonical(project); require(project == PROJECT, 'fixed canonical project required')
    require(sha(ROOT/OWN_SOURCE) == expected_source_sha, 'externally supplied harness source changed')
    directory = canonical(project/OUTPUT/fixture)
    require(directory.is_dir() and not any(directory.iterdir()), 'fresh parent-created fixture directory required')
    initial = boundary(); started = time.monotonic()
    ready = dict(fixture=fixture, boundary=initial, harness_sha256=expected_source_sha)
    if fixture == 'P4':
        child = subprocess.Popen([sys.executable, '-B', '-c', SLEEP_CODE])
        child_id = identity(child.pid)
        require(child_id is not None and child_id['ppid'] == os.getpid()
            and child_id['pgid'] == initial['identity']['pgid'] and child_id['session'] == initial['identity']['session'],
            'one own same-group child identity required')
        ready['grandchild'] = child_id
        def terminate(signum, _frame):
            code = child.wait(timeout=2.)
            require(code == -signal.SIGTERM and identity(child.pid) is None, 'owned child must be waited/reaped')
            write(directory/'REAPED.json', dict(signal=signum, child_returncode=code, grandchild=child_id,
                no_remaining_child=True, leader=initial['identity']))
            raise SystemExit(0)
        signal.signal(signal.SIGTERM, terminate)
        write(directory/'READY.json', ready)
        while True: time.sleep(.1)
    write(directory/'READY.json', ready)
    if fixture == 'P3': time.sleep(30.); raise RuntimeError('timeout fixture was not terminated')
    result = numerical_fixture(directory) if fixture == 'P1' else allocation_fixture()
    result.update(fixture=fixture, passed=True, elapsed_seconds=time.monotonic()-started,
        peak_rss_bytes=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024, terminal=boundary())
    write(directory/'child-result.json', result)
    return result


def _owned(process, first):
    now = identity(process.pid)
    require(now is not None and first is not None and all(now[k] == first[k] for k in ('pid', 'starttime', 'pgid', 'session'))
        and now['pgid'] == now['session'] == process.pid, 'exact owned child identity required before signals')


def stop_owned(process):
    # Explicit reuse, not a modified timeout/global or generic process killer.
    from scripts.supervise_zpd_joint_progress import _stop_owned
    _stop_owned(process)


def group_alive(process):
    from scripts.supervise_zpd_joint_progress import _group_alive
    return _group_alive(process)


def cleanup(process, first, members=()):
    """Retain the new Popen group even if its leader was already reaped."""
    if group_alive(process):
        current = identity(process.pid)
        if first is None:
            require(process.poll() is None and current is not None, 'cannot bind a missing initial owned identity')
            first = current
        require(first['pgid'] == first['session'] == process.pid, 'only created session/group may be stopped')
        if current is not None:
            require(all(current[k] == first[k] for k in ('pid', 'starttime', 'pgid', 'session')),
                'owned leader identity changed; refuse signals')
        else:
            proven = False
            for saved in members:
                live = identity(saved['pid'])
                if live is not None and all(live[k] == saved[k] for k in ('pid', 'starttime', 'pgid', 'session')):
                    proven |= live['pgid'] == live['session'] == process.pid
            require(proven, 'no live previously bound member; refuse potentially reused group signals')
        stop_owned(process)
    process.wait(timeout=1.)
    if first is not None: _gone(first)
    require(not group_alive(process), 'owned process group survives cleanup')


def _gone(first):
    now = identity(first['pid'])
    require(now is None or now['starttime'] != first['starttime'], 'original owned process remains, including zombies')


def files(directory, pins, *, marker=False):
    require({p.name for p in directory.iterdir()} == set(pins) | ({'COMPLETE.json'} if marker else set()),
        'exact probe fixture inventory required')
    require(all(canonical(directory/n).is_file() and sha(directory/n) == pin for n, pin in pins.items()),
        'consumed probe artifact changed')


def _seal(directory, pins, extra):
    files(directory, pins)
    marker = dict(status='complete', files_sha256=pins, **extra)
    try:
        pin = write(directory/'COMPLETE.json', marker)
        files(directory, pins, marker=True)
        require(sha(directory/'COMPLETE.json') == pin, 'probe marker changed during completion')
        return pin
    except BaseException as error:
        reject(directory, error); raise


def run_fixture(context, fixture, output):
    directory = output/fixture; directory.mkdir()
    command = [sys.executable, '-B', '-m', 'scripts.probe_zpd_joint_progress_resources', '--project', context['project'],
        '--fixture', fixture, '--expected-source-sha', context['source']['files_sha256'][OWN_SOURCE]]
    env = dict(os.environ, **ENVIRONMENT, PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1')
    process = None; first = None; latest = None; started = time.monotonic(); expected_timeout = False
    consumed = {}; ready = None; members = (); last_heartbeat = started
    def ready_value():
        value, pin = consume(directory/'READY.json')
        require('READY.json' not in consumed or consumed['READY.json'] == pin, 'READY changed after consumption')
        consumed['READY.json'] = pin
        saved = value['boundary']['identity']
        require(value['fixture'] == fixture and value['harness_sha256'] == context['source']['files_sha256'][OWN_SOURCE]
            and all(saved[k] == first[k] for k in ('pid', 'starttime', 'pgid', 'session')),
            'READY child identity/source differs')
        require(value['boundary']['address_space_limits'] == [MEMORY_BYTES, MEMORY_BYTES]
            and value['boundary']['environment'] == ENVIRONMENT and value['boundary']['tasks'] == [process.pid]
            and value['boundary']['python_version'] == RUNTIME['python']
            and value['boundary']['python_executable'] == context['python_executable'],
            'READY fixed child resource boundary differs')
        return value
    with (output/(fixture+'.log')).open('x') as log:
        try:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True, preexec_fn=limits)
            first = identity(process.pid)
            require(first is not None and first['pgid'] == first['session'] == process.pid, 'new own session required')
            peak = first['observed_peak_rss_bytes']
            while process.poll() is None:
                latest = identity(process.pid)
                if latest: peak = max(peak, latest['observed_peak_rss_bytes'])
                now = time.monotonic()
                if now-last_heartbeat >= HEARTBEAT_SECONDS:
                    write(output/'STATUS.json', dict(phase='running', fixture=fixture,
                        completed_fixtures=FIXTURES.index(fixture), elapsed_seconds=now-started,
                        child_pid=process.pid, observed_peak_rss_bytes=peak), replace=True)
                    last_heartbeat = now
                if fixture == 'P4' and (directory/'READY.json').exists():
                    ready = ready_value()
                    grandchild = ready['grandchild']; current = identity(grandchild['pid'])
                    require(current is not None and all(current[k] == grandchild[k] for k in ('pid', 'starttime', 'ppid', 'pgid', 'session'))
                        and current['ppid'] == process.pid and current['pgid'] == process.pid, 'exact owned grandchild required')
                    members = (grandchild,)
                    _owned(process, first); cleanup(process, first, members); break
                if now-started >= TIMEOUTS[fixture]:
                    require(fixture == 'P3' and (directory/'READY.json').is_file(), 'unexpected fixture timeout/startup failure')
                    ready = ready_value()
                    _owned(process, first); cleanup(process, first); expected_timeout = True; break
                time.sleep(POLL_SECONDS)
            code = process.wait(timeout=1.); _gone(first)
            require(not group_alive(process), 'successful leader left surviving owned group')
            ready = ready_value()
            if fixture == 'P3':
                require(expected_timeout and code == -signal.SIGTERM and not (directory/'child-result.json').exists(), 'expected timeout must prevent child completion')
                result = dict(expected_failure=True, reason='synthetic_0.5_second_timeout', production_timeout_changed=False)
                consumed['EXPECTED_FAILURE.json'] = write(directory/'EXPECTED_FAILURE.json', result)
            elif fixture == 'P4':
                require(code == 0 and (directory/'REAPED.json').is_file(), 'cleanup leader must record child reaping')
                result, consumed['REAPED.json'] = consume(directory/'REAPED.json')
                require(result['no_remaining_child'] is True and result['grandchild'] == ready['grandchild']
                    and result['leader'] == ready['boundary']['identity'] and result['signal'] == signal.SIGTERM
                    and result['child_returncode'] == -signal.SIGTERM, 'exact owned child reap evidence required')
                _gone(result['grandchild'])
            else:
                require(code == 0 and (directory/'child-result.json').is_file(), 'fixture must complete once')
                result, consumed['child-result.json'] = consume(directory/'child-result.json')
                require(result.get('passed') is True and result['fixture'] == fixture, 'positive trusted fixture result required')
                if fixture == 'P1':
                    consumed.update({'model.json': result['model_sha256'], 'audit.json': result['audit_sha256']})
                    require(all(sha(directory/n) == p for n, p in consumed.items()), 'written numerical evidence changed')
                else:
                    require(result.get('expected_failure') is True and result.get('page_touch') is False
                        and result.get('requested_bytes') == MEMORY_BYTES+mmap.PAGESIZE
                        and (result.get('error_type') == 'MemoryError' or
                            result.get('error_type') == 'OSError' and result.get('errno') == errno.ENOMEM),
                        'exact expected allocation refusal required')
            log.flush(); os.fsync(log.fileno())
            report = dict(fixture=fixture, passed=True, returncode=code, elapsed_seconds=time.monotonic()-started,
                timeout_seconds=TIMEOUTS[fixture], first_identity=first, last_observed_identity=latest,
                observed_peak_rss_bytes=peak, owned_process_gone=True, result=result, empirical_inputs=False, retries=0)
            consumed['report.json'] = write(directory/'report.json', report)
            pin = _seal(directory, consumed, dict(fixture=fixture, synthetic_only=True))
            return dict(report=report, complete_sha256=pin, log_sha256=sha(output/(fixture+'.log')), files_sha256=consumed)
        except BaseException as error:
            cleanup_error = None
            try:
                if process is not None: cleanup(process, first, members)
            except BaseException as failed_cleanup:
                cleanup_error = dict(error_type=type(failed_cleanup).__name__, error=str(failed_cleanup))
            reject(directory, error)
            if cleanup_error is not None: write(directory/'CLEANUP_FAILED.json', cleanup_error)
            raise


def reject(output, error):
    complete = output/'COMPLETE.json'
    if complete.exists(): complete.rename(output/'REJECTED_COMPLETE.json')
    if not (output/'FAILED.json').exists():
        write(output/'FAILED.json', dict(status='failed', error_type=type(error).__name__, error=str(error), retries=0))


def run_probe(project):
    context = preflight(project); output = canonical(Path(context['project'])/OUTPUT)
    os.environ.update(ENVIRONMENT)
    output.mkdir(parents=True); completed = []
    try:
        initial = write(output/'manifest.json', context)
        for fixture in FIXTURES:
            recheck(context)
            write(output/'STATUS.json', dict(phase='running', fixture=fixture, completed_fixtures=len(completed)), replace=True)
            result = run_fixture(context, fixture, output); completed.append(result)
            recheck(context)
        report = dict(verified=True, fixtures=completed, synthetic_only=True, empirical_inputs=False,
            empirical_fitting_authorized=False, production_budgets_changed=False, automatic_retries=0)
        report_pin = write(output/'report.json', report)
        status_pin = write(output/'STATUS.json', dict(phase='complete', completed_fixtures=4), replace=True)
        pins = {'manifest.json': initial, 'report.json': report_pin, 'STATUS.json': status_pin}
        for fixture, value in zip(FIXTURES, completed, strict=True):
            pins.update({fixture+'/'+name: pin for name, pin in value['files_sha256'].items()})
            pins[fixture+'/COMPLETE.json'] = value['complete_sha256']; pins[fixture+'.log'] = value['log_sha256']
        def artifacts():
            wanted = set(pins) | ({'COMPLETE.json'} if (output/'COMPLETE.json').exists() else set())
            require({str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()} == wanted,
                'exact outer probe artifact inventory required')
            require(all(sha(output/n) == p for n, p in pins.items()), 'consumed probe artifact changed')
        def check():
            recheck(context); artifacts()
        check()
        marker = write(output/'COMPLETE.json', dict(status='complete', files_sha256=pins, verified=True,
            synthetic_only=True, empirical_fitting_authorized=False, automatic_retries=0))
        check(); recheck(context); artifacts()
        require(sha(output/'COMPLETE.json') == marker, 'outer probe marker changed')
        return report
    except BaseException as error:
        reject(output, error); raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__); parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--fixture', choices=FIXTURES); parser.add_argument('--expected-source-sha')
    args = parser.parse_args(argv)
    if args.fixture:
        require(args.expected_source_sha is not None, 'child harness SHA required')
        return fixture_child(args.project, args.fixture, args.expected_source_sha)
    require(args.expected_source_sha is None, 'no source override for parent preflight')
    return run_probe(args.project)


if __name__ == '__main__': main()
