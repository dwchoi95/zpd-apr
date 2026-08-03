from __future__ import annotations

import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from src.repair.outcomes import build_outcome_cache


class _FakeRunner:
    slow_release = threading.Event()
    second_problem_finished = threading.Event()

    def __init__(self, **_kwargs: object) -> None:
        pass

    def run_submission(
        self,
        *,
        problem_id: str,
        **_kwargs: object,
    ) -> object:
        if problem_id == "p1":
            self.slow_release.wait(timeout=5)
        else:
            self.second_problem_finished.set()
        case = SimpleNamespace(
            case_id="1",
            verdict=SimpleNamespace(value="AC"),
        )
        return SimpleNamespace(
            verdict=SimpleNamespace(value="AC"),
            cases=[case],
        )


class OutcomeCacheGlobalQueueTest(unittest.TestCase):
    def setUp(self) -> None:
        _FakeRunner.slow_release.clear()
        _FakeRunner.second_problem_finished.clear()

    def test_does_not_wait_for_one_problem_before_scheduling_the_next(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "outcomes.jsonl"
            failures: list[BaseException] = []

            def submissions(problem_dir: Path, **_kwargs: object) -> object:
                problem_id = problem_dir.name
                count = 2 if problem_id == "p1" else 1
                return {
                    f"{problem_id}-s{index}": {
                        "submission_id": f"{problem_id}-s{index}",
                        "verdict": "Accepted",
                        "code": "print(1)",
                    }
                    for index in range(1, count + 1)
                }

            def run() -> None:
                try:
                    build_outcome_cache(
                        root,
                        split="seen_train",
                        output_path=output,
                        workers=2,
                        timeout_sec=0.1,
                    )
                except BaseException as error:  # pragma: no cover
                    failures.append(error)

            with (
                patch(
                    "src.repair.outcomes.load_split_problem_ids",
                    return_value=["p1", "p2"],
                ),
                patch(
                    "src.repair.outcomes.load_split_trajectory_ids",
                    return_value=None,
                ),
                patch(
                    "src.repair.outcomes.load_testcases",
                    return_value=[object()],
                ),
                patch(
                    "src.repair.outcomes._load_problem_submissions",
                    side_effect=submissions,
                ),
                patch(
                    "src.repair.outcomes.PythonSubmissionRunner",
                    _FakeRunner,
                ),
            ):
                thread = threading.Thread(target=run)
                thread.start()
                self.assertTrue(
                    _FakeRunner.second_problem_finished.wait(timeout=2),
                    "p2 was not scheduled while p1 was still running",
                )
                streamed = _wait_for_rows(output, expected=1)
                self.assertEqual(streamed[0]["problem_id"], "p2")
                self.assertTrue(thread.is_alive())

                _FakeRunner.slow_release.set()
                thread.join(timeout=5)

            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])
            self.assertEqual(len(_rows(output)), 3)


def _rows(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _wait_for_rows(
    path: Path,
    *,
    expected: int,
) -> list[dict[str, object]]:
    for _attempt in range(200):
        if path.is_file():
            rows = _rows(path)
            if len(rows) >= expected:
                return rows
        threading.Event().wait(0.01)
    raise AssertionError(f"Timed out waiting for {expected} rows")


if __name__ == "__main__":
    unittest.main()
