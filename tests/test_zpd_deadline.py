from datetime import datetime
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch

from scripts import enforce_zpd_deadline as guard
from scripts import zpd_completion_continuation as bridge

POLICY=json.loads(Path('analysis_protocols/zpd-deadline-20261021.json').read_bytes())


class DeadlineTests(unittest.TestCase):
    def config(self):
        return dict(version=bridge.VERSION,enabled=True,thread_id=bridge.THREAD,project=str(bridge.PROJECT),
            codex=str(bridge.CODEX),permission_overrides=False,retry_ambiguous_delivery=False,
            targets=[dict(family='zpd-example',release_sha256='a'*64)])

    def test_before_deadline_callback_includes_override(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(bridge,'deadline_policy',return_value=POLICY):
            root=Path(tmp).resolve();p=root/'config.json';p.write_text(json.dumps(self.config()))
            run=Mock(return_value=SimpleNamespace(returncode=0,stdout='bad receipt',stderr=''))
            row=dict(family='zpd-example',release_sha256='a'*64,state='complete',certificate_sha256='b'*64)
            bridge.dispatch(dict(experiments=[row]),p,root/'state',run=run,now=datetime.fromisoformat('2026-10-21T12:59:59+09:00'))
            text=run.call_args.args[0][-1]
            self.assertIn('2026-10-21T13:00:00+09:00',text);self.assertIn('최신 사용자 지시 우선',text)

    def test_after_deadline_only_final_report_queues_once_even_offline(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(bridge,'deadline_policy',return_value=POLICY):
            root=Path(tmp).resolve();p=root/'config.json';p.write_text(json.dumps(self.config()))
            run=Mock(return_value=SimpleNamespace(returncode=0,stdout='Queued message 01234567-89ab-cdef-0123-456789abcdef for thread '+bridge.THREAD+'.\n',stderr=''))
            row=dict(family='zpd-example',release_sha256='a'*64,state='complete',certificate_sha256='b'*64)
            snap=dict(experiments=[row],connection_error='offline')
            for _ in range(2):r=bridge.dispatch(snap,p,root/'state',run=run,now=datetime.fromisoformat(POLICY['deadline']))
            self.assertTrue(r['deadline_reached']);run.assert_called_once()
            self.assertIn('최종 방법론 선정',run.call_args.args[0][-1]);self.assertNotIn('이벤트: complete',run.call_args.args[0][-1])
            saved=json.loads((root/'state/state.json').read_bytes())
            self.assertEqual(set(saved['deliveries']),{'zpd-deadline-summary-20261021'})

    def test_no_enforcement_before_deadline(self):
        scan=Mock();stop=Mock()
        with self.assertRaises(ValueError):guard.enforce(POLICY,Path('/unused'),now=datetime.fromisoformat('2026-10-21T12:59:59+09:00'),scan=scan,stop=stop)
        scan.assert_not_called();stop.assert_not_called()

    def test_service_scope_and_inactive_evidence_preserved(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(guard,'PROJECT',Path(tmp).resolve()):
            root=guard.PROJECT;directory=root/'.runtime/fixed';directory.mkdir(parents=True)
            name='zpd-example-coordinator.service';props=dict(MainPID='5',WorkingDirectory=str(directory),
                ExecStart=str(root/'.runtime/env/bin/python')+' -m scripts.run_zpd_example supervise --release x',
                ControlGroup='/user.slice/user-1000.slice/'+name)
            self.assertTrue(guard.eligible(name,props))
            worker='zpd-example-train-C.service'
            self.assertTrue(guard.eligible(worker,dict(props,ControlGroup='/user.slice/user-1000.slice/'+worker,
                ExecStart=str(root/'.runtime/env/bin/python')+' -m scripts.run_zpd_example worker --phase train-C')))
            self.assertFalse(guard.eligible(name,dict(props,MainPID='0',ControlGroup='')))
            self.assertFalse(guard.eligible('other.service',props));self.assertFalse(guard.eligible(guard.SELF,props))
            for key,value in [('WorkingDirectory','/'),('ExecStart','/bin/other'),('ControlGroup','/foreign')]:
                with self.assertRaises(ValueError):guard.eligible(name,dict(props,**{key:value}))

    def test_coordinator_stopped_before_fresh_worker_scan_no_artifacts_deleted(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(guard,'PROJECT',Path(tmp).resolve()),patch.object(guard,'validate_policy'):
            c=dict(unit='zpd-example-coordinator.service');w=dict(unit='zpd-example-worker.service');new=dict(unit='zpd-example-next.service')
            scan=Mock(side_effect=[[w,c],[w,new],[],[]]);stop=Mock()
            result=guard.enforce(POLICY,guard.PROJECT/'outputs/cutoff',now=datetime.fromisoformat(POLICY['deadline']),scan=scan,stop=stop)
            self.assertEqual([v.args[0] for v in stop.call_args_list],[c['unit'],w['unit'],new['unit']])
            self.assertFalse(result['artifacts_deleted']);self.assertFalse(result['experiment_completion_claimed'])

    def test_tampered_deadline_policy_rejected(self):
        for key,value in [('deadline','2026-10-22T13:00:00+09:00'),('remote_project','/'),('preserve_all_artifacts',False)]:
            with self.assertRaises(ValueError):guard.validate_policy(dict(POLICY,**{key:value}))


if __name__=='__main__':unittest.main()
