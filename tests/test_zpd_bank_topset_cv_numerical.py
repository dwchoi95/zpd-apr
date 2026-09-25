"""One genuine seven-arm synthetic fit, isolated from empirical data."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import time
import unittest

from scripts import run_zpd_bank_topset_cv as worker
from scripts.audit_zpd_bank_topset_run import direct_value_gradient
from tests.test_zpd_joint_progress_cv import fixture
from tests.test_zpd_repair_feedback_cv import materialized


class RealTopsetWorkerTests(unittest.TestCase):
    def test_real_seven_arm_pipeline_and_independent_final_gradient(self):
        inputs, labels = fixture(); own = inputs[0]
        train, held = worker.capsule.scope(own); ids = {e.bank_id for e in train}
        own_labels = {k:v for k,v in labels.items() if k[0] in ids}
        transform = worker.features.fit_own_scaler(train,{bid:own.banks[bid] for bid in ids},
            {bid:own.raw_current[bid] for bid in ids},own_labels)
        plan = worker.planner.build_plan(own,transform,own_labels)
        started = time.monotonic()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); prepared = root/'prepared'; output = root/'fold-0'
            contracts = materialized(own,labels,prepared)
            with redirect_stdout(io.StringIO()):
                rows = worker.fit_fold(own,prepared,contracts[0],transform,output,recheck=lambda:None)
            self.assertEqual(len(rows),len(held));self.assertTrue((output/'COMPLETE.json').exists())
            for arm in worker.ARMS:
                model = json.loads((output/(arm+'.json')).read_bytes())
                theta = worker.validate_model(model,own,arm,transform,plan.payload())
                banks,weights = plan.banks(arm)
                _,g,_,_ = direct_value_gradient(theta,banks,weights)
                self.assertLessEqual(float(abs(g).max()),1e-8)
        print('TOPSET_REAL_SYNTHETIC_7_ARMS '+json.dumps(dict(seconds=time.monotonic()-started,
            models=7,held_examples=len(held),empirical=False)),flush=True)


if __name__ == '__main__': unittest.main()
