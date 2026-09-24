"""Authenticated observed replay -> immutable full-universe feedback bridge.

No execution, candidate/target/label access, feature computation, fit or readiness
decision. External authority must come from a separately reviewed consumer
release, never from hashes chosen by an artifact under inspection. Inner COMPLETE
alone is insufficient. Filesystem loading has no production command-line path.
Categorical reconstruction reuses the frozen replay validator/aggregate; this
bridge is not an independently implemented scientific result auditor.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from scripts import prepare_zpd_statement_samples as preparation
from scripts import run_zpd_statement_sample_replay as launcher
from scripts import zpd_statement_sample_replay as replay
from scripts import zpd_statement_sample_progress as progress
from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector

ROOT=Path(__file__).resolve().parents[1]
PROJECT=Path('/home/cdw/VSCode/zpd-apr')
PREPARED=replay.PREPARED
INNER=launcher.OUTPUT
OUTER=launcher.SUPERVISED
VERSION='authenticated_observed_statement_replay_bridge_v1'
OUTER_REQUIRED=frozenset(('manifest.json','report.json','ready-snapshot.json','end-snapshot.json',
    'snapshots.jsonl','retained-unit.json','before-stop.json','cleanup-binding.json','cleanup.json',
    'worker/READY.json','worker/GO.json','worker/DONE.json','worker/ACK.json'))
OUTER_OPTIONAL=frozenset(('before-stop-live.json',))
SOURCE_FILES=tuple(sorted(set((*launcher.SOURCES,
    'scripts/zpd_statement_sample_progress.py','tests/test_zpd_statement_sample_progress.py',
    'scripts/zpd_repair_directed_history.py','scripts/zpd_history_action_encoder.py',
    'scripts/zpd_statement_sample_replay_inputs.py','tests/test_zpd_statement_sample_replay_inputs.py',
    'analysis_protocols/zpd-statement-sample-progress-prospective-20260924.md'))))


require=replay.require
same=replay.same
encoded=replay.encoded


@dataclass(frozen=True)
class ReplayAuthority:
    """Pins supplied by the consumer's external release; this class grants none."""
    outer_complete_sha256: str
    prepared_complete_sha256: str
    runtime_sha256: str
    replay_release_sha256: str

    def __post_init__(self):
        require(all(preparation.is_sha(v) for v in vars(self).values()),'external exact SHA256 pins required')
        require(self.prepared_complete_sha256==replay.PREPARED_COMPLETE_SHA,'fixed prepared authority required')


@dataclass(frozen=True)
class ReplayFeedback:
    universes: object
    vectors: object
    unavailable: object
    source_to_execution: object
    roster_json: bytes
    coverage_json: bytes
    folds_json: bytes
    bindings_json: bytes

    def roster(self):return replay.decode_json(self.roster_json)
    def coverage(self):return replay.decode_json(self.coverage_json)
    def folds(self):return replay.decode_json(self.folds_json)

    def observations(self):
        """Return detached original current/prior/certified-donor rows, never targets."""
        body=self.roster();sources={s['submission_id']:s for s in body['sources']};result=[]
        def historical(ids):
            return [dict(code=bytes.fromhex(sources[i]['source_hex']).decode('utf-8'),
                verdict=sources[i]['verdict'],timestamp=sources[i]['timestamp'],language=sources[i]['language']) for i in ids]
        for row in body['recipients']:
            current=sources[row['current_source_id']]
            result.append(dict(example_id=row['example_id'],user_id=row['user_id'],problem_id=row['problem_id'],
                bank_id=row['bank_id'],fold=row['fold'],current_code=bytes.fromhex(current['source_hex']).decode('utf-8'),
                current_verdict=current['verdict'],current_timestamp=row['current_cutoff'],
                current_source_sha256=current['source_sha256'],history=historical(row['prior_source_ids']),
                donor_history=historical(row['donor_source_ids']),donor_example_id=row['donor_example_id'],
                donor_user_id=row['donor_user_id'],observed_source_ids=[row['current_source_id'],*row['prior_source_ids']],
                donor_source_ids=list(row['donor_source_ids'])))
        return result


