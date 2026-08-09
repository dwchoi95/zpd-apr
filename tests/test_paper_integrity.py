from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"
BIBLIOGRAPHY = ROOT / "paper" / "references.bib"


class PaperIntegrityTest(unittest.TestCase):
    def test_every_reference_is_realized_and_every_citation_is_defined(self) -> None:
        tex = PAPER.read_text(encoding="utf-8")
        bib = BIBLIOGRAPHY.read_text(encoding="utf-8")
        cited = {
            key.strip()
            for group in re.findall(r"\\cite\{([^}]+)\}", tex)
            for key in group.split(",")
        }
        entries = set(re.findall(r"^@\w+\{([^,]+),", bib, flags=re.MULTILINE))
        self.assertGreaterEqual(len(entries), 50)
        self.assertEqual(cited - entries, set(), "undefined citation keys")
        self.assertEqual(entries - cited, set(), "uncited bibliography entries")

    def test_fse_submission_contract_is_present(self) -> None:
        tex = PAPER.read_text(encoding="utf-8")
        self.assertIn(
            r"\documentclass[acmsmall,screen,review,anonymous]{acmart}", tex
        )
        conclusion = tex.index(r"\section{Conclusion}")
        availability = tex.index(r"\label{sec:data-availability}")
        self.assertIn(r"\textbf{Data availability.}", tex[availability:])
        bibliography = tex.index(r"\bibliography{references}")
        self.assertLess(conclusion, availability)
        self.assertLess(availability, bibliography)
        self.assertIn("OpenAI Codex was used interactively", tex)


if __name__ == "__main__":
    unittest.main()
