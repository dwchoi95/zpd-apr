import tempfile
import unittest
from pathlib import Path

from src.experiments.codeworkout_data import _pickle


class CodeWorkoutDataTest(unittest.TestCase):
    def test_refuses_a_pickle_other_than_the_pinned_release(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "dataset_granular_all.pkl").write_bytes(b"not the release")
            with self.assertRaisesRegex(ValueError, "unexpected TIKTOC pickle"):
                _pickle(Path(tmp), Path(tmp))


if __name__ == "__main__":
    unittest.main()
