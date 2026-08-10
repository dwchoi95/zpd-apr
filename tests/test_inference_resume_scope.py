from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.repair.inference import _load_resumable_generations


class InferenceResumeScopeTest(unittest.TestCase):
    def test_accepts_partial_output_from_same_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generations.jsonl"
            self._write(output, [{"example_id": "a"}])
            rows = _load_resumable_generations(output, {"a", "b"})
            self.assertEqual(set(rows), {"a"})

    def test_rejects_output_from_another_split(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generations.jsonl"
            self._write(output, [{"example_id": "seen-a"}])
            with self.assertRaisesRegex(ValueError, "different dataset"):
                _load_resumable_generations(output, {"unseen-a"})

    def test_rejects_duplicate_example_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generations.jsonl"
            self._write(output, [{"example_id": "a"}, {"example_id": "a"}])
            with self.assertRaisesRegex(ValueError, "Duplicate example_id"):
                _load_resumable_generations(output, {"a"})

    @staticmethod
    def _write(path: Path, rows: list[dict[str, str]]) -> None:
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
