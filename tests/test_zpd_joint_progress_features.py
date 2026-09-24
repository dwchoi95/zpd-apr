"""Pure synthetic feature/scaler tests; no empirical bodies, fit optimizer or I/O."""
import copy
from dataclasses import FrozenInstanceError, replace
import inspect
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from sklearn.preprocessing import StandardScaler

from scripts import zpd_joint_progress_features as joint
from scripts import zpd_repair_structure as structural
from scripts.zpd_repair_fit import load_inputs
from src.repair.pilot_contracts import CandidateAttempt, ObservationSource, PilotObservation, source_hash
from tests.test_zpd_repair_feedback_pairs import fixture as training_fixture
from tests.test_zpd_repair_pairwise import fixture as full_fixture


def fixture():
    examples, banks, labels, _, _ = training_fixture()
    raw = {ex.bank_id: joint.raw_current(ex, banks[ex.bank_id]) for ex in examples}
    progress = {}
    for bid, block in raw.items():
        progress[bid] = {}
        for k, arm in enumerate(joint.PROGRESS_ARMS):
            values = np.zeros((len(block.candidate_ids), 32), dtype=np.float64)
            values[0, 3] = -0.
            for i in range(1, len(values)):
                values[i, 0] = i*.03
                if arm != 'CF': values[i, 16] = -i*.02/(k+1)
            progress[bid][arm] = joint.CandidateBlock(block.candidate_ids, values)
    return examples, banks, labels, raw, progress


