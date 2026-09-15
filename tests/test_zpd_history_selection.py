import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_zpd_history_support import digest_file
from scripts.zpd_history_selection import load_selection, fit_selection


class SelectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.items = []
        for i, split in enumerate(('train', 'valid', 'test')):
            self.items.append({'example_id': split, 'split': split, 'user_id': split,
                'problem_id': 'p1', 'timestamp': i + 3, 'current_code_id': 'c',
                'current_verdict': 'WA', 'matching_current_verdict': 'Wrong Answer',
                'history': [{'code_id': 'h', 'timestamp': i + 1, 'verdict': 'WA'}],
                'donor_example_id': None if split == 'train' else 'train'})
        self.items[-1]['current_code_id'] = 'test-not-loaded'
        self.contents = {'features.jsonl': self.items,
            'codes.jsonl': [{'code_id': 'c', 'code': 'x=2'}, {'code_id': 'h', 'code': 'x=1'}],
            'labels-train.jsonl': [{'example_id': 'train', 'next_label': 'AC'}],
            'labels-valid.jsonl': [{'example_id': 'valid', 'next_label': 'WA'}]}
        self.write()

    def write(self):
        for name, records in self.contents.items():
            (self.root / name).write_text(''.join(json.dumps(r) + '\n' for r in records))
        manifest = {'counts': {'train': 1, 'valid': 1, 'test': 1},
                    'file_sha256': {n: digest_file(self.root / n) for n in self.contents}}
        (self.root / 'manifest.json').write_text(json.dumps(manifest))

    def test_no_test_file_or_source_resolution(self):
        result, _ = load_selection(self.root)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[1]['donor_history'], result[0]['history'])
        self.assertFalse((self.root / 'labels-test.jsonl').exists())

    def test_changed_donor_rejected(self):
        self.items[1]['donor_example_id'] = None
        self.write()
        with self.assertRaisesRegex(ValueError, 'donor mapping'):
            load_selection(self.root)

    def test_changed_input_rejected(self):
        (self.root / 'labels-valid.jsonl').write_text('')
        with self.assertRaisesRegex(ValueError, 'input hash'):
            load_selection(self.root)

    def test_selection_rejects_test_rows(self):
        with self.assertRaisesRegex(ValueError, 'rejects test'):
            fit_selection([{'split': 'test'}], self.root)

    @unittest.skipUnless(importlib.util.find_spec('sklearn'), 'sklearn unavailable')
    def test_actual_fit_exports_five_arms(self):
        import numpy as np
        data, _ = load_selection(self.root)
        # Two training users are needed for a nonempty matched training arm.
        extra = dict(data[1], example_id='train2', user_id='train2', split='train')
        data.insert(1, extra)
        result = fit_selection(data, self.root, n_features=16)
        self.assertEqual(set(result), {'C_F', 'H_F', 'S_F', 'H_M', 'U_M'})
        with np.load(self.root / 'H_M-validation.npz', allow_pickle=False) as saved:
            self.assertEqual(saved['seed_probabilities'].shape, (3, 1, 6))
            np.testing.assert_allclose(saved['probabilities'].sum(axis=1), 1)
        self.assertFalse((self.root / 'labels-test.jsonl').exists())
