from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.finalize_cross_user_target_control import finalize


class FinalizeCrossUserTargetControlTest(unittest.TestCase):
    def test_joint_token_cap_preserves_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            rows = [
                {
                    "example_id": name,
                    "problem_id": "p",
                    "history": [{"code": "x"}],
                    "target_code": code,
                    "target_token_edit_distance": distance,
                    "matched_target_token_edit_distance": distance,
                }
                for name, code, distance in (("a", "ok", 1), ("b", "too-long", 2))
            ]
            for stem in ("same", "cross"):
                (root / f"{stem}-0.jsonl").write_text(
                    "".join(json.dumps(row) + "\n" for row in rows)
                )
            result = finalize(
                root,
                root / "same-final.jsonl",
                root / "cross-final.jsonl",
                total_tokens=lambda row: 10 if row["example_id"] == "a" else 20,
                maximum_tokens=10,
            )
            self.assertEqual(result["written_examples_per_condition"], 1)
            self.assertEqual(result["overlength_pairs_excluded"], 1)
            self.assertEqual(len((root / "same-final.jsonl").read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
