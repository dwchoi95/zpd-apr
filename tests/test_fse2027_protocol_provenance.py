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

    def test_verifies_declared_conformance_amendment(self):
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
            original = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                text=True, stdout=subprocess.PIPE,
            ).stdout.strip()
            script.write_text("echo conforming\n", encoding="utf-8")
            subprocess.run(["git", "add", "runner.sh"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "amend"], cwd=repo, check=True)
            replacement = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                text=True, stdout=subprocess.PIPE,
            ).stdout.strip()
            manifest = repo / "protocol.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "scope": "test",
                "amendments": [{
                    "id": "conformance",
                    "original_files": {"runner.sh": original},
                    "replacement_files": {"runner.sh": replacement},
                }],
                "experiments": {"control": {"files": {"runner.sh": replacement}}},
            }), encoding="utf-8")
            result = verify(manifest, repo)
            self.assertTrue(result["all_declared_amendments_verified"])
            self.assertEqual(result["verified_amended_files"], 1)

    def test_verifies_ordered_amendment_chain(self):
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
            revisions = []
            for index, content in enumerate(("frozen", "conforming", "operational")):
                script.write_text(f"echo {content}\n", encoding="utf-8")
                subprocess.run(["git", "add", "runner.sh"], cwd=repo, check=True)
                subprocess.run(
                    ["git", "commit", "-qm", f"revision-{index}"],
                    cwd=repo, check=True,
                )
                revisions.append(subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                    text=True, stdout=subprocess.PIPE,
                ).stdout.strip())
            manifest = repo / "protocol.json"
            manifest.write_text(json.dumps({
                "schema_version": 1,
                "scope": "test",
                "amendments": [
                    {
                        "id": "conformance",
                        "original_files": {"runner.sh": revisions[0]},
                        "replacement_files": {"runner.sh": revisions[1]},
                    },
                    {
                        "id": "operational",
                        "original_files": {"runner.sh": revisions[1]},
                        "replacement_files": {"runner.sh": revisions[2]},
                    },
                ],
                "experiments": {
                    "control": {"files": {"runner.sh": revisions[2]}}
                },
            }), encoding="utf-8")
            result = verify(manifest, repo)
            self.assertTrue(result["all_declared_amendments_verified"])
            self.assertEqual(result["verified_amended_files"], 2)


if __name__ == "__main__":
    unittest.main()
