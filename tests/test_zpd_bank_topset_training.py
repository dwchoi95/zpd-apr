"""Synthetic-only own-scope, stored-score and post-completion join tests."""
import copy
import math
import unittest

import numpy as np
from scipy import sparse

from scripts import diagnose_zpd_bank_topset_training as d
from tests.test_zpd_joint_training_objective import label


def csr_payload(value):
    value=sparse.csr_matrix(value,dtype=np.float64)
    return dict(format='csr',shape=list(value.shape),data_dtype='<f8',index_dtype='<i8',
        data_hex=value.data.astype('<f8').tobytes().hex(),indices_hex=value.indices.astype('<i8').tobytes().hex(),
        indptr_hex=value.indptr.astype('<i8').tobytes().hex())


def fixture(fold=0):
    noop=d.p.digest(b'current');ids=['a','b',noop]
    examples=[dict(example_id=f'e{f}',bank_id=f'b{f}',user_id=f'u{f}') for f in range(5)]
    numeric=np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,0.]])
    current=np.concatenate((numeric,np.zeros((3,4096))),axis=1)
    phi={a:np.zeros((3,32)) for a in d.p.ARMS[:-1]}
    for a in phi:phi[a][:,0]=[.2,.1,0.]
    for a in ('H','Jm','U','L'):phi[a][0,16]=2.
    phi['HS'][1,16]=2.
    inp=dict(fold=fold,synthetic=True,examples=examples,
        assignment=dict(example_fold={f'e{f}':f for f in range(5)}),fold_assignment_sha256='2'*64,
        banks={},raw_current={},interactions={a:{} for a in phi})
    for ex in examples:
        bid=ex['bank_id'];inp['banks'][bid]=dict(candidate_ids=ids,bank_seal_sha256='1'*64,problem_id='p',current_source_hex=b'current'.hex())
        inp['raw_current'][bid]=dict(candidate_ids=ids,numeric=csr_payload(numeric),hashed=csr_payload(np.zeros((3,4096))))
        for a,v in phi.items():inp['interactions'][a][bid]=dict(candidate_ids=ids,dtype='<f8',shape=[3,32],data_hex=v.astype('<f8').tobytes().hex())
    train=[ex for ex in examples if inp['assignment']['example_fold'][ex['example_id']]!=fold]
    mapping={e['example_id']:e['bank_id'] for e in train}
    rows=[r for ex in train for r in (label(ex['bank_id'],'a',True,gain=1.),label(ex['bank_id'],'b',loss=.5),label(ex['bank_id'],noop))]
    envelope=dict(kind='repair_feedback_fold_training_labels_v1',fold=fold,parent_complete_sha256='3'*64,
        fold_assignment_sha256='2'*64,source_binding_sha256='4'*64,example_bank_ids=mapping,
        bank_seals={bid:'1'*64 for bid in mapping.values()},labels=rows)
    contract=dict(expected_fold_assignment_sha256='2'*64,expected_source_binding_sha256='4'*64,expected_sha256='5'*64)
    _,held,labels=d.old.own_scope(inp,envelope,contract)
    keys,y,w,_,training,_=d.old.pair_plan(train,inp['banks'],labels)
    scaler=dict(numeric_scale=[1.,1.,1.],training=training,row_keys=[list(k) for k in keys],y=y.tolist(),weights=w.tolist())
    plan=dict(original_pair_plan=dict(training=training),own_labels_sha256=d.canonical_hash([labels[e['bank_id'],cid] for e in train for cid in ids]))
    plan['plan_sha256']=d.canonical_hash(plan)
    thetaH=np.zeros(4131);thetaH[0]=.1;thetaH[1]=1.;thetaH[4099]=.2;thetaH[4115]=.6
    thetaC=np.zeros(4131);thetaC[0]=2.;thetaC[1]=.5
    mass={e['bank_id']:[] for e in train}
    for (bid,_,_),weight in zip(keys,w,strict=True):mass[bid].append(float(weight))
    weights=np.asarray([math.fsum(mass[e['bank_id']]) for e in train],dtype='<f8')
    models={}
    for arm,theta,tail in (('H',thetaH,phi['H']),('C_joint',thetaC,np.zeros((3,32)))):
        matrix=np.concatenate((current,tail),axis=1)
        hashes=dict(features=d.old.array_hash(*(matrix.astype('<f8') for _ in train)),
            top_indices=d.old.array_hash(*(np.array([0],dtype='<i8') for _ in train)),weights=d.old.array_hash(weights))
        inner=dict(configuration=dict(kind='fixed_repair_bank_topset_newton_v1'),coefficients=theta.tolist(),input_sha256=hashes)
        inner['model_sha256']=d.canonical_hash(inner)
        outer=dict(kind='bank_topset4131_own_fold_model_v1',arm=arm,fold=fold,
            train_example_ids=[e['example_id'] for e in train],held_example_ids=[e['example_id'] for e in held],
            label_contract=contract,transform_sha256=d.canonical_hash(scaler),plan_sha256=d.canonical_hash(plan),top_model=inner)
        outer['model_sha256']=d.canonical_hash(outer);models[arm]=outer
    return inp,envelope,contract,scaler,plan,models


