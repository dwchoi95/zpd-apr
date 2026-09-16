import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from scripts.zpd_history_test import consume_lock, dimensions, reconstruct_models, load_test_labels, run
from scripts.zpd_history_predictor import SEEDS, ARMS


_CANONICAL_LOCK = Path('/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json')
_REAL_PATH_EXISTS = Path.exists


def _fixture_path_exists(path, *args, **kwargs):
    # Full-run fixtures also mock consume_lock; never inspect or modify the real
    # experiment lock. All unrelated filesystem checks keep their real behavior.
    if path == _CANONICAL_LOCK:
        return False
    return _REAL_PATH_EXISTS(path, *args, **kwargs)


class HeldoutBoundaryTests(unittest.TestCase):
    def test_lock_exclusive_persistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'TEST_CONSUMED.json'
            consume_lock(path, {'input_manifest_sha256': 'fixed'})
            with self.assertRaises(FileExistsError):
                consume_lock(path, {'input_manifest_sha256': 'other'})
            record = json.loads(path.read_text())
            self.assertEqual(record['input_manifest_sha256'], 'fixed')
            self.assertEqual(record['state'], 'consumed')
            self.assertFalse(record['automatic_retry'])

    def test_failed_label_read_does_not_release_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root / 'TEST_CONSUMED.json'
            consume_lock(lock, {})
            with self.assertRaises(FileNotFoundError):
                load_test_labels(root, ['x'])
            self.assertTrue(lock.exists())

    def test_dimensions(self):
        self.assertEqual(dimensions('C_F', 8), 26)
        self.assertEqual(dimensions('S_F', 8), 35)
        self.assertEqual(dimensions('H_M', 8), 90)

    def test_label_coverage_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'labels-test.jsonl').write_text(json.dumps({'example_id':'x','next_label':'AC'})+'\n')
            with patch('scripts.zpd_history_test.verified_files'):
                self.assertEqual(load_test_labels(root, ['x']), {'x': 0})
                with self.assertRaises(ValueError):
                    load_test_labels(root, ['different'])

    def test_run_preflight_failure_never_opens_or_consumes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict('sys.modules', {
                'scipy': SimpleNamespace(__version__='1.18.1'),
                'sklearn': SimpleNamespace(__version__='1.9.0')}), \
                patch('numpy.__version__', '2.5.2'), \
                patch.object(Path, 'exists', _fixture_path_exists), \
                patch('scripts.zpd_history_test.verify_selection', side_effect=ValueError('bad seal')), \
                patch('scripts.zpd_history_test.consume_lock') as lock, \
                patch('scripts.zpd_history_test.load_test_labels') as labels:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'bad seal'):
                run(root/'input', root/'selection', root/'protocol',
                    Path('/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json'),
                    root/'output', root/'power', root/'test-protocol')
            lock.assert_not_called()
            labels.assert_not_called()

    def test_run_all_models_checked_then_lock_then_labels(self):
        from contextlib import ExitStack
        from unittest.mock import MagicMock
        calls = []
        valid = {'example_id': 'v', 'split':'valid', 'donor_history':[{}]}
        train = {'example_id': 't', 'split':'train', 'donor_history':[{}]}
        test = {'example_id': 'x', 'split':'test', 'donor_history':[{}]}
        sealed = {'arms': {arm:{'train_example_ids':['t'],'valid_example_ids':['v']} for arm in ARMS}}
        ps = np.full((3, 1, 6), 1/6)
        archive = MagicMock()
        archive.__enter__.return_value = {'example_ids':np.array(['v']), 'seed_probabilities':ps}
        def reconstruct(*args):
            calls.append('model')
            return []
        def consumed(*args):
            calls.append('lock')
        def opened(*args):
            calls.append('labels')
            raise RuntimeError('stop fixture after opening')
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            stack.enter_context(patch.dict('sys.modules', {'scipy':SimpleNamespace(__version__='1.18.1'),
                                                         'sklearn':SimpleNamespace(__version__='1.9.0')}))
            stack.enter_context(patch('numpy.__version__', '2.5.2'))
            stack.enter_context(patch.object(Path, 'exists', _fixture_path_exists))
            mocks = {'verify_selection': lambda *a:(sealed,{}), 'digest_file':lambda *a:'hash',
                     'verified_files':lambda *a:{}, 'load_observed':lambda *a:([train,valid,test],{}),
                     'reconstruct_models':reconstruct, 'features':lambda *a:None,
                     'predict':lambda *a:ps, 'consume_lock':consumed, 'load_test_labels':opened}
            for name, value in mocks.items():
                stack.enter_context(patch('scripts.zpd_history_test.'+name, value))
            stack.enter_context(patch('scripts.zpd_history_test.np.load', return_value=archive))
            root = Path(tmp)
            with self.assertRaisesRegex(RuntimeError, 'stop fixture'):
                run(root/'input', root/'selection', root/'protocol',
                    Path('/home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json'),
                    root/'output', root/'power', root/'test-protocol')
        self.assertEqual(calls, ['model']*5 + ['lock', 'labels'])

    @unittest.skipUnless(importlib.util.find_spec('sklearn'), 'requires frozen remote sklearn')
    def test_model_reconstruction_matches_sgd(self):
        from sklearn.linear_model import SGDClassifier
        x = np.random.default_rng(9).normal(size=(24, 7))
        y = np.arange(24) % 6
        arrays, original = {}, []
        for seed in SEEDS:
            model = SGDClassifier(loss='log_loss', random_state=seed)
            model.partial_fit(x, y, classes=np.arange(6))
            original.append(model.predict_proba(x))
            arrays.update({f'coef_{seed}': model.coef_, f'intercept_{seed}':model.intercept_,
                           f'classes_{seed}':model.classes_})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'models.npz'
            np.savez(path, **arrays)
            recovered = reconstruct_models(path, 7)
            np.testing.assert_array_equal(np.stack(original), np.stack([m.predict_proba(x) for m in recovered]))
            with self.assertRaises(ValueError):
                reconstruct_models(path, 8)


if __name__ == '__main__':
    unittest.main()
