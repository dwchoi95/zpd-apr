"""Inventory archived next-observed submissions; never train or mutate inputs."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def rows(path: Path):
    # splitlines() corrupts JSON strings containing literal Unicode separators.
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def emit(handle, value):
    handle.write(json.dumps(value, ensure_ascii=False) + "\n")


def build(archive_root: Path, retained_root: Path, output: Path) -> dict:
    archive_root, retained_root, output = (p.resolve() for p in
                                          (archive_root, retained_root, output))
    for source in (archive_root, retained_root):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError("output must be separate from source trees")
    if any(part.startswith("canonical-v") or part == "data-canonical-v5"
           for part in output.parts):
        raise ValueError("canonical output paths are forbidden")
    if output.exists():
        raise FileExistsError("output must be a new directory")
    files = sorted(archive_root.glob("p*/submissions.jsonl"))
    if not files:
        raise ValueError("no archived submission files")
    output.mkdir(parents=True)
    counts, users, hashes = Counter(), set(), {}
    handles = {name: (output / f"{name}.jsonl").open("x", encoding="utf-8")
               for name in ("features", "labels", "references", "codes")}
    try:
        for path in files:
            problem = path.parent.name
            sequence_path = path.with_name("sequences.jsonl")
            raw = {}
            for row in rows(path):
                key = str(row["submission_id"])
                if key in raw:
                    raise ValueError("duplicate archived submission ID")
                if row["problem_id"] != problem or not isinstance(row["code_tokens"], str):
                    raise ValueError("submission problem/code mismatch")
                if row.get("lang", "").lower() != "python":
                    raise ValueError("non-Python archive record")
                raw[key] = row
            retained = {}
            for source in sorted((retained_root / problem / "submissions").glob("*.jsonl")):
                hashes[str(source)] = digest(source.read_bytes())
                for row in rows(source):
                    key = str(row["submission_id"])
                    if key in retained:
                        raise ValueError("duplicate retained submission ID")
                    retained[key] = row
            for source in (path, sequence_path):
                hashes[str(source)] = digest(source.read_bytes())
            counts["problems"] += 1
            used, sequence_ids = set(), set()
            for seq in rows(sequence_path):
                sid = str(seq["sequence_id"])
                if sid in sequence_ids:
                    raise ValueError("duplicate sequence ID")
                sequence_ids.add(sid)
                ids = list(map(str, seq["submission_ids"]))
                timestamps, verdicts = seq["timestamps"], seq["verdicts"]
                if seq["problem_id"] != problem or not ids or not (
                    len(ids) == len(timestamps) == len(verdicts) == seq["sequence_length"]
                ):
                    raise ValueError("sequence arrays/problem mismatch")
                if len(set(ids)) != len(ids) or used.intersection(ids):
                    raise ValueError("repeated submission ID in sequences")
                if any(type(t) is not int for t in timestamps) or timestamps != sorted(timestamps):
                    raise ValueError("missing/nonchronological timestamps")
                counts["timestamp_ties"] += len(timestamps) - len(set(timestamps))
                users.add(str(seq["user_id"]))
                counts["sequences"] += 1
                counts["sequences_without_ac"] += not any(v == "Accepted" for v in verdicts)
                counts["sequences_with_post_ac"] += "Accepted" in verdicts[:-1]
                for index, key in enumerate(ids):
                    if key not in raw:
                        raise ValueError("missing archived code join")
                    if raw[key]["verdict"] != verdicts[index]:
                        raise ValueError("archive verdict mismatch")
                    code = raw[key]["code_tokens"]
                    if key in retained and (retained[key]["code"] != code or
                                            retained[key]["timestamp"] != timestamps[index]):
                        raise ValueError("retained code/timestamp mismatch")
                    counts["retained_overlap_ids" if key in retained else "extra_ids"] += 1
                    emit(handles["codes"], {"problem_id": problem, "submission_id": key,
                         "code": code, "code_sha256": digest(code.encode("utf-8"))})
                used.update(ids)
                for index in range(len(ids) - 1):
                    example = f"{problem}:{sid}:{ids[index]}"
                    # No full trajectory length, next verdict, next time or eventual AC here.
                    observed = [{"submission_id": key, "timestamp": timestamps[j],
                                 "verdict": verdicts[j],
                                 "code_sha256": digest(raw[key]["code_tokens"].encode("utf-8"))}
                                for j, key in enumerate(ids[:index + 1])]
                    emit(handles["features"], {"example_id": example,
                         "current_submission_id": ids[index], "observed_history": observed})
                    emit(handles["labels"], {"example_id": example,
                         "next_submission_id": ids[index + 1],
                         "next_timestamp": timestamps[index + 1],
                         "next_historical_verdict": verdicts[index + 1],
                         "next_code_sha256": digest(raw[ids[index + 1]]["code_tokens"].encode("utf-8")),
                         "replayed_pass_rate": None})
                    emit(handles["references"], {"example_id": example,
                         "problem_id": problem, "user_id": str(seq["user_id"]),
                         "sequence_id": sid, "source_file": str(path),
                         "sequence_file": str(sequence_path),
                         "current_retained": ids[index] in retained,
                         "next_retained": ids[index + 1] in retained,
                         "timestamp_order_ambiguous": timestamps[index] == timestamps[index + 1]})
                    counts["prefixes"] += 1
            if used != set(raw):
                raise ValueError("unreferenced archived submission records")
            counts["submission_records"] += len(raw)
    finally:
        for handle in handles.values():
            handle.close()
    manifest = {"schema_version": 1, "task": "next observed archived submission inventory",
                "counts": dict(counts), "users": len(users),
                "eventual_ac_only": counts["sequences_without_ac"] == 0,
                "original_completeness": "unknown", "assistance_observed": False,
                "timestamp_tie_policy": "preserve archive order and flag; no inferred chronology",
                "feature_file": "features.jsonl", "label_file": "labels.jsonl",
                "reference_file": "references.jsonl", "code_store": "codes.jsonl",
                "forbidden_model_inputs": ["example_id", "labels", "references", "unrestricted code store"],
                "code_access_policy": "join only IDs in observed_history; labels are not model inputs",
                "input_sha256": hashes, "script_sha256": digest(Path(__file__).read_bytes())}
    manifest["output_sha256"] = {p.name: digest(p.read_bytes()) for p in sorted(output.glob("*.jsonl"))}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (output / "COMPLETE").write_text("inventory only; no fitting\n", encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--retained-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.archive_root, args.retained_root, args.output), indent=2))


if __name__ == "__main__":
    main()
