import shutil
import unittest

from scripts.check_fse_page_limit import check
from tests.test_paper_integrity import ROOT


@unittest.skipUnless(shutil.which("pdfinfo") and shutil.which("pdftotext"), "Poppler required")
class FSEPageLimitTest(unittest.TestCase):
    def test_rendered_pdf_obeys_18_plus_4_contract(self) -> None:
        result = check(ROOT / "paper" / "main.pdf")
        self.assertLessEqual(result["body_pages"], 18)
        self.assertGreaterEqual(result["data_availability_pages"], 1)
        self.assertLess(
            result["data_availability_start_page"],
            result["references_start_page"],
        )
        self.assertLessEqual(result["reference_pages"], 4)
        self.assertEqual(result["body_lines_on_reference_page"], 0)


if __name__ == "__main__":
    unittest.main()
