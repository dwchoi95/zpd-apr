"""Separately released observed-source sample replay in one attested user unit.

The outside coordinator decodes metadata only and stream-hashes empirical files
as opaque bytes. Only the GO-released worker loads roster/sample bodies. Neither
process opens candidate/label/cache/full-testcase files. No release is created,
and there is no retry, runtime/path override or outside-unit execution fallback.
"""
from __future__ import annotations

import argparse
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
             'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'
import hashlib
import json
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

from scripts import prepare_zpd_statement_samples as preparation
from scripts import probe_zpd_statement_sample_resources as probe
from scripts import zpd_statement_sample_host as host
from scripts import zpd_statement_sample_replay as core

ROOT=Path(__file__).resolve().parents[1]
PROJECT=Path('/home/cdw/VSCode/zpd-apr')
FAMILY=core.FAMILY
OUTPUT=core.OUTPUT
SUPERVISED=FAMILY+'/replay-supervised-v1'
PROBE=FAMILY+'/resource-probe-v1'
UNIT='zpd-statement-samples-replay-20260924-v1.service'
RELEASE='analysis_protocols/zpd-statement-sample-replay-release-20260924.json'
SIDECAR=RELEASE+'.sha256'
PROTOCOL='analysis_protocols/zpd-statement-sample-replay-prospective-20260924.md'
METADATA_BYTES=16*1024**2
POLL_SECONDS=.25
READY_SECONDS=30
KEEPER_SECONDS=5
ENVIRONMENT={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                            'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')}
SOURCES=tuple(sorted(set((*preparation.SOURCE_FILES,*probe.SOURCES,PROTOCOL,
    'scripts/zpd_statement_sample_replay.py','tests/test_zpd_statement_sample_replay.py',
    'scripts/run_zpd_statement_sample_replay.py','tests/test_zpd_statement_sample_replay_launcher.py'))))
PROBE_NAMES=frozenset(('report.json','READY.json','GO.json','WORK_READY.json','END.json','ACK.json',
    'journal.jsonl','progress.json','snapshots.jsonl','ready-snapshot.json','end-snapshot.json',
    'kill-intent.json','retained-unit.json','before-stop.json','before-stop-live.json','cleanup.json','FAILED.json'))


def require(condition,message):
    if not condition:raise ValueError(message)


def canonical(path):return preparation.canonical(path)


def same(left,right):return core.encoded(left)==core.encoded(right)


def sha_file(path):
    """Opaque bounded-memory hashing; no parsing or output buffering."""
    path=canonical(path);require(path.is_file(),'regular authenticated file required')
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(1024**2):digest.update(chunk)
    return digest.hexdigest()


def metadata(path,expected=None,bindings=None):
    path=canonical(path);require(path.is_file() and path.stat().st_size<=METADATA_BYTES,'bounded metadata file required')
    raw=path.read_bytes();require(len(raw)<=METADATA_BYTES,'metadata grew beyond bound')
    if expected is not None:require(core.sha(raw)==expected,'metadata SHA mismatch')
    if bindings is not None:
        pin=core.sha(raw);key=str(path)
        require(key not in bindings or bindings[key]==pin,'consumed metadata drift')
        bindings[key]=pin
    return core.decode_json(raw)


def configuration():
    return dict(kind='statement_sample_replay_launcher_v1',output=OUTPUT,supervised=SUPERVISED,
        unit=UNIT,envelope=host.Envelope().properties(),replay=core.configuration(),
        poll_seconds=POLL_SECONDS,ready_seconds=READY_SECONDS,keeper_seconds=KEEPER_SECONDS,
        metadata_byte_limit=METADATA_BYTES,controller_environment=ENVIRONMENT,
        ready_and_keeper_processes_threads='exactly_the_unit_main_PID',
        outside_empirical_body_decoding=False,outside_opaque_hashing=True,
        parent_limit_as=34359738368,worker_protocol='READY_GO_inner_COMPLETE_live_DONE_ACK_retained_exit_cleanup',
        fitting_authorized=False,retries=0,overwrite=False)


