from __future__ import annotations

import unittest

from src.codenet.context_filter import (
    CONTEXT_WINDOW_TOKENS,
    _progress_envelope_examples,
    _trajectory_configuration_lengths,
)


class _CharacterTokenizer:
    eos_token_id = 0

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        self.assert_template_arguments(tokenize, add_generation_prompt)
        return "\n".join(message["content"] for message in messages) + "\nASSISTANT:"

    @staticmethod
    def assert_template_arguments(
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> None:
        if tokenize or not add_generation_prompt:
            raise AssertionError("Unexpected chat template arguments")

    def __call__(self, text: str, *, add_special_tokens: bool) -> dict[str, list[int]]:
        if add_special_tokens:
            raise AssertionError("Special tokens must be disabled")
        return {"input_ids": [1] * len(text)}


class TrajectoryContextFilterTest(unittest.TestCase):
    def test_progress_envelope_keeps_every_potential_equal_verdict_improvement(
        self,
    ) -> None:
        submissions = [
            (1, {"submission_id": "s1", "verdict": "Runtime Error", "code": "a"}),
            (2, {"submission_id": "s2", "verdict": "Runtime Error", "code": "b"}),
            (3, {"submission_id": "s3", "verdict": "Wrong Answer", "code": "c"}),
            (4, {"submission_id": "s4", "verdict": "Runtime Error", "code": "d"}),
            (5, {"submission_id": "s5", "verdict": "Accepted", "code": "e"}),
        ]

        examples = _progress_envelope_examples(submissions)

        self.assertEqual(
            [target["submission_id"] for _history, (_position, target), _n, _id in examples],
            ["s2", "s3", "s5"],
        )

    def test_any_overlength_configuration_marks_a_trajectory_for_exclusion(
        self,
    ) -> None:
        huge_source = "x" * CONTEXT_WINDOW_TOKENS
        lengths = _trajectory_configuration_lengths(
            _CharacterTokenizer(),
            problem_id="p1",
            context={
                "problem_description": "problem",
                "time_limit": 1,
                "memory_limit": 1,
            },
            submissions=[
                {
                    "submission_id": "s1",
                    "verdict": "Wrong Answer",
                    "code": huge_source,
                },
                {
                    "submission_id": "s2",
                    "verdict": "Accepted",
                    "code": "print(1)",
                },
            ],
            testcase_ids=["case_00001"],
        )

        self.assertGreater(lengths["answer"], CONTEXT_WINDOW_TOKENS)
        self.assertGreater(lengths["strict"], CONTEXT_WINDOW_TOKENS)
        self.assertGreater(lengths["progress-envelope"], CONTEXT_WINDOW_TOKENS)
        self.assertGreater(lengths["final"], CONTEXT_WINDOW_TOKENS)

    def test_final_configuration_accounts_for_execution_feedback(self) -> None:
        submissions = [
            {
                "submission_id": "s1",
                "verdict": "Wrong Answer",
                "code": "print(0)",
            },
            {
                "submission_id": "s2",
                "verdict": "Accepted",
                "code": "print(1)",
            },
        ]
        one_testcase = _trajectory_configuration_lengths(
            _CharacterTokenizer(),
            problem_id="p1",
            context={
                "problem_description": "problem",
                "time_limit": 1,
                "memory_limit": 1,
            },
            submissions=submissions,
            testcase_ids=["case_00001"],
        )
        two_testcases = _trajectory_configuration_lengths(
            _CharacterTokenizer(),
            problem_id="p1",
            context={
                "problem_description": "problem",
                "time_limit": 1,
                "memory_limit": 1,
            },
            submissions=submissions,
            testcase_ids=["case_00001", "case_00002"],
        )

        self.assertGreater(two_testcases["final"], one_testcase["final"])


if __name__ == "__main__":
    unittest.main()
