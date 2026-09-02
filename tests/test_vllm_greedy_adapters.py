from __future__ import annotations

import unittest
from pathlib import Path

from scripts.generate_vllm_greedy_adapters import parse_adapter


class VllmGreedyAdaptersTest(unittest.TestCase):
    def test_adapter_mapping_parser(self) -> None:
        name, path = parse_adapter("Answer2028=/tmp/answer")
        self.assertEqual(name, "Answer2028")
        self.assertEqual(str(path), "/tmp/answer")

    def test_adapter_mapping_rejects_malformed_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "NAME=PATH"):
            parse_adapter("Answer2028")

    def test_generator_retains_all_sequential_adapters_in_cpu_cache(self) -> None:
        source = Path("scripts/generate_vllm_greedy_adapters.py").read_text()
        self.assertIn("max_loras=1", source)
        self.assertIn("max_cpu_loras=len(adapters)", source)


if __name__ == "__main__":
    unittest.main()
