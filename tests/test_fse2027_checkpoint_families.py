from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_checkpoint_families import audit_family


def populate(root: Path, duplicate: bool = False) -> None:
    for relation in ("progress", "strict", "answer"):
        seeds = range(2027, 2036) if relation == "answer" else range(2027, 2030)
        for seed in seeds:
            checkpoint = root / f"seed-{seed}" / relation
            checkpoint.mkdir(parents=True)
            (checkpoint / "training_summary.json").write_text(
                json.dumps(
                    {
                        "dataset_path": f"train-{relation}.jsonl",
                        "source_examples": {"progress": 20, "strict": 15, "answer": 40}[
                            relation
                        ],
                        "effective_batch_size": 16,
                    }
                ),
                encoding="utf-8",
            )
            value = "same" if duplicate else f"{relation}-{seed}"
            (checkpoint / "adapter_model.safetensors").write_text(
                value, encoding="utf-8"
            )


class CheckpointFamilyAuditTest(unittest.TestCase):
    def test_accepts_distinct_matched_nine_checkpoint_families(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            populate(root)
            report = audit_family(
                "test", lambda relation, seed: root / f"seed-{seed}" / relation
            )
        self.assertEqual(report["mixed_candidate_checkpoint_count"], 9)
        self.assertEqual(report["answer_candidate_checkpoint_count"], 9)
        self.assertTrue(report["valid_independent_checkpoint_families"])

    def test_rejects_duplicate_adapter_weights(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            populate(root, duplicate=True)
            with self.assertRaisesRegex(ValueError, "invalid independent"):
                audit_family(
                    "test", lambda relation, seed: root / f"seed-{seed}" / relation
                )


if __name__ == "__main__":
    unittest.main()
