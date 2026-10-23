import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


class PrepareHistraBenchmarkTests(unittest.TestCase):
    def test_histra_students_are_held_out_and_baselines_align(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            problem = tmp / "histra" / "p00001"
            problem.mkdir(parents=True)
            (problem / "problem.html").write_text("<p>x</p>", encoding="utf-8")
            (problem / "meta.json").write_text('{"time_limit_ms": 2000, "memory_limit_kb": 1024}', encoding="utf-8")
            write_jsonl(problem / "tests.jsonl", [{"input": "1\n", "output": "2\n"}])
            subs = [
                {"sid": "s1", "ts": 1, "verdict": "Wrong Answer", "code": "a"},
                {"sid": "s2", "ts": 2, "verdict": "Wrong Answer", "code": "b"},
                {"sid": "s3", "ts": 3, "verdict": "Accepted", "code": "c"},
            ]
            write_jsonl(problem / "trajectories.jsonl", [{"problem_id": "p00001", "user_id": "u1", "submissions": subs}])
            approaches = tmp / "approaches"
            for method in ("refactory", "brafar", "lsgen"):
                write_jsonl(approaches / f"{method}.jsonl", [{"pid": "p00001", "user": "u1", "was": ["a", "b"], "patch": None, "sec": 1.0}])
            train = [{"problem_id": "p00001", "user_id": "u1"}, {"problem_id": "p00001", "user_id": "u2"}, {"problem_id": "p00009", "user_id": "u1"}]
            write_jsonl(tmp / "train.jsonl", train)
            write_jsonl(tmp / "valid.jsonl", train[:1])

            out = tmp / "out"
            subprocess.run(
                [sys.executable, str(ROOT / "src" / "experiments" / "prepare_histra_benchmark.py"),
                 "--histra-data", str(tmp / "histra"), "--histra-approaches", str(approaches),
                 "--train-answer", str(tmp / "train.jsonl"), "--valid-answer", str(tmp / "valid.jsonl"),
                 "--out", str(out)],
                check=True, capture_output=True,
            )

            kept = [json.loads(l) for l in (out / "datasets" / "train-answer.jsonl").read_text().splitlines()]
            self.assertEqual(kept, train[1:])  # only the held-out student's trajectory on that problem leaves
            self.assertEqual((out / "datasets" / "valid-answer.jsonl").read_text(), "")
            row = json.loads((out / "baselines" / "lsgen.generations.jsonl").read_text())
            self.assertEqual(row["example_id"], "p00001:u1:S3")
            self.assertEqual(row["generated_code"], "b")  # no patch returns the last wrong-answer submission unchanged
            case = json.loads((out / "data" / "p00001" / "testcases.jsonl").read_text())
            self.assertEqual(case, {"case_id": "case_00001", "input": "1\n", "expected_output": "2\n"})


if __name__ == "__main__":
    unittest.main()
