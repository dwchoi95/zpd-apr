"""Synthetic preparation tests; no model, tokenizer, program or private labels."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_zpd_transition_generation as preparation
from scripts import zpd_public_transition_prompt as prompt


def fixture():
    pid, eid = 'fixture', 'fixture:s3'
    runtime = 'a' * 64
    samples = (prompt.Sample(1, b'1\n', b'2\n'),)
    suite = prompt.Suite(pid, samples, prompt.sample_set_sha(samples), runtime)
    rows = []
    for sid, owner, timestamp, code in (
            ('s1', 'user', 1, 'print(0)\r\n'), ('s2', 'user', 2, 'print(1)\r\n'),
            ('s3', 'user', 3, 'print(2)\r\n'), ('d1', 'donor', .1, 'print(-1)\n'),
            ('d2', 'donor', .2, 'print(-2)\n')):
        raw = code.encode()
        rows.append(dict(problem_id=pid, submission_id=pid + ':' + sid, raw_submission_id=sid,
            user_id=owner, timestamp=timestamp, language='Python', python_eligible=True,
            source_hex=raw.hex(), source_sha256=prompt.digest(raw), verdict='WA'))
    current = rows[2]
    bank_id = prompt.digest((pid + '|' + current['source_sha256']).encode())
    recipient = dict(example_id=eid, user_id='user', problem_id=pid, bank_id=bank_id, fold=0,
        current_cutoff=3, current_source_id=eid, prior_source_ids=[pid + ':s1', pid + ':s2'],
        donor_source_ids=[pid + ':d1', pid + ':d2'], donor_example_id=pid + ':d3', donor_user_id='donor')
    vector_rows = []
    for row in rows:
        identity = [pid, row['source_sha256'], 'Python']
        outcome = 'AC' if row['submission_id'] == eid else 'WA'
        blocks = [dict(block_index=i, identity=identity, source_sha256=row['source_sha256'],
            sample_set_sha256=suite.sample_set_sha256, runtime_sha256=runtime,
            case_ids=list(suite.case_ids), workers=w, complete=True,
            outcomes=[[suite.case_ids[0], outcome]]) for i, w in enumerate((1, 8, 8, 1))]
        vector_rows.append(dict(identity=identity, submission_ids=[row['submission_id']],
            sample_set_sha256=suite.sample_set_sha256, case_ids=list(suite.case_ids), eligible=True,
            blocks=blocks, stable=True, stable_verdicts=[outcome], ac_mask=[outcome == 'AC']))
    saved = dict(spec={k: recipient[k] for k in ('example_id', 'user_id', 'problem_id', 'bank_id', 'fold')},
        observed_source_ids=[eid, *recipient['prior_source_ids']],
        current_source_sha256=current['source_sha256'], donor_example_id=recipient['donor_example_id'],
        donor_user_id='donor', donor_source_ids=recipient['donor_source_ids'],
        runtime_sha256=runtime, sample_set_sha256=suite.sample_set_sha256, case_ids=list(suite.case_ids),
        candidates=[dict(moments=dict(HS=dict(permutation_indices=preparation.frozen_permutation(2, eid))))])
    sample_item = dict(index=1, input_hex=b'1\n'.hex(), output_hex=b'2\n'.hex(),
        input_sha256=prompt.digest(b'1\n'), output_sha256=prompt.digest(b'2\n'))
    data = {
        'prepared-v1/roster.json': dict(recipients=[recipient], sources=rows),
        'prepared-v1/folds.json': dict(example_fold={eid: 0}, problem_fold={pid: 0},
            folds=1, fold_sizes=[1]),
        'prepared-v1/samples.json': dict(namespace='statement_sample_problem_inventory_v1',
            problems=[dict(problem_id=pid, sample_count=1, sample_set_namespace='statement_sample_set_v1',
                           sample_set_sha256=suite.sample_set_sha256, samples=[sample_item])]),
        'replay-v2/vectors.json': dict(runtime_sha256=runtime,
            usable_only_with_valid_terminal_COMPLETE=True, vectors=vector_rows),
        'replay-v2/COMPLETE.json': dict(runtime_sha256=runtime),
        'readiness-v1/features.jsonl': [saved],
        'requests': [dict(bank_id=bank_id, problem_id=pid, current_source='print(2)\r\n',
            problem_description='Exact full problem.\nDo not alter bytes.', time_limit=2000, memory_limit=262144)],
    }
    counts = dict(recipients=1, users=1, problems=1, folds=1, prompts=4, attempts=8)
    return data, counts


def materialize(data):
    return preparation.materialize(data, fixture()[1])


class TransitionPreparationTests(unittest.TestCase):
    def test_entire_fixture_and_fixed_attempt_slots(self):
        data, counts = fixture()
        value = preparation.materialize(data, counts)
        self.assertEqual(value['counts'], counts)
        self.assertEqual(value['excluded_recipients'], 0)
        self.assertFalse(value['tokenizer_counts_measured'])
        self.assertFalse(value['private_assessment_accessed'])
        self.assertEqual([r['arm'] for r in value['prompts']], list(prompt.ARMS))
        self.assertEqual(len({r['attempt_id'] for r in value['attempts']}), 8)
        for arm in prompt.ARMS:
            attempts = [r for r in value['attempts'] if r['arm'] == arm]
            self.assertEqual([r['public_seed'] for r in attempts], [2027, 2028])
            self.assertEqual([r['draw_index'] for r in attempts], [0, 1])
        self.assertEqual({r['seed'] for r in value['attempts']}, set(value['prompts'][0]['seeds']))
        self.assertEqual(value['configuration']['max_model_len'], 8192)
        self.assertEqual(value['configuration']['max_new_tokens'], 4096)
        self.assertFalse(value['configuration']['retry_fill'])
        self.assertFalse(value['configuration']['truncate_history'])

    def test_common_current_and_problem_are_byte_exact(self):
        data, _ = fixture(); value = materialize(data)
        common = None
        for row in value['prompts']:
            self.assertEqual(prompt.digest(prompt.encoded(row['messages'])), row['prompt_sha256'])
            self.assertEqual(row['messages'][1]['content'], row['user_json'])
            body = json.loads(row['user_json'])
            self.assertEqual(body['current_program'], 'print(2)\r\n')
            self.assertEqual(body['problem_description'], data['requests'][0]['problem_description'])
            self.assertEqual(body['time_limit'], '2000')
            self.assertEqual(body['memory_limit'], '262144')
            body.pop('transitions')
            if common is None: common = body
            self.assertEqual(body, common)
            self.assertNotIn('verdict', row['binding']['supplied_sources'][0])
            self.assertNotIn('user_id', body)

    def test_no_implicit_small_cohort_or_drop(self):
        data, _ = fixture()
        with self.assertRaisesRegex(ValueError, 'full original cohort'):
            preparation.materialize(data)
        data['readiness-v1/features.jsonl'].clear()
        with self.assertRaisesRegex(ValueError, 'full saved readiness'):
            materialize(data)

    def test_preserves_frozen_HS_including_identity(self):
        data, _ = fixture(); value = materialize(data)
        saved = data['readiness-v1/features.jsonl'][0]['candidates'][0]['moments']['HS']['permutation_indices']
        self.assertEqual(value['recipients'][0]['hs_permutation'], saved)
        hs = next(x for x in value['prompts'] if x['arm'] == 'HS')
        self.assertEqual(hs['binding']['supplied_source_ids'],
            [["fixture:s1", "fixture:s2"][i] for i in saved] + ['fixture:s3'])
        data['readiness-v1/features.jsonl'][0]['candidates'].append(dict(moments=dict(HS=dict(permutation_indices=list(reversed(saved))))))
        with self.assertRaisesRegex(ValueError, 'frozen HS'):
            materialize(data)

    def test_future_or_nonchronological_history_refuses_no_exclusion(self):
        data, _ = fixture()
        data['prepared-v1/roster.json']['sources'][0]['timestamp'] = 3
        with self.assertRaisesRegex(ValueError, 'chronology.*no recipient exclusions'):
            materialize(data)

    def test_changed_donor_assignment_refuses(self):
        data, _ = fixture()
        data['prepared-v1/roster.json']['recipients'][0]['donor_user_id'] = 'unrelated'
        with self.assertRaisesRegex(ValueError, 'certified donor assignment'):
            materialize(data)

    def test_future_fields_in_sources_or_request_refuse(self):
        for target in ('sources', 'requests'):
            data, _ = fixture()
            row = (data['prepared-v1/roster.json']['sources'] if target == 'sources' else data['requests'])[0]
            row['future_target'] = 'not permitted'
            with self.assertRaisesRegex(ValueError, 'observed-only|outcome-free'):
                materialize(data)

    def test_nonpython_prior_retained_as_unknown(self):
        data, _ = fixture()
        source = data['prepared-v1/roster.json']['sources'][0]
        source['language'], source['python_eligible'] = 'C++', False
        vector = data['replay-v2/vectors.json']['vectors'][0]
        vector.update(identity=['fixture', source['source_sha256'], 'C++'], blocks=[], eligible=False,
                      stable=False, stable_verdicts=None, ac_mask=None)
        value = materialize(data)
        h = next(x for x in value['prompts'] if x['arm'] == 'H')
        first = json.loads(h['user_json'])['transitions'][0]
        self.assertEqual(first['before_language'], 'C++')
        self.assertEqual(first['before_feedback_unavailable'], 'unavailable_non_python')
        self.assertIsNone(first['aligned_public_cases'][0]['before'])
        self.assertEqual(len(json.loads(h['user_json'])['transitions']), 2)

    def test_unstable_or_unknown_current_never_becomes_all_fail(self):
        for outcome, complete in (('UNKNOWN', True), ('WA', True), ('AC', False)):
            data, _ = fixture()
            row = data['replay-v2/vectors.json']['vectors'][2]
            row['blocks'][0]['outcomes'][0][1] = outcome
            row['blocks'][0]['complete'] = complete
            row.update(stable=False, stable_verdicts=None, ac_mask=None)
            value = materialize(data)
            for p in value['prompts']:
                body = json.loads(p['user_json'])
                self.assertIsNone(body['currently_failing_public_cases'])
                self.assertIsNone(body['current_public_outcomes'][0]['verdict'])

    def test_feedback_identity_or_summary_tampering_refuses(self):
        for field in ('runtime', 'source', 'summary', 'coverage', 'order'):
            data, _ = fixture()
            row = data['replay-v2/vectors.json']['vectors'][0]
            if field == 'runtime': row['blocks'][0]['runtime_sha256'] = 'b' * 64
            if field == 'source': row['blocks'][0]['source_sha256'] = 'b' * 64
            if field == 'summary': row['ac_mask'] = [True]
            if field == 'coverage': data['replay-v2/vectors.json']['vectors'].pop()
            if field == 'order': row['blocks'][0]['workers'] = 8
            with self.assertRaises(ValueError): materialize(data)

    def test_samples_and_original_request_hashes_cannot_drift(self):
        data, _ = fixture()
        data['prepared-v1/samples.json']['problems'][0]['samples'][0]['input_hex'] = b'changed'.hex()
        with self.assertRaisesRegex(ValueError, 'exact-byte hash'):
            materialize(data)
        data, _ = fixture()
        data['requests'][0]['current_source'] = 'print(3)\n'
        with self.assertRaisesRegex(ValueError, 'description/current'):
            materialize(data)

    def test_reader_rechecks_external_pins_and_rejects_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve()
            raw = b'{"value":1}\n'
            (path / 'input.json').write_bytes(raw)
            reader = preparation.PinnedReader(path)
            self.assertEqual(reader.read('input.json', prompt.digest(raw)), {'value': 1})
            with self.assertRaisesRegex(ValueError, 'pin differs'):
                reader.read('input.json', 'a' * 64)
            (path / 'alias.json').symlink_to(path / 'input.json')
            with self.assertRaisesRegex(ValueError, 'canonical'):
                reader.read('alias.json', prompt.digest(raw))
            (path / 'input.json').write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'consumed input changed'):
                reader.recheck()

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError): preparation.decode(raw)

    def test_prepare_seals_once_only_after_success(self):
        data, counts = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in preparation.SOURCE_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# synthetic source\n')
            reader = preparation.PinnedReader(root)
            prepared = preparation.materialize(data, counts)
            output = root / 'prepared'
            with patch.object(preparation, 'load_inputs', return_value=(data, reader)), \
                    patch.object(preparation, 'materialize', return_value=prepared):
                marker = preparation.prepare(root, output)
                self.assertEqual(marker['status'], 'complete')
                for name, expected in marker['files_sha256'].items():
                    self.assertEqual(prompt.digest((output / name).read_bytes()), expected)
                with self.assertRaisesRegex(ValueError, 'no overwrite'):
                    preparation.prepare(root, output)
            other = root / 'rejected'
            with patch.object(preparation, 'load_inputs', side_effect=ValueError('input pin differs')):
                with self.assertRaisesRegex(ValueError, 'pin differs'):
                    preparation.prepare(root, other)
                self.assertFalse(other.exists())


if __name__ == '__main__':
    unittest.main()
