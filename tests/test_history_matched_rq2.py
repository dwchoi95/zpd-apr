import unittest

from scripts.analyze_history_matched_rq2 import matched_ids


class HistoryMatchedRQ2Test(unittest.TestCase):
    def test_requires_distinct_users_and_prior_history(self) -> None:
        base = {
            "problem_id": "p",
            "target_code": "print(1)",
        }
        dataset = [
            base | {"example_id": "a", "user_id": "u1", "history": [{"code": "x"}, {"code": "print(0)"}]},
            base | {"example_id": "b", "user_id": "u2", "history": [{"code": "y"}, {"code": "print(0) # near"}]},
            base | {"example_id": "c", "user_id": "u1", "history": [{"code": "z"}, {"code": "print(0)"}]},
        ]
        evaluation = [
            {"example_id": item, "buggy_verdict": "WA", "buggy_pass_rate": 0.5}
            for item in ("a", "b", "c")
        ]
        selected, audit = matched_ids(dataset, evaluation, similarity=0.5)
        self.assertEqual(selected, {"a", "b", "c"})
        self.assertEqual(audit["matched_pairs"], 2)


if __name__ == "__main__":
    unittest.main()
