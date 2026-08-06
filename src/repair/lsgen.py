from __future__ import annotations

import difflib
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

from ..runner.dataset import load_testcases
from ..runner.python_runner import PythonSubmissionRunner
from .evaluate import budget_bounded_tree_edit_distance, tree_edit_distance
from .inference import _generation_token_budget, extract_python_code


_LSGEN_SYSTEM = """You are a skilled programmer experienced in debugging and providing optimal code fixes.
You are provided with a programming problem and a piece of buggy code written in Python.
You are required to fix the buggy code to meet the problem's requirements while making minimal changes that preserve the original structure and logic as much as possible.
You will receive one or more diff files. In these files, '-' marks lines deleted from a reference buggy code, and '+' marks lines added in its corresponding correct code. Refer to them selectively.

Return the repaired code first in a Python Markdown code block. After the code, provide bug descriptions inside <DESCRIPTIONS_LIST></DESCRIPTIONS_LIST>."""

_DESCRIPTION_SYSTEM = """You analyze a buggy Python program and its corresponding corrected program. Describe the faults and why the edits correct them. Do not propose unrelated changes. Return only concise point-by-point descriptions."""
_MAX_DESCRIPTION_TOKENS = 512


@dataclass(frozen=True)
class LSGenSummary:
    method: str
    base_model: str
    examples: int
    problems: int
    retrieval_pairs: int
    described_pairs: int
    max_iterations: int
    max_new_tokens: int | None
    generated_patches: int
    offline_preparation_sec: float
    average_time_taken_sec: float
    problem_timing_path: Path
    output_path: Path


@dataclass(frozen=True)
class _RepairPair:
    pair_id: str
    problem_id: str
    user_id: str
    buggy_code: str
    correct_code: str
    retention: float


