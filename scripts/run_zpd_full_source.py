"""Isolated full-source representation package using unchanged transition algorithms.

Only the imported driver's FAMILY and unit naming are temporarily rebound.
Generation, public selection, selected-only private replay, and their gates are
the existing implementations. No retry, fitting, exclusion, or promotion exists.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import time

from scripts import run_zpd_transition_generation as core
from scripts.recover_zpd_transition_evaluation import terminal_group
from scripts.prepare_zpd_full_source import validate_representation

PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = PROJECT / 'outputs/zpd-full-source-20261014'
INPUTS = PROJECT / 'outputs/zpd-full-source-inputs-20261014-v1/inputs.json'
BASELINE_INPUTS = PROJECT / 'outputs/zpd-current-last-inputs-20261013-v1/inputs.json'
BASELINE_INPUTS_SHA = 'b49107c71a4df2a7318c9b93f7b42d29a03f502a0e81ce27735310efe7b2515f'
VARIANT = 'full_source_messages_v1'
UNIT_PREFIX = 'zpd-full-source-20261014-v1'
PHASES = ('generation', 'public', 'private')
SECONDS = 21600
REQUIRED_SOURCE_PINS = frozenset((
    'scripts/run_zpd_full_source.py', 'scripts/run_zpd_transition_generation.py',
    'scripts/recover_zpd_transition_evaluation.py', 'scripts/zpd_transition_private.py',
    'scripts/zpd_public_candidate_selection.py', 'src/repair/pilot_contracts.py',
    'scripts/prepare_zpd_full_source.py',
))


def unit(phase):
    core.require(phase in PHASES, 'fixed full-source phase required')
    return UNIT_PREFIX + '-' + phase + '.service'


@contextmanager
def configured_core():
    """Do not mutate old module configuration outside this wrapper's operation."""
    original = core.FAMILY, core.unit
    core.FAMILY, core.unit = FAMILY, unit
    try:
        yield core
    finally:
        core.FAMILY, core.unit = original


def load_release(release_path, release_sha):
    """Authenticate release, pinned preparation, and the representation package."""
    release_path = Path(release_path)
    core.require(release_path.resolve() == release_path.absolute(), 'nonsymlink release required')
    release = core.load_release(release_path, release_sha)
    core.require(release.get('layout_variant') == VARIANT and release.get('family_path') == str(FAMILY)
                 and release['inputs_path'] == str(INPUTS), 'full-source namespace release required')
    core.require(release.get('excluded_recipients') == 0 and release.get('draws_per_arm') == 2
                 and release.get('retries') == 0 and release['fitting'] is False
                 and release['no_retry'] is True and release['no_truncation'] is True,
                 'fixed nofit/noexclude/no-retry scope required')
    core.require(REQUIRED_SOURCE_PINS <= set(release['source_sha256']), 'wrapper/algorithm/terminal source pins required')
    for name in release['source_sha256']:
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'safe source pin path required')
    complete = core.read_pinned(INPUTS.parent / 'COMPLETE.json', release['inputs_complete_sha256'])
    core.require(complete['status'] == 'complete' and complete['layout_variant'] == VARIANT
                 and complete['files_sha256']['inputs.json'] == release['inputs_sha256'], 'full-source preparation seal differs')
    for name, pin in complete['files_sha256'].items():
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'safe preparation file path required')
        path = INPUTS.parent / name
        core.require(path.resolve() == path and core.sha_file(path) == pin, 'preparation artifact changed: ' + name)
    inputs = core.inputs_for(release)
    original = core.read_pinned(BASELINE_INPUTS, BASELINE_INPUTS_SHA)
    validate_representation(inputs, original)
    return release


def source_barrier(release_path, release_sha, revision=None):
    current = core.clean_source()
    root = Path.cwd().resolve()
    core.require(root == Path(__file__).resolve().parents[1]
                 and root == Path(core.__file__).resolve().parents[1], 'wrapper and algorithms must share the clean snapshot')
    core.require(Path(release_path).resolve().is_relative_to(root), 'release must belong to the clean snapshot')
    core.require(revision is None or current == revision, 'snapshot revision changed')
    return current, load_release(release_path, release_sha)


def worker(phase, release_path, release_sha):
    core.require(phase in PHASES, 'fixed full-source phase required')
    with configured_core():
        revision, _ = source_barrier(release_path, release_sha)
        core.worker(phase, release_path, release_sha)
        source_barrier(release_path, release_sha, revision)


