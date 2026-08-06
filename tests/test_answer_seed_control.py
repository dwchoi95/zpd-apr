from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

import json

from src.repair.prompts import build_messages
from src.repair.evaluate import (
    _zss_distance,
    budget_bounded_tree_edit_distance,
    tree_edit_distance,
)
from src.repair.inference import _generation_token_budget, extract_python_code


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from analyze_fse2027_answer_seed_control import audit_checkpoints, rr_contrast  # noqa: E402
from analyze_fse2027_user_overlap import stratify  # noqa: E402
from compose_answer_seed_control import compose, summarize  # noqa: E402
from extract_answer_generations import extract  # noqa: E402
from seed_policy_generations import seed_rows  # noqa: E402
from seed_policy_evaluations import seed_rows as seed_evaluation_rows  # noqa: E402
from normalize_evaluation_baseline import normalize as normalize_baseline  # noqa: E402
from seed_lsgen_always_three import (  # noqa: E402
    preserve_complete_rows,
    seed_rows as seed_lsgen_rows,
)
from select_relation_seed_portfolio import select  # noqa: E402
from sample_problem_balanced_dataset import select as sample_problems  # noqa: E402
from select_execution_portfolio import select_portfolios  # noqa: E402
from apply_patch_budget import apply_budget  # noqa: E402
from build_codeworkout_trajectories import build as build_codeworkout  # noqa: E402
from build_codeworkout_repair_datasets import build as build_codeworkout_data  # noqa: E402
from collect_codeworkout_evaluation import collect as collect_codeworkout  # noqa: E402
from prepare_codeworkout_evaluation import java_source  # noqa: E402
from analyze_fse2027_selected_portfolios import (  # noqa: E402
    assert_same_answer_control,
    clustered_mean_budget_difference,
    holm_adjust,
)
from analyze_codeworkout_portfolios import (  # noqa: E402
    paired_rr_report as codeworkout_paired_rr,
    portfolio as codeworkout_portfolio,
)
from analyze_fse2027_lsgen_budget_controller import choose_budgeted  # noqa: E402
from audit_generation_token_cap import completion_texts  # noqa: E402


