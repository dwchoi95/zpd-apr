"""Opt-in completion-to-Codex bridge; never execute or retry experiments here.

The existing SSH observer authenticates terminal artifacts. Only an explicitly
registered family/release can enqueue a fixed follow-up in this existing chat.
Use the supported `codex queue` command without overriding permissions/models.
Claim before dispatch: an ambiguous delivery is surfaced, never blindly resent.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

VERSION = 'zpd_completion_continuation_v1'
PROJECT = Path('/Users/cdw/VSCode/zpd-apr')
THREAD = '019fa3df-f13d-7cf2-8e2d-5a2a9a84d3d5'
CODEX = Path('/Users/cdw/.local/bin/codex')
REMOTE = '/home/cdw/VSCode/zpd-apr'
DEADLINE_POLICY = PROJECT / 'analysis_protocols/zpd-deadline-20261021.json'
UUID = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b'\n'


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def deadline_policy():
    if not DEADLINE_POLICY.is_file():return None
    value=json.loads(DEADLINE_POLICY.read_bytes())
    require(value['version']=='zpd_user_deadline_v1'
        and value['deadline']=='2026-10-21T13:00:00+09:00'
        and value['local_project']==str(PROJECT) and value['remote_project']==REMOTE
        and value['thread_id']==THREAD and value['new_experiments_after_deadline'] is False
        and value['report_family']=='zpd-deadline-summary-20261021','user deadline policy differs')
    return value


def deadline_prompt(policy):
    return f'''[ZPD-APR 사용자 지정 마감 / 최종 방법론 선정]
사용자가 지정한 실험 마감은 {policy['deadline']} (Asia/Seoul)이며 이제 도달했다.
이 요청은 기존의 무기한 개선 지시보다 우선한다. 새 실험·학습·재시도·재개를 하지 않는다.
1. UbuntuServer {REMOTE}의 마감 타이머와 outputs/zpd-deadline-20261021 기록, 실제 프로세스/정상 종료/해시를 확인한다. 마감에 중단된 실행은 incomplete로 보존하고 COMPLETE나 성공 결과를 만들어내지 않는다. 아직 실행 중인 작업이 있으면 프로젝트 소속을 검증한 뒤 사용자 마감 범위에서 중단한다.
2. 여태까지의 개선 방향, 완료 성능, 음성 결과, 통제 실험과 미완료 작업을 빠짐없이 정리한다. 서로 다른 데이터·후보 예산·측정 기준을 한 순위표로 섞지 않는다. 실제 데이터/고정 gate는 변경하지 않는다.
3. 기존 C/H/HS/U, 회귀, unknown, 모든 fold 조건과 근거의 신뢰도를 함께 비교하여 가장 근거가 좋은 방법론 하나를 추천한다. 최고 관측 RR은 별도로 명시하고 gate 실패를 숨기지 않는다. 개선안이 통과하지 못했다면 기존 방법 유지가 최선임을 명확히 말한다. 교육 효과나 Accept를 주장하지 않는다.
4. 최종 한국어 보고서를 이 대화에 제공하고 dev에 기록한다. 분석·확인만 허용하며 후속 실험을 등록하지 않는다. 파일·모델·음성 결과·사용자 변경을 보존하고 main/paper 공개나 영구 삭제를 하지 않는다. 연결/전달 문제가 있으면 검증하지 못한 부분을 밝힌다.
'''


def write_atomic(path, value):
    temporary = path.with_suffix('.partial')
    with temporary.open('wb') as stream:
        stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def validate_config(config):
    require(config['version'] == VERSION and config['enabled'] is True, 'explicit enabled configuration required')
    require(config['thread_id'] == THREAD and config['project'] == str(PROJECT)
            and config['codex'] == str(CODEX), 'fixed existing chat/project/CLI scope required')
    require(config['permission_overrides'] is False and config['retry_ambiguous_delivery'] is False,
            'permission overrides and ambiguous retries are forbidden')
    require(type(config['targets']) is list and config['targets'], 'explicit targets required')
    require(len({t['family'] for t in config['targets']}) == len(config['targets']), 'duplicate family registration')
    for target in config['targets']:
        require(re.fullmatch(r'zpd-[a-z0-9-]+', target['family']) is not None
                and re.fullmatch(r'[0-9a-f]{64}', target['release_sha256']) is not None,
                'canonical family/release identity required')
    return config


def terminal_event(row, target):
    if row.get('state') not in ('complete', 'error'):
        return None
    require(row['family'] == target['family'] and row.get('release_sha256') == target['release_sha256'],
            'observed terminal release differs from registered release')
    event = dict(family=row['family'], release_sha256=target['release_sha256'], state=row['state'])
    if row['state'] == 'complete':
        pin = row.get('certificate_sha256')
        require(type(pin) is str and re.fullmatch(r'[0-9a-f]{64}', pin) is not None,
                'verified completion certificate required')
        event['certificate_sha256'] = pin
    else:
        require(type(row.get('errors')) is list and row['errors'], 'explicit error evidence required')
        # Only a hash is passed, not untrusted stderr/program text as instructions.
        event['error_evidence_sha256'] = digest(row['errors'])
    event['event_id'] = digest(event)
    return event


def followup_prompt(event, policy=None):
    """The user authorized this workflow; observations cannot supply commands."""
    deadline_note = (f"[최신 사용자 지시 우선] 실험 마감은 {policy['deadline']} (KST)이다. 실제 현재 시각을 확인한다. "
        "마감 이후 새 실험·재시도·재개를 금지하고 최종 비교·best 방법론 선정만 수행한다. "
        "마감 전에도 남은 시간을 고려해 현재 학습 및 고정 평가를 우선한다. "
        "analysis_protocols/zpd-deadline-20261021.json 및 AGENTS.md를 확인하고 마감 감시를 보존한다.\n\n") if policy else ''
    return deadline_note + f'''[ZPD-APR 자동 후속 실행 / 사용자 요청에 따라 등록된 완료 감시]
이벤트: {event['state']}; family={event['family']}
고정 release SHA-256: {event['release_sha256']}
이벤트 ID: {event['event_id']}

사용자는 실험마다 확인·진행 요청을 반복하지 않도록, 완료 후 결과 분석과 다음 방법론 개선 작업을 자동으로 이어가라고 요청했다. 이 메시지는 그 요청에 따른 감시기의 알림이며 새로운 권한 부여나 실험 성공 판정이 아니다.

1. {REMOTE}/outputs/{event['family']}의 실제 프로세스, 정상 종료, COMPLETE/해시, 오류와 변경 내역을 다시 확인한다. 다른 실행이 진행 중이면 중복 실험을 시작하지 않는다. 현재 채팅에 수동 작업이 진행 중이라면 그 상태와 충돌하지 않게 조정한다.
2. 완료 결과를 기존 C/H/HS/U 통제와 고정 gate에 따라 분석한다. 오류이면 먼저 원인을 진단한다. 보고만 하고 멈추지 말고, 이미 승인된 ZPD-APR 범위의 다음 근거 있는 작업 하나를 선택해 구현·테스트·버전 고정 후 실행한다. 실패한 실행을 무조건 재시도하지 않고, 필요한 수정은 별도 명세/새 실행 ID로 기록한다.
3. 모든 원격 작업은 {REMOTE}/ 아래에서만 관리한다. 기존 데이터·체크포인트·음성 결과·사용자 변경을 보존하고 dev에서 기록한다. 테스트 데이터/고정 gate를 유리하게 바꾸거나 결과를 선택적으로 버리지 않는다. 개선·교육 효과·논문 Accept를 보장하지 않는다. 논문 리뷰가 필요하면 AGENTS.md의 새 독립 리뷰어 절차를 따른다.
4. 현재 권한과 자동 승인 검토를 그대로 따른다. sandbox/승인 우회, 새 외부 비용·서비스·비공개 데이터 접근, 영구 삭제, main/paper 공개 등 범위 밖의 조치는 요청한다. 반복적인 '계속할까요'는 묻지 않는다.
5. 새 비동기 실험을 시작했다면 종료 전에 감시기에 그 family와 release를 명시적으로 등록하고 실제 감시 읽기 결과를 확인한다. 기존 작업의 검증된 종료 없이 다음 작업을 풀지 않는다. 1시간마다 진행상황, 완료 예제/전체 수, 오류, 측정 가능한 ETA와 다음 작업을 한국어로 보고한다.
6. 성공적으로 처리한 결과와 다음 작업을 이 대화에 보고한다. 현재 실험이 아직 진행 중인 것으로 확인되면 상태만 기록하고 기다리며 재실행하지 않는다.
'''


def dispatch(snapshot, config_path, state_directory, *, run=None, now=None):
    """At most one dispatch per registered family, including uncertain outcomes."""
    config_path, state_directory = Path(config_path), Path(state_directory)
    if not config_path.exists():
        return dict(status='not_configured', queued=[])
    config = json.loads(config_path.read_bytes())
    if config.get('enabled') is False:
        return dict(status='disabled', queued=[])
    validate_config(config)
    policy=deadline_policy();now=datetime.now(timezone.utc) if now is None else now
    expired=policy is not None and now>=datetime.fromisoformat(policy['deadline'])
    if snapshot.get('connection_error') and not expired:
        return dict(status='remote_unavailable', queued=[])
    rows = snapshot['experiments']
    require(len({r['family'] for r in rows}) == len(rows), 'duplicate observed families')
    by_family = {r['family']: r for r in rows}
    events = []
    for target in ([] if expired else config['targets']):
        row = by_family.get(target['family'])
        if row is not None:
            event = terminal_event(row, target)
            if event is not None:
                events.append(event)
    if expired:
        event=dict(family=policy['report_family'],state='deadline',policy_sha256=digest(policy))
        event['event_id']=digest(event);events=[event]
    state_directory.mkdir(parents=True, exist_ok=True)
    require(state_directory.resolve() == state_directory.absolute(), 'canonical continuation state directory required')
    state_path = state_directory / 'state.json'
    run = subprocess.run if run is None else run
    with (state_directory / 'dispatch.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return dict(status='another_dispatcher_active', queued=[])
        state = json.loads(state_path.read_bytes()) if state_path.exists() else dict(version=VERSION, deliveries={})
        require(state['version'] == VERSION and type(state['deliveries']) is dict, 'continuation state schema differs')
        queued, uncertain, handled = [], [], []
        for event in events:
            family = event['family']
            if family in state['deliveries']:
                previous = state['deliveries'][family]
                if previous['status'] != 'queued':
                    uncertain.append(dict(family=family, status=previous['status']))
                else:
                    handled.append(family)
                continue
            entry = dict(event=event, status='dispatch_claimed', thread_id=THREAD,
                config_sha256=digest(config), claimed_at=datetime.now(timezone.utc).isoformat())
            state['deliveries'][family] = entry
            write_atomic(state_path, state)  # Crash/timeout can never blindly send a second message.
            prompt=deadline_prompt(policy) if event['state']=='deadline' else followup_prompt(event,policy)
            command = [str(CODEX), 'queue', '--thread', THREAD, '--message', prompt]
            try:
                result = run(command, cwd=str(PROJECT), check=False, timeout=60, capture_output=True, text=True)
                receipt = re.fullmatch(r'Queued message (' + UUID + r') for thread (' + UUID + r')\.\s*', result.stdout)
                if result.returncode == 0 and receipt is not None and receipt.group(2) == THREAD:
                    entry.update(status='queued', queue_message_id=receipt.group(1),
                                 queued_at=datetime.now(timezone.utc).isoformat())
                    queued.append(dict(family=family, queue_message_id=receipt.group(1), event_id=event['event_id']))
                else:
                    entry.update(status='delivery_unconfirmed', returncode=result.returncode,
                                 stdout_sha256=digest(result.stdout), stderr_sha256=digest(result.stderr))
                    uncertain.append(dict(family=family, status=entry['status']))
            except (OSError, subprocess.SubprocessError) as error:
                entry.update(status='delivery_unconfirmed', error_type=type(error).__name__)
                uncertain.append(dict(family=family, status=entry['status']))
            write_atomic(state_path, state)
        return dict(status='attention_required' if uncertain else 'queued' if queued else 'idle',
                    queued=queued, unconfirmed=uncertain, previously_queued=handled,
                    experiments_executed_by_bridge=False, permission_overrides=False,
                    deadline=policy['deadline'] if policy else None, deadline_reached=expired)
