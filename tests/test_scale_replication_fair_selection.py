import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_fse2027_scale_replication import selection_audit  # noqa: E402


class ScaleReplicationFairSelectionTest(unittest.TestCase):
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
