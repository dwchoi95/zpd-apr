from __future__ import annotations

import json
import unittest
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
DATASET_ROOT = ROOT / "outputs/split-90-10/canonical-v5/datasets"
OUTCOME_CACHE = (
    ROOT / "outputs/split-90-10/canonical-v5/outcomes/all-original-submissions.jsonl"
)
CONTEXT_MANIFEST = DATA_ROOT / "trajectory_context_4k.jsonl"
ARTIFACTS = {
    "answer": DATASET_ROOT / "train-answer.jsonl",
    "strict": DATASET_ROOT / "train-strict.jsonl",
    "progress": DATASET_ROOT / "train-progress.jsonl",
}
VERDICT_SEVERITY = {
    "Accepted": 0,
    "Wrong Answer": 1,
    "Time Limit Exceeded": 2,
    "Memory Limit Exceeded": 2,
    "Runtime Error": 3,
    "Compilation Error": 4,
    "Compile Error": 4,
    "Internal error": 5,
}
EXECUTION_VERDICT = {
    "AC": "Accepted",
    "WA": "Wrong Answer",
    "TLE": "Time Limit Exceeded",
    "RE": "Runtime Error",
    "CE": "Compilation Error",
}


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _strictly_improves(current: dict[str, Any], target: dict[str, Any]) -> bool:
    return VERDICT_SEVERITY.get(str(target.get("verdict")), 5) < VERDICT_SEVERITY.get(
        str(current.get("verdict")),
        5,
    )


def _testcases_improve(current: dict[str, Any], target: dict[str, Any]) -> bool:
    current_cases = current.get("tc_outcomes")
    target_cases = target.get("tc_outcomes")
    if not isinstance(current_cases, dict) or not isinstance(target_cases, dict):
        return False
    if not current_cases or current_cases.keys() != target_cases.keys():
        return False
    improved = False
    for case_id, current_verdict in current_cases.items():
        current_score = VERDICT_SEVERITY.get(
            EXECUTION_VERDICT.get(str(current_verdict), str(current_verdict)),
            5,
        )
        target_verdict = target_cases[case_id]
        target_score = VERDICT_SEVERITY.get(
            EXECUTION_VERDICT.get(str(target_verdict), str(target_verdict)),
            5,
        )
        if target_score > current_score:
            return False
        improved = improved or target_score < current_score
    return improved


class CanonicalDatasetArtifactsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.allowed = {
            (str(row["problem_id"]), str(row["user_id"]))
            for row in _iter_jsonl(DATA_ROOT / "splits/seen_train.jsonl")
        }
        cls.trajectories: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for problem_id, user_id in cls.allowed:
            cls.trajectories[(problem_id, user_id)] = list(
                _iter_jsonl(
                    DATA_ROOT / problem_id / "submissions" / f"{user_id}.jsonl"
                )
            )

        loaded_outcomes: dict[tuple[str, str], dict[str, Any]] = {}
        if OUTCOME_CACHE.is_file():
            for row in _iter_jsonl(OUTCOME_CACHE):
                loaded_outcomes[
                    (str(row["problem_id"]), str(row["submission_id"]))
                ] = row
        cls.outcomes = {
            key: row
            for key, row in loaded_outcomes.items()
            if "cache_error" not in row
        }

    def _expected(
        self,
        mode: str,
    ) -> Counter[tuple[str, str, tuple[str, ...], str, int]]:
        expected: Counter[tuple[str, str, tuple[str, ...], str, int]] = Counter()
        for (problem_id, user_id), submissions in self.trajectories.items():
            if mode == "answer":
                final = submissions[-1]
                if str(final.get("verdict")) != "Accepted":
                    continue
                for source in submissions[:-1]:
                    if str(source.get("verdict")) == "Accepted":
                        continue
                    expected[
                        (
                            problem_id,
                            user_id,
                            (str(source["submission_id"]),),
                            str(final["submission_id"]),
                            len(submissions),
                        )
                    ] += 1
                continue

            retained = [(1, submissions[0])]
            for position, candidate in enumerate(submissions[1:], start=2):
                current = retained[-1][1]
                keep = _strictly_improves(current, candidate)
                if mode == "progress" and not keep:
                    keep = (
                        str(current.get("verdict"))
                        == str(candidate.get("verdict"))
                        and _testcases_improve(
                            self.outcomes.get(
                                (problem_id, str(current["submission_id"])),
                                {},
                            ),
                            self.outcomes.get(
                                (problem_id, str(candidate["submission_id"])),
                                {},
                            ),
                        )
                    )
                if keep:
                    retained.append((position, candidate))
            for target_index in range(1, len(retained)):
                original_position, target = retained[target_index]
                expected[
                    (
                        problem_id,
                        user_id,
                        tuple(
                            str(submission["submission_id"])
                            for _position, submission in retained[:target_index]
                        ),
                        str(target["submission_id"]),
                        original_position,
                    )
                ] += 1
        return expected

    def _actual(
        self,
        mode: str,
    ) -> Counter[tuple[str, str, tuple[str, ...], str, int]]:
        actual: Counter[tuple[str, str, tuple[str, ...], str, int]] = Counter()
        example_ids: set[str] = set()
        for row in _iter_jsonl(ARTIFACTS[mode]):
            key = (str(row["problem_id"]), str(row["user_id"]))
            self.assertIn(key, self.allowed)
            example_id = str(row["example_id"])
            self.assertNotIn(example_id, example_ids)
            example_ids.add(example_id)
            history = row["history"]
            if mode == "answer":
                self.assertEqual(len(history), 1)
                self.assertNotEqual(str(history[0]["verdict"]), "Accepted")
                self.assertEqual(str(row["target_verdict"]), "Accepted")
            else:
                self.assertEqual(
                    [item["position"] for item in history],
                    list(range(1, len(history) + 1)),
                )
                self.assertEqual(row["target_position"], len(history) + 1)
            actual[
                (
                    key[0],
                    key[1],
                    tuple(str(item["submission_id"]) for item in history),
                    str(row["target_submission_id"]),
                    int(row["original_target_position"]),
                )
            ] += 1
        return actual

    @unittest.skipUnless(
        ARTIFACTS["answer"].is_file(),
        "canonical-v5 Answer artifact has not been generated",
    )
    def test_answer_matches_independent_reconstruction(self) -> None:
        self.assertEqual(self._actual("answer"), self._expected("answer"))

    @unittest.skipUnless(
        ARTIFACTS["strict"].is_file(),
        "canonical-v5 Strict artifact has not been generated",
    )
    def test_strict_matches_independent_reconstruction(self) -> None:
        self.assertEqual(self._actual("strict"), self._expected("strict"))

    @unittest.skipUnless(
        ARTIFACTS["progress"].is_file()
        and OUTCOME_CACHE.with_suffix(".summary.json").is_file()
        and json.loads(
            OUTCOME_CACHE.with_suffix(".summary.json").read_text(encoding="utf-8")
        ).get("outcome_cache_complete")
        is True,
        "canonical-v5 Progress artifact and complete outcome cache are required",
    )
    def test_progress_matches_independent_reconstruction(self) -> None:
        self.assertEqual(self._actual("progress"), self._expected("progress"))

    def test_trajectory_splits_do_not_overlap(self) -> None:
        split_keys = {}
        split_problem_ids = {}
        for split in ("seen_train", "seen_valid", "seen_test", "unseen_test"):
            rows = list(_iter_jsonl(DATA_ROOT / f"splits/{split}.jsonl"))
            split_keys[split] = {
                (str(row["problem_id"]), str(row["user_id"])) for row in rows
            }
            split_problem_ids[split] = {str(row["problem_id"]) for row in rows}
        names = list(split_keys)
        for index, left in enumerate(names):
            for right in names[index + 1 :]:
                self.assertFalse(
                    split_keys[left] & split_keys[right],
                    f"{left} and {right} overlap",
                )
        problem_groups = {
            str(row["problem_id"]): str(row["problem_group"])
            for row in _iter_jsonl(DATA_ROOT / "splits/problem_split.jsonl")
        }
        seen_problem_ids = {
            problem_id
            for problem_id, group in problem_groups.items()
            if group == "seen"
        }
        unseen_problem_ids = {
            problem_id
            for problem_id, group in problem_groups.items()
            if group == "unseen"
        }
        for split in ("seen_train", "seen_valid", "seen_test"):
            self.assertEqual(split_problem_ids[split], seen_problem_ids)
        self.assertEqual(split_problem_ids["unseen_test"], unseen_problem_ids)

        eligibility = {
            (str(row["problem_id"]), str(row["user_id"])): bool(row["eligible"])
            for row in _iter_jsonl(CONTEXT_MANIFEST)
        }
        assigned = set().union(*split_keys.values())
        eligible = {key for key, keep in eligibility.items() if keep}
        excluded = {key for key, keep in eligibility.items() if not keep}
        self.assertEqual(assigned, eligible)
        self.assertFalse(assigned & excluded)


if __name__ == "__main__":
    unittest.main()
