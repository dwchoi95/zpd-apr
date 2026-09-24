"""Pure architecture diagnostics on invented SHA identities and label values."""
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import zpd_joint_progress_architecture as architecture


def digest(text): return hashlib.sha256(text.encode()).hexdigest()


def fixture(n=13):
    """No sources, candidate execution, fits or external artifact bodies."""
    cohort = []; old = []; new = []; labels = {}
    problems = 23 if n == 320 else 5
    for i in range(n):
        count = 7 if n == 320 and i < 16 else 8
        ids = [digest(f'candidate:{i}:{j}') for j in range(count)]
        base = dict(example_id=f'example{i}', user_id=f'user{i}', bank_id=f'bank{i}',
            problem_id=f'p{i % problems}', fold=(i % problems) % 5)
        cohort.append(dict(base, candidate_ids=ids, noop_candidate_id=ids[0]))
        for j, cid in enumerate(ids):
            unknown = j == 3 or (j == 0 and i % 3 == 2)
            labels[base['bank_id'], cid] = dict(bank_id=base['bank_id'], candidate_id=cid,
                status='unknown' if unknown else 'stable', gain=None if unknown else 0.,
                loss=None if unknown else .25 if j == 2 else 0.,
                all_ac=None if unknown else j == 1 or (j == 0 and i % 3 == 0))
        before, after = ((2, 1), (1, 2), (3, 1), (1, 0))[i % 4]
        for target, methods, flag, selected in (
                (old, architecture.progress.METHODS, architecture.OLD_FLAG, before),
                (new, architecture.joint.METHODS, architecture.JOINT_FLAG, after)):
            choices = {name: ids[0 if name == 'noop' else 1 if name == 'first_attempt' else selected] for name in methods}
            scores = {name: {cid: 1. if cid == choices[name] else -float(j)/100 for j, cid in enumerate(ids)}
                for name in methods}
            shared = {arm: dict(features_identical_exact=True, choice_changed=False,
                transition='same', score_difference=dict.fromkeys(ids, 0.)) for arm in architecture.SHARED}
            target.append(dict(base, choices=choices, bank_seal_sha256=digest('bank:'+str(i)),
                candidate_scores=scores, shared_theta_diagnostics=shared, **{flag: True}))
    return cohort, new, old, labels


def fraction(value): return Fraction(value['numerator'], value['denominator'])


