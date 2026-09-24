"""Synthetic joint-gate checks; no empirical artifacts, fits or I/O."""
import copy
import json
import unittest

from scripts import zpd_joint_progress_assessment as gate
from scripts import zpd_repair_progress_assessment as progress
from tests.test_zpd_repair_progress_assessment import fixture as prior_fixture


def fixture():
    cohort, predictions, labels = prior_fixture()
    for row in predictions:
        row['choices']['C_joint'] = row['choices']['structural_C']
    return cohort, predictions, labels


class JointAssessmentTests(unittest.TestCase):
    def test_full_inherited_projection_and_fourteen_results(self):
        c, p, labels = fixture()
        before = progress.assess(c, gate.project_progress(p), labels)
        report = gate.assess(c, p, labels)
        self.assertEqual(report['inherited_progress_gate'], before['gate'])
        self.assertEqual(report['original_gate'], before['original_gate'])
        self.assertTrue(report['gate']['passed'])
        self.assertEqual(gate.ARMS, ('H','Jm','HS','U','L','CF','C_joint'))
        self.assertEqual(len(report['methods']), 14)
        for m in progress.METHODS:
            self.assertEqual(report['full']['results'][m], before['full']['results'][m])
            self.assertEqual(report['full']['equal_problem'][m], before['full']['equal_problem'][m])
            if m != 'H':
                self.assertEqual(report['primary_transitions'][m], before['primary_transitions'][m])
        self.assertEqual(report['full']['examples'], 15)
        self.assertEqual(report['full']['results']['C_joint']['counts']['unknown'], 5)
        self.assertEqual(report['exclusions'], 0)
        json.dumps(report, allow_nan=False)

    def test_matched_current_tie_fails_without_changing_inherited_gates(self):
        c, p, labels = fixture()
        for row in p: row['choices']['C_joint'] = row['choices']['H']
        r = gate.assess(c, p, labels)
        self.assertTrue(r['inherited_progress_gate']['passed'])
        self.assertFalse(r['gate']['joint_current_contribution'])
        self.assertFalse(r['gate']['passed'])

    def test_new_gate_cannot_rescue_any_inherited_gate(self):
        for control in ('CF', 'Jm', 'HS', 'structural_C'):
            c, p, labels = fixture()
            for row in p: row['choices'][control] = row['choices']['H']
            r = gate.assess(c, p, labels)
            with self.subTest(control=control):
                self.assertTrue(r['gate']['joint_current_contribution'])
                self.assertFalse(r['inherited_progress_gate']['passed'])
                self.assertFalse(r['gate']['passed'])

    def test_four_vs_three_nonworse_folds(self):
        for losses in (1, 2):
            c, p, labels = fixture()
            for row in p:
                if row['fold'] < losses and row['example_id'].endswith('-known_nonac'):
                    row['choices'].update(H='bad', C_joint='ac')
            check = gate.assess(c, p, labels)['gate']['joint_current_check']
            with self.subTest(losses=losses):
                self.assertTrue(check['full_check']['passed'])
                self.assertTrue(check['known_nonac_check']['passed'])
                self.assertEqual(check['nonworse_full_folds'], 5-losses)
                self.assertEqual(check['passed'], losses == 1)

    def test_equal_problem_is_not_pooled_substitution(self):
        c, p, labels = fixture()
        for row in p:
            if row['fold'] != 0 and row['example_id'].endswith('-known_nonac'):
                row['choices'].update(H='bad', C_joint='ac')
        template, prediction = c[1], p[1]
        for i in range(29):
            ident, bank = 'extra-'+str(i), 'bank-extra-'+str(i)
            extra = dict(copy.deepcopy(template), example_id=ident, user_id='user-'+ident, bank_id=bank)
            c.append(extra)
            p.append(dict(copy.deepcopy(prediction), example_id=ident, user_id='user-'+ident, bank_id=bank))
            for cid in extra['candidate_ids']:
                labels[bank, cid] = dict(labels[template['bank_id'], cid], bank_id=bank)
        check = gate.assess(c, p, labels)['gate']['joint_current_check']
        self.assertTrue(check['full_check']['checks']['pooled_ac'])
        self.assertFalse(check['full_check']['checks']['equal_problem_ac'])
        self.assertFalse(check['passed'])

    def test_known_ac_regression_and_unknown_protection(self):
        for choice in ('bad', 'regression', 'unknown'):
            c, p, labels = fixture(); p[0]['choices']['H'] = choice
            check = gate.assess(c, p, labels)['gate']['joint_current_check']
            with self.subTest(choice=choice):
                self.assertFalse(check['known_ac_check']['passed'])
                self.assertFalse(check['passed'])

    def test_empty_current_group_is_not_win(self):
        c, p, labels = fixture()
        for row in c:
            if labels[row['bank_id'], 'noop']['status'] == 'stable':
                labels[row['bank_id'], 'noop']['all_ac'] = False
        r = gate.assess(c, p, labels)
        self.assertFalse(r['gate']['joint_current_check']['known_ac_check']['evaluable'])
        self.assertFalse(r['gate']['passed'])
        self.assertIsNone(r['current_status_subgroup_folds']['known_ac']['0']['equal_problem'])

    def test_new_method_schema_and_population_are_strict(self):
        for mutation in ('missing', 'extra', 'foreign', 'boolean', 'extra_field', 'drop', 'duplicate'):
            c, p, labels = fixture()
            if mutation == 'missing': p[0]['choices'].pop('C_joint')
            elif mutation == 'extra': p[0]['choices']['rescue'] = 'ac'
            elif mutation == 'foreign': p[0]['choices']['C_joint'] = 'foreign'
            elif mutation == 'boolean': p[0]['choices']['C_joint'] = True
            elif mutation == 'extra_field': p[0]['label_hint'] = 'forbidden'
            elif mutation == 'drop': p.pop()
            else: p.append(copy.deepcopy(p[0]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): gate.assess(c, p, labels)

    def test_input_immutability_and_shared_diagnostic_cannot_rescue(self):
        values = fixture(); before = copy.deepcopy(values)
        gate.assess(*values); self.assertEqual(values, before)
        for row in values[1]:
            row['choices']['H'] = row['choices']['C_joint']
            row['choices']['shared_H_CF'] = 'ac'
        r = gate.assess(*values)
        self.assertFalse(r['gate']['passed'])
        self.assertFalse(r['gate']['learned_controls_may_replace_primary'])


if __name__ == '__main__': unittest.main()
