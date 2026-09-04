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
\\newcommand{\\CurrentOnlyAnswerThreeSeenRR}{72.0}
\\newcommand{\\ExerciseSensitivityLOOMinimum}{3.6}
\\newcommand{\\StochasticThreeSeenRR}{60.0}
\\newcommand{\\SeenHiddenMixedJointRR}{45.0}
\\newcommand{\\SeenOverlapMixedExactRate}{1.0}
\\newcommand{\\SweepTPointEightSeenRR}{63.0}
\\newcommand{\\CheckpointStochasticThreeSeenRR}{64.0}
\\newcommand{\\BaseStochasticThreeSeenRR}{50.0}
\\newcommand{\\DifficultyMatchedSeenRR}{70.0}
\\newcommand{\\CrossUserTargetSameUserSeenRR}{50.0}
\\newcommand{\\AllPrefixSeenRR}{55.0}
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
            self.assertEqual(result["commands"], 16)
            self.assertEqual(result["referenced_commands"], 16)

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

    def test_finalizer_collects_cross_user_control_checkpoints(self) -> None:
        finalizer = (ROOT / "scripts" / "finalize_fse2027_evidence_remote.sh").read_text(
            encoding="utf-8"
        )
        runner = (
            ROOT / "scripts" / "run_fse2027_cross_user_target_control_remote.sh"
        ).read_text(encoding="utf-8")
        checkpoint_suffix = "checkpoints/split-90-10/cross-user-target-control"
        self.assertIn(checkpoint_suffix, finalizer)
        self.assertIn(checkpoint_suffix, runner)


if __name__ == "__main__":
    unittest.main()
