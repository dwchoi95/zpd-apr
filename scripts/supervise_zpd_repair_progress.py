"""Ten fixed bounded children, with isolated own-job fold entry points.

The outside coordinator alone sees the complete provenance/receipt chain.
Scientific gate failure remains a completed negative result, never a retry.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

from scripts import guard_zpd_repair_progress as guard
from scripts.supervise_zpd_history_action import event,write,child_progress

ROOT=Path(__file__).resolve().parents[1]
MEMORY_BYTES=guard.CHILD_MEMORY_BYTES
HEARTBEAT_SECONDS=guard.HEARTBEAT_SECONDS
TIMEOUTS=dict(guard.TIMEOUTS)


def _limits():resource.setrlimit(resource.RLIMIT_AS,(MEMORY_BYTES,MEMORY_BYTES))


def _group_alive(process):
    try:os.killpg(process.pid,0);return True
    except ProcessLookupError:return False


def _stop_owned(process):
    """Only the new session/process group created by this exact Popen."""
    for sig,seconds in ((signal.SIGTERM,5.),(signal.SIGKILL,5.)):
        try:os.killpg(process.pid,sig)
        except ProcessLookupError:pass
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            process.poll()
            if not _group_alive(process):
                process.wait(timeout=max(.01,deadline-time.monotonic()));return
            time.sleep(.05)
    raise RuntimeError('owned child process group did not terminate within cleanup budget')


def run_child(command,*,name,cwd,stage_output,output,timeout_seconds,required_files):
    """One attempt. A fold needs its actual model/prediction files, not report.json."""
    guard.require(name in guard.STAGES and timeout_seconds==TIMEOUTS[name],'fixed child stage budget required')
    stage_output=guard.canonical(stage_output);output=guard.canonical(output)
    guard.require(not stage_output.exists(),'new child output required; no implicit resume')
    environment=dict(os.environ,**guard.ENVIRONMENT,PYTHONUNBUFFERED='1',PYTHONDONTWRITEBYTECODE='1')
    started=time.monotonic();log_path=output/(name+'.log');process=None
    with log_path.open('x',encoding='utf-8') as log:
        try:
            process=subprocess.Popen(command,cwd=cwd,env=environment,stdout=log,stderr=subprocess.STDOUT,
                start_new_session=True,preexec_fn=_limits)
            while True:
                elapsed=time.monotonic()-started
                event(output,phase='running',stage=name,child_pid=process.pid,elapsed_seconds=elapsed,
                    timeout_seconds=timeout_seconds,child_progress=child_progress(stage_output),log_bytes=log_path.stat().st_size)
                remaining=timeout_seconds-elapsed
                if remaining<=0:raise TimeoutError(name+' exceeded fixed budget')
                try:returncode=process.wait(timeout=min(HEARTBEAT_SECONDS,remaining));break
                except subprocess.TimeoutExpired:continue
            if returncode!=0:raise RuntimeError(f'{name} exited {returncode}; no retry or next-stage release')
            if _group_alive(process):raise RuntimeError('child exited with unexpected surviving descendants')
            guard.require(not (stage_output/'FAILED.json').exists() and not any(stage_output.glob('REJECTED_*')),
                          'failed child output cannot complete')
            seal=guard.verify_marker(stage_output,required_files=required_files)
            log.flush();os.fsync(log.fileno())
            result=dict(name=name,returncode=returncode,elapsed_seconds=time.monotonic()-started,
                output=str(stage_output),log_sha256=guard.sha(log_path),**seal)
            event(output,phase='child_complete',stage=name,result=result);return result
        except BaseException:
            if process is not None:_stop_owned(process)
            raise


def verify_previous(project,results,context):
    for result in results:
        actual=guard.verify_wrapper(project,result['name'],result['complete_sha256'])
        guard.require(guard.same(actual['report']['source'],context['source'])
            and actual['report']['release_sha256']==context['release_sha256'],'previous source/release changed')
        guard.require(guard.sha(guard.paths(project)['supervisor']/(result['name']+'.log'))==result['log_sha256'],
                      'previous child log changed')
        if result['name'].startswith('fold-'):
            own=guard.paths(project)['run']/result['name']
            guard.require(guard.sha(own/'COMPLETE.json')==result['child_complete_sha256'],'owned fold seal changed')


def command_for(project,stage,pins,context):
    """No global receipt/release argument is ever passed to a fitting child."""
    location=guard.paths(project)
    if stage.startswith('fold-'):
        fold=int(stage[-1]);receipt=guard.verify_wrapper(project,'initialize',pins['initialize'])['report']['result']
        pin=receipt['job_sha256'][str(fold)]
        guard.require(guard.sha(location['jobs']/f'fold-{fold}.json')==pin,'initialized own job changed before launch')
        return ([sys.executable,'-B','-m','scripts.run_zpd_repair_progress_job','--project',str(project),
            '--fold',str(fold),'--expected-capsule-sha',pin],location['run']/stage,guard.worker.FILES)
    return ([sys.executable,'-B','-m','scripts.guard_zpd_repair_progress','--project',str(project),
        '--stage',stage,'--previous-stage-sha256',json.dumps(pins,sort_keys=True,separators=(',',':'))],
        location['supervisor']/'stages'/stage,('report.json',))


def supervise(project):
    location=guard.paths(project);output=location['supervisor']
    guard.require(not any(location[k].exists() for k in ('run','jobs','supervisor')),'new run/jobs/supervisor outputs required')
    context=guard.preflight(project)  # Before any output or child.
    output.mkdir(parents=True);results=[];completed=0
    try:
        manifest_sha=guard.write(output/'manifest.json',dict(kind='statement_progress32_fixed10_supervisor_v1',project=str(project),
            source=context['source'],source_root=str(ROOT),release_sha256=context['release_sha256'],
            runtime=context['runtime'],controller_native=context['controller_native'],stages=list(guard.STAGES),
            child_memory_bytes=MEMORY_BYTES,environment=guard.ENVIRONMENT,heartbeat_seconds=HEARTBEAT_SECONDS,
            stage_timeout_seconds=TIMEOUTS,maximum_child_budget_seconds=sum(TIMEOUTS.values()),
            prepared_complete_sha256=guard.PREPARED_COMPLETE_SHA256,preparation_permitted=False,
            automatic_retries=0,model_promotion=False,full_train_refits=0))
        for stage in guard.STAGES:
            guard.recheck(context);verify_previous(project,results,context)
            pins={v['name']:v['complete_sha256'] for v in results}
            command,target,required=command_for(project,stage,pins,context)
            child=run_child(command,name=stage,cwd=ROOT,stage_output=target,output=output,
                timeout_seconds=TIMEOUTS[stage],required_files=required)
            guard.require(child['name']==stage and child['output']==str(target),'child result differs from fixed stage')
            if stage.startswith('fold-'):
                receipt=guard.finish_fold(project,int(stage[-1]),pins,context)
                result=dict(child,child_complete_sha256=child['complete_sha256'],
                    complete_sha256=receipt['complete_sha256'],output=str(output/'stages'/stage))
                count=receipt['report']['result']['predicted_examples']
                guard.require(type(count) is int and 0<count<=320,'valid completed OOF count required');completed+=count
            else:result=child
            results.append(result);verify_previous(project,results,context);guard.recheck(context)
            write(output/'stages.json',results)
            event(output,phase='stage_verified',stage=stage,completed_stages=len(results),completed_oof_examples=completed,total_oof_examples=320)
        audit=guard.verify_wrapper(project,'audit',results[-1]['complete_sha256'])['report']['result']
        guard.require(completed==320 and audit.get('verified') is True and audit.get('recipients')==320
            and audit.get('models')==30 and audit.get('methods')==13,'independent full320/30/13 audit required')
        run_pin=audit['experiment_complete_sha256'];report=guard.read(location['run']/'assessment/report.json')
        guard.require(guard.same(audit['gate'],report['gate']),'independent exact gate mismatch')
        next_action=dict(action='inspect_verified_results_and_freeze_next_evidence_supported_step',gate=report['gate'],
            development_repair_gate_passed=report['gate']['actual_repair_improvement'],
            mechanism_gate_passed=report['gate']['mechanism_contribution'],
            current_feedback_gate_passed=report['gate']['current_feedback_contribution'],
            model_promotion=False,full_train_refit_authorized=False,confirmatory=False,fresh_test_opened=False,
            educational_benefit_established=False,automatic_retry_authorized=False)
        next_action_sha=guard.write(output/'next_action.json',next_action)
        event(output,phase='complete',completed_stages=10,completed_oof_examples=320,total_oof_examples=320,next_action=next_action)
        contracts=guard.contracts_from_context(context)
        def barrier():
            verify_previous(project,results,context);guard.recheck(context)
            guard.require(guard.sha(location['run']/'COMPLETE.json')==run_pin,'audited experiment COMPLETE changed')
            guard.verify_audit_label_inputs(location,contracts)
        names=['manifest.json','stages.json','next_action.json','STATUS.json','events.jsonl','verified/report.json','verified/COMPLETE.json']
        names += [f'stages/{s}/'+n for s in guard.STAGES for n in ('report.json','COMPLETE.json')]
        names += [s+'.log' for s in guard.STAGES]
        pins={n:guard.sha(output/n) for n in names}
        pins.update({'manifest.json':manifest_sha,'next_action.json':next_action_sha})
        barrier();guard.stages._files(output,pins);barrier()
        complete_sha=guard.write(output/'COMPLETE.json',dict(status='complete',completed_stages=10,completed_oof_examples=320,
            completed_fits=30,files_sha256=pins,experiment_complete_sha256=run_pin,release_sha256=context['release_sha256'],
            model_promotion=False,full_train_refits=0,automatic_retries=0))
        barrier();guard.stages._files(output,pins);barrier()
        guard.stages._files(output,pins)
        guard.require(guard.sha(output/'COMPLETE.json')==complete_sha,'outer completion changed after writing')
        return next_action
    except BaseException as error:
        guard.reject(output,error)
        event(output,phase='failed',completed_stages=len(results),completed_oof_examples=completed,
            error_type=type(error).__name__,error=str(error),automatic_retries=0)
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--project',type=Path,required=True)
    return supervise(parser.parse_args(argv).project)


if __name__=='__main__':main()