def zero_baseline(cgroup):
    require(all(v==0 for key,v in cgroup['memory.events'].items() if key!='low')
        and all(v==0 for v in cgroup['pids.events'].values()),'resource event occurred before work release')


def only_keeper(snapshot):
    pid=snapshot['main_process']['pid']
    require(snapshot['cgroup']['processes']==[pid] and snapshot['cgroup']['threads']==[pid],
            'unexpected processes or threads at ready/keeper barrier')


def source_state():
    require(canonical(ROOT)==ROOT,'canonical source snapshot required')
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True).strip(),
            'clean committed snapshot required')
    names=set(SOURCES)|{RELEASE,SIDECAR}
    tracked=subprocess.check_output(['git','ls-files','--error-unmatch','-z','--',*sorted(names)],cwd=ROOT)
    require(set(tracked.decode('utf-8').rstrip('\0').split('\0'))==names,'tracked exact source/release closure required')
    for name in SOURCES:
        module=sys.modules.get(name[:-3].replace('/','.')) if name.endswith('.py') else None
        if module is not None:require(canonical(module.__file__)==ROOT/name,'import outside released snapshot')
    return {key:subprocess.check_output(['git','rev-parse',arg],cwd=ROOT,text=True).strip()
            for key,arg in (('revision','HEAD'),('tree','HEAD^{tree}'))}


def _fixed_probe_name(name):
    if name in ('manifest.json','report.json'):return True
    path=Path(name)
    return (type(name) is str and len(path.parts)==2 and str(path)==name
        and path.parts[0] in ('P0',*probe.FIXTURES) and path.parts[1] in PROBE_NAMES
        and (path.parts[0]!='P0' or path.parts[1]=='report.json'))


def verify_parents(project,approval):
    """Decode fixed parent metadata; stream all other fixed sealed artifacts."""
    bindings={};prepared_dir=canonical(project/core.PREPARED);probe_dir=canonical(project/PROBE)
    require(not (prepared_dir/'FAILED.json').exists() and not (probe_dir/'FAILED.json').exists(),'failed prerequisite')
    def read(base,name,pin):
        path=canonical(base/name);value=metadata(path,pin);bindings[str(path)]=pin;return value
    prepared_complete=read(prepared_dir,'COMPLETE.json',approval['prepared_complete_sha256'])
    require(same({k:prepared_complete[k] for k in prepared_complete if k!='files_sha256'},
        dict(status='complete',recipients=320,problems=23,execution_authorized=False,fitting_authorized=False,excluded_recipients=0))
        and set(prepared_complete.get('files_sha256',{}))==set(preparation.ARTIFACTS),'complete fixed preparation required')
    prepared_manifest=read(prepared_dir,'manifest.json',prepared_complete['files_sha256']['manifest.json'])
    require(same(prepared_manifest.get('configuration'),preparation.configuration())
        and same(prepared_manifest.get('runtime'),preparation.RUNTIME)
        and set(prepared_manifest.get('source_sha256',{}))==set(preparation.SOURCE_FILES)
        and all(approval['source_sha256'][n]==s for n,s in prepared_manifest['source_sha256'].items())
        and prepared_manifest.get('outcomes_opened') is False,'prepared source/runtime ancestry mismatch')
    probe_complete=read(probe_dir,'COMPLETE.json',approval['resource_probe_complete_sha256'])
    require(same({k:probe_complete[k] for k in probe_complete if k!='files_sha256'},
        dict(status='complete',probe_pass=True,replay_authorized=False,fitting_authorized=False,empirical_inputs=False)),
        'successful independently released resource probe required')
    files=probe_complete.get('files_sha256')
    require(type(files) is dict and {'manifest.json','report.json','P0/report.json'}<=set(files)
        and all(_fixed_probe_name(n) and preparation.is_sha(v) for n,v in files.items())
        and all(f+'/report.json' in files and f+'/cleanup.json' in files for f in probe.FIXTURES),
        'exact bounded probe artifact inventory required')
    probe_manifest=read(probe_dir,'manifest.json',files['manifest.json'])
    report=read(probe_dir,'report.json',files['report.json'])
    require(probe_manifest.get('kind')=='trusted_resource_probe_manifest_v1'
        and same(probe_manifest.get('configuration'),probe.configuration())
        and same(probe_manifest.get('runtime'),approval['runtime'])
        and set(probe_manifest.get('source_sha256',{}))==set(probe.SOURCES)
        and all(approval['source_sha256'][n]==s for n,s in probe_manifest['source_sha256'].items())
        and probe_manifest.get('empirical_inputs') is False and probe_manifest.get('replay_authorized') is False,
        'probe runtime/source ancestry mismatch')
    require(report.get('probe_pass') is True and report.get('replay_authorized') is False
        and set(report.get('probes',{}))=={'P0',*probe.FIXTURES}
        and all(p.get('probe_pass') is True for p in report['probes'].values()),'all seven resource probes must pass')
    for directory,inventory in ((prepared_dir,prepared_complete['files_sha256']),(probe_dir,files)):
        for name,pin in inventory.items():
            require(preparation.is_sha(pin),'parent artifact SHA required')
            path=canonical(directory/name);require(sha_file(path)==pin,'parent artifact SHA mismatch')
            bindings[str(path)]=pin
    return bindings


