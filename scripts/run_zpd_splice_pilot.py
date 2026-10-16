"""Bounded all-row splice reconstruction/token audit and no-fit GPU probe."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import time

from scripts import run_zpd_paired_history as paired
from scripts import run_zpd_edit_balanced as balanced
from scripts import run_zpd_edit_balanced_diagnosis as diagnosis
from scripts import zpd_splice_codec as codec
from scripts import train_zpd_paired_history as train

core=paired.core
PROJECT=core.PROJECT
ROOT=PROJECT/'outputs/zpd-splice-pilot-20261017'
UNIT_PREFIX='zpd-splice-pilot-20261017-v1'
PHASES=('materialize','capacity')
SECONDS=dict(materialize=7200,capacity=3600)
PARENT=diagnosis.ROOT
PARENT_SHA='93e29252d0dc27fe502a9486199484e28f0085fc2386da0d406f9a76a0f91391'
PARENT_RELEASE='822ef91a490204af2c37492975871b08e10572f420f73614daee2f854de21de9'
VERSION='splice_representation_capacity_pilot_v1'
REQUIRED={'scripts/zpd_splice_codec.py','scripts/run_zpd_splice_pilot.py',
          'tests/test_zpd_splice_pilot.py','analysis_protocols/zpd-splice-pilot-20261017.md'}
COUNTS=dict(train=19199,valid=4365)


def unit(phase):
    core.require(phase in (*PHASES,'coordinator'),'fixed phase required')
    return UNIT_PREFIX+'-'+phase+'.service'


def predecessor():
    from scripts.watch_zpd_completion import verify_terminal
    outer=core.read_pinned(PARENT/'VERIFIED_COMPLETE.json',PARENT_SHA)
    core.require(outer['release_sha256']==PARENT_RELEASE,'diagnosis release differs')
    verify_terminal(PARENT,outer)
    p=core.props('zpd-edit-balanced-diagnosis-20261017-v1-coordinator.service')
    core.require(core.normal_exit(p) and p.get('ControlGroup')=='','diagnosis not normally finished')
    core.require(not list(PARENT.rglob('*FAILED*.json')),'diagnosis failure marker')
    diagnosis.load_parent(diagnosis.PARENT,live=True)
    return balanced.verify_reuse()


def barrier(path,digest,revision=None):
    own=Path(__file__).resolve().parents[1]
    current=core.clean_source()
    core.require(Path.cwd().resolve()==own and path.resolve()==path and path.is_relative_to(own)
        and (revision is None or current==revision),'clean fixed snapshot required')
    r=core.read_pinned(path,digest)
    core.require(r['version']==VERSION and r['family_path']==str(ROOT)
        and r['predecessor_release_sha256']==PARENT_RELEASE and r['predecessor_complete_sha256']==PARENT_SHA
        and r['phases']==list(PHASES) and r['phase_seconds']==SECONDS and r['counts']==COUNTS
        and r['caps']==train.CAPS and r['seed']==2027 and r['codec']==codec.VERSION
        and r['config']==train.CONFIG and r['lora']==train.LORA,'fixed pilot contract differs')
    for key in ('fitting','generation','private_evaluation','filtering','truncation','retry','model_promotion'):
        core.require(r[key] is False,'pilot scope expanded: '+key)
    core.require(REQUIRED<=set(r['source_sha256']),'missing pilot sources')
    for name,pin in r['source_sha256'].items():
        p=own/name
        core.require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and p.resolve()==p and core.sha_file(p)==pin,'source drift: '+name)
    paired.verify_base_model(r)
    predecessor()
    return current,r


def rows(root,split):
    return {a:train._read_rows(root/(split+'-'+a+'.jsonl')) for a in train.ARMS}


def transform(c,h,tokenizer):
    """Return all records, no filter; hold rather than truncate an overflow."""
    core.require([r['example_id'] for r in c]==[r['example_id'] for r in h], 'paired input order differs')
    converted={a:[] for a in train.ARMS}; audits=[]; overflow=[]
    for left,right in zip(c,h,strict=True):
        core.require(left['current_code']==right['current_code'] and left['target_code']==right['target_code'],
            'paired input current/target differs')
        audit=dict(example_id=left['example_id'],target_raw_sha256=train.sha(left['target_code'].encode()),
                   target_normalized_sha256=train.sha(left['target_code'].rstrip().encode()),arms={})
        for a,row in zip(train.ARMS,(left,right),strict=True):
            new=codec.convert(row);converted[a].append(new)
            old=train.encode_record(row,tokenizer); enc=train.encode_record(new,tokenizer)
            audit['arms'][a]=dict(old_prompt_tokens=old['prompt_tokens'],old_target_tokens=old['output_tokens'],
                new_prompt_tokens=enc['prompt_tokens'],new_target_tokens=enc['output_tokens'],
                full_tokens=enc['full_tokens'],patch_sha256=train.sha(new['target_code'].encode()))
            if enc['prompt_tokens']>4096 or enc['output_tokens']>4096 or enc['full_tokens']>8192:
                overflow.append(dict(example_id=row['example_id'],arm=a,**audit['arms'][a]))
        core.require(converted['C'][-1]['target_code']==converted['H'][-1]['target_code'],'paired patch differs')
        audits.append(audit)
    return converted,audits,overflow


def materialize(r,output):
    old=balanced.verify_reuse();target=output/'materialized';target.mkdir(exist_ok=False)
    tokenizer=paired._tokenizer(r);started=time.monotonic();done=0;summary={};all_overflow=[]
    for split,count in COUNTS.items():
        original=rows(balanced.MATERIALIZED,split)
        core.require(len(original['C'])==len(original['H'])==count,'frozen row count differs')
        # Chunking bounds transient token features and provides truthful example progress.
        converted={a:[] for a in train.ARMS};audit=[];overflow=[]
        for offset in range(0,count,128):
            chunk,items,extra=transform(original['C'][offset:offset+128],original['H'][offset:offset+128],tokenizer)
            for a in train.ARMS:converted[a].extend(chunk[a])
            audit.extend(items);overflow.extend(extra);done+=len(items)
            core.status_write(output/'STATUS.json',dict(phase='materialize',completed_examples=done,
                total_examples=sum(COUNTS.values()),elapsed_seconds=time.monotonic()-started))
        for a in train.ARMS:
            name=split+'-'+a+'.jsonl'
            with (target/name).open('xb') as stream:
                for row in converted[a]:stream.write(core.encoded(row))
            core.require(core.sha_file(balanced.MATERIALIZED/name)==old['files_sha256'][name],'old rows changed')
        core.write_new(target/(split+'-audit.json'),audit)
        if not overflow:
            result=train.paired_preflight(converted['C'],converted['H'],tokenizer)
            core.write_new(target/(split+'-token-preflight.json'),result['report'])
        all_overflow.extend(dict(split=split,**v) for v in overflow)
        summary[split]=dict(examples=count,all_roundtrips_exact=True,
            original_order_sha256=train.sha(train.encoded([row['example_id'] for row in original['C']])),
            old_target_tokens=sum(v['arms']['C']['old_target_tokens'] for v in audit),
            new_target_tokens=sum(v['arms']['C']['new_target_tokens'] for v in audit),
            max_new_target_tokens=max(v['arms']['C']['new_target_tokens'] for v in audit),
            max_new_prompt_tokens={a:max(v['arms'][a]['new_prompt_tokens'] for v in audit) for a in train.ARMS})
    report=dict(status='complete',decision='hold' if all_overflow else 'ready_for_capacity',counts=summary,
        overflow=all_overflow,filtered_examples=0,truncation=False,actual_fit=False,
        codec=codec.VERSION,reused_complete_sha256=balanced.REUSE_PINS['materialize-v1/materialized/COMPLETE.json'])
    core.write_new(target/'report.json',report)
    core.write_new(target/'COMPLETE.json',dict(status='complete',files_sha256={p.name:core.sha_file(p) for p in sorted(target.iterdir())}))
    return report


def paired_data(r):
    root=ROOT/'materialize-v1/materialized'
    paired.read_sealed(root,core.sha_file(root/'COMPLETE.json'))
    report=json.loads((root/'report.json').read_bytes())
    core.require(report['decision']=='ready_for_capacity' and not report['overflow'],'overflow blocks capacity')
    items=rows(root,'train');value=train.paired_preflight(items['C'],items['H'],paired._tokenizer(r))
    core.require(value['report']==json.loads((root/'train-token-preflight.json').read_bytes()),'feature recomputation differs')
    return value


@contextmanager
def configured():
    overrides=dict(FAMILY=ROOT,UNIT_PREFIX=UNIT_PREFIX,PHASES=PHASES,PHASE_SECONDS=SECONDS)
    old={k:getattr(paired,k) for k in overrides}
    for k,v in overrides.items():setattr(paired,k,v)
    try:yield
    finally:
        for k,v in old.items():setattr(paired,k,v)


def command(phase,path,digest):
    with configured():cmd=paired.command(phase,path,digest)
    return ['scripts.run_zpd_splice_pilot' if v=='scripts.run_zpd_paired_history' else v for v in cmd]


def verify_stage(phase,digest):
    cert=json.loads((ROOT/(phase+'-VERIFIED_COMPLETE.json')).read_bytes())
    core.require(cert['release_sha256']==digest and cert['cleanup_verified'] is True and core.normal_exit(cert['exit'])
        and cert['complete_sha256']==core.sha_file(ROOT/(phase+'-v1/STAGE_COMPLETE.json')),'certified child required')
    return core.verify_stage(ROOT/(phase+'-v1'),phase,digest)


def worker(phase,path,digest):
    revision,r=barrier(path,digest)
    core.require(phase in PHASES,'fixed worker required')
    if phase=='capacity':verify_stage('materialize',digest)
    output=ROOT/(phase+'-v1');core.require(not output.exists(),'duplicate worker forbidden')
    with configured():
        guard=paired.PhaseGuard(phase);state=guard(force=True);output.mkdir()
        core.write_new(output/'stage-manifest.json',dict(phase=phase,release_sha256=digest,revision=revision,envelope=state))
        try:
            from importlib.metadata import version
            for package,expected in r['training_versions'].items():
                core.require(version(package)==expected,'training runtime drift: '+package)
            if phase=='materialize':materialize(r,output)
            else:
                value=train.capacity_probe(paired_data(r),base_model=r['base_model'],output_dir=output/'probe',seed=2027)
                core.require(value['status']=='passed' and not value['actual_fit'] and value['optimizer_steps']==0
                    and not value['published_adapter'],'no-fit probe contract differs')
            guard(force=True);barrier(path,digest,revision);core.seal_stage(output,phase,digest)
        except BaseException as exc:
            core.write_new(output/'FAILED.json',dict(error_type=type(exc).__name__,error=str(exc)));raise


def supervise(path,digest):
    revision,r=barrier(path,digest)
    core.require(not ROOT.exists() and all(core.props(unit(p)).get('LoadState')=='not-found' for p in PHASES),
        'duplicate pilot forbidden')
    ROOT.mkdir(parents=True);core.write_new(ROOT/'COORDINATOR.json',dict(release_sha256=digest,revision=revision,retries=0))
    completed=[];active=None
    try:
        for phase in PHASES:
            barrier(path,digest,revision)
            if phase=='capacity' and json.loads((ROOT/'materialize-v1/materialized/report.json').read_bytes())['decision']=='hold':break
            for prior in completed:verify_stage(prior,digest)
            (ROOT/'tmp'/phase).mkdir(parents=True);(ROOT/'runtime-cache'/phase).mkdir(parents=True)
            active=phase;subprocess.run(command(phase,path,digest),check=True,timeout=30)
            deadline=time.monotonic()+SECONDS[phase]+300
            while True:
                props=core.props(unit(phase))
                core.status_write(ROOT/'STATUS.json',dict(phase=phase,completed_phases=completed,checked=time.time()))
                if props.get('SubState')=='exited' or props.get('ActiveState') in ('failed','inactive'):
                    core.require(core.normal_exit(props),'child did not exit normally')
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
        for phase in completed:verify_stage(phase,digest)
        m=json.loads((ROOT/'materialize-v1/materialized/report.json').read_bytes())
        cap=json.loads((ROOT/'capacity-v1/probe/capacity_report.json').read_bytes()) if 'capacity' in completed else None
        summary=dict(status='complete',decision='ready_for_training' if cap else 'hold',materialization=m,capacity=cap,
            completed_examples=sum(COUNTS.values()),total_examples=sum(COUNTS.values()),actual_fit=False,
            model_promotion=False,performance_measured=False,educational_benefit_established=False)
        core.write_new(ROOT/'REPORT.json',summary)
        core.write_new(ROOT/'VERIFIED_COMPLETE.json',dict(status='complete',release_sha256=digest,
            phases={p:core.sha_file(ROOT/(p+'-VERIFIED_COMPLETE.json')) for p in completed},
            files_sha256={'REPORT.json':core.sha_file(ROOT/'REPORT.json')},decision=summary['decision'],model_promotion=False))
    except BaseException as exc:
        if active:subprocess.run(['systemctl','--user','stop',unit(active)],check=True,timeout=30)
        core.write_new(ROOT/'COORDINATOR_FAILED.json',dict(error_type=type(exc).__name__,error=str(exc),completed=completed));raise


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('preflight','worker','supervise'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha',required=True)
    a=p.parse_args();path=a.release.absolute()
    if a.mode=='preflight':barrier(path,a.release_sha);print('preflight passed; no candidate execution or fit')
    elif a.mode=='worker':worker(a.phase,path,a.release_sha)
    else:supervise(path,a.release_sha)


if __name__=='__main__':main()
