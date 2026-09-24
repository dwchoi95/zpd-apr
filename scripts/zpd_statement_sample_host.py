"""Bounded user-systemd envelope primitives; no empirical entrypoint.

This module cannot authorize replay. A separately sealed launcher must bind its
commands, runtime, input release and terminal barriers. Synthetic callers may
exercise the same envelope with explicitly smaller test-only limits. No shell,
root units, installation, runner substitution or outside-unit fallback exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time


UNIT_RE = re.compile(r'zpd-statement-samples-(?:probe|replay)-20260924-[a-z0-9-]+\.service\Z')
CGROUP_ROOT = Path('/sys/fs/cgroup')
PROPERTIES = (
    'Id', 'LoadState', 'ActiveState', 'SubState', 'Result', 'MainPID',
    'ExecMainCode', 'ExecMainStatus', 'ControlGroup', 'Delegate', 'MemoryAccounting',
    'TasksAccounting', 'MemoryMax', 'TasksMax', 'RuntimeMaxUSec', 'KillMode',
    'KillSignal', 'SendSIGKILL', 'Restart', 'RemainAfterExit', 'Type', 'LimitAS',
    'MemoryCurrent', 'MemoryPeak', 'MemorySwapMax', 'TasksCurrent', 'OOMPolicy',
    'ExecMainStartTimestampMonotonic', 'ExecMainExitTimestampMonotonic',
)


class EnvelopeError(RuntimeError):
    pass


@dataclass(frozen=True)
class Envelope:
    memory_bytes: int = 34359738368
    tasks: int = 128
    seconds: int = 21600
    address_bytes: int = 34359738368
    synthetic: bool = False
    swap_bytes: int | None = None
    oom_policy: str = 'stop'

    def __post_init__(self):
        values = (self.memory_bytes, self.tasks, self.seconds, self.address_bytes)
        if any(type(v) is not int or v <= 0 for v in values) or type(self.synthetic) is not bool:
            raise ValueError('positive integer envelope required')
        if (not self.synthetic and values != (34359738368, 128, 21600, 34359738368)
                or self.memory_bytes > 34359738368 or self.tasks > 128
                or self.seconds > 21600 or self.address_bytes > 34359738368):
            raise ValueError('production envelope is fixed; tests may only lower limits')
        if self.swap_bytes is not None and (not self.synthetic or type(self.swap_bytes) is not int or self.swap_bytes != 0):
            raise ValueError('only the synthetic memory probe may request zero swap')
        if self.oom_policy not in ('stop', 'continue') or (self.oom_policy != 'stop' and not self.synthetic):
            raise ValueError('production OOMPolicy is stop; only trusted probes may retain a keeper')

    def properties(self):
        values = dict(MemoryAccounting='yes', TasksAccounting='yes',
            MemoryMax=str(self.memory_bytes), TasksMax=str(self.tasks),
            RuntimeMaxSec=str(self.seconds), LimitAS=str(self.address_bytes),
            KillMode='control-group', KillSignal='SIGKILL', SendSIGKILL='yes',
            Restart='no', RemainAfterExit='yes', Delegate='no', OOMPolicy=self.oom_policy)
        if self.swap_bytes is not None:
            values['MemorySwapMax'] = str(self.swap_bytes)
        return values


def canonical(path):
    path = Path(path).absolute()
    if path != path.resolve():
        raise EnvelopeError('canonical nonsymlink path required')
    return path


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii') + b'\n'


def durable_new(path, value):
    path = canonical(path)
    raw = encoded(value)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return hashlib.sha256(raw).hexdigest()


def durable_append(stream, value):
    stream.write(encoded(value).decode('ascii'))
    stream.flush(); os.fsync(stream.fileno())


def checked_unit(name, envelope=None):
    if type(name) is not str or UNIT_RE.fullmatch(name) is None:
        raise EnvelopeError('unit is outside the fixed experiment namespace')
    if envelope is not None and ('-probe-' in name) != envelope.synthetic:
        raise EnvelopeError('synthetic and production unit namespaces differ')
    return name


def parse_properties(text):
    result = {}
    for line in text.splitlines():
        if '=' not in line:
            raise EnvelopeError('malformed systemd property response')
        key, value = line.split('=', 1)
        if key not in PROPERTIES or key in result:
            raise EnvelopeError('unknown/duplicate systemd property')
        result[key] = value
    if set(result) != set(PROPERTIES):
        raise EnvelopeError('missing systemd property')
    return result


def parse_counters(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) != 2 or not fields[0] or fields[0] in result or not fields[1].isdigit():
            raise EnvelopeError('malformed resource counter')
        result[fields[0]] = int(fields[1])
    if not result:
        raise EnvelopeError('empty resource counters')
    return result


def _seconds(value):
    # systemctl --value/show uses human durations for RuntimeMaxUSec.
    if not value or value == 'infinity':
        raise EnvelopeError('finite runtime limit required')
    units = {'us': .000001, 'ms': .001, 's': 1, 'min': 60, 'h': 3600, 'd': 86400}
    fields = value.split()
    total = 0.0
    for field in fields:
        match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)(us|ms|s|min|h|d)', field)
        if match is None:
            raise EnvelopeError('unrecognized runtime property')
        total += float(match[1]) * units[match[2]]
    if not math.isfinite(total):
        raise EnvelopeError('nonfinite runtime property')
    return total


def verify_properties(values, unit, envelope, *, running=True):
    checked_unit(unit, envelope)
    expected = dict(Id=unit, LoadState='loaded', MemoryAccounting='yes',
        TasksAccounting='yes', MemoryMax=str(envelope.memory_bytes),
        TasksMax=str(envelope.tasks), KillMode='control-group', KillSignal='9',
        SendSIGKILL='yes', Restart='no', RemainAfterExit='yes', Type='exec',
        LimitAS=str(envelope.address_bytes), Delegate='no', OOMPolicy=envelope.oom_policy)
    for key, value in expected.items():
        if values.get(key) != value:
            raise EnvelopeError('effective property mismatch: ' + key)
    if envelope.swap_bytes is not None and values.get('MemorySwapMax') != str(envelope.swap_bytes):
        raise EnvelopeError('effective synthetic swap limit differs')
    if _seconds(values.get('RuntimeMaxUSec', '')) != envelope.seconds:
        raise EnvelopeError('effective runtime differs')
    if running and (values.get('ActiveState') != 'active' or values.get('SubState') != 'running'
                    or not values.get('MainPID', '').isdigit() or int(values['MainPID']) <= 0):
        raise EnvelopeError('unit must be running before releasing child work')


def cgroup_path(control_group, user_id=None):
    uid = os.getuid() if user_id is None else user_id
    prefix = f'/user.slice/user-{uid}.slice/user@{uid}.service/'
    if (type(control_group) is not str or not control_group.startswith(prefix)
            or '..' in Path(control_group).parts or str(Path(control_group)) != control_group):
        raise EnvelopeError('unit cgroup must be below current user manager')
    path = canonical(CGROUP_ROOT / control_group.removeprefix('/'))
    if not path.is_relative_to(CGROUP_ROOT):
        raise EnvelopeError('cgroup path escaped')
    return path


def read_cgroup(control_group):
    root = cgroup_path(control_group)
    if not root.is_dir():
        raise EnvelopeError('resource cgroup disappeared before audit')
    data = {'control_group': control_group}
    for name in ('memory.max', 'memory.current', 'memory.swap.max',
                 'memory.swap.current', 'pids.max', 'pids.current'):
        value = (root / name).read_text(encoding='ascii').strip()
        if value != 'max' and not value.isdigit():
            raise EnvelopeError('invalid cgroup scalar: ' + name)
        data[name] = value
    for name in ('memory.peak', 'pids.peak'):
        path = root / name
        value = path.read_text(encoding='ascii').strip() if path.is_file() else None
        if value is not None and not value.isdigit():
            raise EnvelopeError('invalid optional peak: ' + name)
        data[name] = {'available': value is not None, 'value': value}
    for name in ('memory.events', 'pids.events', 'cgroup.events'):
        data[name] = parse_counters((root / name).read_text(encoding='ascii'))
    local = root / 'memory.events.local'
    data['memory.events.local'] = (parse_counters(local.read_text(encoding='ascii'))
                                   if local.is_file() else None)
    processes = (root / 'cgroup.procs').read_text(encoding='ascii').splitlines()
    if any(not p.isdigit() or int(p) <= 0 for p in processes):
        raise EnvelopeError('invalid cgroup process list')
    data['processes'] = sorted(set(map(int, processes)))
    threads = (root / 'cgroup.threads').read_text(encoding='ascii').splitlines()
    if any(not t.isdigit() or int(t) <= 0 for t in threads):
        raise EnvelopeError('invalid cgroup thread list')
    data['threads'] = sorted(set(map(int, threads)))
    return data


def verify_cgroup(data, envelope, main_pid):
    if (data.get('memory.max') != str(envelope.memory_bytes)
            or data.get('pids.max') != str(envelope.tasks)
            or main_pid not in data.get('processes', [])):
        raise EnvelopeError('effective cgroup limits/membership differ')
    if envelope.swap_bytes is not None and data.get('memory.swap.max') != str(envelope.swap_bytes):
        raise EnvelopeError('effective synthetic cgroup swap limit differs')
    if not {'low', 'high', 'max', 'oom', 'oom_kill'} <= set(data.get('memory.events', {})):
        raise EnvelopeError('memory event accounting unavailable')
    if 'max' not in data.get('pids.events', {}):
        raise EnvelopeError('pids event accounting unavailable')
    if data.get('cgroup.events', {}).get('populated') != 1:
        raise EnvelopeError('running cgroup must be populated')


def check_events(before, after):
    if before.get('control_group') != after.get('control_group'):
        raise EnvelopeError('resource cgroup changed')
    for name in ('memory.events', 'pids.events'):
        if set(before.get(name, {})) != set(after.get(name, {})):
            raise EnvelopeError('resource accounting schema changed')
        for key, old in before[name].items():
            new = after[name][key]
            if new < old:
                raise EnvelopeError('resource event counter reset')
            if key != 'low' and new != old:
                raise EnvelopeError('resource event: ' + name + ':' + key)


def current_membership(pid):
    if type(pid) is not int or pid <= 0:
        raise EnvelopeError('positive PID required')
    entries = Path(f'/proc/{pid}/cgroup').read_text(encoding='ascii').splitlines()
    if len(entries) != 1 or not entries[0].startswith('0::'):
        raise EnvelopeError('unified cgroup membership required')
    return entries[0][3:]


def process_identity(pid):
    """PID plus kernel start time; consumers must compare before signaling."""
    if type(pid) is not int or pid <= 0:
        raise EnvelopeError('positive PID required')
    raw = Path(f'/proc/{pid}/stat').read_text(encoding='ascii')
    tail = raw.rsplit(')', 1)[-1].split()
    if len(tail) < 20 or not tail[19].isdigit():
        raise EnvelopeError('invalid process start time')
    return {'pid': pid, 'start_ticks': int(tail[19]),
            'control_group': current_membership(pid)}


class UserUnit:
    def __init__(self, name, envelope=Envelope(), *, run=subprocess.run):
        self.name = checked_unit(name, envelope)
        self.envelope = envelope
        self._run = run
        self.start_attempted = False

    def _call(self, command, *, check=True, timeout=20):
        result = self._run(command, text=True, capture_output=True,
                           timeout=timeout, check=False)
        if check and result.returncode:
            raise EnvelopeError('user-unit command failed: ' + result.stderr[:2000])
        return result

    def show(self):
        result = self._call(['/usr/bin/systemctl', '--user', 'show', self.name,
            '--all', '--property=' + ','.join(PROPERTIES)])
        return parse_properties(result.stdout)

    def start(self, command, directory):
        if self.start_attempted:
            raise EnvelopeError('a unit start may not be retried')
        directory = canonical(directory)
        if (type(command) is not list or not command or any(type(c) is not str or '\0' in c for c in command)
                or not Path(command[0]).is_absolute() or not directory.is_dir()):
            raise EnvelopeError('absolute executable/list arguments and existing directory required')
        old = self.show()
        if old['LoadState'] != 'not-found' or old['ActiveState'] != 'inactive':
            raise EnvelopeError('unit already exists; no retry/reuse')
        args = ['/usr/bin/systemd-run', '--user', '--quiet', '--unit=' + self.name,
                '--service-type=exec', '--working-directory=' + str(directory)]
        args.extend('--property=' + k + '=' + v for k, v in self.envelope.properties().items())
        # A timed-out command may have created the unit: the outside finally
        # path must inspect/stop this exact unit even without a returned result.
        # A rejected preexisting unit never sets this flag and is not ours to stop.
        self.start_attempted = True
        self._call(args + ['--'] + command)

    def snapshot(self):
        """Live barrier snapshot only. Use show() for retained exit metadata."""
        values = self.show()
        verify_properties(values, self.name, self.envelope)
        cg = read_cgroup(values['ControlGroup'])
        pid = int(values['MainPID'])
        verify_cgroup(cg, self.envelope, pid)
        identity = process_identity(pid)
        if identity['control_group'] != values['ControlGroup']:
            raise EnvelopeError('main process is outside attested cgroup')
        return {'monotonic': time.monotonic(), 'properties': values, 'cgroup': cg,
                'main_process': identity}

    def stop(self):
        # The exact experiment unit, never an all-user or name-glob target.
        return self._call(['/usr/bin/systemctl', '--user', 'stop', self.name])

    def verify_empty(self, control_group):
        values = self.show()
        if values['ActiveState'] not in ('inactive', 'failed') or values['MainPID'] != '0':
            raise EnvelopeError('unit did not terminate')
        root = cgroup_path(control_group)
        if root.exists():
            data = read_cgroup(control_group)
            if data['processes'] or data['cgroup.events'].get('populated') != 0:
                raise EnvelopeError('unit descendants survived termination')
        return values
