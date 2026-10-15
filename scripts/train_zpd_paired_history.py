"""Opt-in paired, pre-rendered-message QLoRA primitive; no legacy trainer changes.

The caller owns source/model/runtime pins and cgroup/normal-exit certification.
Preflight never loads a model. Training uses one fresh adapter, one full epoch,
the supplied common order, and descriptive end-of-epoch validation only.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import time

from src.repair.prompts import render_generation_prompt
from src.repair.train import (
    _TokenCollator, _edit_weighted_causal_loss,
    _forward_without_output_fp32_conversion,
)

VERSION = 'paired_history_training_v1'
ARMS = ('C', 'H')
CAPS = dict(max_input_tokens=4096, max_full_tokens=8192, max_output_tokens=4096)
CONFIG = dict(num_train_epochs=1.0, learning_rate=2e-4,
    per_device_train_batch_size=2, per_device_eval_batch_size=2,
    gradient_accumulation_steps=8, lr_scheduler_type='cosine', warmup_ratio=.03,
    optim='paged_adamw_8bit', weight_decay=0.0, max_grad_norm=1.0,
    bf16=True, fp16=False, gradient_checkpointing=True, group_by_length=False,
    eval_strategy='epoch', save_strategy='no', load_best_model_at_end=False,
    logging_steps=10, report_to=[], remove_unused_columns=False,
    dataloader_num_workers=0, dataloader_drop_last=False)
LORA = dict(r=16, lora_alpha=32, lora_dropout=.05, bias='none',
    task_type='CAUSAL_LM', target_modules=[
        'q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _write(path, value, *, atomic=False):
    path = Path(path)
    temporary = path.with_name(path.name + '.partial') if atomic else path
    with temporary.open('xb') as stream:
        stream.write(encoded(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
    if atomic:
        os.replace(temporary, path)


def _record(record):
    require(type(record) is dict, 'record must be an object')
    for name in ('example_id', 'current_code', 'target_code'):
        require(type(record.get(name)) is str, 'string field required: ' + name)
    require(bool(record['example_id']), 'nonempty example ID required')
    messages = record.get('messages')
    require(type(messages) is list and len(messages) >= 2, 'complete messages required')
    for index, message in enumerate(messages):
        require(type(message) is dict and set(message) == {'role', 'content'}
                and message['role'] == ('system' if index == 0 else 'user')
                and type(message['content']) is str, 'system/user data messages only')
    return {k: deepcopy(record[k]) for k in ('example_id', 'messages', 'current_code', 'target_code')}


def _tokens(tokenizer, text):
    result = tokenizer(text, add_special_tokens=False, truncation=False)['input_ids']
    require(type(result) is list and all(type(i) is int and i >= 0 for i in result),
            'plain untruncated token IDs required')
    return result


def encode_record(record, tokenizer):
    """Pure uncapped encoding for outcome-blind, whole-trajectory preparation.

    No model loads, filtering or truncation. output_tokens includes exactly one
    appended EOS. Extra audit fields never enter the rendered messages.
    """
    record = _record(record)
    require(type(tokenizer.eos_token_id) is int and tokenizer.eos_token_id >= 0,
            'explicit EOS token required')
    prompt = render_generation_prompt(tokenizer, record['messages'])
    require(type(prompt) is str, 'chat template must return text')
    prompt_ids = _tokens(tokenizer, prompt)
    require(prompt_ids, 'nonempty rendered prompt required')
    normalized = record['target_code'].rstrip()
    target_ids = _tokens(tokenizer, normalized) + [tokenizer.eos_token_id]
    full = len(prompt_ids) + len(target_ids)
    return dict(example_id=record['example_id'], input_ids=prompt_ids + target_ids,
        attention_mask=[1] * full, labels=[-100] * len(prompt_ids) + target_ids,
        loss_weights=[0.0] * len(prompt_ids) + [1.0] * len(target_ids),
        prompt_tokens=len(prompt_ids), output_tokens=len(target_ids), full_tokens=full,
        current_sha256=sha(record['current_code'].encode()),
        target_raw_sha256=sha(record['target_code'].encode()),
        target_normalized_sha256=sha(normalized.encode()),
        target_token_ids_sha256=sha(encoded(target_ids)),
        messages_sha256=sha(encoded(record['messages'])),
        rendered_prompt_sha256=sha(prompt.encode()))


def paired_preflight(c_records, h_records, tokenizer, *, max_input_tokens=4096,
                     max_full_tokens=8192, max_output_tokens=4096):
    """Return JSON-safe {report, encoded:{C,H}}; reject, never filter/truncate.

    Each encoded row includes an audit-only example_id, stripped by the trainer.
    The normalized target contract is legacy rstrip + separately tokenized EOS.
    """
    caps = dict(max_input_tokens=max_input_tokens, max_full_tokens=max_full_tokens,
                max_output_tokens=max_output_tokens)
    require(all(type(v) is int and v > 0 for v in caps.values()), 'positive integer caps required')
    require(type(tokenizer.eos_token_id) is int and tokenizer.eos_token_id >= 0,
            'explicit EOS token required')
    records = {a: [_record(r) for r in rows] for a, rows in zip(ARMS, (c_records, h_records), strict=True)}
    ids = [r['example_id'] for r in records['C']]
    require(ids and len(set(ids)) == len(ids), 'nonempty unique example roster required')
    require(ids == [r['example_id'] for r in records['H']], 'paired IDs/order differ')
    features = {a: [] for a in ARMS}; pins = []; overflow = []
    for c, h in zip(records['C'], records['H'], strict=True):
        require(c['current_code'] == h['current_code'] and c['target_code'] == h['target_code'],
                'paired current/target source differs: ' + c['example_id'])
        rows = {a: encode_record(r, tokenizer) for a, r in zip(ARMS, (c, h), strict=True)}
        targets = {a: r['input_ids'][r['prompt_tokens']:] for a, r in rows.items()}
        require(targets['C'] == targets['H'], 'paired encoded targets differ')
        row = {k: rows['C'][k] for k in ('example_id', 'current_sha256', 'target_raw_sha256',
               'target_normalized_sha256', 'target_token_ids_sha256')}
        row.update(target_tokens=rows['C']['output_tokens'], arms={})
        for arm, feature in rows.items():
            n, t, total = feature['prompt_tokens'], feature['output_tokens'], feature['full_tokens']
            row['arms'][arm] = {k: feature[k] for k in ('messages_sha256', 'rendered_prompt_sha256', 'prompt_tokens')}
            row['arms'][arm]['total_tokens'] = total
            if n > max_input_tokens or t > max_output_tokens or total > max_full_tokens:
                overflow.append(dict(example_id=feature['example_id'], arm=arm,
                                     prompt_tokens=n, target_tokens=t, total_tokens=total))
            features[arm].append({k: feature[k] for k in ('example_id', 'input_ids', 'attention_mask', 'labels', 'loss_weights')})
        pins.append(row)
    require(not overflow, 'untruncated paired preflight overlength: ' + json.dumps(overflow, sort_keys=True))
    report = dict(version=VERSION, status='passed', examples=len(ids), example_ids=ids,
        order_sha256=sha(encoded(ids)), caps=caps, eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id,
        excluded_examples=0, truncation=False, target_contract='rstrip_separate_tokenization_then_one_eos',
        edit_token_weight=1.0, per_example=pins,
        records_sha256={a: sha(encoded(records[a])) for a in ARMS},
        encoded_sha256={a: sha(encoded(features[a])) for a in ARMS})
    return dict(report=report, encoded=features)


def validate_preflight(paired):
    """Recheck in-memory prepared feature seals and exact common target masks."""
    report, features = paired['report'], paired['encoded']
    require(report['version'] == VERSION and report['status'] == 'passed'
            and report['truncation'] is False and report['excluded_examples'] == 0,
            'passed, unfiltered paired preflight required')
    ids = report['example_ids']; caps = report['caps']
    require(ids and len(set(ids)) == len(ids) == report['examples']
            and sha(encoded(ids)) == report['order_sha256'], 'preflight roster differs')
    require(set(features) == set(ARMS) and len(report['per_example']) == len(ids), 'preflight schema differs')
    for arm in ARMS:
        require(sha(encoded(features[arm])) == report['encoded_sha256'][arm]
                and [r['example_id'] for r in features[arm]] == ids, 'encoded feature pin/order differs')
        for row, pin in zip(features[arm], report['per_example'], strict=True):
            n = pin['arms'][arm]['prompt_tokens']; t = pin['target_tokens']; full = n + t
            require(row['example_id'] == pin['example_id'] and n > 0 and t > 0
                    and n <= caps['max_input_tokens'] and t <= caps['max_output_tokens']
                    and full <= caps['max_full_tokens'] and full == pin['arms'][arm]['total_tokens'],
                    'feature token caps differ')
            require(len(row['input_ids']) == full and row['attention_mask'] == [1] * full
                    and row['labels'] == [-100] * n + row['input_ids'][n:]
                    and row['loss_weights'] == [0.0] * n + [1.0] * t
                    and row['input_ids'][-1] == report['eos_token_id']
                    and sha(encoded(row['input_ids'][n:])) == pin['target_token_ids_sha256'],
                    'target/masking contract differs')
    return report


class FeatureDataset:
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        return self.rows[index]


class JournalCollator:
    def __init__(self, pad_token_id):
        self.collate = _TokenCollator(pad_token_id)

    def __call__(self, features):
        return dict(self.collate(features), example_ids=[r['example_id'] for r in features])


class ConsumptionJournal:
    """Count successful training microbatches, not estimated optimizer exposure."""
    def __init__(self, output, arm, ids):
        self.output, self.arm, self.ids = Path(output), arm, list(ids)
        require(self.ids and len(set(self.ids)) == len(self.ids), 'unique journal plan required')
        self.consumed = []; self.batches = 0; self.started = time.monotonic()
        self.stream = (self.output / 'consumed-examples.jsonl').open('x', encoding='utf-8')
        self.status('training')

    def check(self, ids):
        require(type(ids) is list and ids and ids == self.ids[len(self.consumed):len(self.consumed) + len(ids)],
                'training traversal differs from common plan')

    def commit(self, ids):
        self.check(ids)
        event = dict(batch_index=self.batches, example_ids=ids, offset=len(self.consumed))
        self.stream.write(encoded(event).decode() + '\n'); self.stream.flush(); os.fsync(self.stream.fileno())
        self.consumed.extend(ids); self.batches += 1; self.status('training')

    def status(self, phase):
        result = dict(phase=phase, arm=self.arm, completed_examples=len(self.consumed),
            total_examples=len(self.ids), unique_completed_examples=len(set(self.consumed)),
            successful_training_microbatches=self.batches, elapsed_seconds=time.monotonic() - self.started,
            consumed_order_sha256=sha(encoded(self.consumed)), planned_order_sha256=sha(encoded(self.ids)),
            coverage_semantics='successful_training_step_calls_not_optimizer_update_estimate')
        _write(self.output / 'STATUS.json', result, atomic=True)
        return result

    def finish(self):
        require(self.consumed == self.ids, 'incomplete one-epoch example traversal')
        return self.status('training_complete')

    def close(self):
        self.stream.close()


def trainer_class(base=None):
    """Import Trainer lazily; injectable base supports synthetic tests."""
    if base is None:
        from transformers import Trainer
        base = Trainer

    class PairedTrainer(base):
        def __init__(self, *args, journal=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.journal = journal
            # Our loss is already a per-microbatch mean, not a batch-item sum.
            self.model_accepts_loss_kwargs = False

        def _get_train_sampler(self, train_dataset=None):
            from torch.utils.data import SequentialSampler
            return SequentialSampler(self.train_dataset if train_dataset is None else train_dataset)

        def _get_eval_sampler(self, eval_dataset):
            from torch.utils.data import SequentialSampler
            return SequentialSampler(eval_dataset)

        def training_step(self, model, inputs, num_items_in_batch=None):
            inputs = dict(inputs); ids = inputs.pop('example_ids')
            require(self.journal is not None, 'exact training journal required')
            self.journal.check(ids)
            loss = super().training_step(model, inputs, num_items_in_batch)
            self.journal.commit(ids)
            return loss

        def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
            del num_items_in_batch
            inputs = dict(inputs); inputs.pop('example_ids', None)
            weights, labels = inputs.pop('loss_weights'), inputs.pop('labels')
            output = _forward_without_output_fp32_conversion(model, inputs)
            loss = _edit_weighted_causal_loss(output.logits, labels, weights)
            return (loss, output) if return_outputs else loss

    return PairedTrainer


def trainable_fingerprint(model):
    import torch
    digest = hashlib.sha256(); parameters = 0; tensors = 0
    for name, parameter in sorted(model.named_parameters()):
        if not parameter.requires_grad:
            continue
        require('lora_' in name, 'unexpected trainable base parameter: ' + name)
        value = parameter.detach().cpu().contiguous()
        metadata = dict(name=name, shape=list(value.shape), dtype=str(value.dtype))
        digest.update(encoded(metadata) + b'\n')
        digest.update(value.view(torch.uint8).numpy().tobytes())
        parameters += parameter.numel(); tensors += 1
    require(tensors > 0, 'no trainable adapter tensors')
    return dict(sha256=digest.hexdigest(), trainable_parameters=parameters, tensors=tensors)


def load_fresh_model(base_model, seed):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, set_seed
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    require(type(seed) is int and seed >= 0, 'integer seed required')
    require(os.environ.get('WORLD_SIZE', '1') == '1' and torch.cuda.is_available()
            and torch.cuda.is_bf16_supported(), 'single-process CUDA BF16 runtime required')
    # Includes all random adapter initialization, not only Trainer construction.
    set_seed(seed)
    tokenizer = AutoTokenizer.from_pretrained(str(base_model), use_fast=True, local_files_only=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = 'right'
    model = AutoModelForCausalLM.from_pretrained(str(base_model), local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16),
        device_map={'': 0}, torch_dtype=torch.bfloat16)
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model.config.use_cache = False
    model = get_peft_model(model, LoraConfig(**deepcopy(LORA)))
    return model, tokenizer


def _new_output(output_dir):
    output = Path(output_dir).absolute()
    require(output.resolve() == output and not output.exists(), 'fresh canonical output required; no resume/overwrite')
    output.mkdir(parents=True, exist_ok=False)
    return output


def _versions():
    from importlib.metadata import version
    return {p: version(p) for p in ('torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes')}


def _matching_tokenizer(tokenizer, *reports):
    require(all(tokenizer.eos_token_id == r['eos_token_id'] and tokenizer.pad_token_id == r['pad_token_id']
                for r in reports), 'loaded tokenizer differs from preflight IDs')


def train_arm(arm, paired, validation_paired, *, base_model, output_dir, seed=2027):
    """One fresh-base arm; no checkpoint/arm selection and no resume.

    A COMPLETE marker here remains provisional until caller normal-exit checking.
    Caller must pin tokenizer/model files: token IDs alone are not a file seal.
    """
    require(arm in ARMS, 'C or H arm required')
    train_report = validate_preflight(paired); valid_report = validate_preflight(validation_paired)
    require(train_report['caps'] == valid_report['caps'] == CAPS, 'frozen training token caps required')
    require(not (set(train_report['example_ids']) & set(valid_report['example_ids'])),
            'training/validation example IDs overlap')
    output = _new_output(output_dir); journal = None
    try:
        from transformers import TrainingArguments
        _write(output / 'preflight.json', dict(train=train_report, validation=valid_report))
        model, tokenizer = load_fresh_model(base_model, seed)
        _matching_tokenizer(tokenizer, train_report, valid_report)
        initial = trainable_fingerprint(model)
        _write(output / 'initialization.json', dict(seed=seed, base_model=str(base_model),
            initial_adapter=initial, lora=LORA, runtime_versions=_versions()))
        journal = ConsumptionJournal(output, arm, train_report['example_ids'])
        args = TrainingArguments(output_dir=str(output), seed=seed, data_seed=seed, **deepcopy(CONFIG))
        trainer = trainer_class()(model=model, args=args,
            train_dataset=FeatureDataset(paired['encoded'][arm]),
            eval_dataset=FeatureDataset(validation_paired['encoded'][arm]),
            data_collator=JournalCollator(tokenizer.pad_token_id), journal=journal)
        trainer.train(resume_from_checkpoint=None)
        coverage = journal.finish()
        require(math.isclose(float(trainer.state.epoch or 0), 1.0, abs_tol=1e-8), 'exact one epoch required')
        expected_steps = math.ceil(math.ceil(train_report['examples'] / CONFIG['per_device_train_batch_size'])
                                   / CONFIG['gradient_accumulation_steps'])
        require(int(trainer.state.global_step) == expected_steps, 'fixed one-epoch optimizer step count differs')
        validations = [r for r in trainer.state.log_history if 'eval_loss' in r]
        require(len(validations) == 1 and math.isfinite(float(validations[0]['eval_loss']))
                and math.isclose(float(validations[0]['epoch']), 1.0, abs_tol=1e-8),
                'one finite end-of-epoch descriptive validation required')
        final = trainable_fingerprint(model)
        adapter = output / 'adapter'; model.save_pretrained(adapter); tokenizer.save_pretrained(adapter)
        files = {str(p.relative_to(output)): sha(p.read_bytes()) for p in sorted(adapter.rglob('*')) if p.is_file()}
        require('adapter/adapter_model.safetensors' in files and 'adapter/adapter_config.json' in files,
                'complete unmerged adapter files required')
        summary = dict(version=VERSION, arm=arm, status='complete', actual_fit=True,
            model_promotion=False, method_improvement_established=False, base_model=str(base_model), seed=seed,
            config=deepcopy(CONFIG), lora=deepcopy(LORA), edit_token_weight=1.0,
            completed_steps=int(trainer.state.global_step), completed_epochs=float(trainer.state.epoch),
            coverage=coverage, validation_examples=valid_report['examples'],
            validation=validations[0], validation_role='descriptive_only_no_checkpoint_selection',
            checkpoint_selection='fixed_final_epoch', initial_adapter=initial, final_adapter=final,
            train_preflight_sha256=sha(encoded(train_report)), validation_preflight_sha256=sha(encoded(valid_report)),
            adapter_files_sha256=files, runtime_versions=_versions(), truncation=False, exclusions=0)
        _write(output / 'training_summary.json', summary)
        journal.status('complete')
        _write(output / 'COMPLETE.json', dict(status='complete', provisional_until_normal_exit=True,
            training_summary_sha256=sha((output / 'training_summary.json').read_bytes()),
            files_sha256={str(p.relative_to(output)): sha(p.read_bytes())
                          for p in sorted(output.rglob('*')) if p.is_file()}))
        return summary
    except BaseException as error:
        _write(output / 'FAILED.json', dict(status='failed', error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        if journal is not None:
            journal.close()


def longest_paired_batch(paired):
    validate_preflight(paired)
    n = len(paired['encoded']['C'])
    require(n >= CONFIG['per_device_train_batch_size'], 'capacity probe requires full fixed microbatch')
    order = sorted(range(n), key=lambda i: (-max(len(paired['encoded'][a][i]['input_ids']) for a in ARMS), i))
    return order[:CONFIG['per_device_train_batch_size']]


def capacity_probe(paired, *, base_model, output_dir, seed=2027):
    """One longest-common-row batch per arm; backward only, no optimizer/save.

    Each arm gets a fresh seeded model. This is a capacity check, NOT fitting or
    a guarantee against later OOM, and never changes frozen batch/length limits.
    """
    report = validate_preflight(paired); indices = longest_paired_batch(paired)
    require(report['caps'] == CAPS, 'frozen capacity token caps required')
    output = _new_output(output_dir)
    try:
        import gc
        import torch
        measurements = {}; initial = None
        for arm in ARMS:
            model, tokenizer = load_fresh_model(base_model, seed)
            _matching_tokenizer(tokenizer, report)
            fingerprint = trainable_fingerprint(model)
            require(initial is None or initial == fingerprint, 'capacity probe adapter initialization differs')
            initial = fingerprint
            rows = [paired['encoded'][arm][i] for i in indices]
            batch = _TokenCollator(tokenizer.pad_token_id)(rows)
            batch = {k: v.to('cuda') for k, v in batch.items()}
            weights, labels = batch.pop('loss_weights'), batch.pop('labels')
            model.train(); model.zero_grad(set_to_none=True); torch.cuda.reset_peak_memory_stats()
            started = time.monotonic()
            with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
                result = _forward_without_output_fp32_conversion(model, batch)
                loss = _edit_weighted_causal_loss(result.logits, labels, weights)
            require(bool(torch.isfinite(loss)), 'nonfinite capacity loss')
            loss.backward(); torch.cuda.synchronize()
            measurements[arm] = dict(example_ids=[r['example_id'] for r in rows],
                tokens=[len(r['input_ids']) for r in rows], loss=float(loss.detach()),
                elapsed_seconds=time.monotonic() - started,
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved())
            require(trainable_fingerprint(model) == initial, 'capacity probe changed adapter weights')
            del loss, result, batch, weights, labels, model
            gc.collect(); torch.cuda.empty_cache()
        result = dict(version=VERSION, status='passed', mode='capacity_probe', actual_fit=False,
            optimizer_steps=0, published_adapter=False, longest_paired_indices=indices,
            initial_adapter=initial, arms=measurements, runtime_versions=_versions(),
            preflight_sha256=sha(encoded(report)), no_retry=True, adaptive_batching=False)
        _write(output / 'capacity_report.json', result)
        return result
    except BaseException as error:
        _write(output / 'FAILED.json', dict(status='failed', error_type=type(error).__name__, error=str(error)))
        raise


def _read_rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('preflight', 'train', 'capacity-probe'))
    parser.add_argument('--c', type=Path, required=True); parser.add_argument('--h', type=Path, required=True)
    parser.add_argument('--valid-c', type=Path); parser.add_argument('--valid-h', type=Path)
    parser.add_argument('--base-model', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--arm', choices=ARMS); parser.add_argument('--seed', type=int, default=2027)
    args = parser.parse_args()
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(args.base_model), use_fast=True, local_files_only=True)
    paired = paired_preflight(_read_rows(args.c), _read_rows(args.h), tokenizer)
    if args.mode == 'preflight':
        output = _new_output(args.output); _write(output / 'preflight.json', paired['report'])
        result = paired['report']
    elif args.mode == 'capacity-probe':
        result = capacity_probe(paired, base_model=args.base_model, output_dir=args.output, seed=args.seed)
    else:
        require(args.arm and args.valid_c and args.valid_h, 'arm and paired validation inputs required')
        valid = paired_preflight(_read_rows(args.valid_c), _read_rows(args.valid_h), tokenizer)
        result = train_arm(args.arm, paired, valid, base_model=args.base_model, output_dir=args.output, seed=args.seed)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
