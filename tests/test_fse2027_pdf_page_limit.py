import shutil
import unittest
from pathlib import Path

from scripts.verify_fse2027_pdf_page_limit import first_content_line, verify


ROOT = Path(__file__).resolve().parents[1]


class FSE2027PDFPageLimitTest(unittest.TestCase):
    def test_first_content_line_ignores_review_header(self) -> None:
        text = "\n  ZPDPatch: Separating Trajectory Supervision from Checkpoint Diversity\n19\n883   References\n"
        self.assertEqual(first_content_line(text), "References")

    @unittest.skipUnless(
        shutil.which("pdfinfo") and shutil.which("pdftotext"),
        "Poppler tools are required",
    )
    def test_current_paper_respects_fse_boundary(self) -> None:
        result = verify(ROOT / "paper" / "main.pdf")
        self.assertEqual(result["body_last_page"], 18)
        self.assertEqual(result["references_first_page"], 19)
        self.assertLessEqual(result["reference_pages"], 4)


if __name__ == "__main__":
    unittest.main()
