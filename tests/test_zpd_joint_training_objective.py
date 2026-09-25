"""Synthetic own-fold scope, mirror/weight, objective and cross-role witnesses."""
import copy
import math
import unittest

import numpy as np
from scipy import sparse

from scripts import diagnose_zpd_joint_training_objective as d


def label(bid,cid,ac=False,loss=0.,gain=0.,unknown=False):
    return dict(bank_id=bid,candidate_id=cid,status='unknown' if unknown else 'stable',
        all_ac=None if unknown else ac,loss=None if unknown else loss,gain=None if unknown else gain)


def fixture():
    examples=[dict(example_id=f'e{f}',bank_id=f'b{f}',user_id=f'u{f}') for f in range(5)]
    banks={e['bank_id']:dict(candidate_ids=['a','b','c'],bank_seal_sha256='1'*64) for e in examples}
    inp=dict(fold=0,examples=examples,banks=banks,assignment=dict(example_fold={f'e{f}':f for f in range(5)}),fold_assignment_sha256='2'*64)
    mapping={e['example_id']:e['bank_id'] for e in examples[1:]}
    rows=[row for bid in mapping.values() for row in (label(bid,'a'),label(bid,'b',loss=.5),label(bid,'c',True,gain=1.))]
    env=dict(kind='repair_feedback_fold_training_labels_v1',fold=0,parent_complete_sha256='3'*64,
        fold_assignment_sha256='2'*64,source_binding_sha256='4'*64,example_bank_ids=mapping,
        bank_seals={bid:'1'*64 for bid in mapping.values()},labels=rows)
    contract=dict(expected_fold_assignment_sha256='2'*64,expected_source_binding_sha256='4'*64,expected_sha256='5'*64)
    return inp,env,contract


