import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_fse2027_scale_replication import selection_audit  # noqa: E402


class ScaleReplicationFairSelectionTest(unittest.TestCase):
    def test_scale_generation_batch_is_configurable_and_defaults_to_eight(self) -> None:
        root = Path(__file__).resolve().parents[1]
        main_script = (root / "scripts/run_fse2027_scale_replication_remote.sh").read_text()
        a3_script = (root / "scripts/run_fse2027_scale_a3_remote.sh").read_text()
        expected = "GENERATION_BATCH_SIZE=${ZPD_SCALE_GENERATION_BATCH_SIZE:-8}"
        self.assertIn(expected, main_script)
        self.assertIn(expected, a3_script)
        self.assertIn('--batch-size "${GENERATION_BATCH_SIZE}"', main_script)
        self.assertIn('--batch-size "${GENERATION_BATCH_SIZE}"', a3_script)

    def test_accepts_matched_nine_choose_three_search_spaces(self) -> None:
        mixed = {
            "candidate_checkpoint_count": 9,
            "feasible_unconstrained_size_three_portfolios": 84,
        }
        answer = {
            "candidate_checkpoint_count": 9,
            "feasible_portfolios": 84,
        }
        result = selection_audit(mixed, answer)
        self.assertTrue(result["candidate_pool_sizes_matched"])
        self.assertTrue(result["portfolio_search_spaces_matched"])

    def test_rejects_candidate_pool_size_mismatch(self) -> None:
        mixed = {
            "candidate_checkpoint_count": 9,
            "feasible_unconstrained_size_three_portfolios": 84,
        }
        answer = {
            "candidate_checkpoint_count": 8,
            "feasible_portfolios": 56,
        }
        with self.assertRaisesRegex(ValueError, "candidate pool sizes differ"):
            selection_audit(mixed, answer)


if __name__ == "__main__":
    unittest.main()
