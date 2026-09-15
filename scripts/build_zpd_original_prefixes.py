"""Inventory original release-snapshot histories; no fitting or outcome filtering.

All languages and repeated source submissions are preserved. 'Original' means
the supplied CodeNet release, not complete lifetime behavior or observed help.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

SALT = "zpd-history-gate-20260915-v1"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def split_for_user(user):
    value = int(digest(f"{SALT}:{user}".encode()), 16) / 2**256
    return "train" if value < .70 else "valid" if value < .85 else "test"


def safe_component(value):
    return bool(value and re.fullmatch(r"[A-Za-z0-9_+.# -]+", value) and value not in {".", ".."})


def build(metadata_root: Path, data_root: Path, problem_roster: Path, output: Path):
    metadata_root, data_root, problem_roster, output = map(Path.resolve, (metadata_root, data_root, problem_roster, output))
    for source in (metadata_root, data_root, problem_roster):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError("output must be separate from input trees")
    if output.exists():
        raise FileExistsError(output)
    problems = sorted(p.name for p in problem_roster.glob("p*") if p.is_dir())
    if not problems or any(not re.fullmatch(r"p\d+", p) for p in problems):
        raise ValueError("invalid/empty fixed problem directory roster")
    output.mkdir(parents=True)
    handles = {name: (output / f"{name}.jsonl").open("x", encoding="utf-8")
               for name in ("features", "references", "labels", "codes", "audit")}
    counts, inputs, sources = Counter(), {}, {}
    users_by_split = defaultdict(set)

    def emit(name, row):
        handles[name].write(json.dumps(row, ensure_ascii=False) + "\n")

    try:
        for problem in problems:
            meta = metadata_root / f"{problem}.csv"
            if not meta.is_file():
                counts["missing_metadata_problems"] += 1
                emit("audit", {"problem_id": problem, "reason": "missing_metadata", "eligibility": "unknown"})
                continue
            inputs[str(meta)] = file_digest(meta)
            groups, ids = defaultdict(list), set()
            with meta.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                if not {"submission_id", "problem_id", "user_id", "date", "language", "filename_ext", "status"}.issubset(reader.fieldnames or []):
                    raise ValueError("unsupported CodeNet metadata schema")
                for raw in reader:
                    if raw["problem_id"] != problem or not raw["user_id"] or not raw["submission_id"] or raw["submission_id"] in ids:
                        raise ValueError("duplicate/mismatched metadata identity")
                    ids.add(raw["submission_id"])
                    try:
                        stamp = int(raw["date"])
                    except ValueError:
                        stamp = None
                    groups[raw["user_id"]].append({**raw, "timestamp": stamp})
            counts["metadata_rows"] += len(ids)
            for user, history in groups.items():
                split = split_for_user(user)
                users_by_split[split].add(user)
                counts["user_problem_groups"] += 1
                if all(row["status"] for row in history) and not any(row["status"] == "Accepted" for row in history):
                    counts["observed_no_ac_user_problem_groups"] += 1
                # Unknown dates prevent determining even the immediate successor.
                if any(row["timestamp"] is None for row in history):
                    counts["undated_user_problem_groups"] += 1
                    emit("audit", {"problem_id": problem, "user_id": user, "reason": "undated_group_order_unknown", "rows": len(history), "eligibility": "unknown"})
                    continue
                history.sort(key=lambda row: (row["timestamp"], row["submission_id"]))
                candidates = [i for i, row in enumerate(history) if row["language"] == "Python" and row["status"] and row["status"] != "Accepted" and history[0]["timestamp"] < row["timestamp"]]
                if not candidates:
                    counts["groups_without_candidate_prefixes"] += 1
                    continue
                last_observed = max(candidates)
                loaded = []
                for source_index, row in enumerate(history):
                    key = f"{problem}:{row['submission_id']}"
                    language, extension, submission = row["language"], row["filename_ext"], row["submission_id"]
                    issue, code_hash, path = None, None, None
                    if not all(safe_component(part) for part in (language, extension, submission)):
                        issue = "unsafe_source_path"
                    else:
                        path = data_root / problem / language / f"{submission}.{extension}"
                        if not path.resolve().is_relative_to(data_root):
                            issue = "source_path_outside_root"
                        elif not path.is_file():
                            issue = "missing_source"
                        elif source_index > last_observed:
                            issue = "future_source_not_read"
                        else:
                            data = path.read_bytes()
                            code_hash = digest(data)
                            sources[str(path)] = code_hash
                            try:
                                code = data.decode("utf-8")
                            except UnicodeDecodeError:
                                issue = "undecodable_source"
                            else:
                                emit("codes", {"code_id": key, "code": code, "source_sha256": code_hash})
                    counts[issue or "readable_sources"] += 1
                    loaded.append({"submission_id": submission, "timestamp": row["timestamp"], "verdict": row["status"] or None,
                                   "language": language or None, "code_id": key if issue is None else None,
                                   "source_sha256": code_hash, "source_issue": issue})
                    if issue and issue != "future_source_not_read":
                        emit("audit", {"problem_id": problem, "submission_id": submission, "source_path": str(path) if path else None, "reason": issue})
                for index, row in enumerate(history):
                    if row["language"] != "Python" or not row["status"] or row["status"] == "Accepted":
                        continue
                    counts["python_non_ac_currents"] += 1
                    if not any(prior["timestamp"] < row["timestamp"] for prior in history[:index]):
                        counts["no_strictly_prior_history"] += 1
                        continue
                    example = f"{problem}:{row['submission_id']}"
                    observed = loaded[:index + 1]
                    successor = loaded[index + 1] if index + 1 < len(loaded) else None
                    # Tie ordering is never inferred from lexical submission IDs.
                    involved = loaded[:index + 2]
                    ambiguous = len({r["timestamp"] for r in involved}) != len(involved)
                    missing = any(r["source_issue"] for r in observed)
                    censored = successor is None and not ambiguous
                    counts["candidate_prefixes"] += 1
                    counts["ambiguous_prefixes"] += ambiguous
                    counts["missing_source_prefixes"] += missing
                    counts["censored_prefixes"] += censored
                    eligible = not ambiguous and not missing and not censored
                    counts["primary_eligible_prefixes"] += eligible
                    counts[f"{split}_primary_eligible_prefixes"] += eligible
                    emit("references", {"example_id": example, "problem_id": problem, "user_id": user, "split": split,
                                        "primary_eligible": eligible, "order_ambiguous": ambiguous,
                                        "observed_source_missing": missing, "right_censored": None if ambiguous else censored})
                    # IDs serve restricted code joins; references and labels are not model inputs.
                    if not ambiguous and not missing:
                        emit("features", {"example_id": example, "current_timestamp": row["timestamp"],
                                          "observed_history": [{**r, "elapsed_seconds": r["timestamp"] - observed[0]["timestamp"]} for r in observed]})
                    emit("labels", {"example_id": example, "next_submission": successor if not ambiguous else None,
                                    "right_censored": censored if not ambiguous else None,
                                    "label_status": "order_ambiguous" if ambiguous else "censored" if censored else "observed"})
    finally:
        for handle in handles.values():
            handle.close()
    manifest = {"schema_version": 1, "scope": "supplied original release snapshot; lifetime completeness unknown",
                "problem_roster": problems, "counts": dict(counts), "metadata_sha256": inputs,
                "source_sha256": sources, "script_sha256": digest(Path(__file__).read_bytes()),
                "split": {"unit": "user_id across problems", "salt": SALT, "algorithm": "SHA256(salt:user_id)/2**256; thresholds .70,.85", "users": {k: len(v) for k, v in users_by_split.items()}},
                "fitting_performed": False, "assistance_observed": False,
                "feature_access": "only observed_history code IDs; references, labels and unrestricted codes forbidden",
                "filters_not_used": ["eventual_AC", "deduplication", "first_AC_truncation", "max_history"],
                "output_sha256": {p.name: file_digest(p) for p in sorted(output.glob("*.jsonl"))}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "COMPLETE").write_text("inventory only; no fitting\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("metadata-root", "data-root", "problem-roster", "output"):
        parser.add_argument(f"--{arg}", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.metadata_root, args.data_root, args.problem_roster, args.output)
    print(json.dumps({"counts": report["counts"], "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
