import unittest

from scripts.split_codeworkout_problems import apply_split


class CodeWorkoutProblemHoldoutTest(unittest.TestCase):
    def test_problem_assignment_is_disjoint_and_deterministic(self) -> None:
        rows = [
            {"problem_id": f"p{problem}", "user_id": f"u{user}", "split": "old"}
            for problem in range(10)
            for user in range(2)
        ]
        first, summary = apply_split(rows, 2027)
        second, _ = apply_split(rows, 2027)
        self.assertEqual(first, second)
        assignment = {}
        for row in first:
            assignment.setdefault(row["problem_id"], set()).add(row["split"])
        self.assertTrue(all(len(splits) == 1 for splits in assignment.values()))
        self.assertEqual(set(summary["problems_by_split"]), {"train", "valid", "test"})
        self.assertEqual(summary["problem_overlap_counts"], {
            "train-valid": 0,
            "train-test": 0,
            "valid-test": 0,
        })
        self.assertEqual(set(summary["students_by_split"]), {"train", "valid", "test"})
        self.assertEqual(
            set(summary["student_overlap_counts"]),
            {"train-valid", "train-test", "valid-test"},
        )


if __name__ == "__main__":
    unittest.main()
