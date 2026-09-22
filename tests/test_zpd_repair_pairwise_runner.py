import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from scripts import run_zpd_repair_pairwise_development as runner


class PairwiseRunnerTests(unittest.TestCase):
    def test_complete_exact_files_and_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            files={}
            for name in ('manifest.json','completions.jsonl','labels.jsonl'):
                (path/name).write_bytes(b'{}')
                files[name]=hashlib.sha256(b'{}').hexdigest()
            marker=dict(status='fully_executed',development_only=True,files_sha256=files)
            (path/'COMPLETE.json').write_text(json.dumps(marker))
            runner.verify_evaluation(path)
            (path/'labels.jsonl').write_bytes(b'changed')
            with self.assertRaises(ValueError):runner.verify_evaluation(path)
            files.pop('labels.jsonl')
            (path/'COMPLETE.json').write_text(json.dumps(marker))
            with self.assertRaises(ValueError):runner.verify_evaluation(path)

    def test_unknown_shared_choice_cancels_and_history_comparisons(self):
        row=dict(example_id='e',candidate_id='same',utility=-1,utility_upper_bound=1)
        group={name:dict(predictions=[row]) for name in ('pairwise_C','pairwise_H','pairwise_U','old_C','old_H','old_U','first_attempt')}
        result=runner.comparisons(group)
        self.assertEqual(result['H-pairwise_C']['lower'],0)
        self.assertEqual(result['H-pairwise_U']['upper'],0)
        group['pairwise_H']={'predictions':[dict(row,candidate_id='different')]}
        result=runner.comparisons(group)
        self.assertEqual(result['H-pairwise_C']['lower'],-2)
        self.assertEqual(result['H-pairwise_C']['upper'],2)

    def test_selection_seal_precedes_diagnostic_label_load(self):
        # Boundary regression check in addition to train-only model fixtures.
        source=inspect.getsource(runner.main)
        self.assertLess(source.index("SELECTION_COMPLETE.json"),source.index("read_jsonl(rep/'evaluation'/'labels.jsonl')"))


if __name__=='__main__':unittest.main()
