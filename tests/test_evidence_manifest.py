from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/build_fse2027_evidence_manifest.py"
VERIFY = ROOT / "scripts/verify_fse2027_evidence_manifest.py"


class EvidenceManifestTest(unittest.TestCase):
    def test_rebuild_excludes_manifest_itself_and_remains_verifiable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_root = root / "canonical-v5"
            analysis = run_root / "analysis"
            checkpoints = root / "canonical-v5-checkpoints"
            external = root / "tiktoc"
            analysis.mkdir(parents=True)
            checkpoints.mkdir()
            external_dataset = external / "derived" / "datasets"
            external_dataset.mkdir(parents=True)
            (external / "source-provenance.json").write_text(
                '{"source_revision": "fixture"}\n', encoding="utf-8"
            )
            (run_root / "split-summary.json").write_text(
                '{"split": "fixture"}\n',
                encoding="utf-8",
            )
            (analysis / "fixture.json").write_text(
                '{"metric": 1}\n',
                encoding="utf-8",
            )
            (external_dataset / "summary.json").write_text(
                '{"trajectories": 3}\n', encoding="utf-8"
            )
            (external_dataset / "token-audit-4k.json").write_text(
                '{"overlength_examples": 0}\n', encoding="utf-8"
            )
            (external_dataset / "token-audit.json").write_text(
                '{"overlength_examples": 19}\n', encoding="utf-8"
            )
            manifest = analysis / "evidence-manifest.json"
            build = [
                sys.executable,
                str(BUILD),
                "--run-root",
                str(run_root),
                "--checkpoint-root",
                str(checkpoints),
                "--external-root",
                str(external),
                "--source-revision",
                "fixture-revision",
                "--output",
                str(manifest),
            ]
            subprocess.run(build, check=True)
            first = json.loads(manifest.read_text(encoding="utf-8"))
            subprocess.run(build, check=True)
            second = json.loads(manifest.read_text(encoding="utf-8"))

            first.pop("created_utc")
            second.pop("created_utc")
            self.assertEqual(first, second)
            self.assertEqual(second["file_count"], 5)
            self.assertEqual(second["external_root_names"], ["tiktoc"])
            paths = {item["path"] for item in second["files"]}
            self.assertNotIn(
                "analysis/evidence-manifest.json",
                paths,
            )
            self.assertIn("derived/datasets/token-audit-4k.json", paths)
            self.assertNotIn("derived/datasets/token-audit.json", paths)
            verified = subprocess.run(
                [
                    sys.executable,
                    str(VERIFY),
                    "--manifest",
                    str(manifest),
                    "--run-root",
                    str(run_root),
                    "--checkpoint-root",
                    str(checkpoints),
                    "--external-root",
                    str(external),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(json.loads(verified.stdout)["verified"], 5)


if __name__ == "__main__":
    unittest.main()
