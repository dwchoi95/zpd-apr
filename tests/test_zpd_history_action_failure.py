import copy
import math
import unittest

from scripts.diagnose_zpd_history_action_failure import ARMS, diagnose_records


def record(identity, user, values, mask, h, baseline, *, language='Python', one=True):
    return dict(example_id=identity, user_id=user, values=values, mask=mask,
        probabilities={a: h if a == 'H' else baseline for a in ARMS},
        target_status='available' if any(mask) else 'unavailable', next_language=language,
        hs_prior_length_one=one, hs_permutation_identity=one, hs_hashed_features_equal=one,
        current_seen_in_fold_training=False,
        within_held_cross_user_distinct_history_collision=False, fold=0)


def fixture_rows():
    return [record('a', 'u1', [1, 0], [True, True], [.8, .2], [.5, .5]),
            record('b', 'u1', [1, 0], [True, False], [.4, .3], [.5, .5], language='C++', one=False),
            record('c', 'u2', [0, 1], [False, True], [.3, .9], [.5, .5]),
            record('d', 'u3', [0, 0], [False, False], [.2, .7], [.5, .5], language=None)]


class FailureDiagnosisTests(unittest.TestCase):
 def test_global_weights_and_exact_additivity(self):
    result = diagnose_records(fixture_rows(), ['e1', 'e2'], {'a': 1, 'b': 2, 'c': 1, 'd': 1})
    overall = result['overall']
    # u1 has two evaluable prefixes, u2 one: original weights are 1/4,1/4,1/2.
    expected = (-math.log(.8)/4-math.log(.4)/4-math.log(.9)/2)
    self.assertAlmostEqual(overall['nll_contribution']['H'], expected)
    assert overall['evaluable_users'] == 2
    assert overall['all_masked_prefixes'] == 1
    self.assertAlmostEqual(overall['global_prefix_weight'], 1.)
    self.assertAlmostEqual(overall['events']['e1']['global_event_weight'], 3/8)
    self.assertAlmostEqual(overall['events']['e2']['global_event_weight'], 5/8)
    # Event-reweighted averages cannot substitute for the primary decomposition.
    self.assertAlmostEqual(overall['events']['e1']['nll_contribution']['H'], -math.log(.8)/8-math.log(.4)/4)
    for groups in result['partitions'].values():
        assert sum(g['prefixes'] for g in groups.values()) == 4
        for arm in ARMS:
            self.assertAlmostEqual(sum(g['nll_contribution'][arm] for g in groups.values()), overall['nll_contribution'][arm])
    for control in ('C0', 'HS'):
        self.assertAlmostEqual(sum(e['h_minus'][control] for e in overall['events'].values()), overall['h_minus'][control])
    missing = result['partitions']['successor_language_family']['unavailable']
    assert missing['prefixes'] == 1 and missing['evaluable_prefixes'] == 0
    assert missing['nll_contribution']['H'] == 0


 def test_invalid_probabilities_masks_duplicates_and_prior_join(self):
    for change in ('nan', 'mask', 'duplicate', 'prior'):
        rows = fixture_rows()
        counts = None
        if change == 'nan': rows[0]['probabilities']['H'][0] = float('nan')
        if change == 'mask': rows[0]['mask'][0] = 1
        if change == 'duplicate': rows[1]['example_id'] = rows[0]['example_id']
        if change == 'prior': counts = {'a': 2, 'b': 2, 'c': 1, 'd': 1}
        with self.assertRaises(ValueError):
            diagnose_records(rows, ['e1', 'e2'], counts)


 def test_clip_and_masked_values_do_not_add_loss(self):
    rows = fixture_rows()
    rows[0]['probabilities']['H'] = [0., 1.]
    before = diagnose_records(rows, ['e1', 'e2'])
    changed = copy.deepcopy(rows)
    changed[1]['values'][1] = 1
    changed[1]['probabilities']['H'][1] = 0.
    after = diagnose_records(changed, ['e1', 'e2'])
    assert before == after
    assert math.isfinite(before['overall']['nll_contribution']['H'])


 def test_no_evaluable_rows_is_not_zero_loss(self):
    with self.assertRaisesRegex(ValueError, 'undefined'):
        diagnose_records([fixture_rows()[-1]], ['e1', 'e2'])


if __name__ == '__main__':
    unittest.main()
