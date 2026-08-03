from __future__ import annotations

import difflib
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from ..runner.dataset import load_testcases
from ..runner.python_runner import PythonSubmissionRunner
from .evaluate import tree_edit_distance
from .inference import _generation_token_budget, extract_python_code


_EXECUTION_SEVERITY = {"AC": 0, "WA": 1, "TLE": 2, "RE": 3, "CE": 4}


@dataclass(frozen=True)
class CandidateGenerationSummary:
    method: str
    base_model: str
    adapter_path: str
    examples: int
    candidates_per_example: int
    generated_candidates: int
    mean_generation_time_sec: float
    output_path: Path


@dataclass(frozen=True)
class CandidateSelectionSummary:
    method: str
    examples: int
    selected_from_base: int
    selected_from_adapter: int
    selected_current_fallback: int
    selected_source_counts: dict[str, int]
    repaired: int
    improved: int
    repair_rate: float
    improvement_rate: float
    mean_tree_edit_distance: float | None
    parseable_for_ted: int
    mean_online_time_sec: float
    output_path: Path


@dataclass(frozen=True)
class CandidateMergeSummary:
    examples: int
    sources: tuple[str, ...]
    generated_candidates: int
    output_path: Path


def merge_generation_candidates(
    generation_paths: list[tuple[str, Path]],
    output_path: Path,
) -> CandidateMergeSummary:
    """Merge existing generation files into the candidate-selection format."""

    if len(generation_paths) < 2:
        raise ValueError("At least two generation sources are required.")
    sources = [source for source, _ in generation_paths]
    if len(sources) != len(set(sources)):
        raise ValueError("Candidate source names must be unique.")

    rows_by_source = {
        source: {str(row["example_id"]): row for row in _iter_jsonl(path)}
        for source, path in generation_paths
    }
    expected_ids = set(next(iter(rows_by_source.values())))
    for source, rows in rows_by_source.items():
        if set(rows) != expected_ids:
            missing = len(expected_ids - set(rows))
            extra = len(set(rows) - expected_ids)
            raise ValueError(
                f"Candidate source {source!r} has mismatched IDs "
                f"(missing={missing}, extra={extra})."
            )

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_count = 0
    with output_path.open("w", encoding="utf-8") as output:
        for example_id in sorted(expected_ids):
            candidates: list[dict[str, Any]] = []
            seen_codes: set[str] = set()
            generation_time = 0.0
            first_row: dict[str, Any] | None = None
            for source, _ in generation_paths:
                row = rows_by_source[source][example_id]
                first_row = first_row or row
                generation_time += float(row.get("generation_time_sec", 0.0))
                code = str(row.get("generated_code", ""))
                normalized = code.strip()
                if normalized in seen_codes:
                    continue
                seen_codes.add(normalized)
                candidates.append(
                    {
                        "candidate_id": f"C{len(candidates) + 1}",
                        "source": source,
                        "generated_code": code,
                        "raw_generation": str(row.get("raw_generation", code)),
                    }
                )
            assert first_row is not None
            candidate_count += len(candidates)
            output.write(
                json.dumps(
                    {
                        "example_id": example_id,
                        "problem_id": first_row["problem_id"],
                        "user_id": first_row["user_id"],
                        "prompt_style": first_row.get("prompt_style"),
                        "generation_time_sec": generation_time,
                        "candidates": candidates,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    summary = CandidateMergeSummary(
        examples=len(expected_ids),
        sources=tuple(sources),
        generated_candidates=candidate_count,
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def select_evaluated_candidates(
    dataset_path: Path,
    evaluation_paths: list[tuple[str, Path]],
    output_path: Path,
    *,
    method: str,
) -> CandidateSelectionSummary:
    """Select among candidates whose execution outcomes are already available."""

    if len(evaluation_paths) < 2:
        raise ValueError("At least two evaluated candidate sources are required.")
    sources = [source for source, _ in evaluation_paths]
    if len(sources) != len(set(sources)):
        raise ValueError("Candidate source names must be unique.")
    records = {str(row["example_id"]): row for row in _iter_jsonl(dataset_path)}
    rows_by_source = {
        source: {str(row["example_id"]): row for row in _iter_jsonl(path)}
        for source, path in evaluation_paths
    }
    expected_ids = set(records)
    for source, rows in rows_by_source.items():
        if set(rows) != expected_ids:
            missing = len(expected_ids - set(rows))
            extra = len(set(rows) - expected_ids)
            raise ValueError(
                f"Evaluated source {source!r} has mismatched IDs "
                f"(missing={missing}, extra={extra})."
            )

    results: list[dict[str, Any]] = []
    for example_id in sorted(expected_ids):
        record = records[example_id]
        current_code = str(record["history"][-1]["code"])
        first = rows_by_source[sources[0]][example_id]
        buggy_pass_rate = float(first["buggy_pass_rate"])
        buggy_verdict = str(first["buggy_verdict"])
        generation_time = 0.0
        candidates: list[dict[str, Any]] = []
        for source in sources:
            row = rows_by_source[source][example_id]
            generation_time += float(row.get("generation_time_sec", 0.0))
            fixed_pass_rate = float(row["fixed_pass_rate"])
            candidates.append(
                {
                    "source": source,
                    "generated_code": str(row.get("generated_code", "")),
                    "raw_generation": str(
                        row.get("raw_generation", row.get("generated_code", ""))
                    ),
                    "execution_verdict": str(row["fixed_verdict"]),
                    "pass_rate": fixed_pass_rate,
                    "non_regressive": fixed_pass_rate >= buggy_pass_rate,
                    "tree_edit_distance": row.get("tree_edit_distance"),
                    "testcase_outcomes": row.get("fixed_tc_outcomes", {}),
                }
            )
        candidates.append(
            {
                "source": "current-fallback",
                "generated_code": current_code,
                "raw_generation": current_code,
                "execution_verdict": buggy_verdict,
                "pass_rate": buggy_pass_rate,
                "non_regressive": True,
                "tree_edit_distance": 0,
                "testcase_outcomes": {},
            }
        )

        def score(item: dict[str, Any]) -> tuple[Any, ...]:
            ted = item.get("tree_edit_distance")
            edit_distance = int(ted) if ted is not None else 10**9
            return (
                int(bool(item["non_regressive"])),
                float(item["pass_rate"]),
                -_EXECUTION_SEVERITY.get(str(item["execution_verdict"]), 5),
                -edit_distance,
                int(str(item["source"]).startswith("adapter")),
            )

        selected = max(candidates, key=score)
        fixed_pass_rate = float(selected["pass_rate"])
        changed = str(selected["generated_code"]).strip() != current_code.strip()
        results.append(
            {
                "example_id": example_id,
                "problem_id": record["problem_id"],
                "user_id": record["user_id"],
                "method": method,
                "prompt_style": first.get("prompt_style"),
                "generation_time_sec": generation_time,
                "generated_code": selected["generated_code"],
                "raw_generation": selected["raw_generation"],
                "buggy_verdict": buggy_verdict,
                "fixed_verdict": selected["execution_verdict"],
                "buggy_pass_rate": buggy_pass_rate,
                "fixed_pass_rate": fixed_pass_rate,
                "repaired": changed and fixed_pass_rate == 1.0,
                "improved": fixed_pass_rate > buggy_pass_rate,
                "tree_edit_distance": selected["tree_edit_distance"],
                "fixed_tc_outcomes": selected["testcase_outcomes"],
                "selected_source": selected["source"],
                "candidate_outcomes": candidates,
            }
        )

    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for item in results:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
    summary = _candidate_selection_summary(method, results, output_path)
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def generate_candidate_repairs(
    dataset_path: Path,
    output_path: Path,
    *,
    prompt_style: str,
    base_model: str,
    adapter_path: Path,
    sampled_candidates: int = 4,
    temperature: float = 0.7,
    top_p: float = 0.95,
    seed: int = 2027,
    resume: bool = True,
) -> CandidateGenerationSummary:
    """Generate complementary base and trajectory-adapter repair candidates."""

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    from .prompts import build_messages, render_generation_prompt

    dataset_path = dataset_path.expanduser().resolve()
    adapter_path = adapter_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(str(adapter_path), use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=quantization,
        device_map={"": 0},
        torch_dtype=compute_dtype,
    )
    model = PeftModel.from_pretrained(base, str(adapter_path))
    model.eval()

    records = list(_iter_jsonl(dataset_path))
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
    pending = [
        record for record in records if str(record["example_id"]) not in existing
    ]
    elapsed_values = [
        float(item.get("generation_time_sec", 0.0)) for item in existing.values()
    ]
    candidate_count = sum(len(item.get("candidates", [])) for item in existing.values())
    mode = "a" if resume and output_path.exists() else "w"
    with output_path.open(mode, encoding="utf-8") as output:
        for record_index, record in enumerate(
            tqdm(pending, desc="Generate repair candidates", unit="example")
        ):
            prompt = render_generation_prompt(
                tokenizer,
                build_messages(record, prompt_style),
            )
            encoded = tokenizer(
                prompt,
                return_tensors="pt",
                add_special_tokens=False,
            ).to(model.device)
            generation_budget = _generation_token_budget(
                model, encoded["input_ids"].shape[1]
            )
            candidates: list[dict[str, Any]] = []
            started = time.perf_counter()
            with torch.inference_mode():
                with model.disable_adapter():
                    base_sequences = model.generate(
                        **encoded,
                        max_new_tokens=generation_budget,
                        do_sample=False,
                        pad_token_id=tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )
                adapter_greedy = model.generate(
                    **encoded,
                    max_new_tokens=generation_budget,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
                sampled = None
                if sampled_candidates > 0:
                    torch.manual_seed(seed + record_index)
                    sampled = model.generate(
                        **encoded,
                        max_new_tokens=generation_budget,
                        do_sample=True,
                        temperature=temperature,
                        top_p=top_p,
                        num_return_sequences=sampled_candidates,
                        pad_token_id=tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                    )
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            input_length = encoded["input_ids"].shape[1]
            groups = [
                ("base-greedy", base_sequences),
                ("adapter-greedy", adapter_greedy),
            ]
            if sampled is not None:
                groups.append(("adapter-sampled", sampled))
            seen_codes: set[str] = set()
            for source, sequences in groups:
                for sequence in sequences:
                    raw = tokenizer.decode(
                        sequence[input_length:], skip_special_tokens=True
                    )
                    code = extract_python_code(raw)
                    normalized = code.strip()
                    if normalized in seen_codes:
                        continue
                    seen_codes.add(normalized)
                    candidates.append(
                        {
                            "candidate_id": f"C{len(candidates) + 1}",
                            "source": source,
                            "generated_code": code,
                            "raw_generation": raw,
                        }
                    )
            item = {
                "example_id": record["example_id"],
                "problem_id": record["problem_id"],
                "user_id": record["user_id"],
                "prompt_style": prompt_style.upper(),
                "generation_time_sec": elapsed,
                "candidates": candidates,
            }
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
            output.flush()
            elapsed_values.append(elapsed)
            candidate_count += len(candidates)

    summary = CandidateGenerationSummary(
        method="ZPDPatch-Candidates",
        base_model=base_model,
        adapter_path=str(adapter_path),
        examples=len(requested_ids),
        candidates_per_example=2 + sampled_candidates,
        generated_candidates=candidate_count,
        mean_generation_time_sec=(
            sum(elapsed_values) / len(elapsed_values) if elapsed_values else 0.0
        ),
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def select_candidate_repairs(
    data_root: Path,
    dataset_path: Path,
    candidates_path: Path,
    output_path: Path,
    *,
    method: str,
    workers: int = 8,
    timeout_sec: float = 2.5,
) -> CandidateSelectionSummary:
    """Select the strongest non-regressive candidate, then prefer smaller edits."""

    records = {item["example_id"]: item for item in _iter_jsonl(dataset_path)}
    candidate_rows = list(_iter_jsonl(candidates_path))
    runner = PythonSubmissionRunner(timeout_sec=timeout_sec, memory_limit_mb=2048)

    def select_one(row: dict[str, Any]) -> dict[str, Any]:
        started = time.perf_counter()
        record = records[row["example_id"]]
        problem_id = str(record["problem_id"])
        current_code = str(record["history"][-1]["code"])
        testcases = load_testcases(data_root / problem_id / "testcases.jsonl")
        current_outcome = runner.run_submission(
            submission_id=f"{record['example_id']}:current",
            problem_id=problem_id,
            code=current_code,
            source_verdict=str(record["history"][-1].get("verdict", "")),
            testcases=testcases,
        )
        current_passed = {
            case.case_id for case in current_outcome.cases if case.verdict.value == "AC"
        }
        evaluated: list[dict[str, Any]] = []
        for candidate in row.get("candidates", []):
            code = str(candidate.get("generated_code", ""))
            outcome = runner.run_submission(
                submission_id=(
                    f"{record['example_id']}:{candidate.get('candidate_id', 'candidate')}"
                ),
                problem_id=problem_id,
                code=code,
                source_verdict=None,
                testcases=testcases,
            )
            passed = {
                case.case_id for case in outcome.cases if case.verdict.value == "AC"
            }
            evaluated.append(
                {
                    **candidate,
                    "execution_verdict": outcome.verdict.value,
                    "passed_testcases": sorted(passed),
                    "testcase_outcomes": {
                        case.case_id: case.verdict.value for case in outcome.cases
                    },
                    "pass_rate": len(passed) / len(testcases),
                    "no_test_regression": current_passed <= passed,
                    "tree_edit_distance": tree_edit_distance(current_code, code),
                    "lexical_edit_distance": _lexical_edit_distance(current_code, code),
                }
            )
        fallback = {
            "candidate_id": "CURRENT",
            "source": "current-fallback",
            "generated_code": current_code,
            "raw_generation": current_code,
            "execution_verdict": current_outcome.verdict.value,
            "passed_testcases": sorted(current_passed),
            "testcase_outcomes": {
                case.case_id: case.verdict.value for case in current_outcome.cases
            },
            "pass_rate": len(current_passed) / len(testcases),
            "no_test_regression": True,
            "tree_edit_distance": 0,
            "lexical_edit_distance": 0,
        }
        evaluated.append(fallback)

        def score(item: dict[str, Any]) -> tuple[Any, ...]:
            ted = item.get("tree_edit_distance")
            edit_distance = (
                int(ted) if ted is not None else int(item["lexical_edit_distance"])
            )
            return (
                int(bool(item["no_test_regression"])),
                len(item["passed_testcases"]),
                -_EXECUTION_SEVERITY.get(str(item["execution_verdict"]), 5),
                -edit_distance,
                int(str(item["source"]).startswith("adapter")),
            )

        selected = max(evaluated, key=score)
        current_pass_rate = len(current_passed) / len(testcases)
        selected_pass_rate = len(selected["passed_testcases"]) / len(testcases)
        changed = str(selected["generated_code"]).strip() != current_code.strip()
        elapsed = float(row.get("generation_time_sec", 0.0)) + (
            time.perf_counter() - started
        )
        return {
            "example_id": record["example_id"],
            "problem_id": problem_id,
            "user_id": record["user_id"],
            "method": method,
            "prompt_style": row.get("prompt_style"),
            "generation_time_sec": elapsed,
            "generated_code": selected["generated_code"],
            "raw_generation": selected["raw_generation"],
            "buggy_verdict": current_outcome.verdict.value,
            "fixed_verdict": selected["execution_verdict"],
            "buggy_pass_rate": current_pass_rate,
            "fixed_pass_rate": selected_pass_rate,
            "repaired": changed and selected_pass_rate == 1.0,
            "improved": selected_pass_rate > current_pass_rate,
            "tree_edit_distance": selected["tree_edit_distance"],
            "fixed_tc_outcomes": selected["testcase_outcomes"],
            "selected_candidate_id": selected["candidate_id"],
            "selected_source": selected["source"],
            "candidate_outcomes": evaluated,
        }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(select_one, row) for row in candidate_rows]
        for future in tqdm(
            as_completed(futures),
            total=len(futures),
            desc="Select repair candidates",
            unit="example",
        ):
            results.append(future.result())
    results.sort(key=lambda item: str(item["example_id"]))
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for item in results:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")

    summary = _candidate_selection_summary(method, results, output_path)
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _candidate_selection_summary(
    method: str,
    results: list[dict[str, Any]],
    output_path: Path,
) -> CandidateSelectionSummary:
    source_counts: dict[str, int] = {}
    for item in results:
        source = str(item["selected_source"])
        source_counts[source] = source_counts.get(source, 0) + 1
    repaired = sum(bool(item["repaired"]) for item in results)
    improved = sum(bool(item["improved"]) for item in results)
    distances = [
        float(item["tree_edit_distance"])
        for item in results
        if item["tree_edit_distance"] is not None
    ]
    return CandidateSelectionSummary(
        method=method,
        examples=len(results),
        selected_from_base=source_counts.get("base-greedy", 0),
        selected_from_adapter=sum(
            count
            for source, count in source_counts.items()
            if source.startswith("adapter")
        ),
        selected_current_fallback=source_counts.get("current-fallback", 0),
        selected_source_counts=source_counts,
        repaired=repaired,
        improved=improved,
        repair_rate=repaired / len(results) if results else 0.0,
        improvement_rate=improved / len(results) if results else 0.0,
        mean_tree_edit_distance=(
            sum(distances) / len(distances) if distances else None
        ),
        parseable_for_ted=len(distances),
        mean_online_time_sec=(
            sum(float(item["generation_time_sec"]) for item in results) / len(results)
            if results
            else 0.0
        ),
        output_path=output_path,
    )


def _lexical_edit_distance(before: str, after: str) -> int:
    before_tokens = before.split()
    after_tokens = after.split()
    matcher = difflib.SequenceMatcher(
        None, before_tokens, after_tokens, autojunk=False
    )
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return max(len(before_tokens), len(after_tokens)) - matched


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
