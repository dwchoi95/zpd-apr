"""Post-completion fixed-bank progress32 diagnosis; no fit or new execution.

Read only the externally pinned completed experiment, its own capsules, accepted
readiness artifacts and sole separated assessment envelope. All unknowns remain
unknown. Geometry/oracle decompositions are post-hoc diagnostics, not new gates,
deployment choices or causal/student-effect estimates.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import combinations
import json
import math
import os
from pathlib import Path
import platform

import numpy as np
from scipy import sparse

from scripts import zpd_repair_progress_capsule as capsule
from scripts import zpd_repair_feedback_labels as label_contract

ROOT=Path(__file__).resolve().parents[1]
FAMILY='outputs/zpd-repair-statement-progress-20260925'
OUTER_SHA='54c76aedb52f2b02569af0534b1725a5b520984f8bfc818bc2837a45e89aa57a'
RUN_SHA='2d0fcc31221073cdf961934924f6559eb4eb324012a96dc698d76b2cbc26b1d9'
READINESS='outputs/zpd-statement-sample-feedback-20260924/readiness-v1'
READINESS_SHA='e9ed6a38c44f56578ea85e02e5220c68c68906aff767abaa047a318f3259afad'
LABEL_PATH='outputs/zpd-repair-feedback-20260924/prepared-v1/assessment/all320-labels.json'
ARMS=tuple(capsule.ARMS)
METHODS=(*ARMS,'structural_C','lexical_C','first_attempt','shared_H_HS','shared_H_Jm','shared_H_CF','noop')
TAU=1e-12  # Frozen geometry diagnostic tolerance, never a ranking/gate change.
SOURCE_FILES=('scripts/diagnose_zpd_repair_progress32.py','tests/test_zpd_repair_progress32_diagnosis.py',
    'scripts/zpd_repair_progress_capsule.py','scripts/zpd_repair_feedback_labels.py')


def require(test,message):
    if not test:raise ValueError(message)


def encoded(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())


def decode(raw):
    def pairs(items):
        d={}
        for k,v in items:
            require(k not in d,'duplicate JSON key');d[k]=v
        return d
    def invalid(_):raise ValueError('nonfinite JSON')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=invalid)


class Reader:
    def __init__(self,project):
        self.project=Path(project).absolute();self.bindings={}
        require(self.project==self.project.resolve(),'canonical project required')

    def read(self,name,pin):
        p=Path(name)
        require(not p.is_absolute() and '..' not in p.parts and str(p)==name,'canonical relative name required')
        path=self.project/p
        require(path.resolve()==path and path.is_file(),'missing/aliased bound artifact')
        raw=path.read_bytes()
        require(digest(raw)==pin and self.bindings.get(name,pin)==pin,'consumed artifact SHA differs: '+name)
        self.bindings[name]=pin;return raw

    def json(self,name,pin):return decode(self.read(name,pin))

    def seal(self,base,pin):
        marker=self.json(base+'/COMPLETE.json',pin)
        require(marker.get('status')=='complete' and type(marker.get('files_sha256')) is dict,'completed seal required')
        require(not any((self.project/base/n).exists() for n in ('FAILED.json','REJECTED_COMPLETE.json')),
                'failed/rejected result forbidden')
        for name,value in marker['files_sha256'].items():self.read(base+'/'+name,value)
        return marker

    def recheck(self):
        for name,pin in self.bindings.items():self.read(name,pin)


def load_completed(project):
    r=Reader(project);outer=r.seal(FAMILY+'/supervised-v1',OUTER_SHA);run=r.seal(FAMILY+'/run-v1',RUN_SHA)
    require(outer['experiment_complete_sha256']==RUN_SHA and run['completed_fits']==30
        and run['recipients']==320 and run['methods']==list(METHODS),'fixed320/30/13 complete run required')
    def runjson(name):return r.json(FAMILY+'/run-v1/'+name,run['files_sha256'][name])
    audit_name='verified/report.json'
    audit=r.json(FAMILY+'/supervised-v1/'+audit_name,outer['files_sha256'][audit_name])
    require(audit['verified'] is True and audit['recipients']==320 and audit['models']==30 and audit['methods']==13,
            'independent numerical audit must precede diagnostic labels')
    manifest=runjson('manifest.json');predictions=runjson('predictions.json');assessment=runjson('assessment/report.json')
    require(audit['gate']==assessment['gate'],'independent gate differs')
    jobs={f:r.json(FAMILY+f'/jobs/fold-{f}.json',run['job_sha256'][str(f)]) for f in range(5)}
    for job in jobs.values():
        for name in SOURCE_FILES[2:]:require(sha(ROOT/name)==job['source_sha256'][name],'consumed frozen validator source changed')
    inputs={f:capsule.decode_inputs(jobs[f]['inputs']) for f in range(5)}
    require(all(v.fold==f and not v.synthetic for f,v in inputs.items()),'production original fold capsules required')
    models={f:{a:runjson(f'fold-{f}/{a}.json') for a in ARMS} for f in range(5)}
    contract=manifest['label_contracts']['assessment']
    payload=r.json(LABEL_PATH,contract['expected_sha256'])
    first=inputs[0]
    labels=label_contract.validate_assessment_envelope(payload,first.banks,{e.example_id:e.bank_id for e in first.examples},
        expected_fold_assignment_sha256=contract['expected_fold_assignment_sha256'],
        expected_source_binding_sha256=contract['expected_source_binding_sha256'])
    readiness=r.seal(READINESS,READINESS_SHA)
    feature_raw=r.read(READINESS+'/features.jsonl',readiness['files_sha256']['features.jsonl'])
    feature_rows=[decode(line) for line in feature_raw.splitlines()]
    require(len(feature_rows)==320 and len({v['spec']['example_id'] for v in feature_rows})==320,'full feature journal required')
    r.recheck()
    return inputs,models,predictions,labels,assessment,feature_rows,r


def known_ac(label):return label['status']=='stable' and label['all_ac']
def regression(label):return label['status']=='stable' and label['loss']>0
def original_group(p,labels):
    v=labels[p['bank_id'],p['choices']['noop']]
    return 'unknown' if v['status']=='unknown' else 'known_ac' if v['all_ac'] else 'known_nonac'


def metrics(predictions,labels,method):
    count=dict(stable_ac=0,stable_regression=0,unknown=0,noop_selected=0)
    for p in predictions:
        cid=p['choices'][method];lab=labels[p['bank_id'],cid]
        count['stable_ac']+=bool(known_ac(lab));count['stable_regression']+=bool(regression(lab))
        count['unknown']+=lab['status']=='unknown';count['noop_selected']+=cid==p['choices']['noop']
    n=len(predictions);a=count['stable_ac'];u=count['unknown'];r=count['stable_regression']
    fractions=None if not n else {k:Fraction(v,n) for k,v in
        (('ac_lower',a),('ac_upper',a+u),('regression_lower',r),('regression_upper',r+u))}
    return dict(examples=n,counts=count,fractions=fractions)


def switches(predictions,labels,control):
    totals=Counter(examples=len(predictions),changed=0,ac_gained=0,ac_lost=0,regression_prevented=0,
        regression_introduced=0,unknown_comparison=0,to_noop=0,from_noop=0,edited_to_edited=0)
    changed=[]
    for p in predictions:
        h,c=p['choices']['H'],p['choices'][control];left,right=labels[p['bank_id'],h],labels[p['bank_id'],c]
        facts={k:False for k in ('ac_gained','ac_lost','regression_prevented','regression_introduced')}
        unknown=left['status']=='unknown' or right['status']=='unknown'
        if not unknown:
            facts=dict(ac_gained=bool(left['all_ac'] and not right['all_ac']),ac_lost=bool(right['all_ac'] and not left['all_ac']),
                regression_prevented=left['loss']==0 and right['loss']>0,regression_introduced=left['loss']>0 and right['loss']==0)
        totals['unknown_comparison']+=unknown
        for k,v in facts.items():totals[k]+=v
        if h!=c:
            mode='to_noop' if h==p['choices']['noop'] else 'from_noop' if c==p['choices']['noop'] else 'edited_to_edited'
            totals['changed']+=1;totals[mode]+=1
            changed.append(dict(example_id=p['example_id'],problem_id=p['problem_id'],fold=p['fold'],
                original_group=original_group(p,labels),transition=mode,H=h,control=c,
                H_label=dict(left),control_label=dict(right),unknown_comparison=unknown,**facts))
    return dict(counts=dict(totals),changed=changed)


def summarize(predictions,labels):
    values={m:metrics(predictions,labels,m) for m in METHODS}
    problems=sorted({p['problem_id'] for p in predictions})
    equal={m:{k:sum((metrics([p for p in predictions if p['problem_id']==problem],labels,m)['fractions'][k]
            for problem in problems),Fraction())/len(problems) for k in ('ac_lower','ac_upper','regression_lower','regression_upper')}
           for m in METHODS} if problems else None
    return dict(examples=len(predictions),problems=len(problems),methods=values,equal_problem=equal,
        paired={m:switches(predictions,labels,m) for m in METHODS if m!='H'})


def norm(vector):return math.sqrt(math.fsum(float(x)*float(x) for x in vector))
def dot(a,b):return math.fsum(float(x)*float(y) for x,y in zip(a,b,strict=True))
def varies(matrix):return len(matrix)>1 and bool(np.any(np.max(matrix,axis=0)-np.min(matrix,axis=0)>TAU))
def top(scores):return min(scores,key=lambda cid:(-scores[cid],cid))


def arrays_sha(*arrays):
    h=hashlib.sha256()
    for value in arrays:
        a=np.ascontiguousarray(value)
        head=json.dumps(dict(shape=list(a.shape),dtype=a.dtype.str),sort_keys=True,separators=(',',':')).encode()
        body=a.tobytes(order='C');h.update(len(head).to_bytes(8,'little'));h.update(head)
        h.update(len(body).to_bytes(8,'little'));h.update(body)
    return h.hexdigest()


def training_arrays(inp,labels):
    """Independent legacy pair/weight reconstruction after full completion.

    Reuse only already allowed all320 assessment core labels, restricted to the
    original training complement. No fold label-body, pair builder or fitter is
    invoked. Both legacy float64 normalizations and exact mirror order remain.
    """
    records=[]
    for ex in inp.examples:
        if inp.assignment['example_fold'][ex.example_id]==inp.fold:continue
        ids=inp.interactions['H'][ex.bank_id].candidate_ids
        keys=[]
        for cid in ids:
            v=labels[ex.bank_id,cid]
            keys.append(None if v['status']=='unknown' else (int(v['all_ac']),int(v['loss']==0),v['gain']-v['loss']))
        pairs=[(i,j,int(keys[i]>keys[j])) for i,j in combinations(range(len(ids)),2)
               if keys[i] is not None and keys[j] is not None and keys[i]!=keys[j]]
        if pairs:records.append((ex,ids,pairs))
    prefix_counts=Counter(ex.user_id for ex,_,_ in records)
    x=[];ys=[];weights=[];base=[];pair_ids=[];example_ids=[]
    for ex,ids,pairs in records:
        phi=inp.interactions['H'][ex.bank_id].matrix;scores=inp.base_scores[ex.bank_id]
        for i,j,y in pairs:
            delta=phi[i]-phi[j];margin=scores[ids[i]]-scores[ids[j]]
            x.extend((delta,-delta));base.extend((margin,-margin));ys.extend((y,1-y))
            weights.extend([1/(prefix_counts[ex.user_id]*len(pairs)*2)]*2)
            pair_ids.extend(([ids[i],ids[j]],[ids[j],ids[i]]));example_ids.extend([ex.example_id]*2)
    require(bool(x),'no unequal training pairs')
    w=np.asarray(weights,dtype=np.float64);w*=len(w)/w.sum();w=w*(1900./float(w.sum()))
    return np.array(x,dtype=np.float64),np.array(ys,dtype=np.int64),w,np.array(base,dtype=np.float64),pair_ids,example_ids


def weighted_quantiles(values,weights):
    """Fixed inverse empirical weighted CDF, no interpolation/search."""
    ordered=sorted(zip(map(float,values),map(float,weights),strict=True));mass=math.fsum(w for _,w in ordered)
    require(bool(ordered) and all(w>0 for _,w in ordered),'positive quantile weights required')
    result={}
    for q in (0.,.25,.5,.75,1.):
        total=0.;value=ordered[-1][0]
        for v,w in ordered:
            total=math.fsum((total,w))
            if total>=q*mass:value=v;break
        result[str(q)]=value
    return result


def logistic_statistics(x,y,w,b,theta):
    signed=2*y-1;mass=math.fsum(map(float,w));m=signed*b
    def sigmoid_negative(value):
        if value>=0:
            e=math.exp(-float(value));return e/(1+e)
        return 1/(1+math.exp(float(value)))
    p=np.array([sigmoid_negative(v) for v in m])
    alpha=.1*w*p
    g0=np.array([-math.fsum(float(alpha[i]*signed[i]*x[i,j]) for i in range(len(w))) for j in range(x.shape[1])])
    fitted_m=signed*(b+np.array([dot(theta,row) for row in x]))
    fitted_p=[sigmoid_negative(v) for v in fitted_m]
    final_g=np.array([float(theta[j])-math.fsum(float(.1*w[i]*signed[i]*fitted_p[i]*x[i,j]) for i in range(len(w)))
        for j in range(x.shape[1])])
    row_norm=np.array([norm(row) for row in x]);triangle=math.fsum(float(a*n) for a,n in zip(alpha,row_norm,strict=True))
    leverage=math.fsum(map(float,alpha))
    return dict(rows=len(w),weight_mass=mass,C=.1,gradient_at_zero_l2=norm(g0),
        gradient_at_zero_current_l2=norm(g0[:16]),gradient_at_zero_residual_l2=norm(g0[16:]),
        fitted_theta_l2=norm(theta),fitted_gradient_infinity=max(map(abs,final_g)),
        logistic_leverage_C_sum_w_sigmoid_negative_signed_base=leverage,
        weighted_mean_sigmoid_negative_signed_base=leverage/(.1*mass),
        C_sum_w_times_half=mass*.05,
        logistic_feature_triangle_bound=triangle,gradient_to_triangle_ratio=norm(g0)/triangle if triangle else None,
        signed_base_margin_weighted_quantiles=weighted_quantiles(m,w),
        weighted_base_sign_accuracy=math.fsum(float(w[i]) for i in range(len(w)) if m[i]>0)/mass,
        weighted_base_tie_mass_fraction=math.fsum(float(w[i]) for i in range(len(w)) if m[i]==0)/mass,
        weighted_base_wrong_mass_fraction=math.fsum(float(w[i]) for i in range(len(w)) if m[i]<0)/mass,
        weighted_fitted_sign_accuracy=math.fsum(float(w[i]) for i in range(len(w)) if fitted_m[i]>0)/mass,
        weighted_zero_feature_mass_fraction=math.fsum(float(w[i]) for i in range(len(w)) if not x[i].any())/mass)


def training_diagnosis(inp,model,labels):
    x,y,w,b,ids,examples=training_arrays(inp,labels)
    require(ids==model['pair_metadata']['pair_candidate_ids'] and examples==model['pair_metadata']['training']['pair_example_ids'],
            'independent exact original pair order differs')
    csr=sparse.csr_matrix(x);csr.sum_duplicates();csr.sort_indices();csr.eliminate_zeros()
    hashes=dict(features=arrays_sha(np.array(csr.shape,dtype='<i8'),csr.indptr.astype('<i8'),csr.indices.astype('<i8'),csr.data.astype('<f8')),
        labels=arrays_sha(y.astype('<i8')),weights=arrays_sha(w.astype('<f8')),base_margin=arrays_sha(b.astype('<f8')))
    require(hashes==model['offset_model']['training']['input_sha256'],'independent training-array hashes differ')
    result=logistic_statistics(x,y,w,b,np.array(model['offset_model']['coefficients'],dtype=float))
    result['verified_training_array_sha256']=hashes
    result['label_access']='post_completion_assessment320_projected_to_exact_training_complement; no_new_label_body'
    return result


def bank_diagnosis(p,block,theta,labels,feature=None):
    """All candidates; known-AC oracle/class ceilings are diagnostics, not choices."""
    ids=block.candidate_ids;x=block.matrix
    require(tuple(p['candidate_scores']['H'])==ids or set(p['candidate_scores']['H'])==set(ids),'candidate identity differs')
    require(theta.shape==(32,) and np.isfinite(theta).all(),'finite32 coefficients required')
    for m in METHODS:require(set(p['candidate_scores'][m])==set(ids) and top(p['candidate_scores'][m])==p['choices'][m],
                            'saved choice/tie rule differs')
    base=p['candidate_scores']['structural_C'];hs=p['candidate_scores']['H'];idx={cid:i for i,cid in enumerate(ids)}
    require(all(math.isclose(base[c]+dot(theta,x[idx[c]]),hs[c],rel_tol=1e-12,abs_tol=1e-10) for c in ids),
            'independently summed coefficient score differs from audited score')
    known=[c for c in ids if known_ac(labels[p['bank_id'],c])]
    unknown=[c for c in ids if labels[p['bank_id'],c]['status']=='unknown']
    classes={}
    for c in ids:classes.setdefault(tuple(map(float,x[idx[c]])),[]).append(c)
    champs=[min(group,key=lambda c:(-base[c],c)) for group in classes.values()]
    accessible=[c for c in champs if c in known]
    base_top=p['choices']['structural_C'];R=norm(theta)
    slack={c:base[base_top]-base[c]-R*norm(x[idx[c]]-x[idx[base_top]]) for c in known}
    radius_blocked=bool(known) and all(v>TAU for v in slack.values())
    selected=p['choices']['H'];miss=bool(known) and not known_ac(labels[p['bank_id'],selected])
    out=dict(example_id=p['example_id'],problem_id=p['problem_id'],fold=p['fold'],bank_id=p['bank_id'],
        original_group=original_group(p,labels),candidates=len(ids),known_ac_candidates=len(known),unknown_candidates=len(unknown),
        oracle_known_ac=bool(known),oracle_possible_ac=bool(known or unknown),H_known_ac=bool(known_ac(labels[p['bank_id'],selected])),
        H_unknown=labels[p['bank_id'],selected]['status']=='unknown',missed_known_ac=miss,
        exact_feature_classes=len(classes),class_champion_known_ac=bool(accessible),
        class_champion_possible_ac=any(c in known or c in unknown for c in champs),
        class_blocked_known_ac=bool(known) and not accessible,observed_theta_l2=R,
        radius_blocked_known_ac=radius_blocked,radius_min_slack=min(slack.values()) if slack else None,
        radius_comparison='every_known_AC_base_gap_minus_R_times_feature_distance_strictly_above_1e-12',
        selected_H=selected,selected_base=base_top,miss_partition=('not_a_known_AC_miss' if not miss else
            'feature_class_blocked' if not accessible else 'accessible_radius_blocked' if radius_blocked else 'accessible_not_radius_blocked'))
    if miss:
        ac=min(known,key=lambda c:(-hs[c],c));delta=x[idx[selected]]-x[idx[ac]]
        out['best_known_ac_comparison']=dict(candidate=ac,selected_status=labels[p['bank_id'],selected]['status'],
            base_advantage_wrong_choice=base[selected]-base[ac],current_block_advantage_wrong_choice=dot(theta[:16],delta[:16]),
            residual_block_advantage_wrong_choice=dot(theta[16:],delta[16:]),
            final_score_advantage_wrong_choice=hs[selected]-hs[ac])
    if feature is not None:
        require(feature['spec']['example_id']==p['example_id'] and tuple(feature['candidate_ids'])==ids,'readiness identity differs')
        for arm in ARMS:
            require(len(feature['candidates'])==len(ids),'readiness full candidates required')
        parsed=[i for i,c in enumerate(feature['candidates']) if c['moments']['H']['candidate_available'] and ids[i]!=p['choices']['noop']]
        first=feature['candidates'][parsed[0] if parsed else 0];moment=first['moments']['H']
        eligible=[i for i,v in enumerate(moment['mask']) if v] if parsed else []
        nominal=feature['spec']['original_nominal_sequence']
        wa=[i for i in eligible if nominal[i]=='WA' and nominal[i+1]=='WA'
            and sum(moment['paired_counts'][i][1:3])>0]
        matrices={a:np.array([c['arms'][a] for c in feature['candidates']],dtype=float) for a in ARMS}
        require(np.array_equal(matrices['H'],x),'readiness H/capsule differs')
        edited=[i for i,c in enumerate(ids) if c!=p['choices']['noop']]
        wa_matrix=np.array([c['wa_offdiagonal_contribution'] for c in feature['candidates']],dtype=float)
        out['support']=dict(current_feedback_available=first['current_feedback_available'],
            current_feedback_reason=first['current_feedback_reason'],prior_transitions=len(moment['mask']),
            eligible_transitions=len(eligible),zero_opportunity=not eligible,singleton_opportunity=len(eligible)==1,
            constant_feedback=bool(eligible) and len({tuple(moment['paired_counts'][i]) for i in eligible})==1,
            WA_WA_offdiag_transitions=len(wa),H_all_zero=not bool(x.any()),edited_H_varies=varies(x[edited]),
            edited_WA_WA_contribution_varies=varies(wa_matrix[edited]),
            edited_contrast={a:varies((matrices['H']-matrices[a])[edited]) for a in ARMS if a!='H'},
            exact_H_equal={a:bool(np.array_equal(matrices['H'],matrices[a])) for a in ARMS if a!='H'})
    return out


def diagnose(inputs,models,predictions,labels,feature_rows=()):
    require(len(predictions)==len({p['example_id'] for p in predictions}),'duplicate predictions')
    all_ids={e.example_id for e in inputs[0].examples}
    require({p['example_id'] for p in predictions}==all_ids,'full fixed prediction coverage required')
    feature={v['spec']['example_id']:v for v in feature_rows}
    require(not feature_rows or set(feature)==all_ids,'full readiness diagnostic coverage required')
    rows=[];norms={};pair_mass={}
    for f in range(5):
        norms[str(f)]={};pair_mass[str(f)]={}
        for a in ARMS:
            theta=np.array(models[f][a]['offset_model']['coefficients'],dtype=float)
            norms[str(f)][a]=dict(full=norm(theta),current=norm(theta[:16]),residual=norm(theta[16:]))
            pair_mass[str(f)][a]=models[f][a]['pair_summary']
    for p in predictions:
        f=p['fold'];inp=inputs[f]
        require(inp.assignment['example_fold'][p['example_id']]==f,'original OOF fold differs')
        rows.append(bank_diagnosis(p,inp.interactions['H'][p['bank_id']],
            np.array(models[f]['H']['offset_model']['coefficients'],dtype=float),labels,feature.get(p['example_id'])))
    summary=Counter({k:sum(bool(r[k]) for r in rows) for k in ('oracle_known_ac','oracle_possible_ac','H_known_ac','H_unknown',
        'missed_known_ac','class_champion_known_ac','class_champion_possible_ac','class_blocked_known_ac','radius_blocked_known_ac')})
    support={}
    if feature_rows:
        for key in ('current_feedback_available','zero_opportunity','singleton_opportunity','constant_feedback','H_all_zero',
                    'edited_H_varies','edited_WA_WA_contribution_varies'):
            support[key]=sum(bool(r['support'][key]) for r in rows)
        support['WA_WA_offdiag_banks']=sum(r['support']['WA_WA_offdiag_transitions']>0 for r in rows)
        support['WA_WA_offdiag_transitions']=sum(r['support']['WA_WA_offdiag_transitions'] for r in rows)
        support['edited_contrast']={a:sum(r['support']['edited_contrast'][a] for r in rows) for a in ARMS if a!='H'}
        support['exact_H_equal']={a:sum(r['support']['exact_H_equal'][a] for r in rows) for a in ARMS if a!='H'}
    return dict(kind='posthoc_fixed_progress32_diagnosis_v1',exclusions=0,refits=0,new_candidate_executions=0,
        confirmatory=False,causal_or_learning_effect_established=False,geometry_tau=TAU,
        full=summarize(predictions,labels),folds={str(f):summarize([p for p in predictions if p['fold']==f],labels) for f in range(5)},
        subgroups={g:summarize([p for p in predictions if original_group(p,labels)==g],labels) for g in ('known_ac','known_nonac','unknown')},
        oracle_and_geometry=dict(summary),miss_partitions=dict(Counter(r['miss_partition'] for r in rows)),
        source_support=support,coefficient_norms=norms,training_pair_mass=pair_mass,banks=rows,
        posthoc_H_training_logistic={str(f):training_diagnosis(inputs[f],models[f]['H'],labels) for f in range(5)},
        limitations=['Oracle/class/radius are overlapping post-hoc diagnostics, not a deployable selector.',
            'A class champion ceiling is a necessary-condition ceiling, not simultaneous linear realizability.',
            'Radius obstruction is at the observed coefficient norm, not impossibility for every coefficient.',
            'No confidence intervals or causal student effects are inferred from adaptive fixed development banks.'])


def serial(value):
    if isinstance(value,Fraction):return dict(numerator=value.numerator,denominator=value.denominator,value=float(value))
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    return value


def main(argv=None):
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--project',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args(argv)
    project=args.project.absolute();output=args.output.absolute()
    require(project.resolve()==project and output.resolve()==output and output in (project/FAMILY/'diagnostic-v1',project/FAMILY/'diagnostic-v2')
        and not output.exists(),'new canonical diagnostic-v1/v2 only; no overwrite/retry')
    sources={name:sha(ROOT/name) for name in SOURCE_FILES}
    inputs,models,predictions,labels,assessment,features,reader=load_completed(project)
    report=serial(diagnose(inputs,models,predictions,labels,features))
    for method in METHODS:require(report['full']['methods'][method]['counts']==assessment['full']['results'][method]['counts'],
                                 'independent counts differ from sealed assessment')
    require(report['full']['equal_problem']==assessment['full']['equal_problem'],'exact equal-problem metrics differ')
    for f in range(5):
        for method in METHODS:
            require(report['folds'][str(f)]['methods'][method]['counts']==assessment['folds'][str(f)]['results'][method]['counts'],
                    'original fold counts differ')
    report['frozen_gate']=assessment['gate'];report['input_sha256']=dict(reader.bindings);report['source_sha256']=sources
    report['diagnostic_runtime']=dict(python=platform.python_version(),numpy=np.__version__,
        scipy=__import__('scipy').__version__,local_posthoc_only=True)
    def barrier():
        require(all(sha(ROOT/n)==v for n,v in sources.items()),'diagnostic source drift');reader.recheck()
    def save(path,raw):
        with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        return digest(raw)
    barrier();output.mkdir(parents=True)
    try:
        raw=encoded(report);pin=save(output/'report.json',raw)
        barrier();require(sha(output/'report.json')==pin,'diagnostic output drift')
        complete=encoded(dict(status='complete',kind='posthoc_progress32_diagnosis_complete_v1',
            files_sha256={'report.json':pin},external_outer_sha256=OUTER_SHA,external_run_sha256=RUN_SHA,
            refits=0,new_outcomes=0,gate_changed=False))
        save(output/'COMPLETE.json',complete)
        barrier();require(sha(output/'report.json')==pin and sha(output/'COMPLETE.json')==digest(complete),'terminal output drift')
    except BaseException:
        if (output/'COMPLETE.json').exists():(output/'COMPLETE.json').rename(output/'REJECTED_COMPLETE.json')
        save(output/'FAILED.json',encoded(dict(status='failed',accepted=False)));raise
    print(json.dumps(dict(output=str(output),oracle=report['oracle_and_geometry'],partitions=report['miss_partitions'],support=report['source_support'])))


if __name__=='__main__':main()
