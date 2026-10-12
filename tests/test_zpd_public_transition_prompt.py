"""Synthetic only: no real source, outcome, tokenizer, model, or program runs."""
from dataclasses import asdict, replace
import json
import unittest

from scripts import zpd_public_transition_prompt as p
from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector


def source(sid, code, when, owner='learner', language='Python'):
    raw = code.encode('utf-8')
    return p.Source('fixture', owner, sid, when, language, raw, p.digest(raw))


def vector(suite, src, verdicts):
    pairs = tuple(zip(suite.case_ids, verdicts, strict=True))
    return ExecutionVector(src.source_sha256, suite.sample_set_sha256, suite.runtime_sha256,
        suite.case_ids, tuple(ExecutionBlock(w, suite.sample_set_sha256, suite.runtime_sha256,
            pairs, True, src.source_sha256) for w in (1, 8, 8, 1)))


def fixture():
    samples = (p.Sample(1, b'1\n', b'2\n'), p.Sample(3, b'2\n', b'3\n'))
    suite = p.Suite('fixture', samples, p.sample_set_sha(samples), 'a'*64)
    prior = (source('s1', 'x=0\r\nprint(x)\r\n', 1),
             source('s2', 'x=1\r\nprint(x)\r\n', 2))
    current = source('s3', 'x=2\r\nprint(x)\r\n\n', 3)
    donors = (source('d1', 'y=0\nprint(y)\n', .5, 'other'),
              source('d2', 'y=1\nprint(y)\n', 1.5, 'other'))
    request = p.Request('Exact public description.\n', '2 seconds', '256 MiB',
        current, prior, donors, 'b'*64, (1, 0), suite)
    outcomes = [('WA', 'AC'), ('AC', 'WA'), ('WA', 'AC'), ('RE', 'WA'), ('AC', 'AC')]
    vectors = {s.execution_key: vector(suite, s, values)
               for s, values in zip((*prior, current, *donors), outcomes, strict=True)}
    return request, vectors


def body(prompt):
    return json.loads(prompt.user_json)


