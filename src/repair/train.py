from __future__ import annotations

import json
from difflib import SequenceMatcher
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TrainingSummary:
    dataset_path: Path
    base_model: str
    prompt_style: str
    source_examples: int
    encoded_examples: int
    validation_examples: int
    encoded_validation_examples: int
    completed_steps: int
    completed_epochs: float
    approximate_examples_seen: int
    per_device_batch_size: int
    gradient_accumulation_steps: int
    effective_batch_size: int
    edit_token_weight: float
    num_train_epochs: float
    resume_from_checkpoint: str | None
    best_eval_loss: float | None
    best_checkpoint: str | None
    output_dir: Path


def train_qlora(
    dataset_path: Path,
    output_dir: Path,
    *,
    prompt_style: str,
    base_model: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    num_train_epochs: float = 1.0,
    learning_rate: float = 2e-4,
    edit_token_weight: float = 1.0,
    validation_dataset_path: Path | None = None,
    eval_steps: int = 100,
    early_stopping_patience: int = 3,
    save_steps: int = 0,
    seed: int = 2027,
    per_device_batch_size: int = 1,
    gradient_accumulation_steps: int = 16,
    resume_from_checkpoint: Path | None = None,
) -> TrainingSummary:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )

    from .prompts import build_messages, render_generation_prompt

    dataset_path = dataset_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if resume_from_checkpoint is not None:
        resume_from_checkpoint = resume_from_checkpoint.expanduser().resolve()
        if not resume_from_checkpoint.is_dir():
            raise FileNotFoundError(
                f"Checkpoint directory not found: {resume_from_checkpoint}"
            )
    tokenizer = AutoTokenizer.from_pretrained(base_model, use_fast=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    raw_dataset = load_dataset("json", data_files=str(dataset_path), split="train")
    source_examples = len(raw_dataset)

    def encode(record: dict[str, Any]) -> dict[str, Any]:
        messages = build_messages(
            record,
            prompt_style,
        )
        prompt = render_generation_prompt(tokenizer, messages)
        target_code = str(record["target_code"]).rstrip()
        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        target_ids = tokenizer(target_code, add_special_tokens=False)["input_ids"]
        target_ids.append(tokenizer.eos_token_id)
        full_ids = prompt_ids + target_ids
        target_weights = _target_loss_weights(
            tokenizer,
            str(record["history"][-1]["code"]),
            target_code,
            edit_token_weight,
        )
        target_weights.append(1.0)
        return {
            "input_ids": full_ids,
            "attention_mask": [1] * len(full_ids),
            "labels": [-100] * len(prompt_ids) + target_ids,
            "loss_weights": [0.0] * len(prompt_ids) + target_weights,
        }

    encoded = raw_dataset.map(
        encode,
        remove_columns=raw_dataset.column_names,
        desc=f"Tokenize prompt {prompt_style.upper()}",
    )
    validation_examples = 0
    encoded_validation_examples = 0
    encoded_validation = None
    if validation_dataset_path is not None:
        validation_dataset_path = validation_dataset_path.expanduser().resolve()
        raw_validation = load_dataset(
            "json",
            data_files=str(validation_dataset_path),
            split="train",
        )
        validation_examples = len(raw_validation)
        encoded_validation = raw_validation.map(
            encode,
            remove_columns=raw_validation.column_names,
            desc=f"Tokenize validation prompt {prompt_style.upper()}",
        )
        encoded_validation_examples = len(encoded_validation)

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
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False
    lora = LoraConfig(
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
    )
    from peft import get_peft_model

    model = get_peft_model(model, lora)
    has_validation = encoded_validation is not None
    checkpoint_steps = eval_steps if has_validation else save_steps
    args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=per_device_batch_size,
        per_device_eval_batch_size=per_device_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        fp16=compute_dtype == torch.float16,
        bf16=compute_dtype == torch.bfloat16,
        logging_steps=10,
        eval_strategy="epoch" if has_validation else "no",
        eval_steps=max(1, eval_steps),
        save_strategy=(
            "epoch" if checkpoint_steps > 0 else "no"
        ),
        save_steps=max(1, checkpoint_steps),
        save_total_limit=2,
        load_best_model_at_end=has_validation,
        metric_for_best_model="eval_loss" if has_validation else None,
        greater_is_better=False if has_validation else None,
        report_to=[],
        seed=seed,
        data_seed=seed,
        remove_unused_columns=False,
        gradient_checkpointing=True,
        group_by_length=True,
        optim="paged_adamw_8bit",
    )
    trainer = _EditWeightedTrainer(
        model=model,
        args=args,
        train_dataset=encoded,
        eval_dataset=encoded_validation,
        data_collator=_TokenCollator(tokenizer.pad_token_id),
        callbacks=(
            [
                EarlyStoppingCallback(
                    early_stopping_patience=early_stopping_patience,
                )
            ]
            if has_validation
            else None
        ),
    )
    trainer.train(
        resume_from_checkpoint=(
            str(resume_from_checkpoint)
            if resume_from_checkpoint is not None
            else None
        )
    )
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    summary = TrainingSummary(
        dataset_path=dataset_path,
        base_model=base_model,
        prompt_style=prompt_style.upper(),
        source_examples=source_examples,
        encoded_examples=len(encoded),
        validation_examples=validation_examples,
        encoded_validation_examples=encoded_validation_examples,
        completed_steps=int(trainer.state.global_step),
        completed_epochs=float(trainer.state.epoch or 0.0),
        approximate_examples_seen=(
            int(trainer.state.global_step)
            * per_device_batch_size
            * gradient_accumulation_steps
        ),
        per_device_batch_size=per_device_batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        effective_batch_size=per_device_batch_size * gradient_accumulation_steps,
        edit_token_weight=edit_token_weight,
        num_train_epochs=num_train_epochs,
        resume_from_checkpoint=(
            str(resume_from_checkpoint)
            if resume_from_checkpoint is not None
            else None
        ),
        best_eval_loss=(
            float(trainer.state.best_metric)
            if trainer.state.best_metric is not None
            else None
        ),
        best_checkpoint=trainer.state.best_model_checkpoint,
        output_dir=output_dir,
    )
    (output_dir / "training_summary.json").write_text(
        json.dumps(asdict(summary), indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


class _TokenCollator:
    def __init__(self, pad_token_id: int) -> None:
        self.pad_token_id = pad_token_id

    def __call__(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        import torch

        longest = max(len(item["input_ids"]) for item in features)

        def padded(key: str, fill: int) -> list[list[int]]:
            return [
                list(item[key]) + [fill] * (longest - len(item[key]))
                for item in features
            ]

        return {
            "input_ids": torch.tensor(padded("input_ids", self.pad_token_id)),
            "attention_mask": torch.tensor(padded("attention_mask", 0)),
            "labels": torch.tensor(padded("labels", -100)),
            "loss_weights": torch.tensor(
                padded("loss_weights", 0.0), dtype=torch.float32
            ),
        }


def _target_loss_weights(
    tokenizer: Any,
    current_code: str,
    target_code: str,
    edit_token_weight: float,
) -> list[float]:
    if edit_token_weight < 1.0:
        raise ValueError("edit_token_weight must be at least 1.0")
    current_ids = tokenizer(current_code, add_special_tokens=False)["input_ids"]
    target_ids = tokenizer(target_code, add_special_tokens=False)["input_ids"]
    weights = [1.0] * len(target_ids)
    matcher = SequenceMatcher(None, current_ids, target_ids, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if j1 == j2:
            if weights:
                weights[min(j1, len(weights) - 1)] = edit_token_weight
            continue
        for index in range(j1, j2):
            weights[index] = edit_token_weight
    return weights


class _EditWeightedTrainer:
    """Lazily inherit Trainer so importing this module does not require transformers."""

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        from transformers import Trainer

        class TrainerWithEditWeights(Trainer):
            def compute_loss(
                self,
                model: Any,
                inputs: dict[str, Any],
                return_outputs: bool = False,
                num_items_in_batch: Any = None,
            ) -> Any:
                del num_items_in_batch
                import torch.nn.functional as functional

                loss_weights = inputs.pop("loss_weights")
                labels = inputs["labels"]
                outputs = model(**inputs)
                shift_logits = outputs.logits[..., :-1, :].contiguous()
                shift_labels = labels[..., 1:].contiguous()
                shift_weights = loss_weights[..., 1:].contiguous()
                valid = shift_labels.ne(-100)
                token_loss = functional.cross_entropy(
                    shift_logits.view(-1, shift_logits.size(-1)),
                    shift_labels.view(-1),
                    reduction="none",
                    ignore_index=-100,
                ).view_as(shift_labels)
                effective_weights = shift_weights * valid
                loss = (token_loss * effective_weights).sum() / effective_weights.sum().clamp_min(1.0)
                return (loss, outputs) if return_outputs else loss

        return TrainerWithEditWeights(*args, **kwargs)
