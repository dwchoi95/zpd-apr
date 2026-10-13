"""Source-only diagnosis tests: synthetic vectors and authenticated local artifacts."""
import copy
from dataclasses import asdict, replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import diagnose_zpd_transition_failure as m


PROJECT = Path(__file__).resolve().parents[1]


def vector(source, verdict='WA', *, unstable=False, runtime='b' * 64, universe='a' * 64):
    cid = m.source_hash(source.encode())
    blocks = tuple(m.ExecutionBlock(w, universe, runtime,
        (('case1', 'RE' if unstable and i == 3 else verdict),), True, cid)
        for i, w in enumerate((1, 8, 8, 1)))
    return m.ExecutionVector(cid, universe, runtime, ('case1',), blocks)


def fixture():
    recipients = [dict(example_id=f'e{i}', problem_id='p', current_source='current',
        current_source_sha256=m.source_hash(b'current'), fold=0) for i in range(2)]
    planned, attempts, predictions = [], [], []
    vectors = {('p', m.source_hash(b'current')): vector('current')}
    for row in recipients:
        eid = row['example_id']
        for arm in m.ARMS:
            sources = [f'{eid}-{arm}-0', f'{eid}-{arm}-1']
            if eid == 'e0' and arm == 'C':
                sources[1] = 'shared-ac'
            if eid == 'e1' and arm == 'H':
                sources[0] = 'shared-ac'
            for draw, source in enumerate(sources):
                p = dict(attempt_id=f'{eid}-{arm}-{draw}', example_id=eid, problem_id='p',
                    arm=arm, draw_index=draw, seed=draw)
                planned.append(p)
                attempts.append(dict(p, attempt=dict(index=draw, seed=draw, status='success', source=source, error=None)))
            selected = sources[0]
            vectors['p', m.source_hash(selected.encode())] = vector(selected, 'AC' if selected == 'shared-ac' else 'WA')
            predictions.append(dict(example_id=eid, problem_id='p', fold=0, arm=arm,
                selected_source=selected, selected_source_sha256=m.source_hash(selected.encode()),
                eligible_candidate_ids=sorted({m.source_hash(s.encode()) for s in ['current', *sources]})))
    return dict(recipients=recipients, attempts=planned), attempts, predictions, vectors


def serialized(vectors):
    return [dict(problem_id=pid, vector=json.loads(m.encoded(asdict(v))), vector_sha256=v.seal_sha256)
            for (pid, _), v in vectors.items()]