def generate_lsgen_repairs(
    dataset_path: Path,
    output_path: Path,
    *,
    data_root: Path,
    retrieval_dataset_path: Path | None = None,
    base_model: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    embedding_model: str = "microsoft/unixcoder-base",
    topk: int = 5,
    max_iterations: int = 3,
    description_batch_size: int = 8,
    retention_threshold: float = 0.5,
    workers: int = 8,
    case_workers: int = 1,
    resume: bool = True,
    timeout_sec: float = 2.5,
    always_generate_max: bool = False,
    max_new_tokens: int | None = None,
) -> LSGenSummary:
    """Run the LSGen artifact pipeline on ZPDPatch final-step examples.

    The official artifact is dataset-specific and hardcodes its judge/API paths. This
    adapter retains its repair-pair filtering, edit-vector retrieval, diff-guided
    generation, and iterative re-retrieval while using the shared local model/judge.
    """

    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        RobertaConfig,
        RobertaModel,
        RobertaTokenizer,
    )

    records = list(_iter_jsonl(dataset_path))
    retrieval_records = (
        list(_iter_jsonl(retrieval_dataset_path))
        if retrieval_dataset_path is not None
        else records
    )
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    requested_ids = {str(record["example_id"]) for record in records}
    existing = (
        {
            str(item["example_id"]): item
            for item in _iter_jsonl(output_path)
            if str(item["example_id"]) in requested_ids
        }
        if resume and output_path.exists()
        else {}
    )
    pending_records = [
        record for record in records if str(record["example_id"]) not in existing
    ]
    pairs = _build_repair_pairs(retrieval_records, retention_threshold)
    pairs_by_problem: dict[str, list[_RepairPair]] = defaultdict(list)
    for pair in pairs:
        pairs_by_problem[pair.problem_id].append(pair)

    if not pending_records:
        timing_path = output_path.with_name(
            f"{output_path.stem}.problem-timing.jsonl"
        )
        problem_timings = (
            list(_iter_jsonl(timing_path)) if timing_path.exists() else []
        )
        summary = LSGenSummary(
            method="LSGen",
            base_model=base_model,
            examples=len(records),
            problems=len({str(record["problem_id"]) for record in records}),
            retrieval_pairs=len(pairs),
            described_pairs=len(pairs),
            max_iterations=max_iterations,
            max_new_tokens=max_new_tokens,
            generated_patches=sum(
                len(item.get("patches", [])) for item in existing.values()
            ),
            offline_preparation_sec=0.0,
            average_time_taken_sec=(
                sum(float(item["repair_time_sec"]) for item in problem_timings)
                / sum(int(item["buggy_count"]) for item in problem_timings)
                if problem_timings
                else 0.0
            ),
            problem_timing_path=timing_path,
            output_path=output_path,
        )
        output_path.with_suffix(".summary.json").write_text(
            json.dumps(asdict(summary), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return summary

    preparation_started = time.perf_counter()
    device = torch.device("cuda:0")
    embed_tokenizer = RobertaTokenizer.from_pretrained(embedding_model)
    embed_config = RobertaConfig.from_pretrained(embedding_model)
    embed_config.is_decoder = True
    embedder = RobertaModel.from_pretrained(embedding_model, config=embed_config)
    embedder.to(device).eval()
    embedding_cache = _embed_pair_codes(
        pairs,
        tokenizer=embed_tokenizer,
        model=embedder,
        device=device,
    )
    # Pair descriptions use only the generator. Keep the embedding model on CPU
    # during this high-memory batched generation phase, then restore it for
    # online retrieval.
    embedder.to("cpu")
    torch.cuda.empty_cache()

    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    generator = AutoModelForCausalLM.from_pretrained(
        base_model,
        device_map={"": 0},
        torch_dtype=compute_dtype,
        attn_implementation="sdpa",
    )
    generator.eval()

    # Bug descriptions are an offline part of the retrieval-solution database and
    # are cached once per pair instead of regenerated for every query.
    descriptions = _describe_pairs(
        pairs,
        tokenizer=tokenizer,
        model=generator,
        batch_size=description_batch_size,
        cache_path=output_path.with_name(
            f"{output_path.stem}.pair-descriptions.jsonl"
        ),
    )
    torch.cuda.empty_cache()
    embedder.to(device).eval()
    offline_preparation_sec = time.perf_counter() - preparation_started

    runner = PythonSubmissionRunner(
        timeout_sec=timeout_sec,
        memory_limit_mb=2048,
        case_workers=case_workers,
    )
    gpu_lock = Lock()
    results: list[dict[str, Any]] = list(existing.values())
    mode = "a" if resume and output_path.exists() else "w"
    output = output_path.open(mode, encoding="utf-8")
    pending_by_problem: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in pending_records:
        pending_by_problem[str(record["problem_id"])].append(record)
    problem_timings: list[dict[str, Any]] = []

    def repair_record(
        record: dict[str, Any],
        problem_id: str,
        testcases: list[Any],
    ) -> dict[str, Any]:
        user_id = str(record["user_id"])
        original_buggy = str(record["history"][-1]["code"])
        oracle_code = str(record["target_code"])
        query_code = original_buggy
        previous_generated: str | None = None
        patches: list[dict[str, Any]] = []
        generation_time_total = 0.0
        execution_time_total = 0.0

        cached_tc_outcomes = record.get("current_tc_outcomes")
        cached_verdict = record.get("current_execution_verdict")
        cached_pass_rate = record.get("current_pass_rate")
        buggy_execution_cached = (
            record.get("current_execution_complete") is True
            and isinstance(cached_tc_outcomes, dict)
            and cached_verdict is not None
            and cached_pass_rate is not None
        )
        if buggy_execution_cached:
            buggy_execution_time = 0.0
            buggy_verdict = str(cached_verdict)
            buggy_pass_rate = float(cached_pass_rate)
        else:
            buggy_started = time.perf_counter()
            buggy_outcome = runner.run_submission(
                submission_id=f"{record['example_id']}:lsgen:buggy",
                problem_id=problem_id,
                code=original_buggy,
                source_verdict=str(record["history"][-1].get("verdict", "")),
                testcases=testcases,
            )
            buggy_execution_time = time.perf_counter() - buggy_started
            buggy_verdict = buggy_outcome.verdict.value
            buggy_pass_rate = _pass_rate(buggy_outcome)
        execution_time_total += buggy_execution_time

        candidates = [
            pair
            for pair in pairs_by_problem.get(problem_id, [])
            if pair.user_id != user_id and pair.pair_id != record["example_id"]
        ]
        for iteration in range(1, max_iterations + 1):
            # The two GPU models are shared. Serializing retrieval and generation
            # keeps inference deterministic while CPU test execution overlaps
            # across records.
            with gpu_lock:
                generation_started = time.perf_counter()
                selected = _retrieve_pairs(
                    query_code,
                    candidates,
                    embedding_cache,
                    tokenizer=embed_tokenizer,
                    model=embedder,
                    device=device,
                    topk=topk,
                    original_buggy=original_buggy,
                    previous_generated=previous_generated,
                )
                selected_ids = [pair.pair_id for pair in selected]
                prompt = _render_repair_prompt(
                    record,
                    query_code,
                    selected,
                    descriptions,
                )
                prompt_text = tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": _LSGEN_SYSTEM},
                        {"role": "user", "content": prompt},
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                )
                encoded = tokenizer(
                    prompt_text,
                    return_tensors="pt",
                    add_special_tokens=False,
                ).to(generator.device)
                torch.cuda.synchronize()
                with torch.inference_mode():
                    generated = generator.generate(
                        **encoded,
                        max_new_tokens=_generation_token_budget(
                            generator,
                            encoded["input_ids"].shape[1],
                            max_new_tokens,
                        ),
                        do_sample=False,
                        pad_token_id=tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )
                torch.cuda.synchronize()
                generation_time = time.perf_counter() - generation_started
                new_tokens = generated[0, encoded["input_ids"].shape[1] :]
                raw = tokenizer.decode(new_tokens, skip_special_tokens=True)
                fixed_code = extract_python_code(raw)
            generation_time_total += generation_time

            execution_started = time.perf_counter()
            outcome = runner.run_submission(
                submission_id=f"{record['example_id']}:lsgen:{iteration}",
                problem_id=problem_id,
                code=fixed_code,
                source_verdict=None,
                testcases=testcases,
            )
            execution_time = time.perf_counter() - execution_started
            execution_time_total += execution_time
            changed_candidate = fixed_code.strip() != original_buggy.strip()
            candidate_ted = (
                budget_bounded_tree_edit_distance(
                    original_buggy, fixed_code, maximum_budget=160
                )
                if changed_candidate
                else 0
            )
            patch = {
                "patch_index": iteration,
                "source": f"iteration-{iteration}",
                "generated_code": fixed_code,
                "raw_generation": raw,
                "fixed_verdict": outcome.verdict.value,
                "fixed_pass_rate": _pass_rate(outcome),
                "tree_edit_distance": candidate_ted,
                "ted_buggy_fixed": candidate_ted,
                "ted_censored_above": 160 if candidate_ted == 161 else None,
                "fixed_tc_outcomes": {
                    case.case_id: case.verdict.value for case in outcome.cases
                },
                "generation_time_sec": generation_time,
                "execution_time_sec": execution_time,
                "metadata": {"retrieval_pair_ids": selected_ids},
            }
            patches.append(patch)
            if outcome.verdict.value == "AC" and not always_generate_max:
                break
            previous_generated = fixed_code

        if always_generate_max:
            accepted = [
                patch for patch in patches if float(patch["fixed_pass_rate"]) == 1.0
            ]
            selected_patch = (
                accepted[0]
                if accepted
                else max(
                    patches,
                    key=lambda patch: (
                        float(patch["fixed_pass_rate"]),
                        -(
                            float(patch["ted_buggy_fixed"])
                            if patch["ted_buggy_fixed"] is not None
                            else float("inf")
                        ),
                        -int(patch["patch_index"]),
                    ),
                )
            )
        else:
            selected_patch = patches[-1]
        final_code = str(selected_patch["generated_code"])
        final_pass_rate = float(selected_patch["fixed_pass_rate"])
        changed = final_code.strip() != original_buggy.strip()
        repaired = changed and final_pass_rate == 1.0
        ted_buggy_fixed = selected_patch["ted_buggy_fixed"] if repaired else None
        ted_fixed_oracle = (
            tree_edit_distance(final_code, oracle_code) if repaired else None
        )
        return {
            "example_id": record["example_id"],
            "problem_id": problem_id,
            "user_id": user_id,
            "method": "LSGen",
            "prompt_style": "LSGen-CommentTextRefDiff",
            "generation_time_sec": generation_time_total,
            "buggy_execution_time_sec": buggy_execution_time,
            "execution_time_sec": execution_time_total,
            "online_time_sec": generation_time_total + execution_time_total,
            "generated_code": final_code,
            "raw_generation": selected_patch["raw_generation"],
            "buggy_verdict": buggy_verdict,
            "buggy_execution_cached": buggy_execution_cached,
            "fixed_verdict": selected_patch["fixed_verdict"],
            "buggy_pass_rate": buggy_pass_rate,
            "fixed_pass_rate": final_pass_rate,
            "repaired": repaired,
            "improved": final_pass_rate > buggy_pass_rate,
            "ted_buggy_fixed": ted_buggy_fixed,
            "ted_fixed_oracle": ted_fixed_oracle,
            "tree_edit_distance": ted_buggy_fixed,
            "fixed_tc_outcomes": selected_patch["fixed_tc_outcomes"],
            "selected_patch_index": selected_patch["patch_index"],
            "selected_source": selected_patch["source"],
            "early_stop_stage": (
                selected_patch["source"]
                if selected_patch["fixed_verdict"] == "AC"
                else None
            ),
            "patches": patches,
            "always_generate_max": always_generate_max,
        }

    for problem_id in sorted(pending_by_problem):
        problem_started = time.perf_counter()
        testcases = load_testcases(data_root / problem_id / "testcases.jsonl")
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(repair_record, record, problem_id, testcases)
                for record in pending_by_problem[problem_id]
            ]
            problem_results = [future.result() for future in as_completed(futures)]
        problem_results.sort(key=lambda item: str(item["example_id"]))

        problem_elapsed = time.perf_counter() - problem_started
        timing = {
            "problem_id": problem_id,
            "method": "LSGen",
            "buggy_count": len(problem_results),
            "repair_time_sec": problem_elapsed,
            "average_time_taken_sec": (
                problem_elapsed / len(problem_results) if problem_results else 0.0
            ),
        }
        problem_timings.append(timing)
        for item in problem_results:
            item["problem_repair_time_sec"] = problem_elapsed
            item["problem_buggy_count"] = len(problem_results)
            item["problem_average_time_taken_sec"] = timing[
                "average_time_taken_sec"
            ]
            results.append(item)
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
            output.flush()
    output.close()
    timing_path = output_path.with_name(f"{output_path.stem}.problem-timing.jsonl")
    with timing_path.open("w", encoding="utf-8") as timing_output:
        for timing in problem_timings:
            timing_output.write(json.dumps(timing, ensure_ascii=False) + "\n")
    summary = LSGenSummary(
        method="LSGen",
        base_model=base_model,
        examples=len(records),
        problems=len({str(record["problem_id"]) for record in records}),
        retrieval_pairs=len(pairs),
        described_pairs=len(descriptions),
        max_iterations=max_iterations,
        max_new_tokens=max_new_tokens,
        generated_patches=sum(len(item.get("patches", [])) for item in results),
        offline_preparation_sec=offline_preparation_sec,
        average_time_taken_sec=(
            sum(float(item["repair_time_sec"]) for item in problem_timings)
            / sum(int(item["buggy_count"]) for item in problem_timings)
            if problem_timings
            else 0.0
        ),
        problem_timing_path=timing_path,
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _build_repair_pairs(
    records: list[dict[str, Any]], threshold: float
) -> list[_RepairPair]:
    all_pairs = [
        _RepairPair(
            pair_id=str(record["example_id"]),
            problem_id=str(record["problem_id"]),
            user_id=str(record["user_id"]),
            buggy_code=str(record["history"][-1]["code"]),
            correct_code=str(record["target_code"]),
            retention=_retention(
                str(record["history"][-1]["code"]), str(record["target_code"])
            ),
        )
        for record in records
    ]
    filtered = [pair for pair in all_pairs if pair.retention >= threshold]
    filtered_ids = {pair.pair_id for pair in filtered}
    all_by_problem: dict[str, list[_RepairPair]] = defaultdict(list)
    filtered_by_problem: dict[str, list[_RepairPair]] = defaultdict(list)
    for pair in all_pairs:
        all_by_problem[pair.problem_id].append(pair)
    for pair in filtered:
        filtered_by_problem[pair.problem_id].append(pair)
    # Every retained problem originally has at least two trajectories. Keep the
    # two highest-retention pairs only when thresholding would make peer retrieval
    # impossible for leave-one-trajectory-out evaluation.
    for problem_id, problem_pairs in all_by_problem.items():
        if len(filtered_by_problem[problem_id]) >= 2:
            continue
        for pair in sorted(problem_pairs, key=lambda item: item.retention, reverse=True):
            if pair.pair_id not in filtered_ids:
                filtered.append(pair)
                filtered_ids.add(pair.pair_id)
            if sum(item.problem_id == problem_id for item in filtered) >= 2:
                break
    return filtered


def _embed_pair_codes(
    pairs: list[_RepairPair],
    *,
    tokenizer: Any,
    model: Any,
    device: Any,
) -> dict[str, tuple[Any, Any]]:
    result: dict[str, tuple[Any, Any]] = {}
    for start in range(0, len(pairs), 16):
        batch = pairs[start : start + 16]
        buggy = _embed_codes([item.buggy_code for item in batch], tokenizer, model, device)
        correct = _embed_codes([item.correct_code for item in batch], tokenizer, model, device)
        for index, item in enumerate(batch):
            result[item.pair_id] = (buggy[index].cpu(), correct[index].cpu())
    return result


def _embed_codes(codes: list[str], tokenizer: Any, model: Any, device: Any) -> Any:
    import torch

    rows: list[list[int]] = []
    owners: list[int] = []
    for owner, code in enumerate(codes):
        code_tokens = tokenizer.tokenize(code)
        chunks = [
            code_tokens[start : start + 508]
            for start in range(0, len(code_tokens), 508)
        ] or [[]]
        for chunk in chunks:
            tokens = [
                tokenizer.cls_token,
                "<encoder-only>",
                tokenizer.sep_token,
                *chunk,
                tokenizer.sep_token,
            ]
            ids = tokenizer.convert_tokens_to_ids(tokens)
            rows.append(ids + [tokenizer.pad_token_id] * (512 - len(ids)))
            owners.append(owner)

    embedding_sums: list[Any | None] = [None] * len(codes)
    token_counts = [0] * len(codes)
    for start in range(0, len(rows), 32):
        source_ids = torch.tensor(rows[start : start + 32], device=device)
        mask = source_ids.ne(tokenizer.pad_token_id)
        with torch.inference_mode():
            token_embeddings = model(
                source_ids,
                attention_mask=mask,
            ).last_hidden_state
        chunk_sums = (token_embeddings * mask.unsqueeze(-1)).sum(1)
        chunk_counts = mask.sum(-1)
        for offset, (chunk_sum, chunk_count) in enumerate(
            zip(chunk_sums, chunk_counts, strict=True)
        ):
            owner = owners[start + offset]
            embedding_sums[owner] = (
                chunk_sum
                if embedding_sums[owner] is None
                else embedding_sums[owner] + chunk_sum
            )
            token_counts[owner] += int(chunk_count)
    return torch.stack(
        [
            embedding_sum / token_count
            for embedding_sum, token_count in zip(
                embedding_sums,
                token_counts,
                strict=True,
            )
        ]
    )


def _retrieve_pairs(
    query_code: str,
    candidates: list[_RepairPair],
    cache: dict[str, tuple[Any, Any]],
    *,
    tokenizer: Any,
    model: Any,
    device: Any,
    topk: int,
    original_buggy: str,
    previous_generated: str | None,
) -> list[_RepairPair]:
    import torch
    import torch.nn.functional as functional

    if not candidates:
        return []
    query = _embed_codes([query_code], tokenizer, model, device)[0].cpu()
    buggy = torch.stack([cache[item.pair_id][0] for item in candidates])
    correct = torch.stack([cache[item.pair_id][1] for item in candidates])
    adjusted = query.unsqueeze(0) + (correct - buggy)
    scores = functional.cosine_similarity(adjusted, correct, dim=1)
    if previous_generated is not None:
        original = _embed_codes([original_buggy], tokenizer, model, device)[0].cpu()
        generated = _embed_codes([previous_generated], tokenizer, model, device)[0].cpu()
        error_adjusted = (generated - original).unsqueeze(0) + buggy
        scores = scores + (1.0 - functional.cosine_similarity(error_adjusted, correct, dim=1))
    indexes = torch.topk(scores, k=min(topk, len(candidates))).indices.tolist()
    return [candidates[index] for index in indexes]


def _describe_pairs(
    pairs: list[_RepairPair],
    *,
    tokenizer: Any,
    model: Any,
    batch_size: int,
    cache_path: Path | None = None,
) -> dict[str, str]:
    import torch
    from tqdm import tqdm

    descriptions = (
        {
            str(item["pair_id"]): str(item["description"])
            for item in _iter_jsonl(cache_path)
        }
        if cache_path is not None and cache_path.exists()
        else {}
    )
    cache = (
        cache_path.open("a", encoding="utf-8") if cache_path is not None else None
    )
    pending = [pair for pair in pairs if pair.pair_id not in descriptions]

    def describe_batch(batch: list[_RepairPair]) -> None:
        prompts = []
        for pair in batch:
            user = (
                "[Buggy Code]\n```python\n"
                + pair.buggy_code
                + "\n```\n[Corrected Code]\n```python\n"
                + pair.correct_code
                + "\n```"
            )
            prompts.append(
                tokenizer.apply_chat_template(
                    [
                        {"role": "system", "content": _DESCRIPTION_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    tokenize=False,
                    add_generation_prompt=True,
                )
            )
        encoded = tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
            add_special_tokens=False,
        ).to(model.device)
        try:
            with torch.inference_mode():
                generated = model.generate(
                    **encoded,
                    max_new_tokens=min(
                        _MAX_DESCRIPTION_TOKENS,
                        _generation_token_budget(
                            model, encoded["input_ids"].shape[1]
                        ),
                    ),
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
        except torch.OutOfMemoryError:
            del encoded
            torch.cuda.empty_cache()
            if len(batch) == 1:
                raise
            midpoint = len(batch) // 2
            describe_batch(batch[:midpoint])
            describe_batch(batch[midpoint:])
            return
        input_length = encoded["input_ids"].shape[1]
        for index, pair in enumerate(batch):
            new_tokens = generated[index, input_length:]
            descriptions[pair.pair_id] = tokenizer.decode(
                new_tokens, skip_special_tokens=True
            ).strip()
            if cache is not None:
                cache.write(
                    json.dumps(
                        {
                            "pair_id": pair.pair_id,
                            "description": descriptions[pair.pair_id],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
                cache.flush()

    for start in tqdm(
        range(0, len(pending), batch_size),
        desc="Describe retrieval pairs",
        unit="batch",
    ):
        describe_batch(pending[start : start + batch_size])
    if cache is not None:
        cache.close()
    return descriptions


def _render_repair_prompt(
    record: dict[str, Any],
    buggy_code: str,
    selected: list[_RepairPair],
    descriptions: dict[str, str],
) -> str:
    references = []
    for pair in selected:
        diff = "\n".join(
            difflib.unified_diff(
                pair.buggy_code.splitlines(),
                pair.correct_code.splitlines(),
                fromfile="buggy.py",
                tofile="correct.py",
                lineterm="",
                n=10_000,
            )
        )
        comments = "\n".join(
            f"# {line}" for line in descriptions.get(pair.pair_id, "").splitlines()
        )
        references.append(f"Diff Code:\n{comments}\n{diff}")
    return (
        "[Programming Problem]\n"
        + str(record["problem_description"])
        + "\n\n[Buggy Code]\n```python\n"
        + buggy_code
        + "\n```\n\n[Diff Files]\n"
        + "\n\n".join(references)
    )


def _retention(before: str, after: str) -> float:
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    if not before_lines:
        return 0.0
    matcher = difflib.SequenceMatcher(a=before_lines, b=after_lines, autojunk=False)
    preserved = sum(block.size for block in matcher.get_matching_blocks())
    return preserved / max(1, len(after_lines))


def _pass_rate(outcome: Any) -> float:
    if not outcome.cases:
        return 0.0
    return sum(case.verdict.value == "AC" for case in outcome.cases) / len(
        outcome.cases
    )


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
