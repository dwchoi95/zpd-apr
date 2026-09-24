"""Nonauthor own-job boundary regressions; mocked OS, no empirical fit/data.

Full320 capsules are synthetic. The fake worker intentionally tests transport
and sealing, not numerical/model validity, Linux limits or a production release.
"""
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import run_zpd_joint_progress_job as job
from tests.test_zpd_joint_progress_job import environment, fake_worker
from tests.test_zpd_joint_progress_capsule import fixture


class JointJobReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = replace(fixture(320, synthetic=False), readiness_complete_sha256=job.READINESS_COMPLETE_SHA256)

    def test_final_predictions_consumer_cannot_mutate_previously_hashed_scaler(self):
        with environment(self.inputs) as env:
            actual_read = Path.read_bytes; reads = []
            def read(path):
                raw = actual_read(path)
                if path == env['output']/'predictions.json':
                    reads.append(1)
                    if len(reads) == 3:
                        (env['output']/'SCALER.json').write_bytes(b'changed after final pre-consumer hash')
                return raw
            with patch.object(job.worker, 'fit_fold', side_effect=fake_worker) as called, \
                 patch.object(Path, 'read_bytes', read), self.assertRaises(ValueError):
                job.execute(env['project'], env['fold'], env['pin'])
            self.assertEqual(called.call_count, 1); self.assertEqual(len(reads), 3)
            self.assertFalse((env['output']/'COMPLETE.json').exists())
            self.assertTrue((env['output']/'REJECTED_COMPLETE.json').exists())
            self.assertTrue((env['output']/'FAILED.json').exists())

    def test_own_job_decode_side_effect_cannot_replace_consumed_externally_pinned_body(self):
        with environment(self.inputs) as env:
            actual_decode = job.launcher.core.decode_json; changed = []
            def decode(raw):
                value = actual_decode(raw)
                if type(value) is dict and value.get('kind') == job.JOB_KIND and not changed:
                    changed.append(True)
                    env['path'].write_bytes(b'{"replacement":"after authenticated raw consume"}\n')
                return value
            with patch.object(job.launcher.core, 'decode_json', decode), \
                 patch.object(job.worker, 'fit_fold') as worker, \
                 self.assertRaisesRegex(ValueError, 'consumed own job changed'):
                job.execute(env['project'], env['fold'], env['pin'])
            self.assertEqual(changed, [True]); worker.assert_not_called()
            self.assertFalse(env['output'].exists())

    def test_mutable_authority_context_rejected_before_source_runtime_consumers(self):
        with environment(self.inputs) as env:
            context = job.preflight(env['project'], env['fold'], env['pin'])
            context.authority['initialization_sha256'] = 'f'*64
            with patch.object(job, 'source_state', side_effect=AssertionError('metadata rejection must precede Git')) as state, \
                 patch.object(job, 'runtime', side_effect=AssertionError('metadata rejection must precede runtime')) as runtime, \
                 self.assertRaisesRegex(ValueError, 'authorization metadata changed'):
                job.recheck(context)
            state.assert_not_called(); runtime.assert_not_called()
            self.assertFalse(env['output'].exists())


if __name__ == '__main__': unittest.main()
