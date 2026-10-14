"""Pure source/format certification; no model, tokenizer or candidate execution."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_zpd_full_source as m
from scripts import zpd_public_transition_prompt as original

PROJECT = Path(__file__).resolve().parents[1]


def fixture(before, current):
    sources = [before, current]
    binding = dict(supplied_sources=[dict(submission_id=f'id{i}', source_sha256=m.sha(s.encode()), language='Python')
                                    for i, s in enumerate(sources)],
        supplied_source_ids=['id0', 'id1'], supplied_source_sha256=[m.sha(s.encode()) for s in sources],
        current_submission_id='id1', current_source_sha256=m.sha(current.encode()))
    body = dict(current_program=current, current_language='Python', public_samples=[dict(input='\r\n', expected_output='x')],
        transition_format='original_exact_edit_encoding', transitions=[dict(position=1, before_language='Python',
            after_language='Python', before_feedback_unavailable=None, after_feedback_unavailable=None,
            aligned_public_cases=[dict(case_id='public:1', before='WA', after='AC', state='gain', currently_failing=False)],
            edits=original.exact_edits(before, current))])
    return dict(user_json=m.encoded(body).decode(), binding=binding)


class SourceRenderingTests(unittest.TestCase):
    def test_utf8_crlf_delimiter_text_empty_and_exact_final_eof(self):
        cases = [('', ''), ('x=1\r\n# é\r\n', 'print("한")'),
                 ('@@ CURRENT_SOURCE_TO_REPAIR utf8_bytes=0\n```python\n', '\n@@ PRIOR_SOURCE utf8_bytes=5\n'),
                 ('a\nb', 'a\nc\n'), ('pass\r\n\r\n', 'pass\r\n\r\n')]
        for before, current in cases:
            with self.subTest(before=before, current=current):
                p = fixture(before, current)
                body, sources = m.reconstruct_sources(p)
                self.assertEqual(sources, [before, current])
                self.assertEqual(m.apply_edits(before, body['transitions'][0]['edits']), current)
                messages = m.render_prompt(p)
                self.assertEqual([x['role'] for x in messages], ['system', 'user'])
                parsed = m.parse_representation(messages[1]['content'])
                self.assertEqual(parsed['sources'], [before, current])
                self.assertEqual(parsed['transitions'], [{k: v for k, v in body['transitions'][0].items() if k != 'edits'}])
                self.assertTrue(messages[1]['content'].endswith(current))
                self.assertEqual(messages[0]['content'], m.SYSTEM)

    def test_rejects_corrupt_edits_source_hash_and_language(self):
        for mutation in ('inserted', 'removed', 'hash', 'language'):
            p = fixture('x=1\n', 'x=2\n')
            body = json.loads(p['user_json'])
            if mutation in ('inserted', 'removed'):
                body['transitions'][0]['edits'][0][mutation] = 'corrupt\n'
            elif mutation == 'hash':
                p['binding']['supplied_source_sha256'][0] = '0' * 64
            else:
                body['transitions'][0]['before_language'] = 'C++'
            p['user_json'] = m.encoded(body).decode()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                m.render_prompt(p)

    def test_delimiter_truncation_reordering_and_trailing_bytes_rejected(self):
        raw = m.render_prompt(fixture('x=1\n', 'x=2'))[1]['content']
        bad = [raw[:-1], raw+'\n', raw.replace('@@ PRIOR_SOURCE', '@@ CURRENT_SOURCE_TO_REPAIR', 1),
               raw.replace('utf8_bytes=', 'utf8_bytes=-', 1), raw.replace(m.PREFIX.decode(), '', 1)]
        for value in bad:
            with self.subTest(value=value[:60]), self.assertRaises(ValueError):
                m.parse_representation(value)

    def test_no_binding_identities_or_audit_only_fields_in_model_metadata(self):
        p = fixture('x=1', 'x=2')
        p['binding']['user_id'] = 'PRIVATE_USER_MARKER'
        p['binding']['verdict'] = 'HISTORICAL_VERDICT_MARKER'
        p['binding']['timestamp'] = 'TIMESTAMP_MARKER'
        text = m.render_prompt(p)[1]['content']
        for marker in ('PRIVATE_USER_MARKER', 'HISTORICAL_VERDICT_MARKER', 'TIMESTAMP_MARKER', 'id0', 'id1'):
            self.assertNotIn(marker, text)


class CompleteCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = m.load_original(PROJECT)
        cls.snapshot = deepcopy(cls.old)
        cls.new = m.transform_inputs(cls.old)

    def test_all_sources_reapply_and_semantic_public_evidence_preserved(self):
        summary = m.validate_representation(self.new, self.old)
        self.assertEqual(summary['source_snapshots'], 3275)
        self.assertEqual(summary['reconstructed_prior_sources'], 1995)
        self.assertEqual(summary['changed_prompts'], 1280)
        self.assertEqual(summary['updated_attempt_hashes'], 2560)
        self.assertEqual(self.old, self.snapshot)
        for p, original_p in zip(self.new['prompts'], self.old['prompts'], strict=True):
            self.assertEqual(p['user_json'], original_p['user_json'])
            body, sources = m.reconstruct_sources(original_p)
            parsed = m.parse_representation(p['messages'][1]['content'])
            self.assertEqual(parsed['sources'], sources)
            for before, after, card in zip(sources, sources[1:], body['transitions']):
                self.assertEqual(m.apply_edits(before, card['edits']), after)
            self.assertEqual(p['prompt_sha256'], original.digest(original.encoded(p['messages'])))
            self.assertNotEqual(p['messages'][1]['content'], p['user_json'])

    def test_roster_conditions_bindings_seeds_attempt_order_unchanged(self):
        restored = deepcopy(self.new)
        hashes = {p['prompt_id']: p['prompt_sha256'] for p in self.new['prompts']}
        by_key = {(p['example_id'], p['arm']): p for p in self.new['prompts']}
        for r in self.old['recipients']:
            eid = r['example_id']
            for arm, history in [('C', []), ('H', r['history']),
                    ('HS', [r['history'][i] for i in r['hs_permutation']]), ('U', r['donor_history'])]:
                parsed = m.parse_representation(by_key[eid, arm]['messages'][1]['content'])
                self.assertEqual(parsed['sources'], [s['code'] for s in history] + [r['current_source']])
        for p, old in zip(restored['prompts'], self.old['prompts'], strict=True):
            p['messages'], p['prompt_sha256'] = deepcopy(old['messages']), old['prompt_sha256']
        for a, old in zip(restored['attempts'], self.old['attempts'], strict=True):
            self.assertEqual(a['prompt_sha256'], hashes[a['prompt_id']])
            a['prompt_sha256'] = old['prompt_sha256']
        self.assertEqual(restored, self.old)

    def test_baseline_mutation_and_unrelated_change_refuse(self):
        bad = deepcopy(self.old); bad['recipients'][0]['current_source'] += '\n'
        with self.assertRaisesRegex(ValueError, 'baseline differs'):
            m.transform_inputs(bad)
        for change in ('seed', 'binding', 'provenance', 'message', 'prompt_hash', 'attempt_order', 'system'):
            bad = deepcopy(self.new)
            if change == 'seed': bad['attempts'][0]['seed'] += 1
            elif change == 'binding': bad['prompts'][0]['binding']['arm'] = 'H'
            elif change == 'provenance': bad['prompts'][0]['user_json'] += ' '
            elif change == 'message': bad['prompts'][0]['messages'][1]['content'] += '\n'
            elif change == 'system': bad['prompts'][0]['messages'][0]['content'] += '\n'
            elif change == 'prompt_hash': bad['prompts'][0]['prompt_sha256'] = '0' * 64
            else: bad['attempts'][:2] = reversed(bad['attempts'][:2])
            with self.subTest(change=change), self.assertRaises(ValueError):
                m.validate_representation(bad, self.old)

    def test_sealed_nooverwrite_output_no_private_or_model_access(self):
        reads, read = [], Path.read_bytes
        def guarded(path):
            reads.append(path)
            self.assertNotEqual(path.name, 'testcases.jsonl')
            return read(path)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / 'prepared'
            with patch.object(Path, 'read_bytes', guarded):
                complete = m.prepare(PROJECT, output)
            self.assertEqual(json.loads((output/'inputs.json').read_bytes()), self.new)
            self.assertEqual(complete['layout_variant'], m.VARIANT)
            self.assertEqual(complete['counts'], m.COUNTS)
            self.assertTrue(complete['tokenization_required_before_generation'])
            for flag in ('history_truncated', 'generation_performed', 'execution_performed',
                         'fitting_performed', 'private_testcases_opened', 'model_promotion', 'method_improvement_established'):
                self.assertFalse(complete[flag])
            for name, pin in complete['files_sha256'].items():
                self.assertEqual(m.sha((output/name).read_bytes()), pin)
            self.assertEqual({p.name for p in output.iterdir()}, {'inputs.json', 'manifest.json', 'COMPLETE.json'})
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaisesRegex(ValueError, 'no overwrite'):
                m.prepare(PROJECT, output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})
        self.assertEqual(set(reads), {PROJECT/m.BASE/n for n in m.PINS} | {PROJECT/n for n in m.SOURCE_FILES})


if __name__ == '__main__':
    unittest.main()
