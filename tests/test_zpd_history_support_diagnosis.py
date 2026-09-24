import unittest

from scripts.diagnose_zpd_history_support import classify


class HistorySupportDiagnosisTests(unittest.TestCase):
    def test_partition(self):
        def m(mask, q, s):
            return dict(mask=mask, paired_counts=q, similarities=s)
        q0, q1 = [1, 0, 0, 0], [0, 1, 0, 0]
        s0, s1 = [0., 0.], [0.5, 0.]
        cases = [
            (m([False], [None], [s0]), 'zero_eligible'),
            (m([False, True], [None, q0], [s0, s1]), 'singleton'),
            (m([True, True], [q0, q0], [s0, s1]), 'constant_feedback'),
            (m([True, True], [q0, q1], [s0, s0]), 'constant_similarity'),
            (m([True, True], [q0, q1], [s0, s1]), 'potential_covariance'),
        ]
        for moment, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify(moment), expected)

    def test_eligible_missing_feedback_rejected(self):
        with self.assertRaises(ValueError):
            classify(dict(mask=[True], paired_counts=[None], similarities=[[0., 0.]]))

    def test_malformed_positions_rejected(self):
        with self.assertRaises(ValueError):
            classify(dict(mask=[True], paired_counts=[], similarities=[[0., 0.]]))

    def test_signed_zero_equal_but_nonzero_not_merged(self):
        m = dict(mask=[True, True], paired_counts=[[1, 0, 0, 0], [0, 1, 0, 0]],
                 similarities=[[0., 0.], [-0., 0.]])
        self.assertEqual(classify(m), 'constant_similarity')
        m['similarities'][1][0] = 1e-20
        self.assertEqual(classify(m), 'potential_covariance')


if __name__ == '__main__':
    unittest.main()
