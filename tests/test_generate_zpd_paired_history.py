import json
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import generate_zpd_paired_history as mod


class GenerationTests(unittest.TestCase):
    def fixture(self, root):
        release = dict(adapter_arm_map=dict(mod.ADAPTER_ARM_MAP), gpu_versions={},
                       model_sha256={}, base_model='sealed-base')
        for arm in ('C', 'H'):
            directory = root / arm; directory.mkdir()
            release['adapter_' + arm] = str(directory)
            for name in ('adapter_config.json', 'adapter_model.safetensors'):
                path = directory / name; path.write_bytes((arm + name).encode())
                release['model_sha256'][str(path)] = mod.core.sha_file(path)
        report = dict(frozen=True)
        release['tokenization_sha256'] = mod.core.sha(mod.core.encoded(report))
        attempts, rendered = [], {}
        for i in range(320):
            for arm in mod.core.ARMS:
                prompt = f'p-{i}-{arm}'
                rendered[prompt] = dict(text=prompt, tokens=1, fits=not (i == 0 and arm == 'H'),
                                        rendered_sha256='a' * 64)
                for draw in (0, 1):
                    attempts.append(dict(attempt_id=f'{i}-{arm}-{draw}', example_id=str(i),
                        arm=arm, prompt_id=prompt, draw_index=draw, seed=100 + draw))
        return release, dict(attempts=attempts), rendered, report

    def test_mixed_requests_preserve_all_slots_and_per_prompt_roles(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); release, inputs, rendered, report = self.fixture(root)
            out = root / 'out'; out.mkdir(); calls = []
            class FakeModel:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs
                    assert kwargs['max_loras'] == 2

                def generate(self, prompts, sampling, *, lora_request, use_tqdm):
                    calls.append(list(zip(prompts, lora_request)))
                    for prompt, request, params in zip(prompts, lora_request, sampling, strict=True):
                        arm = prompt.split('-')[-1]
                        role = mod.ADAPTER_ARM_MAP[arm]
                        assert request.lora_path == release['adapter_' + role]
                        assert params.max_tokens == 4096 and params.n == 1
                    return [SimpleNamespace(outputs=[SimpleNamespace(text='print(1)', finish_reason='stop')])
                            for _ in prompts]
            vllm = ModuleType('vllm'); vllm.LLM = FakeModel; vllm.SamplingParams = lambda **kw: SimpleNamespace(**kw)
            req = ModuleType('vllm.lora.request')
            req.LoRARequest = lambda name, index, path: SimpleNamespace(lora_name=name, lora_int_id=index, lora_path=path)
            with patch.dict(sys.modules, {'vllm': vllm, 'vllm.lora': ModuleType('vllm.lora'), 'vllm.lora.request': req}), \
                 patch.object(mod.core, 'render_inputs', return_value=(rendered, report)), \
                 patch.object(mod.core, 'envelope'):
                mod.generation(inputs, release, out)
            rows = json.loads((out / 'attempts.json').read_bytes())
            self.assertEqual(len(rows), 2560)
            self.assertEqual(sum(r['finish_reason'] == 'prompt_overflow' for r in rows), 2)
            self.assertEqual(sum(len(batch) for batch in calls), 2558)
            for row in rows:
                self.assertEqual(row['adapter_role'], mod.ADAPTER_ARM_MAP[row['arm']])
            self.assertEqual(json.loads((out / 'STATUS.json').read_bytes())['completed_examples'], 320)

    def test_reject_assignment_or_same_adapter_or_file_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); release, *_ = self.fixture(root)
            good = dict(release['adapter_arm_map'])
            release['adapter_arm_map']['HS'] = 'C'
            with self.assertRaisesRegex(ValueError, 'assignment'): mod.adapter_roles(release)
            release['adapter_arm_map'] = good
            original = release['adapter_H']; release['adapter_H'] = release['adapter_C']
            with self.assertRaisesRegex(ValueError, 'separately'): mod.adapter_roles(release)
            release['adapter_H'] = original
            (Path(original) / 'adapter_config.json').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'sealed'): mod.adapter_roles(release)

    def test_frozen_tokens_checked_before_model_construction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve(); release, inputs, rendered, report = self.fixture(root)
            out = root / 'out'; out.mkdir()
            release['tokenization_sha256'] = '0' * 64
            with patch.object(mod.core, 'render_inputs', return_value=(rendered, report)):
                with self.assertRaisesRegex(ValueError, 'tokenization'):
                    mod.generation(inputs, release, out)


if __name__ == '__main__':
    unittest.main()
