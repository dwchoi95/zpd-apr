"""Run plausible patches on generated inputs and compare them with the majority output of accepted programs.

Untrusted programs (students' accepted programs and plausible patches) run only through the repository runner,
src/core/runner/python_runner.py: one subprocess per input, temporary working directory, no shell, 2.5 s wall timeout,
outputs judged by src/core/runner/compare.py. This process only generates inputs and records results.

Usage: python src/experiments/differential/diff.py {validate|inputs|references|patches|recheck|sanity|summarize} [--workers 6]
Paths: ZPD_DIFF_DATA (RQ1 data root, default data-rq1), ZPD_DIFF_TEST (its repair dataset, default datasets/test.jsonl),
ZPD_DIFF_OUT (where inputs, references and outcomes go, default differential).
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import importlib.util
import json
import os
import random
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
GENERATORS = Path(__file__).resolve().parent / "generators"
OUT = Path(os.environ.get("ZPD_DIFF_OUT", "differential"))

from src.core.runner.compare import outputs_match  # noqa: E402
from src.core.runner.dataset import load_testcases  # noqa: E402
from src.core.runner.models import TestCase, Verdict  # noqa: E402
from src.core.runner.python_runner import PythonSubmissionRunner  # noqa: E402

DATA = Path(os.environ.get("ZPD_DIFF_DATA", "data-rq1"))
TEST = Path(os.environ.get("ZPD_DIFF_TEST", "datasets/test.jsonl"))
APPROACHES = Path("output/approaches")
STEPS = Path("output/benchmark/rq1-student-steps.jsonl")
TECHNIQUES = ["zpdpatch", "refactory", "brafar", "mentored", "lsgen-qwen", "lsgen"]
PROBLEMS = sorted(p.name for p in DATA.iterdir() if p.name.startswith("p"))
TIMEOUT_SEC = 2.5
N_REF = 7
SELECT_SEED = 20261026
SEEDS = range(1, 101)
VALIDATION_SEEDS = range(1, 51)
EXCLUDED: dict[str, str] = {}  # no RQ1 statement admits several outputs or a float answer
LOCK = threading.Lock()


def jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


@functools.cache
def runner(problem):
    meta = json.loads((DATA / problem / "metadata.json").read_text())
    # memory_limit is in KB; the runner enforces it only on Linux (RLIMIT_AS), not on this macOS host
    return PythonSubmissionRunner(timeout_sec=TIMEOUT_SEC, memory_limit_mb=int(meta["memory_limit"]) // 1024)


def generator(problem):
    spec = importlib.util.spec_from_file_location(problem, GENERATORS / f"{problem}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@functools.cache
def reference_programs():
    """Up to N_REF distinct accepted programs per problem, a fixed-seed sample of the students' targets."""
    distinct = defaultdict(dict)
    for row in jsonl(TEST):
        distinct[row["problem_id"]].setdefault(row["target_code"], row["example_id"])
    chosen = {}
    for problem in PROBLEMS:
        pool = [(eid, code) for code, eid in distinct[problem].items()]
        picked = random.Random(f"{SELECT_SEED}:{problem}").sample(pool, min(N_REF, len(pool)))
        chosen[problem] = [{"example_id": eid, "sha256": sha(code), "code": code} for eid, code in picked]
    return chosen


def run(problem, code, seed, text, expected=""):
    return runner(problem).run_case(code, TestCase(case_id=str(seed), input_text=text, expected_text=expected))


def pmap(fn, items, workers):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


def run_references(problem, inputs, workers):
    refs = reference_programs()[problem]
    jobs = [(i, seed, text) for seed, text in inputs for i in range(len(refs))]
    results = pmap(lambda j: (j, run(problem, refs[j[0]]["code"], j[1], j[2])), jobs, workers)
    by_seed = defaultdict(dict)
    for (i, seed, _), outcome in results:
        by_seed[seed][i] = outcome
    return refs, by_seed


def cluster(outcomes):
    """Group finished outputs (no RE/TLE) by the benchmark's comparison; returns [(representative, [indices])]."""
    groups = []
    for i, outcome in sorted(outcomes.items()):
        if outcome.verdict in (Verdict.RE, Verdict.TLE):
            continue
        for group in groups:
            if outputs_match(group[0], outcome.stdout):
                group[1].append(i)
                break
        else:
            groups.append((outcome.stdout, [i]))
    return sorted(groups, key=lambda g: -len(g[1]))