class JointTrainingDiagnosisTests(unittest.TestCase):
    def test_own_scope_rejects_held_extra_missing_before_preferences(self):
        inp,env,contract=fixture();train,held,labels=d.own_scope(inp,env,contract)
        self.assertEqual(len(train),4);self.assertEqual(len(held),1);self.assertEqual(len(labels),12)
        for change in ('held','missing','duplicate','wrong_fold','bool_fold','wrong_binding'):
            other=copy.deepcopy(env)
            if change=='held':other['labels'].append(label('b0','a'))
            elif change=='missing':other['labels'].pop()
            elif change=='duplicate':other['labels'].append(other['labels'][0])
            elif change=='wrong_fold':other['fold']=1
            elif change=='bool_fold':other['fold']=False
            else:other['source_binding_sha256']='6'*64
            with self.subTest(change=change),self.assertRaises(ValueError):d.own_scope(inp,other,contract)

    def test_pair_relation_mirrors_original_mass_and_categories(self):
        inp,env,contract=fixture();train,_,labels=d.own_scope(inp,env,contract)
        rows,y,w,classes,meta,counts=d.pair_plan(train,inp['banks'],labels)
        self.assertEqual(len(rows),24);self.assertEqual(meta['train_prefixes'],4)
        self.assertAlmostEqual(w.sum(),1900.);self.assertEqual(y[1::2].tolist(),(1-y[::2]).tolist())
        np.testing.assert_array_equal(w[::2],w[1::2])
        for a,b in zip(rows[::2],rows[1::2]):self.assertEqual(a,(b[0],b[2],b[1]))
        self.assertEqual(classes.count('ac_nonac'),16);self.assertEqual(classes.count('nonac_preservation'),8)
        self.assertEqual(counts['b1']['informative_unordered_pairs'],3)

    def test_unknown_and_uninformative_banks_stay_covered(self):
        inp,env,contract=fixture()
        for row in env['labels']:
            if row['bank_id']=='b1':row.update(status='unknown',gain=None,loss=None,all_ac=None)
        train,_,labels=d.own_scope(inp,env,contract)
        _,_,_,_,meta,counts=d.pair_plan(train,inp['banks'],labels)
        self.assertEqual(meta['train_prefixes'],4);self.assertEqual(meta['uninformative_train_example_ids'],['e1'])
        self.assertEqual(counts['b1']['pairs_with_unknown'],3)
        self.assertEqual(d.outcome('a',{c:labels['b1',c] for c in ('a','b','c')},'a'),
            dict(candidate_id='a',status='unknown',known_ac=False,known_regression=False,unknown=True,noop=True))

    def test_miss_critical_pair_weights_do_not_renormalize(self):
        inp,env,contract=fixture();train,_,labels=d.own_scope(inp,env,contract)
        rows,y,w,classes,_,_=d.pair_plan(train,inp['banks'],labels)
        margins=np.array([1. if c=='nonac_preservation' else -1. for c in classes]);loss=np.logaddexp(0.,-margins)
        total=d.pair_stats(range(len(rows)),w,margins,loss)
        ac=d.pair_stats((i for i,c in enumerate(classes) if c=='ac_nonac'),w,margins,loss)
        lower=d.pair_stats((i for i,c in enumerate(classes) if c!='ac_nonac'),w,margins,loss)
        self.assertAlmostEqual(ac['weight_mass'],1900.*2/3)
        self.assertAlmostEqual(ac['weight_mass']+lower['weight_mass'],total['weight_mass'])
        self.assertAlmostEqual(ac['weighted_logistic_loss']+lower['weighted_logistic_loss'],total['weighted_logistic_loss'])
        self.assertEqual(ac['positive_margin_rows'],0);self.assertEqual(lower['negative_margin_rows'],0)

    def test_numerical_hash_and_saved_optimum_zero_design(self):
        inp,env,contract=fixture();train,_,labels=d.own_scope(inp,env,contract)
        rows,y,w,_,_,_=d.pair_plan(train,inp['banks'],labels)
        x=sparse.csr_matrix((len(rows),4131),dtype=np.float64);theta=np.zeros(4131)
        hashes=dict(features=d.array_hash(np.array(x.shape,dtype='<i8'),x.indptr.astype('<i8'),x.indices.astype('<i8'),x.data.astype('<f8')),
            labels=d.array_hash(y.astype('<i8')),weights=d.array_hash(w.astype('<f8')),base_margin=d.array_hash(np.zeros(len(y),dtype='<f8')))
        model=dict(training=dict(input_sha256=hashes),optimization=dict(objective=190*math.log(2),weighted_logistic_loss=190*math.log(2),l2_penalty=0.),final_gradient=theta.tolist())
        margins,losses,check=d.numerical_check(x,y,w,theta,model)
        self.assertEqual(check['fresh_gradient_infinity'],0.);self.assertTrue(np.all(margins==0))
        with self.assertRaises(ValueError):d.numerical_check(x,y,2*w,theta,model)

    def test_ac_priority_labels_can_have_opposing_lower_tier_gradient(self):
        # Root's scalar existence witness, not an empirical result or optimizer.
        ids=[str(i) for i in range(9)];train=[dict(example_id='e',bank_id='b',user_id='u')]
        banks={'b':dict(candidate_ids=ids)}
        labels={('b',str(i)):label('b',str(i),ac=i==8,gain=1. if i==8 else (8-i)/10) for i in range(9)}
        rows,y,w,classes,_,_=d.pair_plan(train,banks,labels)
        feature={str(i):float(i) if i<8 else 9. for i in range(9)}
        x=np.zeros((len(rows),4131))
        for i,(_,a,b) in enumerate(rows):x[i,0]=feature[a]-feature[b]
        g=d.class_gradients(sparse.csr_matrix(x),y,w,classes,np.zeros(4131))['zero']['classes']
        self.assertEqual(g['ac_nonac']['cosine_with_ac_gradient'],1.)
        self.assertEqual(g['nonac_net_gain']['cosine_with_ac_gradient'],-1.)
        self.assertGreater(g['nonac_net_gain']['l2_norm'],g['ac_nonac']['l2_norm'])

    def test_complete_four_role_join_unknowns_and_secondary_misses(self):
        oof=[];rows=[]
        for held in range(5):
            old=dict(example_id=f'e{held}',bank_id=f'b{held}',problem_id='p',fold=held,current_status='known_nonac',
                H_known_ac=held==0,H_unknown=False,known_ac_miss=held!=0,known_oracle=True)
            oof.append(old)
            for index,f in enumerate(sorted(set(range(5))-{held})):
                rows.append(dict(example_id=old['example_id'],bank_id=old['bank_id'],training_model_fold=f,held_fold=held,
                    current_status=old['current_status'],methods={'H':dict(known_ac=index<held,unknown=False,known_regression=False)}))
        result=d.cross_roles(rows,oof)
        self.assertEqual(result['all_banks']['ac_role_counts'],{str(n):1 for n in range(5)})
        self.assertEqual(result['posthoc_67_oof_misses']['banks'],4)
        with self.assertRaises(ValueError):d.cross_roles(rows[:-1],oof)

    def test_label_nonac_never_outranks_stable_ac(self):
        for gain,loss in [(0.,0.),(1.,0.),(.3,.5)]:
            self.assertGreater(d.preference(label('b','a',True)),d.preference(label('b','n',gain=gain,loss=loss)))
        with self.assertRaises(ValueError):d.preference(label('b','x',unknown=True)|{'all_ac':False})


if __name__=='__main__':unittest.main()
