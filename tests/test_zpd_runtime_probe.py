"""Synthetic prepare and mocked execution checks; no submitted code is run."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.probe_zpd_runtime import execute, order_key, prepare
from src.runner.models import CaseOutcome, Verdict


def mock_submission(**kwargs):
    return SimpleNamespace(cases=[CaseOutcome(c.case_id, Verdict.AC, runtime_sec=.01)
                                  for c in kwargs['testcases']])


class RuntimeProbeTests(unittest.TestCase):
    def inputs(self, root, per_stratum=5, cases=4):
        cache, data = [], {'train': [], 'valid': []}
        for split_number, split in enumerate(('train', 'valid')):
            for verdict_number, verdict in enumerate(('AC', 'TLE')):
                for i in range(per_stratum):
                    problem = f'p{split_number * 100 + verdict_number * 10 + i:05}'
                    submission = 's1'
                    testcase_rows = [{'case_id': f'c{k}', 'input': '', 'expected_output': '1'} for k in range(cases)]
                    path = root / 'testcases' / problem / 'testcases.jsonl'
                    path.parent.mkdir(parents=True)
                    path.write_text(''.join(json.dumps(c) + '\n' for c in testcase_rows))
                    cache.append({'problem_id': problem, 'submission_id': submission,
                                  'execution_verdict': verdict,
                                  'tc_outcomes': {c['case_id']: verdict for c in testcase_rows}})
                    data[split].append({'problem_id': problem, 'target_submission_id': submission,
                                        'target_verdict': 'Accepted', 'target_code': 'print(1)'})
        (root / 'all-original-submissions.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in cache))
        directory = root / 'canonical-datasets'
        directory.mkdir()
        for split, rows in data.items():
            (directory / f'{split}-answer.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))

    def test_prepare_is_hash_deterministic_and_selects_fixed_strata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'input'
            self.inputs(root)
            first, second = Path(directory) / 'one.json', Path(directory) / 'two.json'
            prepare(root, first)
            # Permutation must not change selected records, though file hashes change.
            for path in [root / 'all-original-submissions.jsonl', *sorted((root / 'canonical-datasets').glob('*.jsonl'))]:
                path.write_text('\n'.join(reversed(path.read_text().splitlines())) + '\n')
            prepare(root, second)
            a, b = json.loads(first.read_text()), json.loads(second.read_text())
            self.assertEqual(a['records'], b['records'])
            self.assertEqual(len(a['records']), 16)
            self.assertEqual(len({(r['problem_id'], r['submission_id']) for r in a['records']}), 16)
            for stratum in a['strata'].values():
                self.assertEqual(stratum, {'available': 5, 'selected': 4})
            for row in a['records']:
                self.assertEqual(len(row['testcases']), 3)
                expected = sorted((f'c{k}' for k in range(4)), key=lambda case: order_key('|'.join((row['problem_id'], row['submission_id'], case))))[:3]
                self.assertEqual([c['case_id'] for c in row['testcases']], expected)

    def test_prepare_shortfalls_are_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'input'
            self.inputs(root, per_stratum=2, cases=2)
            output = Path(directory) / 'sample.json'
            prepare(root, output)
            sample = json.loads(output.read_text())
            self.assertEqual(len(sample['records']), 8)
            self.assertTrue(all(c == {'available': 2, 'selected': 2} for c in sample['strata'].values()))
            self.assertTrue(all(len(row['testcases']) == 2 for row in sample['records']))

    def test_prepare_cannot_replace_frozen_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'sample.json'
            output.write_text('frozen')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                prepare(Path(directory), output)
            self.assertEqual(output.read_text(), 'frozen')

    def test_duplicate_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'input'
            self.inputs(root)
            cache = root / 'all-original-submissions.jsonl'
            cache.write_text(cache.read_text() + cache.read_text().splitlines()[0] + '\n')
            with self.assertRaisesRegex(ValueError, 'duplicate cache'):
                prepare(root, Path(directory) / 'sample.json')

    def test_empty_or_duplicate_sample_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sample = Path(directory) / 'input', Path(directory) / 'sample.json'
            self.inputs(root)
            prepare(root, sample)
            original = json.loads(sample.read_text())
            for label in ('empty', 'duplicate_record', 'duplicate_case'):
                changed = json.loads(json.dumps(original))
                if label == 'empty':
                    changed['records'] = []
                elif label == 'duplicate_record':
                    changed['records'].append(changed['records'][0])
                else:
                    changed['records'][0]['testcases'].append(changed['records'][0]['testcases'][0])
                sample.write_text(json.dumps(changed))
                with self.subTest(label=label), patch('scripts.probe_zpd_runtime.PythonSubmissionRunner') as runner:
                    with self.assertRaises(ValueError):
                        execute(sample, Path(directory) / label)
                    runner.assert_not_called()

    def test_mock_execute_preserves_all_blocks_and_raw_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sample, output = Path(directory) / 'input', Path(directory) / 'sample.json', Path(directory) / 'probe'
            self.inputs(root)
            prepare(root, sample)
            frozen = sample.read_bytes()
            with patch('scripts.probe_zpd_runtime.PythonSubmissionRunner') as runner:
                runner.return_value.run_submission.side_effect = mock_submission
                execute(sample, output)
                runner.assert_called_once_with(timeout_sec=2.5, memory_limit_mb=2048, case_workers=1)
                self.assertEqual(runner.return_value.run_submission.call_count, 64)
            rows = [json.loads(line) for line in (output / 'records.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 64)
            self.assertEqual({(r['block'], r['workers']) for r in rows}, {(0, 1), (1, 8), (2, 8), (3, 1)})
            summary = json.loads((output / 'summary.json').read_text())
            self.assertTrue(summary['complete'])
            self.assertTrue((output / 'COMPLETE').is_file())
            self.assertIsNone(summary['learning_effect'])
            self.assertTrue(all(c['cases'] == 48 and c['disagreements'] == 0 for c in summary['paired_block_comparisons'].values()))
            self.assertEqual(sample.read_bytes(), frozen)

    def test_budget_stops_subsequent_blocks_without_imputation(self):
        with tempfile.TemporaryDirectory() as directory:
            root, sample, output = Path(directory) / 'input', Path(directory) / 'sample.json', Path(directory) / 'probe'
            self.inputs(root)
            prepare(root, sample)
            with patch('scripts.probe_zpd_runtime.PythonSubmissionRunner') as runner, patch('scripts.probe_zpd_runtime.time.monotonic', side_effect=[0, 0, 1, 601, 602]):
                runner.return_value.run_submission.side_effect = mock_submission
                execute(sample, output)
            summary = json.loads((output / 'summary.json').read_text())
            self.assertFalse(summary['complete'])
            self.assertEqual(summary['records'], 16)
            self.assertFalse((output / 'COMPLETE').exists())
            self.assertTrue(all(not counts for counts in summary['paired_block_comparisons'].values()))


if __name__ == '__main__':
    unittest.main()
