from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_fair_selection import (
    verify,
    verify_external_split,
    verify_mechanism_ladder,
    verify_problem_crossfit,
)


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

    def test_requires_complete_answer_mechanism_ladder(self) -> None:
        method = {"examples": 10, "pr": 0.8, "rr": 0.7, "ir": 0.75}
        contrast = {
            "paired": [
                {
                    "metric": metric,
                    "examples": 10,
                    "cluster_bootstrap_95ci": [-0.1, 0.1],
                }
                for metric in ("pr", "rr", "ir")
            ]
        }
        value = {
            "answer_3seed_members": ["Answer2027", "Answer2028", "Answer2029"],
            "mixed_target_9choose3": method,
            "answer_9choose3": method,
            "answer_3seed": method,
            "answer_1": method,
            "answer_3seed_minus_answer_1": contrast,
            "answer_9choose3_minus_answer_3seed": contrast,
            "mixed_minus_answer": contrast,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            verify_mechanism_ladder(self.write(root, value))
            del value["answer_3seed"]
            with self.assertRaisesRegex(ValueError, "missing answer_3seed"):
                verify_mechanism_ladder(self.write(root, value))

    def test_rejects_missing_target_contrast_or_mismatched_cohort(self) -> None:
        method = {"examples": 10, "pr": 0.8, "rr": 0.7, "ir": 0.75}
        contrast = {
            "paired": [
                {
                    "metric": metric,
                    "examples": 10,
                    "cluster_bootstrap_95ci": [-0.1, 0.1],
                }
                for metric in ("pr", "rr", "ir")
            ]
        }
        value = {
            "answer_3seed_members": ["Answer2027", "Answer2028", "Answer2029"],
            "mixed_target_9choose3": dict(method),
            "answer_9choose3": dict(method),
            "answer_3seed": dict(method),
            "answer_1": dict(method),
            "answer_3seed_minus_answer_1": contrast,
            "answer_9choose3_minus_answer_3seed": contrast,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "mixed_minus_answer"):
                verify_mechanism_ladder(self.write(root, value))
            value["mixed_minus_answer"] = contrast
            value["answer_1"]["examples"] = 9
            with self.assertRaisesRegex(ValueError, "different examples"):
                verify_mechanism_ladder(self.write(root, value))

    def test_requires_complete_problem_crossfit_audit(self) -> None:
        paired = [
            {"metric": metric, "examples": 997}
            for metric in ("pr", "rr", "ir")
        ]
        fold_sizes = [66, 66, 66, 65, 65]
        value = {
            "folds": 5,
            "test_outcomes_used_for_selection": False,
            "cohort_audit": {
                "validation_examples": 461,
                "test_examples": 997,
                "unique_examples_per_member": True,
                "mixed_answer_validation_examples_identical": True,
                "mixed_answer_test_examples_identical": True,
            },
            "fold_audit": [
                {
                    "fold": fold,
                    "test_problems": count,
                    "validation_problems": 390,
                    "validation_test_problem_overlap": 0,
                }
                for fold, count in enumerate(fold_sizes)
            ],
            "mixed": {"examples": 997, "problems": 328},
            "answer": {"examples": 997, "problems": 328},
            "mixed_minus_answer": {"paired": paired},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            verify_problem_crossfit(self.write(root, value))
            value["fold_audit"][2]["validation_test_problem_overlap"] = 1
            with self.assertRaisesRegex(ValueError, "overlapping"):
                verify_problem_crossfit(self.write(root, value))


if __name__ == "__main__":
    unittest.main()
