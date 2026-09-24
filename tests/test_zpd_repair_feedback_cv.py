"""Staged synthetic repair CV only; no corpus or empirical outcome is opened."""
import copy
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_repair_feedback_cv as runner
from scripts import run_zpd_repair_structure_cv as old
from scripts import zpd_repair_feedback_labels as provider
from scripts import zpd_repair_feedback_offset as offset
from scripts import zpd_repair_feedback_pairs as pairs
from scripts import zpd_repair_structure as structural
from scripts.zpd_repair_fit import load_inputs
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_repair_pairwise import fixture as raw_fixture


EMPTY_PROVENANCE = dict(source_sha256={}, input_sha256={})


def encoded(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False)+'\n').encode()


def fixture(n=10):
    originals, old_banks, old_labels = load_inputs(*raw_fixture()); original = originals[0]
    examples, banks, labels = [], {}, {}
    for i in range(n):
        bid = 'b'+str(i); obs = replace(original.observation, problem_id='p'+str(i%5))
        ex = replace(original, example_id='e'+str(i), user_id='u'+str(i), bank_id=bid, observation=obs)
        examples.append(ex); banks[bid] = replace(old_banks[original.bank_id], problem_id=obs.problem_id)
        for (prior_bid, cid), row in old_labels.items():
            if prior_bid == original.bank_id: labels[bid, cid] = dict(row, bank_id=bid)
    # Keep stable AC, nonAC and unknown originals/candidates represented.
    candidate_ids = [c.candidate_id for c in banks['b0'].candidates]
    labels['b0', candidate_ids[2]].update(status='unknown', gain=None, loss=None, all_ac=None)
    labels['b1', candidate_ids[0]].update(status='unknown', gain=None, loss=None, all_ac=None)
    for cid in candidate_ids[:2]: labels['b2', cid].update(gain=0., loss=0., all_ac=True)
    assignment = old.assign_folds(examples); parents = {}; interactions = {arm: {} for arm in runner.ARMS}
    for arm in runner.ARMS:
        for bid, bank in banks.items():
            ids = tuple(c.candidate_id for c in bank.candidates)
            interactions[arm][bid] = pairs.CandidateInteractions(ids, np.zeros((len(ids), 1296)),
                np.zeros((len(ids), 18)), np.ones((len(ids), 18), dtype=bool))
    for fold in range(5):
        train = [ex for ex in examples if assignment['example_fold'][ex.example_id] != fold]
        held = [ex for ex in examples if assignment['example_fold'][ex.example_id] == fold]
        ids = {ex.bank_id for ex in train}; bs = {bid: banks[bid] for bid in ids}
        labs = {key: row for key, row in labels.items() if key[0] in ids}
        models = {variant+'_C': structural.train_model(train, bs, labs, 'C', variant) for variant in ('structural', 'lexical')}
        old_models = {key: models[key.split('_')[0]+'_C'] for key in runner.OLD_METHODS}
        parent_predictions = tuple(old.prediction(ex, banks[ex.bank_id], old_models, fold) for ex in held)
        parents[fold] = runner.ParentFold(fold, tuple(ex.example_id for ex in train), tuple(ex.example_id for ex in held), models, parent_predictions)
    inputs = runner.PreparedInputs(tuple(examples), banks, assignment, interactions, parents,
        hashlib.sha256(encoded(assignment)).hexdigest(), synthetic=True)
    return inputs, labels


def materialized(inputs, labels, directory):
    directory.mkdir(); contracts = {}
    for fold in [*range(5), None]:
        subset = [ex for ex in inputs.examples if fold is None or inputs.assignment['example_fold'][ex.example_id] != fold]
        bids = {ex.bank_id for ex in subset}
        payload = dict(kind=provider.ASSESSMENT_KIND if fold is None else provider.FOLD_KIND, fold=fold,
            parent_complete_sha256=runner.PARENT_COMPLETE_SHA256, fold_assignment_sha256=inputs.fold_assignment_sha256,
            source_binding_sha256='a'*64, example_bank_ids={ex.example_id: ex.bank_id for ex in subset},
            bank_seals={bid: inputs.banks[bid].seal_sha256 for bid in bids},
            labels=[row for key, row in labels.items() if key[0] in bids])
        path = directory/('assessment/all320-labels.json' if fold is None else f'fold-{fold}/train-labels.json')
        path.parent.mkdir(); data = encoded(payload); path.write_bytes(data)
        contracts[fold] = runner.LabelContract(hashlib.sha256(data).hexdigest(), inputs.fold_assignment_sha256, 'a'*64)
    return contracts


class RepairFeedbackCVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, cls.labels = fixture()

    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.base = Path(directory.name).resolve(); self.run = self.base/'run'; self.label_root = self.base/'prepared'
        self.contracts = materialized(self.inputs, self.labels, self.label_root)

    def start(self, inputs=None, provenance=None):
        return runner.initialize(inputs or self.inputs, self.run, provenance=provenance or EMPTY_PROVENANCE,
                                 label_contracts=self.contracts)

    def test_fixed_source_only_validation_and_original_parent_zero_theta_parity(self):
        with patch('builtins.open', side_effect=AssertionError('file I/O forbidden')):
            cohort = runner.validate_inputs(self.inputs)
        self.assertEqual(len(cohort), 10)
        self.assertEqual({r['fold'] for r in cohort}, set(range(5)))
        self.assertEqual(runner.ARMS, ('H', 'Jm', 'HS', 'U', 'L'))
        with self.assertRaisesRegex(ValueError, 'train320'):
            runner.validate_inputs(replace(self.inputs, synthetic=False))
        for mutation in ('extra_bank', 'support_pin', 'parent_pin', 'folds', 'unknown_arm', 'event_masks'):
            inputs = copy.deepcopy(self.inputs)
            if mutation == 'extra_bank': inputs.banks['held'] = inputs.banks['b0']
            elif mutation == 'support_pin': inputs = replace(inputs, support_complete_sha256='c'*64)
            elif mutation == 'parent_pin': inputs = replace(inputs, parent_complete_sha256='c'*64)
            elif mutation == 'folds': inputs.assignment['example_fold']['e0'] = (inputs.assignment['example_fold']['e0']+1)%5
            elif mutation == 'unknown_arm': inputs.interactions['rescue'] = inputs.interactions['H']
            else: inputs.interactions['HS']['b0'].event_masks[0, 0] = False
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): runner.validate_inputs(inputs)

    def test_parent_model_held_membership_scaler_coefficients_and_scores_cannot_drift(self):
        for mutation in ('train_ids', 'pair_ids', 'scale', 'coefficient', 'condition', 'prediction', 'choices'):
            inputs = copy.deepcopy(self.inputs); parent = inputs.parent_folds[0]; model = parent.models['structural_C']
            if mutation == 'train_ids': inputs.parent_folds[0] = replace(parent, train_example_ids=parent.held_example_ids)
            elif mutation == 'pair_ids': model['training']['pair_example_ids'][0] = parent.held_example_ids[0]
            elif mutation == 'scale': model['numeric_scale'].pop()
            elif mutation == 'coefficient': model['coefficients'].pop()
            elif mutation == 'condition': model['condition'] = 'H'
            elif mutation == 'prediction':
                scores = parent.predictions[0]['candidate_scores']['structural_C']; scores[next(iter(scores))] += .001
            else: parent.predictions[0]['choices']['noop'] = 'other'
            model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): runner.validate_inputs(inputs)

    def test_single_worker_opens_only_own_fold_label_and_exact_training_scope(self):
        self.start(); read_bytes = Path.read_bytes; accessed = []; fit_calls = []
        def guarded(path):
            accessed.append(path)
            self.assertEqual(path, self.label_root/'fold-0/train-labels.json')
            return read_bytes(path)
        actual_build = pairs.build_pairs
        def checked(examples, banks, labels, interactions, base):
            fit_calls.append(1); required = {ex.bank_id for ex in examples}
            self.assertEqual(required, set(banks)); self.assertEqual(required, {key[0] for key in labels})
            self.assertTrue(all(self.inputs.assignment['example_fold'][ex.example_id] != 0 for ex in examples))
            self.assertTrue({ex.observation.problem_id for ex in examples}.isdisjoint(
                {ex.observation.problem_id for ex in self.inputs.examples if self.inputs.assignment['example_fold'][ex.example_id] == 0}))
            return actual_build(examples, banks, labels, interactions, base)
        with patch.object(Path, 'read_bytes', guarded), patch.object(pairs, 'build_pairs', checked):
            predicted = runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)
        self.assertEqual(len(accessed), 1); self.assertEqual(len(fit_calls), 5)
        self.assertEqual(len(predicted), 2); self.assertEqual(set(predicted[0]['choices']), set(runner.METHODS))
        self.assertEqual(set(predicted[0]['candidate_scores']), set(runner.METHODS))
        self.assertNotIn('labels', inspect.signature(runner.fit_fold).parameters)
        self.assertNotIn('labels', inspect.signature(runner.predict_fold).parameters)
        self.assertTrue((self.run/'fold-0/COMPLETE.json').exists())
        self.assertFalse((self.run/'PREDICTIONS_COMPLETE.json').exists())

    def test_fit_failure_records_partial_results_and_blocks_all_remaining_cells(self):
        self.start(); real_fit = offset.fit_offset; calls = []
        def fail_third(*args):
            calls.append(1)
            if len(calls) == 3: raise offset.OffsetOptimizationError('synthetic convergence failure', {'gradient': .1})
            return real_fit(*args)
        with patch.object(offset, 'fit_offset', fail_third), self.assertRaisesRegex(RuntimeError, 'convergence'):
            runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)
        self.assertEqual(len(calls), 3)
        self.assertTrue((self.run/'fold-0/H.json').exists()); self.assertTrue((self.run/'fold-0/Jm.json').exists())
        self.assertFalse((self.run/'fold-0/HS.json').exists()); self.assertFalse((self.run/'fold-0/COMPLETE.json').exists())
        self.assertEqual(runner._read(self.run/'FAILED.json')['completed_fits_in_failed_fold'], 2)
        for operation in (lambda: runner.fit_fold(self.inputs, 1, self.label_root, self.contracts[1], self.run),
                          lambda: runner.finalize_predictions(self.inputs, self.run),
                          lambda: runner.assess_predictions(self.inputs, self.run, self.label_root, self.contracts[None])):
            with self.assertRaisesRegex(ValueError, 'cannot resume'): operation()

    def test_terminal_status_write_failure_cannot_leave_complete_marker(self):
        self.start(); actual = runner._status
        def fail_complete(directory, **value):
            if value.get('phase') == 'complete': raise OSError('synthetic terminal write failure')
            return actual(directory, **value)
        with patch.object(runner, '_status', fail_complete), self.assertRaisesRegex(OSError, 'terminal write'):
            runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)
        self.assertTrue((self.run/'fold-0/MODELS_COMPLETE.json').exists())
        self.assertTrue((self.run/'fold-0/predictions.json').exists())
        self.assertFalse((self.run/'fold-0/COMPLETE.json').exists())
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_partial_complete_marker_write_is_never_authoritative(self):
        directory = self.base/'seal'; directory.mkdir(); (directory/'artifact.json').write_text('{}')
        actual = runner._write
        def partial(path, value):
            if path.name == 'COMPLETE.json.partial':
                path.write_text('{"status":'); raise OSError('synthetic partial seal write')
            return actual(path, value)
        with patch.object(runner, '_write', partial), self.assertRaisesRegex(OSError, 'partial seal'):
            runner._seal(directory, ['artifact.json'])
        self.assertTrue((directory/'COMPLETE.json.partial').exists())
        self.assertFalse((directory/'COMPLETE.json').exists())

    def test_in_memory_array_shape_and_dtype_are_bound(self):
        original = runner.input_fingerprint(self.inputs)
        for field in ('shape', 'dtype'):
            changed = copy.deepcopy(self.inputs); block = changed.interactions['H']['b0']
            matrix = block.matrix.reshape(1, -1) if field == 'shape' else block.matrix.view(np.int64)
            changed.interactions['H']['b0'] = replace(block, matrix=matrix)
            self.assertNotEqual(runner.input_fingerprint(changed), original)

    def test_worker_runtime_drift_prevents_completion_without_retry(self):
        self.start(); runtime = runner._runtime(); actual_predict = runner.predict_fold
        def changed(*args):
            result = actual_predict(*args); runtime['scipy'] = 'synthetic-drift'; return result
        with patch.object(runner, '_runtime', lambda: dict(runtime)), patch.object(runner, 'predict_fold', changed):
            with self.assertRaisesRegex(ValueError, 'runtime changed'):
                runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)
        self.assertFalse((self.run/'fold-0/COMPLETE.json').exists())
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_assessment_and_fold_contracts_must_match_trusted_initialization(self):
        self.start()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('wrong-contract label read forbidden')):
            with self.assertRaisesRegex(ValueError, 'trusted initialization'):
                runner.assess_predictions(self.inputs, self.run, self.label_root,
                    replace(self.contracts[None], expected_source_binding_sha256='c'*64))
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_cross_source_preparation_contracts_cannot_initialize(self):
        self.contracts[0] = replace(self.contracts[0], expected_source_binding_sha256='c'*64)
        with self.assertRaisesRegex(ValueError, 'one frozen source'): self.start()
        self.assertTrue((self.run/'FAILED.json').exists())
        self.assertFalse((self.run/'FOLDS_COMPLETE.json').exists())

    def test_drift_during_final_assessment_replay_prevents_terminal_seal(self):
        self.start(); (self.run/'PREDICTIONS_COMPLETE.json').write_text('{}\n')
        predictions = []
        for row in runner._cohort(self.inputs):
            predictions.append(dict({key: row[key] for key in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')},
                choices={method: row['noop_candidate_id'] for method in runner.METHODS},
                shared_theta_diagnostics={arm: dict(features_identical_exact=True, choice_changed=False,
                    transition='same', score_difference={}) for arm in ('HS', 'Jm')}))
        runtime = runner._runtime(); calls = []
        def replay(*args):
            calls.append(1)
            if len(calls) == 2: runtime['scipy'] = 'synthetic-final-replay-drift'
            return predictions
        # Numerical all25 replay is independently covered by the320 end-to-end
        # test. Here isolate the last-consumption/barrier ordering failure.
        with patch.object(runner, '_prediction_barrier', replay), \
                patch.object(runner, '_runtime', lambda: dict(runtime)), \
                patch.object(provider, 'validate_assessment_envelope', return_value=self.labels):
            with self.assertRaisesRegex(ValueError, 'runtime changed'):
                runner.assess_predictions(self.inputs, self.run, self.label_root, self.contracts[None])
        self.assertEqual(len(calls), 2)
        self.assertFalse((self.run/'assessment/COMPLETE.json').exists())
        self.assertFalse((self.run/'COMPLETE.json').exists())
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_extra_held_labels_rejected_before_any_optimizer_call(self):
        self.start(); path = self.label_root/'fold-0/train-labels.json'; payload = runner._read(path)
        held = next(ex for ex in self.inputs.examples if self.inputs.assignment['example_fold'][ex.example_id] == 0)
        payload['labels'].append(next(row for key, row in self.labels.items() if key[0] == held.bank_id))
        path.write_bytes(encoded(payload)); contract = replace(self.contracts[0], expected_sha256=runner._sha(path))
        with patch.object(offset, 'fit_offset', side_effect=AssertionError('optimizer must not run')), self.assertRaisesRegex(ValueError, 'trusted initialization'):
            runner.fit_fold(self.inputs, 0, self.label_root, contract, self.run)
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_missing_prediction_barrier_never_opens_assessment_labels(self):
        self.start()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('assessment read forbidden')):
            with self.assertRaises(FileNotFoundError):
                runner.assess_predictions(self.inputs, self.run, self.label_root, self.contracts[None])
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_own_label_drift_and_source_drift_prevent_terminal_fold_seal(self):
        for which in ('label', 'source'):
            base = self.base/which; base.mkdir(); run = base/'run'; labels = base/'prepared'
            contracts = materialized(self.inputs, self.labels, labels)
            source = base/'source.py'; source.write_text('before\n')
            provenance = dict(source_sha256={str(source): runner._sha(source)}, input_sha256={})
            runner.initialize(self.inputs, run, provenance=provenance, label_contracts=contracts)
            actual = runner.predict_fold
            def mutate(*args):
                result = actual(*args)
                (labels/'fold-0/train-labels.json' if which == 'label' else source).write_text('changed\n')
                return result
            with patch.object(runner, 'predict_fold', mutate), self.assertRaisesRegex(ValueError, 'changed'):
                runner.fit_fold(self.inputs, 0, labels, contracts[0], run)
            self.assertTrue((run/'fold-0/predictions.json').exists())
            self.assertFalse((run/'fold-0/COMPLETE.json').exists()); self.assertTrue((run/'FAILED.json').exists())

    def test_new_paths_only_and_cli_unreleased_before_io(self):
        self.start()
        with self.assertRaisesRegex(ValueError, 'new run'): self.start()
        link = self.base/'alias'; link.symlink_to(self.run, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'nonsymlink'):
            runner.initialize(self.inputs, link, provenance=EMPTY_PROVENANCE, label_contracts=self.contracts)
        with patch('builtins.open', side_effect=AssertionError('I/O forbidden')):
            with self.assertRaisesRegex(RuntimeError, 'NOT released'): runner.main(['--project', 'forbidden'])

    def test_preparation_passes_raw_bytes_only_to_public_verification_boundary(self):
        raw = {'synthetic': b'not-real-source'}
        with patch.object(provider, 'materialize_fold_labels', return_value={'done': True}) as materialize:
            self.assertEqual(runner.prepare_labels(raw, self.base/'prepared-new'), {'done': True})
        materialize.assert_called_once_with(raw, self.base/'prepared-new')

    def test_all25_synthetic_fits_seal_320_predictions_before_separate_assessment(self):
        inputs, labels = fixture(320); root = self.base/'full'; root.mkdir(); run = root/'run'; label_root = root/'prepared'
        contracts = materialized(inputs, labels, label_root)
        runner.initialize(inputs, run, provenance=EMPTY_PROVENANCE, label_contracts=contracts)
        fits = []; real_fit = offset.fit_offset
        def counted(*args):
            fits.append(len(args[1])); return real_fit(*args)
        with patch.object(offset, 'fit_offset', counted):
            for fold in range(5): runner.fit_fold(inputs, fold, label_root, contracts[fold], run)
        self.assertEqual(len(fits), 25)
        self.assertFalse((run/'COMPLETE.json').exists()); self.assertFalse((run/'PREDICTIONS_COMPLETE.json').exists())
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('no label reads while sealing')):
            predictions = runner.finalize_predictions(inputs, run)
        self.assertEqual(len(predictions), 320)
        self.assertTrue((run/'PREDICTIONS_COMPLETE.json').exists())
        for p in predictions:
            self.assertEqual(p['choices']['H'], p['choices']['structural_C'])
            self.assertTrue(p['zero_residual_parent_choice_parity'])
            for arm in ('HS', 'Jm'):
                self.assertTrue(p['shared_theta_diagnostics'][arm]['features_identical_exact'])
                self.assertEqual(p['candidate_scores']['H'], p['candidate_scores']['shared_H_'+arm])
        reads = []; real_read = Path.read_bytes
        def assessment_only(path):
            reads.append(path)
            self.assertTrue((run/'PREDICTIONS_COMPLETE.json').exists()); self.assertEqual(len(fits), 25)
            self.assertEqual(path, label_root/'assessment/all320-labels.json')
            return real_read(path)
        with patch.object(Path, 'read_bytes', assessment_only), patch.object(offset, 'fit_offset', side_effect=AssertionError('no refit')):
            report = runner.assess_predictions(inputs, run, label_root, contracts[None])
        self.assertEqual(len(reads), 1); self.assertFalse(report['gate']['passed'])
        self.assertEqual(report['full']['examples'], 320); self.assertEqual(report['full_train_refits'], 0)
        self.assertFalse(report['model_promotion']); self.assertFalse((run/'full-train').exists())
        complete = runner._read(run/'COMPLETE.json'); self.assertEqual(complete['completed_fits'], 25)
        for name, digest in complete['files_sha256'].items(): self.assertEqual(runner._sha(run/name), digest)
        self.assertEqual(report['shared_theta_diagnostics']['HS']['identical_features']['examples'], 320)
        with self.assertRaisesRegex(ValueError, 'cannot resume'):
            runner.fit_fold(inputs, 0, label_root, contracts[0], run)


if __name__ == '__main__':
    unittest.main()
