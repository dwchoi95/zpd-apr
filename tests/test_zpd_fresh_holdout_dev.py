import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.zpd_fresh_holdout_dev import build, split_for_user, stage

HEADER = 'submission_id,problem_id,user_id,date,language,original_language,filename_ext,status,cpu_time,memory,code_size,accuracy\n'


def v1_test(user):
    return int(hashlib.sha256(f'zpd-history-gate-20260915-v1:{user}'.encode()).hexdigest(), 16) / 2**256 >= .85


def find(predicate):
    return next(f'u{i}' for i in range(100000) if predicate(f'u{i}'))


T = find(lambda u: split_for_user(u) == 'train' and not v1_test(u))
V = find(lambda u: split_for_user(u) == 'valid' and not v1_test(u))
E = find(lambda u: split_for_user(u) == 'eval' and not v1_test(u))
X = find(lambda u: split_for_user(u) == 'train' and v1_test(u))


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def fixture(root, hidden_verdict):
    original, audit = root / 'original', root / 'audit'
    write(original / 'metadata/p00010.csv', HEADER + f's0,p00010,{X},1,Python,P,py,Accepted,1,1,1,1/1\n')
    lines = []
    for user in (T, V, E, X):
        verdicts = ('Wrong Answer', 'Wrong Answer', 'Accepted') if user in (T, V) else (hidden_verdict,) * 3
        for step, verdict in enumerate(verdicts, 1):
            lines.append(f's{user}{step},p00020,{user},{step},Python,P,py,{verdict},{step},1,1,1/1\n')
            write(original / f'data/p00020/Python/s{user}{step}.py', f'print({step})\n')
    write(original / 'metadata/p00020.csv', HEADER + ''.join(lines))
    report = {'per_problem': {'p00020': {'dataset': 'AtCoder'}, 'p00030': {'dataset': 'AIZU'}},
              'exposure_sources': {'history_gate_roster': ['p00010'], 'python800_benchmark': ['p00010']}}
    write(audit / 'report.json', json.dumps(report))
    write(audit / 'COMPLETE', hashlib.sha256((audit / 'report.json').read_bytes()).hexdigest() + '\n')
    return original, audit


class FreshHoldoutDevTest(unittest.TestCase):
    def staged(self, root, verdict, name):
        original, audit = fixture(root, verdict)
        expected = (audit / 'COMPLETE').read_text().strip()
        return original, stage(audit, original, root / name, expected_complete=expected)

    def test_stage_drops_eval_and_excluded_users_blindly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, first = self.staged(root, 'Accepted', 'a')
            _, second = self.staged(root, 'Runtime Error', 'b')
            staged = (root / 'a/metadata/p00020.csv').read_text()
            self.assertEqual(staged, (root / 'b/metadata/p00020.csv').read_text())
        self.assertEqual(first, second)
        self.assertIn(T, staged)
        self.assertIn(V, staged)
        self.assertNotIn(f',{E},', staged)
        self.assertNotIn(f',{X},', staged)
        self.assertEqual(first['roster'], ['p00020'])
        self.assertEqual(first['excluded_user_count'], 1)
        self.assertEqual(first['eval_structural_users'], [E])
        self.assertEqual(first['structural_upper_bound_users'], {'train': 1, 'valid': 1, 'eval': 1})

    def test_build_uses_unmodified_builder_with_dev_splits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original, _ = self.staged(root, 'Accepted', 'staging')
            manifest = build(root / 'staging', original, root / 'prefixes')
            refs = [json.loads(line) for line in (root / 'prefixes/references.jsonl').read_text().splitlines()]
        self.assertEqual(manifest['split']['salt'], 'zpd-fresh-holdout-20260917-v1')
        self.assertEqual({(r['user_id'], r['split']) for r in refs}, {(T, 'train'), (V, 'valid')})
        self.assertEqual(manifest['counts']['primary_eligible_prefixes'], 2)


if __name__ == '__main__':
    unittest.main()