def command(phase, release_path, release_sha, snapshot=None):
    """Launch THIS wrapper, not the original driver's unscoped entry point."""
    core.require(phase in PHASES, 'fixed full-source phase required')
    snapshot = Path.cwd().resolve() if snapshot is None else Path(snapshot)
    memory, tasks, address = core.limits(phase)
    properties = dict(MemoryMax=str(memory), TasksMax=str(tasks), LimitAS=address,
        RuntimeMaxSec=str(SECONDS), KillMode='control-group', KillSignal='SIGKILL', SendSIGKILL='yes',
        Restart='no', OOMPolicy='stop', Delegate='no', RemainAfterExit='yes',
        MemoryAccounting='yes', TasksAccounting='yes', WorkingDirectory=str(snapshot),
        StandardOutput='append:' + str(FAMILY / (phase + '.log')),
        StandardError='append:' + str(FAMILY / (phase + '.log')))
    cmd = ['/usr/bin/systemd-run', '--user', '--unit=' + unit(phase), '--service-type=exec']
    cmd += ['--property=' + k + '=' + v for k, v in properties.items()]
    environment = dict(PYTHONDONTWRITEBYTECODE='1', TOKENIZERS_PARALLELISM='false',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
        HF_HOME=str(PROJECT / '.cache/huggingface'), TORCH_HOME=str(PROJECT / '.cache/torch'),
        XDG_CACHE_HOME=str(PROJECT / '.cache'), TRITON_CACHE_DIR=str(PROJECT / '.cache/triton'),
        TMPDIR=str(PROJECT / '.runtime/transition-tmp-20261012'))
    cmd += ['--setenv=' + k + '=' + v for k, v in environment.items()]
    python = PROJECT / ('.runtime/fse-vllm/bin/python' if phase == 'generation' else '.runtime/fse-env/bin/python')
    return cmd + [str(python), '-m', 'scripts.run_zpd_full_source', 'worker', '--phase', phase,
                  '--release', str(release_path), '--release-sha', release_sha]


def certify(phase, release_path, release_sha, revision, values=None):
    source_barrier(release_path, release_sha, revision)
    name = unit(phase)
    values = core.props(name) if values is None else values
    core.require(core.normal_exit(values), 'phase did not exit normally: ' + phase)
    output = FAMILY / (phase + '-v1')
    seal = core.verify_stage(output, phase, release_sha)
    core.require(not any('FAILED' in n or 'INCOMPLETE' in n or n.endswith('.partial') for n in seal['files_sha256']),
                 'failed/incomplete stage cannot be certified')
    manifest = json.loads((output / 'stage-manifest.json').read_bytes())
    core.require(manifest['revision'] == revision and manifest['release_sha256'] == release_sha
                 and manifest['phase'] == phase, 'worker source/release binding changed')
    cleanup = terminal_group(values, manifest['envelope']['cgroup'], name)
    certificate = dict(status='complete', layout_variant=VARIANT, release_sha256=release_sha,
        complete_sha256=core.sha_file(output / 'STAGE_COMPLETE.json'), revision=revision,
        exit={k: values[k] for k in ('Result', 'ExecMainCode', 'ExecMainStatus', 'MainPID', 'SubState')},
        systemd_properties=values, **cleanup)
    core.write_new(FAMILY / (phase + '-VERIFIED_COMPLETE.json'), certificate)
    subprocess.run(['/usr/bin/systemctl', '--user', 'stop', name], check=True, timeout=30)
    return certificate


