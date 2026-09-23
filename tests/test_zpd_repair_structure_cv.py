"""Synthetic pipeline tests, not repair performance measurements."""
import contextlib
import copy
from dataclasses import replace
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_repair_structure_cv as runner
from scripts import zpd_repair_structure as learner
from scripts.zpd_repair_fit import load_inputs
from scripts.zpd_repair_replication import read, sha
from src.repair.pilot_contracts import source_hash
from tests.test_zpd_repair_pairwise import fixture


def training_fixture():
    old_examples,old_banks,old_labels = load_inputs(*fixture())
    original = old_examples[0]
    examples,banks,labels = [],{},{}
    for i in range(10):
        bid = 'bank'+str(i)
        obs = replace(original.observation,problem_id='p'+str(i//2))
        examples.append(replace(original,example_id='e'+str(i),user_id='u'+str(i),bank_id=bid,observation=obs))
        banks[bid] = replace(old_banks[original.bank_id],problem_id=obs.problem_id)
        for (old_bid,cid),value in old_labels.items():
            if old_bid==original.bank_id:
                labels[bid,cid] = dict(value,bank_id=bid)
    return examples,banks,labels


class StructureCVTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.output = self.base/'run'
        self.data = training_fixture()

    def run_cv(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return runner.run_cv(*self.data,self.output,**kwargs)

    def test_folds_group_problem_and_do_not_depend_on_input_order(self):
        examples,_,_ = self.data
        first = runner.assign_folds(examples)
        second = runner.assign_folds(list(reversed(examples)))
        self.assertEqual(first,second)
        self.assertEqual(first['fold_sizes'],[2]*5)
        for ex in examples:
            self.assertEqual(first['example_fold'][ex.example_id],first['problem_fold'][ex.observation.problem_id])

    def test_rejects_valid_duplicate_users_or_insufficient_problem_support(self):
        examples,_,_ = self.data
        for values in ([replace(examples[0],split='valid')]+examples[1:],
                       [replace(examples[0],user_id=examples[1].user_id)]+examples[1:],examples[:6]):
            with self.assertRaises(ValueError):
                runner.assign_folds(values)

    def test_all30_fits_hold_out_complete_problem_and_seal_before_outcome_join(self):
        examples,banks,labels = self.data
        assignment = runner.assign_folds(examples)
        real_fit = learner.train_model
        calls = []
        def checked_fit(train,passed_banks,passed_labels,condition,variant,reference_pair_weight):
            self.assertTrue((self.output/'FOLDS_COMPLETE.json').exists())
            fold = len(calls)//6
            allowed = {ex.bank_id for ex in train}
            self.assertEqual(set(passed_banks),allowed)
            self.assertEqual({k[0] for k in passed_labels},allowed)
            self.assertEqual(len(train),8)
            self.assertTrue(all(ex.split=='train' for ex in train))
            self.assertTrue(all(assignment['example_fold'][ex.example_id]!=fold for ex in train))
            self.assertEqual(reference_pair_weight,1900)
            calls.append((variant,condition))
            return real_fit(train,passed_banks,passed_labels,condition,variant,reference_pair_weight)
        real_summary = runner.summarize
        def checked_summary(predictions,passed_labels):
            self.assertEqual(len(calls),30)
            self.assertTrue((self.output/'PREDICTIONS_COMPLETE.json').exists())
            return real_summary(predictions,passed_labels)
        with patch.object(learner,'train_model',checked_fit),patch.object(runner,'summarize',checked_summary):
            report = self.run_cv()
        self.assertEqual(calls,list(runner.CELLS)*5)
        self.assertFalse(report['decision']['full_train_refits_authorized'])
        self.assertEqual(len(report['results']),8)
        self.assertEqual(report['results']['structural_C']['examples'],10)
        self.assertFalse((self.output/'full-train').exists())
        complete = read(self.output/'COMPLETE.json')
        self.assertEqual(complete['completed_recipients'],10)
        self.assertEqual(complete['completed_fits'],30)
        for filename,digest in complete['files_sha256'].items():
            self.assertEqual(sha(self.output/filename),digest)
        self.assertEqual(read(self.output/'STATUS.json')['phase'],'complete')

    def test_pass_conditionally_runs_exactly_six_additional_full_train_fits(self):
        real_fit = learner.train_model
        sizes = []
        def fit(*args,**kwargs):
            sizes.append(len(args[0]))
            return real_fit(*args,**kwargs)
        forced = dict(full_train_refits_authorized=True,eligible_for_separately_frozen_development_replay=True)
        with patch.object(learner,'train_model',fit),patch.object(runner,'resource_gate',return_value=forced):
            self.run_cv()
        self.assertEqual(sizes,[8]*30+[10]*6)
        self.assertEqual(len(read(self.output/'full-train/COMPLETE.json')['model_files_sha256']),6)
        self.assertEqual(read(self.output/'COMPLETE.json')['completed_fits'],36)

    def test_fit_failure_retains_progress_but_never_marks_complete(self):
        with patch.object(learner,'train_model',side_effect=ValueError('synthetic fit failure')):
            with self.assertRaisesRegex(ValueError,'synthetic fit failure'):
                self.run_cv()
        state = read(self.output/'STATUS.json')
        self.assertEqual(state['phase'],'failed')
        self.assertEqual(state['completed_recipients'],0)
        self.assertTrue((self.output/'folds.json').exists())
        self.assertFalse((self.output/'COMPLETE.json').exists())
        with self.assertRaisesRegex(ValueError,'new output'):
            self.run_cv()

    def test_input_drift_fails_closed_after_preserving_predictions(self):
        binding = self.base/'input'
        binding.write_text('before')
        digest = sha(binding)
        real_summary = runner.summarize
        def mutate(*args):
            binding.write_text('after')
            return real_summary(*args)
        with patch.object(runner,'summarize',mutate):
            with self.assertRaisesRegex(ValueError,'input changed'):
                self.run_cv(provenance=dict(input_sha256={str(binding):digest}))
        self.assertTrue((self.output/'PREDICTIONS_COMPLETE.json').exists())
        self.assertEqual(read(self.output/'STATUS.json')['phase'],'failed')
        self.assertFalse((self.output/'COMPLETE.json').exists())

    def test_terminal_log_failure_cannot_leave_a_complete_seal(self):
        real_event = runner._event
        def fail_terminal(*args,**kwargs):
            if kwargs.get('phase')=='complete':
                raise OSError('synthetic terminal write failure')
            return real_event(*args,**kwargs)
        with patch.object(runner,'_event',fail_terminal):
            with self.assertRaisesRegex(OSError,'terminal write'):
                self.run_cv()
        self.assertEqual(read(self.output/'STATUS.json')['phase'],'failed')
        self.assertFalse((self.output/'COMPLETE.json').exists())
        self.assertTrue((self.output/'PREDICTIONS_COMPLETE.json').exists())

    def test_extra_labels_not_allowed(self):
        examples,banks,labels = self.data
        labels['unseen',source_hash(b'x')] = next(iter(labels.values()))
        with self.assertRaisesRegex(ValueError,'exact train-only'):
            self.run_cv()

    def test_parent_data_and_training_ids_bound_across_host_prefixes(self):
        parent = dict(input_sha256={'/server/project/outputs/family/observations.jsonl':'a'*64},
            expected_evaluation_files_sha256={'original':{'labels.jsonl':'b'*64}},
            train_ids={'train64':['e0'],'train320':['e0','e1']})
        files = {'/local/project/outputs/family/observations.jsonl':'a'*64}
        evaluations = {'original':{'labels.jsonl':'b'*64}}
        runner.verify_parent_bindings(parent,files,evaluations,['e0'],['e0','e1'])
        for changed_files,changed_evaluations,changed_ids in (
                ({next(iter(files)):'c'*64},evaluations,['e0','e1']),
                (files,{'original':{'labels.jsonl':'c'*64}},['e0','e1']),
                (files,evaluations,['e1','e0'])):
            with self.assertRaisesRegex(ValueError,'frozen parent'):
                runner.verify_parent_bindings(parent,changed_files,changed_evaluations,['e0'],changed_ids)
        parent['input_sha256']['/elsewhere/outputs/family/observations.jsonl']='a'*64
        with self.assertRaisesRegex(ValueError,'duplicate normalized'):
            runner.verify_parent_bindings(parent,files,evaluations,['e0'],['e0','e1'])

    def test_preflight_failure_is_recorded_without_touching_existing_run(self):
        output = self.base/'outputs/zpd-repair-structure-cv-20260923/run-v1'
        args = ['--project',str(self.base),'--output',str(output)]
        with contextlib.redirect_stdout(io.StringIO()),patch.object(runner.subprocess,'check_output',return_value='dirty'):
            with self.assertRaisesRegex(ValueError,'clean source'):
                runner.main(args)
        self.assertEqual(read(output/'STATUS.json')['phase'],'preflight_failed')
        digest=sha(output/'STATUS.json')
        with self.assertRaisesRegex(ValueError,'new output'):
            runner.main(args)
        self.assertEqual(sha(output/'STATUS.json'),digest)

    def test_unknown_counts_and_failure_classes_are_preserved(self):
        examples,banks,labels = self.data
        predictions = []
        for i,ex in enumerate(examples):
            noop = source_hash(banks[ex.bank_id].current_source)
            bad,good = source_hash(b'x = 2\n'),source_hash(b'x = 1\n')
            choices = dict(noop=noop,first_attempt=good,lexical_C=good,structural_C=bad)
            predictions.append(dict(example_id=ex.example_id,user_id=ex.user_id,bank_id=ex.bank_id,
                problem_id=ex.observation.problem_id,fold=i//2,choices=choices,
                candidate_edit_tokens={noop:0,bad:1,good:1}))
        labels['bank0',bad].update(status='unknown',gain=None,loss=None,all_ac=None)
        report = runner.summarize(predictions,labels)
        primary = report['results']['structural_C']
        self.assertEqual(primary['counts']['unknown'],1)
        self.assertEqual(primary['counts']['regression_rate_lower_bound'],9)
        self.assertEqual(primary['counts']['regression_rate_upper_bound'],10)
        self.assertEqual(report['failure_cases'][0]['classification'],'unknown_selected')
        self.assertEqual(report['failure_cases'][1]['classification'],'ranking_miss_with_ac_in_bank')
        self.assertEqual(report['oracle_availability']['banks_with_stable_ac'],10)
        self.assertEqual(report['oracle_availability']['primary_unknown_with_stable_ac'],1)
        self.assertFalse(runner.resource_gate(report)['full_train_refits_authorized'])

    def test_gate_cannot_promote_secondary_arm_or_accept_added_regression(self):
        metric = dict(rr_lower_bound=.5,regression_rate_lower_bound=.1,regression_rate_upper_bound=.2)
        values = {name:dict(metrics=dict(metric)) for name in ('structural_C','lexical_C','first_attempt','structural_H')}
        report = dict(results=copy.deepcopy(values),equal_problem_metrics={k:dict(v['metrics']) for k,v in values.items()},
            fold_results={str(i):copy.deepcopy(values) for i in range(5)})
        report['results']['structural_H']['metrics']['rr_lower_bound']=1.
        self.assertFalse(runner.resource_gate(report)['full_train_refits_authorized'])
        report['results']['structural_C']['metrics']['rr_lower_bound']=.6
        report['equal_problem_metrics']['structural_C']['rr_lower_bound']=.6
        self.assertTrue(runner.resource_gate(report)['full_train_refits_authorized'])
        report['results']['structural_C']['metrics']['regression_rate_lower_bound']=.11
        self.assertFalse(runner.resource_gate(report)['full_train_refits_authorized'])
        report['results']['structural_C']['metrics']['regression_rate_lower_bound']=.1
        for i in (0,1):
            report['fold_results'][str(i)]['structural_C']['metrics']['rr_lower_bound']=.4
        self.assertFalse(runner.resource_gate(report)['full_train_refits_authorized'])


if __name__=='__main__':
    unittest.main()
