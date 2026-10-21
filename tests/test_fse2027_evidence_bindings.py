import json
import re
import unittest
from pathlib import Path

from scripts.build_fse2027_evidence_bindings import CURATED, build, definitions, expand

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "paper" / "fse2027-result-bridge.tex"
PAPER = ROOT / "paper" / "main.tex"
BINDINGS = ROOT / "paper" / "main.evidence-bindings.json"
RESERVED = {
    "tool": r"\textsc{ZPDPatch}",
    "progress": r"\textsc{Progress}",
    "strict": r"\textsc{Strict}",
    "answer": r"\textsc{Answer}",
}


class EvidenceBindingsTest(unittest.TestCase):
    def test_checked_in_bindings_are_reproducible(self) -> None:
        payload, problems = build(BRIDGE, PAPER)
        self.assertEqual(problems, [])
        self.assertEqual(len(payload["bindings"]), len(CURATED))
        self.assertEqual(payload, json.loads(BINDINGS.read_text()))

    def test_every_binding_expands_to_manuscript_text(self) -> None:
        """The same expansion the verifier performs must land verbatim in the paper."""
        defs = {**definitions(BRIDGE), **RESERVED}
        paper_text = PAPER.read_text()
        rows = json.loads(BINDINGS.read_text())["bindings"]
        for row in rows:
            names = set(re.findall(r"\\([A-Za-z]+)\b", row["template"])) & defs.keys()
            self.assertEqual(names, set(row["commands"]), row["template"])
            self.assertIn(expand(row["template"], defs), paper_text)

    def test_value_drift_is_rejected(self) -> None:
        drifted = ROOT / "paper" / ".drifted-bridge.tex"
        drifted.write_text(
            BRIDGE.read_text().replace(
                r"\newcommand{\CurrentOnlyAnswerThreeSeenRR}{72.0}",
                r"\newcommand{\CurrentOnlyAnswerThreeSeenRR}{99.9}",
            )
        )
        try:
            _, problems = build(drifted, PAPER)
        finally:
            drifted.unlink()
        self.assertTrue(
            any("CurrentOnlyAnswerThreeSeenRR=99.9" in problem for problem in problems),
            problems,
        )

    def test_moved_clause_is_rejected(self) -> None:
        moved = ROOT / "paper" / ".moved-main.tex"
        moved.write_text(
            PAPER.read_text().replace("at 72.0\\% Seen and 81.2\\% Unseen.", "at these two split rates.")
        )
        try:
            _, problems = build(BRIDGE, moved)
        finally:
            moved.unlink()
        self.assertTrue(any("literal snippet occurs 0 times" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