def _outer_marker(value,authority):
    replay.exact_fields(value,('status','kind','files_sha256','inner_complete_sha256','prepared_complete_sha256',
        'resource_probe_complete_sha256','cleanup_verified','fitting_authorized'))
    require(value['status']=='complete' and value['kind']=='statement_sample_replay_supervisor_v1'
        and value['prepared_complete_sha256']==authority.prepared_complete_sha256
        and value['cleanup_verified'] is True and value['fitting_authorized'] is False
        and preparation.is_sha(value['inner_complete_sha256']) and preparation.is_sha(value['resource_probe_complete_sha256']),
        'accepted outer supervisor completion required')
    files=value['files_sha256']
    require(type(files) is dict and OUTER_REQUIRED<=set(files)<=OUTER_REQUIRED|OUTER_OPTIONAL
        and all(preparation.is_sha(v) for v in files.values()),'exact outer filename allowlist required')
    return files


def _fixed_marker(value,files):
    require(type(value) is dict and type(value.get('files_sha256')) is dict
        and set(value['files_sha256'])==set(files)
        and all(preparation.is_sha(v) for v in value['files_sha256'].values()),'exact fixed artifact inventory required')
    return value['files_sha256']


def _rows(raw):
    require(type(raw) is bytes,'immutable journal bytes required')
    if not raw:return []
    require(raw.endswith(b'\n'),'complete journal line terminator required')
    lines=raw.split(b'\n')[:-1]
    require(all(lines),'blank journal rows forbidden')
    return [replay.decode_json(line) for line in lines]


def _cgroup_types(value):
    """Reject numeric coercion in saved accounting before host comparisons."""
    require(type(value) is dict and type(value.get('control_group')) is str,'saved cgroup object required')
    for name in ('processes','threads'):
        ids=value.get(name)
        require(type(ids) is list and all(type(v) is int and v>0 for v in ids)
            and ids==sorted(set(ids)),'strict unique saved PID/thread list required')
    for name in ('memory.events','pids.events','cgroup.events'):
        counters=value.get(name)
        require(type(counters) is dict and counters and all(type(k) is str and k
            and type(v) is int and v>=0 for k,v in counters.items()),'strict nonnegative saved event counters required')
    if value.get('memory.events.local') is not None:
        counters=value['memory.events.local']
        require(type(counters) is dict and counters and all(type(k) is str and k
            and type(v) is int and v>=0 for k,v in counters.items()),'strict local event counters required')


def _snapshot(value,identity,*,keeper=False):
    replay.exact_fields(value,('monotonic','properties','cgroup','main_process'))
    require(replay.finite_nonnegative(value['monotonic']) and same(value['main_process'],identity),
            'accepted live main identity/time differs')
    _cgroup_types(value['cgroup'])
    launcher.host.verify_properties(value['properties'],launcher.UNIT,launcher.host.Envelope())
    require(value['properties']['MainPID']==str(identity['pid'])
        and value['properties']['ControlGroup']==identity['control_group']==value['cgroup']['control_group'],
        'accepted property/cgroup/main identity differs')
    launcher.host.verify_cgroup(value['cgroup'],launcher.host.Envelope(),identity['pid'])
    if keeper:launcher.only_keeper(value)


