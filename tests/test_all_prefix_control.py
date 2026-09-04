from __future__ import annotations

import unittest

from scripts.build_all_prefix_evaluation import phase, transform


class AllPrefixControlTest(unittest.TestCase):
    def test_phase_boundaries(self) -> None:
        self.assertEqual([phase(i, 7) for i in range(1, 7)], [
            "early", "early", "middle", "middle", "last", "last"
        ])
        self.assertEqual(phase(1, 2), "last")

    def test_transform_preserves_original_position_as_metadata(self) -> None:
        row = {
            "example_id": "e",
            "problem_id": "p",
            "user_id": "u",
            "history": [{"position": 1, "code": "a"}, {"position": 2, "code": "b"}],
            "target_position": 3,
            "current_pass_rate": 0.5,
            "current_execution_verdict": "WA",
        }
        result = transform(row)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["history"][0]["position"], 1)
        self.assertEqual(result["trajectory_source_position"], 2)
        self.assertEqual(result["trajectory_phase"], "last")
        self.assertEqual(result["attempts_remaining_to_acceptance"], 1)


if __name__ == "__main__":
    unittest.main()
