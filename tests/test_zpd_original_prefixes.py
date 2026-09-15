import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.build_zpd_original_prefixes import build, split_for_user


class OriginalPrefixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.meta, self.data, self.roster = (self.root / p for p in ("meta", "data", "roster"))
        for path in (self.meta, self.data, self.roster / "p1"):
            path.mkdir(parents=True)

    def make(self, records, missing=()):
        with (self.meta / "p1.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["submission_id", "problem_id", "user_id", "date", "language", "filename_ext", "status"])
            for sid, stamp, lang, status in records:
                writer.writerow([sid, "p1", "u1", stamp, lang, "py", status])
                if sid not in missing:
                    path = self.data / "p1" / lang / f"{sid}.py"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b" x = 1\n\n")
        self.output = self.root / "out"
        return build(self.meta, self.data, self.roster, self.output)

    def read(self, name):
        with (self.output / f"{name}.jsonl").open() as handle:
            return [json.loads(line) for line in handle]

    def test_repeats_post_ac_and_other_language_next_preserved(self):
        result = self.make([("s1", 1, "Python", "Accepted"), ("s2", 2, "Python", "Wrong Answer"),
                            ("s3", 3, "Java", "Wrong Answer"), ("s4", 4, "Python", "Wrong Answer")])
        features, labels = self.read("features"), self.read("labels")
        self.assertEqual(len(features), 2)
        self.assertEqual(len(features[1]["observed_history"]), 4)
        self.assertEqual(labels[0]["next_submission"]["language"], "Java")
        self.assertTrue(labels[1]["right_censored"])
        self.assertEqual(self.read("codes")[0]["code"], " x = 1\n\n")
        self.assertEqual(result["counts"]["primary_eligible_prefixes"], 1)

    def test_missing_past_not_skipped(self):
        result = self.make([("s1", 1, "Java", "Wrong Answer"), ("s2", 2, "Python", "Wrong Answer"),
                            ("s3", 3, "Java", "Wrong Answer")], missing=("s1", "s3"))
        self.assertEqual(self.read("features"), [])
        self.assertEqual(self.read("labels")[0]["next_submission"]["submission_id"], "s3")
        self.assertEqual(result["counts"]["missing_source_prefixes"], 1)
        self.assertEqual(result["counts"]["observed_no_ac_user_problem_groups"], 1)

    def test_ties_excluded_and_no_inferred_next(self):
        self.make([("s1", 1, "Python", "Wrong Answer"), ("s2", 2, "Python", "Wrong Answer"),
                   ("s3", 2, "Python", "Wrong Answer")])
        self.assertEqual(self.read("features"), [])
        self.assertTrue(all(r["label_status"] == "order_ambiguous" for r in self.read("labels")))

    def test_undated_group_unknown(self):
        result = self.make([("s1", "", "Python", "Wrong Answer"), ("s2", 2, "Python", "Wrong Answer")])
        self.assertEqual(result["counts"]["undated_user_problem_groups"], 1)
        self.assertEqual(self.read("features"), [])

    def test_split_stable_and_output_protected(self):
        self.assertEqual(split_for_user("u1"), split_for_user("u1"))
        with self.assertRaises(ValueError):
            build(self.meta, self.data, self.roster, self.meta / "out")


if __name__ == "__main__":
    unittest.main()
