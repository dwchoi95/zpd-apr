"""Amendment 2026-10-27: plausible patches against the student's own accepted program (no execution here).

Reads executions/ (patches), executions_own/ (students' targets) and outcomes/ (within reach); writes
outcomes_vs_own/<technique>.jsonl and summary_vs_own.json. A seed is a failure under three readings:
  any       - WA, RE or TLE on the first run (the registered rule)
  wa_re     - WA or RE only (TLE counted as a pass)
  rechecked - WA or RE, or a TLE whose single 2-worker rerun is not AC
"""
import hashlib
import json
import os
from collections import Counter
from math import comb
from pathlib import Path

OUT = Path(os.environ.get("ZPD_DIFF_OUT", "differential"))
TECHNIQUES = ["zpdpatch", "refactory", "brafar", "mentored", "lsgen-qwen", "lsgen"]
MODES = ["any", "wa_re", "rechecked"]


def jsonl(path):
    return [json.loads(line) for line in open(path) if line.strip()]


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def failing(ex, mode):
    seeds = set()
    for seed, verdict in ex["verdicts"].items():
        if verdict in ("WA", "RE") or (verdict == "TLE" and (
                mode == "any" or (mode == "rechecked" and ex.get("tle_recheck", {}).get(seed, {}).get("verdict", "AC") != "AC"))):
            seeds.add(int(seed))
    return seeds


_ex = {"verdicts": {"1": "AC", "2": "TLE", "3": "WA", "4": "TLE", "5": "TLE"},
       "tle_recheck": {"2": {"verdict": "AC"}, "4": {"verdict": "TLE"}, "5": {"verdict": "WA"}}}
assert failing(_ex, "any") == {2, 3, 4, 5} and failing(_ex, "wa_re") == {3} and failing(_ex, "rechecked") == {3, 4, 5}


def share(rows, key):
    n = sum(bool(r[key]) for r in rows)
    return {"count": n, "of": len(rows), "share": n / len(rows) if rows else None}


def mcnemar(b, c):
    n, k = b + c, min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n) if n else 1.0


def load(dirname):
    return {(r["problem_id"], r["sha256"]): r for p in sorted((OUT / dirname).glob("p*.jsonl")) for r in jsonl(p)}


patch_ex, own_ex = load("executions"), load("executions_own")
test = jsonl(Path(os.environ.get("ZPD_DIFF_TEST", "datasets/test.jsonl")))
own_of = {r["example_id"]: own_ex[(r["problem_id"], sha(r["target_code"]))] for r in test}
assert len(own_of) == len(test) == 1753

summary = {"family": "differential-20261026-v1", "amendment": "2026-10-27 (zpd-differential-20261026.md)",
           "failure_readings": {"any": "WA, RE or TLE on the first run (registered rule)", "wa_re": "WA or RE only",
                                "rechecked": "WA or RE, or a TLE whose single 2-worker rerun is not AC"}, "students_own_accepted": {}, "techniques": {},
           "paired_with_zpdpatch": {}}

# Students' own accepted programs, one per buggy program (example_id).
for mode in MODES:
    per_problem = {}
    for row in test:
        d = per_problem.setdefault(row["problem_id"], {"programs": 0, "failing": 0})
        d["programs"] += 1
        d["failing"] += bool(failing(own_of[row["example_id"]], mode))
    total = sum(d["failing"] for d in per_problem.values())
    summary["students_own_accepted"][mode] = {"failing": total, "of": len(test), "share": total / len(test),
                                              "per_problem": dict(sorted(per_problem.items()))}
summary["students_own_accepted"]["first_run_tle_runs"] = sum(
    v == "TLE" for ex in own_ex.values() for v in ex["verdicts"].values())

by_tech = {}
for technique in TECHNIQUES:
    reach = {r["example_id"]: r for r in jsonl(OUT / "outcomes" / f"{technique}.jsonl")}
    rows = []
    for row in jsonl(Path("output/approaches") / f"{technique}.jsonl"):
        if row.get("repaired") is not True:
            continue
        ex = patch_ex[(row["problem_id"], sha(row["generated_code"]))]
        own = own_of[row["example_id"]]
        out = {"example_id": row["example_id"], "problem_id": row["problem_id"],
               "within_reach": reach[row["example_id"]]["within_reach"]}
        for mode in MODES:
            suffix = "" if mode == "any" else f"_{mode}"
            mine, theirs = failing(ex, mode), failing(own, mode)
            out[f"patch_fails{suffix}"] = bool(mine)
            out[f"own_fails{suffix}"] = bool(theirs)
            out[f"beyond_own{suffix}"] = bool(mine - theirs)
            if mode == "any":
                out["patch_fail_seeds"], out["own_fail_seeds"] = sorted(mine), sorted(theirs)
        rows.append(out)
    by_tech[technique] = {r["example_id"]: r for r in rows}
    (OUT / "outcomes_vs_own").mkdir(exist_ok=True)
    with open(OUT / "outcomes_vs_own" / f"{technique}.jsonl", "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    within = [r for r in rows if r["within_reach"]]
    entry = {"plausible": len(rows), "within_reach_plausible": len(within)}
    for mode in MODES:
        suffix = "" if mode == "any" else f"_{mode}"
        entry[mode] = {
            "beyond_own": share(rows, f"beyond_own{suffix}"),
            "within_reach_beyond_own": share(within, f"beyond_own{suffix}"),
            "own_fails": share(rows, f"own_fails{suffix}"),
            "within_reach_own_fails": share(within, f"own_fails{suffix}"),
            "patch_fails": share(rows, f"patch_fails{suffix}"),
        }
    entry["per_problem_any"] = {
        p: {"plausible": sum(r["problem_id"] == p for r in rows),
            "beyond_own": sum(r["problem_id"] == p and r["beyond_own"] for r in rows),
            "own_fails": sum(r["problem_id"] == p and r["own_fails"] for r in rows)}
        for p in sorted({r["problem_id"] for r in rows})}
    summary["techniques"][technique] = entry

for technique in TECHNIQUES[1:]:
    common = sorted(set(by_tech["zpdpatch"]) & set(by_tech[technique]))
    entry = {"common": len(common)}
    for mode in MODES:
        key = "beyond_own" if mode == "any" else f"beyond_own_{mode}"
        z = [by_tech["zpdpatch"][e][key] for e in common]
        o = [by_tech[technique][e][key] for e in common]
        b = sum(a and not c for a, c in zip(z, o))
        c = sum(c and not a for a, c in zip(z, o))
        entry[mode] = {"zpdpatch_beyond_own": sum(z), "other_beyond_own": sum(o), "only_zpdpatch": b,
                       "only_other": c, "exact_mcnemar_p": mcnemar(b, c)}
    summary["paired_with_zpdpatch"][technique] = entry

(OUT / "summary_vs_own.json").write_text(json.dumps(summary, indent=1) + "\n")

if __name__ == "__main__":
    for mode in MODES:
        s = summary["students_own_accepted"][mode]
        print(f"own accepted failing [{mode}]: {s['failing']}/{s['of']}")
    for t, e in summary["techniques"].items():
        a = e["any"]
        print(t, a["beyond_own"], a["within_reach_beyond_own"], a["own_fails"], a["within_reach_own_fails"])
    for t, e in summary["paired_with_zpdpatch"].items():
        print(t, e["common"], e["any"])
