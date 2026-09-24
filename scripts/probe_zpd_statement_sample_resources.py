"""Separately released trusted fixtures only; never reads an empirical input.

The outside coordinator owns durable resource evidence and exact-unit cleanup.
Unit entry is fixed to one of six literal fixtures and cannot bypass its ready
attestation. This module does not authorize replay, fitting, or runtime changes.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import select
import signal
import subprocess
import sys
import time

from scripts import zpd_statement_sample_host as host
from scripts.zpd_repair_evaluate import SandboxRunner, sandbox_command
from src.runner.models import TestCase
from src.runner.python_runner import _SUBPROCESS_RUNNER

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = 'outputs/zpd-statement-sample-feedback-20260924'
OUTPUT = FAMILY + '/resource-probe-v1'
PROTOCOL = 'analysis_protocols/zpd-statement-sample-resource-probe-20260924.md'
RELEASE = 'analysis_protocols/zpd-statement-sample-resource-probe-release-20260924.json'
SIDECAR = RELEASE + '.sha256'
SOURCES = (
    PROTOCOL, 'scripts/probe_zpd_statement_sample_resources.py',
    'scripts/zpd_statement_sample_host.py', 'scripts/zpd_repair_evaluate.py',
    'src/repair/pilot_contracts.py', 'src/runner/models.py',
    'src/runner/python_runner.py', 'src/runner/compare.py',
    'tests/test_zpd_statement_sample_resources.py',
    'tests/test_zpd_statement_sample_host.py',
)
FIXTURES = ('P1', 'P2', 'P3', 'P4', 'P5', 'P6')
POLL_SECONDS = .05
BARRIER_SECONDS = 5.
UNIT_SECONDS = 30.
SUITE_SECONDS = 600.
SENTINEL = 'ZPD_TRUSTED_PROBE_SENTINEL'
SENTINEL_VALUE = 'fixed_nonsecret_probe_20260924'
NORMAL_CODE = "import time\ntime.sleep(0.25)\nprint('PROBE_OK')\n"
OUTPUT_CODE = "import sys,time\nsys.stdout.write('X'*(8*1024*1024))\nsys.stderr.write('E'*(1024*1024))\ntime.sleep(0.25)\n"
TIMEOUT_CODE = "import os,time\nos.fork()\ntime.sleep(10)\n"
ISOLATION_CODE = r'''
import json,os,time
s={}
with open('/proc/self/status') as f:
    for line in f:
        key,_,value=line.partition(':')
        if key in ('NoNewPrivs','CapEff','CapPrm','CapBnd','NSpid'):
            s[key]=value.strip()
mounts={}
with open('/proc/self/mountinfo') as f:
    for line in f:
        fields=line.split()
        if fields[4] in ('/usr','/lib','/lib64','/tmp','/proc','/dev'):
            mounts[fields[4]]=fields[5].split(',')
print(json.dumps(dict(net=os.readlink('/proc/self/ns/net'),pid=os.readlink('/proc/self/ns/pid'),
    status=s,home=os.path.exists('/home'),users=os.path.exists('/Users'),
    project=os.path.exists('/home/cdw/VSCode/zpd-apr'),
    sentinel='ZPD_TRUSTED_PROBE_SENTINEL' in os.environ,mounts=mounts),sort_keys=True))
time.sleep(0.25)
'''


def digest(data):
    return hashlib.sha256(data).hexdigest()


def same(left, right):
    return host.encoded(left) == host.encoded(right)


def require(condition, message):
    if not condition:
        raise host.EnvelopeError(message)


def sha_file(path):
    path = host.canonical(path)
    require(path.is_file(), 'regular source/runtime file required')
    return digest(path.read_bytes())


def json_file(path):
    path = host.canonical(path)
    return json.loads(path.read_bytes().decode('utf-8', errors='strict'))


def envelope(fixture):
    require(fixture in FIXTURES, 'fixed trusted fixture required')
    changes = {
        'P1': {}, 'P2': dict(memory_bytes=256*2**20, tasks=16, seconds=20),
        'P3': dict(memory_bytes=128*2**20, tasks=16, seconds=20, swap_bytes=0,oom_policy='continue'),
        'P4': dict(seconds=15), 'P5': dict(seconds=3), 'P6': {},
    }
    return host.Envelope(synthetic=True, **changes[fixture])


def unit_name(fixture):
    require(fixture in FIXTURES, 'fixed trusted fixture required')
    return 'zpd-statement-samples-probe-20260924-' + fixture.lower() + '.service'


def configuration():
    return dict(kind='trusted_statement_sample_resource_probe_v1',
        output=OUTPUT, fixtures=['P0', *FIXTURES],
        fixture_sha256={k: digest(v.encode()) for k, v in
            dict(normal=NORMAL_CODE, bounded_output=OUTPUT_CODE,
                 timeout=TIMEOUT_CODE, isolation=ISOLATION_CODE).items()},
        envelopes={f: asdict(envelope(f)) for f in FIXTURES},
        p2_max_forks=20, p3_max_blocks=160, p3_block_bytes=2**20,
        pressure_child_seconds=10, sandbox_workers=8, sandbox_case_workers=1,
        sandbox_timeout_seconds=2.5, sandbox_memory_mib=2048,
        poll_seconds=POLL_SECONDS, barrier_seconds=BARRIER_SECONDS,
        unit_watchdog_seconds=UNIT_SECONDS, suite_seconds=SUITE_SECONDS,
        output_record='first1024_codepoints_count_and_canonical_JSON_string_SHA',
        empirical_inputs=False, execution_scope='fixed_trusted_fixtures_only',
        replay_authorized=False, fitting_authorized=False, retries=0, overwrite=False)


def _command(command):
    result = subprocess.run(command, text=True, capture_output=True,
                            timeout=5, check=False)
    require(result.returncode == 0, 'trusted runtime identity command failed')
    return result.stdout.strip() or result.stderr.strip()


def _binary(path):
    requested = Path(path)
    require(requested.is_absolute(), 'absolute trusted executable required')
    resolved = requested.resolve(strict=True)
    return dict(requested=str(requested), resolved=str(resolved), sha256=sha_file(resolved))


def runtime_identity():
    """Trusted binaries/platform only; no empirical input or workload execution."""
    require(sys.platform == 'linux', 'released runtime probe requires Linux')
    binaries = {k: _binary(p) for k, p in dict(controller=sys.executable,
        execution_python='/usr/bin/python3', bwrap='/usr/bin/bwrap',
        systemctl='/usr/bin/systemctl', systemd_run='/usr/bin/systemd-run',
        ldd='/usr/bin/ldd').items()}
    libraries = {}
    for key in ('controller', 'execution_python', 'bwrap'):
        output = _command(['/usr/bin/ldd', binaries[key]['resolved']])
        paths = []
        for line in output.splitlines():
            require('not found' not in line, 'runtime shared library missing')
            fields = line.strip().split()
            selected = fields[2] if len(fields) >= 3 and fields[1] == '=>' else fields[0] if fields else ''
            if selected.startswith('/'):
                paths.append(_binary(selected))
            else:
                require(selected.startswith(('linux-vdso', 'linux-gate')),
                        'unrecognized trusted ldd response')
        require(paths, 'dynamic dependency identity unavailable')
        libraries[key] = sorted(paths, key=lambda v: v['resolved'])
    uname = os.uname()
    return dict(python=sys.version, architecture=uname.machine, kernel_release=uname.release,
        kernel_version=uname.version, system=uname.sysname, libc=list(platform.libc_ver()),
        binaries=binaries, dynamic_libraries=libraries,
        execution_python_version=_command(['/usr/bin/python3', '--version']),
        bwrap_version=_command(['/usr/bin/bwrap', '--version']),
        systemd_version=_command(['/usr/bin/systemctl', '--version']),
        sandbox_command=sandbox_command(), subprocess_runner_sha256=digest(_SUBPROCESS_RUNNER.encode()))


def source_state():
    require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'],
                cwd=ROOT, text=True).strip(), 'clean committed source snapshot required')
    required = set(SOURCES) | {RELEASE, SIDECAR}
    tracked = subprocess.check_output(['git', 'ls-files', '--error-unmatch', '-z', '--',
        *sorted(required)], cwd=ROOT).decode().rstrip('\0').split('\0')
    require(set(tracked) == required, 'exact tracked release/source inventory required')
    for name in SOURCES:
        module = sys.modules.get(name[:-3].replace('/', '.')) if name.endswith('.py') else None
        if module is not None:
            require(host.canonical(module.__file__) == ROOT/name, 'import escaped clean snapshot')
    return {key: subprocess.check_output(['git', 'rev-parse', arg], cwd=ROOT, text=True).strip()
            for key, arg in (('revision', 'HEAD'), ('tree', 'HEAD^{tree}'))}


def preflight(project, *, fixture=None):
    """Release is required before any unit, output, or fixture work."""
    project = host.canonical(project)
    require(project == PROJECT and host.canonical(ROOT).is_relative_to(project/'.runtime'),
            'fixed project and clean runtime snapshot required')
    require(ROOT != project/'.runtime', 'dedicated snapshot required')
    if fixture is not None:
        require(fixture in FIXTURES, 'fixed fixture required')
    raw = (ROOT/RELEASE).read_bytes(); side = (ROOT/SIDECAR).read_bytes()
    require(re.fullmatch(b'[0-9a-f]{64}\n', side) is not None and
            digest(raw) == side[:-1].decode(), 'external release SHA sidecar required')
    approval = json.loads(raw)
    required = {'kind', 'project', 'output', 'configuration', 'source_sha256',
                'runtime', 'trusted_probe_authorized', 'replay_authorized', 'decision_reason'}
    require(type(approval) is dict and set(approval) == required, 'strict external probe release required')
    require(approval['kind'] == 'trusted_statement_sample_resource_probe_release_v1'
        and approval['project'] == str(PROJECT) and approval['output'] == OUTPUT
        and approval['trusted_probe_authorized'] is True and approval['replay_authorized'] is False
        and type(approval['decision_reason']) is str and approval['decision_reason'].strip()
        and same(approval['configuration'], configuration()), 'probe release configuration mismatch')
    require(type(approval['source_sha256']) is dict and set(approval['source_sha256']) == set(SOURCES),
            'exact probe-only source inventory required')
    state = source_state()
    for name, expected in approval['source_sha256'].items():
        require(sha_file(ROOT/name) == expected, 'released source changed: '+name)
    measured = runtime_identity()
    require(same(measured, approval['runtime']), 'released trusted runtime changed')
    output = host.canonical(project/OUTPUT)
    require(not output.exists() if fixture is None else output.is_dir(),
            'new coordinator output or exact existing fixture root required')
    return dict(project=project, output=output, approval=approval, state=state,
        release_sha256=digest(raw), sidecar_sha256=digest(side), runtime=measured)


def recheck(context, *, check_runtime=True):
    require(same(source_state(), context['state']), 'source snapshot changed')
    for name, expected in context['approval']['source_sha256'].items():
        require(sha_file(ROOT/name) == expected, 'source drift before seal')
    require(sha_file(ROOT/RELEASE) == context['release_sha256'] and
            sha_file(ROOT/SIDECAR) == context['sidecar_sha256'], 'release drift')
    if check_runtime:
        require(same(runtime_identity(), context['runtime']), 'runtime drift before seal')


def text_record(text):
    require(type(text) is str, 'exact diagnostic string required')
    data = json.dumps(text, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    return dict(excerpt=text[:1024], characters=len(text), json_string_sha256=digest(data),
                truncated=len(text) > 1024, encoding='canonical_ASCII_JSON_string')


class ArtifactLedger:
    """Pin bytes at write/consumption, never retroactively bless a directory."""
    def __init__(self, root):
        self.root = host.canonical(root)
        self.hashes = {}

    def _path(self, name):
        path = host.canonical(self.root/name)
        require(path.is_relative_to(self.root) and path != self.root, 'artifact path escaped')
        return path

    def bind(self, name, expected):
        require(name not in self.hashes or self.hashes[name] == expected, 'consumed artifact drift')
        self.hashes[name] = expected
        require(sha_file(self._path(name)) == expected, 'artifact changed after write/consumption')

    def write(self, name, value):
        require(name not in self.hashes, 'artifact cannot be overwritten')
        expected = digest(host.encoded(value))
        require(host.durable_new(self._path(name), value) == expected, 'artifact write digest differs')
        self.bind(name, expected)
        return expected

    def read(self, name):
        raw = self._path(name).read_bytes()
        value = json.loads(raw.decode('utf-8', errors='strict'))
        self.bind(name, digest(raw))
        return value

    def verify(self):
        actual = {str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}
        require(actual == set(self.hashes), 'unexpected or missing probe artifact')
        for name, expected in self.hashes.items():
            require(sha_file(self._path(name)) == expected, 'sealed probe artifact drift')


def process_metadata(pid):
    identity = host.process_identity(pid)
    status = {}
    for line in Path(f'/proc/{pid}/status').read_text(encoding='ascii').splitlines():
        key, _, value = line.partition(':')
        if key in ('PPid', 'NSpid', 'NoNewPrivs', 'CapEff', 'CapPrm', 'CapBnd'):
            status[key] = value.strip()
    value = dict(identity, status=status,
        net=os.readlink(f'/proc/{pid}/ns/net'), pid_namespace=os.readlink(f'/proc/{pid}/ns/pid'),
        executable=os.readlink(f'/proc/{pid}/exe'))
    require(host.process_identity(pid) == identity, 'process identity changed while inspecting')
    return value


def is_alive(identity):
    try:
        return host.process_identity(identity['pid']) == identity
    except FileNotFoundError:
        return False


def snapshot_processes(snapshot):
    records = []
    for pid in snapshot['cgroup']['processes']:
        try:
            record = process_metadata(pid)
        except FileNotFoundError:
            continue  # A short-lived process disappeared; never invent metadata.
        require(record['control_group'] == snapshot['properties']['ControlGroup'],
                'process escaped owned cgroup')
        records.append(record)
    return records


def verify_ready(ready, snapshot, fixture, context):
    expected = dict(kind='trusted_fixture_ready_v1', fixture=fixture, unit=unit_name(fixture),
        main_process=snapshot['main_process'], release_sha256=context['release_sha256'])
    require(same(ready, expected), 'ready identity/start-time/release mismatch')


def _wait_file(path, deadline):
    while time.monotonic() < deadline:
        if path.is_file():
            return json_file(path)
        time.sleep(POLL_SECONDS)
    raise host.EnvelopeError('bounded fixture barrier expired')


def _child_wait(pid, deadline):
    while time.monotonic() < deadline:
        found, status = os.waitpid(pid, os.WNOHANG)
        if found:
            return status
        time.sleep(POLL_SECONDS)
    # Exact unreaped child; it cannot be a reused unrelated PID.
    os.kill(pid, signal.SIGKILL)
    os.waitpid(pid, 0)
    raise host.EnvelopeError('trusted child exceeded fixed independent deadline')


def _fork_waiter(seconds=10):
    pid = os.fork()
    if pid == 0:
        time.sleep(seconds)
        os._exit(0)
    return host.process_identity(pid)


def _p1():
    os.environ[SENTINEL] = SENTINEL_VALUE
    codes = [(f'normal{i}', NORMAL_CODE, 'PROBE_OK') for i in range(6)]
    codes += [('isolation', ISOLATION_CODE, ''), ('output', OUTPUT_CODE, '')]
    runner = SandboxRunner()
    require((runner.case_workers, runner.timeout_sec, runner.memory_limit_mb) == (1, 2.5, 2048),
            'unchanged runner limits required')
    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda item: runner.run_case(item[1], TestCase(item[0], '', item[2])), codes))
    rows = []
    isolation = None
    for result, (name, _, _) in zip(outcomes, codes, strict=True):
        require(result.case_id == name and str(result.verdict) == ('AC' if name.startswith('normal') else 'WA'),
                'trusted P1 terminal verdict differs')
        if name == 'isolation':
            isolation = json.loads(result.stdout)
        if name == 'output':
            require(result.stdout == 'X'*(8*2**20) and result.stderr == 'E'*(2**20),
                    'unmodified bounded output capture differs')
        rows.append(dict(case_id=name, verdict=str(result.verdict), stdout=text_record(result.stdout),
                         stderr=text_record(result.stderr)))
    return dict(results=rows, isolation=isolation)


def _p2():
    read_fd, write_fd = os.pipe(); children=[]; eagain=False
    try:
        for _ in range(20):
            try:
                pid=os.fork()
            except OSError as exc:
                if exc.errno != errno.EAGAIN:
                    raise
                eagain=True; break
            if pid == 0:
                os.close(write_fd)
                select.select([read_fd], [], [], 10)
                os.close(read_fd); os._exit(0)
            children.append(host.process_identity(pid))
    finally:
        os.close(read_fd); os.close(write_fd)
        statuses=[_child_wait(p['pid'], time.monotonic()+10) for p in children]
    require(eagain and children and all(os.WIFEXITED(s) and os.WEXITSTATUS(s)==0 for s in statuses),
            'bounded pids-pressure fixture did not hit/reap expected children')
    return dict(eagain=eagain, children=children, children_reaped=len(statuses), max_attempts=20)


def _p3():
    pid=os.fork()
    if pid == 0:
        deadline=time.monotonic()+10; blocks=[]
        for _ in range(160):
            if time.monotonic() >= deadline:
                os._exit(117)
            block=bytearray(2**20)
            for offset in range(0, len(block), 4096): block[offset]=1
            blocks.append(block)
        os._exit(118)  # Reaching160 MiB is not proof of128 MiB enforcement.
    identity=host.process_identity(pid)
    status=_child_wait(pid, time.monotonic()+10)
    return dict(child=identity, signal=os.WTERMSIG(status) if os.WIFSIGNALED(status) else None,
                exit_status=os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
                children_reaped=1)


def _p4():
    result=SandboxRunner().run_case(TIMEOUT_CODE, TestCase('timeout', '', ''))
    require(str(result.verdict)=='TLE', 'unchanged per-case timeout did not fire')
    return dict(verdict='TLE', call_returned_monotonic=time.monotonic())


def run_fixture(project, fixture):
    context=preflight(project, fixture=fixture)
    directory=host.canonical(context['output']/fixture)
    require(directory.is_dir(), 'coordinator must create exact fixture directory')
    manifest=json_file(context['output']/'manifest.json')
    require(manifest['release_sha256']==context['release_sha256'] and
            same(manifest['source'],context['state']), 'fixture coordinator/source binding mismatch')
    unit=host.UserUnit(unit_name(fixture), envelope(fixture)); snap=unit.snapshot()
    require(snap['main_process']==host.process_identity(os.getpid()), 'fixture must be attested unit main')
    require(resource.getrlimit(resource.RLIMIT_AS)==(32*2**30,32*2**30), 'fixed parent address limit required')
    ready=dict(kind='trusted_fixture_ready_v1', fixture=fixture, unit=unit.name,
        main_process=snap['main_process'], release_sha256=context['release_sha256'])
    host.durable_new(directory/'READY.json',ready)
    go=_wait_file(directory/'GO.json',time.monotonic()+BARRIER_SECONDS)
    require(same(go,dict(kind='trusted_fixture_go_v1',ready_sha256=sha_file(directory/'READY.json'),
                        main_process=snap['main_process'])), 'work acknowledgment differs')
    current=unit.snapshot();require(current['main_process']==snap['main_process'], 'main identity changed')
    if fixture in ('P5','P6'):
        if fixture=='P6':
            with (directory/'journal.jsonl').open('x',encoding='ascii') as stream:
                host.durable_append(stream,dict(kind='trusted_completion_row', sequence=0, fixture='P6'))
        host.durable_new(directory/'progress.json',dict(fixture=fixture, phase='before_one_fork'))
        child=_fork_waiter()
        host.durable_new(directory/'WORK_READY.json',dict(fixture=fixture, child=child,
                         main_process=snap['main_process']))
        time.sleep(10)
        _child_wait(child['pid'],time.monotonic()+1)
        raise host.EnvelopeError('intentional termination fixture unexpectedly survived')
    result={'P1':_p1,'P2':_p2,'P3':_p3,'P4':_p4}[fixture]()
    recheck(context,check_runtime=False)
    end=dict(kind='trusted_fixture_end_v1',fixture=fixture,main_process=snap['main_process'],result=result)
    host.durable_new(directory/'END.json',end)
    ack=_wait_file(directory/'ACK.json',time.monotonic()+BARRIER_SECONDS)
    require(same(ack,dict(kind='trusted_fixture_ack_v1',end_sha256=sha_file(directory/'END.json'))),
            'final resource acknowledgment differs')


def event_deltas(before, after):
    require(before['control_group']==after['control_group'],'resource cgroup changed')
    result={}
    for name in ('memory.events','pids.events'):
        require(set(before[name])==set(after[name]),'resource event schema changed')
        result[name]={k:after[name][k]-old for k,old in before[name].items()}
        require(all(x>=0 for x in result[name].values()),'resource counters reset')
    return result


def _isolation(value, outside):
    require(type(value)is dict and set(value)=={'net','pid','status','home','users','project','sentinel','mounts'},
            'strict fixed-key isolation metadata required')
    require(value['net']!=outside['net'] and value['pid']!=outside['pid_namespace'], 'namespace isolation absent')
    require(all(value[k] is False for k in ('home','users','project','sentinel')), 'host path/environment visible')
    s=value['status'];require(s['NoNewPrivs']=='1' and int(s['CapEff'],16)==0 and int(s['CapPrm'],16)==0,
                             'sandbox privilege isolation differs')
    require('CapBnd'in s and 'NSpid'in s and 'ro'in value['mounts'].get('/usr',[]), 'readonly/capability evidence missing')
    for name in ('/lib','/lib64'):
        if name in value['mounts']:require('ro'in value['mounts'][name],'runtime bind mount is writable')


def assess_normal(fixture, result, before, after, outside, observed_processes, runtime):
    deltas=event_deltas(before,after)
    if fixture in ('P1','P4'):
        host.check_events(before,after)
    elif fixture=='P2':
        require(result.get('eagain') is True and result['children_reaped']==len(result['children'])
                and 0<len(result['children'])<=15 and deltas['pids.events']['max']>0,
                'pids enforcement not independently evidenced')
    elif fixture=='P3':
        require(result.get('signal')==signal.SIGKILL and result.get('children_reaped')==1
                and deltas['memory.events']['oom_kill']>0
                and (deltas['memory.events']['max']>0 or deltas['memory.events']['oom']>0),
                'actual memory OOM kill not independently evidenced')
    target=runtime['binaries']['execution_python']['resolved']
    sandbox=[p for p in observed_processes if p['executable']==target and
             p['pid_namespace']!=outside['pid_namespace']]
    if fixture=='P1':
        require(len(result.get('results',[]))==8 and len(sandbox)>=8,'eight live sandbox workers not observed')
        _isolation(result['isolation'],outside)
        require(all(p['net']!=outside['net'] and p['status'].get('NoNewPrivs')=='1'
            and int(p['status'].get('CapEff','1'),16)==0 and int(p['status'].get('CapPrm','1'),16)==0
            for p in sandbox),'live host-process isolation metadata differs')
    if fixture=='P4':
        require(result.get('verdict')=='TLE' and len(sandbox)>=2,'forked timeout descendants not observed')
    return deltas


def run_p0():
    """Fixed mock metadata only; never starts a unit or executes a fixture."""
    from copy import deepcopy
    env=envelope('P1');name=unit_name('P1')
    values={k:'' for k in host.PROPERTIES}
    values.update(Id=name,LoadState='loaded',ActiveState='active',SubState='running',MainPID='123',
        MemoryAccounting='yes',TasksAccounting='yes',MemoryMax=str(32*2**30),TasksMax='128',
        RuntimeMaxUSec='6h',KillMode='control-group',KillSignal='9',SendSIGKILL='yes',Restart='no',
        RemainAfterExit='yes',Type='exec',LimitAS=str(32*2**30),Delegate='no',OOMPolicy='stop')
    cg=dict(control_group='/mock',**{'memory.max':str(32*2**30),'pids.max':'128','processes':[123],
        'memory.events':dict(low=0,high=0,max=0,oom=0,oom_kill=0),'pids.events':{'max':0},
        'cgroup.events':{'populated':1}})
    host.verify_properties(values,name,env)
    host.verify_cgroup(cg,env,123)
    checks=[]
    for key,bad in (('MemoryMax','127'),('TasksMax','127'),('MainPID','0'),('Type','unsupported'),
                    ('Delegate','yes'),('OOMPolicy','continue')):
        changed=deepcopy(values);changed[key]=bad
        checks.append((key,lambda v=changed:host.verify_properties(v,name,env)))
    checks += [('missing_cgroup_file',lambda:host.verify_cgroup({},env,123)),
        ('wrong_main_membership',lambda:host.verify_cgroup(cg,env,999)),
        ('wrong_start_time',lambda:require({'pid':123,'start_ticks':1}=={'pid':123,'start_ticks':2},'start mismatch')),
        ('permission_or_controller_unavailable',lambda:require(False,'controller access unavailable')),
        ('source_SHA_drift',lambda:require('a'*64=='b'*64,'source SHA drift')),
        ('runtime_drift',lambda:require(same({'python':'fixed'},{'python':'changed'}),'runtime drift'))]
    rows=[]
    for name,check in checks:
        try:check()
        except host.EnvelopeError as exc:
            rows.append(dict(check=name,work_released=False,error=text_record(str(exc))))
        else:raise host.EnvelopeError('P0 mutation did not refuse work: '+name)
    return dict(probe_pass=True,workloads=0,checks=rows)


def kill_main(unit, identity):
    snapshot=unit.snapshot()
    require(snapshot['main_process']==identity and host.process_identity(identity['pid'])==identity,
            'main PID/start-time/cgroup changed before signal')
    os.kill(identity['pid'],signal.SIGKILL)


def coordinate_fixture(context, fixture, suite_deadline, *, unit_factory=host.UserUnit,
                       clock=time.monotonic, sleep=time.sleep):
    """One owned unit; no retries, broad signals, collection or implicit success."""
    directory=host.canonical(context['output']/fixture);directory.mkdir(exist_ok=False)
    start=clock();deadline=min(suite_deadline,start+UNIT_SECONDS)
    command_deadline=deadline
    def bounded_run(command, **kwargs):
        remaining=command_deadline-clock()
        require(remaining>0,'outside unit watchdog expired')
        kwargs['timeout']=min(kwargs.get('timeout',20),remaining)
        return subprocess.run(command,**kwargs)
    unit=unit_factory(unit_name(fixture),envelope(fixture),run=bounded_run)
    ledger=context.setdefault('ledger',ArtifactLedger(context['output']))
    prefix=fixture+'/'
    def write(name,value):return ledger.write(prefix+name,value)
    def read(name):return ledger.read(prefix+name)
    outside=process_metadata(os.getpid());first=None;last=None;ready=None;end=None;retained=None
    observed={};work=None;killed=False;sent_go=False;sent_ack=False;pass_result=None;error=None;cleanup_error=None
    journal=directory/'snapshots.jsonl'
    journal_hash=hashlib.sha256()
    def capture(stream):
        nonlocal last
        snap=unit.snapshot()
        if first is not None:require(snap['main_process']==first['main_process'],'unit main identity changed')
        cg=snap['cgroup']
        require(cg['pids.current'].isdigit() and int(cg['pids.current'])<=unit.envelope.tasks
                and len(cg['threads'])<=unit.envelope.tasks,'observed unit task limit exceeded')
        peak=cg['pids.peak']
        require(not peak['available'] or int(peak['value'])<=unit.envelope.tasks,'observed peak task limit exceeded')
        procs=snapshot_processes(snap)
        row=dict(snapshot=snap,process_metadata=procs)
        host.durable_append(stream,row);journal_hash.update(host.encoded(row))
        if sent_go:
            for proc in procs:observed[(proc['pid'],proc['start_ticks'])]=proc
        last=snap
        return snap
    def consume_work():
        value=read('WORK_READY.json')
        require(type(value)is dict and set(value)=={'fixture','main_process','child'}
            and value['fixture']==fixture and value['main_process']==first['main_process'],
            'intentional work identity differs')
        child=value['child']
        require(type(child)is dict and set(child)=={'pid','start_ticks','control_group'}
            and child['control_group']==first['main_process']['control_group']
            and child['pid']!=first['main_process']['pid']
            and host.process_identity(child['pid'])==child,'trusted child is not live in owned unit')
        record=process_metadata(child['pid']);observed[(record['pid'],record['start_ticks'])]=record
        require(read('progress.json')==dict(fixture=fixture,phase='before_one_fork'),'fixed progress record differs')
        if fixture=='P6':
            expected=host.encoded(dict(kind='trusted_completion_row',sequence=0,fixture='P6'))
            ledger.bind(prefix+'journal.jsonl',digest(expected))
        return value
    try:
        require(Path(sys.executable).is_absolute(),'absolute controller interpreter required')
        command=[sys.executable,'-B','-m','scripts.probe_zpd_statement_sample_resources',
                 '--project',str(context['project']),'--fixture',fixture]
        with journal.open('x',encoding='ascii') as stream:
            unit.start(command,ROOT)
            while clock()<min(deadline,start+BARRIER_SECONDS):
                snap=capture(stream)
                if (directory/'READY.json').is_file():
                    ready=read('READY.json');verify_ready(ready,snap,fixture,context)
                    first=snap
                    write('ready-snapshot.json',snap)
                    write('GO.json',dict(kind='trusted_fixture_go_v1',
                        ready_sha256=ledger.hashes[prefix+'READY.json'],main_process=snap['main_process']))
                    sent_go=True;break
                sleep(POLL_SECONDS)
            require(sent_go,'ready barrier expired; work not released')
            while clock()<deadline:
                values=unit.show()
                if values['MainPID']=='0' or values['ActiveState']=='failed':
                    retained=values;break
                try:snap=capture(stream)
                except (FileNotFoundError,host.EnvelopeError):
                    state=unit.show()
                    if state['MainPID']=='0':retained=state;break
                    raise
                if fixture in ('P5','P6') and work is None and (directory/'WORK_READY.json').is_file():
                    work=consume_work()
                if fixture=='P6' and not killed and (directory/'WORK_READY.json').is_file():
                    require(work is not None,'live child attestation required before main kill')
                    write('kill-intent.json',dict(main_process=first['main_process'],signal='SIGKILL'))
                    kill_main(unit,first['main_process']);killed=True
                if (directory/'END.json').is_file():
                    end=read('END.json')
                    require(type(end)is dict and set(end)=={'kind','fixture','main_process','result'}
                        and end['kind']=='trusted_fixture_end_v1' and end['fixture']==fixture
                        and end['main_process']==first['main_process'], 'end identity differs')
                    require(fixture in ('P1','P2','P3','P4'),'intentional death fixture wrote normal end')
                    # The harness remains alive. Require no case process before
                    # ACK; P4 gets its stated five-second per-case cleanup bound.
                    limit=min(deadline,end['result'].get('call_returned_monotonic',clock())+BARRIER_SECONDS)
                    while any(pid!=first['main_process']['pid'] for pid in last['cgroup']['processes']) and clock()<limit:
                        sleep(POLL_SECONDS);capture(stream)
                    require(last['cgroup']['processes']==[first['main_process']['pid']], 'case descendants survive before unit cleanup')
                    deltas=assess_normal(fixture,end['result'],first['cgroup'],last['cgroup'],outside,
                                         list(observed.values()),context['runtime'])
                    write('end-snapshot.json',last)
                    write('ACK.json',dict(kind='trusted_fixture_ack_v1',end_sha256=ledger.hashes[prefix+'END.json']))
                    sent_ack=True;pass_result=dict(event_deltas=deltas)
                    break
                sleep(POLL_SECONDS)
            if sent_ack:
                ack_deadline=min(deadline,clock()+BARRIER_SECONDS)
                while clock()<ack_deadline:
                    retained=unit.show()
                    if retained['MainPID']=='0':break
                    sleep(POLL_SECONDS)
                require(retained['MainPID']=='0' and retained['Result']=='success' and retained['ExecMainStatus']=='0',
                        'acknowledged harness failed to exit normally')
            elif fixture in ('P5','P6') and retained is not None:
                require(retained['Result']==('timeout' if fixture=='P5' else 'signal') and
                        retained['MainPID']=='0' and retained['ExecMainCode']=='2'
                        and retained['ExecMainStatus']=='9','intentional SIGKILL unit failure not evidenced')
                require(work is not None,'live-observed durable progress/child evidence absent')
                if fixture=='P6':
                    require(killed and (directory/'journal.jsonl').is_file(),'forced death/journal evidence absent')
                require(not (directory/'END.json').exists() and not (directory/'ACK.json').exists(),
                        'unexpected normal completion after intentional failure')
                pass_result=dict(raw_final_cgroup_available=False,expected_unit_result=retained['Result'])
            else:
                raise host.EnvelopeError('unit ended early or outside watchdog expired')
            write('retained-unit.json',retained)
            cleanup_deadline=min(suite_deadline,clock()+BARRIER_SECONDS)
            if fixture in ('P5','P6'):
                ended=retained['ExecMainExitTimestampMonotonic']
                require(ended.isdigit() and 0<int(ended)/1e6<=clock(), 'monotonic termination evidence absent')
                cleanup_deadline=min(cleanup_deadline,int(ended)/1e6+BARRIER_SECONDS)
                require(clock()<=cleanup_deadline,'termination evidence arrived after cleanup deadline')
            identities=[{k:p[k] for k in ('pid','start_ticks','control_group')} for p in observed.values()]
            while any(is_alive(p) for p in identities) and clock()<cleanup_deadline:sleep(POLL_SECONDS)
            require(not any(is_alive(p) for p in identities),'owned process survived termination')
            if fixture in ('P2','P3','P5','P6'):
                write('FAILED.json',dict(expected_guard_outcome='FAILED_unknown',
                    intentional_fixture=True,fixture=fixture))
    except BaseException as exc:
        error=dict(type=type(exc).__name__,message=text_record(str(exc)))
    finally:
        if journal.exists():
            try:ledger.bind(prefix+'snapshots.jsonl',journal_hash.hexdigest())
            except BaseException as exc:error=dict(type=type(exc).__name__,message=text_record(str(exc)))
        command_deadline=min(suite_deadline,clock()+BARRIER_SECONDS)
        if getattr(unit,'start_attempted',False):
            try:
                state=unit.show()
                write('before-stop.json',state)
                # A start timeout may still have created the exact requested
                # service. Only this attempted unit is eligible for cleanup.
                if state['LoadState']!='not-found':
                    require(state['Id']==unit.name,'refuse cleanup of a different unit identity')
                    try:host.verify_properties(state,unit.name,unit.envelope,running=False)
                    except BaseException as exc:
                        cleanup_error=dict(type=type(exc).__name__,message=text_record(str(exc)))
                    if state['MainPID']!='0':
                        identity=host.process_identity(int(state['MainPID']))
                        require(identity['control_group']==state['ControlGroup'],'main cgroup differs before cleanup')
                        if first is not None:require(identity==first['main_process'],'PID reuse before cleanup')
                        # A configuration mismatch must not prevent exact-owned
                        # cleanup. Preserve raw evidence without asserting validity.
                        try:
                            live=dict(properties=state,main_process=identity,
                                      cgroup=host.read_cgroup(state['ControlGroup']))
                            write('before-stop-live.json',live)
                        except BaseException as exc:
                            cleanup_error=dict(type=type(exc).__name__,message=text_record(str(exc)))
                    cg=first['properties']['ControlGroup'] if first else state['ControlGroup']
                    unit.stop();empty=unit.verify_empty(cg)
                    write('cleanup.json',dict(unit=unit.name,empty=True,properties=empty))
                else:
                    require(first is None,'owned unit disappeared before retained cleanup')
                    write('cleanup.json',dict(unit=unit.name,not_created=True))
            except BaseException as exc:
                cleanup_error=dict(type=type(exc).__name__,message=text_record(str(exc)))
    report=dict(fixture=fixture,unit=unit.name,probe_pass=error is None and cleanup_error is None and pass_result is not None,
        expected_guard_outcome='FAILED_unknown' if fixture in ('P2','P3','P5','P6') else 'normal',
        work_released=sent_go,acknowledged=sent_ack,result=pass_result,error=error,cleanup_error=cleanup_error,
        started_monotonic=start,finished_monotonic=clock())
    if not report['probe_pass'] and not (directory/'FAILED.json').exists():write('FAILED.json',report)
    write('report.json',report)
    require(report['probe_pass'],'trusted fixture failed or inconclusive: '+fixture)
    return report


def coordinator(project):
    context=preflight(project);output=context['output'];output.mkdir(parents=True,exist_ok=False)
    deadline=time.monotonic()+SUITE_SECONDS
    manifest=dict(kind='trusted_resource_probe_manifest_v1',configuration=configuration(),
        source=context['state'],source_root=str(ROOT),source_sha256=context['approval']['source_sha256'],
        release_sha256=context['release_sha256'],runtime=context['runtime'],empirical_inputs=False,
        replay_authorized=False,fitting_authorized=False)
    ledger=ArtifactLedger(output);context['ledger']=ledger
    try:
        ledger.write('manifest.json',manifest)
        (output/'P0').mkdir();p0=run_p0();ledger.write('P0/report.json',p0)
        reports={'P0':p0}
        for fixture in FIXTURES:
            require(time.monotonic()<deadline,'whole trusted-probe deadline expired')
            recheck(context)
            reports[fixture]=coordinate_fixture(context,fixture,deadline)
        ledger.write('report.json',dict(probe_pass=True,probes=reports,replay_authorized=False))
        ledger.verify()
        recheck(context)
        ledger.verify()
        recheck(context)
        require(time.monotonic()<=deadline,'whole trusted-probe deadline expired before seal')
        host.durable_new(output/'COMPLETE.json',dict(status='complete',probe_pass=True,files_sha256=ledger.hashes,
            replay_authorized=False,fitting_authorized=False,empirical_inputs=False))
    except BaseException as exc:
        marker=output/'COMPLETE.json'
        if marker.exists():
            rejected=output/'REJECTED_COMPLETE.json'
            require(not rejected.exists(),'refuse rejected marker overwrite')
            marker.rename(rejected)
        host.durable_new(output/'FAILED.json',dict(error_type=type(exc).__name__,error=text_record(str(exc)),
            replay_authorized=False,fitting_authorized=False))
        raise


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--fixture',choices=FIXTURES)
    args=parser.parse_args()
    if args.fixture:run_fixture(args.project,args.fixture)
    else:coordinator(args.project)


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        # No raw diagnostic or full traceback is sent to systemd's journal.
        print(host.encoded(dict(error_type=type(exc).__name__,error=text_record(str(exc)))).decode('ascii'),end='')
        raise SystemExit(1) from None
