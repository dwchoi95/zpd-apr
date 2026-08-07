from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script("build_observed_hidden_evaluation.py")
analyzer = load_script("analyze_observed_hidden_evaluation.py")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


class ObservedHiddenEvaluationTest(unittest.TestCase):
    def test_build_hides_feedback_and_partitions_every_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_root = root / "data"
            cases = [
                {"case_id": f"c{i}", "input": str(i), "expected": str(i)}
                for i in range(5)
            ]
            write_jsonl(data_root / "p1" / "testcases.jsonl", cases)
            outcomes = {f"c{i}": "AC" if i else "WA" for i in range(5)}
            dataset = root / "dataset.jsonl"
            write_jsonl(
                dataset,
                [
                    {
                        "example_id": "e1",
                        "problem_id": "p1",
                        "history": [
                            {
                                "code": "print(0)",
                                "tc_outcomes": outcomes,
                                "passed_testcases": ["c1", "c2", "c3", "c4"],
                                "pass_rate": 0.8,
                                "execution_verdict": "WA",
                                "execution_complete": True,
                            }
                        ],
                        "current_tc_outcomes": outcomes,
                        "target_tc_outcomes": {key: "AC" for key in outcomes},
                    }
                ],
            )
            output = root / "observed.jsonl"
            manifest = root / "manifest.jsonl"
            summary = builder.build(
                data_root,
                dataset,
                output,
                root / "observed-root",
                root / "hidden-root",
                manifest,
                seed=2027,
            )
            partition = builder.read_jsonl(manifest)[0]
            observed = set(partition["observed_case_ids"])
            hidden = set(partition["hidden_case_ids"])
            self.assertFalse(observed & hidden)
            self.assertEqual(observed | hidden, {f"c{i}" for i in range(5)})
            self.assertEqual((len(observed), len(hidden)), (3, 2))
            row = builder.read_jsonl(output)[0]
            shown = row["history"][0]
            self.assertEqual(set(shown["tc_outcomes"]), observed)
            self.assertFalse(shown["execution_complete"])
            self.assertEqual(
                shown["verdict"],
                builder.DISPLAY_VERDICT[shown["execution_verdict"]],
            )
            self.assertTrue(summary["observed_feedback_only"])

    def test_analysis_requires_observed_and_hidden_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "selected.jsonl"
            hidden_a = root / "a.jsonl"
            hidden_b = root / "b.jsonl"
            write_jsonl(
                selected,
                [
                    {
                        "example_id": "e1",
                        "problem_id": "p1",
                        "selected_source": "A",
                        "repaired": True,
                    },
                    {
                        "example_id": "e2",
                        "problem_id": "p1",
                        "selected_source": "B",
                        "repaired": True,
                    },
                    {
                        "example_id": "e3",
                        "problem_id": "p2",
                        "selected_source": "current-fallback",
                        "repaired": False,
                    },
                ],
            )
            write_jsonl(
                hidden_a,
                [
                    {"example_id": "e1", "repaired": True},
                    {"example_id": "e2", "repaired": False},
                    {"example_id": "e3", "repaired": False},
                ],
            )
            write_jsonl(
                hidden_b,
                [
                    {"example_id": "e1", "repaired": False},
                    {"example_id": "e2", "repaired": False},
                    {"example_id": "e3", "repaired": False},
                ],
            )
            rows = analyzer.method_rows(selected, {"A": hidden_a, "B": hidden_b})
            summary = analyzer.summarize(rows)
            self.assertEqual(summary["observed_repairs"], 2)
            self.assertEqual(summary["hidden_repairs"], 1)
            self.assertEqual(summary["joint_repairs"], 1)
            self.assertEqual(summary["hidden_confirmation_given_observed"], 0.5)
            self.assertEqual(len(summary["joint_repair_rate_wilson_95_ci"]), 2)


if __name__ == "__main__":
    unittest.main()
