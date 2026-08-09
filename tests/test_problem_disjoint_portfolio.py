import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/analyze_problem_disjoint_portfolio.py"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class ProblemDisjointPortfolioTest(unittest.TestCase):
    def test_writes_composed_rows_and_additional_reference_contrast(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            members = []
            for index in range(3):
                path = root / f"member-{index}.jsonl"
                rows = [
                    {
                        "example_id": "e1",
                        "problem_id": "p1",
                        "user_id": "u1",
                        "buggy_pass_rate": 0.0,
                        "fixed_pass_rate": 1.0 if index == 0 else 0.0,
                        "repaired": index == 0,
                        "ted_buggy_fixed": 1 if index == 0 else None,
                        "ted_fixed_oracle": 0 if index == 0 else None,
                    },
                    {
                        "example_id": "e2",
                        "problem_id": "p2",
                        "user_id": "u2",
                        "buggy_pass_rate": 0.0,
                        "fixed_pass_rate": 0.5 if index == 1 else 0.0,
                        "repaired": False,
                        "ted_buggy_fixed": 2 if index == 1 else None,
                        "ted_fixed_oracle": None,
                    },
                ]
                write_jsonl(path, rows)
                members.append(path)

            stability = root / "stability.json"
            stability.write_text(
                json.dumps(
                    {
                        "selected_problem_disjoint_validation": {
                            "members": ["Answer1", "Answer2", "Answer3"],
                            "validation_problems": 1,
                        },
                        "validation_test_problem_overlap": 1,
                    }
                ),
                encoding="utf-8",
            )
            baseline_rows = [
                {
                    "example_id": "e1",
                    "problem_id": "p1",
                    "user_id": "u1",
                    "buggy_pass_rate": 0.0,
                    "fixed_pass_rate": 1.0,
                    "repaired": True,
                    "improved": True,
                    "ted_buggy_fixed": 1,
                    "ted_fixed_oracle": 0,
                },
                {
                    "example_id": "e2",
                    "problem_id": "p2",
                    "user_id": "u2",
                    "buggy_pass_rate": 0.0,
                    "fixed_pass_rate": 0.0,
                    "repaired": False,
                    "improved": False,
                    "ted_buggy_fixed": None,
                    "ted_fixed_oracle": None,
                },
            ]
            reference = root / "reference.jsonl"
            write_jsonl(reference, baseline_rows)
            output = root / "analysis.json"
            composed = root / "composed.jsonl"
            command = [
                sys.executable,
                str(SCRIPT),
                "--stability",
                str(stability),
            ]
            for index, path in enumerate(members, start=1):
                command.extend(["--member", f"Answer{index}={path}"])
            command.extend(
                [
                    "--full-selection",
                    str(reference),
                    "--answer3",
                    str(reference),
                    "--reference",
                    f"Other={reference}",
                    "--composed-output",
                    str(composed),
                    "--bootstrap-samples",
                    "20",
                    "--output",
                    str(output),
                ]
            )
            subprocess.run(command, check=True, cwd=ROOT, capture_output=True, text=True)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(composed.read_text(encoding="utf-8").splitlines()), 2)
            self.assertIn("Other", result["problem_disjoint_minus_references"])


if __name__ == "__main__":
    unittest.main()
