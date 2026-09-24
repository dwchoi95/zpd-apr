"""Pure synthetic readiness truth tables; no corpus, I/O, execution or fitting."""
import copy
from dataclasses import replace
import hashlib
import math
import unittest
from unittest.mock import patch

import numpy as np

from scripts import zpd_statement_sample_readiness as r
from scripts import zpd_statement_sample_progress as p
from tests.test_zpd_statement_sample_progress import fixture


CODES=('x=2\n','x=0\n','x=1\n','x=3\n','y=0\n','x=5\n','z=4\n','pass\n')
IDS=tuple(hashlib.sha256(v.encode()).hexdigest() for v in CODES)


def synthetic_bank(n=8,unknown=False,no_samples=False):
    args=fixture()
    if unknown or no_samples:args['vectors']={}
    if no_samples:args['universe']=replace(args['universe'],case_ids=())
    candidates=tuple(p.candidate_features(**dict(args,candidate_code=code)) for code in CODES[:n])
    return r.BankFeatures(IDS[:n],np.zeros((n,18),dtype=np.float64),np.ones((n,18),dtype=bool),candidates)


def spec(i=0,n=8,k=3):
    return r.BankSpec(f'e{i}',f'u{i}',f'p{i%23}',(i%23)%5,f'b{i}','a'*64,IDS[:n],IDS[0],('WA','WA','WA'),k)


def cohort(only_fold=None):
    good={n:synthetic_bank(n) for n in (7,8)}
    absent={n:synthetic_bank(n,unknown=True) for n in (7,8)} if only_fold is not None else None
    specs=tuple(spec(i,7 if i<16 else 8) for i in range(320))
    features={s.example_id:(good if only_fold is None or s.fold==only_fold else absent)[len(s.candidate_ids)] for s in specs}
    return specs,features


