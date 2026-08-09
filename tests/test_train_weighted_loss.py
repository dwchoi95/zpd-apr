import unittest

import torch
import torch.nn.functional as functional
from accelerate.utils.operations import convert_outputs_to_fp32

from src.repair.train import (
    _edit_weighted_causal_loss,
    _forward_without_output_fp32_conversion,
)


class EditWeightedCausalLossTests(unittest.TestCase):
    def test_matches_flattened_reference_loss_and_gradients(self) -> None:
        torch.manual_seed(2027)
        reference_logits = torch.randn(3, 7, 11, dtype=torch.float64, requires_grad=True)
        optimized_logits = reference_logits.detach().clone().requires_grad_(True)
        labels = torch.randint(0, 11, (3, 7))
        labels[0, :3] = -100
        labels[1, 4] = -100
        weights = torch.rand(3, 7, dtype=torch.float64) + 0.5

        shift_logits = reference_logits[..., :-1, :].contiguous()
        shift_labels = labels[..., 1:].contiguous()
        shift_weights = weights[..., 1:].contiguous()
        valid = shift_labels.ne(-100)
        token_loss = functional.cross_entropy(
            shift_logits.view(-1, shift_logits.size(-1)),
            shift_labels.view(-1),
            reduction="none",
            ignore_index=-100,
        ).view_as(shift_labels)
        effective_weights = shift_weights * valid
        reference = (token_loss * effective_weights).sum() / effective_weights.sum()
        optimized = _edit_weighted_causal_loss(optimized_logits, labels, weights)

        reference.backward()
        optimized.backward()
        torch.testing.assert_close(optimized, reference, rtol=1e-12, atol=1e-12)
        torch.testing.assert_close(
            optimized_logits.grad,
            reference_logits.grad,
            rtol=1e-12,
            atol=1e-12,
        )

    def test_all_ignored_targets_produce_differentiable_zero(self) -> None:
        logits = torch.randn(2, 4, 5, requires_grad=True)
        labels = torch.full((2, 4), -100)
        weights = torch.ones(2, 4)

        loss = _edit_weighted_causal_loss(logits, labels, weights)
        loss.backward()

        self.assertEqual(loss.item(), 0.0)
        torch.testing.assert_close(logits.grad, torch.zeros_like(logits))

    def test_bfloat16_uses_fp32_row_loss(self) -> None:
        torch.manual_seed(2028)
        logits = torch.randn(2, 5, 7, dtype=torch.bfloat16, requires_grad=True)
        labels = torch.randint(0, 7, (2, 5))
        weights = torch.rand(2, 5)
        expected_parts = []
        expected_weight = weights[:, 1:].sum()
        for row in range(2):
            expected_parts.append(
                (
                    functional.cross_entropy(
                        logits[row, :-1].float(),
                        labels[row, 1:],
                        reduction="none",
                    )
                    * weights[row, 1:]
                ).sum()
            )

        actual = _edit_weighted_causal_loss(logits, labels, weights)

        torch.testing.assert_close(actual, sum(expected_parts) / expected_weight)

    def test_accelerate_conversion_is_deferred(self) -> None:
        class FakeModel:
            pass

        model = FakeModel()
        model.forward = convert_outputs_to_fp32(
            lambda **_inputs: torch.ones(2, dtype=torch.bfloat16)
        )

        converted = model.forward()
        preserved = _forward_without_output_fp32_conversion(model, {})

        self.assertEqual(converted.dtype, torch.float32)
        self.assertEqual(preserved.dtype, torch.bfloat16)


if __name__ == "__main__":
    unittest.main()
