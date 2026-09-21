import json
from pathlib import Path
import tempfile
import unittest

from scripts.prepare_zpd_repair_replication import prepare, read, sha, SALT


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root, self.data, self.previous, self.output = [base / n for n in ('input', 'data', 'previous', 'output')]
        for path in (self.root, self.data / 'p1', self.previous):
            path.mkdir(parents=True)
        (self.data / 'p1' / 'description.html').write_text('<p>Problem</p>')
        (self.data / 'p1' / 'metadata.json').write_text('{}')
        (self.data / 'p1' / 'testcases.jsonl').write_text('not parsed, hashed only')
        self.codes = [dict(code_id=f'c{i}', code=f'x = {i}', source_sha256=sha(f'x = {i}'.encode())) for i in range(12)]
        self.rows = [self.row('donor', 'train', 'du', 'c0', 10)]
        self.rows += [self.row(f'v{i}', 'valid', f'u{i}', f'c{i}', 20 + i) for i in range(1, 9)]
        self.seal_input()
        source = lambda i: dict(submission_id=f'c{i}', source=f'x = {i}', source_sha256=sha(f'x = {i}'.encode()), timestamp=i, verdict='WA')
        self.old = [dict(user_id='u1', observation=dict(current=source(2), prior=[source(3)]), donor_history=[source(4)])]
        self.seal_previous()

    def row(self, identity, split, user, code, timestamp):
        return dict(example_id=identity, split=split, user_id=user, current_code_id=code, timestamp=timestamp,
                    current_verdict='WA', matching_current_verdict='Wrong Answer', history=[],
                    problem_id='p1', donor_example_id=None if split == 'train' else 'donor')

    def write_rows(self, path, rows):
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows))

    def seal_input(self):
        self.write_rows(self.root / 'features.jsonl', self.rows)
        self.write_rows(self.root / 'codes.jsonl', self.codes)
        self.hashes = {n: sha((self.root / n).read_bytes()) for n in ('features.jsonl', 'codes.jsonl')}
        (self.root / 'manifest.json').write_text(json.dumps(dict(file_sha256=self.hashes)))

    def seal_previous(self):
        self.write_rows(self.previous / 'observations.jsonl', self.old)
        for name in ('requests.jsonl', 'exclusions.jsonl'):
            (self.previous / name).write_text('')
        hashes = {n: sha((self.previous / n).read_bytes()) for n in ('observations.jsonl', 'requests.jsonl', 'exclusions.jsonl')}
        (self.previous / 'manifest.json').write_text(json.dumps(dict(output_sha256=hashes, input_sha256=self.hashes)))

    def run_prepare(self, size=4):
        return prepare(self.root, self.data, self.previous, self.output, sample_size=size)

    def test_deterministic_exclusions_and_strict_requests(self):
        result = self.run_prepare()
        selected = read(self.output / 'observations.jsonl')
        self.assertEqual({r['example_id'] for r in selected}, {'v5', 'v6', 'v7', 'v8'})
        self.assertEqual(result['selection_salt'], SALT)
        self.assertEqual(result['verified_source_count'], 12)
        self.assertTrue(all(r['split'] == 'valid' for r in selected))
        requests = read(self.output / 'requests.jsonl')
        self.assertEqual(requests, read(self.output / 'requests-0.jsonl'))
        self.assertEqual(read(self.output / 'requests-1.jsonl'), [])
        for request in requests:
            self.assertEqual(set(request), {'bank_id', 'problem_id', 'current_source', 'problem_description', 'time_limit', 'memory_limit'})
            self.assertEqual(request['bank_id'], sha(('p1|' + sha(request['current_source'].encode())).encode()))
        other = self.output.parent / 'again'
        repeated = prepare(self.root, self.data, self.previous, other, sample_size=4)
        self.assertEqual(result, repeated)
        self.assertFalse(any(self.root.glob('labels*')))

    def test_insufficient_fails_without_output(self):
        with self.assertRaisesRegex(ValueError, 'insufficient'):
            self.run_prepare(5)
        self.assertFalse(self.output.exists())

    def test_manifest_tampering(self):
        (self.previous / 'requests.jsonl').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'manifest mismatch'):
            self.run_prepare()

    def test_production_requires_original_96_cohort(self):
        self.old[0]['split'] = 'valid'
        self.seal_previous()
        with self.assertRaisesRegex(ValueError, 'original 64 train'):
            prepare(self.root, self.data, self.previous, self.output,
                    sample_size=4, require_original_cohort=True)

    def test_all_code_sha_verified_even_unused(self):
        self.codes[-1]['code'] = 'changed unused'
        self.seal_input()
        self.seal_previous()
        with self.assertRaisesRegex(ValueError, 'source SHA mismatch'):
            self.run_prepare()

    def test_raw_verdict_match_not_category_match(self):
        self.rows[0]['matching_current_verdict'] = 'Time Limit Exceeded'
        self.seal_input()
        self.seal_previous()
        with self.assertRaisesRegex(ValueError, 'donor mismatch'):
            self.run_prepare()

    def test_future_donor_rejected(self):
        self.rows[0]['timestamp'] = 1000
        self.seal_input()
        self.seal_previous()
        with self.assertRaisesRegex(ValueError, 'donor mismatch'):
            self.run_prepare()

    def test_selected_user_only_one_prefix(self):
        for row in self.rows:
            if row['example_id'] in ('v5', 'v6'):
                row['user_id'] = 'same'
        self.seal_input()
        self.seal_previous()
        with self.assertRaisesRegex(ValueError, 'insufficient'):
            self.run_prepare()

    def test_full_budget_request_batches_are_64(self):
        self.codes = [dict(code_id=f'c{i}', code=f'x = {i}', source_sha256=sha(f'x = {i}'.encode())) for i in range(133)]
        self.rows = [self.row('donor', 'train', 'du', 'c0', 10)]
        self.rows += [self.row(f'v{i}', 'valid', f'u{i}', f'c{i}', 20 + i) for i in range(1, 133)]
        self.seal_input()
        self.seal_previous()
        result = self.run_prepare(128)
        self.assertEqual(result['counts']['valid_selected'], 128)
        self.assertEqual(len(read(self.output / 'requests-0.jsonl')), 64)
        self.assertEqual(len(read(self.output / 'requests-1.jsonl')), 64)


if __name__ == '__main__':
    unittest.main()
