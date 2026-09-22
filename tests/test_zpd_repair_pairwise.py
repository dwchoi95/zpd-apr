"""Synthetic pairwise correctness checks, never empirical performance evidence."""
import copy
import json
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts.zpd_repair_fit import load_inputs, history
from scripts.zpd_repair_pairwise import (fit_report, lexical_features, preference,
    score_model, select_model, selection_key, train_model, training_data)
from src.repair.pilot_contracts import source_hash
from src.repair.pilot_ranker import features


def fixture():
    def source(ident, code, timestamp):
        return dict(submission_id=ident, source=code, source_sha256=source_hash(code.encode()),
                    timestamp=timestamp, verdict='WA')
    observations, banks, labels = [], [], []
    for i, split in enumerate(('train', 'train', 'valid')):
        bid = 'b'+str(i)
        current = 'x = 0\n' + ('# valid\n' if split == 'valid' else '')
        candidates = ['x = 1\n', 'x = 2\n']
        banks.append(dict(bank_id=bid, problem_id='p', current_source=current,
            generator_config_sha256='a'*64, seeds=list(range(8)),
            attempts=[dict(index=j, seed=j, status='success', source=candidates[j%2], error=None)
                      for j in range(8)]))
        observations.append(dict(example_id='e'+str(i), user_id='u'+str(i), split=split,
            bank_id=bid, observation=dict(problem_id='p', current=source('c'+str(i),current,10),
                prior=[source('h'+str(i),candidates[0],1)]),
            donor_history=[source('d'+str(i),candidates[1],2)], donor_user_id='donor'))
        for j, code in enumerate([current]+candidates):
            labels.append(dict(bank_id=bid,candidate_id=source_hash(code.encode()),status='stable',
                               gain=.5 if j == 1 else 0.,loss=.5 if j == 2 else 0.,all_ac=j == 1))
    return observations, banks, labels


