"""Read-only SSH observer with opt-in local Codex continuation dispatch.

This is NOT a native ChatGPT scheduled task. It never directly launches, retries,
stops, or changes an experiment. With explicit continuation.json registration,
terminal events enqueue a follow-up in the existing chat through `codex queue`.
macOS launchd runs every five minutes. --no-notify disables both notifications
and continuation dispatch for a read-only check.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

REMOTE_PROJECT = Path('/home/cdw/VSCode/zpd-apr')
REMOTE_SCRIPT = REMOTE_PROJECT/'.runtime/zpd-observer-20261013-v1/watch_zpd_completion.py'
LOCAL_STATE = Path('/Users/cdw/VSCode/zpd-apr/.runtime/zpd-observer-20261013-v1')
KST = timezone(timedelta(hours=9))
FAMILIES = ('zpd-transition-diagnosis-20261013', 'zpd-current-last-20261013',
            'zpd-full-source-20261014', 'zpd-paired-history-run-20261015',
            'zpd-paired-inference-20261016', 'zpd-crossed-inference-20261016')
FAMILY_NAMES = dict(zip(FAMILIES, ('후보 진단', '현재 코드 마지막 배치', '전체 소스 이력 표현',
                                 '동일 조건 C/H 신규 학습', 'C/H 학습 완료 후 평가 복구', '어댑터·입력 교차 진단')))
PAIRED_FAMILY = 'zpd-paired-history-run-20261015'
RECOVERY_FAMILY = 'zpd-paired-inference-20261016'
CROSSED_FAMILY = 'zpd-crossed-inference-20261016'
MATCHED_FAMILIES = (PAIRED_FAMILY, RECOVERY_FAMILY, CROSSED_FAMILY)
PAIRED_UNIT_PREFIX = 'zpd-paired-history-20261015-v1'
PAIRED_PHASES = ('cache', 'materialize', 'capacity', 'train-C', 'train-H', 'generation', 'public', 'private')
PAIRED_STATUS = {'cache':'cache-v1/cache/STATUS.json',
    'train-C':'train-C-v1/training/STATUS.json', 'train-H':'train-H-v1/training/STATUS.json',
    'generation':'generation-v1/STATUS.json', 'public':'public-v1/STATUS.json',
    'private':'private-v1/evaluation/STATUS.json'}
PAIRED_LABELS = {'cache':'공개 샘플 캐시', 'materialize':'학습 입력·토큰 점검', 'capacity':'학습 용량 점검',
    'train-C':'C 어댑터 학습', 'train-H':'H 어댑터 학습', 'generation':'후보 생성',
    'public':'공개 샘플 선택', 'private':'전체 테스트 평가', 'complete':'최종 봉인 대기'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def require(value, message):
    if not value: raise ValueError(message)


def verify_files(directory, marker):
    value = read(directory/marker)
    require(value['status']=='complete', 'incomplete seal')
    for name,pin in value['files_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe artifact path')
        require(sha(directory/name)==pin, 'artifact drift: '+name)
    return value


def verify_terminal(directory, outer):
    if directory.name == PAIRED_FAMILY:
        return verify_paired_terminal(directory, outer)
    if directory.name in (RECOVERY_FAMILY,CROSSED_FAMILY):
        variant = 'crossed_adapter_input_diagnostic_v1' if directory.name == CROSSED_FAMILY else 'paired_history_ipc_recovery_v1'
        require(outer['status']=='complete' and outer['layout_variant']==variant
                and set(outer['phases'])=={'generation','public','private'},
                'recovery completion identity differs')
        verify_files(directory,'VERIFIED_COMPLETE.json')
        for phase in ('generation','public','private'):
            cert=read(directory/(phase+'-VERIFIED_COMPLETE.json'))
            require(cert['cleanup_verified'] is True and cert['release_sha256']==outer['release_sha256']
                    and cert['exit']['ExecMainCode']=='1' and cert['exit']['SubState']=='exited',
                    'recovery normal exit/cleanup not certified')
        if directory.name == CROSSED_FAMILY:
            report=read(directory/'REPORT.json')
            require(outer['development_decision']==report['decision']=='diagnostic_only_no_promotion'
                    and report['model_promotion'] is False
                    and report['adapter_arm_map']==dict(C='H',H='C',HS='C',U='C'),
                    'crossed diagnostic claim boundary differs')
    if 'worker_certificate_sha256' in outer:
        require(sha(directory/'WORKER_VERIFIED_COMPLETE.json')==outer['worker_certificate_sha256'], 'worker certificate differs')
        cert=read(directory/'WORKER_VERIFIED_COMPLETE.json')
        require(cert['cleanup_verified'] is True and cert['exit']['Result']=='success'
                and cert['exit']['ExecMainStatus']=='0' and cert['exit']['MainPID']=='0', 'worker not released normally')
        require(sha(directory/'run-v1/COMPLETE.json')==cert['complete_sha256'], 'worker result seal differs')
        verify_files(directory/'run-v1','COMPLETE.json')
        require(sha(directory/'diagnosis-complete-v1/COMPLETE.json')==outer['diagnosis_complete_sha256'], 'diagnosis seal differs')
        dc=read(directory/'diagnosis-complete-v1/COMPLETE.json')
        require(sha(directory/'diagnosis-complete-v1/report.json')==dc['report_sha256'], 'diagnosis report differs')
        r=read(directory/'diagnosis-complete-v1/report.json')
        return {a:{k:r['per_arm'][a][k] for k in ('selected_stable_ac','oracle_lower','oracle_upper','missed_known_ac')}
                for a in ('C','H','HS','U')}
    require(set(outer['phases'])=={'generation','public','private'}, 'all phases required')
    for phase,pin in outer['phases'].items():
        p=directory/(phase+'-VERIFIED_COMPLETE.json');require(sha(p)==pin,'phase certificate differs')
        cert=read(p); require(cert['exit']['Result']=='success' and cert['exit']['ExecMainStatus']=='0'
                and cert['exit']['MainPID']=='0', 'abnormal phase exit')
        require(sha(directory/(phase+'-v1')/'STAGE_COMPLETE.json')==cert['complete_sha256'],'phase seal differs')
        verify_files(directory/(phase+'-v1'),'STAGE_COMPLETE.json')
    r=read(directory/'private-v1/evaluation/report.json')
    return {a:r['full']['results'][a]['counts'] for a in ('C','H','HS','U')}


def report_counts(report):
    counts = report.get('counts')
    if counts is None:
        counts = {a:report['full']['results'][a]['counts'] for a in ('C','H','HS','U')}
    require({'C','H','HS','U'}<=set(counts), 'all matched-training arms required')
    counts={a:counts[a] for a in ('C','H','HS','U')}
    require(all(type(counts[a]['stable_ac']) is int and 0<=counts[a]['stable_ac']<=320 for a in counts),
            'invalid final stable-AC counts')
    return counts


def verify_paired_terminal(directory, outer):
    """Only eight normal exits, cleanup and sealed results establish completion."""
    require(outer['status']=='complete' and set(outer['phases'])==set(PAIRED_PHASES), 'all eight phases required')
    dynamic=read(directory/'INFERENCE_RELEASE_COMPLETE.json')
    require(dynamic['status']=='complete' and dynamic['parent_release_sha256']==outer['release_sha256']
            and dynamic['inference_release_sha256']==outer['inference_release_sha256']
            ==sha(directory/'inference-release.json'), 'dynamic inference release binding differs')
    for phase,pin in outer['phases'].items():
        path=directory/(phase+'-VERIFIED_COMPLETE.json')
        require(sha(path)==pin, 'paired phase certificate differs')
        cert=read(path)
        require(cert['status']=='complete' and cert['cleanup_verified'] is True
                and cert['exit']['Result']=='success' and cert['exit']['ExecMainStatus']=='0'
                and cert['exit']['MainPID']=='0' and cert['exit']['ExecMainCode']=='1'
                and cert['exit']['SubState']=='exited', 'paired worker exit/cleanup not certified')
        expected=outer['inference_release_sha256'] if phase in PAIRED_PHASES[-3:] else outer['release_sha256']
        require(cert['parent_release_sha256']==outer['release_sha256'] and cert['release_sha256']==expected,
                'paired certificate release differs')
        stage=directory/(phase+'-v1')
        require(sha(stage/'STAGE_COMPLETE.json')==cert['complete_sha256'], 'paired stage seal differs')
        seal=verify_files(stage,'STAGE_COMPLETE.json')
        require(seal['phase']==phase and seal['release_sha256']==expected, 'paired stage identity differs')
    require('REPORT.json' in outer['files_sha256'], 'paired final report not sealed')
    verify_files(directory,'VERIFIED_COMPLETE.json')
    result=report_counts(read(directory/'REPORT.json'))
    private=report_counts(read(directory/'private-v1/evaluation/report.json'))
    require(result==private, 'paired final/private result counts differ')
    return result


def paired_progress(root):
    """Parent phase wins over stale completed cache/training status files."""
    parent=read(root/'STATUS.json') if (root/'STATUS.json').is_file() else {}
    phase=parent.get('phase')
    if phase is None:
        phase=next((p for p in reversed(PAIRED_PHASES) if (root/(p+'-v1')).is_dir()),None)
    row=dict(state='running' if phase is not None else 'starting', phase=phase or 'preparing',
        pipeline_phase=phase, completed_examples=0,total_examples=0,progress_unit='단계',
        completed_phases=parent.get('completed_phases',[]),unit=parent.get('unit'),unit_prefix=PAIRED_UNIT_PREFIX)
    if phase in ('failed','error','rejected'):
        row.update(state='error',errors=['coordinator phase: '+phase]);return row
    paths=[]
    if phase in PAIRED_STATUS:paths.append(root/PAIRED_STATUS[phase])
    if phase in PAIRED_PHASES:paths.append(root/(phase+'-v1')/'STATUS.json')
    path=next((p for p in paths if p.is_file()),None)
    if path is not None:
        status=read(path);row['worker_phase']=status.get('phase')
        if status.get('phase') in ('failed','error','rejected'):
            row.update(state='error',errors=[str(path.relative_to(root))+': '+status['phase']]);return row
        row.update(elapsed_seconds=status.get('elapsed_seconds'),attempt_statuses=status.get('attempt_statuses'))
        if phase=='cache':
            row.update(completed_examples=status.get('terminal_source_blocks',status.get('completed_source_blocks',0)),
                total_examples=status.get('planned_source_blocks',0),progress_unit='소스 블록',
                completed_source_blocks=status.get('completed_source_blocks'),
                terminal_source_blocks=status.get('terminal_source_blocks'),
                completed_case_attempts=status.get('completed_case_attempts'),
                total_case_attempts=status.get('planned_case_attempts'),
                unique_sources=status.get('unique_sources'),unavailable_unique_sources=status.get('unavailable_unique_sources'),
                current_block=status.get('current_block'),journaled_case_attempts=status.get('journaled_case_attempts'))
        else:
            row.update(completed_examples=status.get('completed_examples',0),
                total_examples=status.get('total_examples',320 if phase in ('generation','public','private') else 0),
                progress_unit='예제',completed_case_attempts=status.get('completed_case_attempts'),
                total_case_attempts=status.get('total_case_attempts'))
    else:
        if phase in ('generation','public','private'):
            row.update(completed_examples=0,total_examples=320,progress_unit='예제')
        else:
            row.update(completed_examples=len(row['completed_phases']),total_examples=len(PAIRED_PHASES),progress_unit='단계')
    materialized=root/'materialize-v1/materialized'
    if (materialized/'COMPLETE.json').is_file() and (materialized/'report.json').is_file():
        row['training_population']=read(materialized/'report.json').get('counts',{})
    if phase=='capacity':
        path=root/'capacity-v1/probe/capacity_report.json'
        if path.is_file():row['capacity_report_present']=True
    return row


def remote_snapshot(project=REMOTE_PROJECT):
    rows=[]
    for family in FAMILIES:
        root=project/'outputs'/family
        row=dict(family=family,state='not_started',completed_examples=0,total_examples=320)
        if root.exists():
            if family in MATCHED_FAMILIES and (root/'COORDINATOR.json').is_file():
                row['release_sha256']=read(root/'COORDINATOR.json').get('release_sha256')
            failures=sorted(p for p in root.rglob('*FAILED*.json') if p.is_file())
            if family in MATCHED_FAMILIES:
                failures+=sorted(p for p in root.rglob('REJECTED_COMPLETE.json') if p.is_file())
            if failures:
                row.update(state='error',errors=[str(p.relative_to(root)) for p in failures])
            elif family in MATCHED_FAMILIES:
                try:
                    if (root/'VERIFIED_COMPLETE.json').exists():
                        outer=read(root/'VERIFIED_COMPLETE.json')
                        results=verify_terminal(root,outer)
                        row.update(state='complete',completed_examples=320,certificate_sha256=sha(root/'VERIFIED_COMPLETE.json'),
                            completed_at=datetime.fromtimestamp((root/'VERIFIED_COMPLETE.json').stat().st_mtime,KST).isoformat(),
                            results=results,matched_fresh_training=True,
                            training_population=read(root/'REPORT.json').get('training_population',{}))
                    else:
                        row.update(paired_progress(root))
                        if family==RECOVERY_FAMILY:row['unit_prefix']='zpd-paired-inference-20261016-v1'
                        if family==CROSSED_FAMILY:row['unit_prefix']='zpd-crossed-inference-20261016-v1'
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    row.update(state='error',errors=['paired observer validation: '+str(exc)[:240]])
            elif (root/'VERIFIED_COMPLETE.json').exists():
                outer=read(root/'VERIFIED_COMPLETE.json');require(outer['status']=='complete','outer status differs')
                row.update(state='complete',completed_examples=320,certificate_sha256=sha(root/'VERIFIED_COMPLETE.json'),
                    completed_at=datetime.fromtimestamp((root/'VERIFIED_COMPLETE.json').stat().st_mtime,KST).isoformat(),
                    results=verify_terminal(root,outer))
            else:
                paths=[root/name for name in ('run-v1/STATUS.json','private-v1/evaluation/STATUS.json',
                    'public-v1/STATUS.json','generation-v1/STATUS.json','STATUS.json')]
                path=next((p for p in paths if p.is_file()),None)
                if path:
                    p=read(path); row.update(state='running',phase=p.get('phase'),
                        completed_examples=p.get('completed_examples',0),total_examples=p.get('total_examples',320),
                        completed_case_attempts=p.get('completed_case_attempts'),total_case_attempts=p.get('total_case_attempts'),
                        elapsed_seconds=p.get('elapsed_seconds'),attempt_statuses=p.get('attempt_statuses'))
                else: row['state']='starting'
        rows.append(row)
    return dict(checked_at=datetime.now(KST).isoformat(),experiments=rows)


def terminal_key(row):
    if row['state']=='complete':return 'complete:'+row['certificate_sha256']
    if row['state']=='error':return 'error:'+json.dumps(row.get('errors',[]),sort_keys=True)
    return None


def due(snapshot,state,now):
    changed=any(terminal_key(r) and state.get('terminal',{}).get(r['family'])!=terminal_key(r)
                for r in snapshot.get('experiments',[]))
    connection_changed=snapshot.get('connection_error')!=state.get('connection_error')
    return changed or connection_changed or now-state.get('last_notification',0)>=3600


def korean_report(snapshot):
    if snapshot.get('connection_error'):
        return 'UbuntuServer 확인 실패: '+snapshot['connection_error'][:160]+' (실험 재실행 없음)'
    lines=[]
    # macOS may collapse long notification bodies: show the newest run first.
    for r in reversed(snapshot['experiments']):
        label=FAMILY_NAMES[r['family']]
        if r['state']=='complete':
            line=f"{label}: 완료 320/320, {r['completed_at'][11:16]} KST"
            if r['family'] in MATCHED_FAMILIES:
                line+='; 신규 C/H 어댑터별 정답 '+', '.join(f"{a} {r['results'][a]['stable_ac']}/320" for a in ('C','H','HS','U'))
                population=r.get('training_population',{}).get('train',{})
                if population:
                    line+=f"; 학습 원천 {population['candidate_examples']}→적격 {population['retained_examples']}예제"
                line+='. 적응적 개발 결과; 모델 승격·교육 효과 주장 없음'
                if r['family']==CROSSED_FAMILY:line+='; C 입력=H 어댑터, H/HS/U 입력=C 어댑터 (교차 진단 전용)'
            elif r['family']==FAMILIES[0]:
                c,h=r['results']['C'],r['results']['H']
                line+=f". C 정답 {c['selected_stable_ac']}, H 정답 {h['selected_stable_ac']} (H 후보 상한 {h['oracle_upper']})"
            else:
                c,h=r['results']['C'],r['results']['H']
                line+=f". C 정답 {c['stable_ac']}, H 정답 {h['stable_ac']}. 다음: 개선 여부 검토"
        elif r['state']=='error':line=label+': 오류 발생, 재실행하지 않음'
        elif r['state']=='not_started':line=label+': 아직 시작 안 됨'
        else:
            phase=r.get('pipeline_phase',r.get('phase'))
            display=PAIRED_LABELS.get(phase,phase or '준비') if r['family'] in MATCHED_FAMILIES else r.get('phase','준비')
            line=f"{label}: {display} {r['completed_examples']}/{r['total_examples']} {r.get('progress_unit','예제')}, 실행장애 기록 없음"
            if r.get('attempt_statuses',{}):
                failed=sum(n for status,n in r['attempt_statuses'].items() if status!='success')
                if failed:line+=f', 생성 실패 {failed}회 (제외·재시도 없음)'
            if r.get('completed_case_attempts') is not None:
                line+=f", 테스트 {r['completed_case_attempts']}/{r['total_case_attempts']}"
            if r['family']==PAIRED_FAMILY and phase=='cache' and r.get('unavailable_unique_sources'):
                line+=f", 공개 샘플 없음 {r['unavailable_unique_sources']}개 소스 (실패 아님)"
            population=r.get('training_population',{}).get('train',{})
            if r['family']==PAIRED_FAMILY and population:
                line+=f", 학습 원천 {population['candidate_examples']}→적격 {population['retained_examples']}예제"
            elapsed,done,total=r.get('elapsed_seconds'),r['completed_examples'],r['total_examples']
            if elapsed and 10<=done<total:
                estimate=datetime.fromisoformat(snapshot['checked_at'])+timedelta(seconds=elapsed*(total-done)/done)
                line+=f", 현 단계 예상 {estimate:%H:%M} KST (단순 속도 추정)"
            else:line+=', 종료시각 추정 중'
            next_phase={'generation':'공개 테스트 선택','public_selection':'전체 테스트 평가','private_execution':'자동 결과 집계'}
            if r['family'] in MATCHED_FAMILIES:
                after={a:b for a,b in zip(PAIRED_PHASES,PAIRED_PHASES[1:])}
                line+=', 다음: '+PAIRED_LABELS.get(after.get(phase),'결과 검증')
            else:line+=', 다음: '+next_phase.get(r.get('phase'),'결과 검증')
        lines.append(line)
    return '\n'.join(lines)


def notify(body):
    # Arguments, not interpolated AppleScript: source/result text cannot execute.
    script='on run argv\n display notification (item 1 of argv) with title "ZPD-APR 진행 보고"\nend run'
    subprocess.run(['/usr/bin/osascript','-e',script,body],check=True,timeout=20,capture_output=True,text=True)


def write_atomic(path,value):
    tmp=path.with_suffix(path.suffix+'.partial')
    with tmp.open('w') as out:
        json.dump(value,out,ensure_ascii=False,indent=2);out.flush();os.fsync(out.fileno())
    tmp.replace(path)


def observe(no_notify=False):
    LOCAL_STATE.mkdir(parents=True,exist_ok=True)
    with (LOCAL_STATE/'observer.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        state=read(LOCAL_STATE/'state.json') if (LOCAL_STATE/'state.json').exists() else {}
        command=shlex.join([str(REMOTE_PROJECT/'.runtime/fse-env/bin/python'),str(REMOTE_SCRIPT),'--remote'])
        try:
            response=subprocess.run(['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',
                '-o','ServerAliveInterval=10','-o','ServerAliveCountMax=2','UbuntuServer',command],
                check=True,timeout=90,capture_output=True,text=True)
            snapshot=json.loads(response.stdout)
        except (OSError,subprocess.SubprocessError,ValueError) as exc:
            snapshot=dict(checked_at=datetime.now(KST).isoformat(),connection_error=str(exc)[:240],experiments=[])
        now=time.time(); report=korean_report(snapshot)
        result=dict(snapshot=snapshot,korean_report=report,notification_requested=False,
                    chat_message_sent=False,chat_message_queued=False,experiment_mutations=False)
        if not no_notify:
            try:
                if __package__:
                    from .zpd_completion_continuation import dispatch
                else:
                    from zpd_completion_continuation import dispatch
                followup=dispatch(snapshot,LOCAL_STATE/'continuation.json',LOCAL_STATE/'continuation-state')
                result['agent_continuation']=followup
                result['chat_message_queued']=bool(followup['queued'])
                if followup['queued']:
                    report+='\n완료 후 결과 분석·다음 작업을 현재 대화에 자동 예약했습니다.'
                elif followup['status']=='attention_required':
                    report+='\n자동 후속 예약의 수신 확인이 필요합니다. 중복 전송하지 않았습니다.'
            except (OSError,ValueError,KeyError,TypeError) as exc:
                result['continuation_error']=type(exc).__name__+': '+str(exc)[:240]
                report+='\n자동 후속 예약 점검 오류: 실험 재실행 없음.'
        result['korean_report']=report
        if not no_notify and due(snapshot,state,now):
            try:
                notify(report);result['notification_requested']=True
                state.update(last_notification=now,connection_error=snapshot.get('connection_error'),
                    terminal={r['family']:terminal_key(r) for r in snapshot['experiments'] if terminal_key(r)})
                write_atomic(LOCAL_STATE/'state.json',state)
            except (OSError,subprocess.SubprocessError) as exc:
                result['notification_error']=str(exc)
        write_atomic(LOCAL_STATE/'LATEST_REPORT.json',result)
        with (LOCAL_STATE/'events.jsonl').open('a') as out:
            out.write(json.dumps(result,ensure_ascii=False)+'\n')
        print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--remote',action='store_true')
    parser.add_argument('--no-notify',action='store_true');args=parser.parse_args()
    if args.remote:print(json.dumps(remote_snapshot(),ensure_ascii=False))
    else:observe(args.no_notify)
