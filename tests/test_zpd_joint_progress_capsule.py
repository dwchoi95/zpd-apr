"""Synthetic joint capsule boundary tests; no empirical I/O or fitting."""
import copy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import zpd_joint_progress_capsule as capsule
from tests.test_zpd_repair_progress_capsule import fixture as prior_fixture


def fixture(n=10, *, fold=0, synthetic=True):
    """Use only synthetic source/bank objects, never fit/load a parent model."""
    old = prior_fixture(n, fold=fold, synthetic=synthetic)
    return capsule.FoldInputs(old.fold, old.examples, old.banks, old.assignment,
        {ex.bank_id: capsule.features.raw_current(ex, old.banks[ex.bank_id]) for ex in old.examples},
        old.interactions, old.parent_predictions, old.parent_training, old.parent_structure_model_sha256,
        old.fold_assignment_sha256, old.readiness_complete_sha256, old.synthetic)


class JointCapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()
        cls.body = capsule.encode_inputs(cls.inputs)

    def test_roundtrip_pure_source_replay_and_separate_exact_signed_zero32(self):
        original = self.inputs
        with patch('builtins.open', side_effect=AssertionError('no I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no bodies')), \
             patch.object(capsule.features, 'fit_own_scaler', side_effect=AssertionError('no scaler fit')), \
             patch.object(capsule.features.StandardScaler, 'fit', side_effect=AssertionError('no fitting')):
            rows = capsule.validate_inputs(original)
            value = capsule.encode_inputs(original)
            loaded = capsule.decode_inputs(json.loads(json.dumps(value, allow_nan=False)))
            self.assertEqual(capsule.fingerprint(original), capsule.fingerprint(loaded))
        self.assertEqual(len(rows), 10)
        self.assertEqual(value['configuration']['features']['dimension'], 4131)
        self.assertNotIn('base_scores', value)
        for a, b in zip(original.examples, loaded.examples, strict=True):
            self.assertEqual(a, b)
            self.assertEqual(len(b.observation.prior), 2)
            self.assertEqual(len(b.donor_history), 2)
            self.assertIn(b'\xce\xb1\t\n\n', b.observation.prior[0].source)
        for bid, block in original.raw_current.items():
            for key in ('numeric', 'hashed'):
                matrix = getattr(loaded.raw_current[bid], key)
                self.assertEqual(capsule._encode_csr(getattr(block, key)), capsule._encode_csr(matrix))
                for array in (matrix.data, matrix.indices, matrix.indptr):
                    with self.assertRaises(ValueError): array.flags.writeable = True
        for arm in capsule.ARMS:
            for bid, block in original.interactions[arm].items():
                x = loaded.interactions[arm][bid].matrix
                self.assertEqual(block.matrix.tobytes(), x.tobytes())
                self.assertTrue(np.signbit(x[0, 5]))
                with self.assertRaises(ValueError): x.flags.writeable = True
        with self.assertRaises(FrozenInstanceError): loaded.fold = 1

    def test_full_production_membership_and_all_five_own_held_projections(self):
        full = fixture(320, synthetic=False)
        rows = capsule.validate_inputs(full)
        self.assertEqual((len(rows), len({r['problem_id'] for r in rows}), sum(len(r['candidate_ids']) for r in rows)),
            (320, 23, 2544))
        self.assertEqual(len(capsule.decode_inputs(capsule.encode_inputs(full)).examples), 320)
        seen = []
        for fold in range(5):
            part = fixture(fold=fold)
            capsule.validate_inputs(part)
            train, held = capsule.scope(part)
            self.assertEqual([r['example_id'] for r in part.parent_predictions], [ex.example_id for ex in held])
            self.assertEqual(part.parent_training['informative_train_example_ids'], [ex.example_id for ex in train])
            seen.extend(ex.example_id for ex in held)
        self.assertEqual(sorted(seen), sorted(ex.example_id for ex in self.inputs.examples))
        for bad in (replace(self.inputs, synthetic=False), replace(self.inputs, synthetic=1), replace(self.inputs, fold=True)):
            with self.assertRaises(ValueError): capsule.validate_inputs(bad)

    def test_no_global_sibling_models_scaler_labels_or_base_offsets_in_schema(self):
        for where, key in (('top', 'base_scores'), ('top', 'parent_folds'), ('top', 'coefficients'),
                ('top', 'label_contracts'), ('top', 'runtime'), ('top', 'numeric_scale'), ('top', 'weights'),
                ('training', 'other_fold'), ('training', 'labels_sha256'), ('raw', 'scaler'),
                ('prediction', 'training'), ('prediction', 'parent_model'), ('scores', 'progress_H'),
                ('choices', 'shared_H_CF')):
            body = copy.deepcopy(type(self).body)
            target = {'top': body, 'training': body['parent_training'],
                'raw': next(iter(body['raw_current'].values())), 'prediction': body['parent_predictions'][0],
                'scores': body['parent_predictions'][0]['candidate_scores'],
                'choices': body['parent_predictions'][0]['choices']}[where]
            target[key] = {'foreign_fold_sha256': 'e' * 64}
            with self.subTest(where=where, key=key), self.assertRaises(ValueError): capsule.decode_inputs(body)
        text = json.dumps(type(self).body)
        for prohibited in ('"base_scores"', '"label_contracts"', '"numeric_scale"', '"parent_folds"', '"coefficients"'):
            self.assertNotIn(prohibited, text)

    def test_raw_source_parity_rejects_scaling_hash_change_identity_and_order(self):
        for mode in ('numeric', 'hashed', 'order', 'seal', 'bank', 'extra', 'missing'):
            inputs = copy.deepcopy(self.inputs)
            bid = inputs.examples[0].bank_id
            block = inputs.raw_current[bid]
            if mode in ('numeric', 'hashed'):
                x = getattr(block, mode).copy(); x.data = x.data.copy(); x.data[0] += .01
                inputs.raw_current[bid] = replace(block, **{mode: x})
            elif mode == 'order': inputs.raw_current[bid] = replace(block, candidate_ids=tuple(reversed(block.candidate_ids)))
            elif mode == 'seal': inputs.raw_current[bid] = replace(block, bank_seal_sha256='e' * 64)
            elif mode == 'bank': inputs.raw_current[bid] = replace(block, bank_id='foreign')
            elif mode == 'extra': inputs.raw_current['foreign'] = block
            else: inputs.raw_current.pop(bid)
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule.validate_inputs(inputs)

    def test_strict_csr_wire_preserves_explicit_zero_and_signed_zero_without_coercion(self):
        values = np.array([0., -0., 1., -2.], dtype=np.float64)
        x = sparse.csr_matrix((values, np.array([0, 2, 1, 2]), np.array([0, 2, 4])), shape=(2, 3))
        wire = capsule._encode_csr(x)
        self.assertEqual(wire['index_dtype'], '<i8')
        self.assertEqual(len(bytes.fromhex(wire['indices_hex'])), 32)
        restored = capsule._decode_csr(wire, 2, 3)
        self.assertEqual(wire, capsule._encode_csr(restored))
        self.assertEqual(restored.data.tobytes(), values.tobytes())
        self.assertEqual(restored.nnz, 4)
        empty = sparse.csr_matrix((2, 4096), dtype=np.float64)
        self.assertEqual(capsule._encode_csr(empty), capsule._encode_csr(
            capsule._decode_csr(capsule._encode_csr(empty), 2, 4096)))
        # A codec roundtrip alone is not raw feature authenticity.
        body = copy.deepcopy(type(self).body)
        row = next(iter(body['raw_current'].values()))
        raw = row['numeric']; data = np.frombuffer(bytes.fromhex(raw['data_hex']), dtype='<f8').copy()
        data[0] += 1.; raw['data_hex'] = data.tobytes().hex()
        with self.assertRaisesRegex(ValueError, 'source replay'): capsule.decode_inputs(body)

    def test_malformed_csr_wire_ranges_noncanonical_indices_and_nonfinite(self):
        base = capsule._encode_csr(sparse.csr_matrix(np.array([[1., 2., 0.], [0., 3., 0.]], dtype=np.float64)))
        for mode in ('dtype', 'index_dtype', 'bool_shape', 'width', 'truncated', 'trailing', 'negative',
                'out_of_range', 'duplicate', 'unsorted', 'terminal', 'descending', 'nonfinite', 'extra', 'hex_space'):
            body = copy.deepcopy(base)
            if mode == 'dtype': body['data_dtype'] = '<f4'
            elif mode == 'index_dtype': body['index_dtype'] = '<i4'
            elif mode == 'bool_shape': body['shape'][0] = True
            elif mode == 'width': body['shape'][1] = 4
            elif mode == 'truncated': body['indices_hex'] = body['indices_hex'][:-2]
            elif mode == 'trailing': body['data_hex'] += '00' * 8
            elif mode in ('negative', 'out_of_range', 'duplicate', 'unsorted'):
                values = np.frombuffer(bytes.fromhex(body['indices_hex']), dtype='<i8').copy()
                if mode == 'negative': values[0] = -1
                elif mode == 'out_of_range': values[0] = 3
                elif mode == 'duplicate': values[1] = values[0]
                else: values[:2] = [1, 0]
                body['indices_hex'] = values.tobytes().hex()
            elif mode in ('terminal', 'descending'):
                values = np.frombuffer(bytes.fromhex(body['indptr_hex']), dtype='<i8').copy()
                if mode == 'terminal': values[-1] -= 1
                else: values[1] = 4
                body['indptr_hex'] = values.tobytes().hex()
            elif mode == 'nonfinite': body['data_hex'] = np.array([np.nan, 2., 3.], dtype='<f8').tobytes().hex()
            elif mode == 'extra': body['format_alias'] = 'csr'
            else: body['data_hex'] = ' ' + body['data_hex']
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule._decode_csr(body, 2, 3)

    def test_in_memory_malformed_csr_rejected_before_scipy_can_coerce(self):
        for mode in ('coo', 'float32', 'float_indices', 'bool_indptr', 'duplicate', 'trailing'):
            inputs = copy.deepcopy(self.inputs)
            bid = inputs.examples[0].bank_id; block = inputs.raw_current[bid]
            x = block.hashed.copy()
            if mode == 'coo': x = x.tocoo()
            elif mode == 'float32': x = x.astype(np.float32)
            elif mode == 'float_indices': x.indices = x.indices.astype(np.float64)
            elif mode == 'bool_indptr': x.indptr = x.indptr.astype(bool)
            elif mode == 'duplicate': x.indices[1] = x.indices[0]
            else: x.data = np.append(x.data, 0.)
            object.__setattr__(block, 'hashed', x)
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule.validate_inputs(inputs)

    def test_parent_scope_accounting_ties_and_no_foreign_hashes(self):
        for mode in ('held_in_training', 'training_bool', 'mass', 'foreign_prediction', 'reverse',
                'score_bool', 'candidate', 'noop', 'tie'):
            body = copy.deepcopy(type(self).body)
            p = body['parent_predictions'][0]
            if mode == 'held_in_training': body['parent_training']['pair_example_ids'][0] = p['example_id']
            elif mode == 'training_bool': body['parent_training']['train_users'] = True
            elif mode == 'mass': body['parent_training']['sample_weight_sum'] = 1899.
            elif mode == 'foreign_prediction': p['example_id'] = capsule.scope(self.inputs)[0][0].example_id
            elif mode == 'reverse': body['parent_predictions'].reverse()
            elif mode == 'score_bool': p['candidate_scores']['structural_C'][next(iter(p['candidate_scores']['structural_C']))] = True
            elif mode == 'candidate': p['candidate_scores']['structural_C']['e' * 64] = 0.
            elif mode == 'noop': p['choices']['noop'] = p['choices']['first_attempt']
            else:
                scores = p['candidate_scores']['structural_C']
                p['candidate_scores']['structural_C'] = dict.fromkeys(scores, 0.)
                p['choices']['structural_C'] = max(scores)
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule.decode_inputs(body)
        body = copy.deepcopy(type(self).body)
        for p in body['parent_predictions']:
            for name in capsule.BASELINES:
                p['candidate_scores'][name] = dict.fromkeys(p['candidate_scores'][name], 0.)
                p['choices'][name] = min(p['candidate_scores'][name])
        capsule.decode_inputs(body)

    def test_progress_tail_noop_common_block_bounds_and_strict_schema(self):
        for mode in ('width', 'noop', 'shared', 'tail', 'bound', 'nan', 'order', 'extra_arm', 'dtype'):
            body = copy.deepcopy(type(self).body); bid = self.inputs.examples[0].bank_id
            row = body['interactions']['CF' if mode == 'tail' else 'H'][bid]
            x = np.frombuffer(bytes.fromhex(row['data_hex']), dtype='<f8').reshape(row['shape']).copy()
            if mode == 'width': row['shape'][1] = 31
            elif mode == 'order': row['candidate_ids'].reverse()
            elif mode == 'extra_arm': body['interactions']['C_joint'] = body['interactions']['CF']
            elif mode == 'dtype': row['dtype'] = 'float64'
            else:
                if mode == 'noop': x[0, 16] = .01
                elif mode == 'shared': x[1, 0] += .01
                elif mode == 'tail': x[1, 16] = .01
                elif mode == 'bound': x[1, 16] = 1.
                else: x[1, 16] = np.nan
                row['data_hex'] = x.tobytes().hex()
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule.decode_inputs(body)

    def test_exact_source_no_normalization_and_no_history_cap(self):
        inputs = copy.deepcopy(self.inputs)
        ex = inputs.examples[0]
        # Arbitrary invalid encoding bytes remain bytes; raw current uses only C.
        source = ex.observation.prior[0]
        code = b'\xff\x00\r\n\t  # exact bytes\n\n'
        changed = replace(source, source=code, source_sha256=capsule.source_hash(code))
        ex.observation = replace(ex.observation, prior=(changed, *ex.observation.prior[1:]))
        loaded = capsule.decode_inputs(capsule.encode_inputs(inputs))
        self.assertEqual(loaded.examples[0].observation.prior[0].source, code)
        prior = tuple(replace(changed, submission_id=f'{ex.observation.problem_id}:long{i}', timestamp=-1200+i)
            for i in range(1100))
        donor = tuple(replace(changed, submission_id=f'{ex.observation.problem_id}:donorlong{i}', timestamp=-1300+i)
            for i in range(1100))
        ex.observation = replace(ex.observation, prior=prior); ex.donor_history = donor
        loaded = capsule.decode_inputs(capsule.encode_inputs(inputs))
        self.assertEqual((len(loaded.examples[0].observation.prior), len(loaded.examples[0].donor_history)), (1100, 1100))

    def test_arbitrary_current_candidate_bytes_and_failed_attempt_roundtrip(self):
        inputs = copy.deepcopy(self.inputs)
        ex = inputs.examples[0]; old_bank = inputs.banks[ex.bank_id]
        current_code = b'# coding: impossible-encoding\r\n\xff\x00\t\n'
        candidate_code = b'\xff\xfe\x00# candidate\r\n\t\n\n'
        current = replace(ex.observation.current, source=current_code, source_sha256=capsule.source_hash(current_code))
        ex.observation = replace(ex.observation, current=current)
        attempts = (replace(old_bank.attempts[0], source=candidate_code), *old_bank.attempts[1:-1],
            replace(old_bank.attempts[-1], status='format_failure', source=None, error='synthetic unavailable'))
        bank = replace(old_bank, current_source=current_code, attempts=attempts)
        # Last original attempt was a duplicate, so the complete bank cardinality is unchanged.
        old_ids = tuple(c.candidate_id for c in old_bank.candidates)
        new_ids = tuple(c.candidate_id for c in bank.candidates)
        self.assertEqual(len(old_ids), len(new_ids))
        mapped = dict(zip(old_ids, new_ids, strict=True))
        inputs.banks[ex.bank_id] = bank
        inputs.raw_current[ex.bank_id] = capsule.features.raw_current(ex, bank)
        for arm in capsule.ARMS:
            block = inputs.interactions[arm][ex.bank_id]
            inputs.interactions[arm][ex.bank_id] = capsule.CandidateBlock(new_ids, block.matrix)
        for prediction in inputs.parent_predictions:
            if prediction['example_id'] != ex.example_id: continue
            prediction['bank_seal_sha256'] = bank.seal_sha256
            prediction['choices'] = {key: mapped[cid] for key, cid in prediction['choices'].items()}
            prediction['candidate_scores'] = {name: {mapped[cid]: value for cid, value in scores.items()}
                for name, scores in prediction['candidate_scores'].items()}
        loaded = capsule.decode_inputs(capsule.encode_inputs(inputs))
        self.assertEqual(loaded.examples[0].observation.current.source, current_code)
        self.assertEqual(loaded.banks[ex.bank_id].attempts[0].source, candidate_code)
        self.assertEqual(loaded.banks[ex.bank_id].attempts[-1].status, 'format_failure')
        self.assertIsNone(loaded.banks[ex.bank_id].attempts[-1].source)

    def test_reject_mutated_source_identity_chronology_assignment_and_configuration(self):
        for mode in ('source_sha', 'current_id', 'time', 'donor', 'fold', 'user', 'extra_source', 'configuration', 'missing_bank'):
            body = copy.deepcopy(type(self).body); ex = body['examples'][0]
            if mode == 'source_sha': ex['observation']['prior'][0]['source_sha256'] = '0' * 64
            elif mode == 'current_id': ex['observation']['current']['submission_id'] = 'wrong'
            elif mode == 'time': ex['observation']['prior'][0]['timestamp'] = 100
            elif mode == 'donor': ex['donor_history'].pop()
            elif mode == 'fold': body['assignment']['fold_sizes'][0] += 1
            elif mode == 'user': ex['user_id'] = body['examples'][1]['user_id']
            elif mode == 'extra_source': ex['observation']['current']['future_target'] = 'forbidden'
            elif mode == 'configuration': body['configuration']['features']['whole_vector_normalization'] = 0
            else: body['banks'].pop(ex['bank_id'])
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule.decode_inputs(body)

    def test_detached_mutable_caller_data_and_fingerprint_is_not_authority(self):
        body = capsule.encode_inputs(self.inputs)
        loaded = capsule.decode_inputs(body)
        before = capsule.fingerprint(loaded)
        body['assignment']['fold_sizes'][0] = 999
        body['parent_training']['sample_weight_sum'] = 0.
        body['raw_current'].clear(); body['interactions'].clear()
        self.assertEqual(before, capsule.fingerprint(loaded))
        # Allowed different supplied values change the hash; no self-authentication claim.
        changed = replace(loaded, readiness_complete_sha256='e' * 64)
        self.assertNotEqual(before, capsule.fingerprint(changed))
        changed = capsule.decode_inputs(capsule.encode_inputs(loaded))
        bid = changed.examples[0].bank_id; block = changed.interactions['H'][bid]
        values = block.matrix.copy(); values[1, 16] -= .001
        changed.interactions['H'][bid] = capsule.CandidateBlock(block.candidate_ids, values)
        values[1, 16] = 42.
        self.assertLess(changed.interactions['H'][bid].matrix[1, 16], 0.)
        self.assertNotEqual(before, capsule.fingerprint(changed))


if __name__ == '__main__': unittest.main()
