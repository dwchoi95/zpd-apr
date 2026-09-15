import json
from pathlib import Path
import tempfile
import unittest

from scripts.probe_zpd_runtime import expand_full_cases, prepare
from tests import test_zpd_runtime_probe as fixtures


class RuntimeExpansionTests(unittest.TestCase):
    def test_preserves_targets_and_adds_every_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'input'
            fixtures.RuntimeProbeTests().inputs(root)
            sample, expanded = Path(directory) / 'sample.json', Path(directory) / 'expanded.json'
            prepare(root, sample)
            before = sample.read_bytes()
            expand_full_cases(root, sample, expanded)
            a, b = json.loads(before), json.loads(expanded.read_text())
            self.assertEqual(sample.read_bytes(), before)
            self.assertEqual(len(b['records']), 16)
            for old, new in zip(a['records'], b['records'], strict=True):
                for key in ('problem_id', 'submission_id', 'code', 'split', 'cached_verdict'):
                    self.assertEqual(old[key], new[key])
                self.assertEqual(len(new['testcases']), 4)

    def test_rejects_changed_test_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'input'
            fixtures.RuntimeProbeTests().inputs(root)
            sample = Path(directory) / 'sample.json'
            prepare(root, sample)
            first = json.loads(sample.read_text())['records'][0]
            path = root / 'testcases' / first['problem_id'] / 'testcases.jsonl'
            path.write_bytes(path.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'testcases changed'):
                expand_full_cases(root, sample, Path(directory) / 'expanded.json')
