#!/usr/bin/env python3
"""Generate greedy candidates for several LoRA adapters in one vLLM process."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from src.repair.inference import extract_python_code
from src.repair.prompts import build_messages, render_generation_prompt


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def parse_adapter(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise ValueError("adapter must use NAME=PATH")
    name, path = value.split("=", 1)
    if not name or not path:
        raise ValueError("adapter must use NAME=PATH")
    return name, Path(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--adapter", action="append", required=True)
    parser.add_argument("--max-new-tokens", type=int, default=4096)
    parser.add_argument("--max-model-len", type=int, default=8192)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.82)
    args = parser.parse_args()
    adapters = [parse_adapter(value) for value in args.adapter]
    if len({name for name, _path in adapters}) != len(adapters):
        parser.error("adapter names must be unique")
    for _name, path in adapters:
        if not (path / "adapter_model.safetensors").is_file():
            parser.error(f"missing adapter weights: {path}")

    records = read_jsonl(args.dataset)
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
    lengths = [
        len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
        for prompt in prompts
    ]
    if any(length >= args.max_model_len for length in lengths):
        parser.error("a prompt exhausts the fixed vLLM context")
    params = [
        SamplingParams(
            temperature=0.0,
            max_tokens=min(args.max_new_tokens, args.max_model_len - length),
        )
        for length in lengths
    ]
    model = LLM(
        model=args.base_model,
        tokenizer=args.base_model,
        quantization="bitsandbytes",
        load_format="bitsandbytes",
        dtype="bfloat16",
        enable_lora=True,
        max_lora_rank=64,
        max_model_len=args.max_model_len,
        gpu_memory_utilization=args.gpu_memory_utilization,
        seed=2027,
    )
    args.output_root.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index, (name, adapter) in enumerate(adapters, start=1):
        started = time.perf_counter()
        outputs = model.generate(
            prompts,
            params,
            lora_request=LoRARequest(name.lower(), index, str(adapter)),
        )
        elapsed = time.perf_counter() - started
        if len(outputs) != len(records):
            raise RuntimeError(f"{name}: unexpected vLLM request count")
        destination = args.output_root / f"{name}.generations.jsonl"
        with destination.open("w", encoding="utf-8") as sink:
            for record, output in zip(records, outputs, strict=True):
                raw = output.outputs[0].text
                sink.write(
                    json.dumps(
                        {
                            "example_id": record["example_id"],
                            "problem_id": record["problem_id"],
                            "user_id": record["user_id"],
                            "method": f"{name}-ObservedOnly",
                            "prompt_style": "D",
                            "generation_time_sec": elapsed / len(outputs),
                            "generated_code": extract_python_code(raw),
                            "raw_generation": raw,
                            "temperature": 0.0,
                            "engine": "vllm-continuous-batching",
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        summaries.append(
            {"adapter": name, "examples": len(outputs), "elapsed_sec": elapsed}
        )
    (args.output_root / "generation.summary.json").write_text(
        json.dumps(
            {
                "engine": "vllm-continuous-batching",
                "decoding": "greedy",
                "adapters": summaries,
                "max_new_tokens": args.max_new_tokens,
                "max_model_len": args.max_model_len,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
