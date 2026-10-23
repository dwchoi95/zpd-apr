#!/usr/bin/env python3
"""Measure how much a student changes in one submission, as a reference step size.

Static analysis over the sealed canonical datasets and the retained trajectory corpus.
It generates nothing, executes no testcase, and loads no model: it only compares student
source code that is already stored. Tree edit distance and retention reuse the project's
own metric code, so the values are commensurable with the reported method distances.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

# The six budgets the deployment frontier already reports (scripts/verify_paper_budget_table.py).
BUDGETS = (5, 10, 20, 40, 80, 160)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.analyze_patch_locality import locality
from src.repair.evaluate import tree_edit_distance


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def canonical_trajectory(corpus: Path, problem: str, user: str) -> list[dict[str, Any]]:
    """Chronological submissions cut at the first acceptance, consecutive duplicates removed.

    This is the canonical retention rule of Section II-A; the reconstruction is checked
    against the sealed dataset for every row rather than assumed.
    """
    rows = read_jsonl(corpus / problem / "submissions" / f"{user}.jsonl")
    cut: list[dict[str, Any]] = []
    for row in rows:
        cut.append(row)
        if row["verdict"] == "Accepted":
            break
    kept: list[dict[str, Any]] = []
    for row in cut:
        if kept and kept[-1]["code"] == row["code"]:
            continue
        kept.append(row)
    return kept


def step(before: str, after: str) -> dict[str, Any]:
    measures = locality(before, after)
    return {
        "ted": tree_edit_distance(before, after),
        "token_retention": measures["token_retention"],
        "line_retention": measures["line_retention"],
    }


def summarize(steps: list[dict[str, Any]]) -> dict[str, Any]:
    teds = sorted(s["ted"] for s in steps if s["ted"] is not None)
    out: dict[str, Any] = {
        "steps": len(steps),
        "defined_ted_steps": len(teds),
        "undefined_ted_steps": len(steps) - len(teds),
    }
    if teds:
        quartiles = statistics.quantiles(teds, n=4, method="inclusive") if len(teds) > 1 else [teds[0]] * 3
        deciles = statistics.quantiles(teds, n=10, method="inclusive") if len(teds) > 1 else [teds[0]] * 9
        out["ted"] = {
            "mean": statistics.fmean(teds),
            "median": quartiles[1],
            "lower_quartile": quartiles[0],
            "upper_quartile": quartiles[2],
            "ninetieth_percentile": deciles[8],
            "minimum": teds[0],
            "maximum": teds[-1],
        }
    for name in ("token_retention", "line_retention"):
        values = sorted(s[name] for s in steps)
        if values:
            quartiles = statistics.quantiles(values, n=4, method="inclusive") if len(values) > 1 else [values[0]] * 3
            out[name] = {"mean": statistics.fmean(values), "median": quartiles[1],
                         "lower_quartile": quartiles[0], "upper_quartile": quartiles[2]}
    return out


def _measure_row(task: tuple[Path, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    corpus, row = task
    buggy = row["history"][-1]["code"]
    accepted = row["target_code"]
    traj = canonical_trajectory(corpus, row["problem_id"], row["user_id"])
    if len(traj) < 2:
        raise ValueError(f"trajectory shorter than one step: {row['example_id']}")
    if traj[-2]["code"] != buggy or traj[-1]["code"] != accepted:
        raise ValueError(f"reconstruction disagrees with the sealed dataset: {row['example_id']}")
    pairs = [step(before["code"], after["code"]) for before, after in zip(traj, traj[1:])]
    defined = [s["ted"] for s in pairs if s["ted"] is not None]
    # The largest step this student took unaided on this problem: a size they have shown
    # they can reach. It bounds reach from above; it does not locate their zone.
    reach = max(defined) if defined else None
    return step(buggy, accepted), pairs, reach


def reach_summary(reaches: list[int | None], budgets: tuple[int, ...]) -> dict[str, Any]:
    """Distribution of the largest unaided step per trajectory, read against the budgets."""
    defined = sorted(r for r in reaches if r is not None)
    out: dict[str, Any] = {
        "trajectories": len(reaches),
        "defined": len(defined),
        "undefined": len(reaches) - len(defined),
    }
    if not defined:
        return out
    quartiles = statistics.quantiles(defined, n=4, method="inclusive") if len(defined) > 1 else [defined[0]] * 3
    out["ted"] = {
        "mean": statistics.fmean(defined),
        "median": quartiles[1],
        "lower_quartile": quartiles[0],
        "upper_quartile": quartiles[2],
        "minimum": defined[0],
        "maximum": defined[-1],
    }
    out["share_within_budget"] = {
        str(budget): sum(1 for r in defined if r <= budget) / len(defined) for budget in budgets
    }
    return out


def analyze(corpus: Path, splits: dict[str, Path], limit: int | None,
            budgets: tuple[int, ...] = BUDGETS) -> dict[str, Any]:
    result: dict[str, Any] = {
        "scope": "static comparison of stored student submissions; no generation, training, inference or testcase execution",
        "metric_source": {"ted": "src.repair.evaluate.tree_edit_distance",
                          "retention": "scripts.analyze_patch_locality.locality"},
        "ted_backend": "apted" if _has_apted() else "zss",
        "canonical_rule": "cut at first acceptance; drop consecutive duplicate code",
        "inputs": {name: {"path": str(path), "sha256": digest(path)} for name, path in splits.items()},
        "budgets": list(budgets),
        "splits": {},
    }
    for name, path in splits.items():
        rows = read_jsonl(path)
        if limit:
            rows = rows[:limit]
        final_steps, all_steps, reaches, trajectories = [], [], [], 0
        # ponytail: a process pool only because single-threaded zss over 1,247 trajectories
        # runs for the better part of an hour; the per-row work is independent and ordered.
        with ProcessPoolExecutor() as pool:
            measured = pool.map(_measure_row, ((corpus, row) for row in rows), chunksize=8)
            for final, pairs, reach in measured:
                final_steps.append(final)
                all_steps.extend(pairs)
                reaches.append(reach)
                trajectories += 1
        result["splits"][name] = {
            "examples": len(rows),
            "trajectories": trajectories,
            "final_step": summarize(final_steps),
            "all_steps": summarize(all_steps),
            "demonstrated_reach": reach_summary(reaches, budgets),
        }
    return result


def _has_apted() -> bool:
    try:
        import apted  # noqa: F401
    except ImportError:
        return False
    return True


def demo() -> None:
    """Self-check: the rule cuts at acceptance, drops duplicates, and measures a known step."""
    assert step("a = 1\n", "a = 1\n")["ted"] == 0
    assert step("a = 1\n", "a = 2\n")["ted"] == 1
    assert step("a = 1\n", "(\n")["ted"] is None
    assert step("a = 1\nb = 2\n", "a = 1\n")["token_retention"] == 0.5
    print("self-check OK")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("data"))
    parser.add_argument("--seen", type=Path)
    parser.add_argument("--unseen", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        demo()
        return
    splits = {name: path for name, path in (("seen", args.seen), ("unseen", args.unseen)) if path}
    result = analyze(args.corpus, splits, args.limit)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["splits"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
