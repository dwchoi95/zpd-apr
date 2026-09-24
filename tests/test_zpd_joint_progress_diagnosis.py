"""Focused synthetic diagnosis witnesses; no archive reads or optimizers."""
from dataclasses import dataclass
import copy
import unittest

import numpy as np
from scipy import sparse

from scripts import diagnose_zpd_joint_progress as d


def fixture():
    ids=('1'*64,'2'*64,'3'*64)
    current=np.zeros((3,4099));current[1,0]=2.;current[2,0]=1.
    current=sparse.csr_matrix(current)
    phi={a:np.zeros((3,32)) for a in d.ARMS}
    for arm in d.ARMS[:-2]:phi[arm][2,16]=.2
    theta=np.zeros(4131);theta[0]=1.;theta[4115]=10.
    scores={cid:float(v) for cid,v in zip(ids,[0.,2.,3.])}
    shared={cid:float(v) for cid,v in zip(ids,[0.,2.,1.])}
    prediction=dict(example_id='synthetic',problem_id='problem',fold=0,bank_id='bank',
        candidate_scores={'H':scores,'shared_H_CF':shared},
        choices={'H':ids[2],'shared_H_CF':ids[1],'CF':ids[1],'noop':ids[0]})
    labels={ids[0]:dict(status='stable',all_ac=False,loss=0.),
        ids[1]:dict(status='stable',all_ac=True,loss=0.),ids[2]:dict(status='stable',all_ac=False,loss=1.)}
    return ids,prediction,current,phi,theta,labels


def wire(matrix):
    return dict(format='csr',shape=list(matrix.shape),data_dtype='<f8',index_dtype='<i8',
        data_hex=matrix.data.astype('<f8').tobytes().hex(),
        indices_hex=matrix.indices.astype('<i8').tobytes().hex(),
        indptr_hex=matrix.indptr.astype('<i8').tobytes().hex())


class JointDiagnosisTests(unittest.TestCase):
    def test_exact_classes_merge_signed_zero_but_not_nearby_values(self):
        value=np.array([[0.,-0.],[0.,0.],[0.,np.nextafter(0.,1.)],[0.,1e-15]])
        self.assertEqual(d.exact_classes(value),[[0,1],[2],[3]])

    def test_wrong_sign_residual_is_additive_and_shared_sensitivity_is_separate(self):
        ids,p,current,phi,theta,labels=fixture()
        row=d.bank_diagnosis(p,current,phi,theta,labels)
        self.assertTrue(row['known_ac_miss']);self.assertFalse(row['class_blocked_known_miss'])
        self.assertEqual(row['selected_minus_best_known_ac'],dict(current4099=-1.,G16=0.,residual16=2.,total=1.,residual_direction='positive'))
        self.assertEqual(row['paired']['shared_H_CF']['ac_lost'],1)
        self.assertEqual(row['paired']['shared_H_CF']['regression_introduced'],1)
        self.assertEqual(row['CF_refitted_vs_shared']['selected_candidate_changed'],0)

    def test_unknown_is_not_failure_or_regression_and_possible_oracle_remains(self):
        ids,p,current,phi,theta,labels=fixture()
        labels[ids[1]]=dict(status='unknown',all_ac=None,loss=None)
        row=d.bank_diagnosis(p,current,phi,theta,labels)
        self.assertFalse(row['known_oracle']);self.assertTrue(row['possible_oracle'])
        self.assertFalse(row['known_ac_miss']);self.assertIsNone(row['selected_minus_best_known_ac'])
        self.assertEqual(row['paired']['CF']['not_jointly_known'],1)
        self.assertEqual(row['paired']['CF']['ac_lost'],0)

    def test_full_feature_tie_has_only_sha_champion_not_old_base_champion(self):
        ids,p,current,phi,theta,labels=fixture()
        current=sparse.csr_matrix((3,4099));phi={a:np.zeros((3,32)) for a in d.ARMS};theta=np.zeros(4131)
        p['candidate_scores']={m:dict.fromkeys(ids,0.) for m in ('H','shared_H_CF')}
        p['choices']=dict(H=ids[0],CF=ids[0],shared_H_CF=ids[0],noop=ids[0])
        row=d.bank_diagnosis(p,current,phi,theta,labels)
        self.assertEqual(row['class_sha_champions'],[ids[0]])
        self.assertTrue(row['class_blocked_known_miss'])
        self.assertFalse(row['known_ac_class_champion'])

    def test_class_accessibility_does_not_assert_joint_linear_realizability(self):
        # Two banks can have distinguishable AC alternatives with opposite
        # features requiring opposite coefficient signs. Class ceiling alone
        # is only a bank-local necessary condition.
        self.assertEqual(len(d.exact_classes(np.array([[0.],[1.]]))),2)
        self.assertEqual(len(d.exact_classes(np.array([[0.],[-1.]]))),2)
        self.assertFalse(any(t>0 and -t>0 for t in [-2.,-1.,0.,1.,2.]))

    def test_recomputed_selection_is_strict_even_when_scores_are_within_tolerance(self):
        ids,p,current,phi,theta,labels=fixture()
        p['choices']['H']=ids[1]
        with self.assertRaisesRegex(ValueError,'selected SHA'):
            d.bank_diagnosis(p,current,phi,theta,labels)
        p['choices']['H']=ids[2];p['candidate_scores']['H'][ids[2]]+=.1
        with self.assertRaisesRegex(ValueError,'H score'):
            d.bank_diagnosis(p,current,phi,theta,labels)

    def test_saved_scaler_is_used_without_refit_and_progress_is_not_rescaled(self):
        ids,*_=fixture();num=sparse.csr_matrix(np.array([[0.,0.,0.],[2.,6.,10.],[4.,3.,5.]]))
        hashed=sparse.csr_matrix((3,4096))
        raw=dict(candidate_ids=list(ids),numeric=wire(num),hashed=wire(hashed))
        progress={}
        for arm in d.ARMS[:-1]:
            values=np.zeros((3,32));values[1,0]=.1
            if arm!='CF':values[1,16]=-.2
            progress[arm]=dict(candidate_ids=list(ids),dtype='<f8',shape=[3,32],data_hex=values.tobytes().hex())
        current,phi=d.matrices(raw,progress,[2.,3.,5.],ids)
        np.testing.assert_array_equal(current.toarray()[:,:3],[[0.,0.,0.],[1.,2.,2.],[2.,1.,1.]])
        self.assertEqual(phi['H'][1,16],-.2);self.assertFalse(np.any(phi['C_joint']))
        raw['numeric']['shape']=[True,3]
        with self.assertRaises(ValueError):d.matrices(raw,progress,[2.,3.,5.],ids)

    def test_all_rows_and_unknowns_survive_aggregation(self):
        ids,p,current,phi,theta,labels=fixture()
        a=d.bank_diagnosis(p,current,phi,theta,labels)
        labels[ids[0]]=dict(status='unknown',all_ac=None,loss=None)
        b=d.bank_diagnosis(dict(p,example_id='unknown-original'),current,phi,theta,labels)
        totals=d.aggregate([a,b])
        self.assertEqual(totals['examples'],2);self.assertEqual(totals['candidates'],6)
        self.assertEqual(totals['known_ac_miss'],2)
        self.assertEqual(b['current_status'],'unknown')
        self.assertEqual(totals['paired']['noop']['not_jointly_known'],1)


if __name__=='__main__':unittest.main()
