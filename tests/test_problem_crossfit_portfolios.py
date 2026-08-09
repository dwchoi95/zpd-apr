import unittest

from scripts.analyze_problem_crossfit_portfolios import analyze


def row(example: str, problem: str, repaired: bool, ted: int = 3) -> dict:
    return {
        "example_id": example,
        "problem_id": problem,
        "user_id": f"u-{problem}",
        "buggy_pass_rate": 0.0,
        "current_pass_rate": 0.0,
        "fixed_pass_rate": 1.0 if repaired else 0.25,
        "repaired": repaired,
        "improved": True,
        "ted_buggy_fixed": ted,
        "ted_fixed_oracle": 0,
    }


def candidates(names: list[str], problems: list[str]) -> dict[str, list[dict]]:
    result = {}
    for name_index, name in enumerate(names):
        result[name] = [
            row(
                f"e-{problem}",
                problem,
                repaired=(problem_index + name_index) % 3 == 0,
                ted=2 + name_index,
            )
            for problem_index, problem in enumerate(problems)
        ]
    return result


class ProblemCrossFitTest(unittest.TestCase):
    def test_every_fold_excludes_its_test_problem_identities(self) -> None:
        mixed_names = [
            f"{relation}{seed}"
            for relation in ("Progress", "Strict", "Answer")
            for seed in (2027, 2028, 2029)
        ]
        answer_names = [f"Answer{seed}" for seed in range(2027, 2036)]
        validation_problems = ["t0", "t1", "t2", "t3", "v0", "v1"]
        test_problems = ["t0", "t1", "t2", "t3"]
        result = analyze(
            candidates(mixed_names, validation_problems),
            candidates(mixed_names, test_problems),
            candidates(answer_names, validation_problems),
            candidates(answer_names, test_problems),
            folds=2,
            fold_seed=2027,
            bootstrap_samples=50,
            bootstrap_seed=2027,
        )
        self.assertFalse(result["test_outcomes_used_for_selection"])
        self.assertEqual(result["mixed"]["examples"], 4)
        self.assertEqual(result["answer"]["examples"], 4)
        self.assertTrue(
            all(
                row["validation_test_problem_overlap"] == 0
                for row in result["fold_audit"]
            )
        )
        self.assertEqual(
            set(result["budget"]["mixed_minus_answer"]["per_budget"]),
            {"5", "10", "20", "40", "80", "160"},
        )

    def test_rejects_member_family_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "members differ"):
            analyze(
                {"Progress2027": []},
                {"Progress2028": []},
                {"Answer2027": []},
                {"Answer2027": []},
                folds=2,
                fold_seed=2027,
                bootstrap_samples=10,
                bootstrap_seed=2027,
            )


if __name__ == "__main__":
    unittest.main()