def _cleanup_binding(outer,identity):
    """Check serialized terminal ownership evidence, without live OS probes."""
    value=outer['cleanup-binding.json'];first=outer['ready-snapshot.json']['properties']
    before=outer['before-stop.json'];reported=before['ControlGroup']
    replay.exact_fields(value,('unit','recorded_control_group','reported_control_group',
        'first_main_process','start_timestamp_monotonic','dead_cgroup_observation','live_main_process'))
    stamp=value['start_timestamp_monotonic']
    require(value['unit']==launcher.UNIT and value['recorded_control_group']==identity['control_group']
        and value['reported_control_group']==reported and same(value['first_main_process'],identity)
        and type(stamp) is str and stamp.isdigit() and int(stamp)>0
        and all(p.get('ExecMainStartTimestampMonotonic')==stamp for p in
            (first,outer['end-snapshot.json']['properties'],before,outer['retained-unit.json']))
        and value['live_main_process'] is None,'saved cleanup ownership/start identity differs')
    require(type(reported) is str and reported in ('',identity['control_group']),
            'saved cleanup cgroup path changed')
    dead=value['dead_cgroup_observation']
    if reported:
        require(dead is None,'reported live cgroup cannot use vanished-cgroup evidence')
    else:
        replay.exact_fields(dead,('present','cgroup'))
        require(type(dead['present']) is bool,'strict recorded-cgroup presence required')
        if dead['present']:
            cg=dead['cgroup'];require(type(cg) is dict,'recorded empty-cgroup observation required')
            _cgroup_types(cg)
            require(cg.get('control_group')==identity['control_group'] and same(cg.get('processes'),[])
                and same(cg.get('threads'),[]) and type(cg.get('cgroup.events')) is dict
                and type(cg['cgroup.events'].get('populated')) is int and cg['cgroup.events']['populated']==0,
                'recorded cgroup remains populated or lacks exact empty accounting')
            launcher.host.check_events(outer['ready-snapshot.json']['cgroup'],cg)
        else:require(dead['cgroup'] is None,'absent recorded cgroup cannot contain invented accounting')


