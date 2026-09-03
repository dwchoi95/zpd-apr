from __future__ import annotations

import unittest

from scripts.export_patch_locality_case import select_case


class PatchLocalityCaseTest(unittest.TestCase):
    def test_selects_largest_ted_gap_under_fixed_display_cap(self) -> None:
        dataset = [
            {"example_id": key, "problem_id": key, "history": [{"position": 1, "verdict": "WA", "pass_rate": 0.5, "code": "x"}]}
            for key in ("a", "b")
        ]
        progress = [
            {"example_id": "a", "repaired": True, "ted_buggy_fixed": 1, "generated_code": "p"},
            {"example_id": "b", "repaired": True, "ted_buggy_fixed": 2, "generated_code": "p"},
        ]
        answer = [
            {"example_id": "a", "repaired": True, "ted_buggy_fixed": 8, "generated_code": "a"},
            {"example_id": "b", "repaired": True, "ted_buggy_fixed": 4, "generated_code": "a"},
        ]
        result = select_case(dataset, progress, answer, maximum_chars=10)
        self.assertEqual(result["example_id"], "a")
        self.assertIn("excluded from every estimate", result["role"])

    def test_selects_case_closest_to_median_gap(self) -> None:
        dataset = [
            {"example_id": key, "problem_id": key, "history": [{"position": 1, "verdict": "WA", "pass_rate": 0.5, "code": "x"}]}
            for key in ("a", "b", "c")
        ]
        progress = [
            {"example_id": key, "repaired": True, "ted_buggy_fixed": 1, "generated_code": "p"}
            for key in ("a", "b", "c")
        ]
        answer = [
            {"example_id": "a", "repaired": True, "ted_buggy_fixed": 1, "generated_code": "a"},
            {"example_id": "b", "repaired": True, "ted_buggy_fixed": 3, "generated_code": "a"},
            {"example_id": "c", "repaired": True, "ted_buggy_fixed": 11, "generated_code": "a"},
        ]
        result = select_case(
            dataset, progress, answer, maximum_chars=10, selection="median"
        )
        self.assertEqual(result["example_id"], "b")
        self.assertEqual(result["target_gap"], 2.0)
        self.assertEqual(result["candidate_count"], 3)


if __name__ == "__main__":
    unittest.main()
