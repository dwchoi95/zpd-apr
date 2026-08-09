from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_fair_selection import verify, verify_external_split


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

    def test_external_split_claims_are_exactly_reproduced(self) -> None:
        value = {
            "problems_by_split": {"train": 10, "valid": 3, "test": 4},
            "trajectories_by_split": {"train": 605, "valid": 216, "test": 304},
            "students_by_split": {"train": 213, "valid": 150, "test": 161},
            "problem_overlap_counts": {
                "train-valid": 0,
                "train-test": 0,
                "valid-test": 0,
            },
            "student_overlap_counts": {
                "train-valid": 147,
                "train-test": 151,
                "valid-test": 121,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(Path(directory), value)
            verify_external_split(path)
            value["problem_overlap_counts"]["train-test"] = 1
            path = self.write(Path(directory), value)
            with self.assertRaisesRegex(ValueError, "problem_overlap_counts"):
                verify_external_split(path)


if __name__ == "__main__":
    unittest.main()
