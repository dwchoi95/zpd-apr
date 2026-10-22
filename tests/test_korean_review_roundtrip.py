import re
import unittest
from pathlib import Path

from scripts.strip_korean_review import english

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper" / "main.tex"
HANGUL = re.compile(r"[\uac00-\ud7a3]")


class KoreanReviewRoundTripTest(unittest.TestCase):
    """The English build source must stay recoverable from the Korean working copy."""

    def recovered(self) -> str:
        return english(PAPER.read_text(encoding="utf-8"))

    def test_recovered_source_has_no_korean_and_keeps_the_document(self) -> None:
        source = self.recovered()
        self.assertNotRegex(source, HANGUL)
        self.assertIn(r"\documentclass[10pt,conference]{IEEEtran}", source)
        self.assertIn(r"\begin{document}", source)
        self.assertIn(r"\end{document}", source)
        self.assertIn(r"\section*{Data Availability}", source)

    def test_every_translation_carries_its_english_paragraph(self) -> None:
        lines = PAPER.read_text(encoding="utf-8").split("\n")
        translated = [i for i, line in enumerate(lines)
                      if HANGUL.search(line) and not line.startswith("%")]
        self.assertGreater(len(translated), 50)
        for index in translated:
            self.assertTrue(lines[index + 1].startswith("% "), lines[index][:60])

    def test_checked_in_english_source_matches_the_recovery(self) -> None:
        english_source = ROOT / "paper" / "main.en.tex"
        self.assertTrue(english_source.is_file(), "the recovered English source is not checked in")
        self.assertEqual(english_source.read_text(encoding="utf-8"), self.recovered())

    def test_recovery_is_idempotent(self) -> None:
        once = self.recovered()
        self.assertEqual(english(once), once)

    def test_a_translation_without_its_english_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not followed by a commented paragraph"):
            english("\\section{Introduction}\n한글 문단\n\\noindent next paragraph\n")


if __name__ == "__main__":
    unittest.main()
