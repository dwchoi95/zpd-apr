"""Independent, source-only capsule witnesses; no files, labels or fitting."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_repair_structure as frozen_structural
from tests.test_zpd_joint_progress_capsule import fixture


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


class IndependentJointCapsuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = fixture()

    def test_five_full_population_roundtrips_independent_hash_source_and_matrix_bytes(self):
        all_held = []; source_memberships = progress_rows = 0
        for fold in range(5):
            supplied = fixture(320, fold=fold, synthetic=False)
            body = capsule.encode_inputs(supplied)
            wire = canonical_bytes(body)
            decoded = capsule.decode_inputs(json.loads(wire))
            self.assertEqual(wire, canonical_bytes(capsule.encode_inputs(decoded)))
            self.assertEqual(hashlib.sha256(wire).hexdigest(), capsule.fingerprint(supplied))
            self.assertEqual(capsule.fingerprint(supplied), capsule.fingerprint(decoded))
            self.assertEqual(len(decoded.examples), 320)
            self.assertEqual(len({ex.observation.problem_id for ex in decoded.examples}), 23)
            self.assertEqual(sum(len(bank.candidates) for bank in decoded.banks.values()), 2544)
            train = [ex for ex in decoded.examples if decoded.assignment['example_fold'][ex.example_id] != fold]
            held = [ex for ex in decoded.examples if decoded.assignment['example_fold'][ex.example_id] == fold]
            self.assertFalse({ex.observation.problem_id for ex in train} & {ex.observation.problem_id for ex in held})
            self.assertEqual([ex.example_id for ex in held], [row['example_id'] for row in decoded.parent_predictions])
            all_held.extend(ex.example_id for ex in held)
            self.assertEqual(set(decoded.parent_training['informative_train_example_ids']) |
                set(decoded.parent_training['uninformative_train_example_ids']), {ex.example_id for ex in train})
            for before, after in zip(supplied.examples, decoded.examples, strict=True):
                for a, b in zip((*before.observation.prior, before.observation.current, *before.donor_history),
                                (*after.observation.prior, after.observation.current, *after.donor_history), strict=True):
                    source_memberships += 1
                    self.assertEqual(vars(a), vars(b)); self.assertEqual(hashlib.sha256(b.source).hexdigest(), b.source_sha256)
                bank = decoded.banks[after.bank_id]
                # Frozen raw representation direct call, not the new raw_current wrapper.
                numeric, hashed = frozen_structural.raw_features(after.observation, (), bank, 'C', 'structural')
                for key, independently_computed in (('numeric', numeric), ('hashed', hashed)):
                    saved = body['raw_current'][after.bank_id][key]
                    raw = getattr(decoded.raw_current[after.bank_id], key)
                    for field, dtype in (('data', '<f8'), ('indices', '<i8'), ('indptr', '<i8')):
                        expected = getattr(independently_computed, field).astype(dtype).tobytes()
                        self.assertEqual(bytes.fromhex(saved[field+'_hex']), expected)
                        self.assertEqual(getattr(raw, field).astype(dtype).tobytes(), expected)
                for arm in ('H', 'Jm', 'HS', 'U', 'L', 'CF'):
                    old = supplied.interactions[arm][after.bank_id]
                    new = decoded.interactions[arm][after.bank_id]
                    progress_rows += len(new.candidate_ids)
                    self.assertEqual(old.matrix.tobytes(), new.matrix.tobytes())
                    self.assertEqual(bytes.fromhex(body['interactions'][arm][after.bank_id]['data_hex']), new.matrix.tobytes())
                    self.assertEqual(old.candidate_ids, new.candidate_ids)
        self.assertEqual(len(all_held), 320); self.assertEqual(len(set(all_held)), 320)
        self.assertEqual(source_memberships, 8000)
        self.assertEqual(progress_rows, 76320)

    def test_direct_dataclass_extra_payload_cannot_be_hidden_behind_exact_wire_schema(self):
        def select(inputs, name):
            ex = inputs.examples[0]; bank = inputs.banks[ex.bank_id]
            return {'capsule': inputs, 'example': ex, 'observation': ex.observation,
                'current': ex.observation.current, 'prior': ex.observation.prior[0],
                'donor': ex.donor_history[0], 'bank': bank, 'attempt': bank.attempts[0],
                'raw_current': inputs.raw_current[ex.bank_id],
                'progress': inputs.interactions['H'][ex.bank_id]}[name]
        for name in ('capsule', 'example', 'observation', 'current', 'prior', 'donor', 'bank', 'attempt', 'raw_current', 'progress'):
            value = copy.deepcopy(self.inputs)
            object.__setattr__(select(value, name), 'sibling_label_hash', 'f'*64)
            with self.subTest(object=name), self.assertRaisesRegex(ValueError, 'extra payload'):
                capsule.validate_inputs(value)

    def test_semantically_equal_but_different_raw_csr_wire_is_rejected(self):
        value = copy.deepcopy(self.inputs); bid = value.examples[0].bank_id
        original = value.raw_current[bid]; matrix = original.hashed
        occupied = set(matrix.indices[matrix.indptr[0]:matrix.indptr[1]])
        missing = next(column for column in range(4096) if column not in occupied)
        data = np.insert(matrix.data, 0, -0.)
        indices = np.insert(matrix.indices, 0, missing)
        pointer = matrix.indptr.copy(); pointer[1:] += 1
        changed = sparse.csr_matrix((data, indices, pointer), shape=matrix.shape)
        changed.sort_indices()
        np.testing.assert_array_equal(matrix.toarray(), changed.toarray())
        self.assertEqual(changed.nnz, matrix.nnz+1)
        value.raw_current[bid] = replace(original, hashed=changed)
        with self.assertRaisesRegex(ValueError, 'source replay'): capsule.validate_inputs(value)

    def test_boundaries_do_not_fit_read_files_execute_source_or_open_label_provider(self):
        from scripts import zpd_repair_feedback_labels as labels
        with patch('builtins.open', side_effect=AssertionError('file access forbidden')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('body access forbidden')), \
             patch.object(capsule.features, 'fit_own_scaler', side_effect=AssertionError('scaler fitting forbidden')), \
             patch.object(capsule.features.StandardScaler, 'fit', side_effect=AssertionError('model fitting forbidden')), \
             patch.object(labels, 'load_fold_labels', side_effect=AssertionError('label access forbidden')), \
             patch('subprocess.run', side_effect=AssertionError('execution forbidden')), \
             patch('subprocess.Popen', side_effect=AssertionError('execution forbidden')):
            body = capsule.encode_inputs(self.inputs)
            restored = capsule.decode_inputs(body)
            self.assertEqual(capsule.fingerprint(restored), capsule.fingerprint(self.inputs))

    def test_parent_training_and_held_projection_scope_reject_sibling_or_global_payloads(self):
        for name in ('global_label_contracts', 'base_scores', 'sibling_model_sha256', 'scaler', 'all_fold_models'):
            body = capsule.encode_inputs(self.inputs); body[name] = {'foreign': 'e'*64}
            with self.subTest(name=name), self.assertRaises(ValueError): capsule.decode_inputs(body)
        train, held = capsule.scope(self.inputs)
        for mode in ('held_training_member', 'train_prediction', 'other_fold_prediction', 'prediction_model', 'training_label_hash'):
            body = capsule.encode_inputs(self.inputs)
            if mode == 'held_training_member': body['parent_training']['pair_example_ids'][0] = held[0].example_id
            elif mode == 'train_prediction': body['parent_predictions'][0]['example_id'] = train[0].example_id
            elif mode == 'other_fold_prediction': body['parent_predictions'][0]['fold'] = 1
            elif mode == 'prediction_model': body['parent_predictions'][0]['coefficients'] = [0.]*4099
            else: body['parent_training']['own_label_sha256'] = 'e'*64
            with self.subTest(mode=mode), self.assertRaises(ValueError): capsule.decode_inputs(body)

    def test_all_history_positions_and_exact_unparseable_bytes_preserved(self):
        value = copy.deepcopy(self.inputs); ex = value.examples[0]
        source = ex.observation.prior[0]; payload = b'\xff\x00\r\n\t# preserved\n\n'
        prior = tuple(replace(source, submission_id=f'auth-{i}', timestamp=-3000+i,
            source=payload, source_sha256=hashlib.sha256(payload).hexdigest()) for i in range(1500))
        donor = tuple(replace(source, submission_id=f'donor-{i}', timestamp=-4000+i) for i in range(1500))
        ex.observation = replace(ex.observation, prior=prior); ex.donor_history = donor
        restored = capsule.decode_inputs(capsule.encode_inputs(value)).examples[0]
        self.assertEqual(restored.observation.prior, prior); self.assertEqual(restored.donor_history, donor)
        self.assertEqual(len(restored.observation.prior), 1500)
        self.assertEqual(restored.observation.prior[0].source, payload)
        for malformed in ('future', 'duplicate', 'out_of_order'):
            body = capsule.encode_inputs(self.inputs); history = body['examples'][0]['observation']['prior']
            if malformed == 'future': history[0]['timestamp'] = body['examples'][0]['observation']['current']['timestamp']+1
            elif malformed == 'duplicate': history[1]['submission_id'] = history[0]['submission_id']
            else: history.reverse()
            with self.subTest(malformed=malformed), self.assertRaises(ValueError): capsule.decode_inputs(body)

    def test_accepted_vector_authenticity_is_external_not_claimed_by_fingerprint(self):
        body = capsule.encode_inputs(self.inputs); before = hashlib.sha256(canonical_bytes(body)).hexdigest()
        bid = self.inputs.examples[0].bank_id; row = body['interactions']['H'][bid]
        data = np.frombuffer(bytes.fromhex(row['data_hex']), dtype='<f8').reshape(row['shape']).copy()
        data[1, 16] -= .0001; row['data_hex'] = data.tobytes().hex()
        changed = capsule.decode_inputs(body)
        self.assertNotEqual(before, capsule.fingerprint(changed))
        # Likewise an opaque identity is not self-authentication of a parent.
        other = replace(changed, parent_structure_model_sha256='e'*64)
        self.assertNotEqual(capsule.fingerprint(changed), capsule.fingerprint(other))

    def test_signed_zero_wire_bits_survive_and_caller_mutation_does_not_alias_decode(self):
        body = capsule.encode_inputs(self.inputs); loaded = capsule.decode_inputs(body)
        bid = loaded.examples[0].bank_id
        for arm in capsule.ARMS:
            matrix = loaded.interactions[arm][bid].matrix
            self.assertTrue(np.signbit(matrix[0, 5]))
            self.assertEqual(matrix.astype('<f8').tobytes(), bytes.fromhex(body['interactions'][arm][bid]['data_hex']))
        old = capsule.fingerprint(loaded)
        body['examples'][0]['observation']['prior'].clear()
        body['raw_current'][bid]['numeric']['data_hex'] = ''
        body['interactions']['H'][bid]['data_hex'] = ''
        self.assertEqual(capsule.fingerprint(loaded), old)


if __name__ == '__main__': unittest.main()