def cmd_validate(args):
    for problem in args.problems:
        gen = generator(problem)
        inputs = [(seed, gen.generate(seed)) for seed in VALIDATION_SEEDS]
        refs, by_seed = run_references(problem, inputs, args.workers)
        rows = []
        for seed, _ in inputs:
            outs = by_seed[seed]
            groups = cluster(outs)
            rows.append({
                "seed": seed,
                "verdicts": [outs[i].verdict.value for i in range(len(refs))],
                "runtime_sec": [round(outs[i].runtime_sec, 3) for i in range(len(refs))],
                "stderr_tail": {refs[i]["example_id"]: outs[i].stderr[-300:] for i in range(len(refs))
                                if outs[i].verdict == Verdict.RE},
                "cluster_sizes": [len(g[1]) for g in groups],
            })
        write_jsonl(OUT / "validation" / f"{problem}.jsonl", rows)
        re_count = sum(v == "RE" for r in rows for v in r["verdicts"])
        tle = sum(v == "TLE" for r in rows for v in r["verdicts"])
        split = sum(1 for r in rows if not r["cluster_sizes"] or r["cluster_sizes"][0] < len(refs))
        slow = max(t for r in rows for t in r["runtime_sec"])
        print(f"{problem}: RE={re_count} TLE={tle} not-unanimous={split} max_runtime={slow:.2f}s", flush=True)


def cmd_inputs(args):
    for problem in args.problems:
        gen = generator(problem)
        write_jsonl(OUT / "inputs" / f"{problem}.jsonl", [{"seed": s, "input": gen.generate(s)} for s in SEEDS])
        print(problem, "inputs written", flush=True)


def cmd_references(args):
    refs_all = reference_programs()
    (OUT / "references" / "programs.json").write_text(json.dumps(
        {p: [{"example_id": r["example_id"], "sha256": r["sha256"]} for r in refs_all[p]] for p in PROBLEMS},
        indent=1) + "\n")
    dropped = [r for r in jsonl(OUT / "references" / "dropped.jsonl")
               if r["problem_id"] not in args.problems] if (OUT / "references" / "dropped.jsonl").exists() else []
    for problem in args.problems:
        inputs = [(r["seed"], r["input"]) for r in jsonl(OUT / "inputs" / f"{problem}.jsonl")]
        refs, by_seed = run_references(problem, inputs, args.workers)
        kept = []
        for seed, _ in inputs:
            outs = by_seed[seed]
            groups = cluster(outs)
            verdicts = [outs[i].verdict.value for i in range(len(refs))]
            runtimes = [round(outs[i].runtime_sec, 3) for i in range(len(refs))]
            if groups and len(groups[0][1]) * 2 > len(refs):
                kept.append({"seed": seed, "output": groups[0][0], "agreeing": len(groups[0][1]),
                             "programs": len(refs), "verdicts": verdicts, "runtime_sec": runtimes})
            else:
                dropped.append({"problem_id": problem, "seed": seed, "reason": "no strict majority",
                                "cluster_sizes": [len(g[1]) for g in groups], "verdicts": verdicts,
                                "runtime_sec": runtimes})
        write_jsonl(OUT / "references" / f"{problem}.jsonl", kept)
        print(f"{problem}: kept {len(kept)}/{len(inputs)}", flush=True)
    write_jsonl(OUT / "references" / "dropped.jsonl", sorted(dropped, key=lambda r: (r["problem_id"], r["seed"])))


def plausible(technique):
    return [r for r in jsonl(APPROACHES / f"{technique}.jsonl") if r.get("repaired") is True]


EXEC_DIRS = {"patches": "executions", "targets": "executions_own"}  # amendment 2026-10-27: students' own targets


def program_set(which):
    """problem -> sha -> code: the six techniques' plausible patches, or the students' own accepted programs."""
    programs = defaultdict(dict)
    if which == "targets":
        for row in jsonl(TEST):
            programs[row["problem_id"]][sha(row["target_code"])] = row["target_code"]
    else:
        for technique in TECHNIQUES:
            for row in plausible(technique):
                programs[row["problem_id"]][sha(row["generated_code"])] = row["generated_code"]
    return programs


