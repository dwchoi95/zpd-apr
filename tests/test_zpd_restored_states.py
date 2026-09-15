from pathlib import Path
import unittest

from scripts.audit_zpd_restored_states import audit
from scripts.build_zpd_legacy_prefix_inventory import build
from tests import test_zpd_legacy_prefix_inventory as fixtures


class RestoredStateTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.LegacyInventoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        build(self.fixture.archive, self.fixture.retained, self.fixture.output)
        self.destination = Path(self.fixture.temp.name) / 'state-audit.json'

    def test_extracts_repeats_without_opening_labels(self):
        # Synthetic fixture only: label and reference files deliberately unavailable.
        (self.fixture.output / 'labels.jsonl').unlink()
        (self.fixture.output / 'references.jsonl').unlink()
        result = audit(self.fixture.output, self.destination)
        self.assertEqual(result['counts']['prefixes'], 2)
        self.assertEqual(result['counts']['prefixes_with_exact_current_code_seen_before'], 1)
        self.assertEqual(result['counts']['prefixes_with_unknown_current_execution'], 2)
        self.assertFalse(result['labels_opened'])

    def test_changed_observed_data_rejected(self):
        path = self.fixture.output / 'features.jsonl'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            audit(self.fixture.output, self.destination)

    def test_no_input_overwrite(self):
        with self.assertRaisesRegex(ValueError, 'outside input'):
            audit(self.fixture.output, self.fixture.output / 'features.jsonl')
