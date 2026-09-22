"""Bounded CPU development family; no fresh test/generation/runtime mutation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from importlib.metadata import version

from scripts.zpd_repair_fit import read_jsonl, load_inputs, evaluate, history
from scripts.zpd_repair_pairwise import fit_report, select_model
from src.repair.pilot_ranker import select, TwoChannelCoefficients, features
from src.repair.pilot_contracts import source_hash


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def verify_evaluation(path):
    marker=read(path/'COMPLETE.json')
    if marker['status']!='fully_executed' or marker['development_only'] is not True:
        raise ValueError('incomplete development labels')
    if set(marker['files_sha256'])!={'manifest.json','completions.jsonl','labels.jsonl'}:
        raise ValueError('incomplete execution seal')
    for name,value in marker['files_sha256'].items():
        if sha(path/name)!=value:
            raise ValueError('execution artifact changed')


def comparisons(group):
    result={}
    for arm in ('C','H','U'):
        controls=['first_attempt','old_'+arm]+(['pairwise_C','pairwise_U'] if arm=='H' else [])
        for control in controls:
            left=group['pairwise_'+arm]['predictions'];right=group[control]['predictions']
            bounds=[]
            for a,b in zip(left,right,strict=True):
                if a['example_id']!=b['example_id']:
                    raise ValueError('comparison row mismatch')
                bounds.append((0.,0.) if a['candidate_id']==b['candidate_id'] else
                    (a['utility']-b['utility_upper_bound'],a['utility_upper_bound']-b['utility']))
            result[arm+'-'+control]=dict(lower=sum(a for a,b in bounds)/len(bounds),
                upper=sum(b for a,b in bounds)/len(bounds),examples=len(bounds))
    return result


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('original-root','replication-root','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise ValueError('preserve previous family outputs')
    if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
        raise ValueError('clean source snapshot required')
    old=args.original_root/'run-v1'; rep=args.replication_root/'run-v1'
    for path in (args.original_root/'prepared-v2',args.replication_root/'prepared-v1'):
        for name,value in read(path/'manifest.json')['output_sha256'].items():
            if sha(path/name)!=value:
                raise ValueError('prepared input changed')
    verify_evaluation(old/'evaluation')
    report=read(old/'fit'/'report.json')
    if sha(old/'fit'/'report.json')!=read(old/'fit'/'COMPLETE.json')['report_sha256']:
        raise ValueError('parent report seal')
    original_obs=read_jsonl(args.original_root/'prepared-v2'/'observations.jsonl')
    original_banks=read_jsonl(old/'generation'/'banks.jsonl')
    original_labels=read_jsonl(old/'evaluation'/'labels.jsonl')
    for key,path in [('observations',args.original_root/'prepared-v2'/'observations.jsonl'),
                     ('banks',old/'generation'/'banks.jsonl'),('labels',old/'evaluation'/'labels.jsonl')]:
        if sha(path)!=report['input_sha256'][key]:
            raise ValueError('original fitting inputs changed')
    examples,banks,labels=load_inputs(original_obs,original_banks,original_labels)
    if read(old/'evaluation'/'manifest.json')['bank_seals']!={k:b.seal_sha256 for k,b in banks.items()}:
        raise ValueError('original bank seal mapping')
    if sum(x.split=='train' for x in examples)!=64 or sum(x.split=='valid' for x in examples)!=32:
        raise ValueError('original cohort size mismatch')
    if len({x.user_id for x in examples})!=96:
        raise ValueError('original user duplicates')
    # Build already-exposed diagnostic cohort, retaining only old TRAIN labels.
    train_obs=[r for r in original_obs if r['split']=='train']; train_ids={r['bank_id'] for r in train_obs}
    new_obs=read_jsonl(args.replication_root/'prepared-v1'/'observations.jsonl')
    if sha(args.replication_root/'prepared-v1'/'observations.jsonl')!=sha(rep/'predictions'/'observations.jsonl'):
        raise ValueError('wrong replication observations')
    if sha(old/'generation'/'banks.jsonl')!=read(old/'evaluation'/'manifest.json')['banks_sha256']:
        raise ValueError('evaluation bank changed')
    if len(new_obs)!=128 or len({r['user_id'] for r in new_obs})!=128 or any(r['split']!='valid' for r in new_obs):
        raise ValueError('diagnostic cohort size mismatch')
    if {r['user_id'] for r in new_obs}&{x.user_id for x in examples}:
        raise ValueError('diagnostic users overlap original cohort')
    args.output.mkdir(parents=True)
    inputs=[args.original_root/'prepared-v2'/'observations.jsonl',old/'generation'/'banks.jsonl',old/'evaluation'/'labels.jsonl',
        old/'fit'/'report.json',args.replication_root/'prepared-v1'/'observations.jsonl',rep/'banks.jsonl']
    manifest=dict(source_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        input_sha256={str(p):sha(p) for p in inputs},protocol_sha256=sha(Path('analysis_protocols/zpd-repair-pairwise-development-20260922.md')),
        started=time.time(),scope='exposed development only, no fresh test',
        runtime_versions={name:version(name) for name in ('numpy','scipy','scikit-learn')})
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    fitted=fit_report(examples,banks,labels)
    (args.output/'selection.json').write_text(json.dumps(fitted,indent=2,allow_nan=False)+'\n')
    (args.output/'SELECTION_COMPLETE.json').write_text(json.dumps(dict(selection_sha256=sha(args.output/'selection.json')))+'\n')
    print('18 fixed fits complete; original32 selection sealed',flush=True)
    verify_evaluation(rep/'evaluation')
    if sha(rep/'banks.jsonl')!=read(rep/'evaluation'/'manifest.json')['banks_sha256']:
        raise ValueError('replication evaluation bank changed')
    secondary,second_banks,second_labels=load_inputs(train_obs+new_obs,
        [r for r in original_banks if r['bank_id'] in train_ids]+read_jsonl(rep/'banks.jsonl'),
        [r for r in original_labels if r['bank_id'] in train_ids]+read_jsonl(rep/'evaluation'/'labels.jsonl'))
    if read(rep/'evaluation'/'manifest.json')['bank_seals']!={k:b.seal_sha256 for k,b in second_banks.items() if k not in train_ids}:
        raise ValueError('replication bank seal mapping')
    results={}
    for name,ex,bk,lb in [('selection_valid32',examples,banks,labels),('exposed_diagnostic128',secondary,second_banks,second_labels)]:
        group={}
        for arm in ('C','H','U'):
            model=fitted['selected'][arm]['model']
            group['pairwise_'+arm]=evaluate(ex,bk,lb,lambda x,b:select_model(model,x.observation,history(x,arm),b))
            cell=report['selected'][arm]
            group['old_'+arm]=evaluate(ex,bk,lb,lambda x,b:select(x.observation,b,history=history(x,arm),
                coefficients=TwoChannelCoefficients(**cell['coefficients']),risk_threshold=cell['risk_threshold'],minimum_gain=cell['minimum_gain']).selected_source_sha256)
        group['first_attempt']=evaluate(ex,bk,lb,lambda x,b:source_hash(b.attempts[0].source if b.attempts[0].status=='success' else b.current_source))
        group['noop']=evaluate(ex,bk,lb,lambda x,b:source_hash(b.current_source))
        results[name]=dict(arms=group,paired=comparisons(group))
    secondary_group=results['exposed_diagnostic128']['arms']
    baseline=secondary_group['first_attempt']['metrics']
    eligible=[arm for arm in ('C','H') if secondary_group['pairwise_'+arm]['metrics']['rr_lower_bound']>baseline['rr_lower_bound']
        and secondary_group['pairwise_'+arm]['metrics']['regression_rate_upper_bound']<=baseline['regression_rate_upper_bound']]
    decision=dict(next_family='new_frozen_development_replication' if eligible else 'collect_larger_training_banks',
        eligible_arms=eligible,not_confirmatory=True,no_grid_expansion=True)
    final=dict(results=results,decision=decision,selection_sha256=sha(args.output/'selection.json'),manifest_sha256=sha(args.output/'manifest.json'),
        diagnostic_labels_sha256=sha(rep/'evaluation'/'labels.jsonl'))
    (args.output/'report.json').write_text(json.dumps(final,indent=2,allow_nan=False)+'\n')
    (args.output/'COMPLETE.json').write_text(json.dumps(dict(report_sha256=sha(args.output/'report.json'),selection_sha256=sha(args.output/'selection.json')))+'\n')
    print(json.dumps(decision),flush=True)


if __name__=='__main__':
    main()
