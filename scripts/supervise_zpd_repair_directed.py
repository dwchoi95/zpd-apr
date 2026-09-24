"""Ten bounded directed144 children using read-only sealed preparation.

No retry, preparation, full refit or promotion. Lifecycle is delegated unchanged
to the reviewed process helper; one-stage workers never spawn sibling workers.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from scripts import guard_zpd_repair_directed as guard
from scripts import run_zpd_repair_directed_cv as engine
from scripts.supervise_zpd_history_action import run_stage, event, write

ROOT = Path(__file__).resolve().parents[1]
MEMORY_BYTES = 32*1024**3
HEARTBEAT_SECONDS = 30
TIMEOUTS = {stage: 3600 if stage.startswith('fold-') or stage == 'audit' else 900 for stage in guard.STAGES}


def verify_previous(project, results, context):
    for result in results:
        verified = guard.verify_wrapper(project, result['name'], deep=True)
        if (verified['complete_sha256'] != result['complete_sha256']
                or verified['report']['source'] != context['source']
                or verified['report']['release_sha256'] != context['release_sha256']):
            raise ValueError('previous stage/source/release changed before continuation')
        if guard.sha(guard.paths(project)['supervisor']/(result['name']+'.log')) != result['log_sha256']:
            raise ValueError('previous child log changed before continuation')


def supervise(project):
    location = guard.paths(project); output = location['supervisor']
    if any(location[name].exists() for name in ('run', 'supervisor')):
        raise ValueError('new directed run and supervisor outputs required; no overwrite or retry')
    context = guard.preflight(project)
    commands = [(stage, [sys.executable, '-B', '-m', 'scripts.guard_zpd_repair_directed',
                 '--project', str(location['project']), '--stage', stage], output/'stages'/stage, TIMEOUTS[stage]) for stage in guard.STAGES]
    output.mkdir(parents=True)
    guard.write(output/'manifest.json', dict(kind='bounded_repair_directed_10_stage_supervisor_v1',
        project=str(location['project']), source=context['source'], source_root=str(ROOT), release_sha256=context['release_sha256'],
        runtime=guard.RUNTIME, external_guard_released=True, engine_own_cli_remains_unreleased=True,
        child_memory_bytes=MEMORY_BYTES, heartbeat_seconds=HEARTBEAT_SECONDS, blas_threads=1,
        maximum_child_budget_seconds=sum(TIMEOUTS.values()), reused_preparation_complete_sha256=guard.PREPARED_COMPLETE_SHA256,
        stages=[dict(name=name, command=command, output=str(path), timeout_seconds=limit) for name, command, path, limit in commands],
        preparation_permitted=False, automatic_retries=0, model_promotion=False, full_train_refits=0))
    results = []; completed_oof = 0
    try:
        for name, command, stage_output, limit in commands:
            guard.recheck(context); verify_previous(project, results, context)
            result = run_stage(command, name=name, cwd=ROOT, stage_output=stage_output, output=output,
                timeout_seconds=limit, heartbeat_seconds=HEARTBEAT_SECONDS, memory_bytes=MEMORY_BYTES)
            if result['name'] != name or result['output'] != str(stage_output): raise ValueError('child result differs from fixed stage')
            results.append(result); verify_previous(project, results, context); guard.recheck(context)
            write(output/'stages.json', results)
            if name.startswith('fold-'):
                count = guard.read(stage_output/'report.json')['result']['predicted_examples']
                if type(count) is not int or not 0 < count <= 320: raise ValueError('valid completed OOF example count required')
                completed_oof += count
            event(output, phase='stage_verified', stage=name, completed_stages=len(results), completed_oof_examples=completed_oof, total_oof_examples=320)
        audit = guard.verify_wrapper(project, 'audit', deep=True)['report']['result']
        if completed_oof != 320 or audit.get('verified') is not True or audit.get('recipients') != 320 or audit.get('models') != 25 or audit.get('methods') != 11:
            raise ValueError('complete independent320/25/11 numerical audit required')
        if audit.get('experiment_complete_sha256') != guard.sha(location['run']/'COMPLETE.json'):
            raise ValueError('audit must bind exact completed experiment')
        report = guard.read(location['run']/'assessment/report.json')
        if audit.get('gate') != report['gate']: raise ValueError('independent gate differs from sealed assessment')
        next_action = dict(action='inspect_verified_results_and_freeze_next_evidence_supported_step', gate=report['gate'],
            model_promotion=False, full_train_refit_authorized=False,
            development_repair_gate_passed=report['gate']['actual_repair_improvement'],
            mechanism_gate_passed=report['gate']['mechanism_contribution'], confirmatory=False, fresh_test_opened=False,
            educational_benefit_established=False,
            instruction='Retain all results, including failures; no automatic control promotion or fresh-data opening.')
        guard.write(output/'next_action.json', next_action)
        event(output, phase='complete', completed_stages=10, completed_oof_examples=320, total_oof_examples=320, next_action=next_action)
        verify_previous(project, results, context); guard.recheck(context)
        names = ['manifest.json', 'stages.json', 'next_action.json', 'STATUS.json', 'events.jsonl', 'verified/report.json', 'verified/COMPLETE.json']
        names += [f'stages/{stage}/'+name for stage in guard.STAGES for name in ('report.json', 'COMPLETE.json')]
        names += [stage+'.log' for stage in guard.STAGES]
        contracts = {None if key == 'assessment' else int(key): engine.LabelContract(**value)
                     for key, value in context['label_contracts'].items()}
        guard.verify_audit_label_inputs(location, contracts)
        engine._seal(output, names, completed_stages=10, completed_oof_examples=320,
            experiment_complete_sha256=guard.sha(location['run']/'COMPLETE.json'), release_sha256=context['release_sha256'], model_promotion=False)
        return next_action
    except BaseException as error:
        failure = dict(phase='failed', completed_stages=results, error_type=type(error).__name__, error=str(error),
            retry_authorized=False, next_action='diagnose_operational_failure_without_repeating_or_changing_frozen_experiment')
        guard.write(output/'FAILED.json', failure); event(output, **failure)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    return supervise(parser.parse_args(argv).project)


if __name__ == '__main__': main()
