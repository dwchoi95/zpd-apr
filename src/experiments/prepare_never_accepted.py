#!/usr/bin/env python3
"""Build a data root of the RQ1 problems' trajectories that never reach acceptance, filtered as the benchmark was.

A trajectory is one student's Python 3 submissions to a problem in time order. It is kept when the student never got
any submission to the problem accepted, made at least two wrong-answer submissions that are not all identical, and
every submission parses. The test cases, limits and descriptions are the benchmark's (FixEval). After execution, the
verdict-reproduction filter of the benchmark is applied to the outcome cache, not here.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path


def parses(code: str) -> bool:
    try:
        ast.parse(code)
    except (SyntaxError, ValueError):
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--codenet", type=Path, required=True, help="Project_CodeNet root (metadata/, data/)")
    parser.add_argument("--benchmark-data", type=Path, required=True, help="the RQ1 benchmark's data root")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    problems = sorted(p.name for p in args.benchmark_data.iterdir() if p.is_dir() and p.name.startswith("p"))
    manifest, summary = [], {}
    for problem in problems:
        rows = list(csv.DictReader((args.codenet / "metadata" / f"{problem}.csv").open(encoding="utf-8")))
        accepted = {r["user_id"] for r in rows if r["status"] == "Accepted"}
        by_user = defaultdict(list)
        for r in rows:
            if r["language"] == "Python" and "3" in r["original_language"] and r["user_id"] not in accepted:
                by_user[r["user_id"]].append(r)
        kept = 0
        for user, subs in sorted(by_user.items()):
            subs.sort(key=lambda r: (int(r["date"]), r["submission_id"]))
            codes = [(args.codenet / "data" / problem / "Python" / f"{r['submission_id']}.py").read_text(errors="replace")
                     for r in subs]
            wrong = [c for r, c in zip(subs, codes) if r["status"] == "Wrong Answer"]
            if len(wrong) < 2 or len(set(wrong)) < 2 or not all(map(parses, codes)):
                continue
            path = args.out / problem / "submissions" / f"{user}.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as out:
                for r, code in zip(subs, codes):
                    out.write(json.dumps({"submission_id": r["submission_id"], "timestamp": int(r["date"]),
                                          "verdict": r["status"], "code": code}, ensure_ascii=False) + "\n")
            manifest.append({"problem_id": problem, "user_id": user, "relative_path": f"{problem}/submissions/{user}.jsonl",
                             "first_timestamp": int(subs[0]["date"]), "submission_count": len(subs), "split": "test"})
            kept += 1
        (args.out / problem).mkdir(parents=True, exist_ok=True)
        for name in ("testcases.jsonl", "metadata.json", "description.html"):
            shutil.copyfile(args.benchmark_data / problem / name, args.out / problem / name)
        summary[problem] = {"never_accepted_users": len(by_user), "kept": kept}
    (args.out / "splits").mkdir(parents=True, exist_ok=True)
    with (args.out / "splits" / "test.jsonl").open("w", encoding="utf-8") as out:
        out.writelines(json.dumps(m) + "\n" for m in manifest)
    (args.out / "prepare-summary.json").write_text(json.dumps(
        {"problems": summary, "trajectories": len(manifest), "submissions": sum(m["submission_count"] for m in manifest)},
        indent=2) + "\n")
    print(len(manifest), sum(m["submission_count"] for m in manifest))


if __name__ == "__main__":
    main()
