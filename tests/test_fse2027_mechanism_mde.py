from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "mechanism_mde", Path("scripts/analyze_fse2027_mechanism_mde.py")
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class MechanismMDETest(unittest.TestCase):
    def test_ci_width_drives_two_sided_mde(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bridge = Path(directory) / "bridge.tex"
            lines = []
            for effect, ci in MODULE.CONTRASTS.values():
                lines.append(f"\\newcommand{{\\{effect}}}{{1.0}}\n")
                lines.append(f"\\newcommand{{\\{ci}}}{{[-1.00, 3.00]}}\n")
            bridge.write_text("".join(lines), encoding="utf-8")
            result = MODULE.analyze(bridge)
            first = next(iter(result["contrasts"].values()))
            self.assertAlmostEqual(
                first["ci_width_derived_standard_error_percentage_points"],
                4 / (2 * 1.96),
            )
            self.assertGreater(
                first["two_sided_alpha_0_05_power_0_80_mde_percentage_points"],
                2.8,
            )


if __name__ == "__main__":
    unittest.main()
