"""Deterministic diagnostic witnesses; no fitting or empirical artifacts."""
from fractions import Fraction
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np

from scripts import diagnose_zpd_repair_progress32 as d


def label(bank,cid,*,ac=False,loss=0.,unknown=False):
    return dict(bank_id=bank,candidate_id=cid,status='unknown' if unknown else 'stable',
                all_ac=None if unknown else ac,gain=None if unknown else 0.,loss=None if unknown else loss)


def fixture(*,base=None,theta=None,matrix=None,ac='a',unknown=()):
    ids=('a','b','n');base=base or dict(a=1.,b=2.,n=0.)
    x=np.zeros((3,32)) if matrix is None else np.asarray(matrix,dtype=np.float64)
    theta=np.zeros(32) if theta is None else np.asarray(theta,dtype=np.float64)
    scores={m:dict(base) for m in d.METHODS}
    scores['H']={c:base[c]+d.dot(theta,x[i]) for i,c in enumerate(ids)}
    scores['noop']={c:float(c=='n') for c in ids}
    choices={m:d.top(s) for m,s in scores.items()}
    p=dict(example_id='example',user_id='user',bank_id='bank',problem_id='problem',fold=0,
        choices=choices,candidate_scores=scores)
    labs={('bank',c):label('bank',c,ac=c==ac,unknown=c in unknown) for c in ids}
    # Pure geometry uses tiny readable IDs; real loading uses the independently
    # validated SHA-identified capsule CandidateBlock. No parser is bypassed by
    # the production loader or altered to accommodate this synthetic fixture.
    return p,SimpleNamespace(candidate_ids=ids,matrix=x),theta,labs


