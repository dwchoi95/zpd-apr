"""Matched preference feasibility and no-update backward probe, separate release."""
from contextlib import contextmanager
from importlib.metadata import version
import gc
import json
from pathlib import Path
import time

from scripts import run_zpd_splice_pilot as lifecycle
from scripts import run_zpd_anchor_pilot as release_check
from scripts import run_zpd_likelihood_selection as parent
from scripts import run_zpd_edit_balanced as reuse
from scripts import materialize_zpd_paired_history as material
from scripts import train_zpd_paired_history as train
from scripts import zpd_preference_objective as objective

core = parent.core
ROOT = core.PROJECT / 'outputs/zpd-preference-pilot-20261020'
UNIT_PREFIX = 'zpd-preference-pilot-20261020-v1'
VERSION = objective.VERSION
PARENT_RELEASE = 'f779e61fe46d7553975ad1f1c5963a8e8a7d9f5f9828b82eb1153d78d1e5e11d'
PARENT_SHA = 'c8c1f073c1379edb3407df3641e6d71d218c5ef97ed6472ba11ed3dec6d99f65'
PREPARED = core.PROJECT / 'outputs/zpd-paired-history-20261015/prepared-v1'
PREPARED_SHA = '827c547b54b95f9c6bf8360073f41cfafaca003353ae7579ecf9579a8b4df6f9'
REQUIRED = {'scripts/run_zpd_preference_pilot.py', 'scripts/zpd_preference_objective.py',
            'tests/test_zpd_preference_pilot.py', 'analysis_protocols/zpd-preference-pilot-20261020.md'}
BASE_SUPERVISE = lifecycle.supervise
BASE_COMMAND = lifecycle.command
BASE_VERIFY_STAGE = lifecycle.verify_stage


def predecessor():
    from scripts.watch_zpd_completion import verify_terminal
    outer = core.read_pinned(parent.FAMILY / 'VERIFIED_COMPLETE.json', PARENT_SHA)
    core.require(outer['release_sha256'] == PARENT_RELEASE, 'predecessor release differs')
    verify_terminal(parent.FAMILY, outer)
    props = core.props(parent.UNIT_PREFIX + '-coordinator.service')
    core.require(core.normal_exit(props) and props.get('ControlGroup') == '', 'predecessor not normally released')
    for phase, pin in outer['phases'].items():
        cert = core.read_pinned(parent.FAMILY / (phase + '-VERIFIED_COMPLETE.json'), pin)
        release_check.released(cert, parent.UNIT_PREFIX + '-' + phase + '.service', PARENT_RELEASE)
    core.require(not list(parent.FAMILY.rglob('*FAILED*.json')), 'parent failure marker')
    return reuse.verify_reuse()


def barrier(path, digest, revision=None):
    own = Path(__file__).resolve().parents[1]
    current = core.clean_source()
    core.require(Path.cwd().resolve() == own and path.resolve() == path and path.is_relative_to(own)
                 and (revision is None or current == revision), 'clean fixed snapshot required')
    r = core.read_pinned(path, digest)
    core.require(r['version'] == VERSION and r['family_path'] == str(ROOT)
        and r['parent_release_sha256'] == PARENT_RELEASE and r['parent_complete_sha256'] == PARENT_SHA
        and r['phases'] == list(lifecycle.PHASES) and r['phase_seconds'] == lifecycle.SECONDS
        and r['counts'] == lifecycle.COUNTS and r['caps'] == train.CAPS
        and r['method'] == objective.contract() and r['prepared_complete_sha256'] == PREPARED_SHA
        and r['materialized_complete_sha256'] == reuse.REUSE_PINS['materialize-v1/materialized/COMPLETE.json'],
        'fixed preference pilot contract differs')
    old = core.read_pinned(own / 'analysis_protocols/zpd-likelihood-selection-release-20261020.json', PARENT_RELEASE)
    core.require(REQUIRED <= set(r['source_sha256']), 'pilot sources missing')
    for name, pin in old['source_sha256'].items():
        if name not in ('scripts/watch_zpd_completion.py', 'tests/test_watch_zpd_completion.py'):
            core.require(r['source_sha256'].get(name) == pin, 'unrelated source changed: ' + name)
    for name, pin in r['source_sha256'].items():
        p = own / name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and p.resolve() == p and core.sha_file(p) == pin, 'source drift: ' + name)
    for key in ('base_model', 'adapter_C', 'adapter_H', 'model_sha256', 'development_gate'):
        core.require(r[key] == old[key], 'frozen model/gate differs: ' + key)
    for key, expected in r['training_versions'].items():
        core.require(version(key) == expected, 'pilot package drift: ' + key)
    predecessor()
    material.read_sealed(PREPARED, PREPARED_SHA)
    parent.models_pinned(r)
    return current, r


