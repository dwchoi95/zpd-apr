import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.verify_fse2027_protocol_provenance import verify


class ProtocolProvenanceTest(unittest.TestCase):
    def test_accepts_frozen_blob_and_rejects_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=repo, check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Test"], cwd=repo, check=True
            )
            script = repo / "runner.sh"
            script.write_text("echo frozen\n", encoding="utf-8")
            subprocess.run(["git", "add", "runner.sh"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "freeze"], cwd=repo, check=True)
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                text=True, stdout=subprocess.PIPE,
            ).stdout.strip()
            manifest = repo / "protocol.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "scope": "test",
                "experiments": {"control": {"files": {"runner.sh": revision}}},
            }), encoding="utf-8")

            result = verify(manifest, repo)
            self.assertTrue(result["all_frozen_blobs_unchanged"])
            self.assertEqual(result["verified_files"], 1)

            script.write_text("echo changed\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "differs from frozen"):
                verify(manifest, repo)


if __name__ == "__main__":
    unittest.main()
