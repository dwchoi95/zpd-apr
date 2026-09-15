import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_zpd_legacy_prefix_inventory import build, rows


class LegacyInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.archive, self.retained, self.output = root / 'archive', root / 'retained', root / 'out'
        self.problem = self.archive / 'p1'
        self.problem.mkdir(parents=True)
        self.retained.mkdir()
        self.raw = [{'submission_id': f's{i}', 'problem_id': 'p1', 'lang': 'python',
                     'code_tokens': code, 'verdict': verdict}
                    for i, (code, verdict) in enumerate([
                        (' x = "\u2028"\n', 'Wrong Answer'),
                        (' x = "\u2028"\n', 'Wrong Answer'), ('x=2\n', 'Accepted')])]
        self.seq = {'sequence_id': 'q', 'problem_id': 'p1', 'user_id': 'u',
                    'sequence_length': 3, 'submission_ids': ['s0', 's1', 's2'],
                    'timestamps': [1, 1, 3],
                    'verdicts': ['Wrong Answer', 'Wrong Answer', 'Accepted']}
        self.save()

    def save(self):
        (self.problem / 'submissions.jsonl').write_text(
            ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in self.raw))
        (self.problem / 'sequences.jsonl').write_text(json.dumps(self.seq) + '\n')

    def test_preserves_code_and_separates_future(self):
        report = build(self.archive, self.retained, self.output)
        features = list(rows(self.output / 'features.jsonl'))
        labels = list(rows(self.output / 'labels.jsonl'))
        codes = list(rows(self.output / 'codes.jsonl'))
        self.assertEqual(codes[0]['code'], self.raw[0]['code_tokens'])
        self.assertEqual(features[0]['observed_history'][0]['submission_id'], 's0')
        self.assertNotIn('next_timestamp', features[0])
        self.assertNotIn('sequence_length', features[0])
        self.assertEqual(labels[0]['next_submission_id'], 's1')
        self.assertEqual(report['counts']['timestamp_ties'], 1)
        self.assertEqual(report['counts']['prefixes'], 2)
        self.assertTrue(report['eventual_ac_only'])
        self.assertTrue((self.output / 'COMPLETE').exists())

    def test_missing_code_fails_without_complete(self):
        self.raw.pop()
        self.save()
        with self.assertRaisesRegex(ValueError, 'missing archived code'):
            build(self.archive, self.retained, self.output)
        self.assertFalse((self.output / 'COMPLETE').exists())

    def test_reverse_timestamp_fails(self):
        self.seq['timestamps'] = [2, 1, 3]
        self.save()
        with self.assertRaisesRegex(ValueError, 'nonchronological'):
            build(self.archive, self.retained, self.output)

    def test_retained_code_mismatch_fails(self):
        target = self.retained / 'p1' / 'submissions'
        target.mkdir(parents=True)
        (target / 'u.jsonl').write_text(json.dumps(
            {'submission_id': 's0', 'code': 'different', 'timestamp': 1}) + '\n')
        with self.assertRaisesRegex(ValueError, 'retained code/timestamp'):
            build(self.archive, self.retained, self.output)

    def test_refuses_overwrite_and_input_subdirectory(self):
        self.output.mkdir()
        with self.assertRaises(FileExistsError):
            build(self.archive, self.retained, self.output)
        with self.assertRaisesRegex(ValueError, 'separate'):
            build(self.archive, self.retained, self.archive / 'new')

    def test_non_success_cohort_not_silently_removed(self):
        self.raw[-1]['verdict'] = 'Wrong Answer'
        self.seq['verdicts'][-1] = 'Wrong Answer'
        self.save()
        report = build(self.archive, self.retained, self.output)
        self.assertFalse(report['eventual_ac_only'])
        self.assertEqual(report['counts']['prefixes'], 2)


if __name__ == '__main__':
    unittest.main()
