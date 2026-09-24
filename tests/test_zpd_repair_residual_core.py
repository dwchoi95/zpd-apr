"""Only synthetic objects/arrays; no empirical labels, models, banks or I/O."""
import copy
from dataclasses import FrozenInstanceError, replace
import inspect
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from scipy.optimize import brentq
from scipy.special import expit

from scripts import zpd_repair_residual_core as core
from scripts import zpd_repair_directed_history as directed
from scripts import zpd_repair_feedback_offset as legacy_offset
from scripts import zpd_repair_feedback_pairs as legacy_pairs
from scripts import zpd_repair_structure as structural
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_repair_feedback_pairs import fixture

SPEC = core.ResidualSpec(directed.VERSION, 144, canonical_hash(directed.configuration()),
                         'fixed_repair_directed_offset_logistic_v1')
OLD_SPEC = core.ResidualSpec('synthetic_legacy1296_parity', 1296, 'a'*64, 'synthetic_residual_parity_v1')


def arrays(width=144, base=0., zero=False):
    x = np.zeros((2, width), dtype=np.float64)
    if not zero: x[0, 0] = 1.; x[1, 0] = -1.
    return x, np.array([1, 0], dtype=np.int64), np.full(2, 950.), np.array([base, -base], dtype=np.float64)


def blocks(interactions, width):
    return {bid: core.CandidateBlock(value.candidate_ids, value.matrix[:, :width]) for bid, value in interactions.items()}


def reseal(model):
    model['model_sha256'] = core._model_hash({k: v for k, v in model.items() if k != 'model_sha256'})
    return model


class ResidualCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = core.fit_offset(*arrays(), spec=SPEC)
        cls.zero_model = core.fit_offset(*arrays(zero=True), spec=SPEC)

    def test_spec_and_candidate_block_are_strict_immutable_owned_values(self):
        for kwargs in (dict(dimension=True), dict(dimension=0), dict(feature_configuration_sha256='wrong'),
                       dict(representation=''), dict(model_kind=None)):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): replace(SPEC, **kwargs)
        with self.assertRaises(FrozenInstanceError): SPEC.dimension = 1296
        source = np.zeros((2, 144)); block = core.CandidateBlock(('a'*64, 'b'*64), source)
        source[:] = 1.
        self.assertFalse(block.matrix.any())
        with self.assertRaises(ValueError): block.matrix.flags.writeable = True
        with self.assertRaises(FrozenInstanceError): block.candidate_ids = ()
        for ids, matrix in ((['a'*64], np.zeros((1, 144))), (('a'*64, 'a'*64), np.zeros((2, 144))),
                            (('a'*64,), np.zeros((1, 144), dtype=np.float32)),
                            (('a'*64,), np.full((1, 144), np.nan)), (('not-sha',), np.zeros((1, 144)))):
            with self.assertRaises(ValueError): core.CandidateBlock(ids, matrix)

    def test_1296_pair_arrays_and_legacy_training_metadata_exact_parity(self):
        ex, banks, labels, interactions, base = fixture()
        plan = core.make_pair_plan(ex, banks, labels)
        actual = core.materialize_pairs(plan, blocks(interactions, 1296), base, spec=OLD_SPEC)
        old = legacy_pairs.build_pairs(ex, banks, labels, interactions, base)
        for key in ('matrix', 'y', 'weights', 'base_margin'):
            left, right = getattr(actual, key), getattr(old, key)
            np.testing.assert_array_equal(left, right)
            self.assertEqual(left.tobytes(), right.tobytes())
        self.assertEqual(actual.metadata['training'], old.metadata['training'])
        self.assertEqual(actual.metadata['pair_candidate_ids'], old.metadata['pair_candidate_ids'])
        _, old_y, old_w, _, old_meta = structural.training_data(ex, banks, labels, 'C', 'structural')
        np.testing.assert_array_equal(actual.y, old_y); np.testing.assert_array_equal(actual.weights, old_w)
        self.assertEqual(actual.metadata['training'], old_meta)
        for key in actual.metadata['all_pair_counts']:
            self.assertEqual(actual.metadata['all_pair_counts'][key], old.metadata['all_pair_counts'][key])
        self.assertNotIn('event_count', actual.metadata)
        self.assertNotIn('event_available_candidates', actual.metadata['banks'][0])

    def test_1296_objective_coefficients_certificate_and_scorer_parity(self):
        values = arrays(1296, base=.25)
        theta = np.linspace(-.1, .2, 1296)
        a = core.objective_and_gradient(theta, *values, spec=OLD_SPEC)
        b = legacy_offset.objective_and_gradient(theta, *values)
        self.assertEqual(a[0], b[0]); np.testing.assert_array_equal(a[1], b[1])
        model = core.fit_offset(*values, spec=OLD_SPEC)
        old_model = legacy_offset.fit_offset(*values)
        for key in ('coefficients', 'final_gradient', 'training', 'optimization', 'runtime'):
            self.assertEqual(model[key], old_model[key])
        _, banks, _, interactions, base = fixture()
        for bid, block in blocks(interactions, 1296).items():
            scores = core.score_candidates(model, block, base[bid], expected_spec=OLD_SPEC)
            self.assertEqual(scores, legacy_pairs.score_candidates(old_model, banks[bid], interactions[bid], base[bid]))
            self.assertEqual(core.select_candidate(model, block, base[bid], expected_spec=OLD_SPEC),
                             legacy_pairs.select_candidate(old_model, banks[bid], interactions[bid], base[bid]))

    def test_144_materializes_without_padding_and_plan_reused_without_mutation(self):
        ex, banks, labels, interactions, base = fixture()
        plan = core.make_pair_plan(ex, banks, labels); before = plan.metadata
        for _ in range(5):
            result = core.materialize_pairs(plan, blocks(interactions, 144), base, spec=SPEC)
            self.assertEqual(result.matrix.shape, (12, 144))
            self.assertEqual(result.metadata['spec']['dimension'], 144)
            result.metadata['training']['ordered_pairs'] = -1
            result.weights[:] = -1
        self.assertEqual(plan.metadata, before)
        self.assertTrue((plan.weights > 0).all())
        with self.assertRaises(ValueError): plan.y.flags.writeable = True
        with self.assertRaises(ValueError): plan.weights.flags.writeable = True

    def test_signed_zero_mirrors_match_frozen_array_hashes(self):
        ex, banks, labels, interactions, base = fixture()
        for bid in interactions:
            interactions[bid].matrix[:] = 0.
            base[bid] = dict.fromkeys(base[bid], 0.)
        actual = core.materialize_pairs(core.make_pair_plan(ex, banks, labels), blocks(interactions, 1296), base, spec=OLD_SPEC)
        old = legacy_pairs.build_pairs(ex, banks, labels, interactions, base)
        for name in ('matrix', 'base_margin'):
            self.assertEqual(core._sha_arrays(getattr(actual, name)), core._sha_arrays(getattr(old, name)))

    def test_user_prefix_pair_weights_and_uninformative_prefix_match_legacy(self):
        ex, banks, labels, interactions, base = fixture()
        ex.append(replace(ex[0], example_id='e3', bank_id='b3'))
        banks['b3'] = banks['b0']; interactions['b3'] = copy.deepcopy(interactions['b0']); base['b3'] = dict(base['b0'])
        for (bid, cid), row in list(labels.items()):
            if bid == 'b0': labels['b3', cid] = dict(row, bank_id='b3')
        ids = interactions['b3'].candidate_ids
        labels['b3', ids[2]].update(gain=0., loss=0., all_ac=False)
        data = core.materialize_pairs(core.make_pair_plan(ex, banks, labels), blocks(interactions, 144), base, spec=SPEC)
        reference = legacy_pairs.build_pairs(ex, banks, labels, interactions, base)
        np.testing.assert_array_equal(data.weights, reference.weights)
        self.assertEqual(data.metadata['training'], reference.metadata['training'])
        totals = {}
        users = {value.example_id: value.user_id for value in ex}
        for eid, weight in zip(data.metadata['training']['pair_example_ids'], data.weights):
            totals[users[eid]] = totals.get(users[eid], 0.)+weight
        np.testing.assert_allclose(list(totals.values()), 950.)

    def test_unknown_ties_and_zero_differences_retained_without_noop_preference(self):
        ex, banks, labels, interactions, base = fixture()
        ids = interactions['b0'].candidate_ids
        labels['b0', ids[2]].update(status='unknown', gain=None, loss=None, all_ac=None)
        for row in labels.values():
            if row['bank_id'] == 'b1': row.update(status='unknown', gain=None, loss=None, all_ac=None)
        for interaction in interactions.values(): interaction.matrix[:] = 0.
        data = core.materialize_pairs(core.make_pair_plan(ex, banks, labels), blocks(interactions, 144), base, spec=SPEC)
        self.assertEqual(data.matrix.shape, (2, 144)); self.assertFalse(data.matrix.any())
        self.assertEqual(data.metadata['training']['uninformative_train_example_ids'], ['e1'])
        self.assertEqual(data.metadata['all_pair_counts']['unordered_pairs'], 6)
        self.assertEqual(data.metadata['informative_pair_counts']['zero_interaction_pairs'], 1)
        self.assertEqual(data.metadata['banks'][0]['unknown_candidates'], 1)
        block = blocks(interactions, 144)['b0']; base['b0'][ids[2]] = 100.
        self.assertEqual(core.select_candidate(self.model, block, base['b0'], expected_spec=SPEC), ids[2])
        labels['b0', ids[0]].update(all_ac=True, gain=0., loss=0.)
        labels['b0', ids[1]].update(all_ac=True, gain=0., loss=0.)
        with self.assertRaises(core.NoInformativePairs) as error: core.make_pair_plan(ex, banks, labels)
        self.assertEqual(error.exception.metadata['banks'][0]['stable_tied_pairs'], 1)
        self.assertEqual(error.exception.metadata['training']['sample_weight_sum'], 0.)

    def test_exact_scope_rejects_extra_held_labels_before_value_access(self):
        ex, banks, labels, interactions, base = fixture()
        labels['held_bank', 'held_sha'] = object()
        with self.assertRaisesRegex(ValueError, 'labels must have exactly'): core.make_pair_plan(ex, banks, labels)
        labels.pop(('held_bank', 'held_sha'))
        for split in ('valid', 'test', 'held'):
            with self.assertRaisesRegex(ValueError, 'fold-training'):
                core.make_pair_plan([replace(ex[0], split=split), ex[1]], banks, labels)
        for field in ('example_id', 'bank_id'):
            bad = [ex[0], replace(ex[1], **{field: getattr(ex[0], field)})]
            with self.assertRaisesRegex(ValueError, 'unique'): core.make_pair_plan(bad, banks, labels)
        labels[next(iter(labels))]['future_field'] = True
        with self.assertRaisesRegex(ValueError, 'core-label'): core.make_pair_plan(ex, banks, labels)

    def test_exact_candidate_bank_coverage_order_dimensions_and_base_scalars(self):
        ex, banks, labels, interactions, base = fixture(); plan = core.make_pair_plan(ex, banks, labels)
        good = blocks(interactions, 144)
        for mutated in (dict(good, held_bank=object()), {bid: block for bid, block in good.items() if bid != 'b0'},
                        blocks(interactions, 1296), dict(good, b0=core.CandidateBlock(tuple(reversed(good['b0'].candidate_ids)), good['b0'].matrix))):
            with self.assertRaises(ValueError): core.materialize_pairs(plan, mutated, base, spec=SPEC)
        for value in (True, '0', float('nan'), np.array(0.)):
            bad = copy.deepcopy(base); bad['b0'][good['b0'].candidate_ids[0]] = value
            with self.assertRaises(ValueError): core.materialize_pairs(plan, good, bad, spec=SPEC)
        with self.assertRaises(ValueError): core.materialize_pairs(plan, good, dict(base, held={}), spec=SPEC)

    def test_144_analytical_optimum_fixed_options_and_exact_parameter_count(self):
        model = self.model
        optimum = brentq(lambda theta: theta-190.*expit(-theta), 0., 20.)
        self.assertAlmostEqual(model['coefficients'][0], optimum, delta=1e-6)
        np.testing.assert_array_equal(model['coefficients'][1:], np.zeros(143))
        self.assertEqual(len(model['coefficients']), 144)
        self.assertEqual(len(model['final_gradient']), 144)
        self.assertEqual(model['configuration']['representation']['feature_configuration_sha256'], SPEC.feature_configuration_sha256)
        actual = core.minimize
        with patch.object(core, 'minimize', wraps=actual) as call: core.fit_offset(*arrays(), spec=SPEC)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args.kwargs, dict(method='L-BFGS-B', jac=True, bounds=None,
            options=dict(maxiter=2000, ftol=1e-12, gtol=1e-8, maxcor=10, maxls=20, maxfun=15000)))
        np.testing.assert_array_equal(call.call_args.args[1], np.zeros(144))
        self.assertEqual(set(inspect.signature(core.fit_offset).parameters), {'x', 'labels', 'weights', 'base_margin', 'spec'})

    def test_144_gradient_finite_difference_and_mirror_equivalence(self):
        x, y, w, base = arrays(base=.2); x[0, 1] = .2; x[1, 1] = -.2
        theta = np.linspace(-.1, .2, 144)
        value, gradient = core.objective_and_gradient(theta, x, y, w, base, spec=SPEC)
        single = .5*float(theta@theta)+190.*float(np.logaddexp(0., -(base[0]+x[0]@theta)))
        self.assertAlmostEqual(value, single, places=12)
        for coordinate in (0, 1, 2, 143):
            plus = theta.copy(); minus = theta.copy(); plus[coordinate] += 1e-5; minus[coordinate] -= 1e-5
            a = core.objective_and_gradient(plus, x, y, w, base, spec=SPEC)[0]
            b = core.objective_and_gradient(minus, x, y, w, base, spec=SPEC)[0]
            self.assertAlmostEqual(gradient[coordinate], (a-b)/2e-5, delta=2e-8)

    def test_zero_features_extreme_margins_and_csr_hash_parity(self):
        zero = self.zero_model
        np.testing.assert_array_equal(zero['coefficients'], np.zeros(144))
        self.assertEqual(zero['training']['zero_difference_rows'], 2)
        self.assertEqual(zero['training']['hessian_spectral_upper_bound'], 1.)
        for base in (-10000., 10000.):
            value, gradient = core.objective_and_gradient(np.zeros(144), *arrays(base=base), spec=SPEC)
            self.assertTrue(math.isfinite(value)); self.assertTrue(np.isfinite(gradient).all())
        x, y, w, base = arrays()
        other = core.fit_offset(sparse.csr_matrix(x), y, w, base, spec=SPEC)
        self.assertEqual(other['training']['input_sha256'], self.model['training']['input_sha256'])
        self.assertEqual(other['coefficients'], self.model['coefficients'])
        shifted = core.fit_offset(*arrays(base=8.), spec=SPEC)
        self.assertLess(shifted['coefficients'][0], self.model['coefficients'][0]-1.)

    def test_wrong_specs_old_models_padded_vectors_and_resealed_tampering_rejected(self):
        for spec in (replace(SPEC, dimension=1296), replace(SPEC, model_kind='old'),
                     replace(SPEC, feature_configuration_sha256='b'*64), replace(SPEC, representation='other')):
            with self.assertRaisesRegex(ValueError, 'spec-bound'): core.validate_offset(self.model, expected_spec=spec)
        with self.assertRaises(ValueError): core.validate_offset(legacy_offset.fit_offset(*arrays(1296)), expected_spec=OLD_SPEC)
        mutations = [lambda m: m['coefficients'].extend([0.]*1152), lambda m: m['coefficients'].__setitem__(0, True),
            lambda m: m['coefficients'].__setitem__(0, '1'), lambda m: m['final_gradient'].__setitem__(0, 1e-4),
            lambda m: m['optimization'].__setitem__('status', True),
            lambda m: m['configuration'].__setitem__('fixed_base_margin_coefficient', 2.),
            lambda m: m['training'].__setitem__('rows', 3), lambda m: m['training'].__setitem__('weight_mass', 1800.),
            lambda m: m['training']['input_sha256'].__setitem__('features', 'wrong')]
        for mutate in mutations:
            bad = copy.deepcopy(self.model); mutate(bad); reseal(bad)
            with self.assertRaises(ValueError): core.validate_offset(bad, expected_spec=SPEC)
        with self.assertRaises(ValueError): core.validate_offset(self.model, expected_spec=vars(SPEC))

    def test_invalid_matrix_weights_labels_mirrors_and_overflow_rejected(self):
        mutations = [lambda a: a.__setitem__(0, a[0].astype(np.float32)),
            lambda a: a.__setitem__(0, np.zeros((2, 1296))), lambda a: a[0].__setitem__((0, 0), float('inf')),
            lambda a: a[0].__setitem__((1, 0), .3), lambda a: a.__setitem__(1, a[1].astype(bool)),
            lambda a: a[1].__setitem__(1, 1), lambda a: a[2].__setitem__(0, -1.),
            lambda a: a[2].__setitem__(0, 949.), lambda a: a[3].__setitem__(1, 1.)]
        for mutate in mutations:
            data = list(arrays()); mutate(data)
            with self.assertRaises(ValueError): core.fit_offset(*data, spec=SPEC)
        x, y, w, base = arrays(); matrix = sparse.csr_matrix(x)
        matrix.has_canonical_format = False
        with self.assertRaises(ValueError): core.fit_offset(matrix, y, w, base, spec=SPEC)

    def test_convergence_failure_malformed_results_no_retry_or_loosened_gradient(self):
        def result(fun, zero, **kwargs):
            value, gradient = fun(zero)
            return SimpleNamespace(success=True, status=0, message='false success', nit=0, nfev=1, njev=1,
                                   x=zero, fun=value, jac=gradient)
        with patch.object(core, 'minimize', side_effect=result) as call:
            with self.assertRaises(core.OffsetOptimizationError) as error: core.fit_offset(*arrays(), spec=SPEC)
        self.assertEqual(call.call_count, 1)
        self.assertGreater(error.exception.diagnostics['gradient_infinity_norm'], 1e-6)
        for error_value in (RuntimeError('injected'),):
            with patch.object(core, 'minimize', side_effect=error_value) as call:
                with self.assertRaises(core.OffsetOptimizationError): core.fit_offset(*arrays(), spec=SPEC)
            self.assertEqual(call.call_count, 1)
        with patch.object(core, 'minimize', return_value=SimpleNamespace(success='true')):
            with self.assertRaises(core.OffsetOptimizationError): core.fit_offset(*arrays(), spec=SPEC)

    def test_label_blind_fixed_base_unknown_selection_sha_tie_shared_theta_and_no_io(self):
        ids = ('b'*64, 'a'*64, 'c'*64)
        block = core.CandidateBlock(ids, np.zeros((3, 144)))
        base = dict(zip(ids, [.5, .5, -.2]))
        with patch.object(Path, 'open', side_effect=AssertionError('pure core cannot read files')):
            scores = core.score_candidates(self.model, block, base, expected_spec=SPEC)
            self.assertEqual(scores, base)
            self.assertEqual(core.select_candidate(self.model, block, base, expected_spec=SPEC), 'a'*64)
            for _control in ('HS', 'Jm'):
                self.assertEqual(core.score_candidates(self.model, core.CandidateBlock(ids, block.matrix), base, expected_spec=SPEC), scores)
        # There is no label argument to mutate or inspect during selection.
        self.assertEqual(set(inspect.signature(core.score_candidates).parameters), {'model', 'block', 'base_scores', 'expected_spec'})
        self.assertEqual(core.validate_offset(json.loads(json.dumps(self.model)), expected_spec=SPEC).shape, (144,))


if __name__ == '__main__':
    unittest.main()
