import unittest

from scripts.check_repair_pilot import smoke_report


class RepairPilotSmokeTests(unittest.TestCase):
    def test_end_to_end_synthetic_only_and_reproducible(self):
        report = smoke_report()
        self.assertEqual(report, smoke_report())
        self.assertFalse(report["empirical_performance_measured"])
        self.assertFalse(report["trained"])
        self.assertFalse(report["candidate_programs_executed"])
        self.assertEqual(report["attempts"], 8)
        self.assertEqual(report["unique_candidates_including_noop"], 3)


if __name__ == "__main__":
    unittest.main()