class JointFeaturesTests(unittest.TestCase):
    def setUp(self):
        self.examples, self.banks, self.labels, self.raw, self.progress = fixture()

    def transform(self):
        return joint.fit_own_scaler(self.examples, self.banks, self.raw, self.labels)

    def test_source_current_exact_structural_parity_no_ids_or_history_features(self):
        ex = self.examples[0]; bank = self.banks[ex.bank_id]
        numeric, hashed = structural.raw_features(ex.observation, (), bank, 'C', 'structural')
        block = self.raw[ex.bank_id]
        for a, b in ((block.numeric, numeric), (block.hashed, hashed)):
            for name in ('data', 'indices', 'indptr'):
                self.assertEqual(getattr(a, name).tobytes(), getattr(b, name).tobytes())
        priors = tuple(ObservationSource(f'old-{i}', i/1000., b'other=1\n', source_hash(b'other=1\n'), 'CE')
            for i in range(500))
        changed = replace(ex, example_id='new-id', user_id='new-user', bank_id='renamed-bank',
            observation=PilotObservation(bank.problem_id, ex.observation.current, priors), donor_history=priors)
        altered = joint.raw_current(changed, bank)
        self.assertEqual(len(changed.observation.prior), 500)
        np.testing.assert_array_equal(altered.numeric.toarray(), numeric.toarray())
        np.testing.assert_array_equal(altered.hashed.toarray(), hashed.toarray())
        self.assertEqual(joint.NUMERIC_NAMES, tuple(structural.numeric_names('C')))
        self.assertEqual(hashed.shape[1], 4096)

    def test_arbitrary_source_bytes_and_ordered_ast_fallback_match_frozen_raw(self):
        ex = self.examples[0]; original = self.banks[ex.bank_id]
        code = b'if (: \xff\x00\r\nlast_token\n'
        bank = replace(original, attempts=tuple(CandidateAttempt(i, i, 'success', code) for i in range(8)))
        block = joint.raw_current(ex, bank)
        numeric, hashed = structural.raw_features(ex.observation, (), bank, 'C', 'structural')
        np.testing.assert_array_equal(block.numeric.toarray(), numeric.toarray())
        np.testing.assert_array_equal(block.hashed.toarray(), hashed.toarray())
        self.assertEqual(bank.attempts[0].source, code)

    def test_scaler_current_pairs_and_two_weight_normalizations_exact_legacy_parity(self):
        transform = self.transform()
        old_x, old_y, old_w, old_scale, old_info = structural.training_data(
            self.examples, self.banks, self.labels, 'C', 'structural')
        np.testing.assert_array_equal(transform.numeric_scale, old_scale)
        blocks = {bid: joint.compose_blocks(raw, transform, self.progress[bid])['C_joint'] for bid, raw in self.raw.items()}
        x, y, weights, info = joint.mirrored_pairs(transform, blocks)
        np.testing.assert_array_equal(x[:, :4099].toarray(), old_x.toarray())
        self.assertFalse(x[:, 4099:].nnz)
        self.assertEqual(y.tobytes(), old_y.tobytes()); self.assertEqual(weights.tobytes(), old_w.tobytes())
        self.assertEqual(info, old_info)
        self.assertNotIn('fixed_base_coefficient', json.dumps(info))
        self.assertNotIn('base_margin', inspect.signature(joint.mirrored_pairs).parameters)
        self.assertGreater(np.max(np.sqrt(x.multiply(x).sum(axis=1))), 1.)

    def test_scaler_once_seven_arms_append_only_and_signed_zero_authority(self):
        original_fit = StandardScaler.fit
        calls = []
        def counted(scaler, *args, **kwargs):
            calls.append(1); return original_fit(scaler, *args, **kwargs)
        with patch.object(StandardScaler, 'fit', counted): transform = self.transform()
        with patch.object(StandardScaler, 'fit', side_effect=AssertionError('no second scaler fit')):
            all_blocks = {bid: joint.compose_blocks(raw, transform, self.progress[bid]) for bid, raw in self.raw.items()}
        self.assertEqual(len(calls), 1)
        for bid, blocks in all_blocks.items():
            self.assertEqual(tuple(blocks), ('H', 'Jm', 'HS', 'U', 'L', 'CF', 'C_joint'))
            current = blocks['H'].matrix[:, :4099].toarray()
            for arm, block in blocks.items():
                self.assertEqual(block.matrix.shape, (3, 4131)); self.assertTrue(block.matrix.has_canonical_format)
                np.testing.assert_array_equal(block.matrix[:, :4099].toarray(), current)
                if arm != 'C_joint':
                    self.assertEqual(block.progress.tobytes(), self.progress[bid][arm].matrix.tobytes())
                    self.assertTrue(np.signbit(block.progress[0, 3]))
                    np.testing.assert_array_equal(block.matrix[:, 4099:].toarray(), self.progress[bid][arm].matrix)
                else: self.assertFalse(block.progress.any())
            self.assertFalse(blocks['CF'].matrix[:, 4115:].nnz)
            self.assertTrue(blocks['H'].matrix[:, 4115:].nnz)

    def test_held_values_and_labels_cannot_enter_scaler_and_held_transform_is_fixed(self):
        ex, banks, labels = load_inputs(*full_fixture()); held = ex[-1]
        before = self.transform()
        held_raw = joint.raw_current(held, banks[held.bank_id])
        held_progress = {arm: joint.CandidateBlock(held_raw.candidate_ids, self.progress['b0'][arm].matrix)
            for arm in joint.PROGRESS_ARMS}
        with patch.object(StandardScaler, 'fit', side_effect=AssertionError('held must not fit')):
            joint.compose_blocks(held_raw, before, held_progress)
        for key in list(labels):
            if key[0] == held.bank_id: labels[key] = {'arbitrary': 'held labels must remain inaccessible'}
        after = self.transform()
        self.assertEqual(before.numeric_scale.tobytes(), after.numeric_scale.tobytes())
        for raw_map, bank_map, label_map in ((dict(self.raw, b2=held_raw), self.banks, self.labels),
                (self.raw, banks, self.labels), (self.raw, self.banks, labels)):
            with self.assertRaises(ValueError): joint.fit_own_scaler(self.examples, bank_map, raw_map, label_map)
        with self.assertRaises(ValueError): joint.fit_own_scaler(ex, banks, {**self.raw, 'b2': held_raw}, labels)

    def test_equal_user_prefix_candidate_scaling_ties_and_unknowns(self):
        ex = replace(self.examples[0], example_id='e3', bank_id='b3')
        self.examples.append(ex); self.banks['b3'] = self.banks['b0']
        self.raw['b3'] = joint.raw_current(ex, self.banks['b3'])
        for (bid, cid), row in list(self.labels.items()):
            if bid == 'b0': self.labels['b3', cid] = dict(row, bank_id='b3')
        ids = self.raw['b3'].candidate_ids
        self.labels['b3', ids[2]].update(gain=.5, loss=0., all_ac=True)  # Tied but still scaler row.
        self.labels['b1', ids[2]].update(status='unknown', gain=None, loss=None, all_ac=None)
        transform = self.transform()
        expected_rows = [('b0', cid) for cid in ids]+[('b1', cid) for cid in ids[:2]]+[('b3', cid) for cid in ids]
        self.assertEqual(transform.scaler_candidate_ids, tuple(expected_rows))
        np.testing.assert_array_equal(transform.scaler_weights, np.array([1/6]*3+[1/2]*2+[1/6]*3))
        reference = structural.training_data(self.examples, self.banks, self.labels, 'C', 'structural')
        np.testing.assert_array_equal(transform.numeric_scale, reference[3])
        self.assertEqual(transform.weights.tobytes(), reference[2].tobytes())
        self.assertEqual(transform.training, reference[4])

    def test_uninformative_prefix_retained_not_scaler_row_and_no_fallback(self):
        for cid in self.raw['b1'].candidate_ids: self.labels['b1', cid].update(gain=0., loss=0., all_ac=False)
        transform = self.transform()
        self.assertEqual([bid for bid, _ in transform.bank_candidate_ids], ['b0', 'b1'])
        self.assertTrue(all(bid == 'b0' for bid, _ in transform.scaler_candidate_ids))
        self.assertEqual(transform.training['uninformative_train_example_ids'], ['e1'])
        blocks = {bid: joint.compose_blocks(raw, transform, self.progress[bid])['H'] for bid, raw in self.raw.items()}
        x, _, _, _ = joint.mirrored_pairs(transform, blocks)
        self.assertEqual(len(transform.y), 6); self.assertEqual(x.shape, (6, 4131))
        for row in self.labels.values(): row.update(gain=0., loss=0., all_ac=False)
        with self.assertRaisesRegex(ValueError, 'no unequal'): self.transform()

    def test_nearconstant_numeric_matches_sklearn_constant_rule_and_rank_deficiency(self):
        for bid, block in list(self.raw.items()):
            numeric = sparse.csr_matrix(np.array([[1e12, 2., 1.],
                [1e12+np.spacing(1e12), 2., 0.], [1e12+2*np.spacing(1e12), 2., 0.]], dtype=np.float64))
            self.raw[bid] = replace(block, numeric=numeric)
        transform = self.transform()
        numeric = sparse.vstack([self.raw[bid].numeric for bid in ('b0', 'b1')], format='csr')
        expected = StandardScaler(with_mean=False).fit(numeric, sample_weight=np.full(6, 1/3))
        for name, ref in (('numeric_scale', expected.scale_), ('numeric_mean', expected.mean_), ('numeric_variance', expected.var_)):
            self.assertEqual(getattr(transform, name).tobytes(), ref.tobytes())
        self.assertEqual(transform.numeric_scale[0], 1.); self.assertGreater(transform.numeric_variance[0], 0.)
        self.assertEqual(transform.numeric_scale[1], 1.); self.assertEqual(transform.numeric_variance[1], 0.)
        blocks = joint.compose_blocks(self.raw['b0'], transform, self.progress['b0'])
        self.assertGreater(blocks['H'].matrix[0, 0], 1e11)  # No clipping / global L2.

    def test_zero_pair_rows_retained_exact_mirrors_without_norm_bound(self):
        transform = self.transform()
        blocks = {}
        for bid, raw in self.raw.items():
            x = sparse.csr_matrix(np.ones((len(raw.candidate_ids), 4131), dtype=np.float64)*3.)
            x[:, 4099:] = 0.
            blocks[bid] = joint.JointBlock(raw.candidate_ids, x, np.zeros((len(raw.candidate_ids), 32)))
        matrix, y, w, _ = joint.mirrored_pairs(transform, blocks)
        self.assertEqual(matrix.shape, (12, 4131)); self.assertFalse(matrix.nnz)
        np.testing.assert_array_equal(y[1::2], 1-y[::2]); np.testing.assert_array_equal(w[1::2], w[::2])
        self.assertEqual(transform.row_keys[1], ('b0', transform.row_keys[0][2], transform.row_keys[0][1]))

    def test_inputs_owned_immutable_and_metadata_detached(self):
        transform = self.transform(); block = joint.compose_blocks(self.raw['b0'], transform, self.progress['b0'])['H']
        for value in (transform.numeric_scale, transform.weights, transform.scaler_weights,
                      block.progress, block.matrix.data, self.raw['b0'].numeric.data):
            with self.assertRaises(ValueError): value.flags.writeable = True
        with self.assertRaises(FrozenInstanceError): block.candidate_ids = ()
        info = transform.training; info['sample_weight_sum'] = 0.
        self.assertGreater(transform.training['sample_weight_sum'], 1899.)

    def test_malformed_raw_dimensions_nonfinite_unsorted_duplicate_and_float32(self):
        block = self.raw['b0']
        for numeric in (sparse.csr_matrix(np.zeros((3, 4))), sparse.csr_matrix(np.zeros((3, 3), dtype=np.float32)),
                sparse.csr_matrix(np.full((3, 3), np.nan)), sparse.coo_matrix(np.zeros((3, 3))),
                sparse.csr_matrix((np.ones(2), np.array([1, 1]), np.array([0, 2, 2, 2])), shape=(3, 3))):
            with self.subTest(shape=numeric.shape), self.assertRaises(ValueError): replace(block, numeric=numeric)
        with self.assertRaises(ValueError): replace(block, hashed=sparse.csr_matrix(np.zeros((3, 4095))))
        with self.assertRaises(ValueError): replace(block, candidate_ids=tuple(reversed(block.candidate_ids[:2])))
        bad = dict(self.raw); bad['b0'] = replace(block, bank_seal_sha256='e'*64)
        with self.assertRaises(ValueError): joint.fit_own_scaler(self.examples, self.banks, bad, self.labels)

    def test_progress_dimensions_order_nonfinite_CF_current_noop_and_norm_rejected(self):
        transform = self.transform(); raw = self.raw['b0']
        for mode in ('width', 'order', 'nan', 'CFtail', 'current', 'noop', 'norm', 'arm', 'zero_noop_flag'):
            inputs = dict(self.progress['b0']); x = inputs['H'].matrix.copy(); r = raw
            if mode == 'width': x = np.zeros((3, 144))
            elif mode == 'order':
                inputs['H'] = joint.CandidateBlock(tuple(reversed(raw.candidate_ids)), x)
            elif mode == 'nan':
                inputs['H'] = copy.deepcopy(inputs['H']); x[1, 16] = np.nan; object.__setattr__(inputs['H'], 'matrix', x)
            elif mode == 'CFtail':
                cf = inputs['CF'].matrix.copy(); cf[1, 16] = .01; inputs['CF'] = joint.CandidateBlock(raw.candidate_ids, cf)
            elif mode == 'current': x[1, 0] += .01
            elif mode == 'noop': x[0, 16] = .01
            elif mode == 'norm': x[1, 16] = 1.
            elif mode == 'arm': inputs['extra'] = inputs['H']
            else:
                n = raw.numeric.toarray(); n[:, 2] = 0.; r = replace(raw, numeric=sparse.csr_matrix(n))
            if mode in ('width', 'current', 'noop', 'norm'): inputs['H'] = joint.CandidateBlock(raw.candidate_ids, x)
            with self.subTest(mode=mode), self.assertRaises(ValueError): joint.compose_blocks(r, transform, inputs)

    def test_transform_and_joint_pair_schema_rejections(self):
        transform = self.transform(); blocks = {bid: joint.compose_blocks(raw, transform, self.progress[bid])['H'] for bid, raw in self.raw.items()}
        for fields in (dict(numeric_scale=np.ones(4)), dict(numeric_scale=np.array([1., 0., 1.])),
                dict(numeric_scale=np.array([1., np.inf, 1.])), dict(y=transform.y.astype(bool)),
                dict(weights=np.full(len(transform.y), 1.)), dict(row_keys=tuple(reversed(transform.row_keys))),
                dict(_training_json=json.dumps(dict(transform.training, fixed_base_coefficient=1.)))):
            with self.subTest(fields=tuple(fields)), self.assertRaises(ValueError): replace(transform, **fields)
        for value in ({'b0': blocks['b0']}, dict(blocks, extra=blocks['b0'])):
            with self.assertRaises(ValueError): joint.mirrored_pairs(transform, value)
        block = blocks['b0']
        with self.assertRaises(ValueError): replace(block, matrix=sparse.csr_matrix(np.zeros((3, 4099))))
        with self.assertRaises(ValueError): replace(block, progress=block.progress*2.)

    def test_pure_pipeline_has_no_files_optimizer_or_source_execution(self):
        with (patch('builtins.open', side_effect=AssertionError('no I/O')),
              patch.object(Path, 'read_bytes', side_effect=AssertionError('no empirical input')),
              patch.object(structural.LogisticRegression, 'fit', side_effect=AssertionError('no optimizer'))):
            raw = {ex.bank_id: joint.raw_current(ex, self.banks[ex.bank_id]) for ex in self.examples}
            transform = joint.fit_own_scaler(self.examples, self.banks, raw, self.labels)
            blocks = {bid: joint.compose_blocks(value, transform, self.progress[bid])['H'] for bid, value in raw.items()}
            result = joint.mirrored_pairs(transform, blocks)
        self.assertEqual(result[0].shape[1], 4131)
        self.assertFalse(joint.configuration()['learned_base_input'])
        self.assertIsNone(joint.configuration()['pair_norm_upper_bound'])


if __name__ == '__main__': unittest.main()
