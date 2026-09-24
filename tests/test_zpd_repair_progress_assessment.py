"""Synthetic thirteen-method gate tests; no empirical data or file access."""
import copy
import json
import unittest

from scripts import zpd_repair_progress_assessment as gate
from scripts import zpd_repair_feedback_assessment as old
from tests.test_zpd_repair_feedback_assessment import fixture as original_fixture


def fixture():
    c, p, labels = original_fixture()
    for row in p:
        row['choices'].update(CF=row['choices']['structural_C'], shared_H_CF=row['choices']['H'])
    return c, p, labels


class ProgressAssessmentTests(unittest.TestCase):
    def test_exact_original_projection_and_all_thirteen_methods(self):
        c, p, labels = fixture(); report = gate.assess(c, p, labels)
        before = old.assess(c, gate.project_original(p), labels)
        self.assertEqual(report['original_gate'], before['gate'])
        self.assertTrue(report['gate']['passed'])
        self.assertEqual(len(report['methods']), 13)
        for method in old.METHODS:
            self.assertEqual(report['full']['results'][method], before['full']['results'][method])
            self.assertEqual(report['full']['equal_problem'][method], before['full']['equal_problem'][method])
            if method != 'H':
                self.assertEqual(report['primary_transitions'][method], before['primary_transitions'][method])
        self.assertEqual(report['full']['examples'], 15)
        self.assertEqual(report['full']['results']['H']['counts']['unknown'], 5)
        self.assertEqual(report['exclusions'], 0)
        json.dumps(report, allow_nan=False)

    def test_cf_tie_cannot_pass_or_change_original_gates(self):
        c, p, labels = fixture()
        for row in p: row['choices']['CF'] = row['choices']['H']
        report = gate.assess(c, p, labels)
        self.assertTrue(report['original_gate']['passed'])
        self.assertFalse(report['gate']['current_feedback_contribution'])
        self.assertFalse(report['gate']['passed'])

    def test_cf_gain_cannot_rescue_failed_original_gates(self):
        c, p, labels = fixture()
        for row in p: row['choices']['Jm'] = row['choices']['H']
        report = gate.assess(c, p, labels)
        self.assertTrue(report['gate']['current_feedback_contribution'])
        self.assertFalse(report['original_gate']['mechanism_contribution'])
        self.assertFalse(report['gate']['passed'])

    def test_four_vs_three_full_folds_with_global_cf_gain(self):
        for losses in (1, 2):
            c, p, labels = fixture()
            for row in p:
                if row['fold'] < losses and row['example_id'].endswith('-known_nonac'):
                    row['choices'].update(H='bad', CF='ac')
            cf = gate.assess(c, p, labels)['gate']['current_feedback_check']
            with self.subTest(losses=losses):
                self.assertTrue(cf['full_check']['passed'])
                self.assertTrue(cf['known_nonac_check']['passed'])
                self.assertEqual(cf['nonworse_full_folds'], 5-losses)
                self.assertEqual(cf['passed'], losses == 1)

    def test_equal_problem_cf_gate_not_pooled_substitution(self):
        c, p, labels = fixture()
        for row in p:
            if row['fold'] != 0 and row['example_id'].endswith('-known_nonac'):
                row['choices'].update(H='bad', CF='ac')
        template = c[1]; prediction = p[1]
        for i in range(29):
            ident = 'extra-'+str(i); bank = 'bank-'+ident
            extra = dict(copy.deepcopy(template), example_id=ident, user_id='user-'+ident, bank_id=bank)
            c.append(extra)
            p.append(dict(copy.deepcopy(prediction), example_id=ident, user_id='user-'+ident, bank_id=bank))
            for cid in extra['candidate_ids']:
                labels[bank, cid] = dict(labels[template['bank_id'], cid], bank_id=bank)
        cf = gate.assess(c, p, labels)['gate']['current_feedback_check']
        self.assertTrue(cf['full_check']['checks']['pooled_ac'])
        self.assertFalse(cf['full_check']['checks']['equal_problem_ac'])
        self.assertFalse(cf['passed'])

    def test_known_ac_and_regression_protection_against_cf(self):
        for choice in ('bad', 'regression', 'unknown'):
            c, p, labels = fixture(); p[0]['choices']['H'] = choice
            cf = gate.assess(c, p, labels)['gate']['current_feedback_check']
            with self.subTest(choice=choice):
                self.assertFalse(cf['known_ac_check']['passed'])
                self.assertFalse(cf['passed'])

    def test_empty_current_group_is_not_win(self):
        c, p, labels = fixture()
        for row in c:
            lab = labels[row['bank_id'], 'noop']
            if lab['status'] == 'stable': lab['all_ac'] = False
        report = gate.assess(c, p, labels)
        cf = report['gate']['current_feedback_check']
        self.assertFalse(cf['known_ac_check']['evaluable'])
        self.assertFalse(cf['passed'])
        self.assertIsNone(report['current_status_subgroup_folds']['known_ac']['0']['equal_problem'])

    def test_strict_new_method_schema_and_choices(self):
        for mutation in ('missing', 'extra', 'foreign_cf', 'foreign_shared', 'bool_cf', 'extra_field'):
            c, p, labels = fixture()
            if mutation == 'missing': p[0]['choices'].pop('CF')
            elif mutation == 'extra': p[0]['choices']['rescue'] = 'ac'
            elif mutation == 'foreign_cf': p[0]['choices']['CF'] = 'foreign'
            elif mutation == 'foreign_shared': p[0]['choices']['shared_H_CF'] = 'foreign'
            elif mutation == 'bool_cf': p[0]['choices']['CF'] = True
            else: p[0]['label_hint'] = 'forbidden'
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): gate.assess(c, p, labels)

    def test_input_immutability_and_diagnostic_cannot_rescue(self):
        inputs = fixture(); before = copy.deepcopy(inputs)
        gate.assess(*inputs); self.assertEqual(inputs, before)
        for row in inputs[1]:
            row['choices']['H'] = row['choices']['CF']
            row['choices']['shared_H_CF'] = 'ac'
        self.assertFalse(gate.assess(*inputs)['gate']['passed'])
        self.assertFalse(gate.assess(*inputs)['gate']['learned_controls_may_replace_primary'])


if __name__ == '__main__': unittest.main()
