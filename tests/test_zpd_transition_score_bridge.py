"""Synthetic projection/export/prediction tests; no labels, fitting or execution."""
import copy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse
from sklearn.preprocessing import StandardScaler

from scripts import zpd_repair_structure as structural
from scripts import zpd_transition_score_bridge as bridge
from scripts.zpd_repair_fit import Example
from src.repair.pilot_contracts import (
    CandidateAttempt, CandidateBank, ObservationSource, PilotObservation,
    canonical_hash, source_hash)


def reseal(value, key='projection_sha256'):
    value[key] = canonical_hash({k: v for k, v in value.items() if k != key})
    return value


def projection():
    folds = []
    for fold in range(5):
        folds.append(dict(fold=fold, numeric_scale=[2., 3., 4.],
            theta=[float((j % 7) - 3) / (fold + 2) for j in range(4099)],
            held_example_ids=[f'ex-{i}' for i in range(fold * 64, (fold + 1) * 64)],
            **{k: 'a' * 64 for k in bridge.FOLD_FIELDS if k.endswith('sha256')}))
    return reseal(dict(kind=bridge.VERSION, arm='C_joint',
        archive_complete_sha256=bridge.COMPLETE_SHA256,
        numeric_names=list(bridge.features.NUMERIC_NAMES), numeric_dimension=3,
        hash_dimension=4096, current_dimension=4099, offset=False, intercept=False,
        folds=folds, example_folds={eid: f['fold'] for f in folds for eid in f['held_example_ids']}))


def example_and_bank(index=0, candidate=b'print(2)\n'):
    current = b'print(1)\n'
    observed = ObservationSource(f's-{index}', 1., current, source_hash(current), 'UNUSED_SOURCE_ONLY')
    ex = Example(f'ex-{index}', f'user-{index}', 'valid', f'bank-{index}',
                 PilotObservation('synthetic', observed, ()), ())
    seeds = tuple(range(8))
    attempts = tuple(CandidateAttempt(i, i, 'success', candidate) for i in seeds)
    return ex, CandidateBank('synthetic', current, 'b' * 64, seeds, attempts)


def parity_fixture(value):
    examples = []; banks = {}; rows = []; scorer = bridge.FrozenScorer(value)
    for i in range(320):
        ex, bank = example_and_bank(i); examples.append(ex); banks[ex.bank_id] = bank
        scores = scorer.score_bank(ex, bank)
        rows.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
            bank_seal_sha256=bank.seal_sha256, fold=i // 64, problem_id=bank.problem_id,
            candidate_scores={'C_joint': scores}, choices={'C_joint': min(scores, key=lambda cid: (-scores[cid], cid))}))
    return examples, banks, rows


def archive_fixture(directory, *, nonzero_tail=False, offset=False):
    """Sealed synthetic archive with conspicuous pair data that must not decode."""
    directory = Path(directory); inventory = {}; value = projection()
    all_ids = list(value['example_folds'])
    for fold in value['folds']:
        number = fold['fold']; sub = directory / f'fold-{number}'; sub.mkdir()
        top = dict(coefficients=fold['theta'] + [1. if nonzero_tail else 0.] + [0.] * 31,
            final_gradient=[0.] * 4131, configuration=dict(dimension=4131,
                offset='present' if offset else 'absent', intercept='not_added'))
        reseal(top, 'model_sha256')
        model = dict(kind='bank_topset4131_own_fold_model_v1', arm='C_joint', fold=number,
            top_model=top, held_example_ids=fold['held_example_ids'],
            train_example_ids=[x for x in all_ids if x not in fold['held_example_ids']],
            transform_sha256='c' * 64)
        reseal(model, 'model_sha256')
        scaler = dict(kind='joint_current_own_training_transform_v1', numeric_scale=fold['numeric_scale'],
                      y=['DO_NOT_DECODE_PAIR_LABEL_SENTINEL'], training={'secret': 'DO_NOT_EXPORT'})
        for name, body in (('C_joint.json', model), ('SCALER.json', scaler)):
            raw = bridge.encoded(body); (sub / name).write_bytes(raw)
            inventory[f'fold-{number}/{name}'] = hashlib.sha256(raw).hexdigest()
    complete = dict(kind='bank_topset4131_complete_v1', status='complete', recipients=320,
                    completed_fits=35, files_sha256=inventory)
    raw = bridge.encoded(complete); (directory / 'COMPLETE.json').write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