def materialize(r, output):
    original_seal = reuse.verify_reuse()
    material.read_sealed(PREPARED, PREPARED_SHA)
    target = output / 'materialized'; target.mkdir(exist_ok=False)
    tokenizer = lifecycle.paired._tokenizer(r)
    total = sum(lifecycle.COUNTS.values()); started = time.monotonic(); done = 0
    counts = {}; issues = []; ids_seen = set(); users = {}; probes = None
    for split, count in lifecycle.COUNTS.items():
        rows = lifecycle.rows(reuse.MATERIALIZED, split)
        provenance_list = train._read_rows(PREPARED / ('pairs-' + split + '.jsonl'))
        provenance = {p['example_id']: p for p in provenance_list}
        core.require(len(provenance) == len(provenance_list), 'duplicate prepared ID')
        ids = [row['example_id'] for row in rows['C']]
        core.require(len(ids) == count and len(set(ids)) == count and not ids_seen.intersection(ids)
                     and ids == [row['example_id'] for row in rows['H']], 'paired population/order differs')
        ids_seen.update(ids); users[split] = {row['user_id'] for row in rows['C']}; audit = []
        for c, h in zip(rows['C'], rows['H'], strict=True):
            p = provenance[c['example_id']]
            core.require(p['split'] == split, 'split provenance differs')
            item = objective.audit_pair(c, h, tokenizer, p); audit.append(item)
            if item['issues']: issues.append(dict(split=split, example_id=c['example_id'], issues=item['issues']))
            done += 1
            if done % 64 == 0 or done == total:
                core.status_write(output / 'STATUS.json', dict(phase='materialize', completed_examples=done,
                    total_examples=total, elapsed_seconds=time.monotonic()-started))
        core.write_new(target / (split + '-audit.json'), audit)
        counts[split] = dict(examples=count, order_sha256=train.sha(train.encoded(ids)),
            users=len(users[split]), issues=sum(bool(a['issues']) for a in audit))
        if split == 'train' and not any(a['issues'] for a in audit):
            indices = objective.longest_indices(audit)
            probes = dict(indices=indices, records={a: [rows[a][i] for i in indices] for a in train.ARMS})
        for a in train.ARMS:
            name = split + '-' + a + '.jsonl'
            core.require(core.sha_file(reuse.MATERIALIZED / name) == original_seal['files_sha256'][name], 'records drift')
    core.require(not users['train'].intersection(users['valid']), 'train/valid user overlap')
    decision = 'hold' if issues else 'ready_for_capacity'
    if decision == 'ready_for_capacity': core.write_new(target / 'probe-records.json', probes)
    report = dict(status='complete', decision=decision, counts=counts, overflow=issues,
        issues=issues, filtered_examples=0, truncation=False, actual_fit=False, codec=VERSION,
        objective=objective.contract(), native_verdicts_not_private_revalidated=True,
        prepared_complete_sha256=PREPARED_SHA, reused_complete_sha256=r['materialized_complete_sha256'])
    core.write_new(target / 'report.json', report)
    core.write_new(target / 'COMPLETE.json', dict(status='complete', files_sha256={
        p.name: core.sha_file(p) for p in sorted(target.iterdir())}))
    return report


