"""Root's synthetic cross-implementation checks of the independent auditor.

No empirical inputs, solver invocation, or production execution is involved.
"""
import copy
from dataclasses import replace
import unittest

import numpy as np

from scripts import audit_zpd_repair_feedback_cv as auditor
from scripts import audit_zpd_repair_feedback_support as support
from scripts import zpd_repair_feedback_assessment as assessment
from scripts import zpd_repair_feedback_offset as offset
from scripts import zpd_repair_feedback_pairs as pairs
from tests.test_zpd_repair_feedback_audit import raw_case, assessment_fixture


class IndependentAuditReviewTests(unittest.TestCase):
    def test_mixed_language_transition_and_candidate_gating_parity(self):
        _, bank, observed, _, _ = raw_case()
        sources = ('x = 0\n', 'if x < 0:\n print(x)\n', 'if (: bad',
                   'int main(){return 0;}', 'x = [1, 2]\nprint(x[0])\n')
        for count in (1, 2, 3, 5, 9):
            row = copy.deepcopy(observed)
            row['history'] = [dict(code=sources[i % 5], verdict=('WA', 'RE', 'CE', 'AC', 'TLE')[i % 5],
                                   timestamp=i, language='C++' if i % 5 == 3 else 'Python')
                              for i in range(count)]
            row['donor_history'] = [dict(h, code=sources[(i + 1) % 5],
                language='C++' if (i + 1) % 5 == 3 else 'Python') for i, h in enumerate(row['history'])]
            row.update(fold=0, current_source_sha256='0'*64, donor_example_id='donor', donor_user_id='other',
                       observed_source_ids=['e0'] + [f's{i}' for i in range(count)],
                       donor_source_ids=[f'd{i}' for i in range(count)])
            self.assertEqual(set(row), support.OBSERVATION_FIELDS)
            actual_y, actual_m, actual = support.interaction_matrices(row, bank)
            y, m, expected = auditor.independent_interactions(row, bank)
            np.testing.assert_array_equal(actual_y, y)
            np.testing.assert_array_equal(actual_m, m)
            for arm in auditor.ARMS:
                np.testing.assert_allclose(actual[arm], expected[arm], atol=2e-14, rtol=2e-14)

    def test_exact_pair_bytes_for_unequal_users_ties_and_unknowns(self):
        cases = [raw_case(i) for i in range(24)]
        examples = [replace(c[0], user_id=f'user{i//3}') for i, c in enumerate(cases)]
        banks = {e.bank_id: c[1] for e, c in zip(examples, cases)}
        labels = {key: value for c in cases for key, value in c[4].items()}
        random = np.random.default_rng(602)
        blocks = {}
        base = {}
        for i, (e, c) in enumerate(zip(examples, cases)):
            block = c[3]['H']
            blocks[e.bank_id] = pairs.CandidateInteractions(block.candidate_ids,
                random.normal(size=block.matrix.shape)*.01, block.event_values, block.event_masks)
            base[e.bank_id] = {cid: float(random.normal()) for cid in block.candidate_ids}
            if i % 5 == 0:
                for key in labels:
                    if key[0] == e.bank_id and labels[key]['status'] == 'stable':
                        labels[key] = dict(labels[key], all_ac=False)
        produced = pairs.build_pairs(examples, banks, labels, blocks, base)
        reference = auditor.reconstruct_pairs(examples, banks, labels, blocks, base)
        for key in ('matrix', 'y', 'weights', 'base_margin'):
            np.testing.assert_array_equal(getattr(produced, key), reference[key])
        self.assertEqual(produced.metadata['training'], reference['training'])
        self.assertEqual(produced.metadata['pair_candidate_ids'], reference['pair_candidate_ids'])

    def test_scalar_objective_and_all_gradient_coordinates(self):
        random = np.random.default_rng(607)
        x = np.zeros((14, 1296)); x[::2] = random.normal(size=(7, 1296))*.02; x[1::2] = -x[::2]
        y = np.tile(np.array([1, 0], dtype=np.int64), 7)
        w = np.full(14, 1900./14)
        b = np.zeros(14); b[::2] = random.normal(size=7); b[1::2] = -b[::2]
        theta = random.normal(size=1296)*.1
        value, gradient = offset.objective_and_gradient(theta, x, y, w, b)
        reference, independent_gradient, _ = auditor.numerical_reference(theta, x, y, w, b)
        self.assertAlmostEqual(value, reference['objective'], places=10)
        np.testing.assert_allclose(gradient, independent_gradient, atol=1e-10, rtol=1e-10)

    def test_rational_assessment_parity_under_all_method_switches(self):
        random = np.random.default_rng(613)
        for _ in range(25):
            cohort, predictions, labels = assessment_fixture()
            for row in predictions:
                for method in assessment.METHODS:
                    if method != 'noop':
                        row['choices'][method] = str(random.choice(['noop', 'ac', 'bad', 'reg', 'unknown']))
            actual = assessment.assess(cohort, predictions, labels)
            expected = auditor.independent_assessment(cohort, predictions, labels)
            self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
