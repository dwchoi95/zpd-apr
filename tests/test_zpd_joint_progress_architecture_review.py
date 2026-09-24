"""Nonauthor paired diagnostic checks using independently counted fractions."""
from fractions import Fraction
import random
import unittest

from scripts import zpd_joint_progress_architecture as architecture
from tests.test_zpd_joint_progress_architecture import fixture, fraction


class ArchitectureReviewTests(unittest.TestCase):
    def test_seeded_all_candidate_choices_keep_known_unknown_paired_estimands(self):
        rng = random.Random(20260925)
        for case in range(30):
            cohort, new, old, labels = fixture(17)
            for predictions in (new, old):
                for row in predictions:
                    ids = list(row['candidate_scores']['H']); choice = rng.choice(ids)
                    for name in ('H', 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF'):
                        row['choices'][name] = choice
                        row['candidate_scores'][name] = {cid: float(cid == choice) for cid in ids}
            result = architecture.report(cohort, new, old, labels,
                reference_pins=architecture.REFERENCE_PINS, synthetic=True)
            def rates(rows):
                labs = [labels[row['bank_id'], row['choices']['H']] for row in rows]
                ac = sum(lab['status'] == 'stable' and lab['all_ac'] for lab in labs)
                reg = sum(lab['status'] == 'stable' and lab['loss'] > 0 for lab in labs)
                unknown = sum(lab['status'] == 'unknown' for lab in labs)
                return (Fraction(ac, len(rows)), Fraction(ac+unknown, len(rows)),
                    Fraction(reg, len(rows)), Fraction(reg+unknown, len(rows)))
            for column, rows in (('joint_H', new), ('progress32_H', old)):
                pooled = rates(rows)
                problems = [rates([row for row in rows if row['problem_id'] == pid])
                    for pid in sorted({row['problem_id'] for row in rows})]
                for i, metric in enumerate(architecture.core.METRICS):
                    with self.subTest(case=case, column=column, metric=metric):
                        self.assertEqual(fraction(result['full']['results'][column]['fractions'][metric]), pooled[i])
                        self.assertEqual(fraction(result['full']['equal_problem'][column][metric]),
                            sum((p[i] for p in problems), Fraction()) / len(problems))
            pairs = [(labels[a['bank_id'], a['choices']['H']], labels[b['bank_id'], b['choices']['H']])
                for a, b in zip(new, old, strict=True)]
            known = [(a, b) for a, b in pairs if a['status'] == b['status'] == 'stable']
            switches = result['full']['paired_switches']
            self.assertEqual(switches['not_jointly_known'], len(pairs)-len(known))
            self.assertEqual(switches['ac_gained'], sum(a['all_ac'] and not b['all_ac'] for a, b in known))
            self.assertEqual(switches['ac_lost'], sum(b['all_ac'] and not a['all_ac'] for a, b in known))
            self.assertEqual(result['exclusions'], 0); self.assertNotIn('gate', result)
            self.assertNotIn('passed', result); self.assertEqual(result['additional_scored_primary_methods'], 0)

    def test_reversing_architectures_reverses_differences_not_population(self):
        cohort, new, old, labels = fixture(17)
        first = architecture.report(cohort, new, old, labels, reference_pins=architecture.REFERENCE_PINS, synthetic=True)
        for before, after in zip(old, new, strict=True):
            # Swap only H and its shared-input diagnostic score/choice copies.
            for name in ('H', 'shared_H_HS', 'shared_H_Jm', 'shared_H_CF'):
                before['choices'][name], after['choices'][name] = after['choices'][name], before['choices'][name]
                before['candidate_scores'][name], after['candidate_scores'][name] = after['candidate_scores'][name], before['candidate_scores'][name]
        second = architecture.report(cohort, new, old, labels, reference_pins=architecture.REFERENCE_PINS, synthetic=True)
        self.assertEqual(first['population'], second['population'])
        for estimand in ('pooled', 'equal_problem'):
            for metric in architecture.core.METRICS:
                self.assertEqual(fraction(first['full']['delta_joint_minus_progress32'][estimand][metric]),
                    -fraction(second['full']['delta_joint_minus_progress32'][estimand][metric]))
        a, b = first['full']['paired_switches'], second['full']['paired_switches']
        self.assertEqual(a['ac_gained'], b['ac_lost']); self.assertEqual(a['ac_lost'], b['ac_gained'])
        self.assertEqual(a['not_jointly_known'], b['not_jointly_known'])


if __name__ == '__main__': unittest.main()
