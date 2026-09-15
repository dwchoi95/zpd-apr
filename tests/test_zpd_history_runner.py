"""Split-sealed training-loader regression tests; no real outcome files."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.run_zpd_history_gate import load_training


class TrainingLoaderTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        features = []
        for split in ("train", "valid", "test"):
            features.append({
                "example_id": split, "user_id": "u-" + split,
                "problem_id": "p1", "split": split, "timestamp": 2,
                "current_verdict": "WA", "matching_current_verdict": "Wrong Answer",
                "current_code_id": "current" if split == "train" else "not-loaded",
                "history": [{"code_id": "prior", "verdict": "WA", "timestamp": 1}],
            })
        contents = {
            "features.jsonl": features,
            "codes.jsonl": [{"code_id": "current", "code": "print(2)"},
                            {"code_id": "prior", "code": "print(1)"}],
            "labels-train.jsonl": [{"example_id": "train", "next_label": "AC"}],
        }
        hashes = {}
        for name, rows in contents.items():
            data = "".join(json.dumps(row) + "\n" for row in rows).encode()
            (self.root / name).write_bytes(data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        # These hashes deliberately have no corresponding physical label files.
        hashes.update({"labels-valid.jsonl": "not-present", "labels-test.jsonl": "not-present"})
        self.manifest = {"file_sha256": hashes, "counts": {"train": 1, "valid": 1, "test": 1}}
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))

    def test_train_loader_without_valid_or_test_label_files(self):
        loaded, _ = load_training(self.root)
        self.assertEqual([row["example_id"] for row in loaded], ["train"])
        self.assertEqual(loaded[0]["next_label"], "AC")
        self.assertEqual(loaded[0]["current_code"], "print(2)")
        self.assertFalse((self.root / "labels-test.jsonl").exists())
        self.assertFalse((self.root / "labels-valid.jsonl").exists())

    def test_training_hash_tampering_is_rejected(self):
        with (self.root / "labels-train.jsonl").open("a") as stream:
            stream.write("\n")
        with self.assertRaisesRegex(ValueError, "planning input changed"):
            load_training(self.root)

    def test_training_denominator_is_checked(self):
        self.manifest["counts"]["train"] = 2
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "training label coverage mismatch"):
            load_training(self.root)


if __name__ == "__main__":
    unittest.main()
