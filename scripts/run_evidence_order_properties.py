#!/usr/bin/env python3
"""Run the executable evidence-order certificates without pytest."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    test_path = root / "tests" / "test_evidence_order.py"
    namespace = runpy.run_path(str(test_path))
    tests = sorted(
        (name, value)
        for name, value in namespace.items()
        if name.startswith("test_") and callable(value)
    )
    for name, test in tests:
        test()
        print(f"PASS {name}")
    print(f"{len(tests)} executable evidence-order certificates passed")


if __name__ == "__main__":
    main()
