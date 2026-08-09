from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_fair_selection import verify


def report() -> dict:
    return {
        "selection_fairness_audit": {
            "mixed_candidate_checkpoint_count": 9,
            "answer_candidate_checkpoint_count": 9,
            "mixed_feasible_size_three_portfolios": 84,
            "answer_feasible_size_three_portfolios": 84,
            "candidate_pool_sizes_matched": True,
            "portfolio_search_spaces_matched": True,
        }
    }


class FairSelectionVerifierTest(unittest.TestCase):
    def write(self, root: Path, value: dict) -> Path:
        path = root / "analysis.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_accepts_exact_nine_choose_three_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            verify(self.write(Path(directory), report()))

    def test_rejects_missing_or_mismatched_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "missing"):
                verify(self.write(root, {}))
            value = report()
            value["selection_fairness_audit"][
                "answer_feasible_size_three_portfolios"
            ] = 56
            with self.assertRaisesRegex(ValueError, "expected 84"):
                verify(self.write(root, value))


if __name__ == "__main__":
    unittest.main()
