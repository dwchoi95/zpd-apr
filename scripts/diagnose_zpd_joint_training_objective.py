"""Post-completion own-training diagnosis; no fit, scaler fit or new outcomes.

Each fold calculation receives only its own training envelope. All five saved
models are scored at their saved coefficients; a later cross-role join uses an
already sealed OOF diagnosis. Training incidences are not independent samples.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
import platform
import tarfile

from scripts import diagnose_zpd_joint_progress as prior
import numpy as np
from scipy import sparse
from scipy.special import expit
import scipy

require = prior.require
CLASSES = ('ac_nonac', 'nonac_preservation', 'nonac_net_gain')
METHODS = ('H', 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF')
PRIOR_SOURCE_SHA = 'aacc2a695823c8bc3363f3700040d84d5307acdc6b5dab7d9df0c06e8c846010'
OOF_COMPLETE_SHA = 'b480e27fdd10cc6b8ace8754bf44863a51f924512a55b84a4db1d005be8ab818'
OOF_REPORT_SHA = '54517b987ff866a8c7ca06fdb784dec8eae038107dd1bbbd07586cf329c0c2b3'
OUTPUT = 'outputs/zpd-joint-training-diagnosis-20260925/diagnostic-v1'


def preference(row):
    require(set(row) == {'bank_id','candidate_id','status','gain','loss','all_ac'}, 'exact core label fields required')
    if row['status'] == 'unknown':
        require(all(row[k] is None for k in ('gain','loss','all_ac')), 'unknown remains null')
        return None
    require(row['status'] == 'stable' and type(row['all_ac']) is bool
        and all(type(row[k]) in (int,float) and math.isfinite(row[k]) and 0 <= row[k] <= 1 for k in ('gain','loss'))
        and row['gain']+row['loss'] <= 1+1e-12 and (not row['all_ac'] or row['loss'] == 0), 'invalid stable core label')
    return int(row['all_ac']), int(row['loss'] == 0), row['gain']-row['loss']


def own_scope(inp, envelope, contract):
    """Reject held/extra/missing keys BEFORE inspecting any label value."""
    fold = inp['fold']; assignment = inp['assignment']['example_fold']
    require(type(fold) is int and 0 <= fold < 5, 'exact fold required')
    examples = inp['examples']
    require(len({e['example_id'] for e in examples}) == len(examples)
        and set(assignment) == {e['example_id'] for e in examples}
        and all(type(f) is int and 0 <= f < 5 for f in assignment.values()), 'exact source/assignment coverage required')
    train = [e for e in examples if assignment[e['example_id']] != fold]
    held = [e for e in examples if assignment[e['example_id']] == fold]
    mapping = {e['example_id']:e['bank_id'] for e in train}
    fields = {'kind','fold','parent_complete_sha256','fold_assignment_sha256','source_binding_sha256','example_bank_ids','bank_seals','labels'}
    require(set(envelope) == fields and envelope['kind'] == 'repair_feedback_fold_training_labels_v1'
        and type(envelope['fold']) is int and envelope['fold'] == fold
        and envelope['example_bank_ids'] == mapping
        and envelope['fold_assignment_sha256'] == contract['expected_fold_assignment_sha256'] == inp['fold_assignment_sha256']
        and envelope['source_binding_sha256'] == contract['expected_source_binding_sha256'], 'own envelope contract/scope differs')
    require(envelope['bank_seals'] == {bid:inp['banks'][bid]['bank_seal_sha256'] for bid in mapping.values()}, 'own bank seal mismatch')
    labels = {(row['bank_id'],row['candidate_id']):row for row in envelope['labels']}
    expected = {(bid,cid) for bid in mapping.values() for cid in inp['banks'][bid]['candidate_ids']}
    require(len(labels) == len(envelope['labels']) and set(labels) == expected, 'exact own candidate label scope required')
    for row in labels.values(): preference(row)
    return train, held, labels


def array_hash(*arrays):
    sha = hashlib.sha256()
    for array in arrays:
        array = np.ascontiguousarray(array)
        header = json.dumps(dict(shape=list(array.shape),dtype=array.dtype.str),sort_keys=True,separators=(',',':')).encode()
        for block in (header,array.tobytes(order='C')):
            sha.update(len(block).to_bytes(8,'little'));sha.update(block)
    return sha.hexdigest()


def pair_plan(train, banks, labels):
    """Reconstruct legacy relation/order/weights independently; no producer call."""
    records=[]; bank_counts={}; stable_counts={}
    for ex in train:
        bid=ex['bank_id'];ids=banks[bid]['candidate_ids'];keys=[preference(labels[bid,c]) for c in ids]
        stable=[i for i,k in enumerate(keys) if k is not None]
        pairs=[]
        for a,b in combinations(stable,2):
            if keys[a] != keys[b]:
                category = CLASSES[next(i for i in range(3) if keys[a][i] != keys[b][i])]
                pairs.append((a,b,int(keys[a] > keys[b]),category))
        bank_counts[bid]=dict(candidates=len(ids),stable_candidates=len(stable),unknown_candidates=len(ids)-len(stable),
            pairs_with_unknown=len(ids)*(len(ids)-1)//2-len(stable)*(len(stable)-1)//2,
            stable_tied_pairs=len(stable)*(len(stable)-1)//2-len(pairs),informative_unordered_pairs=len(pairs))
        stable_counts[bid]=len(stable)
        if pairs:records.append((ex,pairs))
    require(bool(records),'no informative training pairs')
    prefixes=Counter(ex['user_id'] for ex,_ in records);all_users={ex['user_id'] for ex in train}
    rows=[];y=[];weight=[];categories=[];example_ids=[]
    for ex,pairs in records:
        bid=ex['bank_id'];ids=banks[bid]['candidate_ids']
        for a,b,target,category in pairs:
            rows.extend(((bid,ids[a],ids[b]),(bid,ids[b],ids[a])))
            y.extend((target,1-target));weight.extend([1/(prefixes[ex['user_id']]*len(pairs)*2)]*2)
            categories.extend((category,category));example_ids.extend([ex['example_id']]*2)
    weights=np.asarray(weight,dtype=np.float64)
    weights *= len(weights)/weights.sum();old_mass=float(weights.sum());weights=weights*(1900./old_mass)
    informative=[ex['example_id'] for ex,_ in records]
    training=dict(train_prefixes=len(train),train_users=len(all_users),informative_train_prefixes=len(records),
        uninformative_train_prefixes=len(train)-len(records),users=len(prefixes),users_without_informative_prefix=len(all_users-set(prefixes)),
        ordered_pairs=len(rows),pair_example_ids=example_ids,informative_train_example_ids=informative,
        uninformative_train_example_ids=sorted({ex['example_id'] for ex in train}-set(informative)),
        stable_train_candidates=sum(stable_counts[ex['bank_id']] for ex,_ in records),
        weight_normalization='fixed_reference_total_pair_weight',reference_pair_weight=1900.,
        sample_weight_sum=float(weights.sum()),prior_mean_one_weight_sum=old_mass)
    return rows,np.asarray(y,dtype=np.int64),weights,categories,training,bank_counts


def numerical_check(matrix,y,weights,theta,model):
    matrix.sum_duplicates();matrix.eliminate_zeros();matrix.sort_indices()
    hashes=dict(features=array_hash(np.asarray(matrix.shape,dtype='<i8'),matrix.indptr.astype('<i8'),matrix.indices.astype('<i8'),matrix.data.astype('<f8')),
        labels=array_hash(y.astype('<i8')),weights=array_hash(weights.astype('<f8')),base_margin=array_hash(np.zeros(len(y),dtype='<f8')))
    require(hashes == model['training']['input_sha256'], 'independent train array SHA mismatch')
    signed=2.*y-1.;margins=signed*np.asarray(matrix@theta).ravel();losses=np.logaddexp(0.,-margins)
    gradient=theta-.1*np.asarray(matrix.T@(weights*signed*expit(-margins))).ravel()
    loss=.1*float(np.dot(weights,losses));penalty=.5*float(np.dot(theta,theta));objective=loss+penalty
    require(np.isfinite(gradient).all() and np.max(np.abs(gradient)) <= 1e-8, 'saved solution fresh gradient fails frozen limit')
    opt=model['optimization']
    require(all(math.isclose(actual,opt[name],abs_tol=1e-10,rel_tol=1e-10)
        for name,actual in [('objective',objective),('weighted_logistic_loss',loss),('l2_penalty',penalty)]), 'fresh objective mismatch')
    require(np.allclose(gradient,model['final_gradient'],rtol=1e-10,atol=1e-10), 'fresh gradient vector differs')
    return margins,losses,dict(input_sha256=hashes,objective=objective,C_weighted_logistic_loss=loss,
        penalty=penalty,fresh_gradient_infinity=float(np.max(np.abs(gradient))),weight_mass=math.fsum(map(float,weights)))


def pair_stats(indices,weights,margins,losses):
    ids=np.asarray(list(indices),dtype=np.int64);w=weights[ids];m=margins[ids];loss=losses[ids]
    mass=math.fsum(map(float,w));correct=math.fsum(map(float,w[m>0]))
    return dict(mirrored_rows=len(ids),unordered_pairs=len(ids)//2,weight_mass=mass,
        weighted_logistic_loss=math.fsum(map(float,w*loss)),C_weighted_logistic_loss=.1*math.fsum(map(float,w*loss)),
        positive_margin_rows=int(np.sum(m>0)),negative_margin_rows=int(np.sum(m<0)),zero_margin_rows=int(np.sum(m==0)),
        correctly_signed_weight=correct,wrong_signed_weight=math.fsum(map(float,w[m<0])),zero_margin_weight=math.fsum(map(float,w[m==0])),
        weighted_sign_accuracy=None if not mass else correct/mass)


def class_gradients(matrix,y,weights,categories,theta):
    """Descriptive saved-solution and zero-point data gradients, no update."""
    result={};signed=2.*y-1.
    for name,point in [('saved',theta),('zero',np.zeros_like(theta))]:
        margin=signed*np.asarray(matrix@point).ravel();factor=-.1*weights*signed*expit(-margin)
        gradients={}
        for category in CLASSES:
            indices=np.asarray([i for i,c in enumerate(categories) if c==category],dtype=np.int64)
            gradients[category]=np.asarray(matrix[indices].T@factor[indices]).ravel()
        ac=gradients['ac_nonac'];acnorm=float(np.linalg.norm(ac));summary={}
        for category,g in gradients.items():
            norm=float(np.linalg.norm(g));dot=float(np.dot(g,ac))
            summary[category]=dict(l2_norm=norm,gradient_sha256=array_hash(g.astype('<f8')),
                dot_with_ac_gradient=dot,cosine_with_ac_gradient=None if norm*acnorm==0 else dot/(norm*acnorm),
                dot_with_saved_theta=float(np.dot(g,theta)),
                block_norms={block:float(np.linalg.norm(g[a:b])) for block,a,b in
                    [('current4099',0,4099),('G16',4099,4115),('residual16',4115,4131)]})
        combined=sum(gradients.values(),np.zeros_like(theta))
        result[name]=dict(classes=summary,data_gradient_l2=float(np.linalg.norm(combined)),
            regularized_gradient_infinity=float(np.max(np.abs(point+combined))))
    return result


def status(label):
    if label['status']=='unknown':return 'unknown'
    return 'known_ac' if label['all_ac'] else 'known_nonac'


def outcome(choice, labels, noop):
    label=labels[choice];unknown=label['status']=='unknown'
    return dict(candidate_id=choice,status=status(label),known_ac=not unknown and label['all_ac'],
        known_regression=not unknown and label['loss']>0,unknown=unknown,noop=choice==noop)


def fold_calculation(inp,envelope,contract,scaler,outer_model):
    train,held,labels=own_scope(inp,envelope,contract)
    require(outer_model['train_example_ids']==[e['example_id'] for e in train]
        and outer_model['held_example_ids']==[e['example_id'] for e in held]
        and outer_model['label_contract']==contract and outer_model['fold']==inp['fold'] and outer_model['arm']=='H','saved own model scope differs')
    theta=np.asarray(outer_model['joint_model']['coefficients'],dtype=np.float64)
    require(theta.shape==(4131,) and np.isfinite(theta).all(),'saved finite native4131 theta required')
    blocks={};scores={};orders={};noops={}
    for ex in train:
        bid=ex['bank_id'];bank=inp['banks'][bid];ids=tuple(bank['candidate_ids']);orders[bid]={c:i for i,c in enumerate(ids)}
        current,phi=prior.matrices(inp['raw_current'][bid],{a:inp['interactions'][a][bid] for a in prior.ARMS[:-1]},scaler['numeric_scale'],ids)
        blocks[bid]=sparse.hstack([current,sparse.csr_matrix(phi['H'])],format='csr')
        method_scores={}
        for method,arm in [('H','H'),('shared_H_HS','HS'),('shared_H_Jm','Jm'),('shared_H_CF','CF')]:
            x=blocks[bid] if arm=='H' else sparse.hstack([current,sparse.csr_matrix(phi[arm])],format='csr')
            values=np.asarray(x@theta).ravel();require(np.isfinite(values).all(),'nonfinite training score')
            method_scores[method]=dict(zip(ids,map(float,values)))
        scores[bid]=method_scores;noops[bid]=prior.digest(bytes.fromhex(bank['current_source_hex']))
        require(noops[bid] in ids,'source/noop identity differs')
    keys,y,weights,categories,training,bank_counts=pair_plan(train,inp['banks'],labels)
    require(training==outer_model['training']==scaler['training'],'original training metadata differs')
    require([list(v) for v in keys]==scaler['row_keys'] and y.tolist()==scaler['y'] and weights.tolist()==scaler['weights'],'saved pair order/labels/legacy weights differ')
    differences=[]
    for bid,a,b in keys[::2]:
        diff=blocks[bid][orders[bid][a]]-blocks[bid][orders[bid][b]]
        differences.extend((diff,-diff))
    matrix=sparse.vstack(differences,format='csr')
    margins,losses,numerical=numerical_check(matrix,y,weights,theta,outer_model['joint_model'])
    category_stats={name:pair_stats((i for i,v in enumerate(categories) if v==name),weights,margins,losses) for name in CLASSES}
    category_stats['all']=pair_stats(range(len(keys)),weights,margins,losses)
    row_lookup={key:i for i,key in enumerate(keys)};bank_pair_rows={bid:[] for bid in blocks}
    for i,(bid,_,_) in enumerate(keys):bank_pair_rows[bid].append(i)
    results=[]
    for ex in train:
        bid=ex['bank_id'];ids=inp['banks'][bid]['candidate_ids'];local={c:labels[bid,c] for c in ids}
        choices={m:prior.chosen(ids,scores[bid][m]) for m in METHODS}
        ac=[c for c in ids if status(local[c])=='known_ac'];possible=[c for c in ids if status(local[c])!='known_nonac']
        best=None if not ac else prior.chosen(ac,scores[bid]['H']);chosen=choices['H']
        unknown_selected=status(local[chosen])=='unknown';miss=bool(ac and status(local[chosen])!='known_ac')
        critical=[]
        if miss and not unknown_selected:
            for correct in ac:
                i=row_lookup[bid,correct,chosen];mirror=row_lookup[bid,chosen,correct]
                critical.append(dict(ac_candidate_id=correct,selected_candidate_id=chosen,
                    ac_minus_selected_margin=scores[bid]['H'][correct]-scores[bid]['H'][chosen],
                    original_mirrored_weight=float(weights[i]+weights[mirror]),
                    original_C_weighted_logistic_loss=.1*float(weights[i]*losses[i]+weights[mirror]*losses[mirror])))
        results.append(dict(example_id=ex['example_id'],bank_id=bid,problem_id=inp['banks'][bid]['problem_id'],
            user_id=ex['user_id'],training_model_fold=inp['fold'],held_fold=inp['assignment']['example_fold'][ex['example_id']],
            current_status=status(local[noops[bid]]),counts=bank_counts[bid],known_ac_oracle=bool(ac),possible_ac_oracle=bool(possible),
            known_ac_miss=miss,unknown_selected_with_known_ac=bool(ac and unknown_selected),
            methods={m:outcome(choices[m],local,noops[bid]) for m in METHODS},
            paired_shared_controls={m:prior.paired(chosen,choices[m],noops[bid],local) for m in METHODS[1:]},
            scores=scores[bid],best_H_scoring_known_ac=best,
            selected_minus_best_known_ac=None if best is None else scores[bid]['H'][chosen]-scores[bid]['H'][best],
            all_pair_statistics=pair_stats(bank_pair_rows[bid],weights,margins,losses),
            selected_wrong_vs_known_ac_critical_pairs=critical))
    return dict(fold=inp['fold'],train_examples=len(train),held_examples=len(held),numerical=numerical,
        class_gradients=class_gradients(matrix,y,weights,categories,theta),
        original_training=training,classes=category_stats,incidences=results,summary=summarize(results))


def summarize(rows):
    result=dict(training_incidences=len(rows),unique_banks=len({r['bank_id'] for r in rows}),
        known_ac_oracle=sum(r['known_ac_oracle'] for r in rows),possible_ac_oracle=sum(r['possible_ac_oracle'] for r in rows),
        known_ac_misses=sum(r['known_ac_miss'] for r in rows),unknown_selected_with_known_ac=sum(r['unknown_selected_with_known_ac'] for r in rows))
    result['methods']={m:{key:sum(r['methods'][m][key] for r in rows) for key in ('known_ac','known_regression','unknown','noop')} for m in METHODS}
    result['paired_shared_controls']={m:dict(sum((Counter(r['paired_shared_controls'][m]) for r in rows),Counter())) for m in METHODS[1:]}
    return result


def cross_roles(rows,oof_rows):
    grouped={r['example_id']:[] for r in oof_rows}
    for row in rows:
        require(row['example_id'] in grouped,'extra train example in role join');grouped[row['example_id']].append(row)
    output=[]
    for old in oof_rows:
        group=grouped[old['example_id']]
        require(len(group)==4 and {r['training_model_fold'] for r in group}==set(range(5))-{old['fold']}
            and all(r['bank_id']==old['bank_id'] and r['held_fold']==old['fold'] and r['current_status']==old['current_status'] for r in group),'exact four training roles required')
        output.append(dict(example_id=old['example_id'],bank_id=old['bank_id'],problem_id=old['problem_id'],held_fold=old['fold'],
            current_status=old['current_status'],training_H_AC_roles=sum(r['methods']['H']['known_ac'] for r in group),
            training_H_unknown_roles=sum(r['methods']['H']['unknown'] for r in group),
            training_H_regression_roles=sum(r['methods']['H']['known_regression'] for r in group),
            oof_H_known_ac=old['H_known_ac'],oof_H_unknown=old['H_unknown'],oof_known_ac_miss=old['known_ac_miss'],
            known_ac_oracle=old['known_oracle']))
    def table(selected):
        return dict(banks=len(selected),ac_role_counts={str(n):sum(r['training_H_AC_roles']==n for r in selected) for n in range(5)},
            unknown_role_counts={str(n):sum(r['training_H_unknown_roles']==n for r in selected) for n in range(5)})
    return dict(rows=output,all_banks=table(output),known_ac_oracle=table([r for r in output if r['known_ac_oracle']]),
        posthoc_67_oof_misses=table([r for r in output if r['oof_known_ac_miss']]),
        oof_known_ac=table([r for r in output if r['oof_H_known_ac']]),
        held_folds={str(f):table([r for r in output if r['held_fold']==f]) for f in range(5)},
        current_status={s:table([r for r in output if r['current_status']==s]) for s in ('known_ac','known_nonac','unknown')})


def main(argv=None):
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--source-tar',type=Path,required=True);parser.add_argument('--oof-diagnosis',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    output=prior.canonical(args.output);archive=prior.canonical(args.archive);tar_path=prior.canonical(args.source_tar)
    require(not output.exists() and not output.is_relative_to(archive),'fresh separate diagnostic output required')
    require(output==Path(__file__).resolve().parents[1]/OUTPUT,'fixed diagnostic-v1 output required')
    source_path=Path(__file__).resolve();test_path=source_path.parents[1]/'tests/test_zpd_joint_training_objective.py'
    source_pins={str(p):prior.digest(p.read_bytes()) for p in (source_path,test_path,Path(prior.__file__).resolve())}
    require(source_pins[str(Path(prior.__file__).resolve())]==PRIOR_SOURCE_SHA,'reviewed prior diagnostic helper drift')
    reader=prior.Reader(archive);outer=reader.seal('supervised-v1',prior.PINS['outer']);run=reader.seal('run-v1',prior.PINS['run'])
    require(outer['experiment_complete_sha256']==prior.PINS['run'] and run['completed_fits']==35 and run['recipients']==320,'completed full experiment required')
    manifest=reader.json('run-v1/manifest.json',run['files_sha256']['manifest.json'])
    prepared=reader.json('prepared-v1/COMPLETE.json',prior.PINS['prepared'])
    tar_raw=tar_path.read_bytes();require(prior.digest(tar_raw)==prior.PINS['source_tar'],'execution tar pin differs')
    jobs={f:reader.json(f'jobs/fold-{f}.json',run['job_sha256'][str(f)]) for f in range(5)}
    with tarfile.open(tar_path) as source_tar:
        for job in jobs.values():
            require(job['source_sha256']==jobs[0]['source_sha256'],'execution closure changed across jobs')
        for name,pin in jobs[0]['source_sha256'].items():
            member=source_tar.getmember(name);require(member.isfile() and prior.digest(source_tar.extractfile(member).read())==pin,'execution source mismatch')
    def barrier():
        reader.recheck();require(prior.digest(tar_path.read_bytes())==prior.PINS['source_tar'],'execution tar changed')
        require(all(prior.digest(Path(p).read_bytes())==pin for p,pin in source_pins.items()),'diagnostic source/test/helper changed')
    output.mkdir(parents=True);files={};folds=[]
    def save(name,value):files[name]=prior.write_new(output/name,prior.encoded(value))
    try:
        for fold in range(5):
            job=jobs[fold];contract=job['own_label_contract'];inp=job['inputs']
            require(inp['fold']==fold and inp['synthetic'] is False and len(inp['examples'])==320,'full real own capsule required')
            require(contract==manifest['label_contracts'][str(fold)],'external own-label contract differs')
            name=f'fold-{fold}/train-labels.json';pin=contract['expected_sha256']
            require(prepared['files_sha256'][name]==pin,'prepared own-label SHA differs')
            envelope=reader.json('prepared-v1/'+name,pin)
            require(envelope['parent_complete_sha256']==prepared['parent_complete_sha256'],'own ancestry differs')
            scaler=reader.json(f'run-v1/fold-{fold}/SCALER.json',run['files_sha256'][f'fold-{fold}/SCALER.json'])
            model=reader.json(f'run-v1/fold-{fold}/H.json',run['files_sha256'][f'fold-{fold}/H.json'])
            result=fold_calculation(inp,envelope,contract,scaler,model);del envelope
            barrier();save(f'fold-{fold}.json',result);folds.append(result)
            print(json.dumps(dict(phase='training_diagnosis',completed_incidences=sum(x['train_examples'] for x in folds),total_incidences=1280,fold=fold)),flush=True)
        all_rows=[r for fold in folds for r in fold['incidences']]
        require(len(all_rows)==1280 and len({r['bank_id'] for r in all_rows})==320,'whole training incidence coverage differs')
        # Only now read the already public OOF diagnosis; never assessment label bodies.
        oof_root=prior.canonical(args.oof_diagnosis);oof_marker_raw=(oof_root/'COMPLETE.json').read_bytes()
        require(prior.digest(oof_marker_raw)==OOF_COMPLETE_SHA,'OOF diagnostic completion pin differs')
        oof_marker=prior.decode(oof_marker_raw);require(oof_marker['files_sha256']['report.json']==OOF_REPORT_SHA,'OOF diagnostic report link differs')
        oof_raw=(oof_root/'report.json').read_bytes();require(prior.digest(oof_raw)==OOF_REPORT_SHA,'OOF report pin differs')
        oof=prior.decode(oof_raw);role_table=cross_roles(all_rows,oof['rows'])
        summary=summarize(all_rows)
        pooled={name: {key:math.fsum(fold['classes'][name][key] for fold in folds) for key in
            ('weight_mass','weighted_logistic_loss','C_weighted_logistic_loss','correctly_signed_weight','wrong_signed_weight','zero_margin_weight')}
            for name in (*CLASSES,'all')}
        for name in pooled:
            for key in ('mirrored_rows','unordered_pairs','positive_margin_rows','negative_margin_rows','zero_margin_rows'):
                pooled[name][key]=sum(fold['classes'][name][key] for fold in folds)
            pooled[name]['weighted_sign_accuracy']=pooled[name]['correctly_signed_weight']/pooled[name]['weight_mass'] if pooled[name]['weight_mass'] else None
        report=dict(kind='completed_joint4131_own_training_objective_diagnosis_v1',verification_status='provisional_pending_independent_review',
            fitting_performed=False,scaler_refitting_performed=False,exclusions=0,whole_training=summary,
            classes=pooled,folds={str(f['fold']):dict(summary=f['summary'],classes=f['classes'],numerical=f['numerical'],class_gradients=f['class_gradients']) for f in folds},
            current_status={s:summarize([r for r in all_rows if r['current_status']==s]) for s in ('known_ac','known_nonac','unknown')},
            cross_roles=role_table,scientific_gate_unchanged=oof['scientific_gate'],
            provenance=dict(archive_inputs=dict(reader.bindings),execution_source_tar_sha256=prior.PINS['source_tar'],execution_sources=jobs[0]['source_sha256'],
                diagnostic_sources=source_pins,oof_diagnostic_complete_sha256=OOF_COMPLETE_SHA,oof_diagnostic_report_sha256=OOF_REPORT_SHA,
                runtime=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform())),
            scope=dict(old_all320_posthoc=True,own_training_only_per_fold=True,assessment_label_body_opened=False,
                no_independent_sample_or_fresh_RR_claim=True,shared_controls_hold_all_coefficients_fixed=True,
                causal_objective_misspecification_established=False,new_method_authorized=False))
        save('report.json',report);barrier()
        require(prior.digest((oof_root/'COMPLETE.json').read_bytes())==OOF_COMPLETE_SHA and prior.digest((oof_root/'report.json').read_bytes())==OOF_REPORT_SHA,'OOF diagnostic changed')
        require(all(prior.digest((output/name).read_bytes())==pin for name,pin in files.items()),'diagnostic output drift')
        marker=prior.write_new(output/'COMPLETE.json',prior.encoded(dict(status='complete',verification_status='provisional_pending_independent_review',
            files_sha256=files,training_incidences=1280,banks=320,fitting_performed=False)))
        barrier();require(prior.digest((output/'COMPLETE.json').read_bytes())==marker and all(prior.digest((output/n).read_bytes())==p for n,p in files.items()),'terminal diagnostic drift')
    except BaseException as error:
        if (output/'COMPLETE.json').exists():(output/'COMPLETE.json').rename(output/'REJECTED_COMPLETE.json')
        prior.write_new(output/'FAILED.json',prior.encoded(dict(status='failed',error_type=type(error).__name__,error=str(error))))
        raise
    print(json.dumps(dict(phase='complete',output=str(output),whole_training=summary,cross_roles=role_table['all_banks'])),flush=True)


if __name__=='__main__':main()
