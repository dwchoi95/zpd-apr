from __future__ import annotations

import argparse
import json
import runpy
import sys
from dataclasses import asdict
from pathlib import Path

# run.py <command> [arguments] runs src/experiments/<module>.py with those arguments (<command> --help lists them).
EXPERIMENTS = {
    "hold-out-students": ("hold_out_students", "drop the RQ1 benchmark's students from a training dataset"),
    "sample-validation": ("sample_problem_balanced_dataset", "draw one validation input per problem for Select"),
    "select": ("select_execution_portfolio", "choose the cascade from the checkpoints' validation evaluations"),
    "compose": ("compose_answer_seed_control", "run evaluated checkpoints as a cascade (Algorithm 1)"),
    "normalize-baseline": ("normalize_evaluation_baseline", "take the submission's verdict and pass rate from a reference evaluation"),
    "generate-greedy": ("generate_vllm_greedy_adapters", "generate one greedy repair per input for several adapters with vLLM"),
    "generate-samples": ("generate_vllm_stochastic_candidates", "draw sampled repairs from one model with vLLM"),
    "paired-control": ("build_paired_target_control", "pair Answer and Progress examples whose targets differ"),
    "paired-strict": ("build_paired_strict_control", "give the paired Answer examples Strict targets"),
    "cross-user-control": ("build_cross_user_target_control", "replace Progress targets with another student's submission"),
    "finalize-cross-user": ("finalize_cross_user_target_control", "keep the examples both target sources cover"),
    "java-prepare": ("prepare_codeworkout_evaluation", "write Java sources for every returned program and test case"),
    "java-judge": ("judge_codeworkout_in_container", "compile and run the Java sources in the judge image"),
    "java-collect": ("collect_codeworkout_evaluation", "turn the judge's statuses into evaluation rows"),
    "differential": ("differential.diff", "run plausible patches on generated inputs"),
    "differential-check": ("differential.check_constraints", "assert every generated input satisfies its problem's constraints"),
    "differential-own": ("differential.vs_own", "compare failing patches with the student's own accepted program"),
    "sampled-ted": ("sampled_ablation_ted", "TED of the repaired returns of the sampled ablation variants"),
    "codenet-attempts": ("codenet_attempts", "attempts to acceptance and verdict changes on every AtCoder problem"),
}
SPLITS = ("train", "valid", "test", "seen_train", "seen_valid", "seen_test", "unseen_test")
PROMPTS = ("A", "B", "C", "D", "a", "b", "c", "d")


