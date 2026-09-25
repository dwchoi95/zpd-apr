import unittest
import numpy as np
from scripts import zpd_bank_topset_objective as objective
from scripts.audit_zpd_bank_topset_run import direct_value_gradient


class DirectContrastAuditTests(unittest.TestCase):
    def test_independent_contrast_matches_objective_and_finite_difference(self):
        rng=np.random.default_rng(20270925)
        banks=(objective.Bank(rng.normal(size=(7,5)),(0,2)),objective.Bank(rng.normal(size=(4,5)),(1,)))
        weights=np.array([700.,1200.]);theta=rng.normal(size=5)
        actual=objective.coefficient_objective(theta,banks,weights)
        value,g,data,penalty=direct_value_gradient(theta,banks,weights)
        self.assertAlmostEqual(value,actual.objective,places=11)
        np.testing.assert_allclose(g,actual.gradient,rtol=1e-12,atol=1e-12)
        for i in range(5):
            v=np.zeros(5);v[i]=1e-6
            numerical=(direct_value_gradient(theta+v,banks,weights)[0]-direct_value_gradient(theta-v,banks,weights)[0])/2e-6
            self.assertAlmostEqual(g[i],numerical,places=6)

    def test_identical_extreme_rows_have_only_ridge_gradient(self):
        bank=objective.Bank(np.full((7,2),1e100),(0,));theta=np.array([.1,-.2])
        value,g,_,_=direct_value_gradient(theta,(bank,),np.array([1900.]))
        np.testing.assert_array_equal(g,theta)
        self.assertTrue(np.isfinite(value))

    def test_empty_rest_and_zero_weight_are_not_negative_examples(self):
        banks=(objective.Bank(np.eye(3),(0,1,2)),objective.Bank(np.eye(3),(0,)))
        theta=np.array([1.,2.,3.])
        value,g,data,penalty=direct_value_gradient(theta,banks,np.array([1900.,0.]))
        self.assertEqual(data,0.);self.assertEqual(value,penalty)
        np.testing.assert_array_equal(g,theta)


if __name__ == '__main__': unittest.main()