class ArchitectureTests(unittest.TestCase):
    def setUp(self): self.cohort, self.new, self.old, self.labels = fixture()

    def report(self, **kwargs):
        return architecture.report(self.cohort, self.new, self.old, self.labels,
            reference_pins=kwargs.pop('reference_pins', dict(architecture.REFERENCE_PINS)),
            synthetic=kwargs.pop('synthetic', True), **kwargs)

    def test_pure_full_metrics_paired_direction_and_no_gate_or_method_promotion(self):
        with patch('builtins.open', side_effect=AssertionError('no I/O')), \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('no body reads')), \
             patch.object(architecture.core, 'assess', side_effect=AssertionError('no gate invocation')), \
             patch.object(architecture.progress, 'assess', side_effect=AssertionError('no old gate invocation')), \
             patch.object(architecture.joint, 'assess', side_effect=AssertionError('no primary gate invocation')):
            result = self.report()
        self.assertEqual(result['kind'], architecture.KIND)
        self.assertEqual(result['gate_effect'], 'none'); self.assertEqual(result['primary_gate_effect'], 'none')
        self.assertFalse(result['model_promotion']); self.assertFalse(result['causal_base_failure_established'])
        self.assertEqual(result['original_primary_method_count'], 14)
        self.assertEqual(result['additional_scored_primary_methods'], 0)
        self.assertNotIn('gate', result); self.assertNotIn('passed', result); self.assertNotIn('methods', result)
        self.assertEqual(result['population'], dict(examples=13, problems=5, candidates=104, folds=5))
        self.assertEqual(result['exclusions'], 0)
        json.dumps(result, allow_nan=False)
        expected = dict(examples=13, selected_candidate_changed=13, ac_gained=0, ac_lost=0,
            regression_prevented=0, regression_introduced=0, not_jointly_known=0,
            edited_to_edited=10, to_noop=3, from_noop=0)
        for a, b in zip(self.new, self.old, strict=True):
            new = self.labels[a['bank_id'], a['choices']['H']]
            old = self.labels[b['bank_id'], b['choices']['H']]
            if 'unknown' in (new['status'], old['status']): expected['not_jointly_known'] += 1
            else:
                expected['ac_gained'] += int(new['all_ac'] and not old['all_ac'])
                expected['ac_lost'] += int(old['all_ac'] and not new['all_ac'])
                expected['regression_prevented'] += int(new['loss'] == 0 and old['loss'] > 0)
                expected['regression_introduced'] += int(new['loss'] > 0 and old['loss'] == 0)
        self.assertEqual(result['full']['paired_switches'], expected)

    def test_independent_fraction_pooled_and_equal_problem_reconstruction(self):
        result = self.report(); full = result['full']
        independent = {}
        for column, predictions in (('joint_H', self.new), ('progress32_H', self.old)):
            def values(rows):
                labs = [self.labels[row['bank_id'], row['choices']['H']] for row in rows]
                n = len(rows); ac = sum(l['status'] == 'stable' and l['all_ac'] for l in labs)
                reg = sum(l['status'] == 'stable' and l['loss'] > 0 for l in labs)
                unknown = sum(l['status'] == 'unknown' for l in labs)
                return dict(zip(architecture.core.METRICS,
                    (Fraction(ac, n), Fraction(ac+unknown, n), Fraction(reg, n), Fraction(reg+unknown, n))))
            pooled = values(predictions)
            by_problem = {pid: values([row for row in predictions if row['problem_id'] == pid])
                for pid in {row['problem_id'] for row in predictions}}
            equal = {k: sum((v[k] for v in by_problem.values()), Fraction())/len(by_problem) for k in pooled}
            independent[column] = (pooled, equal)
            for name in architecture.core.METRICS:
                self.assertEqual(fraction(full['results'][column]['fractions'][name]), pooled[name])
                self.assertEqual(fraction(full['equal_problem'][column][name]), equal[name])
        self.assertNotEqual(independent['joint_H'][0]['ac_lower'], independent['joint_H'][1]['ac_lower'])
        for index, key in enumerate(('pooled', 'equal_problem')):
            for name in architecture.core.METRICS:
                self.assertEqual(fraction(full['delta_joint_minus_progress32'][key][name]),
                    independent['joint_H'][index][name]-independent['progress32_H'][index][name])

    def test_all_current_groups_folds_unknowns_and_empty_cells_retained(self):
        result = self.report()
        self.assertEqual(set(result['folds']), set(map(str, range(5))))
        self.assertEqual(sum(v['examples'] for v in result['folds'].values()), 13)
        groups = result['current_status_subgroups']
        self.assertEqual({name: cell['examples'] for name, cell in groups.items()},
            dict(known_ac=5, known_nonac=4, unknown=4))
        empty = []
        for name, folds in result['current_status_subgroup_folds'].items():
            self.assertEqual(sum(v['examples'] for v in folds.values()), groups[name]['examples'])
            for cell in folds.values():
                if not cell['examples']:
                    empty.append(cell); self.assertIsNone(cell['equal_problem'])
                    self.assertIsNone(cell['delta_joint_minus_progress32'])
                    self.assertFalse(cell['results']['joint_H']['evaluable'])
        self.assertTrue(empty)
        self.assertGreater(result['full']['results']['progress32_H']['counts']['unknown'], 0)

    def test_full_production320_and_literal_external_pin_contract(self):
        rows, new, old, labels = fixture(320)
        result = architecture.report(rows, new, old, labels, reference_pins=dict(architecture.REFERENCE_PINS))
        self.assertEqual(result['population'], dict(examples=320, problems=23, candidates=2544, folds=5))
        self.assertFalse(result['synthetic']); self.assertEqual(len(result['score_references']), 320)
        with self.assertRaisesRegex(ValueError, 'complete320'): self.report(synthetic=False)
        altered = dict(architecture.REFERENCE_PINS, predictions_sha256='f'*64)
        with self.assertRaisesRegex(ValueError, 'fixed production'):
            architecture.report(rows, new, old, labels, reference_pins=altered)
        self.assertEqual(self.report(reference_pins=altered)['reference_pins'], altered)
        for pins in ({}, dict(architecture.REFERENCE_PINS, foreign='e'*64),
                     dict(architecture.REFERENCE_PINS, predictions_sha256=True)):
            with self.assertRaises(ValueError): self.report(reference_pins=pins)
        with self.assertRaises(ValueError): self.report(synthetic=1)

    def test_detached_all_candidate_score_references_and_order_independent_join(self):
        result = self.report()
        self.new.reverse(); self.old = self.old[3:]+self.old[:3]
        reordered = self.report()
        self.assertEqual(result['full'], reordered['full'])
        self.assertEqual(result['score_references'], reordered['score_references'])
        self.assertEqual([r['example_id'] for r in result['score_references']], [r['example_id'] for r in self.cohort])
        lookup = {r['example_id']: r for r in result['score_references']}
        for rows, key in ((self.new, 'joint_H'), (self.old, 'progress32_H')):
            for row in rows:
                self.assertEqual(lookup[row['example_id']][key],
                    dict(choice=row['choices']['H'], candidate_scores=row['candidate_scores']['H']))
        before = copy.deepcopy(result)
        self.new[0]['candidate_scores']['H'].clear(); self.cohort[0]['candidate_ids'].clear()
        self.assertEqual(result, before)

    def test_method_rosters_scores_argmax_and_rich_schema_rejections(self):
        for mode in ('new_method', 'old_method', 'missing_new', 'missing_old', 'missing_score', 'nan',
                'bool', 'wrong_argmax', 'flag', 'extra_field', 'seal', 'diagnostic', 'same_features_false_scores'):
            cohort, new, old, labels = fixture(); row = new[0]; cid = cohort[0]['candidate_ids'][0]
            if mode == 'new_method': row['choices']['rescue'] = cid
            elif mode == 'old_method': old[0]['choices']['C_joint'] = cid
            elif mode == 'missing_new': row['choices'].pop('C_joint')
            elif mode == 'missing_old': old[0]['choices'].pop('CF')
            elif mode == 'missing_score': row['candidate_scores']['H'].pop(cid)
            elif mode == 'nan': row['candidate_scores']['H'][cid] = float('nan')
            elif mode == 'bool': row['candidate_scores']['H'][cid] = True
            elif mode == 'wrong_argmax': row['choices']['H'] = cid
            elif mode == 'flag': row[architecture.JOINT_FLAG] = 1
            elif mode == 'extra_field': row['model'] = {}
            elif mode == 'seal': old[0]['bank_seal_sha256'] = 'e'*64
            elif mode == 'diagnostic': row['shared_theta_diagnostics']['HS']['choice_changed'] = True
            else:
                row['candidate_scores']['shared_H_HS'][cid] -= .25
                row['shared_theta_diagnostics']['HS']['score_difference'][cid] = .25
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                architecture.report(cohort, new, old, labels, reference_pins=architecture.REFERENCE_PINS, synthetic=True)

    def test_cohort_label_coverage_unknown_and_fold_mismatch_rejections(self):
        for mode in ('missing', 'duplicate', 'user', 'fold_bool', 'problem_crossfold', 'candidate_sha',
                'label_missing', 'label_extra', 'unknown_fabricated', 'noop_loss', 'membership'):
            cohort, new, old, labels = fixture()
            if mode == 'missing': new.pop()
            elif mode == 'duplicate': old.append(copy.deepcopy(old[0]))
            elif mode == 'user': cohort[1]['user_id'] = cohort[0]['user_id']
            elif mode == 'fold_bool': new[0]['fold'] = False
            elif mode == 'problem_crossfold': cohort[5]['fold'] = 1
            elif mode == 'candidate_sha': cohort[0]['candidate_ids'][0] = 'not-sha'
            elif mode == 'label_missing': labels.pop(next(iter(labels)))
            elif mode == 'label_extra': labels['foreign', 'f'*64] = next(iter(labels.values()))
            elif mode == 'unknown_fabricated':
                next(value for value in labels.values() if value['status'] == 'unknown')['all_ac'] = False
            elif mode == 'noop_loss': labels[cohort[0]['bank_id'], cohort[0]['noop_candidate_id']]['loss'] = .1
            else: old[0]['bank_id'] = old[1]['bank_id']
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                architecture.report(cohort, new, old, labels, reference_pins=architecture.REFERENCE_PINS, synthetic=True)

    def test_SHA_tie_break_and_negative_results_not_rewritten(self):
        cohort, new, old, labels = fixture()
        for rows in (new, old):
            for row in rows:
                ids = list(row['candidate_scores']['H']); selected = min(ids)
                for name in ('H', 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF'):
                    row['candidate_scores'][name] = dict.fromkeys(ids, 0.)
                    row['choices'][name] = selected
        tied = architecture.report(cohort, new, old, labels, reference_pins=architecture.REFERENCE_PINS, synthetic=True)
        self.assertEqual(tied['full']['paired_switches']['selected_candidate_changed'], 0)
        self.assertEqual(fraction(tied['full']['delta_joint_minus_progress32']['pooled']['ac_lower']), 0)
        # Make old H always AC and joint H always known non-AC regression.
        for i, rows in enumerate((self.old, self.new)):
            for index, row in enumerate(rows):
                chosen = self.cohort[index]['candidate_ids'][1 if i == 0 else 2]
                for name in ('H', 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF'):
                    row['choices'][name] = chosen
                    row['candidate_scores'][name] = {cid: float(cid == chosen) for cid in row['candidate_scores'][name]}
        negative = self.report()
        self.assertEqual(fraction(negative['full']['delta_joint_minus_progress32']['pooled']['ac_lower']), -1)
        self.assertEqual(fraction(negative['full']['delta_joint_minus_progress32']['pooled']['regression_lower']), 1)
        self.assertEqual(negative['full']['paired_switches']['ac_lost'], 13)
        self.assertFalse(negative['model_promotion']); self.assertNotIn('passed', negative)


if __name__ == '__main__': unittest.main()
