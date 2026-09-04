from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_cross_user_target_control import (
    build,
    evidence_signature,
    token_edit_distance,
)


def row(example: str, user: str, source_code: str, target_code: str, target: str) -> dict:
    return {
        "example_id": example,
        "problem_id": "p1",
        "user_id": user,
        "history": [{"submission_id": f"source-{example}", "position": 4, "code": source_code}],
        "target_submission_id": target,
        "target_position": 5,
        "original_target_position": 8,
        "target_code": target_code,
        "target_verdict": "Wrong Answer",
        "target_execution_verdict": "WA",
        "target_pass_rate": 0.5,
        "target_passed_testcases": ["a"],
        "target_tc_outcomes": {"a": "AC", "b": "WA"},
    }


class CrossUserTargetControlTest(unittest.TestCase):
    def test_matches_exact_evidence_and_nearest_distance(self) -> None:
        rows = [
            row("a", "u1", "aaaa", "aaaaXX", "ta"),
            row("b", "u2", "bbbb", "bbbbX", "tb"),
            row("c", "u3", "cccc", "ccccXXX", "tc"),
        ]

        def distance(before: str, after: str) -> int:
            return abs(len(after) - len(before))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            source.write_text("".join(json.dumps(item) + "\n" for item in rows))
            same, cross = root / "same.jsonl", root / "cross.jsonl"
            result = build(source, same, cross, distance_fn=distance)
            same_rows = [json.loads(line) for line in same.read_text().splitlines()]
            cross_rows = [json.loads(line) for line in cross.read_text().splitlines()]
            self.assertEqual(result["matched_examples"], 3)
            self.assertEqual(result["exact_token_distance_matches"], 0)
            self.assertEqual(result["mean_absolute_token_distance_difference"], 1.0)
            for left, right in zip(same_rows, cross_rows):
                self.assertEqual(left["example_id"], right["example_id"])
                self.assertEqual(left["history"], right["history"])
                self.assertEqual(left["history"][0]["position"], 1)
                self.assertEqual(left["target_position"], 2)
                self.assertNotEqual(left["user_id"], right["matched_target_user_id"])
                self.assertEqual(evidence_signature(left), evidence_signature(right))

    def test_excludes_groups_without_another_user(self) -> None:
        only = row("a", "u1", "a", "aa", "ta")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            source.write_text(json.dumps(only) + "\n")
            result = build(
                source,
                root / "same.jsonl",
                root / "cross.jsonl",
                distance_fn=lambda before, after: abs(len(after) - len(before)),
            )
            self.assertEqual(result["matched_examples"], 0)
            self.assertEqual(result["unmatched_no_cross_user_exact_evidence"], 1)

    def test_token_distance_ignores_layout_and_counts_changes(self) -> None:
        self.assertEqual(token_edit_distance("x=1\n", "x = 1 # same\n"), 0)
        self.assertEqual(token_edit_distance("x=1\n", "x=2\n"), 1)

    def test_distance_caliper_excludes_bad_matches(self) -> None:
        rows = [
            row("a", "u1", "a", "aa", "ta"),
            row("b", "u2", "b", "b" * 20, "tb"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            source.write_text("".join(json.dumps(item) + "\n" for item in rows))
            result = build(
                source,
                root / "same.jsonl",
                root / "cross.jsonl",
                distance_fn=lambda before, after: abs(len(after) - len(before)),
            )
            self.assertEqual(result["matched_examples"], 0)
            self.assertEqual(result["unmatched_distance_caliper"], 2)

    def test_problem_shards_are_disjoint_and_complete(self) -> None:
        rows = [
            dict(row("a", "u1", "a", "aa", "ta"), problem_id="p1"),
            dict(row("b", "u2", "b", "bb", "tb"), problem_id="p1"),
            dict(row("c", "u1", "c", "cc", "tc"), problem_id="p2"),
            dict(row("d", "u2", "d", "dd", "td"), problem_id="p2"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            source.write_text("".join(json.dumps(item) + "\n" for item in rows))
            selected: set[str] = set()
            for shard in range(2):
                same = root / f"same-{shard}.jsonl"
                result = build(
                    source,
                    same,
                    root / f"cross-{shard}.jsonl",
                    shard_count=2,
                    shard_index=shard,
                    distance_fn=lambda before, after: abs(len(after) - len(before)),
                )
                self.assertEqual(result["input_examples"], 4)
                ids = {
                    json.loads(line)["example_id"]
                    for line in same.read_text().splitlines()
                }
                self.assertFalse(selected & ids)
                selected |= ids
            self.assertEqual(len(selected), 4)


if __name__ == "__main__":
    unittest.main()