class FrozenProjectionTests(unittest.TestCase):
    def test_strict_json_roundtrip_and_external_pin(self):
        p = projection(); clone = json.loads(bridge.encoded(p))
        self.assertEqual(bridge.validate_projection(clone, expected_sha256=p['projection_sha256']), p['projection_sha256'])
        with self.assertRaisesRegex(ValueError, 'external projection'):
            bridge.validate_projection(clone, expected_sha256='0' * 64)

    def test_no_labels_training_offsets_or_old_scores_in_projection(self):
        p = projection()
        for key in ('y', 'training', 'train_example_ids', 'candidate_scores', 'base_margin'):
            changed = copy.deepcopy(p); changed[key] = []; reseal(changed)
            with self.assertRaises(ValueError): bridge.validate_projection(changed)
            changed = copy.deepcopy(p); changed['folds'][0][key] = []; reseal(changed)
            with self.assertRaises(ValueError): bridge.validate_projection(changed)
        for key in ('offset', 'intercept'):
            changed = copy.deepcopy(p); changed[key] = 0.; reseal(changed)
            with self.assertRaises(ValueError): bridge.validate_projection(changed)

    def test_vector_types_dimensions_and_finiteness(self):
        for field, values in (('numeric_scale', [1., 0., 1.]), ('numeric_scale', [1., True, 1.]),
                ('numeric_scale', [1., 1.]), ('theta', [0.] * 4098), ('theta', ['0'] * 4099)):
            p = projection(); p['folds'][0][field] = values; reseal(p)
            with self.assertRaises(ValueError): bridge.validate_projection(p)
        for invalid in (float('nan'), float('inf'), True):
            with self.assertRaises(ValueError): bridge._vector([invalid] * 3, 3, 'test')

    def test_fold_mapping_cannot_duplicate_omit_reorder_or_add(self):
        for mutate in (
            lambda p: p['folds'][0]['held_example_ids'].append('ex-64'),
            lambda p: p['folds'][0]['held_example_ids'].pop(),
            lambda p: p['folds'].reverse(),
            lambda p: p['example_folds'].update({'new-example': 0}),
            lambda p: p['example_folds'].update({'ex-0': False}),
        ):
            p = projection(); mutate(p); reseal(p)
            with self.assertRaises(ValueError): bridge.validate_projection(p)

    def test_rehashed_content_requires_externally_pinned_projection(self):
        p = projection(); pin = p['projection_sha256']; p['folds'][0]['theta'][0] += 1; reseal(p)
        with self.assertRaises(ValueError): bridge.FrozenScorer(p, expected_sha256=pin)

    def test_export_authenticates_archive_and_decodes_no_pair_label_array(self):
        with tempfile.TemporaryDirectory() as directory:
            pin = archive_fixture(directory); original = json.loads; decoded = []
            def guarded(raw, *args, **kwargs):
                if isinstance(raw, (str, bytes)):
                    self.assertNotIn('DO_NOT_DECODE_PAIR_LABEL_SENTINEL', raw.decode() if isinstance(raw, bytes) else raw)
                result = original(raw, *args, **kwargs); decoded.append(result); return result
            with patch.object(bridge, 'COMPLETE_SHA256', pin), patch.object(bridge.json, 'loads', guarded):
                p = bridge.export_projection(directory)
                self.assertEqual(bridge.validate_projection(p), p['projection_sha256'])
            self.assertEqual(len(decoded), 11)  # COMPLETE + five (model, scale), no SCALER dict.
            serialized = bridge.encoded(p).decode()
            for marker in ('DO_NOT_EXPORT', 'DO_NOT_DECODE_PAIR_LABEL', '"y"', '"training"', '"train_example_ids"'):
                self.assertNotIn(marker, serialized)
            self.assertTrue(all(len(f['theta']) == 4099 and len(f['numeric_scale']) == 3 for f in p['folds']))

    def test_archive_tamper_rejected_even_with_valid_rehashed_model(self):
        with tempfile.TemporaryDirectory() as directory:
            pin = archive_fixture(directory); path = Path(directory) / 'fold-0/C_joint.json'
            model = json.loads(path.read_bytes()); model['top_model']['coefficients'][0] += 1
            reseal(model['top_model'], 'model_sha256'); reseal(model, 'model_sha256')
            path.write_bytes(bridge.encoded(model))
            with patch.object(bridge, 'COMPLETE_SHA256', pin), self.assertRaisesRegex(ValueError, 'file seal mismatch'):
                bridge.export_projection(directory)

    def test_nonzero_progress_tail_and_offset_fail_before_export(self):
        for options in ({'nonzero_tail': True}, {'offset': True}):
            with tempfile.TemporaryDirectory() as directory:
                pin = archive_fixture(directory, **options)
                with patch.object(bridge, 'COMPLETE_SHA256', pin), self.assertRaises(ValueError):
                    bridge.export_projection(directory)


