"""Fresh matched C/H training and unchanged prospective inference/evaluation.

Eight exclusive isolated stages, without retries or implicit continuation. Inner
seals are provisional: normal child exit and verified empty/removed cgroups are
required before every successor. The exposed development cohort is exploratory;
this experiment cannot promote a model or establish educational benefit.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from scripts import run_zpd_transition_generation as core
from scripts.recover_zpd_transition_evaluation import terminal_group

PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = PROJECT / 'outputs/zpd-paired-history-run-20261015'
PREPARED = PROJECT / 'outputs/zpd-paired-history-20261015/prepared-v1'
PREPARED_SHA = '827c547b54b95f9c6bf8360073f41cfafaca003353ae7579ecf9579a8b4df6f9'
INPUTS = PROJECT / 'outputs/zpd-full-source-inputs-20261014-v1/inputs.json'
UNIT_PREFIX = 'zpd-paired-history-20261015-v1'
VERSION = 'paired_history_release_v1'
PHASES = ('cache', 'materialize', 'capacity', 'train-C', 'train-H', 'generation', 'public', 'private')
INFERENCE = PHASES[-3:]
PHASE_SECONDS = dict(zip(PHASES, (43200, 7200, 3600, 86400, 86400, 21600, 21600, 21600), strict=True))
ADAPTER_ARM_MAP = dict(C='C', H='H', HS='H', U='H')
REQUIRED_SOURCE_PINS = frozenset((
    'scripts/run_zpd_paired_history.py', 'scripts/cache_zpd_paired_history.py',
    'scripts/materialize_zpd_paired_history.py', 'scripts/train_zpd_paired_history.py',
    'scripts/generate_zpd_paired_history.py', 'scripts/run_zpd_transition_generation.py',
    'scripts/recover_zpd_transition_evaluation.py', 'scripts/zpd_transition_private.py',
    'scripts/zpd_public_candidate_selection.py', 'scripts/zpd_repair_evaluate.py',
    'scripts/probe_zpd_statement_sample_resources.py', 'src/repair/pilot_contracts.py',
    'src/repair/train.py', 'src/repair/prompts.py', 'scripts/prepare_zpd_full_source.py',
    'scripts/zpd_public_transition_prompt.py', 'scripts/prepare_zpd_paired_history.py',
    'src/runner/python_runner.py', 'src/runner/models.py', 'src/runner/compare.py',
))
GPU_PACKAGES = frozenset(('torch', 'transformers', 'bitsandbytes', 'vllm'))
TRAINING_PACKAGES = frozenset(('torch', 'transformers', 'peft', 'accelerate', 'bitsandbytes'))


def unit(phase):
    core.require(phase in PHASES, 'fixed paired-history phase required')
    return UNIT_PREFIX + '-' + phase + '.service'


def limits(phase):
    core.require(phase in PHASES, 'fixed paired-history phase required')
    if phase in ('capacity', 'train-C', 'train-H', 'generation'):
        return 64 * 2**30, 1024, 'infinity'
    size = 16 if phase == 'materialize' else 32
    return size * 2**30, 128, str(size * 2**30)


def envelope(phase):
    memory, tasks, address = limits(phase)
    values = core.props(unit(phase))
    expected = dict(Id=unit(phase), LoadState='loaded', ActiveState='active', SubState='running',
        MainPID=str(os.getpid()), MemoryMax=str(memory), TasksMax=str(tasks), LimitAS=address,
        KillMode='control-group', KillSignal='9', SendSIGKILL='yes', Restart='no', OOMPolicy='stop',
        Type='exec', Delegate='no', RemainAfterExit='yes', MemoryAccounting='yes', TasksAccounting='yes')
    core.require(all(values.get(k) == v for k, v in expected.items()), 'effective phase envelope differs')
    from scripts.zpd_statement_sample_host import _seconds
    core.require(_seconds(values['RuntimeMaxUSec']) == PHASE_SECONDS[phase], 'phase deadline differs')
    groups = [s.split(':', 2)[2] for s in Path('/proc/self/cgroup').read_text().splitlines() if s.startswith('0::')]
    core.require(len(groups) == 1 and groups[0] == values['ControlGroup']
        and groups[0].startswith(f'/user.slice/user-{os.getuid()}.slice/')
        and groups[0].endswith('/' + unit(phase)), 'dedicated phase cgroup required')
    root = Path('/sys/fs/cgroup') / groups[0].lstrip('/')
    core.require((root / 'memory.max').read_text().strip() == str(memory)
        and (root / 'pids.max').read_text().strip() == str(tasks), 'effective cgroup limits differ')
    events = {name: dict((k, int(v)) for k, v in (line.split() for line in (root / name).read_text().splitlines()))
              for name in ('memory.events', 'pids.events')}
    core.require(all(v == 0 for values in events.values() for k, v in values.items() if k != 'low'),
                 'aggregate resource event invalidates phase')
    return dict(cgroup=groups[0], properties=expected, events=events)


class PhaseGuard:
    """Cheap per-case clock check; serialize/throttle OS checks to five seconds."""
    def __init__(self, phase):
        self.phase, self.deadline = phase, time.monotonic() + PHASE_SECONDS[phase]
        self.last_checked = float('-inf')
        self.lock = threading.Lock()

    def __call__(self, *, force=False):
        core.require(time.monotonic() < self.deadline, 'phase monotonic deadline exceeded')
        with self.lock:
            now = time.monotonic()
            if force or now - self.last_checked >= 5:
                result = envelope(self.phase)
                self.last_checked = time.monotonic()
            else:
                result = None
        core.require(time.monotonic() < self.deadline, 'phase monotonic deadline exceeded')
        return result


def read_sealed(root, pin):
    root = Path(root).absolute()
    core.require(root.resolve() == root, 'canonical artifact directory required')
    seal = core.read_pinned(root / 'COMPLETE.json', pin)
    core.require(seal['status'] == 'complete', 'complete artifact required')
    files = seal['files_sha256']
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
    core.require(actual == set(files) | {'COMPLETE.json'}, 'sealed artifact inventory differs')
    core.require(not any('FAILED' in n or 'INCOMPLETE' in n or n.endswith('.partial') for n in actual),
                 'failed or incomplete artifact')
    for name, digest in files.items():
        path = root / name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts
                     and path.resolve() == path and core.sha_file(path) == digest, 'sealed artifact drift: ' + name)
    return seal


def verify_base_model(release):
    """Pin all local model metadata/tokenizers/shards, not only selected weights.

    Hugging Face snapshot entries normally symlink to blobs. Their lexical
    snapshot paths are fixed and their target bytes are hashed, not rejected.
    """
    base = Path(release['base_model'])
    pins = release['model_sha256']
    core.require(base.is_absolute() and base.is_dir() and type(pins) is dict and bool(pins),
                 'local pinned base model required')
    inventory = {str(p) for p in base.rglob('*') if p.is_file()}
    core.require(set(pins) == inventory, 'exact base model/tokenizer file inventory required; no old adapter files')
    required = {'config.json', 'tokenizer_config.json', 'tokenizer.json', 'model.safetensors.index.json'}
    core.require({str(base / n) for n in required} <= inventory, 'base tokenizer/config/shard index required')
    for name, pin in pins.items():
        core.require(Path(name).is_relative_to(base) and '..' not in Path(name).parts
                     and core.sha_file(Path(name)) == pin, 'base model/tokenizer drift: ' + name)
    index = json.loads((base / 'model.safetensors.index.json').read_bytes())
    shards = set(index['weight_map'].values())
    core.require(bool(shards) and all(type(n) is str and Path(n).name == n
        and n.endswith('.safetensors') and str(base / n) in inventory for n in shards),
        'every indexed model shard must be pinned')


def load_release(path, digest):
    release = core.read_pinned(path, digest)
    core.require(release['version'] == VERSION and release['family_path'] == str(FAMILY)
        and release['phases'] == list(PHASES) and release['phase_seconds'] == PHASE_SECONDS,
        'fixed paired-history namespace/phases required')
    core.require(release['prepared_path'] == str(PREPARED)
        and release['prepared_complete_sha256'] == PREPARED_SHA
        and release['inputs_path'] == str(INPUTS), 'fixed prepared/evaluation inputs required')
    core.require(release['arms'] == list(core.ARMS) and release['recipients'] == 320
        and release['attempts'] == 2560 and release['seed'] == 2027
        and release['no_retry'] is True and release['retries'] == 0
        and release['no_truncation'] is True and release['fitting'] is True
        and release['model_promotion'] is False and release['confirmatory'] is False,
        'fixed matched-training exploratory scope required')
    core.require(REQUIRED_SOURCE_PINS <= set(release['source_sha256']), 'missing required source pins')
    for name, pin in release['source_sha256'].items():
        source = Path(name)
        core.require(not source.is_absolute() and '..' not in source.parts
            and source.resolve().is_relative_to(Path.cwd().resolve())
            and source.absolute() == source.resolve() and core.sha_file(source) == pin, 'source drift: ' + name)
    core.require(type(release['gpu_versions']) is dict and GPU_PACKAGES <= set(release['gpu_versions'])
        and type(release['training_versions']) is dict and TRAINING_PACKAGES <= set(release['training_versions'])
        and all(type(v) is str and bool(v) for v in [*release['gpu_versions'].values(), *release['training_versions'].values()]),
        'explicit complete GPU/training runtime pin maps required')
    verify_base_model(release)
    core.require(core.sha_file(Path(release['scorer_path'])) == release['scorer_sha256'], 'frozen scorer drift')
    read_sealed(PREPARED, release['prepared_complete_sha256'])
    inputs_seal = read_sealed(INPUTS.parent, release['inputs_complete_sha256'])
    core.require(inputs_seal['files_sha256']['inputs.json'] == release['inputs_sha256'], 'evaluation input pin differs')
    core.inputs_for(release)
    # Check presence/types without accessing private assessment bodies here.
    core.require(type(release['testcase_sha256']) is dict and bool(release['testcase_sha256'])
        and all(type(release[k]) is str and len(release[k]) == 64
                for k in ('tokenization_sha256', 'cache_runtime_sha256')), 'frozen inference/runtime pins required')
    return release


def source_barrier(release_path, release_sha, revision=None):
    current = core.clean_source()
    root = Path.cwd().resolve()
    core.require(root == Path(__file__).resolve().parents[1] == Path(core.__file__).resolve().parents[1],
                 'driver and algorithms must share clean snapshot')
    path = Path(release_path).absolute()
    core.require(path.resolve() == path and path.is_relative_to(root), 'parent release must belong to snapshot')
    core.require(revision is None or current == revision, 'snapshot revision changed')
    return current, load_release(path, release_sha)


@contextmanager
def configured_core():
    from scripts.generate_zpd_paired_history import generation
    original = core.FAMILY, core.unit, core.generation
    core.FAMILY, core.unit, core.generation = FAMILY, unit, generation
    try:
        yield core
    finally:
        core.FAMILY, core.unit, core.generation = original


def _inference_pin(parent_sha):
    marker = json.loads((FAMILY / 'INFERENCE_RELEASE_COMPLETE.json').read_bytes())
    core.require(marker['status'] == 'complete' and marker['parent_release_sha256'] == parent_sha,
                 'dynamic inference release parent differs')
    path = FAMILY / 'inference-release.json'
    core.require(core.sha_file(path) == marker['inference_release_sha256'], 'dynamic inference release drift')
    return path, marker['inference_release_sha256']


def verified_dependency(phase, parent_sha):
    actual_sha = _inference_pin(parent_sha)[1] if phase in INFERENCE else parent_sha
    marker = json.loads((FAMILY / (phase + '-VERIFIED_COMPLETE.json')).read_bytes())
    core.require(marker['parent_release_sha256'] == parent_sha and marker['cleanup_verified'] is True
        and marker['status'] == 'complete' and marker['release_sha256'] == actual_sha
        and core.normal_exit(marker['exit'])
        and marker['complete_sha256'] == core.sha_file(FAMILY / (phase + '-v1/STAGE_COMPLETE.json')),
        'normal-exit dependency certificate differs')
    seal = core.verify_stage(FAMILY / (phase + '-v1'), phase, actual_sha)
    core.require(not any('FAILED' in n or 'INCOMPLETE' in n or n.endswith('.partial')
                         for n in seal['files_sha256']), 'failed/incomplete dependency')
    return seal


def verify_training_pair(parent_sha):
    from scripts import train_zpd_paired_history as training
    summaries = {}
    for arm in ('C', 'H'):
        phase = 'train-' + arm
        verified_dependency(phase, parent_sha)
        root = FAMILY / (phase + '-v1/training')
        seal = read_sealed(root, core.sha_file(root / 'COMPLETE.json'))
        row = core.read_pinned(root / 'training_summary.json', seal['training_summary_sha256'])
        core.require(row['arm'] == arm and row['status'] == 'complete' and row['actual_fit'] is True
            and row['seed'] == 2027 and row['config'] == training.CONFIG and row['lora'] == training.LORA
            and row['completed_epochs'] == 1.0 and row['truncation'] is False and row['exclusions'] == 0
            and row['checkpoint_selection'] == 'fixed_final_epoch'
            and row['validation_role'] == 'descriptive_only_no_checkpoint_selection'
            and row['model_promotion'] is False, 'fixed one-epoch training summary differs')
        coverage = row['coverage']
        core.require(coverage['consumed_order_sha256'] == coverage['planned_order_sha256']
            and coverage['completed_examples'] == coverage['unique_completed_examples'] == coverage['total_examples'],
            'incomplete or reordered training coverage')
        summaries[arm] = row
    c, h = summaries['C'], summaries['H']
    for field in ('initial_adapter', 'base_model', 'config', 'lora', 'seed', 'completed_steps',
                  'train_preflight_sha256', 'validation_preflight_sha256', 'validation_examples', 'runtime_versions'):
        core.require(c[field] == h[field], 'unmatched C/H training field: ' + field)
    core.require(c['coverage']['planned_order_sha256'] == h['coverage']['planned_order_sha256'],
                 'C/H traversal order differs')
    verified_dependency('capacity', parent_sha)
    capacity = json.loads((FAMILY / 'capacity-v1/probe/capacity_report.json').read_bytes())
    core.require(capacity['status'] == 'passed' and capacity['actual_fit'] is False
        and capacity['optimizer_steps'] == 0 and capacity['published_adapter'] is False
        and capacity['initial_adapter'] == c['initial_adapter'], 'capacity/fresh initializer mismatch')
    return summaries


def inference_release(release_path, parent_sha, revision, *, create=False):
    _, parent = source_barrier(release_path, parent_sha, revision)
    summaries = verify_training_pair(parent_sha)
    result = deepcopy(parent)
    result.update(version='transition_generation_release_v1', fitting=False, phase_seconds=21600,
        parent_release_path=str(Path(release_path).absolute()), parent_release_sha256=parent_sha,
        parent_revision=revision, adapter_arm_map=ADAPTER_ARM_MAP,
        training_certificates_sha256={a: core.sha_file(FAMILY / ('train-' + a + '-VERIFIED_COMPLETE.json'))
                                     for a in ('C', 'H')},
        initial_trainable_sha256=summaries['C']['initial_adapter']['sha256'],
        matched_training_order_sha256=summaries['C']['coverage']['planned_order_sha256'])
    for arm, summary in summaries.items():
        root = FAMILY / ('train-' + arm + '-v1/training')
        result['adapter_' + arm] = str(root / 'adapter')
        files = summary['adapter_files_sha256']
        core.require({'adapter/adapter_model.safetensors', 'adapter/adapter_config.json'} <= set(files),
                     'complete fresh adapter required')
        for name, pin in files.items():
            core.require(Path(name).parts[0] == 'adapter' and '..' not in Path(name).parts
                         and not Path(name).is_absolute() and core.sha_file(root / name) == pin,
                         'fresh adapter file differs')
            result['model_sha256'][str(root / name)] = pin
    path = FAMILY / 'inference-release.json'
    if create:
        core.write_new(path, result)
        core.write_new(FAMILY / 'INFERENCE_RELEASE_COMPLETE.json', dict(status='complete',
            parent_release_sha256=parent_sha, inference_release_sha256=core.sha_file(path),
            training_certificates_sha256=result['training_certificates_sha256']))
    selected, digest = _inference_pin(parent_sha)
    core.require(core.read_pinned(selected, digest) == result, 'dynamic inference release binding differs')
    return selected, digest


def _tokenizer(release):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(release['base_model'], use_fast=True, local_files_only=True)


def _paired(release, split):
    from scripts.train_zpd_paired_history import paired_preflight
    root = FAMILY / 'materialize-v1/materialized'
    rows = {a: [json.loads(line) for line in (root / (split + '-' + a + '.jsonl')).read_bytes().splitlines()]
            for a in ('C', 'H')}
    paired = paired_preflight(rows['C'], rows['H'], _tokenizer(release))
    stored = json.loads((root / (split + '-token-preflight.json')).read_bytes())
    core.require(paired['report'] == stored, 'recomputed paired token preflight differs')
    return paired


def _runtime_check(release):
    from scripts.probe_zpd_statement_sample_resources import runtime_identity
    runtime = runtime_identity()
    core.require(core.sha(core.encoded(runtime)) == release['cache_runtime_sha256'], 'cache runtime identity drift')
    return runtime


def run_early_phase(phase, release, output, guard, parent_sha):
    if phase == 'cache':
        from scripts.cache_zpd_paired_history import execute_cache
        runtime = _runtime_check(release)
        core.write_new(output / 'runtime.json', runtime)
        tasks = json.loads((PREPARED / 'tasks.json').read_bytes())
        execute_cache(tasks, output / 'cache', guard=guard, runtime_sha256=release['cache_runtime_sha256'])
        _runtime_check(release)
    elif phase == 'materialize':
        from scripts.materialize_zpd_paired_history import materialize
        cached = FAMILY / 'cache-v1/cache'
        materialize(PREPARED, release['prepared_complete_sha256'], cached,
                    core.sha_file(cached / 'COMPLETE.json'), _tokenizer(release), output / 'materialized')
    else:
        from scripts import train_zpd_paired_history as training
        paired = _paired(release, 'train')
        if phase == 'capacity':
            report = training.capacity_probe(paired, base_model=release['base_model'], output_dir=output / 'probe', seed=2027)
            core.require(report['status'] == 'passed' and report['actual_fit'] is False
                and report['optimizer_steps'] == 0 and report['published_adapter'] is False, 'capacity probe failed')
        else:
            training.train_arm(phase[-1], paired, _paired(release, 'valid'),
                               base_model=release['base_model'], output_dir=output / 'training', seed=2027)


def validate_phase_result(phase, release, output):
    """An outer seal cannot stand in for the primitive's required terminal data."""
    if phase in INFERENCE:
        return
    if phase == 'capacity':
        row = json.loads((output / 'probe/capacity_report.json').read_bytes())
        core.require(row['status'] == 'passed' and row['actual_fit'] is False
            and row['optimizer_steps'] == 0 and row['published_adapter'] is False, 'capacity result differs')
        return
    inner_name = 'cache' if phase == 'cache' else 'materialized' if phase == 'materialize' else 'training'
    root = output / inner_name
    seal = read_sealed(root, core.sha_file(root / 'COMPLETE.json'))
    if phase == 'cache':
        core.require(seal['runtime_sha256'] == release['cache_runtime_sha256']
            and seal['host_cleanup_verification_required'] is True
            and seal['counts']['completed_source_blocks'] == seal['counts']['planned_source_blocks']
            and seal['counts']['completed_case_attempts'] == seal['counts']['planned_case_attempts'],
            'cache terminal coverage/runtime differs')
    elif phase == 'materialize':
        core.require(seal['prepared_complete_sha256'] == release['prepared_complete_sha256']
            and seal['cache_complete_sha256'] == core.sha_file(FAMILY / 'cache-v1/cache/COMPLETE.json')
            and seal['history_truncated'] is False and seal['dev_evaluation_recipients_filtered'] is False,
            'materialized input binding differs')
    else:
        row = core.read_pinned(root / 'training_summary.json', seal['training_summary_sha256'])
        core.require(seal['provisional_until_normal_exit'] is True and row['status'] == 'complete'
            and row['arm'] == phase[-1] and row['actual_fit'] is True and row['completed_epochs'] == 1.0,
            'training terminal result differs')


