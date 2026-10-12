import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import zpd_transition_private as m
from src.runner.models import CaseOutcome, Verdict


def population():
    recipients = [dict(example_id=f'e{i}', problem_id=f'p{i % 5}',
                       current_source='current', fold=i % 5) for i in range(320)]
    predictions = [dict(example_id=r['example_id'], arm=arm,
        selected_source='better' if arm == 'H' else 'current',
        selected_source_sha256=m.sha(b'better' if arm == 'H' else b'current'))
        for r in recipients for arm in m.ARMS]
    return recipients, predictions


class PrivateReplayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.data = self.root / 'data'
        self.output = self.root / 'result'
        self.recipients, self.predictions = population()
        self.pins = {}
        for i in range(5):
            path = self.data / f'p{i}/testcases.jsonl'
            path.parent.mkdir(parents=True)
            path.write_bytes(m.encoded(dict(case_id=f'case-p{i}', input='', expected_output='x')))
            self.pins[f'p{i}/testcases.jsonl'] = m.file_sha(path)
        self.calls = []

    def runner(self, _runner, source, case):
        self.calls.append((source, case.case_id))
        return CaseOutcome(case.case_id, Verdict.AC if source == 'better' or case.case_id == 'case-p0'
                           else Verdict.WA)

    def execute(self, behavior=None, runtime_identity=None, **kwargs):
        def mocked(runner, source, case):
            return (behavior or self.runner)(runner, source, case)
        with patch.object(m, '_runtime_identity', side_effect=runtime_identity or
                          (lambda: {'synthetic_test_only': True})), \
                patch.object(m.evaluator.SandboxRunner, 'run_case', new=mocked):
            return m.execute_private(self.recipients, self.predictions, self.data,
                                     self.pins, self.output, **kwargs)

    def test_selected_union_deduplicated_four_blocks_and_exact_label_scope(self):
        before = copy.deepcopy((self.recipients, self.predictions, self.pins))
        result = self.execute()
        self.assertEqual(before, (self.recipients, self.predictions, self.pins))
        self.assertTrue(result['complete'])
        self.assertEqual(len(self.calls), 40)  # 5 problems * 2 exact sources * 4 blocks.
        self.assertEqual({c[0] for c in self.calls}, {'current', 'better'})
        self.assertEqual(len(result['labels']), 320 * 5)
        self.assertEqual({r['arm'] for r in result['labels']}, set(m.METHODS))
        journal = [json.loads(line) for line in (self.output / 'completions.jsonl').read_text().splitlines()]
        self.assertEqual(len(journal), 40)
        self.assertEqual([r['block_index'] for r in journal], [i for i in range(4) for _ in range(10)])
        self.assertEqual([r['block']['workers'] for r in journal], [n for n in (1, 8, 8, 1) for _ in range(10)])
        marker = json.loads((self.output / 'COMPLETE.json').read_text())
        self.assertTrue(marker['provisional_until_normal_unit_exit'])
        self.assertEqual(marker['labels'], 1600)
        for name, digest in marker['files_sha256'].items():
            self.assertEqual(m.file_sha(self.output / name), digest)
        status = json.loads((self.output / 'STATUS.json').read_text())
        self.assertEqual(status['completed_source_blocks'], 40)
        self.assertEqual(status['completed_examples'], 320)
        self.assertEqual(status['total_examples'], 320)
        with self.assertRaises(FileExistsError):
            self.execute()

    def test_new_gate_groups_folds_pairs_and_claim_boundaries(self):
        report = self.execute()['report']
        self.assertEqual(report['development_gate']['decision'], 'proceed')
        self.assertTrue(report['development_gate']['passed'])
        self.assertEqual(report['full']['results']['H']['counts']['stable_ac'], 320)
        self.assertEqual(report['full']['results']['C']['counts']['stable_ac'], 64)
        self.assertEqual(report['current_status_subgroups']['known_ac']['examples'], 64)
        self.assertEqual(report['current_status_subgroups']['known_nonac']['examples'], 256)
        self.assertEqual(report['current_status_subgroups']['unknown']['examples'], 0)
        self.assertEqual(report['paired_H']['C']['ac_gained'], 256)
        self.assertEqual(report['paired_H']['C']['selected_candidate_changed'], 320)
        self.assertEqual(report['full']['equal_problem']['C']['ac_lower']['value'], .2)
        self.assertEqual(set(report['folds']), {'0', '1', '2', '3', '4'})
        self.assertFalse(report['historical_gates_evaluated'])
        self.assertFalse(report['confirmatory'])
        self.assertFalse(report['model_promotion'])
        self.assertFalse(report['educational_benefit_established'])
        self.assertFalse(report['unknown_bounds_are_confidence_intervals'])
        self.assertNotIn('Jm', report['methods'])
        self.assertNotIn('CF', report['methods'])

    def test_every_input_failure_is_before_any_private_file_read(self):
        mutations = [
            lambda r, p, pins: r.pop(),
            lambda r, p, pins: r[1].update(example_id=r[0]['example_id']),
            lambda r, p, pins: r[0].update(problem_id='../outside'),
            lambda r, p, pins: r[0].update(fold=True),
            lambda r, p, pins: r[0].update(fold=1),
            lambda r, p, pins: p.pop(),
            lambda r, p, pins: p[1].update(arm='C'),
            lambda r, p, pins: p[0].update(example_id='foreign'),
            lambda r, p, pins: p[0].update(arm='Jm'),
            lambda r, p, pins: p[0].update(selected_source_sha256='0' * 64),
            lambda r, p, pins: p[0].update(extra='forbidden'),
            lambda r, p, pins: pins.update({'foreign/testcases.jsonl': 'a' * 64}),
            lambda r, p, pins: pins.update({'p0/testcases.jsonl': 'invalid'}),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                rec, pred, pins = copy.deepcopy((self.recipients, self.predictions, self.pins))
                mutation(rec, pred, pins)
                with patch.object(m, '_read_cases', side_effect=AssertionError('private read')) as read:
                    with self.assertRaises(ValueError):
                        m.execute_private(rec, pred, self.data, pins, self.output)
                    read.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_pin_corruption_and_symlink_fail_before_sandbox(self):
        self.pins['p0/testcases.jsonl'] = '0' * 64
        with patch.object(m, '_runtime_identity') as runtime:
            with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
                self.execute()
            runtime.assert_not_called()
        path = self.data / 'p0/testcases.jsonl'
        self.pins['p0/testcases.jsonl'] = m.file_sha(path)
        actual = self.root / 'actual.jsonl'
        path.rename(actual)
        path.symlink_to(actual)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.execute()
        self.assertFalse(self.output.exists())

    def test_current_unknown_propagates_to_all_choices_and_noop(self):
        def unknown_current(_runner, source, case):
            if source == 'current':
                raise OSError('synthetic resource failure')
            return CaseOutcome(case.case_id, Verdict.AC)
        result = self.execute(unknown_current)
        self.assertTrue(result['complete'])  # Fully executed is not the same as stable.
        self.assertTrue(all(row['status'] == 'unknown' for row in result['labels']))
        self.assertTrue(all(row['gain'] is None and row['loss'] is None and row['all_ac'] is None
                            for row in result['labels']))
        report = result['report']
        self.assertEqual(report['development_gate']['decision'], 'hold')
        self.assertEqual(report['current_status_subgroups']['unknown']['examples'], 320)
        self.assertEqual(report['full']['results']['H']['fractions']['ac_upper']['value'], 1.)
        self.assertEqual(report['paired_H']['C']['not_jointly_known'], 320)

    def test_same_ac_mask_but_different_verdict_is_unstable_unknown(self):
        calls = {}
        def unstable(_runner, source, case):
            key = source, case.case_id
            calls[key] = calls.get(key, 0) + 1
            verdict = Verdict.WA if source == 'current' or calls[key] % 2 else Verdict.TLE
            return CaseOutcome(case.case_id, verdict)
        result = self.execute(unstable)
        self.assertTrue(all(r['status'] == 'unknown' for r in result['labels'] if r['arm'] == 'H'))
        self.assertTrue(all(r['status'] == 'stable' for r in result['labels'] if r['arm'] == 'C'))
        self.assertFalse(result['report']['development_gate']['passed'])

    def test_deadline_retains_population_unknowns_and_never_completes(self):
        result = self.execute(deadline_seconds=1e-9)
        self.assertFalse(result['complete'])
        self.assertEqual(len(result['labels']), 1600)
        self.assertEqual(len(self.calls), 0)
        self.assertTrue(all(row['status'] == 'unknown' for row in result['labels']))
        self.assertEqual(result['report']['development_gate']['decision'], 'hold')
        self.assertFalse((self.output / 'COMPLETE.json').exists())
        self.assertTrue((self.output / 'INCOMPLETE.json').exists())
        self.assertEqual((self.output / 'completions.jsonl').read_bytes(), b'')

    def test_unexpected_worker_failure_is_durably_failed(self):
        with patch.object(m.evaluator, 'run_source', side_effect=RuntimeError('synthetic failure')):
            with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
                self.execute()
        failed = json.loads((self.output / 'FAILED.json').read_text())
        self.assertFalse(failed['assessment_valid'])
        self.assertFalse((self.output / 'COMPLETE.json').exists())
        self.assertTrue((self.output / 'manifest.json').exists())

    def test_runtime_drift_cannot_receive_a_complete_marker(self):
        identity = iter([{'synthetic': 1}, {'synthetic': 2}])
        with self.assertRaisesRegex(ValueError, 'runtime changed'):
            self.execute(runtime_identity=lambda: next(identity))
        self.assertEqual(len(self.calls), 40)
        self.assertTrue((self.output / 'FAILED.json').exists())
        self.assertFalse((self.output / 'COMPLETE.json').exists())

    def test_case_pin_reread_barrier_catches_in_execution_drift(self):
        changed = False
        def drift(runner, source, case):
            nonlocal changed
            if not changed:
                changed = True
                path = self.data / 'p0/testcases.jsonl'
                path.write_bytes(path.read_bytes() + b'\n')
            return self.runner(runner, source, case)
        with self.assertRaisesRegex(ValueError, 'testcase changed'):
            self.execute(drift)
        self.assertEqual(len(self.calls), 40)
        self.assertTrue((self.output / 'FAILED.json').exists())
        self.assertFalse((self.output / 'COMPLETE.json').exists())

    def test_exact_whitespace_and_problem_identity_are_never_normalized(self):
        self.predictions[0].update(selected_source='current ', selected_source_sha256=m.sha(b'current '))
        roster, tasks, pins = m._validate(self.recipients, self.predictions, self.pins)
        self.assertEqual(len(tasks), 11)
        self.assertIn(('p0', m.sha(b'current ')), tasks)
        self.assertIn(('p0', m.sha(b'current')), tasks)
        self.assertIn(('p1', m.sha(b'current')), tasks)

    def test_deadline_bounds_and_missing_case_ids_fail_closed(self):
        for invalid in (0, -1, True, float('nan'), float('inf'), 21601):
            with self.subTest(deadline=invalid), self.assertRaises(ValueError):
                self.execute(deadline_seconds=invalid)
        path = self.data / 'p0/testcases.jsonl'
        raw = m.encoded(dict(case_id='duplicate', input='', expected_output=''))
        path.write_bytes(raw + raw)
        self.pins['p0/testcases.jsonl'] = m.file_sha(path)
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.execute()


class NewGateTests(unittest.TestCase):
    def fixture(self):
        recipients, predictions = population()
        rows, _, _ = m._validate(recipients, predictions, {f'p{i}/testcases.jsonl': 'a' * 64 for i in range(5)})
        labels = [dict(example_id=row['example_id'], arm=arm,
            source_sha256='current' if arm == 'noop' else arm, is_noop=arm == 'noop',
            status='stable', all_ac=arm == 'H', gain=1. if arm == 'H' else 0., loss=0.)
            for row in rows for arm in m.METHODS]
        return rows, labels

    def test_any_control_tie_regression_unknown_or_worse_fold_holds(self):
        rows, labels = self.fixture()
        self.assertTrue(m.assess(rows, labels, execution_complete=True)['development_gate']['passed'])
        for change in ('tie_HS', 'regression', 'unknown', 'worse_fold'):
            values = copy.deepcopy(labels)
            for label in values:
                if change == 'tie_HS' and label['arm'] == 'HS':
                    label['all_ac'] = True
                if change == 'regression' and label['arm'] == 'H' and label['example_id'] == 'e0':
                    label.update(loss=.5, all_ac=False)
                if change == 'unknown' and label['arm'] == 'H' and label['example_id'] == 'e0':
                    label.update(status='unknown', gain=None, loss=None, all_ac=None)
                if change == 'worse_fold' and int(label['example_id'][1:]) % 5 == 0:
                    label['all_ac'] = label['arm'] == 'C'
            with self.subTest(change=change):
                report = m.assess(rows, values, execution_complete=True)
                self.assertEqual(report['development_gate']['decision'], 'hold')
        self.assertFalse(m.assess(rows, labels, execution_complete=False)['development_gate']['passed'])

    def test_equal_problem_is_not_pooled_weighting(self):
        rows = [dict(problem_id=pid, labels={arm: dict(status='stable', all_ac=ac,
                    loss=0., is_noop=False) for arm in m.METHODS})
                for pid, ac in [('p0', True), ('p0', True), ('p1', False)]]
        report = m._serialize(m._group(rows))
        self.assertEqual(report['results']['H']['fractions']['ac_lower']['numerator'], 2)
        self.assertEqual(report['results']['H']['fractions']['ac_lower']['denominator'], 3)
        self.assertEqual(report['equal_problem']['H']['ac_lower']['value'], .5)


if __name__ == '__main__':
    unittest.main()
