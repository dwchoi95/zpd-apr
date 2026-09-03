from __future__ import annotations

import json
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.repair.evaluate import evaluate_generations


class _FakeRunner:
    slow_release = threading.Event()
    calls: list[str] = []

    def __init__(self, **_kwargs: object) -> None:
        pass

    def run_submission(self, *, code: str, **_kwargs: object) -> object:
        self.calls.append(code)
        if code == "slow":
            self.slow_release.wait(timeout=5)
        verdict = "WA" if code.startswith(("buggy", "wrong")) else "AC"
        case = SimpleNamespace(
            case_id="1",
            verdict=SimpleNamespace(value=verdict),
        )
        return SimpleNamespace(
            verdict=SimpleNamespace(value=verdict),
            cases=[case],
        )


class EvaluateStreamingTest(unittest.TestCase):
    def setUp(self) -> None:
        _FakeRunner.calls = []
        _FakeRunner.slow_release.clear()

    def test_writes_each_completed_result_before_all_futures_finish(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.jsonl"
            generations = root / "generations.jsonl"
            output = root / "evaluation.jsonl"
            _write_jsonl(
                dataset,
                [
                    _record("b", "buggy-b"),
                    _record("a", "buggy-a"),
                ],
            )
            _write_jsonl(
                generations,
                [
                    _generation("b", "slow"),
                    _generation("a", "fast"),
                ],
            )
            failures: list[BaseException] = []

            def run() -> None:
                try:
                    _evaluate(dataset, generations, output)
                except BaseException as error:  # pragma: no cover - surfaced below
                    failures.append(error)

            thread = threading.Thread(target=run)
            thread.start()
            streamed = _wait_for_jsonl_rows(output, expected=1)
            self.assertEqual([item["example_id"] for item in streamed], ["a"])
            self.assertTrue(thread.is_alive())

            _FakeRunner.slow_release.set()
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])
            completed = list(_iter_jsonl(output))
            self.assertEqual(
                [item["example_id"] for item in completed],
                ["a", "b"],
            )

    def test_resume_skips_results_already_streamed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.jsonl"
            generations = root / "generations.jsonl"
            output = root / "evaluation.jsonl"
            _write_jsonl(
                dataset,
                [
                    _record("a", "buggy-a"),
                    _record("b", "buggy-b"),
                ],
            )
            _write_jsonl(generations, [_generation("a", "fast-a")])
            _evaluate(dataset, generations, output)

            _FakeRunner.calls = []
            _write_jsonl(
                generations,
                [
                    _generation("a", "fast-a"),
                    _generation("b", "fast-b"),
                ],
            )
            summary = _evaluate(dataset, generations, output)

            self.assertNotIn("fast-a", _FakeRunner.calls)
            self.assertIn("fast-b", _FakeRunner.calls)
            self.assertEqual(summary.examples, 2)
            self.assertEqual(summary.repaired, 2)
            self.assertEqual(len(list(_iter_jsonl(output))), 2)

    def test_skips_ted_for_unsuccessful_repairs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.jsonl"
            generations = root / "generations.jsonl"
            output = root / "evaluation.jsonl"
            _write_jsonl(dataset, [_record("a", "buggy-a")])
            _write_jsonl(generations, [_generation("a", "wrong-a")])

            with (
                patch("src.repair.evaluate.PythonSubmissionRunner", _FakeRunner),
                patch(
                    "src.repair.evaluate.load_testcases",
                    return_value=[object()],
                ),
                patch("src.repair.evaluate.tree_edit_distance") as ted,
            ):
                summary = evaluate_generations(
                    dataset.parent,
                    dataset,
                    generations,
                    output,
                    workers=2,
                    timeout_sec=0.1,
                    ted_workers=1,
                )

            ted.assert_not_called()
            self.assertEqual(summary.repaired, 0)
            [result] = list(_iter_jsonl(output))
            self.assertIsNone(result["ted_buggy_fixed"])
            self.assertIsNone(result["ted_fixed_oracle"])

    def test_explicit_execution_only_mode_skips_ted_for_repairs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.jsonl"
            generations = root / "generations.jsonl"
            output = root / "evaluation.jsonl"
            _write_jsonl(dataset, [_record("a", "buggy-a")])
            _write_jsonl(generations, [_generation("a", "fixed-a")])
            with (
                patch("src.repair.evaluate.PythonSubmissionRunner", _FakeRunner),
                patch("src.repair.evaluate.load_testcases", return_value=[object()]),
                patch("src.repair.evaluate.tree_edit_distance") as ted,
            ):
                summary = evaluate_generations(
                    dataset.parent,
                    dataset,
                    generations,
                    output,
                    workers=2,
                    timeout_sec=0.1,
                    compute_tree_edit_distance=False,
                )
            ted.assert_not_called()
            self.assertEqual(summary.repaired, 1)
            [result] = list(_iter_jsonl(output))
            self.assertIsNone(result["ted_buggy_fixed"])

    def test_frozen_baseline_avoids_reexecuting_current_program(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "dataset.jsonl"
            generations = root / "generations.jsonl"
            baseline = root / "baseline.jsonl"
            output = root / "evaluation.jsonl"
            _write_jsonl(dataset, [_record("a", "buggy-a")])
            _write_jsonl(generations, [_generation("a", "fixed-a")])
            _write_jsonl(baseline, [{
                "example_id": "a",
                "buggy_verdict": "WA",
                "buggy_pass_rate": 0.25,
            }])
            with (
                patch("src.repair.evaluate.PythonSubmissionRunner", _FakeRunner),
                patch("src.repair.evaluate.load_testcases", return_value=[object()]),
            ):
                evaluate_generations(
                    dataset.parent,
                    dataset,
                    generations,
                    output,
                    workers=2,
                    timeout_sec=0.1,
                    compute_tree_edit_distance=False,
                    baseline_reference_path=baseline,
                )
            self.assertNotIn("buggy-a", _FakeRunner.calls)
            self.assertIn("fixed-a", _FakeRunner.calls)
            [result] = list(_iter_jsonl(output))
            self.assertEqual(result["buggy_verdict"], "WA")
            self.assertEqual(result["buggy_pass_rate"], 0.25)


def _evaluate(dataset: Path, generations: Path, output: Path) -> object:
    with (
        patch("src.repair.evaluate.PythonSubmissionRunner", _FakeRunner),
        patch("src.repair.evaluate.load_testcases", return_value=[object()]),
        patch("src.repair.evaluate.tree_edit_distance", return_value=0),
    ):
        return evaluate_generations(
            dataset.parent,
            dataset,
            generations,
            output,
            workers=2,
            timeout_sec=0.1,
            ted_workers=1,
        )


def _record(example_id: str, buggy_code: str) -> dict[str, object]:
    return {
        "example_id": example_id,
        "problem_id": "p",
        "history": [
            {
                "code": buggy_code,
                "verdict": "Wrong Answer",
            }
        ],
        "target_code": "oracle",
    }


def _generation(example_id: str, code: str) -> dict[str, object]:
    return {
        "example_id": example_id,
        "method": "Answer",
        "generated_code": code,
        "generation_time_sec": 0.1,
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _iter_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _wait_for_jsonl_rows(
    path: Path,
    *,
    expected: int,
    timeout: float = 3.0,
) -> list[dict[str, object]]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            rows = _iter_jsonl(path)
            if len(rows) >= expected:
                return rows
        time.sleep(0.01)
    raise AssertionError(f"Timed out waiting for {expected} rows in {path}")


if __name__ == "__main__":
    unittest.main()
