from __future__ import annotations

import argparse
import gc
import heapq
import json
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as functional
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

from src.repair.prompts import build_messages, render_generation_prompt
from src.repair.train import _TokenCollator, _target_loss_weights


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure worst-case QLoRA micro-batch memory and throughput."
    )
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--gradient-checkpointing", action="store_true")
    parser.add_argument("--repeats", type=int, default=2)
    return parser.parse_args()


def _longest_features(
    dataset: Path,
    tokenizer: Any,
    *,
    count: int,
) -> list[dict[str, Any]]:
    longest: list[tuple[int, int, dict[str, Any]]] = []
    with dataset.open(encoding="utf-8") as source:
        for index, line in enumerate(source):
            if not line.strip():
                continue
            record = json.loads(line)
            prompt = render_generation_prompt(
                tokenizer,
                build_messages(record, "D"),
            )
            target_code = str(record["target_code"]).rstrip()
            prompt_ids = tokenizer(
                prompt,
                add_special_tokens=False,
            )["input_ids"]
            target_ids = tokenizer(
                target_code,
                add_special_tokens=False,
            )["input_ids"]
            target_ids.append(tokenizer.eos_token_id)
            weights = _target_loss_weights(
                tokenizer,
                str(record["history"][-1]["code"]),
                target_code,
                1.0,
            )
            weights.append(1.0)
            feature = {
                "input_ids": prompt_ids + target_ids,
                "attention_mask": [1] * (len(prompt_ids) + len(target_ids)),
                "labels": [-100] * len(prompt_ids) + target_ids,
                "loss_weights": [0.0] * len(prompt_ids) + weights,
            }
            item = (len(feature["input_ids"]), index, feature)
            if len(longest) < count:
                heapq.heappush(longest, item)
            elif item[0] > longest[0][0]:
                heapq.heapreplace(longest, item)
    return [
        item[2]
        for item in sorted(longest, key=lambda value: (-value[0], value[1]))
    ]


def _weighted_loss(model: Any, batch: dict[str, torch.Tensor]) -> torch.Tensor:
    weights = batch.pop("loss_weights")
    labels = batch["labels"]
    outputs = model(**batch)
    shift_logits = outputs.logits[..., :-1, :].contiguous()
    shift_labels = labels[..., 1:].contiguous()
    shift_weights = weights[..., 1:].contiguous()
    valid = shift_labels.ne(-100)
    token_loss = functional.cross_entropy(
        shift_logits.view(-1, shift_logits.size(-1)),
        shift_labels.view(-1),
        reduction="none",
        ignore_index=-100,
    ).view_as(shift_labels)
    effective_weights = shift_weights * valid
    return (token_loss * effective_weights).sum() / effective_weights.sum().clamp_min(
        1.0
    )


def main() -> None:
    args = _arguments()
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    maximum_batch = max(args.batch_sizes)
    features = _longest_features(
        args.dataset.expanduser().resolve(),
        tokenizer,
        count=maximum_batch,
    )
    print(
        json.dumps(
            {
                "event": "selected_longest_examples",
                "lengths": [len(item["input_ids"]) for item in features],
            }
        ),
        flush=True,
    )

    compute_dtype = (
        torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    )
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=compute_dtype,
        ),
        device_map={"": 0},
        torch_dtype=compute_dtype,
    )
    model = prepare_model_for_kbit_training(
        model,
        use_gradient_checkpointing=args.gradient_checkpointing,
    )
    model.config.use_cache = False
    model = get_peft_model(
        model,
        LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
        ),
    )
    model.train()
    collator = _TokenCollator(tokenizer.pad_token_id)

    for batch_size in args.batch_sizes:
        if batch_size > len(features):
            break
        durations: list[float] = []
        try:
            for _repeat in range(args.repeats):
                model.zero_grad(set_to_none=True)
                gc.collect()
                torch.cuda.empty_cache()
                torch.cuda.reset_peak_memory_stats()
                batch = {
                    key: value.to("cuda")
                    for key, value in collator(features[:batch_size]).items()
                }
                torch.cuda.synchronize()
                started = time.perf_counter()
                loss = _weighted_loss(model, batch)
                loss.backward()
                torch.cuda.synchronize()
                durations.append(time.perf_counter() - started)
                peak_allocated = torch.cuda.max_memory_allocated() / 1024**2
                peak_reserved = torch.cuda.max_memory_reserved() / 1024**2
                del batch, loss
            median_seconds = sorted(durations)[len(durations) // 2]
            sequence_length = len(features[0]["input_ids"])
            print(
                json.dumps(
                    {
                        "event": "batch_result",
                        "gradient_checkpointing": args.gradient_checkpointing,
                        "batch_size": batch_size,
                        "sequence_length": sequence_length,
                        "seconds": median_seconds,
                        "examples_per_second": batch_size / median_seconds,
                        "tokens_per_second": (
                            batch_size * sequence_length / median_seconds
                        ),
                        "peak_allocated_mib": peak_allocated,
                        "peak_reserved_mib": peak_reserved,
                        "status": "ok",
                    }
                ),
                flush=True,
            )
        except torch.cuda.OutOfMemoryError as error:
            model.zero_grad(set_to_none=True)
            gc.collect()
            torch.cuda.empty_cache()
            print(
                json.dumps(
                    {
                        "event": "batch_result",
                        "gradient_checkpointing": args.gradient_checkpointing,
                        "batch_size": batch_size,
                        "status": "oom",
                        "error": str(error),
                    }
                ),
                flush=True,
            )
            break


if __name__ == "__main__":
    main()
