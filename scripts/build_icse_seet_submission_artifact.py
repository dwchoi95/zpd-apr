"""Export a local anonymous, analysis-only supplement from retained outcomes.

Refuses to overwrite an output directory/archive. Never executes experiment
runners or changes source datasets, protocols, checkpoints, or result files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path

from scripts.analyze_patch_locality import locality, resolve_generated_codes
from scripts.compose_answer_seed_control import compose

ROOT = Path(__file__).resolve().parents[1]
RUN = Path("outputs/split-90-10/canonical-v5")
ANALYSIS = RUN / "analysis"
FIELDS = ("repaired", "improved", "fixed_pass_rate", "ted_buggy_fixed", "ted_fixed_oracle")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitize(value):
    """Aggregate-only exports: remove source/identity payloads and private paths."""
    if isinstance(value, dict):
        excluded = {"code", "generated_code", "current_source", "selected_source",
                    "prompt", "history", "joint_preservation_rows"}
        return {k: sanitize(v) for k, v in value.items() if k not in excluded
                and not (k in ("user_id", "example_id") and not isinstance(v, dict))}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"/(?:home|Users)/[^/\s]+/(?:VSCode/)?zpd-apr/?", "./", value)
        value = re.sub(r"/(?:home|Users)/[^\s]+", "[private-path]", value)
        value = re.sub(r"\bu\d{6,}\b", "[user]", value)
    return value


def anonymize(left, right, retention):
    if len({r["example_id"] for r in left}) != len(left) or len({r["example_id"] for r in right}) != len(right):
        raise ValueError("duplicate evaluation IDs")
    if {r["example_id"] for r in left} != {r["example_id"] for r in right}:
        raise ValueError("unmatched evaluation IDs")
    maps = {key: {value: f"{key}-{i:05d}" for i, value in enumerate(sorted({str(r[key]) for r in left}))}
            for key in ("example_id", "problem_id", "user_id")}
    def one(row, metrics):
        return {**{k: maps[k][str(row[k])] for k in maps if k in row},
                **{k: row.get(k) for k in metrics}}
    # Order-preserving aliases retain sorted-cluster and sorted-example RNG semantics.
    return ([one(r, FIELDS) for r in left], [one(r, FIELDS) for r in right],
            [one(r, tuple(k for k in r if k.endswith("retention"))) for r in retention])


def build(output):
    output = output.resolve()
    archive = output.with_suffix(".zip")
    if output.exists() or archive.exists():
        raise FileExistsError("use a fresh output path; previous exports are preserved")
    output.mkdir(parents=True)
    sources = {}
    def read(path, jsonl=False):
        path = ROOT / path
        sources[str(path.relative_to(ROOT))] = digest(path)
        text = path.read_text()
        return [json.loads(s) for s in text.splitlines() if s.strip()] if jsonl else json.loads(text)
    def emit(path, payload):
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(sanitize(payload), indent=2, ensure_ascii=False) + "\n")
    def emit_pairs(path, payload):
        # Explicitly whitelisted metric fields and local aliases, not generic aggregate sanitization.
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2) + "\n")
    def copy(source, target):
        sources[str(source)] = digest(ROOT / source)
        dest = output / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / source, dest)

    summary = read(ANALYSIS / "fse2027-paired-target-control-corrected.json")
    for split, seed in (("seen", 8100), ("unseen", 8200)):
        base = RUN / "eval/paired-target-control-corrected" / split
        dataset = read(RUN / "datasets/paired-target-control" / f"{split}-test.jsonl", True)
        source = {r["example_id"]: r["history"][-1]["code"] for r in dataset}
        evaluations = {m: {r["example_id"]: r for r in read(base / f"{m}3.evaluation.jsonl", True)}
                       for m in ("progress", "answer")}
        candidates = {f"{m}-{s}": {r["example_id"]: r for r in read(base / f"{m}-{s}.evaluation.jsonl", True)}
                      for m in evaluations for s in (2027, 2028, 2029)}
        resolve_generated_codes(evaluations, candidates, source)
        retention = []
        for key in sorted(source):
            p, a = evaluations["progress"][key], evaluations["answer"][key]
            if p["repaired"] and a["repaired"]:
                lp, la = locality(source[key], p["generated_code"]), locality(source[key], a["generated_code"])
                retention.append({"example_id": key, "problem_id": p["problem_id"], "user_id": p["user_id"],
                                  **{k: lp[k] - la[k] for k in lp}})
        left, right, retention = anonymize(list(evaluations["progress"].values()), list(evaluations["answer"].values()), retention)
        emit_pairs(f"pairs/python-{split}.json", dict(examples=len(left), progress=left, answer=right,
                    retention=retention, bootstrap_seeds={"problem_id": seed}))
        stored = summary["splits"][split]
        local = stored["source_preservation_on_joint_repairs"]
        emit(f"expected/python-{split}.json", {"problem_id": stored["unrestricted"]["progress_minus_answer"],
             "joint_repairs": local["joint_repairs"],
             "retention_means": {k: v["left_minus_right"] for k, v in local["metrics"].items()}})

    java = read(ANALYSIS / "fse2027-paired-java-control.json")
    dataset = read(RUN / "datasets/paired-java-control/test.jsonl", True)
    methods = {}
    for method in ("progress", "answer"):
        stages = [(f"{method}-{seed}", read(RUN / "eval/paired-java-control" / f"{method}-{seed}.evaluation.jsonl", True))
                  for seed in (2027, 2028, 2029)]
        methods[method] = compose(dataset, stages)
    left, right, retention = anonymize(methods["progress"], methods["answer"], java["joint_preservation_rows"])
    emit_pairs("pairs/java.json", dict(examples=len(left), progress=left, answer=right,
                retention=retention, bootstrap_seeds={"problem_id": 9150, "user_id": 9151}))
    emit("expected/java.json", {"problem_id": java["exercise_cluster_comparison"],
         "user_id": java["student_cluster_comparison"], "joint_repairs": len(retention),
         "retention_means": {k: v["mean_difference"] for k, v in java["joint_preservation"]["metrics"].items()}})
    robustness = read(ANALYSIS / "fse2027-robustness.json")
    emit("evidence/history-retraining.json", {k: v for k, v in robustness["comparisons"].items() if k.startswith("rq2_")})
    emit("evidence/result-bridge.json", read(ANALYSIS / "fse2027-result-bridge.json"))
    emit("evidence/deadline-results.json", read(Path("analysis_protocols/zpd-deadline-results-20261021.json")))
    for name in ("fse2027-peer-distributions.json", "fse2027-prompt-distribution-control.json"):
        emit("evidence/" + name, read(ANALYSIS / name))
    preflight = read(RUN / "datasets/paired-java-control/preflight.json")
    conditions = dict(base_model="Qwen2.5-Coder-7B-Instruct", base_revision="c03e6d358207e414f1eca0bb1891e29f1db0e242",
        matched_python=dict(train_per_target=7389, validation_per_target=931, test=dict(seen=997, unseen=250)),
        matched_java=preflight, peer_control=dict(train_per_arm=5231, validation_per_arm=306,
            canonical_progress_train=21416, canonical_progress_valid=2685),
        training=dict(seeds=[2027,2028,2029], epochs=1, learning_rate=0.0002, batch_size=2,
            accumulation=8, lora_rank=16, lora_alpha=32, lora_dropout=0.05,
            target_token_weight=1, checkpoint_selection="minimum validation loss; epoch evaluation/saving in retained train.py"),
        matched_inference=dict(prompt="D, current-only with position reset", decoder="greedy", max_new_tokens=4096,
            ordered_members=[2027,2028,2029], selection="all three same-target seeds, not validation subset search",
            python_batch=4, java_batch=24, candidate_feedback=False),
        runtime=dict(python="controller interpreter subprocess; 2.5s/test; 2048MB address space; minor version not pinned",
            java="oj:java-21-e5acbd8e27; network none; shared 16GB; compile 15s and whole harness 15s"),
        unavailable=["checkpoint weight files not included or reverified", "original Python minor-version manifest"],
        scope="saved-outcome analysis only; no post-deadline experiment; no public deposit")
    for path in ("src/repair/train.py", "src/repair/inference.py", "src/runner/python_runner.py",
                 "src/repair/evaluate.py", "scripts/run_fse2027_paired_target_control_remote.sh",
                 "scripts/run_fse2027_paired_java_remote.sh", "scripts/run_codeworkout_java_container.sh"):
        sources[path] = digest(ROOT / path)
    emit("conditions.json", conditions)
    copy(Path("paper/submission/README.txt"), "README.txt")
    copy(Path("scripts/verify_icse_seet_artifact.py"), "verify.py")
    for name in ("analyze_fse2027_robustness.py", "analyze_patch_locality.py", "analyze_paired_java_control.py", "compose_answer_seed_control.py"):
        copy(Path("scripts") / name, "scripts/" + name)
    for name in ("literature-breadth-audit.csv", "literature-breadth-audit.md", "literature-breadth-correction-20261021.txt"):
        copy(Path("paper") / name, "literature/" + name)
    copy(Path("paper/claim-evidence-ledger.md"), "evidence/claim-evidence-ledger.md")
    files = {str(p.relative_to(output)): digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
    emit("manifest.json", dict(schema=1, files=files, original_inputs=sources,
         paper_sha256=digest(ROOT / "paper/main.en.pdf"), source_sha256=digest(ROOT / "paper/main.en.tex")))
    # Assert no workstation/account handles were exported, including copied docs.
    for path in output.rglob("*"):
        if path.is_file():
            text = path.read_text()
            if any(marker in text for marker in ("/Users/", "/home/cdw", "dwchoi95", "cdw@")):
                raise ValueError("private location in " + str(path))
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                # Neutral, deterministic metadata: no local user or build timestamp.
                info = zipfile.ZipInfo(str(path.relative_to(output)), date_time=(2026,10,21,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                bundle.writestr(info, path.read_bytes())
    return dict(directory=str(output), archive=str(archive), files=len(files), sha256=digest(archive))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2))
