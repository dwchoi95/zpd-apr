"""Synthetic support accounting; optimization and scoring are prohibited."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from scripts import audit_zpd_conditional_preservation_support as audit
from scripts.audit_zpd_repair_preservation_cv import supervision
from tests.test_zpd_repair_preservation import fixture


class ConditionalSupportTests(unittest.TestCase):
    def rows(self):
        examples,banks,labels = fixture()
        examples = [replace(e,observation=replace(e.observation,current=replace(e.observation.current,
            verdict='Time Limit Exceeded' if int(e.example_id[1:])%2 else 'Wrong Answer'))) for e in examples]
        with (patch('sklearn.linear_model.LogisticRegression.fit',side_effect=AssertionError('forbidden fitting')),
              patch('scripts.zpd_repair_structure.score_model',side_effect=AssertionError('forbidden scoring'))):
            meta = supervision(examples,banks,labels,'refined_balanced')
            return audit.support_rows(examples,banks,meta['prefixes'])

    def test_mapping_uses_only_nominal_six_categories(self):
        for raw,wanted in [('Accepted','AC'),('Wrong Answer','WA'),('Compile Error','CE'),('Compilation Error','CE'),
            ('Runtime Error','RE'),('Time Limit Exceeded','RESOURCE'),('Memory Limit Exceeded','RESOURCE'),('mystery','OTHER')]:
            self.assertEqual(audit.category(raw),wanted)
        for value in ('',None,True):
            with self.assertRaises(ValueError):audit.category(value)

    def test_pair_mass_direction_and_constant_edited_rows(self):
        rows = self.rows();report = audit.summarize_support(rows);total = report['total']
        self.assertAlmostEqual(total['pair_mass'],1900.)
        self.assertAlmostEqual(total['pair_mass'],total['noop_win_mass']+total['noop_loss_mass']+total['edited_only_mass'])
        self.assertEqual(total['unordered_pairs'],total['noop_win_pairs']+total['noop_loss_pairs']+total['edited_only_pairs'])
        self.assertGreater(total['edited_only_mass'],0.)
        for row in rows:
            if row['current_stratum'] == 'unknown':
                self.assertEqual(row['noop_win_pairs']+row['noop_loss_pairs'],0)
        self.assertGreater(total['noop_win_pairs'],0);self.assertGreater(total['noop_loss_pairs'],0)

    def test_zero_columns_are_not_identified_by_edited_only_pairs(self):
        rows = self.rows();report = audit.summarize_support(rows)
        self.assertEqual(report['category_likelihood_rank'],2)
        self.assertEqual(report['zero_likelihood_columns'],['AC','CE','RE','OTHER'])
        self.assertEqual(set(report['cells']),set(audit.CATEGORIES))
        for cell in report['cells']['CE'].values():self.assertEqual(cell['prefixes'],0)

    def test_noop_opportunity_prefixes_not_mirrored_rows(self):
        rows = self.rows()
        pure_ac = [r for r in rows if int(r['example_id'][1:])%6 == 1]
        self.assertTrue(pure_ac)
        for row in pure_ac:
            self.assertEqual(row['noop_win_pairs'],2)
            self.assertEqual(row['noop_loss_pairs'],0)
        summary = audit.aggregate(pure_ac)
        self.assertEqual(summary['noop_win_prefixes'],len(pure_ac))
        self.assertEqual(summary['noop_win_pairs'],2*len(pure_ac))
        self.assertEqual(summary['users'],len(pure_ac))


if __name__ == '__main__':unittest.main()
