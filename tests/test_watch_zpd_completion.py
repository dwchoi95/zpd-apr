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
        self.assertTrue(report.startswith('전체 소스 이력 표현'))

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


if __name__=='__main__':unittest.main()
