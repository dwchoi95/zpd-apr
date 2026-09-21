import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.run_zpd_repair_replication import verify_files


class ReplicationLauncherChecks(unittest.TestCase):
    def test_hash_mismatch_stops_chain(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'input.json').write_bytes(b'fixed')
            verify_files(root,{'input.json':hashlib.sha256(b'fixed').hexdigest()})
            with self.assertRaises(ValueError):
                verify_files(root,{'input.json':hashlib.sha256(b'changed').hexdigest()})


if __name__=='__main__':
    unittest.main()
