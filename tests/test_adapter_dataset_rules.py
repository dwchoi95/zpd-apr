from __future__ import annotations

import inspect
from pathlib import Path
import unittest
from collections import Counter
from types import SimpleNamespace

from src.repair.candidates import generate_candidate_repairs
from src.repair.dataset import (
    VERDICT_ORDERS,
    _build_adapter_examples,
    _is_testcase_verdict_improvement,
    build_repair_dataset,
)
from src.repair.inference import (
    _example_sampling_seed,
    _generation_token_budget,
    generate_repairs,
)
from src.repair.lsgen import generate_lsgen_repairs
from src.repair.outcomes import build_outcome_cache
from src.repair.prompts import build_messages
from src.repair.sequential import _build_stage_prompt, run_sequential_repairs
from src.repair.train import train_qlora
from src.repair.zero_shot import _build_retry_prompt, run_zero_shot_repairs


def _submission(position: int, verdict: str) -> tuple[int, dict[str, object]]:
    return (
        position,
        {
            "submission_id": f"s{position}",
            "verdict": verdict,
            "code": f"# S{position}",
        },
    )


def _outcome(*verdicts: str) -> dict[str, object]:
    tc_outcomes = {
        f"case_{index}": verdict
        for index, verdict in enumerate(verdicts, start=1)
    }
    return {
        "execution_verdict": next(
            (verdict for verdict in verdicts if verdict != "AC"),
            "AC",
        ),
        "passed_testcases": [
            case_id for case_id, verdict in tc_outcomes.items() if verdict == "AC"
        ],
        "pass_rate": sum(verdict == "AC" for verdict in verdicts) / len(verdicts),
        "tc_outcomes": tc_outcomes,
    }


def _target_ids(
    examples: list[
        tuple[
            list[tuple[int, dict[str, object]]],
            tuple[int, dict[str, object]],
            int,
            str,
        ]
    ],
) -> list[str]:
    return [str(target["submission_id"]) for _history, (_pos, target), _n, _id in examples]


def _history_ids(
    examples: list[
        tuple[
            list[tuple[int, dict[str, object]]],
            tuple[int, dict[str, object]],
            int,
            str,
        ]
    ],
) -> list[list[str]]:
    return [
        [str(submission["submission_id"]) for _pos, submission in history]
        for history, _target, _n, _id in examples
    ]