def preflight(project,*,worker=False):
    project=canonical(project)
    require(project==PROJECT and canonical(ROOT).is_relative_to(project/'.runtime') and ROOT!=project/'.runtime',
            'fixed project and dedicated canonical runtime snapshot required')
    release=canonical(ROOT/RELEASE);sidecar=canonical(ROOT/SIDECAR)
    require(release.is_file() and sidecar.is_file(),'separate replay release required')
    require(sidecar.stat().st_size==65,'strict release sidecar required')
    side=sidecar.read_bytes();require(re.fullmatch(b'[0-9a-f]{64}\n',side) is not None,'strict release sidecar required')
    approval=metadata(release,side[:-1].decode('ascii'))
    required={'kind','project','output','supervised','unit','configuration','prepared_complete_sha256',
        'resource_probe_complete_sha256','source_sha256','runtime','runtime_sha256','controller_runtime',
        'protocol_sha256','execution_authorized','fitting_authorized','decision_reason'}
    core.exact_fields(approval,required)
    require(approval['kind']=='statement_sample_replay_release_v1' and approval['project']==str(PROJECT)
        and approval['output']==OUTPUT and approval['supervised']==SUPERVISED and approval['unit']==UNIT
        and same(approval['configuration'],configuration())
        and approval['prepared_complete_sha256']==core.PREPARED_COMPLETE_SHA
        and preparation.is_sha(approval['resource_probe_complete_sha256'])
        and preparation.is_sha(approval['runtime_sha256']) and approval['runtime_sha256']==core.sha(core.encoded(approval['runtime']))
        and approval['execution_authorized'] is True and approval['fitting_authorized'] is False
        and type(approval['decision_reason']) is str and bool(approval['decision_reason'].strip()),'strict replay release contract required')
    require(type(approval['source_sha256']) is dict and set(approval['source_sha256'])==set(SOURCES),
            'exact replay source closure required')
    state=source_state()
    require(all(preparation.is_sha(v) and sha_file(ROOT/n)==v for n,v in approval['source_sha256'].items()),'released source mismatch')
    require(same(approval['protocol_sha256'],{n:approval['source_sha256'][n] for n in (PROTOCOL,probe.PROTOCOL)}),
            'both prospective protocol hashes required')
    require(same(approval['controller_runtime'],preparation.RUNTIME)
        and same(preparation.runtime(),approval['controller_runtime'])
        and same(probe.runtime_identity(),approval['runtime']),'released exact runtime required')
    run=canonical(project/OUTPUT);outside=canonical(project/SUPERVISED)
    require(not run.exists(),'new replay output required; no retry')
    require(outside.is_dir() if worker else not outside.exists(),'fresh coordinator or existing owned worker boundary required')
    bindings=verify_parents(project,approval)
    return dict(project=project,run=run,outside=outside,approval=approval,state=state,bindings=bindings,
        release_sha256=sha_file(release),sidecar_sha256=core.sha(side))


