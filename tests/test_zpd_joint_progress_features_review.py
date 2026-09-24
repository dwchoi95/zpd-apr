"""Nonauthor synthetic witnesses for raw-current/progress32 composition."""
import copy
from dataclasses import replace
import unittest

import numpy as np

from scripts import zpd_joint_progress_features as joint
from scripts import zpd_repair_structure as previous
from tests.test_zpd_joint_progress_features import fixture


class JointFeatureReviewTests(unittest.TestCase):
    def test_uneven_user_prefixes_unknowns_and_ties_keep_original_current_pairs(self):
        rng = np.random.default_rng(20260925)
        for case in range(12):
            examples, banks, labels, raw, progress = fixture()
            originals = list(examples)
            for index in range(5):
                old = originals[index % 2]
                ex = replace(old, example_id=f'e-extra-{index}', bank_id=f'b-extra-{index}',
                    user_id=f'u{index % 3}')
                examples.append(ex); banks[ex.bank_id] = banks[old.bank_id]
                raw[ex.bank_id] = joint.raw_current(ex, banks[ex.bank_id])
                progress[ex.bank_id] = progress[old.bank_id]
                for cid in raw[ex.bank_id].candidate_ids:
                    row = dict(labels[old.bank_id, cid], bank_id=ex.bank_id)
                    status = int(rng.integers(0, 4))
                    if status == 0:
                        row.update(status='unknown', all_ac=None, gain=None, loss=None)
                    else:
                        row.update(status='stable', all_ac=status == 3,
                            gain=.5 if status == 3 else 0., loss=.25 if status == 1 else 0.)
                        if next(c for c in banks[ex.bank_id].candidates if c.candidate_id == cid).is_noop:
                            row.update(gain=0., loss=0.)
                    labels[ex.bank_id, cid] = row
            transform = joint.fit_own_scaler(examples, banks, raw, labels)
            blocks = {bid: joint.compose_blocks(value, transform, progress[bid])['H']
                for bid, value in raw.items()}
            matrix, y, weights, info = joint.mirrored_pairs(transform, blocks)
            old_x, old_y, old_weights, old_scale, old_info = previous.training_data(
                examples, banks, labels, 'C', 'structural')
            with self.subTest(case=case):
                np.testing.assert_array_equal(matrix[:, :4099].toarray(), old_x.toarray())
                self.assertEqual(y.tobytes(), old_y.tobytes())
                self.assertEqual(weights.tobytes(), old_weights.tobytes())
                self.assertEqual(transform.numeric_scale.tobytes(), old_scale.tobytes())
                self.assertEqual(info, old_info)
                for row, (bid, left, right) in enumerate(transform.row_keys):
                    block = progress[bid]['H']
                    a, b = block.candidate_ids.index(left), block.candidate_ids.index(right)
                    np.testing.assert_array_equal(matrix[row, 4099:].toarray()[0], block.matrix[a]-block.matrix[b])

    def test_foreign_label_values_are_not_read_and_caller_objects_are_not_changed(self):
        examples, banks, labels, raw, progress = fixture()
        class Forbidden(dict):
            def get(self, *args, **kwargs):
                raise AssertionError('foreign label read')
        extra = dict(labels); extra['foreign', 'candidate'] = Forbidden()
        with self.assertRaisesRegex(ValueError, 'labels must have exactly'):
            joint.fit_own_scaler(examples, banks, raw, extra)
        before = copy.deepcopy(labels)
        source_bytes = {bid: (value.numeric.data.tobytes(), value.hashed.data.tobytes()) for bid, value in raw.items()}
        accepted_bytes = {(bid, arm): block.matrix.tobytes() for bid, arms in progress.items() for arm, block in arms.items()}
        transform = joint.fit_own_scaler(examples, banks, raw, labels)
        for bid, value in raw.items():
            blocks = joint.compose_blocks(value, transform, progress[bid])
            self.assertEqual(source_bytes[bid], (value.numeric.data.tobytes(), value.hashed.data.tobytes()))
            for arm in joint.PROGRESS_ARMS:
                self.assertEqual(blocks[arm].progress.tobytes(), accepted_bytes[bid, arm])
                self.assertEqual(progress[bid][arm].matrix.tobytes(), accepted_bytes[bid, arm])
        self.assertEqual(labels, before)

    def test_shared_current_zero_subspaces_and_no_extra_pair_rescaling(self):
        examples, banks, labels, raw, progress = fixture()
        transform = joint.fit_own_scaler(examples, banks, raw, labels)
        all_blocks = {bid: joint.compose_blocks(value, transform, progress[bid]) for bid, value in raw.items()}
        pairs = {arm: joint.mirrored_pairs(transform, {bid: blocks[arm] for bid, blocks in all_blocks.items()})[0]
            for arm in joint.ARMS}
        for arm, matrix in pairs.items():
            np.testing.assert_array_equal(matrix[:, :4099].toarray(), pairs['C_joint'][:, :4099].toarray())
            self.assertFalse((matrix[::2]+matrix[1::2]).nnz)
            if arm != 'C_joint':
                np.testing.assert_array_equal(matrix[:, 4099:4115].toarray(), pairs['H'][:, 4099:4115].toarray())
        self.assertFalse(pairs['C_joint'][:, 4099:].nnz)
        self.assertFalse(pairs['CF'][:, 4115:].nnz)
        self.assertGreater(float(np.max(pairs['H'].multiply(pairs['H']).sum(axis=1))), 1.)


if __name__ == '__main__':
    unittest.main()
