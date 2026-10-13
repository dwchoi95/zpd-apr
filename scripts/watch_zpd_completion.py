"""Read-only SSH observer: hourly Mac reports and prompt terminal notifications.

This is NOT a ChatGPT scheduled task and cannot resume an agent conversation.
It never launches, retries, stops, or changes an experiment. macOS launchd runs
it every five minutes; completion/error changes and hourly reports notify the
logged-in user while the Mac is awake and UbuntuServer is reachable.
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
FAMILIES = ('zpd-transition-diagnosis-20261013', 'zpd-current-last-20261013')


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


def remote_snapshot(project=REMOTE_PROJECT):
    rows=[]
    for family in FAMILIES:
        root=project/'outputs'/family
        row=dict(family=family,state='not_started',completed_examples=0,total_examples=320)
        if root.exists():
            failures=sorted(p for p in root.rglob('*FAILED*.json') if p.is_file())
            if failures:
                row.update(state='error',errors=[str(p.relative_to(root)) for p in failures])
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
    names={FAMILIES[0]:'후보 진단',FAMILIES[1]:'현재 코드 마지막 배치'}
    lines=[]
    for r in snapshot['experiments']:
        label=names[r['family']]
        if r['state']=='complete':
            line=f"{label}: 완료 320/320, {r['completed_at'][11:16]} KST"
            if r['family']==FAMILIES[0]:
                c,h=r['results']['C'],r['results']['H']
                line+=f". C 정답 {c['selected_stable_ac']}, H 정답 {h['selected_stable_ac']} (H 후보 상한 {h['oracle_upper']})"
            else:
                c,h=r['results']['C'],r['results']['H']
                line+=f". C 정답 {c['stable_ac']}, H 정답 {h['stable_ac']}. 다음: 개선 여부 검토"
        elif r['state']=='error':line=label+': 오류 발생, 재실행하지 않음'
        elif r['state']=='not_started':line=label+': 아직 시작 안 됨'
        else:
            line=f"{label}: {r.get('phase','준비')} {r['completed_examples']}/{r['total_examples']} 예제, 실행장애 기록 없음"
            if r.get('attempt_statuses',{}):
                failed=sum(n for status,n in r['attempt_statuses'].items() if status!='success')
                if failed:line+=f', 생성 실패 {failed}회 (제외·재시도 없음)'
            if r.get('completed_case_attempts') is not None:
                line+=f", 테스트 {r['completed_case_attempts']}/{r['total_case_attempts']}"
            elapsed,done,total=r.get('elapsed_seconds'),r['completed_examples'],r['total_examples']
            if elapsed and 10<=done<total:
                estimate=datetime.fromisoformat(snapshot['checked_at'])+timedelta(seconds=elapsed*(total-done)/done)
                line+=f", 현 단계 예상 {estimate:%H:%M} KST (단순 속도 추정)"
            else:line+=', 종료시각 추정 중'
            next_phase={'generation':'공개 테스트 선택','public_selection':'전체 테스트 평가','private_execution':'자동 결과 집계'}
            line+=', 다음: '+next_phase.get(r.get('phase'),'결과 검증')
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
                    chat_message_sent=False,experiment_mutations=False)
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
