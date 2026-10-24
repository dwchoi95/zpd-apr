"""Compute the paper's tables, figure data, and in-text numbers from ../output/ (the reported per-input rows).
Writes output/tables.tex ('% rows:<name>' sections for fill_tables.py) and output/numbers.txt.
Usage: python3 paper/src/summarize.py"""
import json
import os
import statistics
from collections import defaultdict

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # <repo>/paper/
OUT = os.path.join(os.path.dirname(PAPER), "output")                   # <repo>/output/

CONCEPTS = {
    "p02623": "Two-stack prefix sums", "p02659": "Exact decimals", "p02686": "Bracket ordering",
    "p02694": "Interest loop", "p02742": "Board parity", "p02743": "Square-root bounds",
    "p02761": "Digit constraints", "p02823": "Distance parity", "p02891": "Repeated-string runs",
    "p02975": "XOR circle", "p03240": "Center search", "p03324": "Divisibility count",
    "p03438": "Array operations", "p03838": "Sign cases",
}


def rows(path):
    with open(os.path.join(OUT, path), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def pct(x):
    return f"{100 * x:.1f}"


def num(x):
    return f"{x:g}" if float(x).is_integer() else f"{x:.1f}"


def rr(items):
    return sum(bool(r["repaired"]) for r in items) / len(items)


def more(a, b):
    """Relative difference of a over b, as the paper's 'X% more/fewer'."""
    return f"{100 * abs(a / b - 1):.1f}"


def reach_by_trajectory(steps):
    reach = {}
    for r in steps:
        defined = [s for s in r["step_ted"] if s is not None]
        reach[tuple(r["example_id"].split(":")[:2])] = max(defined) if defined else None
    return reach


def within_reach(items, reach):
    def ok(r):
        limit = reach.get((r["problem_id"], r["user_id"]))
        return bool(r["repaired"]) and limit is not None and r["ted_buggy_fixed"] is not None and r["ted_buggy_fixed"] <= limit
    return sum(map(ok, items)) / len(items)


def within_budget(items, budget):
    return sum(bool(r["repaired"]) and r["ted_buggy_fixed"] is not None and r["ted_buggy_fixed"] <= budget for r in items) / len(items)


def joint_retention(a, b):
    a = {r["example_id"]: r for r in a}
    joint = [k for k, r in a.items() for _ in [0] if r["repaired"]]
    b = {r["example_id"]: r for r in b}
    joint = [k for k in joint if b[k]["repaired"]]
    mean = lambda m, key: statistics.mean(m[k][key] for k in joint)
    return joint, {side: {key: mean(m, key) for key in ("token_retention", "line_retention")} for side, m in (("a", a), ("b", b))}


def main():
    tables, numbers = {}, {}

    # Table I and Figure 1: the RQ1 benchmark and its students' steps.
    inputs, steps = rows("benchmark/rq1-inputs.jsonl"), rows("benchmark/rq1-student-steps.jsonl")
    by_problem = defaultdict(list)
    for r in inputs:
        by_problem[r["problem_id"]].append(r)
    step_by_problem, reach_by_problem = defaultdict(list), defaultdict(list)
    for r in steps:
        defined = [s for s in r["step_ted"] if s is not None]
        p = r["example_id"].split(":")[0]
        step_by_problem[p] += defined
        reach_by_problem[p].append(max(defined))
    tables["data"] = [
        f"{p} & {CONCEPTS[p]} & {len(rs)} & {rs[0]['tests']} & {statistics.mean(r['loc'] for r in rs):.1f} & "
        f"{num(statistics.median(step_by_problem[p]))} & {num(statistics.median(reach_by_problem[p]))} \\\\"
        for p, rs in sorted(by_problem.items())]
    all_steps = [s for p in step_by_problem for s in step_by_problem[p]]
    all_reach = [x for p in reach_by_problem for x in reach_by_problem[p]]
    tables["datatotal"] = [
        f"Total & & {len(inputs):,} & {sum(rs[0]['tests'] for rs in by_problem.values())} & "
        f"{statistics.mean(r['loc'] for r in inputs):.1f} & {num(statistics.median(all_steps))} & {num(statistics.median(all_reach))} \\\\"]
    share = lambda b: sum(x <= b for x in all_reach) / len(all_reach)
    mentored, lsgen = rows("approaches/mentored.jsonl"), rows("approaches/lsgen.jsonl")
    tables["reach"] = [
        f"\\addplot[reference] coordinates {{(20,{pct(share(20))}) (160,{pct(share(160))})}};",
        *(f"\\addplot[{style}] coordinates {{(20,{pct(within_budget(m, 20))}) (160,{pct(within_budget(m, 160))}) (none,{pct(rr(m))})}};"
          for style, m in (("baseline2", mentored), ("baseline3", lsgen)))]
    numbers.update({"rq1.steps": len(all_steps), "rq1.step.median": num(statistics.median(all_steps)),
                    "rq1.step.mean": f"{statistics.mean(all_steps):.1f}", "rq1.reach.median": num(statistics.median(all_reach)),
                    "rq1.mentored.within20.fewer": more(within_budget(mentored, 20), rr(mentored)),
                    "rq1.lsgen.within20.fewer": more(within_budget(lsgen, 20), rr(lsgen))})

    # Table III and IV: target rules (RQ2).
    reach = reach_by_trajectory(rows("benchmark/canonical-student-steps.jsonl"))
    t = {split: {rule: rows(f"targets/{split}/{rule}.jsonl") for rule in ("answer", "progress")} for split in ("seen", "unseen", "java")}
    ret = {split: joint_retention(t[split]["answer"], t[split]["progress"]) for split in t}
    cell = lambda split, rule, f: f(split, rule)
    lines = []
    for label, f, java in (
        ("RR (\\%)", lambda s, r: pct(rr(t[s][r])), True),
        ("Within reach (\\%)", lambda s, r: pct(within_reach(t[s][r], reach)), False),
        ("Tokens (\\%)", lambda s, r: pct(ret[s][1]["a" if r == "answer" else "b"]["token_retention"]), True),
        ("Lines (\\%)", lambda s, r: pct(ret[s][1]["a" if r == "answer" else "b"]["line_retention"]), True),
    ):
        if lines:
            lines.append("\\midrule")
        for i, rule in enumerate(("answer", "progress")):
            head = f"\\multirow{{2}}{{*}}{{{label}}}" if i == 0 else ""
            values = [cell(s, rule, f) for s in ("seen", "unseen")] + [cell("java", rule, f) if java else "--"]
            lines.append(f"{head} & {rule.title()} & {' & '.join(values)} \\\\" if i == 0 else f" & {rule.title()} & {' & '.join(values)} \\\\")
    tables["targets"] = lines
    for s in t:
        a, b = ret[s][1]["a"], ret[s][1]["b"]
        numbers[f"rq2.{s}.joint"] = len(ret[s][0])
        numbers[f"rq2.{s}.tokens.more"] = more(b["token_retention"], a["token_retention"])
        numbers[f"rq2.{s}.lines.more"] = more(b["line_retention"], a["line_retention"])
        numbers[f"rq2.{s}.rr.fewer"] = more(rr(t[s]["progress"]), rr(t[s]["answer"]))
    ja = {r["example_id"]: r for r in t["java"]["answer"]}
    per_exercise = defaultdict(lambda: [0, 0])
    for r in t["java"]["answer"]:
        per_exercise[r["problem_id"]][0] += bool(r["repaired"])
    for r in t["java"]["progress"]:
        per_exercise[r["problem_id"]][1] += bool(r["repaired"])
    ex = [sum(a > p for a, p in per_exercise.values()), sum(a == p for a, p in per_exercise.values()), sum(a < p for a, p in per_exercise.values())]
    diffs = [r["token_retention"] - ja[r["example_id"]]["token_retention"] for r in t["java"]["progress"] if r["repaired"] and ja[r["example_id"]]["repaired"]]
    tr = [sum(d < 0 for d in diffs), sum(d == 0 for d in diffs), sum(d > 0 for d in diffs)]
    tables["uneven"] = [f"{label} & {e} & {pct(n / len(diffs))}\\% \\\\" for label, e, n in zip(("Answer better", "Tied", "Progress better"), ex, tr)]
    numbers["rq2.java.extra_repairs"] = sum(a - p for a, p in per_exercise.values() if a > p)
    numbers["rq2.java.max_extra_one_exercise"] = max(a - p for a, p in per_exercise.values())

    # Table V: ablation (RQ3); each variant against ZPDPatch under the same inference conditions.
    pairs = (("\\textsc{ZPDPatch}-Train", "no-training", "sampled"),
             ("\\textsc{ZPDPatch}-Portfolio", "one-checkpoint", "zpdpatch"),
             ("\\textsc{ZPDPatch}-Distinct", "same-checkpoint", "distinct-checkpoints"),
             ("\\textsc{ZPDPatch}+History", "history", "zpdpatch"))
    tables["ablation"] = []
    for label, variant, reference in pairs:
        cells = []
        for s in ("seen", "unseen"):
            v, z = rr(rows(f"ablation/{s}/{variant}.jsonl")), rr(rows(f"ablation/{s}/{reference}.jsonl"))
            cells += [pct(v), pct(z)]
            numbers[f"rq3.{variant}.{s}.fewer"] = more(v, z)
        tables["ablation"].append(f"{label} & {' & '.join(cells)} \\\\")

    # Table VI and Figure 6: generality (RQ4).
    settings = (("1.5B model", "scale-1.5b/seen", "scale-1.5b/unseen"), ("Java", "java-students", "java-exercises"))
    tables["generality"] = []
    for label, seen, unseen in settings:
        cells = []
        for key, path in (("seen", seen), ("unseen", unseen)):
            one, port = rr(rows(f"generality/{path}/one-checkpoint.jsonl")), rr(rows(f"generality/{path}/zpdpatch.jsonl"))
            cells += [pct(one), pct(port)]
            numbers[f"rq4.{path}.more"] = more(port, one)
        tables["generality"].append(f"{label} & {' & '.join(cells)} \\\\")
    codes = {"seen": ("SF", "SM", "SL"), "unseen": ("UF", "UM", "UL")}
    series = {}
    for name in ("zpdpatch", "one-checkpoint"):
        coords = []
        for s in ("seen", "unseen"):
            items = rows(f"generality/prefix/{s}/{name}.jsonl")
            for phase, code in zip(("early", "middle", "last"), codes[s]):
                coords.append(f"({pct(rr([r for r in items if r['trajectory_phase'] == phase]))},{code})")
        series[name] = " ".join(coords)
    tables["position"] = [f"\\addplot[proposed] coordinates {{{series['zpdpatch']}}};",
                          f"\\addplot[variant] coordinates {{{series['one-checkpoint']}}};"]

    with open(os.path.join(PAPER, "output", "tables.tex"), "w") as f:
        for name, body in tables.items():
            f.write(f"% rows:{name}\n" + "".join(line + "\n" for line in body))
    with open(os.path.join(PAPER, "output", "numbers.txt"), "w") as f:
        f.writelines(f"{k} = {v}\n" for k, v in numbers.items())
    print({k: len(v) for k, v in tables.items()}, len(numbers), "numbers")


if __name__ == "__main__":
    main()
