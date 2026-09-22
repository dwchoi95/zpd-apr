from pathlib import Path
import unittest
from scripts.run_zpd_repair_pairwise_replication import FROZEN_SOURCE
from scripts.run_zpd_repair_replication import verify_files


class PairwiseReplicationLauncher(unittest.TestCase):
    def test_frozen_feature_source_contract(self):
        verify_files(Path(__file__).resolve().parents[1],FROZEN_SOURCE)


if __name__=='__main__':unittest.main()
