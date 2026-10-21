import shutil
import unittest
from pathlib import Path

from scripts.verify_fse2027_pdf_page_limit import BODY_LAST_PAGE, PAGE_LIMIT, first_content_line, verify


ROOT = Path(__file__).resolve().parents[1]


class FSE2027PDFPageLimitTest(unittest.TestCase):
    def test_first_content_line_ignores_review_header(self) -> None:
        text = "\nFSE ’27, July 12–16, 2027, Shenzhen, China                      Anon.\n10\n883   References\n"
        self.assertEqual(first_content_line(text), "References")

    def test_first_content_line_ignores_running_head(self) -> None:
        text = "\n  Trading Coverage for Locality in Educational Program Repair    FSE ’27\n883 Conclusion\n"
        self.assertEqual(first_content_line(text), "Trading Coverage for Locality in Educational Program Repair")

    @unittest.skipUnless(
        shutil.which("pdfinfo") and shutil.which("pdftotext"),
        "Poppler tools are required",
    )
    def test_current_paper_respects_fse_boundary(self) -> None:
        if r"\documentclass[10pt,conference]{IEEEtran}" in (ROOT / "paper" / "main.tex").read_text():
            self.skipTest("Venue changed to ICSE-SEET; test_icse_seet_pdf enforces its boundary")
        result = verify(ROOT / "paper" / "main.pdf")
        self.assertLessEqual(result["total_pages"], PAGE_LIMIT)
        self.assertLessEqual(result["body_last_page"], BODY_LAST_PAGE)
        self.assertLessEqual(result["references_first_page"], BODY_LAST_PAGE)
        self.assertLessEqual(result["extra_reference_pages"], 2)


if __name__ == "__main__":
    unittest.main()
