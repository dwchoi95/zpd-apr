"""Matched four-arm inference with two freshly trained, sealed LoRA adapters.

C uses its current-only trained adapter. H/HS/U use the same history-trained
adapter. Everything else follows the frozen full-source generation contract.
The outside driver owns dataset/source/model releases and normal-exit seals.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import time

from scripts import run_zpd_transition_generation as core

ADAPTER_ARM_MAP = {'C': 'C', 'H': 'H', 'HS': 'H', 'U': 'H'}


def adapter_roles(release):
    core.require(release['adapter_arm_map'] == ADAPTER_ARM_MAP,
                 'fixed matched adapter-to-prompt assignment required')
    paths = {arm: Path(release['adapter_' + arm]) for arm in ('C', 'H')}
    core.require(paths['C'] != paths['H'], 'separately trained adapters required')
    for arm, path in paths.items():
        core.require(path.is_absolute() and path.resolve() == path,
                     'canonical fresh adapter path required')
        for name in ('adapter_config.json', 'adapter_model.safetensors'):
            full = path / name
            core.require(str(full) in release['model_sha256']
                         and core.sha_file(full) == release['model_sha256'][str(full)],
                         'sealed fresh adapter file required: ' + arm + '/' + name)
    return paths


def generation(inputs, release, output, *, terminalize=None):
    """Drop-in core worker generation; no fallback adapter or dropped slot."""
    from importlib.metadata import version
    for package, expected in release['gpu_versions'].items():
        core.require(version(package) == expected, 'frozen GPU dependency differs: ' + package)
    for path, digest in release['model_sha256'].items():
        core.require(core.sha_file(Path(path)) == digest, 'frozen model/tokenizer differs: ' + path)
    paths = adapter_roles(release)
    rendered, token_report = core.render_inputs(inputs, release['base_model'])
    core.write_new(output / 'tokenization.json', token_report)
    core.require(core.sha(core.encoded(token_report)) == release['tokenization_sha256'],
                 'tokenization changed since frozen full-source preflight')
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest
    model = LLM(model=release['base_model'], tokenizer=release['base_model'], quantization='bitsandbytes',
        load_format='bitsandbytes', dtype='bfloat16', max_model_len=8192, gpu_memory_utilization=.85,
        seed=2027, enable_lora=True, max_lora_rank=64, max_loras=2, max_num_seqs=8)
    adapters = {a: LoRARequest('paired-history-' + a, i, str(paths[a]))
                for a, i in (('C', 1), ('H', 2))}
    core.write_new(output / 'adapter-assignment.json', dict(arm_map=ADAPTER_ARM_MAP,
        paths={a: str(p) for a, p in paths.items()},
        model_sha256={a: release['model_sha256'][str(p / 'adapter_model.safetensors')]
                      for a, p in paths.items()},
        same_history_adapter_for_H_HS_U=True, full_factorial=False))
    attempts = inputs['attempts']; completed = []; started = time.monotonic()
    (output / 'attempts').mkdir()
    for offset in range(0, len(attempts), 8):
        batch = attempts[offset:offset + 8]; pending = []; sampling = []; terminal_rows = []
        for row in batch:
            core.require(row['arm'] in ADAPTER_ARM_MAP, 'unknown inference arm')
            prompt = rendered[row['prompt_id']]
            if not prompt['fits']:
                entry = dict(index=row['draw_index'], seed=row['seed'], status='resource_failure', source=None,
                             error='untruncated prompt plus fixed output exceeds context')
                terminal_rows.append(dict(**row, attempt=entry, raw_text=None, finish_reason='prompt_overflow'))
            else:
                pending.append(row)
                sampling.append(SamplingParams(n=1, temperature=.8, top_p=.95, seed=row['seed'], max_tokens=4096))
        if pending:
            requests = [adapters[ADAPTER_ARM_MAP[row['arm']]] for row in pending]
            results = model.generate([rendered[row['prompt_id']]['text'] for row in pending], sampling,
                                     lora_request=requests, use_tqdm=False)
            core.require(len(results) == len(pending), 'generation response count differs')
            for row, result in zip(pending, results, strict=True):
                core.require(len(result.outputs) == 1, 'one output per attempt required')
                item = result.outputs[0]
                terminal_rows.append(dict(**row,
                    attempt=(core.terminal(row['draw_index'], row['seed'], item.text, item.finish_reason)
                             if terminalize is None else terminalize(row, item.text, item.finish_reason)),
                    raw_text=item.text, finish_reason=item.finish_reason))
        for row in terminal_rows:
            prompt = rendered[row['prompt_id']]; role = ADAPTER_ARM_MAP[row['arm']]
            row.update(prompt_tokens=prompt['tokens'], rendered_prompt_sha256=prompt['rendered_sha256'],
                       adapter_role=role, adapter_model_sha256=release['model_sha256'][
                           str(paths[role] / 'adapter_model.safetensors')])
            core.write_new(output / 'attempts' / (row['attempt_id'] + '.json'), row)
            completed.append(row)
        counts = Counter(r['example_id'] for r in completed)
        core.status_write(output / 'STATUS.json', dict(phase='generation',
            completed_examples=sum(v == 8 for v in counts.values()), total_examples=320,
            completed_attempts=len(completed), total_attempts=2560,
            attempt_statuses=dict(Counter(r['attempt']['status'] for r in completed)),
            elapsed_seconds=time.monotonic() - started))
        core.envelope('generation')
    core.require(len(completed) == 2560 and len({r['attempt_id'] for r in completed}) == 2560,
                 'all unique terminal attempts required')
    core.write_new(output / 'attempts.json', completed)
    for path, digest in release['model_sha256'].items():
        core.require(core.sha_file(Path(path)) == digest, 'model changed during generation')


if __name__ == '__main__':
    raise SystemExit('Use the separately sealed paired-history coordinator.')
