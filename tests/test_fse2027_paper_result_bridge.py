import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_paper_result_bridge import verify


ROOT = Path(__file__).resolve().parents[1]


BRIDGE = """\
\\newcommand{\\ScaleMixedSeenRR}{61.0}
\\newcommand{\\CodeWorkoutProblemMixedRR}{71.0}
\\newcommand{\\PromptCurrentMixedSeenRR}{64.0}
\\newcommand{\\CrossFitMixedSeenRR}{60.0}
\\newcommand{\\VerdictOrderProgressCanonicalSeenRR}{45.0}
"""


class PaperResultBridgeTest(unittest.TestCase):
    def materialize(self, root: Path, bridge: str = BRIDGE) -> tuple[Path, Path, Path]:
        expected = root / "generated.tex"
        checked_in = root / "fse2027-result-bridge.tex"
        paper = root / "main.tex"
        expected.write_text(bridge, encoding="utf-8")
        checked_in.write_text(bridge, encoding="utf-8")
        references = " ".join(
            "\\" + line.split("\\", 2)[2].split("}", 1)[0]
            for line in bridge.splitlines()
        )
        paper.write_text(
            "\\input{fse2027-result-bridge}\n" + references + "\n",
            encoding="utf-8",
        )
        return expected, checked_in, paper

    def test_accepts_identical_consumed_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected, checked_in, paper = self.materialize(Path(directory))
            result = verify(expected, checked_in, paper)
            self.assertTrue(result["byte_identical"])
            self.assertEqual(result["commands"], 5)
            self.assertEqual(result["referenced_commands"], 5)

    def test_rejects_stale_checked_in_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected, checked_in, paper = self.materialize(Path(directory))
            checked_in.write_text(BRIDGE.replace("61.0", "60.0"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs"):
                verify(expected, checked_in, paper)

    def test_rejects_unconsumed_result_family(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            expected, checked_in, paper = self.materialize(Path(directory))
            paper.write_text(
                paper.read_text(encoding="utf-8").replace(
                    "\\PromptCurrentMixedSeenRR", "Prompt omitted"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Prompt"):
                verify(expected, checked_in, paper)

    def test_finalizer_enforces_bridge_audit(self) -> None:
        finalizer = (ROOT / "scripts" / "finalize_fse2027_evidence_remote.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("verify_fse2027_paper_result_bridge.py", finalizer)
        self.assertIn("paper/fse2027-result-bridge.tex", finalizer)
        self.assertIn("fse2027-paper-result-bridge-audit.json", finalizer)


if __name__ == "__main__":
    unittest.main()
