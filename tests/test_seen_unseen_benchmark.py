import json
import lzma
import tempfile
import unittest
from pathlib import Path

from src.experiments.codenet.seen_unseen import build_seen_unseen_benchmark
from tests.test_rq1_benchmark import _codenet


class SeenUnseenBenchmarkTest(unittest.TestCase):
    def test_writes_the_listed_trajectories_and_the_split_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _codenet(tmp / "codenet")
            (tmp / "codenet/derived/benchmarks/Project_CodeNet_Python800/p00001").mkdir()
            row = {"user_id": "u2", "problem_id": "p00001", "relative_path": "p00001/submissions/u2.jsonl", "split": "unseen_test"}
            manifest = {
                "splits": {"problem_split": [{"problem_id": "p00001"}], "unseen_test": [row]},
                "summary": {"seed": 2027},
                "submissions": {"p00001/submissions/u2.jsonl": ["s3"]},
            }
            path = tmp / "manifest.json.xz"
            path.write_bytes(lzma.compress(json.dumps(manifest).encode()))
            build_seen_unseen_benchmark(tmp / "codenet", tmp / "out", manifest_path=path)
            out = tmp / "out"
            [record] = [json.loads(l) for l in (out / "p00001/submissions/u2.jsonl").read_text().splitlines()]
            # Seen/Unseen programs are stored as submitted.
            self.assertEqual(record, {"submission_id": "s3", "timestamp": 30, "verdict": "Accepted", "code": "print(3)\n"})
            self.assertFalse((out / "p00001/submissions/u1.jsonl").exists())
            self.assertEqual(json.loads((out / "splits/unseen_test.jsonl").read_text()), row)
            self.assertEqual(json.loads((out / "splits/summary.json").read_text()), {"seed": 2027})
            self.assertTrue((out / "p00001/testcases.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
