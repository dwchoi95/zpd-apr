import unittest
import numpy as np

from scripts.summarize_zpd_history_selection import metrics


class MetricsTest(unittest.TestCase):
    def test_equal_users_not_rows(self):
        p = np.array([[.5, .5, 0, 0, 0, 0], [.5, .5, 0, 0, 0, 0], [.25, .75, 0, 0, 0, 0]])
        result, _ = metrics([0, 0, 0], p, ['a', 'a', 'b'])
        self.assertAlmostEqual(result['user_equal_nll'], (-np.log(.5) - np.log(.25)) / 2)
        self.assertAlmostEqual(result['user_equal_accuracy'], .5)
        self.assertAlmostEqual(sum(b['user_weight_mass'] for b in result['calibration']), 1)
        self.assertAlmostEqual(result['user_equal_multiclass_brier'], (.5 + 1.125) / 2)

    def test_bad_probabilities(self):
        with self.assertRaisesRegex(ValueError, 'invalid probabilities'):
            metrics([0], np.zeros((1, 6)), ['a'])
