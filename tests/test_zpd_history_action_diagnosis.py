import unittest

from scripts import diagnose_zpd_history_action_cv as diagnosis


def row(user, value, probability, mask=True):
    return {'user_id': user, 'values': [value], 'mask': [mask],
            'probabilities': {arm: [probability] for arm in diagnosis.ARMS}}


class DiagnosisTests(unittest.TestCase):
    def test_equal_user_not_equal_prefix(self):
        rows = [row('a', 1, .9)] * 3 + [row('b', 1, .1)]
        summary = diagnosis.summarize(rows, ['event'])
        import math
        self.assertAlmostEqual(summary['loss']['H'], (-math.log(.9) - math.log(.1)) / 2)
        self.assertEqual(summary['users'], 2)

    def test_unavailable_is_not_zero_loss(self):
        summary = diagnosis.summarize([row('a', 1, .9, False)], ['event'])
        self.assertIsNone(summary['loss']['H'])
        self.assertEqual(summary['all_masked_prefixes'], 1)
        self.assertEqual(summary['users'], 0)

    def test_zero_probability_clip_is_finite(self):
        import math
        self.assertAlmostEqual(diagnosis.losses(row('a', 1, 0), ['e'])['H']['prefix_loss'], -math.log(1e-12))

    def test_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            diagnosis.losses(row('a', 1, float('nan')), ['e'])

    def checks(self, passed):
        return {c: {'aggregate_strictly_better': passed, 'at_least_four_folds': passed,
                    'simultaneous_upper_below_zero': passed} for c in diagnosis.CONTROLS}

    def test_gate_failure_does_not_select_secondary_winner(self):
        result = diagnosis.route({'gate_passed': False, 'checks': self.checks(False)})
        self.assertEqual(set(result['failed_checks']), set(diagnosis.CONTROLS))
        self.assertFalse(result['automatic_model_promotion'])

    def test_gate_pass_only_releases_protocol_design(self):
        result = diagnosis.route({'gate_passed': True, 'checks': self.checks(True)})
        self.assertEqual(result['action'], 'freeze_and_audit_repair_integration')
        self.assertFalse(result['repair_improvement_established'])
        self.assertTrue(result['new_protocol_and_code_audit_required'])

    def test_inconsistent_gate_rejected(self):
        with self.assertRaises(ValueError):
            diagnosis.route({'gate_passed': True, 'checks': self.checks(False)})


if __name__ == '__main__':
    unittest.main()
