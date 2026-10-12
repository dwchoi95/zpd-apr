"""Public-only, parameter-free execution selection on frozen candidate banks.

Preparation and selection import only the standard library and cannot execute
candidate code. Production execution is a separate, sandboxed Linux worker.
Private assessment labels are read only AFTER all choices have been sealed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

VERSION = 'public_candidate_selection_v1'
PROTOCOL = 'analysis_protocols/zpd-public-candidate-selection-20261012.json'
UNIT = 'zpd-public-candidates-20261012-v1.service'
OUTPUT = 'outputs/zpd-public-candidates-20261012/run-v1'
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
PREPARED = 'outputs/zpd-statement-sample-feedback-20260924/prepared-v1/'
RUN = 'archive/zpd-bank-topset-run-20260925/run-v1/'
PINS = {
    PREPARED+'COMPLETE.json': '161436b47e020e990071413c6e5645811323705ae5fa7c7f0eb684a9b6943caf',
    PREPARED+'samples.json': 'a6a0fd1c55c1be458f40f269e49e7a250c9a55bc1a5ad7b1638c8f7d5c73b491',
    PREPARED+'roster.json': '22025ebad2f6989f74601c5a3a27a8648db3f75ff7e44d8c08f7b8a55b78d024',
    RUN+'COMPLETE.json': '8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf',
    RUN+'predictions.json': '29d6dfb422a5f6fc4519678a15ed236a5b819f5dd986f95fab1ca66c2c8349eb',
    'outputs/zpd-repair-development-20260918/run-v1/generation/banks.jsonl': '857410476ca9e9f0665341b1f174c7975977ded29a525e56bf02172ca07375b0',
    'outputs/zpd-repair-risk-development-20260923/run-v1/banks.jsonl': '3769662063e39e7115e3be83ec17d50b57fa17dc65a6c9159ada5b8f371d00fc',
}
LABEL_PATH = 'outputs/zpd-repair-feedback-20260924/prepared-v1/assessment/all320-labels.json'
LABEL_SHA = '97dcfbb2b70eb2e7dac7eb93a0ec0722630fa74baefacbde747fcf79a98691f4'
METHODS = ('H','Jm','HS','U','L','CF','C_joint','structural_C','lexical_C',
           'first_attempt','shared_H_HS','shared_H_Jm','shared_H_CF','noop')
ARTIFACTS = frozenset(('manifest.json','completions.jsonl','public-vectors.json','predictions.json',
                      'selection-diagnostics.json','PREDICTIONS_COMPLETE.json','report.json','STATUS.json'))


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode()+b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    raw = encoded(value)
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return sha(raw)


def status_write(path, value):
    temporary = Path(path).with_suffix('.partial')
    write_new(temporary, value)
    temporary.replace(path)


def read_pinned(path, digest):
    raw = Path(path).read_bytes()
    require(sha(raw) == digest, 'input SHA mismatch: '+str(path))
    return ([json.loads(line) for line in raw.splitlines() if line.strip()]
            if str(path).endswith('.jsonl') else json.loads(raw))


def stable_mask(blocks, case_ids):
    """Unknown, inconsistent, missing, duplicate or incomplete blocks never pass."""
    require(len(set(case_ids)) == len(case_ids), 'duplicate case IDs')
    if not case_ids or len(blocks) != 4:
        return None
    if sorted(b['block_index'] for b in blocks) != [0,1,2,3]:
        return None
    vectors = []
    for block in sorted(blocks, key=lambda b: b['block_index']):
        pairs = block['outcomes']
        if (not block['complete'] or [p[0] for p in pairs] != case_ids
                or any(p[1] not in {'AC','WA','CE','RE','TLE'} for p in pairs)):
            return None
        vectors.append([p[1] for p in pairs])
    return [v == 'AC' for v in vectors[0]] if all(v == vectors[0] for v in vectors) else None


def choose(scores, masks, noop, fallback):
    """All constraints are public. No historical/future/private label input."""
    require(set(scores) == set(masks) and noop in scores and fallback in scores,
            'exact candidate coverage including noop and fallback required')
    require(all(type(v) in (float,int) and math.isfinite(v) for v in scores.values()),
            'finite frozen scores required')
    current = masks[noop]
    if current is None or not current:
        return fallback, dict(fallback=True, reason='current_public_unavailable', safe=[], top=[])
    require(all(type(x) is bool for x in current), 'boolean current mask required')
    safe = []
    for cid, mask in masks.items():
        if mask is None:
            continue
        require(len(mask) == len(current) and all(type(x) is bool for x in mask),
                'matched sample universe and boolean masks required')
        if all(not before or after for before,after in zip(current,mask)):
            safe.append(cid)
    require(noop in safe, 'current must preserve its identical observation')
    maximum = max(sum(masks[c]) for c in safe)
    top = sorted(c for c in safe if sum(masks[c]) == maximum)
    winner = min(top, key=lambda c: (-scores[c], c))
    return winner, dict(fallback=False, reason=None, safe=sorted(safe), top=top,
                        current_passes=sum(current), selected_passes=maximum)


def prepare(project, output):
    project, output = Path(project), Path(output)
    require(not output.exists(), 'preparation already exists; no overwrite')
    data = {name: read_pinned(project/name, pin) for name,pin in PINS.items()}
    complete = data[PREPARED+'COMPLETE.json']
    require(complete['status']=='complete' and all(
        complete['files_sha256'][n] == PINS[PREPARED+n] for n in ('samples.json','roster.json')),
        'prepared completion chain differs')
    terminal = data[RUN+'COMPLETE.json']
    require(terminal['status']=='complete' and terminal['files_sha256']['predictions.json']==PINS[RUN+'predictions.json'],
            'frozen score completion chain differs')
    predictions = data[RUN+'predictions.json']
    roster = data[PREPARED+'roster.json']
    recipients = {r['example_id']:r for r in roster['recipients']}
    originals = {s['submission_id']:s for s in roster['sources']}
    banks = {}
    for name,rows in data.items():
        if not name.endswith('banks.jsonl'):
            continue
        for row in rows:
            require(row['bank_id'] not in banks, 'duplicate input bank')
            banks[row['bank_id']] = row
    samples = {}
    for problem in data[PREPARED+'samples.json']['problems']:
        pid = problem['problem_id']; cases = []
        for item in problem['samples']:
            for field in ('input','output'):
                raw = bytes.fromhex(item[field+'_hex'])
                require(sha(raw)==item[field+'_sha256'], 'sample byte identity differs')
                raw.decode('utf-8', errors='strict')
            cases.append(dict(case_id=f"statement-sample:{pid}:{item['index']}",
                              input_hex=item['input_hex'], output_hex=item['output_hex']))
        samples[pid] = dict(sample_set_sha256=problem['sample_set_sha256'], cases=cases)
    tasks = {}; cohort = []
    for pred in predictions:
        ex = pred['example_id']; row = banks[pred['bank_id']]; rec = recipients[ex]
        source = row['current_source'].encode('utf-8'); noop = sha(source)
        require(pred['choices']['noop']==noop and rec['bank_id']==pred['bank_id']
                and rec['problem_id']==pred['problem_id']==row['problem_id']
                and rec['fold']==pred['fold'] and rec['user_id']==pred['user_id'], 'bank identity differs')
        require(sha((row['problem_id']+'|'+noop).encode())==row['bank_id'], 'bank source binding differs')
        original = originals[rec['current_source_id']]
        require(original['source_hex']==source.hex(), 'current source differs from observed prefix')
        sources = {noop:source}
        for attempt in row['attempts']:
            if attempt['status']=='success':
                raw=attempt['source'].encode('utf-8'); sources[sha(raw)]=raw
        require(set(pred['candidate_scores'])==set(METHODS) and set(pred['choices'])==set(METHODS),
                'all fourteen frozen methods required')
        for arm in METHODS:
            scores=pred['candidate_scores'][arm]
            require(set(scores)==set(sources), 'candidate inventory changed')
            require(all(type(v) in (float,int) and math.isfinite(v) for v in scores.values()),
                    'finite frozen scores required')
        ids=sorted(sources); mapping={}
        for cid in ids:
            identity=[row['problem_id'],cid,'Python']
            key=sha(encoded(identity)); mapping[cid]=key
            task=dict(identity=identity, source_hex=sources[cid].hex(),
                eligible=bool(samples[row['problem_id']]['cases']) and (cid!=noop or original['language']=='Python'))
            require(key not in tasks or tasks[key]==task, 'deduplicated task conflict')
            tasks[key]=task
        cohort.append(dict(example_id=ex,user_id=pred['user_id'],bank_id=pred['bank_id'],
            problem_id=pred['problem_id'],fold=pred['fold'],candidate_ids=ids,noop_candidate_id=noop,
            task_ids=mapping, scores=pred['candidate_scores'],old_choices=pred['choices']))
    require(len(cohort)==len(recipients)==320 and len({r['example_id'] for r in cohort})==320
            and sum(len(r['candidate_ids']) for r in cohort)==2544
            and len({r['problem_id'] for r in cohort})==23
            and set(samples)=={r['problem_id'] for r in cohort}, 'full fixed cohort required')
    protocol_raw=(project/PROTOCOL).read_bytes()
    output.mkdir(parents=True, exist_ok=False)
    bundle=dict(version=VERSION,protocol_sha256=sha(protocol_raw),input_sha256=PINS,
                cohort=cohort,samples=samples,tasks=tasks)
    digest=write_new(output/'bundle.json',bundle)
    write_new(output/'COMPLETE.json',dict(status='complete',bundle_sha256=digest,
        protocol_sha256=sha(protocol_raw),examples=len(cohort),candidate_memberships=2544,
        unique_tasks=len(tasks),planned_source_blocks=4*sum(t['eligible'] for t in tasks.values()),
        planned_case_attempts=4*sum(len(samples[t['identity'][0]]['cases']) for t in tasks.values() if t['eligible']),
        labels_opened=False,candidate_execution=False))
    return digest


def select_all(bundle, vectors):
    require(set(vectors)==set(bundle['tasks']), 'exact execution-task coverage required')
    predictions=[]; diagnostics=[]
    for row in bundle['cohort']:
        masks={cid:vectors[key] for cid,key in row['task_ids'].items()}
        choices={}; detail=None
        for arm in METHODS:
            if arm=='noop':
                choices[arm]=row['noop_candidate_id']; continue
            choices[arm], detail=choose(row['scores'][arm],masks,row['noop_candidate_id'],row['old_choices'][arm])
        predictions.append({**{k:row[k] for k in ('example_id','user_id','bank_id','problem_id','fold')},'choices':choices})
        diagnostics.append(dict(example_id=row['example_id'],**detail,
            unavailable_candidates=sum(v is None for v in masks.values()),
            c_exec_changed=choices['C_joint']!=row['old_choices']['C_joint']))
    return predictions, diagnostics


def verify_unit_properties(values):
    expected=dict(Id=UNIT,LoadState='loaded',ActiveState='active',SubState='running',
        MainPID=str(os.getpid()),MemoryMax='34359738368',TasksMax='128',LimitAS='34359738368',
        KillMode='control-group',KillSignal='9',SendSIGKILL='yes',Restart='no',OOMPolicy='stop',
        Type='exec',Delegate='no',RemainAfterExit='yes',MemoryAccounting='yes',TasksAccounting='yes')
    require(all(values.get(k)==v for k,v in expected.items()), 'effective unit properties differ')
    from scripts.zpd_statement_sample_host import _seconds, EnvelopeError
    try:
        seconds=_seconds(values.get('RuntimeMaxUSec',''))
    except EnvelopeError as exc:
        raise ValueError('invalid effective unit deadline') from exc
    require(seconds==21600, 'effective unit wall deadline differs')


def envelope(verify_unit=False):
    """Verify the actual aggregate cgroup, not just per-process Python limits."""
    require(sys.platform=='linux', 'execution requires Linux sandbox host')
    lines=Path('/proc/self/cgroup').read_text().splitlines()
    groups=[s.split(':',2)[2] for s in lines if s.startswith('0::')]
    require(len(groups)==1 and groups[0].endswith('/'+UNIT)
            and groups[0].startswith(f'/user.slice/user-{os.getuid()}.slice/'), 'dedicated user unit required')
    base=Path('/sys/fs/cgroup')/groups[0].lstrip('/')
    require((base/'memory.max').read_text().strip()=='34359738368'
            and (base/'pids.max').read_text().strip()=='128', 'aggregate memory/task limits required')
    events={}
    for name in ('memory.events','pids.events'):
        events[name]={k:int(v) for k,v in (line.split() for line in (base/name).read_text().splitlines())}
    require(all(v==0 for k,v in events['memory.events'].items() if k!='low')
            and all(v==0 for v in events['pids.events'].values()), 'aggregate resource event; run invalid')
    result=dict(cgroup=groups[0],events=events)
    if verify_unit:
        names=('Id','LoadState','ActiveState','SubState','MainPID','MemoryMax','TasksMax','LimitAS',
               'KillMode','KillSignal','SendSIGKILL','Restart','OOMPolicy','Type','Delegate',
               'RemainAfterExit','MemoryAccounting','TasksAccounting','RuntimeMaxUSec')
        raw=subprocess.check_output(['/usr/bin/systemctl','--user','show',UNIT,
                                     '--property='+','.join(names)],text=True,timeout=10)
        values=dict(line.split('=',1) for line in raw.splitlines())
        require(set(values)==set(names),'missing or extra effective unit properties')
        verify_unit_properties(values);result['properties']=values
    return result


def prediction_barrier(output, files, bundle_path, bundle_sha):
    require(sha(Path(bundle_path).read_bytes())==bundle_sha,'bundle changed during execution')
    for name in ('predictions.json','public-vectors.json','PREDICTIONS_COMPLETE.json'):
        require(sha((Path(output)/name).read_bytes())==files[name], 'prediction barrier drift: '+name)
    terminal=json.loads((Path(output)/'PREDICTIONS_COMPLETE.json').read_bytes())
    require(terminal['status']=='complete' and terminal['assessment_opened'] is False
            and terminal['predictions_sha256']==files['predictions.json']
            and terminal['vectors_sha256']==files['public-vectors.json']
            and terminal['bundle_sha256']==bundle_sha, 'prediction completion chain differs')


def assess_sealed(bundle, predictions, labels):
    from scripts import zpd_joint_progress_assessment as assessment
    from scripts import zpd_repair_feedback_assessment as original
    from fractions import Fraction
    cohort=[{k:r[k] for k in assessment.COHORT_FIELDS} for r in bundle['cohort']]
    indexed={(r['bank_id'],r['candidate_id']):r for r in labels['labels']}
    report=assessment.assess(cohort,predictions,indexed)
    old=[{**{k:r[k] for k in ('example_id','user_id','bank_id','problem_id','fold')},
          'choices':r['old_choices']} for r in bundle['cohort']]
    old_report=assessment.assess(cohort,old,indexed)
    # Reuse exact fraction metrics; component tests do not replace ZPD gates.
    def metrics(rows):
        cell=original._metrics(rows,indexed,'C_joint')
        per=[original._metrics([r for r in rows if r['problem_id']==pid],indexed,'C_joint')
             for pid in sorted({r['problem_id'] for r in rows})]
        return cell,{k:sum((r['fractions'][k] for r in per),Fraction())/len(per)
                     for k in original.METRICS} if per else {}
    checks={}
    for group in ('all','known_nonac','known_ac'):
        def belongs(r):
            current=indexed[r['bank_id'],r['choices']['noop']]
            return group=='all' or (current['status']=='stable' and current['all_ac']==(group=='known_ac'))
        new_rows=[r for r in predictions if belongs(r)]; old_rows=[r for r in old if belongs(r)]
        a,ae=metrics(new_rows); b,be=metrics(old_rows)
        require(a['examples'] and a['examples']==b['examples'], 'component group unavailable')
        for weighting,x,y in [('pooled',a['fractions'],b['fractions']),('equal_problem',ae,be)]:
            checks[group+'_'+weighting+'_ac']=(x['ac_lower']>=y['ac_lower'] if group=='known_ac' else x['ac_lower']>y['ac_lower'])
            for name in ('regression_lower','regression_upper'):
                checks[group+'_'+weighting+'_'+name]=x[name]<=y[name]
        checks[group+'_unknown_nonincrease']=a['counts']['unknown']<=b['counts']['unknown']
    nonworse=sum(report['folds'][str(f)]['results']['C_joint']['counts']['stable_ac'] >=
                 old_report['folds'][str(f)]['results']['C_joint']['counts']['stable_ac'] for f in range(5))
    checks['at_least_four_nonworse_folds']=nonworse>=4
    return dict(version=VERSION,matched_execution=report,frozen_original=old_report,
        component_gate=dict(primary='C_exec',control='frozen_C_joint',checks=checks,passed=all(checks.values()),
                            nonworse_folds=nonworse),model_promotion=False,educational_benefit_established=False,
        note='Adaptive development only; component improvement does not establish authentic-history benefit.')


def worker(bundle_path, bundle_sha):
    require(Path.cwd().resolve()!=PROJECT and Path.cwd().resolve().is_relative_to(PROJECT/'.runtime'),
            'run only from a separate runtime snapshot')
    require(not subprocess.check_output(['git','status','--porcelain'],text=True).strip(), 'clean execution snapshot required')
    bundle=read_pinned(bundle_path,bundle_sha)
    require(sha(Path(PROTOCOL).read_bytes())==bundle['protocol_sha256'], 'prospective protocol drift')
    output=PROJECT/OUTPUT
    require(not output.exists(), 'run exists; duplicate execution and implicit resume forbidden')
    state=envelope(verify_unit=True)
    from scripts import zpd_statement_sample_replay as core
    from scripts import zpd_repair_evaluate as evaluator
    from scripts.probe_zpd_statement_sample_resources import runtime_identity
    from src.runner.models import TestCase
    require((evaluator.SandboxRunner.timeout_sec,evaluator.SandboxRunner.memory_limit_mb,
             evaluator.SandboxRunner.case_workers)==(2.5,2048,1), 'unchanged runner required')
    runtime=dict(python=sys.version,execution_python=evaluator.sandbox_preflight(),
        binaries={name:sha(Path(name).read_bytes()) for name in ('/usr/bin/python3','/usr/bin/bwrap')},
        host_runtime=runtime_identity(),
        source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    runtime_sha=sha(encoded(runtime)); tasks={}
    def source_barrier():
        require(not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
                and subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==runtime['source_revision'],
                'execution source changed')
        require(all(sha(Path(name).read_bytes())==digest for name,digest in runtime['binaries'].items()),
                'execution runtime changed')
        require(runtime_identity()==runtime['host_runtime'], 'runtime dependency identity changed')
        require(sha(Path(PROTOCOL).read_bytes())==bundle['protocol_sha256'], 'protocol changed')
    for key,item in bundle['tasks'].items():
        pid,cid,language=item['identity']; problem=bundle['samples'][pid]
        cases=tuple(TestCase(c['case_id'],bytes.fromhex(c['input_hex']).decode('utf-8'),
                            bytes.fromhex(c['output_hex']).decode('utf-8')) for c in problem['cases'])
        task=core.ReplayTask(pid,cid,language,bytes.fromhex(item['source_hex']),problem['sample_set_sha256'],
                            cases,(),(),() if item['eligible'] else ('unavailable_public_source_or_cases',))
        task.integrity();require(sha(task.source)==cid,'candidate source changed');tasks[key]=task
    eligible=[key for key,t in tasks.items() if t.eligible]
    total_cases=4*sum(len(tasks[k].cases) for k in eligible)
    output.mkdir(parents=True,exist_ok=False);started=time.monotonic();deadline=started+21600
    files={}; records={k:[] for k in tasks};completed_cases=0; completed_blocks=0
    try:
        files['manifest.json']=write_new(output/'manifest.json',dict(version=VERSION,bundle_sha256=bundle_sha,
            protocol_sha256=bundle['protocol_sha256'],runtime=runtime,envelope=state,selection_before_labels=True))
        def check():
            require(time.monotonic()<deadline,'six-hour wall limit exceeded');return envelope()
        def progress(block):
            finished={key for key,blocks in records.items() if len(blocks)==4 or not tasks[key].eligible}
            done=sum(all(k in finished for k in r['task_ids'].values()) for r in bundle['cohort'])
            return dict(phase='public_execution',block=block,completed_examples=done,total_examples=320,
                completed_source_blocks=completed_blocks,total_source_blocks=4*len(eligible),
                completed_case_attempts=completed_cases,total_case_attempts=total_cases,
                elapsed_seconds=time.monotonic()-started)
        with (output/'completions.jsonl').open('xb') as journal:
            for block,workers in enumerate(core.WORKERS):
                check(); pending={};remaining=iter(eligible)
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    def submit():
                        key=next(remaining,None)
                        if key is not None:
                            pending[pool.submit(core.measured_block,tasks[key],block,runtime_sha,deadline,evaluator.SandboxRunner())]=key
                    for _ in range(workers):submit()
                    while pending:
                        check();done,_=wait(pending,timeout=10,return_when=FIRST_COMPLETED)
                        for future in done:
                            key=pending.pop(future);value=future.result();check()
                            require(value['complete'],'incomplete block')
                            journal.write(encoded(dict(task_id=key,block=value)));journal.flush();os.fsync(journal.fileno())
                            records[key].append(value);completed_blocks+=1;completed_cases+=len(value['outcomes'])
                            submit()
                        status_write(output/'STATUS.json',progress(block))
        check();require(completed_cases==total_cases,'incomplete public case execution')
        vectors={key:stable_mask(blocks,[c.case_id for c in tasks[key].cases]) for key,blocks in records.items()}
        files['public-vectors.json']=write_new(output/'public-vectors.json',vectors)
        predictions,diagnostics=select_all(bundle,vectors)
        files['predictions.json']=write_new(output/'predictions.json',predictions)
        files['selection-diagnostics.json']=write_new(output/'selection-diagnostics.json',diagnostics)
        # Explicit prediction seal BEFORE loading any private assessment labels.
        files['PREDICTIONS_COMPLETE.json']=write_new(output/'PREDICTIONS_COMPLETE.json',dict(
            status='complete',examples=len(predictions),predictions_sha256=files['predictions.json'],
            vectors_sha256=files['public-vectors.json'],bundle_sha256=bundle_sha,assessment_opened=False))
        check();envelope(verify_unit=True)
        prediction_barrier(output,files,bundle_path,bundle_sha)
        source_barrier()
        labels=read_pinned(PROJECT/LABEL_PATH,LABEL_SHA)
        report=assess_sealed(bundle,predictions,labels)
        report['execution']=dict(source_blocks=completed_blocks,case_attempts=completed_cases,
            unavailable_tasks=sum(v is None for v in vectors.values()),elapsed_seconds=time.monotonic()-started)
        files['report.json']=write_new(output/'report.json',report)
        status_write(output/'STATUS.json',{**progress(3),'phase':'complete'})
        files['STATUS.json']=sha((output/'STATUS.json').read_bytes())
        files['completions.jsonl']=sha((output/'completions.jsonl').read_bytes())
        check();envelope(verify_unit=True);source_barrier()
        require(all(sha((output/name).read_bytes())==digest for name,digest in files.items()),'output drift')
        write_new(output/'COMPLETE.json',dict(status='complete',files_sha256=files,
            bundle_sha256=bundle_sha,assessment_sha256=LABEL_SHA,examples=320,model_promotion=False,
            provisional_until_normal_unit_exit=True,
            component_passed=report['component_gate']['passed'],zpd_passed=report['matched_execution']['gate']['passed']))
    except BaseException as exc:
        write_new(output/'FAILED.json',dict(error_type=type(exc).__name__,error=str(exc),
            completed_source_blocks=completed_blocks,assessment_valid=False))
        raise


def verify_terminal(output, unit_values, bundle_sha):
    require(unit_values.get('Result')=='success' and unit_values.get('ExecMainCode')=='1'
            and unit_values.get('ExecMainStatus')=='0' and unit_values.get('MainPID')=='0'
            and unit_values.get('SubState')=='exited', 'worker must exit normally')
    output=Path(output)
    require(not (output/'FAILED.json').exists(), 'worker failure marker present')
    raw=(output/'COMPLETE.json').read_bytes();complete=json.loads(raw)
    require(complete['status']=='complete' and complete['bundle_sha256']==bundle_sha
            and complete['examples']==320 and complete['assessment_sha256']==LABEL_SHA
            and complete['model_promotion'] is False and complete['provisional_until_normal_unit_exit'] is True
            and type(complete['component_passed']) is bool and type(complete['zpd_passed']) is bool
            and set(complete['files_sha256'])==ARTIFACTS
            and {p.name for p in output.iterdir()}==ARTIFACTS|{'COMPLETE.json'},
            'worker terminal identity mismatch')
    for name,pin in complete['files_sha256'].items():
        require(Path(name).name==name and sha((output/name).read_bytes())==pin, 'worker artifact drift')
    manifest=json.loads((output/'manifest.json').read_bytes())
    group=manifest['envelope']['cgroup']
    require(type(group) is str and group.startswith(f'/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/')
            and group.endswith('/'+UNIT) and '..' not in Path(group).parts and str(Path(group))==group,
            'bound worker cgroup path invalid')
    require(unit_values.get('ControlGroup') in ('',group), 'terminal worker cgroup binding changed')
    return dict(status='complete',worker_complete_sha256=sha(raw),bundle_sha256=bundle_sha,bound_control_group=group,
        unit_exit=unit_values,component_passed=complete['component_passed'],
        zpd_passed=complete['zpd_passed'],model_promotion=False,examples=320)


def watch(bundle_sha):
    """Durable outside-unit completion check; never launches or retries work."""
    require(sys.platform=='linux','Linux unit monitor required')
    parent=(PROJECT/OUTPUT).parent
    parent.mkdir(parents=True,exist_ok=True)
    write_new(parent/'WATCHER.json',dict(unit=UNIT,bundle_sha256=bundle_sha,started=time.time(),
        pid=os.getpid(),launches_work=False,retries=0))
    started=time.monotonic()
    fields='Id,LoadState,ActiveState,SubState,MainPID,Result,ExecMainCode,ExecMainStatus,ControlGroup'
    try:
        while time.monotonic()-started<21900:
            raw=subprocess.check_output(['/usr/bin/systemctl','--user','show',UNIT,'--property='+fields],
                                        text=True,timeout=10)
            values=dict(line.split('=',1) for line in raw.splitlines())
            require(values.get('Id')==UNIT and values.get('LoadState')=='loaded','worker unit unavailable')
            status_write(parent/'MONITOR_STATUS.json',dict(phase='monitoring',checked=time.time(),unit=values))
            if values.get('SubState')=='exited' or values.get('ActiveState') in ('failed','inactive'):
                terminal=verify_terminal(PROJECT/OUTPUT,values,bundle_sha)
                cg=Path('/sys/fs/cgroup')/terminal['bound_control_group'].lstrip('/')
                if cg.exists():
                    require(not (cg/'cgroup.procs').read_text().strip(), 'worker descendants remain')
                    require('populated 0' in (cg/'cgroup.events').read_text().splitlines(), 'worker cgroup still populated')
                status_write(parent/'MONITOR_STATUS.json',dict(phase='complete',checked=time.time(),**terminal))
                write_new(parent/'VERIFIED_COMPLETE.json',terminal)
                return
            time.sleep(20)
        raise TimeoutError('worker did not terminate within fixed unit deadline plus300s')
    except BaseException as exc:
        marker=parent/'VERIFIED_COMPLETE.json'
        if marker.exists():
            marker.rename(parent/'REJECTED_VERIFIED_COMPLETE.json')
        write_new(parent/'MONITOR_FAILED.json',dict(error_type=type(exc).__name__,error=str(exc),
                                                  unit=UNIT,assessment_valid=False))
        raise


def main():
    parser=argparse.ArgumentParser(__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p=sub.add_parser('worker');p.add_argument('--bundle',type=Path,required=True);p.add_argument('--bundle-sha',required=True)
    p=sub.add_parser('watch');p.add_argument('--bundle-sha',required=True)
    args=parser.parse_args()
    if args.command=='prepare':print(prepare(args.project,args.output))
    elif args.command=='worker':worker(args.bundle,args.bundle_sha)
    else:watch(args.bundle_sha)


if __name__=='__main__':main()
