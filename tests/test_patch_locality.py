import unittest

from scripts.analyze_patch_locality import locality, paired_locality, resolve_generated_codes


class PatchLocalityTest(unittest.TestCase):
    def test_retention_and_paired_direction(self) -> None:
        source_code = "x = 1\nprint(x)\n"
        close = "x = 2\nprint(x)\n"
        replacement = "print(2)\n"
        self.assertGreater(
            locality(source_code, close)["token_retention"],
            locality(source_code, replacement)["token_retention"],
        )
        base = {
            "example_id": "e",
            "problem_id": "p",
            "repaired": True,
        }
        left = {"e": {**base, "generated_code": close}}
        right = {"e": {**base, "generated_code": replacement}}
        result = paired_locality(
            left,
            right,
            {"e": source_code},
            samples=20,
            seed=2027,
        )
        self.assertGreater(result["metrics"]["token_retention"]["left_minus_right"], 0)

    def test_resolves_composed_selected_source(self) -> None:
        evaluations = {
            "portfolio": {
                "e": {"example_id": "e", "selected_source": "Answer1"},
                "f": {"example_id": "f", "selected_source": "current-fallback"},
            }
        }
        candidates = {
            "Answer1": {"e": {"example_id": "e", "generated_code": "print(1)"}}
        }
        resolve_generated_codes(
            evaluations,
            candidates,
            {"e": "print(0)", "f": "print(2)"},
        )
        self.assertEqual(evaluations["portfolio"]["e"]["generated_code"], "print(1)")
        self.assertEqual(evaluations["portfolio"]["f"]["generated_code"], "print(2)")


if __name__ == "__main__":
    unittest.main()
