"""Bounded, train-only structural CV pipeline; no generation or test access.

One fixed 30-fit family, persisted fold predictions, all-result reporting and a
conditional six-fit full-train seal. Failure never promotes a secondary arm.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from fractions import Fraction
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import time

from scripts.zpd_repair_fit import history
from scripts.zpd_repair_pairwise_replication import _contrast, _summary, _value
from scripts.zpd_repair_replication import read, rows, sha, write
from scripts.zpd_repair_risk_development import (
    evaluation_metadata, parse_examples, prepared, read_labels, verify_generation)
from src.repair.pilot_contracts import source_hash
from src.repair.pilot_ranker import features

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'analysis_protocols/zpd-repair-structure-cv-20260923.md'
PARENT_REPORT_SHA = '614a351037f9883279271f4c6a968ff38647e3b770269ed5b6db4ad33039d1a0'
PARENT_MANIFEST_SHA = '2687686775860c9b924ebaac838bf63a5ef35241a4eea6c1fff7d5f5d6d3ef88'
SALT = 'structure-cv-20260923-v1'
CELLS = tuple((variant, condition) for variant in ('lexical', 'structural') for condition in ('C', 'H', 'U'))
PRIMARY = 'structural_C'
CONTROLS = ('lexical_C', 'first_attempt')


def _output_key(path):
    parts = Path(path).parts
    if parts.count('outputs')!=1 or '..' in parts:
        raise ValueError('unambiguous project outputs path required')
    return '/'.join(parts[parts.index('outputs'):])


def verify_parent_bindings(parent, required_bindings, evaluations, train64, train320):
    """Bind actual consumed data to the frozen parent, across host prefixes."""
    expected = {}
    for path,digest in parent['input_sha256'].items():
        key = _output_key(path)
        if key in expected:
            raise ValueError('duplicate normalized parent input')
        expected[key] = digest
    for path,digest in required_bindings.items():
        if expected.get(_output_key(path))!=digest:
            raise ValueError('consumed input differs from frozen parent')
    for name,files in evaluations.items():
        if parent['expected_evaluation_files_sha256'].get(name)!=files:
            raise ValueError('consumed evaluation differs from frozen parent')
    if parent['train_ids']!={'train64':train64,'train320':train320}:
        raise ValueError('consumed training IDs differ from frozen parent')


def assign_folds(examples):
    """Outcome-blind balanced grouping, with no recipient or bank duplicates."""
    if not examples or any(ex.split != 'train' for ex in examples):
        raise ValueError('nonempty train-only inputs required')
    for attr in ('example_id', 'user_id', 'bank_id'):
        if len({getattr(ex, attr) for ex in examples}) != len(examples):
            raise ValueError('one unique example/bank per recipient required')
    counts = Counter(ex.observation.problem_id for ex in examples)
    if len(counts) < 5:
        raise ValueError('at least five problems required; no fold relaxation')
    order = sorted(counts, key=lambda pid: (-counts[pid], hashlib.sha256((SALT+'|'+pid).encode()).hexdigest(), pid))
    sizes = [0]*5
    mapping = {}
    for pid in order:
        fold = min(range(5), key=lambda i: (sizes[i], i))
        mapping[pid] = fold
        sizes[fold] += counts[pid]
    return dict(salt=SALT, folds=5, problem_fold=mapping, fold_sizes=sizes,
                problem_counts=dict(sorted(counts.items())),
                example_fold={ex.example_id:mapping[ex.observation.problem_id] for ex in examples})


def load_training(project, *, production=True):
    """Verify ancestry and existing evidence; never open the two128 outcomes."""
    project = Path(project)
    original = project/'outputs/zpd-repair-development-20260918'
    replication = project/'outputs/zpd-repair-replication-20260921'
    next_root = project/'outputs/zpd-repair-pairwise-replication-20260922'
    expansion = project/'outputs/zpd-repair-risk-development-20260923'
    prep_paths = dict(original=original/'prepared-v2', replication=replication/'prepared-v1',
                      next=next_root/'prepared-v1', training=expansion/'prepared-v1')
    preps, observations, bindings, parent_bindings = {}, {}, {}, {}
    def bind(path):
        bindings[str(path.resolve())] = sha(path)
    for name, path in prep_paths.items():
        preps[name], observations[name] = prepared(path)
        bind(path/'manifest.json')
        parent_bindings[str(path/'manifest.json')]=sha(path/'manifest.json')
        parent_bindings[str(path/'observations.jsonl')]=sha(path/'observations.jsonl')
        for filename in preps[name]['output_sha256']:
            bind(path/filename)
    old = observations['original']+observations['replication']+observations['next']
    new = observations['training']
    if production:
        if (Counter(r['split'] for r in observations['original']) != Counter(train=64,valid=32)
                or any(len(observations[k]) != 128 or any(r['split'] != 'valid' for r in observations[k])
                       for k in ('replication','next'))
                or len(new) != 256 or any(r['split'] != 'train' for r in new)):
            raise ValueError('frozen64/32/128/128/256 ancestry required')
        if preps['training'].get('selection_salt') != 'repair-training-20260923-v1':
            raise ValueError('wrong training expansion family')
    if len({r['user_id'] for r in old+new}) != len(old+new):
        raise ValueError('ancestral recipient users overlap')
    parents = {name:sha(prep_paths[name]/'manifest.json') for name in ('original','replication','next')}
    if preps['training'].get('previous_manifest_sha256') != parents:
        raise ValueError('training ancestry mismatch')
    if production and (preps['replication'].get('previous_manifest_sha256') != parents['original']
            or preps['next'].get('previous_manifest_sha256') != {k:parents[k] for k in ('original','replication')}
            or preps['training'].get('previous_output_sha256') != {k:preps[k]['output_sha256'] for k in parents}):
        raise ValueError('ancestral preparation seals mismatch')
    if any(prep['input_sha256'] != preps['original']['input_sha256'] for prep in preps.values()):
        raise ValueError('source corpus drift')
    old_sources = {s['source_sha256'] for r in old for s in
                   (r['observation']['current'],*r['observation']['prior'],*r['donor_history'])}
    if any(r['observation']['current']['source_sha256'] in old_sources for r in new):
        raise ValueError('new training current overlaps ancestor source')
    run = expansion/'run-v1'
    complete = read(run/'COMPLETE.json')
    for field, relative in (('fit_complete_sha256','fit/COMPLETE.json'),
                            ('evaluation_complete_sha256','evaluation/COMPLETE.json'),
                            ('banks_complete_sha256','BANKS_COMPLETE.json')):
        if complete.get(field) != sha(run/relative):
            raise ValueError('completed parent family seal mismatch')
        bind(run/relative)
    bind(run/'COMPLETE.json')
    fit_complete = read(run/'fit/COMPLETE.json')
    for field, relative in (('report_sha256','fit/report.json'),('models_sha256','fit/models.json'),
                            ('manifest_sha256','fit/manifest.json'),('models_complete_sha256','fit/MODELS_COMPLETE.json')):
        if fit_complete.get(field) != sha(run/relative):
            raise ValueError('parent fit seal mismatch')
        bind(run/relative)
    if production and sha(run/'fit/report.json') != PARENT_REPORT_SHA:
        raise ValueError('wrong completed motivation family')
    if production and sha(run/'fit/manifest.json') != PARENT_MANIFEST_SHA:
        raise ValueError('wrong frozen parent manifest')
    parent_manifest = read(run/'fit/manifest.json')
    if production:
        for name,digest in parent_manifest['source_sha256'].items():
            if sha(ROOT/name)!=digest:
                raise ValueError('frozen dependency source drift')
    if read(run/'BANKS_COMPLETE.json').get('banks_sha256') != sha(run/'banks.jsonl'):
        raise ValueError('parent bank collection seal mismatch')
    groups, labels_by_group, configs, runtimes, evaluation_files = {}, {}, {}, {}, {}
    for name, directory, bank_path in (
            ('original',original/'run-v1',original/'run-v1/generation/banks.jsonl'),
            ('training',run,run/'banks.jsonl')):
        groups[name] = parse_examples(observations[name], rows(bank_path))
        configs[name] = verify_generation(prep_paths[name],directory,bank_path,original=name=='original')
        meta, marker = evaluation_metadata(directory/'evaluation',bank_path,groups[name][1],preps[name],production=production)
        runtimes[name] = meta['runtime_sha256']
        evaluation_files[name] = marker['files_sha256']
        # Original32 shares the physical original64 file. It is verified but
        # strictly filtered out before the learner or diagnostic sees labels.
        all_labels = read_labels(directory/'evaluation',groups[name][1],marker)
        train_ids = {ex.bank_id for ex in groups[name][0] if ex.split == 'train'}
        labels_by_group[name] = {key:value for key,value in all_labels.items() if key[0] in train_ids}
        for path in (bank_path,directory/'evaluation/COMPLETE.json',
                     *(directory/'evaluation'/filename for filename in marker['files_sha256'])):
            bind(path)
        for path in (bank_path,directory/'evaluation/COMPLETE.json',directory/'evaluation/manifest.json'):
            parent_bindings[str(path)]=sha(path)
        chunks = [directory/'generation'] if name=='original' else [directory/f'generation-{i}' for i in range((len(rows(prep_paths[name]/'requests.jsonl'))+63)//64)]
        for chunk in chunks:
            for filename in ('manifest.json','COMPLETE','banks.jsonl'):
                bind(chunk/filename)
                parent_bindings[str(chunk/filename)]=sha(chunk/filename)
    if configs['original'] != configs['training'] or runtimes['original'] != runtimes['training']:
        raise ValueError('generator or evaluator runtime drift')
    examples = [ex for name in ('original','training') for ex in groups[name][0] if ex.split=='train']
    verify_parent_bindings(parent_manifest,parent_bindings,evaluation_files,
        [ex.example_id for ex in groups['original'][0] if ex.split=='train'],[ex.example_id for ex in examples])
    ids = {ex.bank_id for ex in examples}
    banks = {key:value for name in groups for key,value in groups[name][1].items() if key in ids}
    labels = {key:value for values in labels_by_group.values() for key,value in values.items()}
    if len(examples) != len(ids) or production and len(examples) != 320:
        raise ValueError('unique train320 banks required')
    if len(labels) != sum(len(b.candidates) for b in banks.values()):
        raise ValueError('training label coverage mismatch')
    valid_current = {r['observation']['current']['source_sha256'] for r in old if r['split']=='valid'}
    if valid_current & {source_hash(ex.observation.current.source) for ex in examples}:
        raise ValueError('current-source train/valid overlap')
    assign_folds(examples)
    return examples, banks, labels, bindings


def prediction(ex, bank, models, fold):
    from scripts.zpd_repair_structure import score_model
    noop = source_hash(bank.current_source)
    first = bank.attempts[0]
    choices = dict(noop=noop, first_attempt=source_hash(first.source) if first.status=='success' else noop)
    scores = {}
    for key, model in models.items():
        scores[key] = score_model(model,ex.observation,history(ex,model['condition']),bank)
        choices[key] = min(scores[key],key=lambda cid:(-scores[key][cid],cid))
    return dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,fold=fold,
                problem_id=bank.problem_id,bank_seal_sha256=bank.seal_sha256,choices=choices,
                candidate_scores=scores,
                candidate_edit_tokens={c.candidate_id:features(ex.observation,c.source,history=())['candidate_edit_tokens']
                                       for c in bank.candidates})


def summarize(predictions, labels):
    if not predictions:
        raise ValueError('empty out-of-fold predictions')
    methods = tuple(predictions[0]['choices'])
    if any(tuple(p['choices']) != methods for p in predictions):
        # JSON round trips sort object keys. Compare sets rather than insertion
        # order for externally loaded predictions, but reject missing cells.
        if any(set(p['choices']) != set(methods) for p in predictions):
            raise ValueError('inconsistent prediction methods')
    def result(group):
        values = {m:_summary([_value(p,p['choices'][m],labels[p['bank_id'],p['choices'][m]]) for p in group]) for m in methods}
        # Exactly one prefix per user: use exact integer ratios for the gate's
        # count metrics, avoiding apparent differences from summation roundoff.
        for cell in values.values():
            if group:
                for key in ('rr_lower_bound','rr_upper_bound','regression_rate_lower_bound','regression_rate_upper_bound'):
                    cell['metrics'][key]=float(Fraction(int(cell['counts'][key]),len(group)))
        return values
    overall = result(predictions)
    problems = {pid:result([p for p in predictions if p['problem_id']==pid]) for pid in sorted({p['problem_id'] for p in predictions})}
    folds = {str(fold):result([p for p in predictions if p['fold']==fold]) for fold in range(5)}
    equal_problem = {m:{k:float(sum(Fraction(int(cell[m]['counts'][k]),cell[m]['examples']) for cell in problems.values())/len(problems))
                        for k in ('rr_lower_bound','rr_upper_bound','regression_rate_lower_bound','regression_rate_upper_bound')}
                     for m in methods}
    strata = {key:[] for key in ('known_ac','known_nonac','unknown')}
    failure_cases = []
    oracle_available = Counter()
    transitions = {control:Counter() for control in CONTROLS}
    for p in predictions:
        lab = labels[p['bank_id'],p['choices']['noop']]
        stratum = 'unknown' if lab['status']=='unknown' else 'known_ac' if lab['all_ac'] else 'known_nonac'
        strata[stratum].append(p)
        chosen = labels[p['bank_id'],p['choices'][PRIMARY]]
        available = [cid for (bid,cid),value in labels.items() if bid==p['bank_id'] and value['status']=='stable' and value['all_ac']]
        oracle_available['examples'] += 1
        oracle_available['banks_with_stable_ac'] += bool(available)
        oracle_available['banks_without_stable_ac'] += not bool(available)
        oracle_available['primary_known_misses_with_stable_ac'] += bool(available) and chosen['status']=='stable' and not chosen['all_ac']
        oracle_available['primary_unknown_with_stable_ac'] += bool(available) and chosen['status']=='unknown'
        for control in CONTROLS:
            other = labels[p['bank_id'],p['choices'][control]]
            cell = transitions[control]
            cell['selected_candidate_changed'] += p['choices'][PRIMARY] != p['choices'][control]
            if chosen['status']=='unknown' or other['status']=='unknown':
                cell['not_jointly_known'] += 1
            else:
                cell['ac_gained'] += chosen['all_ac'] and not other['all_ac']
                cell['ac_lost'] += other['all_ac'] and not chosen['all_ac']
                cell['regression_prevented'] += chosen['loss']==0 and other['loss']>0
                cell['regression_introduced'] += chosen['loss']>0 and other['loss']==0
        if chosen['status']=='unknown' or not chosen['all_ac']:
            failure_cases.append(dict(example_id=p['example_id'],problem_id=p['problem_id'],fold=p['fold'],
                original_status=stratum,selected_candidate=p['choices'][PRIMARY],selected_label=chosen,
                stable_ac_candidates=available,classification='unknown_selected' if chosen['status']=='unknown' else
                'ranking_miss_with_ac_in_bank' if available else 'no_stable_ac_in_bank',
                choices=p['choices']))
    return dict(results=overall,problem_results=problems,fold_results=folds,
                equal_problem_metrics=equal_problem,
                oracle_availability=dict(oracle_available),
                original_status_subgroups={k:dict(examples=len(v),results=result(v)) for k,v in strata.items()},
                primary_transitions={k:dict(v) for k,v in transitions.items()},failure_cases=failure_cases,
                paired_utility_bounds={m+'-first_attempt':_contrast(overall[m]['predictions'],overall['first_attempt']['predictions'])
                                       for m in methods if m not in ('first_attempt','noop')})


def resource_gate(report):
    checks = {}
    for control in CONTROLS:
        p = report['results'][PRIMARY]['metrics']
        c = report['results'][control]['metrics']
        ep = report['equal_problem_metrics'][PRIMARY]
        ec = report['equal_problem_metrics'][control]
        checks[control] = dict(ac_lower_strictly_greater=p['rr_lower_bound']>c['rr_lower_bound'],
            regression_lower_no_worse=p['regression_rate_lower_bound']<=c['regression_rate_lower_bound'],
            regression_upper_no_worse=p['regression_rate_upper_bound']<=c['regression_rate_upper_bound'],
            equal_problem_ac_lower_strictly_greater=ep['rr_lower_bound']>ec['rr_lower_bound'],
            equal_problem_regression_lower_no_worse=ep['regression_rate_lower_bound']<=ec['regression_rate_lower_bound'],
            equal_problem_regression_upper_no_worse=ep['regression_rate_upper_bound']<=ec['regression_rate_upper_bound'])
    stable_folds = sum(cell[PRIMARY]['metrics']['rr_lower_bound']>=cell['lexical_C']['metrics']['rr_lower_bound']
                       for cell in report['fold_results'].values())
    passed = all(all(v.values()) for v in checks.values()) and stable_folds>=4
    return dict(primary=PRIMARY,checks=checks,nonworse_ac_folds=stable_folds,required_nonworse_folds=4,
                eligible_for_separately_frozen_development_replay=passed,
                full_train_refits_authorized=passed,confirmatory=False,zpd_benefit_established=False,
                next_action='seal_six_full_train_models_then_separately_freeze_new_user_development' if passed else
                'retain_negative_result_then_design_history_state_and_objective',
                no_grid_expansion=True)


def _event(output, **fields):
    value = dict(timestamp_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**fields)
    temp = output/'STATUS.json.tmp'
    write(temp,value)
    temp.replace(output/'STATUS.json')
    with (output/'events.jsonl').open('a') as handle:
        handle.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n')
        handle.flush()
    print(json.dumps(value,sort_keys=True),flush=True)


def run_cv(examples,banks,labels,output,*,provenance=None):
    """Internal API also used by synthetic tests; all examples must be train."""
    from scripts.zpd_repair_structure import train_model
    output = Path(output)
    if output.exists():
        raise ValueError('new output directory required; no implicit retry')
    assignment = assign_folds(examples)
    required = {(ex.bank_id,c.candidate_id) for ex in examples for c in banks[ex.bank_id].candidates}
    if set(labels)!=required or set(banks)!={ex.bank_id for ex in examples}:
        raise ValueError('exact train-only bank/label coverage required')
    output.mkdir(parents=True)
    write(output/'manifest.json',dict(kind='structure_problem_group_cv_train_only',confirmatory=False,
        fresh_test_opened=False,primary=PRIMARY,training_recipients=len(examples),
        cells=[v+'_'+c for v,c in CELLS],fold_fit_budget=30,full_train_fit_budget=6,
        reference_pair_weight=1900,provenance=provenance or {},
        note='Exposed-development motivated train-only CV; no pedagogical/confirmatory inference.'))
    write(output/'folds.json',assignment)
    write(output/'FOLDS_COMPLETE.json',dict(folds_sha256=sha(output/'folds.json'),manifest_sha256=sha(output/'manifest.json')))
    predictions = []
    fitted = completed = 0
    try:
        _event(output,phase='folds_sealed',completed_recipients=0,total_recipients=len(examples),completed_fits=0)
        for fold in range(5):
            directory = output/f'fold-{fold}'
            directory.mkdir()
            train = [ex for ex in examples if assignment['example_fold'][ex.example_id]!=fold]
            held = [ex for ex in examples if assignment['example_fold'][ex.example_id]==fold]
            ids = {ex.bank_id for ex in train}
            train_banks = {key:bank for key,bank in banks.items() if key in ids}
            train_labels = {key:value for key,value in labels.items() if key[0] in ids}
            models = {}
            for variant,condition in CELLS:
                key = variant+'_'+condition
                models[key] = train_model(train,train_banks,train_labels,condition,variant,reference_pair_weight=1900)
                write(directory/(key+'.json'),models[key])
                fitted += 1
                _event(output,phase='fitting',fold=fold,cell=key,completed_fits=fitted,
                       completed_recipients=completed,total_recipients=len(examples))
            write(directory/'MODELS_COMPLETE.json',dict(
                model_files_sha256={key+'.json':sha(directory/(key+'.json')) for key in models},
                train_example_ids=[ex.example_id for ex in train],held_example_ids=[ex.example_id for ex in held],
                folds_sha256=sha(output/'folds.json')))
            current = [prediction(replace(ex,split='valid'),banks[ex.bank_id],models,fold) for ex in held]
            write(directory/'predictions.json',current)
            write(directory/'COMPLETE.json',dict(status='label_blind_predictions_complete',
                predictions_sha256=sha(directory/'predictions.json'),models_complete_sha256=sha(directory/'MODELS_COMPLETE.json')))
            predictions.extend(current)
            completed += len(held)
            _event(output,phase='fold_predicted',fold=fold,completed_fits=fitted,
                   completed_recipients=completed,total_recipients=len(examples))
        predictions.sort(key=lambda p:p['example_id'])
        write(output/'predictions.json',predictions)
        write(output/'PREDICTIONS_COMPLETE.json',dict(predictions_sha256=sha(output/'predictions.json'),
            fold_complete_sha256={str(i):sha(output/f'fold-{i}/COMPLETE.json') for i in range(5)}))
        report = summarize(predictions,labels)
        report.update(kind='structure_problem_group_cv_train_only',confirmatory=False,fresh_test_opened=False,
                      note='Unknown-outcome bounds are not sampling confidence intervals. OOF models share training data.')
        report['decision'] = resource_gate(report)
        write(output/'report.json',report)
        write(output/'next_action.json',report['decision'])
        if report['decision']['full_train_refits_authorized']:
            directory = output/'full-train'
            directory.mkdir()
            for variant,condition in CELLS:
                key = variant+'_'+condition
                model = train_model(examples,banks,labels,condition,variant,reference_pair_weight=1900)
                write(directory/(key+'.json'),model)
                fitted += 1
                _event(output,phase='full_train_refit',cell=key,completed_fits=fitted,
                       completed_recipients=completed,total_recipients=len(examples))
            write(directory/'COMPLETE.json',dict(model_files_sha256={v+'_'+c+'.json':sha(directory/(v+'_'+c+'.json')) for v,c in CELLS},
                report_sha256=sha(output/'report.json'),folds_sha256=sha(output/'folds.json')))
        if provenance:
            for path,value in provenance.get('input_sha256',{}).items():
                if sha(path)!=value:
                    raise ValueError('input changed during run')
            for relative,value in provenance.get('source_sha256',{}).items():
                if sha(ROOT/relative)!=value:
                    raise ValueError('source changed during run')
        files = ('manifest.json','folds.json','FOLDS_COMPLETE.json','predictions.json',
                 'PREDICTIONS_COMPLETE.json','report.json','next_action.json')
        marker = dict(status='complete',confirmatory=False,completed_recipients=completed,total_recipients=len(examples),
                      completed_fits=fitted,files_sha256={name:sha(output/name) for name in files},
                      full_train_complete_sha256=sha(output/'full-train/COMPLETE.json') if (output/'full-train/COMPLETE.json').exists() else None)
        _event(output,phase='complete',completed_recipients=completed,total_recipients=len(examples),
               completed_fits=fitted,decision=report['decision'])
        # Completion is the final authoritative write. If terminal progress
        # logging fails, the exception path cannot leave a false COMPLETE seal.
        write(output/'COMPLETE.json',marker)
        return report
    except Exception as exc:
        _event(output,phase='failed',completed_recipients=completed,total_recipients=len(examples),
               completed_fits=fitted,error_type=type(exc).__name__,error=str(exc))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args(argv)
    if args.output.resolve().parent != (args.project/'outputs/zpd-repair-structure-cv-20260923').resolve():
        raise ValueError('fixed project output family required')
    if args.output.exists():
        raise ValueError('new output directory required; no implicit retry')
    try:
        if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
            raise ValueError('clean source snapshot required')
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        examples,banks,labels,inputs = load_training(args.project)
    except Exception as exc:
        args.output.mkdir(parents=True,exist_ok=False)
        _event(args.output,phase='preflight_failed',completed_recipients=0,total_recipients=320,
               completed_fits=0,error_type=type(exc).__name__,error=str(exc))
        raise
    implementation = ('scripts/run_zpd_repair_structure_cv.py','scripts/zpd_repair_structure.py',
        'scripts/zpd_repair_pairwise.py','scripts/zpd_repair_risk_development.py',
        'scripts/zpd_repair_pairwise_replication.py','scripts/zpd_repair_replication.py',
        'scripts/zpd_repair_fit.py','scripts/zpd_repair_evaluate.py',
        'scripts/prepare_zpd_repair_next.py','src/repair/pilot_contracts.py','src/repair/pilot_ranker.py',
        str(PROTOCOL.relative_to(ROOT)))
    provenance = dict(source_revision=revision,input_sha256=inputs,
        source_sha256={name:sha(ROOT/name) for name in implementation},
        protocol_sha256=sha(PROTOCOL),parent_report_sha256=PARENT_REPORT_SHA,
        python=platform.python_version(),libraries={k:version(k) for k in ('numpy','scipy','scikit-learn')})
    return run_cv(examples,banks,labels,args.output,provenance=provenance)


if __name__=='__main__':
    main()
