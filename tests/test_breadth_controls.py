from __future__ import annotations

import unittest
from pathlib import Path


class BreadthControlProtocolTest(unittest.TestCase):
    def test_runner_fixes_all_requested_cells(self) -> None:
        runner = Path("scripts/run_fse2027_breadth_controls_remote.sh").read_text()
        self.assertIn("for temperature in 0.2 0.4 0.6 0.8 1.0", runner)
        self.assertIn("checkpoint-stochastic", runner)
        self.assertIn("base-stochastic", runner)
        self.assertIn("--sampling-seed 4101 --sampling-seed 4102 --sampling-seed 4103", runner)
        self.assertIn("--gpu-memory-utilization 0.82", runner)

    def test_generator_allows_base_model_or_adapter(self) -> None:
        generator = Path("scripts/generate_vllm_stochastic_candidates.py").read_text()
        self.assertIn('parser.add_argument("--adapter", type=Path)', generator)
        self.assertIn('"adapter": None if args.adapter is None', generator)


if __name__ == "__main__":
    unittest.main()
