from __future__ import annotations

import csv
import html
import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable

from tqdm import tqdm


@dataclass(frozen=True)
class CasePair:
    input_path: Path
    output_path: Path


@dataclass(frozen=True)
class TestcaseBundle:
    contest: str
    task: str
    path: Path
    cases: tuple[CasePair, ...]


@dataclass(frozen=True)
class BuildSummary:
    problems: int
    problems_with_testcases: int
    problems_without_testcases: int
    users: int
    submissions: int
    testcases: int
    missing_submission_sources: int
    output_root: Path


class _SampleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._tag: str | None = None
        self._heading_parts: list[str] = []
        self._pre_parts: list[str] = []
        self._pending_sample: tuple[str, str] | None = None
        self.inputs: dict[str, str] = {}
        self.outputs: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag == "h3":
            self._tag = "h3"
            self._heading_parts = []
        elif tag == "pre" and self._pending_sample is not None:
            self._tag = "pre"
            self._pre_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._tag == "h3":
            heading = " ".join("".join(self._heading_parts).split())
            match = re.fullmatch(r"Sample\s+(Input|Output)(?:\s+(\d+))?", heading, re.I)
            self._pending_sample = None
            if match:
                kind = match.group(1).lower()
                index = match.group(2) or "1"
                self._pending_sample = (kind, index)
            self._tag = None
        elif tag == "pre" and self._tag == "pre" and self._pending_sample is not None:
            kind, index = self._pending_sample
            value = html.unescape("".join(self._pre_parts))
            target = self.inputs if kind == "input" else self.outputs
            target[index] = value
            self._pending_sample = None
            self._tag = None

    def handle_data(self, data: str) -> None:
        if self._tag == "h3":
            self._heading_parts.append(data)
        elif self._tag == "pre":
            self._pre_parts.append(data)


def build_python800_dataset(
    source_root: Path,
    output_root: Path,
    *,
    overwrite: bool = False,
    require_testcases: bool = False,
) -> BuildSummary:
    source_root = source_root.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    paths = _validate_source_layout(source_root)

    problem_ids = sorted(path.name for path in paths["benchmark"].iterdir() if path.is_dir())
    problem_metadata = _load_problem_metadata(paths["problem_list"])
    bundles, sample_index = _index_testcase_bundles(paths["testcases"])
    testcase_mapping = _resolve_testcase_mapping(
        problem_ids,
        problem_metadata,
        paths["descriptions"],
        bundles,
        sample_index,
    )

    missing_atcoder = [
        problem_id
        for problem_id in problem_ids
        if problem_metadata.get(problem_id, {}).get("dataset") == "AtCoder"
        and problem_id not in testcase_mapping
    ]
    if require_testcases and missing_atcoder:
        preview = ", ".join(missing_atcoder)
        families = Counter(
            _problem_family(problem_metadata[problem_id].get("name", ""))
            for problem_id in missing_atcoder
        )
        family_preview = ", ".join(
            f"{name}={count}" for name, count in families.most_common()
        )
        raise RuntimeError(
            f"Could not map testcases for {len(missing_atcoder)} AtCoder problems: "
            f"{preview}. Groups: {family_preview}"
        )

    output_root.mkdir(parents=True, exist_ok=True)
    totals: Counter[str] = Counter()
    for problem_id in tqdm(problem_ids, desc="Build CodeNet Python800", unit="problem"):
        destination = output_root / problem_id
        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Destination already exists: {destination}. Use --overwrite to replace it."
            )

        temporary = output_root / f".{problem_id}.tmp"
        if temporary.exists():
            shutil.rmtree(temporary)
        temporary.mkdir(parents=True)

        metadata = problem_metadata.get(problem_id)
        if metadata is None:
            raise KeyError(f"Missing problem metadata for {problem_id}")
        _write_problem_metadata(temporary / "metadata.json", metadata)

        description_source = paths["descriptions"] / f"{problem_id}.html"
        if not description_source.exists():
            raise FileNotFoundError(f"Missing problem description: {description_source}")
        shutil.copyfile(description_source, temporary / "description.html")

        testcase_count = _write_testcases(
            temporary / "testcases.jsonl",
            testcase_mapping.get(problem_id),
        )
        if testcase_count:
            totals["problems_with_testcases"] += 1
            totals["testcases"] += testcase_count
        else:
            totals["problems_without_testcases"] += 1

        submission_stats = _write_submissions(
            problem_id=problem_id,
            metadata_path=paths["metadata"] / f"{problem_id}.csv",
            source_dir=paths["data"] / problem_id / "Python",
            destination_dir=temporary / "submissions",
        )
        totals.update(submission_stats)

        if destination.exists():
            shutil.rmtree(destination)
        temporary.replace(destination)

    return BuildSummary(
        problems=len(problem_ids),
        problems_with_testcases=totals["problems_with_testcases"],
        problems_without_testcases=totals["problems_without_testcases"],
        users=totals["users"],
        submissions=totals["submissions"],
        testcases=totals["testcases"],
        missing_submission_sources=totals["missing_submission_sources"],
        output_root=output_root,
    )


