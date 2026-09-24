"""Synthetic fixed-loss and CV integrity checks; no real outcomes are opened."""
import contextlib
import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts import zpd_repair_preservation as learner
from scripts import run_zpd_repair_preservation_cv as runner
from scripts import run_zpd_repair_structure_cv as previous
from scripts import zpd_repair_structure as structure
from scripts.zpd_repair_fit import load_inputs
from scripts.zpd_repair_replication import read, sha
from src.repair.pilot_contracts import canonical_hash, source_hash
from tests.test_zpd_repair_pairwise import fixture as original_fixture


def fixture():
    originals,old_banks,old_labels = load_inputs(*original_fixture())
    original = originals[0]; old = old_banks[original.bank_id]
    examples = [];banks = {};labels = {}
    for i in range(30):
        bid = 'bank'+str(i); observation = replace(original.observation,problem_id='p'+str(i//6))
        examples.append(replace(original,example_id='e'+str(i),user_id='u'+str(i),bank_id=bid,observation=observation))
        bank = replace(old,problem_id=observation.problem_id);banks[bid] = bank
        for c in bank.candidates:
            value = dict(old_labels[original.bank_id,c.candidate_id],bank_id=bid)
            kind = i%6
            if kind in (0,1):
                ac = kind == 1 or c.source != b'x = 2\n'
                value.update(status='stable',all_ac=ac,gain=0.,loss=0. if ac else .5)
            elif kind == 4 and c.is_noop or kind == 5:
                value.update(status='unknown',all_ac=None,gain=None,loss=None)
            labels[bid,c.candidate_id] = value
    return examples,banks,labels


def make_references(examples,banks,labels):
    folds = previous.assign_folds(examples);result = {}
    for fold in range(5):
        train = [e for e in examples if folds['example_fold'][e.example_id] != fold]
        held = [e for e in examples if folds['example_fold'][e.example_id] == fold]
        ids = {e.bank_id for e in train};bs = {k:v for k,v in banks.items() if k in ids};ls = {k:v for k,v in labels.items() if k[0] in ids}
        models = {name:structure.train_model(train,bs,ls,'C',name.split('_')[0]) for name in runner.LEARNED_CONTROLS}
        result[str(fold)] = dict(models=models,train_example_ids=[e.example_id for e in train],held_example_ids=[e.example_id for e in held],
            predictions=[previous.prediction(e,banks[e.bank_id],models,fold) for e in held])
    return result


class PreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = fixture();cls.references = make_references(*cls.data)

    def setUp(self):
        temp = tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve();self.output = self.base/'run'
        self.examples,self.banks,self.labels = copy.deepcopy(self.data)
        ref = self.references['0'];ids = set(ref['train_example_ids'])
        self.train = [e for e in self.examples if e.example_id in ids]
        bids = {e.bank_id for e in self.train}
        self.train_banks = {k:v for k,v in self.banks.items() if k in bids}
        self.train_labels = {k:v for k,v in self.labels.items() if k[0] in bids}
        self.reference = ref['models']['structural_C']

    def training(self,cell):
        return learner.training_data(self.train,self.train_banks,self.train_labels,self.reference,cell)

    def model(self,cell='refined_balanced'):
        return learner.train_model(self.train,self.train_banks,self.train_labels,self.reference,cell)

    def run_cv(self,**kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.run_cv(self.examples,self.banks,self.labels,self.references,self.output,**kwargs)

    def test_refinement_preserves_strict_qualities_and_unknowns(self):
        ac = dict(status='stable',all_ac=True,gain=0.,loss=0.)
        bad = dict(status='stable',all_ac=False,gain=0.,loss=.5)
        unknown = dict(status='unknown',all_ac=None,gain=None,loss=None)
        def key(lab,s='known_ac',noop=False):
            return learner.refined_preference(lab,current_stratum=s,is_noop=noop,relation='refined')
        self.assertGreater(key(ac,noop=True),key(ac))
        self.assertGreater(key(ac),key(bad,noop=True))
        self.assertEqual(key(ac,s='known_nonac',noop=True),key(ac,s='known_nonac'))
        self.assertEqual(key(ac,s='unknown',noop=True),key(ac,s='unknown'))
        self.assertIsNone(key(unknown,noop=True))

    def test_all_ac_ties_create_pairs_and_preserve_every_prefix(self):
        old = self.training('legacy_natural')[-1];new = self.training('refined_natural')[-1]
        a = next(e for e in self.train if int(e.example_id[1:])%6 == 1)
        old_row = next(r for r in old['prefixes'] if r['example_id'] == a.example_id)
        new_row = next(r for r in new['prefixes'] if r['example_id'] == a.example_id)
        self.assertEqual(old_row['pairs'],[])
        self.assertEqual(len(new_row['pairs']),len(new_row['stable_candidate_ids'])-1)
        noop = source_hash(self.banks[a.bank_id].current_source)
        self.assertTrue(all((left if target else right) == noop for left,right,target in new_row['pairs']))
        self.assertEqual(len(new['prefixes']),len(self.train))
        self.assertTrue(set(old['informative_train_example_ids']) <= set(new['informative_train_example_ids']))

    def test_balancing_retains_unknown_pairs_and_natural_unknown_mass(self):
        for relation in ('legacy','refined'):
            _,_,_,_,natural = self.training(relation+'_natural')
            x,y,w,_,balanced = self.training(relation+'_balanced')
            self.assertAlmostEqual(w.sum(),1900.)
            self.assertGreater(balanced['stratum_mass']['unknown'],0)
            self.assertAlmostEqual(balanced['stratum_mass']['unknown'],natural['stratum_mass']['unknown'])
            self.assertAlmostEqual(balanced['stratum_mass']['known_ac'],balanced['stratum_mass']['known_nonac'])
            unknown = [r for r in balanced['prefixes'] if r['stratum'] == 'unknown' and r['pairs']]
            self.assertTrue(unknown)
            self.assertTrue(all(r['row_weight'] > 0 for r in unknown))
            np.testing.assert_array_equal(y[0::2],1-y[1::2])
            np.testing.assert_array_equal(x[0::2].toarray(),-x[1::2].toarray())
        self.assertNotEqual(self.training('legacy_balanced')[-1]['natural_stratum_mass']['unknown'],
                            self.training('refined_balanced')[-1]['natural_stratum_mass']['unknown'])

    def test_new_all_ac_tie_loss_gradient_pushes_noop_without_coefficient_override(self):
        x,y,weights,_,meta = self.training('refined_balanced')
        pure = {e.example_id for e in self.train if int(e.example_id[1:])%6 == 1}
        chosen = np.array([i for i,ident in enumerate(meta['pair_example_ids']) if ident in pure])
        noop_column = learner.numeric_names('C').index('candidate_is_noop')
        gradient_at_zero = float(x[chosen,noop_column].toarray().ravel() @ (weights[chosen]*(.5-y[chosen])))
        self.assertLess(gradient_at_zero,0.)

    def test_exact_shared_scale_and_legacy_no_fit_reuse(self):
        with patch.object(StandardScaler,'fit',side_effect=AssertionError('new scaler fit')):
            for cell in learner.CELLS:
                self.assertEqual(self.training(cell)[3].tolist(),self.reference['numeric_scale'])
        with patch.object(LogisticRegression,'fit',side_effect=AssertionError('legacy refitted')):
            model = self.model('legacy_natural')
        self.assertEqual(model['coefficients'],self.reference['coefficients'])
        ex = self.examples[0]
        self.assertEqual(learner.score_model(model,ex.observation,self.banks[ex.bank_id]),
                         structure.score_model(self.reference,ex.observation,(),self.banks[ex.bank_id]))

    def test_zero_known_support_fails_without_unknown_redistribution(self):
        for ex in self.train:
            noop = source_hash(self.train_banks[ex.bank_id].current_source)
            if self.train_labels[ex.bank_id,noop]['status'] == 'stable':
                self.train_labels[ex.bank_id,noop].update(all_ac=False,gain=0.,loss=0.)
        with self.assertRaisesRegex(ValueError,'both known strata'):
            self.training('refined_balanced')

    def test_train_whitelist_and_reference_membership_fail_closed(self):
        extra = copy.deepcopy(next(iter(self.train_labels.values())))
        self.train_labels['held','future'] = extra
        with self.assertRaisesRegex(ValueError,'whitelist'):
            self.training('refined_balanced')
        del self.train_labels['held','future']
        bad = copy.deepcopy(self.reference)
        bad['training']['informative_train_example_ids'][0] = 'foreign'
        bad['model_sha256'] = canonical_hash({k:v for k,v in bad.items() if k != 'model_sha256'})
        with self.assertRaisesRegex(ValueError,'membership'):
            learner.training_data(self.train,self.train_banks,self.train_labels,bad,'refined_balanced')

    def test_prediction_labelblind_roundtrip_and_unknown_candidate_retained(self):
        model = self.model();ex = next(e for e in self.train if int(e.example_id[1:])%6 == 4)
        with patch.object(LogisticRegression,'fit',side_effect=AssertionError('prediction fit')):
            scores = learner.score_model(json.loads(json.dumps(model)),ex.observation,self.banks[ex.bank_id])
        self.assertEqual(set(scores),{c.candidate_id for c in self.banks[ex.bank_id].candidates})
        self.assertIn(source_hash(self.banks[ex.bank_id].current_source),scores)
        self.assertEqual(learner.select_model(model,ex.observation,self.banks[ex.bank_id]),min(scores,key=lambda cid:(-scores[cid],cid)))

    def test_resealed_configuration_and_mass_tampering_rejected(self):
        original = self.model()
        for key,value in [('C',1.),('numeric_scale',[0.,1.,1.]),('hash_dimension',2048),('legacy_model_reused',True)]:
            bad = copy.deepcopy(original);bad[key] = value
            bad['model_sha256'] = canonical_hash({k:v for k,v in bad.items() if k != 'model_sha256'})
            with self.subTest(key=key),self.assertRaises(ValueError):
                learner.validate_model(bad)
        bad = copy.deepcopy(original);bad['training']['stratum_mass']['unknown'] += 1
        bad['model_sha256'] = canonical_hash({k:v for k,v in bad.items() if k != 'model_sha256'})
        with self.assertRaises(ValueError):learner.validate_model(bad)

    def test_pipeline_exact_fifteen_fits_and_prediction_seal_before_summary(self):
        actual = runner.train_model;calls = []
        folds = previous.assign_folds(self.examples)
        def checked(train,banks,labels,reference,cell):
            fold = len(calls)//4
            self.assertTrue((self.output/'FOLDS_COMPLETE.json').is_file())
            self.assertTrue(all(folds['example_fold'][e.example_id] != fold for e in train))
            self.assertEqual(set(banks),{e.bank_id for e in train})
            self.assertEqual({k[0] for k in labels},set(banks))
            calls.append(cell)
            return actual(train,banks,labels,reference,cell)
        summary = runner.summarize
        def checked_summary(*args):
            self.assertEqual(calls,list(learner.CELLS)*5)
            self.assertTrue((self.output/'PREDICTIONS_COMPLETE.json').is_file())
            return summary(*args)
        with patch.object(runner,'train_model',checked),patch.object(runner,'summarize',checked_summary):
            result = self.run_cv()
        marker = read(self.output/'COMPLETE.json')
        self.assertEqual(marker['completed_fits'],15);self.assertEqual(marker['reused_models'],5)
        self.assertFalse(result['decision']['full_train_refits_authorized'])
        self.assertFalse((self.output/'full-train').exists())
        self.assertEqual(set(result['results']),set(runner.METHODS))
        for name,digest in marker['files_sha256'].items():self.assertEqual(sha(self.output/name),digest)

    def test_failures_preserve_partial_without_completion_or_implicit_resume(self):
        with patch.object(runner,'train_model',side_effect=ValueError('synthetic fit failure')):
            with self.assertRaisesRegex(ValueError,'synthetic fit failure'):self.run_cv()
        self.assertTrue((self.output/'FAILED.json').exists());self.assertFalse((self.output/'COMPLETE.json').exists())
        with self.assertRaises(FileExistsError):self.run_cv()

    def test_terminal_logging_failure_cannot_leave_false_complete(self):
        actual = runner.event
        def fail(path,**fields):
            if fields['phase'] == 'complete':raise OSError('terminal failure')
            return actual(path,**fields)
        with patch.object(runner,'event',fail):
            with self.assertRaisesRegex(OSError,'terminal failure'):self.run_cv()
        self.assertTrue((self.output/'FAILED.json').exists());self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_reference_chain_load_and_changed_model_rejected(self):
        parent = self.base/'outputs/zpd-repair-structure-cv-20260923/run-v1'
        with contextlib.redirect_stdout(io.StringIO()):previous.run_cv(self.examples,self.banks,self.labels,parent)
        refs,bindings,_ = runner.load_references(self.base,self.examples,{},production=False)
        self.assertEqual(len(refs),5);self.assertGreater(len(bindings),40)
        with (parent/'fold-0/structural_C.json').open('a') as stream:stream.write(' ')
        with self.assertRaisesRegex(ValueError,'sealed reference'):
            runner.load_references(self.base,self.examples,{},production=False)

    def test_alias_and_existing_cli_output_do_not_get_overwritten(self):
        alias = self.base/'alias';alias.symlink_to(self.base,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'symlink'):
            runner.main(['--project',str(alias),'--output',str(alias/runner.FAMILY/'run-v1')])
        output = self.base/runner.FAMILY/'run-v1';output.mkdir(parents=True)
        runner.write(output/'STATUS.json',{'user':'owned'});digest = sha(output/'STATUS.json')
        with self.assertRaisesRegex(ValueError,'new direct child'):
            runner.main(['--project',str(self.base),'--output',str(output)])
        self.assertEqual(sha(output/'STATUS.json'),digest)

    def test_gate_strict_old_structural_comparator_and_both_fold_stabilities(self):
        def cell(ac,reg=1,unknown=0):
            return dict(examples=10,counts=dict(rr_lower_bound=ac,rr_upper_bound=ac+unknown,
                regression_rate_lower_bound=reg,regression_rate_upper_bound=reg+unknown),metrics={})
        values = {m:cell(7 if m == runner.PRIMARY else 6) for m in runner.METHODS}
        report = dict(results=copy.deepcopy(values),problem_results={'p':copy.deepcopy(values)},
                      fold_results={str(f):copy.deepcopy(values) for f in range(5)})
        self.assertTrue(runner.resource_gate(report)['gate_passed'])
        self.assertFalse(runner.resource_gate(report)['full_train_refits_authorized'])
        report['results']['structural_C'] = cell(7)
        self.assertFalse(runner.resource_gate(report)['gate_passed'])
        report['results']['structural_C'] = cell(6)
        for f in ('0','1'):report['fold_results'][f]['structural_C'] = cell(8)
        self.assertFalse(runner.resource_gate(report)['gate_passed'])


if __name__ == '__main__':unittest.main()
