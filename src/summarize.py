"""Compute the paper's tables, figure data, and in-text numbers from ../output/ (the reported per-input rows).
Writes output/tables.tex ('% rows:<name>' sections for fill_tables.py) and output/numbers.txt.
Usage: python3 paper/src/summarize.py"""
import json
import os
import random
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


def joint_retention(a, b):
    a = {r["example_id"]: r for r in a}
    joint = [k for k, r in a.items() for _ in [0] if r["repaired"]]
    b = {r["example_id"]: r for r in b}
    joint = [k for k in joint if b[k]["repaired"]]
    mean = lambda m, key: statistics.mean(m[k][key] for k in joint)
    return joint, {side: {key: mean(m, key) for key in ("token_retention", "line_retention")} for side, m in (("a", a), ("b", b))}


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

    # RQ4: the portfolio at every position of a trajectory.
    for split in ("seen", "unseen"):
        port, one = (rows(f"generality/prefix/{split}/{n}.jsonl") for n in ("zpdpatch", "one-checkpoint"))
        by = lambda items, ph: rr([r for r in items if r["trajectory_phase"] == ph])
        gains = [float(more(by(port, ph), by(one, ph))) for ph in ("early", "middle", "last")]
        rates = [100 * by(port, ph) for ph in ("early", "middle", "last")]
        numbers[f"rq4.prefix.{split}.more.range"] = f"{min(gains):.1f}--{max(gains):.1f}"
        numbers[f"rq4.prefix.{split}.rr.range"] = f"{min(rates):.1f}--{max(rates):.1f}"

    # Threats to Validity.
    port = rows("ablation/seen/zpdpatch.jsonl")
    rq1_fixed = [r for r in rows("approaches/zpdpatch.jsonl") if r["repaired"]]
    numbers["threats.rq1.training_copy"] = sum(r["training_copy"] for r in rq1_fixed)
    numbers["threats.rq1.repairs"] = len(rq1_fixed)
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
    grid = (1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 1000)
    curve = lambda style, share: f"\\addplot[{style}] coordinates {{" + " ".join(f"({b},{100 * share(b):.1f})" for b in grid) + "};"
    tables["reach"] = [curve("referenceline", share)] + [curve(style, lambda b, m=m: within_budget(m, b))
                                                         for style, m in (("mentoredline", mentored), ("qwenline", qwen), ("gptline", lsgen))]
    fixed_ted = lambda m: statistics.mean(r["ted_buggy_fixed"] for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None)
    numbers.update({"lim.mentored.returns_submission.share": pct(1 - rr(mentored)), "lim.lsgen.returns_submission.share": pct(1 - rr(lsgen)),
                    "lim.lsgen_qwen.returns_submission.share": pct(1 - rr(qwen)), "rq1.lsgen_qwen.rr": pct(rr(qwen)),
                    "rq1.lsgen_qwen.ted_vs_step.more": more(fixed_ted(qwen), statistics.mean(all_steps)),
                    "lim.within20.fewer.range": "--".join(more(within_budget(m, 20), rr(m)) for m in (mentored, lsgen)) + " / qwen " + more(within_budget(qwen, 20), rr(qwen)),
                    "lim.within20.rr.range": f"{min(100 * within_budget(m, 20) for m in (mentored, qwen, lsgen)):.1f}--{max(100 * within_budget(m, 20) for m in (mentored, qwen, lsgen)):.1f}"})
    numbers.update({"rq1.steps": len(all_steps), "rq1.step.median": num(statistics.median(all_steps)),
                    "rq1.step.mean": f"{statistics.mean(all_steps):.1f}", "rq1.reach.median": num(statistics.median(all_reach)),
                    "rq1.mentored.within20.fewer": more(within_budget(mentored, 20), rr(mentored)),
                    "rq1.lsgen.within20.fewer": more(within_budget(lsgen, 20), rr(lsgen))})

    # Section II-B figure: (a) pass rate and wrong-answer share at the first, middle, and last failing submissions and at
    # acceptance, over every trajectory; (b) the students' steps by class.
    def states(r):  # the distinct submissions of a trajectory, from its steps: (verdict, pass rate)
        return [(r["step_verdicts"][0][0], r["step_pass_rates"][0][0])] + [(b, pb) for (_, b), (_, pb) in zip(r["step_verdicts"], r["step_pass_rates"])]
    trajectories_states = [states(r) for r in steps]
    middles = [t[1:-2] for t in trajectories_states if len(t) > 3]
    points = (("first", [t[0][1] for t in trajectories_states], [t[0][0] == "WA" for t in trajectories_states]),
              ("middle", [statistics.mean(p for _, p in m) for m in middles], [statistics.mean(v == "WA" for v, _ in m) for m in middles]),
              ("last", [t[-2][1] for t in trajectories_states], [t[-2][0] == "WA" for t in trajectories_states]),
              ("accepted", [t[-1][1] for t in trajectories_states], [t[-1][0] == "WA" for t in trajectories_states]))
    tables["climb"] = [
        "\\addplot[referenceline, mark=*, mark size=1.3pt] coordinates {" + " ".join(f"({i},{100 * statistics.mean(p):.1f})" for i, (_, p, _) in enumerate(points)) + "};",
        "\\addplot[verdictline, dashed, mark=square*, mark size=1.2pt] coordinates {" + " ".join(f"({i},{100 * statistics.mean(w):.1f})" for i, (_, _, w) in enumerate(points)) + "};"]
    numbers.update({"lim.trajectories": len(trajectories_states), "lim.trajectories.with_middle": len(middles),
                    **{f"lim.{name}.pass_rate": f"{100 * statistics.mean(p):.1f}" for name, p, _ in points},
                    **{f"lim.{name}.wa.share": f"{100 * statistics.mean(w):.1f}" for name, _, w in points},
                    "lim.last_passes_more_than_first.share": pct(sum(t[-2][1] > t[0][1] for t in trajectories_states) / len(trajectories_states)),
                    "lim.last_passes_as_many_as_first.share": pct(sum(t[-2][1] == t[0][1] for t in trajectories_states) / len(trajectories_states))})
    classes = [c for r in steps for c in r["step_class"]]
    tables["stepclasses"] = [f"\\addplot[{style}] coordinates {{({100 * classes.count(c) / len(classes):.1f},0)}};"
                             for c, style in (("AC", "toacceptance"), ("forward", "forwardstep"), ("sideways", "sidewaysstep"), ("regress", "regressstep"))]
    numbers.update({**{f"lim.steps.{c}.share": pct(classes.count(c) / len(classes)) for c in ("AC", "forward", "sideways", "regress")},
                    "lim.trajectories.with_forward.share": pct(sum("forward" in r["step_class"] for r in steps) / len(steps)),
                    "lim.forward.verdict_kept.share": pct(sum(a == b for r in steps for (a, b), c in zip(r["step_verdicts"], r["step_class"]) if c == "forward")
                                                          / classes.count("forward")),
                    "lim.regress.verdict_kept.share": pct(sum(a == b for r in steps for (a, b), c in zip(r["step_verdicts"], r["step_class"]) if c == "regress")
                                                          / classes.count("regress"))})

    # RQ1 figure: the patches of ZPDPatch against the students' own steps.
    zpd, qwen = rows("approaches/zpdpatch.jsonl"), rows("approaches/lsgen-qwen.jsonl")
    rq1_reach = reach_by_trajectory(steps)
    fixes = lambda m: [r for r in m if r["repaired"] and r["ted_buggy_fixed"] is not None]
    share_in_reach = lambda m: within_reach(m, rq1_reach) * len(m) / len(fixes(m))
    patch = [r["ted_buggy_fixed"] for r in fixes(zpd)]
    cdf = lambda xs: " ".join(f"({x},{100 * sum(v <= x for v in xs) / len(xs):.1f})"
                              for x in (1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 1000))
    tables["patchsize"] = [f"\\addplot[referenceline] coordinates {{{cdf(all_steps)}}};",
                           f"\\addplot[proposedline] coordinates {{{cdf(patch)}}};"]
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
    tables["rq1"] = [
        "\\multirow{2}{*}{Within reach} & Fixed (\\%) & " + cells([pct(share_in_reach(g)) for g in groups]),
        " & Problems ($\\geq$70\\%) & " + cells([f"{sum(share_in_reach(by_problem[p]) >= 0.7 for p in problems(g))}/{len(problems(g))}" for g in groups]),
        "\\midrule",
        "\\multirow{2}{*}{Med.\\ tokens kept (\\%)} & Patch & " + cells([pct(statistics.median(r["token_retention"] for r in fixes(g))) for g in groups]),
        " & Student step & " + cells([pct(statistics.median(x for r in g for x in r["step_token_retention"])) for g in group_steps]),
        "\\midrule",
        "\\multirow{2}{*}{Med.\\ lines kept (\\%)} & Patch & " + cells([pct(statistics.median(r["line_retention"] for r in fixes(g))) for g in groups]),
        " & Student step & " + cells([pct(statistics.median(x for r in g for x in r["step_line_retention"])) for g in group_steps]),
        "\\midrule",
        "\\multirow{3}{*}{Student's fix (\\%)} & No larger & " + cells(against_fix(lambda r: own_fix[r["example_id"]] is not None and r["ted_buggy_fixed"] <= own_fix[r["example_id"]])),
        " & Within 10 & " + cells(against_fix(lambda r: near(r, 10))),
        " & Same AST & " + cells(against_fix(lambda r: near(r, 0))),
    ]

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
    others = (("mentored", "\\textsc{Mentored}", mentored), ("lsgen_qwen", "\\textsc{LSGen}\\textsubscript{Qwen}", qwen),
              ("lsgen", "\\textsc{LSGen}\\textsubscript{GPT}", lsgen))
    mean = lambda m, key: statistics.mean(r[key] for r in fixes(m))
    tables["comparison"] = [
        f"{label} & {pct(rr(m))} & {pct(share_in_reach(m))} & {pct(within_reach(m, rq1_reach))} & {mean(m, 'ted_buggy_fixed'):.1f} & "
        f"{pct(mean(m, 'token_retention'))} & {pct(mean(m, 'line_retention'))} \\\\"
        for _, label, m in (("zpdpatch", "\\textsc{ZPDPatch}", zpd), *others)]

    numbers.update({f"rq2.{key}.within_reach.rr": pct(within_reach(m, rq1_reach))
                    for key, m in (("zpdpatch", zpd), *((k, m) for k, _, m in others))})

    def ordered(*techniques):
        """Algorithm 1 with these techniques as its ordered generators: the first fix, else the last one's return."""
        by_id = [{r["example_id"]: r for r in m} for m in techniques]
        return [next((m[k] for m in by_id if m[k]["repaired"]), by_id[-1][k]) for k in sorted(by_id[0])]

    in_reach = lambda r: within_reach([r], rq1_reach) == 1
    tables["combined"] = [bars("variant", "y", [(key, m, in_reach) for key, _, m in others]),
                          bars("proposed", "y", [(key, ordered(zpd, m), in_reach) for key, _, m in others])]
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
    numbers["rq2.lsgen.within20.more.range"] = span([float(more(within_budget(zpd, 20), within_budget(m, 20))) for _, _, m in others[1:]])
    numbers["rq2.combined.rr.more.range"] = span([float(more(rr(ordered(zpd, m)), rr(m))) for _, _, m in others])
    numbers["rq2.combined.within_reach.more.range"] = span([float(more(within_reach(ordered(zpd, m), rq1_reach), within_reach(m, rq1_reach))) for _, _, m in others])
    numbers["rq2.combined.ted.smaller.range"] = span([float(more(mean(ordered(zpd, m), "ted_buggy_fixed"), mean(m, "ted_buggy_fixed"))) for _, _, m in others])
    for key, m in (("lsgen", lsgen), ("lsgen_qwen", qwen)):  # ZPDPatch adds within-reach fixes Mentored does not make
        numbers[f"rq2.mentored_{key}.zpdpatch_first.within_reach.more"] = more(
            within_reach(ordered(zpd, mentored, m), rq1_reach), within_reach(ordered(mentored, m), rq1_reach))

    # Tables IV and V: target rules (RQ3).
    reach = reach_by_trajectory(rows("benchmark/canonical-student-steps.jsonl"))
    t = {split: {rule: rows(f"targets/{split}/{rule}.jsonl") for rule in ("answer", "progress")} for split in ("seen", "unseen", "java")}
    ret = {split: joint_retention(t[split]["answer"], t[split]["progress"]) for split in t}
    cell = lambda split, rule, f: f(split, rule)
    lines = []
    for label, f, java in (
        ("RR (\\%)", lambda s, r: pct(rr(t[s][r])), True),
        ("Within-reach RR (\\%)", lambda s, r: pct(within_reach(t[s][r], reach)), False),
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
        numbers[f"rq3.{s}.joint"] = len(ret[s][0])
        numbers[f"rq3.{s}.tokens.more"] = more(b["token_retention"], a["token_retention"])
        numbers[f"rq3.{s}.lines.more"] = more(b["line_retention"], a["line_retention"])
        numbers[f"rq3.{s}.rr.fewer"] = more(rr(t[s]["progress"]), rr(t[s]["answer"]))
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
    pairs = (("\\textsc{ZPDPatch}-Train\\(^\\dagger\\)", "no-training", "sampled"),
             ("\\textsc{ZPDPatch}-Portfolio", "one-checkpoint", "zpdpatch"),
             ("\\textsc{ZPDPatch}-Distinct\\(^\\dagger\\)", "same-checkpoint", "distinct-checkpoints"),
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

    in_text(numbers, mentored, lsgen, steps, t, reach)
    with open(os.path.join(PAPER, "output", "tables.tex"), "w") as f:
        for name, body in tables.items():
            f.write(f"% rows:{name}\n" + "".join(line + "\n" for line in body))
    with open(os.path.join(PAPER, "output", "numbers.txt"), "w") as f:
        f.writelines(f"{k} = {v}\n" for k, v in numbers.items())
    print({k: len(v) for k, v in tables.items()}, len(numbers), "numbers")


if __name__ == "__main__":
    main()
