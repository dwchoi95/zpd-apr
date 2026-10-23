#!/usr/bin/env python3
"""Convert the HISTRA benchmark into this repository's data layout and hold its students out of training."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Iterable

Row = dict[str, Any]
BASELINES = ("refactory", "brafar", "lsgen")


def read_jsonl(path: Path) -> list[Row]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Row]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def example_id(trajectory: Row) -> str:
    # final-accepted examples are named after the accepted target's 1-based position
    return f"{trajectory['problem_id']}:{trajectory['user_id']}:S{len(trajectory['submissions'])}"


def load_inputs(approaches: Path) -> dict[tuple[str, str], list[str]]:
    """The wrong-answer programs every HISTRA technique was given (HISTRA edits a few to run on current Python)."""
    inputs: dict[tuple[str, str], list[str]] = {}
    for method in BASELINES:
        for record in read_jsonl(approaches / f"{method}.jsonl"):
            key = (record["pid"], record["user"])
            assert inputs.setdefault(key, record["was"]) == record["was"], (method, key)
    return inputs


def build_data_root(histra_data: Path, out: Path, inputs: dict[tuple[str, str], list[str]]) -> tuple[list[Row], int]:
    trajectories: list[Row] = []
    split_rows: list[Row] = []
    edited = 0
    for problem_dir in sorted(p for p in histra_data.iterdir() if p.is_dir() and p.name.startswith("p")):
        target = out / problem_dir.name
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(problem_dir / "problem.html", target / "description.html")
        meta = json.loads((problem_dir / "meta.json").read_text(encoding="utf-8"))
        (target / "metadata.json").write_text(
            json.dumps({"time_limit": meta["time_limit_ms"], "memory_limit": meta["memory_limit_kb"]}, indent=2) + "\n",
            encoding="utf-8",
        )
        write_jsonl(
            target / "testcases.jsonl",
            (
                {"case_id": f"case_{index:05d}", "input": test["input"], "expected_output": test["output"]}
                for index, test in enumerate(read_jsonl(problem_dir / "tests.jsonl"), start=1)
            ),
        )
        for trajectory in read_jsonl(problem_dir / "trajectories.jsonl"):
            was = inputs[(trajectory["problem_id"], trajectory["user_id"])]
            submissions = trajectory["submissions"]
            assert submissions[-1]["verdict"] == "Accepted" and len(was) == len(submissions) - 1, example_id(trajectory)
            edited += sum(s["code"] != code for s, code in zip(submissions, was))
            submissions = [dict(s, code=code) for s, code in zip(submissions, was)] + submissions[-1:]
            trajectory = dict(trajectory, submissions=submissions)
            write_jsonl(
                target / "submissions" / f"{trajectory['user_id']}.jsonl",
                (
                    {"submission_id": s["sid"], "timestamp": s["ts"], "verdict": s["verdict"], "code": s["code"]}
                    for s in submissions
                ),
            )
            split_rows.append(
                {
                    "problem_id": trajectory["problem_id"],
                    "user_id": trajectory["user_id"],
                    "relative_path": f"{problem_dir.name}/submissions/{trajectory['user_id']}.jsonl",
                    "first_timestamp": submissions[0]["ts"],
                    "submission_count": len(submissions),
                    "split": "test",
                }
            )
            trajectories.append(trajectory)
    write_jsonl(out / "splits" / "test.jsonl", split_rows)
    return trajectories, edited


def baseline_generations(approach: Path, trajectories: dict[tuple[str, str], Row], method: str) -> list[Row]:
    rows = []
    for record in read_jsonl(approach):
        trajectory = trajectories[(record["pid"], record["user"])]
        buggy = trajectory["submissions"][-2]["code"]
        assert record["was"][-1] == buggy, (record["pid"], record["user"])
        # a technique that returns no passing patch leaves the submission unchanged
        code = record["patch"] if record["patch"] is not None else buggy
        rows.append(
            {
                "example_id": example_id(trajectory),
                "problem_id": record["pid"],
                "user_id": record["user"],
                "method": method,
                "prompt_style": "external",
                "generation_time_sec": record.get("sec"),
                "generated_code": code,
                "raw_generation": record["patch"],
            }
        )
    assert len(rows) == len(trajectories), (method, len(rows))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--histra-data", type=Path, required=True)
    parser.add_argument("--histra-approaches", type=Path, required=True)
    parser.add_argument("--train-answer", type=Path, required=True)
    parser.add_argument("--valid-answer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    trajectories, edited = build_data_root(args.histra_data, args.out / "data", load_inputs(args.histra_approaches))
    held_out = {(t["problem_id"], t["user_id"]): t for t in trajectories}
    summary: Row = {
        "trajectories": len(trajectories),
        "problems": len({k[0] for k in held_out}),
        "submissions_edited_by_histra": edited,
        "inputs": {},
    }
    for name, source in (("train-answer", args.train_answer), ("valid-answer", args.valid_answer)):
        rows = read_jsonl(source)
        kept = [r for r in rows if (r["problem_id"], r["user_id"]) not in held_out]
        write_jsonl(args.out / "datasets" / f"{name}.jsonl", kept)
        summary[name] = {"source": len(rows), "kept": len(kept), "removed": len(rows) - len(kept)}
        summary["inputs"][name] = sha256(source)
    for method in BASELINES:
        approach = args.histra_approaches / f"{method}.jsonl"
        write_jsonl(args.out / "baselines" / f"{method}.generations.jsonl", baseline_generations(approach, held_out, method))
        summary["inputs"][method] = sha256(approach)
    (args.out / "prepare-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
