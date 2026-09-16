import json
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import zpd_history_v2_development as runner


class Matrix:
    def __init__(self, value):
        self.value = np.asarray(value)
        self.shape = self.value.shape
        self.data = self.value.ravel()

    def __getitem__(self, index):
        return Matrix(self.value[index])


class Encoder:
    fits = []

    def __init__(self, n_features):
        pass

    def fit(self, rows, weights):
        if any(r['split'] != 'train' for r in rows):
            raise AssertionError('scaler fit on heldout')
        self.fits.append([r['example_id'] for r in rows])
        return self

    def transform(self, rows, arm):
        return Matrix(np.ones((len(rows), 2)))

    def state_dict(self):
        return {'train_only': True}


class Model:
    fits = 0
    instances = 0

    def __init__(self, **kwargs):
        Model.instances += 1
        self.coef_ = np.zeros((6, 2))
        self.intercept_ = np.zeros(6)
        self.classes_ = np.arange(6)

    def partial_fit(self, x, y, classes, sample_weight):
        Model.fits += 1
        return self

    def predict_proba(self, x):
        return np.full((x.shape[0], 6), 1/6)


def fixture():
    rows = []
    for i in range(5):
        history = [{'code': 'x=1', 'timestamp': 1, 'verdict': 'WA'}]
        rows.append(dict(example_id=str(i), user_id=str(i), problem_id='p',
                         split='train' if i < 3 else 'valid', timestamp=2,
                         current_code='x=2', current_verdict='WA', history=history,
                         donor_history=history, next_label='AC'))
    return rows


class DevelopmentTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('scipy') and importlib.util.find_spec('sklearn'), 'requires frozen remote numerical runtime')
    def test_real_encoder_optimizer_integration(self):
        with tempfile.TemporaryDirectory() as directory:
            result = runner.fit_development(fixture(), Path(directory), n_features=8)
            self.assertEqual(result['fit_count'], 108)
            self.assertFalse(result['test_opened'])
            self.assertEqual(result['completed_train_example_exposures'], 6480)
            self.assertEqual(set(result['arms']), set(runner.ARMS))
            self.assertTrue(all(np.isfinite(arm['ensemble']['user_equal_nll']) for arm in result['arms'].values()))

    def test_physical_input_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in runner.ALLOWED_INPUTS:
                (root / name).write_text('{}')
            runner.require_development_bundle(root)
            (root / 'labels-test.jsonl').write_text('')
            with self.assertRaises(ValueError):
                runner.require_development_bundle(root)

    def test_alpha_and_h_cell_selection(self):
        self.assertEqual(runner.select_alpha([{'alpha': a, 'mean_seed_valid_nll': 1.} for a in runner.ALPHAS])['alpha'], .001)
        arms = {arm: {'mean_seed_valid_nll': 1., 'ensemble': {'user_equal_nll': 1.}} for arm in runner.ARMS}
        arms['H_PR']['mean_seed_valid_nll'] = .8
        arms['H_IZ']['ensemble']['user_equal_nll'] = .1  # Ensemble alone must not select IZ.
        arms['H_PR']['ensemble']['user_equal_nll'] = .9
        result = runner.development_decision(arms)
        self.assertEqual(result['selected_h_cell'], 'H_PR')
        self.assertEqual(result['next_action'], 'new_holdout_eligibility_audit_only')
        arms['U_PR']['ensemble']['user_equal_nll'] = .8
        self.assertEqual(runner.development_decision(arms)['next_action'], 'stop_this_family')
        arms['H_PR']['mean_seed_valid_nll'] = 1.
        self.assertEqual(runner.development_decision(arms)['selected_h_cell'], 'H_PR')

    def test_fixed_budget_and_train_only_scaler(self):
        Model.fits, Model.instances, Encoder.fits = 0, 0, []
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            events = []
            result = runner.fit_development(fixture(), output, events.append, encoder_class=Encoder, model_class=Model, n_features=8)
            self.assertEqual(result['fit_count'], 108)
            self.assertEqual(Model.instances, 108 + 12)
            self.assertEqual(Model.fits, 108 * 20 + 12)
            self.assertEqual(result['completed_train_example_exposures'], 3 * 2160)
            self.assertEqual(len(Encoder.fits), 2)  # disposable smoke, then one common real scaler
            self.assertEqual(Encoder.fits[1], ['0', '1', '2'])
            self.assertEqual(len(list(output.glob('*-model.npz'))), 108)
            self.assertEqual(len(list(output.glob('*-COMPLETE.json'))), 12)
            self.assertEqual(set(result['arms']), set(runner.ARMS))
            self.assertEqual(result['arms']['C_R']['selected_alpha'], .001)
            self.assertFalse(result['test_opened'])
            self.assertEqual(events[-1]['completed_train_example_exposures'], 6480)
            self.assertNotIn('nll', json.loads((output / 'smoke.json').read_text()))

    def test_test_rows_rejected(self):
        data = fixture()
        data[-1]['split'] = 'test'
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, 'rejects all test'):
            runner.fit_development(data, Path(directory), encoder_class=Encoder, model_class=Model)

    def test_pr_anchor_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = {'selected_alpha': .001, 'candidates': [{'alpha': .001, 'seed_nll': [1., 1., 1.]}],
                      'validation_file': 'new.npz'}
            (root / 'H_M-selection.json').write_text(json.dumps(report))
            p = np.full((3, 2, 6), 1/6)
            for name in ('new.npz', 'H_M-validation.npz'):
                np.savez(root / name, example_ids=['a', 'b'], labels=[0, 1], seed_probabilities=p)
            self.assertEqual(runner.check_pr_anchor('H_PR', report, root, root)['status'], 'reproduced')
            report['candidates'][0]['seed_nll'][0] = 1.01
            with self.assertRaisesRegex(ValueError, 'NLL drift'):
                runner.check_pr_anchor('H_PR', report, root, root)


if __name__ == '__main__':
    unittest.main()
