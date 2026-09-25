"""Post-completion top-set training/OOF diagnosis; never fit or refit.

Each fold function receives only its own training labels. After all five own
parts are saved, their agreeing label copies support a descriptive old/new OOF
join. These are repeated development observations, not fresh evaluation data.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import platform
import tarfile

from scripts import diagnose_zpd_joint_training_objective as old
import numpy as np
from scipy import sparse
import scipy

p=old.prior
require=p.require
METHODS=('H','C_joint','shared_H_HS','shared_H_Jm','shared_H_CF')
PINS=dict(run='8b738b124da9f8af2941d502e9ba0f7c5e2b6248094c03ca68bade6bbebc87bf',
    outer='5b07dabf77340d99438b767f5055fe45d5617bbc28248003cb77d2d2464a29cf',
    numerical='0e8411f3b8f02a741089b0d9fc6ca4d6e6727556dffc2e9ecd3adc8b2a75a67e',
    prepared='71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e',
    old_diagnosis='b27e5e8a2ec093c9c298126c03ed912b6eddb7627ba514c1b84de846f3cea852',
    source_tar='12e7f528c2a240baa9d3361ef58001288e0c563731a81280a8df49a15aeff3e8')
OLD_HELPER_SHA='57da5f85b22cf4b75f042bf494150a685caab7bdf9c5ff1d4541c49a62417624'
PRIOR_HELPER_SHA='aacc2a695823c8bc3363f3700040d84d5307acdc6b5dab7d9df0c06e8c846010'
OUTPUT='outputs/zpd-bank-topset-training-diagnosis-20260925/diagnostic-v1'


def canonical_hash(value):
    return p.digest(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode())


def sum_pairs(values):
    values=list(values)
    return {key:sum(row.get(key,0) for row in values) for key in sorted({k for row in values for k in row})}


def perturbation_certificate(ids,left,right):
    """Sufficient rank-invariance bound on supplied float64 score vectors.

