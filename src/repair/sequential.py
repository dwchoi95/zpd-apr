from __future__ import annotations

import json
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from ..runner.dataset import load_testcases
from ..runner.python_runner import PythonSubmissionRunner
from .evaluate import tree_edit_distance
from .inference import _generation_token_budget, extract_python_code
from .prompts import build_messages, render_generation_prompt


@dataclass(frozen=True)
class SequentialRepairSummary:
    method: str
    prompt_style: str
    base_model: str
    adapter_paths: dict[str, str]
    stage_feedback: bool
    compute_tree_edit_distance: bool
    examples: int
    problems: int
    stage_generated_counts: dict[str, int]
    early_stop_counts: dict[str, int]
    selected_source_counts: dict[str, int]
    repaired: int
    improved: int
    repair_rate: float
    improvement_rate: float
    average_time_taken_sec: float
    mean_generation_time_sec: float
    mean_execution_time_sec: float
    mean_ted_buggy_fixed_on_repaired: float | None
    mean_ted_fixed_oracle_on_repaired: float | None
    parseable_repaired_for_buggy_fixed_ted: int
    parseable_repaired_for_fixed_oracle_ted: int
    problem_timing_path: Path
    output_path: Path


@dataclass(frozen=True)
class JointOrderedEvaluationSummary:
    examples: int
    sources: tuple[str, ...]
    candidate_entries: int
    unique_candidate_executions: int
    individual_summary_paths: dict[str, str]
    sequential_summary_path: str
    output_dir: Path


@dataclass(frozen=True)
class StageGenerationExtractionSummary:
    examples: int
    stage_counts: dict[str, int]
    output_paths: dict[str, str]
    evaluation_path: Path
    output_dir: Path


def extract_stage_generations(
    evaluation_path: Path,
    output_dir: Path,
    *,
    stages: tuple[str, ...] = ("progress", "strict", "answer"),
) -> StageGenerationExtractionSummary:
    """Recover generated stage outputs from a sequential evaluation for resume."""

    evaluation_path = evaluation_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    requested = tuple(dict.fromkeys(stage.lower() for stage in stages))
    rows_by_stage: dict[str, dict[str, dict[str, Any]]] = {
        stage: {} for stage in requested
    }
    examples = 0

    for row in _iter_jsonl(evaluation_path):
        example_id = str(row["example_id"])
        examples += 1
        for patch in row.get("patches", []):
            stage = str(patch.get("source", "")).lower()
            if stage not in rows_by_stage:
                continue
            recovered = {
                "example_id": example_id,
                "problem_id": row["problem_id"],
                "user_id": row["user_id"],
                "method": f"ZPDPatch-{stage.title()}",
                "prompt_style": str(row.get("prompt_style", "D")).upper(),
                "generation_time_sec": float(
                    patch.get("generation_time_sec", 0.0)
                ),
                "generated_code": str(patch.get("generated_code", "")),
                "raw_generation": str(
                    patch.get("raw_generation", patch.get("generated_code", ""))
                ),
            }
            previous = rows_by_stage[stage].get(example_id)
            if previous is not None and previous != recovered:
                raise ValueError(
                    f"Conflicting {stage} candidates for example {example_id}."
                )
            rows_by_stage[stage][example_id] = recovered

    output_paths: dict[str, str] = {}
    stage_counts: dict[str, int] = {}
    for stage, rows in rows_by_stage.items():
        path = output_dir / f"{stage}-generation.jsonl"
        _write_jsonl(path, [rows[key] for key in sorted(rows)])
        output_paths[stage] = str(path)
        stage_counts[stage] = len(rows)

    summary = StageGenerationExtractionSummary(
        examples=examples,
        stage_counts=stage_counts,
        output_paths=output_paths,
        evaluation_path=evaluation_path,
        output_dir=output_dir,
    )
    (output_dir / "stage-generation-extraction.summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str)
        + "\n",
        encoding="utf-8",
    )
    return summary


