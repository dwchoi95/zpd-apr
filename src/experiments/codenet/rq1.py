"""Build the RQ1 benchmark (14 AtCoder problems) from Project CodeNet and the trajectory manifest."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .builder import (
    _find_case_pairs,
    _load_problem_metadata,
    _read_text,
    _validate_source_layout,
    _write_problem_metadata,
)

MANIFEST = Path(__file__).with_name("rq1_manifest.json")


def python3_compatible(code: str) -> str:
    """fractions.gcd was removed in Python 3.9 (it was valid when the programs were submitted)."""
    code = code.replace("from fractions import gcd", "from math import gcd")
    return re.sub(r"\bfractions\.gcd\b", "math.gcd", code)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_rq1_benchmark(
    source_root: Path,
    output_root: Path,
    *,
    manifest_path: Path = MANIFEST,
    overwrite: bool = False,
) -> dict[str, int]:
    paths = _validate_source_layout(source_root.expanduser().resolve())
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problem_metadata = _load_problem_metadata(paths["problem_list"])
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"Destination already exists: {output_root}. Use --overwrite to replace it.")
        shutil.rmtree(output_root)
    split_rows: list[dict[str, Any]] = []
    for problem_id, tests in sorted(manifest["tests"].items()):
        destination = output_root / problem_id
        destination.mkdir(parents=True)
        _write_problem_metadata(destination / "metadata.json", problem_metadata[problem_id])
        shutil.copyfile(paths["descriptions"] / f"{problem_id}.html", destination / "description.html")
        _write_jsonl(destination / "testcases.jsonl", [
            {"case_id": f"case_{index:05d}", "input": _read_text(case.input_path), "expected_output": _read_text(case.output_path)}
            for index, case in enumerate(_find_case_pairs(paths["testcases"] / tests), start=1)
        ])
        with (paths["metadata"] / f"{problem_id}.csv").open(encoding="utf-8", newline="") as file:
            rows = {row["submission_id"]: row for row in csv.DictReader(file)}
        for listed_problem, user_id, submission_ids in manifest["trajectories"]:
            if listed_problem != problem_id:
                continue
            submissions = []
            for position, submission_id in enumerate(submission_ids, start=1):
                code = _read_text(paths["data"] / problem_id / "Python" / f"{submission_id}.py")
                submissions.append({
                    "submission_id": submission_id,
                    "timestamp": int(rows[submission_id]["date"]),
                    "verdict": rows[submission_id]["status"],
                    "code": code if position == len(submission_ids) else python3_compatible(code),
                })
            _write_jsonl(destination / "submissions" / f"{user_id}.jsonl", submissions)
            split_rows.append({
                "problem_id": problem_id,
                "user_id": user_id,
                "relative_path": f"{problem_id}/submissions/{user_id}.jsonl",
                "first_timestamp": submissions[0]["timestamp"],
                "submission_count": len(submissions),
                "split": "test",
            })
    _write_jsonl(output_root / "splits" / "test.jsonl", split_rows)
    return {"problems": len(manifest["tests"]), "trajectories": len(split_rows),
            "submissions": sum(row["submission_count"] for row in split_rows)}
