from copy import deepcopy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from scripts import materialize_zpd_paired_history as m
from scripts import zpd_public_transition_prompt as p
from scripts import cache_zpd_paired_history as cache
from scripts import train_zpd_paired_history as train

RUNTIME = 'a' * 64


class FakeTokenizer:
    """Small deterministic byte-like pieces; never imports/downloads a model."""
    eos_token_id = 0
    pad_token_id = None

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return '\n'.join(r['role'] + ': ' + r['content'] for r in messages) + '\nassistant:'

    def __call__(self, text, *, add_special_tokens, truncation):
        assert add_special_tokens is False and truncation is False
        return dict(input_ids=[sum(map(ord, text[i:i+4])) + 1 for i in range(0, len(text), 4)])


def full_pair(eid, user, split, *, long_prior=False):
    value, _sample = fixture()
    value.update(example_id=eid, user_id=user, split=split, trajectory_id='p1:' + user,
                 target_submission_id='target-' + user,
                 target_code='SUPERVISION_TARGET_NOT_PROMPT\r\n  ', target_timestamp=6)
    value['target_sha256'] = m.sha(value['target_code'].encode())
    value['prior'][0]['source'] = ('x' * 24000 if long_prior else 'int main(){}\r\n')
    value['prior'][0]['source_sha256'] = m.sha(value['prior'][0]['source'].encode())
    py = dict(value['current'], submission_id='prior-python', timestamp=2,
              source='print(1)\r\n', source_sha256=m.sha(b'print(1)\r\n'))
    value['prior'] = [value['prior'][0], py, dict(py, submission_id='repeat-python', timestamp=3)]
    value['current']['timestamp'] = 4
    for source in [*value['prior'], value['current']]:
        source['user_id'] = user
    return value


def public_sample():
    samples = (p.Sample(3, b' 1\r\n', b'2\n'), p.Sample(8, '한\n'.encode(), b'3\n '))
    return dict(problem_id='p1', sample_set_sha256=p.sample_set_sha(samples), available=True,
        cases=[dict(case_id=f'statement-sample:p1:{s.index}', input=s.input_bytes.decode(),
                    expected_output=s.expected_bytes.decode()) for s in samples])


def reseal(folder, body):
    body = deepcopy(body)
    body['files_sha256'] = {name: m.sha((folder/name).read_bytes()) for name in body['files_sha256']}
    (folder/'COMPLETE.json').write_bytes(m.encoded(body))
    return m.sha((folder/'COMPLETE.json').read_bytes())


def synthetic_bundle(root, pairs=None, *, sample_override=None):
    """Construct real loader-schema artifacts, never invoke any runner."""
    prepared, cached = root/'prepared', root/'cache'
    prepared.mkdir(); cached.mkdir()
    if pairs is None:
        pairs = dict(train=[full_pair('ta0', 'A', 'train'), full_pair('tb0', 'B', 'train'),
                            full_pair('ta1', 'A', 'train', long_prior=True), full_pair('tc0', 'C', 'train')],
                     valid=[full_pair('va0', 'V1', 'valid'), full_pair('vb0', 'V2', 'valid')])
    sample = public_sample() if sample_override is None else sample_override
    tasks = {}
    for values in pairs.values():
        for row in values:
            for source in [*row['prior'], row['current']]:
                if source['language'] != 'Python': continue
                key = source['problem_id'], source['source_sha256'], source['language']
                tasks[key] = {k: source[k] for k in ('problem_id', 'source_sha256', 'language', 'source')}
                tasks[key].update(sample_set_sha256=sample['sample_set_sha256'], cases=sample['cases'])
    tasks = [tasks[k] for k in sorted(tasks)]
    prep_artifacts = {'pairs-' + split + '.jsonl': b''.join(m.encoded(row) for row in values)
                      for split, values in pairs.items()}
    prep_artifacts.update({'tasks.json': m.encoded(tasks), 'samples.json': m.encoded([sample]),
                          'manifest.json': m.encoded({'fixture': True})})
    for name, raw in prep_artifacts.items(): (prepared/name).write_bytes(raw)
    prep_seal = dict(status='complete', files_sha256={n: m.sha(v) for n, v in prep_artifacts.items()})
    prepared_sha = reseal(prepared, prep_seal)
    vectors, ledger = {}, {}
    for task in cache._tasks(tasks):
        # Prior is stable AC/WA, current is stable WA/AC, original indices 3/8.
        verdicts = ('WA', 'AC') if task.source == b'print(0)' else ('AC', 'WA')
        blocks = {i: dict(block=dict(workers=workers, universe_sha256=task.sample_set_sha256,
                    runtime_sha256=RUNTIME, source_sha256=task.source_sha256, complete=True,
                    outcomes=list(zip([c.case_id for c in task.cases], verdicts, strict=True))))
                  for i, workers in enumerate(cache.WORKERS)} if task.cases else {}
        vectors[task.key] = cache._vector(task, blocks, RUNTIME)
        ledger[task.key] = task.ledger()
    contents = {'vectors.json': dict(schema_version=cache.VERSION, runtime_sha256=RUNTIME,
                    usable_only_with_valid_terminal_COMPLETE=True, vectors=vectors),
                'tasks.json': ledger,
                'manifest.json': dict(schema_version=cache.VERSION, runtime_sha256=RUNTIME,
                    tasks_sha256=cache.sha(cache.encoded(tasks)), public_only=True),
                'STATUS.json': dict(phase='complete')}
    for name in cache.ARTIFACTS:
        (cached/name).write_bytes(m.encoded(contents[name]) if name in contents else b'')
    cache_seal = dict(status='complete', schema_version=cache.VERSION, runtime_sha256=RUNTIME,
        files_sha256={name: m.sha((cached/name).read_bytes()) for name in cache.ARTIFACTS})
    cache_sha = reseal(cached, cache_seal)
    return prepared, prepared_sha, cached, cache_sha, pairs


