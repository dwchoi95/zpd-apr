from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .codenet import (
    audit_trajectory_contexts,
    build_python800_dataset,
    create_balanced_rq1_splits,
    create_longitudinal_splits,
    create_problem_holdout_split,
    create_seen_unseen_splits,
    create_volume_ordered_problem_manifests,
    filter_by_benchmark_accepted,
    refine_dataset,
    refine_submission_trajectories,
)
from .runner.dataset import run_problem_outcomes
from .runner.python_runner import PythonSubmissionRunner
from .repair import (
    build_current_code_only_dataset,
    build_repair_dataset,
    build_outcome_cache,
    compare_rq1,
    evaluate_generations,
    filter_rq1_examples,
    evaluate_ordered_generations,
    extract_stage_generations,
    generate_candidate_repairs,
    generate_repairs,
    generate_lsgen_repairs,
    merge_generation_candidates,
    rescore_evaluations,
    run_zero_shot_repairs,
    run_sequential_repairs,
    sample_repair_dataset,
    select_prompt,
    select_candidate_repairs,
    select_evaluated_candidates,
    sample_repair_examples,
    train_qlora,
)


DEFAULT_CODENET_ROOT = Path("/Users/cdw/VSCode/aria/data/Project_CodeNet")
DEFAULT_PYTHON800_ROOT = (
    DEFAULT_CODENET_ROOT
    / "derived"
    / "benchmarks"
    / "Project_CodeNet_Python800"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="ZPDPatch command-line interface")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-data", help="Build the CodeNet Python800 dataset")
    build.add_argument("--source-root", type=Path, default=DEFAULT_CODENET_ROOT)
    build.add_argument("--output-root", type=Path, default=Path("data"))
    build.add_argument("--overwrite", action="store_true")
    build.add_argument("--require-testcases", action="store_true")

    refine = commands.add_parser("refine-data", help="Filter unusable trajectories")
    refine.add_argument("--data-root", type=Path, default=Path("data"))
    refine.add_argument("--min-problems", type=int, default=1)

    refine_trajectories = commands.add_parser(
        "refine-trajectories",
        help="Normalize and truncate trajectories at their first Accepted submission",
    )
    refine_trajectories.add_argument("--data-root", type=Path, default=Path("data"))
    refine_trajectories.add_argument("--min-submissions", type=int, default=3)

    benchmark_accepted = commands.add_parser(
        "filter-benchmark-accepted",
        help="Keep trajectories ending in a Python800 benchmark Accepted program",
    )
    benchmark_accepted.add_argument("--data-root", type=Path, default=Path("data"))
    benchmark_accepted.add_argument(
        "--benchmark-root",
        type=Path,
        default=DEFAULT_PYTHON800_ROOT,
    )
    benchmark_accepted.add_argument(
        "--min-trajectories-per-problem",
        type=int,
        default=2,
    )

    split = commands.add_parser("split-data", help="Create longitudinal splits")
    split.add_argument("--data-root", type=Path, default=Path("data"))

    split_problems = commands.add_parser(
        "split-problems",
        help="Create a physical problem-held-out split",
    )
    split_problems.add_argument("--data-root", type=Path, default=Path("data"))
    split_problems.add_argument("--seed", type=int, default=2027)

    commands.add_parser(
        "split-problems-by-volume",
        help="Create problem manifests ordered by descending trajectory volume",
    ).add_argument("--data-root", type=Path, default=Path("data"))

    balanced_rq1 = commands.add_parser(
        "split-rq1-balanced",
        help="Balance seen/unseen problems by trajectory volume and split each 80/20",
    )
    balanced_rq1.add_argument("--data-root", type=Path, default=Path("data"))
    balanced_rq1.add_argument("--seed", type=int, default=2027)

    seen_unseen = commands.add_parser(
        "split-seen-unseen",
        help=(
            "Assign high-volume problems 90:10 to Seen/Unseen and split "
            "Seen trajectories 80:10:10"
        ),
    )
    seen_unseen.add_argument("--data-root", type=Path, default=Path("data"))
    seen_unseen.add_argument("--seed", type=int, default=2027)
    seen_unseen.add_argument("--trajectory-context-manifest", type=Path)

    context_audit = commands.add_parser(
        "audit-trajectory-contexts",
        help="Exclude trajectories when any configuration exceeds 4,096 tokens",
    )
    context_audit.add_argument("--data-root", type=Path, default=Path("data"))
    context_audit.add_argument(
        "--output",
        type=Path,
        default=Path("data/trajectory_context_4k.jsonl"),
    )
    context_audit.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
    )

    run = commands.add_parser("run", help="Run submissions for one problem")
    run.add_argument("problem_dir", type=Path, help="Path like data/p02659")
    run.add_argument("--output-root", type=Path, default=Path("outputs"))
    run.add_argument("--timeout-sec", type=float, default=2.5)
    run.add_argument("--no-resume", action="store_true")

    repair_data = commands.add_parser(
        "build-repair-data",
        help="Materialize trajectory-prefix examples for SFT or evaluation",
    )
    repair_data.add_argument("--data-root", type=Path, default=Path("data"))
    repair_data.add_argument(
        "--split",
        choices=(
            "train",
            "valid",
            "test",
            "seen_train",
            "seen_valid",
            "seen_test",
            "unseen_test",
        ),
        required=True,
    )
    repair_data.add_argument(
        "--target-mode",
        choices=(
            "all",
            "non-worsening",
            "strict-improvement",
            "hybrid-productive",
            "productive",
            "same-severity-productive",
            "progress",
            "strict",
            "answer",
            "final",
            "final-accepted",
        ),
        default=None,
    )
    repair_data.add_argument(
        "--exclude-accepted-targets",
        action="store_true",
        help="Exclude transitions whose target submission is Accepted",
    )
    repair_data.add_argument("--output", type=Path, default=None)
    repair_data.add_argument("--outcome-cache", type=Path, default=None)

    current_only_data = commands.add_parser(
        "make-current-code-only",
        help="Remove prior submissions and reset the current position for RQ2",
    )
    current_only_data.add_argument("dataset", type=Path)
    current_only_data.add_argument("output", type=Path)

    sample_data = commands.add_parser(
        "sample-repair-data-grouped",
        help="Create a deterministic problem-balanced repair dataset sample",
    )
    sample_data.add_argument("dataset", type=Path)
    sample_data.add_argument("output", type=Path)
    sample_data.add_argument("--size", type=int, required=True)
    sample_data.add_argument("--max-examples-per-problem", type=int, default=4)
    sample_data.add_argument("--seed", type=int, default=2027)

    outcome_cache = commands.add_parser(
        "build-outcome-cache",
        help="Execute unique submissions and cache compact per-test outcomes",
    )
    outcome_cache.add_argument(
        "--data-root", type=Path, default=Path("data")
    )
    outcome_cache.add_argument(
        "--split",
        choices=(
            "train",
            "valid",
            "test",
            "seen_train",
            "seen_valid",
            "seen_test",
            "unseen_test",
        ),
        required=True,
    )
    outcome_cache.add_argument("--output", type=Path, default=None)
    outcome_cache.add_argument("--workers", type=int, default=24)
    outcome_cache.add_argument("--case-workers", type=int, default=1)
    outcome_cache.add_argument("--timeout-sec", type=float, default=2.5)
    outcome_cache.add_argument("--no-resume", action="store_true")

    filter_rq1 = commands.add_parser(
        "filter-rq1-data",
        help="Keep examples whose buggy program is non-AC and oracle is AC locally",
    )
    filter_rq1.add_argument("dataset", type=Path)
    filter_rq1.add_argument("outcome_cache", type=Path)
    filter_rq1.add_argument("output", type=Path)

    sample_repair = commands.add_parser(
        "sample-repair-examples",
        help="Select a deterministic problem-diverse repair evaluation subset",
    )
    sample_repair.add_argument("dataset", type=Path)
    sample_repair.add_argument("output", type=Path)
    sample_repair.add_argument("--size", type=int, required=True)
    sample_repair.add_argument("--seed", type=int, default=2027)

    train = commands.add_parser("train-qlora", help="Fine-tune a repair model with QLoRA")
    train.add_argument("dataset", type=Path)
    train.add_argument("output_dir", type=Path)
    train.add_argument(
        "--prompt", choices=("A", "B", "C", "D", "a", "b", "c", "d"), required=True
    )
    train.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-1.5B-Instruct",
    )
    train.add_argument("--epochs", type=float, default=1.0)
    train.add_argument("--learning-rate", type=float, default=2e-4)
    train.add_argument("--edit-token-weight", type=float, default=1.0)
    train.add_argument("--validation-dataset", type=Path, default=None)
    train.add_argument("--eval-steps", type=int, default=100)
    train.add_argument("--early-stopping-patience", type=int, default=3)
    train.add_argument("--save-steps", type=int, default=0)
    train.add_argument("--seed", type=int, default=2027)
    train.add_argument("--batch-size", type=int, default=1)
    train.add_argument("--gradient-accumulation", type=int, default=16)
    train.add_argument("--resume-from-checkpoint", type=Path, default=None)

    generate = commands.add_parser("generate", help="Generate repairs with a base or SFT model")
    generate.add_argument("dataset", type=Path)
    generate.add_argument("output", type=Path)
    generate.add_argument("--method", required=True)
    generate.add_argument(
        "--prompt", choices=("A", "B", "C", "D", "a", "b", "c", "d"), required=True
    )
    generate.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-1.5B-Instruct",
    )
    generate.add_argument("--adapter", type=Path, default=None)
    generate.add_argument("--batch-size", type=int, default=1)
    generate.add_argument("--no-resume", action="store_true")

    zero_shot = commands.add_parser(
        "repair-zero-shot",
        help="Run up to three execution-guided zero-shot repair attempts",
    )
    zero_shot.add_argument("dataset", type=Path)
    zero_shot.add_argument("output", type=Path)
    zero_shot.add_argument("--data-root", type=Path, default=Path("data"))
    zero_shot.add_argument("--method", default="Zero-shot")
    zero_shot.add_argument(
        "--prompt",
        choices=("A", "B", "C", "D", "a", "b", "c", "d"),
        default="D",
    )
    zero_shot.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
    )
    zero_shot.add_argument("--max-attempts", type=int, default=3)
    zero_shot.add_argument("--batch-size", type=int, default=1)
    zero_shot.add_argument("--workers", type=int, default=1)
    zero_shot.add_argument("--case-workers", type=int, default=1)
    zero_shot.add_argument("--timeout-sec", type=float, default=2.5)
    zero_shot.add_argument("--no-resume", action="store_true")

    sequential = commands.add_parser(
        "repair-sequential",
        help="Generate, execute, and select repairs from ordered adapters",
    )
    sequential.add_argument("dataset", type=Path)
    sequential.add_argument("output", type=Path)
    sequential.add_argument("--data-root", type=Path, default=Path("data"))
    sequential.add_argument("--method", default="ZPDPatch")
    sequential.add_argument(
        "--prompt",
        choices=("A", "B", "C", "D", "a", "b", "c", "d"),
        default="D",
    )
    sequential.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
    )
    sequential.add_argument(
        "--adapter",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="Ordered adapter stage; repeat for Progress, Strict, and Answer",
    )
    sequential.add_argument("--batch-size", type=int, default=1)
    sequential.add_argument("--workers", type=int, default=8)
    sequential.add_argument("--case-workers", type=int, default=1)
    sequential.add_argument("--timeout-sec", type=float, default=2.5)
    sequential.add_argument(
        "--outcome-cache",
        type=Path,
        default=None,
        help="Cached execution evidence used to enrich every historical submission",
    )
    feedback = sequential.add_mutually_exclusive_group()
    feedback.add_argument(
        "--stage-feedback",
        dest="stage_feedback",
        action="store_true",
        help="Append earlier generated outcomes to later adapter prompts (ablation)",
    )
    feedback.add_argument(
        "--no-stage-feedback",
        dest="stage_feedback",
        action="store_false",
        help="Give every adapter the same observed trajectory (default)",
    )
    sequential.set_defaults(stage_feedback=False)
    sequential.add_argument("--no-resume", action="store_true")

    ordered_evaluate = commands.add_parser(
        "evaluate-ordered",
        help="Evaluate ordered adapter generations with shared deterministic outcomes",
    )
    ordered_evaluate.add_argument("dataset", type=Path)
    ordered_evaluate.add_argument("output_dir", type=Path)
    ordered_evaluate.add_argument("--data-root", type=Path, default=Path("data"))
    ordered_evaluate.add_argument("--method", default="ZPDPatch")
    ordered_evaluate.add_argument(
        "--prompt",
        choices=("A", "B", "C", "D", "a", "b", "c", "d"),
        default="D",
    )
    ordered_evaluate.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
    )
    ordered_evaluate.add_argument(
        "--generation",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="Ordered generation source; repeat for each adapter stage",
    )
    ordered_evaluate.add_argument("--workers", type=int, default=1)
    ordered_evaluate.add_argument(
        "--ted-workers",
        type=int,
        default=None,
        help="Separate process count for tree-edit distance computation",
    )
    ordered_evaluate.add_argument("--timeout-sec", type=float, default=2.5)
    ordered_evaluate.add_argument(
        "--outcome-cache",
        type=Path,
        default=None,
        help="Complete original-submission outcomes used to skip current-code execution",
    )

    stage_generations = commands.add_parser(
        "extract-stage-generations",
        help="Recover adapter generations from sequential evaluation output",
    )
    stage_generations.add_argument("evaluation", type=Path)
    stage_generations.add_argument("output_dir", type=Path)
    stage_generations.add_argument(
        "--stage",
        action="append",
        default=[],
        help="Stage to extract; defaults to progress, strict, and answer",
    )

    candidates = commands.add_parser(
        "generate-candidates",
        help="Generate complementary base and trajectory-adapter repair candidates",
    )
    candidates.add_argument("dataset", type=Path)
    candidates.add_argument("output", type=Path)
    candidates.add_argument(
        "--prompt", choices=("A", "B", "C", "D", "a", "b", "c", "d"), required=True
    )
    candidates.add_argument("--base-model", required=True)
    candidates.add_argument("--adapter", type=Path, required=True)
    candidates.add_argument("--sampled-candidates", type=int, default=4)
    candidates.add_argument("--temperature", type=float, default=0.7)
    candidates.add_argument("--top-p", type=float, default=0.95)
    candidates.add_argument("--seed", type=int, default=2027)
    candidates.add_argument("--no-resume", action="store_true")

    merge_candidates = commands.add_parser(
        "merge-candidates",
        help="Merge existing generation files for execution-guided selection",
    )
    merge_candidates.add_argument("output", type=Path)
    merge_candidates.add_argument(
        "--generation",
        action="append",
        required=True,
        metavar="SOURCE=PATH",
    )

    candidate_select = commands.add_parser(
        "select-candidates",
        help="Execute and select the strongest non-regressive repair candidate",
    )
    candidate_select.add_argument("dataset", type=Path)
    candidate_select.add_argument("candidates", type=Path)
    candidate_select.add_argument("output", type=Path)
    candidate_select.add_argument("--method", required=True)
    candidate_select.add_argument("--data-root", type=Path, default=Path("data"))
    candidate_select.add_argument("--workers", type=int, default=8)
    candidate_select.add_argument("--timeout-sec", type=float, default=2.5)

    evaluated_select = commands.add_parser(
        "select-evaluated-candidates",
        help="Select candidates using existing execution-evaluation files",
    )
    evaluated_select.add_argument("dataset", type=Path)
    evaluated_select.add_argument("output", type=Path)
    evaluated_select.add_argument("--method", required=True)
    evaluated_select.add_argument(
        "--evaluation",
        action="append",
        required=True,
        metavar="SOURCE=PATH",
    )

    evaluate = commands.add_parser("evaluate", help="Execute and score generated repairs")
    evaluate.add_argument("dataset", type=Path)
    evaluate.add_argument("generations", type=Path)
    evaluate.add_argument("output", type=Path)
    evaluate.add_argument("--data-root", type=Path, default=Path("data"))
    evaluate.add_argument("--workers", type=int, default=8)
    evaluate.add_argument("--ted-workers", type=int, default=None)
    evaluate.add_argument("--timeout-sec", type=float, default=2.5)
    evaluate.add_argument("--no-resume", action="store_true")

    rescore = commands.add_parser(
        "rescore-evaluation",
        help="Recompute metrics from stored execution outcomes",
    )
    rescore.add_argument("dataset", type=Path)
    rescore.add_argument("evaluations", type=Path)
    rescore.add_argument("output", type=Path)

    lsgen = commands.add_parser(
        "generate-lsgen",
        help="Run the official LSGen pipeline adapted to the shared dataset and model",
    )
    lsgen.add_argument("dataset", type=Path)
    lsgen.add_argument("output", type=Path)
    lsgen.add_argument("--data-root", type=Path, default=Path("data"))
    lsgen.add_argument(
        "--retrieval-dataset",
        type=Path,
        default=None,
        help="Optional peer trajectory pool; query examples still come from dataset",
    )
    lsgen.add_argument(
        "--base-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
    )
    lsgen.add_argument("--embedding-model", default="microsoft/unixcoder-base")
    lsgen.add_argument("--topk", type=int, default=5)
    lsgen.add_argument("--max-iterations", type=int, default=3)
    lsgen.add_argument("--description-batch-size", type=int, default=8)
    lsgen.add_argument("--retention-threshold", type=float, default=0.5)
    lsgen.add_argument("--workers", type=int, default=8)
    lsgen.add_argument("--case-workers", type=int, default=1)
    lsgen.add_argument("--timeout-sec", type=float, default=2.5)
    lsgen.add_argument("--no-resume", action="store_true")

    choose_prompt = commands.add_parser(
        "select-prompt",
        help="Select A or B by RR, IR, TED, and ATT in that order",
    )
    choose_prompt.add_argument("prompt_a_summary", type=Path)
    choose_prompt.add_argument("prompt_b_summary", type=Path)
    choose_prompt.add_argument("output", type=Path)

    compare = commands.add_parser(
        "compare-rq1",
        help="Aggregate RQ1 metrics and paired repair-rate tests",
    )
    compare.add_argument("output", type=Path)
    compare.add_argument(
        "--evaluation",
        action="append",
        required=True,
        metavar="METHOD=PATH",
    )

    args = parser.parse_args()
    if args.command == "build-data":
        summary = build_python800_dataset(
            args.source_root,
            args.output_root,
            overwrite=args.overwrite,
            require_testcases=args.require_testcases,
        )
        for key, value in asdict(summary).items():
            print(f"{key}: {value}")
        return

    if args.command == "refine-data":
        summary = refine_dataset(
            args.data_root,
            min_problems_per_user=args.min_problems,
        )
        for key, value in asdict(summary).items():
            print(f"{key}: {value}")
        return

    if args.command == "refine-trajectories":
        summary = refine_submission_trajectories(
            args.data_root,
            minimum_submissions=args.min_submissions,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
        return

    if args.command == "filter-benchmark-accepted":
        summary = filter_by_benchmark_accepted(
            args.data_root,
            args.benchmark_root,
            minimum_trajectories_per_problem=args.min_trajectories_per_problem,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))
        return

    if args.command == "split-data":
        summary = create_longitudinal_splits(args.data_root)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "split-problems":
        summary = create_problem_holdout_split(args.data_root, seed=args.seed)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "split-problems-by-volume":
        summary = create_volume_ordered_problem_manifests(args.data_root)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "split-rq1-balanced":
        summary = create_balanced_rq1_splits(args.data_root, seed=args.seed)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "split-seen-unseen":
        summary = create_seen_unseen_splits(
            args.data_root,
            seed=args.seed,
            trajectory_context_manifest=args.trajectory_context_manifest,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "audit-trajectory-contexts":
        summary = audit_trajectory_contexts(
            args.data_root,
            args.output,
            base_model=args.base_model,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "build-repair-data":
        output = args.output or Path("outputs/datasets") / f"{args.split}.jsonl"
        summary = build_repair_dataset(
            args.data_root,
            split=args.split,
            output_path=output,
            target_mode=args.target_mode,
            exclude_accepted_targets=args.exclude_accepted_targets,
            outcome_cache_path=args.outcome_cache,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "make-current-code-only":
        summary = build_current_code_only_dataset(args.dataset, args.output)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "sample-repair-data-grouped":
        summary = sample_repair_dataset(
            args.dataset,
            args.output,
            size=args.size,
            max_examples_per_problem=args.max_examples_per_problem,
            seed=args.seed,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "build-outcome-cache":
        output = args.output or Path("outputs/outcomes") / f"{args.split}.jsonl"
        summary = build_outcome_cache(
            args.data_root,
            split=args.split,
            output_path=output,
            workers=args.workers,
            case_workers=args.case_workers,
            timeout_sec=args.timeout_sec,
            resume=not args.no_resume,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "filter-rq1-data":
        summary = filter_rq1_examples(
            args.dataset,
            args.outcome_cache,
            args.output,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "sample-repair-examples":
        summary = sample_repair_examples(
            args.dataset,
            args.output,
            size=args.size,
            seed=args.seed,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "train-qlora":
        summary = train_qlora(
            args.dataset,
            args.output_dir,
            prompt_style=args.prompt,
            base_model=args.base_model,
            num_train_epochs=args.epochs,
            learning_rate=args.learning_rate,
            edit_token_weight=args.edit_token_weight,
            validation_dataset_path=args.validation_dataset,
            eval_steps=args.eval_steps,
            early_stopping_patience=args.early_stopping_patience,
            save_steps=args.save_steps,
            seed=args.seed,
            per_device_batch_size=args.batch_size,
            gradient_accumulation_steps=args.gradient_accumulation,
            resume_from_checkpoint=args.resume_from_checkpoint,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "generate":
        summary = generate_repairs(
            args.dataset,
            args.output,
            method=args.method,
            prompt_style=args.prompt,
            base_model=args.base_model,
            adapter_path=args.adapter,
            batch_size=args.batch_size,
            resume=not args.no_resume,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "repair-zero-shot":
        summary = run_zero_shot_repairs(
            args.data_root,
            args.dataset,
            args.output,
            method=args.method,
            prompt_style=args.prompt,
            base_model=args.base_model,
            max_attempts=args.max_attempts,
            batch_size=args.batch_size,
            workers=args.workers,
            case_workers=args.case_workers,
            timeout_sec=args.timeout_sec,
            resume=not args.no_resume,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "repair-sequential":
        adapters: list[tuple[str, Path]] = []
        for value in args.adapter:
            name, separator, path = value.partition("=")
            if not separator or not name or not path:
                parser.error("--adapter must use NAME=PATH")
            adapters.append((name, Path(path)))
        summary = run_sequential_repairs(
            args.data_root,
            args.dataset,
            args.output,
            adapters=adapters,
            method=args.method,
            prompt_style=args.prompt,
            base_model=args.base_model,
            batch_size=args.batch_size,
            workers=args.workers,
            case_workers=args.case_workers,
            timeout_sec=args.timeout_sec,
            stage_feedback=args.stage_feedback,
            outcome_cache_path=args.outcome_cache,
            resume=not args.no_resume,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "evaluate-ordered":
        generation_paths: list[tuple[str, Path]] = []
        for value in args.generation:
            name, separator, path = value.partition("=")
            if not separator or not name or not path:
                parser.error("--generation must use NAME=PATH")
            generation_paths.append((name, Path(path)))
        summary = evaluate_ordered_generations(
            args.data_root,
            args.dataset,
            args.output_dir,
            generation_paths=generation_paths,
            method=args.method,
            prompt_style=args.prompt,
            base_model=args.base_model,
            workers=args.workers,
            ted_workers=args.ted_workers,
            timeout_sec=args.timeout_sec,
            outcome_cache_path=args.outcome_cache,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "extract-stage-generations":
        stages = tuple(args.stage) if args.stage else ("progress", "strict", "answer")
        summary = extract_stage_generations(
            args.evaluation,
            args.output_dir,
            stages=stages,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "generate-candidates":
        summary = generate_candidate_repairs(
            args.dataset,
            args.output,
            prompt_style=args.prompt,
            base_model=args.base_model,
            adapter_path=args.adapter,
            sampled_candidates=args.sampled_candidates,
            temperature=args.temperature,
            top_p=args.top_p,
            seed=args.seed,
            resume=not args.no_resume,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "merge-candidates":
        generation_paths: list[tuple[str, Path]] = []
        for value in args.generation:
            source, separator, path = value.partition("=")
            if not separator or not source or not path:
                parser.error("--generation must use SOURCE=PATH")
            generation_paths.append((source, Path(path)))
        summary = merge_generation_candidates(generation_paths, args.output)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "select-candidates":
        summary = select_candidate_repairs(
            args.data_root,
            args.dataset,
            args.candidates,
            args.output,
            method=args.method,
            workers=args.workers,
            timeout_sec=args.timeout_sec,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "select-evaluated-candidates":
        evaluation_paths: list[tuple[str, Path]] = []
        for value in args.evaluation:
            source, separator, path = value.partition("=")
            if not separator or not source or not path:
                parser.error("--evaluation must use SOURCE=PATH")
            evaluation_paths.append((source, Path(path)))
        summary = select_evaluated_candidates(
            args.dataset,
            evaluation_paths,
            args.output,
            method=args.method,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "evaluate":
        summary = evaluate_generations(
            args.data_root,
            args.dataset,
            args.generations,
            args.output,
            workers=args.workers,
            timeout_sec=args.timeout_sec,
            resume=not args.no_resume,
            ted_workers=args.ted_workers,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "rescore-evaluation":
        summary = rescore_evaluations(args.dataset, args.evaluations, args.output)
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "generate-lsgen":
        summary = generate_lsgen_repairs(
            args.dataset,
            args.output,
            data_root=args.data_root,
            retrieval_dataset_path=args.retrieval_dataset,
            base_model=args.base_model,
            embedding_model=args.embedding_model,
            topk=args.topk,
            max_iterations=args.max_iterations,
            retention_threshold=args.retention_threshold,
            workers=args.workers,
            case_workers=args.case_workers,
            resume=not args.no_resume,
            timeout_sec=args.timeout_sec,
        )
        print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "select-prompt":
        result = select_prompt(
            args.prompt_a_summary,
            args.prompt_b_summary,
            args.output,
        )
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2, default=str))
        return

    if args.command == "compare-rq1":
        evaluations: dict[str, Path] = {}
        for value in args.evaluation:
            if "=" not in value:
                parser.error("--evaluation must use METHOD=PATH")
            method, path = value.split("=", 1)
            if not method or method in evaluations:
                parser.error(f"Invalid or duplicate evaluation method: {method}")
            evaluations[method] = Path(path)
        result = compare_rq1(evaluations, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    output = run_problem_outcomes(
        args.problem_dir,
        runner=PythonSubmissionRunner(timeout_sec=args.timeout_sec),
        output_root=args.output_root,
        resume=not args.no_resume,
    )
    print(output)
