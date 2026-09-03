#!/usr/bin/env python3
"""Generate fixed-seed stochastic candidates with continuous vLLM batching."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.repair.inference import _example_sampling_seed, extract_python_code
from src.repair.prompts import build_messages, render_generation_prompt


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument(
        "--method-prefix",
        default="Answer2027",
        help="Stable method label written to every generation row.",
    )
    parser.add_argument("--sampling-seed", action="append", type=int, required=True)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.92)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    if args.temperature <= 0 or not 0 < args.top_p <= 1:
        parser.error("invalid stochastic decoding parameters")
    if args.adapter is not None and not (
        args.adapter / "adapter_model.safetensors"
    ).is_file():
        parser.error(f"missing adapter weights: {args.adapter}")
    records = read_jsonl(args.dataset)
    if args.limit is not None:
        records = records[: args.limit]
    if not records:
        parser.error("dataset is empty")

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    prompts = [
        render_generation_prompt(tokenizer, build_messages(record, "D"))
        for record in records
    ]
    prompt_lengths = [
        len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
        for prompt in prompts
    ]
    if any(length >= args.max_model_len for length in prompt_lengths):
        parser.error("a prompt exhausts the fixed vLLM context")

    expanded_prompts: list[str] = []
    sampling_params: list[SamplingParams] = []
    request_keys: list[tuple[int, dict]] = []
    for sampling_seed in args.sampling_seed:
        for record, prompt, prompt_length in zip(
            records, prompts, prompt_lengths, strict=True
        ):
            expanded_prompts.append(prompt)
            sampling_params.append(SamplingParams(
                n=1,
                temperature=args.temperature,
                top_p=args.top_p,
                seed=_example_sampling_seed(
                    sampling_seed, str(record["example_id"])
                ),
                max_tokens=min(
                    args.max_new_tokens, args.max_model_len - prompt_length
                ),
            ))
            request_keys.append((sampling_seed, record))

    model_kwargs = dict(
        model=args.base_model,
        tokenizer=args.base_model,
        quantization="bitsandbytes",
        load_format="bitsandbytes",
        dtype="bfloat16",
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        seed=2027,
    )
    if args.adapter is not None:
        model_kwargs.update(enable_lora=True, max_lora_rank=64)
    model = LLM(**model_kwargs)
    started = time.perf_counter()
    generate_kwargs = {}
    if args.adapter is not None:
        generate_kwargs["lora_request"] = LoRARequest(
            args.method_prefix.lower(), 1, str(args.adapter)
        )
    outputs = model.generate(expanded_prompts, sampling_params, **generate_kwargs)
    elapsed = time.perf_counter() - started
    if len(outputs) != len(request_keys):
        raise RuntimeError("vLLM returned an unexpected request count")

    args.output_root.mkdir(parents=True, exist_ok=True)
    destinations = {
        seed: (args.output_root / f"sample-{seed}.generations.jsonl").open(
            "w", encoding="utf-8"
        )
        for seed in args.sampling_seed
    }
    try:
        for (sampling_seed, record), output in zip(request_keys, outputs, strict=True):
            raw_text = output.outputs[0].text
            payload = {
                "example_id": record["example_id"],
                "problem_id": record["problem_id"],
                "user_id": record["user_id"],
                "method": f"{args.method_prefix}-Sample{sampling_seed}",
                "prompt_style": "D",
                "generation_time_sec": elapsed / len(outputs),
                "generated_code": extract_python_code(raw_text),
                "raw_generation": raw_text,
                "sampling_seed": sampling_seed,
                "example_sampling_seed": _example_sampling_seed(
                    sampling_seed, str(record["example_id"])
                ),
                "temperature": args.temperature,
                "top_p": args.top_p,
                "engine": "vllm-continuous-batching",
            }
            destinations[sampling_seed].write(
                json.dumps(payload, ensure_ascii=False) + "\n"
            )
    finally:
        for destination in destinations.values():
            destination.close()

    summary = {
        "engine": "vllm-continuous-batching",
        "examples": len(records),
        "requests": len(outputs),
        "sampling_seeds": args.sampling_seed,
        "method_prefix": args.method_prefix,
        "adapter": None if args.adapter is None else str(args.adapter),
        "temperature": args.temperature,
        "top_p": args.top_p,
        "max_new_tokens": args.max_new_tokens,
        "max_model_len": args.max_model_len,
        "elapsed_sec": elapsed,
        "mean_request_sec": elapsed / len(outputs),
    }
    (args.output_root / "generation.summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
