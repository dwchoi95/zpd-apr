from __future__ import annotations

import unittest

from scripts.analyze_seen_training_overlap import audit


class SeenTrainingOverlapTest(unittest.TestCase):
    def test_exact_structural_overlap_ignores_formatting(self) -> None:
        training = [{"example_id": "tr", "problem_id": "p", "user_id": "u1", "target_code": "x=1\nprint(x)"}]
        dataset = [{"example_id": "te", "problem_id": "p", "user_id": "u2", "target_code": "print(2)", "history": [{"code": "print(0)"}]}]
        selected = [{"example_id": "te", "problem_id": "p", "selected_source": "Answer", "repaired": True}]
        sources = {"Answer": [{"example_id": "te", "generated_code": "x = 1\nprint(x)"}]}
        result = audit(training, dataset, selected, sources)
        generated = result["selected_generated"]
        self.assertEqual(generated["exact_same_problem_train_target"], 1)
        self.assertEqual(generated["exact_other_user_train_target"], 1)
        self.assertEqual(generated["exact_own_heldout_oracle"], 0)


if __name__ == "__main__":
    unittest.main()