class DiagnosisTests(unittest.TestCase):
    def test_missing_is_unknown_and_shared_source_supplies_evidence(self):
        inputs, attempts, predictions, vectors = fixture()
        report = m.assess(inputs, attempts, predictions, vectors)
        self.assertEqual(report['per_arm']['C']['selected_stable_ac'], 0)
        self.assertEqual(report['per_arm']['C']['oracle_lower'], 1)
        self.assertEqual(report['per_arm']['C']['oracle_upper'], 2)
        self.assertEqual(report['per_arm']['C']['missed_known_ac'], 1)
        self.assertEqual(report['per_arm']['H']['selected_stable_ac'], 1)
        self.assertEqual(report['per_arm']['HS']['oracle_lower'], 0)
        self.assertEqual(report['per_arm']['HS']['oracle_upper'], 2)
        self.assertGreater(report['coverage']['missing_unique_source_tasks'], 0)
        self.assertFalse(report['model_promotion'])
        self.assertFalse(report['method_improvement_established'])
        self.assertTrue(report['retrospective_diagnostic'])

    def test_unknown_current_and_unknown_candidate_are_not_failure(self):
        inputs, attempts, predictions, vectors = fixture()
        vectors['p', m.source_hash(b'current')] = vector('current', unstable=True)
        report = m.assess(inputs, attempts, predictions, vectors)
        self.assertEqual(report['per_arm']['H']['selected_stable_ac'], 0)
        self.assertEqual(report['per_arm']['H']['selected_unknown'], 2)
        self.assertEqual(report['per_arm']['H']['oracle_lower'], 0)
        self.assertEqual(report['per_arm']['H']['source_only_oracle_lower'], 1)
        self.assertEqual(report['per_arm']['H']['oracle_upper'], 2)
        vectors['p', m.source_hash(b'current')] = vector('current')
        vectors['p', m.source_hash(b'shared-ac')] = vector('shared-ac', 'AC', unstable=True)
        report = m.assess(inputs, attempts, predictions, vectors)
        self.assertEqual(report['per_arm']['C']['oracle_lower'], 0)
        self.assertEqual(report['per_arm']['C']['oracle_upper'], 2)
        self.assertEqual(report['coverage']['unstable_observed_vectors'], 1)

    def test_merged_full_coverage_tightens_bounds_without_selection_changes(self):
        inputs, attempts, predictions, vectors = fixture()
        before = m.assess(inputs, attempts, predictions, vectors)
        sources = m._inventory(inputs, attempts, predictions)[3]
        for key, source in sources.items():
            vectors.setdefault(key, vector(source))
        after = m.assess(inputs, attempts, predictions, serialized(vectors))
        self.assertEqual(after['coverage']['missing_unique_source_tasks'], 0)
        for arm in m.ARMS:
            self.assertEqual(after['per_arm'][arm]['oracle_lower'], after['per_arm'][arm]['oracle_upper'])
            self.assertEqual(after['per_arm'][arm]['selected_stable_ac'], before['per_arm'][arm]['selected_stable_ac'])

    def test_exact_whitespace_is_a_different_unexecuted_source(self):
        inputs, attempts, predictions, vectors = fixture()
        attempt = next(x for x in attempts if x['example_id'] == 'e0' and x['arm'] == 'C' and x['draw_index'] == 1)
        attempt['attempt']['source'] = 'shared-ac\n'
        pred = next(x for x in predictions if x['example_id'] == 'e0' and x['arm'] == 'C')
        pred['eligible_candidate_ids'].remove(m.source_hash(b'shared-ac'))
        pred['eligible_candidate_ids'].append(m.source_hash(b'shared-ac\n'))
        report = m.assess(inputs, attempts, predictions, vectors)
        self.assertEqual(report['per_arm']['C']['oracle_lower'], 0)
        self.assertEqual(report['per_arm']['C']['oracle_upper'], 2)

    def test_failure_produces_no_executable_candidate_and_no_retry_fill(self):
        inputs, attempts, predictions, vectors = fixture()
        attempt = next(x for x in attempts if x['example_id'] == 'e0' and x['arm'] == 'C' and x['draw_index'] == 1)
        attempt['attempt'].update(source=None, status='resource_failure', error='output token limit')
        pred = next(x for x in predictions if x['example_id'] == 'e0' and x['arm'] == 'C')
        pred['eligible_candidate_ids'].remove(m.source_hash(b'shared-ac'))
        report = m.assess(inputs, attempts, predictions, vectors)
        self.assertEqual(report['per_arm']['C']['attempts']['resource_failure'], 1)
        self.assertEqual(report['per_arm']['C']['proven_no_ac'], 1)

    def test_binding_corruption_rejected(self):
        mutations = [
            lambda i, a, p, v: a.pop(),
            lambda i, a, p, v: a[0].update(seed=999),
            lambda i, a, p, v: p[0].update(selected_source_sha256='0' * 64),
            lambda i, a, p, v: p[0]['eligible_candidate_ids'].append('0' * 64),
            lambda i, a, p, v: p.append(copy.deepcopy(p[0])),
            lambda i, a, p, v: v.update({('foreign', 'a' * 64): next(iter(v.values()))}),
            lambda i, a, p, v: v.update({('p', m.source_hash(b'shared-ac')): vector('shared-ac', runtime='c' * 64)}),
            lambda i, a, p, v: v.update({('p', m.source_hash(b'shared-ac')): vector('shared-ac', universe='c' * 64)}),
        ]
        for mutate in mutations:
            args = fixture()
            mutate(*args)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                m.assess(*args)

    def test_vector_seal_duplicate_and_incomplete_replay(self):
        rows = serialized(fixture()[3])
        restored = m.deserialize_vectors(rows)
        self.assertEqual(len(restored), len(rows))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            m.deserialize_vectors(rows + [rows[0]])
        rows[0]['vector_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'SHA mismatch'):
            m.deserialize_vectors(rows)
        inputs, attempts, predictions, vectors = fixture()
        key = 'p', m.source_hash(b'shared-ac')
        vectors[key] = replace(vectors[key], blocks=vectors[key].blocks[:3])
        report = m.assess(inputs, attempts, predictions, vectors)
        self.assertEqual(report['per_arm']['C']['oracle_lower'], 0)
        self.assertEqual(report['per_arm']['C']['oracle_upper'], 2)

    def test_artifact_and_stage_hash_corruption_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'data.json').write_bytes(m.encoded({'value': 1}))
            seal = dict(status='complete', files_sha256={'data.json': m.file_sha(root / 'data.json')})
            (root / 'COMPLETE.json').write_bytes(m.encoded(seal))
            digest = m.file_sha(root / 'COMPLETE.json')
            m._seal(root, 'COMPLETE.json', digest, exact=True)
            (root / 'data.json').write_bytes(m.encoded({'value': 2}))
            with self.assertRaisesRegex(ValueError, 'sealed file SHA mismatch'):
                m._seal(root, 'COMPLETE.json', digest, exact=True)
            with self.assertRaisesRegex(ValueError, 'artifact SHA mismatch'):
                m._read(root / 'COMPLETE.json', '0' * 64)


