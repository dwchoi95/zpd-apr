import copy
import unittest

from scripts.diagnose_zpd_history_action_c2 import compare_predictions, ARMS
from scripts.diagnose_zpd_history_action_failure import diagnose_records
from scripts.zpd_history_action_encoder import EVENTS


def fixture():
    base = dict(example_id='e0', user_id='u0', problem_id='p0', fold=0, donor_example_id='d0',
        values=[0.]*18, mask=[True]*18, target_status='available', next_language='Python',
        current_source_sha256='a'*64, current_seen_in_fold_training=False,
        within_held_cross_user_distinct_history_collision=False, hs_prior_length_one=True,
        hs_permutation_identity=True, hs_hashed_features_equal=True,
        probabilities={arm:[.5]*18 for arm in ARMS})
    before = [base]; after = copy.deepcopy(before)
    after[0]['probabilities']['H'] = [.4]*18
    def report(rows):
        decomposition = diagnose_records(rows, EVENTS)
        all_rows = decomposition['overall']
        return dict(events=list(EVENTS), decision={'gate_passed':False},
            results={a:dict(user_equal_masked_nll=all_rows['nll_contribution'][a],
                evaluable_prefixes=1, all_masked_prefixes=0, users=1) for a in ARMS},
            event_diagnostics={'events':{e:v['nll_contribution'] for e,v in all_rows['events'].items()}})
    return before, after, report(before), report(after)


class C2DiagnosisTests(unittest.TestCase):
    def test_all_events_and_additive_groups_preserved(self):
        result = compare_predictions(*fixture())
        self.assertFalse(result['c2_decision_unchanged']['gate_passed'])
        self.assertEqual(result['c0_parity']['maximum_absolute_difference'], 0.)
        self.assertEqual(len(result['c2']['events']), 18)
        for arm in ARMS:
            self.assertAlmostEqual(sum(g['C2'][arm] for g in result['event_groups_additive_mass'].values()),
                result['c2']['overall']['nll_contribution'][arm])

    def test_mask_target_and_c0_drift_rejected(self):
        for change in ('mask', 'values', 'donor', 'c0'):
            before, after, r1, r2 = fixture()
            if change == 'mask': after[0]['mask'][0] = False
            elif change == 'values': after[0]['values'][0] = 1.
            elif change == 'donor': after[0]['donor_example_id'] = 'wrong'
            else: after[0]['probabilities']['C0'][0] = .51
            with self.assertRaises(ValueError): compare_predictions(before, after, r1, r2)

    def test_contribution_or_event_drop_rejected(self):
        before, after, r1, r2 = fixture()
        r2['event_diagnostics']['events'][EVENTS[0]]['H'] += .01
        with self.assertRaises(ValueError): compare_predictions(before, after, r1, r2)
        before, after, r1, r2 = fixture()
        r2['events'].pop()
        with self.assertRaises(ValueError): compare_predictions(before, after, r1, r2)


if __name__ == '__main__':
    unittest.main()