def summarize_private(report, release_sha, report_sha):
    """Preserve existing descriptive gate results; never infer historical success."""
    core.require(report['methods'] == [*core.ARMS, 'noop'] and report['full']['examples'] == 320
                 and report['execution_complete'] is True, 'complete selected-only private report required')
    core.require(report['historical_gates_evaluated'] is False
                 and report['historical_gate_status'] == 'not_applicable_to_new_generation_arms'
                 and report['confirmatory'] is False and report['model_promotion'] is False
                 and report['educational_benefit_established'] is False, 'private report claim boundary differs')
    counts = {arm: deepcopy(report['full']['results'][arm]['counts']) for arm in report['methods']}
    return dict(version='full_source_representation_package_report_v1', layout_variant=VARIANT,
        intervention_kind='representation_package', pure_order_ablation=False,
        training_distribution_alignment_established=False, history_model_established=False,
        release_sha256=release_sha, private_report_sha256=report_sha,
        examples=320, methods=list(report['methods']), counts=counts,
        full=deepcopy(report['full']), folds=deepcopy(report['folds']), paired_H=deepcopy(report['paired_H']),
        current_status_subgroups=deepcopy(report['current_status_subgroups']),
        development_gate=deepcopy(report['development_gate']),
        historical_gate_status=report['historical_gate_status'], historical_gates_evaluated=False,
        historical_gates_passed=False, confirmatory=False, model_promotion=False,
        educational_benefit_established=False, execution_complete=True,
        unknown_bounds_are_confidence_intervals=False,
        summary_ko='전체 소스 메시지 표현 패키지 실험: ' + ', '.join(
            arm + ' stable AC ' + str(counts[arm]['stable_ac']) + '/320' for arm in core.ARMS)
            + '. 기존 development gate: ' + str(report['development_gate']['decision'])
            + '. 적응적 개발 진단이며 모델 승격 또는 교육 효과를 주장하지 않습니다.',
        limitations=['Full-source message representation package versus the previous JSON-diff package; not a pure ordering ablation.',
            'Exposed adaptive development cohort; training-distribution alignment and a history-conditioned model are not established.',
            'Generation, selector, selected-only private evaluation and descriptive development gate are unchanged.',
            'No comparison against another run is an automatic promotion or historical-gate pass.',
            'An incomplete or unstable observation is not a failed candidate.'])


def finalize(release_path, release_sha, revision):
    source_barrier(release_path, release_sha, revision)
    for phase in PHASES:
        core.verified_dependency(phase, release_sha)
    private = FAMILY / 'private-v1/evaluation'
    complete = json.loads((private / 'COMPLETE.json').read_bytes())
    core.require(complete['status'] == 'complete' and complete['provisional_until_normal_unit_exit'] is True,
                 'complete private result required')
    report_sha = complete['files_sha256']['report.json']
    report = core.read_pinned(private / 'report.json', report_sha)
    summary = summarize_private(report, release_sha, report_sha)
    core.write_new(FAMILY / 'REPORT.json', summary)
    core.status_write(FAMILY / 'STATUS.json', dict(phase='complete', completed_phases=list(PHASES), checked=time.time()))
    certificate = dict(status='complete', layout_variant=VARIANT, release_sha256=release_sha, revision=revision,
        phases={phase: core.sha_file(FAMILY / (phase + '-VERIFIED_COMPLETE.json')) for phase in PHASES},
        files_sha256={'REPORT.json': core.sha_file(FAMILY / 'REPORT.json')},
        development_decision=report['development_gate']['decision'],
        model_promotion=False, historical_gates_passed=False, confirmatory=False)
    core.write_new(FAMILY / 'VERIFIED_COMPLETE.json', certificate)
    return summary


def supervise(release_path, release_sha):
    """Fresh family only; fixed generation -> public -> private, without retry."""
    release_path = Path(release_path).absolute()
    with configured_core():
        revision, _ = source_barrier(release_path, release_sha)
        core.require(not FAMILY.exists(), 'run family already exists; no duplicate coordinator')
        for phase in PHASES:
            core.require(core.props(unit(phase)).get('LoadState') == 'not-found', 'phase unit already exists')
        FAMILY.mkdir(parents=True)
        core.write_new(FAMILY / 'COORDINATOR.json', dict(release_sha256=release_sha, layout_variant=VARIANT,
            revision=revision, phases=list(PHASES), started=time.time(), retries=0))
        completed, launched = [], []
        try:
            for phase in PHASES:
                source_barrier(release_path, release_sha, revision)
                core.require(not (FAMILY / (phase + '-v1')).exists()
                             and core.props(unit(phase)).get('LoadState') == 'not-found', 'duplicate next phase')
                for prior in completed:
                    core.verified_dependency(prior, release_sha)
                # A launch timeout/nonzero return can follow successful unit
                # creation. Include this exact fresh unit in failure cleanup.
                launched.append(phase)
                subprocess.run(command(phase, release_path, release_sha), check=True, timeout=30)
                deadline = time.monotonic() + SECONDS + 300
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
        except BaseException as exc:
            cleanup = {}
            for phase in launched:
                if phase not in completed:
                    try:
                        subprocess.run(['/usr/bin/systemctl', '--user', 'stop', unit(phase)], check=True, timeout=30)
                        cleanup[phase] = 'stop_completed'
                    except BaseException as stop_error:
                        cleanup[phase] = type(stop_error).__name__ + ': ' + str(stop_error)
            core.write_new(FAMILY / 'COORDINATOR_FAILED.json', dict(error_type=type(exc).__name__, error=str(exc),
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
