import unittest

from scripts.diagnose_zpd_repair_preservation_failure import paired_record, aggregate, margin_decomposition


def result(cid, *, noop=False, ac=False, regression=False, unknown=False):
    return dict(candidate_id=cid, noop=float(noop), rr_lower_bound=float(ac),
                regression_rate_lower_bound=float(regression), unknown=float(unknown))


class PreservationFailureTests(unittest.TestCase):
    def test_loss_and_unknown_are_not_conflated(self):
        base = dict(example_id='x', problem_id='p', fold=0)
        old = result('repair', ac=True)
        noop = result('original', noop=True)
        lost = paired_record(base, noop, old, noop)
        self.assertEqual((lost['category'], lost['ac_lost'], lost['jointly_known']), ('to_noop', 1, 1))
        uncertain = paired_record(dict(base, example_id='y'), result('original', noop=True, unknown=True), old, result('original', unknown=True))
        self.assertEqual((uncertain['ac_lost'], uncertain['not_jointly_known']), (0, 1))
        report = aggregate([lost, uncertain])
        self.assertEqual(report['overall']['prefixes'], 2)
        self.assertEqual(report['overall']['ac_lost'], 1)
        self.assertEqual(report['by_category']['to_noop']['not_jointly_known'], 1)

    def test_linear_ledger_is_additive_not_interventional(self):
        value = margin_decomposition({'noop': -1., 'repair': 1.}, {'noop': .5, 'repair': .1},
            'noop', 'repair', -1.8, .3)
        self.assertAlmostEqual(value['total_margin_change'], 2.4)
        self.assertAlmostEqual(value['noop_coordinate_change'], 2.1)
        self.assertAlmostEqual(value['other_coordinate_change'], .3)
        self.assertAlmostEqual(value['noop_coordinate_change']+value['other_coordinate_change'], value['total_margin_change'])

    def test_nonnoop_changes_do_not_count_as_abstention(self):
        base = dict(example_id='x', problem_id='p', fold=1)
        row = paired_record(base, result('new', regression=True), result('old', ac=True), result('original'))
        self.assertEqual(row['category'], 'nonnoop_change')
        self.assertEqual(row['ac_lost'], 1)
        self.assertEqual(row['regression_introduced'], 1)


if __name__ == '__main__':
    unittest.main()
