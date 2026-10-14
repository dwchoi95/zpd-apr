import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_paper_budget_table import BUDGETS, expected_claims, expected_series, verify

PAPER = (
    r"\includegraphics{Figures/fse2027-budget-frontier.pdf}"
    "\n"
    r"Figure~\ref{fig:budget} operationalizes that tradeoff. "
    r"At a maximum structural edit budget of 20 AST nodes, the gate returns an accepted repair for 22.0\% "
    r"of inputs against 7.0\% with always-three LSGen, a problem-clustered difference of 15.0 points "
    "[10.00, 20.00]; across the six predeclared budgets the mean difference is 15.0 points [10.00, 20.00]. "
    "LSGen crosses over only at the broadest budget, where it leads by -15.0 points."
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
            lsgen["per_budget"][str(budget)] = {
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

    def script(self, root: Path, series: dict[str, list[float]]) -> Path:
        path = root / "plot.py"
        lines = [f"    assert series['{name}'] == {values}" for name, values in series.items()]
        path.write_text("def check(series, data):\n" + "\n".join(lines) + "\n")
        return path

    def paths(self, root: Path, lsgen: dict, current: dict) -> tuple[Path, Path, Path]:
        paper = root / "main.tex"
        paper.write_text(PAPER)
        lsgen_path = root / "lsgen.json"
        lsgen_path.write_text(json.dumps(lsgen))
        current_path = root / "current.json"
        current_path.write_text(json.dumps(current))
        return paper, lsgen_path, current_path

    def test_claims_are_rendered_from_evidence(self) -> None:
        lsgen, current = self.fixtures()
        claims = expected_claims(lsgen, current)
        self.assertEqual(claims[0], r"accepted repair for 22.0\% of inputs")
        self.assertEqual(claims[2], "difference of 15.0 points [10.00, 20.00]")

    def test_verify_accepts_matching_figure_and_prose(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, lsgen_path, current_path = self.paths(root, lsgen, current)
            script = self.script(root, expected_series(lsgen, current))
            result = verify(paper, script, lsgen_path, current_path)
            self.assertEqual(result["verified_claims"], 5)

    def test_verify_rejects_figure_guard_drift(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, lsgen_path, current_path = self.paths(root, lsgen, current)
            series = expected_series(lsgen, current)
            series["LSGen"][0] = 99.9
            script = self.script(root, series)
            with self.assertRaisesRegex(ValueError, "figure guard values differ"):
                verify(paper, script, lsgen_path, current_path)

    def test_verify_rejects_prose_transcription_drift(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, lsgen_path, current_path = self.paths(root, lsgen, current)
            paper.write_text(PAPER.replace("15.0 points [10.00, 20.00]", "99.0 points [10.00, 20.00]", 1))
            script = self.script(root, expected_series(lsgen, current))
            with self.assertRaisesRegex(ValueError, "differs from evidence"):
                verify(paper, script, lsgen_path, current_path)

    def test_verify_requires_the_figure(self) -> None:
        lsgen, current = self.fixtures()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paper, lsgen_path, current_path = self.paths(root, lsgen, current)
            paper.write_text(PAPER.replace(r"\ref{fig:budget}", "Figure 2"))
            script = self.script(root, expected_series(lsgen, current))
            with self.assertRaisesRegex(ValueError, "include and reference"):
                verify(paper, script, lsgen_path, current_path)


if __name__ == "__main__":
    unittest.main()
