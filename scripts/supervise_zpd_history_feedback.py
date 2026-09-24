"""Bounded C3 fit -> independent replay, with no retries or model promotion."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from scripts import zpd_history_feedback_release as release
from scripts.supervise_zpd_history_action import (
    run_stage, verify_previous_stages, write, read, sha, event, source_state,
    HEARTBEAT_SECONDS, MEMORY_BYTES, CROSS_FIT_SECONDS, FOLLOWUP_SECONDS)

ROOT=Path(__file__).resolve().parents[1]
FAMILY='outputs/zpd-history-feedback-coupling-20260924'


def supervise(project,output,run_output):
    project,output,run_output=map(release.canonical,(project,output,run_output))
    if output.parent != project/FAMILY or run_output.parent != project/FAMILY or output == run_output:
        raise ValueError('distinct direct output children of fixed family required')
    if output.exists() or run_output.exists():
        raise ValueError('new output paths required; no automatic retry')
    provenance=source_state()
    # Fail closed before creating a supervisor or launching any child.
    release.check_release(project,project/release.SUPPORT_RELATIVE,
        release.SUPPORT_COMPLETE_SHA,ROOT/release.RELEASE_RELATIVE)
    commands=[
        ('crossfit',[sys.executable,'-B','-m','scripts.run_zpd_history_feedback_cv',
            '--project',str(project),'--output',str(run_output),
            '--support',str(project/release.SUPPORT_RELATIVE),
            '--support-complete-sha256',release.SUPPORT_COMPLETE_SHA,
            '--release',str(ROOT/release.RELEASE_RELATIVE)],run_output,CROSS_FIT_SECONDS),
        ('verify',[sys.executable,'-B','-m','scripts.audit_zpd_history_feedback_cv',
            '--project',str(project),'--run',str(run_output),'--output',str(output/'verified')],
            output/'verified',FOLLOWUP_SECONDS)]
    output.mkdir(parents=True)
    write(output/'manifest.json',dict(kind='bounded_feedback_coupling_crossfit_and_audit_v1',
        source=provenance,source_root=str(ROOT),project_root=str(project),
        support_complete_sha256=release.SUPPORT_COMPLETE_SHA,release_sha256=release.RELEASE_SHA,
        heartbeat_seconds=HEARTBEAT_SECONDS,child_memory_bytes=MEMORY_BYTES,
        stages=[dict(name=n,command=c,output=str(o),timeout_seconds=t) for n,c,o,t in commands],
        automatic_retries=0,model_promotion=False,fresh_test_opened=False))
    results=[]
    try:
        for name,command,stage_output,timeout in commands:
            if source_state() != provenance:
                raise ValueError('source drift before next stage')
            verify_previous_stages(results)
            results.append(run_stage(command,name=name,cwd=ROOT,stage_output=stage_output,
                output=output,timeout_seconds=timeout))
        verify_previous_stages(results)
        if source_state() != provenance:
            raise ValueError('source drift before supervisor completion')
        audit=read(output/'verified/report.json')
        if audit.get('verified') is not True:
            raise ValueError('positive independent numerical audit required')
        report=read(run_output/'report.json')
        next_action=dict(action=report['decision']['next_action'],decision=report['decision'],
            model_promotion=False,repair_improvement_established=False,
            instruction='Root must inspect verified results and continue the separately frozen research path; no automatic refit.')
        write(output/'stages.json',results);write(output/'next_action.json',next_action)
        verify_previous_stages(results)
        event(output,phase='complete',completed_stages=len(results),next_action=next_action)
        if source_state() != provenance:
            raise ValueError('source drift before terminal supervisor seal')
        verify_previous_stages(results)
        write(output/'COMPLETE.json',dict(status='complete',completed_stages=len(results),
            run_complete_sha256=sha(run_output/'COMPLETE.json'),files_sha256={name:sha(output/name) for name in
                ('manifest.json','stages.json','next_action.json','verified/COMPLETE.json','STATUS.json','events.jsonl')}))
        return next_action
    except BaseException as exc:
        failure=dict(phase='failed',completed_stages=results,error_type=type(exc).__name__,error=str(exc),
            next_action='diagnose_operational_failure_without_repeating_or_changing_frozen_experiment')
        write(output/'FAILED.json',failure);event(output,**failure)
        raise


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run-output',type=Path,required=True)
    args=parser.parse_args()
    supervise(args.project,args.output,args.run_output)


if __name__=='__main__':
    main()