def cmd_patches(args):
    programs = program_set(args.set)
    for problem in args.problems:
        path = OUT / EXEC_DIRS[args.set] / f"{problem}.jsonl"
        done = {r["sha256"] for r in jsonl(path)} if path.exists() else set()
        refs = jsonl(OUT / "references" / f"{problem}.jsonl")
        inputs = {r["seed"]: r["input"] for r in jsonl(OUT / "inputs" / f"{problem}.jsonl")}
        todo = [(h, c) for h, c in sorted(programs[problem].items()) if h not in done]
        print(f"{problem}: {len(programs[problem])} distinct programs, {len(todo)} to run, {len(refs)} inputs",
              flush=True)
        started = time.time()

        def one(item, problem=problem, refs=refs, inputs=inputs, path=path):
            digest, code = item
            verdicts, runtimes, first = {}, {}, None
            for ref in refs:
                outcome = run(problem, code, ref["seed"], inputs[ref["seed"]], ref["output"])
                verdicts[str(ref["seed"])] = outcome.verdict.value
                runtimes[str(ref["seed"])] = round(outcome.runtime_sec, 3)
                if first is None and outcome.verdict != Verdict.AC:
                    first = {"seed": ref["seed"], "stdout_head": outcome.stdout[:200],
                             "stderr_tail": outcome.stderr[-300:]}
            with LOCK, open(path, "a") as f:
                f.write(json.dumps({"sha256": digest, "problem_id": problem, "verdicts": verdicts,
                                    "runtime_sec": runtimes, "first_failure": first}) + "\n")

        pmap(one, todo, args.workers)
        print(f"{problem}: done in {time.time() - started:.0f}s", flush=True)


def cmd_recheck(args):
    """Run each TLE (program, seed) once more, as a load check; the primary outcome is left unchanged."""
    for problem in args.problems:
        path = OUT / EXEC_DIRS[args.set] / f"{problem}.jsonl"
        rows = jsonl(path)
        codes = program_set(args.set)[problem]
        refs = {r["seed"]: r["output"] for r in jsonl(OUT / "references" / f"{problem}.jsonl")}
        inputs = {r["seed"]: r["input"] for r in jsonl(OUT / "inputs" / f"{problem}.jsonl")}
        jobs = [(r["sha256"], int(s)) for r in rows for s, v in r["verdicts"].items()
                if v == "TLE" and str(s) not in r.get("tle_recheck", {})]
        results = pmap(lambda j: (j, run(problem, codes[j[0]], j[1], inputs[j[1]], refs[j[1]])), jobs, args.workers)
        found = defaultdict(dict)
        for (digest, seed), outcome in results:
            found[digest][str(seed)] = {"verdict": outcome.verdict.value, "runtime_sec": round(outcome.runtime_sec, 3)}
        for r in rows:
            if r["sha256"] in found:
                r.setdefault("tle_recheck", {}).update(found[r["sha256"]])
        write_jsonl(path, rows)
        print(f"{problem}: rechecked {len(jobs)} TLE runs", flush=True)


def cmd_sanity(args):
    refs_all = reference_programs()
    report = {"reference_fixeval": [], "zpdpatch_fixeval": []}
    for problem in PROBLEMS:
        cases = load_testcases(DATA / problem / "testcases.jsonl")
        for ref in refs_all[problem][:2]:
            outcome = runner(problem).run_submission(submission_id=ref["example_id"], problem_id=problem,
                                                     code=ref["code"], source_verdict="Accepted", testcases=cases)
            report["reference_fixeval"].append({"problem_id": problem, "example_id": ref["example_id"],
                                                "verdict": outcome.verdict.value, "cases": len(cases),
                                                "passed": sum(c.verdict == Verdict.AC for c in outcome.cases)})
            print("ref", problem, ref["example_id"], outcome.verdict.value, flush=True)
    sample = random.Random(SELECT_SEED).sample(plausible("zpdpatch"), 20)
    for row in sample:
        cases = load_testcases(DATA / row["problem_id"] / "testcases.jsonl")
        outcome = runner(row["problem_id"]).run_submission(submission_id=row["example_id"],
                                                           problem_id=row["problem_id"], code=row["generated_code"],
                                                           source_verdict=None, testcases=cases)
        report["zpdpatch_fixeval"].append({"example_id": row["example_id"], "verdict": outcome.verdict.value,
                                           "cases": len(cases),
                                           "passed": sum(c.verdict == Verdict.AC for c in outcome.cases)})
        print("zpd", row["example_id"], outcome.verdict.value, flush=True)
    (OUT / "sanity" / "fixeval_spot_checks.json").write_text(json.dumps(report, indent=1) + "\n")


def share(num, den):
    return {"count": num, "of": den, "share": num / den if den else None}