class PublicTransitionPromptTests(unittest.TestCase):
    def test_full_current_description_and_common_cases_are_identical(self):
        request, vectors = fixture(); prompts = p.build_prompts(request, vectors)
        self.assertEqual(tuple(prompts), p.ARMS)
        common = None
        for arm, prompt in prompts.items():
            value = body(prompt)
            self.assertEqual(value['current_program'].encode(), request.current.source)
            self.assertEqual(value['problem_description'], request.problem_description)
            value.pop('transitions')
            if common is None: common = value
            self.assertEqual(value, common)
            self.assertEqual(prompt.messages()[0]['content'], p.SYSTEM)
            self.assertEqual(prompt.seeds, prompts['C'].seeds)
        self.assertEqual(body(prompts['C'])['transitions'], [])
        self.assertEqual(common['currently_failing_public_cases'], [request.suite.case_ids[0]])

    def test_every_exact_edit_is_aligned_with_its_actual_case_pair(self):
        request, vectors = fixture(); cards = body(p.build_prompts(request, vectors)['H'])['transitions']
        self.assertEqual(len(cards), len(request.prior))
        sequence = (*request.prior, request.current)
        for card, before, after in zip(cards, sequence, sequence[1:], strict=False):
            self.assertEqual(p.apply_edits(before.source.decode(), card['edits']).encode(), after.source)
            self.assertEqual([c['case_id'] for c in card['aligned_public_cases']], list(request.suite.case_ids))
            self.assertEqual([c['before'] for c in card['aligned_public_cases']],
                             list(vectors[before.execution_key].stable_outcomes))
            self.assertEqual([c['after'] for c in card['aligned_public_cases']],
                             list(vectors[after.execution_key].stable_outcomes))
        self.assertEqual([c['state'] for c in cards[0]['aligned_public_cases']], ['gain', 'loss'])
        self.assertEqual([c['state'] for c in cards[1]['aligned_public_cases']], ['loss', 'gain'])

    def test_entire_supplied_history_is_reconstructible_backward(self):
        request, vectors = fixture()
        for arm, prompt in p.build_prompts(request, vectors).items():
            expected = {'C': (), 'H': request.prior,
                        'HS': tuple(reversed(request.prior)), 'U': request.donor_prior}[arm]
            value = body(prompt); restored = value['current_program']
            actual = []
            for card in reversed(value['transitions']):
                reverse = [dict(before_start=e['after_start'], before_end=e['after_end'],
                    after_start=e['before_start'], after_end=e['before_end'],
                    removed=e['inserted'], inserted=e['removed']) for e in card['edits']]
                restored = p.apply_edits(restored, reverse); actual.append(restored.encode())
            self.assertEqual(list(reversed(actual)), [s.source for s in expected])

    def test_shuffle_moves_source_bound_outcomes_and_rebuilds_edits(self):
        request, vectors = fixture(); value = body(p.build_prompts(request, vectors)['HS'])
        first = value['transitions'][0]
        self.assertEqual(p.apply_edits(request.prior[1].source.decode(), first['edits']).encode(), request.prior[0].source)
        self.assertEqual([c['before'] for c in first['aligned_public_cases']], ['AC', 'WA'])
        self.assertEqual([c['after'] for c in first['aligned_public_cases']], ['WA', 'AC'])
        self.assertNotIn('timestamp', p.encoded(value).decode())
        self.assertNotIn('submission_id', p.encoded(value).decode())
        self.assertEqual(value['current_program'].encode(), request.current.source)

    def test_identity_shuffle_is_retained_and_equals_history_prompt(self):
        request, vectors = fixture(); request = replace(request, hs_permutation=(0, 1))
        prompts = p.build_prompts(request, vectors)
        self.assertEqual(prompts['H'].messages(), prompts['HS'].messages())
        self.assertEqual(prompts['H'].prompt_sha256, prompts['HS'].prompt_sha256)

    def test_donor_is_only_certified_prior_anchored_to_recipient_current(self):
        request, vectors = fixture(); prompt = p.build_prompts(request, vectors)['U']
        binding = json.loads(prompt.binding_json)
        self.assertEqual(binding['supplied_source_ids'], ['d1', 'd2', 's3'])
        self.assertEqual(binding['supplied_sources'][0]['feedback_sha256'],
                         vectors[request.donor_prior[0].execution_key].seal_sha256)
        cards = body(prompt)['transitions']
        self.assertEqual(p.apply_edits(request.donor_prior[-1].source.decode(), cards[-1]['edits']).encode(), request.current.source)

    def test_current_only_model_input_is_independent_of_prior_feedback(self):
        request, vectors = fixture(); before = p.build_prompts(request, vectors)
        vectors = dict(vectors)
        vectors[request.prior[0].execution_key] = vector(request.suite, request.prior[0], ('CE', 'CE'))
        after = p.build_prompts(request, vectors)
        self.assertEqual(before['C'].messages(), after['C'].messages())
        self.assertNotEqual(before['H'].messages(), after['H'].messages())

    def test_missing_current_is_unknown_not_all_failed(self):
        request, vectors = fixture(); vectors.pop(request.current.execution_key)
        for prompt in p.build_prompts(request, vectors).values():
            value = body(prompt)
            self.assertIsNone(value['currently_failing_public_cases'])
            self.assertTrue(all(c['verdict'] is None for c in value['current_public_outcomes']))
            for card in value['transitions']:
                self.assertTrue(all(c['currently_failing'] is None for c in card['aligned_public_cases']))

    def test_incomplete_or_categorically_unstable_feedback_stays_unavailable(self):
        request, vectors = fixture(); key = request.prior[0].execution_key; original = vectors[key]
        for replacement in (replace(original, blocks=original.blocks[:3]),
                replace(original, blocks=(*original.blocks[:3],
                    replace(original.blocks[3], outcomes=((request.suite.case_ids[0], 'RE'),
                                                         (request.suite.case_ids[1], 'AC')))))):
            values = dict(vectors); values[key] = replacement
            card = body(p.build_prompts(request, values)['H'])['transitions'][0]
            self.assertIsNotNone(card['before_feedback_unavailable'])
            self.assertTrue(all(c['before'] is None and c['state'] == 'unavailable'
                                for c in card['aligned_public_cases']))

    def test_no_partial_case_subset_recovery(self):
        request, vectors = fixture(); key = request.prior[0].execution_key; original = vectors[key]
        vectors[key] = replace(original, blocks=tuple(replace(b, outcomes=b.outcomes[:1], complete=False)
                                                     for b in original.blocks))
        card = body(p.build_prompts(request, vectors)['H'])['transitions'][0]
        self.assertTrue(all(c['before'] is None for c in card['aligned_public_cases']))

    def test_nonpython_history_keeps_exact_source_changes_without_fake_feedback(self):
        request, vectors = fixture(); old = request.prior[0]
        foreign = source('s1', 'int main() { return 0; }\n', 1, language='C++')
        request = replace(request, prior=(foreign, request.prior[1])); vectors.pop(old.execution_key)
        card = body(p.build_prompts(request, vectors)['H'])['transitions'][0]
        self.assertEqual(card['before_language'], 'C++')
        self.assertEqual(card['before_feedback_unavailable'], 'unavailable_non_python')
        self.assertEqual(p.apply_edits(foreign.source.decode(), card['edits']).encode(), request.prior[1].source)

    def test_empty_suite_is_unknown_not_vacuous_success(self):
        request, _ = fixture(); suite = p.Suite('fixture', (), p.sample_set_sha(()), 'a'*64)
        request = replace(request, suite=suite)
        value = body(p.build_prompts(request, {})['H'])
        self.assertEqual(value['current_feedback_unavailable'], 'unavailable_samples')
        self.assertIsNone(value['currently_failing_public_cases'])
        self.assertEqual(len(value['transitions']), len(request.prior))

    def test_empty_history_retains_all_four_arms_and_noop_source(self):
        request, vectors = fixture(); request = replace(request, prior=(), donor_prior=(), hs_permutation=())
        vectors = {request.current.execution_key: vectors[request.current.execution_key]}
        prompts = p.build_prompts(request, vectors)
        self.assertTrue(all(body(x)['transitions'] == [] for x in prompts.values()))
        self.assertEqual(len({x.prompt_sha256 for x in prompts.values()}), 1)

    def test_future_and_cross_owner_sources_are_rejected_before_hs(self):
        request, _ = fixture()
        for prior in ((replace(request.prior[0], timestamp=4), request.prior[1]),
                      tuple(reversed(request.prior)),
                      (replace(request.prior[0], user_id='someone'), request.prior[1])):
            with self.assertRaises(ValueError): replace(request, prior=prior)
        with self.assertRaises(ValueError): replace(request, donor_prior=request.prior)
        with self.assertRaises(ValueError): replace(request, donor_prior=request.donor_prior[:1])
        with self.assertRaises(ValueError): replace(request, hs_permutation=(0, 0))

    def test_future_or_candidate_vector_is_rejected_not_ignored(self):
        request, vectors = fixture(); future = source('later', 'x=999', 4)
        vectors[future.execution_key] = vector(request.suite, future, ('AC', 'AC'))
        with self.assertRaises(ValueError): p.build_prompts(request, vectors)

    def test_exact_field_allowlists_reject_targets(self):
        request, _ = fixture()
        for key in ('next_code', 'next_verdict', 'candidate_code', 'final_ac', 'assessment'):
            payload = {f.name: getattr(request, f.name) for f in p.fields(p.Request)}
            payload[key] = 'forbidden'
            with self.assertRaises(ValueError): p.Request.from_mapping(payload)
            record = asdict(request.current); record[key] = 'forbidden'
            with self.assertRaises(ValueError): p.Source.from_mapping(record)

    def test_source_suite_runtime_and_case_order_mismatches_fail_closed(self):
        request, vectors = fixture(); key = request.current.execution_key; original = vectors[key]
        for wrong in (vector(replace(request.suite, runtime_sha256='c'*64), request.current, ('AC', 'AC')),
                      replace(original, testcase_ids=tuple(reversed(original.testcase_ids)))):
            values = dict(vectors); values[key] = wrong
            with self.assertRaises(ValueError): p.build_prompts(request, values)
        blocks = tuple(replace(b, outcomes=tuple(reversed(b.outcomes))) for b in original.blocks)
        values = dict(vectors); values[key] = replace(original, blocks=blocks)
        with self.assertRaises(ValueError): p.build_prompts(request, values)
        with self.assertRaises(ValueError): replace(request.current, source=b'changed')
        with self.assertRaises(ValueError): replace(request.suite, sample_set_sha256='0'*64)

    def test_failed_case_category_is_not_coarsened_in_history(self):
        request, vectors = fixture(); key = request.prior[0].execution_key
        vectors[key] = vector(request.suite, request.prior[0], ('RE', 'TLE'))
        card = body(p.build_prompts(request, vectors)['H'])['transitions'][0]
        self.assertEqual([c['before'] for c in card['aligned_public_cases']], ['RE', 'TLE'])
        self.assertEqual([c['state'] for c in card['aligned_public_cases']], ['gain', 'fail_fail'])

    def test_wrong_source_or_nonreleased_verdict_vector_fails(self):
        request, vectors = fixture(); key = request.prior[0].execution_key
        for wrong in (vector(request.suite, request.current, ('AC', 'AC')),
                      vector(request.suite, request.prior[0], ('MLE', 'AC'))):
            values = dict(vectors); values[key] = wrong
            with self.assertRaises(ValueError): p.build_prompts(request, values)

    def test_unknown_is_not_execution_failure_or_gain(self):
        request, vectors = fixture(); key = request.prior[0].execution_key
        vectors[key] = vector(request.suite, request.prior[0], ('UNKNOWN', 'AC'))
        first = body(p.build_prompts(request, vectors)['H'])['transitions'][0]
        self.assertEqual([c['state'] for c in first['aligned_public_cases']], ['unavailable', 'unavailable'])

    def test_seeds_and_output_reserves_match_without_claiming_input_length_parity(self):
        request, vectors = fixture(); prompts = p.build_prompts(request, vectors)
        self.assertEqual(len({x.seeds for x in prompts.values()}), 1)
        config = p.configuration()
        self.assertEqual(config['attempts_per_arm'], 2)
        self.assertEqual(config['attempts_per_recipient'], 8)
        audit = p.token_budget(dict(C=100, H=4096, HS=4097, U=8192))
        self.assertEqual(audit['H']['status'], 'runnable')
        self.assertEqual(audit['HS']['status'], 'resource_failure_no_truncation')
        for value in audit.values():
            self.assertEqual(value['attempts'], 2); self.assertEqual(value['max_new_tokens'], 4096)
            self.assertFalse(value['generation_authorized'])
        with self.assertRaises(ValueError): p.token_budget(dict(C=True, H=2, HS=2, U=2))
        with self.assertRaises(ValueError): p.token_budget(dict(C=2, H=2, HS=2))

    def test_exact_edit_roundtrips_keep_empty_lines_unicode_and_missing_final_newline(self):
        examples = [('', ''), ('', 'x'), ('x', ''), ('a\r\nb\r\n', 'a\nb\n'),
                    ('# 한글\n\nprint(1)', '# 한글\nprint(2)\n'),
                    ('a\nb\nc\nd\n', 'z\na\nc\nx\nd\n')]
        for before, after in examples:
            edits = p.exact_edits(before, after)
            self.assertEqual(p.apply_edits(before, edits), after)
            reverse = [dict(before_start=e['after_start'], before_end=e['after_end'],
                after_start=e['before_start'], after_end=e['before_end'], removed=e['inserted'],
                inserted=e['removed']) for e in edits]
            self.assertEqual(p.apply_edits(after, reverse), before)

    def test_full_history_is_not_limited_by_renderer(self):
        request, _ = fixture()
        prior = tuple(source('s'+str(i), f'x={i}\n', i+1) for i in range(20))
        donors = tuple(source('d'+str(i), f'y={i}\n', i+.5, owner='other') for i in range(20))
        current = source('now', 'print(100)\n', 30)
        request = replace(request, current=current, prior=prior, donor_prior=donors,
                          hs_permutation=tuple(reversed(range(20))))
        prompts = p.build_prompts(request, {})
        for arm in ('H', 'HS', 'U'):
            self.assertEqual(len(body(prompts[arm])['transitions']), 20)
        self.assertFalse(p.configuration()['truncate_history'])

    def test_no_launch_or_file_side_effect_is_authorized(self):
        request, vectors = fixture(); prompts = p.build_prompts(request, vectors)
        for prompt in prompts.values():
            config = json.loads(prompt.binding_json)['configuration']
            self.assertFalse(config['generation_authorized'])
            self.assertFalse(config['execution_authorized'])
            self.assertFalse(config['fitting_authorized'])
        self.assertNotIn('appropriate support', p.SYSTEM)
        self.assertNotIn('conceptual scope', p.SYSTEM)


if __name__ == '__main__':
    unittest.main()