class AdapterDatasetRulesTest(unittest.TestCase):
    def test_answer_pairs_every_pre_ac_submission_with_final_ac(self) -> None:
        submissions = [
            _submission(1, "Runtime Error"),
            _submission(2, "Accepted"),
            _submission(3, "Wrong Answer"),
            _submission(4, "Accepted"),
        ]

        examples = _build_adapter_examples(
            submissions,
            target_mode="answer",
            problem_id="p1",
            outcomes={},
            counts=Counter(),
        )

        self.assertEqual(_target_ids(examples), ["s4", "s4"])
        self.assertEqual(_history_ids(examples), [["s1"], ["s3"]])

    def test_strict_keeps_only_source_verdict_improvements(self) -> None:
        submissions = [
            _submission(1, "Runtime Error"),
            _submission(2, "Runtime Error"),
            _submission(3, "Time Limit Exceeded"),
            _submission(4, "Memory Limit Exceeded"),
            _submission(5, "Time Limit Exceeded"),
            _submission(6, "Wrong Answer"),
            _submission(7, "Wrong Answer"),
            _submission(8, "Wrong Answer"),
            _submission(9, "Accepted"),
        ]

        examples = _build_adapter_examples(
            submissions,
            target_mode="strict",
            problem_id="p1",
            outcomes={},
            counts=Counter(),
        )

        self.assertEqual(_target_ids(examples), ["s3", "s6", "s9"])
        self.assertEqual(
            _history_ids(examples),
            [["s1"], ["s1", "s3"], ["s1", "s3", "s6"]],
        )

    def test_progress_adds_same_verdict_pareto_improvements(self) -> None:
        submissions = [
            _submission(1, "Runtime Error"),
            _submission(2, "Runtime Error"),
            _submission(3, "Time Limit Exceeded"),
            _submission(4, "Time Limit Exceeded"),
            _submission(5, "Time Limit Exceeded"),
            _submission(6, "Wrong Answer"),
            _submission(7, "Wrong Answer"),
            _submission(8, "Wrong Answer"),
            _submission(9, "Accepted"),
        ]
        outcomes = {
            ("p1", "s1"): _outcome("RE", "RE"),
            ("p1", "s2"): _outcome("WA", "RE"),
            ("p1", "s3"): _outcome("TLE", "TLE"),
            ("p1", "s4"): _outcome("WA", "RE"),
            ("p1", "s5"): _outcome("WA", "TLE"),
            ("p1", "s6"): _outcome("WA", "WA"),
            ("p1", "s7"): _outcome("WA", "WA"),
            ("p1", "s8"): _outcome("AC", "WA"),
            ("p1", "s9"): _outcome("AC", "AC"),
        }

        examples = _build_adapter_examples(
            submissions,
            target_mode="progress",
            problem_id="p1",
            outcomes=outcomes,
            counts=Counter(),
        )

        self.assertEqual(
            _target_ids(examples),
            ["s2", "s3", "s5", "s6", "s8", "s9"],
        )
        self.assertEqual(
            _history_ids(examples),
            [
                ["s1"],
                ["s1", "s2"],
                ["s1", "s2", "s3"],
                ["s1", "s2", "s3", "s5"],
                ["s1", "s2", "s3", "s5", "s6"],
                ["s1", "s2", "s3", "s5", "s6", "s8"],
            ],
        )

    def test_accepted_vs_failure_order_rebuilds_retained_chains(self) -> None:
        submissions = [
            _submission(1, "Runtime Error"),
            _submission(2, "Runtime Error"),
            _submission(3, "Time Limit Exceeded"),
            _submission(4, "Wrong Answer"),
            _submission(5, "Accepted"),
        ]
        outcomes = {
            ("p1", "s1"): _outcome("RE", "RE"),
            ("p1", "s2"): _outcome("AC", "RE"),
            ("p1", "s3"): _outcome("TLE", "TLE"),
            ("p1", "s4"): _outcome("WA", "WA"),
            ("p1", "s5"): _outcome("AC", "AC"),
        }
        order = VERDICT_ORDERS["accepted-vs-failure"]
        strict = _build_adapter_examples(
            submissions,
            target_mode="strict",
            problem_id="p1",
            outcomes=outcomes,
            counts=Counter(),
            severity_map=order,
        )
        progress = _build_adapter_examples(
            submissions,
            target_mode="progress",
            problem_id="p1",
            outcomes=outcomes,
            counts=Counter(),
            severity_map=order,
        )
        self.assertEqual(_target_ids(strict), ["s5"])
        self.assertEqual(_history_ids(strict), [["s1"]])
        self.assertEqual(_target_ids(progress), ["s2", "s5"])
        self.assertEqual(_history_ids(progress), [["s1"], ["s1", "s2"]])

    def test_testcase_improvement_rejects_regression_or_coverage_change(self) -> None:
        self.assertTrue(
            _is_testcase_verdict_improvement(
                _outcome("TLE", "TLE"),
                _outcome("WA", "TLE"),
            )
        )
        self.assertFalse(
            _is_testcase_verdict_improvement(
                _outcome("TLE", "TLE"),
                _outcome("WA", "RE"),
            )
        )
        self.assertTrue(
            _is_testcase_verdict_improvement(
                _outcome("MLE", "MLE"),
                _outcome("WA", "MLE"),
            )
        )
        self.assertFalse(
            _is_testcase_verdict_improvement(
                _outcome("TLE", "TLE"),
                _outcome("TLE"),
            )
        )

    def test_history_constraint_options_do_not_exist(self) -> None:
        record = {
            "problem_description": "A" * 9_000 + "DESCRIPTION_END",
            "time_limit": 1000,
            "memory_limit": 1024,
            "history": [
                {
                    "position": index,
                    "submission_id": f"s{index}",
                    "verdict": "Wrong Answer",
                    "code": f"# S{index}",
                }
                for index in range(1, 10)
            ],
        }

        messages = build_messages(record, "D")
        rendered_history = "\n".join(message["content"] for message in messages)
        for index in range(1, 10):
            self.assertIn(f"# S{index}", rendered_history)
        self.assertIn("DESCRIPTION_END", rendered_history)

        forbidden_parameters = {
            "history_mode",
            "limit",
            "limit_problems",
            "max_description_chars",
            "max_history",
            "max_input_tokens",
            "max_length",
            "max_steps",
            "max_target_chars",
            "max_testcase_input_chars",
            "max_testcases_per_problem",
        }
        for function in (
            build_messages,
            build_repair_dataset,
            build_outcome_cache,
            train_qlora,
            generate_repairs,
            run_zero_shot_repairs,
            run_sequential_repairs,
            generate_candidate_repairs,
            generate_lsgen_repairs,
        ):
            self.assertFalse(
                forbidden_parameters & inspect.signature(function).parameters.keys(),
                function.__name__,
            )

    def test_generation_uses_all_remaining_model_context(self) -> None:
        model = SimpleNamespace(
            config=SimpleNamespace(max_position_embeddings=100)
        )

        self.assertEqual(_generation_token_budget(model, 30), 70)
        self.assertEqual(_generation_token_budget(model, 30, 40), 40)
        with self.assertRaisesRegex(ValueError, "input is not truncated"):
            _generation_token_budget(model, 100)

    def test_stochastic_generation_seed_is_resume_stable_and_example_specific(self) -> None:
        first = _example_sampling_seed(3101, "example-a")
        self.assertEqual(first, _example_sampling_seed(3101, "example-a"))
        self.assertNotEqual(first, _example_sampling_seed(3102, "example-a"))
        self.assertNotEqual(first, _example_sampling_seed(3101, "example-b"))
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 2**63 - 1)

    def test_stochastic_runner_restarts_complete_batched_seed_pass(self) -> None:
        runner = Path("scripts/run_fse2027_stochastic_candidate_control_remote.sh").read_text()
        self.assertIn("generate_vllm_stochastic_candidates.py", runner)
        self.assertIn("--sampling-seed 3101 --sampling-seed 3102", runner)
        self.assertIn("--max-model-len 8192", runner)

    def test_dynamic_stage_feedback_omits_only_generated_code_on_overflow(self) -> None:
        class CharacterTokenizer:
            def apply_chat_template(
                self,
                messages: list[dict[str, str]],
                *,
                tokenize: bool,
                add_generation_prompt: bool,
            ) -> str:
                self.assert_options = (tokenize, add_generation_prompt)
                return "\n".join(message["content"] for message in messages)

            def __call__(self, text: str, *, add_special_tokens: bool) -> dict[str, list[int]]:
                self.add_special_tokens = add_special_tokens
                return {"input_ids": list(range(len(text)))}

        tokenizer = CharacterTokenizer()
        record = {
            "problem_description": "Add two integers.",
            "time_limit": 1000,
            "memory_limit": 1024,
            "history": [
                {
                    "position": 1,
                    "submission_id": "s1",
                    "verdict": "Wrong Answer",
                    "code": "print(0)",
                }
            ],
        }
        attempts = [
            {
                "source": "Progress",
                "generated_code": "x" * 1_000,
                "fixed_verdict": "WA",
                "fixed_pass_rate": 0.5,
                "fixed_tc_outcomes": {"case_1": "AC", "case_2": "WA"},
                "repair_status": "equal",
                "baseline_pass_rate": 0.5,
            }
        ]
        full_prompt = "\n".join(
            message["content"]
            for message in build_messages(
                record,
                "D",
                repair_attempts=attempts,
            )
        )
        compact_attempt = {**attempts[0], "include_generated_code": False}
        compact_prompt = "\n".join(
            message["content"]
            for message in build_messages(
                record,
                "D",
                repair_attempts=[compact_attempt],
            )
        )
        context_length = len(compact_prompt) + 1
        self.assertGreaterEqual(len(full_prompt), context_length)

        prompt, omitted = _build_stage_prompt(
            tokenizer,
            record,
            "D",
            repair_attempts=attempts,
            context_length=context_length,
        )

        self.assertEqual(omitted, 1)
        self.assertNotIn("x" * 1_000, prompt)
        self.assertIn("Execution verdict: WA", prompt)
        self.assertIn("Pass rate: 1/2 (50.0%)", prompt)
        self.assertIn("print(0)", prompt)

    def test_zero_shot_retry_overflow_preserves_execution_feedback(self) -> None:
        class CharacterTokenizer:
            def apply_chat_template(
                self,
                messages: list[dict[str, str]],
                *,
                tokenize: bool,
                add_generation_prompt: bool,
            ) -> str:
                return "\n".join(message["content"] for message in messages)

            def __call__(self, text: str, *, add_special_tokens: bool) -> dict[str, list[int]]:
                return {"input_ids": list(range(len(text)))}

        tokenizer = CharacterTokenizer()
        feedback = (
            "The previous candidate was not accepted. Its verdict was WA and "
            "it passed 1 of 2 test cases."
        )
        messages = [
            {"role": "system", "content": "Repair the program."},
            {"role": "user", "content": "Original code: print(0)"},
            {"role": "assistant", "content": "x" * 1_000},
            {"role": "user", "content": feedback},
        ]
        compact_marker = (
            "Previous generated program omitted because its full text would "
            "exceed the model context; the following execution feedback is "
            "preserved."
        )
        context_length = (
            len("\n".join(["Repair the program.", "Original code: print(0)", compact_marker, feedback]))
            + 1
        )

        prompt, omitted = _build_retry_prompt(
            tokenizer,
            messages,
            context_length=context_length,
        )

        self.assertEqual(omitted, 1)
        self.assertNotIn("x" * 1_000, prompt)
        self.assertIn("Original code: print(0)", prompt)
        self.assertIn(feedback, prompt)


if __name__ == "__main__":
    unittest.main()