def _validate_source_layout(source_root: Path) -> dict[str, Path]:
    descriptions = source_root / "problem_descriptions"
    paths = {
        "benchmark": source_root / "derived" / "benchmarks" / "Project_CodeNet_Python800",
        "data": source_root / "data",
        "metadata": source_root / "metadata",
        "problem_list": source_root / "metadata" / "problem_list.csv",
        "descriptions": descriptions,
        "testcases": source_root / "test_cases",
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing Project CodeNet paths:\n" + "\n".join(missing))
    return paths


def _load_problem_metadata(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return {row["id"]: row for row in csv.DictReader(file)}


def _write_problem_metadata(path: Path, row: dict[str, str]) -> None:
    payload = {
        "time_limit": _optional_int(row.get("time_limit")),
        "memory_limit": _optional_int(row.get("memory_limit")),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_submissions(
    *,
    problem_id: str,
    metadata_path: Path,
    source_dir: Path,
    destination_dir: Path,
) -> Counter[str]:
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing submission metadata: {metadata_path}")
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing Python submissions for {problem_id}: {source_dir}")

    source_by_id = {
        source.stem: source
        for source in source_dir.iterdir()
        if source.is_file() and not source.name.startswith(".")
    }
    rows: list[dict[str, str]] = []
    missing_sources = 0
    with metadata_path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("language") != "Python":
                continue
            if row.get("submission_id") not in source_by_id:
                missing_sources += 1
                continue
            rows.append(row)

    rows.sort(
        key=lambda row: (
            row.get("user_id", ""),
            _optional_int(row.get("date")) or 0,
            row.get("submission_id", ""),
        )
    )
    destination_dir.mkdir(parents=True)

    users = 0
    submissions = 0
    current_user: str | None = None
    output = None
    try:
        for row in rows:
            user_id = row["user_id"]
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", user_id):
                raise ValueError(f"Unsafe CodeNet user_id in {problem_id}: {user_id!r}")
            if user_id != current_user:
                if output is not None:
                    output.close()
                output = (destination_dir / f"{user_id}.jsonl").open("w", encoding="utf-8")
                current_user = user_id
                users += 1

            submission_id = row["submission_id"]
            code = source_by_id[submission_id].read_text(encoding="utf-8", errors="replace")
            record = {
                "submission_id": submission_id,
                "timestamp": _optional_int(row.get("date")),
                "verdict": row.get("status") or None,
                "code": code,
            }
            assert output is not None
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            submissions += 1
    finally:
        if output is not None:
            output.close()

    return Counter(
        users=users,
        submissions=submissions,
        missing_submission_sources=missing_sources,
    )


def _index_testcase_bundles(
    testcase_root: Path,
) -> tuple[dict[tuple[str, str], TestcaseBundle], dict[tuple[str, str], set[tuple[str, str]]]]:
    bundles: dict[tuple[str, str], TestcaseBundle] = {}
    sample_index: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
    contest_dirs = sorted(path for path in testcase_root.iterdir() if path.is_dir())
    for contest_dir in tqdm(contest_dirs, desc="Index testcase samples", unit="contest"):
        for task_dir in sorted(path for path in contest_dir.iterdir() if path.is_dir()):
            cases = tuple(_find_case_pairs(task_dir))
            if not cases:
                continue
            key = (contest_dir.name, task_dir.name)
            bundle = TestcaseBundle(
                contest=contest_dir.name,
                task=task_dir.name,
                path=task_dir,
                cases=cases,
            )
            bundles[key] = bundle
            for case in cases:
                if not _looks_like_sample(case.input_path.name):
                    continue
                fingerprint = _case_fingerprint(
                    _read_text(case.input_path),
                    _read_text(case.output_path),
                )
                sample_index[fingerprint].add(key)
    return bundles, sample_index


def _resolve_testcase_mapping(
    problem_ids: list[str],
    metadata: dict[str, dict[str, str]],
    descriptions: Path,
    bundles: dict[tuple[str, str], TestcaseBundle],
    sample_index: dict[tuple[str, str], set[tuple[str, str]]],
) -> dict[str, TestcaseBundle]:
    task_hints = _build_task_hints(metadata)
    direct_hints = _build_direct_bundle_hints(metadata, bundles, task_hints)
    mapping: dict[str, TestcaseBundle] = {}
    for problem_id in problem_ids:
        row = metadata.get(problem_id, {})
        if row.get("dataset") != "AtCoder":
            continue
        description_path = descriptions / f"{problem_id}.html"
        if not description_path.exists():
            continue
        direct_hint = direct_hints.get(problem_id)
        if direct_hint is not None:
            mapping[problem_id] = bundles[direct_hint]
            continue

        samples = _extract_sample_pairs(description_path)
        scores: Counter[tuple[str, str]] = Counter()
        for sample_input, sample_output in samples:
            scores.update(sample_index.get(_case_fingerprint(sample_input, sample_output), ()))
        if scores:
            highest = max(scores.values())
            if highest != len(samples):
                continue
            candidates = [key for key, score in scores.items() if score == highest]
            hint = task_hints.get(problem_id)
            if hint is not None:
                hinted = [key for key in candidates if key[1].upper() == hint]
                if len(hinted) == 1:
                    candidates = hinted
            if len(candidates) == 1:
                mapping[problem_id] = bundles[candidates[0]]
    return mapping


def _build_task_hints(metadata: dict[str, dict[str, str]]) -> dict[str, str]:
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for problem_id, row in metadata.items():
        if row.get("dataset") != "AtCoder":
            continue
        name = row.get("name", "")
        contest = _standard_contest(name)
        if contest is None:
            continue
        groups[contest].append(problem_id)

    hints: dict[str, str] = {}
    for (kind, _), problem_ids in groups.items():
        offset = 2 if kind == "ARC" else 0
        for index, problem_id in enumerate(sorted(problem_ids)):
            if offset + index < 26:
                hints[problem_id] = chr(ord("A") + offset + index)
    return hints


def _build_direct_bundle_hints(
    metadata: dict[str, dict[str, str]],
    bundles: dict[tuple[str, str], TestcaseBundle],
    task_hints: dict[str, str],
) -> dict[str, tuple[str, str]]:
    available = {
        (contest.lower(), task.upper()): (contest, task)
        for contest, task in bundles
    }
    hints: dict[str, tuple[str, str]] = {}
    for problem_id, task in task_hints.items():
        contest = _standard_contest(metadata[problem_id].get("name", ""))
        if contest is None:
            continue
        kind, number = contest
        if kind == "ABC" and number == "042":
            directory = "ARC058_ABC042"
        elif kind == "ABC" and number == "043":
            directory = "ARC059_ABC043"
        else:
            directory = f"{kind}{number}"
        key = available.get((directory.lower(), task))
        if key is not None:
            hints[problem_id] = key
    return hints


def _standard_contest(name: str) -> tuple[str, str] | None:
    patterns = {
        "ABC": r"AtCoder Beginner Contest\s+(\d+)",
        "ARC": r"AtCoder Regular Contest\s+(\d+)",
        "AGC": r"AtCoder Grand Contest\s+(\d+)",
    }
    for kind, pattern in patterns.items():
        match = re.search(pattern, name, re.I)
        if match:
            return kind, match.group(1).zfill(3)
    return None


def _problem_family(name: str) -> str:
    standard = _standard_contest(name)
    if standard is not None:
        return "".join(standard)
    if " - " in name:
        return name.split(" - ", 1)[0]
    return name or "<unnamed>"


def _extract_sample_pairs(path: Path) -> list[tuple[str, str]]:
    parser = _SampleParser()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    indexes = sorted(set(parser.inputs) & set(parser.outputs), key=lambda value: int(value))
    return [(parser.inputs[index], parser.outputs[index]) for index in indexes]


def _find_case_pairs(task_dir: Path) -> Iterable[CasePair]:
    input_dir = task_dir / "in"
    output_dir = task_dir / "out"
    if not output_dir.is_dir():
        return

    if input_dir.is_dir():
        input_paths = _visible_files(input_dir)
    else:
        input_paths = _visible_files(task_dir)
    output_paths = _visible_files(output_dir)
    outputs_by_name = {path.name: path for path in output_paths}
    outputs_by_stem: dict[str, list[Path]] = defaultdict(list)
    for path in output_paths:
        outputs_by_stem[path.stem].append(path)

    for input_path in sorted(input_paths, key=lambda path: path.name):
        output_path = outputs_by_name.get(input_path.name)
        if output_path is None:
            same_stem = outputs_by_stem.get(input_path.stem, [])
            if len(same_stem) == 1:
                output_path = same_stem[0]
        if output_path is not None:
            yield CasePair(input_path=input_path, output_path=output_path)


def _visible_files(directory: Path) -> list[Path]:
    return [
        path
        for path in directory.iterdir()
        if path.is_file() and not path.name.startswith(".")
    ]


def _write_testcases(path: Path, bundle: TestcaseBundle | None) -> int:
    with path.open("w", encoding="utf-8") as output:
        if bundle is None:
            return 0
        for index, case in enumerate(bundle.cases, start=1):
            record = {
                "case_id": f"case_{index:05d}",
                "input": _read_text(case.input_path),
                "expected_output": _read_text(case.output_path),
            }
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(bundle.cases) if bundle is not None else 0


def _looks_like_sample(filename: str) -> bool:
    value = filename.lower()
    return bool(
        re.search(
            r"sample|example|(?:^|[-_])s\d+(?:[-_.]|$)|^a0?\d+(?:\.[^.]+)?$",
            value,
        )
    )


def _case_fingerprint(input_text: str, output_text: str) -> tuple[str, str]:
    return (_normalize_tokens(input_text), _normalize_tokens(output_text))


def _normalize_tokens(value: str) -> str:
    return " ".join(value.split())


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _optional_int(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(value)
