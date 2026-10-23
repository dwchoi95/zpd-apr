#!/usr/bin/env python3
"""Compile CodeWorkout Java method submissions and durably cache outcomes."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from tqdm import tqdm


Row = dict[str, Any]


def compile_one(row: Row, timeout_sec: float) -> Row:
    started = time.perf_counter()
    code = str(row["code"])
    source = "public class Submission {\n" + code + "\n}\n"
    with tempfile.TemporaryDirectory(prefix="zpd-cw-javac-") as raw_dir:
        work = Path(raw_dir)
        path = work / "Submission.java"
        path.write_text(source, encoding="utf-8")
        try:
            result = subprocess.run(
                [
                    "javac",
                    "-proc:none",
                    "-J-Xmx128m",
                    "-encoding",
                    "UTF-8",
                    "-d",
                    str(work),
                    str(path),
                ],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            returncode = result.returncode
            stderr = result.stderr
            timed_out = False
        except subprocess.TimeoutExpired as error:
            returncode = 124
            stderr = str(error)
            timed_out = True
    return {
        "submission_id": row["submission_id"],
        "problem_id": row["problem_id"],
        "compiles": returncode == 0,
        "timed_out": timed_out,
        "returncode": returncode,
        "stderr_first_line": stderr.strip().splitlines()[0] if stderr.strip() else "",
        "compile_time_sec": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=32)
    parser.add_argument("--timeout-sec", type=float, default=10.0)
    args = parser.parse_args()
    with args.input.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source if line.strip()]
    completed: set[str] = set()
    if args.output.exists():
        with args.output.open(encoding="utf-8") as source:
            completed = {
                str(json.loads(line)["submission_id"])
                for line in source
                if line.strip()
            }
    pending = [row for row in rows if str(row["submission_id"]) not in completed]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8", buffering=1) as destination:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(compile_one, row, args.timeout_sec): row
                for row in pending
            }
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Compile CodeWorkout submissions",
                unit="submission",
            ):
                destination.write(json.dumps(future.result(), ensure_ascii=False) + "\n")
                destination.flush()
    print(
        json.dumps(
            {
                "input_submissions": len(rows),
                "previously_cached": len(completed),
                "newly_cached": len(pending),
                "cached_total": len(completed) + len(pending),
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
