"""Analysis-only regressions; no experiment modules or remote actions."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import summarize_zpd_deadline as summary


class DeadlineSummaryTests(unittest.TestCase):
    def test_counts_preserve_unknown_and_denominator(self):
        row = {"examples": 320, "counts": {"stable_ac": 200, "unknown": 16,
                                          "stable_regression": 17}}
        self.assertEqual(summary.metric_nodes({"H": row})[0],
                         {"json_path": "/H", **row})

    def test_readiness_does_not_become_repair_metric(self):
        self.assertEqual(summary.metric_nodes({"actual_fit": True,
                                              "completed_examples": 38398,
                                              "performance_measured": False}), [])

    def test_historical_rates_keep_original_population(self):
        row = summary.metric_nodes({"H": {"metrics": {"examples": 32,
                     "rr_lower_bound": 0.625, "unknown": 1 / 32}}})[0]
        self.assertEqual(row["examples"], 32)
        self.assertEqual(row["counts"], {"rr_lower_bound": 20, "unknown": 1})

    def test_gates_preserved_without_relaxation(self):
        gate = {"passed": False, "required_nonworse_folds": 5,
                "checks": {"all_five_folds": False, "pooled_ac": True}}
        result = summary.original_gates({"development_gate": gate})
        self.assertEqual(result, [{"json_path": "/development_gate", "value": gate}])

    def test_cohorts_are_not_merged(self):
        rows = summary.metric_nodes({str(n): {"H": {"examples": n,
                    "counts": {"stable_ac": 20, "unknown": 1}}} for n in (32, 128)})
        self.assertEqual([r["examples"] for r in rows], [32, 128])

    def test_report_hash_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "report.json"
            report.write_text('{"result": 1}')
            pin = hashlib.sha256(report.read_bytes()).hexdigest()
            (root / "COMPLETE.json").write_text(json.dumps({"files_sha256": {"report.json": pin}}))
            with patch.object(summary, "ROOT", root):
                self.assertTrue(summary.parent_report_binding("report.json"))
                report.write_text('{"result": 2}')
                with self.assertRaisesRegex(AssertionError, "seal drift"):
                    summary.parent_report_binding("report.json")


if __name__ == "__main__":
    unittest.main()
