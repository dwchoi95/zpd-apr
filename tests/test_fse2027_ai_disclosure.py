import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"


class FSE2027AIDisclosureTest(unittest.TestCase):
    def test_methods_discloses_research_lifecycle_ai_use(self) -> None:
        text = PAPER.read_text(encoding="utf-8")
        implementation = text.split("\\subsection{Implementation}", 1)[1].split(
            "\\subsection{Ablations}", 1
        )[0]
        normalized = " ".join(implementation.split())
        for required in (
            "OpenAI Codex",
            "propose control and validation-selection",
            "implement dataset builders",
            "orchestrate experiments",
            "develop statistical-analysis scripts",
            "assist manuscript drafting",
            "authors selected the final design and acceptance criteria",
            "reviewed code changes",
            "checked reported values against saved machine-readable outputs",
            "every cited work was checked against a retrievable source",
        ):
            self.assertIn(required, normalized)


if __name__ == "__main__":
    unittest.main()
