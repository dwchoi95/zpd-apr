"""Frozen, label-blind repair replication on new development users; never fit.

Predict seals decisions before execution. Assess accepts only complete sealed
execution evidence. Descriptive paired comparisons are not confirmatory claims.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.zpd_repair_evaluate import parse_bank
from scripts.zpd_repair_fit import source, metrics
from src.repair.pilot_contracts import PilotObservation, source_hash
from src.repair.pilot_ranker import TwoChannelCoefficients, features, select


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def verify_files(directory, marker):
    files = marker.get('files_sha256', {})
    if not files:
        raise ValueError('sealed files required')
    for name, expected in files.items():
        if Path(name).name != name or sha(directory / name) != expected:
            raise ValueError('sealed file hash mismatch')


def inputs(observation_rows, bank_rows):
    banks = {}
    for row in bank_rows:
        if row['bank_id'] in banks:
            raise ValueError('duplicate bank')
        banks[row['bank_id']] = parse_bank(row)
    examples, users, ids, used = [], set(), set(), set()
    for row in observation_rows:
        required = {'example_id','user_id','split','bank_id','observation','donor_history','donor_user_id'}
        if set(row) not in (required, required | {'donor_example_id'}):
            raise ValueError('observation allowlist')
        if row['split'] != 'valid' or row['user_id'] in users or row['example_id'] in ids:
            raise ValueError('unique validation users and examples required')
        users.add(row['user_id']); ids.add(row['example_id']); used.add(row['bank_id'])
        raw = row['observation']
        if set(raw) != {'problem_id','current','prior'}:
            raise ValueError('observation fields')
        obs = PilotObservation(raw['problem_id'], source(raw['current']), tuple(source(x) for x in raw['prior']))
        donor = tuple(source(x) for x in row['donor_history'])
        if not obs.prior or len(donor) != len(obs.prior) or row['donor_user_id'] == row['user_id']:
            raise ValueError('matched different-user nonempty history required')
        bank = banks[row['bank_id']]
        if bank.problem_id != obs.problem_id or bank.current_source != obs.current.source:
            raise ValueError('observation bank mismatch')
        features(obs, bank.current_source, history=donor)
        examples.append((row, obs, donor, bank))
    if not examples or used != set(banks):
        raise ValueError('nonempty exact bank coverage required')
    keys = {}
    for bank in banks.values():
        if keys.setdefault(bank.key, bank.seal_sha256) != bank.seal_sha256:
            raise ValueError('conflicting same-key banks')
    return examples, banks


def predict(observations, banks, parent_report, parent_complete, output):
    observations, banks, parent_report, parent_complete, output = map(Path, (observations,banks,parent_report,parent_complete,output))
    if output.exists():
        raise FileExistsError('new output required')
    if read(parent_complete).get('report_sha256') != sha(parent_report):
        raise ValueError('parent fit report seal mismatch')
    parent = read(parent_report)
    if parent.get('kind') != 'exposed_validation_development_only' or parent.get('confirmatory') is not False or parent.get('fresh_test_opened') is not False:
        raise ValueError('expected development parent fit')
    if set(parent['selected']) != {'C','H','U'}:
        raise ValueError('exact C/H/U parent required')
    configurations = {}
    for condition in ('C','H','U'):
        cell = parent['selected'][condition]
        if cell['condition'] != condition:
            raise ValueError('parent condition mismatch')
        configurations[condition] = {k: cell[k] for k in ('condition','alpha','risk_threshold','minimum_gain','coefficients')}
        if set(cell['coefficients']) != {'risk','gain'}:
            raise ValueError('two-channel coefficients required')
        TwoChannelCoefficients(**cell['coefficients'])
    examples, parsed = inputs(rows(observations), rows(banks))
    predictions = []
    for row, obs, donor, bank in examples:
        choices = {}
        for condition, history in [('C',()),('H',obs.prior),('U',donor)]:
            cfg = configurations[condition]
            choices[condition] = select(obs,bank,history=history,coefficients=TwoChannelCoefficients(**cfg['coefficients']),risk_threshold=cfg['risk_threshold'],minimum_gain=cfg['minimum_gain']).selected_source_sha256
        noop = source_hash(bank.current_source)
        first = bank.attempts[0]
        edits = {c.candidate_id: features(obs,c.source,history=())['candidate_edit_tokens'] for c in bank.candidates}
        nonnoop = [c.candidate_id for c in bank.candidates if not c.is_noop]
        choices.update(first_attempt=source_hash(first.source) if first.status == 'success' else noop,
            min_edit_nonnoop=min(nonnoop,key=lambda c:(edits[c],c)) if nonnoop else noop,noop=noop)
        predictions.append(dict(example_id=row['example_id'],user_id=row['user_id'],bank_id=row['bank_id'],
            bank_seal_sha256=bank.seal_sha256,problem_id=bank.problem_id,choices=choices,
            candidate_edit_tokens=edits,first_attempt_status=first.status))
    output.mkdir(parents=True,exist_ok=False)
    # Exact inputs retained so later assessment can check all candidate metadata.
    (output/'observations.jsonl').write_bytes(observations.read_bytes())
    (output/'banks.jsonl').write_bytes(banks.read_bytes())
    write(output/'predictions.json',predictions)
    write(output/'manifest.json',dict(kind='frozen_development_replication',confirmatory=False,
        trained=False,labels_opened=False,configurations=configurations,
        parent_report_sha256=sha(parent_report),parent_complete_sha256=sha(parent_complete),
        input_sha256={'observations':sha(observations),'banks':sha(banks)},
        implementation_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'src/repair/pilot_ranker.py',ROOT/'src/repair/pilot_contracts.py')}))
    write(output/'COMPLETE.json',dict(status='predictions_sealed_before_execution',files_sha256={name:sha(output/name) for name in ('observations.jsonl','banks.jsonl','predictions.json','manifest.json')}))
    return predictions


def validate_labels(label_rows, banks):
    labels = {}
    for row in label_rows:
        if set(row) != {'bank_id','candidate_id','status','gain','loss','all_ac','problem_id','is_noop','n_cases','evidence','bank_seal_sha256'}:
            raise ValueError('label allowlist')
        bank = banks[row['bank_id']]
        candidates = {c.candidate_id:c for c in bank.candidates}
        candidate = candidates[row['candidate_id']]
        if row['problem_id'] != bank.problem_id or row['bank_seal_sha256'] != bank.seal_sha256 or row['is_noop'] is not candidate.is_noop:
            raise ValueError('label bank provenance')
        if type(row['n_cases']) is not int or row['n_cases'] <= 0:
            raise ValueError('testcase count')
        ev = row['evidence']
        if set(ev) != {'status','gained_testcases','lost_testcases','candidate_all_ac','current_vector_sha256','candidate_vector_sha256'} or ev['status'] != row['status'] or ev['candidate_all_ac'] != row['all_ac']:
            raise ValueError('evidence mismatch')
        if row['status'] == 'unknown':
            if any(row[k] is not None for k in ('gain','loss','all_ac')) or ev['gained_testcases'] is not None or ev['lost_testcases'] is not None:
                raise ValueError('unknown must remain null')
        elif row['status'] == 'stable':
            if type(row['all_ac']) is not bool or any(type(row[k]) not in (float,int) or not math.isfinite(row[k]) or not 0 <= row[k] <= 1 for k in ('gain','loss')) or row['gain']+row['loss'] > 1+1e-12:
                raise ValueError('invalid stable fractions')
            for key,field in [('gained_testcases','gain'),('lost_testcases','loss')]:
                value=ev[key]
                if not isinstance(value,list) or len(set(value)) != len(value) or not math.isclose(len(value)/row['n_cases'],row[field],abs_tol=1e-12):
                    raise ValueError('fraction evidence mismatch')
            if set(ev['gained_testcases']) & set(ev['lost_testcases']):
                raise ValueError('overlapping gain/loss')
            if candidate.is_noop and (row['gain'] or row['loss']):
                raise ValueError('noop gain/loss')
        else:
            raise ValueError('unknown status')
        key = row['bank_id'],row['candidate_id']
        if key in labels:
            raise ValueError('duplicate labels')
        labels[key]=row
    if set(labels) != {(bid,c.candidate_id) for bid,b in banks.items() for c in b.candidates}:
        raise ValueError('exact candidate label coverage required')
    return labels


def assess(predictions, labels, output):
    predictions,labels,output=map(Path,(predictions,labels,output))
    if output.exists():
        raise FileExistsError('new output required')
    seal=read(predictions/'COMPLETE.json')
    if seal.get('status') != 'predictions_sealed_before_execution' or set(seal.get('files_sha256',{})) != {'observations.jsonl','banks.jsonl','predictions.json','manifest.json'}:
        raise ValueError('pre-execution prediction seal required')
    verify_files(predictions,seal)
    marker=read(labels.parent/'COMPLETE.json')
    if marker.get('status') != 'fully_executed' or marker.get('development_only') is not True or set(marker.get('files_sha256',{})) != {'manifest.json','completions.jsonl','labels.jsonl'} or labels.name != 'labels.jsonl':
        raise ValueError('complete development evaluator required')
    verify_files(labels.parent,marker)
    examples,banks=inputs(rows(predictions/'observations.jsonl'),rows(predictions/'banks.jsonl'))
    execution=read(labels.parent/'manifest.json')
    if execution['banks_sha256'] != sha(predictions/'banks.jsonl') or execution['bank_seals'] != {bid:b.seal_sha256 for bid,b in banks.items()}:
        raise ValueError('execution bank seal mismatch')
    label_map=validate_labels(rows(labels),banks)
    preds=read(predictions/'predictions.json')
    if not isinstance(preds,list) or len(preds) != len(examples):
        raise ValueError('exact prediction coverage required')
    prediction_manifest=read(predictions/'manifest.json')
    if prediction_manifest.get('kind') != 'frozen_development_replication' or prediction_manifest.get('trained') is not False or prediction_manifest.get('labels_opened') is not False or prediction_manifest.get('confirmatory') is not False:
        raise ValueError('label-blind frozen manifest required')
    if prediction_manifest.get('input_sha256') != {'observations':sha(predictions/'observations.jsonl'),'banks':sha(predictions/'banks.jsonl')}:
        raise ValueError('prediction input provenance mismatch')
    configs=prediction_manifest['configurations']
    if set(configs) != {'C','H','U'}:
        raise ValueError('frozen configuration coverage')
    for p,(row,obs,donor,bank) in zip(preds,examples):
        if set(p) != {'example_id','user_id','bank_id','bank_seal_sha256','problem_id','choices','candidate_edit_tokens','first_attempt_status'}:
            raise ValueError('prediction allowlist')
        expected={'example_id':row['example_id'],'user_id':row['user_id'],'bank_id':row['bank_id'],'bank_seal_sha256':bank.seal_sha256,'problem_id':bank.problem_id,'first_attempt_status':bank.attempts[0].status}
        if any(p[k] != v for k,v in expected.items()):
            raise ValueError('prediction identity mismatch')
        edits={c.candidate_id:features(obs,c.source,history=())['candidate_edit_tokens'] for c in bank.candidates}
        if p['candidate_edit_tokens'] != edits:
            raise ValueError('prediction candidate feature mismatch')
        expected_choices={}
        for condition,hist in [('C',()),('H',obs.prior),('U',donor)]:
            cfg=configs[condition]
            expected_choices[condition]=select(obs,bank,history=hist,coefficients=TwoChannelCoefficients(**cfg['coefficients']),risk_threshold=cfg['risk_threshold'],minimum_gain=cfg['minimum_gain']).selected_source_sha256
        noop=source_hash(bank.current_source); first=bank.attempts[0]
        nonnoop=[c.candidate_id for c in bank.candidates if not c.is_noop]
        expected_choices.update(noop=noop,first_attempt=source_hash(first.source) if first.status=='success' else noop,min_edit_nonnoop=min(nonnoop,key=lambda c:(edits[c],c)) if nonnoop else noop)
        if p['choices'] != expected_choices:
            raise ValueError('prediction choices differ from frozen model')
    results={}
    oracle_choices={}
    for bid,bank in banks.items():
        stable=[lab for (b,_),lab in label_map.items() if b==bid and lab['status']=='stable']
        oracle_choices[bid]=min(stable,key=lambda lab:(-(lab['gain']-lab['loss']),lab['candidate_id']))['candidate_id'] if stable else source_hash(bank.current_source)
    for condition in ('C','H','U','first_attempt','min_edit_nonnoop','noop','stable_only_utility_oracle_NOT_DEPLOYABLE'):
        values=[]
        for p in preds:
            cid=oracle_choices[p['bank_id']] if condition=='stable_only_utility_oracle_NOT_DEPLOYABLE' else p['choices'][condition]
            lab=label_map[p['bank_id'],cid]; unknown=lab['status']=='unknown'
            values.append(dict(example_id=p['example_id'],user_id=p['user_id'],bank_id=p['bank_id'],candidate_id=cid,
                utility=-1. if unknown else lab['gain']-lab['loss'],utility_upper_bound=1. if unknown else lab['gain']-lab['loss'],
                rr_lower_bound=float(not unknown and lab['all_ac']),rr_upper_bound=float(unknown or lab['all_ac']),
                loss_fraction_lower_bound=0. if unknown else lab['loss'],regression_rate_lower_bound=float(not unknown and lab['loss']>0),regression_rate_upper_bound=float(unknown or lab['loss']>0),
                edit_tokens=p['candidate_edit_tokens'][cid],unknown=float(unknown),noop=float(cid==p['choices']['noop'])))
        results[condition]=dict(metrics=metrics(values),predictions=values,counts={k:sum(v[k] for v in values) for k in ('rr_lower_bound','rr_upper_bound','regression_rate_lower_bound','regression_rate_upper_bound','unknown','noop')})
    contrasts={}
    for other in ('C','U','first_attempt'):
        pairs=list(zip(results['H']['predictions'],results[other]['predictions']))
        # Identical candidate evidence is shared, so its paired difference is
        # exactly zero even when execution is unknown.
        bounds=[(0.,0.) if h['candidate_id']==c['candidate_id'] else (h['utility']-c['utility_upper_bound'],h['utility_upper_bound']-c['utility']) for h,c in pairs]
        contrasts['H-'+other]=dict(net_gain_mean_lower_bound=sum(x[0] for x in bounds)/len(bounds),net_gain_mean_upper_bound=sum(x[1] for x in bounds)/len(bounds),conservative_scoring_difference=sum(h['utility']-c['utility'] for h,c in pairs)/len(pairs),different_choices=sum(h['candidate_id']!=c['candidate_id'] for h,c in pairs),examples=len(pairs))
    has_ac={bid:any(lab['status']=='stable' and lab['all_ac'] for (b,_),lab in label_map.items() if b==bid) for bid in banks}
    oracle_diagnostics=dict(stable_only_utility_oracle_NOT_DEPLOYABLE=results.pop('stable_only_utility_oracle_NOT_DEPLOYABLE'),
        banks=len(banks),banks_with_stable_ac=sum(has_ac.values()),
        banks_with_unknown_candidates=sum(any(lab['status']=='unknown' for (b,_),lab in label_map.items() if b==bid) for bid in banks),
        attempt_status_counts=dict(Counter(a.status for bank in banks.values() for a in bank.attempts)),
        candidate_count=len(label_map),unknown_candidate_count=sum(lab['status']=='unknown' for lab in label_map.values()),
        h_known_nonac_with_stable_ac_available=sum(has_ac[p['bank_id']] and label_map[p['bank_id'],p['choices']['H']]['status']=='stable' and not label_map[p['bank_id'],p['choices']['H']]['all_ac'] for p in preds),
        note='Outcome-only upper-bound diagnostics, never deployed or model-selected; stable-only oracle falls back to unknown noop if no stable candidate exists.')
    report=dict(kind='frozen_development_replication',confirmatory=False,trained=False,model_selection_changed=False,
        primary='H-C paired net gain',contrasts=contrasts,results=results,oracle_diagnostics=oracle_diagnostics,first_attempt_status_counts=dict(Counter(p['first_attempt_status'] for p in preds)),
        note='Frozen original 64-train/32-validation coefficients. New development users only. No significance testing. Unknown utility interval [-1,1]; shared unknown choices cancel in paired contrasts.',
        prediction_complete_sha256=sha(predictions/'COMPLETE.json'),evaluation_complete_sha256=sha(labels.parent/'COMPLETE.json'))
    output.mkdir(parents=True,exist_ok=False); write(output/'report.json',report)
    write(output/'COMPLETE.json',{'report_sha256':sha(output/'report.json')})
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='mode',required=True)
    p=sub.add_parser('predict')
    for name in ('observations','banks','parent-report','parent-complete','output'):
        p.add_argument('--'+name,required=True,type=Path)
    p=sub.add_parser('assess')
    for name in ('predictions','labels','output'):
        p.add_argument('--'+name,required=True,type=Path)
    args=vars(parser.parse_args(argv)); mode=args.pop('mode')
    (predict if mode=='predict' else assess)(**args)


if __name__=='__main__':
    main()
