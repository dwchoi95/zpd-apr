import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_paper_budget_table import BUDGETS, expected_rows, verify


class PaperBudgetTableTest(unittest.TestCase):
    def fixtures(self) -> tuple[dict, dict]:
        lsgen = {"per_budget": {}}
        current = {"splits": {"seen": {"budget_frontier": []}}}
        for index, budget in enumerate(BUDGETS):
            key = str(budget)
            lsgen["per_budget"][key] = {
                "budget_indexed_unconstrained": {"repair_rate": 0.20 + index / 100},
                "lsgen": {"repair_rate": 0.05 + index / 100},
                "budget_indexed_unconstrained_minus_lsgen": {
                    "rr_difference": 0.15,
                    "problem_cluster_95ci": [0.10, 0.20],
                },
            }
            current["splits"]["seen"]["budget_frontier"].append({
                "budget": budget,
                "current_only_answer_3seed": {"rr": 0.10 + index / 100},
            })
        return lsgen, current

    def test_expected_rows_use_paper_format(self) -> None:
        lsgen, current = self.fixtures()
        rows = expected_rows(lsgen, current)
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            rows[0],
            "5 & 20.0 & 10.0 & 5.0 & +15.0 [10.0, 20.0] " + "\\\\",
        )

    def test_verify_rejects_transcription_drift(self) -> None:
        lsgen, current = self.fixtures()
        rows = expected_rows(lsgen, current)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper = root / "main.tex"
            lsgen_path = root / "lsgen.json"
            current_path = root / "current.json"
            paper.write_text("\n".join(rows))
            lsgen_path.write_text(json.dumps(lsgen))
            current_path.write_text(json.dumps(current))
            self.assertEqual(
                verify(paper, lsgen_path, current_path)["verified_rows"], 6
            )
            paper.write_text("\n".join(rows).replace("+15.0", "+99.0"))
            with self.assertRaisesRegex(ValueError, "differs from evidence"):
                verify(paper, lsgen_path, current_path)

    def test_verify_accepts_tex_math_delimiters(self) -> None:
        lsgen, current = self.fixtures()
        lsgen["per_budget"]["160"]["budget_indexed_unconstrained_minus_lsgen"] = {
            "rr_difference": -0.097,
            "problem_cluster_95ci": [-0.142, -0.054],
        }
        rows = expected_rows(lsgen, current)
        rows[-1] = rows[-1].replace("--9.7 [--14.2, --5.4]", "$-9.7$ [$-14.2$, $-5.4$]")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper = root / "main.tex"
            lsgen_path = root / "lsgen.json"
            current_path = root / "current.json"
            paper.write_text("\n".join(rows))
            lsgen_path.write_text(json.dumps(lsgen))
            current_path.write_text(json.dumps(current))
            self.assertEqual(verify(paper, lsgen_path, current_path)["verified_rows"], 6)


if __name__ == "__main__":
    unittest.main()