def fixture():
    def src(sid, when, code, language='Python'):
        return dict(problem_id='p1', user_id='PRIVATE_OWNER', submission_id=sid,
                    timestamp=when, language=language, source=code, source_sha256=m.sha(code.encode()))
    before = src('old', 1, 'int main(){}\r\n', 'C++')
    current = src('current', 3, 'print(0)')
    pair = dict(problem_id='p1', user_id='PRIVATE_OWNER', prior=[before, src('repeat', 2, before['source'], 'C++')],
                current=current, problem_description='Add one.', time_limit='2', memory_limit='2048',
                target_code='PRIVATE_TARGET', target_timestamp=4, native_verdict='PRIVATE_VERDICT')
    s = p.Sample(3, b'1\n', b'2\n')
    sample = dict(problem_id='p1', sample_set_sha256=p.sample_set_sha((s,)),
                  cases=[dict(case_id='statement-sample:p1:3', input='1\n', expected_output='2\n')])
    return pair, sample


class MaterializationTests(unittest.TestCase):
    def test_full_raw_repeats_languages_current_eof_and_no_target_leak(self):
        pair, sample = fixture()
        messages = m.build_messages(pair, 'H', sample, {}, 'a' * 64)
        body = m.full.parse_representation(messages[1]['content'])
        self.assertEqual(body['sources'], [r['source'] for r in [*pair['prior'], pair['current']]])
        self.assertEqual(body['transitions'][0]['before_language'], 'C++')
        for value in ('PRIVATE_OWNER', 'PRIVATE_TARGET', 'PRIVATE_VERDICT'):
            self.assertNotIn(value, str(messages))
        other = deepcopy(pair); other['target_code'] = 'DIFFERENT_TARGET'
        self.assertEqual(messages, m.build_messages(other, 'H', sample, {}, 'a' * 64))
        current = m.build_messages(pair, 'C', sample, {}, 'a' * 64)
        self.assertEqual(m.full.parse_representation(current[1]['content'])['sources'], ['print(0)'])

    def test_future_or_wrong_owner_prior_rejected(self):
        for field, value in [('timestamp', 3), ('user_id', 'different')]:
            pair, sample = fixture(); pair['prior'][0][field] = value
            with self.assertRaises(ValueError):m.build_messages(pair, 'H', sample, {}, 'a' * 64)

    def test_whole_trajectory_both_arms_and_exact_cap(self):
        rows = [dict(example_id=str(i), trajectory_id=t) for i, t in enumerate(('a', 'b', 'a', 'c'))]
        lengths = [{a: dict(m.CAPS) for a in m.ARMS} for _ in rows]
        lengths[2]['H']['max_input_tokens'] += 1
        kept, bad = m.eligible_trajectories(rows, lengths)
        self.assertEqual(kept, [1, 3]); self.assertEqual(set(bad), {'a'})
        self.assertEqual(bad['a'][0]['arm'], 'H')
        lengths[0]['C']['max_input_tokens'] = True
        with self.assertRaises(ValueError):m.eligible_trajectories(rows, lengths)


