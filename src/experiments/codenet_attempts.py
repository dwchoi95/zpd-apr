#!/usr/bin/env python3
"""Attempts to acceptance and verdict changes of every student on every AtCoder problem of Project CodeNet (all languages).

Reads only CodeNet's metadata (problem_list.csv and metadata/<pid>.csv). A student-problem pair orders the student's
submissions in any language by date; its attempts to acceptance is the 1-based index of the first Accepted one. For every
two consecutive submissions of a pair, including those after its first acceptance, the change of verdict is counted.
Writes output/benchmark/atcoder-attempts.json.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("codenet", type=Path, help="Project_CodeNet root (metadata/)")
    parser.add_argument("output", type=Path, help="the output/ folder")
    args = parser.parse_args()
    problems = [r["id"] for r in csv.DictReader(open(args.codenet / "metadata" / "problem_list.csv")) if r["dataset"] == "AtCoder"]
    attempts, never, change, pairs_n, subs = Counter(), 0, Counter(), 0, 0
    for pid in problems:
        path = args.codenet / "metadata" / f"{pid}.csv"
        if not path.exists():
            continue
        seq = defaultdict(list)
        for r in csv.DictReader(open(path, encoding="utf-8")):
            seq[r["user_id"]].append((int(r["date"]), r["submission_id"], r["status"]))
        for subs_u in seq.values():
            subs_u.sort()
            verdicts = [s for _, _, s in subs_u]
            subs += len(verdicts)
            k = verdicts.index("Accepted") + 1 if "Accepted" in verdicts else None
            if k is None:
                never += 1
            else:
                attempts[k] += 1
            for a, b in zip(verdicts, verdicts[1:]):
                change[(a, b)] += 1
                pairs_n += 1
    out = {"problems": len(problems), "submissions": subs, "pairs_accepted": sum(attempts.values()), "pairs_never": never,
           "attempts": {str(k): v for k, v in sorted(attempts.items())},
           "transitions": {f"{a} -> {b}": v for (a, b), v in change.most_common()}, "transition_pairs": pairs_n}
    dest = args.output / "benchmark" / "atcoder-attempts.json"
    dest.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    acc = sum(attempts.values())
    print(f"AtCoder problems {len(problems)}, submissions {subs}, student-problem pairs accepted {acc}, never {never}")
    print("first try:", f"{100 * attempts[1] / acc:.1f}%", "| 2:", f"{100 * attempts[2] / acc:.1f}%", "| 3+:", f"{100 * sum(v for k, v in attempts.items() if k >= 3) / acc:.1f}%")
    kept = sum(v for (a, b), v in change.items() if a == b and b != "Accepted")
    print(f"consecutive pairs: {pairs_n}; failing verdict unchanged {100 * kept / pairs_n:.1f}%")
    for (a, b), v in change.most_common(10):
        print(f"  {a} -> {b}: {100 * v / pairs_n:.1f}%")


if __name__ == "__main__":
    main()
