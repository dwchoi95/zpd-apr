import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify_paper_budget_table import BUDGETS, expected_rows, verify


class PaperBudgetTableTest(unittest.TestCase):
    def fixtures(self) -> tuple[dict, dict, dict]:
        mixed = {"selected_unconstrained_by_budget": {}}
        answer = {"selected_by_budget": {}}
        per_budget = {}
        for index, budget in enumerate(BUDGETS):
            key = str(budget)
            mixed["selected_unconstrained_by_budget"][key] = {
                "members": ["Answer2027", "Progress2028", "Strict2029"]
            }
            answer["selected_by_budget"][key] = {
                "members": ["Answer2030", "Answer2031", "Answer2032"]
            }
            per_budget[key] = {
                "difference": index / 1000,
                "problem_cluster_95ci": [-0.01, 0.02],
            }
        analysis = {
            "splits": {
                "seen": {
                    "budget_indexed_zpdpatch_minus_answer_9choose3": {
                        "per_budget": per_budget
                    }
                }
            }
        }
        return mixed, answer, analysis

    def test_expected_rows_use_paper_format(self) -> None:
        mixed, answer, analysis = self.fixtures()
        rows = expected_rows(mixed, answer, analysis)
        self.assertEqual(len(rows), 6)
        self.assertEqual(
            rows[0],
            "5 & A27--P28--S29 & A30--A31--A32 & +0.00 [--1.00, 2.00] "
            + "\\\\",
        )

    def test_verify_rejects_transcription_drift(self) -> None:
        mixed, answer, analysis = self.fixtures()
        rows = expected_rows(mixed, answer, analysis)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "paper": root / "main.tex",
                "mixed": root / "mixed.json",
                "answer": root / "answer.json",
                "analysis": root / "analysis.json",
            }
            paths["paper"].write_text("\n".join(rows))
            paths["mixed"].write_text(json.dumps(mixed))
            paths["answer"].write_text(json.dumps(answer))
            paths["analysis"].write_text(json.dumps(analysis))
            audit = verify(
                paths["paper"], paths["mixed"], paths["answer"], paths["analysis"]
            )
            self.assertEqual(audit["verified_rows"], 6)
            paths["paper"].write_text("\n".join(rows).replace("+0.00", "+9.99"))
            with self.assertRaisesRegex(ValueError, "differs from evidence"):
                verify(
                    paths["paper"],
                    paths["mixed"],
                    paths["answer"],
                    paths["analysis"],
                )


if __name__ == "__main__":
    unittest.main()
