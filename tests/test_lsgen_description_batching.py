from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import torch

from src.repair.lsgen import _RepairPair, _describe_pairs


class _Batch(dict):
    def to(self, _device: object) -> "_Batch":
        return self


class _Tokenizer:
    pad_token_id = 0
    eos_token_id = 2

    def apply_chat_template(self, *_args: object, **_kwargs: object) -> str:
        return "prompt"

    def __call__(self, prompts: list[str], **_kwargs: object) -> _Batch:
        return _Batch(
            input_ids=torch.tensor([[1, 2] for _prompt in prompts]),
            attention_mask=torch.tensor([[1, 1] for _prompt in prompts]),
        )

    def decode(self, tokens: object, **_kwargs: object) -> str:
        return f"description-{len(tokens)}"  # type: ignore[arg-type]


class _Model:
    device = "cpu"
    config = SimpleNamespace(max_position_embeddings=4096)

    def __init__(self) -> None:
        self.batch_sizes: list[int] = []
        self.generation_budgets: list[int] = []

    def generate(self, **encoded: object) -> torch.Tensor:
        input_ids = encoded["input_ids"]
        assert isinstance(input_ids, torch.Tensor)
        batch_size = input_ids.shape[0]
        self.batch_sizes.append(batch_size)
        self.generation_budgets.append(int(encoded["max_new_tokens"]))
        if batch_size > 1:
            raise torch.OutOfMemoryError("synthetic batch OOM")
        suffix = torch.tensor([[3]], dtype=input_ids.dtype)
        return torch.cat([input_ids, suffix], dim=1)


class LSGenDescriptionBatchingTest(unittest.TestCase):
    def test_oom_batch_is_recursively_split_and_streamed(self) -> None:
        pairs = [
            _RepairPair(
                pair_id=f"pair-{index}",
                problem_id="p",
                user_id=f"u-{index}",
                buggy_code="print(0)",
                correct_code="print(1)",
                retention=1.0,
            )
            for index in range(4)
        ]
        model = _Model()
        with TemporaryDirectory() as directory:
            cache_path = Path(directory) / "descriptions.jsonl"
            descriptions = _describe_pairs(
                pairs,
                tokenizer=_Tokenizer(),
                model=model,
                batch_size=4,
                cache_path=cache_path,
            )

            self.assertEqual(set(descriptions), {pair.pair_id for pair in pairs})
            self.assertEqual(len(cache_path.read_text().splitlines()), 4)
            self.assertEqual(model.batch_sizes[0], 4)
            self.assertEqual(model.batch_sizes.count(1), 4)
            self.assertEqual(set(model.generation_budgets), {512})


if __name__ == "__main__":
    unittest.main()
