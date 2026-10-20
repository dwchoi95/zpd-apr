"""User-authorized fixed cutoff; only active ZPD project services are stopped.

Never deletes, rewrites experiment results, or fabricates COMPLETE markers.
Read-only inspection is the default; enforcement is rejected before the date.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

PROJECT=Path('/home/cdw/VSCode/zpd-apr')
DEADLINE='2026-10-21T13:00:00+09:00'
SELF='zpd-deadline-cutoff-20261021.service'


def require(ok,message):
    if not ok:raise ValueError(message)


def validate_policy(value):
    require(value['version']=='zpd_user_deadline_v1' and value['deadline']==DEADLINE
        and value['remote_project']==str(PROJECT) and value['timezone']=='Asia/Seoul'
        and value['stop_running_project_experiments'] is True
        and value['new_experiments_after_deadline'] is False and value['preserve_all_artifacts'] is True,
        'fixed user cutoff policy required')
    return value


def eligible(name,props):
    if name==SELF or not re.fullmatch(r'zpd-[A-Za-z0-9-]+\.service',name):return False
    if props.get('MainPID','0')=='0' and not props.get('ControlGroup'):return False
    directory=Path(props.get('WorkingDirectory','/'))
    command=props.get('ExecStart','')
    require(directory.is_absolute() and directory.resolve()==directory
        and directory.is_relative_to(PROJECT/'.runtime') and directory!=PROJECT/'.runtime'
        and str(PROJECT/'.runtime/')+'/' in command
        and re.search(r' -m scripts\.run_zpd_[a-z_]+ (supervise|worker|coordinator)( |;)',command),
        'active ZPD service has unverified scope: '+name)
    group=props.get('ControlGroup','')
    require(group.startswith('/user.slice/') and group.endswith('/'+name)
        and '..' not in Path(group).parts,'service cgroup scope differs: '+name)
    return True


def properties(name):
    raw=subprocess.check_output(['systemctl','--user','show','--all',name],text=True,timeout=10)
    return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)


def active_targets():
    raw=subprocess.check_output(['systemctl','--user','list-units','--type=service','--all','--no-legend','--plain'],text=True,timeout=10)
    names=[line.split()[0] for line in raw.splitlines() if line.strip() and line.split()[0].startswith('zpd-')]
    targets=[]
    for name in names:
        p=properties(name)
        if eligible(name,p):targets.append(dict(unit=name,properties={k:p.get(k) for k in
            ('Id','MainPID','ControlGroup','WorkingDirectory','ExecStart','ActiveState','SubState')}))
    return targets


def enforce(policy,output,*,now=None,scan=active_targets,stop=None):
    validate_policy(policy);now=datetime.now(timezone.utc) if now is None else now
    require(now>=datetime.fromisoformat(policy['deadline']),'deadline not reached; nothing may be stopped')
    output=Path(output);require(output.resolve()==output and output.is_relative_to(PROJECT/'outputs'),
        'project-local cutoff audit required')
    output.mkdir(parents=True,exist_ok=True)
    stop=(lambda name:subprocess.run(['systemctl','--user','stop',name],check=True,timeout=60)) if stop is None else stop
    stopped=[]
    # Stop all coordinators before taking a fresh worker snapshot, closing the
    # normal launch-next-stage race. Bound repeated scans; never kill by PID/glob.
    with (output/'events.jsonl').open('a') as log:
        for _ in range(4):
            targets=scan()
            if not targets:break
            coordinators=[r for r in targets if r['unit'].endswith('-coordinator.service')]
            for row in coordinators or targets:
                log.write(json.dumps(dict(event='stop_requested',at=datetime.now(timezone.utc).isoformat(),**row))+'\n');log.flush()
                stop(row['unit']);stopped.append(row['unit'])
        remaining=scan()
        report=dict(status='enforced' if not remaining else 'incomplete',deadline=policy['deadline'],
            checked_at=datetime.now(timezone.utc).isoformat(),stopped_units=stopped,remaining_units=remaining,
            artifacts_deleted=False,experiment_completion_claimed=False,reason='user_deadline_not_scientific_failure')
        log.write(json.dumps(report)+'\n');log.flush()
    target=output/('cutoff-'+str(time.time_ns())+'.json')
    with target.open('x') as stream:json.dump(report,stream,indent=2)
    require(not remaining,'scoped experiment services remain after cutoff')
    return report


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('inspect','enforce'))
    p.add_argument('--policy',type=Path,required=True);p.add_argument('--sha256',required=True);a=p.parse_args()
    raw=a.policy.read_bytes();require(hashlib.sha256(raw).hexdigest()==a.sha256,'deadline policy hash differs')
    policy=validate_policy(json.loads(raw))
    if a.mode=='inspect':result=dict(deadline=policy['deadline'],targets=active_targets(),mutations=False)
    else:result=enforce(policy,PROJECT/'outputs/zpd-deadline-20261021')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
