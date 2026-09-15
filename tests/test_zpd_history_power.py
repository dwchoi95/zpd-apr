import unittest
from unittest.mock import patch

import numpy as np

from scripts.zpd_history_power import estimate_train_power, summarize_difference, summaries, user_fold


class HistoryPowerTests(unittest.TestCase):
    def rows(self):
        return [{"example_id": str(i), "user_id": "user"+str(i), "split": "train",
                 "problem_id": "p", "timestamp": i+100, "current_code": "x=2",
                 "current_verdict": "WA", "next_label": "AC",
                 "history": [{"code": "x=1", "verdict": "WA", "timestamp": 1}]}
                for i in range(40)]

    def test_fixed_fold_and_mde(self):
        self.assertEqual(user_fold("abc"), user_fold("abc"))
        out = summarize_difference({"a": 1., "b": 3.}, 100)
        self.assertEqual(out["sample_variance"], 2.)
        self.assertAlmostEqual(out["detectable_nll_difference"], .3962039811599345, places=12)
        self.assertEqual(summarize_difference({"a": 1.}, 10)["status"], "not_evaluable")
        self.assertIsNone(summarize_difference({"a": 1., "b": 3.}, 0)["detectable_nll_difference"])

    def test_matching_retains_raw_verdict(self):
        rows = self.rows()[:2]
        rows[0].update(current_verdict="RESOURCE", matching_current_verdict="TLE")
        rows[1].update(current_verdict="RESOURCE", matching_current_verdict="MLE")
        self.assertEqual([r["current_verdict"] for r in summaries(rows)], ["TLE", "MLE"])

    def test_guard_rejects_unverified_and_heldout(self):
        kwargs = dict(prospective_test_users=10, prospective_matched_test_users=10)
        with self.assertRaises(RuntimeError):
            estimate_train_power(self.rows(), **kwargs)
        rows = self.rows()
        rows[-1]["split"] = "test"
        with self.assertRaisesRegex(ValueError, "train rows only"):
            estimate_train_power(rows, provenance_verified=True, implementation_frozen=True, **kwargs)

    def test_oof_and_fold_donors_train_only(self):
        calls = []
        def fake_fit(train, held, condition, **kwargs):
            self.assertIn(kwargs["contrast"], ("C_H", "U_H"))
            calls.append((train, held, condition))
            self.assertFalse({r["user_id"] for r in train} & {r["user_id"] for r in held})
            return np.full(len(held), .5 if condition == "H" else 1.)
        with patch("scripts.zpd_history_power.fit_fixed", side_effect=fake_fit):
            out = estimate_train_power(self.rows(), prospective_test_users=10,
                                       prospective_matched_test_users=8,
                                       provenance_verified=True, implementation_frozen=True)
        self.assertEqual(out["C_H"]["user_count"], 40)
        self.assertEqual(out["C_H"]["mean_difference"], .5)
        self.assertGreater(out["U_H"]["user_count"], 0)
        for fold in out["folds"]:
            self.assertFalse(set(fold["donor_users"]) & set(fold["held_users"]))
        for train, held, condition in calls:
            if condition == "U":
                self.assertTrue(all(r.get("donor_history") for r in train+held))
        self.assertNotIn("ready", out)


if __name__ == "__main__":
    unittest.main()
