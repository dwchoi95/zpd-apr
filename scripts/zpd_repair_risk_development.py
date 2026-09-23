"""Sealed, train-only larger-support/risk-filter development comparison.

Exactly six rankers and six risk models; no hyperparameter/model selection.
The three evaluated validation cohorts are exposed development data, never
confirmation. Their execution outcomes cannot enter the learner interfaces.
"""
from __future__ import annotations

import argparse
from collections import Counter
from importlib.metadata import version
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

from scripts.prepare_zpd_repair_next import verify_files as verify_prepared_files
from scripts.zpd_repair_evaluate import parse_bank
from scripts.zpd_repair_fit import Example, history, source
from scripts.zpd_repair_pairwise import select_model, training_data
from scripts.zpd_repair_pairwise_replication import _contrast, _summary, _value
from scripts.zpd_repair_replication import read, rows, sha, validate_labels, write
from src.repair.pilot_contracts import PilotObservation, canonical_hash, source_hash
from src.repair.pilot_ranker import features

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'analysis_protocols/zpd-repair-risk-development-20260923.md'
PRIMARY = 'train320_C_filtered'
REFERENCE_PAIR_WEIGHT = 1900
REFERENCE_CANDIDATE_WEIGHT = 467
EVALUATION_FILES = {'manifest.json','completions.jsonl','labels.jsonl'}


def prepared(path):
    manifest=read(path/'manifest.json')
    hashes=manifest['output_sha256']
    required={'observations.jsonl','requests.jsonl','exclusions.jsonl'}
    if not required<=set(hashes) or any(name not in required and not re.fullmatch(r'requests-[0-9]+\.jsonl',name) for name in hashes):
        raise ValueError('strict outcome-free preparation seal required')
    verify_prepared_files(path,hashes)
    return manifest,rows(path/'observations.jsonl')


def parse_examples(observations,bank_rows):
    """Label-free train/valid parser: no synthetic split relabeling adapter."""
    banks={}
    for row in bank_rows:
        if row['bank_id'] in banks:raise ValueError('duplicate bank')
        banks[row['bank_id']]=parse_bank(row)
    examples=[];ids=set();used=set();keys={}
    for row in observations:
        required={'example_id','user_id','split','bank_id','observation','donor_history','donor_user_id'}
        if set(row) not in (required,required|{'donor_example_id'}) or row['split'] not in ('train','valid'):
            raise ValueError('strict train/valid observation schema required')
        if row['example_id'] in ids:raise ValueError('duplicate example')
        ids.add(row['example_id']);used.add(row['bank_id'])
        raw=row['observation']
        if set(raw)!={'problem_id','current','prior'}:raise ValueError('observation allowlist')
        obs=PilotObservation(raw['problem_id'],source(raw['current']),tuple(source(h) for h in raw['prior']))
        donor=tuple(source(h) for h in row['donor_history'])
        if not obs.prior or len(donor)!=len(obs.prior) or row['donor_user_id']==row['user_id']:
            raise ValueError('matched nonempty different-user histories required')
        bank=banks[row['bank_id']]
        if bank.problem_id!=obs.problem_id or bank.current_source!=obs.current.source:
            raise ValueError('observation-bank mismatch')
        features(obs,bank.current_source,history=donor)
        if keys.setdefault(bank.key,bank.seal_sha256)!=bank.seal_sha256:
            raise ValueError('same-key bank conflict')
        examples.append(Example(row['example_id'],row['user_id'],row['split'],row['bank_id'],obs,donor))
    if not examples or used!=set(banks):raise ValueError('exact bank coverage required')
    return examples,banks


def _normalize_generation(config):
    result=dict(config)
    result['source_sha256']={('scripts/generate_zpd_repair_banks.py' if Path(key).name=='generate_zpd_repair_banks.py' else key):value
                             for key,value in config['source_sha256'].items()}
    return result


