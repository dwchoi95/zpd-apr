"""Nonauthor synthetic boundary tests: no process launch, signals or real fit."""
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from scripts import probe_zpd_joint_progress_resources as probe


def process_identity(pid=700, *, start=42, group=700, session=700):
    return dict(pid=pid, state='S', ppid=1, pgid=group, session=session,
        starttime=start, observed_peak_rss_bytes=1024)


class ResourceProbeIndependentTests(unittest.TestCase):
    def test_cleanup_rejects_changed_leader_start_group_or_session_without_signals(self):
        first = process_identity(); process = Mock(pid=700)
        for key in ('starttime', 'pgid', 'session'):
            now = dict(first); now[key] += 1
            with self.subTest(key=key), patch.object(probe, 'group_alive', return_value=True), \
                    patch.object(probe, 'identity', return_value=now), patch.object(probe, 'stop_owned') as stop:
                with self.assertRaises(ValueError): probe.cleanup(process, first)
                stop.assert_not_called()

    def test_reaped_leader_requires_live_previously_bound_descendant(self):
        first = process_identity(); child = process_identity(701, start=45); process = Mock(pid=700)
        for live in (None, dict(child, starttime=46), dict(child, session=800)):
            with self.subTest(live=live), patch.object(probe, 'group_alive', return_value=True), \
                    patch.object(probe, 'identity', side_effect=lambda pid: None if pid == 700 else live), \
                    patch.object(probe, 'stop_owned') as stop:
                with self.assertRaises(ValueError): probe.cleanup(process, first, (child,))
                stop.assert_not_called()
        alive = {700: None, 701: child}
        def stopped(_): alive[701] = None
        with patch.object(probe, 'group_alive', side_effect=[True, False]), \
                patch.object(probe, 'identity', side_effect=lambda pid: alive[pid]), \
                patch.object(probe, 'stop_owned', side_effect=stopped) as stop:
            probe.cleanup(process, first, (child,))
            stop.assert_called_once_with(process); process.wait.assert_called_once_with(timeout=1.)

    def test_consumed_ready_pin_cannot_be_replaced_by_new_favorable_bytes(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); ready = root/'READY.json'
            probe.write(ready, {'state': 'original'})
            _, consumed = probe.consume(ready)
            ready.write_text('{"state":"changed"}\n')
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                probe._seal(root, {'READY.json': consumed}, {'synthetic_only': True})
            self.assertFalse((root/'COMPLETE.json').exists())

    def test_late_inner_complete_side_effect_preserves_rejected_marker_not_success(self):
        for mode in ('drift', 'fsync'):
            with self.subTest(mode=mode), TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(); pin = probe.write(root/'REAPED.json', {'reaped': True})
                actual = probe.write
                def write(path, value, **kwargs):
                    result = actual(path, value, **kwargs)
                    if path.name == 'COMPLETE.json':
                        if mode == 'fsync': raise OSError('synthetic post-publish fsync failure')
                        (root/'REAPED.json').write_text('{"reaped":false}\n')
                    return result
                with patch.object(probe, 'write', side_effect=write), self.assertRaises((ValueError, OSError)):
                    probe._seal(root, {'REAPED.json': pin}, {'synthetic_only': True})
                self.assertFalse((root/'COMPLETE.json').exists())
                self.assertTrue((root/'REJECTED_COMPLETE.json').exists()); self.assertTrue((root/'FAILED.json').exists())

    def test_existing_unowned_artifact_is_not_adopted_and_p3_timeout_is_local(self):
        before = copy.deepcopy(probe.configuration())
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); pin = probe.write(root/'report.json', {'ready': True})
            probe.write(root/'foreign.json', {'other': True})
            with self.assertRaisesRegex(ValueError, 'inventory'):
                probe._seal(root, {'report.json': pin}, {'synthetic_only': True})
            self.assertTrue((root/'foreign.json').exists()); self.assertFalse((root/'COMPLETE.json').exists())
        self.assertEqual(probe.configuration(), before)
        self.assertEqual(probe.TIMEOUTS, {'P1': 3600., 'P2': 30., 'P3': .5, 'P4': 30.})
        self.assertEqual(probe.MEMORY_BYTES, 34359738368)

    def test_final_artifact_consumer_cannot_hide_late_source_runtime_drift(self):
        with TemporaryDirectory() as temporary:
            project = Path(temporary).resolve(); output = project/probe.OUTPUT
            context = dict(project=str(project), synthetic='mocked metadata authority')
            state = {'intact': True, 'injected': False}
            def recheck(_):
                if not state['intact']: raise ValueError('synthetic late source/runtime drift')
            def fixture(_context, name, root):
                directory = root/name; directory.mkdir()
                pin = probe.write(directory/'report.json', {'fixture': name, 'mocked': True})
                complete = probe._seal(directory, {'report.json': pin}, {'synthetic_only': True})
                (root/(name+'.log')).write_bytes(b'synthetic log\n')
                return dict(report={'fixture': name}, complete_sha256=complete,
                    log_sha256=probe.sha(root/(name+'.log')), files_sha256={'report.json': pin})
            original = probe.sha
            def hashed(path):
                value = original(path)
                if (output/'COMPLETE.json').exists() and path == output/'P4/report.json' and not state['injected']:
                    state.update(intact=False, injected=True)
                return value
            with patch.object(probe, 'preflight', return_value=context), \
                    patch.object(probe, 'recheck', side_effect=recheck), \
                    patch.object(probe, 'run_fixture', side_effect=fixture), \
                    patch.object(probe, 'sha', side_effect=hashed), patch.dict(probe.os.environ):
                with self.assertRaisesRegex(ValueError, 'late source/runtime drift'): probe.run_probe(project)
            self.assertTrue(state['injected'])
            self.assertFalse((output/'COMPLETE.json').exists())
            self.assertTrue((output/'REJECTED_COMPLETE.json').exists()); self.assertTrue((output/'FAILED.json').exists())


if __name__ == '__main__': unittest.main()
