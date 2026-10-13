"""Order-only preparation checks; no model, tokenizer, testcase or candidate runs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import prepare_zpd_current_last as m
from scripts import zpd_public_transition_prompt as original_prompt

PROJECT = Path(__file__).resolve().parents[1]


class MemberRelocationTests(unittest.TestCase):
    def test_exact_nested_member_text_and_escape_forms_survive(self):
        raw = '{"a":{"z": [1, 2], "current_program":"nested"},"current_program":"print(\\\"a,b{}\\\")\\r\\n\\u00e9","b":[{"x":"\\u0061"}]}'
        members = m.top_level_members(raw)
        expected = '{' + ','.join(v for k, v in members if k != 'current_program') + ',' + dict(members)['current_program'] + '}'
        moved = m.relocate_current_program(raw)
        self.assertEqual(moved, expected)
        self.assertEqual(json.loads(moved), json.loads(raw))
        self.assertEqual(len(moved), len(raw))
        self.assertEqual(m.top_level_members(moved), [x for x in members if x[0] != 'current_program']
                         + [x for x in members if x[0] == 'current_program'])
        self.assertEqual(m.relocate_current_program(moved), moved)

    def test_rejects_ambiguous_invalid_or_missing_program(self):
        for raw in ('{}', '[]', '{"x":1}', '{"current_program":1}',
                    '{"current_program":"a","current_program":"b"}',
                    '{"current_program":"a","nested":{"x":1,"x":2}}',
                    '{"current_program":"a","x":NaN}', '{"current_program":"a",}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                m.relocate_current_program(raw)

    def test_original_hash_serialization_contract_is_exact(self):
        value = [{'role': 'system', 'content': '\u00e9\r\n'}, {'content': '{"b":1,"a":2}', 'role': 'user'}]
        self.assertEqual(m.encoded(value), original_prompt.encoded(value))
        self.assertEqual(m.sha(m.encoded(value)), original_prompt.digest(original_prompt.encoded(value)))


class FrozenPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = m.load_original(PROJECT)
        cls.before = deepcopy(cls.original)
        cls.result = m.transform(cls.original)

    def test_original_pins_and_no_input_mutation(self):
        self.assertEqual(self.original, self.before)
        for name, pin in m.PINS.items():
            self.assertEqual(m.sha((PROJECT / m.BASE / name).read_bytes()), pin)
        self.assertEqual(m.sha((PROJECT / m.HASH_CONTRACT_SOURCE).read_bytes()), m.HASH_CONTRACT_SHA256)
        with patch.dict(m.PINS, {'inputs.json': '0' * 64}), self.assertRaisesRegex(ValueError, 'pin differs'):
            m.load_original(PROJECT)

    def test_only_permitted_cells_change_and_order_is_retained(self):
        restored = deepcopy(self.result)
        for old, new in zip(self.original['prompts'], restored['prompts'], strict=True):
            self.assertEqual(new['prompt_id'], old['prompt_id'])
            self.assertEqual(new['messages'][0], old['messages'][0])
            self.assertEqual(new['binding'], old['binding'])
            self.assertEqual(new['seeds'], old['seeds'])
            self.assertEqual(json.loads(new['user_json']), json.loads(old['user_json']))
            members = m.top_level_members(old['user_json'])
            self.assertEqual(m.top_level_members(new['user_json']),
                [x for x in members if x[0] != 'current_program'] + [x for x in members if x[0] == 'current_program'])
            self.assertNotEqual(new['user_json'], old['user_json'])
            self.assertEqual(len(new['user_json']), len(old['user_json']))
            self.assertEqual(new['messages'][1]['content'], new['user_json'])
            self.assertEqual(new['prompt_sha256'], original_prompt.digest(original_prompt.encoded(new['messages'])))
            new['user_json'] = old['user_json']
            new['messages'][1]['content'] = old['messages'][1]['content']
            new['prompt_sha256'] = old['prompt_sha256']
        for old, new in zip(self.original['attempts'], restored['attempts'], strict=True):
            new['prompt_sha256'] = old['prompt_sha256']
        self.assertEqual(restored, self.original)

    def test_full_population_and_updated_attempt_bindings(self):
        self.assertEqual(self.result['counts'], m.COUNTS)
        self.assertEqual(len(self.result['prompts']), 1280)
        self.assertEqual(len(self.result['attempts']), 2560)
        prompts = {p['prompt_id']: p for p in self.result['prompts']}
        for attempt in self.result['attempts']:
            p = prompts[attempt['prompt_id']]
            self.assertEqual(attempt['prompt_sha256'], p['prompt_sha256'])
            self.assertEqual(attempt['seed'], p['seeds'][attempt['draw_index']])
            self.assertEqual(list(json.loads(p['user_json']))[-1], 'current_program')
        for key in ('recipients', 'folds', 'configuration', 'public_samples'):
            self.assertEqual(self.result[key], self.original[key])

    def test_invalid_original_binding_and_population_refuse(self):
        mutations = (
            lambda x: x['prompts'][0].update(prompt_sha256='0' * 64),
            lambda x: x['prompts'][0]['messages'][1].update(content='{}'),
            lambda x: x['prompts'][0]['binding'].update(current_source_sha256='0' * 64),
            lambda x: x['attempts'][0].update(seed=-1),
            lambda x: x['attempts'][0].update(prompt_sha256='0' * 64),
            lambda x: x['prompts'].pop(),
            lambda x: x['attempts'].pop(),
            lambda x: x.update(excluded_recipients=1),
        )
        for mutate in mutations:
            value = deepcopy(self.original)
            mutate(value)
            snapshot = deepcopy(value)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                m.transform(value)
            self.assertEqual(value, snapshot)

    def test_sealed_exclusive_output_and_no_empirical_access(self):
        opened = []
        original_read_bytes = Path.read_bytes
        def read_bytes(path):
            opened.append(path)
            self.assertNotEqual(path.name, 'testcases.jsonl')
            return original_read_bytes(path)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / 'prepared'
            with patch.object(Path, 'read_bytes', read_bytes):
                complete = m.prepare(PROJECT, output)
            self.assertEqual({p.name for p in output.iterdir()}, {'inputs.json', 'manifest.json', 'COMPLETE.json'})
            self.assertEqual(json.loads((output / 'inputs.json').read_bytes()), self.result)
            self.assertEqual(json.loads((output / 'COMPLETE.json').read_bytes()), complete)
            for name, pin in complete['files_sha256'].items():
                self.assertEqual(m.sha((output / name).read_bytes()), pin)
            self.assertEqual(complete['layout_variant'], 'current_program_last_v1')
            self.assertEqual(complete['changed_prompts'], 1280)
            self.assertEqual(complete['updated_attempt_hashes'], 2560)
            self.assertTrue(complete['tokenization_required_before_generation'])
            for flag in ('generation_performed', 'execution_performed', 'fitting_performed',
                         'private_testcases_opened', 'model_promotion', 'method_improvement_established', 'history_truncated'):
                self.assertFalse(complete[flag])
            inventory = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaisesRegex(ValueError, 'no overwrite'):
                m.prepare(PROJECT, output)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, inventory)
        allowed = {PROJECT / m.BASE / name for name in m.PINS}
        allowed |= {PROJECT / name for name in (*m.SOURCE_FILES, m.HASH_CONTRACT_SOURCE)}
        self.assertEqual(set(opened), allowed)


if __name__ == '__main__':
    unittest.main()