def worker(phase, release_path, release_sha):
    core.require(phase in PHASES, 'fixed worker phase required')
    revision, release = source_barrier(release_path, release_sha)
    for prior in PHASES[:PHASES.index(phase)]:
        verified_dependency(prior, release_sha)
    output = FAMILY / (phase + '-v1')
    core.require(not output.exists(), 'no duplicate, overwrite, resume or retry')
    if phase in INFERENCE:
        actual_path, actual_sha = inference_release(release_path, release_sha, revision)
        try:
            with configured_core():
                core.worker(phase, actual_path, actual_sha)
            source_barrier(release_path, release_sha, revision)
            inference_release(release_path, release_sha, revision)
        except BaseException as error:
            if output.exists() and not (output / 'FAILED.json').exists():
                core.write_new(output / 'FAILED.json', dict(error_type=type(error).__name__, error=str(error), valid=False))
            raise
        return
    guard = PhaseGuard(phase)
    state = guard(force=True)
    output.mkdir(parents=True, exist_ok=False)
    core.write_new(output / 'stage-manifest.json', dict(phase=phase, release_sha256=release_sha,
        revision=revision, envelope=state, started=time.time(), python=sys.version))
    try:
        if phase != 'cache':
            for package, expected in release['training_versions'].items():
                core.require(version(package) == expected, 'training runtime differs: ' + package)
        run_early_phase(phase, release, output, guard, release_sha)
        guard(force=True)
        source_barrier(release_path, release_sha, revision)
        for prior in PHASES[:PHASES.index(phase)]:
            verified_dependency(prior, release_sha)
        if phase != 'cache':
            for package, expected in release['training_versions'].items():
                core.require(version(package) == expected, 'training runtime changed: ' + package)
        validate_phase_result(phase, release, output)
        guard(force=True)
        core.seal_stage(output, phase, release_sha)
    except BaseException as error:
        core.write_new(output / 'FAILED.json', dict(error_type=type(error).__name__, error=str(error), valid=False))
        raise