def recheck(context):
    approval=context['approval'];project=context['project']
    require(same(source_state(),context['state']),'source/Git drift')
    require(all(sha_file(ROOT/n)==v for n,v in approval['source_sha256'].items()),'source SHA drift')
    require(sha_file(ROOT/RELEASE)==context['release_sha256'] and sha_file(ROOT/SIDECAR)==context['sidecar_sha256'],'release drift')
    require(same(preparation.runtime(),approval['controller_runtime']) and same(probe.runtime_identity(),approval['runtime']),'runtime drift')
    require(not (project/core.PREPARED/'FAILED.json').exists() and not (project/PROBE/'FAILED.json').exists(),'prerequisite failed')
    require(all(sha_file(path)==value for path,value in context['bindings'].items()),'input SHA drift')


def verify_inner(context):
    run=context['run'];require(not (run/'FAILED.json').exists() and not (run/'REJECTED_COMPLETE.json').exists(),'rejected inner replay')
    consumed={};marker=metadata(run/'COMPLETE.json',bindings=consumed)
    core.exact_fields(marker,('status','kind','files_sha256','runtime_sha256','prepared_complete_sha256',
        'terminal_source_blocks','planned_source_blocks','completed_case_attempts','roster_counts','fitting_authorized'))
    require(marker['status']=='complete' and marker['kind']==core.VERSION
        and marker['runtime_sha256']==context['approval']['runtime_sha256']
        and marker['prepared_complete_sha256']==context['approval']['prepared_complete_sha256']
        and marker['fitting_authorized'] is False and set(marker['files_sha256'])==set(core.ARTIFACTS)
        and marker['terminal_source_blocks']==marker['planned_source_blocks']
        and all(type(marker[k]) is int and marker[k]>=0 for k in ('terminal_source_blocks','planned_source_blocks','completed_case_attempts'))
        and marker['roster_counts'].get('recipients')==320 and marker['roster_counts'].get('problems')==23,
        'full core terminal metadata required')
    require(set(p.name for p in run.iterdir())==set(core.ARTIFACTS)|{'COMPLETE.json'},'unexpected inner artifact inventory')
    for name,pin in marker['files_sha256'].items():
        require(preparation.is_sha(pin) and sha_file(run/name)==pin,'inner output SHA mismatch')
    pin=consumed[str(run/'COMPLETE.json')]
    require(sha_file(run/'COMPLETE.json')==pin,'inner marker changed while consuming artifacts')
    return dict(complete_sha256=pin,marker=marker)


def quarantine(context):
    marker=context['run']/'COMPLETE.json'
    if marker.exists():
        rejected=context['run']/'REJECTED_COMPLETE.json'
        require(not rejected.exists(),'rejected marker already exists')
        canonical(marker).rename(canonical(rejected))


def _wait(path,deadline,bindings=None):
    while time.monotonic()<deadline:
        if path.exists():return metadata(path,bindings=bindings)
        time.sleep(POLL_SECONDS)
    raise TimeoutError('fixed handshake deadline exceeded')