def _metadata_agreement(outer,inner,authority,plan,outer_marker,inner_marker):
    manifest=outer['manifest.json'];inner_manifest=inner['manifest.json']
    replay.exact_fields(manifest,('kind','configuration','source','source_sha256','runtime','release_sha256',
        'input_sha256','prepared_complete_sha256','resource_probe_complete_sha256'))
    require(manifest['kind']=='statement_sample_replay_supervisor_v1'
        and same(manifest['configuration'],launcher.configuration())
        and manifest['release_sha256']==authority.replay_release_sha256
        and manifest['prepared_complete_sha256']==authority.prepared_complete_sha256
        and manifest['resource_probe_complete_sha256']==outer_marker['resource_probe_complete_sha256']
        and replay.sha(encoded(manifest['runtime']))==authority.runtime_sha256
        and type(manifest['source_sha256']) is dict and set(manifest['source_sha256'])==set(launcher.SOURCES)
        and all(preparation.is_sha(v) for v in manifest['source_sha256'].values()),'outer runtime/release/source contract differs')
    input_pins=manifest['input_sha256']
    require(type(input_pins) is dict and all(preparation.is_sha(v) for v in input_pins.values()),'outer input bindings required')
    for name in input_pins:
        path=Path(name)
        require(type(name) is str and path.is_absolute() and str(path)==name and '..' not in path.parts
            and (name in {str(PROJECT/PREPARED/n) for n in (*preparation.ARTIFACTS,'COMPLETE.json')}
                 or path.is_relative_to(PROJECT/launcher.PROBE)
                 and (str(path.relative_to(PROJECT/launcher.PROBE))=='COMPLETE.json'
                      or launcher._fixed_probe_name(str(path.relative_to(PROJECT/launcher.PROBE))))),
            'outer prerequisite path outside fixed source-only boundary')
    replay.exact_fields(manifest['source'],('revision','tree'))
    require(all(type(v) is str and len(v)==40 and all(c in '0123456789abcdef' for c in v)
                for v in manifest['source'].values()),'Git revision/tree identity required')
    replay.exact_fields(inner_manifest,('kind','configuration','runtime_sha256','provenance','synthetic_runner'))
    p=inner_manifest['provenance']
    replay.exact_fields(p,('prepared_complete_sha256','resource_probe_complete_sha256','source','source_sha256',
        'runtime','controller_runtime','release_sha256','unit','main_process','baseline'))
    require(inner_manifest['kind']==replay.VERSION and same(inner_manifest['configuration'],replay.configuration())
        and inner_manifest['runtime_sha256']==authority.runtime_sha256 and inner_manifest['synthetic_runner'] is False
        and same(p['controller_runtime'],preparation.RUNTIME) and p['unit']==launcher.UNIT
        and all(same(p[k],manifest[k]) for k in ('prepared_complete_sha256','resource_probe_complete_sha256',
            'source','source_sha256','runtime','release_sha256')),'inner provenance differs from accepted outer')
    first,last=outer['ready-snapshot.json'],outer['end-snapshot.json']
    identity=p['main_process']
    replay.exact_fields(identity,('pid','start_ticks','control_group'))
    require(type(identity['pid']) is int and identity['pid']>0
        and type(identity['start_ticks']) is int and identity['start_ticks']>=0
        and type(identity['control_group']) is str and Path(identity['control_group']).name==launcher.UNIT,
        'strict process start identity required')
    for snap in (first,last):
        _snapshot(snap,identity,keeper=True)
    launcher.zero_baseline(first['cgroup']);launcher.host.check_events(first['cgroup'],last['cgroup'])
    require(same(p['baseline'],first['cgroup']),'worker baseline differs from accepted cgroup')
    launcher._retained_success(outer['retained-unit.json'])
    launcher._retained_success(outer['before-stop.json'])
    _cleanup_binding(outer,identity)
    cleanup=outer['cleanup.json']
    replay.exact_fields(cleanup,('empty','unit','properties'))
    require(cleanup.get('empty') is True and cleanup.get('unit')==launcher.UNIT
        and cleanup.get('properties',{}).get('ActiveState')=='inactive'
        and cleanup['properties'].get('MainPID')=='0','owned-unit cleanup not accepted')
    counts=plan.to_json();roster=replay.decode_json(plan.roster_json)
    replay.exact_fields(inner_marker,('status','kind','files_sha256','runtime_sha256','prepared_complete_sha256',
        'terminal_source_blocks','planned_source_blocks','completed_case_attempts','roster_counts','fitting_authorized'))
    expected=dict(status='complete',kind=replay.VERSION,runtime_sha256=authority.runtime_sha256,
        prepared_complete_sha256=authority.prepared_complete_sha256,terminal_source_blocks=counts['planned_source_blocks'],
        planned_source_blocks=counts['planned_source_blocks'],completed_case_attempts=counts['planned_case_attempts'],
        roster_counts=roster['counts'],fitting_authorized=False)
    require(same({k:inner_marker[k] for k in inner_marker if k!='files_sha256'},expected),
            'complete full-cohort replay counts differ')
    report=outer['report.json'];reference=dict(complete_sha256=outer_marker['inner_complete_sha256'],marker=inner_marker)
    replay.exact_fields(report,('status','unit','inner','elapsed_seconds','cleanup_verified','fitting_authorized'))
    require(report.get('status')=='complete' and report.get('unit')==launcher.UNIT
        and same(report.get('inner'),reference) and report.get('cleanup_verified') is True
        and report.get('fitting_authorized') is False and replay.finite_nonnegative(report.get('elapsed_seconds')),
        'outer report did not accept exact inner marker')
    return identity,reference