def command(phase, release_path, release_sha, snapshot=None):
    snapshot = Path.cwd().resolve() if snapshot is None else Path(snapshot)
    memory, tasks, address = limits(phase)
    properties = dict(MemoryMax=str(memory), TasksMax=str(tasks), LimitAS=address,
        RuntimeMaxSec=str(PHASE_SECONDS[phase]), KillMode='control-group', KillSignal='SIGKILL', SendSIGKILL='yes',
        Restart='no', OOMPolicy='stop', Delegate='no', RemainAfterExit='yes', MemoryAccounting='yes',
        TasksAccounting='yes', WorkingDirectory=str(snapshot),
        StandardOutput='append:' + str(FAMILY / (phase + '.log')),
        StandardError='append:' + str(FAMILY / (phase + '.log')))
    cmd = ['/usr/bin/systemd-run', '--user', '--unit=' + unit(phase), '--service-type=exec']
    cmd += ['--property=' + k + '=' + v for k, v in properties.items()]
    local = FAMILY / 'runtime-cache' / phase
    environment = dict(PYTHONDONTWRITEBYTECODE='1', TOKENIZERS_PARALLELISM='false', OMP_NUM_THREADS='1',
        OPENBLAS_NUM_THREADS='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        HF_HOME=str(local / 'huggingface'), TORCH_HOME=str(local / 'torch'), XDG_CACHE_HOME=str(local),
        TRITON_CACHE_DIR=str(local / 'triton'), TMPDIR=str(FAMILY / 'tmp' / phase))
    cmd += ['--setenv=' + k + '=' + v for k, v in environment.items()]
    gpu_env = phase in ('materialize', 'capacity', 'train-C', 'train-H', 'generation')
    python = PROJECT / ('.runtime/fse-vllm/bin/python' if gpu_env else '.runtime/fse-env/bin/python')
    return cmd + [str(python), '-m', 'scripts.run_zpd_paired_history', 'worker', '--phase', phase,
                  '--release', str(release_path), '--release-sha', release_sha]