def cmd_summarize(args):
    reach = {}
    for row in jsonl(STEPS):
        reach[":".join(row["example_id"].split(":")[:2])] = max(row["step_ted"])
    executions = {}
    for problem in PROBLEMS:
        if problem in EXCLUDED:
            continue
        for row in jsonl(OUT / "executions" / f"{problem}.jsonl"):
            executions[(problem, row["sha256"])] = row
    kept = {p: len(jsonl(OUT / "references" / f"{p}.jsonl")) for p in PROBLEMS if p not in EXCLUDED}
    summary = {"family": "differential-20261026-v1", "protocol": "zpd-differential-20261026.md",
               "timeout_sec": TIMEOUT_SEC, "reference_programs_per_problem": N_REF, "seeds": [1, 100],
               "excluded_problems": EXCLUDED, "kept_inputs": kept,
               "dropped_inputs": jsonl(OUT / "references" / "dropped.jsonl"),
               "fail_definition": "any kept input with WA, RE or TLE under the runner (2.5 s)",
               "within_reach_definition": "ted_buggy_fixed <= max(step_ted) of the trajectory "
                                          "(output/benchmark/rq1-student-steps.jsonl, key problem:user)",
               "techniques": {}}
    for technique in TECHNIQUES:
        out_rows = []
        for row in plausible(technique):
            problem = row["problem_id"]
            if problem in EXCLUDED:
                continue
            ex = executions[(problem, sha(row["generated_code"]))]
            fails = [(int(s), v) for s, v in sorted(ex["verdicts"].items(), key=lambda kv: int(kv[0])) if v != "AC"]
            recheck = ex.get("tle_recheck", {})
            confirmed = [(s, v) for s, v in fails if v != "TLE" or recheck.get(str(s), {}).get("verdict", "AC") != "AC"]
            key = ":".join(row["example_id"].split(":")[:2])
            ted = row.get("ted_buggy_fixed")
            out_rows.append({
                "example_id": row["example_id"], "problem_id": problem, "program_sha256": ex["sha256"],
                "inputs_run": len(ex["verdicts"]), "failures": len(fails),
                "failure_kinds": dict(Counter(v for _, v in fails)),
                "first_failing_seed": fails[0][0] if fails else None,
                "first_failing_kind": fails[0][1] if fails else None,
                "failures_tle_rechecked": len(confirmed),
                "ted_buggy_fixed": ted, "demonstrated_reach": reach[key],
                "within_reach": ted is not None and ted <= reach[key],
            })
        write_jsonl(OUT / "outcomes" / f"{technique}.jsonl", out_rows)
        within = [r for r in out_rows if r["within_reach"]]
        per_problem = {}
        for problem in PROBLEMS:
            rows = [r for r in out_rows if r["problem_id"] == problem]
            per_problem[problem] = {"plausible": len(rows), "failing": sum(r["failures"] > 0 for r in rows),
                                    "within_reach": sum(r["within_reach"] for r in rows),
                                    "within_reach_failing": sum(r["within_reach"] and r["failures"] > 0 for r in rows)}
        summary["techniques"][technique] = {
            "plausible": len(out_rows),
            "failing_any": share(sum(r["failures"] > 0 for r in out_rows), len(out_rows)),
            "within_reach_plausible": len(within),
            "within_reach_failing_any": share(sum(r["failures"] > 0 for r in within), len(within)),
            "failing_any_wa_or_re_only": share(
                sum(any(k in r["failure_kinds"] for k in ("WA", "RE")) for r in out_rows), len(out_rows)),
            "within_reach_failing_any_wa_or_re_only": share(
                sum(any(k in r["failure_kinds"] for k in ("WA", "RE")) for r in within), len(within)),
            "failing_any_after_tle_recheck": share(sum(r["failures_tle_rechecked"] > 0 for r in out_rows),
                                                   len(out_rows)),
            "within_reach_failing_any_after_tle_recheck": share(
                sum(r["failures_tle_rechecked"] > 0 for r in within), len(within)),
            "first_failing_kind": dict(Counter(r["first_failing_kind"] for r in out_rows if r["failures"])),
            "per_problem": per_problem,
        }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    for t, s in summary["techniques"].items():
        print(t, s["failing_any"], s["within_reach_failing_any"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "inputs", "references", "patches", "recheck", "sanity",
                                            "summarize"])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--set", choices=sorted(EXEC_DIRS), default="patches")
    parser.add_argument("--problems", nargs="*", default=PROBLEMS)
    args = parser.parse_args()
    args.problems = [p for p in args.problems if p not in EXCLUDED]
    globals()[f"cmd_{args.command}"](args)