def worker(project):
    context=preflight(project,worker=True);outside=context['outside'];handshake=outside/'worker'
    require(handshake.is_dir(),'owned worker handshake directory required')
    consumed={};manifest=metadata(outside/'manifest.json',bindings=consumed)
    require(manifest.get('release_sha256')==context['release_sha256'] and same(manifest.get('source'),context['state']),
            'worker/coordinator source release differs')
    require(resource.getrlimit(resource.RLIMIT_AS)==(34359738368,34359738368),'parent address-space cap not enforced')
    identity=host.process_identity(os.getpid())
    require(Path(identity['control_group']).name==UNIT,'worker is outside the exact released unit')
    own_unit=host.UserUnit(UNIT,host.Envelope())
    def attest_main():
        live=own_unit.snapshot()
        require(same(live['main_process'],identity),'worker is not the live fixed unit main process')
        zero_baseline(live['cgroup'])
        only_keeper(live)
        return live
    attest_main()
    ready=dict(kind='statement_sample_replay_ready_v1',main_process=identity,
        source=context['state'],release_sha256=context['release_sha256'])
    host.durable_new(handshake/'READY.json',ready)
    try:
        go=_wait(handshake/'GO.json',time.monotonic()+READY_SECONDS,consumed)
        core.exact_fields(go,('kind','ready_sha256','main_process','baseline','runtime_sha256'))
        require(go['kind']=='statement_sample_replay_go_v1' and go['ready_sha256']==sha_file(handshake/'READY.json')
            and same(go['main_process'],identity) and go['runtime_sha256']==context['approval']['runtime_sha256'],
            'wrong authenticated work acknowledgment')
        attest_main()
        baseline=go['baseline'];host.verify_cgroup(baseline,host.Envelope(),identity['pid'])
        zero_baseline(baseline)
        require(baseline['control_group']==identity['control_group'],'worker cgroup differs')
        def operational():
            require(same(host.process_identity(identity['pid']),identity),'worker process identity escaped/reused')
            now=host.read_cgroup(identity['control_group']);host.verify_cgroup(now,host.Envelope(),identity['pid'])
            host.check_events(baseline,now)
        operational();recheck(context)
        inputs=core.load_prepared(context['project'],context['approval']['prepared_complete_sha256'])
        def barrier():
            recheck(context);inputs.recheck()
            require(all(sha_file(p)==s for p,s in consumed.items()),'consumed worker metadata changed')
        def abort():
            path=handshake/'ABORT_REQUEST.json'
            if not path.exists():host.durable_new(path,dict(kind='statement_sample_replay_abort_v1',reason='operational_failure'))
            os._exit(2)  # outside coordinator owns exact cgroup-wide reap
        provenance=dict(prepared_complete_sha256=context['approval']['prepared_complete_sha256'],
            resource_probe_complete_sha256=context['approval']['resource_probe_complete_sha256'],
            source=context['state'],source_sha256=context['approval']['source_sha256'],
            runtime=context['approval']['runtime'],controller_runtime=context['approval']['controller_runtime'],
            release_sha256=context['release_sha256'],unit=UNIT,main_process=identity,baseline=baseline)
        core.run_replay(inputs.plan,context['run'],context['approval']['runtime_sha256'],provenance,
            barrier=barrier,operational_check=operational,terminate_and_reap=abort)
        barrier();operational();inner=verify_inner(context)
        host.durable_new(handshake/'DONE.json',dict(kind='statement_sample_replay_done_v1',main_process=identity,**inner))
        end=time.monotonic()+KEEPER_SECONDS
        while time.monotonic()<end:
            operational()
            if (handshake/'ACK.json').exists():
                ack=metadata(handshake/'ACK.json')
                require(same(ack,dict(kind='statement_sample_replay_ack_v1',done_sha256=sha_file(handshake/'DONE.json'),
                    complete_sha256=inner['complete_sha256'])),'wrong terminal acknowledgment')
                operational();return
            time.sleep(POLL_SECONDS)
        raise TimeoutError('outside audit did not acknowledge live terminal keeper')
    except BaseException as exc:
        try:
            quarantine(context)
            if not (handshake/'ABORT_REQUEST.json').exists():host.durable_new(handshake/'ABORT_REQUEST.json',
                dict(kind='statement_sample_replay_abort_v1',error_type=type(exc).__name__,error=core.diagnostic_summary(str(exc))))
        finally:os._exit(2)


def _retained_success(values):
    host.verify_properties(values,UNIT,host.Envelope(),running=False)
    require(values.get('ActiveState')=='active' and values.get('SubState')=='exited'
        and values.get('MainPID')=='0' and values.get('Result')=='success'
        and values.get('ExecMainCode') in ('1','exited') and values.get('ExecMainStatus')=='0',
        'worker did not exit normally after ACK')


