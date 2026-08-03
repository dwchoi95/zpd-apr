from __future__ import annotations

import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from .inference import _generation_token_budget, extract_python_code
from .sequential import (
    SequentialRepairSummary,
    _append_problem_outputs,
    _build_summary,
    _evaluate_current_programs,
    _evaluate_stage,
    _prepare_problem_resume,
    _select_final_result,
    _write_jsonl,
)


def run_zero_shot_repairs(
    data_root: Path,
    dataset_path: Path,
    output_path: Path,
    *,
    method: str = "Zero-shot",
    prompt_style: str = "D",
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    max_attempts: int = 3,
    batch_size: int = 1,
    workers: int = 1,
    case_workers: int = 1,
    timeout_sec: float = 2.5,
    resume: bool = True,
) -> SequentialRepairSummary:
    """Run a base LLM for at most three execution-guided repair attempts."""

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from .prompts import build_messages, render_generation_prompt

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    data_root = data_root.expanduser().resolve()
    dataset_path = dataset_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map={"": 0},
        torch_dtype=compute_dtype,
        attn_implementation="sdpa",
    )
    model.eval()

    records = list(_iter_jsonl(dataset_path))
    records_by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_problem[str(record["problem_id"])].append(record)

    from ..runner.python_runner import PythonSubmissionRunner

    runner = PythonSubmissionRunner(
        timeout_sec=timeout_sec,
        memory_limit_mb=2048,
        case_workers=case_workers,
    )
    attempt_names = [f"attempt-{index}" for index in range(1, max_attempts + 1)]
    timing_path = output_path.with_name(f"{output_path.stem}.problem-timing.jsonl")
    results, problem_timings, completed_problems = _prepare_problem_resume(
        records_by_problem,
        output_path,
        timing_path,
        resume=resume,
    )
    stage_generated_counts = {name: 0 for name in attempt_names}
    early_stop_counts = {name: 0 for name in attempt_names}
    for result in results:
        for patch in result.get("patches", []):
            source = str(patch.get("source", ""))
            if source in stage_generated_counts:
                stage_generated_counts[source] += 1
        early_stop_stage = result.get("early_stop_stage")
        if early_stop_stage in early_stop_counts:
            early_stop_counts[str(early_stop_stage)] += 1

    for problem_id in sorted(records_by_problem):
        if problem_id in completed_problems:
            continue
        problem_started = time.perf_counter()
        problem_records = records_by_problem[problem_id]
        records_by_id = {
            str(record["example_id"]): record for record in problem_records
        }
        messages_by_id = {
            example_id: build_messages(
                record,
                prompt_style,
            )
            for example_id, record in records_by_id.items()
        }
        states = _evaluate_current_programs(
            data_root,
            problem_records,
            runner=runner,
            workers=workers,
        )
        unresolved = list(records_by_id)

        for patch_index, attempt_name in enumerate(attempt_names, start=1):
            if not unresolved:
                break
            stage_records = [records_by_id[example_id] for example_id in unresolved]
            prompts: dict[str, str] = {}
            for example_id in unresolved:
                prompt, omitted_codes = _build_retry_prompt(
                    tokenizer,
                    messages_by_id[example_id],
                    context_length=int(model.config.max_position_embeddings),
                )
                if omitted_codes:
                    print(
                        "Execution-only retry feedback used for "
                        f"{example_id} before {attempt_name}: omitted "
                        f"{omitted_codes} generated code block(s) to keep the "
                        "dynamic prompt inside the model context."
                    )
                prompts[example_id] = prompt
            generated = _generate_attempt(
                model,
                tokenizer,
                stage_records,
                prompts,
                attempt_name=attempt_name,
                batch_size=batch_size,
            )
            stage_generated_counts[attempt_name] += len(generated)
            evaluated = _evaluate_stage(
                data_root,
                stage_records,
                generated,
                patch_index=patch_index,
                runner=runner,
                workers=workers,
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
                    states[example_id]["early_stop_stage"] = attempt_name
                    early_stop_counts[attempt_name] += 1
                    continue
                messages_by_id[example_id].extend(
                    [
                        {
                            "role": "assistant",
                            "content": str(candidate["raw_generation"]),
                        },
                        {
                            "role": "user",
                            "content": _retry_feedback(candidate),
                        },
                    ]
                )
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
    _write_jsonl(output_path, results)
    _write_jsonl(timing_path, problem_timings)
    summary = _build_summary(
        results,
        method=method,
        prompt_style=prompt_style,
        base_model=base_model,
        adapters=[],
        stage_feedback=True,
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


def _generate_attempt(
    model: Any,
    tokenizer: Any,
    records: list[dict[str, Any]],
    prompts: dict[str, str],
    *,
    attempt_name: str,
    batch_size: int,
) -> dict[str, dict[str, Any]]:
    import torch
    from tqdm import tqdm

    generated_rows: dict[str, dict[str, Any]] = {}
    for start in tqdm(
        range(0, len(records), batch_size),
        desc=f"Generate {attempt_name}",
        unit="batch",
    ):
        batch = records[start : start + batch_size]
        encoded = tokenizer(
            [prompts[str(record["example_id"])] for record in batch],
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
                "source": attempt_name,
                "generated_code": extract_python_code(raw),
                "raw_generation": raw,
                "generation_time_sec": per_example_elapsed,
            }
    return generated_rows


def _retry_feedback(candidate: dict[str, Any]) -> str:
    outcomes = candidate.get("fixed_tc_outcomes", {})
    passed = sum(verdict == "AC" for verdict in outcomes.values())
    total = len(outcomes)
    return (
        "The previous candidate was not accepted. "
        f"Its verdict was {candidate['fixed_verdict']} and it passed "
        f"{passed} of {total} test cases. Repair the program again while "
        "preserving its existing structure where possible. Return only the "
        "complete Python program."
    )


def _build_retry_prompt(
    tokenizer: Any,
    messages: list[dict[str, str]],
    *,
    context_length: int,
) -> tuple[str, int]:
    """Keep retry outcomes while omitting oversized generated code blocks."""

    from .prompts import render_generation_prompt

    if context_length < 1:
        raise ValueError("Model context length must be positive.")
    compacted = [dict(message) for message in messages]

    def render() -> tuple[str, int]:
        prompt = render_generation_prompt(tokenizer, compacted)
        tokens = len(
            tokenizer(prompt, add_special_tokens=False)["input_ids"]
        )
        return prompt, tokens

    prompt, tokens = render()
    if tokens < context_length:
        return prompt, 0

    assistant_messages = sorted(
        (
            message
            for message in compacted
            if message.get("role") == "assistant"
            and message.get("content")
        ),
        key=lambda message: len(str(message.get("content", ""))),
        reverse=True,
    )
    omitted = 0
    for message in assistant_messages:
        message["content"] = (
            "Previous generated program omitted because its full text would "
            "exceed the model context; the following execution feedback is "
            "preserved."
        )
        omitted += 1
        prompt, tokens = render()
        if tokens < context_length:
            return prompt, omitted

    raise ValueError(
        f"Input uses {tokens} tokens after omitting every prior generated code "
        f"block, but model context is {context_length}; the original trajectory "
        "is not truncated."
    )


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
