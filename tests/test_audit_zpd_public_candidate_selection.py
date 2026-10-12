"""Synthetic fixtures only; never read empirical outcomes or execute sources."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import audit_zpd_public_candidate_selection as a


def fixture():
    samples, tasks, cohort, labels = {}, {}, [], []
    for i in range(10):
        pid = 'p' + str(i // 2)
        cases = [dict(case_id=f'statement-sample:{pid}:{j}', input_hex='310a', output_hex='320a') for j in (1, 2)]
        sample_sha = a.sha(a.canonical(dict(namespace='statement_sample_set_v1', samples=[
            dict(index=j, input_hex='310a', output_hex='320a') for j in (1, 2)])))
        samples[pid] = dict(cases=cases, sample_set_sha256=sample_sha)
        ids = {name: a.sha(f'{i}:{name}'.encode()) for name in ('noop', 'bad', 'good')}
        bank = a.sha((pid + '|' + ids['noop']).encode()); mapping = {}
        for name, cid in ids.items():
            identity = [pid, cid, 'Python']; key = a.sha(a.canonical(identity, True)); mapping[cid] = key
            tasks[key] = dict(identity=identity, source_hex=f'{i}:{name}'.encode().hex(), eligible=True)
            labels.append(dict(bank_id=bank, candidate_id=cid, status='stable', gain=1. if name == 'good' and i % 2 else 0.,
                               loss=1. if name == 'bad' else 0., all_ac=(name == 'good' or name == 'noop' and i % 2 == 0)))
        cohort.append(dict(example_id='e' + str(i), user_id='u' + str(i), bank_id=bank, problem_id=pid, fold=i // 2,
                           candidate_ids=sorted(ids.values()), noop_candidate_id=ids['noop'], task_ids=mapping,
                           old_choices={arm: ids['noop' if arm == 'noop' else 'bad'] for arm in a.METHODS},
                           scores={arm: {ids['noop']: 3., ids['bad']: 100., ids['good']: -5.} for arm in a.METHODS}))
    bundle = dict(version=a.VERSION, protocol_sha256=a.PROTOCOL_SHA, input_sha256={}, samples=samples, tasks=tasks, cohort=cohort)
    journal = []
    diagnostic = dict(excerpt='', characters=0, json_string_sha256=a.sha(a.canonical('')), truncated=False, encoding='canonical_ASCII_JSON_string')
    runtime_sha = 'a' * 64
    for index in range(4):
        for key, task in tasks.items():
            pid, cid, _ = task['identity']; source = bytes.fromhex(task['source_hex']).decode()
            verdicts = ['WA', 'AC'] if source.endswith('bad') else ['AC', 'AC'] if source.endswith('good') else ['AC', 'WA']
            ids = [case['case_id'] for case in samples[pid]['cases']]
            journal.append(dict(task_id=key, block=dict(execution_id=a.sha(a.canonical(task['identity'])), identity=task['identity'],
                block_index=index, workers=(1, 8, 8, 1)[index], source_sha256=cid, sample_set_sha256=samples[pid]['sample_set_sha256'],
                runtime_sha256=runtime_sha, case_ids=ids, outcomes=[list(pair) for pair in zip(ids, verdicts)],
                cases=[dict(case_id=case, verdict=verdict, stderr=copy.deepcopy(diagnostic), runtime_sec=.01) for case, verdict in zip(ids, verdicts)],
                complete=True, elapsed_seconds=.02, started_utc='2026-10-12T00:00:00+00:00', ended_utc='2026-10-12T00:00:01+00:00')))
    return bundle, journal, runtime_sha, {'labels': labels}


class IndependentReplayTests(unittest.TestCase):
    def setUp(self):
        self.bundle, self.journal, self.runtime, self.envelope = fixture()

    def vectors(self):
        return a.replay_vectors(self.bundle, self.journal, self.runtime)[0]

    def test_bundle_full_inventory_hashes_and_problem_folds(self):
        population = dict(examples=10, problems=5, candidate_memberships=30, problem_folds=5)
        a.validate_bundle(self.bundle, population)
        for mutation in (
            lambda b: b['cohort'].pop(),
            lambda b: b['cohort'][0]['candidate_ids'].pop(),
            lambda b: b['cohort'][0].update(fold=4),
            lambda b: b['tasks'][next(iter(b['tasks']))].update(source_hex='00'),
            lambda b: b['samples']['p0']['cases'][0].update(input_hex='320a'),
        ):
            value = copy.deepcopy(self.bundle); mutation(value)
            with self.assertRaises(ValueError):
                a.validate_bundle(value, population)

    def test_four_blocks_and_all_case_counts(self):
        vectors, counts = a.replay_vectors(self.bundle, self.journal, self.runtime)
        self.assertEqual(len(vectors), 30)
        self.assertEqual(counts, dict(source_blocks=120, case_attempts=240, unavailable_tasks=0))

    def test_journal_identity_and_completeness_fail_closed(self):
        for mutation in (
            lambda j: j.pop(), lambda j: j.append(copy.deepcopy(j[-1])),
            lambda j: j[0]['block'].update(workers=8),
            lambda j: j[0]['block'].update(runtime_sha256='b' * 64),
            lambda j: j[0]['block'].update(source_sha256='b' * 64),
            lambda j: j[0]['block'].update(sample_set_sha256='b' * 64),
            lambda j: j[0]['block'].update(execution_id=j[0]['task_id']),
            lambda j: j[0]['block'].update(complete=False),
            lambda j: j[0]['block']['outcomes'].reverse(),
            lambda j: j[0]['block']['cases'][0]['stderr'].update(json_string_sha256='b' * 64),
            lambda j: j[0]['block']['cases'][0].update(verdict='RE'),
        ):
            value = copy.deepcopy(self.journal); mutation(value)
            with self.assertRaises(ValueError):
                a.replay_vectors(self.bundle, value, self.runtime)

    def test_unknown_or_inconsistent_observation_stays_unavailable(self):
        for verdict in ('WA', 'UNKNOWN'):
            journal = copy.deepcopy(self.journal)
            journal[0]['block']['outcomes'][0][1] = verdict
            journal[0]['block']['cases'][0]['verdict'] = verdict
            if verdict == 'UNKNOWN':
                journal[0]['block']['cases'][0]['unknown_reason'] = 'synthetic'
            vectors, _ = a.replay_vectors(self.bundle, journal, self.runtime)
            self.assertIsNone(vectors[journal[0]['task_id']])

    def test_ineligible_task_not_executed(self):
        key = next(iter(self.bundle['tasks']))
        self.bundle['tasks'][key]['eligible'] = False
        journal = [r for r in self.journal if r['task_id'] != key]
        vectors, _ = a.replay_vectors(self.bundle, journal, self.runtime)
        self.assertIsNone(vectors[key])
        with self.assertRaises(ValueError):
            a.replay_vectors(self.bundle, self.journal, self.runtime)

    def test_safe_then_pass_count_then_frozen_score_and_noop(self):
        predictions, diagnostics = a.replay_choices(self.bundle, self.vectors())
        row, pred = self.bundle['cohort'][0], predictions[0]
        self.assertEqual(set(pred['choices']), set(a.METHODS))
        self.assertEqual(pred['choices']['noop'], row['noop_candidate_id'])
        good = a.sha(b'0:good'); bad = a.sha(b'0:bad')
        self.assertEqual(pred['choices']['C_joint'], good)
        self.assertNotIn(bad, diagnostics[0]['safe'])
        self.assertTrue(diagnostics[0]['c_exec_changed'])
        self.assertEqual(diagnostics[0]['selected_passes'], 2)

    def test_score_then_sha_tie_fallback_and_current_all_pass(self):
        vectors = {key: [True, True] for key in self.bundle['tasks']}
        for row in self.bundle['cohort']:
            for arm in a.METHODS:
                row['scores'][arm] = dict.fromkeys(row['candidate_ids'], 0.)
        predictions, diagnostics = a.replay_choices(self.bundle, vectors)
        self.assertEqual(predictions[0]['choices']['C_joint'], min(self.bundle['cohort'][0]['candidate_ids']))
        self.assertFalse(diagnostics[0]['fallback'])
        current_key = self.bundle['cohort'][0]['task_ids'][self.bundle['cohort'][0]['noop_candidate_id']]
        for unavailable in (None, []):
            vectors[current_key] = unavailable
            predictions, diagnostics = a.replay_choices(self.bundle, vectors)
            self.assertEqual(predictions[0]['choices'], self.bundle['cohort'][0]['old_choices'])
            self.assertTrue(diagnostics[0]['fallback'])

    def test_exact_metrics_and_component_but_not_history_success(self):
        labels = a.label_index(self.bundle, self.envelope)
        predictions, _ = a.replay_choices(self.bundle, self.vectors())
        new = a.assessment(predictions, labels)
        old_rows = [{**{k: row[k] for k in a.IDENTITY}, 'choices': row['old_choices']} for row in self.bundle['cohort']]
        old = a.assessment(old_rows, labels)
        self.assertEqual(new['full']['results']['C_joint']['counts'], dict(stable_ac=10, stable_regression=0, unknown=0, noop_selected=0))
        self.assertEqual(old['full']['results']['C_joint']['counts']['stable_regression'], 10)
        self.assertEqual(new['current_status_subgroups']['known_nonac']['examples'], 5)
        self.assertEqual(new['full']['equal_problem']['C_joint']['ac_lower'], Fraction(1))
        self.assertTrue(a.component(new, old)['passed'])
        self.assertFalse(new['gate']['passed'])
        self.assertFalse(a.component(new, new)['passed'])

    def test_unknown_bounds_pooled_and_equal_problem_are_distinct(self):
        labels = a.label_index(self.bundle, self.envelope)
        predictions, _ = a.replay_choices(self.bundle, self.vectors())
        rows = predictions[:3]
        chosen = rows[0]['choices']['C_joint']
        labels[rows[0]['bank_id'], chosen] = dict(status='unknown', gain=None, loss=None, all_ac=None)
        result = a.group(rows, labels)
        self.assertEqual(result['results']['C_joint']['fractions']['ac_lower'], Fraction(2, 3))
        self.assertEqual(result['results']['C_joint']['fractions']['ac_upper'], Fraction(1))
        self.assertEqual(result['results']['C_joint']['fractions']['regression_upper'], Fraction(1, 3))
        self.assertEqual(result['equal_problem']['C_joint']['ac_lower'], Fraction(3, 4))
        self.assertEqual(result['equal_problem']['C_joint']['regression_upper'], Fraction(1, 4))

    def test_label_full_inventory_unknown_null_and_noop(self):
        for mutation in (
            lambda e: e['labels'].pop(), lambda e: e['labels'].append(copy.deepcopy(e['labels'][0])),
            lambda e: e['labels'][0].update(status='unknown'),
            lambda e: e['labels'][0].update(gain=.1),
        ):
            envelope = copy.deepcopy(self.envelope); mutation(envelope)
            with self.assertRaises(ValueError):
                a.label_index(self.bundle, envelope)

    def test_duplicate_json_and_nonfinite_are_rejected(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
            with self.assertRaises(ValueError):
                a.decode(raw)

    def terminal_fixture(self, root):
        run = root / 'run-v1'; run.mkdir()
        group = '/user.slice/user-1000.slice/user@1000.service/app.slice/' + a.UNIT
        values = {name: {} for name in a.FILES}
        values['manifest.json'] = dict(envelope=dict(cgroup=group))
        values['predictions.json'] = []; values['public-vectors.json'] = {}
        raw = {name: a.canonical(value, True) for name, value in values.items()}
        raw['completions.jsonl'] = b''
        raw['PREDICTIONS_COMPLETE.json'] = a.canonical(dict(status='complete', examples=320, bundle_sha256=a.BUNDLE_SHA,
            assessment_opened=False, predictions_sha256=a.sha(raw['predictions.json']), vectors_sha256=a.sha(raw['public-vectors.json'])), True)
        for name, body in raw.items():
            (run / name).write_bytes(body)
        complete = dict(status='complete', files_sha256={name: a.sha(body) for name, body in raw.items()}, bundle_sha256=a.BUNDLE_SHA,
                        assessment_sha256=a.LABEL_SHA, examples=320, model_promotion=False, provisional_until_normal_unit_exit=True,
                        component_passed=False, zpd_passed=False)
        complete_raw = a.canonical(complete, True); (run / 'COMPLETE.json').write_bytes(complete_raw)
        outer = dict(status='complete', worker_complete_sha256=a.sha(complete_raw), bundle_sha256=a.BUNDLE_SHA,
                     bound_control_group=group, unit_exit=dict(Id=a.UNIT, LoadState='loaded', ActiveState='active', SubState='exited',
                     Result='success', ExecMainCode='1', ExecMainStatus='0', MainPID='0', ControlGroup=''),
                     component_passed=False, zpd_passed=False, model_promotion=False, examples=320)
        (root / 'VERIFIED_COMPLETE.json').write_bytes(a.canonical(outer, True))
        return outer

    def test_terminal_hash_chain_normal_exit_and_exact_inventory(self):
        for mutation in ('none', 'failed', 'extra', 'corrupt', 'nonzero', 'missingseal', 'symlink'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory); outer = self.terminal_fixture(root)
                if mutation == 'none':
                    a.authenticate_terminal(root); continue
                if mutation in ('failed', 'extra'):
                    (root / 'run-v1' / ('FAILED.json' if mutation == 'failed' else 'extra.json')).write_bytes(b'{}')
                elif mutation == 'corrupt':
                    (root / 'run-v1' / 'predictions.json').write_bytes(b'{}')
                elif mutation == 'nonzero':
                    outer['unit_exit']['ExecMainStatus'] = '1'
                    (root / 'VERIFIED_COMPLETE.json').write_bytes(a.canonical(outer, True))
                elif mutation == 'missingseal':
                    (root / 'VERIFIED_COMPLETE.json').unlink()
                else:
                    path = root / 'run-v1' / 'report.json'; path.unlink(); path.symlink_to(root / 'run-v1' / 'public-vectors.json')
                with self.assertRaises((ValueError, FileNotFoundError)):
                    a.authenticate_terminal(root)

    def test_no_private_read_when_public_authentication_fails(self):
        opened = []
        def reader(path, digest=None):
            opened.append(str(path))
            raise ValueError('synthetic unsealed input')
        with patch.object(a, 'read', side_effect=reader), self.assertRaises(ValueError):
            a.audit(Path('/synthetic'), Path('/synthetic/result'))
        self.assertFalse(any(path.endswith(a.LABEL_PATH) for path in opened))


if __name__ == '__main__':
    unittest.main()
