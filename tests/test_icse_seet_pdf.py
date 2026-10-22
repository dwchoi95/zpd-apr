import shutil
import unittest
from pathlib import Path

from scripts.verify_icse_seet_pdf import HEADINGS, check_pages, check_source, verify


class ICSESEETFormatTest(unittest.TestCase):
    def pages(self, body=10, refs=2):
        return ["\n".join(HEADINGS)] + ["Body text"] * (body - 1) + ["REFERENCES\n[1] Reference"] + ["[2] Reference"] * (refs - 1)

    def test_accepts_ten_plus_two(self):
        result = check_pages(self.pages())
        self.assertEqual((result["body_pages"], result["reference_pages"]), (10, 2))

    def test_rejects_eleven_body_even_within_twelve_total(self):
        with self.assertRaisesRegex(ValueError, "body page"):
            check_pages(self.pages(11, 1))

    def test_rejects_three_reference_pages(self):
        with self.assertRaisesRegex(ValueError, "reference page"):
            check_pages(self.pages(8, 3))

    def test_rejects_body_after_references(self):
        pages = self.pages()
        pages[0] = pages[0].replace("Conclusion", "")
        pages[-1] += "\nVI. CONCLUSION"
        with self.assertRaisesRegex(ValueError, "late body"):
            check_pages(pages)

    def test_rejects_boundary_ambiguity(self):
        pages = self.pages()
        pages[10] = "Body continuation\n" + pages[10]
        with self.assertRaisesRegex(ValueError, "fresh page"):
            check_pages(pages)

    def test_rejects_wrong_class_and_font_hacks(self):
        valid = r"\documentclass[10pt,conference]{IEEEtran}\author{}\bibliographystyle{IEEEtran}"
        check_source(valid)
        for text in (valid.replace("10pt", "9pt"), valid + r"\fontsize{9}{10}", valid + r"\vspace{-1cm}", valid.replace("conference]", "conference,compsoc]"), valid + r"\usepackage{algorithm2e}", valid + r"\begin{algorithm}"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                check_source(text)

    @unittest.skipUnless(all(shutil.which(t) for t in ("pdfinfo", "pdftotext", "pdftohtml", "pdffonts")), "Poppler required")
    def test_current_manuscript(self):
        root = Path(__file__).resolve().parents[1]
        result = verify(root / "paper/main.en.pdf", root / "paper/main.en.tex")
        self.assertEqual(result["title_pt"], 24)
        self.assertEqual(result["body_pt"], 10)


if __name__ == "__main__":
    unittest.main()