class Progress32DiagnosisTests(unittest.TestCase):
    def test_logistic_gradient_leverage_and_quantiles_have_scalar_witness(self):
        x=np.zeros((2,32));x[0,0]=1.;x[1,0]=-1.
        y=np.array([1,0]);w=np.array([950.,950.]);theta=np.zeros(32)
        zero=d.logistic_statistics(x,y,w,np.zeros(2),theta)
        self.assertEqual(zero['gradient_at_zero_l2'],95.)
        self.assertEqual(zero['logistic_leverage_C_sum_w_sigmoid_negative_signed_base'],95.)
        self.assertEqual(zero['weighted_base_tie_mass_fraction'],1.)
        saturated=d.logistic_statistics(x,y,w,np.array([20.,-20.]),theta)
        self.assertAlmostEqual(saturated['gradient_at_zero_l2'],190./(1+np.exp(20.)),places=15)
        self.assertEqual(saturated['weighted_base_sign_accuracy'],1.)
        self.assertLess(saturated['gradient_at_zero_l2'],1e-6)
        self.assertEqual(d.weighted_quantiles([1,2,3],[1,2,1]),{'0.0':1.,'0.25':1.,'0.5':2.,'0.75':2.,'1.0':3.})

    def test_independent_original_pairs_and_two_normalizations_match_pure_reference(self):
        from tests.test_zpd_repair_progress_capsule import fixture as inputs_fixture
        inp=inputs_fixture();labs={}
        train,_=d.capsule.scope(inp);banks={e.bank_id:inp.banks[e.bank_id] for e in train}
        for bid,bank in banks.items():
            for i,c in enumerate(bank.candidates):
                labs[bid,c.candidate_id]=label(bid,c.candidate_id,ac=i==1,unknown=i==len(bank.candidates)-1 and not c.is_noop)
        x,y,w,b,ids,examples=d.training_arrays(inp,labs)
        plan=d.capsule.newton.make_pair_plan(train,banks,labs)
        reference=d.capsule.newton.materialize_pairs(plan,{bid:inp.interactions['H'][bid] for bid in banks},
            {bid:inp.base_scores[bid] for bid in banks},spec=inp.interactions and d.capsule.SPEC)
        np.testing.assert_array_equal(x,reference.matrix)
        np.testing.assert_array_equal(y,reference.y)
        np.testing.assert_array_equal(w,reference.weights)
        np.testing.assert_array_equal(b,reference.base_margin)
        self.assertEqual(ids,reference.metadata['pair_candidate_ids'])
        self.assertEqual(examples,reference.metadata['training']['pair_example_ids'])

    def test_feature_class_ceiling_and_radius_are_not_disjoint(self):
        p,block,theta,labs=fixture()
        r=d.bank_diagnosis(p,block,theta,labs)
        self.assertTrue(r['oracle_known_ac']);self.assertTrue(r['class_blocked_known_ac'])
        self.assertTrue(r['radius_blocked_known_ac'])
        self.assertEqual(r['miss_partition'],'feature_class_blocked')
        self.assertEqual(r['exact_feature_classes'],1)

    def test_accessible_ac_can_be_outside_observed_coefficient_radius(self):
        x=np.zeros((3,32));x[0,16]=.2;t=np.zeros(32);t[16]=.1
        p,block,theta,labs=fixture(matrix=x,theta=t)
        r=d.bank_diagnosis(p,block,theta,labs)
        self.assertTrue(r['class_champion_known_ac']);self.assertTrue(r['radius_blocked_known_ac'])
        self.assertAlmostEqual(r['radius_min_slack'],.98)
        self.assertEqual(r['miss_partition'],'accessible_radius_blocked')

    def test_wrong_sign_residual_can_destroy_a_correct_base_choice(self):
        x=np.zeros((3,32));x[1,16]=.2;t=np.zeros(32);t[16]=1.
        p,block,theta,labs=fixture(base=dict(a=1.,b=.9,n=0.),matrix=x,theta=t)
        r=d.bank_diagnosis(p,block,theta,labs)
        self.assertEqual(p['choices']['structural_C'],'a');self.assertEqual(p['choices']['H'],'b')
        self.assertFalse(r['radius_blocked_known_ac']);self.assertTrue(r['missed_known_ac'])
        margin=r['best_known_ac_comparison']
        self.assertAlmostEqual(margin['base_advantage_wrong_choice'],-.1)
        self.assertAlmostEqual(margin['residual_block_advantage_wrong_choice'],.2)
        self.assertAlmostEqual(margin['final_score_advantage_wrong_choice'],.1)
        switched=d.switches([p],labs,'structural_C')
        self.assertEqual(switched['counts']['ac_lost'],1)
        self.assertEqual(switched['counts']['edited_to_edited'],1)

    def test_unknown_candidates_do_not_become_known_oracle_success_or_failure(self):
        p,block,theta,labs=fixture(ac=None,unknown=('b',))
        r=d.bank_diagnosis(p,block,theta,labs)
        self.assertFalse(r['oracle_known_ac']);self.assertTrue(r['oracle_possible_ac'])
        self.assertTrue(r['H_unknown']);self.assertFalse(r['missed_known_ac'])
        m=d.metrics([p],labs,'H')
        self.assertEqual(m['counts']['unknown'],1)
        self.assertEqual(m['fractions']['ac_lower'],Fraction(0))
        self.assertEqual(m['fractions']['ac_upper'],Fraction(1))
        self.assertEqual(d.switches([p],labs,'CF')['counts']['unknown_comparison'],1)

    def test_sha_tie_and_signed_zero_share_the_same_exact_class(self):
        x=np.zeros((3,32));x[0,0]=-0.
        p,block,theta,labs=fixture(base=dict(a=2.,b=2.,n=0.),matrix=x)
        r=d.bank_diagnosis(p,block,theta,labs)
        self.assertEqual(r['exact_feature_classes'],1)
        self.assertTrue(r['class_champion_known_ac']);self.assertTrue(r['H_known_ac'])

    def test_score_mismatch_and_nonfinite_theta_refused(self):
        p,block,theta,labs=fixture();p['candidate_scores']['H']['a']+=.01
        with self.assertRaisesRegex(ValueError,'coefficient score'):d.bank_diagnosis(p,block,theta,labs)
        p,block,theta,labs=fixture();theta[0]=float('nan')
        with self.assertRaisesRegex(ValueError,'finite32'):d.bank_diagnosis(p,block,theta,labs)

    def test_equal_problem_is_exact_and_not_pooled(self):
        p,_,_,labs=fixture();pred=[]
        for i in range(3):
            row=dict(p,example_id=str(i),user_id=str(i),bank_id=str(i),problem_id='small' if i==0 else 'large')
            pred.append(row)
            for cid in ('a','b','n'):labs[str(i),cid]=label(str(i),cid,ac=i==0 and cid=='b')
        result=d.summarize(pred,labs)
        self.assertEqual(result['methods']['H']['fractions']['ac_lower'],Fraction(1,3))
        self.assertEqual(result['equal_problem']['H']['ac_lower'],Fraction(1,2))
        self.assertEqual(d.serial(Fraction(1,3))['denominator'],3)

    def test_support_masks_keep_unavailable_and_original_nominal_sequence(self):
        p,block,theta,labs=fixture()
        moment=dict(candidate_available=True,mask=[True,False,True],paired_counts=[[0,1,0,0],None,[1,0,0,0]])
        cs=[dict(arms={a:[0.]*32 for a in d.ARMS},moments={'H':moment},
            wa_offdiagonal_contribution=[0.]*32,current_feedback_available=True,current_feedback_reason=None) for _ in range(3)]
        feature=dict(spec=dict(example_id='example',original_nominal_sequence=['WA','WA','RE','WA']),
            candidate_ids=['a','b','n'],candidates=cs)
        r=d.bank_diagnosis(p,block,theta,labs,feature)['support']
        self.assertEqual(r['prior_transitions'],3);self.assertEqual(r['eligible_transitions'],2)
        self.assertEqual(r['WA_WA_offdiag_transitions'],1)
        self.assertFalse(r['edited_WA_WA_contribution_varies']);self.assertFalse(r['constant_feedback'])
        self.assertTrue(r['H_all_zero'])

    def test_consumed_reader_rejects_path_escape_and_byte_drift(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();(root/'x.json').write_bytes(b'{}\n');r=d.Reader(root)
            self.assertEqual(r.json('x.json',d.digest(b'{}\n')), {})
            for name in ('../x.json','/x.json','a/../x.json'):
                with self.assertRaises(ValueError):r.read(name,'a'*64)
            (root/'x.json').write_bytes(b'{"changed":true}\n')
            with self.assertRaisesRegex(ValueError,'SHA differs'):r.recheck()
        with self.assertRaises(ValueError):d.decode(b'{"a":1,"a":2}')
        with self.assertRaises(ValueError):d.decode(b'{"x":NaN}')


if __name__=='__main__':unittest.main()
