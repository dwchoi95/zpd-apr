import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import watch_zpd_completion as m


class WatchTests(unittest.TestCase):
    def row(self):return dict(family=m.FAMILIES[0],state='complete',certificate_sha256='a')

    def test_completion_once_and_hourly_even_unchanged(self):
        snapshot={'experiments':[self.row()]};state={'last_notification':1000,'terminal':{m.FAMILIES[0]:'complete:a'}}
        self.assertFalse(m.due(snapshot,state,1200));self.assertTrue(m.due(snapshot,state,4600))
        snapshot['experiments'][0]['certificate_sha256']='b';self.assertTrue(m.due(snapshot,state,1200))

    def test_first_completion_error_and_connection_recovery_notify(self):
        self.assertTrue(m.due({'experiments':[self.row()]},{'last_notification':100},101))
        self.assertTrue(m.due({'experiments':[],'connection_error':'offline'},{'last_notification':100},101))
        self.assertTrue(m.due({'experiments':[]},{'last_notification':100,'connection_error':'offline'},101))

    def test_no_output_means_not_started_not_complete(self):
        with tempfile.TemporaryDirectory() as d:
            s=m.remote_snapshot(Path(d))
        self.assertEqual([r['state'] for r in s['experiments']],['not_started']*len(m.FAMILIES))

    def test_full_source_family_reports_without_relaunch(self):
        row=dict(family='zpd-full-source-20261014',state='running',phase='generation',
                 completed_examples=16,total_examples=320,elapsed_seconds=60)
        report=m.korean_report(dict(checked_at='2026-10-14T13:00:00+09:00',experiments=[row]))
        self.assertIn('전체 소스 이력 표현',report)
        self.assertIn('16/320',report)
        self.assertIn('공개 테스트 선택',report)

    def test_latest_family_is_first_in_notification(self):
        rows=[dict(family=f,state='not_started') for f in m.FAMILIES]
        report=m.korean_report(dict(experiments=rows))
        self.assertTrue(report.startswith('원문 지정 수정 C/H 학습·평가'))

    def test_failure_takes_precedence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'outputs'/m.FAMILIES[0];root.mkdir(parents=True)
            (root/'MONITOR_FAILED.json').write_text('{}');(root/'VERIFIED_COMPLETE.json').write_text('{}')
            self.assertEqual(m.remote_snapshot(Path(d))['experiments'][0]['state'],'error')

    def test_partial_status_never_terminal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'outputs'/m.FAMILIES[0]/'run-v1';root.mkdir(parents=True)
            (root/'STATUS.json').write_text(json.dumps(dict(phase='complete',completed_examples=320,total_examples=320)))
            s=m.remote_snapshot(Path(d))
        self.assertEqual(s['experiments'][0]['state'],'running')
        self.assertIsNone(m.terminal_key(s['experiments'][0]))

    def test_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'value.json').write_text('{}')
            (root/'COMPLETE.json').write_text(json.dumps(dict(status='complete',files_sha256={'value.json':m.sha(root/'value.json')})))
            m.verify_files(root,'COMPLETE.json');(root/'value.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'drift'):m.verify_files(root,'COMPLETE.json')

    def test_notification_content_is_argument_not_script(self):
        body='hello " & do shell script "unsafe'
        with patch.object(m.subprocess,'run') as run:m.notify(body)
        command=run.call_args.args[0]
        self.assertEqual(command[-1],body);self.assertNotIn(body,command[-2])

    def test_completed_attempt_failures_visible_without_worker_crash(self):
        row=dict(family=m.FAMILIES[1],state='running',phase='generation',completed_examples=27,total_examples=320,
                 elapsed_seconds=95,attempt_statuses={'success':214,'resource_failure':2})
        report=m.korean_report(dict(checked_at='2026-10-13T21:11:18+09:00',experiments=[row]))
        self.assertIn('생성 실패 2회',report)
        self.assertIn('27/320',report)
        self.assertIn('현 단계 예상',report)

    def test_local_observer_never_sends_chat_and_readonly_remote_command(self):
        snapshot=dict(checked_at='now',experiments=[])
        with tempfile.TemporaryDirectory() as d,patch.object(m,'LOCAL_STATE',Path(d)), \
             patch.object(m.subprocess,'run') as run,patch.object(m,'notify') as notify:
            run.return_value.stdout=json.dumps(snapshot)
            m.observe(no_notify=True)
            result=m.read(Path(d)/'LATEST_REPORT.json')
            self.assertFalse(result['chat_message_sent']);self.assertFalse(result['experiment_mutations'])
            notify.assert_not_called();self.assertEqual(run.call_args.args[0][0],'/usr/bin/ssh')
            self.assertNotIn('systemd-run',run.call_args.args[0][-1])


class PairedHistoryWatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.project=Path(self.temp.name);self.root=self.project/'outputs'/m.PAIRED_FAMILY
        self.root.mkdir(parents=True)

    def write(self,path,value):
        path=self.root/path;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value));return m.sha(path)

    def snapshot(self):
        return m.remote_snapshot(self.project)

    def row(self):return next(r for r in self.snapshot()['experiments'] if r['family']==m.PAIRED_FAMILY)

    def test_initializing_generation_reports_examples_not_eight_training_stages(self):
        self.write(Path('STATUS.json'),dict(phase='generation',completed_phases=[]))
        row=self.row()
        self.assertEqual(row['completed_examples'],0)
        self.assertEqual(row['total_examples'],320)
        self.assertEqual(row['progress_unit'],'예제')

    def terminal(self,full_report=False,cleanup=True):
        counts={a:dict(stable_ac=n,regressions=7,unknown=11) for a,n in zip(('C','H','HS','U'),(201,202,199,198))}
        report={'full':{'results':{a:{'counts':v} for a,v in counts.items()}}}
        private_sha=self.write(Path('private-v1/evaluation/report.json'),report)
        inference_sha=self.write(Path('inference-release.json'),dict(parent_release_sha256='release',adapter_arm_map=dict(C='C',H='H',HS='H',U='H')))
        self.write(Path('INFERENCE_RELEASE_COMPLETE.json'),dict(status='complete',parent_release_sha256='release',inference_release_sha256=inference_sha))
        phases={}
        for phase in m.PAIRED_PHASES:
            files={'evaluation/report.json':private_sha} if phase=='private' else {}
            pin=inference_sha if phase in m.PAIRED_PHASES[-3:] else 'release'
            seal=self.write(Path(phase+'-v1/STAGE_COMPLETE.json'),dict(status='complete',phase=phase,release_sha256=pin,files_sha256=files))
            phases[phase]=self.write(Path(phase+'-VERIFIED_COMPLETE.json'),dict(status='complete',cleanup_verified=cleanup,
                parent_release_sha256='release',release_sha256=pin,complete_sha256=seal,
                exit={'Result':'success','ExecMainStatus':'0','MainPID':'0','ExecMainCode':'1','SubState':'exited'}))
        report_sha=self.write(Path('REPORT.json'),report if full_report else dict(counts=dict(counts,noop={'stable_ac':0}),
            training_population={'train':dict(candidate_examples=19456,retained_examples=19000)},development_gate={'decision':'hold'}))
        self.write(Path('VERIFIED_COMPLETE.json'),dict(status='complete',release_sha256='release',phases=phases,
            inference_release_sha256=inference_sha,files_sha256={'REPORT.json':report_sha}))
        return counts

    def test_existing_families_preserved_and_all_paired_paths_collected(self):
        self.assertEqual(m.FAMILIES[:3],('zpd-transition-diagnosis-20261013','zpd-current-last-20261013','zpd-full-source-20261014'))
        for phase,path in m.PAIRED_STATUS.items():
            self.write(Path('STATUS.json'),dict(phase=phase,completed_phases=[],unit=m.PAIRED_UNIT_PREFIX+'-'+phase+'.service'))
            self.write(Path(path),dict(phase='training' if phase.startswith('train-') else 'running',completed_examples=17,
                total_examples=19400,terminal_source_blocks=17,completed_source_blocks=16,planned_source_blocks=200,
                completed_case_attempts=51,planned_case_attempts=600,elapsed_seconds=60))
            with self.subTest(phase=phase):
                row=self.row();self.assertEqual(row['pipeline_phase'],phase);self.assertEqual(row['completed_examples'],17)
                self.assertEqual(row['state'],'running');self.assertIsNone(m.terminal_key(row))
                self.assertEqual(row['unit_prefix'],m.PAIRED_UNIT_PREFIX)

    def test_cache_status_schema_and_unavailable_not_failure(self):
        self.write(Path('STATUS.json'),dict(phase='cache',completed_phases=[]))
        self.write(Path(m.PAIRED_STATUS['cache']),dict(phase='running',current_block=2,completed_source_blocks=199,
            terminal_source_blocks=200,planned_source_blocks=400,completed_case_attempts=540,journaled_case_attempts=540,
            planned_case_attempts=1200,unique_sources=105,unavailable_unique_sources=5,elapsed_seconds=600))
        row=self.row();self.assertEqual(row['progress_unit'],'소스 블록');self.assertEqual(row['completed_examples'],200)
        self.assertEqual(row['completed_source_blocks'],199);self.assertEqual(row['total_case_attempts'],1200)
        report=m.korean_report(self.snapshot())
        self.assertIn('200/400 소스 블록',report);self.assertIn('테스트 540/1200',report)
        self.assertIn('공개 샘플 없음 5개 소스 (실패 아님)',report);self.assertIn('학습 입력·토큰 점검',report)

    def test_parent_training_phase_wins_over_completed_cache(self):
        self.write(Path(m.PAIRED_STATUS['cache']),dict(phase='complete',terminal_source_blocks=100,planned_source_blocks=100))
        self.write(Path('STATUS.json'),dict(phase='train-H',completed_phases=['cache','materialize','capacity','train-C']))
        self.write(Path(m.PAIRED_STATUS['train-H']),dict(phase='training',arm='H',completed_examples=111,total_examples=19000,elapsed_seconds=100))
        self.write(Path('materialize-v1/materialized/COMPLETE.json'),dict(status='complete'))
        self.write(Path('materialize-v1/materialized/report.json'),dict(counts={'train':dict(candidate_examples=19456,retained_examples=19000)}))
        row=self.row();self.assertEqual(row['pipeline_phase'],'train-H');self.assertEqual(row['completed_examples'],111)
        report=m.korean_report(self.snapshot())
        self.assertIn('H 어댑터 학습 111/19000 예제',report);self.assertIn('학습 원천 19456→적격 19000예제',report)
        self.assertIn('현 단계 예상',report);self.assertIn('다음: 후보 생성',report)

    def test_parent_only_materialization_capacity_and_finalizing_not_complete(self):
        for phase in ('materialize','capacity','complete'):
            self.write(Path('STATUS.json'),dict(phase=phase,completed_phases=list(m.PAIRED_PHASES) if phase=='complete' else ['cache']))
            with self.subTest(phase=phase):
                row=self.row();self.assertEqual(row['state'],'running');self.assertEqual(row['progress_unit'],'단계')
                self.assertIsNone(m.terminal_key(row));self.assertIn(m.PAIRED_LABELS[phase],m.korean_report(self.snapshot()))

    def test_all_eight_normal_cleanup_certificates_and_both_report_schemas(self):
        for full in (False,True):
            expected=self.terminal(full_report=full)
            row=self.row();self.assertEqual(row['state'],'complete');self.assertEqual(row['results'],expected)
            self.assertTrue(row['matched_fresh_training'])
            report=m.korean_report(self.snapshot())
            for phrase in ('신규 C/H 어댑터별 정답','C 201/320','H 202/320','HS 199/320','U 198/320','모델 승격·교육 효과 주장 없음'):
                self.assertIn(phrase,report)
            if not full:self.assertIn('학습 원천 19456→적격 19000예제',report)

    def test_uncertified_cleanup_drift_or_missing_phase_is_error_not_completion(self):
        self.terminal(cleanup=False)
        self.assertEqual(self.row()['state'],'error')
        self.terminal();self.write(Path('REPORT.json'),dict(counts={}))
        self.assertEqual(self.row()['state'],'error')
        self.terminal();outer=m.read(self.root/'VERIFIED_COMPLETE.json');outer['phases'].pop('capacity')
        self.write(Path('VERIFIED_COMPLETE.json'),outer)
        self.assertEqual(self.row()['state'],'error')
        self.assertEqual(len(self.snapshot()['experiments']),len(m.FAMILIES))

    def test_dynamic_binding_and_exit_code_substate_must_be_valid(self):
        for mutation in ('wrong_dynamic_pin','wrong_parent','bad_code','running','dynamic_bytes'):
            self.terminal()
            if mutation=='dynamic_bytes':
                self.write(Path('inference-release.json'),dict(changed=True))
            else:
                cert=m.read(self.root/'generation-VERIFIED_COMPLETE.json')
                if mutation=='wrong_dynamic_pin':cert['release_sha256']='release'
                elif mutation=='wrong_parent':cert['parent_release_sha256']='wrong-parent'
                elif mutation=='bad_code':cert['exit']['ExecMainCode']='2'
                else:cert['exit']['SubState']='running'
                pin=self.write(Path('generation-VERIFIED_COMPLETE.json'),cert)
                outer=m.read(self.root/'VERIFIED_COMPLETE.json');outer['phases']['generation']=pin
                self.write(Path('VERIFIED_COMPLETE.json'),outer)
            with self.subTest(mutation=mutation):self.assertEqual(self.row()['state'],'error')

    def test_rejected_marker_and_status_failure_notify_without_relaunch(self):
        self.write(Path('STATUS.json'),dict(phase='failed',completed_phases=['cache']))
        row=self.row();self.assertEqual(row['state'],'error')
        self.assertTrue(m.due(self.snapshot(),{'last_notification':100},101))
        self.terminal();self.write(Path('train-H-v1/REJECTED_COMPLETE.json'),{})
        row=self.row();self.assertEqual(row['state'],'error')
        self.assertIn('재실행하지 않음',m.korean_report(self.snapshot()))

    def test_paired_hourly_unchanged_and_terminal_once(self):
        self.write(Path('STATUS.json'),dict(phase='cache',completed_phases=[]))
        snapshot=self.snapshot();state={'last_notification':1000}
        self.assertFalse(m.due(snapshot,state,1200));self.assertTrue(m.due(snapshot,state,4600))
        self.terminal();snapshot=self.snapshot();row=self.row()
        self.assertTrue(m.due(snapshot,state,1200))
        state['terminal']={m.PAIRED_FAMILY:m.terminal_key(row)}
        self.assertFalse(m.due(snapshot,state,1200))


if __name__=='__main__':unittest.main()
