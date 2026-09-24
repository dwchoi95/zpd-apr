"""Synthetic assessment only; no files or production outcomes are read."""
import copy
import json
import unittest

from scripts import zpd_repair_feedback_assessment as assessment


def fixture():
    cohort = []; predictions = []; labels = {}
    for fold in range(5):
        for status in ('known_ac', 'known_nonac', 'unknown'):
            ident = f'{fold}-{status}'; bank = 'bank-' + ident
            row = dict(example_id=ident, user_id='user-' + ident, bank_id=bank,
                problem_id=f'p{fold}', fold=fold, candidate_ids=['noop', 'bad', 'ac', 'unknown', 'regression'],
                noop_candidate_id='noop')
            cohort.append(row)
            for cid in row['candidate_ids']:
                unknown = cid == 'unknown' or cid == 'noop' and status == 'unknown'
                ac = cid == 'ac' or cid == 'noop' and status == 'known_ac'
                labels[bank, cid] = dict(bank_id=bank, candidate_id=cid,
                    status='unknown' if unknown else 'stable', gain=None if unknown else 0.,
                    loss=None if unknown else .25 if cid == 'regression' else 0.,
                    all_ac=None if unknown else ac)
            primary = 'noop' if status == 'known_ac' else 'ac' if status == 'known_nonac' else 'unknown'
            baseline = 'noop' if status == 'known_ac' else 'bad' if status == 'known_nonac' else 'unknown'
            choices = {method: baseline for method in assessment.METHODS}
            choices.update(H=primary, noop='noop', shared_H_HS=primary, shared_H_Jm=primary)
            predictions.append(dict({key: row[key] for key in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')}, choices=choices))
    return cohort, predictions, labels


class RepairFeedbackAssessmentTests(unittest.TestCase):
    def test_all_fixed_gate_conditions_can_pass_without_discarding_unknowns(self):
        cohort, predictions, labels = fixture()
        report = assessment.assess(cohort, predictions, labels)
        self.assertTrue(report['gate']['passed'])
        self.assertEqual(report['full']['examples'], 15)
        self.assertEqual(report['full']['results']['H']['counts']['unknown'], 5)
        self.assertEqual(report['full']['results']['H']['fractions']['ac_lower'],
                         dict(numerator=2, denominator=3, value=2/3))
        self.assertEqual(report['full']['results']['H']['fractions']['ac_upper']['value'], 1.)
        self.assertEqual(report['full']['results']['H']['fractions']['regression_upper']['value'], 1/3)
        self.assertEqual(report['gate']['nonworse_full_folds']['structural_C'], 5)
        self.assertEqual(report['primary_transitions']['structural_C']['ac_gained'], 5)
        self.assertEqual(report['exclusions'], 0)
        json.dumps(report, allow_nan=False)

    def test_identical_primary_and_baseline_is_not_strict_improvement(self):
        c, p, lab = fixture()
        for row in p:
            row['choices']['H'] = row['choices']['structural_C']
        report = assessment.assess(c, p, lab)
        self.assertFalse(report['gate']['actual_repair_improvement'])
        self.assertFalse(report['gate']['mechanism_contribution'])
        self.assertFalse(report['gate']['passed'])

    def test_better_control_or_shared_theta_diagnostic_never_rescues_primary(self):
        c, p, lab = fixture()
        for row in p:
            row['choices']['H'] = row['choices']['structural_C']
            row['choices']['Jm'] = 'ac'
            row['choices']['shared_H_HS'] = 'ac'
        report = assessment.assess(c, p, lab)
        self.assertFalse(report['gate']['passed'])
        self.assertEqual(report['primary'], 'H')
        self.assertFalse(report['gate']['learned_controls_may_replace_primary'])

    def test_known_ac_protection_alone_cannot_pass_anti_abstention(self):
        c, p, lab = fixture()
        for row in p:
            if row['example_id'].endswith('-known_ac'):
                for method in (*assessment.BASELINES, *assessment.CONTROLS):
                    row['choices'][method] = 'bad'
            elif row['example_id'].endswith('-known_nonac'):
                row['choices']['H'] = 'bad'
        report = assessment.assess(c, p, lab)
        self.assertTrue(all(v['passed'] for v in report['gate']['baseline_checks'].values()))
        self.assertFalse(report['gate']['known_nonac_check']['passed'])
        self.assertFalse(report['gate']['passed'])
        self.assertEqual(report['primary_transitions']['structural_C']['to_noop'], 5)

    def test_known_ac_damage_and_regression_each_fail(self):
        for choice in ('bad', 'regression', 'unknown'):
            c, p, lab = fixture(); p[0]['choices']['H'] = choice
            report = assessment.assess(c, p, lab)
            with self.subTest(choice=choice):
                self.assertFalse(report['gate']['known_ac_check']['passed'])
                self.assertFalse(report['gate']['passed'])

    def test_empty_current_group_is_not_evaluable_or_a_win(self):
        c, p, lab = fixture()
        for row in c:
            current = lab[row['bank_id'], 'noop']
            if current['status'] == 'stable':
                current['all_ac'] = False
        report = assessment.assess(c, p, lab)
        self.assertFalse(report['gate']['known_ac_check']['evaluable'])
        self.assertFalse(report['gate']['passed'])
        self.assertEqual(report['current_status_subgroups']['known_ac']['examples'], 0)
        for group in report['current_status_subgroup_folds']['known_ac'].values():
            self.assertIsNone(group['results']['H']['fractions'])
            self.assertFalse(group['results']['H']['evaluable'])

    def test_extra_or_missing_labels_predictions_and_methods_are_rejected(self):
        for mutation in ('extra_label', 'missing_label', 'missing_prediction', 'duplicate_prediction',
                         'extra_method', 'missing_method', 'foreign_candidate', 'bool_fold', 'cross_problem'):
            c, p, lab = fixture()
            if mutation == 'extra_label': lab['held', 'candidate'] = {}
            elif mutation == 'missing_label': lab.pop(next(iter(lab)))
            elif mutation == 'missing_prediction': p.pop()
            elif mutation == 'duplicate_prediction': p[-1] = copy.deepcopy(p[0])
            elif mutation == 'extra_method': p[0]['choices']['rescue'] = 'ac'
            elif mutation == 'missing_method': p[0]['choices'].pop('HS')
            elif mutation == 'foreign_candidate': p[0]['choices']['H'] = 'new'
            elif mutation == 'bool_fold': p[0]['fold'] = False
            else: c[3]['problem_id'] = c[0]['problem_id']
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                assessment.assess(c, p, lab)

    def test_bad_unknown_fractions_and_noop_evidence_are_rejected(self):
        for mutation in ('unknown_ac', 'nan', 'bool_gain', 'ac_loss', 'noop_loss'):
            c, p, lab = fixture(); bank = c[0]['bank_id']
            if mutation == 'unknown_ac': lab[bank, 'unknown']['all_ac'] = False
            elif mutation == 'nan': lab[bank, 'bad']['gain'] = float('nan')
            elif mutation == 'bool_gain': lab[bank, 'bad']['gain'] = True
            elif mutation == 'ac_loss': lab[bank, 'ac']['loss'] = .1
            else: lab[bank, 'noop'].update(all_ac=False, loss=.1)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                assessment.assess(c, p, lab)

    def test_input_objects_remain_unchanged(self):
        inputs = fixture(); before = copy.deepcopy(inputs)
        assessment.assess(*inputs)
        self.assertEqual(inputs, before)


if __name__ == '__main__':
    unittest.main()
