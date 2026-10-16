"""One objective-only matched training intervention, then unchanged evaluation.

The seven-stage lifecycle reuses sealed input bytes, not adapters or outcomes.
No cache rerun, filtering, tuning, retries, or implicit promotion is permitted.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import shutil

from scripts import run_zpd_paired_history as parent
from scripts import run_zpd_paired_inference_recovery as ipc
from scripts import zpd_edit_balanced_objective as objective

core = parent.core
PROJECT = parent.PROJECT
FAMILY = PROJECT / 'outputs/zpd-edit-balanced-20261016'
UNIT_PREFIX = 'zpd-edit-balanced-20261016-v1'
VERSION = 'edit_balanced_paired_release_v1'
PHASES = parent.PHASES[1:]
PHASE_SECONDS = {p: parent.PHASE_SECONDS[p] for p in PHASES}
RPC_BASE = PROJECT / 'tmp/eb-1016-v1'
OLD_FAMILY = parent.FAMILY
OLD_RELEASE = '2323a878e1dad79ac8bbfde048581670ca8de8c3280f6903433c8edf09b3036b'
MATERIALIZED = OLD_FAMILY / 'materialize-v1/materialized'
REUSE_PINS = {
    'materialize-VERIFIED_COMPLETE.json': '34f84a911d9d5ec9420b69ad7a7b70f272bb895210f51e029ac5f627a162be11',
    'materialize-v1/STAGE_COMPLETE.json': '9df548caa465121a9cec46e7945520bf891e4a9dcc055b39e461e625c13ce1a0',
    'materialize-v1/materialized/COMPLETE.json': 'daab8a4aa855c1e33f2da5ea814f8b64d82d56083bad6e627f0712408c0d0cca',
}
TIE_FAMILY = PROJECT / 'outputs/zpd-anchor-tie-20261016'
TIE_RELEASE = 'f2ca99301cee4ae630c0f801025d1457b71807a8ce622dfa9dea55a637fd0683'
TIE_COMPLETE = 'a0d208e6b1b2f9d7dbcc219ab8e9e48280117e3184b735f690bb9617ed714659'
BASE_BARRIER = parent.source_barrier
BASE_EARLY = parent.run_early_phase
BASE_VALIDATE = parent.validate_phase_result
BASE_COMMAND = parent.command
BASE_PAIR = parent.verify_training_pair
BASE_SUMMARIZE = parent.summarize_private
REQUIRED = {'scripts/run_zpd_edit_balanced.py', 'scripts/zpd_edit_balanced_objective.py',
            'tests/test_zpd_edit_balanced.py', 'analysis_protocols/zpd-edit-balanced-20261016.md'}


def amendment():
    return dict(objective=objective.contract(), input_family=str(OLD_FAMILY), input_pins=REUSE_PINS,
        input_release_sha256=OLD_RELEASE, predecessor_family=str(TIE_FAMILY),
        predecessor_release_sha256=TIE_RELEASE, predecessor_complete_sha256=TIE_COMPLETE,
        byte_identical_records=True, fresh_base_initialization=True, cache_repeated=False,
        adaptive_development=True, parameter_search=False, rpc_base_path=str(RPC_BASE))


def validate_amendment(release, previous, latest):
    core.require(release.get('objective_intervention') == amendment(), 'fixed objective amendment required')
    mutable = {'version', 'family_path', 'phases', 'phase_seconds', 'source_sha256', 'objective_intervention'}
    core.require({k:v for k,v in release.items() if k not in mutable}
                 == {k:v for k,v in previous.items() if k not in mutable}, 'scientific training/evaluation contract changed')
    core.require(REQUIRED <= set(release['source_sha256']), 'missing objective source pins')
    allowed = {'scripts/train_zpd_paired_history.py', 'scripts/watch_zpd_completion.py',
               'tests/test_watch_zpd_completion.py'}
    for baseline in (previous, latest):
        for name, pin in baseline['source_sha256'].items():
            if name not in allowed:
                core.require(release['source_sha256'].get(name) == pin, 'unrelated source changed: ' + name)


def verify_reuse():
    for name, pin in REUSE_PINS.items():
        core.require(core.sha_file(OLD_FAMILY / name) == pin, 'reused materialization drift: ' + name)
    cert = json.loads((OLD_FAMILY / 'materialize-VERIFIED_COMPLETE.json').read_bytes())
    core.require(cert['status'] == 'complete' and cert['cleanup_verified'] is True
        and core.normal_exit(cert['exit']) and cert['release_sha256'] == OLD_RELEASE
        and cert['complete_sha256'] == REUSE_PINS['materialize-v1/STAGE_COMPLETE.json'],
        'normal-exit reused input certificate required')
    core.verify_stage(OLD_FAMILY / 'materialize-v1', 'materialize', OLD_RELEASE)
    return parent.read_sealed(MATERIALIZED, REUSE_PINS['materialize-v1/materialized/COMPLETE.json'])


def source_barrier(path, digest, revision=None):
    current, release = BASE_BARRIER(path, digest, revision)
    previous = core.read_pinned(Path('analysis_protocols/zpd-paired-history-release-20261015.json'), OLD_RELEASE)
    latest = core.read_pinned(Path('analysis_protocols/zpd-anchor-tie-release-20261016.json'), TIE_RELEASE)
    validate_amendment(release, previous, latest)
    verify_reuse()
    from scripts.watch_zpd_completion import verify_terminal
    outer = core.read_pinned(TIE_FAMILY / 'VERIFIED_COMPLETE.json', TIE_COMPLETE)
    core.require(outer['release_sha256'] == TIE_RELEASE, 'predecessor release differs')
    verify_terminal(TIE_FAMILY, outer)
    values = core.props('zpd-anchor-tie-20261016-v1-coordinator.service')
    core.require(core.normal_exit(values) and values.get('ControlGroup') == '', 'predecessor not normally finished')
    ipc.validate_rpc_path(RPC_BASE)
    return current, release


def paired(release, split):
    root = FAMILY / 'materialize-v1/materialized'
    rows = {a: [json.loads(line) for line in (root / (split + '-' + a + '.jsonl')).read_bytes().splitlines()]
            for a in ('C', 'H')}
    result = objective.paired_preflight(rows['C'], rows['H'], parent._tokenizer(release))
    core.require(result['report'] == json.loads((root / (split + '-token-preflight.json')).read_bytes()),
                 'recomputed balanced preflight differs')
    return result


def materialize(release, output):
    old_seal = verify_reuse()
    root = output / 'materialized'; root.mkdir(exist_ok=False)
    audits = {}
    tokenizer = parent._tokenizer(release)
    for split in ('train', 'valid'):
        rows = {}
        for arm in ('C', 'H'):
            name = split + '-' + arm + '.jsonl'
            shutil.copyfile(MATERIALIZED / name, root / name)
            core.require(core.sha_file(root / name) == old_seal['files_sha256'][name], 'record bytes changed')
            rows[arm] = [json.loads(line) for line in (root / name).read_bytes().splitlines()]
        result = objective.paired_preflight(rows['C'], rows['H'], tokenizer)
        old = json.loads((MATERIALIZED / (split + '-token-preflight.json')).read_bytes())
        for key in ('example_ids', 'order_sha256', 'caps', 'records_sha256', 'target_contract'):
            core.require(result['report'][key] == old[key], 'paired input contract changed: ' + key)
        core.write_new(root / (split + '-token-preflight.json'), result['report'])
        audits[split] = result['report']['objective_audit']
        name = split + '-trajectory-exclusions.json'
        shutil.copyfile(MATERIALIZED / name, root / name)
    report = json.loads((MATERIALIZED / 'report.json').read_bytes())
    report.update(objective_intervention=amendment(), objective_audit=audits)
    core.write_new(root / 'report.json', report)
    seal = deepcopy(old_seal)
    seal.update(objective_intervention=amendment(), reused_complete_sha256=REUSE_PINS['materialize-v1/materialized/COMPLETE.json'],
        files_sha256={str(p.relative_to(root)): core.sha_file(p) for p in sorted(root.iterdir()) if p.is_file()})
    core.write_new(root / 'COMPLETE.json', seal)


def run_early_phase(phase, release, output, guard, parent_sha):
    if phase == 'materialize':
        materialize(release, output)
    else:
        BASE_EARLY(phase, release, output, guard, parent_sha)


def validate_phase_result(phase, release, output):
    if phase != 'materialize':
        return BASE_VALIDATE(phase, release, output)
    root = output / 'materialized'
    seal = parent.read_sealed(root, core.sha_file(root / 'COMPLETE.json'))
    core.require(seal['objective_intervention'] == amendment()
        and seal['reused_complete_sha256'] == REUSE_PINS['materialize-v1/materialized/COMPLETE.json']
        and seal['history_truncated'] is False and seal['dev_evaluation_recipients_filtered'] is False,
        'objective materialization binding differs')


def verify_training_pair(digest):
    summaries = BASE_PAIR(digest)
    for row in summaries.values():
        core.require(row.get('objective') == objective.contract() and row['edit_token_weight'] is None,
                     'trained objective differs')
    return summaries


def command(phase, path, digest, snapshot=None):
    cmd = BASE_COMMAND(phase, path, digest, snapshot)
    cmd = ['scripts.run_zpd_edit_balanced' if x == 'scripts.run_zpd_paired_history' else x for x in cmd]
    if phase == 'generation':
        cmd = ['--setenv=TMPDIR=' + str(RPC_BASE) if x.startswith('--setenv=TMPDIR=') else x for x in cmd]
        cmd.insert(cmd.index(str(PROJECT / '.runtime/fse-vllm/bin/python')),
                   '--setenv=VLLM_RPC_BASE_PATH=' + str(RPC_BASE))
    return cmd


def summarize_private(report, release_sha, report_sha, population):
    result = BASE_SUMMARIZE(report, release_sha, report_sha, population)
    result.update(intervention_kind='edit_copy_balanced_matched_C_H_training', objective_intervention=amendment())
    result['limitations'].append('Objective-only adaptive intervention; unchanged final-AC targets do not measure learning benefit.')
    return result


@contextmanager
def configured():
    overrides = dict(FAMILY=FAMILY, UNIT_PREFIX=UNIT_PREFIX, VERSION=VERSION, PHASES=PHASES,
        PHASE_SECONDS=PHASE_SECONDS, source_barrier=source_barrier, _paired=paired,
        run_early_phase=run_early_phase, validate_phase_result=validate_phase_result,
        verify_training_pair=verify_training_pair, command=command, summarize_private=summarize_private)
    previous = {k:getattr(parent,k) for k in overrides}
    for k,v in overrides.items(): setattr(parent,k,v)
    try:
        yield
    finally:
        for k,v in previous.items(): setattr(parent,k,v)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('mode', choices=('verify', 'worker', 'supervise'))
    parser.add_argument('--phase', choices=PHASES)
    parser.add_argument('--release', type=Path, required=True); parser.add_argument('--release-sha', required=True)
    args = parser.parse_args()
    with configured():
        if args.mode == 'verify':
            revision, _ = source_barrier(args.release, args.release_sha)
            print(json.dumps(dict(status='verified', revision=revision, objective=objective.contract())))
        elif args.mode == 'supervise':
            source_barrier(args.release, args.release_sha)
            core.require(not FAMILY.exists() and not RPC_BASE.exists(), 'fresh objective and IPC namespaces required')
            RPC_BASE.mkdir(parents=True, mode=0o700, exist_ok=False)
            parent.supervise(args.release, args.release_sha)
        else:
            if args.phase == 'generation':
                old = ipc.RPC_BASE; ipc.RPC_BASE = RPC_BASE
                try: core.write_new(FAMILY / 'IPC_PREFLIGHT.json', ipc.probe_ipc())
                finally: ipc.RPC_BASE = old
            parent.worker(args.phase, args.release, args.release_sha)


if __name__ == '__main__':
    main()
