import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_zpd_fresh_holdout import audit

HEADER = 'submission_id,problem_id,user_id,date,language,original_language,filename_ext,status,cpu_time,memory,code_size,accuracy\n'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def fixture(root, verdict):
    repo, original = root / 'repo', root / 'original'
    (repo / 'data' / 'p00001').mkdir(parents=True, exist_ok=True)
    write(repo / 'data/splits/problem_split.jsonl', json.dumps({'problem_id': 'p00001'}) + '\n')
    write(repo / 'outputs/zpd-history-gate-20260915/original-prefixes/manifest.json',
          json.dumps({'problem_roster': ['p00001']}))
    write(root / 'remote.txt', 'p00001\n')
    (original / 'derived/benchmarks/Project_CodeNet_Python800/p00004').mkdir(parents=True, exist_ok=True)
    write(original / 'metadata/problem_list.csv', 'id,name,dataset\np00002,x,AtCoder\n')
    write(original / 'metadata/p00001.csv', HEADER + f's9,p00001,u1,1,Python,Python (3),py,{verdict},1,1,1,1/1\n')
    write(original / 'metadata/p00004.csv', HEADER + f's8,p00004,u3,1,Python,Python (3),py,{verdict},1,1,1,1/1\n')
    write(original / 'metadata/p00003.csv', HEADER + f's7,p00003,u2,1,C,C,c,{verdict},1,1,1,1/1\n')
    write(original / 'metadata/p00002.csv', HEADER + ''.join(
        f'{sid},p00002,{user},{date},{lang},{lang} (x),{ext},{verdict},{date},{date},9,0/1\n'
        for sid, user, date, lang, ext in [('s1', 'u1', 10, 'C++', 'cpp'), ('s2', 'u1', 20, 'Python', 'py'),
                                           ('s3', 'u1', 20, 'Python', 'py'), ('s4', 'u2', 5, 'Python', 'py'),
                                           ('s5', 'u2', 7, 'Python', 'py')]))
    for problem, name in [('p00001', 's9.py'), ('p00004', 's8.py'), ('p00002', 's2.py'), ('p00002', 's5.py')]:
        write(original / 'data' / problem / 'Python' / name, 'print(1)\n')
    return repo, original, root / 'remote.txt'


class FreshHoldoutAuditTest(unittest.TestCase):
    def run_audit(self, verdict):
        with tempfile.TemporaryDirectory() as tmp:
            repo, original, remote = fixture(Path(tmp), verdict)
            report = audit(repo, original, remote, repo / 'outputs/audit')
            with self.assertRaises(ValueError):
                audit(repo, original, remote, repo / 'outputs/audit')
            return report

    def test_counts_and_exposure(self):
        report = self.run_audit('Accepted')
        self.assertEqual(report['population_counts']['candidate_problems'], 1)
        self.assertEqual(report['exposure_counts']['union'], 2)
        self.assertTrue(report['local_equals_remote_data'])
        self.assertEqual(report['per_problem']['p00002'], {
            'rows': 5, 'python_rows': 4, 'structural_prefix_upper_bound': 3,
            'upper_bound_outside_python800_any': 1, 'upper_bound_outside_history_gate_any': 1,
            'upper_bound_outside_history_gate_test_split': 3, 'tie_rows': 2,
            'source_available': 2, 'user_problem_groups': 2, 'dataset': 'AtCoder'})
        self.assertEqual(report['exposure_user_tier_counts'],
                         {'python800_any': 2, 'history_gate_any': 1, 'history_gate_test_split': 0})
        self.assertEqual(report['totals']['prefix_users_outside_python800_any'], 1)

    def test_report_is_independent_of_dropped_columns(self):
        blind = lambda r: json.dumps({k: v for k, v in r.items() if k != 'candidate_metadata_sha256'}, sort_keys=True)
        with tempfile.TemporaryDirectory() as tmp:
            reports = []
            for name, verdict in [('a', 'Accepted'), ('b', 'Wrong Answer')]:
                repo, original, remote = fixture(Path(tmp), verdict)
                reports.append(audit(repo, original, remote, repo / 'outputs' / name))
        self.assertNotEqual(reports[0]['candidate_metadata_sha256'], reports[1]['candidate_metadata_sha256'])
        self.assertEqual(blind(reports[0]), blind(reports[1]))


if __name__ == '__main__':
    unittest.main()
