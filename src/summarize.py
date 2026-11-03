"""Compute the paper's tables, figure data, and in-text numbers from ../output/ (the reported per-input rows).
Writes output/tables.tex ('% rows:<name>' sections for fill_tables.py) and output/numbers.txt.
Usage: python3 paper/src/summarize.py"""
import json
import os
import random
import math
import statistics
from collections import defaultdict

PAPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # <repo>/paper/
OUT = os.path.join(os.path.dirname(PAPER), "output")                   # <repo>/output/

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


def interval(items, hit, samples=2000, seed=2027):
    """95% percentile interval, in percent, of the share of items that hit, resampling problems with replacement."""
    counts = defaultdict(lambda: [0, 0])
    for r in items:
        counts[r["problem_id"]][0] += bool(hit(r))
        counts[r["problem_id"]][1] += 1
    problems, rng, draws = sorted(counts), random.Random(seed), []
    for _ in range(samples):
        pick = [counts[rng.choice(problems)] for _ in problems]
        draws.append(100 * sum(h for h, _ in pick) / sum(n for _, n in pick))
    draws.sort()
    return draws[int(0.025 * samples)], draws[int(0.975 * samples) - 1]


def bars(style, axis, points):
    """One pgfplots bar series with asymmetric error bars; points are (position, items, hit)."""
    other = "y" if axis == "x" else "x"
    lines = []
    for position, items, hit in points:
        value = 100 * sum(bool(hit(r)) for r in items) / len(items)
        low, high = interval(items, hit)
        lines.append(f"{value:.1f} {position} {high - value:.1f} {value - low:.1f}")
    return (f"\\addplot[{style}, error bars/.cd, {axis} dir=both, {axis} explicit] table[row sep=\\\\, {axis}=v, {other}=at, "
            f"{axis} error plus=p, {axis} error minus=m] {{v at p m\\\\ {'\\\\ '.join(lines)}\\\\}};")


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



def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"text.usetex": True, "text.latex.preamble": r"\usepackage{mathptmx}", "font.family": "serif",
                         "font.size": 8, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6})
    return plt


def plot_attempts(d):
    """Figure 1: (a) trajectories (student-problem pairs) of CodeNet's AtCoder submissions by the submission at which
    they are first accepted, with those never accepted at 0 (every count above zero; log scales); (b) verdict changes between any two consecutive submissions,
    also after acceptance; each with its sub-caption below. Written to output/fig-attempts.pdf."""
    from matplotlib.colors import LogNorm
    plt = _mpl()
    fig, (ax, hx) = plt.subplots(1, 2, figsize=(3.45, 1.55), gridspec_kw={"width_ratios": [1, 1]})
    pts = sorted((int(k), v) for k, v in d["attempts"].items() if v > 0)
    top = pts[-1][0]
    ax.scatter([k for k, _ in pts], [v for _, v in pts], s=3, color="black", linewidths=0)
    ax.scatter([0], [d["pairs_never"]], s=6, facecolors="none", edgecolors="black", linewidths=0.6)   # never accepted, at 0
    ax.set_xscale("symlog", linthresh=10, linscale=0.8); ax.set_yscale("log"); ax.set_xlim(-0.5, top * 1.1)
    ticks = [0, 1, 2, 3, 5, 10, 20, 50, 100, top]
    ax.set_xticks(ticks, [str(x) for x in ticks], fontsize=5.5)
    ax.minorticks_off()
    ax.set_xlabel("Submissions"); ax.set_ylabel("Trajectories")
    ax.grid(color="0.9", linewidth=0.4); ax.set_axisbelow(True)
    names = {"Wrong Answer": "WA", "Time Limit Exceeded": "TLE", "Runtime Error": "RE", "Memory Limit Exceeded": "MLE",
             "Compile Error": "CE", "Accepted": "AC"}
    rows_ = cols = list(names.values())   # pairs with another status (e.g., Output Limit Exceeded) are left out
    m = [[0] * len(cols) for _ in rows_]
    for key, v in d["transitions"].items():
        a, b = (names.get(s) for s in key.split(" -> "))
        if a in rows_ and b in cols:
            m[rows_.index(a)][cols.index(b)] += v
    norm = LogNorm(vmin=1, vmax=max(map(max, m)))
    cmap = plt.get_cmap("Greys")
    hx.imshow([[max(x, 1) for x in r] for r in m], cmap=cmap, norm=norm, aspect="auto")
    for i, r in enumerate(m):
        for j, x in enumerate(r):
            label = f"{x / 1e6:.1f}M" if x >= 1e6 else f"{x / 1000:.0f}k" if x >= 1000 else str(x)
            hx.text(j, i, label, ha="center", va="center", fontsize=4.5, color="white" if sum(cmap(norm(max(x, 1)))[:3]) / 3 < 0.55 else "black")
    hx.set_xticks(range(len(cols)), cols, fontsize=6); hx.set_yticks(range(len(rows_)), rows_, fontsize=6)
    hx.set_xlabel("Next verdict"); hx.set_ylabel("Previous verdict")
    fig.tight_layout(pad=0.2, w_pad=0.8)
    fig.canvas.draw()  # sub-captions under both panels, on one line below the lower x label
    inv = fig.transFigure.inverted()
    y = min(inv.transform(a.xaxis.label.get_window_extent())[0][1] for a in (ax, hx)) - 0.04
    for a, s in ((ax, "(a) Submissions to Acceptance"), (hx, "(b) Verdict Changes")):
        x0, x1 = a.get_position().x0, a.get_position().x1
        fig.text((x0 + x1) / 2, y, s, ha="center", va="top", fontsize=8)
    fig.savefig(os.path.join(PAPER, "output", "fig-attempts.pdf"), bbox_inches="tight", pad_inches=0.01)
    plt.close(fig)