@unittest.skipUnless((PROJECT / m.ARCHIVE / 'completed-private-v1/VERIFIED_COMPLETE.json').is_file(), 'pinned archive unavailable')
class FrozenArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loaded = m.load(PROJECT)

    def test_pinned_coverage_and_selected_ac_reproduce(self):
        report = self.loaded['report']
        self.assertEqual(report['coverage']['unique_source_tasks'], 1922)
        self.assertEqual(report['coverage']['observed_unique_source_tasks'], 1134)
        self.assertEqual(report['coverage']['missing_unique_source_tasks'], 788)
        self.assertEqual(report['coverage']['unstable_observed_vectors'], 27)
        self.assertEqual(len(report['rows']), 1280)
        for arm, selected, lower, upper, missed in [('C', 204, 206, 301, 2), ('H', 130, 131, 274, 1),
                ('HS', 121, 123, 265, 2), ('U', 124, 126, 260, 2)]:
            row = report['per_arm'][arm]
            self.assertEqual([row[k] for k in ('selected_stable_ac', 'oracle_lower', 'oracle_upper', 'missed_known_ac')],
                             [selected, lower, upper, missed])

    def test_preparation_is_exact_missing_only_complete_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(m, 'load', return_value=self.loaded):
            output = Path(directory).resolve() / 'diagnosis'
            result = m.prepare(PROJECT, output)
            bundle = result['bundle']
            self.assertEqual(len(bundle['tasks']), 788)
            self.assertEqual(len(bundle['recipients']), 320)
            self.assertEqual(len(bundle['existing_task_keys']), 1134)
            self.assertEqual(bundle['total_planned_source_blocks'], 3152)
            keys = {(x['problem_id'], x['source_sha256']) for x in bundle['tasks']}
            self.assertFalse(keys & set(map(tuple, bundle['existing_task_keys'])))
            self.assertEqual(keys, set(self.loaded['sources']) - set(self.loaded['vector_map']))
            self.assertEqual(keys, {tuple(k) for r in bundle['recipients'] for k in r['missing_task_keys']})
            for row in bundle['tasks']:
                self.assertEqual(set(row), {'problem_id', 'source_sha256', 'source'})
                self.assertEqual(m.source_hash(row['source'].encode()), row['source_sha256'])
            self.assertEqual(bundle['input_sha256'], m.canonical_hash(bundle['tasks']))
            self.assertEqual(bundle['expected_runtime_sha256'], m.canonical_hash(bundle['expected_runtime']))
            for name, digest in result['complete']['files_sha256'].items():
                self.assertEqual(m.file_sha(output / name), digest)
            self.assertFalse(result['complete']['private_testcases_opened'])
            with self.assertRaises(FileExistsError):
                m.prepare(PROJECT, output)

    def test_load_never_opens_private_cases(self):
        original = Path.open
        def guarded(path, *args, **kwargs):
            self.assertNotEqual(path.name, 'testcases.jsonl')
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded):
            self.assertEqual(m.load(PROJECT)['report']['examples'], 320)


if __name__ == '__main__':
    unittest.main()