def verify_generation(preparation,run,bank_path,*,original=False):
    request_rows=rows(preparation/'requests.jsonl')
    chunks=[(run/'generation',preparation/'requests.jsonl')] if original else [
        (run/f'generation-{i}',preparation/f'requests-{i}.jsonl') for i in range((len(request_rows)+63)//64)]
    generated=[];configs=[];chunk_requests=[]
    for directory,request in chunks:
        marker=read(directory/'COMPLETE');manifest=read(directory/'manifest.json')
        if marker.get('banks_sha256')!=sha(directory/'banks.jsonl') or marker.get('manifest_sha256')!=sha(directory/'manifest.json'):
            raise ValueError('generation artifact seal mismatch')
        config=manifest['config'];bank_rows=rows(directory/'banks.jsonl');requests=rows(request)
        if manifest.get('generator_config_sha256')!=canonical_hash(config) or manifest.get('requests_sha256')!=sha(request):
            raise ValueError('generation config/request provenance mismatch')
        if marker.get('attempts')!=8*len(requests) or len(bank_rows)!=len(requests):
            raise ValueError('fixed generation attempt coverage mismatch')
        expected={r['bank_id']:r for r in requests}
        if len(expected)!=len(requests) or {r['bank_id'] for r in bank_rows}!=set(expected):
            raise ValueError('generation request bank coverage mismatch')
        for row in bank_rows:
            bank=parse_bank(row);request_row=expected[row['bank_id']]
            if bank.generator_config_sha256!=manifest['generator_config_sha256'] or bank.problem_id!=request_row['problem_id'] or bank.current_source.decode('utf-8')!=request_row['current_source']:
                raise ValueError('generated bank request/config mismatch')
            expected_seeds=[int(hashlib.sha256(f'{seed}|{row["bank_id"]}'.encode()).hexdigest()[:8],16) for seed in config['seeds']]
            if list(bank.seeds)!=expected_seeds:raise ValueError('derived per-bank generation seeds changed')
        generated.extend(bank_rows);configs.append(_normalize_generation(config));chunk_requests.extend(requests)
    if not configs or any(config!=configs[0] for config in configs) or chunk_requests!=request_rows or generated!=rows(bank_path):
        raise ValueError('merged bank/config/request mismatch')
    return configs[0]


def evaluation_metadata(directory,bank_path,banks,prep,*,production):
    """Read only evaluator metadata now; do not open labels or completions."""
    marker=read(directory/'COMPLETE.json')
    if marker.get('status')!='fully_executed' or marker.get('development_only') is not True or set(marker.get('files_sha256',{}))!=EVALUATION_FILES:
        raise ValueError('fully executed development evidence required')
    if marker['files_sha256']['manifest.json']!=sha(directory/'manifest.json'):
        raise ValueError('execution manifest hash mismatch')
    manifest=read(directory/'manifest.json');runtime=manifest['runtime']
    if manifest.get('development_only') is not True or manifest.get('banks_sha256')!=sha(bank_path) or manifest.get('bank_seals')!={key:bank.seal_sha256 for key,bank in banks.items()}:
        raise ValueError('execution bank binding mismatch')
    if manifest.get('runtime_sha256')!=canonical_hash(runtime):raise ValueError('runtime hash mismatch')
    if runtime.get('timeout_sec')!=2.5 or runtime.get('memory_limit_mb')!=2048 or runtime.get('case_workers')!=1 or list(runtime.get('block_workers',[]))!=[1,8,8,1]:
        raise ValueError('frozen execution settings mismatch')
    if production and (runtime.get('injected_runner') is not False or manifest.get('max_seconds')!=21600):
        raise ValueError('production sandbox/six-hour budget required')
    pids={bank.problem_id for bank in banks.values()}
    if set(manifest['testcase_files_sha256'])!=pids or set(manifest['universe_sha256'])!=pids:
        raise ValueError('testcase universe coverage mismatch')
    for pid in pids:
        if prep['data_sha256'].get(pid+'/testcases.jsonl')!=manifest['testcase_files_sha256'][pid]:
            raise ValueError('testcase data differs from preparation')
    return manifest,marker


def read_labels(directory,banks,marker):
    """Outcome-access boundary, used for held-out development only after seal."""
    if read(directory/'COMPLETE.json')!=marker:raise ValueError('evaluator marker changed')
    for name,value in marker['files_sha256'].items():
        if sha(directory/name)!=value:raise ValueError('execution artifact hash mismatch')
    labels=validate_labels(rows(directory/'labels.jsonl'),banks)
    if any(row['status']=='stable' and row['all_ac'] and row['loss']!=0 for row in labels.values()):
        raise ValueError('all-AC candidate cannot regress')
    return labels


def cohort_contract(groups,*,production):
    expected={'original':Counter(train=64,valid=32),'replication':Counter(valid=128),
              'next':Counter(valid=128),'training':Counter(train=256)}
    all_examples=[ex for examples,_ in groups.values() for ex in examples]
    if len({ex.user_id for ex in all_examples})!=len(all_examples) or len({ex.example_id for ex in all_examples})!=len(all_examples):
        raise ValueError('recipient users/examples overlap across cohorts')
    if production and (len(all_examples)!=608 or any(Counter(ex.split for ex in groups[name][0])!=counts for name,counts in expected.items())):
        raise ValueError('fixed 64/32/128/128/256 cohort contract required')
    if any(ex.split!='train' for ex in groups['training'][0]) or any(ex.split!='valid' for key in ('replication','next') for ex in groups[key][0]):
        raise ValueError('training/validation cohort split mismatch')
    train={source_hash(ex.observation.current.source) for ex in all_examples if ex.split=='train'}
    valid={source_hash(ex.observation.current.source) for ex in all_examples if ex.split=='valid'}
    if train&valid:raise ValueError('current source SHA overlaps train and valid')
    old=[ex for name in ('original','replication','next') for ex in groups[name][0]]
    old_sources={source_hash(value.source) for ex in old for value in (ex.observation.current,*ex.observation.prior,*ex.donor_history)}
    if any(source_hash(ex.observation.current.source) in old_sources for ex in groups['training'][0]):
        raise ValueError('new training current overlaps previous source')


def assess_group(examples,banks,labels,models,select_filtered):
    """All fixed decisions, controls, missing-outcome bounds and status strata."""
    saved=[]
    for ex in examples:
        bank=banks[ex.bank_id];noop=source_hash(bank.current_source);first=bank.attempts[0]
        choices={'noop':noop,'first_attempt':source_hash(first.source) if first.status=='success' else noop}
        for key,cell in models.items():
            supplied=history(ex,cell['condition'])
            choices[key+'_raw']=select_model(cell['rank_model'],ex.observation,supplied,bank)
            choices[key+'_filtered']=select_filtered(cell['rank_model'],cell['risk_model'],ex.observation,supplied,bank)
        saved.append(dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,problem_id=bank.problem_id,
            choices=choices,candidate_edit_tokens={c.candidate_id:features(ex.observation,c.source,history=())['candidate_edit_tokens'] for c in bank.candidates}))
    methods=list(saved[0]['choices'])
    results={method:_summary([_value(p,p['choices'][method],labels[p['bank_id'],p['choices'][method]]) for p in saved]) for method in methods}
    paired={method+'-first_attempt':_contrast(results[method]['predictions'],results['first_attempt']['predictions']) for method in methods if method not in ('first_attempt','noop')}
    for size in ('train64','train320'):
        for condition in ('C','H','U'):
            left=size+'_'+condition+'_filtered';right=size+'_'+condition+'_raw'
            paired[left+'-'+right]=_contrast(results[left]['predictions'],results[right]['predictions'])
        for condition in ('H','U'):
            left=size+'_'+condition+'_filtered';right=size+'_C_filtered'
            paired[left+'-'+right]=_contrast(results[left]['predictions'],results[right]['predictions'])
    paired['train320_C_filtered-train64_C_filtered']=_contrast(results['train320_C_filtered']['predictions'],results['train64_C_filtered']['predictions'])
    by_status={key:set() for key in ('known_ac','known_nonac','unknown')}
    for p in saved:
        noop=labels[p['bank_id'],p['choices']['noop']]
        key='unknown' if noop['status']=='unknown' else 'known_ac' if noop['all_ac'] else 'known_nonac'
        by_status[key].add(p['example_id'])
    subgroups={key:dict(examples=len(ids),results={method:_summary([v for v in result['predictions'] if v['example_id'] in ids]) for method,result in results.items()}) for key,ids in by_status.items()}
    problem_ids={p['example_id']:p['problem_id'] for p in saved}
    problems={pid:{method:_summary([v for v in result['predictions'] if problem_ids[v['example_id']]==pid]) for method,result in results.items()} for pid in sorted(set(problem_ids.values()))}
    return dict(results=results,paired_utility_bounds=paired,original_status_subgroups=subgroups,
                problem_results=problems,decisions=saved,
                note='All exposed development; bounds reflect unknown outcomes, not sampling confidence intervals.')


def resource_decision(reports):
    checks={}
    for cohort in ('replication_valid128','next_valid128'):
        primary=reports[cohort]['results'][PRIMARY]['metrics'];first=reports[cohort]['results']['first_attempt']['metrics']
        checks[cohort]=dict(ac_lower_strictly_greater=primary['rr_lower_bound']>first['rr_lower_bound'],
            regression_lower_no_worse=primary['regression_rate_lower_bound']<=first['regression_rate_lower_bound'],
            regression_upper_no_worse=primary['regression_rate_upper_bound']<=first['regression_rate_upper_bound'])
    eligible=all(all(check.values()) for check in checks.values())
    return dict(primary=PRIMARY,checks=checks,eligible_for_separately_frozen_development_replay=eligible,
        next_action='prepare_separate_frozen_new_user_development_replay' if eligible else 'retain_negative_result_and_train_only_diagnosis',
        confirmatory=False,zpd_benefit_established=False,no_grid_expansion=True)


def run_development(original_root,replication_root,next_root,training_prepared,training_run,output,*,production=True):
    from scripts.zpd_repair_risk import train_fixed_ranker, train_risk_model, select_filtered
    roots=list(map(Path,(original_root,replication_root,next_root,training_prepared,training_run,output)))
    original_root,replication_root,next_root,training_prepared,training_run,output=roots
    if output.exists():raise ValueError('new output directory required')
    if production and subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('clean source snapshot required')
    source_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    locations={
        'original':(original_root/'prepared-v2',original_root/'run-v1',original_root/'run-v1'/'generation'/'banks.jsonl'),
        'replication':(replication_root/'prepared-v1',replication_root/'run-v1',replication_root/'run-v1'/'banks.jsonl'),
        'next':(next_root/'prepared-v1',next_root/'run-v1',next_root/'run-v1'/'banks.jsonl'),
        'training':(training_prepared,training_run,training_run/'banks.jsonl')}
    preparations={};groups={};evaluations={};markers={};generation_configs={};input_hashes={}
    for name,(prep,run,bank_path) in locations.items():
        preparations[name],observations=prepared(prep)
        groups[name]=parse_examples(observations,rows(bank_path))
        generation_configs[name]=verify_generation(prep,run,bank_path,original=name=='original')
        evaluations[name],markers[name]=evaluation_metadata(run/'evaluation',bank_path,groups[name][1],preparations[name],production=production)
        for path in (prep/'manifest.json',prep/'observations.jsonl',bank_path,run/'evaluation'/'COMPLETE.json',run/'evaluation'/'manifest.json'):
            input_hashes[str(path)]=sha(path)
        generation_directories=[run/'generation'] if name=='original' else [run/f'generation-{i}' for i in range((len(rows(prep/'requests.jsonl'))+63)//64)]
        for directory in generation_directories:
            for filename in ('manifest.json','COMPLETE','banks.jsonl'):
                input_hashes[str(directory/filename)]=sha(directory/filename)
    cohort_contract(groups,production=production)
    if any(config!=generation_configs['original'] for config in generation_configs.values()):raise ValueError('generator drift between cohorts')
    if any(ev['runtime_sha256']!=evaluations['original']['runtime_sha256'] for ev in evaluations.values()):raise ValueError('execution runtime drift between cohorts')
    source_inputs=preparations['original']['input_sha256']
    if any(prep['input_sha256']!=source_inputs for prep in preparations.values()):raise ValueError('different feature/code input corpus')
    previous_hashes={name:sha(locations[name][0]/'manifest.json') for name in ('original','replication','next')}
    if production:
        if preparations['replication'].get('previous_manifest_sha256')!=previous_hashes['original']:
            raise ValueError('replication preparation original ancestry mismatch')
        expected_next={name:previous_hashes[name] for name in ('original','replication')}
        if preparations['next'].get('previous_manifest_sha256')!=expected_next:
            raise ValueError('next preparation ancestry mismatch')
    if preparations['training'].get('previous_manifest_sha256')!=previous_hashes:
        raise ValueError('training preparation ancestor binding mismatch')
    if production and (preparations['training'].get('previous_users')!=352 or preparations['training'].get('previous_selected_rows')!=352 or preparations['training'].get('selection_salt')!='repair-training-20260923-v1'):
        raise ValueError('training preparation fixed exclusion contract mismatch')
    shared_data={};shared_universes={}
    for name,prep in preparations.items():
        for key,value in prep['data_sha256'].items():
            if shared_data.setdefault(key,value)!=value:raise ValueError('shared prepared problem data drift')
        for pid,value in evaluations[name]['universe_sha256'].items():
            if shared_universes.setdefault(pid,value)!=value:raise ValueError('shared execution testcase universe drift')
    # These are the only two outcome files available to the fit stage. Original
    # data physically combines64/32; explicit bank filtering prevents valid leakage.
    original_labels=read_labels(locations['original'][1]/'evaluation',groups['original'][1],markers['original'])
    new_labels=read_labels(training_run/'evaluation',groups['training'][1],markers['training'])
    original_train=[ex for ex in groups['original'][0] if ex.split=='train']
    train_ids={ex.bank_id for ex in original_train}
    train_banks={key:value for key,value in groups['original'][1].items() if key in train_ids}
    train_labels={key:value for key,value in original_labels.items() if key[0] in train_ids}
    train320=original_train+groups['training'][0]
    banks320={**train_banks,**groups['training'][1]};labels320={**train_labels,**new_labels}
    if len(banks320)!=len(train_banks)+len(groups['training'][1]):raise ValueError('training bank IDs overlap')
    pair_mass=training_data(original_train,train_banks,train_labels,'C','lexical')[-1]['ordered_pairs']
    candidate_mass=sum(lab['status']=='stable' for lab in train_labels.values())
    if production and (pair_mass!=REFERENCE_PAIR_WEIGHT or candidate_mass!=REFERENCE_CANDIDATE_WEIGHT):
        raise ValueError('original64 reference masses must be1900pairs/467stable candidates')
    if not pair_mass or not candidate_mass:raise ValueError('positive original reference masses required')
    output.mkdir(parents=True,exist_ok=False)
    implementations=[Path(__file__),ROOT/'scripts/zpd_repair_risk.py',ROOT/'scripts/zpd_repair_pairwise.py',ROOT/'scripts/zpd_repair_pairwise_replication.py',ROOT/'scripts/zpd_repair_replication.py',ROOT/'scripts/zpd_repair_fit.py',ROOT/'src/repair/pilot_contracts.py',ROOT/'src/repair/pilot_ranker.py']
    manifest=dict(kind='risk_train_support_development_v1',confirmatory=False,fresh_test_opened=False,
        source_revision=source_revision,source_sha256={str(p.relative_to(ROOT)):sha(p) for p in implementations},
        protocol_sha256=sha(PROTOCOL),input_sha256=input_hashes,started=time.time(),
        expected_evaluation_files_sha256={name:marker['files_sha256'] for name,marker in markers.items()},
        reference_pair_weight=pair_mass,reference_candidate_weight=candidate_mass,
        runtime_versions={name:version(name) for name in ('numpy','scipy','scikit-learn')},
        train_ids={'train64':[ex.example_id for ex in original_train],'train320':[ex.example_id for ex in train320]},
        evaluation_label_policy='Original combined64/32 parsed before fitting, only64 passed to learner; both128 outcomes opened only after model seal.')
    write(output/'manifest.json',manifest)
    models={}
    for size,examples,banks,labels in [('train64',original_train,train_banks,train_labels),('train320',train320,banks320,labels320)]:
        for condition in ('C','H','U'):
            rank=train_fixed_ranker(examples,banks,labels,condition,pair_mass)
            risk=train_risk_model(examples,banks,labels,condition,candidate_mass)
            models[size+'_'+condition]=dict(condition=condition,training_size=len(examples),
                rank_model=rank,risk_model=risk,rank_model_sha256=canonical_hash(rank),risk_model_sha256=canonical_hash(risk))
    write(output/'models.json',models)
    write(output/'MODELS_COMPLETE.json',dict(status='models_sealed_before_development_evaluation',
        rank_fits=6,risk_fits=6,models_sha256=sha(output/'models.json'),manifest_sha256=sha(output/'manifest.json')))
    print('Six fixed rankers and six risk models sealed; opening exposed development outcomes',flush=True)
    # No128 outcome label/completion has been opened before the durable model seal.
    heldout={name:read_labels(locations[name][1]/'evaluation',groups[name][1],markers[name]) for name in ('replication','next')}
    reports={}
    for name,group,label_map in [('original_valid32','original',original_labels),('replication_valid128','replication',heldout['replication']),('next_valid128','next',heldout['next'])]:
        examples,banks=groups[group]
        reports[name]=assess_group([ex for ex in examples if ex.split=='valid'],banks,label_map,models,select_filtered)
    frozen_check={'available':False}
    frozen_parent=next_root/'run-v1'/'predictions'/'parent_selection.json'
    if frozen_parent.exists():
        parent_complete=frozen_parent.parent/'parent_complete.json'
        if read(parent_complete).get('selection_sha256')!=sha(frozen_parent):raise ValueError('frozen parent selection seal mismatch')
        cell=read(frozen_parent)['selected']['C'];model=cell['model']
        if model['variant']!='lexical' or model['C']!=.1:raise ValueError('original frozenC is not lexicalC.1')
        actual={p['example_id']:p['candidate_id'] for p in reports['original_valid32']['results']['train64_C_raw']['predictions']}
        expected={p['example_id']:p['candidate_id'] for p in cell['predictions']}
        frozen_check=dict(available=True,original_valid32_choices_equal=actual==expected,parent_selection_sha256=sha(frozen_parent),examples=len(actual))
        if actual!=expected:raise ValueError('original64 fixedC choices differ from frozenC')
    if production and not frozen_check['available']:raise ValueError('frozen originalC parent selection required')
    for path,expected in input_hashes.items():
        if sha(Path(path))!=expected:raise ValueError('input changed during fit/evaluation')
    for name,(prep,run,_) in locations.items():
        verify_prepared_files(prep,preparations[name]['output_sha256'])
        for filename,expected in markers[name]['files_sha256'].items():
            if sha(run/'evaluation'/filename)!=expected:raise ValueError('outcome evidence changed during fit/evaluation')
    for relative,expected in manifest['source_sha256'].items():
        if sha(ROOT/relative)!=expected:raise ValueError('source changed during fit/evaluation')
    if sha(PROTOCOL)!=manifest['protocol_sha256']:raise ValueError('protocol changed during fit/evaluation')
    if sha(output/'models.json')!=read(output/'MODELS_COMPLETE.json')['models_sha256']:
        raise ValueError('sealed models changed')
    final=dict(kind='risk_train_support_development_v1',confirmatory=False,fresh_test_opened=False,
        primary=PRIMARY,results=reports,decision=resource_decision(reports),frozen_original_C=frozen_check,
        models_complete_sha256=sha(output/'MODELS_COMPLETE.json'),manifest_sha256=sha(output/'manifest.json'),
        evaluation_label_sha256={name:sha(locations[name][1]/'evaluation'/'labels.jsonl') for name in locations},
        note='All results are exposed development evidence; neither superiority nor ZPD/learning effects are established.')
    write(output/'report.json',final)
    write(output/'COMPLETE.json',dict(report_sha256=sha(output/'report.json'),models_complete_sha256=sha(output/'MODELS_COMPLETE.json'),
        models_sha256=sha(output/'models.json'),manifest_sha256=sha(output/'manifest.json')))
    return final


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('original-root','replication-root','next-root','training-prepared','training-run','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args(argv)
    report=run_development(**vars(args))
    print(json.dumps(report['decision'],sort_keys=True))
    return report


if __name__=='__main__':main()
