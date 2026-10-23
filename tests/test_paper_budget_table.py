import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_paper_budget_table import BUDGETS, expected_claims, expected_series, verify

PROSE = (
    "Per-budget Seen rates are 10.0/20.0/5.0\\% at TED 5, 11.0/21.0/6.0 at 10, 12.0/22.0/7.0 at 20, "
    "13.0/23.0/8.0 at 40, 14.0/24.0/9.0 at 80, and 15.0/25.0/30.0 at 160 for current-only "
    "Answer-3Seed/Mixed/LSGen. At TED 20, Mixed repairs 22.0\\% of Seen inputs versus LSGen's 7.0\\%, a "
    "15.0-point difference [10.00, 20.00]. Across the six prespecified budgets its mean advantage "
    "over LSGen is 15.0 points [10.00, 20.00]."
)


class PaperBudgetTableTest(unittest.TestCase):
    def fixtures(self) -> tuple[dict, dict]:
        lsgen = {
            "per_budget": {},
            "mean_over_predeclared_budgets": {
                "budget_indexed_unconstrained": {
                    "difference": 0.15,
                    "problem_cluster_95ci": [0.10, 0.20],
                }
            },
        }
        current = {"splits": {"seen": {"budget_frontier": []}}}
        for index, budget in enumerate(BUDGETS):
            last = index == len(BUDGETS) - 1
            lsgen["per_budget"][str(budget)] = {
                "budget_indexed_unconstrained": {"repair_rate": 0.20 + index / 100},
                "lsgen": {"repair_rate": 0.30 if last else 0.05 + index / 100},
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

    def paths(self, root: Path, lsgen: dict, current: dict, prose: str = PROSE):
        paper = root / "main.tex"
        paper.write_text(prose)
        lsgen_path = root / "lsgen.json"
        lsgen_path.write_text(json.dumps(lsgen))
        current_path = root / "current.json"
        current_path.write_text(json.dumps(current))
        return paper, lsgen_path, current_path

    def script(self, root: Path, series: dict[str, list[float]]) -> Path:
        path = root / "plot.py"
        lines = [f"    assert series['{name}'] == {values}" for name, values in series.items()]
        path.write_text("def check(series, data):\n" + "\n".join(lines) + "\n")
        return path

    def test_claims_are_rendered_from_evidence(self) -> None:
        lsgen, current = self.fixtures()
        claims, frontier = expected_claims(lsgen, current)
        self.assertTrue(frontier.startswith("Per-budget Seen rates are 10.0/20.0/5.0"))
        self.assertIn("and 15.0/25.0/30.0 at 160", frontier)
        self.assertTrue(any("At TED 20" in claim for claim in claims))

    def test_verify_accepts_reported_prose_without_a_figure(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, lsgen_path, current_path = self.paths(root, lsgen, current)
            result = verify(paper, self.script(root, expected_series(lsgen, current)), lsgen_path, current_path)
            self.assertEqual(result["verified_claims"], 4)
            self.assertFalse(result["checked_figure_guards"])

    def test_verify_rejects_prose_transcription_drift(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, lsgen_path, current_path = self.paths(
                root, lsgen, current, PROSE.replace("12.0/22.0/7.0 at 20", "12.0/99.0/7.0 at 20")
            )
            with self.assertRaisesRegex(ValueError, "differs from evidence"):
                verify(paper, self.script(root, expected_series(lsgen, current)), lsgen_path, current_path)

    def test_verify_checks_figure_guards_when_the_paper_shows_the_figure(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prose = PROSE + "\n\\includegraphics{Figures/fse2027-budget-frontier.pdf}\n\\ref{fig:budget}"
            paper, lsgen_path, current_path = self.paths(root, lsgen, current, prose)
            series = expected_series(lsgen, current)
            self.assertTrue(verify(paper, self.script(root, series), lsgen_path, current_path)["checked_figure_guards"])
            series["LSGen"][0] = 99.9
            with self.assertRaisesRegex(ValueError, "figure guard values differ"):
                verify(paper, self.script(root, series), lsgen_path, current_path)


if __name__ == "__main__":
    unittest.main()
