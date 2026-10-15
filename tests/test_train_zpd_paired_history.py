"""Synthetic encoding/accounting/Trainer tests; no downloads or candidate runs."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import train_zpd_paired_history as m


class Tokenizer:
    eos_token_id = 0
    pad_token_id = None

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        assert tokenize is False and add_generation_prompt is True
        return '|'.join(r['content'] for r in messages) + '|assistant:'

    def __call__(self, text, *, add_special_tokens, truncation):
        assert add_special_tokens is False and truncation is False
        return {'input_ids': [ord(c) + 1 for c in text]}


def record(eid='e0', prompt='current', target='print(1)\r\n  '):
    return dict(example_id=eid, messages=[dict(role='system', content='repair'),
        dict(role='user', content=prompt)], current_code='print(0)\r\n', target_code=target,
        hidden_audit_label='NOT_A_MODEL_INPUT')


def pair(n=3, prefix='e'):
    c = [record(prefix + str(i)) for i in range(n)]
    h = [record(prefix + str(i), 'prior\ncurrent' + 'x' * i) for i in range(n)]
    return m.paired_preflight(c, h, Tokenizer())


class EncodingTests(unittest.TestCase):
    def test_public_uncapped_encoding_target_eos_mask_and_hashes(self):
        row = record(); feature = m.encode_record(row, Tokenizer())
        n = feature['prompt_tokens']; target = [ord(c) + 1 for c in 'print(1)'] + [0]
        self.assertEqual(feature['input_ids'][n:], target)
        self.assertEqual(feature['labels'], [-100] * n + target)
        self.assertEqual(feature['loss_weights'], [0.] * n + [1.] * len(target))
        self.assertEqual(feature['output_tokens'], len(target))
        self.assertEqual(feature['full_tokens'], n + len(target))
        self.assertEqual(feature['target_raw_sha256'], m.sha(row['target_code'].encode()))
        self.assertEqual(feature['target_normalized_sha256'], m.sha(b'print(1)'))
        self.assertEqual(feature['target_token_ids_sha256'], m.sha(m.encoded(target)))
        self.assertNotIn('hidden_audit_label', feature)
        altered = deepcopy(row); altered['hidden_audit_label'] = 'different'
        self.assertEqual(m.encode_record(altered, Tokenizer()), feature)

    def test_complete_pair_same_targets_different_prompts_and_raw_bytes(self):
        prepared = pair(); report = m.validate_preflight(prepared)
        self.assertEqual(report['examples'], 3)
        self.assertFalse(report['truncation']); self.assertEqual(report['excluded_examples'], 0)
        for pin in report['per_example']:
            self.assertGreater(pin['arms']['H']['prompt_tokens'], pin['arms']['C']['prompt_tokens'])
        self.assertEqual(report['pad_token_id'], 0)
        self.assertEqual(report['order_sha256'], m.sha(m.encoded(['e0', 'e1', 'e2'])))

    def test_exact_cap_boundary_accepts_all_three_limits(self):
        c = record(); h = record(prompt='prior current')
        cf, hf = m.encode_record(c, Tokenizer()), m.encode_record(h, Tokenizer())
        caps = dict(max_input_tokens=max(cf['prompt_tokens'], hf['prompt_tokens']),
                    max_output_tokens=cf['output_tokens'], max_full_tokens=hf['full_tokens'])
        self.assertEqual(m.paired_preflight([c], [h], Tokenizer(), **caps)['report']['examples'], 1)
        for key in caps:
            smaller = dict(caps); smaller[key] -= 1
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'overlength'):
                m.paired_preflight([c], [h], Tokenizer(), **smaller)

    def test_public_encoder_does_not_filter_long_records(self):
        feature = m.encode_record(record(prompt='x' * 5000), Tokenizer())
        self.assertGreater(feature['prompt_tokens'], 4096)
        with self.assertRaisesRegex(ValueError, 'overlength'):
            m.paired_preflight([record()], [record(prompt='x' * 5000)], Tokenizer())

    def test_pair_identity_order_current_and_raw_target_are_strict(self):
        c = [record('a'), record('b')]
        mutations = []
        h = deepcopy(c); h.reverse(); mutations.append(h)
        h = deepcopy(c); h[1]['example_id'] = 'a'; mutations.append(h)
        h = deepcopy(c); h[0]['current_code'] += '\n'; mutations.append(h)
        h = deepcopy(c); h[0]['target_code'] = h[0]['target_code'].rstrip(); mutations.append(h)
        mutations.append(c[:1])
        for h in mutations:
            with self.subTest(h=h), self.assertRaises(ValueError):
                m.paired_preflight(c, h, Tokenizer())
        with self.assertRaises(ValueError): m.paired_preflight([], [], Tokenizer())

    def test_nonidentical_encoded_targets_refused(self):
        class UnstableTokenizer(Tokenizer):
            calls = 0
            def __call__(self, text, **kwargs):
                result = super().__call__(text, **kwargs)
                if text == 'print(1)':
                    self.calls += 1
                    result['input_ids'].append(self.calls)
                return result
        with self.assertRaisesRegex(ValueError, 'encoded targets differ'):
            m.paired_preflight([record()], [record()], UnstableTokenizer())

    def test_messages_no_assistant_labels_or_coercion(self):
        for field, value in [('example_id', 3), ('current_code', None), ('target_code', True)]:
            r = record(); r[field] = value
            with self.assertRaises(ValueError): m.encode_record(r, Tokenizer())
        r = record(); r['messages'].append(dict(role='assistant', content='target'))
        with self.assertRaises(ValueError): m.encode_record(r, Tokenizer())

    def test_tampered_encoded_pin_and_mask_rejected(self):
        for change in ('token', 'id', 'mask', 'target_hash'):
            p = pair()
            if change == 'token': p['encoded']['H'][0]['input_ids'][0] += 1
            elif change == 'id': p['encoded']['H'][0]['example_id'] = 'wrong'
            elif change == 'target_hash': p['report']['per_example'][0]['target_token_ids_sha256'] = '0' * 64
            else:
                p['encoded']['H'][0]['labels'][0] = 3
                p['report']['encoded_sha256']['H'] = m.sha(m.encoded(p['encoded']['H']))
            with self.subTest(change=change), self.assertRaises(ValueError): m.validate_preflight(p)

    def test_invalid_pair_fails_before_model_and_before_output(self):
        p = pair(); p['encoded']['C'][0]['input_ids'][0] += 1
        with tempfile.TemporaryDirectory() as tmp, patch.object(m, 'load_fresh_model') as load:
            with self.assertRaises(ValueError):
                m.train_arm('C', p, pair(prefix='v'), base_model='never-load', output_dir=Path(tmp)/'out')
            load.assert_not_called(); self.assertFalse((Path(tmp)/'out').exists())


class FakeTrainer:
    def __init__(self, *args, **kwargs):
        self.model_accepts_loss_kwargs = True
        self.train_dataset = kwargs.get('train_dataset')
        self.fail = False

    def training_step(self, model, inputs, num_items_in_batch=None):
        assert 'example_ids' not in inputs
        if self.fail: raise RuntimeError('synthetic backward failure')
        return 7


class AccountingTests(unittest.TestCase):
    def test_successful_training_steps_only_and_exact_remainder(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = m.ConsumptionJournal(tmp, 'H', ['a', 'b', 'c'])
            try:
                trainer = m.trainer_class(FakeTrainer)(journal=journal)
                self.assertFalse(trainer.model_accepts_loss_kwargs)
                trainer.training_step(None, {'example_ids': ['a', 'b']}, 2)
                trainer.fail = True
                with self.assertRaises(RuntimeError): trainer.training_step(None, {'example_ids': ['c']}, 1)
                self.assertEqual(journal.consumed, ['a', 'b'])
                with self.assertRaisesRegex(ValueError, 'incomplete'): journal.finish()
                trainer.fail = False; trainer.training_step(None, {'example_ids': ['c']}, 1)
                status = journal.finish()
                self.assertEqual(status['completed_examples'], 3)
                self.assertEqual(status['successful_training_microbatches'], 2)
                self.assertEqual(status['consumed_order_sha256'], status['planned_order_sha256'])
                events = [json.loads(s) for s in (Path(tmp)/'consumed-examples.jsonl').read_text().splitlines()]
                self.assertEqual([x for e in events for x in e['example_ids']], ['a', 'b', 'c'])
                self.assertFalse((Path(tmp)/'STATUS.json.partial').exists())
            finally: journal.close()

    def test_reordered_repeated_extra_examples_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = m.ConsumptionJournal(tmp, 'C', ['a', 'b'])
            try:
                for ids in ([], ['b'], ['a', 'b', 'c']):
                    with self.assertRaises(ValueError): journal.commit(ids)
                journal.commit(['a'])
                with self.assertRaises(ValueError): journal.commit(['a'])
            finally: journal.close()

    def test_fixed_config_no_best_checkpoint_or_adaptive_batching(self):
        self.assertEqual(m.CONFIG['num_train_epochs'], 1)
        self.assertEqual(m.CONFIG['per_device_train_batch_size'], 2)
        self.assertEqual(m.CONFIG['gradient_accumulation_steps'], 8)
        self.assertFalse(m.CONFIG['group_by_length'])
        self.assertEqual(m.CONFIG['eval_strategy'], 'epoch')
        self.assertEqual(m.CONFIG['save_strategy'], 'no')
        self.assertFalse(m.CONFIG['load_best_model_at_end'])
        self.assertEqual(m.LORA['r'], 16)
        self.assertEqual(len(m.LORA['target_modules']), 7)

    def test_longest_common_batch_is_arm_independent_and_fixed_size(self):
        p = pair(4)
        self.assertEqual(m.longest_paired_batch(p), [3, 2])
        self.assertEqual([p['encoded'][a][i]['example_id'] for a in m.ARMS for i in [3, 2]],
                         ['e3', 'e2', 'e3', 'e2'])
        with self.assertRaisesRegex(ValueError, 'full fixed microbatch'): m.longest_paired_batch(pair(1))

    def test_output_refuses_existing_or_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()/'out'; m._new_output(output)
            with self.assertRaises(ValueError): m._new_output(output)
            link = Path(tmp)/'link'; link.symlink_to(output, target_is_directory=True)
            with self.assertRaises(ValueError): m._new_output(link)

    def test_train_validation_overlap_refused_before_loading(self):
        with patch.object(m, 'load_fresh_model') as load:
            with self.assertRaisesRegex(ValueError, 'overlap'):
                m.train_arm('C', pair(), pair(), base_model='no', output_dir='never-created')
            load.assert_not_called()


class SealingTests(unittest.TestCase):
    def test_success_saves_only_final_adapter_and_exclusive_provisional_seal(self):
        class Model:
            def save_pretrained(self, folder):
                folder.mkdir()
                (folder/'adapter_model.safetensors').write_bytes(b'synthetic-adapter')
                (folder/'adapter_config.json').write_text('{}')
        class Tok:
            eos_token_id = 0; pad_token_id = 0
            def save_pretrained(self, folder):
                (folder/'tokenizer_config.json').write_text('{}')
        class SuccessfulTrainer:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.state = SimpleNamespace(epoch=1.0, global_step=1,
                    log_history=[dict(epoch=1.0, eval_loss=.4)])
            def train(self, *, resume_from_checkpoint):
                assert resume_from_checkpoint is None
                journal = self.kwargs['journal']
                for offset in range(0, len(journal.ids), 2):
                    journal.commit(journal.ids[offset:offset+2])
        fake_transformers = SimpleNamespace(TrainingArguments=lambda **kwargs: SimpleNamespace(**kwargs))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()/'new'
            with patch.dict(sys.modules, transformers=fake_transformers), \
                    patch.object(m, 'load_fresh_model', return_value=(Model(), Tok())) as load, \
                    patch.object(m, 'trainer_class', return_value=SuccessfulTrainer), \
                    patch.object(m, 'trainable_fingerprint', return_value={'sha256': 'initial'}), \
                    patch.object(m, '_versions', return_value={'synthetic': '1'}):
                summary = m.train_arm('H', pair(), pair(prefix='v'), base_model='pinned-base', output_dir=output)
                load.assert_called_once_with('pinned-base', 2027)
                with self.assertRaisesRegex(ValueError, 'no resume'):
                    m.train_arm('H', pair(), pair(prefix='v'), base_model='pinned-base', output_dir=output)
            self.assertEqual(summary['checkpoint_selection'], 'fixed_final_epoch')
            self.assertEqual(summary['coverage']['completed_examples'], 3)
            self.assertEqual(summary['validation_role'], 'descriptive_only_no_checkpoint_selection')
            self.assertFalse(summary['model_promotion'])
            seal = json.loads((output/'COMPLETE.json').read_text())
            self.assertTrue(seal['provisional_until_normal_exit'])
            self.assertEqual(set(seal['files_sha256']),
                             {str(p.relative_to(output)) for p in output.rglob('*') if p.is_file()} - {'COMPLETE.json'})
            for name, pin in seal['files_sha256'].items():
                self.assertEqual(m.sha((output/name).read_bytes()), pin)
            self.assertFalse((output/'FAILED.json').exists())

    def test_failed_model_load_seals_no_adapter_or_completion(self):
        fake_transformers = SimpleNamespace(TrainingArguments=object)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve()/'failure'
            with patch.dict(sys.modules, transformers=fake_transformers), \
                    patch.object(m, 'load_fresh_model', side_effect=RuntimeError('synthetic capacity failure')):
                with self.assertRaises(RuntimeError):
                    m.train_arm('C', pair(), pair(prefix='v'), base_model='no', output_dir=output)
            self.assertEqual(json.loads((output/'FAILED.json').read_text())['status'], 'failed')
            self.assertFalse((output/'adapter').exists())
            self.assertFalse((output/'COMPLETE.json').exists())


try:
    import torch
    from transformers import Trainer, TrainingArguments
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@unittest.skipUnless(HAS_TORCH, 'optional local torch/transformers required for synthetic integration')
class SyntheticTrainerTests(unittest.TestCase):
    def test_real_one_epoch_loop_preserves_partial_batch_and_descriptive_validation(self):
        from transformers.modeling_outputs import CausalLMOutput
        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.lora_A = torch.nn.Parameter(torch.randn(5, 5))
            def forward(self, input_ids, attention_mask=None, labels=None, **kwargs):
                return CausalLMOutput(logits=self.lora_A[input_ids])
        rows = [dict(example_id=str(i), input_ids=[i+1, 2, 3], attention_mask=[1, 1, 1],
                     labels=[-100, 2, 3], loss_weights=[0., 1., 1.]) for i in range(3)]
        valid = [dict(r, example_id='v' + r['example_id']) for r in rows]
        with tempfile.TemporaryDirectory() as tmp:
            journal = m.ConsumptionJournal(tmp, 'H', ['0', '1', '2'])
            try:
                args = TrainingArguments(output_dir=tmp, use_cpu=True, report_to=[],
                    per_device_train_batch_size=2, per_device_eval_batch_size=2,
                    gradient_accumulation_steps=8, num_train_epochs=1,
                    eval_strategy='epoch', save_strategy='no', load_best_model_at_end=False,
                    remove_unused_columns=False, group_by_length=False, disable_tqdm=True)
                trainer = m.trainer_class(Trainer)(model=TinyModel(), args=args,
                    train_dataset=m.FeatureDataset(rows), eval_dataset=m.FeatureDataset(valid),
                    data_collator=m.JournalCollator(0), journal=journal)
                trainer.train(resume_from_checkpoint=None)
                journal.finish()
                self.assertEqual(trainer.state.epoch, 1.0)
                self.assertEqual(trainer.state.global_step, 1)
                self.assertEqual(journal.batches, 2)
                self.assertEqual(journal.consumed, ['0', '1', '2'])
                self.assertEqual(len([r for r in trainer.state.log_history if 'eval_loss' in r]), 1)
                self.assertIsNone(trainer.state.best_model_checkpoint)
            finally: journal.close()

    def test_sequential_sampler_and_metadata_stripping(self):
        rows = pair()['encoded']['H']
        trainer = m.trainer_class(FakeTrainer)(train_dataset=m.FeatureDataset(rows))
        self.assertEqual(list(trainer._get_train_sampler()), [0, 1, 2])
        self.assertEqual(list(trainer._get_eval_sampler(m.FeatureDataset(rows))), [0, 1, 2])
        batch = m.JournalCollator(0)(rows[:2])
        self.assertEqual(batch['example_ids'], ['e0', 'e1'])
        self.assertEqual(batch['input_ids'].shape[0], 2)

    def test_real_trainer_accumulation_normalizes_custom_microbatch_means(self):
        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.lora_A = torch.nn.Parameter(torch.randn(5, 5))
            def forward(self, input_ids, attention_mask=None, **kwargs):
                self.assert_no_audit = not kwargs
                return SimpleNamespace(logits=self.lora_A[input_ids])
        torch.manual_seed(2027)
        model = TinyModel(); reference = deepcopy(model)
        rows = [dict(example_id=str(i), input_ids=[i+1, 2, 3], attention_mask=[1, 1, 1],
                     labels=[-100, 2, 3], loss_weights=[0., 1., 1.]) for i in range(2)]
        with tempfile.TemporaryDirectory() as tmp:
            journal = m.ConsumptionJournal(tmp, 'C', ['0', '1'])
            try:
                args = TrainingArguments(output_dir=tmp, use_cpu=True, report_to=[],
                    per_device_train_batch_size=1, gradient_accumulation_steps=2,
                    remove_unused_columns=False)
                trainer = m.trainer_class(Trainer)(model=model, args=args,
                    train_dataset=m.FeatureDataset(rows), data_collator=m.JournalCollator(0), journal=journal)
                self.assertFalse(trainer.model_accepts_loss_kwargs)
                trainer.current_gradient_accumulation_steps = 2
                for row in rows:
                    trainer.training_step(model, m.JournalCollator(0)([row]), num_items_in_batch=torch.tensor(4))
                full = m._TokenCollator(0)(rows)
                loss = m._edit_weighted_causal_loss(reference(full['input_ids']).logits,
                                                     full['labels'], full['loss_weights'])
                loss.backward()
                torch.testing.assert_close(model.lora_A.grad, reference.lora_A.grad)
                self.assertTrue(model.assert_no_audit)
                journal.finish()
            finally: journal.close()

    def test_fingerprint_reproducible_and_sensitive_to_adapter_not_frozen_base(self):
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.lora_A = torch.nn.Parameter(torch.tensor([[1., 2.]]))
                self.base = torch.nn.Parameter(torch.tensor([8.]), requires_grad=False)
        model = Tiny(); first = m.trainable_fingerprint(model)
        self.assertEqual(first, m.trainable_fingerprint(deepcopy(model)))
        with torch.no_grad(): model.base.add_(1)
        self.assertEqual(first, m.trainable_fingerprint(model))
        with torch.no_grad(): model.lora_A.add_(1)
        self.assertNotEqual(first['sha256'], m.trainable_fingerprint(model)['sha256'])


if __name__ == '__main__':
    unittest.main()
