"""Student-disjoint matched-target replication; no Python AST metric for Java."""
import argparse
import json
from pathlib import Path
import re
import numpy as np

from scripts.analyze_fse2027_robustness import read_jsonl, paired_suite_rows, summarize_method
from scripts.analyze_patch_locality import retained_fraction
from scripts.compose_answer_seed_control import compose


def preservation_summary(rows):
    report = {'joint_repairs': len(rows), 'estimand': 'mean paired retention difference on joint repairs; not a learning outcome', 'metrics': {}}
    for metric in ('lexical_retention', 'line_retention'):
        intervals = {}
        for cluster in ('problem_id', 'user_id'):
            groups = {}
            for row in rows:
                groups.setdefault(str(row[cluster]), []).append(row[metric])
            if not groups:
                intervals[cluster] = {'clusters': 0, 'ci95': None}
                continue
            sums = np.array([sum(v) for v in groups.values()])
            sizes = np.array([len(v) for v in groups.values()])
            rng = np.random.default_rng(9152)
            draws = rng.integers(len(groups), size=(10000, len(groups)))
            values = sums[draws].sum(axis=1) / sizes[draws].sum(axis=1)
            intervals[cluster] = {'clusters': len(groups), 'ci95': np.quantile(values, [.025, .975]).tolist()}
        report['metrics'][metric] = {'mean_difference': float(np.mean([r[metric] for r in rows])) if rows else None, 'cluster_intervals': intervals}
    return report


def preflight(root):
    users = {}
    counts = {}
    for split in ("train", "valid"):
        left = read_jsonl(root / f"{split}-progress.jsonl")
        right = read_jsonl(root / f"{split}-answer.jsonl")
        assert left and len(left) == len(right)
        for a, b in zip(left, right, strict=True):
            assert all(a[k] == b[k] for k in ("example_id", "problem_id", "user_id", "history"))
            assert len(a["history"]) == 1
            assert a["target_submission_id"] != b["target_submission_id"]
        users[split] = {r["user_id"] for r in left}
        counts[split] = len(left)
    test = read_jsonl(root / "test.jsonl")
    assert test and all(len(r["history"]) == 1 for r in test)
    users["test"] = {r["user_id"] for r in test}
    assert not (users["train"] & users["valid"] or users["train"] & users["test"] or users["valid"] & users["test"])
    return {"counts": {**counts, "test": len(test)}, "users": {k: len(v) for k, v in users.items()}, "student_overlap": 0, "exact_source_pairs": True}


def analyze(root, dataset):
    source = {r["example_id"]: r for r in read_jsonl(dataset)}
    methods = {}
    for relation in ("progress", "answer"):
        stages = []
        candidates = {}
        for seed in (2027, 2028, 2029):
            name = f"{relation}-{seed}"
            rows = read_jsonl(root / f"{name}.evaluation.jsonl")
            codes = {r["example_id"]: r["generated_code"] for r in read_jsonl(root / f"{name}.generations.jsonl")}
            for row in rows:
                row["generated_code"] = codes[row["example_id"]]
            stages.append((name, rows))
            candidates[name] = {r["example_id"]: r for r in rows}
        rows = compose(list(source.values()), stages)
        for row in rows:
            key = row["example_id"]
            selected = row["selected_source"]
            row["generated_code"] = source[key]["history"][-1]["code"] if selected == "current-fallback" else candidates[selected][key]["generated_code"]
        methods[relation] = rows
    comparison = paired_suite_rows(methods["progress"], methods["answer"], left_label="Progress3", right_label="Answer3", samples=10000, seed=9150)
    # Re-label clusters for a second, otherwise identical student bootstrap.
    student = {m: [{**r, "problem_id": str(r["user_id"])} for r in rows] for m, rows in methods.items()}
    student_comparison = paired_suite_rows(student["progress"], student["answer"], left_label="Progress3", right_label="Answer3", samples=10000, seed=9151)
    a = {r["example_id"]: r for r in methods["answer"]}
    preservation = []
    # Explicit language-neutral lexical segmentation; strings/comments are not parsed as Python.
    tokens = lambda code: re.findall(r"\w+|[^\w\s]", code)
    for p in methods["progress"]:
        key = p["example_id"]
        if not (p["repaired"] and a[key]["repaired"]):
            continue
        code = source[key]["history"][-1]["code"]
        line = lambda s: [x.strip() for x in s.splitlines() if x.strip()]
        preservation.append({"example_id": key, "problem_id": p["problem_id"], "user_id": p["user_id"], **{name: retained_fraction(fn(code), fn(p["generated_code"])) - retained_fraction(fn(code), fn(a[key]["generated_code"])) for name, fn in (("lexical_retention", tokens), ("line_retention", line))}})
    return {"dataset": "student-disjoint CodeWorkout", "methods": {m: summarize_method(rows) for m, rows in methods.items()}, "exercise_cluster_comparison": comparison, "student_cluster_comparison": student_comparison, "joint_preservation_rows": preservation, "joint_preservation": preservation_summary(preservation), "per_exercise": {m: {str(problem): {"n": sum(r["problem_id"] == problem for r in rows), "repairs": sum(r["problem_id"] == problem and r["repaired"] for r in rows)} for problem in {r["problem_id"] for r in rows}} for m, rows in methods.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = preflight(args.preflight) if args.preflight else analyze(args.root, args.dataset)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
