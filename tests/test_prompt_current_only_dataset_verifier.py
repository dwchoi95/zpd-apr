import tempfile
import unittest
from pathlib import Path

from scripts.verify_prompt_current_only_datasets import verify_pair


class PromptCurrentOnlyDatasetVerifierTest(unittest.TestCase):
    def write(self, path: Path, row: dict) -> None:
        import json

        path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    def test_accepts_only_last_history_with_reset_position(self) -> None:
        row = {
            "example_id": "e1",
            "problem_id": "p1",
            "target_code": "ok",
            "target_position": 3,
            "history": [
                {"position": 1, "code": "a"},
                {"position": 2, "code": "b"},
            ],
        }
        transformed = dict(row)
        transformed["history"] = [{"position": 1, "code": "b"}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            current = root / "current.jsonl"
            self.write(source, row)
            self.write(current, transformed)
            result = verify_pair("seen", source, current)
            self.assertEqual(result["examples"], 1)
            self.assertEqual(result["positions_reset"], 1)

    def test_rejects_non_history_change(self) -> None:
        row = {
            "example_id": "e1",
            "problem_id": "p1",
            "target_code": "ok",
            "history": [{"position": 2, "code": "b"}],
        }
        transformed = dict(row)
        transformed["target_code"] = "changed"
        transformed["history"] = [{"position": 1, "code": "b"}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            current = root / "current.jsonl"
            self.write(source, row)
            self.write(current, transformed)
            with self.assertRaisesRegex(ValueError, "non-history fields"):
                verify_pair("seen", source, current)