def run_sequential_repairs(
    data_root: Path,
    dataset_path: Path,
    output_path: Path,
    *,
    adapters: list[tuple[str, Path]],
    method: str = "ZPDPatch",
    prompt_style: str = "D",
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    batch_size: int = 1,
    workers: int = 8,
    case_workers: int = 1,
    timeout_sec: float = 2.5,
    stage_feedback: bool = False,
    compute_tree_edit_distance: bool = True,
    outcome_cache_path: Path | None = None,
    resume: bool = True,
) -> SequentialRepairSummary:
    """Generate and execute adapter candidates in order, stopping at the first AC."""

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not adapters:
        raise ValueError("At least one adapter is required.")
    adapter_names = [name for name, _ in adapters]
    if len(adapter_names) != len(set(adapter_names)):
        raise ValueError("Adapter names must be unique.")

    data_root = data_root.expanduser().resolve()
    dataset_path = dataset_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_adapters = [
        (name, path.expanduser().resolve()) for name, path in adapters
    ]

    tokenizer = AutoTokenizer.from_pretrained(
        str(resolved_adapters[0][1]), use_fast=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map={"": 0},
        torch_dtype=compute_dtype,
        attn_implementation="sdpa",
    )
    first_name, first_path = resolved_adapters[0]
    model = PeftModel.from_pretrained(
        base,
        str(first_path),
        adapter_name=first_name,
    )
    for adapter_name, adapter_path in resolved_adapters[1:]:
        model.load_adapter(str(adapter_path), adapter_name=adapter_name)
    model.eval()

    records = list(_iter_jsonl(dataset_path))
    if outcome_cache_path is not None:
        from .outcomes import load_outcome_cache

        resolved_outcome_cache = outcome_cache_path.expanduser().resolve()
        _enrich_history_with_outcomes(
            records,
            load_outcome_cache(resolved_outcome_cache),
            execution_complete=_outcome_cache_is_complete(resolved_outcome_cache),
        )
    runner = PythonSubmissionRunner(
        timeout_sec=timeout_sec,
        memory_limit_mb=2048,
        case_workers=case_workers,
    )
    records_by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_problem[str(record["problem_id"])].append(record)

    timing_path = output_path.with_name(f"{output_path.stem}.problem-timing.jsonl")
    results, problem_timings, completed_problems = _prepare_problem_resume(
        records_by_problem,
        output_path,
        timing_path,
        resume=resume,
    )
    if not compute_tree_edit_distance and results:
        for result in results:
            result["ted_buggy_fixed"] = None
            result["ted_fixed_oracle"] = None
            result["tree_edit_distance"] = None
            for collection in ("patches", "candidate_outcomes"):
                for candidate in result.get(collection, []):
                    candidate["tree_edit_distance"] = None
                    candidate["ted_fixed_oracle"] = None
        _write_jsonl(output_path, results)
    stage_generated_counts = {name: 0 for name in adapter_names}
    early_stop_counts = {name: 0 for name in adapter_names}
    for result in results:
        for patch in result.get("patches", []):
            source = str(patch.get("source", ""))
            if source in stage_generated_counts:
                stage_generated_counts[source] += 1
        early_stop_stage = result.get("early_stop_stage")
        if early_stop_stage in early_stop_counts:
            early_stop_counts[str(early_stop_stage)] += 1

    adapter_indices = {
        adapter_name: index
        for index, (adapter_name, _path) in enumerate(resolved_adapters, start=1)
    }
    for problem_id in sorted(records_by_problem):
        if problem_id in completed_problems:
            continue
        problem_started = time.perf_counter()
        problem_records = records_by_problem[problem_id]
        records_by_id = {
            str(record["example_id"]): record for record in problem_records
        }
        states = _evaluate_current_programs(
            data_root,
            problem_records,
            runner=runner,
            workers=workers,
        )
        unresolved = list(records_by_id)

        for adapter_name, _adapter_path in resolved_adapters:
            if not unresolved:
                break
            model.set_adapter(adapter_name)
            stage_records = [records_by_id[example_id] for example_id in unresolved]
            stage_prompts: dict[str, str] = {}
            for example_id in unresolved:
                attempts = (
                    _repair_attempts_for_prompt(states[example_id])
                    if stage_feedback
                    else []
                )
                prompt, omitted_codes = _build_stage_prompt(
                    tokenizer,
                    records_by_id[example_id],
                    prompt_style,
                    repair_attempts=attempts,
                    context_length=int(model.config.max_position_embeddings),
                )
                if omitted_codes:
                    print(
                        "Execution-only stage feedback used for "
                        f"{example_id} before {adapter_name}: omitted "
                        f"{omitted_codes} generated code block(s) to keep the "
                        "dynamic prompt inside the model context."
                    )
                stage_prompts[example_id] = prompt
            generated = _generate_stage(
                model,
                tokenizer,
                stage_records,
                stage_prompts,
                adapter_name=adapter_name,
                batch_size=batch_size,
            )
            stage_generated_counts[adapter_name] += len(generated)
            evaluated = _evaluate_stage(
                data_root,
                stage_records,
                generated,
                patch_index=adapter_indices[adapter_name],
                runner=runner,
                workers=workers,
                states=states,
            )
            next_unresolved: list[str] = []
            for example_id in unresolved:
                candidate = evaluated[example_id]
                states[example_id]["candidates"].append(candidate)
                states[example_id]["generation_time_sec"] += float(
                    candidate["generation_time_sec"]
                )
                states[example_id]["execution_time_sec"] += float(
                    candidate["execution_time_sec"]
                )
                if candidate["fixed_verdict"] == "AC":
                    states[example_id]["early_stop_stage"] = adapter_name
                    early_stop_counts[adapter_name] += 1
                else:
                    next_unresolved.append(example_id)
            unresolved = next_unresolved

        with ThreadPoolExecutor(max_workers=workers) as executor:
            problem_results = list(
                executor.map(
                    lambda example_id: _select_final_result(
                        records_by_id[example_id],
                        states[example_id],
                        method=method,
                        prompt_style=prompt_style,
                        compute_tree_edit_distance=compute_tree_edit_distance,
                    ),
                    sorted(records_by_id),
                )
            )
        problem_elapsed = time.perf_counter() - problem_started
        timing = {
            "problem_id": problem_id,
            "method": method,
            "buggy_count": len(problem_results),
            "repair_time_sec": problem_elapsed,
            "average_time_taken_sec": (
                problem_elapsed / len(problem_results) if problem_results else 0.0
            ),
        }
        problem_timings.append(timing)
        for result in problem_results:
            result["problem_repair_time_sec"] = problem_elapsed
            result["problem_buggy_count"] = len(problem_results)
            result["problem_average_time_taken_sec"] = timing[
                "average_time_taken_sec"
            ]
        results.extend(problem_results)
        _append_problem_outputs(
            output_path,
            timing_path,
            problem_results,
            timing,
        )

    results.sort(key=lambda item: str(item["example_id"]))
    problem_timings.sort(key=lambda item: str(item["problem_id"]))
    _write_jsonl(timing_path, problem_timings)
    _write_jsonl(output_path, results)

    summary = _build_summary(
        results,
        method=method,
        prompt_style=prompt_style,
        base_model=base_model,
        adapters=resolved_adapters,
        stage_feedback=stage_feedback,
        compute_tree_edit_distance=compute_tree_edit_distance,
        stage_generated_counts=stage_generated_counts,
        early_stop_counts=early_stop_counts,
        problem_timings=problem_timings,
        problem_timing_path=timing_path,
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _enrich_history_with_outcomes(
    records: list[dict[str, Any]],
    outcomes: dict[tuple[str, str], dict[str, Any]],
    *,
    execution_complete: bool,
) -> None:
    """Attach cached execution evidence to every observed student submission."""

    for record in records:
        problem_id = str(record["problem_id"])
        for submission in record.get("history", []):
            outcome = outcomes.get(
                (problem_id, str(submission.get("submission_id", "")))
            )
            if outcome is None:
                continue
            submission.update(
                {
                    "execution_verdict": outcome["execution_verdict"],
                    "pass_rate": outcome["pass_rate"],
                    "passed_testcases": outcome["passed_testcases"],
                    "tc_outcomes": outcome["tc_outcomes"],
                    "execution_complete": execution_complete,
                }
            )


def _outcome_cache_is_complete(path: Path) -> bool:
    summary_path = path.with_suffix(".summary.json")
    if not summary_path.is_file():
        return False
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return summary.get("outcome_cache_complete") is True


def _prepare_problem_resume(
    records_by_problem: dict[str, list[dict[str, Any]]],
    output_path: Path,
    timing_path: Path,
    *,
    resume: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    """Keep only fully written problems so interrupted runs can resume safely."""

    if not resume:
        _write_jsonl(output_path, [])
        _write_jsonl(timing_path, [])
        return [], [], set()

    rows = list(_iter_jsonl(output_path)) if output_path.exists() else []
    timings = list(_iter_jsonl(timing_path)) if timing_path.exists() else []
    rows_by_problem: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        rows_by_problem[str(row["problem_id"])][str(row["example_id"])] = row
    timings_by_problem = {
        str(timing["problem_id"]): timing for timing in timings
    }

    completed: set[str] = set()
    kept_rows: list[dict[str, Any]] = []
    kept_timings: list[dict[str, Any]] = []
    for problem_id, problem_records in records_by_problem.items():
        expected_ids = {str(record["example_id"]) for record in problem_records}
        existing_rows = rows_by_problem.get(problem_id, {})
        if (
            set(existing_rows) == expected_ids
            and problem_id in timings_by_problem
        ):
            completed.add(problem_id)
            kept_rows.extend(existing_rows.values())
            kept_timings.append(timings_by_problem[problem_id])

    kept_rows.sort(key=lambda item: str(item["example_id"]))
    kept_timings.sort(key=lambda item: str(item["problem_id"]))
    _write_jsonl(output_path, kept_rows)
    _write_jsonl(timing_path, kept_timings)
    return kept_rows, kept_timings, completed


def _append_problem_outputs(
    output_path: Path,
    timing_path: Path,
    problem_results: list[dict[str, Any]],
    timing: dict[str, Any],
) -> None:
    with output_path.open("a", encoding="utf-8") as output:
        for item in problem_results:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
        output.flush()
    with timing_path.open("a", encoding="utf-8") as timing_output:
        timing_output.write(json.dumps(timing, ensure_ascii=False) + "\n")
        timing_output.flush()


def evaluate_ordered_generations(
    data_root: Path,
    dataset_path: Path,
    output_dir: Path,
    *,
    generation_paths: list[tuple[str, Path]],
    method: str = "ZPDPatch",
    prompt_style: str = "D",
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    workers: int = 1,
    ted_workers: int | None = None,
    timeout_sec: float = 2.5,
    outcome_cache_path: Path | None = None,
) -> JointOrderedEvaluationSummary:
    """Evaluate all adapter outputs once and derive fair individual/sequential results."""

    from .evaluate import _evaluation_summary

    if not generation_paths:
        raise ValueError("At least one generation source is required.")
    sources = [source for source, _ in generation_paths]
    if len(sources) != len(set(sources)):
        raise ValueError("Generation source names must be unique.")

    data_root = data_root.expanduser().resolve()
    dataset_path = dataset_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    records = {
        str(record["example_id"]): record for record in _iter_jsonl(dataset_path)
    }
    rows_by_source = {
        source: {
            str(row["example_id"]): row
            for row in _iter_jsonl(path.expanduser().resolve())
        }
        for source, path in generation_paths
    }
    expected_ids = set(records)
    for source, rows in rows_by_source.items():
        if set(rows) != expected_ids:
            raise ValueError(
                f"Generation source {source!r} does not match the evaluation dataset."
            )

    cached_outcomes_by_submission: dict[str, dict[str, Any]] = {}
    if outcome_cache_path is not None:
        cached_outcomes_by_submission = {
            str(row["submission_id"]): row
            for row in _iter_jsonl(outcome_cache_path.expanduser().resolve())
        }

    runner = PythonSubmissionRunner(timeout_sec=timeout_sec, memory_limit_mb=2048)

    def evaluate_record(
        example_id: str,
    ) -> tuple[str, dict[str, Any], int]:
        record = records[example_id]
        problem_id = str(record["problem_id"])
        current = record["history"][-1]
        current_code = str(current["code"])
        testcases = load_testcases(data_root / problem_id / "testcases.jsonl")

        cached_current = cached_outcomes_by_submission.get(
            str(current.get("submission_id", ""))
        )
        if (
            cached_current is not None
            and str(cached_current.get("problem_id")) == problem_id
            and isinstance(cached_current.get("tc_outcomes"), dict)
            and cached_current.get("execution_verdict") is not None
            and cached_current.get("pass_rate") is not None
        ):
            current_candidate = {
                "patch_index": None,
                "source": "current-fallback",
                "generated_code": current_code,
                "raw_generation": current_code,
                "fixed_verdict": str(cached_current["execution_verdict"]),
                "fixed_pass_rate": float(cached_current["pass_rate"]),
                "tree_edit_distance": 0,
                "fixed_tc_outcomes": {
                    str(case_id): str(verdict)
                    for case_id, verdict in cached_current["tc_outcomes"].items()
                },
                "generation_time_sec": 0.0,
                "execution_time_sec": 0.0,
            }
            outcome_cache: dict[str, tuple[Any, float]] = {}
        else:
            current_started = time.perf_counter()
            current_outcome = runner.run_submission(
                submission_id=f"{example_id}:current",
                problem_id=problem_id,
                code=current_code,
                source_verdict=str(current.get("verdict", "")),
                testcases=testcases,
            )
            current_execution_time = time.perf_counter() - current_started
            current_candidate = _outcome_candidate(
                patch_index=None,
                source="current-fallback",
                code=current_code,
                raw_generation=current_code,
                outcome=current_outcome,
                current_code=current_code,
                generation_time_sec=0.0,
                execution_time_sec=current_execution_time,
                compute_tree_edit_distance=False,
            )
            outcome_cache = {
                current_code.strip(): (current_outcome, current_execution_time)
            }
        unique_generated_executions = 0
        candidates: dict[str, dict[str, Any]] = {}
        for patch_index, source in enumerate(sources, start=1):
            generation = rows_by_source[source][example_id]
            code = str(generation.get("generated_code", ""))
            cache_key = code.strip()
            if cache_key == current_code.strip():
                candidates[source] = {
                    **current_candidate,
                    "patch_index": patch_index,
                    "source": source,
                    "raw_generation": str(generation.get("raw_generation", code)),
                    "generation_time_sec": float(
                        generation.get("generation_time_sec", 0.0)
                    ),
                }
                continue
            cached = outcome_cache.get(cache_key)
            if cached is None:
                fixed_started = time.perf_counter()
                outcome = runner.run_submission(
                    submission_id=f"{example_id}:{source}",
                    problem_id=problem_id,
                    code=code,
                    source_verdict=None,
                    testcases=testcases,
                )
                execution_time = time.perf_counter() - fixed_started
                outcome_cache[cache_key] = (outcome, execution_time)
                unique_generated_executions += 1
            else:
                outcome, execution_time = cached
            candidates[source] = _outcome_candidate(
                patch_index=patch_index,
                source=source,
                code=code,
                raw_generation=str(generation.get("raw_generation", code)),
                outcome=outcome,
                current_code=current_code,
                generation_time_sec=float(
                    generation.get("generation_time_sec", 0.0)
                ),
                execution_time_sec=execution_time,
                compute_tree_edit_distance=False,
            )
        return example_id, {
            "record": record,
            "current": current_candidate,
            "candidates": candidates,
        }, unique_generated_executions

    execution_cache_path = output_dir / "ordered-execution-cache.jsonl"
    cached_executions: dict[str, dict[str, Any]] = {}
    if execution_cache_path.exists():
        cached_rows: list[dict[str, Any]] = []
        with execution_cache_path.open(encoding="utf-8") as cache_input:
            for line in cache_input:
                if not line.strip():
                    continue
                try:
                    cached_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        for cached in cached_rows:
            example_id = str(cached.get("example_id", ""))
            candidates = cached.get("candidates")
            if (
                example_id in expected_ids
                and isinstance(cached.get("current"), dict)
                and isinstance(candidates, dict)
                and set(candidates) == set(sources)
            ):
                cached_executions[example_id] = cached

    # Rewrite once to discard stale, duplicate, or truncated cache rows. New
    # records are then flushed as each future completes so an interrupted RQ2
    # evaluation resumes at the example boundary.
    with execution_cache_path.open("w", encoding="utf-8") as cache_output:
        for example_id in sorted(cached_executions):
            cache_output.write(
                json.dumps(cached_executions[example_id], ensure_ascii=False) + "\n"
            )

    evaluated: dict[str, dict[str, Any]] = {
        example_id: {
            "record": records[example_id],
            "current": cached["current"],
            "candidates": cached["candidates"],
        }
        for example_id, cached in cached_executions.items()
    }
    unique_candidate_executions = sum(
        int(cached.get("unique_candidate_executions", 0))
        for cached in cached_executions.values()
    )
    pending_ids = sorted(expected_ids - set(evaluated))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(evaluate_record, example_id)
            for example_id in pending_ids
        ]
        with execution_cache_path.open("a", encoding="utf-8") as cache_output:
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Execute ordered adapter outputs",
                unit="example",
            ):
                example_id, row, unique_count = future.result()
                evaluated[example_id] = row
                unique_candidate_executions += unique_count
                cache_output.write(
                    json.dumps(
                        {
                            "example_id": example_id,
                            "current": row["current"],
                            "candidates": row["candidates"],
                            "unique_candidate_executions": unique_count,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                cache_output.flush()

    ted_jobs: list[tuple[str, str, str, str, str, bool]] = []
    for example_id in sorted(expected_ids):
        row = evaluated[example_id]
        current_code = str(row["current"]["generated_code"])
        oracle_code = str(row["record"]["target_code"])
        candidates = row["candidates"]
        needed_sources = {
            source
            for source in sources
            if (
                str(candidates[source]["generated_code"]).strip()
                != current_code.strip()
                and float(candidates[source]["fixed_pass_rate"]) == 1.0
            )
        }
        if not any(candidates[source]["fixed_verdict"] == "AC" for source in sources):
            all_candidates = [row["current"], *(candidates[source] for source in sources)]
            best_pass_rate = max(
                float(candidate["fixed_pass_rate"])
                for candidate in all_candidates
            )
            tied = [
                candidate
                for candidate in all_candidates
                if float(candidate["fixed_pass_rate"]) == best_pass_rate
            ]
            if (
                len(tied) > 1
                and not any(
                    candidate["source"] == "current-fallback" for candidate in tied
                )
            ):
                needed_sources.update(str(candidate["source"]) for candidate in tied)
        for source in sources:
            candidate = row["candidates"][source]
            generated_code = str(candidate["generated_code"])
            changed = generated_code.strip() != current_code.strip()
            repaired = changed and float(candidate["fixed_pass_rate"]) == 1.0
            if changed and source in needed_sources:
                ted_jobs.append(
                    (
                        example_id,
                        source,
                        current_code,
                        generated_code,
                        oracle_code,
                        repaired,
                    )
                )
            else:
                candidate["tree_edit_distance"] = 0
                candidate["ted_fixed_oracle"] = None

    effective_ted_workers = workers if ted_workers is None else ted_workers
    with ProcessPoolExecutor(max_workers=effective_ted_workers) as executor:
        future_to_candidate = {
            executor.submit(
                _ordered_candidate_tree_distances,
                current_code,
                generated_code,
                oracle_code,
                repaired,
            ): (example_id, source)
            for (
                example_id,
                source,
                current_code,
                generated_code,
                oracle_code,
                repaired,
            ) in ted_jobs
        }
        for future in tqdm(
            as_completed(future_to_candidate),
            total=len(future_to_candidate),
            desc="Compute ordered adapter TED",
            unit="candidate",
        ):
            example_id, source = future_to_candidate[future]
            buggy_fixed, fixed_oracle = future.result()
            candidate = evaluated[example_id]["candidates"][source]
            candidate["tree_edit_distance"] = buggy_fixed
            candidate["ted_fixed_oracle"] = fixed_oracle

    individual_summary_paths: dict[str, str] = {}
    for source in sources:
        results: list[dict[str, Any]] = []
        for example_id in sorted(expected_ids):
            row = evaluated[example_id]
            record = row["record"]
            current = row["current"]
            candidate = row["candidates"][source]
            fixed_pass_rate = float(candidate["fixed_pass_rate"])
            buggy_pass_rate = float(current["fixed_pass_rate"])
            changed = (
                str(candidate["generated_code"]).strip()
                != str(current["generated_code"]).strip()
            )
            repaired = changed and fixed_pass_rate == 1.0
            generation_time = float(candidate["generation_time_sec"])
            execution_time = float(current["execution_time_sec"]) + float(
                candidate["execution_time_sec"]
            )
            ted_buggy_fixed = candidate.get("tree_edit_distance") if repaired else None
            ted_fixed_oracle = candidate.get("ted_fixed_oracle") if repaired else None
            results.append(
                {
                    "example_id": record["example_id"],
                    "problem_id": record["problem_id"],
                    "user_id": record["user_id"],
                    "method": f"{method}-{source.title()}",
                    "prompt_style": prompt_style.upper(),
                    "generation_time_sec": generation_time,
                    "buggy_execution_time_sec": current["execution_time_sec"],
                    "fixed_execution_time_sec": candidate["execution_time_sec"],
                    "execution_time_sec": execution_time,
                    "online_time_sec": generation_time + execution_time,
                    "generated_code": candidate["generated_code"],
                    "raw_generation": candidate["raw_generation"],
                    "buggy_verdict": current["fixed_verdict"],
                    "fixed_verdict": candidate["fixed_verdict"],
                    "buggy_pass_rate": buggy_pass_rate,
                    "fixed_pass_rate": fixed_pass_rate,
                    "repaired": repaired,
                    "improved": fixed_pass_rate > buggy_pass_rate,
                    "ted_buggy_fixed": ted_buggy_fixed,
                    "ted_fixed_oracle": ted_fixed_oracle,
                    "tree_edit_distance": ted_buggy_fixed,
                    "fixed_tc_outcomes": candidate["fixed_tc_outcomes"],
                    "selected_patch_index": candidate["patch_index"],
                    "selected_source": source,
                    "patches": [candidate],
                }
            )
        output_path = output_dir / f"{source}-eval.jsonl"
        _write_jsonl(output_path, results)
        summary = _evaluation_summary(results, output_path)
        individual_summary_paths[source] = str(
            output_path.with_suffix(".summary.json")
        )

    stage_generated_counts = {source: 0 for source in sources}
    early_stop_counts = {source: 0 for source in sources}
    sequential_results: list[dict[str, Any]] = []
    for example_id in sorted(expected_ids):
        row = evaluated[example_id]
        current = row["current"]
        invoked = [current]
        generation_time = 0.0
        execution_time = float(current["execution_time_sec"])
        early_stop_stage: str | None = None
        for source in sources:
            candidate = row["candidates"][source]
            invoked.append(candidate)
            stage_generated_counts[source] += 1
            generation_time += float(candidate["generation_time_sec"])
            execution_time += float(candidate["execution_time_sec"])
            if candidate["fixed_verdict"] == "AC":
                early_stop_stage = source
                early_stop_counts[source] += 1
                break
        state = {
            "buggy_verdict": current["fixed_verdict"],
            "buggy_pass_rate": current["fixed_pass_rate"],
            "buggy_execution_cached": (
                float(current["execution_time_sec"]) == 0.0
            ),
            "generation_time_sec": generation_time,
            "execution_time_sec": execution_time,
            "early_stop_stage": early_stop_stage,
            "candidates": invoked,
        }
        sequential_results.append(
            _select_final_result(
                row["record"],
                state,
                method=f"{method}-Sequential",
                prompt_style=prompt_style,
            )
        )

    sequential_output = output_dir / "sequential-eval.jsonl"
    _write_jsonl(sequential_output, sequential_results)
    sequential_problem_timings = _aggregate_problem_timings_from_rows(
        sequential_results,
        method=f"{method}-Sequential",
    )
    sequential_timing_path = output_dir / "sequential-eval.problem-timing.jsonl"
    _write_jsonl(sequential_timing_path, sequential_problem_timings)
    sequential_summary = _build_summary(
        sequential_results,
        method=f"{method}-Sequential",
        prompt_style=prompt_style,
        base_model=base_model,
        adapters=[
            (source, path.expanduser().resolve())
            for source, path in generation_paths
        ],
        stage_feedback=False,
        compute_tree_edit_distance=True,
        stage_generated_counts=stage_generated_counts,
        early_stop_counts=early_stop_counts,
        problem_timings=sequential_problem_timings,
        problem_timing_path=sequential_timing_path,
        output_path=sequential_output,
    )
    sequential_summary_path = sequential_output.with_suffix(".summary.json")
    sequential_summary_path.write_text(
        json.dumps(
            asdict(sequential_summary),
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    summary = JointOrderedEvaluationSummary(
        examples=len(expected_ids),
        sources=tuple(sources),
        candidate_entries=len(expected_ids) * len(sources),
        unique_candidate_executions=unique_candidate_executions,
        individual_summary_paths=individual_summary_paths,
        sequential_summary_path=str(sequential_summary_path),
        output_dir=output_dir,
    )
    (output_dir / "joint-evaluation.summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _outcome_candidate(
    *,
    patch_index: int | None,
    source: str,
    code: str,
    raw_generation: str,
    outcome: Any,
    current_code: str,
    generation_time_sec: float,
    execution_time_sec: float,
    compute_tree_edit_distance: bool = True,
) -> dict[str, Any]:
    return {
        "patch_index": patch_index,
        "source": source,
        "generated_code": code,
        "raw_generation": raw_generation,
        "fixed_verdict": outcome.verdict.value,
        "fixed_pass_rate": _pass_rate(outcome),
        "tree_edit_distance": (
            tree_edit_distance(current_code, code)
            if compute_tree_edit_distance
            else None
        ),
        "fixed_tc_outcomes": {
            case.case_id: case.verdict.value for case in outcome.cases
        },
        "generation_time_sec": generation_time_sec,
        "execution_time_sec": execution_time_sec,
    }


def _ordered_candidate_tree_distances(
    current_code: str,
    generated_code: str,
    oracle_code: str,
    repaired: bool,
) -> tuple[int | None, int | None]:
    return (
        tree_edit_distance(current_code, generated_code),
        tree_edit_distance(generated_code, oracle_code) if repaired else None,
    )


def _evaluate_current_programs(
    data_root: Path,
    records: list[dict[str, Any]],
    *,
    runner: PythonSubmissionRunner,
    workers: int,
) -> dict[str, dict[str, Any]]:
    def evaluate(record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        example_id = str(record["example_id"])
        problem_id = str(record["problem_id"])
        current = record["history"][-1]
        current_code = str(current["code"])
        cached_tc_outcomes = record.get("current_tc_outcomes")
        cached_verdict = record.get("current_execution_verdict")
        cached_pass_rate = record.get("current_pass_rate")
        execution_cached = (
            record.get("current_execution_complete") is True
            and isinstance(cached_tc_outcomes, dict)
            and cached_verdict is not None
            and cached_pass_rate is not None
        )
        if execution_cached:
            buggy_verdict = str(cached_verdict)
            buggy_pass_rate = float(cached_pass_rate)
            tc_outcomes = {
                str(case_id): str(verdict)
                for case_id, verdict in cached_tc_outcomes.items()
            }
            execution_time = 0.0
        else:
            started = time.perf_counter()
            testcases = load_testcases(data_root / problem_id / "testcases.jsonl")
            outcome = runner.run_submission(
                submission_id=f"{example_id}:current",
                problem_id=problem_id,
                code=current_code,
                source_verdict=str(current.get("verdict", "")),
                testcases=testcases,
            )
            execution_time = time.perf_counter() - started
            buggy_verdict = outcome.verdict.value
            buggy_pass_rate = _pass_rate(outcome)
            tc_outcomes = {
                case.case_id: case.verdict.value for case in outcome.cases
            }
        current_candidate = {
            "patch_index": None,
            "source": "current-fallback",
            "generated_code": current_code,
            "raw_generation": current_code,
            "fixed_verdict": buggy_verdict,
            "fixed_pass_rate": buggy_pass_rate,
            "tree_edit_distance": 0,
            "fixed_tc_outcomes": tc_outcomes,
            "generation_time_sec": 0.0,
            "execution_time_sec": execution_time,
        }
        return example_id, {
            "buggy_verdict": buggy_verdict,
            "buggy_pass_rate": buggy_pass_rate,
            "buggy_execution_cached": execution_cached,
            "generation_time_sec": 0.0,
            "execution_time_sec": execution_time,
            "early_stop_stage": None,
            "candidates": [current_candidate],
        }

    states: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(evaluate, record) for record in records]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Execute current programs",
            unit="example",
        ):
            example_id, state = future.result()
            states[example_id] = state
    return states


def _generate_stage(
    model: Any,
    tokenizer: Any,
    records: list[dict[str, Any]],
    prompts: dict[str, str],
    *,
    adapter_name: str,
    batch_size: int,
) -> dict[str, dict[str, Any]]:
    import torch

    generated_rows: dict[str, dict[str, Any]] = {}
    for start in tqdm(
        range(0, len(records), batch_size),
        desc=f"Generate {adapter_name}",
        unit="batch",
    ):
        batch = records[start : start + batch_size]
        batch_prompts = [prompts[str(record["example_id"])] for record in batch]
        encoded = tokenizer(
            batch_prompts,
            return_tensors="pt",
            add_special_tokens=False,
            padding=True,
        ).to(model.device)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        started = time.perf_counter()
        with torch.inference_mode():
            sequences = model.generate(
                **encoded,
                max_new_tokens=_generation_token_budget(
                    model, encoded["input_ids"].shape[1]
                ),
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        input_length = encoded["input_ids"].shape[1]
        per_example_elapsed = elapsed / len(batch)
        for record, sequence in zip(batch, sequences, strict=True):
            raw = tokenizer.decode(sequence[input_length:], skip_special_tokens=True)
            generated_rows[str(record["example_id"])] = {
                "source": adapter_name,
                "generated_code": extract_python_code(raw),
                "raw_generation": raw,
                "generation_time_sec": per_example_elapsed,
            }
    return generated_rows


def _evaluate_stage(
    data_root: Path,
    records: list[dict[str, Any]],
    generated: dict[str, dict[str, Any]],
    *,
    patch_index: int,
    runner: PythonSubmissionRunner,
    workers: int,
    states: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    def evaluate(record: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        started = time.perf_counter()
        example_id = str(record["example_id"])
        problem_id = str(record["problem_id"])
        row = generated[example_id]
        fixed_code = str(row["generated_code"])
        if states is not None:
            prior = next(
                (
                    candidate
                    for candidate in reversed(states[example_id]["candidates"])
                    if str(candidate.get("generated_code", "")).strip()
                    == fixed_code.strip()
                ),
                None,
            )
            if prior is not None:
                return example_id, {
                    **row,
                    "patch_index": patch_index,
                    "fixed_verdict": prior["fixed_verdict"],
                    "fixed_pass_rate": prior["fixed_pass_rate"],
                    "tree_edit_distance": prior.get("tree_edit_distance"),
                    "fixed_tc_outcomes": prior["fixed_tc_outcomes"],
                    "execution_time_sec": 0.0,
                    "execution_reused_from": prior["source"],
                }
        testcases = load_testcases(data_root / problem_id / "testcases.jsonl")
        outcome = runner.run_submission(
            submission_id=f"{example_id}:{row['source']}",
            problem_id=problem_id,
            code=fixed_code,
            source_verdict=None,
            testcases=testcases,
        )
        return example_id, {
            **row,
            "patch_index": patch_index,
            "fixed_verdict": outcome.verdict.value,
            "fixed_pass_rate": _pass_rate(outcome),
            "tree_edit_distance": None,
            "fixed_tc_outcomes": {
                case.case_id: case.verdict.value for case in outcome.cases
            },
            "execution_time_sec": time.perf_counter() - started,
            "execution_reused_from": None,
        }

    evaluated: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(evaluate, record) for record in records]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Execute generated repairs",
            unit="repair",
        ):
            example_id, candidate = future.result()
            evaluated[example_id] = candidate
    return evaluated


def _repair_attempts_for_prompt(
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    current = next(
        candidate
        for candidate in state["candidates"]
        if candidate.get("source") == "current-fallback"
    )
    current_code = str(current.get("generated_code", "")).strip()
    current_pass_rate = float(current.get("fixed_pass_rate", 0.0))
    attempts = [
        candidate
        for candidate in state["candidates"]
        if candidate.get("patch_index") is not None
    ]
    attempts = sorted(
        attempts,
        key=lambda candidate: (
            float(candidate.get("fixed_pass_rate", 0.0)),
            str(candidate.get("generated_code", "")).strip() != current_code,
            int(candidate.get("patch_index") or 0),
        ),
        reverse=True,
    )
    result: list[dict[str, Any]] = []
    for candidate in attempts:
        item = dict(candidate)
        candidate_code = str(candidate.get("generated_code", "")).strip()
        candidate_pass_rate = float(candidate.get("fixed_pass_rate", 0.0))
        if candidate_code == current_code:
            status = "no-op"
        elif candidate_pass_rate < current_pass_rate:
            status = "regression"
        elif candidate_pass_rate == current_pass_rate:
            status = "equal"
        else:
            status = "partial-improvement"
        item["repair_status"] = status
        item["baseline_pass_rate"] = current_pass_rate
        result.append(item)
    return result


def _build_stage_prompt(
    tokenizer: Any,
    record: dict[str, Any],
    prompt_style: str,
    *,
    repair_attempts: list[dict[str, Any]],
    context_length: int,
) -> tuple[str, int]:
    """Fall back to execution-only feedback when generated code fills context.

    The original trajectory is never shortened. Only dynamically generated code
    blocks from failed earlier stages are omitted, longest first, while their
    verdict and per-test execution feedback remain in the prompt.
    """

    if context_length < 1:
        raise ValueError("Model context length must be positive.")
    attempts = [dict(attempt) for attempt in repair_attempts]

    def render() -> tuple[str, int]:
        prompt = render_generation_prompt(
            tokenizer,
            build_messages(
                record,
                prompt_style,
                repair_attempts=attempts,
            ),
        )
        tokens = len(
            tokenizer(prompt, add_special_tokens=False)["input_ids"]
        )
        return prompt, tokens

    prompt, tokens = render()
    if tokens < context_length:
        return prompt, 0

    code_candidates = sorted(
        (
            attempt
            for attempt in attempts
            if attempt.get("include_generated_code", True) is not False
            and str(attempt.get("repair_status", ""))
            not in {"no-op", "regression"}
            and str(attempt.get("generated_code", ""))
        ),
        key=lambda attempt: len(str(attempt.get("generated_code", ""))),
        reverse=True,
    )
    omitted = 0
    for attempt in code_candidates:
        attempt["include_generated_code"] = False
        omitted += 1
        prompt, tokens = render()
        if tokens < context_length:
            return prompt, omitted

    raise ValueError(
        f"Input uses {tokens} tokens after omitting every failed-stage code "
        f"block, but model context is {context_length}; the original trajectory "
        "is not truncated."
    )


def _select_final_result(
    record: dict[str, Any],
    state: dict[str, Any],
    *,
    method: str,
    prompt_style: str,
    compute_tree_edit_distance: bool = True,
) -> dict[str, Any]:
    candidates = state["candidates"]
    early_stop_stage = state["early_stop_stage"]
    if early_stop_stage is not None:
        selected = next(
            candidate
            for candidate in candidates
            if candidate["source"] == early_stop_stage
        )
    else:
        best_pass_rate = max(
            float(candidate["fixed_pass_rate"]) for candidate in candidates
        )
        tied = [
            candidate
            for candidate in candidates
            if float(candidate["fixed_pass_rate"]) == best_pass_rate
        ]
        current_fallback = next(
            (
                candidate
                for candidate in tied
                if candidate["source"] == "current-fallback"
            ),
            None,
        )
        if current_fallback is not None:
            selected = current_fallback
        elif len(tied) == 1:
            selected = tied[0]
        elif not compute_tree_edit_distance:
            selected = tied[0]
        else:
            for candidate in tied:
                if candidate.get("tree_edit_distance") is None:
                    candidate["tree_edit_distance"] = tree_edit_distance(
                        str(record["history"][-1]["code"]),
                        str(candidate["generated_code"]),
                    )
            selected = min(
                tied,
                key=lambda candidate: (
                    _ted_for_selection(candidate["tree_edit_distance"]),
                ),
            )

    current_code = str(record["history"][-1]["code"])
    fixed_code = str(selected["generated_code"])
    oracle_code = str(record["target_code"])
    changed = fixed_code.strip() != current_code.strip()
    fixed_pass_rate = float(selected["fixed_pass_rate"])
    buggy_pass_rate = float(state["buggy_pass_rate"])
    repaired = changed and fixed_pass_rate == 1.0
    ted_buggy_fixed = None
    ted_fixed_oracle = None
    if repaired and compute_tree_edit_distance:
        ted_buggy_fixed = selected.get("tree_edit_distance")
        if ted_buggy_fixed is None:
            ted_buggy_fixed = tree_edit_distance(current_code, fixed_code)
        ted_fixed_oracle = selected.get("ted_fixed_oracle")
        if ted_fixed_oracle is None:
            ted_fixed_oracle = tree_edit_distance(fixed_code, oracle_code)
    patches = [
        candidate for candidate in candidates if candidate["patch_index"] is not None
    ]
    return {
        "example_id": record["example_id"],
        "problem_id": record["problem_id"],
        "user_id": record["user_id"],
        "method": method,
        "prompt_style": prompt_style.upper(),
        "generation_time_sec": state["generation_time_sec"],
        "execution_time_sec": state["execution_time_sec"],
        "online_time_sec": (
            float(state["generation_time_sec"]) + float(state["execution_time_sec"])
        ),
        "generated_code": fixed_code,
        "raw_generation": selected["raw_generation"],
        "buggy_verdict": state["buggy_verdict"],
        "buggy_execution_cached": state["buggy_execution_cached"],
        "fixed_verdict": selected["fixed_verdict"],
        "buggy_pass_rate": buggy_pass_rate,
        "fixed_pass_rate": fixed_pass_rate,
        "repaired": repaired,
        "improved": fixed_pass_rate > buggy_pass_rate,
        "ted_buggy_fixed": ted_buggy_fixed,
        "ted_fixed_oracle": ted_fixed_oracle,
        "tree_edit_distance": ted_buggy_fixed,
        "fixed_tc_outcomes": selected["fixed_tc_outcomes"],
        "selected_patch_index": selected["patch_index"],
        "selected_source": selected["source"],
        "early_stop_stage": early_stop_stage,
        "patches": patches,
        "candidate_outcomes": candidates,
    }


def _build_summary(
    results: list[dict[str, Any]],
    *,
    method: str,
    prompt_style: str,
    base_model: str,
    adapters: list[tuple[str, Path]],
    stage_feedback: bool,
    compute_tree_edit_distance: bool,
    stage_generated_counts: dict[str, int],
    early_stop_counts: dict[str, int],
    problem_timings: list[dict[str, Any]],
    problem_timing_path: Path,
    output_path: Path,
) -> SequentialRepairSummary:
    selected_source_counts: dict[str, int] = {}
    for result in results:
        source = str(result["selected_source"])
        selected_source_counts[source] = selected_source_counts.get(source, 0) + 1
    repaired = sum(bool(result["repaired"]) for result in results)
    improved = sum(bool(result["improved"]) for result in results)
    repaired_buggy_fixed_distances = [
        float(result["ted_buggy_fixed"])
        for result in results
        if result["repaired"] and result["ted_buggy_fixed"] is not None
    ]
    repaired_fixed_oracle_distances = [
        float(result["ted_fixed_oracle"])
        for result in results
        if result["repaired"] and result["ted_fixed_oracle"] is not None
    ]
    generation_times = [float(result["generation_time_sec"]) for result in results]
    execution_times = [float(result["execution_time_sec"]) for result in results]
    return SequentialRepairSummary(
        method=method,
        prompt_style=prompt_style.upper(),
        base_model=base_model,
        adapter_paths={name: str(path) for name, path in adapters},
        stage_feedback=stage_feedback,
        compute_tree_edit_distance=compute_tree_edit_distance,
        examples=len(results),
        problems=len(problem_timings),
        stage_generated_counts=stage_generated_counts,
        early_stop_counts=early_stop_counts,
        selected_source_counts=selected_source_counts,
        repaired=repaired,
        improved=improved,
        repair_rate=repaired / len(results) if results else 0.0,
        improvement_rate=improved / len(results) if results else 0.0,
        average_time_taken_sec=(
            sum(float(timing["repair_time_sec"]) for timing in problem_timings)
            / sum(int(timing["buggy_count"]) for timing in problem_timings)
            if problem_timings
            else 0.0
        ),
        mean_generation_time_sec=(
            sum(generation_times) / len(generation_times) if generation_times else 0.0
        ),
        mean_execution_time_sec=(
            sum(execution_times) / len(execution_times) if execution_times else 0.0
        ),
        mean_ted_buggy_fixed_on_repaired=(
            sum(repaired_buggy_fixed_distances)
            / len(repaired_buggy_fixed_distances)
            if repaired_buggy_fixed_distances
            else None
        ),
        mean_ted_fixed_oracle_on_repaired=(
            sum(repaired_fixed_oracle_distances)
            / len(repaired_fixed_oracle_distances)
            if repaired_fixed_oracle_distances
            else None
        ),
        parseable_repaired_for_buggy_fixed_ted=len(
            repaired_buggy_fixed_distances
        ),
        parseable_repaired_for_fixed_oracle_ted=len(
            repaired_fixed_oracle_distances
        ),
        problem_timing_path=problem_timing_path,
        output_path=output_path,
    )


def _aggregate_problem_timings_from_rows(
    rows: list[dict[str, Any]],
    *,
    method: str,
) -> list[dict[str, Any]]:
    """Compatibility timing for pre-generated adapter ablations.

    The RQ1 online runners measure real problem wall-clock intervals. This
    evaluator operates on already generated files, so it can only aggregate the
    stored online durations by problem.
    """

    totals: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        problem_id = str(row["problem_id"])
        totals[problem_id] += float(row.get("online_time_sec", 0.0))
        counts[problem_id] += 1
    return [
        {
            "problem_id": problem_id,
            "method": method,
            "buggy_count": counts[problem_id],
            "repair_time_sec": totals[problem_id],
            "average_time_taken_sec": totals[problem_id] / counts[problem_id],
            "measurement": "aggregated-precomputed-duration",
        }
        for problem_id in sorted(totals)
    ]


def _pass_rate(outcome: Any) -> float:
    if not outcome.cases:
        return 0.0
    return sum(case.verdict.value == "AC" for case in outcome.cases) / len(
        outcome.cases
    )


def _ted_for_selection(value: int | None) -> int:
    return value if value is not None else 10**9


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
