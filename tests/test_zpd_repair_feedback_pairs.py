"""Supplied-object synthetic tests only; never read an empirical artifact."""
import copy
from dataclasses import replace
import inspect
from itertools import combinations
import unittest
from unittest.mock import patch

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from scripts import zpd_repair_feedback_offset as offset
from scripts import zpd_repair_feedback_pairs as pairs
from scripts import zpd_repair_structure as structural
from scripts.zpd_repair_fit import Example, load_inputs
from scripts.zpd_repair_pairwise import preference
from tests.test_zpd_repair_pairwise import fixture as raw_fixture


def fixture():
    examples, all_banks, all_labels = load_inputs(*raw_fixture())
    examples = examples[:2]
    banks = {ex.bank_id: all_banks[ex.bank_id] for ex in examples}
    labels = {key: value for key, value in all_labels.items() if key[0] in banks}
    interactions, base = {}, {}
    for bid, bank in banks.items():
        ids = tuple(c.candidate_id for c in bank.candidates); n = len(ids)
        matrix = np.zeros((n, pairs.DIMENSION), dtype=np.float64)
        matrix[:, 0] = np.arange(n)*.1
        values = np.zeros((n, 18), dtype=np.float64); values[:, 0] = np.arange(n)%2
        masks = np.ones((n, 18), dtype=bool)
        interactions[bid] = pairs.CandidateInteractions(ids, matrix, values, masks)
        base[bid] = dict(zip(ids, [.7, -.4, .2]))
    return examples, banks, labels, interactions, base


def small_model(zero=False):
    x = np.zeros((2, pairs.DIMENSION), dtype=np.float64)
    if not zero:
        x[0, 0] = 1.; x[1, 0] = -1.
    return offset.fit_offset(x, np.array([1, 0], dtype=np.int64), np.full(2, 950.), np.zeros(2))


class FeedbackPairsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = small_model()
        cls.zero_model = small_model(zero=True)

    def test_exact_legacy_targets_weights_order_and_metadata(self):
        ex, banks, labels, interactions, base = fixture()
        data = pairs.build_pairs(ex, banks, labels, interactions, base)
        _, old_y, old_w, _, old_meta = structural.training_data(ex, banks, labels, 'C', 'structural')
        np.testing.assert_array_equal(data.y, old_y)
        np.testing.assert_array_equal(data.weights, old_w)
        self.assertEqual(data.metadata['training'], old_meta)
        expected_candidates = []
        for example in ex:
            candidates = banks[example.bank_id].candidates
            for a, b in combinations(range(len(candidates)), 2):
                left, right = candidates[a].candidate_id, candidates[b].candidate_id
                if preference(labels[example.bank_id, left]) != preference(labels[example.bank_id, right]):
                    expected_candidates += [[left, right], [right, left]]
        self.assertEqual(data.metadata['pair_candidate_ids'], expected_candidates)
        self.assertEqual(data.matrix.shape, (12, 1296))
        np.testing.assert_array_equal(data.matrix[1::2], -data.matrix[::2])
        np.testing.assert_array_equal(data.base_margin[1::2], -data.base_margin[::2])
        np.testing.assert_array_equal(data.y[1::2], 1-data.y[::2])
        np.testing.assert_array_equal(data.weights[1::2], data.weights[::2])
        self.assertAlmostEqual(float(data.weights.sum()), 1900.)
        row = 0
        for example in ex:
            bid = example.bank_id
            for a, b in combinations(range(len(banks[bid].candidates)), 2):
                left, right = interactions[bid].candidate_ids[a], interactions[bid].candidate_ids[b]
                np.testing.assert_array_equal(data.matrix[row], interactions[bid].matrix[a]-interactions[bid].matrix[b])
                self.assertEqual(data.base_margin[row], base[bid][left]-base[bid][right])
                row += 2

    def test_equal_user_then_prefix_then_pair_mass_with_noninformative_prefix(self):
        ex, banks, labels, interactions, base = fixture()
        # A second distinct bank/prefix for u0; one informative prefix for u1.
        third = replace(ex[0], example_id='e3', bank_id='b3')
        ex.append(third); banks['b3'] = banks['b0']
        interactions['b3'] = copy.deepcopy(interactions['b0']); base['b3'] = dict(base['b0'])
        for (_, cid), row in list(labels.items()):
            if row['bank_id'] == 'b0': labels['b3', cid] = dict(row, bank_id='b3')
        # Two candidates tie, so e3 contributes only two, not three, pairs.
        ids = interactions['b3'].candidate_ids
        labels['b3', ids[2]].update(gain=.5, loss=0., all_ac=True)
        data = pairs.build_pairs(ex, banks, labels, interactions, base)
        _, old_y, old_w, _, old_meta = structural.training_data(ex, banks, labels, 'C', 'structural')
        np.testing.assert_array_equal(data.y, old_y); np.testing.assert_array_equal(data.weights, old_w)
        self.assertEqual(data.metadata['training'], old_meta)
        per_prefix = {eid: float(data.weights[np.array(old_meta['pair_example_ids']) == eid].sum()) for eid in ['e0', 'e1', 'e3']}
        self.assertAlmostEqual(per_prefix['e0'], 475.)
        self.assertAlmostEqual(per_prefix['e3'], 475.)
        self.assertAlmostEqual(per_prefix['e1'], 950.)
        for cid in ids: labels['b3', cid].update(gain=0., loss=0., all_ac=False)
        data = pairs.build_pairs(ex, banks, labels, interactions, base)
        self.assertEqual(data.metadata['training']['uninformative_train_example_ids'], ['e3'])
        self.assertEqual(len(data.metadata['banks']), 3)
        self.assertEqual(data.metadata['banks'][2]['stable_tied_pairs'], 3)
        self.assertAlmostEqual(data.weights[:6].sum(), 950.)

    def test_unknown_ties_zero_differences_and_all_banks_retained(self):
        ex, banks, labels, interactions, base = fixture()
        ids = interactions['b0'].candidate_ids
        labels['b0', ids[2]].update(status='unknown', gain=None, loss=None, all_ac=None)
        # Informative labels but entirely zero feature differences must survive.
        interactions['b0'].matrix[:] = 0.
        for cid in interactions['b1'].candidate_ids:
            labels['b1', cid].update(gain=0., loss=0., all_ac=False)
        data = pairs.build_pairs(ex, banks, labels, interactions, base)
        self.assertEqual(data.matrix.shape, (2, 1296)); self.assertFalse(data.matrix.any())
        self.assertEqual(data.metadata['training']['train_prefixes'], 2)
        self.assertEqual(data.metadata['training']['uninformative_train_example_ids'], ['e1'])
        self.assertEqual(data.metadata['banks'][0]['unknown_candidates'], 1)
        self.assertEqual(data.metadata['banks'][0]['pairs_with_unknown'], 2)
        self.assertEqual(data.metadata['informative_pair_counts']['zero_interaction_pairs'], 1)
        self.assertEqual(data.metadata['all_pair_counts']['unordered_pairs'], 6)
        self.assertEqual(len(data.metadata['banks'][0]['candidate_ids']), 3)
        # Unknown candidate still participates in scoring and can win.
        base['b0'][ids[2]] = 100.
        self.assertEqual(pairs.select_candidate(self.model, banks['b0'], interactions['b0'], base['b0']), ids[2])

    def test_all_uninformative_raises_with_complete_bank_metadata(self):
        args = fixture(); ex, banks, labels, interactions, base = args
        for row in labels.values(): row.update(status='unknown', gain=None, loss=None, all_ac=None)
        with self.assertRaises(pairs.NoInformativePairs) as error:
            pairs.build_pairs(*args)
        metadata = error.exception.metadata
        self.assertEqual(len(metadata['banks']), 2)
        self.assertEqual(metadata['training']['uninformative_train_example_ids'], ['e0', 'e1'])
        self.assertEqual(metadata['training']['sample_weight_sum'], 0.)
        self.assertEqual(sum(b['unknown_candidates'] for b in metadata['banks']), 6)

    def test_all_ac_ties_do_not_gain_an_implicit_noop_preference(self):
        args = fixture(); ids = args[3]['b0'].candidate_ids
        for cid in ids[:2]: args[2]['b0', cid].update(gain=0., loss=0., all_ac=True)
        data = pairs.build_pairs(*args)
        bank = data.metadata['banks'][0]
        self.assertEqual(bank['stable_tied_pairs'], 1)
        self.assertEqual(bank['informative_unordered_pairs'], 2)
        self.assertNotIn([ids[0], ids[1]], data.metadata['pair_candidate_ids'][:4])
        _, reference_y, reference_w, _, reference_meta = structural.training_data(*args[:3], 'C', 'structural')
        np.testing.assert_array_equal(data.y, reference_y)
        np.testing.assert_array_equal(data.weights, reference_w)
        self.assertEqual(data.metadata['training'], reference_meta)

    def test_mask_and_variation_diagnostics_never_filter_rows(self):
        args = fixture(); _, _, _, interactions, _ = args
        block = interactions['b0']; block.matrix[:] = 0.; block.matrix[1, 0] = 1e-13
        block.event_masks[1, 0] = False
        data = pairs.build_pairs(*args)
        counts = data.metadata['banks'][0]
        self.assertEqual(counts['all_pair_counts']['interaction_varying_pairs'], 0)
        self.assertEqual(counts['all_pair_counts']['zero_interaction_pairs'], 1)
        self.assertEqual(counts['all_pair_counts']['mask_different_pairs'], 2)
        self.assertEqual(counts['all_pair_counts']['effective_event_different_pairs'], 0)
        self.assertEqual(counts['all_pair_counts']['event_value_different_pairs'], 2)
        self.assertEqual(counts['event_available_candidates'][0], 2)
        self.assertEqual(data.matrix.shape[0], 12)
        self.assertNotEqual(data.matrix[0, 0], 0.)

    def test_exact_key_equality_rejects_extra_held_labels_without_value_access(self):
        args = list(fixture())
        args[2]['held_bank', 'held_sha'] = object()  # invalid value must not be inspected
        with self.assertRaisesRegex(ValueError, 'labels must have exactly'):
            pairs.build_pairs(*args)
        for position in [1, 3, 4]:
            args = list(fixture()); args[position]['held_bank'] = object()
            with self.subTest(position=position), self.assertRaisesRegex(ValueError, 'exactly'):
                pairs.build_pairs(*args)
        args = list(fixture()); args[2].pop(next(iter(args[2])))
        with self.assertRaisesRegex(ValueError, 'exactly'):
            pairs.build_pairs(*args)

    def test_nontrain_and_duplicate_examples_banks_and_wrong_types_rejected(self):
        for split in ['valid', 'held', 'test', '', None]:
            args = list(fixture()); args[0][0] = replace(args[0][0], split=split)
            with self.subTest(split=split), self.assertRaisesRegex(ValueError, 'fold-training'):
                pairs.build_pairs(*args)
        for field, value in [('example_id', 'e0'), ('bank_id', 'b0')]:
            args = list(fixture()); args[0][1] = replace(args[0][1], **{field: value})
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'unique'):
                pairs.build_pairs(*args)
        args = list(fixture()); args[0][0] = vars(args[0][0])
        with self.assertRaisesRegex(ValueError, 'exact Example'): pairs.build_pairs(*args)
        args = list(fixture()); args[0] = []
        with self.assertRaisesRegex(ValueError, 'nonempty'): pairs.build_pairs(*args)

    def test_unknown_label_fields_identity_and_impossible_evidence_rejected(self):
        updates = [dict(held_label=True), dict(candidate_id='wrong'), dict(status='surprise'),
            dict(gain=True), dict(all_ac=1), dict(status='unknown'), dict(loss=.1, all_ac=True),
            dict(gain=float('nan')), dict(gain=.8, loss=.8), dict(bank_id='held')]
        for update in updates:
            args = fixture(); key = next(iter(args[2])); args[2][key].update(update)
            with self.subTest(update=update), self.assertRaises(ValueError): pairs.build_pairs(*args)
        args = fixture(); key = next(iter(args[2])); args[2][key]['gain'] = .1
        with self.assertRaisesRegex(ValueError, 'no-op'): pairs.build_pairs(*args)

    def test_full_label_provenance_schema_and_nested_extra_fields(self):
        args = fixture(); _, banks, labels, _, _ = args
        for (bid, cid), row in labels.items():
            candidate = next(c for c in banks[bid].candidates if c.candidate_id == cid)
            row.update(problem_id=banks[bid].problem_id, is_noop=candidate.is_noop, n_cases=2,
                bank_seal_sha256=banks[bid].seal_sha256,
                evidence=dict(status=row['status'], gained_testcases=['t0'] if row['gain'] else [],
                    lost_testcases=['t1'] if row['loss'] else [], candidate_all_ac=row['all_ac'],
                    current_vector_sha256='a'*64, candidate_vector_sha256='b'*64))
        pairs.build_pairs(*args)
        mutations = [lambda row: row.update(bank_seal_sha256='c'*64),
            lambda row: row.update(n_cases=True), lambda row: row['evidence'].update(future_label=1),
            lambda row: row['evidence'].update(candidate_all_ac=1),
            lambda row: row['evidence'].update(gained_testcases=['t0']),
            lambda row: row['evidence'].update(current_vector_sha256={}),
            lambda row: row.update(is_noop=False)]
        for mutate in mutations:
            bad = copy.deepcopy(args); mutate(next(iter(bad[2].values())))
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): pairs.build_pairs(*bad)

    def test_interaction_dimensions_dtypes_order_and_base_scores_are_strict(self):
        changes = [dict(candidate_ids=('wrong',)), dict(candidate_ids=['not', 'tuple']),
            dict(matrix=np.zeros((3, 1295))), dict(matrix=np.zeros((3, 1296), dtype=np.float32)),
            dict(matrix=np.full((3, 1296), np.nan)), dict(event_values=np.zeros((3, 17))),
            dict(event_values=np.full((3, 18), .5)), dict(event_values=np.zeros((3, 18), dtype=int)),
            dict(event_masks=np.ones((3, 18), dtype=np.float64))]
        for change in changes:
            args = fixture(); args[3]['b0'] = replace(args[3]['b0'], **change)
            with self.subTest(change=list(change)), self.assertRaises(ValueError): pairs.build_pairs(*args)
            with self.assertRaises(ValueError): pairs.score_candidates(self.model, args[1]['b0'], args[3]['b0'], args[4]['b0'])
        args = fixture(); args[3]['b0'] = replace(args[3]['b0'], candidate_ids=tuple(reversed(args[3]['b0'].candidate_ids)))
        with self.assertRaisesRegex(ValueError, 'order'): pairs.build_pairs(*args)
        for value in [True, float('inf'), np.array(1.), '1']:
            args = fixture(); args[4]['b0'][next(iter(args[4]['b0']))] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'finite real'): pairs.build_pairs(*args)
        args = fixture(); args[4]['b0']['held_candidate'] = 0.
        with self.assertRaisesRegex(ValueError, 'exactly'): pairs.build_pairs(*args)

    def test_bank_observation_mismatch_rejected(self):
        args = fixture()
        args[1]['b0'] = replace(args[1]['b0'], problem_id='another_problem')
        with self.assertRaisesRegex(ValueError, 'observation and bank'): pairs.build_pairs(*args)

    def test_scorer_fixed_base_and_shared_theta_identical_features(self):
        _, banks, _, interactions, base = fixture(); bank = banks['b0']; block = interactions['b0']
        scores = pairs.score_candidates(self.model, bank, block, base['b0'])
        theta = np.array(self.model['coefficients'])
        np.testing.assert_array_equal(list(scores.values()), np.array(list(base['b0'].values()))+block.matrix@theta)
        self.assertEqual(pairs.score_candidates(self.zero_model, bank, block, base['b0']), base['b0'])
        for control in ['HS', 'Jm']:
            same = copy.deepcopy(block)
            self.assertEqual(scores, pairs.score_candidates(self.model, bank, same, base['b0']), control)
            self.assertEqual(pairs.select_candidate(self.model, bank, block, base['b0']),
                             pairs.select_candidate(self.model, bank, same, base['b0']))
        shifted = {cid: value+3. for cid, value in base['b0'].items()}
        shifted_scores = pairs.score_candidates(self.model, bank, block, shifted)
        np.testing.assert_allclose([shifted_scores[cid]-scores[cid] for cid in scores], 3., rtol=0., atol=1e-15)
        self.assertEqual(pairs.select_candidate(self.model, bank, block, shifted), pairs.select_candidate(self.model, bank, block, base['b0']))

    def test_direct_candidate_score_differences_equal_training_margins(self):
        args = fixture(); data = pairs.build_pairs(*args)
        scores = {ex.example_id: pairs.score_candidates(self.model, args[1][ex.bank_id], args[3][ex.bank_id], args[4][ex.bank_id]) for ex in args[0]}
        expected = [scores[eid][a]-scores[eid][b] for eid, (a, b) in
                    zip(data.metadata['training']['pair_example_ids'], data.metadata['pair_candidate_ids'])]
        margins = data.base_margin+data.matrix@np.asarray(self.model['coefficients'])
        np.testing.assert_allclose(margins, expected, rtol=0., atol=1e-15)

    def test_label_blind_scoring_unknowns_ties_and_unreachable_label_mutation(self):
        _, banks, labels, interactions, base = fixture(); bank = banks['b0']; block = interactions['b0']
        score = pairs.score_candidates(self.model, bank, block, base['b0'])
        labels.clear(); labels['inaccessible_held', 'candidate'] = object()
        self.assertEqual(score, pairs.score_candidates(self.model, bank, block, base['b0']))
        self.assertNotIn('labels', inspect.signature(pairs.score_candidates).parameters)
        with self.assertRaises(TypeError): pairs.score_candidates(self.model, bank, block, base['b0'], labels=labels)
        equal_base = {cid: 7. for cid in block.candidate_ids}
        self.assertEqual(pairs.select_candidate(self.zero_model, bank, block, equal_base), min(block.candidate_ids))

    def test_no_io_scaler_fit_or_base_learning_and_input_arrays_unchanged(self):
        args = fixture(); before = copy.deepcopy(args)
        with patch('builtins.open', side_effect=AssertionError('I/O forbidden')), \
                patch.object(StandardScaler, 'fit', side_effect=AssertionError('scale refit forbidden')), \
                patch.object(LogisticRegression, 'fit', side_effect=AssertionError('base fit forbidden')), \
                patch.object(offset, 'fit_offset', side_effect=AssertionError('fit forbidden')):
            data = pairs.build_pairs(*args)
            pairs.score_candidates(self.model, args[1]['b0'], args[3]['b0'], args[4]['b0'])
        self.assertEqual(args[2], before[2]); self.assertEqual(args[4], before[4])
        for bid in args[3]:
            np.testing.assert_array_equal(args[3][bid].matrix, before[3][bid].matrix)
            np.testing.assert_array_equal(args[3][bid].event_values, before[3][bid].event_values)
            np.testing.assert_array_equal(args[3][bid].event_masks, before[3][bid].event_masks)
            self.assertFalse(np.shares_memory(data.matrix, args[3][bid].matrix))

    def test_overflow_and_invalid_offset_model_rejected(self):
        args = fixture(); args[3]['b0'].matrix[0, 0] = 1e308; args[3]['b0'].matrix[1, 0] = -1e308
        with self.assertRaisesRegex(ValueError, 'difference exceeds'): pairs.build_pairs(*args)
        args = fixture(); ids = args[3]['b0'].candidate_ids; args[4]['b0'][ids[0]] = 1e308; args[4]['b0'][ids[1]] = -1e308
        with self.assertRaisesRegex(ValueError, 'difference exceeds'): pairs.build_pairs(*args)
        args = fixture(); args[3]['b0'].matrix[0, 0] = 1e308
        with self.assertRaisesRegex(ValueError, 'nonfinite fixed-offset'):
            pairs.score_candidates(self.model, args[1]['b0'], args[3]['b0'], args[4]['b0'])
        model = copy.deepcopy(self.model); model['configuration']['fixed_base_margin_coefficient'] = 2.
        with self.assertRaisesRegex(ValueError, 'configuration'):
            pairs.score_candidates(model, args[1]['b0'], args[3]['b0'], args[4]['b0'])


if __name__ == '__main__':
    unittest.main()
