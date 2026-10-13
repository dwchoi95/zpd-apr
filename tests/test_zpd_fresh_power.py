from statistics import NormalDist
import unittest

from scripts.zpd_fresh_power import SPEC, estimate, go_decision, mde, user_fold


def rows(count=60):
    return [{'example_id': f'p1:s{i}', 'user_id': f'u{i}', 'problem_id': 'p1', 'split': 'train',
             'timestamp': 100 + i, 'current_verdict': 'WA', 'matching_current_verdict': 'Wrong Answer',
             'current_code': f'print({i % 3})\n', 'next_label': 'AC' if i % 2 else 'WA',
             'history': [{'code': 'print(1)\n', 'verdict': 'WA', 'timestamp': i}]}
            for i in range(count)]


class FreshPowerTest(unittest.TestCase):
    def test_mde_and_boundary_rule(self):
        z = NormalDist().inv_cdf(.975) + NormalDist().inv_cdf(.8)
        self.assertAlmostEqual(mde({'a': 0., 'b': 2.}, 2)['detectable_nll_difference'], z)
        at_threshold = {c: {'detectable_nll_difference': t} for c, t in SPEC['go_thresholds'].items()}
        self.assertTrue(go_decision(at_threshold)['proceed_to_stage_e'])
        at_threshold['U_H']['detectable_nll_difference'] += 1e-9
        self.assertFalse(go_decision(at_threshold)['proceed_to_stage_e'])

    def test_train_only_crossfit_with_real_encoder(self):
        with self.assertRaises(ValueError):
            estimate([dict(rows()[0], split='valid')], 10, n_features=16)
        events = []
        result = estimate(rows(), 100, n_features=16, callback=events.append)
        self.assertEqual(len(events), SPEC['folds'] * len(SPEC['arms']) * len(SPEC['seeds']))
        self.assertGreater(result['U_H']['user_count'], 0)
        self.assertEqual(result['C_H']['user_count'], result['U_H']['user_count'])
        self.assertEqual(sum(f['held_users'] for f in result['folds']), result['U_H']['user_count'])
        self.assertIn('proceed_to_stage_e', result['decision'])
        self.assertEqual({user_fold(f'u{i}') for i in range(60)}, set(range(5)))


if __name__ == '__main__':
    unittest.main()