Fractions make the gap/perturbation comparison exact for those finite scores,
not for an unrounded real model. No tunable tolerance or near-tie reassignment.
"""
    require(bool(ids) and set(left)==set(right)==set(ids),'exact score candidate coverage required')
    require(all(type(s[c]) in (int,float) and math.isfinite(s[c]) for s in (left,right) for c in ids),'finite real scores required')
    winner=p.chosen(ids,left);others=[c for c in ids if c!=winner]
    a={c:Fraction.from_float(float(left[c])) for c in ids};b={c:Fraction.from_float(float(right[c])) for c in ids}
    changes=[a[c]-b[c] for c in ids];span=max(changes)-min(changes)
    gap=None if not others else a[winner]-max(a[c] for c in others)
    certificate=not others or span==0 or gap>span
    unchanged=winner==p.chosen(ids,right)
    require(not certificate or unchanged,'exact sufficient score-vector bound contradicted')
    return dict(maximum_pairwise_score_perturbation=float(span),winner_runner_up_gap=None if gap is None else float(gap),
        decision_invariant_certificate=certificate,choice_unchanged=unchanged,
        exact_fraction_comparison=True,bound_is_sufficient_not_necessary=True)


def score_bank(inp,ex,scaler,theta,local):
    bid=ex['bank_id'];bank=inp['banks'][bid];ids=tuple(bank['candidate_ids'])
    require(set(local)==set(ids),'all candidate labels retained')
    current,phi=p.matrices(inp['raw_current'][bid],{a:inp['interactions'][a][bid] for a in p.ARMS[:-1]},scaler['numeric_scale'],ids)
    matrices={a:sparse.hstack([current,sparse.csr_matrix(phi[a])],format='csr') for a in ('H','C_joint','HS','Jm','CF')}
    scores={}
    for method,arm in (('H','H'),('C_joint','C_joint'),('shared_H_HS','HS'),('shared_H_Jm','Jm'),('shared_H_CF','CF')):
        coefficient=theta['C_joint' if method=='C_joint' else 'H']
        values=np.asarray(matrices[arm]@coefficient).ravel()
        require(np.isfinite(values).all(),'finite native4131 saved-theta score required')
        scores[method]=dict(zip(ids,map(float,values),strict=True))
    components=dict(current4099=np.asarray(current@theta['H'][:4099]).ravel(),
        G16=phi['H'][:,:16]@theta['H'][4099:4115],residual16=phi['H'][:,16:]@theta['H'][4115:])
    for i,cid in enumerate(ids):
        require(math.isclose(math.fsum(float(v[i]) for v in components.values()),scores['H'][cid],abs_tol=1e-10,rel_tol=1e-10),'H component additivity differs')
    noop=p.digest(bytes.fromhex(bank['current_source_hex']));require(noop in ids,'current/noop source SHA differs')
    choices={m:p.chosen(ids,scores[m]) for m in METHODS}
    ac=[cid for cid in ids if old.status(local[cid])=='known_ac']
    margins={}
    for method in METHODS:
        best=p.chosen(ac,scores[method]) if ac else None;selected=choices[method]
        others=[c for c in ids if c!=selected]
        margins[method]=dict(best_known_ac=best,selected_minus_best_known_ac=None if best is None else scores[method][selected]-scores[method][best],
            winner_runner_up_gap=None if not others else scores[method][selected]-max(scores[method][c] for c in others))
    best=margins['H']['best_known_ac'];chosen=choices['H']
    decomposition=None if best is None else {name:float(v[ids.index(chosen)]-v[ids.index(best)]) for name,v in components.items()}
    result=dict(example_id=ex['example_id'],user_id=ex['user_id'],bank_id=bid,problem_id=bank['problem_id'],
        bank_seal_sha256=bank['bank_seal_sha256'],training_model_fold=inp['fold'],
        held_fold=inp['assignment']['example_fold'][ex['example_id']],current_status=old.status(local[noop]),
        candidate_ids=list(ids),noop_id=noop,candidate_labels=local,known_ac_oracle=bool(ac),
        possible_ac_oracle=any(old.status(v)!='known_nonac' for v in local.values()),
        methods={m:old.outcome(choices[m],local,noop) for m in METHODS},scores=scores,
        score_spreads={name:float(np.ptp(v)) for name,v in components.items()}|{
            'history32':float(np.ptp(components['G16']+components['residual16'])),
            'H_total':float(np.ptp(list(scores['H'].values())))},
        H_component_scores={name:dict(zip(ids,map(float,v),strict=True)) for name,v in components.items()},
        method_margins=margins,H_selected_minus_best_known_ac_components=decomposition,
        paired_controls={m:p.paired(chosen,choices[m],noop,local) for m in METHODS[1:]},
        shared_H_perturbation={m:perturbation_certificate(ids,scores['H'],scores[m]) for m in METHODS[2:]},
        exact_H_feature_equal={a:bool(np.array_equal(phi['H'],phi[a])) for a in ('HS','Jm','CF')})
    return result,matrices


def fold_calculation(inp,envelope,contract,scaler,plan,models):
    """Pure own-scope calculation: no cross-fold/OOF labels or model fitting."""
    train,held,labels=old.own_scope(inp,envelope,contract)
    require(set(models)=={'H','C_joint'},'exact H and C_joint saved models required')
    keys,y,pairweights,_,training,_=old.pair_plan(train,inp['banks'],labels)
    require(training==scaler['training'] and [list(v) for v in keys]==scaler['row_keys']
        and y.tolist()==scaler['y'] and pairweights.tolist()==scaler['weights'],'original own pair/scaler ancestry differs')
    require(plan['plan_sha256']==canonical_hash({k:v for k,v in plan.items() if k!='plan_sha256'})
        and plan['original_pair_plan']['training']==training
        and plan['own_labels_sha256']==canonical_hash([labels[ex['bank_id'],cid] for ex in train for cid in inp['banks'][ex['bank_id']]['candidate_ids']]),'saved top-set plan ancestry differs')
    theta={}
    for arm,outer in models.items():
        require(outer['kind']=='bank_topset4131_own_fold_model_v1' and outer['arm']==arm and outer['fold']==inp['fold']
            and outer['train_example_ids']==[e['example_id'] for e in train] and outer['held_example_ids']==[e['example_id'] for e in held]
            and outer['label_contract']==contract and outer['transform_sha256']==canonical_hash(scaler)
            and outer['plan_sha256']==canonical_hash(plan)
            and outer['model_sha256']==canonical_hash({k:v for k,v in outer.items() if k!='model_sha256'}),'saved new model scope/hash differs')
        model=outer['top_model']
        require(model['configuration']['kind']=='fixed_repair_bank_topset_newton_v1'
            and model['model_sha256']==canonical_hash({k:v for k,v in model.items() if k!='model_sha256'})
            and type(model['coefficients']) is list and len(model['coefficients'])==4131
            and all(type(v) in (int,float) and math.isfinite(v) for v in model['coefficients']),'saved native new-model coefficient identity differs')
        theta[arm]=np.asarray(model['coefficients'],dtype=np.float64)
    require(not np.any(theta['C_joint'][4099:]),'current-only model must have exact zero tail')
    masses={ex['bank_id']:[] for ex in train}
    for (bid,_,_),weight in zip(keys,pairweights,strict=True):masses[bid].append(float(weight))
    rows=[];stable_features={a:[] for a in models};tops=[];weights=[]
    for ex in train:
        bid=ex['bank_id'];ids=inp['banks'][bid]['candidate_ids'];local={cid:labels[bid,cid] for cid in ids}
        row,matrices=score_bank(inp,ex,scaler,theta,local);rows.append(row)
        stable=[i for i,cid in enumerate(ids) if old.preference(local[cid]) is not None]
        if stable:
            values=[old.preference(local[ids[i]]) for i in stable];top=tuple(i for i,v in enumerate(values) if v==max(values))
            tops.append(np.asarray(top,dtype='<i8'));weights.append(math.fsum(masses[bid]))
            for arm in models:stable_features[arm].append(matrices[arm][stable].toarray().astype('<f8'))
        else:require(not masses[bid],'unknown-only bank acquired objective mass')
    input_hashes={a:dict(features=old.array_hash(*stable_features[a]),top_indices=old.array_hash(*tops),weights=old.array_hash(np.asarray(weights,dtype='<f8'))) for a in models}
    require(all(input_hashes[a]==models[a]['top_model']['input_sha256'] for a in models),'reconstructed raw bank objective identity differs')
    return dict(fold=inp['fold'],train_examples=len(train),held_examples=len(held),input_sha256_matched=input_hashes,
        coefficient_norms={a:{name:float(np.linalg.norm(t[lo:hi])) for name,lo,hi in (('current4099',0,4099),('G16',4099,4115),('residual16',4115,4131))} for a,t in theta.items()},
        summary=summarize(rows),incidences=rows),theta


def summarize(rows):
    result=dict(incidences=len(rows),unique_banks=len({r['bank_id'] for r in rows}),known_ac_oracle=sum(r['known_ac_oracle'] for r in rows),
        possible_ac_oracle=sum(r['possible_ac_oracle'] for r in rows))
    result['methods']={m:{k:sum(r['methods'][m][k] for r in rows) for k in ('known_ac','known_regression','unknown','noop')}|{
        'known_ac_misses':sum(r['known_ac_oracle'] and not r['methods'][m]['known_ac'] for r in rows)} for m in METHODS}
    result['paired_controls']={m:sum_pairs(r['paired_controls'][m] for r in rows) for m in METHODS[1:]}
    result['shared_H_perturbation']={m:dict(certificate=sum(r['shared_H_perturbation'][m]['decision_invariant_certificate'] for r in rows),
        actually_unchanged=sum(r['shared_H_perturbation'][m]['choice_unchanged'] for r in rows)) for m in METHODS[2:]}
    return result


def compare_training(rows,old_rows):
    previous={(r['training_model_fold'],r['example_id']):r for r in old_rows}
    require(len(previous)==len(old_rows)==len(rows)
        and {(r['training_model_fold'],r['example_id']) for r in rows}==set(previous),'old/new complete incidence counts differ')
    comparisons=[]
    for row in rows:
        key=row['training_model_fold'],row['example_id'];require(key in previous,'missing old training role')
        before=previous[key];labels=row['candidate_labels'];noop=row['noop_id']
        require(before['bank_id']==row['bank_id'] and before['held_fold']==row['held_fold']
            and before['current_status']==row['current_status'],'old/new incidence identity differs')
        cid=before['methods']['H']['candidate_id'];require(cid in labels,'old selected candidate absent')
        require(old.outcome(cid,labels,noop)==before['methods']['H'],'old outcome and agreeing own labels differ')
        comparisons.append(dict(example_id=row['example_id'],bank_id=row['bank_id'],training_model_fold=key[0],
            old_H=before['methods']['H'],new_H=row['methods']['H'],new_C_joint=row['methods']['C_joint'],
            paired={m:p.paired(row['methods'][m]['candidate_id'],cid,noop,labels) for m in ('H','C_joint')}))
    return dict(incidences=comparisons,old_training_H={k:sum(r['old_H'][k] for r in comparisons) for k in ('known_ac','known_regression','unknown','noop')},
        paired={m:sum_pairs(r['paired'][m] for r in comparisons) for m in ('H','C_joint')})


def consensus_labels(rows):
    """Called only after own result parts are written; four agreeing roles."""
    labels={};roles={}
    for row in rows:
        bid=row['bank_id'];fold=row['training_model_fold']
        roles.setdefault(bid,set());require(fold not in roles[bid],'duplicate bank training role');roles[bid].add(fold)
        if bid in labels:require(labels[bid]==row['candidate_labels'],'own envelope label copies disagree')
        else:labels[bid]=row['candidate_labels']
    require(all(len(v)==4 for v in roles.values()),'four own-training label copies required')
    return labels


def cross_roles(training,old_training,oof,old_predictions):
    old_lookup={r['example_id']:r for r in old_predictions};groups={r['example_id']:[] for r in oof}
    oldgroups={k:[] for k in groups}
    for row in training:require(row['example_id'] in groups,'extra new training identity');groups[row['example_id']].append(row)
    for row in old_training:require(row['example_id'] in oldgroups,'extra old training identity');oldgroups[row['example_id']].append(row)
    require(len(old_lookup)==len(old_predictions)==len(oof),'all old/new OOF IDs required')
    result=[]
    for row in oof:
        eid=row['example_id'];f=row['held_fold'];before=old_lookup[eid];g=groups[eid];og=oldgroups[eid]
        require(len(g)==len(og)==4 and {r['training_model_fold'] for r in g}=={r['training_model_fold'] for r in og}==set(range(5))-{f}
            and before['fold']==f and before['bank_id']==row['bank_id'],'exact train/held four-role join required')
        label=row['candidate_labels'];oldid=before['choices']['H'];oldout=old.outcome(oldid,label,row['noop_id'])
        result.append(dict(example_id=eid,bank_id=row['bank_id'],problem_id=row['problem_id'],held_fold=f,current_status=row['current_status'],
            known_ac_oracle=row['known_ac_oracle'],old_training_H_ac_roles=sum(r['methods']['H']['known_ac'] for r in og),
            new_training_H_ac_roles=sum(r['methods']['H']['known_ac'] for r in g),
            new_training_C_joint_ac_roles=sum(r['methods']['C_joint']['known_ac'] for r in g),
            old_oof_H=oldout,new_oof_methods=row['methods'],
            paired_new_vs_old={m:p.paired(row['methods'][m]['candidate_id'],oldid,row['noop_id'],label) for m in ('H','C_joint')}))
    def table(selected):return dict(banks=len(selected),role_counts={name:{str(n):sum(r[name]==n for r in selected) for n in range(5)}
        for name in ('old_training_H_ac_roles','new_training_H_ac_roles','new_training_C_joint_ac_roles')})
    return dict(rows=result,all_banks=table(result),known_ac_oracle=table([r for r in result if r['known_ac_oracle']]),
        old_oof_H={k:sum(r['old_oof_H'][k] for r in result) for k in ('known_ac','known_regression','unknown','noop')},
        old_oof_misses_posthoc=table([r for r in result if r['known_ac_oracle'] and not r['old_oof_H']['known_ac']]),
        new_oof_misses_posthoc=table([r for r in result if r['known_ac_oracle'] and not r['new_oof_methods']['H']['known_ac']]),
        paired_new_vs_old={m:sum_pairs(r['paired_new_vs_old'][m] for r in result) for m in ('H','C_joint')})


def main(argv=None):
    parser=argparse.ArgumentParser(__doc__)
    for name in ('archive','source-tar','prepared','old-diagnosis','old-archive','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args(argv);project=Path(__file__).resolve().parents[1]
    output=p.canonical(args.output);require(output==project/OUTPUT and not output.exists(),'fixed fresh diagnostic output required')
    source_files=(Path(__file__).resolve(),project/'tests/test_zpd_bank_topset_training.py',Path(old.__file__).resolve(),Path(p.__file__).resolve())
    source_pins={str(path):p.digest(path.read_bytes()) for path in source_files}
    require(source_pins[str(Path(old.__file__).resolve())]==OLD_HELPER_SHA and source_pins[str(Path(p.__file__).resolve())]==PRIOR_HELPER_SHA,'reviewed diagnostic helper changed')
    reader=p.Reader(args.archive);prep_reader=p.Reader(args.prepared);previous=p.Reader(args.old_diagnosis);old_archive=p.Reader(args.old_archive)
    outer=reader.seal('supervised-v1',PINS['outer']);run=reader.seal('run-v1',PINS['run']);verified=reader.seal('verified-v1',PINS['numerical'])
    require(outer['experiment_complete_sha256']==PINS['run'] and outer['audit_complete_sha256']==PINS['numerical']
        and run['completed_fits']==35 and run['recipients']==320,'complete new35/320 and independent numerical links required')
    audit=reader.json('verified-v1/report.json',verified['files_sha256']['report.json'])
    require(audit['verified'] is True and (audit['models'],audit['recipients'],audit['methods'])==(35,320,14),'accepted full numerical replay required')
    manifest=reader.json('run-v1/manifest.json',run['files_sha256']['manifest.json'])
    release=reader.json('release.json',manifest['release_sha256'])
    prepared=prep_reader.json('COMPLETE.json',PINS['prepared'])
    tar_path=p.canonical(args.source_tar);require(p.digest(tar_path.read_bytes())==PINS['source_tar'],'execution source tar differs')
    jobs={f:reader.json(f'jobs/fold-{f}.json',manifest['job_sha256'][str(f)]) for f in range(5)}
    with tarfile.open(tar_path) as source:
        require(all(j['source_sha256']==release['source_sha256'] for j in jobs.values()),'executed source closure differs')
        for name,pin in release['source_sha256'].items():
            member=source.getmember(name);require(member.isfile() and p.digest(source.extractfile(member).read())==pin,'executed source bytes differ')
    def barrier():
        require(all(p.digest(Path(path).read_bytes())==pin for path,pin in source_pins.items()),'diagnostic source/test drift')
        require(p.digest(tar_path.read_bytes())==PINS['source_tar'],'execution tar drift')
        for r in (reader,prep_reader,previous,old_archive):r.recheck()
    output.mkdir(parents=True);files={};folds=[];thetas={};scalers={}
    def save(name,value):files[name]=p.write_new(output/name,p.encoded(value))
    try:
        for f in range(5):
            job=jobs[f];inp=job['inputs'];contract=job['own_label_contract']
            require(inp['fold']==f and inp['synthetic'] is False and len(inp['examples'])==320,'full original production fold required')
            require(len({inp['banks'][e['bank_id']]['problem_id'] for e in inp['examples']})==23
                and sum(len(inp['banks'][e['bank_id']]['candidate_ids']) for e in inp['examples'])==2544,'all23 problems/2544 candidates retained')
            name=f'fold-{f}/train-labels.json';pin=contract['expected_sha256'];require(prepared['files_sha256'][name]==pin,'own label ancestry differs')
            envelope=prep_reader.json(name,pin);require(envelope['parent_complete_sha256']==prepared['parent_complete_sha256'],'own label parent differs')
            scalers[f]=reader.json(f'run-v1/fold-{f}/SCALER.json',run['files_sha256'][f'fold-{f}/SCALER.json'])
            require(scalers[f]==job['transform'],'saved original transform changed')
            plan=reader.json(f'run-v1/fold-{f}/PLAN.json',run['files_sha256'][f'fold-{f}/PLAN.json'])
            models={a:reader.json(f'run-v1/fold-{f}/{a}.json',run['files_sha256'][f'fold-{f}/{a}.json']) for a in ('H','C_joint')}
            result,thetas[f]=fold_calculation(inp,envelope,contract,scalers[f],plan,models);del envelope
            barrier();save(f'fold-{f}.json',result);folds.append(result)
            print(json.dumps(dict(phase='own_training',completed_incidences=sum(r['train_examples'] for r in folds),total_incidences=1280)),flush=True)
        rows=[r for fold in folds for r in fold['incidences']]
        require(len(rows)==1280 and len({r['bank_id'] for r in rows})==320,'all1280 training incidences/320 banks required')
        save('OWN_PARTS_COMPLETE.json',dict(status='complete',files_sha256=dict(files),training_incidences=1280))
        # No OOF scoring/old-new joins before all own parts above are sealed.
        consensus=consensus_labels(rows)
        oldseal=previous.json('COMPLETE.json',PINS['old_diagnosis'])
        oldfolds=[previous.json(f'fold-{f}.json',oldseal['files_sha256'][f'fold-{f}.json']) for f in range(5)]
        oldrows=[r for fold in oldfolds for r in fold['incidences']]
        comparison=compare_training(rows,oldrows)
        predictions=reader.json('run-v1/predictions.json',run['files_sha256']['predictions.json'])
        oldrun=old_archive.json('run-v1/COMPLETE.json',p.PINS['run'])
        oldpred=old_archive.json('run-v1/predictions.json',oldrun['files_sha256']['predictions.json'])
        require(len(predictions)==len({r['example_id'] for r in predictions})==320,'exact OOF320 required')
        oof=[]
        for pred in predictions:
            f=pred['fold'];inp=jobs[f]['inputs'];ex=next(e for e in inp['examples'] if e['example_id']==pred['example_id'])
            require(inp['assignment']['example_fold'][ex['example_id']]==f and ex['bank_id']==pred['bank_id'],'OOF identity differs')
            row,_=score_bank(inp,ex,scalers[f],thetas[f],consensus[ex['bank_id']])
            for method in METHODS:
                require(row['methods'][method]['candidate_id']==pred['choices'][method]
                    and set(row['scores'][method])==set(pred['candidate_scores'][method])
                    and all(math.isclose(s,pred['candidate_scores'][method][cid],abs_tol=1e-10,rel_tol=1e-10) for cid,s in row['scores'][method].items()),'OOF saved score or exact selected SHA differs')
            oof.append(row)
        report=reader.json('run-v1/report.json',run['files_sha256']['report.json'])
        result=dict(kind='bank_topset_completed_training_diagnosis_v1',verification_status='provisional_pending_independent_review',
            whole_training=summarize(rows),training_comparison=comparison,cross_roles=cross_roles(rows,oldrows,oof,oldpred),
            oof=summarize(oof),oof_rows=oof,folds={str(f['fold']):dict(summary=f['summary'],coefficient_norms=f['coefficient_norms'],input_sha256_matched=f['input_sha256_matched']) for f in folds},
            current_status={s:summarize([r for r in rows if r['current_status']==s]) for s in ('known_ac','known_nonac','unknown')},
            scientific_gate_unchanged=report['gate'],provenance=dict(input_sha256={str(r.root):dict(r.bindings) for r in (reader,prep_reader,previous,old_archive)},
                execution_source_tar_sha256=PINS['source_tar'],diagnostic_source_sha256=source_pins,
                runtime=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__)),
            scope=dict(fitting=False,scaler_refitting=False,Hessian_replay=False,fresh_outcomes=False,assessment_label_body_opened=False,
                exclusions=0,old_all320_posthoc=True,repeated_training_incidences_not_independent_samples=True,
                causal_history_or_objective_effect_established=False,local_uniqueness_implies_linear_realizability=False))
        save('report.json',result);barrier()
        require(all(p.digest((output/name).read_bytes())==pin for name,pin in files.items()),'diagnostic output drift')
        complete=p.write_new(output/'COMPLETE.json',p.encoded(dict(status='complete',verification_status='provisional_pending_independent_review',files_sha256=files,
            training_incidences=1280,banks=320,fitting_performed=False)))
        barrier();require(p.digest((output/'COMPLETE.json').read_bytes())==complete and all(p.digest((output/name).read_bytes())==pin for name,pin in files.items()),'terminal output drift')
    except BaseException as error:
        if (output/'COMPLETE.json').exists():(output/'COMPLETE.json').rename(output/'REJECTED_COMPLETE.json')
        p.write_new(output/'FAILED.json',p.encoded(dict(status='failed',error_type=type(error).__name__,error=str(error))))
        raise


if __name__=='__main__':main()
