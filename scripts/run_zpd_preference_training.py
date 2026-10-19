"""Four exclusive stages: immutable C/H references, then one C/H DPO epoch."""
import argparse
from contextlib import contextmanager
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import time

from scripts import run_zpd_preference_identity_pilot as pilot
from scripts import train_zpd_preference as trainer
from scripts import run_zpd_paired_history as paired

core=paired.core
ROOT=core.PROJECT/'outputs/zpd-preference-training-20261020'
UNIT_PREFIX='zpd-preference-training-20261020-v1'
VERSION='matched_immutable_reference_dpo_release_v1'
PHASES=('reference-C','reference-H','train-C','train-H')
SECONDS=dict(zip(PHASES,(28800,28800,86400,86400),strict=True))
PARENT_RELEASE='c55c6db085747064a247c453dc7433b159844ddf8e370a1e09b54a3d30da1dbc'
PARENT_SHA='834b9fe17d1ca25846274526fd624b3cd3f7854cd9d1877e608de4ea23111146'
MATERIAL_SHA='1d9886a201c761cc493a68c0c768137733a201232df52ac906e098e5d36deee4'
CAPACITY_SHA='30620dad1c0919ea5e05c8f4d4cd430284b0b882600ab83cbc09467f71e24810'
REQUIRED={'scripts/run_zpd_preference_training.py','scripts/train_zpd_preference.py',
    'tests/test_zpd_preference_training.py','analysis_protocols/zpd-preference-training-20261020.md'}


def unit(phase):
    core.require(phase in PHASES,'fixed preference phase required')
    return UNIT_PREFIX+'-'+phase+'.service'


def predecessor():
    from scripts.watch_zpd_completion import verify_terminal
    outer=core.read_pinned(pilot.ROOT/'VERIFIED_COMPLETE.json',PARENT_SHA)
    core.require(outer['release_sha256']==PARENT_RELEASE and outer['decision']=='ready_for_training',
        'certified ready pilot required')
    verify_terminal(pilot.ROOT,outer)
    props=core.props(pilot.UNIT_PREFIX+'-coordinator.service')
    core.require(core.normal_exit(props) and props.get('ControlGroup')=='','pilot coordinator not released')
    for phase,pin in outer['phases'].items():
        cert=core.read_pinned(pilot.ROOT/(phase+'-VERIFIED_COMPLETE.json'),pin)
        pilot.base.release_check.released(cert,pilot.UNIT_PREFIX+'-'+phase+'.service',PARENT_RELEASE)
    core.require(not list(pilot.ROOT.rglob('*FAILED*.json')),'pilot failure marker')
    paired.read_sealed(pilot.ROOT/'materialize-v1/materialized',MATERIAL_SHA)
    cap=core.read_pinned(pilot.ROOT/'capacity-v1/probe/capacity_report.json',CAPACITY_SHA)
    core.require(cap['status']=='passed' and cap['actual_fit'] is False and cap['optimizer_steps']==0,'no-fit pilot required')
    pilot.base.reuse.verify_reuse()
    return cap


def validate_release(r,old):
    core.require(r['version']==VERSION and r['family_path']==str(ROOT) and r['phases']==list(PHASES)
        and r['phase_seconds']==SECONDS and r['parent_release_sha256']==PARENT_RELEASE
        and r['parent_complete_sha256']==PARENT_SHA and r['method']==trainer.contract(), 'training contract differs')
    for key in ('counts','caps','prepared_complete_sha256','materialized_complete_sha256','base_model',
                'adapter_C','adapter_H','model_sha256','development_gate','training_versions'):
        core.require(r[key]==old[key],'data/model/performance gate differs: '+key)
    core.require(REQUIRED<=set(r['source_sha256']),'missing new training source pin')
    for name,pin in old['source_sha256'].items():
        if name not in ('scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'):
            core.require(r['source_sha256'].get(name)==pin,'parent source changed: '+name)


