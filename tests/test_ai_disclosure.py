import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"


class AIDisclosureTest(unittest.TestCase):
    """The manuscript must keep disclosing assisted work and who is answerable for it."""

    def paragraph(self) -> str:
        text = PAPER.read_text(encoding="utf-8")
        match = re.search(r"\\noindent\\textbf\{Research process\.\}(.*?)(?=\n\n|\\subsection|\\section)", text, re.S)
        self.assertIsNotNone(match, "the research-process disclosure is missing")
        return " ".join(match[1].split())

    def test_discloses_the_assistant_and_its_scope(self) -> None:
        disclosure = self.paragraph()
        for required in ("OpenAI Codex", "design", "code", "orchestration", "diagnostics", "manuscript"):
            self.assertIn(required, disclosure)

    def test_states_author_responsibility_and_evidence_provenance(self) -> None:
        disclosure = self.paragraph()
        for required in (
            "under author instructions",
            "we do not claim authors manually ran every job",
            "retained execution records",
        ):
            self.assertIn(required, disclosure)

    def test_records_the_experiment_cutoff(self) -> None:
        disclosure = self.paragraph()
        self.assertIn("cutoff", disclosure)
        self.assertRegex(disclosure, r"21 October 2026")
        self.assertIn("adds no training", disclosure)


if __name__ == "__main__":
    unittest.main()
