import unittest

from scripts.select_problem_disjoint_fair_pools import select_disjoint


def row(problem: str, repaired: bool) -> dict:
    return {
        "example_id": problem,
        "problem_id": problem,
        "buggy_pass_rate": 0.0,
        "fixed_pass_rate": 1.0 if repaired else 0.0,
        "repaired": repaired,
        "improved": repaired,
        "ted_buggy_fixed": 1 if repaired else None,
    }


class ProblemDisjointFairPoolsTest(unittest.TestCase):
    def test_excludes_test_problems_for_both_matched_pools(self) -> None:
        mixed = {}
        relations = {}
        for relation in ("Answer", "Progress", "Strict"):
            for seed in range(3):
                name = f"{relation}{seed}"
                mixed[name] = [row("keep", seed == 0), row("drop", True)]
                relations[name] = relation
        answer = {
            f"Answer{seed}": [row("keep", seed < 3), row("drop", True)]
            for seed in range(9)
        }
        result = select_disjoint(mixed, relations, answer, [row("drop", False)])
        self.assertEqual(result["validation_problems"], 1)
        self.assertEqual(result["validation_test_problem_overlap"], 0)
        self.assertEqual(result["mixed"]["best_unconstrained"]["score"]["examples"], 1)
        self.assertEqual(result["answer"]["selected_unrestricted"]["score"]["examples"], 1)


if __name__ == "__main__":
    unittest.main()