def in_text(numbers, mentored, lsgen, steps, t, reach):
    """Numbers the prose states that no table or figure carries."""
    # Section II-B: a student's own step against a returned program.
    all_steps = [s for r in steps for s in r["step_ted"] if s is not None]
    numbers["rq1.step.token_retention.median"] = pct(statistics.median(x for r in steps for x in r["step_token_retention"] if x is not None))
    lsgen_ted = statistics.mean(r["ted_buggy_fixed"] for r in lsgen if r["repaired"] and r["ted_buggy_fixed"] is not None)
    numbers["rq1.lsgen.ted_vs_step.more"] = more(lsgen_ted, statistics.mean(all_steps))
    numbers["rq1.mentored.rr"], numbers["rq1.lsgen.rr"] = pct(rr(mentored)), pct(rr(lsgen))

    # Settings and Section III: the corpus.
    with open(os.path.join(OUT, "benchmark/corpus.json")) as f:
        corpus = json.load(f)
    seen = corpus["seen_training"]
    numbers.update({"train.trajectories": f"{seen['trajectories']:,}", "train.problems": seen["problems"],
                    **{f"train.pairs.{k}": f"{v:,}" for k, v in seen["pairs"].items()},
                    "train.progress.same_verdict": f"{seen['progress_pairs_same_verdict']:,}",
                    "train.progress.same_verdict.share": pct(seen["progress_pairs_same_verdict"] / seen["pairs"]["progress"]),
                    "train.pairs.progress.more_than_strict": more(seen["pairs"]["progress"], seen["pairs"]["strict"]),
                    "train.consecutive_pairs": f"{seen['consecutive_failing_pairs']:,}",
                    "train.consecutive_pairs.same_verdict.share": pct(seen["consecutive_failing_pairs_same_verdict"] / seen["consecutive_failing_pairs"]),
                    **{f"java.{k}": f"{v:,}" for k, v in corpus["codeworkout"].items()}})
    canonical = rows("benchmark/canonical-inputs.jsonl")
    for split in ("seen", "unseen"):
        items = [r for r in canonical if r["split"] == split]
        numbers[f"{split}.inputs"], numbers[f"{split}.problems"] = len(items), len({r["problem_id"] for r in items})
        numbers[f"{split}.loc.mean"] = f"{statistics.mean(r['loc'] for r in items):.1f}"
    seen_inputs = [r for r in canonical if r["split"] == "seen"]
    numbers["seen.wa.share"] = pct(sum(r["verdict"] == "WA" for r in seen_inputs) / len(seen_inputs))

    # Section III-E: Select on the validation inputs.
    names = [f"{rule}{seed}" for rule in ("Answer", "Progress", "Strict") for seed in (2027, 2028, 2029)]
    repaired = {n: {r["example_id"] for r in rows(f"selection/{n}.jsonl") if r["repaired"]} for n in names}
    validation = len(rows("selection/Answer2027.jsonl"))
    union = lambda members: len(set().union(*(repaired[m] for m in members)))
    single = [len(repaired[n]) / validation for n in names]
    chosen = ["Answer2027", "Answer2028", "Answer2029"]
    one_per_rule = max(union((a, p, s)) for a in names[:3] for p in names[3:6] for s in names[6:])
    numbers.update({"select.validation": validation, "select.single.min": pct(min(single)), "select.single.max": pct(max(single)),
                    "select.first": pct(len(repaired[chosen[0]]) / validation),
                    "select.second.adds": len(repaired[chosen[1]] - repaired[chosen[0]]),
                    "select.third.adds": len(repaired[chosen[2]] - repaired[chosen[0]] - repaired[chosen[1]]),
                    "select.portfolio": pct(union(chosen) / validation), "select.portfolio.more": more(union(chosen) / validation, max(single)),
                    "select.all_nine": pct(union(names) / validation), "select.share_of_nine": pct(union(chosen) / union(names)),
                    "select.one_per_rule": pct(one_per_rule / validation)})

    # RQ3 (target source): edit size and reach of the two rules.
    for split in ("seen", "unseen"):
        a, p = ({r["example_id"]: r for r in t[split][rule]} for rule in ("answer", "progress"))
        joint = [k for k in a if a[k]["repaired"] and p[k]["repaired"]
                 and a[k]["ted_buggy_fixed"] is not None and p[k]["ted_buggy_fixed"] is not None]
        numbers[f"rq3.{split}.ted.smaller"] = more(statistics.mean(p[k]["ted_buggy_fixed"] for k in joint), statistics.mean(a[k]["ted_buggy_fixed"] for k in joint))
        wa, wp = within_reach(t[split]["answer"], reach), within_reach(t[split]["progress"], reach)
        numbers[f"rq3.{split}.within_reach.difference"] = more(wp, wa)
        numbers[f"rq3.{split}.answer.repairs_within_reach.share"] = pct(wa / rr(t[split]["answer"]))
        numbers[f"rq3.{split}.progress.repairs_within_reach.share"] = pct(wp / rr(t[split]["progress"]))

        own, peer = (rows(f"targets/{split}/progress-{n}.jsonl") for n in ("same-user", "cross-user"))
        numbers[f"rq3.{split}.peer_targets.more"] = more(rr(peer), rr(own))
        own, peer = ({r["example_id"]: r for r in items} for items in (own, peer))
        joint = [k for k in own if own[k]["repaired"] and peer[k]["repaired"]
                 and own[k]["ted_buggy_fixed"] is not None and peer[k]["ted_buggy_fixed"] is not None]
        numbers[f"rq3.{split}.peer_targets.ted.larger"] = more(statistics.mean(peer[k]["ted_buggy_fixed"] for k in joint),
                                                             statistics.mean(own[k]["ted_buggy_fixed"] for k in joint))

    # Threats to Validity.
    port = rows("ablation/seen/zpdpatch.jsonl")
    rq1_fixed = [r for r in rows("approaches/zpdpatch.jsonl") if r["repaired"]]
    numbers["threats.rq1.training_copy"] = sum(r["training_copy"] for r in rq1_fixed)
    numbers["threats.rq1.repairs"] = len(rq1_fixed)
    ast_copy = lambda name: [r["training_ast_copy"] for r in rows(f"approaches/{name}.jsonl") if r["repaired"]]
    numbers["threats.rq1.training_ast_copy"] = sum(ast_copy("zpdpatch"))
    numbers["threats.rq1.training_ast_copy.share"] = pct(statistics.mean(ast_copy("zpdpatch")))
    shares = [100 * statistics.mean(ast_copy(n)) for n in ("refactory", "brafar", "mentored", "lsgen-qwen", "lsgen")]
    numbers["threats.rq1.others.training_ast_copy.range"] = f"{min(shares):.1f}--{max(shares):.1f}"
    numbers["threats.training_copy.share"] = pct(sum(r["training_copy"] for r in port if r["repaired"]) / sum(r["repaired"] for r in port))
    rq1_inputs = rows("benchmark/rq1-inputs.jsonl")
    problems = len({r["problem_id"] for r in rq1_inputs} | {r["problem_id"] for r in canonical}) + corpus["codeworkout"]["exercises"]
    submissions = len({r["example_id"] for r in rq1_inputs} | {r["example_id"] for r in canonical}) + corpus["codeworkout"]["test_trajectories"]
    stated = submissions // 1000 * 1000  # "over 3,000"
    prior_problems, prior_submissions = (5, 65), (407, 1783)  # Refactory/Brafar and LSGen benchmarks, as their papers report
    numbers.update({"threats.problems": problems, "threats.submissions": f"{submissions:,}", "threats.submissions.stated": f"{stated:,}",
                    "threats.problems.times": f"{problems / max(prior_problems):.1f}--{problems / min(prior_problems):.1f}",
                    "threats.submissions.times": f"{stated / max(prior_submissions):.1f}--{stated / min(prior_submissions):.1f}"})