class BankTopsetTrainingTests(unittest.TestCase):
    def test_complete_own_fold_scores_input_hash_and_history_substitution(self):
        result,theta=d.fold_calculation(*fixture())
        self.assertEqual(result['train_examples'],4);self.assertEqual(result['held_examples'],1)
        self.assertEqual(result['summary']['methods']['H']['known_ac'],4)
        self.assertEqual(result['summary']['methods']['C_joint']['known_ac'],4)
        self.assertEqual(result['summary']['methods']['shared_H_CF']['known_regression'],4)
        self.assertEqual(result['summary']['paired_controls']['shared_H_CF']['ac_gained'],4)
        self.assertEqual(result['summary']['paired_controls']['shared_H_CF']['ac_lost'],0)
        for row in result['incidences']:
            self.assertTrue(row['exact_H_feature_equal']['Jm'])
            self.assertTrue(row['shared_H_perturbation']['shared_H_Jm']['decision_invariant_certificate'])
            self.assertFalse(row['shared_H_perturbation']['shared_H_CF']['decision_invariant_certificate'])
            self.assertGreater(row['score_spreads']['history32'],0)
            self.assertEqual(row['methods']['H']['candidate_id'],'a')
            self.assertEqual(row['method_margins']['H']['selected_minus_best_known_ac'],0)

    def test_labels_change_outcomes_never_scores_or_selected_candidates(self):
        inp,env,contract,scaler,plan,models=fixture();result,theta=d.fold_calculation(inp,env,contract,scaler,plan,models)
        ex=inp['examples'][1];local=result['incidences'][0]['candidate_labels']
        first,_=d.score_bank(inp,ex,scaler,theta,local)
        changed={cid:label(ex['bank_id'],cid,unknown=True) for cid in local}
        second,_=d.score_bank(inp,ex,scaler,theta,changed)
        self.assertEqual(first['scores'],second['scores'])
        self.assertEqual({m:v['candidate_id'] for m,v in first['methods'].items()},
                         {m:v['candidate_id'] for m,v in second['methods'].items()})
        self.assertTrue(second['methods']['H']['unknown']);self.assertFalse(second['known_ac_oracle'])

    def test_scope_candidate_order_hash_and_saved_scaler_tampering_rejected(self):
        for change in ('held','candidate_order','coefficient','scale','input_hash'):
            parts=list(copy.deepcopy(fixture()));inp,env,contract,scaler,plan,models=parts
            if change=='held':env['labels'].append(label('b0','a'))
            elif change=='candidate_order':inp['raw_current']['b1']['candidate_ids']=list(reversed(inp['raw_current']['b1']['candidate_ids']))
            elif change=='coefficient':models['H']['top_model']['coefficients'][0]=7.
            elif change=='scale':scaler['numeric_scale'][0]=2.
            else:
                models['H']['top_model']['input_sha256']['features']='0'*64
                inner=models['H']['top_model'];inner['model_sha256']=d.canonical_hash({k:v for k,v in inner.items() if k!='model_sha256'})
                models['H']['model_sha256']=d.canonical_hash({k:v for k,v in models['H'].items() if k!='model_sha256'})
            with self.subTest(change=change),self.assertRaises(ValueError):d.fold_calculation(*parts)

    def test_exact_perturbation_gap_bound_no_tolerance_tie_reselection(self):
        ids=('a','b','c');left=dict(a=1.,b=0.,c=-1.)
        self.assertTrue(d.perturbation_certificate(ids,left,dict(a=.9,b=.1,c=-1.))['decision_invariant_certificate'])
        self.assertFalse(d.perturbation_certificate(ids,left,dict(a=0.,b=1.,c=-1.))['decision_invariant_certificate'])
        equal=dict(a=0.,b=-0.,c=-1.)
        self.assertTrue(d.perturbation_certificate(ids,equal,dict(a=2.,b=2.,c=1.))['decision_invariant_certificate'])
        tiny=float(np.nextafter(1.,np.inf))
        self.assertFalse(d.perturbation_certificate(('a','b'),dict(a=1.,b=tiny),dict(a=tiny,b=1.))['choice_unchanged'])
        for wrong in (dict(a=True,b=0.,c=-1.),dict(a=math.nan,b=0.,c=-1.)):
            with self.assertRaises(ValueError):d.perturbation_certificate(ids,wrong,left)

    def test_four_roles_consensus_and_old_new_comparison(self):
        rows=[];thetas={};parts={}
        for fold in range(5):
            parts[fold]=fixture(fold);result,thetas[fold]=d.fold_calculation(*parts[fold]);rows.extend(result['incidences'])
        consensus=d.consensus_labels(rows);self.assertEqual(len(consensus),5)
        oldrows=copy.deepcopy(rows)
        for row in oldrows:row['methods']['H']=d.old.outcome('b',row['candidate_labels'],row['noop_id'])
        comparison=d.compare_training(rows,oldrows)
        self.assertEqual(comparison['paired']['H']['ac_gained'],20)
        self.assertEqual(comparison['paired']['H']['regression_prevented'],20)
        oof=[];oldpred=[]
        for fold in range(5):
            inp,_,_,scaler,_,_=parts[fold];ex=inp['examples'][fold]
            row,_=d.score_bank(inp,ex,scaler,thetas[fold],consensus[ex['bank_id']]);oof.append(row)
            oldpred.append(dict(example_id=ex['example_id'],bank_id=ex['bank_id'],fold=fold,choices={'H':'b'}))
        joined=d.cross_roles(rows,oldrows,oof,oldpred)
        self.assertEqual(joined['all_banks']['role_counts']['new_training_H_ac_roles']['4'],5)
        self.assertEqual(joined['all_banks']['role_counts']['old_training_H_ac_roles']['0'],5)
        self.assertEqual(joined['paired_new_vs_old']['H']['ac_gained'],5)
        with self.assertRaises(ValueError):d.consensus_labels(rows[:-1])
        altered=copy.deepcopy(rows);altered[-1]['candidate_labels']['a']['all_ac']=False
        with self.assertRaises(ValueError):d.consensus_labels(altered)
        with self.assertRaises(ValueError):d.cross_roles(rows[:-1],oldrows,oof,oldpred)
        with self.assertRaises(ValueError):d.compare_training(rows,oldrows[:-1])

    def test_unknowns_and_empty_summary_not_false_success(self):
        result,_=d.fold_calculation(*fixture());rows=result['incidences']
        row=copy.deepcopy(rows[0]);cid=row['methods']['H']['candidate_id']
        row['candidate_labels'][cid]=label(row['bank_id'],cid,unknown=True)
        row['methods']['H']=d.old.outcome(cid,row['candidate_labels'],row['noop_id'])
        value=d.summarize([row])['methods']['H']
        self.assertEqual(value['unknown'],1);self.assertEqual(value['known_ac'],0)
        self.assertEqual(value['known_ac_misses'],1)
        empty=d.summarize([]);self.assertEqual(empty['incidences'],0)
        self.assertEqual(empty['methods']['H']['known_ac'],0)


if __name__=='__main__':unittest.main()
