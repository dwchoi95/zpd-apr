"""Synthetic-only roster validation; no submitted program is executed."""
import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
import unittest
from unittest.mock import patch

from scripts import zpd_observed_source_roster as roster


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fixture(index=0, *, problem='p1', fold=0):
    current = f'print({index})\n'
    sha = digest(current.encode())
    def hist(kind, timestamp):
        return dict(code=f'{kind} = {index}\n', verdict='WA',
                    timestamp=timestamp, language='Python')
    return dict(example_id=f'{problem}:s{index}c', user_id=f'u{index}',
        problem_id=problem, bank_id=digest((problem+'|'+sha).encode()), fold=fold,
        current_code=current, current_verdict='WA', current_timestamp=10+10*index,
        current_source_sha256=sha, history=[hist('prior', 2), hist('prior', 3)],
        donor_history=[hist('donor', 0), hist('donor', 1)],
        donor_example_id=f'{problem}:d{index}c', donor_user_id=f'du{index}',
        observed_source_ids=[f'{problem}:s{index}c', f'{problem}:s{index}a', f'{problem}:s{index}b'],
        donor_source_ids=[f'{problem}:d{index}a', f'{problem}:d{index}b'])


class ObservedSourceRosterTests(unittest.TestCase):
    def test_exact_sources_membership_and_execution_only_dedup(self):
        row = fixture(); result = roster.build_roster([row])
        self.assertEqual(len(result.sources), 5)
        self.assertEqual(len(result.memberships), 5)
        self.assertEqual(len(result.execution_requests), 3)
        self.assertEqual([m.position for m in result.memberships if m.role == 'prior'], [0,1])
        self.assertEqual([m.position for m in result.memberships if m.role == 'current'], [2])
        self.assertEqual(result.recipients[0].prior_source_ids, tuple(row['observed_source_ids'][1:]))
        self.assertNotIn(row['donor_example_id'], {s.submission_id for s in result.sources})
        for source in result.sources:
            self.assertEqual(source.source_sha256, digest(source.source))
            self.assertEqual(source.raw_submission_id, source.submission_id.split(':')[1])
        body = result.to_json()
        self.assertFalse(body['execution_authorized'])
        self.assertFalse(body['configuration']['execution_authorized'])
        self.assertIn('not_supplied', body['configuration']['donor_cutoff'])
        self.assertNotIn('donor_timestamp', json.dumps(body))

    def test_json_safe_frozen_and_detached(self):
        row = fixture(); result = roster.build_roster([row]); before = result.roster_sha256
        with self.assertRaises(FrozenInstanceError): result.sources[0].language = 'C'
        with self.assertRaises(TypeError): result.sources[0].source[0] = 0
        with self.assertRaises(FrozenInstanceError): result.memberships[0].position = 9
        row['history'][0]['code'] = 'changed'
        payload = result.to_json(); payload['sources'][0]['source_hex'] = ''
        payload['recipients'][0]['prior_source_ids'].clear()
        self.assertEqual(before, result.roster_sha256)
        json.dumps(result.to_json(), allow_nan=False)
        self.assertEqual(len(result.recipients[0].prior_source_ids), 2)

    def test_nonpython_and_exact_utf8_empty_sources_retained(self):
        row = fixture(); code = '\tα\n\n  <>&\x00\n'
        row['history'][0].update(code=code, language='C++')
        row['history'][1].update(code='', language='Python')
        result = roster.build_roster([row])
        sources = {s.submission_id: s for s in result.sources}
        old = sources[row['observed_source_ids'][1]]
        self.assertEqual(old.source, code.encode()); self.assertFalse(old.python_eligible)
        self.assertEqual(bytes.fromhex(old.to_json()['source_hex']), code.encode())
        self.assertEqual(sources[row['observed_source_ids'][2]].source, b'')
        self.assertEqual(result.to_json()['counts']['languages'], {'C++':1,'Python':4})

    def test_all_history_and_no_execution_no_file_access(self):
        row = fixture(); count = 1201; row['current_timestamp'] = count+5
        row['history'] = [dict(code='same\n', verdict='WA', timestamp=i, language='Python') for i in range(count)]
        row['donor_history'] = copy.deepcopy(row['history'])
        row['observed_source_ids'] = [row['example_id']]+[f'p1:a{i}' for i in range(count)]
        row['donor_source_ids'] = [f'p1:b{i}' for i in range(count)]
        with patch('builtins.open', side_effect=AssertionError('no file I/O')):
            result = roster.build_roster([row]); payload = result.to_json()
        self.assertEqual(len(result.sources), 1+2*count)
        self.assertEqual(payload['counts']['roles'], {'current':1,'donor':count,'prior':count})
        self.assertEqual(len(result.execution_requests), 2)

    def test_input_order_invariant_and_same_problem_same_fold_allowed(self):
        rows = [fixture(i) for i in range(3)]
        self.assertEqual(roster.build_roster(rows).roster_sha256,
                         roster.build_roster(list(reversed(rows))).roster_sha256)
        self.assertEqual(roster.build_roster(rows).to_json()['counts']['problems'], 1)

    def test_current_source_reused_as_other_donor_preserves_owner_contexts(self):
        rows = [fixture(0), fixture(1)]
        rows[1]['donor_user_id'] = rows[0]['user_id']
        rows[1]['donor_history'] = [copy.deepcopy(rows[0]['history'][0]), dict(
            code=rows[0]['current_code'], verdict='WA', timestamp=10, language='Python')]
        rows[1]['donor_source_ids'] = [rows[0]['observed_source_ids'][1], rows[0]['example_id']]
        result = roster.build_roster(rows)
        self.assertEqual(len(result.sources), 8)
        occurrences = [m for m in result.memberships if m.submission_id == rows[0]['example_id']]
        self.assertEqual({m.role for m in occurrences}, {'current','donor'})
        self.assertEqual({m.recipient_id for m in occurrences}, {r['example_id'] for r in rows})

    def test_strict_top_level_and_history_allowlists(self):
        for key in ('target_code', 'next_verdict', 'labels', 'testcase_evidence', 'current_language'):
            row = fixture(); row[key] = 'forbidden'
            with self.subTest(key=key), self.assertRaises(ValueError): roster.build_roster([row])
        row = fixture(); del row['donor_source_ids']
        with self.assertRaises(ValueError): roster.build_roster([row])
        for field in ('source_sha256','target','testcase_evidence'):
            row = fixture(); row['history'][0][field] = 'forbidden'
            with self.subTest(field=field), self.assertRaises(ValueError): roster.build_roster([row])

    def test_invalid_input_container_empty_and_scalar_types(self):
        for value in ([], (), {}, None, iter([fixture()])):
            with self.subTest(value=type(value)), self.assertRaises(ValueError): roster.build_roster(value)
        for field, value in (('current_code', b'x'), ('current_code', '\ud800'),
                             ('current_verdict','Accepted'), ('current_timestamp',True),
                             ('current_timestamp',float('nan')), ('current_timestamp',float('inf')),
                             ('current_timestamp',10**1000), ('current_source_sha256','A'*64)):
            row = fixture(); row[field] = value
            with self.subTest(field=field,value=repr(value)[:50]), self.assertRaises(ValueError): roster.build_roster([row])

    def test_fold_type_range_and_problem_consistency(self):
        for fold in (-1,5,True,1.,'1'):
            with self.subTest(fold=fold), self.assertRaises(ValueError): roster.build_roster([fixture(fold=fold)])
        with self.assertRaisesRegex(ValueError,'problem fold'):
            roster.build_roster([fixture(),fixture(1,fold=1)])
        rows = [fixture(i,problem=f'p{i}',fold=i) for i in range(5)]
        self.assertEqual(roster.build_roster(rows).to_json()['counts']['folds'], {str(i):1 for i in range(5)})

    def test_duplicate_example_user_bank_rejected(self):
        for field in ('example_id','user_id','bank_id'):
            rows = [fixture(),fixture(1)]; rows[1][field] = rows[0][field]
            with self.subTest(field=field), self.assertRaises(ValueError): roster.build_roster(rows)
        rows = [fixture(),fixture(1)]
        for key in ('current_code','current_source_sha256','bank_id'): rows[1][key] = rows[0][key]
        with self.assertRaisesRegex(ValueError,'bank'): roster.build_roster(rows)

    def test_id_problem_path_and_donor_boundaries(self):
        for field, value in (('problem_id','../p1'), ('example_id','p2:s0c'),
                ('donor_example_id','p2:dc'), ('donor_example_id','p1:s0c'),
                ('donor_user_id','u0'), ('user_id','x/y'), ('example_id','p1:a:b'),
                ('example_id','p1:'), ('example_id','p1:a b')):
            row = fixture(); row[field] = value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): roster.build_roster([row])
        for field in ('observed_source_ids','donor_source_ids'):
            row = fixture(); row[field][-1] = 'p2:bad'
            with self.subTest(field=field), self.assertRaises(ValueError): roster.build_roster([row])
        row = fixture(); row['donor_source_ids'][-1] = row['donor_example_id']
        with self.assertRaises(ValueError): roster.build_roster([row])

    def test_chain_alignment_and_duplicate_identity_rejected(self):
        for mutation in ('empty','length','ids','current_order','duplicate','cross_user','tuple'):
            row = fixture()
            if mutation == 'empty': row['history'] = []
            elif mutation == 'length': row['donor_history'].pop()
            elif mutation == 'ids': row['observed_source_ids'].pop()
            elif mutation == 'current_order': row['observed_source_ids'].reverse()
            elif mutation == 'duplicate': row['observed_source_ids'][2] = row['observed_source_ids'][1]
            elif mutation == 'cross_user': row['donor_source_ids'][0] = row['observed_source_ids'][1]
            else: row['history'] = tuple(row['history'])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): roster.build_roster([row])

    def test_ties_reverse_future_and_invalid_languages_rejected(self):
        for role in ('history','donor_history'):
            for value in (2 if role == 'history' else 0, 10, 11, float('nan'), True):
                row = fixture(); row[role][1]['timestamp'] = value
                with self.subTest(role=role,value=value), self.assertRaises(ValueError): roster.build_roster([row])
            row = fixture(); row[role].reverse()
            with self.assertRaises(ValueError): roster.build_roster([row])
        for language in ('',None,' Python','Python\n','a/b','\ud800'):
            row = fixture(); row['history'][0]['language'] = language
            with self.subTest(language=repr(language)), self.assertRaises(ValueError): roster.build_roster([row])

    def test_same_source_identity_conflicts_fail_closed(self):
        for field, value in (('code','different'),('timestamp',.5),('timestamp',0.),
                             ('language','Java'),('verdict','RE')):
            rows = [fixture(),fixture(1)]
            rows[1]['donor_example_id'] = rows[0]['donor_example_id']
            rows[1]['donor_user_id'] = rows[0]['donor_user_id']
            rows[1]['donor_source_ids'] = rows[0]['donor_source_ids'][:]
            rows[1]['donor_history'] = copy.deepcopy(rows[0]['donor_history'])
            rows[1]['donor_history'][0][field] = value
            with self.subTest(field=field,value=value), self.assertRaisesRegex(ValueError,'conflicting source'):
                roster.build_roster(rows)
        rows = [fixture(),fixture(1)]
        rows[1]['donor_source_ids'] = rows[0]['donor_source_ids'][:]
        rows[1]['donor_history'] = copy.deepcopy(rows[0]['donor_history'])
        with self.assertRaisesRegex(ValueError,'conflicting source'): roster.build_roster(rows)

    def test_donor_current_owner_conflicts_rejected_without_requesting_source(self):
        rows = [fixture(),fixture(1)]
        rows[1]['donor_example_id'] = rows[0]['donor_example_id']
        with self.assertRaisesRegex(ValueError,'donor current owner'): roster.build_roster(rows)
        rows = [fixture(),fixture(1)]
        rows[1]['donor_example_id'] = rows[0]['example_id']
        with self.assertRaisesRegex(ValueError,'source owner'): roster.build_roster(rows)

    def test_language_and_problem_are_execution_identity_components(self):
        rows = [fixture(),fixture(1,problem='p2',fold=1)]
        rows[0]['history'][1]['language'] = 'C++'
        rows[1]['history'][0]['code'] = rows[0]['history'][0]['code']
        result = roster.build_roster(rows)
        sha = digest(rows[0]['history'][0]['code'].encode())
        tasks = [t for t in result.execution_requests if t.source_sha256 == sha]
        self.assertEqual({(t.problem_id,t.language) for t in tasks}, {('p1','Python'),('p1','C++'),('p2','Python')})

    def test_actual_certified_join_synthetic_fixture_contract(self):
        from scripts import audit_zpd_repair_feedback_support as support
        from tests.test_zpd_repair_feedback_support import fixture as joined_fixture
        s,f,o,b,a,_ = joined_fixture()
        joined, _, coverage = support.join_observations(s,f,o,b,a)
        self.assertEqual(roster.OBSERVATION_FIELDS, support.OBSERVATION_FIELDS)
        result = roster.build_roster(joined)
        self.assertEqual(len(result.recipients), 10)
        self.assertEqual(len(result.sources), coverage['source_ids'])
        self.assertEqual(len(result.memberships), 50)
        self.assertEqual(result.to_json()['counts']['folds'], {str(i):2 for i in range(5)})


if __name__ == '__main__':
    unittest.main()