def _print(summary: object) -> None:
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str))


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in EXPERIMENTS:
        command = sys.argv.pop(1)
        sys.argv[0] = f"run.py {command}"
        runpy.run_module(f"src.experiments.{EXPERIMENTS[command][0]}", run_name="__main__")
        return

    parser = argparse.ArgumentParser(
        description="ZPDPatch command-line interface",
        epilog="Experiment commands (run.py <command> --help):\n"
        + "\n".join(f"  {name:20s}{help}" for name, (_, help) in EXPERIMENTS.items()),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build-data", help="Build a data root from Project CodeNet or TIKTOC")
    build.add_argument("--benchmark", choices=("rq1", "seen-unseen", "codeworkout"), required=True,
                       help="rq1: the 14-problem RQ1 benchmark; seen-unseen: the Seen/Unseen corpus of RQ2-RQ4; "
                            "codeworkout: the Java corpus (--source-root is a TIKTOC checkout)")
    build.add_argument("--source-root", type=Path, required=True)
    build.add_argument("--output-root", type=Path, default=Path("data"))
    build.add_argument("--base-model", help="tokenizer for the 4,096-token filter (codeworkout)")
    build.add_argument("--image", default="zpdpatch-java:21", help="Java judge image built from docker/java (codeworkout)")
    build.add_argument("--overwrite", action="store_true")

    outcome_cache = commands.add_parser("build-outcome-cache", help="Execute every submission of a split once")
    outcome_cache.add_argument("--data-root", type=Path, default=Path("data"))
    outcome_cache.add_argument("--split", choices=SPLITS, required=True)
    outcome_cache.add_argument("--output", type=Path, required=True)
    outcome_cache.add_argument("--workers", type=int, default=24)
    outcome_cache.add_argument("--case-workers", type=int, default=1)
    outcome_cache.add_argument("--timeout-sec", type=float, default=2.5)
    outcome_cache.add_argument("--no-resume", action="store_true")

    repair_data = commands.add_parser("build-repair-data", help="Pair each buggy submission with its target (Mine)")
    repair_data.add_argument("--data-root", type=Path, default=Path("data"))
    repair_data.add_argument("--split", choices=SPLITS, required=True)
    repair_data.add_argument("--target-mode", choices=("answer", "strict", "progress", "final-accepted"), required=True,
                             help="final-accepted: each trajectory's last wrong submission with its accepted program (test inputs)")
    repair_data.add_argument("--outcome-cache", type=Path)
    repair_data.add_argument("--output", type=Path, required=True)

    current_only = commands.add_parser("make-current-code-only", help="Keep only the current submission in each prompt")
    current_only.add_argument("dataset", type=Path)
    current_only.add_argument("output", type=Path)

    filter_rq1 = commands.add_parser("filter-rq1-data",
                                     help="Keep inputs whose buggy program fails and whose accepted program passes locally")
    filter_rq1.add_argument("dataset", type=Path)
    filter_rq1.add_argument("outcome_cache", type=Path)
    filter_rq1.add_argument("output", type=Path)

    train = commands.add_parser("train-qlora", help="Fine-tune one QLoRA adapter (Train)")
    train.add_argument("dataset", type=Path)
    train.add_argument("output_dir", type=Path)
    train.add_argument("--prompt", choices=PROMPTS, required=True)
    train.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    train.add_argument("--epochs", type=float, default=1.0)
    train.add_argument("--learning-rate", type=float, default=2e-4)
    train.add_argument("--edit-token-weight", type=float, default=1.0)
    train.add_argument("--validation-dataset", type=Path)
    train.add_argument("--eval-steps", type=int, default=100)
    train.add_argument("--early-stopping-patience", type=int, default=2)
    train.add_argument("--save-steps", type=int, default=0)
    train.add_argument("--seed", type=int, default=2027)
    train.add_argument("--batch-size", type=int, default=2)
    train.add_argument("--gradient-accumulation", type=int, default=8)
    train.add_argument("--resume-from-checkpoint", type=Path)

    generate = commands.add_parser("generate", help="Generate one repair per input with a base model and an optional adapter")
    generate.add_argument("dataset", type=Path)
    generate.add_argument("output", type=Path)
    generate.add_argument("--method", required=True)
    generate.add_argument("--prompt", choices=PROMPTS, required=True)
    generate.add_argument("--base-model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    generate.add_argument("--adapter", type=Path)
    generate.add_argument("--batch-size", type=int, default=1)
    generate.add_argument("--max-new-tokens", type=int)
    generate.add_argument("--sampling-seed", type=int, help="sample with a per-input seed instead of decoding greedily")
    generate.add_argument("--temperature", type=float, default=0.8)
    generate.add_argument("--top-p", type=float, default=0.95)
    generate.add_argument("--no-resume", action="store_true")

    evaluate = commands.add_parser("evaluate", help="Judge returned programs on the test suite; compute TED and retention")
    evaluate.add_argument("dataset", type=Path)
    evaluate.add_argument("generations", type=Path)
    evaluate.add_argument("output", type=Path)
    evaluate.add_argument("--data-root", type=Path, default=Path("data"))
    evaluate.add_argument("--workers", type=int, default=8)
    evaluate.add_argument("--ted-workers", type=int)
    evaluate.add_argument("--baseline-reference", type=Path, help="reuse the submission's verdict and pass rate by example ID")
    evaluate.add_argument("--timeout-sec", type=float, default=2.5)
    evaluate.add_argument("--no-resume", action="store_true")

    args = parser.parse_args()
    if args.command == "build-data":
        if args.benchmark == "codeworkout":
            from .experiments.codeworkout_data import build_codeworkout_benchmark

            print(json.dumps(build_codeworkout_benchmark(args.source_root, args.output_root, base_model=args.base_model,
                                                         image=args.image, overwrite=args.overwrite)))
            return
        from .experiments.codenet import build_rq1_benchmark, build_seen_unseen_benchmark

        build_benchmark = build_rq1_benchmark if args.benchmark == "rq1" else build_seen_unseen_benchmark
        print(json.dumps(build_benchmark(args.source_root, args.output_root, overwrite=args.overwrite)))
    elif args.command == "build-outcome-cache":
        from .core.outcomes import build_outcome_cache

        _print(build_outcome_cache(args.data_root, split=args.split, output_path=args.output, workers=args.workers,
                                   case_workers=args.case_workers, timeout_sec=args.timeout_sec, resume=not args.no_resume))
    elif args.command == "build-repair-data":
        from .core.dataset import build_repair_dataset

        _print(build_repair_dataset(args.data_root, split=args.split, output_path=args.output, target_mode=args.target_mode,
                                    outcome_cache_path=args.outcome_cache))
    elif args.command == "make-current-code-only":
        from .core.dataset import build_current_code_only_dataset

        _print(build_current_code_only_dataset(args.dataset, args.output))
    elif args.command == "filter-rq1-data":
        from .core.filtering import filter_rq1_examples

        _print(filter_rq1_examples(args.dataset, args.outcome_cache, args.output))
    elif args.command == "train-qlora":
        from .core.train import train_qlora

        _print(train_qlora(
            args.dataset, args.output_dir, prompt_style=args.prompt, base_model=args.base_model,
            num_train_epochs=args.epochs, learning_rate=args.learning_rate, edit_token_weight=args.edit_token_weight,
            validation_dataset_path=args.validation_dataset, eval_steps=args.eval_steps,
            early_stopping_patience=args.early_stopping_patience, save_steps=args.save_steps, seed=args.seed,
            per_device_batch_size=args.batch_size, gradient_accumulation_steps=args.gradient_accumulation,
            resume_from_checkpoint=args.resume_from_checkpoint))
    elif args.command == "generate":
        from .core.inference import generate_repairs

        _print(generate_repairs(
            args.dataset, args.output, method=args.method, prompt_style=args.prompt, base_model=args.base_model,
            adapter_path=args.adapter, batch_size=args.batch_size, resume=not args.no_resume,
            max_new_tokens=args.max_new_tokens, sampling_seed=args.sampling_seed, temperature=args.temperature,
            top_p=args.top_p))
    elif args.command == "evaluate":
        from .core.evaluate import evaluate_generations

        _print(evaluate_generations(
            args.data_root, args.dataset, args.generations, args.output, workers=args.workers,
            timeout_sec=args.timeout_sec, resume=not args.no_resume, ted_workers=args.ted_workers,
            baseline_reference_path=args.baseline_reference))
