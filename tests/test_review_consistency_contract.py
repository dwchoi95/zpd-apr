import json
from pathlib import Path
import tempfile
import unittest

from scripts.compose_answer_seed_control import compose
from scripts.analyze_paired_java_control import preflight


class ReviewContractTest(unittest.TestCase):
    def test_unrestricted_repairs_unparseable_source_but_finite_budget_abstains(self):
        dataset = [{"example_id": "e", "history": [{"code": "if :"}]}]
        candidate = {"example_id": "e", "problem_id": "p", "user_id": "u", "buggy_pass_rate": 0., "fixed_pass_rate": 1., "repaired": True, "ted_buggy_fixed": None, "generated_code": "print(1)"}
        stages = [("Answer2027", [candidate]), ("Answer2028", [candidate]), ("Answer2029", [candidate])]
        unrestricted = compose(dataset, stages)[0]
        self.assertTrue(unrestricted["repaired"])
        self.assertEqual(unrestricted["selected_source"], "Answer2027")
        for budget in (0, 5, 160):
            bounded = compose(dataset, stages, max_ted=budget)[0]
            self.assertFalse(bounded["repaired"])
            self.assertEqual(bounded["selected_source"], "current-fallback")

    def test_java_preflight_rejects_cross_split_student(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for split in ("train", "valid"):
                for relation in ("progress", "answer"):
                    row = {"example_id": split, "problem_id": "p", "user_id": "same-student", "history": [{"code": "return 0;"}], "target_submission_id": relation}
                    (root / f"{split}-{relation}.jsonl").write_text(json.dumps(row) + "\n")
            (root / "test.jsonl").write_text(json.dumps({"user_id": "other", "history": [{"code": "return 0;"}]}) + "\n")
            with self.assertRaises(AssertionError):
                preflight(root)


if __name__ == "__main__":
    unittest.main()
