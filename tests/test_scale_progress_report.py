import tempfile
import unittest
from pathlib import Path

from scripts.report_fse2027_scale_progress import summarize


class ScaleProgressReportTest(unittest.TestCase):
    def test_counts_completed_and_active_examples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            datasets = root / "datasets"
            checkpoints = root / "checkpoints"
            datasets.mkdir()
            for mode, count in (("progress", 5), ("strict", 3), ("answer", 7)):
                (datasets / f"train-{mode}.jsonl").write_text(
                    "{}\n" * count, encoding="utf-8"
                )
            summary = checkpoints / "seed-2027" / "progress" / "training_summary.json"
            summary.parent.mkdir(parents=True)
            summary.write_text("{}\n", encoding="utf-8")
            log = root / "train.log"
            log.write_text(
                "Training 1.5B progress seed 2027\n"
                "5/5\n"
                "Training 1.5B strict seed 2027\n"
                "1/3\n",
                encoding="utf-8",
            )
            result = summarize(log, checkpoints, datasets)
            self.assertEqual(result["planned_adapters"], 15)
            self.assertEqual(result["completed_adapters"], 1)
            self.assertEqual(result["examples_total"], 5 * 3 + 3 * 3 + 7 * 9)
            self.assertEqual(result["examples_completed"], 5 + 3)
            self.assertEqual(result["active_adapter"]["mode"], "strict")
            self.assertEqual(result["active_adapter"]["examples_completed"], 3)


if __name__ == "__main__":
    unittest.main()
