#!/usr/bin/env python3
"""TED from every failing submission of each RQ1 trajectory to the student's next submission and to their accepted one.

For trajectory s_1..s_n (s_n accepted) and each failing s_i, writes ted(s_i, s_{i+1}) (the student's step) and
ted(s_i, s_n) (the distance a repair toward that correct program covers) to output/benchmark/rq1-distance-to-acceptance.jsonl.
"""

from __future__ import annotations

import argparse
import json
from multiprocessing import Pool
from pathlib import Path

from src.core.evaluate import tree_edit_distance


def teds(job: tuple[str, str, str]) -> tuple[int | None, int | None]:
    code, nxt, accepted = job
    return tree_edit_distance(code, nxt), tree_edit_distance(code, accepted)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="benchmark data root: <pid>/submissions/<user>.jsonl")
    parser.add_argument("output", type=Path, help="the output/ folder (reads benchmark/rq1-student-steps.jsonl)")
    args = parser.parse_args()
    steps = [json.loads(l) for l in open(args.output / "benchmark" / "rq1-student-steps.jsonl", encoding="utf-8") if l.strip()]
    jobs, keys = [], []
    for r in steps:
        pid, user, _ = r["example_id"].split(":")
        subs = [json.loads(l) for l in open(args.data / pid / "submissions" / f"{user}.jsonl", encoding="utf-8") if l.strip()]
        codes = [s["code"] for s in subs]
        codes = [c for k, c in enumerate(codes) if k == 0 or c != codes[k - 1]]   # a resubmitted identical program is one state
        n = len(r["step_ted"]) + 1
        assert len(codes) == n, (r["example_id"], len(codes), n)
        for i in range(n - 1):
            jobs.append((codes[i], codes[i + 1], codes[n - 1]))
            keys.append((r["example_id"], i, n - 1, r["step_ted"][i]))
    with Pool() as pool:
        res = pool.map(teds, jobs, chunksize=8)
    out = args.output / "benchmark" / "rq1-distance-to-acceptance.jsonl"
    mismatch = 0
    with out.open("w", encoding="utf-8") as f:
        for (eid, i, failing, step), (nxt, acc) in zip(keys, res):
            mismatch += nxt != step
            f.write(json.dumps({"example_id": eid, "position": i, "failing": failing, "ted_next": nxt, "ted_accepted": acc}) + "\n")
    print(f"{len(keys)} failing submissions; steps differing from rq1-student-steps: {mismatch}")


if __name__ == "__main__":
    main()
