"""Read-only audit of controller outputs, donor splits, and prompt provenance."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.analyze_patch_locality import resolve_generated_codes
from scripts.compose_answer_seed_control import compose


def read(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def parses(code):
    try:
        ast.parse(code)
        return True
    except (SyntaxError, ValueError, TypeError):
        return False


def digest(code):
    return hashlib.sha256(code.encode()).hexdigest()


def audit(root):
    result = {"paired": {}, "donors": {}, "prompt_inputs": {}}
    for split in ("seen", "unseen"):
        dataset = read(root / "datasets/paired-target-control" / f"{split}-test.jsonl")
        source = {r["example_id"]: r["history"][-1]["code"] for r in dataset}
        folder = root / "eval/paired-target-control" / split
        methods, candidates = {}, {}
        replay_mismatches = []
        for relation in ("progress", "answer"):
            stages = []
            for seed in (2027, 2028, 2029):
                name = f"{relation}-{seed}"
                rows = read(folder / f"{name}.evaluation.jsonl")
                stages.append((name, rows))
                candidates[name] = {r["example_id"]: r for r in rows}
            methods[relation] = {r["example_id"]: r for r in read(folder / f"{relation}3.evaluation.jsonl")}
            for row in compose(dataset, stages):
                old = methods[relation][row["example_id"]]
                for field in ("repaired", "selected_source", "fixed_pass_rate", "ted_buggy_fixed"):
                    if row.get(field) != old.get(field):
                        replay_mismatches.append([relation, row["example_id"], field])
        resolve_generated_codes(methods, candidates, source)
        joint = [key for key in source if all(methods[m][key]["repaired"] for m in methods)]
        counts = Counter()
        exceptions = []
        for key in joint:
            flags = {"source": parses(source[key]), **{m: parses(methods[m][key]["generated_code"]) for m in methods}}
            ted_present = all(methods[m][key].get("ted_buggy_fixed") is not None for m in methods)
            counts["joint"] += 1
            counts["joint_ted_present"] += ted_present
            counts["source_unparseable"] += not flags["source"]
            counts["generated_unparseable"] += not all(flags[m] for m in methods)
            counts["missing_ted_despite_parseable"] += all(flags.values()) and not ted_present
            if not ted_present:
                exceptions.append({"example_id": key, "parses": flags})
        result["paired"][split] = {"counts": dict(counts), "replay_mismatches": replay_mismatches, "ted_exceptions": exceptions}
        for variant, path in {
            "canonical": root / "datasets" / f"{split}-test-final.jsonl",
            "current_only": root / "datasets/prompt-distribution-current-only" / f"{split}-test.jsonl",
        }.items():
            rows = read(path)
            result["prompt_inputs"][f"{split}_{variant}"] = {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "history_lengths": dict(Counter(len(r["history"]) for r in rows))}
    donor_ids = {}
    for split in ("train", "valid"):
        pool = read(root / "datasets" / f"{split}-progress.jsonl")
        by_id = {r["example_id"]: r for r in pool}
        peers = read(root / "datasets/cross-user-target-control" / f"{split}-cross-user.jsonl")
        violations = []
        for r in peers:
            donor = by_id.get(r["matched_target_source_example_id"])
            if donor is None or any(r[k] != donor[k] for k in ("target_code", "target_submission_id", "problem_id")) or str(r["user_id"]) == str(donor["user_id"]):
                violations.append(r["example_id"])
        reuse = Counter(r["target_submission_id"] for r in peers)
        donor_ids[split] = set(reuse)
        result["donors"][split] = {"source_records": len(pool), "matched_records": len(peers), "unique_donor_submissions": len(reuse), "unique_donor_users": len({r["matched_target_user_id"] for r in peers}), "reuse_histogram": dict(Counter(reuse.values())), "unique_target_codes": len({digest(r["target_code"]) for r in peers}), "violations": violations}
    result["donors"]["train_valid_donor_overlap"] = len(donor_ids["train"] & donor_ids["valid"])
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
