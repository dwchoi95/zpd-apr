#!/usr/bin/env python3
"""Replace each Answer target with another student's accepted program of the same problem (a solution-supervised control).

`closest` takes the accepted program that keeps the largest share of the current submission's tokens (the paper's token
retention; ties by line retention, then student); `random` draws one, seeded per example. The pool is the accepted
targets of the other students in `pool`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from functools import lru_cache
from multiprocessing import Pool
from pathlib import Path

from src.core.retention import _lines, _python_tokens, _retained_fraction

POOL: dict[str, list[tuple[str, str]]] = {}


def init(pool: dict[str, list[tuple[str, str]]]) -> None:
    POOL.update(pool)


@lru_cache(maxsize=None)
def tokens(code: str) -> tuple[list[str], list[str]]:
    return _python_tokens(code), _lines(code)


def closest(row: dict) -> tuple[str, str, float]:
    source_tokens, source_lines = tokens(row["history"][-1]["code"])
    best = None
    for user, candidate in POOL[row["problem_id"]]:
        if user == row["user_id"]:
            continue
        candidate_tokens, candidate_lines = tokens(candidate)
        key = (_retained_fraction(source_tokens, candidate_tokens), _retained_fraction(source_lines, candidate_lines))
        if best is None or key > best[0] or (key == best[0] and user < best[1]):
            best = (key, user, candidate)
    return best[1], best[2], best[0][0]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("pool", type=Path, help="Answer dataset whose accepted targets form the pool")
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=("closest", "random"), required=True)
    parser.add_argument("--seed", type=int, default=2027)
    parser.add_argument("--workers", type=int, default=24)
    args = parser.parse_args()

    seen = defaultdict(set)
    with args.pool.open(encoding="utf-8") as source:
        for row in map(json.loads, source):
            code = row["target_code"]
            if code.strip() not in seen[(row["problem_id"], row["user_id"])]:
                seen[(row["problem_id"], row["user_id"])].add(code.strip())
                POOL.setdefault(row["problem_id"], []).append((row["user_id"], code))
    with args.dataset.open(encoding="utf-8") as source:
        rows = [json.loads(line) for line in source]

    if args.mode == "closest":
        with Pool(args.workers, initializer=init, initargs=(POOL,)) as pool:
            picks = pool.map(closest, rows, chunksize=16)
    else:
        picks = []
        for row in rows:
            others = [(u, c) for u, c in POOL[row["problem_id"]] if u != row["user_id"]]
            digest = hashlib.sha256(f"{args.seed}:{row['example_id']}".encode()).digest()
            user, code = random.Random(digest).choice(others)
            picks.append((user, code, None))
    with args.output.open("w", encoding="utf-8") as output:
        for row, (user, code, kept) in zip(rows, picks):
            row = dict(row, target_code=code, peer_user_id=user, peer_token_retention=kept)
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(args.output), "rows": len(rows), "mode": args.mode}))


if __name__ == "__main__":
    main()