def main():
    tables, numbers = {}, {}

    # Table I and Figure 1: the RQ1 benchmark and its students' steps.
    inputs, steps = rows("benchmark/rq1-inputs.jsonl"), rows("benchmark/rq1-student-steps.jsonl")
    step_by_problem, reach_by_problem = defaultdict(list), defaultdict(list)
    for r in steps:
        defined = [s for s in r["step_ted"] if s is not None]
        p = r["example_id"].split(":")[0]
        step_by_problem[p] += defined
        reach_by_problem[p].append(max(defined))
    all_steps = [s for p in step_by_problem for s in step_by_problem[p]]
    all_reach = [x for p in reach_by_problem for x in reach_by_problem[p]]

    def bench_row(label, items, step_rows):
        """One row of Table I: problems, buggy programs, test cases, mean LOC, and median step and reach."""
        tests = {r["problem_id"]: r["tests"] for r in items}
        defined = [d for d in ([s for s in r["step_ted"] if s is not None] for r in step_rows) if d]
        step = num(statistics.median(s for d in defined for s in d)) if defined else "--"
        reach = num(statistics.median(max(d) for d in defined)) if defined else "--"
        return (f"{label} & {len(tests)} & {len(items):,} & {sum(tests.values()):,} & "
                f"{statistics.mean(r['loc'] for r in items):.1f} & {step} & {reach} \\\\")
    # Upper part: the RQ1 benchmark by AtCoder score; lower part: the test sets of RQ3 and RQ4 (no student steps for Java).
    score = {r["problem_id"]: r["score"] for r in inputs}
    difficulty = {200: "Easy", 300: "Medium", 600: "Hard"}
    tables["data"] = [bench_row(difficulty[points], [r for r in inputs if r["score"] == points],
                                [r for r in steps if score[r["example_id"].split(":")[0]] == points])
                      for points in sorted(set(score.values()))]
    tables["datatotal"] = [bench_row("Total", inputs, steps)]
    canonical, canonical_steps = rows("benchmark/canonical-inputs.jsonl"), rows("benchmark/canonical-student-steps.jsonl")
    split_of = {r["example_id"]: r["split"] for r in canonical}
    tables["datasplits"] = [bench_row(name.title(), [r for r in canonical if r["split"] == name],
                                      [r for r in canonical_steps if split_of[r["example_id"]] == name]) for name in ("seen", "unseen")]
    java = rows("benchmark/java-inputs.jsonl")
    tables["datasplits"].append(bench_row("Java", java, []))
    tables["datasplitstotal"] = [bench_row("Total", canonical + java, [])]  # steps exist for Python only, so none here
    medians = [statistics.median(v) for v in step_by_problem.values()]
    numbers["rq1.step.median.by_problem.range"] = f"{num(min(medians))}--{num(max(medians))}"
    share = lambda b: sum(x <= b for x in all_reach) / len(all_reach)
    mentored, lsgen = rows("approaches/mentored.jsonl"), rows("approaches/lsgen.jsonl")
    qwen = rows("approaches/lsgen-qwen.jsonl")
    refactory, brafar = rows("approaches/refactory.jsonl"), rows("approaches/brafar.jsonl")
    baselines = (refactory, brafar, mentored, qwen, lsgen)
    grid = (1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 1000)
    curve = lambda style, share: f"\\addplot[{style}] coordinates {{" + " ".join(f"({b},{100 * share(b):.1f})" for b in grid) + "};"
    # Section II-B: Figure 1, and the table of each baseline's patches against the student's own step from the same buggy
    # program to acceptance.
    step_share = lambda b: sum(x <= b for x in all_steps) / len(all_steps)
    sizes = lambda m: [r["ted_buggy_fixed"] for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None]
    codenet = json.load(open(os.path.join(OUT, "benchmark", "atcoder-attempts.json")))
    plot_attempts(codenet)
    failing = {"Wrong Answer", "Time Limit Exceeded", "Runtime Error", "Memory Limit Exceeded", "Compile Error"}
    fail_fail = {k: v for k, v in codenet["transitions"].items() if set(k.split(" -> ")) <= failing}
    first_fails = codenet["pairs_accepted"] + codenet["pairs_never"] - codenet["attempts"]["1"]
    numbers.update({"lim.codenet.problems": f"{codenet['problems']:,}", "lim.codenet.submissions": f"{codenet['submissions']:,}",
                    "lim.codenet.first_fails": f"{first_fails:,}", "lim.codenet.second.share": pct(codenet["attempts"]["2"] / first_fails),
                    "lim.codenet.attempts.max": max(map(int, codenet["attempts"])),
                    "lim.codenet.third_or_never.share": pct((sum(v for k, v in codenet["attempts"].items() if int(k) >= 3) + codenet["pairs_never"]) / first_fails),
                    "lim.codenet.fail_fail": f"{sum(fail_fail.values()):,}",
                    "lim.codenet.fail_fail.kept.share": pct(sum(v for k, v in fail_fail.items() if len(set(k.split(" -> "))) == 1) / sum(fail_fail.values()))})
    own_step = {r["example_id"]: r["step_ted"][-1] for r in steps}   # the student's step from s_{n-1} to acceptance
    configs = (("\\textsc{Refactory}", refactory), ("\\textsc{Brafar}", brafar), ("\\textsc{Mentored}", mentored),
               ("\\textsc{LSGen}\\textsubscript{Qwen}", qwen), ("\\textsc{LSGen}\\textsubscript{GPT}", lsgen))
    by_id, reach = {r["example_id"]: r for r in steps}, reach_by_trajectory(steps)
    student = {"ted_buggy_fixed": lambda k: own_step[k], "token_retention": lambda k: by_id[k]["step_token_retention"][-1],
               "line_retention": lambda k: by_id[k]["step_line_retention"][-1]}

    def against_student(fixes, key):   # shares of the patches below, equal to, and above the student's own step
        signs = [(r[key] > student[key](r["example_id"])) - (r[key] < student[key](r["example_id"])) for r in fixes]
        return [signs.count(s) / len(signs) for s in (-1, 0, 1)]
    split = [(name, [r for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None and own_step.get(r["example_id"]) is not None])
             for name, m in configs]
    tables["reach"] = [f"{name} & {len(f):,} & " + " & ".join(pct(x) for key in student for x in against_student(f, key)) + " \\\\"
                       for name, f in split]
    span = lambda values: f"{min(values):.1f}--{max(values):.1f}"
    beyond = lambda f: statistics.mean(r["ted_buggy_fixed"] > reach[tuple(r["example_id"].split(":")[:2])] for r in f)
    numbers.update({"lim.own.ted.larger.range": span([100 * against_student(f, "ted_buggy_fixed")[2] for _, f in split]),
                    "lim.own.ted.smaller.range": span([100 * against_student(f, "ted_buggy_fixed")[0] for _, f in split]),
                    "lim.own.token_retention.smaller.range": span([100 * against_student(f, "token_retention")[0] for _, f in split]),
                    "lim.own.line_retention.smaller.range": span([100 * against_student(f, "line_retention")[0] for _, f in split]),
                    "lim.own.beyond_reach.range": span([100 * beyond(f) for _, f in split])})
    own_step = {r["example_id"]: r["step_ted"][-1] for r in steps}   # the student's own step from the buggy program to acceptance
    larger = lambda m: [r["ted_buggy_fixed"] > own_step[r["example_id"]] for r in m
                        if r["repaired"] and r["ted_buggy_fixed"] is not None and own_step.get(r["example_id"]) is not None]
    four = (refactory, brafar, mentored, lsgen)
    numbers.update({"lim.baselines.ted.median.range": f"{min(statistics.median(sizes(m)) for m in four):g}--{max(statistics.median(sizes(m)) for m in four):g}",
                    "lim.baselines.larger_than_own_step.range": f"{min(100 * statistics.mean(larger(m)) for m in four):.1f}--{max(100 * statistics.mean(larger(m)) for m in four):.1f}"})
    fixed_ted = lambda m: statistics.mean(r["ted_buggy_fixed"] for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None)
    numbers.update({"lim.mentored.returns_submission.share": pct(1 - rr(mentored)), "lim.lsgen.returns_submission.share": pct(1 - rr(lsgen)),
                    "lim.lsgen_qwen.returns_submission.share": pct(1 - rr(qwen)), "rq1.lsgen_qwen.rr": pct(rr(qwen)),
                    "rq1.lsgen_qwen.ted_vs_step.more": more(fixed_ted(qwen), statistics.mean(all_steps)),
                    "lim.within20.fewer.range": "--".join(more(within_budget(m, 20), rr(m)) for m in (mentored, lsgen)) + " / qwen " + more(within_budget(qwen, 20), rr(qwen)),
                    "lim.within20.rr.range": f"{min(100 * within_budget(m, 20) for m in baselines):.1f}--{max(100 * within_budget(m, 20) for m in baselines):.1f}",
                    "lim.within20.fewer.all.range": f"{min(float(more(within_budget(m, 20), rr(m))) for m in baselines):.1f}--{max(float(more(within_budget(m, 20), rr(m))) for m in baselines):.1f}",
                    "lim.rr.range": f"{min(100 * rr(m) for m in baselines):.1f}--{max(100 * rr(m) for m in baselines):.1f}",
                    "lim.returns_submission.range": f"{min(100 * (1 - rr(m)) for m in baselines):.1f}--{max(100 * (1 - rr(m)) for m in baselines):.1f}",
                    "lim.ted_vs_step.max": f"{max(float(more(fixed_ted(m), statistics.mean(all_steps))) for m in baselines):.1f}",
                    "lim.baselines.ted_vs_step.range": f"{min(float(more(fixed_ted(m), statistics.mean(all_steps))) for m in (refactory, brafar, mentored, lsgen)):.1f}--{max(float(more(fixed_ted(m), statistics.mean(all_steps))) for m in (refactory, brafar, mentored, lsgen)):.1f}",
                    "lim.baselines.rr.range": f"{min(100 * rr(m) for m in (refactory, brafar, mentored, lsgen)):.1f}--{max(100 * rr(m) for m in (refactory, brafar, mentored, lsgen)):.1f}",
                    "lim.step.within20.share": pct(step_share(20)),
                    **{f"lim.{key}.rr": pct(rr(m)) for key, m in (("refactory", refactory), ("brafar", brafar))},
                    **{f"lim.{key}.ted_vs_step.more": more(fixed_ted(m), statistics.mean(all_steps)) for key, m in (("refactory", refactory), ("brafar", brafar), ("mentored", mentored))}})
    numbers.update({"rq1.steps": len(all_steps), "rq1.step.median": num(statistics.median(all_steps)),
                    "rq1.step.mean": f"{statistics.mean(all_steps):.1f}", "rq1.reach.median": num(statistics.median(all_reach)),
                    "rq1.mentored.within20.fewer": more(within_budget(mentored, 20), rr(mentored)),
                    "rq1.lsgen.within20.fewer": more(within_budget(lsgen, 20), rr(lsgen))})

    # Section II-B: pass rate and wrong-answer share at the first, middle, and last failing submissions and at acceptance,
    # over every trajectory, and the students' steps by class.
    def states(r):  # the distinct submissions of a trajectory, from its steps: (verdict, pass rate)
        return [(r["step_verdicts"][0][0], r["step_pass_rates"][0][0])] + [(b, pb) for (_, b), (_, pb) in zip(r["step_verdicts"], r["step_pass_rates"])]
    trajectories_states = [states(r) for r in steps]
    middles = [t[1:-2] for t in trajectories_states if len(t) > 3]
    points = (("first", [t[0][1] for t in trajectories_states], [t[0][0] == "WA" for t in trajectories_states]),
              ("middle", [statistics.mean(p for _, p in m) for m in middles], [statistics.mean(v == "WA" for v, _ in m) for m in middles]),
              ("last", [t[-2][1] for t in trajectories_states], [t[-2][0] == "WA" for t in trajectories_states]),
              ("accepted", [t[-1][1] for t in trajectories_states], [t[-1][0] == "WA" for t in trajectories_states]))
    numbers.update({"lim.trajectories": len(trajectories_states), "lim.trajectories.with_middle": len(middles),
                    **{f"lim.{name}.pass_rate": f"{100 * statistics.mean(p):.1f}" for name, p, _ in points},
                    **{f"lim.{name}.wa.share": f"{100 * statistics.mean(w):.1f}" for name, _, w in points},
                    "lim.last_passes_more_than_first.share": pct(sum(t[-2][1] > t[0][1] for t in trajectories_states) / len(trajectories_states)),
                    "lim.last_passes_as_many_as_first.share": pct(sum(t[-2][1] == t[0][1] for t in trajectories_states) / len(trajectories_states))})
    classes = [c for r in steps for c in r["step_class"]]
    failing_steps = [c for c in classes if c != "AC"]   # steps that end in a program failing some test case on re-execution
    up_worse = [c == "regress" for r in steps for (pa, pb), c in zip(r["step_pass_rates"], r["step_class"]) if c != "AC" and pb > pa]
    numbers.update({"lim.failing_steps": f"{len(failing_steps):,}", "lim.pass_rate_up.worse.share": pct(statistics.mean(up_worse)),
                    **{f"lim.failing_steps.{c}.share": pct(failing_steps.count(c) / len(failing_steps)) for c in ("forward", "sideways", "regress")}})
    numbers.update({**{f"lim.steps.{c}.share": pct(classes.count(c) / len(classes)) for c in ("AC", "forward", "sideways", "regress")},
                    "lim.trajectories.with_forward.share": pct(sum("forward" in r["step_class"] for r in steps) / len(steps)),
                    "lim.forward.verdict_kept.share": pct(sum(a == b for r in steps for (a, b), c in zip(r["step_verdicts"], r["step_class"]) if c == "forward")
                                                          / classes.count("forward")),
                    "lim.regress.verdict_kept.share": pct(sum(a == b for r in steps for (a, b), c in zip(r["step_verdicts"], r["step_class"]) if c == "regress")
                                                          / classes.count("regress"))})

    by_problem = lambda items: [[x for r, x in items if r["problem_id"] == p] for p in sorted({r["problem_id"] for r, _ in items})]
    balanced = lambda items: statistics.mean(statistics.mean(g) for g in by_problem(items) if g)
    numbers.update({f"lim.{name}.pass_rate.balanced": f"{100 * balanced([(r, p) for r, p in zip(steps, ps)]):.1f}"
                    for name, ps, _ in points[:3] if len(ps) == len(steps)})

    # RQ1 figure: the patches of ZPDPatch against the students' own steps.
    zpd, qwen = rows("approaches/zpdpatch.jsonl"), rows("approaches/lsgen-qwen.jsonl")
    rq1_reach = reach_by_trajectory(steps)
    fixes = lambda m: [r for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None]
    share_in_reach = lambda m: within_reach(m, rq1_reach) * len(m) / len(fixes(m))
    patch = [r["ted_buggy_fixed"] for r in fixes(zpd)]
    above = lambda xs, x: 100 * sum(v > x for v in xs) / len(xs)
    curves = [("referenceline", all_steps)] + [
        (style, [r["ted_buggy_fixed"] for r in fixes(m)])
        for style, m in (("refactoryline", refactory), ("brafarline", brafar), ("mentoredline", mentored),
                         ("qwenline", qwen), ("gptline", lsgen), ("proposedline", zpd))]
    # each curve, then its points on the two reference lines (median reach 49, and 50% at its median)
    tables["patchsize"] = [
        f"\\addplot[{s}] coordinates {{{' '.join(f'({x},{above(xs, x):.1f})' for x in (*range(1, 101), 120, 150, 200, 300, 500, 700, 1000))}}};"
        for s, xs in curves] + [
        f"\\addplot[{s}, forget plot, only marks, mark=*, mark size=1.1pt] coordinates {{(49,{above(xs, 49):.1f}) ({statistics.median(xs):g},50)}};"
        for s, xs in curves]
    numbers.update({"rq1.zpdpatch.rr": pct(rr(zpd)), "rq1.zpdpatch.within_reach.share": pct(share_in_reach(zpd)),
                    "rq1.zpdpatch.ted.median": num(statistics.median(patch)),
                    "rq1.zpdpatch.token_retention.median": pct(statistics.median(r["token_retention"] for r in fixes(zpd))),
                    "rq1.zpdpatch.own_accepted.share": pct(sum(r["ted_fixed_oracle"] == 0 for r in fixes(zpd)) / len(fixes(zpd))),
                    # patches and steps larger than the median student's demonstrated reach
                    "rq1.zpdpatch.above_reach_median.share": pct(sum(x > statistics.median(all_reach) for x in patch) / len(patch)),
                    "rq1.step.above_reach_median.share": pct(sum(x > statistics.median(all_reach) for x in all_steps) / len(all_steps)),
                    "rq1.zpdpatch.above_reach_median.fewer": more(sum(x > statistics.median(all_reach) for x in patch) / len(patch),
                                                                  sum(x > statistics.median(all_reach) for x in all_steps) / len(all_steps))})

    # Within reach by difficulty and by problem; line retention; the student's own fix of the same buggy program.
    for points, name in difficulty.items():
        group = [r for r in zpd if score[r["problem_id"]] == points]
        numbers[f"rq1.zpdpatch.within_reach.share.{name.lower()}"] = pct(share_in_reach(group))
        numbers[f"rq1.zpdpatch.repairs.{name.lower()}"] = sum(bool(r["repaired"]) for r in group)
    by_problem = defaultdict(list)
    for r in zpd:
        by_problem[r["problem_id"]].append(r)
    numbers["rq1.zpdpatch.problems.within_reach.share.at_least_70"] = sum(share_in_reach(g) >= 0.7 for g in by_problem.values())
    numbers["rq1.zpdpatch.line_retention.median"] = pct(statistics.median(r["line_retention"] for r in fixes(zpd)))
    numbers["rq1.step.line_retention.median"] = pct(statistics.median(x for r in steps for x in r["step_line_retention"]))
    own_fix = {r["example_id"]: r["step_ted"][-1] for r in steps}
    judged = [r for r in fixes(zpd) if own_fix[r["example_id"]] is not None]
    numbers["rq1.zpdpatch.no_larger_than_own_fix.share"] = pct(sum(r["ted_buggy_fixed"] <= own_fix[r["example_id"]] for r in judged) / len(judged))
    numbers["rq1.zpdpatch.within10_of_own_accepted.share"] = pct(sum(r["ted_fixed_oracle"] is not None and r["ted_fixed_oracle"] <= 10 for r in fixes(zpd)) / len(fixes(zpd)))

    # Table (RQ1): the patches of ZPDPatch against the students' own steps and fixes, by difficulty.
    groups = [[r for r in zpd if score[r["problem_id"]] == points] for points in difficulty] + [zpd]
    group_steps = [[r for r in steps if score[r["example_id"].split(":")[0]] == points] for points in difficulty] + [steps]
    near = lambda r, k: r["ted_fixed_oracle"] is not None and r["ted_fixed_oracle"] <= k
    against_fix = lambda test: [pct(sum(test(r) for r in fixes(g)) / len(fixes(g))) for g in groups]
    problems = lambda g: {r["problem_id"] for r in g}
    cells = lambda values: " & ".join(values) + " \\\\"

    # Table (RQ1): the forward steps students took against those ZPDPatch returns without repairing.
    short = {"Wrong Answer": "WA", "Time Limit Exceeded": "TLE", "Runtime Error": "RE", "Memory Limit Exceeded": "MLE"}
    v = lambda x: short.get(x, x)
    student_forward = [(v(a), v(b), pa, pb, t) for r in steps
                       for (a, b), (pa, pb), t, c in zip(r["step_verdicts"], r["step_pass_rates"], r["step_ted"], r["step_class"])
                       if c == "forward"]
    zpd_forward = [(v(r["buggy_verdict"]), v(r["fixed_verdict"]), r["buggy_pass_rate"], r["fixed_pass_rate"], r["ted_buggy_returned"])
                   for r in zpd if r["step_class"] == "forward"]
    def step_column(items):
        moves = [(a, b) for a, b, *_ in items]
        share = lambda pair: pct(moves.count(pair) / len(moves))
        rest = 1 - (moves.count(("WA", "WA")) + moves.count(("TLE", "WA"))) / len(moves)
        return [f"{len(items):,}", share(("WA", "WA")), share(("TLE", "WA")), pct(rest),
                pct(statistics.median(pb - pa for _, _, pa, pb, _ in items)),
                pct(statistics.median(pb / pa - 1 for _, _, pa, pb, _ in items if pa > 0)),
                num(statistics.median(t for *_, t in items if t is not None))]
    labels = ["Forward steps", "WA $\\to$ WA (\\%)", "TLE $\\to$ WA (\\%)", "Other (\\%)",
              "Pass rate gain (points)", "Pass rate gain (\\%)", "TED"]
    columns = list(zip(step_column(student_forward), step_column(zpd_forward)))
    tables["rq1steps"] = [f"{label} & {a} & {b} \\\\" + ("\n\\midrule" if i in (0, 3) else "") for i, (label, (a, b)) in enumerate(zip(labels, columns))]
    student_classes = [c for r in steps for c in r["step_class"]]
    changed = [r["step_class"] for r in zpd if r["step_class"] is not None]
    numbers.update({"rq1.step.regress.share": pct(student_classes.count("regress") / len(student_classes)),
                    "rq1.zpdpatch.changed.regress.share": pct(changed.count("regress") / len(changed))})

    # The students' own last step (to their accepted program) on the buggy programs ZPDPatch leaves and repairs.
    last = {r["example_id"]: r["step_ted"][-1] for r in steps}
    own = lambda repaired: statistics.mean(last[r["example_id"]] for r in zpd if bool(r["repaired"]) == repaired and last[r["example_id"]] is not None)
    numbers["rq1.zpdpatch.unrepaired.own_step.larger"] = more(own(False), own(True))

    # Table II and the RQ2 figure: ZPDPatch and the existing techniques on the same buggy programs.
    others = (("refactory", "\\textsc{Refactory}", refactory), ("brafar", "\\textsc{Brafar}", brafar),
              ("mentored", "\\textsc{Mentored}", mentored), ("lsgen_qwen", "\\textsc{LSGen}\\textsubscript{Qwen}", qwen),
              ("lsgen", "\\textsc{LSGen}\\textsubscript{GPT}", lsgen))
    mean = lambda m, key: statistics.mean(r[key] for r in fixes(m))
    # Table III (RQ1): every technique's repairs against the students' own steps and fixes.
    span = lambda values: f"{min(values):.1f}--{max(values):.1f}"
    techniques = [zpd] + [m for _, _, m in others]
    by_problem_of = lambda m: [[r for r in m if r["problem_id"] == p] for p in sorted({r["problem_id"] for r in fixes(m)})]
    no_larger = lambda r: own_fix[r["example_id"]] is not None and r["ted_buggy_fixed"] <= own_fix[r["example_id"]]
    share_of = lambda m, test: sum(map(test, fixes(m))) / len(fixes(m))
    columns = [[pct(share_in_reach(m)) for m in techniques],
               [f"{sum(share_in_reach(g) >= 0.7 for g in by_problem_of(m))}/{len(by_problem_of(m))}" for m in techniques],
               *([pct(statistics.median(r[key] for r in fixes(m))) for m in techniques] for key in ("token_retention", "line_retention")),
               *([pct(share_of(m, test)) for m in techniques] for test in (no_larger, lambda r: near(r, 10), lambda r: near(r, 0)))]
    rows_rq1 = [" & ".join(cells) + " \\\\" for cells in zip(["\\textsc{ZPDPatch}"] + [name for _, name, _ in others], *columns)]
    tables["rq1"] = [f"Students & -- & -- & {pct(statistics.median(x for r in steps for x in r['step_token_retention']))}"
                     f" & {pct(statistics.median(x for r in steps for x in r['step_line_retention']))} & -- & -- & -- \\\\",
                     "\\midrule"] + rows_rq1[1:] + ["\\midrule"] + rows_rq1[:1]
    rest = [m for _, _, m in others]
    above = lambda m: sum(r["ted_buggy_fixed"] > statistics.median(all_reach) for r in fixes(m)) / len(fixes(m))
    numbers.update({
        "rq1.others.within_reach.share.range": span([100 * share_in_reach(m) for m in rest]),
        "rq1.others.ted.median.range": f"{num(min(statistics.median(r['ted_buggy_fixed'] for r in fixes(m)) for m in rest))}--{num(max(statistics.median(r['ted_buggy_fixed'] for r in fixes(m)) for m in rest))}",
        "rq1.others.above_reach_median.share.range": span([100 * above(m) for m in rest]),
        "rq1.others.token_retention.median.max": f"{max(100 * statistics.median(r['token_retention'] for r in fixes(m)) for m in rest):.1f}",
        "rq1.others.line_retention.median.max": f"{max(100 * statistics.median(r['line_retention'] for r in fixes(m)) for m in rest):.1f}",
        "rq1.others.no_larger.max": f"{max(100 * share_of(m, no_larger) for m in rest):.1f}",
        "rq1.others.within10.max": f"{max(100 * share_of(m, lambda r: near(r, 10)) for m in rest):.1f}",
        "rq1.others.same_ast.max": f"{max(100 * share_of(m, lambda r: near(r, 0)) for m in rest):.1f}",
        "rq1.others.problems70.max": max(sum(share_in_reach(g) >= 0.7 for g in by_problem_of(m)) for m in rest)})

    numbers.update({f"rq2.{key}.within_reach.rr": pct(within_reach(m, rq1_reach))
                    for key, m in (("zpdpatch", zpd), *((k, m) for k, _, m in others))})

    def ordered(*techniques):
        """Algorithm 1 with these techniques as its ordered generators: the first fix, else the last one's return."""
        by_id = [{r["example_id"]: r for r in m} for m in techniques]
        return [next((m[k] for m in by_id if m[k]["repaired"]), by_id[-1][k]) for k in sorted(by_id[0])]

    in_reach = lambda r: within_reach([r], rq1_reach) == 1
    tables["combined"] = [bars("baseline2", "y", [(key, m, in_reach) for key, _, m in others]),
                          bars("proposed", "y", [(key, ordered(zpd, m), in_reach) for key, _, m in others]),
                          f"\\draw[violet, densely dashed, thick] ({{rel axis cs:0,0}} |- {{axis cs:refactory,{pct(within_reach(zpd, rq1_reach))}}}) -- "
                          f"({{rel axis cs:1,0}} |- {{axis cs:refactory,{pct(within_reach(zpd, rq1_reach))}}});"]
    z = {r["example_id"]: r for r in fixes(zpd)}
    for key, _, m in others:
        o = {r["example_id"]: r for r in fixes(m)}
        joint = [k for k in z if k in o]
        both = ordered(zpd, m)
        numbers.update({
            f"rq2.{key}.joint": len(joint),
            f"rq2.{key}.joint.ted.smaller": more(statistics.mean(z[k]["ted_buggy_fixed"] for k in joint),
                                                 statistics.mean(o[k]["ted_buggy_fixed"] for k in joint)),
            f"rq2.{key}.joint.smaller.share": pct(sum(z[k]["ted_buggy_fixed"] < o[k]["ted_buggy_fixed"] for k in joint) / len(joint)),
            **{f"rq2.{key}.within{b}": pct(within_budget(m, b)) for b in (5, 10, 20)},
            f"rq2.{key}.combined.rr": pct(rr(both)),
            f"rq2.{key}.combined.within_reach.more": more(within_reach(both, rq1_reach), within_reach(m, rq1_reach)),
            f"rq2.{key}.combined.ted.mean": f"{mean(both, 'ted_buggy_fixed'):.1f}"})
    numbers.update({f"rq2.zpdpatch.within{b}": pct(within_budget(zpd, b)) for b in (5, 10, 20)})
    # A buggy program a technique does not repair: the existing techniques return the submission itself (no code kept),
    # ZPDPatch the candidate passing the most test cases, judged by the Mine predicates (progress_step).
    for _, _, m in others:
        assert all(r["generated_code"] is None for r in m if not r["repaired"])
    unrepaired = [r for r in zpd if not r["repaired"]]
    forward = [r for r in unrepaired if r["step_class"] == "forward"]
    numbers.update({
        "rq2.zpdpatch.unrepaired.forward.share": pct(len(forward) / len(unrepaired)),
        "rq2.zpdpatch.forward.pass_rate.gain.median": pct(statistics.median(r["fixed_pass_rate"] / r["buggy_pass_rate"] - 1 for r in forward if r["buggy_pass_rate"] > 0)),
        "rq2.zpdpatch.forward.within_reach.share": pct(sum(r["ted_buggy_returned"] is not None and r["ted_buggy_returned"] <= rq1_reach[(r["problem_id"], r["user_id"])] for r in forward) / len(forward))})
    span = lambda values: f"{min(values):.1f}--{max(values):.1f}"
    numbers["rq2.zpdpatch.rr.fewer.range"] = span([float(more(rr(zpd), rr(m))) for _, _, m in others])
    numbers["rq2.within_reach.share.more.range"] = span([float(more(share_in_reach(zpd), share_in_reach(m))) for _, _, m in others])
    for key in ("token_retention", "line_retention"):
        numbers[f"rq2.{key}.more.range"] = span([float(more(mean(zpd, key), mean(m, key))) for _, _, m in others])
    numbers["rq2.within5.more.range"] = span([float(more(within_budget(zpd, 5), within_budget(m, 5))) for _, _, m in others])
    numbers["rq2.lsgen.within20.more.range"] = span([float(more(within_budget(zpd, 20), within_budget(m, 20))) for k, _, m in others if k.startswith("lsgen")])
    numbers["rq2.combined.rr.more.range"] = span([float(more(rr(ordered(zpd, m)), rr(m))) for _, _, m in others])
    numbers["rq2.combined.within_reach.more.range"] = span([float(more(within_reach(ordered(zpd, m), rq1_reach), within_reach(m, rq1_reach))) for _, _, m in others])
    numbers["rq2.combined.ted.smaller.range"] = span([float(more(mean(ordered(zpd, m), "ted_buggy_fixed"), mean(m, "ted_buggy_fixed"))) for _, _, m in others])
    for key, m in (("lsgen", lsgen), ("lsgen_qwen", qwen)):  # ZPDPatch adds within-reach fixes Mentored does not make
        numbers[f"rq2.mentored_{key}.zpdpatch_first.within_reach.more"] = more(
            within_reach(ordered(zpd, mentored, m), rq1_reach), within_reach(ordered(mentored, m), rq1_reach))

    # Review responses on the RQ1 benchmark, from the stored returns only.
    # (a) On the buggy programs both repair: retention and the share within reach, ZPDPatch against each technique.
    zf = {r["example_id"]: r for r in fixes(zpd)}
    joint_more = {"token_retention": [], "line_retention": [], "reach": []}
    for key, _, m in others:
        of = {r["example_id"]: r for r in fixes(m)}
        joint = [k for k in zf if k in of]
        for name in ("token_retention", "line_retention"):
            value = more(statistics.mean(zf[k][name] for k in joint), statistics.mean(of[k][name] for k in joint))
            numbers[f"rq2.{key}.joint.{name}.more"] = value
            joint_more[name].append(float(value))
        a, b = (within_reach([x[k] for k in joint], rq1_reach) for x in (zf, of))
        numbers[f"rq2.{key}.joint.within_reach.{'more' if a >= b else 'fewer'}"] = more(a, b)
        if a >= b:
            joint_more["reach"].append(float(more(a, b)))
    for name, values in joint_more.items():
        numbers[f"rq2.joint.{name}.more.range"] = span(values)
    # Table V (RQ2): each technique on all buggy programs, and ZPDPatch against it on the buggy programs both repair.
    tables["rq2"] = [
        f"{name} & {pct(rr(m))} & {pct(rr(m) - within_reach(m, rq1_reach))} & {numbers[f'rq2.{key}.joint.ted.smaller']}"
        f" & {numbers[f'rq2.{key}.joint.token_retention.more']} & {numbers[f'rq2.{key}.joint.line_retention.more']} \\\\" for key, name, m in others] + [
        "\\midrule", f"\\textsc{{ZPDPatch}} & {pct(rr(zpd))} & {pct(rr(zpd) - within_reach(zpd, rq1_reach))} & -- & -- & -- \\\\"]
    # The programs cluster in 14 problems, so paired differences are judged by problem: the share of problems where
    # ZPDPatch keeps more tokens on the jointly repaired programs, and a bootstrap over problems of the within-reach
    # gain (points) of placing ZPDPatch first.
    problems = sorted({r["problem_id"] for r in zpd})
    rng = random.Random(2027)
    draws = [[rng.choice(problems) for _ in problems] for _ in range(10000)]
    kept_more, gains, lows, ups = [], [], [], []
    for _, _, m in others:
        of = {r["example_id"]: r for r in fixes(m)}
        joint = [k for k in zf if k in of]
        diff = {p: [zf[k]["token_retention"] - of[k]["token_retention"] for k in joint if zf[k]["problem_id"] == p] for p in problems}
        kept_more.append(100 * sum(statistics.mean(d) > 0 for d in diff.values() if d) / sum(bool(d) for d in diff.values()))
        alone = {r["example_id"]: within_reach([r], rq1_reach) for r in m}
        gain = {p: [0, 0] for p in problems}
        for r in ordered(zpd, m):
            gain[r["problem_id"]][0] += within_reach([r], rq1_reach) - alone[r["example_id"]]
            gain[r["problem_id"]][1] += 1
        gains.append(100 * sum(g for g, _ in gain.values()) / len(m))
        boot = sorted(100 * sum(gain[p][0] for p in d) / sum(gain[p][1] for p in d) for d in draws)
        lows.append(boot[249])
        ups.append(sum(g > 0 for g, _ in gain.values()))
    numbers["rq2.joint.token_retention.problems.share.range"] = span(kept_more)
    numbers["rq2.combined.within_reach.points.range"] = span(gains)
    numbers["rq2.combined.within_reach.ci.low.min"] = f"{min(lows):.1f}"
    numbers["rq2.combined.within_reach.problems.up.range"] = f"{min(ups)}--{max(ups)}"
    # (b) By quartile of the student's own step to acceptance: the share of each technique's repairs within reach.
    own_step = {r["example_id"]: r["step_ted"][-1] for r in steps}
    cuts = statistics.quantiles([own_step[r["example_id"]] for r in zpd], n=4)
    quartile = lambda r: sum(own_step[r["example_id"]] > c for c in cuts)
    def quartile_shares(m):
        return [within_reach([r for r in fixes(m) if quartile(r) == q], rq1_reach) * 100 for q in range(4)]
    numbers["rq2.zpdpatch.quartile.share.range"] = span(quartile_shares(zpd))
    numbers["rq2.zpdpatch.quartile.highest"] = all(
        z >= max(o) for z, o in zip(quartile_shares(zpd), zip(*(quartile_shares(m) for _, _, m in others))))
    numbers["rq2.others.quartile.share.max"] = f"{max(max(quartile_shares(m)) for _, _, m in others):.1f}"
    # (c) Buggy programs ZPDPatch repairs within reach that no existing technique repairs within reach.
    reached = lambda m: {r["example_id"] for r in m if within_reach([r], rq1_reach) == 1}
    union = set().union(*(reached(m) for _, _, m in others))
    numbers["rq2.zpdpatch.only_within_reach"] = len(reached(zpd) - union)
    numbers["rq2.zpdpatch.only_within_reach.share"] = pct(len(reached(zpd) - union) / len(zpd))
    numbers["rq2.others.union.within_reach.share"] = pct(len(union) / len(zpd))
    # (d) Stricter reach: the largest step before the buggy program, the median step, and the step to acceptance.
    variants = {}
    for r in steps:
        key, teds = tuple(r["example_id"].split(":")[:2]), [x for x in r["step_ted"] if x is not None]
        variants.setdefault("before", {})[key] = max(teds[:-1]) if len(teds) > 1 else None
        variants.setdefault("median", {})[key] = statistics.median(teds) if teds else None
        variants.setdefault("own", {})[key] = teds[-1] if teds else None
    for name, limits in variants.items():
        share = lambda m: within_reach(m, limits) * len(m) / len(fixes(m))
        numbers[f"rq2.reach_{name}.zpdpatch.share"] = pct(share(zpd))
        numbers[f"rq2.reach_{name}.others.share.max"] = f"{max(100 * share(m) for _, _, m in others):.1f}"
        numbers[f"rq2.reach_{name}.combined.more.range"] = span(
            [float(more(within_reach(ordered(zpd, m), limits), within_reach(m, limits))) for _, _, m in others])
    # (e) What ZPDPatch returns: repaired, a forward step, another program that passes more, or the submission.
    changed = [r for r in unrepaired if r["generated_code"] is not None]
    numbers.update({"rq2.zpdpatch.unrepaired.changed": len(changed),
                    "rq2.zpdpatch.unrepaired.forward": len(forward),
                    "rq2.zpdpatch.unrepaired.other_more": sum(r["step_class"] != "forward" and r["fixed_pass_rate"] > r["buggy_pass_rate"] for r in changed),
                    "rq2.zpdpatch.unrepaired.unchanged.share": pct((len(unrepaired) - len(changed)) / len(zpd)),
                    "rq1.step.pass_fewer.share": pct(sum(pb < pa for r in steps for pa, pb in r["step_pass_rates"]) / len(all_steps))})
    # (f) A step budget: the budgets at which ZPDPatch repairs the most, and another technique in front instead.
    numbers["rq2.zpdpatch.best_budgets"] = ",".join(str(b) for b in (1, 2, 3, 5, 7, 10, 15, 20, 30, 50)
                                                     if within_budget(zpd, b) > max(within_budget(m, b) for _, _, m in others))
    for key, _, m in others:
        numbers[f"rq2.{key}.front.within_reach.range"] = span(
            [100 * within_reach(ordered(f, m), rq1_reach) for k, _, f in others if k != key])
    numbers["rq2.zpdpatch.leads.upto5"] = all(within_budget(zpd, b) > max(within_budget(m, b) for m in rest) for b in range(1, 6))
    numbers["rq2.others.within20.range"] = span([100 * within_budget(m, 20) for m in rest])
    # (g) Beyond reach: the share of each technique's repairs above the student's demonstrated reach (the four
    # techniques of the Abstract and Introduction take LSGen with GPT-4o), and over all buggy programs, a plausible
    # patch beyond reach or the student's own accepted AST.
    four = [m for k, _, m in others if k != "lsgen_qwen"]
    beyond = lambda m: rr(m) - within_reach(m, rq1_reach)
    own_ast = lambda m: sum(near(r, 0) for r in fixes(m)) / len(m)
    numbers.update({
        "rq2.zpdpatch.exceed_reach.share": pct(1 - share_in_reach(zpd)),
        "rq2.four.exceed_reach.share.range": span([100 * (1 - share_in_reach(m)) for m in four]),
        "rq2.others.exceed_reach.share.range": span([100 * (1 - share_in_reach(m)) for m in rest]),
        "rq2.four.within_reach.share.more.range": span([float(more(share_in_reach(zpd), share_in_reach(m))) for m in four]),
        "rq2.zpdpatch.beyond_reach.all": pct(beyond(zpd)),
        "rq2.others.beyond_reach.all.range": span([100 * beyond(m) for m in rest]),
        "rq2.beyond_reach.all.fewer.range": span([float(more(beyond(zpd), beyond(m))) for m in rest]),
        "rq1.zpdpatch.own_accepted.all": pct(own_ast(zpd)),
        "rq1.others.own_accepted.all.range": span([100 * own_ast(m) for m in rest]),
        "rq1.own_accepted.all.more": more(own_ast(zpd), max(own_ast(m) for m in rest))})
    hard = lambda m: [r for r in m if score[r["problem_id"]] == 600]
    numbers["rq1.others.within_reach.share.hard.max"] = f"{max(100 * share_in_reach(hard(m)) for m in rest if fixes(hard(m))):.1f}"
    # Every program ZPDPatch returns other than the submission, a repair or a forward step, within reach.
    forward_in_reach = sum(r["ted_buggy_returned"] is not None and r["ted_buggy_returned"] <= rq1_reach[(r["problem_id"], r["user_id"])] for r in forward)
    numbers["rq2.zpdpatch.changed.within_reach.share"] = pct(
        (within_reach(zpd, rq1_reach) * len(zpd) + forward_in_reach) / (sum(bool(r["repaired"]) for r in zpd) + len(forward)))
    # Retention on the buggy programs both repair, within each quartile of the student's own step to acceptance.
    def joint_kept_more(m):
        of = {r["example_id"]: r for r in fixes(m)}
        joint = [[k for k in zf if k in of and quartile(zf[k]) == q] for q in range(4)]
        return [statistics.mean(zf[k]["token_retention"] for k in j) > statistics.mean(of[k]["token_retention"] for k in j) for j in joint]
    numbers["rq2.joint.token_retention.every_quartile"] = all(all(joint_kept_more(m)) for m in rest)
    # The running example (Figure 3(b)): the student's reach, the forward step of ZPDPatch, and the others' repairs.
    example = {r["example_id"]: r for r in zpd}["p02761:u367701763:S3"]
    numbers["rq2.example.reach"] = rq1_reach[(example["problem_id"], example["user_id"])]
    numbers["rq2.example.zpdpatch.ted"] = example["ted_buggy_returned"]
    example_teds = [r["ted_buggy_fixed"] for m in rest for r in m if r["example_id"] == example["example_id"] and r["repaired"]]
    numbers["rq2.example.others.ted.range"] = f"{min(example_teds)}--{max(example_teds)}"
    # The cascade against its first checkpoint alone (the one checkpoint of RQ3 and RQ4); the first checkpoint's
    # repairs are exactly the returns selected from it.
    first = [dict(r, repaired=bool(r["repaired"]) and r["selected_source"] == "Answer2027") for r in zpd]
    by_problem_pair = [([r for r in first if r["problem_id"] == p], [r for r in zpd if r["problem_id"] == p]) for p in problems]
    numbers.update({
        "rq3.rq1.one_checkpoint.fewer": more(rr(first), rr(zpd)),
        "rq3.rq1.one_checkpoint.within_reach.fewer": more(within_reach(first, rq1_reach), within_reach(zpd, rq1_reach)),
        "rq3.rq1.one_checkpoint.problems.fewer": sum(rr(a) < rr(b) and within_reach(a, rq1_reach) < within_reach(b, rq1_reach) for a, b in by_problem_pair)})

    # The same number of candidates from the untrained base model in front of each technique.
    base3 = rows("approaches/base-three-samples.jsonl")
    numbers["rq2.base3.rr"] = pct(rr(base3))
    numbers["rq2.base3.front.within_reach.more.range"] = span(
        [float(more(within_reach(ordered(base3, m), rq1_reach), within_reach(m, rq1_reach))) for _, _, m in others])
    tables["combined"].insert(1, bars("variant", "y", [(key, ordered(base3, m), in_reach) for key, _, m in others]))


    # Plausible patches on generated inputs (Threats): any failure, and a failure where the student's own accepted
    # program passes.
    diff = {k: rows(f"differential/{k}.jsonl") for k in ("zpdpatch", "refactory", "brafar", "mentored", "lsgen-qwen", "lsgen")}
    share = lambda items, key: 100 * sum(r[key] for r in items) / len(items)
    others_diff = [v for k, v in diff.items() if k != "zpdpatch"]
    only_own = lambda items: 100 * sum(r["patch_fails"] and not r["beyond_own"] for r in items) / sum(r["patch_fails"] for r in items)
    with open(os.path.join(OUT, "differential/students.json")) as f:
        students_diff = json.load(f)
    numbers.update({
        "threats.diff.zpdpatch.fails": f"{share(diff['zpdpatch'], 'patch_fails'):.1f}",
        "threats.diff.others.fails.range": span([share(v, "patch_fails") for v in others_diff]),
        "threats.diff.all.fails.range": span([share(v, "patch_fails") for v in diff.values()]),
        "threats.diff.zpdpatch.beyond_own": f"{share(diff['zpdpatch'], 'beyond_own'):.1f}",
        "threats.diff.others.beyond_own.range": span([share(v, "beyond_own") for v in others_diff]),
        # failing patches that fail no input the student's own accepted program passes
        "threats.diff.zpdpatch.only_own.share": f"{only_own(diff['zpdpatch']):.1f}",
        "threats.diff.others.only_own.share.range": span([only_own(v) for v in others_diff]),
        "threats.diff.students.fails": pct(students_diff["any"]["share"])})

    # Tables IV and V: target rules (RQ3).
    reach = reach_by_trajectory(rows("benchmark/canonical-student-steps.jsonl"))
    t = {split: {rule: rows(f"targets/{split}/{rule}.jsonl") for rule in ("answer", "progress")} for split in ("seen", "unseen", "java")}
    # Table VII: each rule trained on the same examples (Strict: strict-target-20261103-v1). Retention is the mean over
    # the buggy programs that every rule of the row repairs.
    cols = {s: {r: rows(f"targets/{s}/{r}.jsonl") for r in ("answer", "strict", "progress")} for s in ("seen", "unseen", "java")}
    reach_of = {"seen": reach, "unseen": reach}
    common = {c: set.intersection(*({r["example_id"] for r in m if r["repaired"]} for m in cols[c].values())) for c in cols}

    def retention(col, rule, key):
        by_id = {r["example_id"]: r for r in cols[col][rule]}
        return statistics.mean(by_id[k][key] for k in common[col])
    kept = lambda col, rule, key: pct(retention(col, rule, key))
    metrics = (lambda c, r: pct(rr(cols[c][r])),
               lambda c, r: pct(within_reach(cols[c][r], reach_of[c])),
               lambda c, r: kept(c, r, "token_retention"),
               lambda c, r: kept(c, r, "line_retention"))
    lines = []
    for c, label in (("seen", "Seen"), ("unseen", "Unseen")):
        values = [f(c, rule) if rule in cols[c] else "" for f in metrics for rule in ("answer", "strict", "progress")]
        lines.append(f"{label} & {' & '.join(values)} \\\\")
    tables["targets"] = lines
    # Table IX (RQ4): the same target-rule comparison on Java with students held out.
    tables["javatargets"] = [f"{label} & {' & '.join(f(r) if r in cols['java'] else '' for r in ('answer', 'strict', 'progress'))} \\\\"
                             for label, f in (("RR", lambda r: pct(rr(cols["java"][r]))),
                                              ("Tokens", lambda r: kept("java", r, "token_retention")),
                                              ("Lines", lambda r: kept("java", r, "line_retention")))]
    # Table VIII (RQ3): Progress trained on the student's own targets and on another student's with the same execution
    # outcomes and token difference (cross-user target control, current-only prompts); TED on the programs both repair.
    tables["targetsource"] = []
    for s, label in (("seen", "Seen"), ("unseen", "Unseen")):
        own, other = rows(f"targets/{s}/progress-same-user.jsonl"), rows(f"targets/{s}/progress-cross-user.jsonl")
        fo, ft = ({r["example_id"]: r for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None} for m in (own, other))
        joint = [k for k in fo if k in ft]
        ted = [statistics.mean(f[k]["ted_buggy_fixed"] for k in joint) for f in (fo, ft)]
        tables["targetsource"].append(f"{label} & {pct(rr(own))} & {pct(rr(other))} & {pct(within_reach(own, reach))}"
                                      f" & {pct(within_reach(other, reach))} & {ted[0]:.1f} & {ted[1]:.1f} \\\\")
        numbers.update({f"rq3.source.{s}.rr.more": more(rr(other), rr(own)),
                        f"rq3.source.{s}.within_reach.fewer": more(within_reach(other, reach), within_reach(own, reach)),
                        f"rq3.source.{s}.ted.larger": more(ted[1], ted[0])})
    for s in cols:
        numbers[f"rq3.{s}.joint"] = len(common[s])
        for rule in ("strict", "progress"):
            key = "" if rule == "progress" else "strict."
            numbers[f"rq3.{s}.{key}tokens.more"] = more(retention(s, rule, "token_retention"), retention(s, "answer", "token_retention"))
            numbers[f"rq3.{s}.{key}lines.more"] = more(retention(s, rule, "line_retention"), retention(s, "answer", "line_retention"))
            numbers[f"rq3.{s}.{key}rr.fewer"] = more(rr(cols[s][rule]), rr(cols[s]["answer"]))
            if s in reach_of:
                numbers[f"rq3.{s}.{key}within_reach.change"] = f"{100 * (within_reach(cols[s][rule], reach) / within_reach(cols[s]['answer'], reach) - 1):+.1f}"
        numbers[f"rq3.{s}.strict.rr.more_than_progress"] = more(rr(cols[s]["strict"]), rr(cols[s]["progress"]))
    ja = {r["example_id"]: r for r in t["java"]["answer"]}
    per_exercise = defaultdict(lambda: [0, 0])
    for r in t["java"]["answer"]:
        per_exercise[r["problem_id"]][0] += bool(r["repaired"])
    for r in t["java"]["progress"]:
        per_exercise[r["problem_id"]][1] += bool(r["repaired"])
    ex = [sum(a > p for a, p in per_exercise.values()), sum(a == p for a, p in per_exercise.values()), sum(a < p for a, p in per_exercise.values())]
    diffs = [r["token_retention"] - ja[r["example_id"]]["token_retention"] for r in t["java"]["progress"] if r["repaired"] and ja[r["example_id"]]["repaired"]]
    tr = [sum(d < 0 for d in diffs), sum(d == 0 for d in diffs), sum(d > 0 for d in diffs)]
    numbers["rq3.java.extra_repairs"] = sum(a - p for a, p in per_exercise.values() if a > p)
    numbers["rq3.java.max_extra_one_exercise"] = max(a - p for a, p in per_exercise.values())

    # Table III: ablation (RQ3); each variant against ZPDPatch under the same inference conditions.
    pairs = (("Training\\(^\\dagger\\)", "no-training", "sampled"),        # rows: each choice without and with it
             ("Cascade", "one-checkpoint", "zpdpatch"),
             ("Distinct checkpoints\\(^\\dagger\\)", "same-checkpoint", "distinct-checkpoints"),
             ("Current-only prompt", "history", "zpdpatch"))
    # Figure (RQ3): one bar series per split and side, over the four choices.
    rate = {}
    for (label, variant, reference), x in zip(pairs, ("training", "cascade", "distinct", "current")):
        for s in ("seen", "unseen"):
            v, z = rr(rows(f"ablation/{s}/{variant}.jsonl")), rr(rows(f"ablation/{s}/{reference}.jsonl"))
            rate[(s, 0, x)], rate[(s, 1, x)] = v, z
            numbers[f"rq3.{variant}.{s}.fewer"] = more(v, z)
    # Train-dagger within reach and the student's own accepted AST, with the TED of the sampled returns (sampled-ted).
    for s in ("seen", "unseen"):
        ted = {(r["variant"], r["example_id"]): r for r in rows(f"ablation/{s}/sampled-ted.jsonl")}
        filled = lambda v: [dict(r, **{k: ted[(v, r["example_id"])][k] for k in ("ted_buggy_fixed", "ted_fixed_oracle")})
                            if r["repaired"] else r for r in rows(f"ablation/{s}/{v}.jsonl")]
        base, one = filled("no-training"), filled("sampled")
        own_ast = lambda m: sum(bool(r["repaired"]) and r["ted_fixed_oracle"] == 0 for r in m)
        numbers[f"rq3.no-training.{s}.within_reach.fewer"] = more(within_reach(base, reach), within_reach(one, reach))
        numbers[f"rq3.no-training.{s}.own_accepted.fewer"] = more(own_ast(base), own_ast(one))
    # Figure 6 (RQ3): how many fewer buggy programs each variant repairs; Unseen is plotted first so Seen sits on top.
    drop = {"training": "no-training", "reach": "no-training", "cascade": "one-checkpoint", "distinct": "same-checkpoint", "current": "history"}
    fewer = lambda y, s: numbers[f"rq3.{drop[y]}.{s}.{'within_reach.' if y == 'reach' else ''}fewer"]
    tables["ablation"] = [f"\\addplot[{style}] coordinates {{{' '.join(f'({fewer(y, s)},{y})' for y in drop)}}};"
                          for s, style in (("unseen", "fill=red!25, draw=red!60!black"), ("seen", "fill=red!70!black, draw=red!60!black"))]

    # Table VI and Figure 6: generality (RQ4).
    settings = (("1.5B model", "scale-1.5b/seen", "scale-1.5b/unseen"), ("Java", "java-students", "java-exercises"))
    # Figure (RQ4): one checkpoint and the cascade by setting; within reach for the 1.5B model (Java has no student steps).
    gen = {}
    for label, seen, unseen in settings:
        for key, path in (("seen", seen), ("unseen", unseen)):
            one, port = rr(rows(f"generality/{path}/one-checkpoint.jsonl")), rr(rows(f"generality/{path}/zpdpatch.jsonl"))
            gen[(label, key)] = (one, port)
            numbers[f"rq4.{path}.more"] = more(port, one)
    for s in ("seen", "unseen"):
        one, port = (rows(f"generality/scale-1.5b/{s}/{n}.jsonl") for n in ("one-checkpoint", "zpdpatch"))
        gen[("reach", s)] = (within_reach(one, reach), within_reach(port, reach))
        numbers[f"rq4.scale-1.5b/{s}.within_reach.more"] = more(gen[("reach", s)][1], gen[("reach", s)][0])
    # Figure 7 (RQ4): (a) the 1.5B model, RR and within reach; (b) Java with students or problems held out.
    one_cascade = (("fill=teal!20, draw=teal!60!black", 0), ("fill=teal!75!black, draw=teal!60!black", 1))
    tables["generality15"] = [f"\\addplot[{style}] coordinates {{{' '.join(f'({x},{100 * gen[(g, s)][i]:.1f})' for g, s, x in (('1.5B model', 'seen', 'rrseen'), ('1.5B model', 'unseen', 'rrunseen'), ('reach', 'seen', 'reachseen'), ('reach', 'unseen', 'reachunseen')))}}};"
                              for style, i in one_cascade]
    tables["generalityjava"] = [f"\\addplot[{style}] coordinates {{{' '.join(f'({x},{100 * gen[('Java', s)][i]:.1f})' for s, x in (('seen', 'students'), ('unseen', 'problems')))}}};"
                                for style, i in one_cascade]

    in_text(numbers, mentored, lsgen, steps, t, reach)
    with open(os.path.join(PAPER, "output", "tables.tex"), "w") as f:
        for name, body in tables.items():
            f.write(f"% rows:{name}\n" + "".join(line + "\n" for line in body))
    with open(os.path.join(PAPER, "output", "numbers.txt"), "w") as f:
        f.writelines(f"{k} = {v}\n" for k, v in numbers.items())
    print({k: len(v) for k, v in tables.items()}, len(numbers), "numbers")


if __name__ == "__main__":
    main()
