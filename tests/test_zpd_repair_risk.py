"""Synthetic fixed-mass risk/ranking checks, not empirical performance evidence."""
import copy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts.zpd_repair_fit import history, load_inputs
from scripts.zpd_repair_pairwise import score_model, train_model, training_data
from scripts.zpd_repair_risk import (
    risk_logits, risk_scores, select_filtered, train_fixed_ranker, train_risk_model)
from src.repair.pilot_contracts import CandidateAttempt, canonical_hash, source_hash
from tests.test_zpd_repair_pairwise import fixture


class RiskTests(unittest.TestCase):
    def data(self):
        return load_inputs(*fixture())

    def test_reference_mass_preserves_original_rank_fit_and_schema(self):
        examples,banks,labels=self.data()
        for condition in ('C','H','U'):
            reference=len(training_data(examples,banks,labels,condition,'lexical')[2])
            old=train_model(examples,banks,labels,condition,'lexical',.1)
            new=train_fixed_ranker(examples,banks,labels,condition,reference)
            np.testing.assert_allclose(old['coefficients'],new['coefficients'],rtol=1e-10,atol=1e-10)
            self.assertEqual(new['C'],.1)
            self.assertAlmostEqual(new['training']['sample_weight_sum'],reference)
            self.assertEqual(new['training']['reference_pair_weight'],reference)
            ex=examples[-1]
            score_model(new,ex.observation,history(ex,condition),banks[ex.bank_id])

    def test_risk_never_reads_validation_labels_or_fits_at_prediction(self):
        examples,banks,labels=self.data()
        only_train={key:value for key,value in labels.items() if key[0]!='b2'}
        first=train_risk_model(examples,banks,labels,'H',6)
        second=train_risk_model(examples,banks,only_train,'H',6)
        self.assertEqual(first,second)
        self.assertEqual(first,train_risk_model(examples[:2],banks,only_train,'H',6))
        rank=train_fixed_ranker(examples,banks,only_train,'H',12)
        ex=examples[-1]
        with patch.object(LogisticRegression,'fit',side_effect=AssertionError('prediction fit')), \
             patch.object(StandardScaler,'fit',side_effect=AssertionError('prediction scaling')):
            scores=risk_scores(json.loads(json.dumps(first)),ex.observation,ex.observation.prior,banks[ex.bank_id])
            candidate=select_filtered(rank,first,ex.observation,ex.observation.prior,banks[ex.bank_id])
        self.assertIn(candidate,scores)
        self.assertTrue(all(0<=v<=1 and np.isfinite(v) for v in scores.values()))

    def test_fixed_total_mass_does_not_grow_with_duplicate_support(self):
        examples,banks,labels=self.data()
        expanded=list(examples)
        for ex in examples[:2]:
            duplicate=copy.copy(ex);duplicate.example_id+='-copy';duplicate.user_id+='-copy'
            expanded.append(duplicate)
        for fit,reference,key in [(train_fixed_ranker,12,'reference_pair_weight'),
                                   (train_risk_model,6,'reference_candidate_weight')]:
            original=fit(examples,banks,labels,'C',reference)
            larger=fit(expanded,banks,labels,'C',reference)
            self.assertAlmostEqual(original['training']['sample_weight_sum'],reference)
            self.assertAlmostEqual(larger['training']['sample_weight_sum'],reference)
            self.assertEqual(larger['training'][key],reference)
            np.testing.assert_allclose(original['coefficients'],larger['coefficients'],rtol=1e-8,atol=1e-8)
            self.assertAlmostEqual(original['intercept'],larger['intercept'])

    def test_equal_user_prefix_candidate_weights_with_fixed_mass(self):
        examples,banks,labels=self.data()
        extra=copy.copy(examples[0]);extra.example_id='extra';examples.append(extra)
        observed=[];original_fit=LogisticRegression.fit
        def record(estimator,x,y,sample_weight=None):
            observed.append(np.array(sample_weight))
            return original_fit(estimator,x,y,sample_weight=sample_weight)
        with patch.object(LogisticRegression,'fit',autospec=True,side_effect=record):
            model=train_risk_model(examples,banks,labels,'C',6)
        self.assertEqual(len(observed),1)
        ids=model['training']['candidate_example_ids'];user={ex.example_id:ex.user_id for ex in examples}
        sums={u:0. for u in ('u0','u1')}
        for ident,weight in zip(ids,observed[0]):sums[user[ident]]+=weight
        self.assertAlmostEqual(sums['u0'],3)
        self.assertAlmostEqual(sums['u1'],3)
        self.assertEqual(model['training']['stable_train_candidates'],9)
        self.assertEqual(model['training']['class_counts'],{'non_regression':6,'regression':3})
        self.assertAlmostEqual(model['training']['class_weight_sums']['regression'],2)

    def test_unknown_exclusion_and_zero_stable_abort(self):
        examples,banks,labels=self.data()
        for (bid,_),lab in labels.items():
            if bid=='b0':lab.update(status='unknown',gain=None,loss=None,all_ac=None)
        model=train_risk_model(examples,banks,labels,'C',6)
        meta=model['training']
        self.assertEqual(meta['stable_train_candidates'],3)
        self.assertEqual(meta['unknown_train_candidates'],3)
        self.assertEqual(meta['excluded_train_example_ids'],['e0'])
        self.assertEqual(meta['users_without_stable_candidates'],1)
        self.assertAlmostEqual(meta['sample_weight_sum'],6)
        for (bid,_),lab in labels.items():
            if bid=='b1':lab.update(status='unknown',gain=None,loss=None,all_ac=None)
        with self.assertRaisesRegex(ValueError,'no stable'):train_risk_model(examples,banks,labels,'C',6)
        with self.assertRaisesRegex(ValueError,'no unequal'):train_fixed_ranker(examples,banks,labels,'C',12)

    def test_single_class_uses_fixed_mass_laplace_probability(self):
        examples,banks,labels=self.data()
        for lab in labels.values():lab.update(gain=0.,loss=0.,all_ac=False)
        model=train_risk_model(examples,banks,labels,'C',6)
        ex=examples[-1]
        self.assertTrue(model['training']['one_class_laplace_constant'])
        scores=risk_scores(model,ex.observation,(),banks[ex.bank_id])
        np.testing.assert_allclose(list(scores.values()),[1/8]*3)
        self.assertTrue(all(v==0 for v in model['coefficients']))

    def test_invalid_reference_inputs_and_future_history_rejected(self):
        examples,banks,labels=self.data()
        for fit in (train_fixed_ranker,train_risk_model):
            for reference in (0,-1,float('inf'),float('nan'),True,'6'):
                with self.subTest(fit=fit.__name__,reference=reference),self.assertRaises(ValueError):
                    fit(examples,banks,labels,'C',reference)
        invalid=copy.copy(examples[-1]);invalid.split='test'
        with self.assertRaisesRegex(ValueError,'train and exposed valid'):
            train_risk_model(examples+[invalid],banks,labels,'C',6)
        model=train_risk_model(examples,banks,labels,'H',6);ex=examples[-1]
        with self.assertRaisesRegex(ValueError,'authentic'):
            risk_scores(model,ex.observation,ex.donor_history,banks[ex.bank_id])

    def test_risk_hash_schema_numeric_and_condition_checks(self):
        examples,banks,labels=self.data();ex=examples[-1]
        model=train_risk_model(examples,banks,labels,'C',6)
        for mutation in ('hash','extra','dimension','scale','type'):
            bad=copy.deepcopy(model)
            if mutation=='hash':bad['coefficients'][0]+=1
            if mutation=='extra':bad['future_label']=True
            if mutation=='dimension':bad['coefficients']=bad['coefficients'][:-1]
            if mutation=='scale':bad['numeric_scale'][0]=0
            if mutation=='type':bad['intercept']=True
            if mutation not in ('hash','extra'):
                bad['model_sha256']=canonical_hash({k:v for k,v in bad.items() if k!='model_sha256'})
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                risk_scores(bad,ex.observation,(),banks[ex.bank_id])
        rank=train_fixed_ranker(examples,banks,labels,'H',12)
        with self.assertRaisesRegex(ValueError,'matching fixed'):
            select_filtered(rank,model,ex.observation,(),banks[ex.bank_id])

    def test_first_relative_filter_inclusive_and_noop_always_eligible(self):
        examples,banks,_=self.data();ex=examples[-1];bank=banks[ex.bank_id]
        noop=source_hash(bank.current_source);first=source_hash(bank.attempts[0].source)
        other=next(c.candidate_id for c in bank.candidates if c.candidate_id not in (noop,first))
        rank={'condition':'C','C':.1,'variant':'lexical'};risk={'condition':'C'}
        ranking={noop:1.,first:5.,other:9.};probability={noop:.9,first:.2,other:.8}
        with patch('scripts.zpd_repair_risk.score_model',return_value=ranking), \
             patch('scripts.zpd_repair_risk.risk_logits',return_value=probability):
            self.assertEqual(select_filtered(rank,risk,ex.observation,(),bank),first)
            probability[other]=.2
            self.assertEqual(select_filtered(rank,risk,ex.observation,(),bank),other)
            ranking[noop]=10.
            self.assertEqual(select_filtered(rank,risk,ex.observation,(),bank),noop)
            self.assertEqual(probability[noop],.9)  # Never fabricate zero risk.
            ranking.update({noop:1.,first:5.,other:5.})
            self.assertEqual(select_filtered(rank,risk,ex.observation,(),bank),min(first,other))

    def test_failed_first_attempt_falls_back_to_exact_noop(self):
        examples,banks,_=self.data();ex=examples[-1];bank=banks[ex.bank_id]
        attempt=bank.attempts[0]
        bank=replace(bank,attempts=(CandidateAttempt(attempt.index,attempt.seed,'generation_failure',None,'synthetic'),)+bank.attempts[1:])
        noop=source_hash(bank.current_source);ranking={c.candidate_id:10. for c in bank.candidates};ranking[noop]=1.
        probability={c.candidate_id:.8 for c in bank.candidates};probability[noop]=.1
        with patch('scripts.zpd_repair_risk.score_model',return_value=ranking), \
             patch('scripts.zpd_repair_risk.risk_logits',return_value=probability):
            chosen=select_filtered({'condition':'C','C':.1,'variant':'lexical'},
                {'condition':'C'},ex.observation,(),bank)
        self.assertEqual(chosen,noop)

    def test_extreme_logits_report_finitely_without_losing_filter_order(self):
        examples,banks,labels=self.data();ex=examples[-1];bank=banks[ex.bank_id]
        model=train_risk_model(examples,banks,labels,'C',6)
        for intercept,probability in ((1000.,1.),(-1000.,0.)):
            extreme=copy.deepcopy(model)
            extreme['coefficients']=[0.]*len(extreme['coefficients'])
            extreme['intercept']=intercept
            extreme['model_sha256']=canonical_hash({k:v for k,v in extreme.items() if k!='model_sha256'})
            self.assertEqual(set(risk_logits(extreme,ex.observation,(),bank).values()),{intercept})
            self.assertEqual(set(risk_scores(extreme,ex.observation,(),bank).values()),{probability})
        noop=source_hash(bank.current_source);first=source_hash(bank.attempts[0].source)
        other=next(c.candidate_id for c in bank.candidates if c.candidate_id not in (noop,first))
        ranking={noop:1.,first:5.,other:9.}
        for baseline_logit,unsafe_logit in ((40.,50.),(1000.,1001.),(-1000.,-999.)):
            logits={noop:unsafe_logit+1,first:baseline_logit,other:unsafe_logit}
            with self.subTest(baseline_logit=baseline_logit), \
                 patch('scripts.zpd_repair_risk.score_model',return_value=ranking), \
                 patch('scripts.zpd_repair_risk.risk_logits',return_value=logits), \
                 patch('scripts.zpd_repair_risk.risk_scores',side_effect=AssertionError('saturated probability used')):
                chosen=select_filtered({'condition':'C','C':.1,'variant':'lexical'},
                    {'condition':'C'},ex.observation,(),bank)
            self.assertEqual(chosen,first)


if __name__=='__main__':unittest.main()
