"""Synthetic own-fold plans only; no empirical I/O, optimizer or execution."""
import copy
from dataclasses import FrozenInstanceError, replace
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import zpd_bank_topset_plan as module
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from scripts.zpd_repair_residual_core import make_pair_plan
from src.repair.pilot_contracts import canonical_hash
from tests.test_zpd_joint_progress_capsule import fixture as capsule_fixture


def fixture(n=10, *, fold=0, synthetic=True):
    """Construct labels, not a model. The only fit is a synthetic own scaler."""
    inputs = capsule_fixture(n, fold=fold, synthetic=synthetic)
    train, _ = capsule.scope(inputs)
    labels = {}
    for ex in train:
        for i, candidate in enumerate(inputs.banks[ex.bank_id].candidates):
            labels[ex.bank_id, candidate.candidate_id] = dict(bank_id=ex.bank_id,
                candidate_id=candidate.candidate_id, status='stable' if i < 3 else 'unknown',
                gain=(0. if i == 0 else .5 if i == 1 else .2) if i < 3 else None,
                loss=0. if i < 3 else None, all_ac=(i == 1) if i < 3 else None)
    return inputs, labels


def transform_for(inputs, labels):
    train, _ = capsule.scope(inputs)
    return features.fit_own_scaler(train, {e.bank_id: inputs.banks[e.bank_id] for e in train},
        {e.bank_id: inputs.raw_current[e.bank_id] for e in train}, labels)


def set_row(labels, bid, cid, *, status='stable', gain=0., loss=0., all_ac=False):
    labels[bid, cid].update(status=status, gain=gain, loss=loss, all_ac=all_ac)