class MaterializeIntegrationTests(unittest.TestCase):
    def test_empty_sample_cache_identities_remain_unavailable_not_vacuous_success(self):
        empty = dict(problem_id='p1', sample_set_sha256=p.sample_set_sha(()), available=False, cases=[])
        pairs = dict(train=[full_pair('t', 'T', 'train')], valid=[full_pair('v', 'V', 'valid')])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prepared, pp, cached, cp, _ = synthetic_bundle(root, pairs, sample_override=empty)
            m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')
            row = json.loads((root/'out/train-H.jsonl').read_bytes())
            common = m.full.parse_representation(row['messages'][1]['content'])['common']
            self.assertEqual(common['public_samples'], [])
            self.assertEqual(common['current_public_outcomes'], [])
            self.assertIsNone(common['currently_failing_public_cases'])
            self.assertEqual(common['current_feedback_unavailable'], 'unavailable_samples')

    def test_unstable_full_verdict_vector_remains_unknown_not_failed(self):
        pairs = dict(train=[full_pair('t', 'T', 'train')], valid=[full_pair('v', 'V', 'valid')])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); prepared, pp, cached, cp, _ = synthetic_bundle(root, pairs)
            body = json.loads((cached/'vectors.json').read_bytes())
            key = cache.source_key('p1', m.sha(b'print(0)'), 'Python')
            row = body['vectors'][key]
            row['blocks'][0]['outcomes'][0][1] = 'CE'
            row.update(stable_verdicts=None, ac_mask=None,
                       feedback_unavailable_reasons=['unstable_full_verdict_vector'])
            (cached/'vectors.json').write_bytes(m.encoded(body))
            cp = reseal(cached, json.loads((cached/'COMPLETE.json').read_bytes()))
            m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')
            displayed = json.loads((root/'out/train-H.jsonl').read_bytes())
            common = m.full.parse_representation(displayed['messages'][1]['content'])['common']
            self.assertEqual(common['current_public_outcomes'],
                [dict(case_id='statement-sample:p1:3', verdict=None),
                 dict(case_id='statement-sample:p1:8', verdict=None)])
            self.assertIsNone(common['currently_failing_public_cases'])
            self.assertEqual(common['current_feedback_unavailable'], 'incomplete_unknown_or_unstable_full_vector')

    def test_actual_cache_schema_complete_messages_paired_lengths_shuffle_and_seals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            prepared, prep_sha, cached, cache_sha, pairs = synthetic_bundle(root)
            output = root/'materialized'
            with patch.object(cache, 'load_vectors', wraps=cache.load_vectors) as loader:
                seal = m.materialize(prepared, prep_sha, cached, cache_sha, FakeTokenizer(), output)
            loader.assert_called_once()
            self.assertEqual(loader.call_args.kwargs['runtime_sha256'], RUNTIME)
            counts = seal['counts']
            self.assertEqual(counts['train']['candidate_examples'], 4)
            self.assertEqual(counts['train']['retained_examples'], 2)
            self.assertEqual(counts['train']['excluded_examples'], 2)
            self.assertEqual(counts['train']['excluded_trajectories'], 1)
            self.assertEqual(counts['train']['observed_raw_prior_count'], 6)
            exclusion = json.loads((output/'train-trajectory-exclusions.json').read_bytes())
            self.assertEqual(set(exclusion), {'p1:A'})
            self.assertTrue(all(r['example_id'] == 'ta1' and r['arm'] == 'H' for r in exclusion['p1:A']))
            indexed = {r['example_id']: r for rows in pairs.values() for r in rows}
            users = {}
            for split, indices in [('train', [1, 3]), ('valid', [0, 1])]:
                random.Random(2027).shuffle(indices)
                expected = [pairs[split][i]['example_id'] for i in indices]
                rows = {arm: [json.loads(r) for r in (output/f'{split}-{arm}.jsonl').read_bytes().splitlines()]
                        for arm in m.ARMS}
                self.assertEqual([r['example_id'] for r in rows['C']], expected)
                self.assertEqual([r['example_id'] for r in rows['H']], expected)
                users[split] = {r['user_id'] for r in rows['C']}
                preflight = train.paired_preflight(rows['C'], rows['H'], FakeTokenizer(), **m.CAPS)
                self.assertEqual(preflight['report'], json.loads((output/f'{split}-token-preflight.json').read_bytes()))
                self.assertEqual(counts[split]['order_sha256'], preflight['report']['order_sha256'])
                for c, h in zip(rows['C'], rows['H'], strict=True):
                    pair_row = indexed[c['example_id']]
                    self.assertEqual(c['target_code'], h['target_code'])
                    self.assertEqual(c['current_code'], h['current_code'])
                    self.assertEqual({k: v for k, v in c.items() if k != 'messages'},
                                     {k: v for k, v in h.items() if k != 'messages'})
                    cf, hf = train.encode_record(c, FakeTokenizer()), train.encode_record(h, FakeTokenizer())
                    self.assertEqual(cf['target_token_ids_sha256'], hf['target_token_ids_sha256'])
                    for arm, row in [('C', c), ('H', h)]:
                        displayed = m.full.parse_representation(row['messages'][1]['content'])
                        sources = [pair_row['current']['source']]
                        if arm == 'H': sources = [r['source'] for r in pair_row['prior']] + sources
                        self.assertEqual(displayed['sources'], sources)
                        self.assertTrue(row['messages'][1]['content'].endswith(pair_row['current']['source']))
                        self.assertEqual([s['case_id'] for s in displayed['common']['public_samples']],
                                         ['statement-sample:p1:3', 'statement-sample:p1:8'])
                        self.assertEqual(displayed['common']['current_public_outcomes'],
                                         [dict(case_id='statement-sample:p1:3', verdict='WA'),
                                          dict(case_id='statement-sample:p1:8', verdict='AC')])
                        self.assertNotIn('SUPERVISION_TARGET_NOT_PROMPT', str(row['messages']))
                        if arm == 'H':
                            final = displayed['transitions'][-1]['aligned_public_cases']
                            self.assertEqual([r['case_id'] for r in final],
                                             ['statement-sample:p1:3', 'statement-sample:p1:8'])
                            self.assertEqual([(r['before'], r['after']) for r in final], [('AC', 'WA'), ('WA', 'AC')])
            self.assertFalse(users['train'] & users['valid'])
            self.assertEqual(set(seal['files_sha256']),
                             {p.name for p in output.iterdir()} - {'COMPLETE.json'})
            for name, pin in seal['files_sha256'].items(): self.assertEqual(m.sha((output/name).read_bytes()), pin)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaisesRegex(ValueError, 'new canonical'):
                m.materialize(prepared, prep_sha, cached, cache_sha, FakeTokenizer(), output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_user_overlap_even_in_length_excluded_trajectory_rejected(self):
        pairs = dict(train=[full_pair('too-long', 'shared', 'train', long_prior=True),
                            full_pair('keep', 'safe', 'train')],
                     valid=[full_pair('valid', 'shared', 'valid')])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); prepared, pp, cached, cp, _ = synthetic_bundle(root, pairs)
            with self.assertRaisesRegex(ValueError, 'user overlap'):
                m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')
            self.assertFalse((root/'out').exists())

    def test_complete_but_missing_vector_is_not_silent_missing_feedback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); prepared, pp, cached, cp, _ = synthetic_bundle(root)
            body = json.loads((cached/'vectors.json').read_bytes())
            body['vectors'].pop(next(iter(body['vectors'])))
            (cached/'vectors.json').write_bytes(m.encoded(body))
            cp = reseal(cached, json.loads((cached/'COMPLETE.json').read_bytes()))
            with self.assertRaises(ValueError):
                m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')
            self.assertFalse((root/'out').exists())

    def test_wrong_task_manifest_rejected_even_with_valid_file_seals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); prepared, pp, cached, cp, _ = synthetic_bundle(root)
            manifest = json.loads((cached/'manifest.json').read_bytes()); manifest['tasks_sha256'] = 'b' * 64
            (cached/'manifest.json').write_bytes(m.encoded(manifest))
            cp = reseal(cached, json.loads((cached/'COMPLETE.json').read_bytes()))
            with self.assertRaises(ValueError):
                m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')

    def test_mandatory_sample_and_task_files_must_be_sealed(self):
        for name in ('samples.json', 'tasks.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); prepared, pp, cached, cp, _ = synthetic_bundle(root)
                seal = json.loads((prepared/'COMPLETE.json').read_bytes()); del seal['files_sha256'][name]
                pp = reseal(prepared, seal)
                with self.assertRaises(ValueError):
                    m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')

    def test_bad_runtime_case_ids_bytes_or_external_pin_refused(self):
        for mutation in ('runtime', 'case_id', 'sample_bytes', 'external_pin', 'failed'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); prepared, pp, cached, cp, _ = synthetic_bundle(root)
                if mutation in ('runtime', 'case_id'):
                    body = json.loads((cached/'vectors.json').read_bytes())
                    vector = next(iter(body['vectors'].values()))
                    if mutation == 'runtime': vector['runtime_sha256'] = 'b' * 64
                    else: vector['case_ids'][0] = 'statement-sample:p1:1'
                    (cached/'vectors.json').write_bytes(m.encoded(body))
                    cp = reseal(cached, json.loads((cached/'COMPLETE.json').read_bytes()))
                elif mutation == 'sample_bytes':
                    samples = json.loads((prepared/'samples.json').read_bytes())
                    samples[0]['cases'][0]['input'] = 'changed'
                    (prepared/'samples.json').write_bytes(m.encoded(samples))
                    pp = reseal(prepared, json.loads((prepared/'COMPLETE.json').read_bytes()))
                elif mutation == 'failed': (cached/'FAILED.json').write_text('{}')
                else: pp = '0' * 64
                with self.assertRaises(ValueError):
                    m.materialize(prepared, pp, cached, cp, FakeTokenizer(), root/'out')
                self.assertFalse((root/'out').exists())


if __name__ == '__main__':unittest.main()
