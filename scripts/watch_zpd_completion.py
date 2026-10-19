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
            'zpd-paired-inference-20261016', 'zpd-crossed-inference-20261016', 'zpd-anchored-routing-20261016',
            'zpd-anchored-diagnosis-20261016', 'zpd-anchor-tie-20261016', 'zpd-edit-balanced-20261016',
            'zpd-edit-balanced-diagnosis-20261017', 'zpd-splice-pilot-20261017', 'zpd-splice-training-20261018', 'zpd-splice-diagnosis-20261019', 'zpd-anchor-pilot-20261019', 'zpd-anchor-training-20261019', 'zpd-anchor-diagnosis-20261019', 'zpd-public-revision-20261019', 'zpd-revision-diagnosis-20261019', 'zpd-counterexample-revision-20261020', 'zpd-deanchored-revision-20261020', 'zpd-deanchored-diagnosis-20261020', 'zpd-likelihood-selection-20261020')
FAMILY_NAMES = dict(zip(FAMILIES, ('후보 진단', '현재 코드 마지막 배치', '전체 소스 이력 표현',
                                 '동일 조건 C/H 신규 학습', 'C/H 학습 완료 후 평가 복구', '어댑터·입력 교차 진단', '현재 코드 후보 고정 라우팅',
                                 '고정 라우팅 후보 누락분 진단', '공개 동점 후보 선택 개선', '수정·보존 균형 학습',
                                 '균형 학습 후보·회귀 원인 진단', '줄 구간 수정 방식 사전 검증', '줄 구간 수정 C/H 학습·평가', '줄 구간 수정 실패·후보 진단', '원문 지정 수정 방식 사전 검증', '원문 지정 수정 C/H 학습·평가', '원문 지정 후보·회귀 원인 진단', '공개 실행 피드백 기반 두 번째 후보 생성', '공개 피드백 수정 후보·복사 실패 진단', '공개 실패 반례 기반 조건부 수정', '실패 생성 코드 비노출 반례 수정', '비노출 반례 후보·공개 비공개 전이 진단', '이력 조건부 확률 후보 선택')))
