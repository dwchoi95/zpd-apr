import unittest

from scripts.analyze_fse2027_robustness import paired_suite_rows


def row(example_id: str, problem_id: str, ted: int) -> dict:
    return {
        "example_id": example_id,
        "problem_id": problem_id,
        "repaired": True,
        "improved": True,
        "fixed_pass_rate": 1.0,
        "ted_buggy_fixed": ted,
        "ted_fixed_oracle": 0,
    }


class PairedTedClusterTest(unittest.TestCase):
    def test_joint_repair_ted_reports_problem_cluster_estimands(self) -> None:
        left = [row("p1:e1", "p1", 2), row("p1:e2", "p1", 2), row("p2:e1", "p2", 8)]
        right = [row("p1:e1", "p1", 4), row("p1:e2", "p1", 4), row("p2:e1", "p2", 6)]
        report = paired_suite_rows(
            left,
            right,
            left_label="left",
            right_label="right",
            samples=200,
            seed=2027,
        )
        paired = report["paired_ted"]
        self.assertEqual(paired["joint_repairs"], 3)
        self.assertEqual(paired["joint_repair_problems"], 2)
        self.assertAlmostEqual(paired["right_minus_left_mean_ted"], 2 / 3)
        self.assertAlmostEqual(paired["right_minus_left_problem_balanced_mean_ted"], 0.0)
        self.assertEqual(len(paired["problem_cluster_bootstrap_95ci"]), 2)
        self.assertEqual(len(paired["problem_bootstrap_95ci"]), 2)


if __name__ == "__main__":
    unittest.main()