class AnswerSeedControlAnalysisTest(unittest.TestCase):
    def test_normalizes_candidate_rows_to_one_cached_baseline(self) -> None:
        rows = [
            {
                "example_id": "e",
                "buggy_pass_rate": 0.5,
                "buggy_verdict": "WA",
                "fixed_pass_rate": 0.4,
                "improved": False,
            }
        ]
        references = [
            {"example_id": "e", "buggy_pass_rate": 0.25, "buggy_verdict": "TLE"}
        ]
        normalized, changed = normalize_baseline(rows, references)
        self.assertEqual(changed, 1)
        self.assertEqual(normalized[0]["buggy_pass_rate"], 0.25)
        self.assertEqual(normalized[0]["buggy_verdict"], "TLE")
        self.assertTrue(normalized[0]["improved"])

    def test_seeds_matching_individual_execution_outcome(self) -> None:
        dataset = [
            {
                "example_id": "e",
                "history": [{"code": "x = 0\n"}],
                "target_code": "x = 1\n",
            }
        ]
        generation = {
            "example_id": "e",
            "generated_code": "x = 1\n",
            "raw_generation": "x = 1\n",
            "generation_time_sec": 0.5,
        }
        sequential = {
            "example_id": "e",
            "problem_id": "p",
            "user_id": "u",
            "buggy_verdict": "WA",
            "buggy_pass_rate": 0.0,
            "candidate_outcomes": [
                {
                    "source": "Answer",
                    "generated_code": "x = 1\n",
                    "fixed_verdict": "AC",
                    "fixed_pass_rate": 1.0,
                    "fixed_tc_outcomes": {"case_1": "AC"},
                    "execution_time_sec": 0.25,
                }
            ],
        }
        rows = seed_evaluation_rows(
            dataset,
            [generation],
            [],
            method="Answer2028",
            source="Answer",
            sequential=[sequential],
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["repaired"])
        self.assertEqual(rows[0]["fixed_tc_outcomes"], {"case_1": "AC"})
        self.assertEqual(rows[0]["execution_reused_from"], "Answer")

    def test_flat_evaluation_seed_requires_matching_generated_code(self) -> None:
        dataset = [
            {
                "example_id": "e",
                "history": [{"code": "x = 0\n"}],
                "target_code": "x = 1\n",
            }
        ]
        generation = {"example_id": "e", "generated_code": "x = 1\n"}
        flat = [
            {
                "example_id": "e",
                "generated_code": "x = 1\n",
                "fixed_pass_rate": 1.0,
                "repaired": True,
            }
        ]
        rows = seed_evaluation_rows(
            dataset,
            [generation],
            [],
            method="Answer2027",
            source="Answer",
            sequential=[],
            flat=flat,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["method"], "Answer2027")

    def test_first_flat_execution_source_has_priority(self) -> None:
        dataset = [
            {
                "example_id": "e",
                "history": [{"code": "x = 0\n"}],
                "target_code": "x = 1\n",
            }
        ]
        generation = {"example_id": "e", "generated_code": "x = 1\n"}
        authoritative = {
            "example_id": "e",
            "generated_code": "x = 1\n",
            "fixed_pass_rate": 1.0,
            "repaired": True,
        }
        noisy_reexecution = {
            **authoritative,
            "fixed_pass_rate": 0.5,
            "repaired": False,
        }
        rows = seed_evaluation_rows(
            dataset,
            [generation],
            [],
            method="Answer2029",
            source="Answer",
            sequential=[],
            flat=[authoritative, noisy_reexecution],
        )
        self.assertEqual(rows[0]["fixed_pass_rate"], 1.0)
        self.assertTrue(rows[0]["repaired"])

    def test_budget_bounded_ted_uses_sound_node_count_lower_bound(self) -> None:
        before = "x = 0\n"
        after = "\n".join(f"x{i} = {i}" for i in range(20)) + "\n"
        self.assertEqual(
            budget_bounded_tree_edit_distance(before, after, maximum_budget=2),
            3,
        )

    def test_budget_bounded_exact_ted_matches_canonical_zss(self) -> None:
        pairs = [
            ("x = 0\n", "x = 1\n"),
            ("if x:\n    y = 1\n", "if not x:\n    y = 2\n"),
            ("for i in a:\n    print(i)\n", "for j in a:\n    print(j + 1)\n"),
        ]
        for before, after in pairs:
            canonical_zss = _zss_distance(ast.parse(before), ast.parse(after))
            self.assertEqual(
                budget_bounded_tree_edit_distance(
                    before, after, maximum_budget=10_000
                ),
                canonical_zss,
            )
            self.assertEqual(tree_edit_distance(before, after), canonical_zss)

    def test_seeds_complete_and_partial_lsgen_candidate_prefixes(self) -> None:
        dataset = [
            {
                "example_id": "a",
                "history": [{"code": "x = 0\n"}],
                "target_code": "x = 1\n",
            },
            {
                "example_id": "b",
                "history": [{"code": "y = 0\n"}],
                "target_code": "y = 1\n",
            },
        ]

        def patch(index: int, code: str, rate: float) -> dict:
            return {
                "patch_index": index,
                "source": f"iteration-{index}",
                "generated_code": code,
                "raw_generation": code,
                "fixed_verdict": "AC" if rate == 1.0 else "WA",
                "fixed_pass_rate": rate,
                "fixed_tc_outcomes": {},
            }

        legacy = [
            {
                "example_id": "a",
                "problem_id": "p",
                "user_id": "u",
                "buggy_pass_rate": 0.0,
                "patches": [
                    patch(1, "x = 2\n", 0.5),
                    patch(2, "x = 1\n", 1.0),
                    patch(3, "x = 3\n", 1.0),
                ],
            },
            {
                "example_id": "b",
                "problem_id": "p",
                "user_id": "v",
                "buggy_pass_rate": 0.0,
                "patches": [patch(1, "y = 1\n", 1.0)],
            },
        ]
        rows = seed_lsgen_rows(dataset, legacy)
        self.assertEqual([row["example_id"] for row in rows], ["a", "b"])
        self.assertEqual(rows[0]["selected_patch_index"], 2)
        self.assertTrue(rows[0]["always_generate_max"])
        self.assertFalse(rows[1]["always_generate_max"])
        self.assertEqual(len(rows[1]["patches"]), 1)
        self.assertTrue(
            all(
                "ted_buggy_fixed" in candidate
                for row in rows
                for candidate in row["patches"]
            )
        )

    def test_lsgen_resume_preserves_only_completed_always_three_rows(self) -> None:
        seeded = [
            {"example_id": "a", "patches": [{"patch_index": 1}]},
            {"example_id": "b", "patches": [{"patch_index": 1}]},
        ]
        completed = {
            "example_id": "a",
            "patches": [{"patch_index": i} for i in (1, 2, 3)],
            "always_generate_max": True,
        }
        incomplete = {
            "example_id": "b",
            "patches": [{"patch_index": 1}, {"patch_index": 2}],
            "always_generate_max": False,
        }
        merged = preserve_complete_rows(seeded, [completed, incomplete])
        self.assertIs(merged[0], completed)
        self.assertIs(merged[1], seeded[1])

    def test_generation_budget_respects_explicit_cap(self) -> None:
        model = type("Model", (), {"config": type("Config", (), {"max_position_embeddings": 32768})()})()
        self.assertEqual(_generation_token_budget(model, 1000, 4096), 4096)
        self.assertEqual(_generation_token_budget(model, 32000, 4096), 768)

    def test_generation_cap_audit_finds_nested_completions(self) -> None:
        row = {
            "raw_generation": "top",
            "patches": [{"raw_generation": "patch"}],
            "candidate_outcomes": [{"raw_generation": "candidate"}],
        }
        self.assertEqual(
            list(completion_texts(row)), ["top", "patch", "candidate"]
        )

    def test_codeworkout_builder_stops_at_first_ac_and_holds_out_users(self) -> None:
        submissions = []
        compile_rows = []
        for user in ("u1", "u2", "u3"):
            for position, outcomes in enumerate(([0, 0], [1, 0], [1, 1]), start=1):
                submission_id = f"{user}-{position}"
                submissions.append(
                    {
                        "submission_id": submission_id,
                        "user_id": user,
                        "problem_id": 1,
                        "assignment_id": 1,
                        "code": f"public int f() {{ return {position}; }}",
                        "prompt": "p",
                        "timestamp": f"2020-01-0{position}",
                        "timestep": position,
                        "testcase_pass": outcomes,
                        "score": sum(outcomes) / len(outcomes),
                    }
                )
                compile_rows.append(
                    {"submission_id": submission_id, "compiles": position != 1}
                )
        trajectories, summary = build_codeworkout(submissions, compile_rows, 2027)
        self.assertEqual(len(trajectories), 3)
        self.assertTrue(
            all(row["submissions"][-1]["verdict"] == "AC" for row in trajectories)
        )
        self.assertTrue(
            all(row["submissions"][0]["verdict"] == "CE" for row in trajectories)
        )
        self.assertEqual(summary["user_overlap_across_splits"], 0)

        datasets, dataset_summary = build_codeworkout_data(trajectories)
        answer_rows = datasets["train-answer"]
        self.assertTrue(answer_rows)
        self.assertTrue(all(len(row["history"]) == 1 for row in answer_rows))
        self.assertTrue(
            all(row["target_verdict"] == "Accepted" for row in answer_rows)
        )
        self.assertEqual(dataset_summary["student_overlap"], 0)

    def test_codeworkout_progress_keeps_same_verdict_test_improvement(self) -> None:
        trajectory = {
            "trajectory_id": "cw:1:u",
            "user_id": "u",
            "problem_id": "cw001",
            "prompt": "Return an integer.",
            "split": "train",
            "submissions": [
                {
                    "submission_id": "s1",
                    "code": "class Main { int f(){ return 0; } }",
                    "verdict": "WA",
                    "testcase_pass": [0, 0],
                },
                {
                    "submission_id": "s2",
                    "code": "class Main { int f(){ return 1; } }",
                    "verdict": "WA",
                    "testcase_pass": [1, 0],
                },
                {
                    "submission_id": "s3",
                    "code": "class Main { int f(){ return 2; } }",
                    "verdict": "AC",
                    "testcase_pass": [1, 1],
                },
            ],
        }
        datasets, _summary = build_codeworkout_data([trajectory])
        self.assertEqual(len(datasets["train-strict"]), 1)
        self.assertEqual(len(datasets["train-progress"]), 2)
        self.assertEqual(
            [row["original_target_position"] for row in datasets["train-progress"]],
            [2, 3],
        )

    def test_prompt_switches_codeworkout_language_to_java(self) -> None:
        record = {
            "problem_description": "Return an integer.",
            "time_limit": "unknown",
            "memory_limit": "unknown",
            "language": "Java",
            "history": [
                {
                    "position": 1,
                    "verdict": "Wrong Answer",
                    "code": "class Main {}",
                }
            ],
        }
        messages = build_messages(record, "D")
        self.assertIn("complete Java submission", messages[0]["content"])
        self.assertIn("```java", messages[1]["content"])
        self.assertEqual(
            extract_python_code("```java\npublic int f() { return 1; }\n```"),
            "public int f() { return 1; }",
        )

    def test_codeworkout_java_harness_and_collector(self) -> None:
        source = java_source(
            "public int sortaSum(int a, int b) { return a + b; }",
            "sortaSum",
            [("1, 2", "3"), ("3, 4", "7")],
        )
        self.assertIn("class Candidate", source)
        self.assertIn("obj.sortaSum(1, 2)", source)
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            (root / "abc.txt").write_text(
                "ok\n__ZPD_CASE_0001__3\n__ZPD_CASE_0002__0\n",
                encoding="utf-8",
            )
            manifest = [
                {
                    "slug": "abc",
                    "example_id": "e",
                    "problem_id": "cw001",
                    "user_id": "u",
                    "expected": ["3", "7"],
                    "current_tc_outcomes": {"case_001": "WA", "case_002": "WA"},
                    "current_pass_rate": 0.0,
                }
            ]
            rows, summary = collect_codeworkout(manifest, root)
        self.assertEqual(rows[0]["fixed_pass_rate"], 0.5)
        self.assertTrue(rows[0]["improved"])
        self.assertEqual(summary["repair_rate"], 0.0)

    def test_codeworkout_portfolio_rejects_duplicate_examples(self) -> None:
        row = {
            "example_id": "duplicate",
            "problem_id": "cw001",
            "user_id": "u",
            "current_pass_rate": 0.0,
            "fixed_pass_rate": 1.0,
            "repaired": True,
            "improved": True,
        }
        with self.assertRaisesRegex(ValueError, "duplicate example_id"):
            codeworkout_portfolio([[row, dict(row)]])

        _rows, summary = codeworkout_portfolio([[row]])
        self.assertEqual(summary["pass_rate"], 1.0)
        self.assertNotIn("program_rate", summary)

        weaker = [{**row, "repaired": False, "fixed_pass_rate": 0.0}]
        contrast = codeworkout_paired_rr([row], weaker, "left", "right")
        self.assertEqual(contrast["left_minus_right"], 1.0)
        self.assertEqual(contrast["left_only"], 1)

    def test_codeworkout_portfolio_rejects_baseline_drift(self) -> None:
        row = {
            "example_id": "e1",
            "problem_id": "cw001",
            "user_id": "u1",
            "current_pass_rate": 0.25,
            "fixed_pass_rate": 1.0,
            "repaired": True,
            "improved": True,
        }
        drifted = dict(row, current_pass_rate=0.5)
        with self.assertRaisesRegex(ValueError, "baselines disagree"):
            codeworkout_portfolio([[row], [drifted]])

    def test_patch_budget_abstains_without_regression(self) -> None:
        row = {
            "repaired": True,
            "improved": True,
            "buggy_pass_rate": 0.25,
            "fixed_pass_rate": 1.0,
            "ted_buggy_fixed": 21,
            "tree_edit_distance": 21,
            "selected_source": "Answer",
        }
        gated = apply_budget(row, 20)
        self.assertFalse(gated["repaired"])
        self.assertEqual(gated["fixed_pass_rate"], row["buggy_pass_rate"])
        self.assertEqual(gated["selected_source"], "current-fallback:patch-budget")
        self.assertTrue(apply_budget(row, 21)["repaired"])

    def test_budgeted_controller_continues_past_over_budget_acceptance(self) -> None:
        dataset = [{"example_id": "e", "problem_id": "p", "user_id": "u"}]

        def candidate(ted: int) -> dict:
            return {
                "example_id": "e",
                "problem_id": "p",
                "user_id": "u",
                "buggy_pass_rate": 0.0,
                "fixed_pass_rate": 1.0,
                "repaired": True,
                "ted_buggy_fixed": ted,
                "ted_fixed_oracle": 0,
            }

        rows = compose(
            dataset,
            [("first", [candidate(30)]), ("second", [candidate(10)]), ("third", [candidate(5)])],
            max_ted=20,
        )
        self.assertTrue(rows[0]["repaired"])
        self.assertEqual(rows[0]["selected_source"], "second")
        self.assertEqual(rows[0]["budget_eligible_candidate_count"], 2)

    def test_lsgen_budget_replay_continues_after_over_budget_acceptance(self) -> None:
        row = {
            "example_id": "e",
            "problem_id": "p",
            "user_id": "u",
            "buggy_pass_rate": 0.0,
            "patches": [
                {
                    "patch_index": 1,
                    "source": "iteration-1",
                    "fixed_pass_rate": 1.0,
                    "ted_buggy_fixed": 30,
                },
                {
                    "patch_index": 2,
                    "source": "iteration-2",
                    "fixed_pass_rate": 1.0,
                    "ted_buggy_fixed": 10,
                },
                {
                    "patch_index": 3,
                    "source": "iteration-3",
                    "fixed_pass_rate": 0.5,
                    "ted_buggy_fixed": 5,
                },
            ],
        }
        selected = choose_budgeted(row, 20)
        self.assertTrue(selected["repaired"])
        self.assertEqual(selected["selected_source"], "iteration-2")

    def test_problem_balanced_sample_is_deterministic_and_complete(self) -> None:
        rows = [
            {"example_id": "a", "problem_id": "p1"},
            {"example_id": "b", "problem_id": "p1"},
            {"example_id": "c", "problem_id": "p2"},
        ]
        first = sample_problems(rows, 2027)
        second = sample_problems(list(reversed(rows)), 2027)
        self.assertEqual(first, second)
        self.assertEqual({row["problem_id"] for row in first}, {"p1", "p2"})

    def test_execution_selection_enforces_one_candidate_per_relation(self) -> None:
        def rows(repaired_ids: set[str]) -> list[dict]:
            return [
                {
                    "example_id": example_id,
                    "problem_id": example_id,
                    "buggy_pass_rate": 0.0,
                    "fixed_pass_rate": 1.0 if example_id in repaired_ids else 0.0,
                    "repaired": example_id in repaired_ids,
                    "improved": example_id in repaired_ids,
                    "ted_buggy_fixed": 1,
                }
                for example_id in ("a", "b", "c", "d")
            ]

        evaluations = {
            "P1": rows({"a", "b"}),
            "P2": rows({"a"}),
            "P3": rows({"b"}),
            "S1": rows({"c"}),
            "S2": rows(set()),
            "S3": rows(set()),
            "A1": rows({"d"}),
            "A2": rows(set()),
            "A3": rows(set()),
        }
        relations = {
            name: {"P": "Progress", "S": "Strict", "A": "Answer"}[name[0]]
            for name in evaluations
        }
        report = select_portfolios(evaluations, relations)
        selected = report["selected_relation_constrained"]
        self.assertEqual(set(selected["members"]), {"P1", "S1", "A1"})
        self.assertEqual(selected["score"]["repaired"], 4)
        budget_selected = report["selected_budget_aware_relation_constrained"]
        self.assertEqual(set(budget_selected["members"]), {"P1", "S1", "A1"})
        self.assertEqual(
            set(budget_selected["score"]["repair_rate_by_max_ted"]),
            {"5", "10", "20", "40", "80", "160"},
        )
        self.assertEqual(
            set(report["selected_relation_constrained_by_budget"]),
            {"5", "10", "20", "40", "80", "160"},
        )
        self.assertEqual(
            set(report["selected_unconstrained_by_budget"]),
            {"5", "10", "20", "40", "80", "160"},
        )
        self.assertEqual(report["feasible_relation_constrained_portfolios"], 27)
        self.assertEqual(report["feasible_unconstrained_size_three_portfolios"], 84)
        self.assertEqual(
            set(report["best_unconstrained"]["members"]), {"P1", "S1", "A1"}
        )

    def test_execution_selection_accepts_codeworkout_current_pass_rate(self) -> None:
        def rows(repaired_ids: set[str]) -> list[dict]:
            return [
                {
                    "example_id": example_id,
                    "problem_id": example_id,
                    "current_pass_rate": 0.0,
                    "fixed_pass_rate": 1.0 if example_id in repaired_ids else 0.0,
                    "repaired": example_id in repaired_ids,
                    "improved": example_id in repaired_ids,
                }
                for example_id in ("a", "b", "c")
            ]

        evaluations = {
            "P1": rows({"a"}), "P2": rows(set()), "P3": rows(set()),
            "S1": rows({"b"}), "S2": rows(set()), "S3": rows(set()),
            "A1": rows({"c"}), "A2": rows(set()), "A3": rows(set()),
        }
        relations = {
            name: {"P": "Progress", "S": "Strict", "A": "Answer"}[name[0]]
            for name in evaluations
        }
        selected = select_portfolios(evaluations, relations)[
            "selected_relation_constrained"
        ]
        self.assertEqual(set(selected["members"]), {"P1", "S1", "A1"})
        self.assertEqual(selected["score"]["repair_rate"], 1.0)
        no_budget = select_portfolios(
            evaluations, relations, include_budget_objective=False
        )
        self.assertIsNone(no_budget["selected_budget_aware_relation_constrained"])
        self.assertIsNone(no_budget["selected_relation_constrained_by_budget"])
        self.assertIsNone(no_budget["selected_unconstrained_by_budget"])
        self.assertIsNone(no_budget["budget_aware_objective"])

    def test_complete_budget_curve_contrast_is_paired_and_clustered(self) -> None:
        def row(example_id: str, problem_id: str, ted: int) -> dict:
            return {
                "example_id": example_id,
                "problem_id": problem_id,
                "repaired": True,
                "ted_buggy_fixed": ted,
            }

        left = [row("a", "p1", 4), row("b", "p1", 9), row("c", "p2", 19)]
        right = [row("a", "p1", 9), row("b", "p1", 19), row("c", "p2", 39)]
        def gated(rows: list[dict]) -> dict[int, list[dict]]:
            return {
                budget: [
                    {**item, "repaired": item["ted_buggy_fixed"] <= budget}
                    for item in rows
                ]
                for budget in (5, 10, 20, 40, 80, 160)
            }

        report = clustered_mean_budget_difference(
            gated(left), gated(right), samples=200, seed=7
        )
        self.assertGreater(report["difference"], 0)
        self.assertEqual(report["budgets"], [5, 10, 20, 40, 80, 160])
        self.assertEqual(report["bootstrap_samples"], 200)
        self.assertGreater(report["problem_cluster_95ci"][0], 0)

    def test_answer_control_reproduction_fails_closed(self) -> None:
        row = {
            "example_id": "e",
            "repaired": True,
            "improved": True,
            "fixed_pass_rate": 1.0,
        }
        self.assertEqual(
            assert_same_answer_control([row], [dict(row)])["outcome_mismatches"],
            0,
        )
        with self.assertRaisesRegex(ValueError, "differs on 1 outcomes"):
            assert_same_answer_control(
                [row], [{**row, "repaired": False, "fixed_pass_rate": 0.5}]
            )

    def test_holm_adjustment_is_monotone_and_named(self) -> None:
        adjusted = holm_adjust({"a": 0.01, "b": 0.03, "c": 0.2})
        self.assertAlmostEqual(adjusted["a"]["holm_adjusted_p"], 0.03)
        self.assertAlmostEqual(adjusted["b"]["holm_adjusted_p"], 0.06)
        self.assertAlmostEqual(adjusted["c"]["holm_adjusted_p"], 0.2)

    def test_relation_seed_selection_uses_validation_loss_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            entries = []
            expected = {"Progress": 2027, "Strict": 2028, "Answer": 2029}
            for relation in expected:
                for seed in (2027, 2028, 2029):
                    checkpoint = root / relation / str(seed)
                    checkpoint.mkdir(parents=True)
                    loss = 0.2 + abs(seed - expected[relation]) / 1000
                    (checkpoint / "training_summary.json").write_text(
                        json.dumps({"best_eval_loss": loss, "validation_examples": 5}),
                        encoding="utf-8",
                    )
                    entries.append((relation, seed, checkpoint))
            report = select(entries)
        self.assertFalse(report["test_outcomes_used"])
        self.assertEqual(
            {key: value["seed"] for key, value in report["selected"].items()},
            expected,
        )

    def test_seed_policy_generations_merges_identical_sources(self) -> None:
        dataset = [{"example_id": "a"}, {"example_id": "b"}]
        direct = [[{"example_id": "a", "generated_code": "x", "method": "old"}]]
        sequential = [
            (
                "Strict",
                [
                    {
                        "example_id": "b",
                        "problem_id": "p",
                        "user_id": "u",
                        "candidate_outcomes": [
                            {"source": "Strict", "generated_code": "y"}
                        ],
                    }
                ],
            )
        ]
        rows = seed_rows(
            dataset,
            method="Strict2028",
            generation_sources=direct,
            sequential_sources=sequential,
        )
        self.assertEqual([row["example_id"] for row in rows], ["a", "b"])
        self.assertTrue(all(row["method"] == "Strict2028" for row in rows))

    def test_extracts_only_invoked_answer_candidate(self) -> None:
        dataset = [
            {"example_id": "a"},
            {"example_id": "b"},
        ]
        sequential = [
            {
                "example_id": "a",
                "problem_id": "p",
                "user_id": "u",
                "prompt_style": "D",
                "candidate_outcomes": [
                    {"source": "Progress", "generated_code": "x"},
                    {
                        "source": "Answer",
                        "generated_code": "fixed",
                        "raw_generation": "fixed",
                        "generation_time_sec": 1.5,
                    },
                ],
            },
            {
                "example_id": "b",
                "problem_id": "p",
                "user_id": "u2",
                "candidate_outcomes": [{"source": "Strict", "generated_code": "y"}],
            },
        ]
        rows = extract(dataset, sequential, method="Answer2028")
        self.assertEqual([row["example_id"] for row in rows], ["a"])
        self.assertEqual(rows[0]["generated_code"], "fixed")
        self.assertTrue(rows[0]["reused_from_sequential_evaluation"])

    def test_user_overlap_strata_are_disjoint_and_complete(self) -> None:
        rows = [
            {"example_id": "a", "user_id": "known"},
            {"example_id": "b", "user_id": "new"},
        ]
        groups = stratify(rows, {"known"})
        self.assertEqual(
            [row["example_id"] for row in groups["train_user_overlap"]], ["a"]
        )
        self.assertEqual(
            [row["example_id"] for row in groups["train_user_disjoint"]], ["b"]
        )

    def test_checkpoint_audit_requires_matching_controls_and_distinct_weights(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            checkpoints = []
            for seed in (2027, 2028, 2029):
                checkpoint = root / str(seed)
                checkpoint.mkdir()
                (checkpoint / "training_summary.json").write_text(
                    json.dumps(
                        {
                            "dataset_path": "/data/train-answer.jsonl",
                            "source_examples": 40_454,
                            "validation_examples": 4_965,
                        }
                    ),
                    encoding="utf-8",
                )
                (checkpoint / "adapter_model.safetensors").write_bytes(
                    f"weights-{seed}".encode()
                )
                checkpoints.append((seed, checkpoint))
            audit = audit_checkpoints(checkpoints)
        self.assertTrue(audit["training_controls_match"])
        self.assertTrue(audit["adapter_weights_are_pairwise_distinct"])
        self.assertTrue(audit["valid_independent_seed_control"])

    def test_checkpoint_audit_rejects_duplicate_weights(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            checkpoints = []
            for seed in (2027, 2028, 2029):
                checkpoint = root / str(seed)
                checkpoint.mkdir()
                (checkpoint / "training_summary.json").write_text(
                    json.dumps({"dataset_path": "/data/train-answer.jsonl"}),
                    encoding="utf-8",
                )
                (checkpoint / "adapter_model.safetensors").write_bytes(b"same")
                checkpoints.append((seed, checkpoint))
            audit = audit_checkpoints(checkpoints)
        self.assertFalse(audit["adapter_weights_are_pairwise_distinct"])
        self.assertFalse(audit["valid_independent_seed_control"])

    def test_claim_requires_positive_problem_cluster_lower_bound(self) -> None:
        report = {
            "exact_mcnemar_two_sided_p": 0.01,
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": 0.04,
                    "cluster_bootstrap_95ci": [0.01, 0.07],
                }
            ],
        }
        contrast = rr_contrast(report)
        self.assertTrue(contrast["supports_heterogeneous_target_claim"])

    def test_claim_is_not_supported_when_interval_includes_zero(self) -> None:
        report = {
            "exact_mcnemar_two_sided_p": 0.4,
            "paired": [
                {
                    "metric": "rr",
                    "left_minus_right_instance_weighted": 0.01,
                    "cluster_bootstrap_95ci": [-0.02, 0.04],
                }
            ],
        }
        contrast = rr_contrast(report)
        self.assertFalse(contrast["supports_heterogeneous_target_claim"])

    def test_sparse_stages_compose_with_early_stop_and_fallback(self) -> None:
        dataset = [
            {"example_id": "a"},
            {"example_id": "b"},
            {"example_id": "c"},
        ]

        def row(example_id: str, fixed: float, *, repaired: bool, ted: int) -> dict:
            return {
                "example_id": example_id,
                "problem_id": "p",
                "user_id": example_id,
                "buggy_pass_rate": 0.25,
                "fixed_pass_rate": fixed,
                "repaired": repaired,
                "improved": fixed > 0.25,
                "ted_buggy_fixed": ted,
                "ted_fixed_oracle": ted + 1,
            }

        stages = [
            (
                "Answer2027",
                [
                    row("a", 1.0, repaired=True, ted=8),
                    row("b", 0.5, repaired=False, ted=6),
                    row("c", 0.1, repaired=False, ted=4),
                ],
            ),
            (
                "Answer2028",
                [
                    row("b", 1.0, repaired=True, ted=7),
                    row("c", 0.5, repaired=False, ted=9),
                ],
            ),
            ("Answer2029", [row("c", 0.5, repaired=False, ted=3)]),
        ]
        rows = compose(dataset, stages)
        by_id = {item["example_id"]: item for item in rows}
        self.assertEqual(by_id["a"]["candidate_count"], 1)
        self.assertEqual(by_id["b"]["selected_source"], "Answer2028")
        self.assertEqual(by_id["c"]["selected_source"], "Answer2029")
        self.assertEqual(by_id["c"]["fixed_pass_rate"], 0.5)
        self.assertAlmostEqual(summarize(rows)["repair_rate"], 2 / 3)


if __name__ == "__main__":
    unittest.main()
