"""Synthetic orchestration contracts; no remote, model or candidate execution."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_zpd_transition_generation as run


RELEASE_SHA = 'a' * 64


def fixture(recipients=1):
    inputs = dict(recipients=[], prompts=[], attempts=[])
    attempts = []
    for i in range(recipients):
        eid = f'problem:s{i}'
        current = f'print({i})\r\n'
        current_sha = run.sha(current.encode())
        bank_id = run.sha(('problem|' + current_sha).encode())
        inputs['recipients'].append(dict(example_id=eid, problem_id='problem', user_id=f'user{i}',
            current_source=current, current_source_sha256=current_sha, bank_id=bank_id, fold=0))
        for arm in run.ARMS:
            prompt_id = eid + ':' + arm
            prompt_sha = run.sha(prompt_id.encode())
            seeds = (1000 + 2 * i, 1001 + 2 * i)
            inputs['prompts'].append(dict(prompt_id=prompt_id, example_id=eid, bank_id=bank_id,
                arm=arm, seeds=list(seeds), prompt_sha256=prompt_sha))
            for draw, seed in enumerate(seeds):
                planned = dict(attempt_id=run.sha(f'{prompt_id}|{draw}'.encode()),
                    prompt_id=prompt_id, example_id=eid, bank_id=bank_id,
                    problem_id='problem', fold=0, arm=arm, draw_index=draw,
                    public_seed=2027 + draw, seed=seed, prompt_sha256=prompt_sha)
                inputs['attempts'].append(planned)
                entry = dict(index=draw, seed=seed, status='success',
                    source=f'print({i}, {arm!r}, {draw})\n', error=None)
                attempts.append(dict(planned, attempt=entry, raw_text=entry['source'], finish_reason='stop'))
    return inputs, attempts


def success_exit():
    return dict(Result='success', ExecMainCode='1', ExecMainStatus='0', MainPID='0',
                SubState='exited', ActiveState='active', ControlGroup='')


class CandidateLedgerTests(unittest.TestCase):
    def test_real_eight_indices_with_exact_planned_seeds_and_arm_membership(self):
        inputs, attempts = fixture()
        banks = run.candidate_banks(inputs, list(reversed(attempts)), RELEASE_SHA)
        bank, owned = banks['problem:s0']
        self.assertEqual([a.index for a in bank.attempts], list(range(8)))
        self.assertEqual(bank.seeds, (1000, 1001) * 4)
        self.assertEqual([a.source for a in bank.attempts], [r['attempt']['source'].encode() for r in attempts])
        self.assertEqual(bank.generator_config_sha256, RELEASE_SHA)
        current = inputs['recipients'][0]['current_source_sha256']
        self.assertEqual(len(bank.candidates), 9)
        for arm in run.ARMS:
            expected = {current} | {run.sha(r['attempt']['source'].encode()) for r in attempts if r['arm'] == arm}
            self.assertEqual(owned[arm], expected)
            for other in run.ARMS:
                if other != arm:
                    self.assertEqual(owned[arm] & owned[other], {current})

    def test_candidates_generated_only_elsewhere_cannot_select_for_arm(self):
        inputs, attempts = fixture()
        bank, owned = run.candidate_banks(inputs, attempts, RELEASE_SHA)['problem:s0']
        h_winner = run.sha(attempts[2]['attempt']['source'].encode())
        scores = {c.candidate_id: 1000. if c.candidate_id == h_winner else 0. for c in bank.candidates}
        current = inputs['recipients'][0]['current_source_sha256']
        for arm in run.ARMS:
            eligible_scores = {cid: scores[cid] for cid in owned[arm]}
            masks = {cid: [True] for cid in owned[arm]}
            fallback = min(eligible_scores, key=lambda cid: (-eligible_scores[cid], cid))
            selected, _ = run.choose(eligible_scores, masks, current, fallback)
            self.assertIn(selected, owned[arm])
            if arm == 'H': self.assertEqual(selected, h_winner)
            else: self.assertNotEqual(selected, h_winner)

    def test_identical_bytes_in_two_arms_are_owned_only_by_actual_generators(self):
        inputs, attempts = fixture()
        attempts[2]['attempt']['source'] = attempts[0]['attempt']['source']
        bank, owned = run.candidate_banks(inputs, attempts, RELEASE_SHA)['problem:s0']
        duplicate = run.sha(attempts[0]['attempt']['source'].encode())
        self.assertEqual(len(bank.attempts), 8)
        self.assertEqual(len(bank.candidates), 8)
        self.assertIn(duplicate, owned['C'])
        self.assertIn(duplicate, owned['H'])
        self.assertNotIn(duplicate, owned['HS'])
        self.assertNotIn(duplicate, owned['U'])

    def test_failure_slots_and_noop_duplicates_are_not_retry_filled(self):
        inputs, attempts = fixture()
        attempts[0]['attempt'].update(status='resource_failure', source=None, error='output token limit')
        attempts[1]['attempt']['source'] = inputs['recipients'][0]['current_source']
        attempts[4]['attempt'].update(status='unknown_failure', source=None, error='unknown finish reason')
        bank, owned = run.candidate_banks(inputs, attempts, RELEASE_SHA)['problem:s0']
        self.assertEqual([a.index for a in bank.attempts], list(range(8)))
        self.assertEqual([a.status for a in bank.attempts[:2]], ['resource_failure', 'success'])
        self.assertEqual(len(bank.candidates), 6)
        self.assertEqual(owned['C'], {inputs['recipients'][0]['current_source_sha256']})
        self.assertEqual(len(owned['HS']), 2)
        self.assertTrue(bank.candidates[0].is_noop)

    def test_exact_source_bytes_are_not_whitespace_normalized(self):
        inputs, attempts = fixture()
        attempts[0]['attempt']['source'] = 'print(100)\n'
        attempts[1]['attempt']['source'] = 'print(100)\r\n'
        bank, owned = run.candidate_banks(inputs, attempts, RELEASE_SHA)['problem:s0']
        self.assertEqual(len(owned['C']), 3)
        self.assertIn(b'print(100)\n', [c.source for c in bank.candidates])
        self.assertIn(b'print(100)\r\n', [c.source for c in bank.candidates])

    def test_multiple_recipients_never_exchange_generated_sources(self):
        inputs, attempts = fixture(2)
        banks = run.candidate_banks(inputs, attempts, RELEASE_SHA)
        for i in range(2):
            bank, owned = banks[f'problem:s{i}']
            mine = {run.sha(r['attempt']['source'].encode()) for r in attempts if r['example_id'] == f'problem:s{i}'}
            self.assertEqual(set.union(*owned.values()), mine | {run.sha(bank.current_source)})
        self.assertFalse(set.union(*banks['problem:s0'][1].values()) & set.union(*banks['problem:s1'][1].values()))

    def test_duplicate_missing_extra_or_foreign_generated_attempt_refuses(self):
        for mutation in ('duplicate', 'missing', 'extra', 'foreign'):
            with self.subTest(mutation=mutation):
                inputs, attempts = fixture()
                if mutation == 'duplicate': attempts[-1] = deepcopy(attempts[0])
                if mutation == 'missing': attempts.pop()
                if mutation == 'extra': attempts.append(deepcopy(attempts[0]))
                if mutation == 'foreign': attempts[-1]['attempt_id'] = 'f' * 64
                with self.assertRaisesRegex(ValueError, 'exact generated attempt coverage'):
                    run.candidate_banks(inputs, attempts, RELEASE_SHA)

    def test_wrong_planned_seed_arm_draw_or_prompt_binding_refuses(self):
        for key, replacement in (('seed', 99999), ('arm', 'U'), ('draw_index', 1),
                ('prompt_sha256', 'f' * 64), ('prompt_id', 'other'),
                ('example_id', 'problem:unrelated'), ('public_seed', 2099), ('bank_id', 'b' * 64)):
            with self.subTest(key=key):
                inputs, attempts = fixture(); attempts[0][key] = replacement
                with self.assertRaisesRegex(ValueError, 'generation ledger binding changed'):
                    run.candidate_banks(inputs, attempts, RELEASE_SHA)

    def test_wrong_terminal_seed_or_draw_index_refuses(self):
        for key, replacement in (('seed', 99999), ('index', 7)):
            with self.subTest(key=key):
                inputs, attempts = fixture(); attempts[0]['attempt'][key] = replacement
                with self.assertRaisesRegex(ValueError, 'terminal seed/index differs'):
                    run.candidate_banks(inputs, attempts, RELEASE_SHA)

    def test_failed_partial_source_and_nonterminal_attempt_refuse(self):
        for replacement in (dict(status='resource_failure', source='print(1)', error='partial'),
                            dict(status='pending', source=None, error='not terminal'),
                            dict(status='success', source='print(1)', error='unexpected error')):
            with self.subTest(replacement=replacement):
                inputs, attempts = fixture(); attempts[0]['attempt'].update(replacement)
                with self.assertRaises(ValueError):
                    run.candidate_banks(inputs, attempts, RELEASE_SHA)


class PreparedInputBindingTests(unittest.TestCase):
    def test_all_320_by_four_by_two_synthetic_input_bindings(self):
        inputs, _ = fixture(320)
        with patch.object(run, 'read_pinned', return_value=inputs):
            result = run.inputs_for(dict(inputs_path='synthetic', inputs_sha256=RELEASE_SHA))
        self.assertIs(result, inputs)

    def test_duplicate_input_identity_and_broken_arm_draw_grid_refuse(self):
        for mutation in ('recipient', 'prompt', 'attempt', 'arm_draw'):
            with self.subTest(mutation=mutation):
                inputs, _ = fixture(320)
                if mutation == 'recipient': inputs['recipients'][-1] = deepcopy(inputs['recipients'][0])
                if mutation == 'prompt': inputs['prompts'][-1] = deepcopy(inputs['prompts'][0])
                if mutation == 'attempt': inputs['attempts'][-1] = deepcopy(inputs['attempts'][0])
                if mutation == 'arm_draw': inputs['attempts'][0]['draw_index'] = 1
                with patch.object(run, 'read_pinned', return_value=inputs), self.assertRaises(ValueError):
                    run.inputs_for(dict(inputs_path='synthetic', inputs_sha256=RELEASE_SHA))

    def test_seed_or_crossarm_prompt_mismatch_refuses(self):
        for mutation in ('seed', 'crossarm_prompt'):
            with self.subTest(mutation=mutation):
                inputs, _ = fixture(320)
                if mutation == 'seed': inputs['attempts'][0]['seed'] += 10
                else: inputs['attempts'][0]['prompt_id'] = inputs['prompts'][1]['prompt_id']
                with patch.object(run, 'read_pinned', return_value=inputs), self.assertRaisesRegex(ValueError, 'prompt binding'):
                    run.inputs_for(dict(inputs_path='synthetic', inputs_sha256=RELEASE_SHA))


class StageSealTests(unittest.TestCase):
    def make_stage(self, root):
        output = Path(root)
        (output / 'nested').mkdir()
        (output / 'nested' / 'attempt.json').write_bytes(b'{"terminal":true}\n')
        (output / 'STATUS.json').write_bytes(b'{"status":"complete"}\n')
        run.seal_stage(output, 'generation', RELEASE_SHA)
        return output

    def test_complete_inventory_hashes_and_provisional_normal_exit_barrier(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.make_stage(directory)
            seal = run.verify_stage(output, 'generation', RELEASE_SHA)
            self.assertEqual(set(seal['files_sha256']), {'nested/attempt.json', 'STATUS.json'})
            self.assertTrue(seal['provisional_until_normal_exit'])
            self.assertNotIn('STAGE_COMPLETE.json', seal['files_sha256'])
            self.assertFalse(run.normal_exit({}))
            self.assertFalse((output / 'VERIFIED_COMPLETE.json').exists())

    def test_changed_extra_or_missing_artifact_refuses(self):
        for mutation in ('changed', 'extra', 'missing'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                output = self.make_stage(directory)
                if mutation == 'changed': (output / 'STATUS.json').write_bytes(b'changed\n')
                if mutation == 'extra': (output / 'unsealed.json').write_bytes(b'{}\n')
                if mutation == 'missing': (output / 'nested' / 'attempt.json').unlink()
                with self.assertRaisesRegex(ValueError, 'artifact drift|extra or missing'):
                    run.verify_stage(output, 'generation', RELEASE_SHA)

    def test_wrong_phase_release_or_nonprovisional_seal_refuses(self):
        for mutation in ('phase', 'release', 'provisional', 'status'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                output = self.make_stage(directory)
                if mutation in ('provisional', 'status'):
                    path = output / 'STAGE_COMPLETE.json'
                    seal = json.loads(path.read_bytes())
                    seal['provisional_until_normal_exit' if mutation == 'provisional' else 'status'] = False
                    path.write_bytes(run.encoded(seal))
                with self.assertRaisesRegex(ValueError, 'completion identity'):
                    run.verify_stage(output, 'public' if mutation == 'phase' else 'generation',
                                     'b' * 64 if mutation == 'release' else RELEASE_SHA)

    def test_failed_incomplete_or_partial_artifact_prevents_sealing(self):
        for name in ('FAILED.json', 'INCOMPLETE.json', 'STATUS.partial', 'nested/FAILED.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory); path = output / name
                path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'{}\n')
                with self.assertRaisesRegex(ValueError, 'incomplete stage'):
                    run.seal_stage(output, 'generation', RELEASE_SHA)
                self.assertFalse((output / 'STAGE_COMPLETE.json').exists())

    def test_existing_completion_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = self.make_stage(directory)
            raw = (output / 'STAGE_COMPLETE.json').read_bytes()
            with self.assertRaises(FileExistsError): run.seal_stage(output, 'generation', RELEASE_SHA)
            self.assertEqual((output / 'STAGE_COMPLETE.json').read_bytes(), raw)

    def test_dependency_requires_both_normal_exit_marker_and_unchanged_stage(self):
        for mutation in ('none', 'missing', 'exit', 'seal', 'payload'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                family = Path(directory)
                output = family / 'generation-v1'; output.mkdir()
                self.make_stage(output)
                marker = dict(status='complete', release_sha256=RELEASE_SHA, exit=success_exit(),
                              complete_sha256=run.sha_file(output / 'STAGE_COMPLETE.json'))
                if mutation == 'exit': marker['exit']['ExecMainStatus'] = '9'
                if mutation == 'seal': marker['complete_sha256'] = 'b' * 64
                if mutation != 'missing': run.write_new(family / 'generation-VERIFIED_COMPLETE.json', marker)
                if mutation == 'payload': (output / 'STATUS.json').write_bytes(b'changed\n')
                with patch.object(run, 'FAMILY', family):
                    if mutation == 'none':
                        self.assertEqual(run.verified_dependency('generation', RELEASE_SHA)['status'], 'complete')
                    else:
                        with self.assertRaises((ValueError, FileNotFoundError)):
                            run.verified_dependency('generation', RELEASE_SHA)


class PrivateProjectionIntegrationTests(unittest.TestCase):
    def test_worker_projects_rich_320_recipient_and_1280_prediction_metadata_before_validate(self):
        # Exercise the REAL worker projection and private schema validator. The
        # execution entrypoint is replaced; no case, label, sandbox or runtime
        # loader may run, and all sources/pins below are synthetic.
        from scripts import zpd_transition_private as private
        inputs, _ = fixture(320)
        predictions = []
        for i, row in enumerate(inputs['recipients']):
            row.update(problem_id=f'p{i % 23:05d}', fold=(i % 23) % 5,
                current_verdict='WA', current_cutoff=100 + i, history=[], donor_history=[],
                hs_permutation=[], donor_assignment_sha256='d' * 64,
                public_case_ids=['synthetic-public-only'])
            for arm in run.ARMS:
                source = row['current_source'] if arm == 'C' else f'print({i}, {arm!r})\n'
                predictions.append(dict(example_id=row['example_id'], arm=arm, selected_source=source,
                    selected_source_sha256=run.sha(source.encode()), eligible_candidate_ids=['synthetic'],
                    diagnostic={'synthetic_public_only': True}, fold=row['fold'], problem_id=row['problem_id']))
        pins = {row['problem_id'] + '/testcases.jsonl': 'b' * 64 for row in inputs['recipients']}
        self.assertEqual(len(pins), 23)
        validated = []
        def validate_only(recipients, selected, cases_root, passed_pins, output):
            roster, tasks, detached_pins = private._validate(recipients, selected, passed_pins)
            self.assertEqual(len(roster), 320)
            self.assertEqual(sum(len(r['choices']) for r in roster), 1280)
            self.assertEqual(detached_pins, pins)
            self.assertTrue(all(set(r) == {'example_id', 'problem_id', 'current_source', 'fold'} for r in recipients))
            self.assertTrue(all(set(r) == {'example_id', 'arm', 'selected_source', 'selected_source_sha256'} for r in selected))
            self.assertEqual(len(tasks), 1280)
            validated.append(True)
        with tempfile.TemporaryDirectory() as directory:
            family = Path(directory)
            public = family / 'public-v1'; public.mkdir()
            prediction_sha = run.write_new(public / 'predictions.json', predictions)
            run.write_new(public / 'PREDICTIONS_COMPLETE.json', dict(private_assessment_accessed=False,
                release_sha256=RELEASE_SHA, predictions_sha256=prediction_sha))
            run.seal_stage(public, 'public', RELEASE_SHA)
            run.write_new(family / 'public-VERIFIED_COMPLETE.json', dict(status='complete',
                release_sha256=RELEASE_SHA, exit=success_exit(),
                complete_sha256=run.sha_file(public / 'STAGE_COMPLETE.json')))
            with patch.object(run, 'FAMILY', family), \
                    patch.object(run, 'clean_source', return_value='synthetic-revision'), \
                    patch.object(run, 'load_release', return_value={'testcase_sha256': pins}), \
                    patch.object(run, 'inputs_for', return_value=inputs), \
                    patch.object(run, 'envelope', return_value={'synthetic': True}), \
                    patch.object(private, '_read_cases', side_effect=AssertionError('must not read private cases')) as cases, \
                    patch.object(private, 'execute_private', side_effect=validate_only) as execute:
                run.worker('private', 'synthetic-release.json', RELEASE_SHA)
                cases.assert_not_called()
                execute.assert_called_once()
            self.assertEqual(validated, [True])
            self.assertEqual(run.verify_stage(family / 'private-v1', 'private', RELEASE_SHA)['status'], 'complete')
        # The rich caller metadata is preserved rather than edited in-place.
        self.assertIn('current_verdict', inputs['recipients'][0])
        self.assertIn('diagnostic', predictions[0])


class CoordinatorExitTests(unittest.TestCase):
    def test_exact_normal_exit_required_not_only_zero_status(self):
        self.assertTrue(run.normal_exit(success_exit()))
        for key, replacement in (('Result', 'timeout'), ('Result', 'oom-kill'),
                ('ExecMainCode', '2'), ('ExecMainStatus', '9'), ('MainPID', '123'), ('SubState', 'running')):
            with self.subTest(key=key, replacement=replacement):
                values = success_exit(); values[key] = replacement
                self.assertFalse(run.normal_exit(values))
        for key in ('Result', 'ExecMainCode', 'ExecMainStatus', 'MainPID', 'SubState'):
            values = success_exit(); values.pop(key)
            self.assertFalse(run.normal_exit(values))

    def coordinator(self, directory, terminal, mutate=False):
        family = Path(directory) / 'synthetic-run'
        invocations = []
        def subprocess_run(command, **kwargs):
            invocations.append(command)
            if command[0] == '/usr/bin/systemd-run':
                output = family / 'generation-v1'
                output.mkdir()
                run.write_new(output / 'stage-manifest.json', dict(envelope=dict(cgroup='/nonexistent-synthetic-zpd-cgroup')))
                run.write_new(output / 'payload.json', {'synthetic': True})
                run.seal_stage(output, 'generation', RELEASE_SHA)
                if mutate: (output / 'payload.json').write_bytes(b'tampered\n')
        return family, invocations, patch.multiple(run, FAMILY=family, PHASES=('generation',)), \
            patch.object(run, 'clean_source', return_value='synthetic-revision'), \
            patch.object(run, 'load_release', return_value={}), \
            patch.object(run, 'props', side_effect=[{'LoadState': 'not-found'}, terminal]), \
            patch.object(run.subprocess, 'run', side_effect=subprocess_run)

    def test_coordinator_requires_normal_exit_and_hashes_before_verified_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            family, calls, config, clean, release, props, process = self.coordinator(directory, success_exit())
            with config, clean, release, props, process:
                run.supervise('synthetic-release.json', RELEASE_SHA)
            marker = json.loads((family / 'generation-VERIFIED_COMPLETE.json').read_bytes())
            self.assertEqual(marker['complete_sha256'], run.sha_file(family / 'generation-v1' / 'STAGE_COMPLETE.json'))
            self.assertEqual(marker['exit']['ExecMainStatus'], '0')
            final = json.loads((family / 'VERIFIED_COMPLETE.json').read_bytes())
            self.assertEqual(final['phases']['generation'], run.sha_file(family / 'generation-VERIFIED_COMPLETE.json'))
            self.assertFalse(final['model_promotion'])
            self.assertFalse(final['confirmatory'])
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[1][:4], ['/usr/bin/systemctl', '--user', 'stop', run.unit('generation')])

    def test_provisional_seal_with_abnormal_exit_never_advances(self):
        terminal = success_exit(); terminal.update(Result='exit-code', ExecMainStatus='1')
        with tempfile.TemporaryDirectory() as directory:
            family, calls, config, clean, release, props, process = self.coordinator(directory, terminal)
            with config, clean, release, props, process, patch.object(run, 'verify_stage', wraps=run.verify_stage) as verify:
                with self.assertRaisesRegex(ValueError, 'did not exit normally'):
                    run.supervise('synthetic-release.json', RELEASE_SHA)
                verify.assert_not_called()
            self.assertTrue((family / 'generation-v1' / 'STAGE_COMPLETE.json').exists())
            self.assertTrue((family / 'COORDINATOR_FAILED.json').exists())
            self.assertFalse((family / 'generation-VERIFIED_COMPLETE.json').exists())
            self.assertFalse((family / 'VERIFIED_COMPLETE.json').exists())
            self.assertEqual(len(calls), 1)

    def test_normal_exit_with_mutated_artifact_never_advances(self):
        with tempfile.TemporaryDirectory() as directory:
            family, calls, config, clean, release, props, process = self.coordinator(directory, success_exit(), mutate=True)
            with config, clean, release, props, process:
                with self.assertRaisesRegex(ValueError, 'artifact drift'):
                    run.supervise('synthetic-release.json', RELEASE_SHA)
            self.assertTrue((family / 'COORDINATOR_FAILED.json').exists())
            self.assertFalse((family / 'generation-VERIFIED_COMPLETE.json').exists())
            self.assertFalse((family / 'VERIFIED_COMPLETE.json').exists())
            self.assertEqual(len(calls), 1)


if __name__ == '__main__':
    unittest.main()