class BankTopsetPlanTests(unittest.TestCase):
    def setUp(self):
        self.inputs, self.labels = fixture()
        self.train, self.held = capsule.scope(self.inputs)

    def build(self, labels=None):
        labels = self.labels if labels is None else labels
        transform = transform_for(self.inputs, labels)
        return module.build_plan(self.inputs, transform, labels), transform

    def test_exact_old_pair_mass_rows_and_all_seven_feature_projections(self):
        plan, transform = self.build()
        payload = plan.payload()
        legacy = make_pair_plan(self.train, {e.bank_id: self.inputs.banks[e.bank_id] for e in self.train}, self.labels)
        self.assertEqual(payload['original_pair_plan']['training'], legacy.metadata['training'])
        self.assertEqual(payload['original_pair_plan']['weights_sha256'], module._array_sha(legacy.weights))
        self.assertEqual(payload['original_pair_plan']['y_sha256'], module._array_sha(legacy.y))
        self.assertEqual(tuple(payload['arms']), features.ARMS)
        for arm in features.ARMS:
            banks, weights = plan.banks(arm)
            self.assertEqual(len(banks), len(self.train))
            self.assertEqual(math.fsum(weights), payload['original_pair_mass'])
            self.assertTrue(math.isclose(math.fsum(weights), 1900., rel_tol=1e-12, abs_tol=1e-12))
            for ex, bank, weight, row in zip(self.train, banks, weights, payload['banks'], strict=True):
                bid = ex.bank_id
                expected_mass = math.fsum(float(w) for key, w in zip(transform.row_keys, transform.weights)
                    if key[0] == bid)
                self.assertEqual(weight, expected_mass)
                self.assertEqual(row['original_ordered_rows'], sum(key[0] == bid for key in transform.row_keys))
                blocks = features.compose_blocks(self.inputs.raw_current[bid], transform,
                    {a: self.inputs.interactions[a][bid] for a in features.PROGRESS_ARMS})
                expected = blocks[arm].matrix[:3].toarray()
                self.assertEqual(bank.features.shape, (3, 4131))
                self.assertEqual(bank.features.tobytes(), expected.tobytes())
                self.assertEqual(bank.top_indices, (1,))
                self.assertEqual(row['stable_features_sha256'][arm], module._array_sha(expected))
        self.assertEqual({b['bank_id'] for b in payload['banks']}, {e.bank_id for e in self.train})
        self.assertNotIn(self.held[0].example_id, json.dumps(payload))

    def test_non_ac_top_is_nonregression_then_net_gain_not_a_fake_ac(self):
        ex = self.train[0]; ids = self.inputs.raw_current[ex.bank_id].candidate_ids
        # No AC. A larger gain with loss still ranks below every zero-loss row.
        set_row(self.labels, ex.bank_id, ids[1], gain=.8, loss=.1)
        set_row(self.labels, ex.bank_id, ids[2], gain=.1)
        set_row(self.labels, ex.bank_id, ids[3], gain=.1)
        plan, _ = self.build(); row = plan.payload()['banks'][0]
        self.assertEqual(row['top_candidate_ids'], list(ids[2:4]))
        self.assertEqual(row['rest_candidate_ids'], list(ids[:2]))
        self.assertEqual(plan.banks('H')[0][0].top_indices, (2, 3))

    def test_all_lexicographic_maxima_retained_with_multiple_ac_and_tied_non_ac(self):
        ex = self.train[0]; ids = self.inputs.raw_current[ex.bank_id].candidate_ids
        # Same AC flag alone is not the whole legacy preference: equal net gain
        # supplies a tied top tier; a lower-gain AC remains stable N.
        set_row(self.labels, ex.bank_id, ids[2], all_ac=True, gain=.5)
        set_row(self.labels, ex.bank_id, ids[3], all_ac=True, gain=.3)
        plan, _ = self.build(); row = plan.payload()['banks'][0]
        self.assertEqual(row['top_candidate_ids'], list(ids[1:3]))
        self.assertEqual(row['rest_candidate_ids'], [ids[0], ids[3]])
        self.assertEqual(plan.banks('H')[0][0].top_indices, (1, 2))

    def test_unknown_only_and_all_tie_and_single_stable_banks_never_drop_from_ledger(self):
        unknown, tied, single = self.train[:3]
        for ex in (unknown, tied, single):
            for i, c in enumerate(self.inputs.banks[ex.bank_id].candidates):
                if ex == tied or ex == single and i == 2:
                    set_row(self.labels, ex.bank_id, c.candidate_id)
                else:
                    set_row(self.labels, ex.bank_id, c.candidate_id, status='unknown', gain=None, loss=None, all_ac=None)
        plan, _ = self.build(); payload = plan.payload()
        a, b, c = payload['banks'][:3]
        self.assertEqual([a['status'], b['status'], c['status']], ['unknown_only', 'stable_all_tie', 'stable_all_tie'])
        self.assertEqual(a['top_candidate_ids'], []); self.assertIsNone(a['objective_bank_index'])
        self.assertEqual(a['original_pair_mass'], 0.)
        self.assertEqual(b['top_candidate_ids'], b['candidate_ids']); self.assertEqual(b['rest_candidate_ids'], [])
        self.assertEqual(c['top_indices_in_stable_rows'], [0])
        self.assertEqual(payload['coverage']['own_training_banks'], len(self.train))
        self.assertEqual(payload['coverage']['objective_banks'], len(self.train)-1)
        self.assertEqual(payload['coverage']['own_training_candidates'], len(self.labels))
        for arm in features.ARMS:
            banks, weights = plan.banks(arm)
            self.assertEqual(weights[:2].tolist(), [0., 0.])
            self.assertEqual(banks[0].top_indices, tuple(range(8)))
            self.assertEqual(banks[1].features.shape, (1, 4131))
            loss, gradient = module.objective.bank_loss_gradient(np.zeros(8), banks[0].top_indices)
            self.assertEqual(loss, 0.); self.assertFalse(gradient.any())
        self.assertEqual(sum(payload['coverage'][k] for k in ('stable_candidates', 'unknown_candidates')), len(self.labels))

    def test_missing_foreign_held_and_nonexact_dict_rejected_before_any_label_value(self):
        transform = transform_for(self.inputs, self.labels)
        class Poison(dict):
            def get(self, *args): raise AssertionError('label value touched')
            def __getitem__(self, key): raise AssertionError('label value touched')
        poison = {key: Poison() for key in self.labels}
        held = self.held[0]; held_id = self.inputs.banks[held.bank_id].candidates[0].candidate_id
        for kind in ('missing', 'foreign', 'held', 'subclass'):
            values = dict(poison)
            if kind == 'missing': values.pop(next(iter(values)))
            elif kind == 'foreign': values['foreign-bank', 'f'*64] = Poison()
            elif kind == 'held': values[held.bank_id, held_id] = Poison()
            else: values = Poison(values)
            with self.subTest(kind=kind), patch.object(module, 'make_pair_plan',
                    side_effect=AssertionError('must reject before consuming label values')), self.assertRaisesRegex(ValueError, 'before label values'):
                module.build_plan(self.inputs, transform, values)

    def test_core_schema_and_identity_stability_evidence_rejections(self):
        transform = transform_for(self.inputs, self.labels); key = next(iter(self.labels))
        for change in ({'candidate_id': 'f'*64}, {'future': 1}, {'status': 'unknown'},
                       {'all_ac': 1}, {'gain': float('nan')}, {'gain': .1}):
            labels = copy.deepcopy(self.labels); labels[key].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): module.build_plan(self.inputs, transform, labels)

    def test_original_transform_pair_and_scaler_ancestry_tampering_rejected(self):
        transform = transform_for(self.inputs, self.labels)
        y = transform.y.copy(); y[:2] = 1-y[:2]
        weights = transform.weights.copy(); weights[:2] += .01; weights[2:4] -= .01
        training = transform.training; training['sample_weight_sum'] = 1900  # Strict JSON numeric type.
        scaler_weights = transform.scaler_weights.copy(); scaler_weights[0] += .01
        variants = [replace(transform, y=y), replace(transform, weights=weights),
            replace(transform, _training_json=json.dumps(training)),
            replace(transform, scaler_weights=scaler_weights),
            replace(transform, scaler_candidate_ids=tuple(reversed(transform.scaler_candidate_ids)))]
        invalid = copy.deepcopy(transform); object.__setattr__(invalid, 'row_keys', tuple(reversed(transform.row_keys)))
        variants.append(invalid)
        for value in variants:
            with self.subTest(value=value is invalid), self.assertRaises(ValueError): module.build_plan(self.inputs, value, self.labels)

    def test_wholly_uninformative_fold_has_no_fabricated_mass_or_fallback(self):
        transform = transform_for(self.inputs, self.labels)
        for row in self.labels.values(): row.update(status='stable', gain=0., loss=0., all_ac=False)
        with self.assertRaisesRegex(ValueError, 'no unequal stable'): module.build_plan(self.inputs, transform, self.labels)

    def test_immutable_arrays_detached_payload_and_original_caller_mutation(self):
        plan, transform = self.build(); payload = plan.payload()
        banks, weights = plan.banks('H'); saved = banks[0].features.tobytes()
        for array in (weights, banks[0].features):
            with self.assertRaises(ValueError): array.flags.writeable = True
        with self.assertRaises(FrozenInstanceError): plan._payload_json = '{}'
        payload['banks'][0]['candidate_ids'].clear(); payload['bank_weights'][0] = 0.
        self.labels.clear(); self.inputs.interactions.clear()
        object.__setattr__(transform, 'numeric_scale', np.ones(3))
        self.assertEqual(plan.banks('H')[0][0].features.tobytes(), saved)
        self.assertTrue(plan.payload()['banks'][0]['candidate_ids'])
        self.assertGreater(plan.payload()['bank_weights'][0], 0.)
        with self.assertRaises(ValueError): plan.banks('Answer')
        body = plan.payload(); pin = body.pop('plan_sha256')
        self.assertEqual(pin, canonical_hash(body))
        self.assertEqual(json.loads(json.dumps(plan.payload(), allow_nan=False)), plan.payload())

    def test_zero_feature_differences_do_not_filter_original_mass(self):
        transform = transform_for(self.inputs, self.labels)
        actual = features.compose_blocks
        def zero(*args):
            blocks = actual(*args)
            return {arm: features.JointBlock(block.candidate_ids,
                sparse.csr_matrix((len(block.candidate_ids), 4131), dtype=np.float64),
                np.zeros((len(block.candidate_ids), 32))) for arm, block in blocks.items()}
        with patch.object(features, 'compose_blocks', zero): plan = module.build_plan(self.inputs, transform, self.labels)
        banks, weights = plan.banks('H')
        self.assertTrue(all(not bank.features.any() for bank in banks))
        self.assertEqual(math.fsum(weights), 1900.)
        self.assertTrue(all(row['original_ordered_rows'] > 0 for row in plan.payload()['banks']))

    def test_pure_no_io_no_optimizer_no_scaler_refit_and_only_own_composition(self):
        transform = transform_for(self.inputs, self.labels); seen = []; actual = features.compose_blocks
        def composed(raw, supplied, progress):
            seen.append(raw.bank_id)
            return actual(raw, supplied, progress)
        with patch('builtins.open', side_effect=AssertionError('no I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no empirical input')), \
             patch.object(features.StandardScaler, 'fit', side_effect=AssertionError('no scaler refit')), \
             patch.object(features, 'fit_own_scaler', side_effect=AssertionError('no scaler refit')), \
             patch.object(features, 'compose_blocks', composed):
            plan = module.build_plan(self.inputs, transform, self.labels)
            for arm in features.ARMS: plan.banks(arm)
        self.assertEqual(seen, [ex.bank_id for ex in self.train])
        self.assertFalse(plan.payload()['configuration']['scaler_fitting_performed'])

    def test_full_production_shape_membership_retained_without_empirical_inputs(self):
        inputs, labels = fixture(320, synthetic=False)
        transform = transform_for(inputs, labels)
        plan = module.build_plan(inputs, transform, labels); body = plan.payload()
        train, held = capsule.scope(inputs)
        self.assertEqual(body['coverage']['full_cohort_banks'], 320)
        self.assertEqual(body['coverage']['full_cohort_candidates'], 2544)
        self.assertEqual(body['coverage']['own_training_candidates'], len(labels))
        self.assertEqual([row['example_id'] for row in body['banks']], [ex.example_id for ex in train])
        self.assertEqual(body['coverage']['held_banks'], len(held))
        self.assertFalse(body['synthetic'])  # Production-shape synthetic objects, no loaded corpus.


if __name__ == '__main__': unittest.main()
