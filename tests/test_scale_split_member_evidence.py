import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_scale_split_members import verify


class ScaleSplitMemberEvidenceTest(unittest.TestCase):
    def write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def test_requires_each_split_member_with_matching_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mixed_path = root / "mixed.json"
            answer_path = root / "answer.json"
            mixed = {
                "best_unconstrained": {"members": ["Answer2027", "Progress2028", "Strict2029"]},
                "selected_unconstrained_by_budget": {},
            }
            answer = {
                "selected_unrestricted": {"members": ["Answer2027", "Answer2028", "Answer2029"]},
                "selected_by_budget": {},
            }
            self.write_json(mixed_path, mixed)
            self.write_json(answer_path, answer)
            datasets = {}
            members = {"Answer2027", "Answer2028", "Answer2029", "Progress2028", "Strict2029"}
            for split in ("seen", "unseen"):
                dataset = root / f"{split}.jsonl"
                rows = [{"example_id": f"{split}-1"}]
                self.write_jsonl(dataset, rows)
                datasets[split] = dataset
                for member in members:
                    evaluation = root / "eval" / "members" / split / f"{member}.evaluation.jsonl"
                    self.write_jsonl(evaluation, rows)
                    self.write_json(evaluation.with_suffix("").with_suffix(".evaluation.summary.json"), {})

            result = verify(root / "eval", datasets, mixed_path, answer_path)
            self.assertTrue(result["splits"]["seen"]["complete"])
            missing = root / "eval" / "members" / "seen" / "Progress2028.evaluation.jsonl"
            missing.unlink()
            with self.assertRaisesRegex(FileNotFoundError, "Progress2028"):
                verify(root / "eval", datasets, mixed_path, answer_path)


if __name__ == "__main__":
    unittest.main()
