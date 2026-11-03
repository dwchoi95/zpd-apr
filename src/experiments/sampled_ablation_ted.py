#!/usr/bin/env python3
"""TED of the repaired returns of the sampled ablation variants, whose rows in output/ablation leave it null.

For `no-training`, `sampled`, and `distinct-checkpoints` of each split, recomputes from the stored generations the TED
from the buggy program (`ted_buggy_fixed`) and to the student's accepted program (`ted_fixed_oracle`) of every repaired
return, and writes them to output/ablation/<split>/sampled-ted.jsonl.
"""

from __future__ import annotations

import argparse
import ast
import json
from multiprocessing import Pool
from pathlib import Path

from src.core.evaluate import tree_edit_distance

SEEDS = (4101, 4102, 4103)
# variant -> (member runs, selected_source of a member)
VARIANTS = {"no-training": ("base", "Sample{}"), "sampled": ("same", "sample-{}"), "distinct-checkpoints": ("distinct", "sample-{}")}


def load(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def teds(job: tuple[str, str, str]) -> tuple[int | None, int | None]:
    buggy, code, accepted = job
    return tree_edit_distance(buggy, code), tree_edit_distance(code, accepted)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("canonical", type=Path, help="canonical runs: datasets/ and eval/current-only-factorial/")
    parser.add_argument("base", type=Path, help="untrained base-model runs: eval/base-current-only/")
    parser.add_argument("output", type=Path, help="the output/ folder")
    args = parser.parse_args()

    with Pool() as pool:
        for split in ("seen", "unseen"):
            data = {str(r["example_id"]): r for r in load(args.canonical / "datasets" / f"{split}-test-final.jsonl")}
            roots = {"base": args.base / "eval/base-current-only" / split,
                     **{k: args.canonical / "eval/current-only-factorial" / split / k for k in ("same", "distinct")}}
            members = {(kind, source.format(seed), str(g["example_id"])): g
                       for kind, source in VARIANTS.values() for seed in SEEDS
                       for g in load(roots[kind] / f"sample-{seed}.evaluation.jsonl")}
            out = []
            for variant, (kind, _) in VARIANTS.items():
                repaired = [r for r in load(args.output / "ablation" / split / f"{variant}.jsonl") if r["repaired"]]
                jobs = []
                for r in repaired:
                    member = members[(kind, r["selected_source"], r["example_id"])]
                    assert member["repaired"] in (True, "True")
                    assert r.get("generated_code") in (None, member["generated_code"])
                    d = data[r["example_id"]]
                    history = ast.literal_eval(d["history"]) if isinstance(d["history"], str) else d["history"]
                    jobs.append((history[-1]["code"], member["generated_code"], d["target_code"]))
                for r, (ted, oracle) in zip(repaired, pool.map(teds, jobs)):
                    out.append({"example_id": r["example_id"], "variant": variant, "ted_buggy_fixed": ted, "ted_fixed_oracle": oracle})
            with (args.output / "ablation" / split / "sampled-ted.jsonl").open("w", encoding="utf-8") as f:
                f.writelines(json.dumps(r) + "\n" for r in out)
            print(split, {v: sum(r["variant"] == v for r in out) for v in VARIANTS})


if __name__ == "__main__":
    main()
