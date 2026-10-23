"""Offline supplement verifier. No model or student-program execution."""
from __future__ import annotations

import hashlib
import argparse
import json
import math
from pathlib import Path

from scripts.analyze_fse2027_robustness import paired_suite_rows


def close(left, right, path="root"):
    if isinstance(right, dict):
        for key, value in right.items():
            close(left[key], value, path + "." + key)
    elif isinstance(right, list):
        assert len(left) == len(right), path
        for i, (a, b) in enumerate(zip(left, right)):
            close(a, b, f"{path}[{i}]")
    elif isinstance(right, (int, float)) and not isinstance(right, bool):
        assert math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-10), (path, left, right)
    else:
        assert left == right, (path, left, right)


def check_hashes(root):
    manifest = json.loads((root / "manifest.json").read_text())
    expected = set(manifest["files"])
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()
              and "__pycache__" not in p.parts and p.name != "manifest.json"}
    assert actual == expected, ("unexpected/missing files", actual ^ expected)
    for name, digest in manifest["files"].items():
        path = (root / name).resolve()
        assert root.resolve() in path.parents, "path traversal"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, name
    return len(expected)


def verify(root):
    files = check_hashes(root)
    result = {"verified_files": files, "comparisons": {}}
    for name in ("python-seen", "python-unseen", "java"):
        pair = json.loads((root / "pairs" / f"{name}.json").read_text())
        expected = json.loads((root / "expected" / f"{name}.json").read_text())
        left, right = pair["progress"], pair["answer"]
        assert len(left) == pair["examples"] == len(right)
        for a, b in zip(left, right, strict=True):
            assert all(a[k] == b[k] for k in ("example_id", "problem_id", "user_id"))
        for cluster, seed in pair["bootstrap_seeds"].items():
            l = [{**r, "problem_id": r[cluster]} for r in left]
            r = [{**r, "problem_id": r[cluster]} for r in right]
            measured = paired_suite_rows(l, r, left_label="Progress3", right_label="Answer3",
                                        samples=10000, seed=seed)
            target = expected[cluster]
            for key in ("rr_contingency", "exact_mcnemar_two_sided_p", "paired", "paired_ted"):
                close(measured[key], target[key], name + "." + cluster + "." + key)
        retention = pair["retention"]
        assert len(retention) == expected["joint_repairs"]
        for metric, value in expected["retention_means"].items():
            close(sum(r[metric] for r in retention) / len(retention), value, name + "." + metric)
        result["comparisons"][name] = {
            "examples": len(left), "progress_success": sum(r["repaired"] for r in left),
            "answer_success": sum(r["repaired"] for r in right),
            "joint_success": len(retention), "cluster_intervals_reproduced": True,
        }
    family = json.loads((root / "evidence/history-retraining.json").read_text())
    ordered = sorted(family, key=lambda x: family[x]["exact_mcnemar_two_sided_p"])
    maximum = 0.0
    adjusted = {}
    for i, name in enumerate(ordered):
        maximum = min(1.0, max(maximum, (len(ordered) - i) * family[name]["exact_mcnemar_two_sided_p"]))
        adjusted[name] = maximum
    assert len(adjusted) == 4
    close(min(adjusted.values()), 0.31341552734375)
    result["history_holm"] = adjusted
    return result


if __name__ == "__main__":
    # Copied to archive root as verify.py by the builder.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.report and args.root.resolve() in args.report.resolve().parents:
        raise ValueError("verification report must be outside the hashed archive directory")
    report = verify(args.root)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
