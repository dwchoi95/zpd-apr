from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"
BIBLIOGRAPHY = ROOT / "paper" / "references.bib"
ARTIFACT = ROOT / "ARTIFACT.md"


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
        availability_heading = tex.index(r"\section{Data and Artifact Availability}")
        availability = tex.index(r"\label{sec:data-availability}")
        bibliography = tex.index(r"\bibliography{references}")
        self.assertLess(conclusion, availability_heading)
        self.assertLess(availability_heading, availability)
        self.assertLess(availability, bibliography)
        self.assertIn("anonymized replication package", tex[availability:])
        self.assertIn(r"\texttt{ARTIFACT.md}", tex[availability:])
        self.assertIn("OpenAI Codex was used interactively", tex)

    def test_every_paper_table_has_an_artifact_mapping(self) -> None:
        tex = PAPER.read_text(encoding="utf-8")
        artifact = ARTIFACT.read_text(encoding="utf-8")
        table_labels = set(re.findall(r"\\label\{(tab:[^}]+)\}", tex))
        self.assertTrue(table_labels)
        missing = {label for label in table_labels if f"`{label}`" not in artifact}
        self.assertEqual(missing, set(), "paper tables missing artifact mappings")

    def test_submission_sources_do_not_expose_local_identity(self) -> None:
        text = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("paper/main.tex", "ARTIFACT.md")
        )
        self.assertIn(r"\author{Anonymous Author(s)}", text)
        for forbidden in (
            "github.com/dwchoi",
            "/home/cdw",
            "/Users/cdw",
            "UbuntuServer",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
