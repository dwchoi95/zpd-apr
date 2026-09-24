"""Independent own-worker boundaries; synthetic temporary files only."""
import copy
from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_repair_progress_cv as worker
from tests.test_zpd_repair_progress_cv import fixture
from tests.test_zpd_repair_feedback_cv import materialized


class IndependentProgressWorkerReview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, cls.labels = fixture()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.prepared = self.root/'prepared'; self.output = self.root/'fold-0'
        self.contracts = materialized(self.inputs[0], self.labels, self.prepared)

    def run_worker(self, inputs=None):
        with redirect_stdout(io.StringIO()):
            return worker.fit_fold(inputs or self.inputs[0], self.prepared,
                self.contracts[0], self.output, recheck=lambda: None)

    def test_own_label_changed_by_last_output_consumer_is_rejected(self):
        original = worker.sha; changed = []
        def digest(path):
            result = original(path)
            if path == self.output/'STATUS.json' and not changed:
                changed.append(True)
                with (self.prepared/'fold-0/train-labels.json').open('ab') as stream:
                    stream.write(b' ')
            return result
        with patch.object(worker, 'sha', digest), self.assertRaisesRegex(ValueError, 'own training-label'):
            self.run_worker()
        self.assertEqual(changed, [True])
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists())

    def test_runtime_changed_by_last_output_consumer_is_rejected(self):
        original = worker.sha; runtime = worker._runtime(); changed = []
        def digest(path):
            result = original(path)
            if path == self.output/'STATUS.json': changed.append(True)
            return result
        def version():
            return dict(runtime, python='injected-runtime-drift') if changed else dict(runtime)
        with patch.object(worker, 'sha', digest), patch.object(worker, '_runtime', version), \
                self.assertRaisesRegex(ValueError, 'inputs/runtime changed'):
            self.run_worker()
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'FAILED.json').exists())

    def test_actual_complete_fsync_exception_quarantines_exact_marker(self):
        original = os.fsync; rejected = []
        def fsync(fd):
            marker = self.output/'COMPLETE.json'
            if marker.exists() and os.fstat(fd).st_ino == marker.stat().st_ino:
                rejected.append(marker.read_bytes())
                raise OSError('injected COMPLETE descriptor fsync')
            return original(fd)
        with patch.object(worker.os, 'fsync', fsync), self.assertRaisesRegex(OSError, 'descriptor fsync'):
            self.run_worker()
        self.assertEqual(len(rejected), 1)
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertEqual((self.output/'REJECTED_COMPLETE.json').read_bytes(), rejected[0])
        failed = json.loads((self.output/'FAILED.json').read_bytes())
        self.assertEqual(failed['completed_fits'], 6)
        self.assertFalse(failed['retry_authorized'])

    def test_identical_inputs_preserve_shared_h_and_read_only_own_scope(self):
        source = copy.deepcopy(self.inputs[0])
        interactions = {arm: {bid: worker.solver.CandidateBlock(block.candidate_ids, block.matrix.copy())
                             for bid, block in source.interactions['CF'].items()}
                        for arm in worker.ARMS}
        source = replace(source, interactions=interactions)
        original = Path.open; reads = []
        def opened(path, mode='r', *args, **kwargs):
            if 'r' in mode:
                reads.append(path)
                self.assertTrue(path == self.prepared/'fold-0/train-labels.json' or path.parent == self.output)
            return original(path, mode, *args, **kwargs)
        with patch.object(Path, 'open', opened):
            predictions = self.run_worker(source)
        self.assertTrue(reads)
        for row in predictions:
            for arm in ('HS', 'Jm', 'CF'):
                name = 'shared_H_'+arm
                self.assertEqual(row['candidate_scores']['H'], row['candidate_scores'][name])
                self.assertEqual(row['choices']['H'], row['choices'][name])
                self.assertTrue(row['shared_theta_diagnostics'][arm]['features_identical_exact'])
            noop = row['choices']['noop']; bid = row['bank_id']
            for method in (*worker.ARMS, 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF'):
                self.assertEqual(row['candidate_scores'][method][noop], source.base_scores[bid][noop])
        cf = json.loads((self.output/'CF.json').read_bytes())['offset_model']
        np.testing.assert_array_equal(cf['coefficients'][16:], np.zeros(16))
        np.testing.assert_array_equal(cf['final_gradient'][16:], np.zeros(16))


if __name__ == '__main__': unittest.main()
