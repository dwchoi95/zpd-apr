"""Independent synthetic boundary witnesses; no empirical inputs or fitting."""
import copy
import unittest

from scripts import zpd_repair_feedback_assessment as assessment


def fixture():
    cohort, predictions, labels = [], [], {}
    for fold in range(5):
        for state in ('known_ac', 'known_nonac', 'unknown'):
            ident = f'review-{fold}-{state}'
            bank = 'bank-' + ident
            row = dict(example_id=ident, user_id='user-' + ident, bank_id=bank,
                problem_id=f'problem-{fold}', fold=fold,
                candidate_ids=['noop', 'ac', 'bad', 'unknown'], noop_candidate_id='noop')
            cohort.append(row)
            for candidate in row['candidate_ids']:
                unknown = candidate == 'unknown' or candidate == 'noop' and state == 'unknown'
                labels[bank, candidate] = dict(bank_id=bank, candidate_id=candidate,
                    status='unknown' if unknown else 'stable',
                    gain=None if unknown else 0., loss=None if unknown else 0.,
                    all_ac=None if unknown else candidate == 'ac' or candidate == 'noop' and state == 'known_ac')
            baseline = 'noop' if state == 'known_ac' else 'bad' if state == 'known_nonac' else 'unknown'
            choices = {method: baseline for method in assessment.METHODS}
            choices.update(H='ac' if state == 'known_nonac' else baseline, noop='noop')
            predictions.append(dict({key: row[key] for key in
                ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')}, choices=choices))
    return cohort, predictions, labels


class IndependentAssessmentBoundaryTests(unittest.TestCase):
    def test_four_of_five_passes_but_three_of_five_fails_despite_global_gain(self):
        for losses in (1, 2):
            cohort, predictions, labels = fixture()
            for row in predictions:
                if row['fold'] < losses and row['example_id'].endswith('-known_nonac'):
                    row['choices']['H'] = 'bad'
                    for method in (*assessment.BASELINES, *assessment.CONTROLS):
                        row['choices'][method] = 'ac'
            report = assessment.assess(cohort, predictions, labels)
            gate = report['gate']
            with self.subTest(losses=losses):
                # All pooled/equal-problem and subgroup predicates still pass;
                # only the prospective fold-count boundary differs.
                self.assertTrue(all(cell['passed'] for cell in gate['baseline_checks'].values()))
                self.assertTrue(gate['known_ac_check']['passed'])
                self.assertTrue(gate['known_nonac_check']['passed'])
                self.assertTrue(all(cell['passed'] for cell in gate['mechanism_checks'].values()))
                self.assertEqual(set(gate['nonworse_full_folds'].values()), {5 - losses})
                self.assertEqual(gate['actual_repair_improvement'], losses == 1)
                self.assertEqual(gate['mechanism_contribution'], losses == 1)
                self.assertEqual(gate['passed'], losses == 1)

    def test_unequal_problem_sizes_cannot_replace_equal_problem_gate_with_pooled(self):
        cohort, predictions, labels = fixture()
        for row in predictions:
            if row['fold'] != 0 and row['example_id'].endswith('-known_nonac'):
                row['choices']['H'] = 'bad'
                for method in (*assessment.BASELINES, *assessment.CONTROLS):
                    row['choices'][method] = 'ac'
        template = next(row for row in cohort if row['example_id'] == 'review-0-known_nonac')
        predicted = next(row for row in predictions if row['example_id'] == template['example_id'])
        for index in range(29):
            ident = f'review-extra-{index}'
            bank = 'bank-' + ident
            extra = dict(copy.deepcopy(template), example_id=ident, user_id='user-' + ident, bank_id=bank)
            cohort.append(extra)
            predictions.append(dict(copy.deepcopy(predicted), example_id=ident, user_id='user-' + ident, bank_id=bank))
            for candidate in extra['candidate_ids']:
                labels[bank, candidate] = dict(labels[template['bank_id'], candidate], bank_id=bank)
        report = assessment.assess(cohort, predictions, labels)
        self.assertEqual(report['full']['examples'], 44)
        for control in assessment.BASELINES:
            check = report['gate']['baseline_checks'][control]
            self.assertTrue(check['checks']['pooled_ac'])
            self.assertFalse(check['checks']['equal_problem_ac'])
            self.assertFalse(check['passed'])
        # Independently derived: (31/32 + 4/3)/5 versus (1/32 + 8/3)/5.
        self.assertEqual(report['full']['equal_problem']['H']['ac_lower'],
                         dict(numerator=221, denominator=480, value=221/480))
        self.assertEqual(report['full']['equal_problem']['structural_C']['ac_lower'],
                         dict(numerator=259, denominator=480, value=259/480))
        self.assertFalse(report['gate']['passed'])

    def test_missing_entire_fold_rejected_even_with_consistent_remaining_coverage(self):
        cohort, predictions, labels = fixture()
        cohort = [row for row in cohort if row['fold'] != 4]
        predictions = [row for row in predictions if row['fold'] != 4]
        banks = {row['bank_id'] for row in cohort}
        labels = {key: value for key, value in labels.items() if key[0] in banks}
        self.assertEqual({key for key in labels},
            {(row['bank_id'], candidate) for row in cohort for candidate in row['candidate_ids']})
        with self.assertRaisesRegex(ValueError, 'all five folds'):
            assessment.assess(cohort, predictions, labels)


if __name__ == '__main__':
    unittest.main()