SPLICE_FAMILY = 'zpd-splice-pilot-20261017'
ANCHOR_PILOT_FAMILY = 'zpd-anchor-pilot-20261019'
PILOT_FAMILIES = (SPLICE_FAMILY, ANCHOR_PILOT_FAMILY)
SPLICE_TRAINING_FAMILY = 'zpd-splice-training-20261018'
SPLICE_TRAINING_UNIT_PREFIX = 'zpd-splice-training-20261018-v2'
ANCHOR_TRAINING_FAMILY = 'zpd-anchor-training-20261019'
ANCHOR_TRAINING_UNIT_PREFIX = 'zpd-anchor-training-20261019-v1'
PAIRED_FAMILY = 'zpd-paired-history-run-20261015'
RECOVERY_FAMILY = 'zpd-paired-inference-20261016'
CROSSED_FAMILY = 'zpd-crossed-inference-20261016'
ANCHORED_FAMILY = 'zpd-anchored-routing-20261016'
DEANCHORED_FAMILY = 'zpd-deanchored-revision-20261020'
DEANCHORED_UNIT_PREFIX = 'zpd-deanchored-revision-20261020-v1'
COUNTEREXAMPLE_FAMILY = 'zpd-counterexample-revision-20261020'
COUNTEREXAMPLE_UNIT_PREFIX = 'zpd-counterexample-revision-20261020-v1'
REVISION_FAMILY = 'zpd-public-revision-20261019'
REVISION_UNIT_PREFIX = 'zpd-public-revision-20261019-v1'
DIAGNOSIS_FAMILY = 'zpd-anchored-diagnosis-20261016'
BALANCED_DIAGNOSIS_FAMILY = 'zpd-edit-balanced-diagnosis-20261017'
SPLICE_DIAGNOSIS_FAMILY = 'zpd-splice-diagnosis-20261019'
ANCHOR_DIAGNOSIS_FAMILY = 'zpd-anchor-diagnosis-20261019'
REVISION_DIAGNOSIS_FAMILY = 'zpd-revision-diagnosis-20261019'
DEANCHORED_DIAGNOSIS_FAMILY = 'zpd-deanchored-diagnosis-20261020'
DIAGNOSIS_FAMILIES = (DIAGNOSIS_FAMILY, BALANCED_DIAGNOSIS_FAMILY, SPLICE_DIAGNOSIS_FAMILY, ANCHOR_DIAGNOSIS_FAMILY, REVISION_DIAGNOSIS_FAMILY, DEANCHORED_DIAGNOSIS_FAMILY)
LIKELIHOOD_FAMILY = 'zpd-likelihood-selection-20261020'
TIE_FAMILY = 'zpd-anchor-tie-20261016'
TIE_UNIT = 'zpd-anchor-tie-20261016-v1-coordinator.service'
BALANCED_FAMILY = 'zpd-edit-balanced-20261016'
BALANCED_UNIT_PREFIX = 'zpd-edit-balanced-20261016-v1'
MATCHED_FAMILIES = (PAIRED_FAMILY, RECOVERY_FAMILY, CROSSED_FAMILY, ANCHORED_FAMILY, BALANCED_FAMILY, SPLICE_TRAINING_FAMILY, ANCHOR_TRAINING_FAMILY, REVISION_FAMILY, COUNTEREXAMPLE_FAMILY, DEANCHORED_FAMILY)
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
    if directory.name in PILOT_FAMILIES:
        require(outer['status']=='complete' and outer['model_promotion'] is False
            and set(outer['phases']) in ({'materialize'},{'materialize','capacity'}), 'splice pilot identity differs')
        verify_files(directory,'VERIFIED_COMPLETE.json')
        for phase,pin in outer['phases'].items():
            cert_path=directory/(phase+'-VERIFIED_COMPLETE.json')
            require(sha(cert_path)==pin,'splice child certificate drift')
            cert=read(cert_path);stage=directory/(phase+'-v1');e=cert['exit']
            require(cert['release_sha256']==outer['release_sha256'] and cert['cleanup_verified'] is True
                and all(e.get(k)==v for k,v in dict(Result='success',ExecMainCode='1',ExecMainStatus='0',MainPID='0',SubState='exited').items())
                and sha(stage/'STAGE_COMPLETE.json')==cert['complete_sha256'],'splice child not verified')
            seal=verify_files(stage,'STAGE_COMPLETE.json')
            require(seal['release_sha256']==outer['release_sha256'] and seal['phase']==phase
                and {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()}
                ==set(seal['files_sha256'])|{'STAGE_COMPLETE.json'},'splice stage inventory differs')
        report=read(directory/'REPORT.json')
        expected_codec = ('unique_original_content_edits_v1' if directory.name == ANCHOR_PILOT_FAMILY
                          else 'original_line_splices_v1')
        require(report['materialization']['codec'] == expected_codec, 'pilot codec identity differs')
        require(report['decision']==outer['decision'] and report['actual_fit'] is False
            and report['model_promotion'] is False and report['performance_measured'] is False,'splice claim differs')
        require((report['decision']=='ready_for_training')==('capacity' in outer['phases']), 'splice capacity decision differs')
        if report['decision']=='ready_for_training':
            require(report['capacity']['status']=='passed' and report['capacity']['optimizer_steps']==0
                and report['capacity']['actual_fit'] is False and report['capacity']['published_adapter'] is False,
                'splice no-fit capacity required')
        else:require(report['decision']=='hold' and report['materialization']['overflow'],'splice hold reason missing')
        return dict(decision=report['decision'],performance_measured=False)
    if directory.name in (TIE_FAMILY,LIKELIHOOD_FAMILY):
        require(outer['status']=='complete' and outer['layout_variant']==('public_tie_conditional_mean_logprob_v1' if directory.name==LIKELIHOOD_FAMILY else 'public_anchor_tie_preference_v1')
                and outer['model_promotion'] is False and outer['provisional_until_coordinator_normal_exit'] is True
                and set(outer['phases'])=={'selection','assessment'}, 'tie replay identity differs')
        verify_files(directory,'VERIFIED_COMPLETE.json')
        for phase,pin in outer['phases'].items():
            cert_path=directory/(phase+'-VERIFIED_COMPLETE.json')
            require(sha(cert_path)==pin,'tie child certificate drift')
            cert=read(cert_path);stage=directory/(phase+'-v1')
            normal=(cert.get('returncode')==0) if directory.name==TIE_FAMILY else (cert['exit']['ExecMainCode']=='1'
                and cert['exit']['ExecMainStatus']=='0' and cert['exit']['Result']=='success' and cert['exit']['MainPID']=='0'
                and cert['exit']['SubState']=='exited' and cert['cleanup_verified'] is True and cert['cgroup_removed'] is True)
            require(cert['status']=='complete' and normal
                    and cert['release_sha256']==outer['release_sha256']
                    and sha(stage/'STAGE_COMPLETE.json')==cert['complete_sha256'],'tie child exit or seal differs')
            seal=verify_files(stage,'STAGE_COMPLETE.json')
            require(seal['release_sha256']==outer['release_sha256'] and seal['phase']==phase
                    and {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()}
                    ==set(seal['files_sha256'])|{'STAGE_COMPLETE.json'}, 'tie stage inventory differs')
        report=read(directory/'REPORT.json')
        if directory.name==LIKELIHOOD_FAMILY:
            seal=read(directory/'selection-v1/PREDICTIONS_COMPLETE.json')
            require(seal['release_sha256']==outer['release_sha256'] and seal['private_assessment_accessed'] is False
                and seal['choices']==1280 and sha(directory/'selection-v1/predictions.json')==seal['predictions_sha256']
                and sha(directory/'assessment-v1/report.json')==sha(directory/'REPORT.json')
                and report['layout_variant']==outer['layout_variant'], 'likelihood selection/assessment binding differs')
        require(report['adaptive_cache_replay'] is True and report['new_execution'] is False
                and report['model_promotion'] is False, 'cache replay claim differs')
        return report_counts(report)
    if directory.name in (PAIRED_FAMILY, BALANCED_FAMILY, SPLICE_TRAINING_FAMILY, ANCHOR_TRAINING_FAMILY):
        phases = PAIRED_PHASES if directory.name == PAIRED_FAMILY else PAIRED_PHASES[1:]
        result = verify_paired_terminal(directory, outer, phases)
        if directory.name == SPLICE_TRAINING_FAMILY:
            require(read(directory/'REPORT.json')['splice_intervention']['codec']=='original_line_splices_v1',
                'splice training codec differs')
        if directory.name == ANCHOR_TRAINING_FAMILY:
            require(read(directory/'REPORT.json')['anchor_intervention']['codec']=='unique_original_content_edits_v1',
                'anchor training codec differs')
        if directory.name == BALANCED_FAMILY:
            require(read(directory/'REPORT.json')['objective_intervention']['objective']['version']
                    == 'edit_copy_balanced_ce_v1', 'balanced objective report differs')
        return result
    if directory.name in (RECOVERY_FAMILY,CROSSED_FAMILY,ANCHORED_FAMILY,REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
        variant = {RECOVERY_FAMILY:'paired_history_ipc_recovery_v1', CROSSED_FAMILY:'crossed_adapter_input_diagnostic_v1',
                   ANCHORED_FAMILY:'current_anchored_equal_budget_routing_v1',
                   REVISION_FAMILY:'public_execution_conditioned_second_draw_v1',
                   COUNTEREXAMPLE_FAMILY:'public_failure_counterexample_second_draw_v1',
                   DEANCHORED_FAMILY:'public_failure_deanchored_second_draw_v1'}[directory.name]
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
        if directory.name == ANCHORED_FAMILY:
            report=read(directory/'REPORT.json')
            require(report['model_promotion'] is False and report['adaptive_replay'] is True
                    and report['generated_during_this_run']==0 and report['routing']['slots_per_arm']==2,
                    'anchored routing claim boundary differs')
        if directory.name in (REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
            report=read(directory/'REPORT.json');amendment=report['public_revision']
            require(report['model_promotion'] is False and report['confirmatory'] is False
                and report['educational_benefit_established'] is False
                and amendment['first_slot_reused_exactly'] is True and amendment['revised_slot']==1
                and amendment['private_feedback_used'] is False and amendment['gate_changed'] is False
                and amendment['fitting'] is False and amendment['candidate_budget_per_arm']==2,
                'public revision claim boundary differs')
            if directory.name in (COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
                require(amendment['policy']=='stable_public_failure_repair_else_independent'
                    and amendment['planned_new_slots']==334 and amendment['existing_slots']==2226
                    and amendment['all_public_pass_still_revised'] is False
                    and amendment['failure_counts']==dict(C=80,H=87,HS=82,U=85)
                    and amendment['explicit_sample_inputs_and_expected_outputs'] is True,
                    'counterexample branch contract differs')
            if directory.name==DEANCHORED_FAMILY:
                require(amendment['generated_proposal_code_shown'] is False
                    and amendment['original_student_sources_removed']==0
                    and amendment['original_routing_unchanged'] is True, 'deanchored scope differs')
    if 'worker_certificate_sha256' in outer:
        require(outer['status']=='complete', 'incomplete diagnostic outer seal')
        require(sha(directory/'WORKER_VERIFIED_COMPLETE.json')==outer['worker_certificate_sha256'], 'worker certificate differs')
        cert=read(directory/'WORKER_VERIFIED_COMPLETE.json')
        require(cert['cleanup_verified'] is True and cert['exit']['Result']=='success'
                and cert['exit']['ExecMainStatus']=='0' and cert['exit']['MainPID']=='0', 'worker not released normally')
        require(sha(directory/'run-v1/COMPLETE.json')==cert['complete_sha256'], 'worker result seal differs')
        verify_files(directory/'run-v1','COMPLETE.json')
        require(sha(directory/'diagnosis-complete-v1/COMPLETE.json')==outer['diagnosis_complete_sha256'], 'diagnosis seal differs')
        dc=read(directory/'diagnosis-complete-v1/COMPLETE.json')
        if directory.name in DIAGNOSIS_FAMILIES:
            require(cert['release_sha256']==dc['release_sha256']==outer['release_sha256']
                    and dc['worker_complete_sha256']==cert['complete_sha256']
                    and dc['full_source_coverage'] is True and outer['model_promotion'] is False,
                    'diagnostic release or claim boundary differs')
            if directory.name in (BALANCED_DIAGNOSIS_FAMILY,SPLICE_DIAGNOSIS_FAMILY,ANCHOR_DIAGNOSIS_FAMILY,REVISION_DIAGNOSIS_FAMILY,DEANCHORED_DIAGNOSIS_FAMILY):
                require(cert['exit']['ExecMainCode']=='1' and cert['exit']['SubState']=='exited',
                        'balanced diagnosis worker normal exit not established')
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
        stage=directory/(phase+'-v1');seal=verify_files(stage,'STAGE_COMPLETE.json')
        if directory.name in (REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
            require(seal['release_sha256']==outer['release_sha256'] and seal['phase']==phase
                and {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()}
                ==set(seal['files_sha256'])|{'STAGE_COMPLETE.json'},'revision stage inventory differs')
    r=read(directory/'private-v1/evaluation/report.json')
    if directory.name in (REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
        report=read(directory/'REPORT.json')
        require(report_counts(report)==report_counts(r) and report['development_gate']==r['development_gate']
            and report['release_sha256']==outer['release_sha256'],'revision final/private result differs')
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


def verify_paired_terminal(directory, outer, phases=PAIRED_PHASES):
    """Only eight normal exits, cleanup and sealed results establish completion."""
    require(outer['status']=='complete' and set(outer['phases'])==set(phases), 'all fixed phases required')
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
    phases = (('generation','public','private') if root.name in
              (RECOVERY_FAMILY,CROSSED_FAMILY,ANCHORED_FAMILY,REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY) else PAIRED_PHASES[1:] if root.name in
              (BALANCED_FAMILY, SPLICE_TRAINING_FAMILY, ANCHOR_TRAINING_FAMILY) else PAIRED_PHASES)
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
            row.update(completed_examples=len(row['completed_phases']),total_examples=len(phases),progress_unit='단계')
    materialized=root/'materialize-v1/materialized'
    if (materialized/'COMPLETE.json').is_file() and (materialized/'report.json').is_file():
        row['training_population']=read(materialized/'report.json').get('counts',{})
        if path is None and phase in ('train-C','train-H'):
            train=row['training_population'].get('train',{})
            total=train.get('examples',train.get('retained_examples'))
            if type(total) is int and total>0:
                row.update(completed_examples=0,total_examples=total,progress_unit='예제',worker_phase='preparing')
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
            if family in (*MATCHED_FAMILIES,*DIAGNOSIS_FAMILIES,TIE_FAMILY,LIKELIHOOD_FAMILY,*PILOT_FAMILIES) and (root/'COORDINATOR.json').is_file():
                row['release_sha256']=read(root/'COORDINATOR.json').get('release_sha256')
            failures=sorted(p for p in root.rglob('*FAILED*.json') if p.is_file())
            if family in MATCHED_FAMILIES:
                failures+=sorted(p for p in root.rglob('REJECTED_COMPLETE.json') if p.is_file())
            if failures:
                row.update(state='error',errors=[str(p.relative_to(root)) for p in failures])
            elif family in PILOT_FAMILIES:
                try:row.update(splice_progress(root))
                except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
                    row.update(state='error',errors=['splice observer validation: '+str(exc)[:240]])
            elif family in (TIE_FAMILY,LIKELIHOOD_FAMILY):
                try:
                    if (root/'VERIFIED_COMPLETE.json').is_file():
                        p=likelihood_properties() if family==LIKELIHOOD_FAMILY else tie_properties()
                        if p.get('MainPID') not in (None,'0'):
                            row.update(state='running',phase='normal_exit_pending',completed_examples=320)
                        else:
                            require(p.get('MainPID')=='0' and p.get('ControlGroup')==''
                                and p.get('Result')=='success' and p.get('ExecMainCode')=='1'
                                and p.get('ExecMainStatus')=='0' and p.get('SubState')=='exited',
                                'tie coordinator normal exit/cleanup not established')
                            outer=read(root/'VERIFIED_COMPLETE.json')
                            require(outer['release_sha256']==row.get('release_sha256'),'tie coordinator release differs')
                            row.update(state='complete',completed_examples=320,
                                certificate_sha256=sha(root/'VERIFIED_COMPLETE.json'),results=verify_terminal(root,outer),
                                completed_at=datetime.fromtimestamp((root/'VERIFIED_COMPLETE.json').stat().st_mtime,KST).isoformat())
                    elif (root/'STATUS.json').is_file():
                        progress=read(root/'STATUS.json')
                        if family==LIKELIHOOD_FAMILY and progress.get('phase')=='selection' and (root/'selection-v1/STATUS.json').is_file():
                            progress=read(root/'selection-v1/STATUS.json')
                        row.update(state='running',**progress)
                    else:row['state']='starting'
                except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
                    row.update(state='error',errors=['tie observer validation: '+str(exc)[:240]])
            elif family in DIAGNOSIS_FAMILIES:
                try:
                    if (root/'VERIFIED_COMPLETE.json').is_file():
                        if family in (BALANCED_DIAGNOSIS_FAMILY,SPLICE_DIAGNOSIS_FAMILY,ANCHOR_DIAGNOSIS_FAMILY,REVISION_DIAGNOSIS_FAMILY,DEANCHORED_DIAGNOSIS_FAMILY):
                            values=(deanchored_diagnosis_properties() if family==DEANCHORED_DIAGNOSIS_FAMILY else
                                    revision_diagnosis_properties() if family==REVISION_DIAGNOSIS_FAMILY else
                                    anchor_diagnosis_properties() if family==ANCHOR_DIAGNOSIS_FAMILY else
                                    splice_diagnosis_properties() if family==SPLICE_DIAGNOSIS_FAMILY
                                    else balanced_diagnosis_properties())
                            if values.get('MainPID') not in (None,'0'):
                                row.update(state='running',phase='normal_exit_pending',completed_examples=320)
                                rows.append(row);continue
                            require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
                                and values.get('Result')=='success' and values.get('ExecMainCode')=='1'
                                and values.get('ExecMainStatus')=='0' and values.get('SubState')=='exited',
                                'balanced diagnosis coordinator normal exit/cleanup not established')
                        outer=read(root/'VERIFIED_COMPLETE.json')
                        require(outer['release_sha256']==row.get('release_sha256'), 'diagnostic coordinator identity differs')
                        row.update(state='complete',completed_examples=320,
                            certificate_sha256=sha(root/'VERIFIED_COMPLETE.json'),
                            completed_at=datetime.fromtimestamp((root/'VERIFIED_COMPLETE.json').stat().st_mtime,KST).isoformat(),
                            results=verify_terminal(root,outer))
                    elif (root/'run-v1/STATUS.json').is_file():
                        progress=read(root/'run-v1/STATUS.json')
                        row.update({k:progress[k] for k in ('phase','completed_examples','total_examples',
                            'completed_unique_sources','total_unique_sources','completed_case_attempts',
                            'total_case_attempts','completed_source_blocks','total_source_blocks','elapsed_seconds') if k in progress})
                        row['state']='running'
                    else:row['state']='starting'
                except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
                    row.update(state='error',errors=['diagnostic observer validation: '+str(exc)[:240]])
            elif family in MATCHED_FAMILIES:
                try:
                    if (root/'VERIFIED_COMPLETE.json').exists():
                        if family in (BALANCED_FAMILY,SPLICE_TRAINING_FAMILY,ANCHOR_TRAINING_FAMILY,REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
                            values=(deanchored_properties() if family==DEANCHORED_FAMILY else counterexample_properties() if family==COUNTEREXAMPLE_FAMILY else revision_properties() if family==REVISION_FAMILY else balanced_properties() if family==BALANCED_FAMILY else
                                anchor_training_properties() if family==ANCHOR_TRAINING_FAMILY else splice_training_properties())
                            if values.get('MainPID') not in (None,'0'):
                                row.update(state='running',phase='normal_exit_pending',completed_examples=320)
                                rows.append(row);continue
                            require(values.get('MainPID')=='0' and values.get('ControlGroup')==''
                                and values.get('Result')=='success' and values.get('ExecMainCode')=='1'
                                and values.get('ExecMainStatus')=='0' and values.get('SubState')=='exited',
                                'balanced coordinator normal exit/cleanup not established')
                        outer=read(root/'VERIFIED_COMPLETE.json')
                        if family in (BALANCED_FAMILY,SPLICE_TRAINING_FAMILY,ANCHOR_TRAINING_FAMILY,REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY):
                            require(outer['release_sha256']==row.get('release_sha256'), 'balanced coordinator release differs')
                        results=verify_terminal(root,outer)
                        row.update(state='complete',completed_examples=320,certificate_sha256=sha(root/'VERIFIED_COMPLETE.json'),
                            completed_at=datetime.fromtimestamp((root/'VERIFIED_COMPLETE.json').stat().st_mtime,KST).isoformat(),
                            results=results,matched_fresh_training=family not in (REVISION_FAMILY,COUNTEREXAMPLE_FAMILY,DEANCHORED_FAMILY),
                            training_population=read(root/'REPORT.json').get('training_population',{}))
                    else:
                        row.update(paired_progress(root))
                        if family==RECOVERY_FAMILY:row['unit_prefix']='zpd-paired-inference-20261016-v1'
                        if family==CROSSED_FAMILY:row['unit_prefix']='zpd-crossed-inference-20261016-v1'
                        if family==ANCHORED_FAMILY:row['unit_prefix']='zpd-anchored-routing-20261016-v1'
                        if family==BALANCED_FAMILY:row['unit_prefix']=BALANCED_UNIT_PREFIX
                        if family==SPLICE_TRAINING_FAMILY:row['unit_prefix']=SPLICE_TRAINING_UNIT_PREFIX
                        if family==ANCHOR_TRAINING_FAMILY:row['unit_prefix']=ANCHOR_TRAINING_UNIT_PREFIX
                        if family==REVISION_FAMILY:row['unit_prefix']=REVISION_UNIT_PREFIX
                        if family==COUNTEREXAMPLE_FAMILY:row['unit_prefix']=COUNTEREXAMPLE_UNIT_PREFIX
                        if family==DEANCHORED_FAMILY:row['unit_prefix']=DEANCHORED_UNIT_PREFIX
                except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
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


def splice_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-splice-pilot-20261017-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def splice_training_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        SPLICE_TRAINING_UNIT_PREFIX+'-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def anchor_training_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        ANCHOR_TRAINING_UNIT_PREFIX+'-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def deanchored_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        DEANCHORED_UNIT_PREFIX+'-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def counterexample_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        COUNTEREXAMPLE_UNIT_PREFIX+'-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def revision_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        REVISION_UNIT_PREFIX+'-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def splice_progress(root):
    row=dict(state='starting',completed_examples=0,total_examples=23564)
    if not (root/'COORDINATOR.json').is_file():return row
    props=anchor_pilot_properties() if root.name == ANCHOR_PILOT_FAMILY else splice_properties()
    require(props.get('ActiveState')!='failed','splice coordinator failed')
    if (root/'VERIFIED_COMPLETE.json').is_file():
        if props.get('MainPID') not in (None,'0'):
            return dict(row,state='running',phase='normal_exit_pending')
        require(all(props.get(k)==v for k,v in dict(MainPID='0',ControlGroup='',Result='success',
            ExecMainCode='1',ExecMainStatus='0',SubState='exited').items()),'splice coordinator normal exit required')
        outer=read(root/'VERIFIED_COMPLETE.json')
        require(outer['release_sha256']==read(root/'COORDINATOR.json')['release_sha256'],'splice release differs')
        results=verify_terminal(root,outer)
        return dict(row,state='complete',completed_examples=23564,results=results,
            certificate_sha256=sha(root/'VERIFIED_COMPLETE.json'),
            completed_at=datetime.fromtimestamp((root/'VERIFIED_COMPLETE.json').stat().st_mtime,KST).isoformat())
    require(props.get('MainPID') not in (None,'0'),'splice coordinator exited without seal')
    state=read(root/'STATUS.json') if (root/'STATUS.json').is_file() else {}
    phase=state.get('phase','materialize');path=root/'materialize-v1/STATUS.json'
    if path.is_file():row.update(read(path))
    row.update(state='running',phase=phase)
    if phase=='capacity':row.update(completed_examples=23564,total_examples=23564)
    return row


def anchor_pilot_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-anchor-pilot-20261019-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def likelihood_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-likelihood-selection-20261020-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def tie_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',TIE_UNIT],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def balanced_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        BALANCED_UNIT_PREFIX+'-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def balanced_diagnosis_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-edit-balanced-diagnosis-20261017-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def deanchored_diagnosis_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-deanchored-diagnosis-20261020-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def revision_diagnosis_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-revision-diagnosis-20261019-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def splice_diagnosis_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-splice-diagnosis-20261019-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def anchor_diagnosis_properties():
    raw=subprocess.check_output(['/usr/bin/systemctl','--user','show','--all',
        'zpd-anchor-diagnosis-20261019-v1-coordinator.service'],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


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
            total=r.get('total_examples',320)
            line=f"{label}: 완료 {total}/{total}, {r['completed_at'][11:16]} KST"
            if r['family'] in PILOT_FAMILIES:
                line+=f"; 사전 검증 {r['results']['decision']}, 학습·성능 평가 아님. 다음: 인증된 준비 결과에 따른 학습 결정"
            elif r['family'] in MATCHED_FAMILIES:
                line+='; 신규 C/H 어댑터별 정답 '+', '.join(f"{a} {r['results'][a]['stable_ac']}/320" for a in ('C','H','HS','U'))
                population=r.get('training_population',{}).get('train',{})
                if 'candidate_examples' in population and 'retained_examples' in population:
                    line+=f"; 학습 원천 {population['candidate_examples']}→적격 {population['retained_examples']}예제"
                elif 'examples' in population:
                    line+=f"; 동일 학습 {population['examples']}예제"
                line+='. 적응적 개발 결과; 모델 승격·교육 효과 주장 없음'
                if r['family']==CROSSED_FAMILY:line+='; C 입력=H 어댑터, H/HS/U 입력=C 어댑터 (교차 진단 전용)'
                if r['family']==ANCHORED_FAMILY:line+='; 공통 C 후보 1개+조건별 H 어댑터 후보 1개 (추가 생성 없음)'
            elif r['family'] in (FAMILIES[0],*DIAGNOSIS_FAMILIES):
                c,h=r['results']['C'],r['results']['H']
                line+=f". C 정답 {c['selected_stable_ac']}, H 정답 {h['selected_stable_ac']} (H 후보 상한 {h['oracle_upper']})"
            elif r['family'] in (TIE_FAMILY,LIKELIHOOD_FAMILY):
                line+='; 정답 '+', '.join(f"{a} {r['results'][a]['stable_ac']}/320" for a in ('C','H','HS','U'))
                line+='; 기존 실행 캐시 재평가, 독립 검증 아님. 다음: 고정 gate 검토'
            else:
                c,h=r['results']['C'],r['results']['H']
                line+=f". C 정답 {c['stable_ac']}, H 정답 {h['stable_ac']}. 다음: 개선 여부 검토"
        elif r['state']=='error':line=label+': 오류 발생, 재실행하지 않음'
        elif r['state']=='not_started':line=label+': 아직 시작 안 됨'
        else:
            phase=r.get('pipeline_phase',r.get('phase'))
            display=PAIRED_LABELS.get(phase,phase or '준비') if r['family'] in MATCHED_FAMILIES else r.get('phase','준비')
            if r['family']==ANCHORED_FAMILY and phase=='generation':display='봉인 후보 구성 (재생성 없음)'
            if r['family'] in DIAGNOSIS_FAMILIES:display='미평가 후보 진단'
            if r['family'] in PILOT_FAMILIES:display=PAIRED_LABELS.get(phase,phase)
            line=f"{label}: {display} {r['completed_examples']}/{r['total_examples']} {r.get('progress_unit','예제')}, 실행장애 기록 없음"
            if r.get('attempt_statuses',{}):
                failed=sum(n for status,n in r['attempt_statuses'].items() if status!='success')
                if failed:line+=f', 생성 실패 {failed}회 (제외·재시도 없음)'
            if r.get('completed_candidates') is not None:
                line+=f", 후보 점수 {r['completed_candidates']}/{r['total_candidates']}"
            if r.get('completed_case_attempts') is not None:
                line+=f", 테스트 {r['completed_case_attempts']}/{r['total_case_attempts']}"
            if r['family']==PAIRED_FAMILY and phase=='cache' and r.get('unavailable_unique_sources'):
                line+=f", 공개 샘플 없음 {r['unavailable_unique_sources']}개 소스 (실패 아님)"
            population=r.get('training_population',{}).get('train',{})
            if r['family']==PAIRED_FAMILY and population:
                line+=f", 학습 원천 {population['candidate_examples']}→적격 {population['retained_examples']}예제"
            elapsed,done,total=r.get('elapsed_seconds'),r['completed_examples'],r['total_examples']
            if r['family']==LIKELIHOOD_FAMILY and r.get('completed_candidates') is not None:
                # Publicly unique winners require no model calls and can make
                # initial recipient completion misleading for timing.
                done,total=r['completed_candidates'],r['total_candidates']
            if r['family'] in DIAGNOSIS_FAMILIES:
                # Recipients finish only during block four; source-block work
                # is observable earlier. Estimate remains explicitly provisional.
                done,total=r.get('completed_case_attempts',0),r.get('total_case_attempts',0)
                if elapsed and done>=100 and total>done:
                    estimate=datetime.fromisoformat(snapshot['checked_at'])+timedelta(seconds=elapsed*(total-done)/done)
                    line+=f", 예상 {estimate:%H:%M} KST (테스트 속도 추정; 블록별 병렬도 차이)"
                else:line+=', 종료시각 추정 중'
                line+=', 다음: 생성 한계와 선택 손실 분리 (성능 개선 판정 아님)'
                lines.append(line)
                continue
            if elapsed and 10<=done<total:
                estimate=datetime.fromisoformat(snapshot['checked_at'])+timedelta(seconds=elapsed*(total-done)/done)
                line+=f", 현 단계 예상 {estimate:%H:%M} KST (단순 속도 추정)"
            else:line+=', 종료시각 추정 중'
            next_phase={'likelihood_selection':'봉인 후 기존 캐시 평가','selection':'봉인 후 기존 캐시 평가','generation':'공개 테스트 선택','public_selection':'전체 테스트 평가','private_execution':'자동 결과 집계'}
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
