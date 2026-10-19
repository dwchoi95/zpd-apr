"""Frozen conditional-likelihood selection then exact-cache assessment.

Selection opens only public candidate inputs and model files. Private vectors
are opened by a separate child only after normal selection exit and sealing.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import time

from scripts import run_zpd_transition_generation as core
from scripts import run_zpd_deanchored_diagnosis as parent
from scripts import recover_zpd_transition_evaluation as recovery
from scripts import diagnose_zpd_transition_failure as diag
from scripts import zpd_likelihood_selection as method

PROJECT=core.PROJECT
FAMILY=PROJECT/'outputs/zpd-likelihood-selection-20261020'
BANK=parent.PARENT
DIAGNOSIS=parent.ROOT
UNIT_PREFIX='zpd-likelihood-selection-20261020-v1'
VERSION=method.VERSION
PHASES=('selection','assessment')
PARENT_RELEASE='b3f1a6a52f97a6b3ff3bd33f8fbec950131311905a79ec4a3b654d9baa13a1ea'
PARENT_COMPLETE='7b26e10bb71e75213fe5294002cd6034eb238de60f9aa2f53ba36fec3cc2a710'
PUBLIC_FILES=('generation-v1/revision-inputs.json','generation-v1/attempts.json',
    'public-v1/predictions.json','public-v1/public-vectors.json','public-v1/scoring.json')
REQUIRED={'scripts/run_zpd_likelihood_selection.py','scripts/zpd_likelihood_selection.py',
    'tests/test_zpd_likelihood_selection.py','analysis_protocols/zpd-likelihood-selection-20261020.md'}


def contract():
    return dict(version=VERSION,scoring='mean_logprob_all_target_tokens_including_eos',
        target_normalization='rstrip_separate_tokenization_then_one_eos',prompt='original_first_slot_full_source',
        max_prompt_tokens=4096,max_target_tokens=4096,max_total_tokens=8192,batch_size=1,
        chunk_tokens=32,quantization='nf4_double',dtype='bfloat16',attention='sdpa',seed=2027,
        adapter_arm_map=method.ROLES,public_constraint_changed=False,
        tie_fallback='original_C_joint_if_any_tied_source_unscorable',unavailable_public='original_C_joint',
        equal_likelihood='lexicographic_source_sha256',fitting=False,parameter_search=False,
        new_generation=False,new_execution=False,private_before_selection=False,model_promotion=False)


def verify_sources(path,digest):
    own=Path(__file__).resolve().parents[1];revision=core.clean_source()
    core.require(Path.cwd().resolve()==own and path.resolve()==path and path.is_relative_to(own),'clean shared snapshot required')
    r=core.read_pinned(path,digest)
    core.require(r['version']==VERSION and r['family_path']==str(FAMILY) and r['method']==contract()
        and r['examples']==320 and r['phases']==list(PHASES) and r['phase_seconds']==21600
        and r['parent_release_sha256']==PARENT_RELEASE and r['parent_complete_sha256']==PARENT_COMPLETE,
        'fixed scientific/lifecycle identity differs')
    base=core.read_pinned(own/'analysis_protocols/zpd-deanchored-diagnosis-release-20261020.json',PARENT_RELEASE)
    for n,pin in base['source_sha256'].items():
        if n not in ('scripts/watch_zpd_completion.py','tests/test_watch_zpd_completion.py'):
            core.require(r['source_sha256'].get(n)==pin,'frozen source changed: '+n)
    bank=core.read_pinned(own/'analysis_protocols/zpd-deanchored-revision-release-20261020.json',parent.PARENT_RELEASE)
    for k in ('model_sha256','base_model','adapter_C','adapter_H','development_gate','testcase_sha256'):
        core.require(r[k]==bank[k],'frozen models/gate/testcases changed: '+k)
    core.require(REQUIRED<=set(r['source_sha256']),'new source pins absent')
    for n,pin in r['source_sha256'].items():
        p=own/n;core.require(not Path(n).is_absolute() and '..' not in Path(n).parts and p.resolve()==p
            and core.sha_file(p)==pin,'source drift: '+n)
    return r,revision


def authenticate(r):
    from scripts.watch_zpd_completion import verify_terminal
    parent.load_parent(BANK,live=True)
    outer=core.read_pinned(DIAGNOSIS/'VERIFIED_COMPLETE.json',PARENT_COMPLETE)
    core.require(outer['release_sha256']==PARENT_RELEASE,'diagnosis release differs');verify_terminal(DIAGNOSIS,outer)
    core.require(core.normal_exit(core.props(parent.UNIT_PREFIX+'-coordinator.service')),'diagnosis coordinator normal exit required')
    for suffix in ('coordinator','worker'):
        p=core.props(parent.UNIT_PREFIX+'-'+suffix+'.service')
        core.require(p.get('MainPID')=='0' and p.get('ControlGroup')=='','diagnosis still active')
    cert=core.read_pinned(DIAGNOSIS/'WORKER_VERIFIED_COMPLETE.json',outer['worker_certificate_sha256'])
    group=cert['recorded_control_group']
    core.require(group.startswith('/user.slice/') and '..' not in Path(group).parts
        and group.endswith('/'+parent.UNIT) and not (Path('/sys/fs/cgroup')/group.lstrip('/')).exists(),
        'diagnosis worker cgroup not removed')
    for n,pin in r['input_sha256'].items():
        core.require(not Path(n).is_absolute() and '..' not in Path(n).parts and core.sha_file(PROJECT/n)==pin,'input drift: '+n)


def public_inputs(r):
    return [core.read_pinned(BANK/n,r['input_sha256'][str((BANK/n).relative_to(PROJECT))]) for n in PUBLIC_FILES]


def tokenize(bundle,r):
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(r['base_model'],local_files_only=True,use_fast=True)
    encoded={t['task_id']:method.encode_task(t,tok) for t in bundle['tasks']}
    report=dict(tasks=len(encoded),scorable=sum(e['fits'] for e in encoded.values()),
        overflow=sum(not e['fits'] for e in encoded.values()),examples=bundle['examples'],truncation=False,
        tokens={k:dict(prompt_tokens=len(e['prompt_ids']),target_tokens=len(e['target_ids']),
            fits=e['fits'],token_sha256=e['token_sha256']) for k,e in encoded.items()})
    return encoded,report


def models_pinned(r):
    for n,pin in r['model_sha256'].items():core.require(core.sha_file(Path(n))==pin,'model/tokenizer drift: '+n)


def activate(model,role):
    model.set_adapter(role);model.requires_grad_(False);model.eval()
    core.require(model.active_adapter==role and not model.training
        and not any(p.requires_grad for p in model.parameters()),'inference-only adapter required')


def selection(r,output,digest):
    for p,v in r['score_versions'].items():core.require(version(p)==v,'scoring package drift: '+p)
    models_pinned(r);data=public_inputs(r);bundle=method.prepare(*data)
    core.require(core.sha(core.encoded(bundle))==r['bundle_sha256'],'public task preparation drift')
    encoded,tokens=tokenize(bundle,r)
    core.require(core.sha(core.encoded(tokens))==r['tokenization_sha256'],'scoring tokenization drift')
    core.write_new(output/'tokenization.json',tokens)
    import torch
    from transformers import AutoModelForCausalLM,BitsAndBytesConfig,set_seed
    from peft import PeftModel
    core.require(torch.cuda.is_available() and torch.cuda.is_bf16_supported(),'CUDA BF16 required')
    set_seed(2027)
    base=AutoModelForCausalLM.from_pretrained(r['base_model'],local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True,bnb_4bit_compute_dtype=torch.bfloat16),
        torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa')
    model=PeftModel.from_pretrained(base,r['adapter_C'],adapter_name='C',is_trainable=False,local_files_only=True)
    model.load_adapter(r['adapter_H'],adapter_name='H',is_trainable=False,local_files_only=True)
    model.config.use_cache=False;activate(model,'C');role='C'
    results={};started=time.monotonic();needed={row['original']['example_id']:set() for row in bundle['rows']}
    for t in bundle['tasks']:needed[t['example_id']].add(t['task_id'])
    core.write_new(output/'inference.json',dict(seed=2027,versions=r['score_versions'],adapter_arm_map=method.ROLES,
        training=False,model_promotion=False,private_assessment_accessed=False))
    # Stable recipient/arm/source order from the sealed public bundle, no
    # score-dependent retries, batching or candidate exclusions.
    with (output/'scores.jsonl').open('xb') as journal:
        for task in bundle['tasks']:
            tid=task['task_id'];e=encoded[tid]
            if role!=task['adapter_role']:role=task['adapter_role'];activate(model,role)
            value=dict(status='scored' if e['fits'] else 'overflow',mean_logprob=method.mean_logprob(model,e) if e['fits'] else None,
                token_sha256=e['token_sha256'],adapter_role=role,prompt_sha256=task['prompt_sha256'],source_sha256=task['source_sha256'])
            results[tid]=value;journal.write(core.encoded(dict(task_id=tid,**value)));journal.flush();os.fsync(journal.fileno())
            core.status_write(output/'STATUS.json',dict(phase='likelihood_selection',completed_examples=sum(v<=results.keys() for v in needed.values()),
                total_examples=320,completed_candidates=len(results),total_candidates=len(bundle['tasks']),
                elapsed_seconds=time.monotonic()-started,overflow=sum(v['status']=='overflow' for v in results.values())))
            core.envelope('selection')
    predictions=method.choose_scored(bundle,results);pin=core.write_new(output/'predictions.json',predictions)
    core.write_new(output/'PREDICTIONS_COMPLETE.json',dict(status='complete',release_sha256=digest,
        predictions_sha256=pin,examples=320,choices=1280,private_assessment_accessed=False,parameter_search=False,
        changed_choices=dict(Counter(p['arm'] for p in predictions if p['diagnostic']['choice_changed']))))
    models_pinned(r)


@contextmanager
def configured():
    values=dict(FAMILY=FAMILY,PHASES=PHASES,unit=lambda phase:UNIT_PREFIX+'-'+phase+'.service',
        limits=lambda phase:(64*2**30,1024,'infinity') if phase=='selection' else (32*2**30,128,str(32*2**30)))
    old={k:getattr(core,k) for k in values}
    for k,v in values.items():setattr(core,k,v)
    try:yield
    finally:
        for k,v in old.items():setattr(core,k,v)


def worker(phase,path,digest):
    r,revision=verify_sources(path,digest)
    with configured():
        state=core.envelope(phase);output=FAMILY/(phase+'-v1');output.mkdir(exist_ok=False)
        core.write_new(output/'stage-manifest.json',dict(phase=phase,release_sha256=digest,revision=revision,envelope=state,started=time.time()))
        try:
            if phase=='selection':selection(r,output,digest)
            else:
                cert=diag._read(FAMILY/'selection-VERIFIED_COMPLETE.json')
                core.require(cert['release_sha256']==digest and core.normal_exit(cert['exit']) and cert['cleanup_verified']
                    and cert['complete_sha256']==core.sha_file(FAMILY/'selection-v1/STAGE_COMPLETE.json'),'selection normal exit and seal required')
                core.verify_stage(FAMILY/'selection-v1','selection',digest)
                seal=diag._read(FAMILY/'selection-v1/PREDICTIONS_COMPLETE.json')
                core.require(seal['private_assessment_accessed'] is False and seal['release_sha256']==digest,'private-before-selection barrier')
                predictions=core.read_pinned(FAMILY/'selection-v1/predictions.json',seal['predictions_sha256'])
                inputs,attempts,old,masks,_=public_inputs(r);cached=[]
                for directory in (BANK/'private-v1/evaluation',DIAGNOSIS/'run-v1'):
                    p=directory/'vectors.json';cached+=core.read_pinned(p,r['input_sha256'][str(p.relative_to(PROJECT))])
                vectors=diag.deserialize_vectors(cached);audit=diag.assess(inputs,attempts,old,vectors,masks)
                parent.verify_selected(audit)
                core.require(len(vectors)==1925 and audit['coverage']['missing_unique_source_tasks']==0,'exact full-bank cache required')
                from scripts.run_zpd_anchor_tie import assess_cache
                labels,report=assess_cache(inputs,predictions,vectors)
                report.update(layout_variant=VERSION,release_sha256=digest,selection_method=contract(),
                    parent_counts={a:dict(stable_ac=parent.SELECTED[a],stable_regression=parent.REGRESSIONS[a],unknown=parent.UNKNOWN[a]) for a in diag.ARMS},
                    independent_confirmation=False,new_test_execution=False)
                core.write_new(output/'labels.json',labels);core.write_new(output/'report.json',report)
            verify_sources(path,digest);core.envelope(phase);core.seal_stage(output,phase,digest)
        except BaseException as exc:
            core.write_new(output/'FAILED.json',dict(error_type=type(exc).__name__,error=str(exc)));raise


def command(phase,path,digest):
    memory,tasks,address=(64*2**30,1024,'infinity') if phase=='selection' else (32*2**30,128,str(32*2**30))
    props=dict(MemoryMax=str(memory),LimitAS=address,TasksMax=str(tasks),RuntimeMaxSec='21600',KillMode='control-group',
        KillSignal='SIGKILL',SendSIGKILL='yes',Restart='no',OOMPolicy='stop',Delegate='no',RemainAfterExit='yes',
        MemoryAccounting='yes',TasksAccounting='yes',WorkingDirectory=str(path.parents[1]),
        StandardOutput='append:'+str(FAMILY/(phase+'.log')),StandardError='append:'+str(FAMILY/(phase+'.log')))
    cmd=['/usr/bin/systemd-run','--user','--unit='+UNIT_PREFIX+'-'+phase+'.service','--service-type=exec']
    cmd+=['--property='+k+'='+v for k,v in props.items()]
    env=dict(PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
        TMPDIR=str(PROJECT/'.staging/likelihood-selection-20261020-v1/tmp'),
        CUDA_CACHE_PATH=str(PROJECT/'.staging/likelihood-selection-20261020-v1/cuda-cache'),
        TRITON_CACHE_DIR=str(PROJECT/'.staging/likelihood-selection-20261020-v1/triton-cache'),
        TORCH_HOME=str(PROJECT/'.cache/torch'),HF_HOME=str(PROJECT/'.cache/huggingface'))
    cmd+=['--setenv='+k+'='+v for k,v in env.items()]
    return cmd+[str(PROJECT/'.runtime/fse-env/bin/python'),'-m','scripts.run_zpd_likelihood_selection','worker',
        '--phase',phase,'--release',str(path),'--release-sha',digest]


def supervise(path,digest):
    r,revision=verify_sources(path,digest);authenticate(r)
    core.require(not FAMILY.exists(),'fresh family required; no retry')
    units=[UNIT_PREFIX+'-'+p+'.service' for p in PHASES]
    core.require(all(core.props(u).get('LoadState')=='not-found' for u in units),'duplicate child unit')
    FAMILY.mkdir();core.write_new(FAMILY/'COORDINATOR.json',dict(release_sha256=digest,revision=revision,started=time.time(),retries=0))
    current=None
    try:
        certs={}
        for phase in PHASES:
            current=UNIT_PREFIX+'-'+phase+'.service'
            core.status_write(FAMILY/'STATUS.json',dict(phase=phase,completed_examples=0,total_examples=320))
            subprocess.run(command(phase,path,digest),check=True,timeout=30);deadline=time.monotonic()+21900
            while True:
                p=core.props(current)
                if p.get('SubState')=='exited' or p.get('ActiveState') in ('failed','inactive'):
                    core.require(core.normal_exit(p),'child normal exit required')
                    output=FAMILY/(phase+'-v1');core.verify_stage(output,phase,digest)
                    manifest=diag._read(output/'stage-manifest.json');group=recovery.terminal_group(p,manifest['envelope']['cgroup'],current)
                    certs[phase]=core.write_new(FAMILY/(phase+'-VERIFIED_COMPLETE.json'),dict(status='complete',release_sha256=digest,
                        complete_sha256=core.sha_file(output/'STAGE_COMPLETE.json'),
                        exit={k:p[k] for k in ('Result','ExecMainCode','ExecMainStatus','MainPID','SubState')},**group))
                    subprocess.run(['/usr/bin/systemctl','--user','stop',current],check=True,timeout=30);current=None;break
                core.require(time.monotonic()<deadline,'phase deadline');time.sleep(10)
            verify_sources(path,digest)
        authenticate(r);report=diag._read(FAMILY/'assessment-v1/report.json');pin=core.write_new(FAMILY/'REPORT.json',report)
        core.status_write(FAMILY/'STATUS.json',dict(phase='complete',completed_examples=320,total_examples=320))
        core.write_new(FAMILY/'VERIFIED_COMPLETE.json',dict(status='complete',layout_variant=VERSION,release_sha256=digest,
            phases=certs,files_sha256={'REPORT.json':pin},parent_complete_sha256=PARENT_COMPLETE,model_promotion=False,
            provisional_until_coordinator_normal_exit=True))
    except BaseException as exc:
        if current:subprocess.run(['/usr/bin/systemctl','--user','stop',current],check=True,timeout=30)
        core.write_new(FAMILY/'COORDINATOR_FAILED.json',dict(error_type=type(exc).__name__,error=str(exc),retries=0));raise


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('mode',choices=('prepare','preflight','supervise','worker'))
    p.add_argument('--phase',choices=PHASES);p.add_argument('--release',type=Path,required=True);p.add_argument('--release-sha',required=True)
    a=p.parse_args();path=a.release.resolve()
    if a.mode=='prepare':
        r=core.read_pinned(path,a.release_sha);b=method.prepare(*public_inputs(r));_,t=tokenize(b,r)
        print(json.dumps(dict(bundle_sha256=core.sha(core.encoded(b)),tokenization_sha256=core.sha(core.encoded(t)),
            tasks=t['tasks'],scorable=t['scorable'],overflow=t['overflow'])));return
    if a.mode=='worker':worker(a.phase,path,a.release_sha)
    elif a.mode=='supervise':supervise(path,a.release_sha)
    else:
        r,_=verify_sources(path,a.release_sha);authenticate(r);models_pinned(r)
        b=method.prepare(*public_inputs(r));_,t=tokenize(b,r)
        core.require(core.sha(core.encoded(b))==r['bundle_sha256'] and core.sha(core.encoded(t))==r['tokenization_sha256'],'preparation drift')
        print(dict(preflight='passed',tasks=t['tasks'],scorable=t['scorable'],overflow=t['overflow']))


if __name__=='__main__':main()
