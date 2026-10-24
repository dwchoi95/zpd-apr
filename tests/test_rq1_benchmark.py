import json
import tempfile
import unittest
from pathlib import Path

from src.experiments.codenet.rq1 import build_rq1_benchmark


def _codenet(root: Path) -> None:
    (root / "derived/benchmarks/Project_CodeNet_Python800").mkdir(parents=True)
    (root / "problem_descriptions").mkdir()
    (root / "problem_descriptions/p00001.html").write_text("<p>x</p>", encoding="utf-8")
    (root / "metadata").mkdir()
    (root / "metadata/problem_list.csv").write_text(
        "id,name,dataset,time_limit,memory_limit,rating,tags,complexity\np00001,X,AtCoder,2000,1024,,,\n", encoding="utf-8")
    (root / "metadata/p00001.csv").write_text(
        "submission_id,problem_id,user_id,date,language,original_language,filename_ext,status,cpu_time,memory,code_size,accuracy\n"
        "s1,p00001,u1,10,Python,Python (3.4.3),py,Wrong Answer,1,1,1,\n"
        "s2,p00001,u1,20,Python,Python (3.4.3),py,Accepted,1,1,1,\n"
        "s3,p00001,u2,30,Python,Python (3.4.3),py,Accepted,1,1,1,\n", encoding="utf-8")
    source = root / "data/p00001/Python"
    source.mkdir(parents=True)
    (source / "s1.py").write_text("from fractions import gcd\nprint(fractions.gcd(2, 4))\n", encoding="utf-8")
    (source / "s2.py").write_text("from fractions import gcd\nprint(2)\n", encoding="utf-8")
    (source / "s3.py").write_text("print(3)\n", encoding="utf-8")
    for name, text in (("in/b.txt", "2\n"), ("in/a.txt", "1\n"), ("out/a.txt", "x\n"), ("out/b.txt", "y\n")):
        path = root / "test_cases/CONTEST/A" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class Rq1BenchmarkTest(unittest.TestCase):
    def test_builds_only_the_listed_trajectories_in_the_runner_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _codenet(tmp / "codenet")
            manifest = tmp / "manifest.json"
            manifest.write_text(json.dumps({"tests": {"p00001": "CONTEST/A"}, "trajectories": [["p00001", "u1", ["s1", "s2"]]]}))
            build_rq1_benchmark(tmp / "codenet", tmp / "out", manifest_path=manifest)
            out = tmp / "out/p00001"
            self.assertEqual(json.loads((out / "metadata.json").read_text()), {"time_limit": 2000, "memory_limit": 1024})
            self.assertEqual((out / "description.html").read_text(), "<p>x</p>")
            cases = [json.loads(l) for l in (out / "testcases.jsonl").read_text().splitlines()]
            self.assertEqual([c["input"] for c in cases], ["1\n", "2\n"])  # file-name order
            subs = [json.loads(l) for l in (out / "submissions/u1.jsonl").read_text().splitlines()]
            # Buggy submissions run on current Python; the accepted endpoint stays as submitted.
            self.assertEqual(subs[0]["code"], "from math import gcd\nprint(math.gcd(2, 4))\n")
            self.assertEqual(subs[1]["code"], "from fractions import gcd\nprint(2)\n")
            self.assertEqual([s["verdict"] for s in subs], ["Wrong Answer", "Accepted"])
            self.assertFalse((out / "submissions/u2.jsonl").exists())
            [split] = [json.loads(l) for l in (tmp / "out/splits/test.jsonl").read_text().splitlines()]
            self.assertEqual(split, {"problem_id": "p00001", "user_id": "u1", "relative_path": "p00001/submissions/u1.jsonl",
                                     "first_timestamp": 10, "submission_count": 2, "split": "test"})


if __name__ == "__main__":
    unittest.main()
