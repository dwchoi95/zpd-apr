from __future__ import annotations

import json
import hashlib
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class GenerationSummary:
    method: str
    prompt_style: str
    base_model: str
    adapter_path: str | None
    max_new_tokens: int | None
    sampling_seed: int | None
    temperature: float | None
    top_p: float | None
    examples: int
    generated: int
    mean_generation_time_sec: float
    output_path: Path


def generate_repairs(
    dataset_path: Path,
    output_path: Path,
    *,
    method: str,
    prompt_style: str,
    base_model: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    adapter_path: Path | None = None,
    batch_size: int = 1,
    resume: bool = True,
    max_new_tokens: int | None = None,
    sampling_seed: int | None = None,
    temperature: float = 0.8,
    top_p: float = 0.95,
) -> GenerationSummary:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    from .prompts import build_messages, render_generation_prompt

    tokenizer_source = str(adapter_path) if adapter_path is not None else base_model
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_source, use_fast=True)
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
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=quantization,
        device_map={"": 0},
        torch_dtype=compute_dtype,
    )
    if adapter_path is not None:
        model = PeftModel.from_pretrained(model, str(adapter_path))
    model.eval()

    if sampling_seed is not None:
        if temperature <= 0:
            raise ValueError("temperature must be positive for stochastic decoding")
        if not 0 < top_p <= 1:
            raise ValueError("top_p must be in (0, 1]")

    records = list(_iter_jsonl(dataset_path))
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    requested_ids = {str(record["example_id"]) for record in records}
    existing = (
        _load_resumable_generations(output_path, requested_ids)
        if resume and output_path.exists()
        else {}
    )
    records = [record for record in records if str(record["example_id"]) not in existing]
    elapsed_values = [
        float(item.get("generation_time_sec", 0.0)) for item in existing.values()
    ]

    mode = "a" if resume and output_path.exists() else "w"
    with output_path.open(mode, encoding="utf-8") as output:
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            prompts = [
                render_generation_prompt(
                    tokenizer,
                    build_messages(record, prompt_style),
                )
                for record in batch
            ]
            encoded = tokenizer(
                prompts,
                return_tensors="pt",
                add_special_tokens=False,
                padding=True,
            ).to(model.device)
            torch.cuda.synchronize()
            started = time.perf_counter()
            if sampling_seed is not None:
                if len(batch) != 1:
                    raise ValueError(
                        "stochastic decoding requires batch_size=1 so every example "
                        "has a resume-stable independent RNG seed"
                    )
                example_seed = _example_sampling_seed(
                    sampling_seed, str(batch[0]["example_id"])
                )
                torch.manual_seed(example_seed)
                torch.cuda.manual_seed_all(example_seed)
            with torch.inference_mode():
                sampling_kwargs = (
                    {"temperature": temperature, "top_p": top_p}
                    if sampling_seed is not None
                    else {}
                )
                generated = model.generate(
                    **encoded,
                    max_new_tokens=_generation_token_budget(
                        model, encoded["input_ids"].shape[1], max_new_tokens
                    ),
                    do_sample=sampling_seed is not None,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    **sampling_kwargs,
                )
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - started
            input_length = encoded["input_ids"].shape[1]
            per_example_elapsed = elapsed / len(batch)
            for record, sequence in zip(batch, generated, strict=True):
                raw_text = tokenizer.decode(
                    sequence[input_length:], skip_special_tokens=True
                )
                code = extract_python_code(raw_text)
                payload = {
                    "example_id": record["example_id"],
                    "problem_id": record["problem_id"],
                    "user_id": record["user_id"],
                    "method": method,
                    "prompt_style": prompt_style.upper(),
                    "generation_time_sec": per_example_elapsed,
                    "generated_code": code,
                    "raw_generation": raw_text,
                    "sampling_seed": sampling_seed,
                    "example_sampling_seed": (
                        _example_sampling_seed(sampling_seed, str(record["example_id"]))
                        if sampling_seed is not None
                        else None
                    ),
                    "temperature": temperature if sampling_seed is not None else None,
                    "top_p": top_p if sampling_seed is not None else None,
                }
                output.write(json.dumps(payload, ensure_ascii=False) + "\n")
                output.flush()
                elapsed_values.append(per_example_elapsed)

    summary = GenerationSummary(
        method=method,
        prompt_style=prompt_style.upper(),
        base_model=base_model,
        adapter_path=str(adapter_path) if adapter_path is not None else None,
        max_new_tokens=max_new_tokens,
        sampling_seed=sampling_seed,
        temperature=temperature if sampling_seed is not None else None,
        top_p=top_p if sampling_seed is not None else None,
        examples=len(requested_ids),
        generated=len(elapsed_values),
        mean_generation_time_sec=(
            sum(elapsed_values) / len(elapsed_values) if elapsed_values else 0.0
        ),
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _example_sampling_seed(sampling_seed: int, example_id: str) -> int:
    """Derive a stable per-example RNG seed independent of order and resume state."""
    digest = hashlib.sha256(f"{sampling_seed}:{example_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big") % (2**63 - 1)


def extract_python_code(text: str) -> str:
    text = text.strip()
    fenced = re.search(
        r"```(?:python|java)?\s*\n?(.*?)```", text, flags=re.I | re.S
    )
    if fenced:
        return fenced.group(1).strip()
    return text


def _generation_token_budget(
    model: Any, input_length: int, max_new_tokens: int | None = None
) -> int:
    context_length = getattr(model.config, "max_position_embeddings", None)
    if not isinstance(context_length, int) or context_length < 1:
        raise ValueError("Model config does not expose a finite context length.")
    remaining = context_length - input_length
    if remaining < 1:
        raise ValueError(
            f"Input uses {input_length} tokens but model context is "
            f"{context_length}; the input is not truncated."
        )
    if max_new_tokens is not None:
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be positive")
        remaining = min(remaining, max_new_tokens)
    return remaining


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _load_resumable_generations(
    output_path: Path,
    requested_ids: set[str],
) -> dict[str, dict[str, Any]]:
    rows = list(_iter_jsonl(output_path))
    row_ids = [str(item.get("example_id", "")) for item in rows]
    if any(not example_id for example_id in row_ids):
        raise ValueError(f"Generation output contains an empty example_id: {output_path}")
    if len(set(row_ids)) != len(row_ids):
        raise ValueError(f"Duplicate example_id in generation output: {output_path}")
    foreign_ids = sorted(set(row_ids) - requested_ids)
    if foreign_ids:
        preview = ", ".join(foreign_ids[:3])
        raise ValueError(
            "Generation output belongs to a different dataset; "
            f"found {len(foreign_ids)} foreign example_id(s) in {output_path}: "
            f"{preview}"
        )
    return {example_id: item for example_id, item in zip(row_ids, rows, strict=True)}