def capacity(r, output):
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig, set_seed
    from peft import PeftModel, prepare_model_for_kbit_training
    core.require(torch.cuda.is_available() and torch.cuda.is_bf16_supported(), 'CUDA BF16 required')
    root = ROOT / 'materialize-v1/materialized'
    material.read_sealed(root, core.sha_file(root / 'COMPLETE.json'))
    report = json.loads((root / 'report.json').read_bytes())
    core.require(report['decision'] == 'ready_for_capacity' and not report['issues'], 'all-row feasibility required')
    data = json.loads((root / 'probe-records.json').read_bytes())
    tok = lifecycle.paired._tokenizer(r); measurements = []; output.mkdir(exist_ok=False)
    for arm in train.ARMS:
        set_seed(2027)
        base = AutoModelForCausalLM.from_pretrained(r['base_model'], local_files_only=True,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
                bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16),
            torch_dtype=torch.bfloat16, device_map={'': 0}, attn_implementation='sdpa')
        base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True,
                                             gradient_checkpointing_kwargs={'use_reentrant': False})
        model = PeftModel.from_pretrained(base, r['adapter_' + arm], is_trainable=True, local_files_only=True)
        model.config.use_cache = False; objective.disable_dropout(model); model.train()
        trainable = [(name, p) for name, p in model.named_parameters() if p.requires_grad]
        core.require(trainable and all('lora_' in name for name, _ in trainable), 'only LoRA can receive gradients')
        initial = train.trainable_fingerprint(model)
        for row in data['records'][arm]:
            pair = objective.encode_pair(row, tok); started = time.monotonic(); torch.cuda.reset_peak_memory_stats()
            with torch.autocast(device_type='cuda', dtype=torch.bfloat16):
                value = objective.probe_pair(model, pair)
            torch.cuda.synchronize()
            core.require(train.trainable_fingerprint(model) == initial, 'capacity probe mutated weights')
            measurements.append(dict(arm=arm, example_id=row['example_id'], **value,
                elapsed_seconds=time.monotonic()-started, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved(), initial_adapter=initial,
                full_tokens={s: pair[s]['full_tokens'] for s in pair}))
            core.write_new(output / ('measurement-' + str(len(measurements)) + '.json'), measurements[-1])
            core.status_write(output.parent / 'STATUS.json', dict(phase='capacity',
                completed_examples=23564, total_examples=23564, completed_probes=len(measurements),
                total_probes=2*len(data['indices'])))
            model.zero_grad(set_to_none=True)
        del model, base, trainable; gc.collect(); torch.cuda.empty_cache()
    result = dict(status='passed', actual_fit=False, optimizer_steps=0, published_adapter=False,
        objective=objective.contract(), longest_paired_indices=data['indices'], probes=measurements,
        validation_used_for_gradients=False, fixed_reference_only_initial_no_update=True,
        future_training_requires_immutable_reference=True, adaptive_batching=False, no_retry=True)
    core.write_new(output / 'capacity_report.json', result)
    return result


def verify_stage(phase, digest):
    result = BASE_VERIFY_STAGE(phase, digest)
    cert = json.loads((ROOT / (phase + '-VERIFIED_COMPLETE.json')).read_bytes())
    release_check.released(cert, UNIT_PREFIX + '-' + phase + '.service', digest)
    return result


def worker(phase, path, digest):
    revision, r = barrier(path, digest)
    if phase == 'capacity': verify_stage('materialize', digest)
    output = ROOT / (phase + '-v1'); core.require(not output.exists(), 'fresh worker required')
    with lifecycle.configured():
        guard = lifecycle.paired.PhaseGuard(phase); envelope = guard(force=True); output.mkdir()
        core.write_new(output / 'stage-manifest.json', dict(phase=phase, release_sha256=digest,
            revision=revision, envelope=envelope))
        try:
            if phase == 'materialize': materialize(r, output)
            else: capacity(r, output / 'probe')
            guard(force=True); barrier(path, digest, revision); core.seal_stage(output, phase, digest)
        except BaseException as exc:
            core.write_new(output / 'FAILED.json', dict(error_type=type(exc).__name__, error=str(exc))); raise


def command(phase, path, digest):
    cmd = BASE_COMMAND(phase, path, digest)
    cmd = [str(core.PROJECT / '.runtime/fse-env/bin/python') if v.endswith('/.runtime/fse-vllm/bin/python')
           else 'scripts.run_zpd_preference_pilot' if v == 'scripts.run_zpd_splice_pilot' else v for v in cmd]
    index = cmd.index(str(core.PROJECT / '.runtime/fse-env/bin/python'))
    cmd.insert(index, '--setenv=CUDA_CACHE_PATH=' + str(ROOT / 'runtime-cache' / phase / 'cuda'))
    return cmd


@contextmanager
def configured():
    overrides = dict(ROOT=ROOT, UNIT_PREFIX=UNIT_PREFIX, VERSION=VERSION, PARENT=parent.FAMILY,
        PARENT_SHA=PARENT_SHA, PARENT_RELEASE=PARENT_RELEASE, REQUIRED=REQUIRED, barrier=barrier,
        predecessor=predecessor, materialize=materialize, worker=worker, command=command, verify_stage=verify_stage)
    previous = {k: getattr(lifecycle, k) for k in overrides}
    for k, v in overrides.items(): setattr(lifecycle, k, v)
    try: yield
    finally:
        for k, v in previous.items(): setattr(lifecycle, k, v)


if __name__ == '__main__':
    with configured(): lifecycle.main()