def barrier(path,digest,revision=None):
    own=Path(__file__).resolve().parents[1];current=core.clean_source()
    core.require(Path.cwd().resolve()==own and path.resolve()==path and path.is_relative_to(own)
        and (revision is None or current==revision),'clean fixed snapshot required')
    r=core.read_pinned(path,digest)
    old=core.read_pinned(own/'analysis_protocols/zpd-preference-identity-pilot-release-20261020.json',PARENT_RELEASE)
    validate_release(r,old)
    for name,pin in r['source_sha256'].items():
        p=own/name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts and p.resolve()==p
            and core.sha_file(p)==pin,'source drift: '+name)
    for key,expected in r['training_versions'].items():core.require(version(key)==expected,'runtime drift: '+key)
    predecessor();pilot.base.material.read_sealed(pilot.base.PREPARED,pilot.base.PREPARED_SHA)
    pilot.base.parent.models_pinned(r)
    return current,r


@contextmanager
def configured():
    overrides=dict(FAMILY=ROOT,UNIT_PREFIX=UNIT_PREFIX,PHASES=PHASES,PHASE_SECONDS=SECONDS,
        limits=lambda phase:(64*2**30,1024,'infinity'))
    old={k:getattr(paired,k) for k in overrides}
    for k,v in overrides.items():setattr(paired,k,v)
    try:yield
    finally:
        for k,v in old.items():setattr(paired,k,v)


def command(phase,path,digest):
    with configured():cmd=paired.command(phase,path,digest)
    cmd=['scripts.run_zpd_preference_training' if v=='scripts.run_zpd_paired_history'
         else str(core.PROJECT/'.runtime/fse-env/bin/python') if v.endswith('/.runtime/fse-vllm/bin/python') else v for v in cmd]
    cmd.insert(cmd.index(str(core.PROJECT/'.runtime/fse-env/bin/python')),
        '--setenv=CUDA_CACHE_PATH='+str(ROOT/'runtime-cache'/phase/'cuda'))
    return cmd


def verify_stage(phase,digest):
    cert=json.loads((ROOT/(phase+'-VERIFIED_COMPLETE.json')).read_bytes())
    pilot.base.release_check.released(cert,unit(phase),digest)
    core.require(cert['complete_sha256']==core.sha_file(ROOT/(phase+'-v1/STAGE_COMPLETE.json')),'stage seal drift')
    return core.verify_stage(ROOT/(phase+'-v1'),phase,digest)


def dependencies(phase,digest):
    core.require(phase in PHASES,'fixed phase required')
    for prior in PHASES[:PHASES.index(phase)]:verify_stage(prior,digest)


def data(arm,tokenizer):
    rows={};audits={};root=pilot.base.reuse.MATERIALIZED
    for split,count in pilot.base.lifecycle.COUNTS.items():
        rows[split]=trainer.train._read_rows(root/(split+'-'+arm+'.jsonl'))
        audits[split]=json.loads((pilot.ROOT/'materialize-v1/materialized'/(split+'-audit.json')).read_bytes())
        ids=[r['example_id'] for r in rows[split]]
        core.require(len(ids)==count and len(set(ids))==count and ids==[a['example_id'] for a in audits[split]],
            'fixed all-row roster differs')
    def pair_at(split,index):return trainer.checked_pair(rows[split][index],tokenizer,audits[split][index],arm)
    return rows,pair_at


def worker(phase,path,digest):
    revision,r=barrier(path,digest);dependencies(phase,digest)
    output=ROOT/(phase+'-v1');core.require(not output.exists(),'no overwrite or resume')
    with configured():
        guard=paired.PhaseGuard(phase);envelope=guard(force=True);output.mkdir()
        core.write_new(output/'stage-manifest.json',dict(phase=phase,release_sha256=digest,revision=revision,envelope=envelope))
        try:
            arm=phase[-1];model,tokenizer=trainer.load_model(r,arm)
            cap=core.read_pinned(pilot.ROOT/'capacity-v1/probe/capacity_report.json',CAPACITY_SHA)
            expected=next(p['initial_adapter'] for p in cap['probes'] if p['arm']==arm)
            core.require(trainer.train.trainable_fingerprint(model)==expected,'original SFT initialization drift')
            rows,pair_at=data(arm,tokenizer)
            if phase.startswith('reference-'):
                trainer.reference_cache(model,rows,pair_at,output/'reference',arm,guard)
            else:
                # Reference seal must be included in its normally exited stage.
                seal=verify_stage('reference-'+arm,digest);ref=ROOT/('reference-'+arm+'-v1/reference')
                trainer.fit(model,tokenizer,rows,pair_at,ref,seal['files_sha256']['reference/COMPLETE.json'],
                    output/'training',arm,guard)
            guard(force=True);barrier(path,digest,revision);core.seal_stage(output,phase,digest)
        except BaseException as exc:
            core.write_new(output/'FAILED.json',dict(error_type=type(exc).__name__,error=str(exc)));raise