def coordinator(project,*,_unit_factory=host.UserUnit):
    context=preflight(project);outside=context['outside'];outside.mkdir(parents=True,exist_ok=False)
    handshake=outside/'worker';handshake.mkdir();unit=_unit_factory(UNIT,host.Envelope())
    start=time.monotonic();deadline=start+core.SECONDS;first=None;inner=None;last=None;error=None;cleanup_error=None
    expected={};consumed={}
    def write(name,value):
        expected[name]=host.durable_new(outside/name,value)
    write('manifest.json',dict(kind='statement_sample_replay_supervisor_v1',configuration=configuration(),
        source=context['state'],source_sha256=context['approval']['source_sha256'],runtime=context['approval']['runtime'],
        release_sha256=context['release_sha256'],input_sha256=context['bindings'],
        prepared_complete_sha256=context['approval']['prepared_complete_sha256'],
        resource_probe_complete_sha256=context['approval']['resource_probe_complete_sha256']))
    try:
        recheck(context)
        # Preserve the venv's argv[0]; the separately pinned runtime records both
        # this requested executable and its resolved binary SHA.
        require(Path(sys.executable).is_absolute(),'absolute controller executable required')
        unit.start([sys.executable,'-B','-m','scripts.run_zpd_statement_sample_replay',
                    '--project',str(context['project']),'--worker'],ROOT)
        ready=_wait(handshake/'READY.json',min(deadline,time.monotonic()+READY_SECONDS),consumed)
        first=unit.snapshot()
        core.exact_fields(ready,('kind','main_process','source','release_sha256'))
        require(ready['kind']=='statement_sample_replay_ready_v1' and same(ready['main_process'],first['main_process'])
            and same(ready['source'],context['state']) and ready['release_sha256']==context['release_sha256'],
            'READY identity/source does not match live unit')
        only_keeper(first)
        zero_baseline(first['cgroup'])
        write('ready-snapshot.json',first)
        write('worker/GO.json',dict(kind='statement_sample_replay_go_v1',
            ready_sha256=consumed[str(handshake/'READY.json')],main_process=first['main_process'],baseline=first['cgroup'],
            runtime_sha256=context['approval']['runtime_sha256']))
        last_heartbeat=start;journal_hash=hashlib.sha256()
        with (outside/'snapshots.jsonl').open('x',encoding='ascii') as journal:
            while time.monotonic()<deadline:
                require(not (handshake/'ABORT_REQUEST.json').exists(),'worker requested operational abort')
                last=unit.snapshot();require(same(last['main_process'],first['main_process']),'main process identity changed')
                host.check_events(first['cgroup'],last['cgroup'])
                if time.monotonic()-last_heartbeat>=30:
                    host.durable_append(journal,last);journal_hash.update(host.encoded(last));last_heartbeat=time.monotonic()
                if (handshake/'DONE.json').exists():
                    done=metadata(handshake/'DONE.json',bindings=consumed);inner=verify_inner(context)
                    require(same(done,dict(kind='statement_sample_replay_done_v1',main_process=first['main_process'],**inner)),
                            'DONE differs from sealed inner marker')
                    only_keeper(last)
                    recheck(context);require(verify_inner(context)==inner,'inner seal changed during terminal recheck')
                    last=unit.snapshot();host.check_events(first['cgroup'],last['cgroup'])
                    require(same(last['main_process'],first['main_process']),'live keeper changed before ACK')
                    only_keeper(last)
                    write('end-snapshot.json',last)
                    write('worker/ACK.json',dict(kind='statement_sample_replay_ack_v1',
                        done_sha256=consumed[str(handshake/'DONE.json')],complete_sha256=inner['complete_sha256']))
                    break
                time.sleep(POLL_SECONDS)
            else:raise TimeoutError('six-hour outside replay watchdog')
        expected['snapshots.jsonl']=journal_hash.hexdigest()
        exit_deadline=min(deadline,time.monotonic()+KEEPER_SECONDS)
        while time.monotonic()<exit_deadline:
            state=unit.show()
            if state['SubState']=='exited':break
            require(state['ActiveState']=='active' and state['SubState']=='running','abnormal worker exit')
            time.sleep(POLL_SECONDS)
        else:raise TimeoutError('worker did not leave terminal keeper')
        _retained_success(state);write('retained-unit.json',state)
        recheck(context);require(verify_inner(context)==inner,'inner marker drift after worker exit')
    except BaseException as exc:
        error=dict(error_type=type(exc).__name__,error=core.diagnostic_summary(str(exc)))
    finally:
        if getattr(unit,'start_attempted',False):
            try:
                state=unit.show()
                if state['LoadState']!='not-found':
                    require(state['Id']==UNIT,'cleanup unit name differs')
                    cg=first['properties']['ControlGroup'] if first is not None else state['ControlGroup']
                    require(state['ControlGroup']==cg,'cleanup cgroup identity changed')
                    host.cgroup_path(cg)
                    if state['MainPID']!='0':
                        identity=host.process_identity(int(state['MainPID']))
                        require(identity['control_group']==cg,'cleanup main escaped owned cgroup')
                        if first is not None:require(same(identity,first['main_process']),'PID reuse before exact-unit stop')
                    # Once ownership is established, neither a property mismatch
                    # nor a failed evidence write may skip exact-unit cleanup.
                    try:
                        write('before-stop.json',state)
                        if state['MainPID']!='0':
                            try:live=host.read_cgroup(cg)
                            except Exception as exc:
                                write('before-stop-live.json',dict(available=False,properties=state,
                                    error=dict(error_type=type(exc).__name__,error=core.diagnostic_summary(str(exc)))))
                                raise
                            write('before-stop-live.json',dict(available=True,properties=state,cgroup=live,
                                main_process=identity,monotonic=time.monotonic()))
                        host.verify_properties(state,UNIT,host.Envelope(),running=False)
                    finally:
                        unit.stop();empty=unit.verify_empty(cg)
                        write('cleanup.json',dict(empty=True,unit=UNIT,properties=empty))
                else:
                    require(first is None,'owned unit disappeared before cleanup')
                    write('before-stop.json',state);write('cleanup.json',dict(not_created=True,unit=UNIT))
            except BaseException as exc:cleanup_error=dict(error_type=type(exc).__name__,error=core.diagnostic_summary(str(exc)))
    if error is not None or cleanup_error is not None:
        quarantine(context)
        host.durable_new(outside/'FAILED.json',dict(error=error,cleanup_error=cleanup_error,inner_accepted=False,
            fitting_authorized=False,retries=0));raise RuntimeError('released replay failed; inspect bounded FAILED metadata')
    try:
        require(inner is not None,'no accepted inner completion')
        report=dict(status='complete',unit=UNIT,inner=inner,elapsed_seconds=time.monotonic()-start,
            cleanup_verified=True,fitting_authorized=False)
        write('report.json',report)
        # Pin handshake bytes when consumed and journal bytes when appended;
        # never retroactively bless an unexpected file or changed output.
        for path,pin in consumed.items():expected[str(Path(path).relative_to(outside))]=pin
        actual={str(p.relative_to(outside)) for p in outside.rglob('*') if p.is_file()}
        require(actual==set(expected),'unexpected outer artifact inventory')
        require(all(sha_file(outside/n)==v for n,v in expected.items()),'outer output drift')
        recheck(context);require(verify_inner(context)==inner,'final inner drift')
        require(not (handshake/'ABORT_REQUEST.json').exists(),'late worker abort')
        recheck(context)
        host.durable_new(outside/'COMPLETE.json',dict(status='complete',kind='statement_sample_replay_supervisor_v1',
            files_sha256=expected,inner_complete_sha256=inner['complete_sha256'],
            prepared_complete_sha256=context['approval']['prepared_complete_sha256'],
            resource_probe_complete_sha256=context['approval']['resource_probe_complete_sha256'],
            cleanup_verified=True,fitting_authorized=False))
        return report
    except BaseException as exc:
        marker=outside/'COMPLETE.json'
        if marker.exists():canonical(marker).rename(canonical(outside/'REJECTED_COMPLETE.json'))
        quarantine(context)
        host.durable_new(outside/'FAILED.json',dict(error_type=type(exc).__name__,error=core.diagnostic_summary(str(exc)),
            inner_accepted=False,fitting_authorized=False));raise


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args()
    try:
        if args.worker:worker(args.project)
        else:coordinator(args.project)
    except Exception as exc:
        # No raw diagnostic traceback or submitted-output side channel.
        print(json.dumps(dict(error_type=type(exc).__name__,error=core.diagnostic_summary(str(exc))),ensure_ascii=True),file=sys.stderr)
        raise SystemExit(2)


if __name__=='__main__':main()
