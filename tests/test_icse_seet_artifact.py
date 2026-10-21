import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_icse_seet_submission_artifact import anonymize, sanitize, build
from scripts.verify_icse_seet_artifact import check_hashes, close


class SupplementTest(unittest.TestCase):
    def test_preserves_cluster_estimand_keys_not_participant_ids(self):
        raw = {"user_id": {"clusters": 33}, "rows": [{"user_id": "123", "example_id": "abc", "repaired": True}]}
        self.assertEqual(sanitize(raw), {"user_id": {"clusters": 33}, "rows": [{"repaired": True}]})

    def test_strips_source_payloads_and_private_locations(self):
        raw = {"generated_code": "secret", "history": ["secret"], "path": "/home/person/VSCode/zpd-apr/outputs/result.json"}
        self.assertEqual(sanitize(raw), {"path": "./outputs/result.json"})

    def test_preserves_pair_and_cluster_order(self):
        rows = [{"example_id": str(i), "problem_id": "p" + str(i // 2), "user_id": "private" + str(i), "repaired": bool(i % 2)} for i in range(4)]
        left, right, retention = anonymize(rows, rows, [])
        self.assertEqual(left, right)
        self.assertEqual(left[0]["problem_id"], left[1]["problem_id"])
        self.assertNotEqual(left[1]["problem_id"], left[2]["problem_id"])
        self.assertNotIn("private", json.dumps(left))
        self.assertEqual(retention, [])
        with self.assertRaises(ValueError):
            anonymize(rows, rows[:-1], [])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            anonymize(rows + rows[:1], rows + rows[:1], [])

    def test_refuses_overwrite_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                build(Path(tmp))

    def test_hash_check_detects_change_and_unlisted_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.txt").write_text("kept")
            (root / "manifest.json").write_text(json.dumps({"files": {"data.txt": hashlib.sha256(b"kept").hexdigest()}}))
            self.assertEqual(check_hashes(root), 1)
            (root / "data.txt").write_text("changed")
            with self.assertRaises(AssertionError):
                check_hashes(root)
            (root / "extra.txt").write_text("not manifested")
            with self.assertRaises(AssertionError):
                check_hashes(root)

    def test_numeric_mismatch_is_not_silently_rounded(self):
        close({"ci": [0.2, 0.3]}, {"ci": [0.2, 0.3]})
        with self.assertRaises(AssertionError):
            close({"ci": [0.2, 0.3]}, {"ci": [0.2, 0.31]})


if __name__ == "__main__":
    unittest.main()
