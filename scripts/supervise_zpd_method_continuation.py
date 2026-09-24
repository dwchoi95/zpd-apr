"""Two frozen, independently checked methodology experiments, not a search loop.

Scientific gate failure does not block the other prespecified experiment.
Operational failure or invalid evidence does: neither is a scientific result.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from scripts.supervise_zpd_history_action import (
    CROSS_FIT_SECONDS, FOLLOWUP_SECONDS, HEARTBEAT_SECONDS, MEMORY_BYTES,
    event, read, run_stage, sha, verify_previous_stages, write)

ROOT = Path(__file__).resolve().parents[1]
FAMILY = 'outputs/zpd-method-continuation-20260924'
REPAIR_FAMILY = 'outputs/zpd-repair-preservation-20260924'
ACTION_FAMILY = 'outputs/zpd-history-action-blocked-20260924'


def source_state():
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise ValueError('clean committed execution snapshot required')
    return {key: subprocess.check_output(['git', 'rev-parse', spec], cwd=ROOT, text=True).strip()
            for key, spec in (('revision', 'HEAD'), ('tree', 'HEAD^{tree}'))}


def stages(project, output):
    repair, action = project / REPAIR_FAMILY / 'run-v1', project / ACTION_FAMILY / 'run-v1'
    definitions = (
        ('repair_crossfit', 'scripts.run_zpd_repair_preservation_cv',
         ['--project', str(project), '--output', str(repair)], repair, FOLLOWUP_SECONDS),
        ('repair_verify', 'scripts.audit_zpd_repair_preservation_cv',
         ['--project', str(project), '--run', str(repair), '--output', str(output / 'repair-verified')],
         output / 'repair-verified', FOLLOWUP_SECONDS),
        ('action_crossfit', 'scripts.run_zpd_history_action_blocked_cv',
         ['--project', str(project), '--output', str(action)], action, CROSS_FIT_SECONDS),
        ('action_verify', 'scripts.audit_zpd_history_action_blocked_cv',
         ['--project', str(project), '--run', str(action), '--output', str(output / 'action-verified')],
         output / 'action-verified', FOLLOWUP_SECONDS),
    )
    return [(name, [sys.executable, '-m', module, *arguments], directory, timeout)
            for name, module, arguments, directory, timeout in definitions]


def supervise(project, output):
    project, output = (Path(p).absolute() for p in (project, output))
    if any(p.resolve() != p for p in (project, output)):
        raise ValueError('canonical paths without symlinks required')
    if output.parent != project / FAMILY or output.exists():
        raise ValueError('new direct child of fixed continuation family required')
    commands = stages(project, output)
    for _, _, directory, _ in commands:
        if directory.exists() or directory.is_symlink():
            raise ValueError('all stage outputs must be new; no silent retry')
    provenance = source_state()
    output.mkdir(parents=True)
    write(output / 'manifest.json', dict(
        kind='two_frozen_methodology_experiments_20260924', source=provenance,
        source_root=str(ROOT), project_root=str(project),
        heartbeat_seconds=HEARTBEAT_SECONDS, child_memory_bytes=MEMORY_BYTES,
        stages=[dict(name=n, command=c, output=str(o), timeout_seconds=t) for n, c, o, t in commands],
        automatic_retries=0, opens_fresh_heldout_labels=False, model_promotion=False,
        scientific_gate_failure_does_not_block_independent_branch=True))
    completed = []
    try:
        for name, command, directory, timeout in commands:
            if source_state() != provenance:
                raise ValueError('source drift before next stage')
            verify_previous_stages(completed)
            completed.append(run_stage(command, name=name, cwd=ROOT, stage_output=directory,
                output=output, timeout_seconds=timeout))
        verify_previous_stages(completed)
        if source_state() != provenance:
            raise ValueError('source drift at completion')
        repair = read(commands[0][2] / 'report.json')
        action = read(commands[2][2] / 'report.json')
        verify_previous_stages(completed)
        if source_state() != provenance:
            raise ValueError('source drift while reading final reports')
        report = dict(kind='two_frozen_methodology_experiments_20260924',
            repair_decision=repair['decision'], action_decision=action['decision'],
            completed_stages=len(completed), confirmatory=False,
            canonical_model_changed=False, paper_results_changed=False,
            note='Repair and behavioral gates are separate; no secondary-arm promotion. '
                 'The fixed queue has ended, not a running autonomous LLM session.')
        write(output / 'stages.json', completed)
        write(output / 'report.json', report)
        event(output, phase='complete', completed_stages=len(completed),
              repair_decision=report['repair_decision'], action_decision=report['action_decision'])
        verify_previous_stages(completed)
        if source_state() != provenance:
            raise ValueError('source drift before final seal')
        write(output / 'COMPLETE.json', dict(status='complete', files_sha256={
            name: sha(output / name) for name in ('manifest.json', 'stages.json', 'report.json',
                'repair-verified/COMPLETE.json', 'action-verified/COMPLETE.json')},
            experiment_complete_sha256={n: sha(d / 'COMPLETE.json') for n, _, d, _ in commands}))
        return report
    except BaseException as exc:
        failure = dict(phase='failed', completed_stages=completed,
            error_type=type(exc).__name__, error=str(exc),
            next_action='diagnose_operational_error_preserve_frozen_protocol_and_partial_artifacts')
        write(output / 'FAILED.json', failure)
        event(output, **failure)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    return supervise(args.project, args.output)


if __name__ == '__main__':
    main()
