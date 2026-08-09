import json
import tempfile
import unittest
from pathlib import Path

from scripts.analyze_normalized_ted_frontier import analyze, ast_nodes


class NormalizedTedFrontierTests(unittest.TestCase):
    def write_rows(self, root: Path, name: str, teds: list[int | None]) -> Path:
        path = root / f"{name}.jsonl"
        rows = []
        for index, ted in enumerate(teds):
            rows.append(
                {
                    "example_id": f"e{index}",
                    "problem_id": f"p{index}",
                    "repaired": ted is not None,
                    "tree_edit_distance": ted,
                }
            )
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        return path

    def test_ast_nodes_and_fixed_portfolio_frontier(self) -> None:
        self.assertEqual(ast_nodes("x = 1\n"), 5)
        self.assertIsNone(ast_nodes("if"))
        dataset = [
            {
                "example_id": "e0",
                "problem_id": "p0",
                "history": [{"code": "x = 1\n"}],
            },
            {
                "example_id": "e1",
                "problem_id": "p1",
                "history": [{"code": "if"}],
            },
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mixed = [
                (f"M{i}", self.write_rows(root, f"m{i}", [1 if i == 0 else None, None]))
                for i in range(3)
            ]
            answer = [
                (f"A{i}", self.write_rows(root, f"a{i}", [2 if i == 0 else None, None]))
                for i in range(3)
            ]
            report = analyze(
                dataset,
                mixed,
                answer,
                [0.2, 0.4],
                bootstrap_samples=20,
                seed=7,
            )
        self.assertEqual(report["examples_parseable_current"], 1)
        self.assertEqual(report["examples_excluded_unparseable_current"], 1)
        self.assertEqual(report["per_budget"]["0.2"]["mixed_rr"], 1.0)
        self.assertEqual(report["per_budget"]["0.2"]["answer_rr"], 0.0)
        self.assertEqual(report["per_budget"]["0.4"]["answer_rr"], 1.0)

    def test_requires_three_complete_member_evaluations(self) -> None:
        dataset = [
            {"example_id": "e0", "problem_id": "p0", "history": [{"code": "x=1"}]}
        ]
        with self.assertRaisesRegex(ValueError, "exactly three"):
            analyze(dataset, [], [], [0.1], bootstrap_samples=1, seed=1)


if __name__ == "__main__":
    unittest.main()
