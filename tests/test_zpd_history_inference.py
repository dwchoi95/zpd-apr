import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts import zpd_history_inference as inference


class HistoryInferenceTests(unittest.TestCase):
    def test_user_equal_not_row_equal(self):
        users, values = inference.user_means([1, 1, 1, -1], ['a', 'a', 'a', 'b'])
        self.assertEqual(list(users), ['a', 'b'])
        self.assertEqual(values.mean(), 0)
        self.assertAlmostEqual(inference.row_weights(['a', 'a', 'a', 'b']).sum(), 1)

    def test_resampling_null_and_constant_positive(self):
        null = inference.paired_user_inference(np.zeros(4), list('abcd'), bootstrap_reps=50, signflip_reps=100)
        self.assertEqual(null['one_sided_p'], 1)
        self.assertEqual(null['ci95'], [0, 0])
        good = inference.paired_user_inference(np.ones(20), [str(i) for i in range(20)], bootstrap_reps=50, signflip_reps=1000)
        self.assertEqual(good['ci95'], [1, 1])
        self.assertLess(good['one_sided_p'], .01)
        # Fixed integer batches must not change Monte Carlo draws.
        again = inference.paired_user_inference(np.ones(20), [str(i) for i in range(20)], bootstrap_reps=50, signflip_reps=1000, batch=7)
        self.assertEqual(good, again)

    def test_holm(self):
        self.assertEqual(inference.holm([.03, .01]), [.03, .02])
        self.assertEqual(inference.holm([.8, .9]), [1, 1])

    def test_metrics(self):
        p = np.eye(6)[[0, 1]]
        result = inference.metrics(np.array([0, 1]), p, ['a', 'b'])
        self.assertEqual(result['user_equal_accuracy'], 1)
        self.assertEqual(result['user_equal_brier_sum_classes'], 0)
        self.assertEqual(result['user_equal_ece_10'], 0)
        self.assertEqual(result['calibration'][9]['rows'], 2)
        with self.assertRaises(ValueError):
            inference.validate_probabilities(np.ones((2, 6)), 2)

    def test_problem_multiplicity_preserves_user_estimand(self):
        # Every represented user's mean is fixed regardless of sampled problem.
        delta = np.array([1., 1., -1., -1.])
        result = inference.problem_sensitivity(delta, ['a', 'a', 'b', 'b'], ['p', 'q', 'p', 'q'], reps=50)
        self.assertEqual(result['ci95'], [0., 0.])
        self.assertEqual(inference.problem_sensitivity([1], ['a'], ['p'])['status'], 'not_measured')

    def test_collision_and_train_overlap(self):
        def row(i, user, split, history):
            return dict(example_id=i, user_id=user, split=split, problem_id='p', current_code_id='c',
                        history=[dict(code_id=history, verdict='WA')])
        rows = [row('0', 't', 'train', 'h1'), row('1', 'a', 'test', 'h1'), row('2', 'b', 'test', 'h2')]
        result, collisions = inference.strata(rows, {'c': 'code', 'h1': 'old1', 'h2': 'old2'})
        self.assertEqual(result['train_code_seen'], {'1', '2'})
        self.assertEqual(result['within_test_crossuser_distinct_history'], {'1', '2'})
        self.assertEqual(len(collisions), 1)
        rows[2]['user_id'] = 'a'
        self.assertEqual(inference.strata(rows, {'c': 'code', 'h1': 'old1', 'h2': 'old2'})[1], set())

    def test_prediction_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'p.npz'
            p = np.full((2, 6), 1/6)
            np.savez(path, example_ids=['a', 'b'], labels=['AC', 'WA'], probabilities=p,
                     seed_probabilities=np.array([p, p, p]))
            self.assertEqual(list(inference.load_predictions(path)['labels']), [0, 1])
            np.savez(path, example_ids=['a', 'a'], labels=[0, 1], probabilities=p,
                     seed_probabilities=np.array([p, p, p]))
            with self.assertRaises(ValueError):
                inference.load_predictions(path)

    def test_sealed_end_to_end_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared, predictions = root / 'prepared', root / 'predictions'
            prepared.mkdir()
            predictions.mkdir()
            features = [dict(example_id=str(i), user_id='u'+str(i), problem_id='p'+str(i % 2),
                             current_code_id='c', split='test', donor_example_id='donor',
                             history=[dict(code_id='h'+str(i % 2), verdict='WA')]) for i in range(4)]
            def write_jsonl(path, rows):
                path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            write_jsonl(prepared / 'features.jsonl', features)
            write_jsonl(prepared / 'codes.jsonl', [dict(code_id='c', code='x'), dict(code_id='h0', code='a'), dict(code_id='h1', code='b')])
            write_jsonl(prepared / 'labels-test.jsonl', [dict(example_id=str(i), next_label='AC') for i in range(4)])
            (prepared / 'manifest.json').write_text(json.dumps({'file_sha256': {p.name: inference.sha(p) for p in prepared.glob('*.jsonl')}}))
            (predictions / 'metadata.json').write_text(json.dumps({
                'input_manifest_sha256': inference.sha(prepared / 'manifest.json'),
                'source_sha256': {'scripts/zpd_history_inference.py': inference.sha(inference.__file__)}}))
            for arm in inference.ARMS:
                p = np.full((4, 6), .1)
                p[:, 0] = .5
                ids = np.array(['0', '1', '2', '3'])
                if arm.startswith('H'):
                    p[:] = .08
                    p[:, 0] = .6
                    ids = ids[::-1]  # Alignment must use IDs, not positional equality.
                np.savez(predictions / (arm+'-test.npz'), example_ids=ids, labels=np.zeros(4, dtype=int),
                         probabilities=p, seed_probabilities=np.array([p, p, p]))
            test_report = dict(test_opened=True, state='complete', automatic_retry=False,
                               file_sha256={p.name: inference.sha(p) for p in predictions.iterdir()})
            (predictions / 'test.json').write_text(json.dumps(test_report))
            (predictions / 'COMPLETE').write_text(inference.sha(predictions / 'test.json')+'\n')
            report = inference.analyze(predictions, prepared, root / 'result')
            self.assertAlmostEqual(report['primary']['C_F-H_F']['improvement_nll'], np.log(.6/.5))
            self.assertEqual((root / 'result' / 'COMPLETE').read_text().strip(), inference.sha(root / 'result' / 'manifest.json'))
            (prepared / 'labels-test.jsonl').write_text('')
            with self.assertRaisesRegex(ValueError, 'prepared input hash'):
                inference.analyze(predictions, prepared, root / 'tampered-result')


if __name__ == '__main__':
    unittest.main()