def authenticate_blobs(blobs,authority):
    """Authenticate exact supplied bytes. No file I/O or release manufacture."""
    require(isinstance(authority,ReplayAuthority) and type(blobs) is dict
        and all(type(k) is str and type(v) is bytes for k,v in blobs.items()),'exact externally pinned byte bundle required')
    consumed={}
    def read(name,pin):
        require(name in blobs and preparation.is_sha(pin),'missing authenticated artifact: '+name)
        raw=blobs[name];require(replay.sha(raw)==pin,'changed authenticated artifact: '+name)
        consumed[name]=pin;return replay.decode_json(raw)
    outer_marker=read(OUTER+'/COMPLETE.json',authority.outer_complete_sha256)
    outer_files=_outer_marker(outer_marker,authority)
    inner_marker=read(INNER+'/COMPLETE.json',outer_marker['inner_complete_sha256'])
    inner_files=_fixed_marker(inner_marker,replay.ARTIFACTS)
    prepared_marker=read(PREPARED+'/COMPLETE.json',authority.prepared_complete_sha256)
    prepared_files=_fixed_marker(prepared_marker,preparation.ARTIFACTS)
    require(same({k:prepared_marker[k] for k in prepared_marker if k!='files_sha256'},dict(status='complete',
        recipients=preparation.COUNTS['recipients'],problems=preparation.COUNTS['problems'],
        execution_authorized=False,fitting_authorized=False,excluded_recipients=0)),'fixed source preparation marker required')
    expected=set(consumed)|{OUTER+'/'+n for n in outer_files}|{INNER+'/'+n for n in inner_files}|{PREPARED+'/'+n for n in prepared_files}
    require(set(blobs)==expected,'unexpected or missing files outside fixed replay bundle')
    prepared={n:read(PREPARED+'/'+n,pin) for n,pin in prepared_files.items()}
    plan=replay.build_plan(prepared)
    parsed={}
    for base,files in ((OUTER,outer_files),(INNER,inner_files)):
        parsed[base]={}
        for name,pin in files.items():
            if name.endswith('.jsonl'):
                raw=blobs[base+'/'+name];require(replay.sha(raw)==pin,'journal SHA mismatch')
                consumed[base+'/'+name]=pin;parsed[base][name]=_rows(raw)
            else:parsed[base][name]=read(base+'/'+name,pin)
    outer,inner=parsed[OUTER],parsed[INNER]
    identity,reference=_metadata_agreement(outer,inner,authority,plan,outer_marker,inner_marker)
    require(all(outer['manifest.json']['input_sha256'].get(str(PROJECT/name))==consumed[name]
                for name in consumed if name.startswith(PREPARED+'/')),'outer does not bind exact consumed preparation')
    require(outer['manifest.json']['input_sha256'].get(str(PROJECT/launcher.PROBE/'COMPLETE.json'))
        ==outer_marker['resource_probe_complete_sha256'],'outer probe authority differs')
    require(all(outer['manifest.json']['source_sha256'][n]==v
                for n,v in prepared['manifest.json']['source_sha256'].items()),'prepared/replay source closure differs')
    require(same(inner['tasks.json'],plan.to_json()),'saved task ledger differs from exact observed preparation')
    records=inner['completions.jsonl']
    vectors,coverage=replay.aggregate(plan,records,authority.runtime_sha256)
    require([r['block_index'] for r in records]==sorted(r['block_index'] for r in records),
            'journal violated sequential four-block schedule')
    counts=plan.to_json()
    require(len(records)==counts['planned_source_blocks'] and coverage['completed_source_blocks']==len(records)
        and coverage['completed_case_attempts']==counts['planned_case_attempts'],'incomplete operational replay cannot be feedback authority')
    require(same(inner['vectors.json'],dict(runtime_sha256=authority.runtime_sha256,
        usable_only_with_valid_terminal_COMPLETE=True,vectors=vectors)),'saved vectors/stability differ from categorical journal')
    require(same(inner['coverage.json'],coverage),'saved source/membership coverage differs from journal')
    expected_status=dict(phase='complete',current_block=None,terminal_source_blocks=len(records),
        planned_source_blocks=counts['planned_source_blocks'],completed_case_attempts=counts['planned_case_attempts'],
        journaled_case_attempts=counts['planned_case_attempts'],planned_case_attempts=counts['planned_case_attempts'],
        unavailable_unique_identities=counts['unavailable_unique_identities'],roster_counts=counts['roster_counts'])
    require(same(inner['STATUS.json'],expected_status),'terminal case/source status differs')
    ready=outer['worker/READY.json'];go=outer['worker/GO.json'];done=outer['worker/DONE.json'];ack=outer['worker/ACK.json']
    require(same(ready,dict(kind='statement_sample_replay_ready_v1',main_process=identity,
        source=outer['manifest.json']['source'],release_sha256=authority.replay_release_sha256)),'READY linkage differs')
    require(same(go,dict(kind='statement_sample_replay_go_v1',ready_sha256=outer_files['worker/READY.json'],
        main_process=identity,baseline=outer['ready-snapshot.json']['cgroup'],runtime_sha256=authority.runtime_sha256)),'GO linkage differs')
    require(same(done,dict(kind='statement_sample_replay_done_v1',main_process=identity,**reference)),'DONE linkage differs')
    require(same(ack,dict(kind='statement_sample_replay_ack_v1',done_sha256=outer_files['worker/DONE.json'],
        complete_sha256=outer_marker['inner_complete_sha256'])),'ACK linkage differs')
    for snap in outer['snapshots.jsonl']:
        _snapshot(snap,identity)
        launcher.host.check_events(outer['ready-snapshot.json']['cgroup'],snap['cgroup'])
    if 'before-stop-live.json' in outer:
        saved=outer['before-stop-live.json']
        require(saved.get('available') is True,'unavailable final accounting cannot authenticate feedback')
        _snapshot({k:v for k,v in saved.items() if k!='available'},identity,keeper=True)
        launcher.host.check_events(outer['ready-snapshot.json']['cgroup'],saved['cgroup'])
    universe={}
    for problem in prepared['samples.json']['problems']:
        pid=problem['problem_id'];universe[pid]=progress.Universe(pid,problem['sample_set_sha256'],authority.runtime_sha256,
            tuple(f'statement-sample:{pid}:{sample["index"]}' for sample in problem['samples']))
    converted={};unavailable={};source_to_execution={}
    for task,row in zip(plan.tasks,vectors,strict=True):
        unavailable[task.identity]=tuple(row['feedback_unavailable_reasons'])
        for source in task.submission_ids:source_to_execution[source]=task.identity
        if task.eligible:
            blocks=tuple(ExecutionBlock(b['workers'],b['sample_set_sha256'],b['runtime_sha256'],
                tuple(tuple(pair) for pair in b['outcomes']),b['complete'],b['source_sha256']) for b in row['blocks'])
            vector=ExecutionVector(task.source_sha256,task.sample_set_sha256,authority.runtime_sha256,
                tuple(c.case_id for c in task.cases),blocks)
            require(vector.stable_outcomes==(tuple(row['stable_verdicts']) if row['stable'] else None),'converted stability differs')
            converted[task.identity]=vector
    require(set(blobs)==set(consumed) and all(replay.sha(blobs[n])==v for n,v in consumed.items()),
            'input bundle changed during authentication')
    return ReplayFeedback(MappingProxyType(universe),MappingProxyType(converted),MappingProxyType(unavailable),
        MappingProxyType(source_to_execution),plan.roster_json,encoded(coverage),encoded(prepared['folds.json']),encoded(consumed))