class PairwiseTests(unittest.TestCase):
    def data(self):
        return load_inputs(*fixture())

    def test_grid_frozen_and_train_valid_only(self):
        report = fit_report(*self.data())
        self.assertEqual(len(report['grid']), 18)
        self.assertFalse(report['confirmatory'])
        self.assertFalse(report['fresh_test_opened'])
        self.assertEqual(set(report['selected']), {'C','H','U'})
        self.assertTrue(all(cell['model']['training']['train_prefixes'] == 2 for cell in report['grid']))
        self.assertTrue(all(len(cell['validation_candidate_scores']) == 1 for cell in report['grid']))

    def test_fit_cannot_read_validation_labels(self):
        examples, banks, labels = self.data()
        train_only = {key:value for key,value in labels.items() if key[0] != 'b2'}
        for variant in ('compact','lexical'):
            first = train_model(examples,banks,labels,'H',variant,1.)
            second = train_model(examples,banks,train_only,'H',variant,1.)
            self.assertEqual(first,second)

    def test_validation_code_cannot_change_scaler_or_fit(self):
        examples,banks,labels = self.data()
        before = train_model(examples,banks,labels,'H','lexical',1.)
        after = train_model(examples[:2],banks,labels,'H','lexical',1.)
        self.assertEqual(before,after)

    def test_predict_never_fits_and_json_roundtrip(self):
        examples,banks,labels = self.data()
        model = json.loads(json.dumps(train_model(examples,banks,labels,'H','lexical',1.)))
        ex = examples[-1]
        with patch.object(LogisticRegression,'fit',side_effect=AssertionError('fit called')), \
             patch.object(StandardScaler,'fit',side_effect=AssertionError('scale fit called')):
            candidate = select_model(model,ex.observation,ex.observation.prior,banks[ex.bank_id])
        self.assertIn(candidate,{c.candidate_id for c in banks[ex.bank_id].candidates})

    def test_lexical_distinguishes_compact_collision(self):
        examples,banks,labels = self.data()
        ex = examples[0]
        left,right = b'x = 1\n',b'x = 2\n'
        self.assertEqual(features(ex.observation,left,history=()),features(ex.observation,right,history=()))
        self.assertNotEqual(lexical_features(ex.observation.current.source,left),
                            lexical_features(ex.observation.current.source,right))
        model = train_model(examples,banks,labels,'C','lexical',1.)
        scores = score_model(model,ex.observation,(),banks[ex.bank_id])
        self.assertGreater(scores[source_hash(left)],scores[source_hash(right)])

    def test_additive_history_count_cancels_ranking(self):
        examples,banks,labels = self.data()
        model = train_model(examples,banks,labels,'H','compact',1.)
        index = model['numeric_names'].index('history_count')
        self.assertEqual(model['coefficients'][index],0.)
        ex = examples[0]
        before = score_model(model,ex.observation,ex.observation.prior,banks[ex.bank_id])
        model['coefficients'][index] = 31.
        after = score_model(model,ex.observation,ex.observation.prior,banks[ex.bank_id])
        offsets = [after[k]-before[k] for k in before]
        np.testing.assert_allclose(offsets,[offsets[0]]*len(offsets))

    def test_mirrored_pairs_and_equal_user_weights(self):
        examples,banks,labels = self.data()
        # u0's prefixes have two unequal pairs, u1's prefix has three.
        labels['b0',source_hash(b'x = 2\n')]['loss'] = 0.
        extra = copy.copy(examples[0]); extra.example_id = 'extra'
        examples.append(extra)
        x,y,w,scale,meta = training_data(examples,banks,labels,'H','lexical')
        np.testing.assert_allclose(x[0::2].toarray(),-x[1::2].toarray())
        np.testing.assert_array_equal(y[0::2],1-y[1::2])
        totals = {user:0. for user in ('u0','u1')}
        users = {ex.example_id:ex.user_id for ex in examples}
        for ident,weight in zip(meta['pair_example_ids'],w): totals[users[ident]] += weight
        self.assertAlmostEqual(totals['u0'],totals['u1'])
        self.assertAlmostEqual(float(w.mean()),1.)
        self.assertEqual(meta['ordered_pairs'],14)

    def test_unknown_excluded_and_pairless_disclosed(self):
        examples,banks,labels = self.data()
        for key,label in labels.items():
            if key[0] == 'b0': label.update(status='unknown',gain=None,loss=None,all_ac=None)
        model = train_model(examples,banks,labels,'H','compact',1.)
        self.assertEqual(model['training']['uninformative_train_prefixes'],1)
        self.assertEqual(model['training']['users_without_informative_prefix'],1)
        self.assertEqual(model['training']['informative_train_example_ids'],['e1'])
        for key,label in labels.items():
            if key[0] == 'b1': label.update(status='unknown',gain=None,loss=None,all_ac=None)
        with self.assertRaisesRegex(ValueError,'no unequal stable'):
            train_model(examples,banks,labels,'H','compact',1.)

    def test_target_order_and_noop_is_candidate(self):
        def label(ac,gain,loss): return dict(status='stable',all_ac=ac,gain=gain,loss=loss)
        self.assertGreater(preference(label(True,.1,0)),preference(label(False,.8,0)))
        self.assertGreater(preference(label(False,0,0)),preference(label(False,.8,.1)))
        examples,banks,labels = self.data()
        model = train_model(examples,banks,labels,'C','compact',1.)
        # Explicit fixture sets all learned scores equal: exact-source SHA tie.
        model['coefficients'] = [0.]*len(model['coefficients'])
        ex=examples[0]; bank=banks[ex.bank_id]
        self.assertEqual(select_model(model,ex.observation,(),bank),min(c.candidate_id for c in bank.candidates))
        self.assertIn(source_hash(bank.current_source),score_model(model,ex.observation,(),bank))

    def test_no_history_or_model_schema_bypass(self):
        examples,banks,labels = self.data(); ex=examples[0]; bank=banks[ex.bank_id]
        model=train_model(examples,banks,labels,'C','compact',1.)
        with self.assertRaisesRegex(ValueError,'empty history'):
            select_model(model,ex.observation,ex.observation.prior,bank)
        model['labels']={}
        with self.assertRaisesRegex(ValueError,'serialized'):
            select_model(model,ex.observation,(),bank)
        model=train_model(examples,banks,labels,'H','compact',1.)
        with self.assertRaisesRegex(ValueError,'authentic'):
            select_model(model,ex.observation,ex.donor_history,bank)

    def test_bad_labels_and_model_numeric_values_rejected(self):
        with self.assertRaises(ValueError):
            preference(dict(status='unknown',gain=0,loss=None,all_ac=None))
        with self.assertRaises(ValueError):
            preference(dict(status='stable',gain=float('nan'),loss=0,all_ac=False))
        with self.assertRaises(ValueError):
            preference(dict(status='stable',gain=.5,loss=.5,all_ac=True))
        examples,banks,labels=self.data(); ex=examples[0]
        model=train_model(examples,banks,labels,'C','compact',1.)
        model['numeric_scale'][0]=0
        with self.assertRaises(ValueError):select_model(model,ex.observation,(),banks[ex.bank_id])

    def test_unknown_validation_and_negative_results_preserved(self):
        examples,banks,labels=self.data()
        for key,label in labels.items():
            if key[0]=='b2':label.update(status='unknown',gain=None,loss=None,all_ac=None)
        report=fit_report(examples,banks,labels)
        for cell in report['grid']:
            self.assertEqual(cell['metrics']['utility'],-1.)
            self.assertEqual(cell['metrics']['rr_lower_bound'],0.)
            self.assertEqual(cell['metrics']['regression_rate_upper_bound'],1.)

    def test_selection_rule_exact(self):
        cell=dict(metrics=dict(rr_lower_bound=.5,regression_rate_upper_bound=.2,utility=.1),variant='lexical',C=1.)
        better=copy.deepcopy(cell);better['variant']='compact'
        self.assertGreater(selection_key(better),selection_key(cell))
        better=copy.deepcopy(cell);better['C']=.1
        self.assertGreater(selection_key(better),selection_key(cell))
        better=copy.deepcopy(cell);better['metrics']['regression_rate_upper_bound']=.1
        self.assertGreater(selection_key(better),selection_key(cell))
        better=copy.deepcopy(cell);better['metrics']['rr_lower_bound']=.6;better['metrics']['utility']=-1
        self.assertGreater(selection_key(better),selection_key(cell))


if __name__ == '__main__':
    unittest.main()