class StatementSampleReadinessTests(unittest.TestCase):
    def test_full_original320_all_conjunctions_and_diagnostics_without_io(self):
        specs,features=cohort()
        with patch('builtins.open',side_effect=AssertionError('pure gate attempted IO')):
            report=r.assess_readiness(specs,features)
        self.assertTrue(report['readiness_passed']);self.assertFalse(report['fit_release_authorized'])
        self.assertEqual((report['totals']['examples'],report['totals']['users'],report['totals']['problems'],report['totals']['candidates']),
                         (320,320,23,2544))
        self.assertEqual(len(report['rows']),320);self.assertEqual(report['excluded_examples'],0)
        self.assertEqual(set(report['totals']['candidate_diagnostics']),set(p.ARMS))
        for fold,groups in report['folds'].items():
            self.assertEqual(groups['train']['examples']+groups['held']['examples'],320)
            self.assertEqual(set(groups['train']['example_ids']),{s.example_id for s in specs if s.fold!=int(fold)})
            self.assertEqual(len(report['prerequisites'][fold]),9);self.assertTrue(all(report['prerequisites'][fold].values()))

    def test_held_only_support_does_not_rescue_its_training_fold_unknowns_retained(self):
        specs,features=cohort(only_fold=0);report=r.assess_readiness(specs,features)
        self.assertFalse(report['readiness_passed']);self.assertFalse(any(report['prerequisites']['0'].values()))
        self.assertTrue(all(all(report['prerequisites'][str(f)].values()) for f in range(1,5)))
        missing=sum(s.fold!=0 for s in specs)
        self.assertEqual(report['totals']['current_unavailable_reasons'],{'missing_feedback':missing})
        self.assertEqual(report['totals']['examples'],320);self.assertEqual(report['totals']['candidates'],2544)
        self.assertTrue(all(report['folds']['0']['train']['all_zero_banks'][a]==missing for a in p.ARMS))

    def test_each_of_nine_predicates_is_necessary_not_any_or_four_folds(self):
        train=r._aggregate([r.bank_record(spec(),synthetic_bank())])
        self.assertTrue(all(r._training_checks(train).values()))
        mutations=[('pairs','edited','varying_pairs','H'),('pairs','edited','old_masked18_tie_H_split_pairs'),
            *(('pairs','all','contrast_pairs',a) for a in r.CONTROLS),
            ('pairs','edited','contrast_pairs','CF'),('authentic_WA_WA_progress_transitions',),
            ('pairs','edited','wa_offdiagonal_varying_pairs')]
        for path in mutations:
            value=copy.deepcopy(train);target=value
            for key in path[:-1]:target=target[key]
            target[path[-1]]=0
            with self.subTest(path=path):
                checks=r._training_checks(value);self.assertEqual(sum(not v for v in checks.values()),1)

    def test_condition3_all_pairs_but_1_2_4_6_require_two_edited_candidates(self):
        x={a:np.zeros((3,32),dtype=np.float64) for a in p.ARMS}
        x['H'][1:,17]=.1  # common edited shift, distinguishable only from no-op
        old=np.zeros((3,18),dtype=np.float64);mask=np.ones((3,18),dtype=bool)
        off=x['H'].copy();geometry=r.pair_geometry(x,old,mask,0,off)
        self.assertEqual(geometry['all']['contrast_pairs']['Jm'],2)
        self.assertEqual(geometry['edited']['contrast_pairs']['Jm'],0)
        self.assertEqual(geometry['edited']['varying_pairs']['H'],0)
        self.assertEqual(geometry['edited']['old_masked18_tie_H_split_pairs'],0)
        self.assertEqual(geometry['edited']['contrast_pairs']['CF'],0)
        self.assertEqual(geometry['edited']['wa_offdiagonal_varying_pairs'],0)
        train=r._aggregate([r.bank_record(spec(),synthetic_bank())])
        for arm in r.CONTROLS:train['pairs']['edited']['contrast_pairs'][arm]=0
        self.assertTrue(all(r._training_checks(train).values()))  # #3 may not be strengthened to edited-only.

    def test_strict_tau_and_exact_masked18_tie_not_raw_or_approximate(self):
        x={a:np.zeros((3,32),dtype=np.float64) for a in p.ARMS};x['H'][1,17]=r.TOLERANCE
        old=np.zeros((3,18),dtype=np.float64);mask=np.ones((3,18),dtype=bool)
        old[1,0]=1;mask[1,0]=False  # raw rows differ, effective masked events tie exactly.
        g=r.pair_geometry(x,old,mask,0,x['H'])
        self.assertEqual(g['edited']['old_masked18_tied_pairs'],1)
        self.assertEqual(g['edited']['varying_pairs']['H'],0)
        x['H'][1,17]=np.nextafter(r.TOLERANCE,np.inf)
        g=r.pair_geometry(x,old,mask,0,x['H'])
        self.assertEqual(g['edited']['old_masked18_tie_H_split_pairs'],1)
        self.assertEqual(g['edited']['wa_offdiagonal_varying_pairs'],1)
        mask[1,0]=True
        self.assertEqual(r.pair_geometry(x,old,mask,0,x['H'])['edited']['old_masked18_tie_H_split_pairs'],0)

    def test_same_original_denominators_positions_and_no_wa_subset_renormalization(self):
        h=synthetic_bank().candidates[1].moments['H'];mask=np.array([True,False,False,True])
        weights,op=p.conditional_weights(mask);sim=np.array([[1.,0.],[0.,0.],[0.,0.],[0.,0.]])
        raw=np.zeros((2,2,4));raw[:,0,1]=weights[:,0]
        h=replace(h,mask=mask,weights=weights,opportunity=op,similarities=sim,
            paired_counts=((0,1,0,0),None,None,(0,0,0,1)),wa_offdiagonal=raw)
        s=replace(spec(),original_nominal_sequence=('WA','WA','CE','AC','AC'),sample_count=1)
        contribution,ts=r._offdiagonal(s,h)
        self.assertEqual(ts,(0,));self.assertEqual(contribution[17],.5/math.sqrt(12.0))
        self.assertAlmostEqual(contribution[25],.2/math.sqrt(12.0),places=16)
        self.assertNotEqual(contribution[25],(1/3)/math.sqrt(12.0))
        self.assertNotEqual(contribution[25],1/math.sqrt(12.0))
        bad=raw.copy();bad[:,0,1]=1
        with self.assertRaisesRegex(ValueError,'original-weight'):r._offdiagonal(s,replace(h,wa_offdiagonal=bad))

    def test_progress_witness_plus_unrelated_variation_cannot_satisfy_condition6(self):
        h=synthetic_bank().candidates[1].moments['H']
        sim=h.similarities.copy();sim[0]=0
        h=replace(h,similarities=sim,wa_offdiagonal=np.zeros((2,2,4)))
        s=replace(spec(),original_nominal_sequence=('WA','WA','CE'))
        contribution,ts=r._offdiagonal(s,h)
        self.assertEqual(ts,(0,));self.assertFalse(contribution.any())
        train=r._aggregate([r.bank_record(spec(),synthetic_bank())])
        train['pairs']['edited']['wa_offdiagonal_varying_pairs']=0
        checks=r._training_checks(train)
        self.assertTrue(checks['condition5_eligible_edited_authentic_WA_WA_progress'])
        self.assertTrue(checks['condition1_edited_H_varies'])
        self.assertFalse(checks['condition6_edited_WA_WA_contribution_varies'])

    def test_missing_samples_are_retained_and_never_inferred_all_fail(self):
        row=r.bank_record(replace(spec(),sample_count=0),synthetic_bank(no_samples=True))
        self.assertFalse(row['current_feedback_available']);self.assertEqual(row['current_feedback_reason'],'unavailable_samples')
        self.assertEqual(row['eligible_authentic_WA_WA_offdiagonal_transition_indices'],[])
        self.assertTrue(all(row['all_zero'].values()))
        self.assertEqual(len(row['candidate_ids']),8)

    def test_exact_cohort_fold_sample_and_candidate_coverage(self):
        specs,features=cohort()
        for mode in ('drop','extra','duplicate_user','split_problem','sample_count','candidate_count'):
            values=list(specs);given=dict(features)
            if mode=='drop':given.pop(specs[0].example_id)
            elif mode=='extra':given['new-example']=next(iter(features.values()))
            elif mode=='duplicate_user':values[1]=replace(values[1],user_id=values[0].user_id)
            elif mode=='split_problem':values[23]=replace(values[23],fold=1)
            elif mode=='sample_count':values[23]=replace(values[23],sample_count=2)
            else:values[0]=replace(values[0],candidate_ids=IDS)
            with self.subTest(mode=mode),self.assertRaises(ValueError):r.assess_readiness(tuple(values),given)
        for bad in (False,1.0,-1,5):
            with self.subTest(fold=bad),self.assertRaises(ValueError):replace(spec(),fold=bad)

    def test_strict_feature_shapes_binary_values_and_noop(self):
        f=synthetic_bank()
        for mode in ('order','old_binary','old_mask_dtype','arm_shape','arm_missing','nan','nonzero_noop'):
            value=f
            if mode=='order':value=replace(f,candidate_ids=tuple(reversed(f.candidate_ids)))
            elif mode=='old_binary':
                x=f.old_event_values.copy();x[0,0]=.5;value=replace(f,old_event_values=x)
            elif mode=='old_mask_dtype':value=replace(f,old_event_masks=f.old_event_masks.astype(int))
            else:
                cs=list(f.candidates);i=0 if mode=='nonzero_noop' else 1;arms=dict(cs[i].arms)
                if mode=='arm_missing':arms.pop('CF')
                elif mode=='arm_shape':arms['H']=np.zeros(31)
                elif mode=='nan':arms['H']=arms['H'].copy();arms['H'][0]=np.nan
                else:cs[0]=cs[1]
                if mode!='nonzero_noop':cs[i]=replace(cs[i],arms=arms)
                value=replace(f,candidates=tuple(cs))
            with self.subTest(mode=mode),self.assertRaises(ValueError):r.bank_record(spec(),value)

    def test_candidate_specific_feedback_history_facts_and_unavailable_nonzero_rejected(self):
        f=synthetic_bank()
        for mode in ('current_counts','paired_counts','history_mass','hs_permutation','unavailable'):
            cs=list(f.candidates);c=cs[1];ms=dict(c.moments)
            if mode=='current_counts':ms={a:replace(m,current_counts=(2,0,0,1)) for a,m in ms.items()}
            elif mode=='paired_counts':
                m=ms['H'];ms['H']=replace(m,paired_counts=((1,1,0,1),m.paired_counts[1]))
            elif mode=='history_mass':
                m=ms['H'];ms['H']=replace(m,history_masses=(999,*m.history_masses[1:]))
            elif mode=='hs_permutation':
                m=ms['HS'];ms['HS']=replace(m,permutation_indices=tuple(reversed(m.permutation_indices)))
            else:
                ms={a:replace(m,candidate_available=False,mask=np.zeros_like(m.mask),weights=np.zeros_like(m.weights),
                    opportunity=np.zeros_like(m.opportunity),paired_counts=(None,)*len(m.mask)) for a,m in ms.items()}
            cs[1]=replace(c,moments=ms)
            with self.subTest(mode=mode),self.assertRaises(ValueError):r.bank_record(spec(),replace(f,candidates=tuple(cs)))

    def test_arithmetic_tampering_cannot_replace_original_conditional_contribution(self):
        f=synthetic_bank()
        for mode in ('weight','contribution','counts_bool','nominal_length'):
            cs=list(f.candidates);c=cs[1];ms=dict(c.moments);m=ms['H'];s=spec()
            if mode=='weight':
                weights=m.weights.copy();weights[:,0]=1;ms['H']=replace(m,weights=weights);c=replace(c,moments=ms)
            elif mode=='contribution':c=replace(c,wa_offdiagonal_contribution=np.zeros(32))
            elif mode=='counts_bool':
                ms['H']=replace(m,paired_counts=((2,True,0,0),m.paired_counts[1]));c=replace(c,moments=ms)
            else:s=replace(s,original_nominal_sequence=('WA','WA'))
            cs[1]=c
            with self.subTest(mode=mode),self.assertRaises(ValueError):r.bank_record(s,replace(f,candidates=tuple(cs)))


if __name__=='__main__':unittest.main()