@dataclass
class LoadedReplay:
    feedback: ReplayFeedback
    reader: preparation.BoundReader
    source_sha256: dict

    def recheck(self):
        _filesystem_inventory(self.reader.root,self.reader.bindings)
        self.reader.recheck()
        require(all(launcher.sha_file(ROOT/n)==v for n,v in self.source_sha256.items()),'consumer source changed')
        # A source-hash consumer may expose artifact drift; recheck consumed
        # bytes, not only their names, after those consumers as well.
        self.reader.recheck()
        # Rejection markers or extra files may appear during terminal hashing.
        # Check the fixed literal directories again after those consumers.
        _filesystem_inventory(self.reader.root,self.reader.bindings)


def _filesystem_inventory(project,names):
    """Only four known directories, and only after an authenticated outer pin."""
    names=set(names)
    for base in (PREPARED,INNER,OUTER):
        for flag in ('FAILED.json','REJECTED_COMPLETE.json'):
            require(not (project/base/flag).exists(),'replay authority was rejected')
        directory=preparation.canonical(project/base)
        require(directory.is_dir(),'missing fixed replay directory')
        expected={n[len(base)+1:].split('/')[0] for n in names if n.startswith(base+'/')}
        entries=list(directory.iterdir())
        require({p.name for p in entries}==expected,'unexpected or missing fixed replay directory entry')
        for path in entries:
            preparation.canonical(path)
            if base==OUTER and path.name=='worker':
                require(path.is_dir(),'fixed worker directory required')
                children=list(path.iterdir())
                require({p.name for p in children}=={n[len(base+'/worker/'):] for n in names
                    if n.startswith(base+'/worker/')},'unexpected or missing fixed worker entry')
                require(all(preparation.canonical(p).is_file() for p in children),'regular worker artifacts required')
            else:require(path.is_file(),'regular fixed replay artifact required')


