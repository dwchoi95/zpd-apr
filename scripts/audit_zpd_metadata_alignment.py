"""Read-only archive alignment against CodeNet metadata; no training or relabeling.

CSV column names follow src/codenet/builder.py. Completeness of the supplied
metadata release is NOT assumed: never-AC means within supplied metadata only.
Equal timestamps cannot establish submission order.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path


def rows(path):
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def timestamp(value):
    try:
        return int(value) if value is not None and str(value).strip() else None
    except (ValueError, TypeError):
        return None


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(archive_root: Path, metadata_root: Path, output: Path):
    archive_root, metadata_root, output = map(Path.resolve, (archive_root, metadata_root, output))
    for source in (archive_root, metadata_root):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError("output must be separate from inputs")
    if output.exists():
        raise FileExistsError(output)
    paths = sorted(archive_root.glob("p*/sequences.jsonl"))
    if not paths:
        raise ValueError("no archive sequences")
    output.mkdir(parents=True)
    totals, reports, hashes = Counter(), [], {}
    with (output / "anomalies.jsonl").open("x", encoding="utf-8") as detail:
        def record(kind, **fields):
            totals[kind] += 1
            detail.write(json.dumps({"kind": kind, **fields}, ensure_ascii=False) + "\n")

        for seqpath in paths:
            problem = seqpath.parent.name
            meta = metadata_root / f"{problem}.csv"
            hashes[str(seqpath)] = sha(seqpath)
            if not meta.exists():
                record("missing_metadata_files", problem_id=problem)
                reports.append({"problem_id": problem, "status": "unknown: missing metadata"})
                continue
            hashes[str(meta)] = sha(meta)
            by_id, groups = {}, defaultdict(list)
            with meta.open(encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                required = {"submission_id", "user_id", "date", "status", "language"}
                if not required.issubset(reader.fieldnames or []):
                    raise ValueError(f"unsupported metadata columns: {meta}")
                for row in reader:
                    key = row["submission_id"]
                    if not key or not row["user_id"] or key in by_id:
                        raise ValueError(f"duplicate/empty metadata identity: {meta}: {key}")
                    if row.get("problem_id", problem) != problem:
                        raise ValueError("metadata problem mismatch")
                    row["_time"] = timestamp(row["date"])
                    by_id[key] = row
                    groups[row["user_id"]].append(row)
            totals["metadata_rows"] += len(by_id)
            subpath = seqpath.with_name("submissions.jsonl")
            raw = {}
            if subpath.exists():
                hashes[str(subpath)] = sha(subpath)
                for row in rows(subpath):
                    key = str(row["submission_id"])
                    if key in raw:
                        raise ValueError("duplicate archived submission")
                    raw[key] = row
            else:
                record("missing_submission_files", problem_id=problem)
            archived_users, used, sequence_ids = set(), set(), set()
            for seq in rows(seqpath):
                user, sid = str(seq["user_id"]), str(seq["sequence_id"])
                ids = list(map(str, seq["submission_ids"]))
                times, verdicts = seq["timestamps"], seq["verdicts"]
                if seq["problem_id"] != problem or not ids or len(ids) != len(times) or len(ids) != len(verdicts):
                    raise ValueError("invalid sequence arrays/problem")
                if sid in sequence_ids or len(set(ids)) != len(ids) or used.intersection(ids):
                    raise ValueError("duplicate sequence/submission identity")
                sequence_ids.add(sid)
                archived_users.add(user)
                used.update(ids)
                totals["archive_sequences"] += 1
                if all(verdicts) and "Accepted" not in verdicts:
                    totals["archive_sequences_without_observed_ac"] += 1
                for index, key in enumerate(ids):
                    common = {"problem_id": problem, "sequence_id": sid, "submission_id": key}
                    found = by_id.get(key)
                    if found is None:
                        record("archive_ids_missing_metadata", **common)
                        continue
                    totals["joined_archive_ids"] += 1
                    for name, observed, expected in (
                        ("user", user, found["user_id"]),
                        ("timestamp", timestamp(times[index]), found["_time"]),
                        ("verdict", verdicts[index], found["status"]),
                    ):
                        if observed is None or observed == "" or expected is None or expected == "":
                            record(f"{name}_unknown", **common)
                        elif observed != expected:
                            record(f"{name}_mismatches", archive=observed, metadata=expected, **common)
                    source = raw.get(key)
                    if source is None:
                        record("archive_ids_missing_submission", **common)
                    else:
                        for field, expected in (("verdict", found["status"]), ("lang", found["language"])):
                            value = source.get(field)
                            if not value or not expected:
                                record(f"submission_{field}_unknown", **common)
                            elif str(value).casefold() != expected.casefold():
                                record(f"submission_{field}_mismatches", archive=value, metadata=expected, **common)
                for left, right in zip(ids, ids[1:]):
                    a, b = by_id.get(left), by_id.get(right)
                    common = {"problem_id": problem, "sequence_id": sid, "left": left, "right": right}
                    totals["archive_next_pairs"] += 1
                    if not a or not b or a["user_id"] != user or b["user_id"] != user or a["_time"] is None or b["_time"] is None:
                        record("next_pair_order_unknown", **common)
                        continue
                    lo, hi = a["_time"], b["_time"]
                    if lo >= hi:
                        record("next_pair_tied_or_reversed", **common)
                        continue
                    middle = [r for r in groups[user] if r["_time"] is not None and lo < r["_time"] < hi]
                    boundary = [r["submission_id"] for r in groups[user] if r["submission_id"] not in {left, right} and r["_time"] in {lo, hi}]
                    if boundary:
                        record("next_pair_boundary_ties", candidates=boundary, **common)
                    if any(r["_time"] is None for r in groups[user]):
                        record("next_pair_has_undated_candidates", **common)
                    if middle:
                        record("next_pair_missing_intermediate", intermediates=[{"submission_id": r["submission_id"], "language": r["language"]} for r in middle], **common)
                        totals["intermediate_metadata_rows"] += len(middle)
                        totals["intermediate_python_rows"] += sum(r["language"] == "Python" for r in middle)
                    languages = [a["language"], b["language"], *(r["language"] for r in middle)]
                    if any(not language for language in languages):
                        record("next_pair_language_unknown", **common)
                    if len({language for language in languages if language}) > 1:
                        record("next_pair_language_switch", **common)
            for user, group in groups.items():
                python = [r for r in group if r["language"] == "Python"]
                for scope, selected in (("all_language", group), ("python", python)):
                    if not selected:
                        continue
                    totals[f"metadata_{scope}_user_problem_groups"] += 1
                    if any(not r["status"] for r in selected):
                        totals[f"metadata_{scope}_ac_status_unknown_groups"] += 1
                    elif not any(r["status"] == "Accepted" for r in selected):
                        totals[f"metadata_{scope}_without_observed_ac_groups"] += 1
                        if user not in archived_users:
                            totals[f"metadata_{scope}_without_observed_ac_absent_archive_groups"] += 1
            reports.append({"problem_id": problem, "status": "audited", "metadata_rows": len(by_id), "archive_users": len(archived_users)})
    report = {"schema_version": 1, "counts": dict(totals), "problems": reports,
              "scope": "archive problem IDs only; never AC means no AC in supplied metadata, not lifetime behavior",
              "metadata_release_completeness": "unknown", "source_code_completeness": "unknown",
              "ordering_policy": "strict timestamp intervals only; ties/undated records flagged, not ordered by ID",
              "counter_policy": "omitted counters are zero within audited files only; missing files remain unknown",
              "input_sha256": hashes, "script_sha256": sha(Path(__file__)),
              "training_performed": False}
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", required=True, type=Path)
    parser.add_argument("--metadata-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.archive_root, args.metadata_root, args.output), indent=2))


if __name__ == "__main__":
    main()
