"""Synthetic own-envelope integration; solver doubled, never a numerical result."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_bank_topset_cv as worker
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from tests.test_zpd_joint_progress_cv import fixture
from tests.test_zpd_repair_feedback_cv import materialized


class BankTopsetWorkerTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.labels = fixture()
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve(); self.prepared = self.root/'prepared'
        self.output = self.root/'fold-0'
        self.contracts = materialized(self.inputs[0], self.labels, self.prepared)
        train = capsule.scope(self.inputs[0])[0]; ids = {ex.bank_id for ex in train}
        self.transform = features.fit_own_scaler(train,
            {bid:self.inputs[0].banks[bid] for bid in ids},
            {bid:self.inputs[0].raw_current[bid] for bid in ids},
            {key:value for key,value in self.labels.items() if key[0] in ids})
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        def fake_fit(banks, weights):
            return dict(test_control_flow_only=True, coefficients=[0.]*4131,
                final_gradient=[0.]*4131, input_sha256=worker.solver.input_hash(banks,weights))
        def fake_validate(model):
            self.assertIs(model['test_control_flow_only'], True)
            return np.asarray(model['coefficients'], dtype=np.float64)
        self.fit = self.stack.enter_context(patch.object(worker.solver,'fit',side_effect=fake_fit))
        self.stack.enter_context(patch.object(worker.solver,'validate_model',side_effect=fake_validate))

    def run_worker(self, check=lambda:None):
        with redirect_stdout(io.StringIO()):
            return worker.fit_fold(self.inputs[0], self.prepared, self.contracts[0],
                self.transform, self.output, recheck=check)

    def test_own_label_only_original_scaler_seven_fits_and_all_methods(self):
        opened = []; original_open = Path.open
        def spy(path, mode='r', *args, **kwargs):
            if 'r' in mode:
                opened.append(path)
                self.assertTrue(path == self.prepared/'fold-0/train-labels.json' or path.parent == self.output)
            return original_open(path,mode,*args,**kwargs)
        with patch.object(Path,'open',spy), patch.object(features,'fit_own_scaler',side_effect=AssertionError('no refit')):
            rows = self.run_worker()
        self.assertEqual(self.fit.call_count,7); self.assertTrue(opened)
        self.assertEqual(len(rows),len(capsule.scope(self.inputs[0])[1]))
        self.assertTrue(all(set(row['choices']) == set(worker.METHODS) for row in rows))
        marker = json.loads((self.output/'COMPLETE.json').read_bytes())
        self.assertEqual(marker['completed_fits'],7); self.assertEqual(marker['automatic_retries'],0)
        self.assertEqual(set(marker['files_sha256']),set(worker.FILES))
        for name,pin in marker['files_sha256'].items(): self.assertEqual(worker.sha(self.output/name),pin)
        saved = json.loads((self.output/'SCALER.json').read_bytes())
        self.assertEqual(saved,worker.previous.transform_payload(self.transform))
        for row in rows:
            for arm in ('HS','Jm','CF'):
                self.assertEqual(row['choices']['H'],row['choices']['shared_H_'+arm])

    def test_fail_closed_no_retry_no_complete(self):
        self.fit.side_effect = RuntimeError('synthetic optimizer failure')
        with self.assertRaisesRegex(RuntimeError,'synthetic optimizer'): self.run_worker()
        self.assertEqual(self.fit.call_count,1)
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertFalse(json.loads((self.output/'FAILED.json').read_bytes())['retry_authorized'])
        with self.assertRaisesRegex(ValueError,'no retry'): self.run_worker()
        self.assertEqual(self.fit.call_count,1)

    def test_mutated_own_labels_block_before_fitting(self):
        altered = patch.object(worker,'sha',return_value='0'*64)
        with altered, self.assertRaisesRegex(ValueError,'own label envelope changed'): self.run_worker()
        self.assertFalse(self.output.exists()); self.assertEqual(self.fit.call_count,0)

    def test_mutated_model_is_rejected(self):
        self.run_worker()
        model = json.loads((self.output/'H.json').read_bytes())
        plan = json.loads((self.output/'PLAN.json').read_bytes())
        model['arm'] = 'C_joint'
        with self.assertRaisesRegex(ValueError,'model identity'):
            worker.validate_model(model,self.inputs[0],'H',self.transform,plan)


if __name__ == '__main__': unittest.main()
