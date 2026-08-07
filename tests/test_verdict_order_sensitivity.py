import unittest

from scripts.audit_verdict_order_sensitivity import ORDERS, pareto, valid


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


if __name__ == "__main__":
    unittest.main()
