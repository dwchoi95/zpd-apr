import math
import unittest

from scripts.audit_zpd_edit_kind_support import moment_vectors, projected, maxdiff


class KindSupportTests(unittest.TestCase):
    def test_kind_projection_recovers_original_formula(self):
        sims = [((.2, .1, 0., 0.), (0., .1, 0., 0.)),
                ((0., .3, .1, 0.), (.1, 0., 0., 0.))]
        moment = dict(mask=[True, True], weights=[[.5, .5], [1/3, 2/3]],
                      paired_counts=[[0, 1, 1, 0], [0, 2, 0, 0]], current_counts=[1, 0, 0, 1])
        h, jm = moment_vectors(sims, moment)
        old_g, old_r, old_product = [], [], []
        for w in moment['weights']:
            for d in range(2):
                s = [sum(t[d]) for t in sims]
                mean = sum(w[i]*s[i] for i in range(2))
                for state in range(4):
                    delta = [(q[state]-moment['current_counts'][state])/2 for q in moment['paired_counts']]
                    old_g.append(mean*moment['current_counts'][state]/2)
                    old_r.append(sum(w[i]*s[i]*delta[i] for i in range(2)))
                    old_product.append(mean*sum(w[i]*delta[i] for i in range(2)))
        self.assertEqual(len(h), 128)
        self.assertLess(maxdiff(projected(h), [x/math.sqrt(12) for x in old_g+old_r]), 1e-15)
        self.assertLess(maxdiff(projected(jm), [x/math.sqrt(12) for x in old_g+old_product]), 1e-15)

    def test_unavailable_and_singleton_are_retained(self):
        sims = [((.3, 0., 0., 0.), (0., 0., 0., 0.))]
        missing = dict(mask=[False], weights=[[0.], [0.]], paired_counts=[None], current_counts=None)
        self.assertEqual(moment_vectors(sims, missing), ((0.,)*128, (0.,)*128))
        singleton = dict(mask=[True], weights=[[1.], [1.]], paired_counts=[[0, 1, 0, 0]], current_counts=[1, 0, 0, 0])
        h, jm = moment_vectors(sims, singleton)
        self.assertEqual(h, jm)

    def test_constant_feedback_does_not_gain_covariance(self):
        sims = [((.3, 0., 0., 0.), (0., 0., 0., 0.)),
                ((0., .4, 0., 0.), (0., 0., 0., 0.))]
        moment = dict(mask=[True, True], weights=[[.5, .5], [1/3, 2/3]],
                      paired_counts=[[0, 1, 0, 0]]*2, current_counts=[1, 0, 0, 0])
        h, jm = moment_vectors(sims, moment)
        self.assertLessEqual(maxdiff(h, jm), 1e-15)


if __name__ == '__main__':
    unittest.main()
