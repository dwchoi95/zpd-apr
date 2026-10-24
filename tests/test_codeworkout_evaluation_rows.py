import tempfile
import unittest
from pathlib import Path

from src.experiments.collect_codeworkout_evaluation import collect
from src.experiments.prepare_codeworkout_evaluation import prepare


class CodeWorkoutEvaluationRowsTest(unittest.TestCase):
    def test_rows_carry_generated_code_and_java_retention_but_not_expected_outputs(self) -> None:
        dataset = [{
            "example_id": "cw013:u1:S2",
            "problem_id": "cw013",
            "user_id": "u1",
            "history": [{"code": "int x = 1;\nreturn x;", "tc_outcomes": {"case_001": "WA"}, "pass_rate": 0.0}],
        }]
        generations = [{"example_id": "cw013:u1:S2", "generated_code": "int x = 2;\nreturn x;"}]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepare(dataset, generations, {13: [("caughtSpeeding(60, false)", "0")]}, root / "sources")
            manifest = [__import__("json").loads(l) for l in (root / "manifest.jsonl").read_text().splitlines()]
            (root / "status").mkdir()
            (root / "status" / f"{manifest[0]['slug']}.txt").write_text("ok\n__ZPD_CASE_1__0\n")
            [row], _summary = collect(manifest, root / "status")
        self.assertEqual(row["generated_code"], "int x = 2;\nreturn x;")
        self.assertEqual((row["token_retention"], row["line_retention"]), (7 / 8, 0.5))
        self.assertNotIn("expected", row)
        self.assertTrue(row["repaired"])


if __name__ == "__main__":
    unittest.main()
