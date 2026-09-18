import tempfile
import unittest
from pathlib import Path
from scripts.generate_zpd_repair_banks import terminal, atomic


class GenerationContracts(unittest.TestCase):
    def test_length_never_executed(self):
        row=terminal(0,2027,'print(1)','length')
        self.assertEqual(row['status'],'resource_failure')
        self.assertIsNone(row['source'])

    def test_empty_and_stop(self):
        self.assertEqual(terminal(0,1,'','stop')['status'],'format_failure')
        self.assertEqual(terminal(0,1,'print(1)','stop')['source'],'print(1)')
        self.assertEqual(terminal(0,1,'print(1)','error')['status'],'unknown_failure')

    def test_atomic_preserves_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'attempt.json'
            atomic(path,dict(status='failure'))
            before=path.read_bytes()
            with self.assertRaises(ValueError):
                atomic(path,dict(status='success'))
            self.assertEqual(before,path.read_bytes())


if __name__=='__main__':
    unittest.main()
