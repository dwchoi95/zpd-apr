#!/usr/bin/env python3
"""Run scripts/compile_codeworkout_in_container.sh in the Java judge image: one '<id>\t<compiles>\t<returncode>' status per unit."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "compile_codeworkout_in_container.sh"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, help="directory written by prepare_codeworkout_java_sources.py")
    parser.add_argument("status_dir", type=Path)
    parser.add_argument("--image", default="zpdpatch-java:21", help="built from docker/java/Dockerfile")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()
    args.status_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "docker", "run", "--rm", "--network", "none", "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{args.sources.resolve()}:/sources:ro", "-v", f"{args.status_dir.resolve()}:/status",
        "-v", f"{SCRIPT}:/compile.sh:ro", "--entrypoint", "bash", args.image, "/compile.sh", "/sources", "/status", str(args.jobs),
    ], check=True)


if __name__ == "__main__":
    main()