def certify(phase, release_path, release_sha, revision, values=None):
    _, release = source_barrier(release_path, release_sha, revision)
    actual_sha = inference_release(release_path, release_sha, revision)[1] if phase in INFERENCE else release_sha
    values = core.props(unit(phase)) if values is None else values
    core.require(core.normal_exit(values), 'phase did not exit normally: ' + phase)
    output = FAMILY / (phase + '-v1')
    seal = core.verify_stage(output, phase, actual_sha)
    core.require(not any('FAILED' in n or 'INCOMPLETE' in n or n.endswith('.partial')
                         for n in seal['files_sha256']), 'failed/incomplete stage cannot be certified')
    validate_phase_result(phase, release, output)
    manifest = json.loads((output / 'stage-manifest.json').read_bytes())
    core.require(manifest['revision'] == revision and manifest['release_sha256'] == actual_sha
                 and manifest['phase'] == phase, 'worker source/release binding differs')
    cleanup = terminal_group(values, manifest['envelope']['cgroup'], unit(phase))
    certificate = dict(status='complete', phase=phase, release_sha256=actual_sha,
        parent_release_sha256=release_sha, revision=revision,
        complete_sha256=core.sha_file(output / 'STAGE_COMPLETE.json'),
        exit={k: values[k] for k in ('Result', 'ExecMainCode', 'ExecMainStatus', 'MainPID', 'SubState')},
        systemd_properties=values, **cleanup)
    core.write_new(FAMILY / (phase + '-VERIFIED_COMPLETE.json'), certificate)
    subprocess.run(['/usr/bin/systemctl', '--user', 'stop', unit(phase)], check=True, timeout=30)
    return certificate