def supervise(path,digest):
    revision,r=barrier(path,digest)
    core.require(not ROOT.exists() and all(core.props(unit(p)).get('LoadState')=='not-found' for p in PHASES),
        'duplicate preference training forbidden')
    ROOT.mkdir(parents=True);core.write_new(ROOT/'COORDINATOR.json',dict(release_sha256=digest,revision=revision,
        phases=list(PHASES),phase_seconds=SECONDS,retries=0))
    completed=[];active=None
    try:
        for phase in PHASES:
            barrier(path,digest,revision);dependencies(phase,digest)
            (ROOT/'tmp'/phase).mkdir(parents=True);(ROOT/'runtime-cache'/phase).mkdir(parents=True)
            active=phase;subprocess.run(command(phase,path,digest),check=True,timeout=30)
            deadline=time.monotonic()+SECONDS[phase]+300
            while True:
                props=core.props(unit(phase));core.status_write(ROOT/'STATUS.json',dict(phase=phase,
                    completed_phases=completed,checked=time.time()))
                if props.get('SubState')=='exited' or props.get('ActiveState') in ('failed','inactive'):
                    core.require(core.normal_exit(props),'child did not exit normally: '+phase)
                    output=ROOT/(phase+'-v1');core.verify_stage(output,phase,digest)
                    manifest=json.loads((output/'stage-manifest.json').read_bytes())
                    core.require(manifest['revision']==revision and manifest['release_sha256']==digest,'worker binding differs')
                    cleanup=paired.terminal_group(props,manifest['envelope']['cgroup'],unit(phase))
                    core.write_new(ROOT/(phase+'-VERIFIED_COMPLETE.json'),dict(status='complete',release_sha256=digest,
                        complete_sha256=core.sha_file(output/'STAGE_COMPLETE.json'),exit={k:props[k] for k in
                        ('Result','ExecMainCode','ExecMainStatus','MainPID','SubState')},**cleanup))
                    subprocess.run(['systemctl','--user','stop',unit(phase)],check=True,timeout=30)
                    completed.append(phase);active=None;break
                core.require(time.monotonic()<deadline,'phase deadline exceeded');time.sleep(20)
        barrier(path,digest,revision)
        for phase in PHASES:verify_stage(phase,digest)
        arms={a:json.loads((ROOT/('train-'+a+'-v1/training/training_summary.json')).read_bytes()) for a in ('C','H')}
        core.require(all(v['completed_examples']==19199 and v['validation_examples']==4365
            and v['identity_examples']==10 and v['actual_fit'] and v['reference_immutable'] for v in arms.values())
            and arms['C']['order_sha256']==arms['H']['order_sha256'],'paired full traversal differs')
        report=dict(status='complete',decision='ready_for_inference',arms=arms,completed_examples=38398,
            total_examples=38398,actual_fit=True,performance_measured=False,model_promotion=False,
            educational_benefit_established=False,development_gate=r['development_gate'])
        core.write_new(ROOT/'REPORT.json',report)
        core.write_new(ROOT/'VERIFIED_COMPLETE.json',dict(status='complete',version=VERSION,release_sha256=digest,
            decision='ready_for_inference',model_promotion=False,phases={p:core.sha_file(ROOT/(p+'-VERIFIED_COMPLETE.json')) for p in PHASES},
            files_sha256={'REPORT.json':core.sha_file(ROOT/'REPORT.json')}))
    except BaseException as exc:
        if active:subprocess.run(['systemctl','--user','stop',unit(active)],check=True,timeout=30)
        core.write_new(ROOT/'COORDINATOR_FAILED.json',dict(error_type=type(exc).__name__,error=str(exc),completed=completed));raise


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('preflight','worker','supervise'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha',required=True)
    a=p.parse_args();path=a.release.absolute()
    if a.mode=='preflight':barrier(path,a.release_sha);print('preflight passed')
    elif a.mode=='worker':worker(a.phase,path,a.release_sha)
    else:supervise(path,a.release_sha)


if __name__=='__main__':main()
