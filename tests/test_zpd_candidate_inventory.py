import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts.inventory_zpd_candidate_problems import inventory


class CandidateInventoryTests(unittest.TestCase):
    def test_path_inventory_is_not_fresh_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, original = root / 'repo', root / 'original'
            (repo / 'data' / 'p00001').mkdir(parents=True)
            (repo / 'data' / 'splits').mkdir()
            (repo / 'data' / 'splits' / 'problem_split.jsonl').write_text(json.dumps({'problem_id': 'p00002'}) + '\n')
            (original / 'metadata').mkdir(parents=True)
            for key in ('p00001', 'p00002', 'p00003'):
                (original / 'metadata' / (key + '.csv')).write_text('not valid metadata; do not parse')
                (original / 'data' / key / 'Python').mkdir(parents=True)
            output = repo / 'outputs' / 'inventory'
            with contextlib.redirect_stdout(io.StringIO()):
                inventory(repo, original, output)
            result = json.loads((output / 'inventory.json').read_text())
            self.assertEqual(result['population']['candidate_problem_ids'], ['p00003'])
            self.assertFalse(result['fresh_holdout_certified'])
            self.assertFalse(result['metadata_contents_opened'])
            with self.assertRaises(ValueError):
                inventory(repo, original, original / 'bad-output')