def summarize_private(report, release_sha, report_sha, population):
    core.require(report['methods'] == [*core.ARMS, 'noop'] and report['full']['examples'] == 320
        and report['execution_complete'] is True and report['historical_gates_evaluated'] is False
        and report['historical_gate_status'] == 'not_applicable_to_new_generation_arms'
        and report['confirmatory'] is False and report['model_promotion'] is False
        and report['educational_benefit_established'] is False, 'unchanged private claim boundary required')
    return dict(version='paired_history_exploratory_report_v1', intervention_kind='fresh_matched_C_H_training',
        release_sha256=release_sha, private_report_sha256=report_sha, examples=320,
        methods=list(report['methods']), adapter_arm_map=ADAPTER_ARM_MAP,
        counts={a: deepcopy(report['full']['results'][a]['counts']) for a in report['methods']},
        training_population=deepcopy(population), full=deepcopy(report['full']), folds=deepcopy(report['folds']),
        paired_H=deepcopy(report['paired_H']), current_status_subgroups=deepcopy(report['current_status_subgroups']),
        development_gate=deepcopy(report['development_gate']), historical_gate_status=report['historical_gate_status'],
        historical_gates_evaluated=False, historical_gates_passed=False, confirmatory=False,
        model_promotion=False, educational_benefit_established=False, execution_complete=True,
        unknown_bounds_are_confidence_intervals=False,
        limitations=['Fresh matched C/H one-epoch adapters; exposed adaptive development cohort.',
            'Shared whole-trajectory training context eligibility; no evaluation recipient exclusion.',
            'Generation selector, selected-only private evaluation and descriptive gate remain unchanged.',
            'No automatic promotion, historical gate pass, or educational-benefit claim.'])


