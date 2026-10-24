#!/usr/bin/env python3
"""Compile each CodeWorkout Java unit inside the Java judge image and write one '<id>\t<compiles>\t<returncode>' status file per unit."""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

# One javac per unit, run in parallel inside a single network-less container.
LOOP = (
    'find /sources -name "*.java" -print0 | xargs -0 -P "$JOBS" -I{} sh -c \''
    'id=$(basename "{}" .java); out=$(mktemp -d); '
    'timeout 30 javac -proc:none -J-Xmx128m -encoding UTF-8 -d "$out" "{}" >/dev/null 2>&1; rc=$?; '
    'if [ "$rc" -eq 0 ]; then ok=true; else ok=false; fi; '
    'printf "%s\\t%s\\t%s\\n" "$id" "$ok" "$rc" > "/status/$id.status"; rm -rf "$out"\''
)


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
        "-e", f"JOBS={args.jobs}", "-v", f"{args.sources.resolve()}:/sources:ro", "-v", f"{args.status_dir.resolve()}:/status",
        "--entrypoint", "sh", args.image, "-c", LOOP,
    ], check=True)
    print(len(list(args.status_dir.glob("*.status"))), "status files")


if __name__ == "__main__":
    main()
