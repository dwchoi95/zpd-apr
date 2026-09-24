"""One fixed preservation-objective crossfit on sealed train320; no new data.

Fifteen new fits, five reused structural baselines, fixed folds and transforms.
All predictions precede held-out label joins. A pass never triggers a full fit.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import time

from scripts.run_zpd_repair_structure_cv import assign_folds, load_training, _output_key
from scripts.zpd_repair_pairwise_replication import _value, _summary, _contrast
from scripts.zpd_repair_replication import read, sha
from scripts.zpd_repair_structure import score_model as reference_scores, _validate_model as validate_reference
from scripts.zpd_repair_preservation import CELLS, train_model, score_model, stratum
from src.repair.pilot_contracts import source_hash
from src.repair.pilot_ranker import features

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT/'analysis_protocols/zpd-preservation-objective-design-20260924.md'
FAMILY = 'outputs/zpd-repair-preservation-20260924'
PARENT_COMPLETE_SHA = 'b306cee0a7142bcdd2d72600602a8c7f60421aa441d18440fd60c7be8af0271f'
PRIMARY = 'refined_balanced'
LEARNED_CONTROLS = ('structural_C','lexical_C')
CONTROLS = (*LEARNED_CONTROLS,'first_attempt')
METHODS = (*CELLS,*LEARNED_CONTROLS,'first_attempt','noop')
COUNT_METRICS = ('rr_lower_bound','rr_upper_bound','regression_rate_lower_bound','regression_rate_upper_bound')


def write(path, value):
    path = Path(path); partial = path.with_name(path.name+'.partial')
    with partial.open('w',encoding='utf-8') as stream:
        json.dump(value,stream,sort_keys=True,allow_nan=False); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    partial.replace(path)


def event(output, **fields):
    value = dict(timestamp_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),**fields)
    with (output/'events.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(value,sort_keys=True,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
    write(output/'STATUS.json',value)
    print(json.dumps(value,sort_keys=True),flush=True)


def _bound(path, expected, bindings):
    path = Path(path).absolute()
    if path.resolve() != path or not path.is_file() or sha(path) != expected:
        raise ValueError('missing/changed/aliased sealed reference: '+str(path))
    bindings[str(path)] = expected


def load_references(project, examples, training_bindings, *, production=True):
    parent = Path(project)/'outputs/zpd-repair-structure-cv-20260923/run-v1'
    bindings = {}; complete = read(parent/'COMPLETE.json')
    if production and sha(parent/'COMPLETE.json') != PARENT_COMPLETE_SHA:
        raise ValueError('wrong frozen structural reference family')
    _bound(parent/'COMPLETE.json',sha(parent/'COMPLETE.json'),bindings)
    if (complete.get('status') != 'complete' or complete.get('completed_fits') != 30
            or complete.get('completed_recipients') != len(examples) or complete.get('full_train_complete_sha256') is not None):
        raise ValueError('completed nonpromoted five-fold reference required')
    root_files = {'manifest.json','folds.json','FOLDS_COMPLETE.json','predictions.json','PREDICTIONS_COMPLETE.json','report.json','next_action.json'}
    if set(complete['files_sha256']) != root_files:
        raise ValueError('exact structural reference inventory required')
    for name,digest in complete['files_sha256'].items():
        _bound(parent/name,digest,bindings)
    manifest = read(parent/'manifest.json'); provenance = manifest['provenance']
    if production:
        original = {_output_key(p):s for p,s in provenance['input_sha256'].items()}
        current = {_output_key(p):s for p,s in training_bindings.items()}
        if original != current:
            raise ValueError('reference and current consumed training inputs differ')
        for name,digest in provenance['source_sha256'].items():
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('unsafe parent source binding')
            _bound(ROOT/name,digest,bindings)
    folds = assign_folds(examples)
    if read(parent/'folds.json') != folds:
        raise ValueError('unchanged exact structural folds required')
    fold_seal = read(parent/'FOLDS_COMPLETE.json')
    if fold_seal != dict(folds_sha256=sha(parent/'folds.json'),manifest_sha256=sha(parent/'manifest.json')):
        raise ValueError('reference folds seal mismatch')
    prediction_seal = read(parent/'PREDICTIONS_COMPLETE.json')
    if prediction_seal['predictions_sha256'] != sha(parent/'predictions.json') or set(prediction_seal['fold_complete_sha256']) != set(map(str,range(5))):
        raise ValueError('reference prediction ancestry mismatch')
    references = {}; joined = []
    for fold in range(5):
        directory = parent/f'fold-{fold}'
        _bound(directory/'COMPLETE.json',prediction_seal['fold_complete_sha256'][str(fold)],bindings)
        marker = read(directory/'COMPLETE.json')
        if marker['status'] != 'label_blind_predictions_complete':
            raise ValueError('reference predictions not sealed')
        _bound(directory/'MODELS_COMPLETE.json',marker['models_complete_sha256'],bindings)
        _bound(directory/'predictions.json',marker['predictions_sha256'],bindings)
        models_seal = read(directory/'MODELS_COMPLETE.json')
        train = [e.example_id for e in examples if folds['example_fold'][e.example_id] != fold]
        held = [e.example_id for e in examples if folds['example_fold'][e.example_id] == fold]
        if (models_seal['train_example_ids'] != train or models_seal['held_example_ids'] != held
                or models_seal['folds_sha256'] != sha(parent/'folds.json')):
            raise ValueError('reference exact fold-training/held identity mismatch')
        expected = {v+'_'+c+'.json' for v in ('lexical','structural') for c in ('C','H','U')}
        if set(models_seal['model_files_sha256']) != expected:
            raise ValueError('reference six-cell model inventory mismatch')
        for name,digest in models_seal['model_files_sha256'].items():
            _bound(directory/name,digest,bindings)
        models = {name:read(directory/(name+'.json')) for name in LEARNED_CONTROLS}
        for name,model in models.items():
            validate_reference(model)
            if model['condition'] != 'C' or model['variant'] != name.split('_')[0]:
                raise ValueError('wrong baseline model cell')
            ids = model['training']['informative_train_example_ids']+model['training']['uninformative_train_example_ids']
            if len(ids) != len(train) or set(ids) != set(train):
                raise ValueError('reference model fitted membership mismatch')
        predictions = read(directory/'predictions.json')
        if [p['example_id'] for p in predictions] != held or any(p['fold'] != fold for p in predictions):
            raise ValueError('reference held prediction alignment mismatch')
        references[str(fold)] = dict(models=models,train_example_ids=train,held_example_ids=held,predictions=predictions)
        joined.extend(predictions)
    if sorted(joined,key=lambda p:p['example_id']) != read(parent/'predictions.json'):
        raise ValueError('reference fold/combined predictions differ')
    return references,bindings,provenance


def validate_references(examples, references):
    assignment = assign_folds(examples)
    if set(references) != set(map(str,range(5))):
        raise ValueError('five exact fold references required')
    for fold in range(5):
        reference = references[str(fold)]
        train = [e.example_id for e in examples if assignment['example_fold'][e.example_id] != fold]
        held = [e.example_id for e in examples if assignment['example_fold'][e.example_id] == fold]
        if reference['train_example_ids'] != train or reference['held_example_ids'] != held:
            raise ValueError('reference fold membership mismatch')
        if set(reference['models']) != set(LEARNED_CONTROLS):
            raise ValueError('both frozen learned controls required')
        for name,model in reference['models'].items():
            validate_reference(model)
            ids = model['training']['informative_train_example_ids']+model['training']['uninformative_train_example_ids']
            if set(ids) != set(train) or len(ids) != len(train) or model['condition'] != 'C' or model['variant'] != name.split('_')[0]:
                raise ValueError('reference model/scale training membership mismatch')
    return assignment


def predict(ex, bank, models, reference, fold):
    scores = {name:score_model(model,ex.observation,bank) for name,model in models.items()}
    scores.update({name:reference_scores(model,ex.observation,(),bank) for name,model in reference.items()})
    if scores['legacy_natural'] != scores['structural_C']:
        raise ValueError('reused baseline scores changed')
    noop = source_hash(bank.current_source); first = bank.attempts[0]
    choices = {name:min(s,key=lambda cid:(-s[cid],cid)) for name,s in scores.items()}
    choices.update(noop=noop,first_attempt=source_hash(first.source) if first.status == 'success' else noop)
    return dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,problem_id=bank.problem_id,
        bank_seal_sha256=bank.seal_sha256,fold=fold,choices=choices,candidate_scores=scores,
        candidate_edit_tokens={c.candidate_id:features(ex.observation,c.source,history=())['candidate_edit_tokens'] for c in bank.candidates})


def summarize(predictions, labels):
    if not predictions or any(set(p['choices']) != set(METHODS) for p in predictions):
        raise ValueError('complete fixed eight-method prediction coverage required')
    def aggregate(group):
        result = {m:_summary([_value(p,p['choices'][m],labels[p['bank_id'],p['choices'][m]]) for p in group]) for m in METHODS}
        if group:
            for value in result.values():
                for name in COUNT_METRICS:
                    value['metrics'][name] = float(Fraction(int(value['counts'][name]),len(group)))
        return result
    overall = aggregate(predictions)
    problems = {pid:aggregate([p for p in predictions if p['problem_id'] == pid]) for pid in sorted({p['problem_id'] for p in predictions})}
    folds = {str(f):aggregate([p for p in predictions if p['fold'] == f]) for f in range(5)}
    equal_problem = {m:{name:float(sum(Fraction(int(v[m]['counts'][name]),v[m]['examples']) for v in problems.values())/len(problems))
        for name in COUNT_METRICS} for m in METHODS}
    strata = {s:[p for p in predictions if stratum(labels[p['bank_id'],p['choices']['noop']]) == s]
              for s in ('known_ac','known_nonac','unknown')}
    transitions = {}
    for control in (*CONTROLS,'legacy_balanced','refined_natural'):
        counts = Counter()
        for p in predictions:
            a = labels[p['bank_id'],p['choices'][PRIMARY]]; b = labels[p['bank_id'],p['choices'][control]]
            counts['selected_candidate_changed'] += p['choices'][PRIMARY] != p['choices'][control]
            if a['status'] == 'unknown' or b['status'] == 'unknown':
                counts['not_jointly_known'] += 1
                counts['primary_unknown'] += a['status'] == 'unknown';counts['control_unknown'] += b['status'] == 'unknown'
            else:
                counts['ac_gained'] += a['all_ac'] and not b['all_ac']; counts['ac_lost'] += b['all_ac'] and not a['all_ac']
                counts['regression_prevented'] += a['loss'] == 0 and b['loss'] > 0
                counts['regression_introduced'] += a['loss'] > 0 and b['loss'] == 0
        transitions[control] = dict(counts)
    return dict(results=overall,problem_results=problems,fold_results=folds,equal_problem_metrics=equal_problem,
        original_status_subgroups={s:dict(examples=len(group),results=aggregate(group)) for s,group in strata.items()},
        primary_transitions=transitions,paired_utility_bounds={PRIMARY+'-'+m:_contrast(overall[PRIMARY]['predictions'],overall[m]['predictions'])
            for m in METHODS if m != PRIMARY})


def resource_gate(report):
    def rates(cell):
        return {name:Fraction(int(cell['counts'][name]),cell['examples']) for name in COUNT_METRICS}
    def equal_problem(method):
        return {name:sum(rates(value[method])[name] for value in report['problem_results'].values())/len(report['problem_results'])
                for name in COUNT_METRICS}
    checks = {}
    for control in CONTROLS:
        p = rates(report['results'][PRIMARY]); c = rates(report['results'][control])
        ep = equal_problem(PRIMARY); ec = equal_problem(control)
        checks[control] = dict(ac_lower_strictly_greater=p['rr_lower_bound'] > c['rr_lower_bound'],
            regression_lower_no_worse=p['regression_rate_lower_bound'] <= c['regression_rate_lower_bound'],
            regression_upper_no_worse=p['regression_rate_upper_bound'] <= c['regression_rate_upper_bound'],
            equal_problem_ac_lower_strictly_greater=ep['rr_lower_bound'] > ec['rr_lower_bound'],
            equal_problem_regression_lower_no_worse=ep['regression_rate_lower_bound'] <= ec['regression_rate_lower_bound'],
            equal_problem_regression_upper_no_worse=ep['regression_rate_upper_bound'] <= ec['regression_rate_upper_bound'])
    stability = {c:sum(rates(v[PRIMARY])['rr_lower_bound'] >= rates(v[c])['rr_lower_bound']
                       for v in report['fold_results'].values()) for c in LEARNED_CONTROLS}
    passed = len(report['fold_results']) == 5 and all(all(v.values()) for v in checks.values()) and all(n >= 4 for n in stability.values())
    return dict(primary=PRIMARY,gate_passed=passed,checks=checks,nonworse_ac_folds=stability,required_nonworse_folds=4,
        eligible_for_separately_frozen_development_replay=passed,full_train_refits_authorized=False,
        confirmatory=False,zpd_benefit_established=False,model_promotion=False,
        next_action='separately_freeze_and_audit_next_development' if passed else 'retain_negative_result_and_train_only_diagnosis')


def check_bindings(bindings):
    for path,digest in bindings.items():
        if sha(path) != digest:
            raise ValueError('input/source/reference changed: '+str(path))


def run_cv(examples,banks,labels,references,output,*,provenance=None):
    output = Path(output)
    if output.exists():
        raise FileExistsError('new output required; no implicit resume/retry')
    assignment = validate_references(examples,references)
    if set(banks) != {e.bank_id for e in examples} or set(labels) != {(e.bank_id,c.candidate_id) for e in examples for c in banks[e.bank_id].candidates}:
        raise ValueError('exact train-only bank/label coverage required')
    bindings = (provenance or {}).get('bindings',{})
    check_bindings(bindings); output.mkdir(parents=True)
    manifest = dict(kind='preservation_problem_group_cv_train_only_v1',confirmatory=False,fresh_test_opened=False,
        primary=PRIMARY,cells=list(CELLS),controls=list(CONTROLS),new_fit_budget=15,full_train_fit_budget=0,
        training_recipients=len(examples),reference_pair_weight=1900,provenance=provenance or {})
    completed = fitted = 0; predictions = []
    try:
        write(output/'manifest.json',manifest);write(output/'folds.json',assignment)
        write(output/'FOLDS_COMPLETE.json',dict(folds_sha256=sha(output/'folds.json'),manifest_sha256=sha(output/'manifest.json')))
        event(output,phase='folds_sealed',completed_recipients=0,total_recipients=len(examples),completed_fits=0)
        for fold in range(5):
            directory = output/f'fold-{fold}';directory.mkdir()
            train = [e for e in examples if assignment['example_fold'][e.example_id] != fold]
            held = [e for e in examples if assignment['example_fold'][e.example_id] == fold]
            bids = {e.bank_id for e in train}; train_banks = {b:banks[b] for b in bids}; train_labels = {k:v for k,v in labels.items() if k[0] in bids}
            ref = references[str(fold)]
            cohort = dict(fold=fold,train_example_ids=[e.example_id for e in train],held_example_ids=[e.example_id for e in held],
                train_problem_ids=sorted({e.observation.problem_id for e in train}),held_problem_ids=sorted({e.observation.problem_id for e in held}),
                reference_model_sha256={k:m['model_sha256'] for k,m in ref['models'].items()},
                bank_seals={e.bank_id:banks[e.bank_id].seal_sha256 for e in train+held})
            write(directory/'cohort.json',cohort)
            for name,model in ref['models'].items():
                write(directory/(name+'.json'),model)
            models = {}
            for cell in CELLS:
                models[cell] = train_model(train,train_banks,train_labels,ref['models']['structural_C'],cell)
                write(directory/(cell+'.json'),models[cell]); fitted += cell != 'legacy_natural'
                event(output,phase='cell_complete',fold=fold,cell=cell,completed_fits=fitted,
                      completed_recipients=completed,total_recipients=len(examples),legacy_reused=cell == 'legacy_natural')
            current = [predict(e,banks[e.bank_id],models,ref['models'],fold) for e in held]
            old = {p['example_id']:p for p in ref['predictions']}
            if set(old) != {e.example_id for e in held}:
                raise ValueError('reference prediction recipients differ')
            for p in current:
                prior = old[p['example_id']]
                for field in ('user_id','bank_id','problem_id','fold','bank_seal_sha256','candidate_edit_tokens'):
                    if prior[field] != p[field]:
                        raise ValueError('reference prediction input mismatch')
                for method in (*LEARNED_CONTROLS,'first_attempt','noop'):
                    if p['choices'][method] != prior['choices'][method]:
                        raise ValueError('frozen control choice changed')
                for method in LEARNED_CONTROLS:
                    if set(p['candidate_scores'][method]) != set(prior['candidate_scores'][method]) or any(
                        not math.isclose(v,prior['candidate_scores'][method][cid],rel_tol=1e-10,abs_tol=1e-12)
                        for cid,v in p['candidate_scores'][method].items()):
                        raise ValueError('frozen control coefficient scores changed')
            write(directory/'predictions.json',current)
            names = ['cohort.json','predictions.json',*[c+'.json' for c in (*CELLS,*LEARNED_CONTROLS)]]
            write(directory/'COMPLETE.json',dict(status='complete',fold=fold,files_sha256={n:sha(directory/n) for n in names}))
            predictions.extend(current);completed += len(held);check_bindings(bindings)
            event(output,phase='fold_predicted',fold=fold,completed_fits=fitted,completed_recipients=completed,total_recipients=len(examples))
        predictions.sort(key=lambda p:p['example_id'])
        write(output/'predictions.json',predictions)
        write(output/'PREDICTIONS_COMPLETE.json',dict(predictions_sha256=sha(output/'predictions.json'),
            fold_complete_sha256={str(f):sha(output/f'fold-{f}/COMPLETE.json') for f in range(5)}))
        report = summarize(predictions,labels)
        report.update(kind=manifest['kind'],confirmatory=False,fresh_test_opened=False,
            note='Adaptive train-only development; unknown-outcome bounds are not confidence intervals; no C1 model integrated.')
        report['decision'] = resource_gate(report)
        write(output/'report.json',report);write(output/'next_action.json',report['decision']);check_bindings(bindings)
        event(output,phase='complete',completed_fits=fitted,completed_recipients=completed,total_recipients=len(examples),gate_passed=report['decision']['gate_passed'])
        files = sorted(str(p.relative_to(output)) for p in output.rglob('*') if p.is_file())
        write(output/'COMPLETE.json',dict(status='complete',completed_folds=5,completed_fits=fitted,reused_models=5,
            completed_recipients=completed,total_recipients=len(examples),full_train_refits=0,gate_passed=report['decision']['gate_passed'],
            files_sha256={n:sha(output/n) for n in files}))
        return report
    except BaseException as error:
        write(output/'FAILED.json',dict(status='failed',error_type=type(error).__name__,error=str(error)))
        event(output,phase='failed',completed_fits=fitted,completed_recipients=completed,total_recipients=len(examples),error=str(error))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args(argv); project = args.project.absolute(); output = args.output.absolute()
    if project.resolve() != project or output.resolve() != output:
        raise ValueError('canonical paths without symlink aliases required')
    if output.parent != project/FAMILY or output.exists():
        raise ValueError('new direct child of fixed preservation family required')
    try:
        if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
            raise ValueError('clean committed source snapshot required')
        revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        examples,banks,labels,inputs = load_training(project)
        references,reference_bindings,previous = load_references(project,examples,inputs)
        libraries = {n:version(n) for n in ('numpy','scipy','scikit-learn')}
        if previous['libraries'] != libraries or previous['python'] != platform.python_version():
            raise ValueError('frozen structural numerical runtime required')
        sources = set(previous['source_sha256'])|{'scripts/zpd_repair_preservation.py','scripts/run_zpd_repair_preservation_cv.py',
            'scripts/audit_zpd_repair_preservation_cv.py','scripts/audit_zpd_history_action_cv.py',str(PROTOCOL.relative_to(ROOT))}
        source_sha = {name:sha(ROOT/name) for name in sorted(sources)}
        bindings = {**inputs,**reference_bindings,**{str(ROOT/name):digest for name,digest in source_sha.items()}}
        provenance = dict(source_revision=revision,source_sha256=source_sha,input_sha256=inputs,
            reference_sha256=reference_bindings,bindings=bindings,protocol_sha256=sha(PROTOCOL),
            parent_complete_sha256=PARENT_COMPLETE_SHA,python=platform.python_version(),libraries=libraries)
    except BaseException as error:
        output.mkdir(parents=True,exist_ok=False)
        write(output/'FAILED.json',dict(status='preflight_failed',error_type=type(error).__name__,error=str(error)))
        event(output,phase='preflight_failed',completed_recipients=0,total_recipients=320,completed_fits=0,error=str(error))
        raise
    return run_cv(examples,banks,labels,references,output,provenance=provenance)


if __name__ == '__main__':
    main()