def finalize(release_path, release_sha, revision):
    source_barrier(release_path, release_sha, revision)
    for phase in PHASES:
        verified_dependency(phase, release_sha)
    inference_release(release_path, release_sha, revision)
    private = FAMILY / 'private-v1/evaluation'
    complete = json.loads((private / 'COMPLETE.json').read_bytes())
    core.require(complete['status'] == 'complete' and complete['provisional_until_normal_unit_exit'] is True,
                 'complete selected-only private result required')
    report_sha = complete['files_sha256']['report.json']
    report = core.read_pinned(private / 'report.json', report_sha)
    population = json.loads((FAMILY / 'materialize-v1/materialized/report.json').read_bytes())['counts']
    summary = summarize_private(report, release_sha, report_sha, population)
    core.write_new(FAMILY / 'REPORT.json', summary)
    core.status_write(FAMILY / 'STATUS.json', dict(phase='complete', completed_phases=list(PHASES), checked=time.time()))
    source_barrier(release_path, release_sha, revision)
    core.write_new(FAMILY / 'VERIFIED_COMPLETE.json', dict(status='complete', release_sha256=release_sha,
        revision=revision, phases={p: core.sha_file(FAMILY / (p + '-VERIFIED_COMPLETE.json')) for p in PHASES},
        files_sha256={'REPORT.json': core.sha_file(FAMILY / 'REPORT.json')},
        inference_release_sha256=_inference_pin(release_sha)[1],
        development_decision=report['development_gate']['decision'], model_promotion=False,
        historical_gates_passed=False, confirmatory=False))
    return summary