class FrozenScoreTests(unittest.TestCase):
    def test_exact_raw_numeric_div_scale_and_normalized_hash_dot_no_offset(self):
        p = projection(); ex, bank = example_and_bank()
        numeric, hashed = structural.raw_features(ex.observation, (), bank, 'C', 'structural')
        expected = sparse.hstack([numeric.multiply(1 / np.array([2., 3., 4.])), hashed], format='csr') @ np.array(p['folds'][0]['theta'])
        scores = bridge.score_bank(p, ex, bank)
        np.testing.assert_array_equal(list(scores.values()), expected)
        self.assertEqual(list(scores), [c.candidate_id for c in bank.candidates])

    def test_new_candidate_bank_and_invalid_syntax_byte_fallback_are_recomputed(self):
        p = projection(); ex, old = example_and_bank(); _, new = example_and_bank(candidate=b'if (: \xff\x00\r\n')
        before = bridge.score_bank(p, ex, old); after = bridge.score_bank(p, ex, new)
        self.assertNotEqual(old.seal_sha256, new.seal_sha256)
        self.assertEqual(set(after), {c.candidate_id for c in new.candidates})
        noop = source_hash(new.current_source)
        self.assertEqual(before[noop], after[noop])
        self.assertNotEqual(set(before), set(after))

    def test_no_files_fits_labels_or_transform_object_during_scoring(self):
        scorer = bridge.FrozenScorer(projection()); ex, bank = example_and_bank()
        with (patch.object(Path, 'read_bytes', side_effect=AssertionError('file access')),
                patch.object(StandardScaler, 'fit', side_effect=AssertionError('fit')),
                patch.object(bridge.features, 'fit_own_scaler', side_effect=AssertionError('fit'))):
            self.assertEqual(len(scorer.score_bank(ex, bank)), 2)

    def test_scorer_copies_and_freezes_scales_coefficients_and_mapping(self):
        p = projection(); scorer = bridge.FrozenScorer(p); ex, bank = example_and_bank()
        before = scorer.score_bank(ex, bank)
        p['folds'][0]['theta'][0] += 200; p['folds'][0]['numeric_scale'][0] = .001
        p['example_folds'][ex.example_id] = 4
        self.assertEqual(before, scorer.score_bank(ex, bank))
        with self.assertRaises(TypeError): scorer.example_folds[ex.example_id] = 3
        with self.assertRaises(ValueError): scorer._folds[0][1][0] = 7.

    def test_history_nominal_verdict_and_bank_id_do_not_enter_c_features(self):
        p = projection(); ex, bank = example_and_bank(); original = bridge.score_bank(p, ex, bank)
        prior = ObservationSource('old', 0., b'print(9)', source_hash(b'print(9)'), 'CE')
        observation = PilotObservation(bank.problem_id, replace(ex.observation.current, verdict='CHANGED'), (prior,))
        altered = replace(ex, observation=observation, bank_id='new-generation-bank', donor_history=(prior,))
        self.assertEqual(original, bridge.score_bank(p, altered, bank))

    def test_oof_fold_is_recipient_bound_and_mismatched_sources_fail(self):
        p = projection(); ex, bank = example_and_bank()
        self.assertNotEqual(bridge.score_bank(p, ex, bank), bridge.score_bank(p, replace(ex, example_id='ex-64'), bank))
        with self.assertRaisesRegex(ValueError, 'held fold'): bridge.score_bank(p, replace(ex, example_id='unseen'), bank)
        with self.assertRaises(ValueError): bridge.score_bank(p, ex, replace(bank, current_source=b'other'))
        with self.assertRaises(ValueError): bridge.score_bank(p, ex, replace(bank, problem_id='other'))


class SourceParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = projection(); cls.examples, cls.banks, cls.rows = parity_fixture(cls.p)

    def test_all_scores_and_argmaxes_are_replayed(self):
        result = bridge.verify_oof_parity(self.p, self.examples, self.banks, self.rows, expected_candidates=640)
        self.assertEqual(result['exact_scores'], 640)
        self.assertEqual(result['matching_argmaxes'], 320)
        self.assertEqual(result['maximum_absolute_difference'], 0.)
        self.assertFalse(result['private_labels_opened'])
        self.assertFalse(result['fitting_performed'])
        self.assertFalse(result['stored_scores_used_for_prediction'])

    def test_partial_duplicate_or_extra_recipient_scope_fails_closed(self):
        for examples, rows in ((self.examples[:-1], self.rows[:-1]),
                (self.examples + self.examples[:1], self.rows + self.rows[:1])):
            with self.assertRaises(ValueError): bridge.verify_oof_parity(self.p, examples, self.banks, rows, expected_candidates=640)
        with self.assertRaises(ValueError): bridge.verify_oof_parity(self.p, self.examples, self.banks, self.rows)

    def test_fabricated_score_wrong_bank_fold_and_choice_fail(self):
        for mutate in (
            lambda row: row['candidate_scores']['C_joint'].update({next(iter(row['candidate_scores']['C_joint'])): 100.}),
            lambda row: row.update(bank_seal_sha256='0' * 64),
            lambda row: row.update(fold=4),
            lambda row: row['choices'].update(C_joint='0' * 64),
        ):
            rows = copy.deepcopy(self.rows); mutate(rows[0])
            with self.assertRaises(ValueError): bridge.verify_oof_parity(self.p, self.examples, self.banks, rows, expected_candidates=640)

    def test_existing_stage_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(bridge, 'export_projection', side_effect=AssertionError('must not read')):
                with self.assertRaisesRegex(ValueError, 'no overwrite'): bridge.prepare_stage('.', directory)


if __name__ == '__main__':
    unittest.main()
