import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.audit_zpd_metadata_alignment import audit


class MetadataAlignmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "archive"
        self.problem = self.archive / "p1"
        self.problem.mkdir(parents=True)
        self.metadata = self.root / "metadata"
        self.metadata.mkdir()
        seq = {"problem_id": "p1", "sequence_id": "q", "user_id": "u1",
               "submission_ids": ["s1", "s3"], "timestamps": [1, 3],
               "verdicts": ["Wrong Answer", "Accepted"]}
        (self.problem / "sequences.jsonl").write_text(json.dumps(seq) + "\n")
        raw = [{"submission_id": key, "verdict": verdict, "lang": "Python",
                "code_tokens": "# literal separator \u2028 preserved"}
               for key, verdict in zip(seq["submission_ids"], seq["verdicts"])]
        (self.problem / "submissions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in raw))

    def metadata_rows(self, rows):
        with (self.metadata / "p1.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["submission_id", "problem_id", "user_id", "date", "status", "language"])
            writer.writerows(rows)

    def run_audit(self):
        return audit(self.archive, self.metadata, self.root / "result")["counts"]

    def test_gap_language_and_unobserved_failure_group(self):
        self.metadata_rows([("s1", "p1", "u1", 1, "Wrong Answer", "Python"),
                            ("s2", "p1", "u1", 2, "Wrong Answer", "C++"),
                            ("s3", "p1", "u1", 3, "Accepted", "Python"),
                            ("s4", "p1", "u2", 1, "Wrong Answer", "Python")])
        counts = self.run_audit()
        self.assertEqual(counts["next_pair_missing_intermediate"], 1)
        self.assertEqual(counts["next_pair_language_switch"], 1)
        self.assertEqual(counts["metadata_python_without_observed_ac_absent_archive_groups"], 1)

    def test_mismatch_and_unknown_not_negative(self):
        self.metadata_rows([("s1", "p1", "u1", "", "", "Python"),
                            ("s3", "p1", "u1", 9, "Wrong Answer", "Python")])
        counts = self.run_audit()
        self.assertEqual(counts["timestamp_unknown"], 1)
        self.assertEqual(counts["timestamp_mismatches"], 1)
        self.assertEqual(counts["verdict_mismatches"], 1)
        self.assertEqual(counts["next_pair_order_unknown"], 1)
        self.assertNotIn("metadata_python_without_observed_ac_groups", counts)

    def test_equal_timestamp_never_infers_order(self):
        self.metadata_rows([("s1", "p1", "u1", 1, "Wrong Answer", "Python"),
                            ("s2", "p1", "u1", 1, "Wrong Answer", "Python"),
                            ("s3", "p1", "u1", 3, "Accepted", "Python")])
        counts = self.run_audit()
        self.assertEqual(counts["next_pair_boundary_ties"], 1)
        self.assertNotIn("next_pair_missing_intermediate", counts)

    def test_missing_metadata_is_unknown(self):
        counts = self.run_audit()
        self.assertEqual(counts["missing_metadata_files"], 1)
        self.assertNotIn("metadata_rows", counts)

    def test_duplicate_ids_fail(self):
        row = ("s1", "p1", "u1", 1, "Wrong Answer", "Python")
        self.metadata_rows([row, row])
        with self.assertRaises(ValueError):
            self.run_audit()

    def test_output_cannot_modify_input(self):
        with self.assertRaises(ValueError):
            audit(self.archive, self.metadata, self.archive / "new")


if __name__ == "__main__":
    unittest.main()
