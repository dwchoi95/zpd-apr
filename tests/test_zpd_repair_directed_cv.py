"""Real144 synthetic staged integration only; never empirical repair outcomes."""
import copy
from dataclasses import asdict, replace
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts import run_zpd_repair_directed_cv as runner
from scripts import zpd_repair_directed_history as directed
from scripts import zpd_repair_residual_newton as core
from scripts import zpd_repair_feedback_labels as provider
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_repair_feedback_cv import (
    EMPTY_PROVENANCE, encoded, fixture as old_fixture, materialized)


def fixture(n=10):
    """Retain synthetic baselines/labels, encode actual edits at their true width."""
    old, labels = old_fixture(n)
    observations = []
    interactions = {arm: {} for arm in runner.ARMS}
    def history_row(source):
        return dict(code=source.source.decode('utf-8'), verdict=source.verdict,
                    timestamp=source.timestamp, language='Python')
    for ex in old.examples:
        current = ex.observation.current
        observation = dict(example_id=ex.example_id, user_id=ex.user_id,
            problem_id=ex.observation.problem_id, bank_id=ex.bank_id,
            fold=old.assignment['example_fold'][ex.example_id],
            current_code=current.source.decode('utf-8'), current_verdict=current.verdict,
            current_timestamp=current.timestamp, current_source_sha256=current.source_sha256,
            history=[history_row(s) for s in ex.observation.prior],
            donor_history=[history_row(s) for s in ex.donor_history],
            donor_example_id='synthetic-donor-'+ex.example_id, donor_user_id='synthetic-donor-user',
            observed_source_ids=[s.submission_id for s in (current, *ex.observation.prior)],
            donor_source_ids=[s.submission_id for s in ex.donor_history])
        observations.append(observation)
        bank = old.banks[ex.bank_id]
        for arm in runner.ARMS:
            history = (observation['donor_history'] if arm == 'U' else
                       observation['history'][-1:] if arm == 'L' else observation['history'])
            matrix = np.asarray([directed.candidate_features(observation['current_code'],
                c.source.decode('utf-8'), current.verdict, history, current.timestamp,
                mode='marginal' if arm == 'Jm' else 'joint', shuffled=arm == 'HS',
                shuffle_key=ex.example_id).vector for c in bank.candidates])
            interactions[arm][ex.bank_id] = core.CandidateBlock(
                tuple(c.candidate_id for c in bank.candidates), matrix)
    return runner.PreparedInputs(old.examples, old.banks, old.assignment, tuple(observations),
        interactions, old.parent_folds, old.fold_assignment_sha256, synthetic=True), labels


class DirectedCVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs, cls.labels = fixture()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve(); self.run = self.base/'run'
        self.label_root = self.base/'prepared'
        self.contracts = materialized(self.inputs, self.labels, self.label_root)

    def start(self, inputs=None, provenance=None):
        return runner.initialize(inputs or self.inputs, self.run,
            provenance=provenance or EMPTY_PROVENANCE, label_contracts=self.contracts)

    def test_source_only_contract_and_true_width_not_padding(self):
        with patch('builtins.open', side_effect=AssertionError('source validation I/O')):
            self.assertEqual(len(runner.validate_inputs(self.inputs)), 10)
        self.assertEqual(runner.SPEC.dimension, 144)
        self.assertEqual(runner.SPEC.model_kind, 'fixed_repair_directed_offset_newton_v2')
        self.assertTrue(any(b.matrix.any() for b in self.inputs.interactions['H'].values()))
        self.assertEqual(runner.SPEC.feature_configuration_sha256, canonical_hash(directed.configuration()))
        for mutation in ('support', 'parent', 'observed_future', 'source', 'arm', 'width', 'noop', 'bound'):
            changed = copy.deepcopy(self.inputs)
            if mutation == 'support': changed = replace(changed, support_complete_sha256='0'*64)
            elif mutation == 'parent': changed = replace(changed, parent_complete_sha256='0'*64)
            elif mutation == 'observed_future': changed.observations[0]['target'] = 'forbidden'
            elif mutation == 'source': changed.observations[0]['current_code'] += '# drift'
            elif mutation == 'arm': changed.interactions['rescue'] = changed.interactions['H']
            else:
                block = changed.interactions['H']['b0']; matrix = block.matrix.copy()
                if mutation == 'width': matrix = np.zeros((len(block.candidate_ids), 1296))
                elif mutation == 'noop': matrix[0, 0] = .01
                else: matrix[1, 0] = 2.
                changed.interactions['H']['b0'] = replace(block, matrix=matrix)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): runner.validate_inputs(changed)

    def test_parent_scores_membership_and_metadata_stay_frozen(self):
        for mutation in ('membership', 'training', 'coefficients', 'scores'):
            changed = copy.deepcopy(self.inputs); parent = changed.parent_folds[0]
            model = parent.models['structural_C']
            if mutation == 'membership': changed.parent_folds[0] = replace(parent, train_example_ids=parent.held_example_ids)
            elif mutation == 'training': model['training']['pair_example_ids'][0] = parent.held_example_ids[0]
            elif mutation == 'coefficients': model['coefficients'].pop()
            else:
                scores = parent.predictions[0]['candidate_scores']['structural_C']
                scores[next(iter(scores))] += .01
            model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): runner.validate_inputs(changed)

    def test_worker_reads_own_labels_once_and_plans_once_for_five_models(self):
        self.start(); actual_read = Path.read_bytes; reads = []; plans = []; fits = []
        actual_plan = core.make_pair_plan; actual_fit = core.fit_offset
        def read(path):
            reads.append(path); self.assertEqual(path, self.label_root/'fold-0/train-labels.json')
            return actual_read(path)
        def plan(examples, banks, labels):
            plans.append(1); ids = {ex.bank_id for ex in examples}
            self.assertEqual(ids, set(banks)); self.assertEqual(ids, {k[0] for k in labels})
            held_problems = {ex.observation.problem_id for ex in self.inputs.examples
                             if self.inputs.assignment['example_fold'][ex.example_id] == 0}
            self.assertTrue(held_problems.isdisjoint({ex.observation.problem_id for ex in examples}))
            return actual_plan(examples, banks, labels)
        def fit(*args, **kwargs):
            self.assertEqual(args[0].shape[1], 144); self.assertEqual(kwargs['spec'], runner.SPEC)
            fits.append(1); return actual_fit(*args, **kwargs)
        with patch.object(Path, 'read_bytes', read), patch.object(core, 'make_pair_plan', plan), \
                patch.object(core, 'fit_offset', fit):
            predictions = runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)
        self.assertEqual((len(reads), len(plans), len(fits), len(predictions)), (1, 1, 5, 2))
        self.assertEqual(set(predictions[0]['choices']), set(runner.METHODS))
        for arm in runner.ARMS:
            model = runner._read(self.run/f'fold-0/{arm}.json')['offset_model']
            self.assertEqual(len(model['coefficients']), 144)
            self.assertEqual(model['configuration']['representation'], asdict(runner.SPEC))
            self.assertLessEqual(model['optimization']['gradient_infinity_norm'], 1e-8)
        self.assertNotIn('labels', inspect.signature(runner.predict_fold).parameters)
        self.assertFalse((self.run/'PREDICTIONS_COMPLETE.json').exists())

    def test_failed_third_optimizer_keeps_two_models_and_never_resumes(self):
        self.start(); actual = core.fit_offset; calls = []
        def fail(*args, **kwargs):
            calls.append(1)
            if len(calls) == 3:
                raise core.OffsetOptimizationError('synthetic convergence failure',
                    {'accepted': False, 'gradient': .1, 'final_theta': [0.]*144,
                     'trace': [{'iteration': 0, 'objective': 1., 'gradient_infinity_norm': .1}]})
            return actual(*args, **kwargs)
        with patch.object(core, 'fit_offset', fail), self.assertRaisesRegex(RuntimeError, 'convergence'):
            runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)
        self.assertEqual(len(calls), 3)
        self.assertTrue((self.run/'fold-0/H.json').exists()); self.assertTrue((self.run/'fold-0/Jm.json').exists())
        self.assertFalse((self.run/'fold-0/HS.json').exists()); self.assertFalse((self.run/'fold-0/COMPLETE.json').exists())
        self.assertEqual(runner._read(self.run/'FAILED.json')['completed_fits_in_failed_fold'], 2)
        diagnostics = runner._read(self.run/'FAILED.json')['diagnostics']
        self.assertFalse(diagnostics['accepted'])
        self.assertEqual(len(diagnostics['final_theta']), 144)
        self.assertEqual(diagnostics['trace'][0]['iteration'], 0)
        with self.assertRaisesRegex(ValueError, 'cannot resume'):
            runner.fit_fold(self.inputs, 1, self.label_root, self.contracts[1], self.run)

    def test_wrong_label_contract_is_rejected_without_any_label_read(self):
        self.start()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('forbidden label read')):
            with self.assertRaisesRegex(ValueError, 'trusted initialization'):
                runner.fit_fold(self.inputs, 0, self.label_root,
                    replace(self.contracts[0], expected_sha256='0'*64), self.run)

    def test_wrong_assessment_contract_is_rejected_without_any_label_read(self):
        self.start()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('forbidden assessment read')):
            with self.assertRaisesRegex(ValueError, 'trusted initialization'):
                runner.assess_predictions(self.inputs, self.run, self.label_root,
                    replace(self.contracts[None], expected_source_binding_sha256='0'*64))
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_all_source_metadata_aligns_and_only_history_language_is_external(self):
        mutations = {
            'ids_order': lambda o: o['observed_source_ids'].reverse(),
            'donor_ids': lambda o: o['donor_source_ids'].__setitem__(0, 'wrong'),
            'current_sha': lambda o: o.__setitem__('current_source_sha256', '0'*64),
            'current_time': lambda o: o.__setitem__('current_timestamp', 2),
            'current_verdict': lambda o: o.__setitem__('current_verdict', 'AC'),
            'prior_code': lambda o: o['history'][0].__setitem__('code', 'pass\n'),
            'prior_time': lambda o: o['history'][0].__setitem__('timestamp', True),
            'donor_verdict': lambda o: o['donor_history'][0].__setitem__('verdict', 'AC'),
            'language': lambda o: o['history'][0].__setitem__('language', False),
            'extra': lambda o: o['history'][0].__setitem__('future', True),
        }
        for name, mutate in mutations.items():
            changed = copy.deepcopy(self.inputs); mutate(changed.observations[0])
            with self.subTest(name=name), self.assertRaises(ValueError): runner.validate_inputs(changed)
        # Typed Example omits language, so source-loader provenance is the
        # language authority. Never silently coerce a declared non-Python row.
        changed = copy.deepcopy(self.inputs); changed.observations[0]['history'][0]['language'] = 'C++'
        self.assertEqual(len(runner.validate_inputs(changed)), 10)

    def test_drift_during_last_assessment_replay_prevents_both_complete_seals(self):
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
            if len(calls) == 2: runtime['scipy'] = 'synthetic-last-replay-drift'
            return predictions
        with patch.object(runner, '_prediction_barrier', replay), \
                patch.object(runner, '_runtime', lambda: dict(runtime)), \
                patch.object(provider, 'validate_assessment_envelope', return_value=self.labels):
            with self.assertRaisesRegex(ValueError, 'runtime changed'):
                runner.assess_predictions(self.inputs, self.run, self.label_root, self.contracts[None])
        self.assertEqual(len(calls), 2)
        self.assertFalse((self.run/'assessment/COMPLETE.json').exists())
        self.assertFalse((self.run/'COMPLETE.json').exists()); self.assertTrue((self.run/'FAILED.json').exists())

    def test_missing_all_models_barrier_never_reads_assessment(self):
        self.start()
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('forbidden assessment read')):
            with self.assertRaises(FileNotFoundError):
                runner.assess_predictions(self.inputs, self.run, self.label_root, self.contracts[None])
        self.assertTrue((self.run/'FAILED.json').exists())

    def test_drift_after_inner_assessment_seal_blocks_outer_complete(self):
        self.start(); (self.run/'PREDICTIONS_COMPLETE.json').write_text('{}\n')
        predictions = [dict({k: row[k] for k in ('example_id', 'user_id', 'bank_id', 'problem_id', 'fold')},
            choices={method: row['noop_candidate_id'] for method in runner.METHODS},
            shared_theta_diagnostics={arm: dict(features_identical_exact=True, choice_changed=False,
                transition='same', score_difference={}) for arm in ('HS', 'Jm')})
            for row in runner._cohort(self.inputs)]
        runtime = runner._runtime(); actual_seal = runner._seal; sealed = []
        def seal(directory, *args, **kwargs):
            result = actual_seal(directory, *args, **kwargs); sealed.append(directory)
            if directory == self.run/'assessment': runtime['scipy'] = 'synthetic-post-inner-drift'
            return result
        with patch.object(runner, '_prediction_barrier', return_value=predictions), \
                patch.object(runner, '_runtime', lambda: dict(runtime)), patch.object(runner, '_seal', seal), \
                patch.object(provider, 'validate_assessment_envelope', return_value=self.labels):
            with self.assertRaisesRegex(ValueError, 'runtime changed'):
                runner.assess_predictions(self.inputs, self.run, self.label_root, self.contracts[None])
        self.assertEqual(sealed, [self.run/'assessment'])
        self.assertTrue((self.run/'assessment/COMPLETE.json').exists())
        self.assertTrue((self.run/'assessment/FAILED.json').exists())
        self.assertFalse((self.run/'COMPLETE.json').exists()); self.assertTrue((self.run/'FAILED.json').exists())

    def test_new_paths_only_no_prepare_api_and_no_production_cli(self):
        self.start()
        with self.assertRaisesRegex(ValueError, 'new run'): self.start()
        self.assertFalse(hasattr(runner, 'prepare_labels'))
        with patch('builtins.open', side_effect=AssertionError('forbidden CLI I/O')):
            with self.assertRaisesRegex(RuntimeError, 'NOT released'): runner.main([])

    def test_prior_numerical_version_and_config_drift_rejected_before_labels(self):
        self.start()
        manifest = runner._read(self.run/'manifest.json')
        self.assertEqual(manifest['numerical_configuration'], core.configuration(runner.SPEC))
        for mutation in ('v1', 'configuration', 'spec_type'):
            changed = copy.deepcopy(manifest)
            if mutation == 'v1': changed['kind'] = 'prospective_repair_directed_cv_staged_v1'
            elif mutation == 'configuration': changed['numerical_configuration']['retries'] = 1
            else: changed['residual_spec']['dimension'] = 144.
            (self.run/'manifest.json').write_bytes(encoded(changed))
            marker = runner._read(self.run/'FOLDS_COMPLETE.json')
            marker['files_sha256']['manifest.json'] = runner._sha(self.run/'manifest.json')
            (self.run/'FOLDS_COMPLETE.json').write_bytes(encoded(marker))
            with self.subTest(mutation=mutation), patch.object(Path, 'read_bytes',
                    side_effect=AssertionError('forbidden label read')):
                with self.assertRaisesRegex(ValueError, 'differ from initialization'):
                    runner.fit_fold(self.inputs, 0, self.label_root, self.contracts[0], self.run)

    def test_observation_and_exact_array_fingerprints_are_bound(self):
        original = runner.input_fingerprint(self.inputs)
        changed = copy.deepcopy(self.inputs); changed.observations[0]['history'][0]['language'] = 'C++'
        self.assertNotEqual(runner.input_fingerprint(changed), original)
        changed = copy.deepcopy(self.inputs); block = changed.interactions['H']['b0']
        changed.interactions['H']['b0'] = replace(block, matrix=np.zeros((len(block.candidate_ids), 145)))
        self.assertNotEqual(runner.input_fingerprint(changed), original)

    def test_late_label_source_runtime_and_terminal_write_drift_fail_closed(self):
        for which in ('label', 'source', 'runtime', 'status'):
            base = self.base/which; base.mkdir(); run = base/'run'; labels = base/'prepared'
            contracts = materialized(self.inputs, self.labels, labels)
            source = base/'source.py'; source.write_text('before\n')
            runner.initialize(self.inputs, run, label_contracts=contracts,
                provenance=dict(source_sha256={str(source): runner._sha(source)}, input_sha256={}))
            runtime = runner._runtime(); predict = runner.predict_fold; status = runner._status
            def mutate(*args):
                result = predict(*args)
                if which == 'runtime': runtime['scipy'] = 'synthetic-drift'
                elif which in ('label', 'source'):
                    (labels/'fold-0/train-labels.json' if which == 'label' else source).write_text('drift\n')
                return result
            def write_status(directory, **body):
                if which == 'status' and body.get('phase') == 'complete': raise OSError('synthetic terminal failure')
                return status(directory, **body)
            with self.subTest(which=which), patch.object(runner, 'predict_fold', mutate), \
                    patch.object(runner, '_runtime', lambda: dict(runtime)), patch.object(runner, '_status', write_status):
                with self.assertRaises((ValueError, OSError)):
                    runner.fit_fold(self.inputs, 0, labels, contracts[0], run)
            self.assertTrue((run/'FAILED.json').exists()); self.assertFalse((run/'fold-0/COMPLETE.json').exists())

    def test_all25_fits_seal_320_before_separate_assessment(self):
        inputs, labels = fixture(320); base = self.base/'full'; base.mkdir()
        run = base/'run'; prepared = base/'prepared'; contracts = materialized(inputs, labels, prepared)
        runner.initialize(inputs, run, provenance=EMPTY_PROVENANCE, label_contracts=contracts)
        fits = []; actual_fit = core.fit_offset
        def fit(*args, **kwargs):
            fits.append(1); return actual_fit(*args, **kwargs)
        with patch.object(core, 'fit_offset', fit):
            for fold in range(5): runner.fit_fold(inputs, fold, prepared, contracts[fold], run)
        self.assertEqual(len(fits), 25); self.assertFalse((run/'COMPLETE.json').exists())
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('label-free seal required')):
            predictions = runner.finalize_predictions(inputs, run)
        self.assertEqual(len(predictions), 320)
        for p in predictions:
            self.assertEqual(set(p['choices']), set(runner.METHODS))
            self.assertTrue(p['zero_residual_parent_choice_parity'])
            for arm in ('HS', 'Jm'):
                self.assertTrue(p['shared_theta_diagnostics'][arm]['features_identical_exact'])
                self.assertEqual(p['candidate_scores']['H'], p['candidate_scores']['shared_H_'+arm])
        reads = []; actual_read = Path.read_bytes
        def assessment_only(path):
            reads.append(path); self.assertEqual(path, prepared/'assessment/all320-labels.json')
            self.assertTrue((run/'PREDICTIONS_COMPLETE.json').exists()); self.assertEqual(len(fits), 25)
            return actual_read(path)
        with patch.object(Path, 'read_bytes', assessment_only), \
                patch.object(core, 'fit_offset', side_effect=AssertionError('no refit')):
            report = runner.assess_predictions(inputs, run, prepared, contracts[None])
        self.assertEqual(len(reads), 1); self.assertEqual(report['full']['examples'], 320)
        self.assertFalse(report['gate']['passed']); self.assertFalse(report['model_promotion'])
        self.assertEqual(report['full_train_refits'], 0)
        self.assertEqual(report['shared_theta_diagnostics']['HS']['identical_features']['examples'], 320)
        self.assertTrue(any(c['status'] == 'unknown' for c in labels.values()))
        complete = runner._read(run/'COMPLETE.json'); self.assertEqual(complete['completed_fits'], 25)
        for name, digest in complete['files_sha256'].items(): self.assertEqual(runner._sha(run/name), digest)


if __name__ == '__main__':
    unittest.main()
