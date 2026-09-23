"""Synthetic accounting checks; no empirical performance claim."""
import copy
import unittest
from unittest.mock import patch

from scripts.diagnose_zpd_repair_risk import diagnose_cohort
from scripts.zpd_repair_fit import load_inputs
from src.repair.pilot_contracts import canonical_hash, source_hash
from tests.test_zpd_repair_pairwise import fixture


class RiskDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.examples, self.banks, self.labels = load_inputs(*fixture())
        self.ex = self.examples[-1]
        self.noop = source_hash(self.ex.observation.current.source)
        self.ac = source_hash(b'x = 1\n')
        self.bad = source_hash(b'x = 2\n')
        rank = {'kind': 'synthetic'}; risk = {'kind': 'synthetic'}
        self.models = {'synthetic': dict(condition='C', rank_model=rank, risk_model=risk,
            rank_model_sha256=canonical_hash(rank), risk_model_sha256=canonical_hash(risk))}

    def diagnose(self, scores, logits):
        with patch('scripts.diagnose_zpd_repair_risk.score_model', return_value=scores), \
             patch('scripts.diagnose_zpd_repair_risk.risk_logits', return_value=logits):
            return diagnose_cohort([self.ex], self.banks, self.labels, self.models)['synthetic']

    def test_prevents_regression_and_recovers_ac(self):
        result = self.diagnose({self.noop: 0, self.ac: 1, self.bad: 2},
                               {self.noop: 5, self.ac: 0, self.bad: 1})
        counts = result['counts']
        self.assertEqual(counts['regressions_prevented'], 1)
        self.assertEqual(counts['ac_gained'], 1)
        self.assertEqual(counts['raw_winner_removed'], 1)
        self.assertEqual(counts['raw_ac_misses'], 1)
        self.assertEqual(counts['filtered_ac_misses'], 0)

    def test_eligible_ac_rank_error_and_noop(self):
        result = self.diagnose({self.noop: 2, self.ac: 1, self.bad: 3},
                               {self.noop: 10, self.ac: 0, self.bad: 1})
        counts = result['counts']
        self.assertEqual(counts['filtered_noop'], 1)
        self.assertEqual(counts['filtered_miss_eligible_ac_ranked_below'], 1)
        self.assertEqual(counts['filtered_miss_all_ac_removed'], 0)

    def test_unknown_change_is_not_counted_as_correctness_loss(self):
        self.labels[self.ex.bank_id, self.bad].update(status='unknown', all_ac=None, gain=None, loss=None)
        labels_before = copy.deepcopy(self.labels)
        result = self.diagnose({self.noop: 0, self.ac: 1, self.bad: 2},
                               {self.noop: 2, self.ac: 0, self.bad: 1})
        counts = result['counts']
        self.assertEqual(counts['changed_with_unknown_outcome'], 1)
        self.assertEqual(counts['raw_unknown'], 1)
        self.assertEqual(counts['ac_gained'], 0)
        self.assertEqual(counts['regressions_prevented'], 0)
        self.assertEqual(self.labels, labels_before)

    def test_filtered_out_ac_is_distinct_from_remaining_ac_rank_error(self):
        # The synthetic first attempt is AC and must always remain eligible.
        # Change its label and the other candidate's label, not the first rule.
        self.labels[self.ex.bank_id, self.ac].update(all_ac=False, gain=0, loss=.5)
        self.labels[self.ex.bank_id, self.bad].update(all_ac=True, gain=.5, loss=0)
        result = self.diagnose({self.noop: 0, self.ac: 1, self.bad: 2},
                               {self.noop: 2, self.ac: 0, self.bad: 1})
        counts = result['counts']
        self.assertEqual(counts['ac_lost'], 1)
        self.assertEqual(counts['regressions_introduced'], 1)
        self.assertEqual(counts['filtered_miss_all_ac_removed'], 1)
        self.assertEqual(counts['filtered_miss_eligible_ac_ranked_below'], 0)
        self.assertEqual(counts['stable_ac_candidates_removed'], 1)

    def test_deterministic_replay_and_bad_model_seal(self):
        scores = {self.noop: 0, self.ac: 1, self.bad: 2}
        logits = {self.noop: 2, self.ac: 0, self.bad: 1}
        self.assertEqual(self.diagnose(scores, logits), self.diagnose(scores, logits))
        self.models['synthetic']['rank_model']['changed'] = True
        with self.assertRaisesRegex(ValueError, 'canonical seal'):
            self.diagnose(scores, logits)

    def test_saved_decision_mismatch_fails_closed(self):
        saved = dict(decisions=[dict(example_id=self.ex.example_id,
            bank_id=self.ex.bank_id, choices={
                'synthetic_raw': self.noop, 'synthetic_filtered': self.ac,
                'noop': self.noop, 'first_attempt': self.ac})])
        with patch('scripts.diagnose_zpd_repair_risk.score_model', return_value={self.noop: 0, self.ac: 1, self.bad: 2}), \
             patch('scripts.diagnose_zpd_repair_risk.risk_logits', return_value={self.noop: 2, self.ac: 0, self.bad: 1}), \
             self.assertRaisesRegex(ValueError, 'replayed choice'):
            diagnose_cohort([self.ex], self.banks, self.labels, self.models, saved)

    def test_unknown_original_remains_a_separate_stratum(self):
        self.labels[self.ex.bank_id, self.noop].update(status='unknown', all_ac=None, gain=None, loss=None)
        result = self.diagnose({self.noop: 0, self.ac: 1, self.bad: 2},
                               {self.noop: 2, self.ac: 0, self.bad: 1})
        self.assertEqual(result['original_status_subgroups']['unknown']['examples'], 1)
        self.assertEqual(result['original_status_subgroups']['known_nonac']['examples'], 0)
        counts = result['counts']
        self.assertEqual(counts['filtered_ac_misses'], counts['filtered_miss_all_ac_removed'] +
                         counts['filtered_miss_eligible_ac_ranked_below'])


if __name__ == '__main__':
    unittest.main()
