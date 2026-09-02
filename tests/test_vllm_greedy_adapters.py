from __future__ import annotations

import unittest

from scripts.generate_vllm_greedy_adapters import parse_adapter


class VllmGreedyAdaptersTest(unittest.TestCase):
    def test_adapter_mapping_parser(self) -> None:
        name, path = parse_adapter("Answer2028=/tmp/answer")
        self.assertEqual(name, "Answer2028")
        self.assertEqual(str(path), "/tmp/answer")

    def test_adapter_mapping_rejects_malformed_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "NAME=PATH"):
            parse_adapter("Answer2028")


if __name__ == "__main__":
    unittest.main()
