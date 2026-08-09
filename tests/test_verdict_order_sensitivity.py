import unittest

from scripts.audit_verdict_order_sensitivity import (
    ORDERS,
    pareto,
    require_all_valid,
    valid,
)


class VerdictOrderSensitivityTest(unittest.TestCase):
    def test_runtime_to_wrong_depends_on_order(self) -> None:
        row = {
            "history": [{"verdict": "Runtime Error"}],
            "target_verdict": "Wrong Answer",
        }
        self.assertTrue(valid(row, "strict", ORDERS["canonical"]))
        self.assertFalse(valid(row, "strict", ORDERS["runtime_before_wrong"]))

    def test_pareto_requires_one_strict_improvement(self) -> None:
        order = ORDERS["canonical"]
        self.assertTrue(pareto({"a": "WA", "b": "RE"}, {"a": "AC", "b": "RE"}, order))
        self.assertFalse(pareto({"a": "WA"}, {"a": "WA"}, order))

    def test_required_order_rejects_any_invalid_label(self) -> None:
        result = {
            "datasets": {
                "train-progress": {
                    "accepted_vs_failure": {"valid": 3, "total": 3}
                }
            }
        }
        require_all_valid(result, "accepted_vs_failure")
        result["datasets"]["train-progress"]["accepted_vs_failure"]["valid"] = 2
        with self.assertRaisesRegex(ValueError, "invalid labels"):
            require_all_valid(result, "accepted_vs_failure")


if __name__ == "__main__":
    unittest.main()