def supervise(release_path, release_sha):
    release_path = Path(release_path).absolute()
    revision, _ = source_barrier(release_path, release_sha)
    core.require(not FAMILY.exists(), 'run family already exists; no retries or duplicate coordinator')
    for phase in PHASES:
        core.require(core.props(unit(phase)).get('LoadState') == 'not-found', 'phase unit already exists')
    FAMILY.mkdir(parents=True, exist_ok=False)
    core.write_new(FAMILY / 'COORDINATOR.json', dict(release_sha256=release_sha, revision=revision,
        phases=list(PHASES), phase_seconds=PHASE_SECONDS, started=time.time(), retries=0))
    completed, launched = [], []
    try:
        for phase in PHASES:
            source_barrier(release_path, release_sha, revision)
            core.require(not (FAMILY / (phase + '-v1')).exists()
                and core.props(unit(phase)).get('LoadState') == 'not-found', 'duplicate next phase')
            for prior in completed:
                verified_dependency(prior, release_sha)
            if phase == 'generation':
                inference_release(release_path, release_sha, revision, create=True)
            (FAMILY / 'tmp' / phase).mkdir(parents=True, exist_ok=False)
            (FAMILY / 'runtime-cache' / phase).mkdir(parents=True, exist_ok=False)
            launched.append(phase)  # A timed-out launch may already have created this unit.
            subprocess.run(command(phase, release_path, release_sha), check=True, timeout=30)
            deadline = time.monotonic() + PHASE_SECONDS[phase] + 300
            while True:
                values = core.props(unit(phase))
                core.status_write(FAMILY / 'STATUS.json', dict(phase=phase, completed_phases=list(completed),
                    checked=time.time(), unit={k: values.get(k) for k in ('Id', 'ActiveState', 'SubState', 'MainPID', 'Result')}))
                if values.get('SubState') == 'exited' or values.get('ActiveState') in ('failed', 'inactive'):
                    certify(phase, release_path, release_sha, revision, values)
                    completed.append(phase)
                    break
                core.require(time.monotonic() < deadline, 'phase monitor deadline exceeded')
                time.sleep(20)
        return finalize(release_path, release_sha, revision)
    except BaseException as error:
        cleanup = {}
        for phase in launched:
            if phase not in completed:
                try:
                    subprocess.run(['/usr/bin/systemctl', '--user', 'stop', unit(phase)], check=True, timeout=30)
                    cleanup[phase] = 'stop_completed'
                except BaseException as stop_error:
                    cleanup[phase] = type(stop_error).__name__ + ': ' + str(stop_error)
        marker = FAMILY / 'VERIFIED_COMPLETE.json'
        if marker.exists():
            marker.rename(FAMILY / 'REJECTED_VERIFIED_COMPLETE.json')
        core.write_new(FAMILY / 'COORDINATOR_FAILED.json', dict(error_type=type(error).__name__, error=str(error),
            completed_phases=completed, launched_phases=launched, exact_unit_cleanup=cleanup, retries=0))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=('worker', 'supervise'))
    parser.add_argument('--phase', choices=PHASES)
    parser.add_argument('--release', type=Path, required=True)
    parser.add_argument('--release-sha', required=True)
    args = parser.parse_args()
    if args.command == 'worker':
        worker(args.phase, args.release, args.release_sha)
    else:
        supervise(args.release, args.release_sha)


if __name__ == '__main__':
    main()
