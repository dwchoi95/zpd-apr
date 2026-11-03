"""Build the Seen/Unseen corpus (RQ2-RQ4) from Project CodeNet and the split manifest."""

from __future__ import annotations

import json
import lzma
import shutil
from pathlib import Path

from .builder import (
    _index_testcase_bundles,
    _load_problem_metadata,
    _resolve_testcase_mapping,
    _validate_source_layout,
    _write_problem_metadata,
    _write_testcases,
)
from .rq1 import _write_jsonl, codenet_records, submission_rows

MANIFEST = Path(__file__).with_name("seen_unseen_manifest.json.xz")


def build_seen_unseen_benchmark(
    source_root: Path,
    output_root: Path,
    *,
    manifest_path: Path = MANIFEST,
    overwrite: bool = False,
) -> dict[str, int]:
    paths = _validate_source_layout(source_root.expanduser().resolve())
    manifest = json.loads(lzma.decompress(manifest_path.read_bytes()))
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"Destination already exists: {output_root}. Use --overwrite to replace it.")
        shutil.rmtree(output_root)
    problem_metadata = _load_problem_metadata(paths["problem_list"])
    # Tests are matched over every Python800 problem, as when the corpus was first built.
    all_problems = sorted(path.name for path in paths["benchmark"].iterdir() if path.is_dir())
    bundles, sample_index = _index_testcase_bundles(paths["testcases"])
    mapping = _resolve_testcase_mapping(all_problems, problem_metadata, paths["descriptions"], bundles, sample_index)
    problems = [row["problem_id"] for row in manifest["splits"]["problem_split"]]
    for problem_id in problems:
        destination = output_root / problem_id
        destination.mkdir(parents=True)
        _write_problem_metadata(destination / "metadata.json", problem_metadata[problem_id])
        shutil.copyfile(paths["descriptions"] / f"{problem_id}.html", destination / "description.html")
        _write_testcases(destination / "testcases.jsonl", mapping.get(problem_id))
    rows_by_problem: dict[str, dict] = {}
    for relative_path, submission_ids in manifest["submissions"].items():
        problem_id = relative_path.split("/", 1)[0]
        if problem_id not in rows_by_problem:
            rows_by_problem = {problem_id: submission_rows(paths, problem_id)}
        _write_jsonl(output_root / relative_path, codenet_records(paths, problem_id, submission_ids, rows_by_problem[problem_id]))
    for name, rows in manifest["splits"].items():
        _write_jsonl(output_root / "splits" / f"{name}.jsonl", rows)
    (output_root / "splits" / "summary.json").write_text(
        json.dumps(manifest["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"problems": len(problems), "trajectories": len(manifest["submissions"])}