def load_feedback(project,authority,*,source_sha256):
    """Fixed-path adapter; external consumer must separately certify this source."""
    require(isinstance(authority,ReplayAuthority),'external replay authority required')
    project=preparation.canonical(project)
    require(project==PROJECT and preparation.canonical(ROOT).is_relative_to(project/'.runtime')
        and ROOT!=project/'.runtime','fixed project and consumer runtime snapshot required')
    require(type(source_sha256) is dict and set(source_sha256)==set(SOURCE_FILES)
        and all(preparation.is_sha(v) and launcher.sha_file(ROOT/n)==v for n,v in source_sha256.items()),
        'external exact consumer source closure required')
    allowed={OUTER+'/COMPLETE.json',INNER+'/COMPLETE.json',PREPARED+'/COMPLETE.json'}
    allowed|={OUTER+'/'+n for n in OUTER_REQUIRED|OUTER_OPTIONAL}
    allowed|={INNER+'/'+n for n in replay.ARTIFACTS}|{PREPARED+'/'+n for n in preparation.ARTIFACTS}
    reader=preparation.BoundReader(project,allowed);blobs={}
    def read(name,pin):
        raw=reader.read(name,pin);blobs[name]=raw;return replay.decode_json(raw)
    # No discovery or body read precedes authentication of this external pin.
    outer=read(OUTER+'/COMPLETE.json',authority.outer_complete_sha256);outer_files=_outer_marker(outer,authority)
    for base in (PREPARED,INNER,OUTER):
        for name in ('FAILED.json','REJECTED_COMPLETE.json'):
            require(not (project/base/name).exists(),'rejected replay cannot supply feedback')
    expected={OUTER+'/COMPLETE.json',INNER+'/COMPLETE.json',PREPARED+'/COMPLETE.json'}
    expected|={OUTER+'/'+n for n in outer_files}|{INNER+'/'+n for n in replay.ARTIFACTS}
    expected|={PREPARED+'/'+n for n in preparation.ARTIFACTS}
    _filesystem_inventory(project,expected)
    inner=read(INNER+'/COMPLETE.json',outer['inner_complete_sha256']);inner_files=_fixed_marker(inner,replay.ARTIFACTS)
    prepared=read(PREPARED+'/COMPLETE.json',authority.prepared_complete_sha256);prepared_files=_fixed_marker(prepared,preparation.ARTIFACTS)
    for base,files in ((OUTER,outer_files),(INNER,inner_files),(PREPARED,prepared_files)):
        for name,pin in files.items():blobs[base+'/'+name]=reader.read(base+'/'+name,pin)
    feedback=authenticate_blobs(blobs,authority)
    replay_sources=replay.decode_json(blobs[OUTER+'/manifest.json'])['source_sha256']
    require(all(source_sha256[n]==v for n,v in replay_sources.items()),
            'consumer uses changed replay-validator dependency sources')
    loaded=LoadedReplay(feedback,reader,dict(source_sha256));loaded.recheck()
    return loaded


if __name__=='__main__':raise SystemExit('No production CLI: a separately released readiness consumer must supply external authority.')
