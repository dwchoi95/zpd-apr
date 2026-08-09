import shutil
import unittest
from pathlib import Path

from scripts.verify_fse2027_anonymity import findings, verify


ROOT = Path(__file__).resolve().parents[1]


class FSE2027AnonymityTest(unittest.TestCase):
    def test_forbidden_identifiers_are_detected(self) -> None:
        result = findings(
            "https://github.com/dwchoi95/zpd-apr /home/cdw/x user@example.org "
            "0000-0002-1825-0097"
        )
        self.assertEqual(
            set(result),
            {"repository account", "local user path", "repository URL", "email address", "ORCID"},
        )

    @unittest.skipUnless(
        shutil.which("pdfinfo") and shutil.which("pdftotext"),
        "Poppler tools are required",
    )
    def test_current_submission_is_anonymous(self) -> None:
        result = verify(
            ROOT / "paper" / "main.pdf",
            [ROOT / "paper" / "main.tex", ROOT / "ARTIFACT.md"],
        )
        self.assertTrue(result["anonymous_author_marker"])
        self.assertEqual(result["forbidden_pattern_matches"], 0)


if __name__ == "__main__":
    unittest.main()
