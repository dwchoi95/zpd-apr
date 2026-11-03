#!/usr/bin/env python3
"""Run judge_codeworkout_in_container.sh in the Java judge image: one '<slug>.txt' status per source."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).with_suffix(".sh")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, help="sources/ written by run.py java-prepare")
    parser.add_argument("status_dir", type=Path)
    parser.add_argument("--image", default="zpdpatch-java:21", help="built from docker/java/Dockerfile")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args()
    args.status_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "docker", "run", "--rm", "--network", "none", "--read-only", "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs", "/tmp:rw,size=4g", "-e", f"ZPD_JAVA_WORKERS={args.workers}",
        "-v", f"{args.sources.resolve()}:/sources:ro", "-v", f"{args.status_dir.resolve()}:/status",
        "-v", f"{SCRIPT}:/judge.sh:ro", "--entrypoint", "bash", args.image, "/judge.sh", "/sources", "/status",
    ], check=True)


if __name__ == "__main__":
    main()
