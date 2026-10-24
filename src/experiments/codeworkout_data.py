"""Build the CodeWorkout (Java) corpus from the TIKTOC release.

Steps: export the official pickle in an isolated process (bubblewrap), compile every submission in the Java judge image
(docker/java/Dockerfile), build first-accepted trajectories split by student, drop trajectories over 4,096 tokens, and
write the student- and exercise-held-out datasets and the matched Answer/Progress datasets of RQ2.
Needs Linux with bubblewrap for the export and Docker for the compile step."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PICKLE_SHA256 = "6fca5f0764a062b761563b2656b72007b0f5db9ffdd2576409e5188a9ad98280"
TEST_FILES = ("test_cases-1-26-24.csv", "test_case_37.csv")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def _run(*args: object) -> None:
    subprocess.run([str(arg) for arg in args], check=True, env={**os.environ, "PYTHONPATH": str(ROOT)})


def _script(name: str, *args: object) -> None:
    _run(sys.executable, HERE / f"{name}.py", *args)


def _pickle(source_root: Path, work: Path) -> Path:
    pickle = source_root / "dataset_granular_all.pkl"
    if not pickle.is_file():
        archive = next(p for p in (source_root / "data/dataset_granular_all.zip", source_root / "dataset_granular_all.zip") if p.is_file())
        with zipfile.ZipFile(archive) as bundle:
            bundle.extract("dataset_granular_all.pkl", work)
        pickle = work / "dataset_granular_all.pkl"
    digest = hashlib.sha256(pickle.read_bytes()).hexdigest()
    if digest != PICKLE_SHA256:
        raise ValueError(f"unexpected TIKTOC pickle {digest}; expected {PICKLE_SHA256}")
    return pickle


def build_codeworkout_benchmark(
    source_root: Path, output_root: Path, *, base_model: str, image: str = "zpdpatch-java:21", overwrite: bool = False
) -> dict[str, str]:
    if output_root.exists():
        if not overwrite:
            raise FileExistsError(f"Destination already exists: {output_root}. Use --overwrite to replace it.")
        shutil.rmtree(output_root)
    work = output_root / "work"
    work.mkdir(parents=True)
    pickle = _pickle(source_root.resolve(), work)
    # The pickle stores javalang objects, so the isolated export needs javalang on its path.
    _run(sys.executable, "-m", "pip", "install", "--quiet", "--target", work / "deps", "javalang==0.13.0")
    submissions = output_root / "submissions.jsonl"
    _run("bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
         "--bind", output_root.resolve(), output_root.resolve(), "--unshare-all", "--die-with-parent", "--new-session",
         "--setenv", "PYTHONPATH", (work / "deps").resolve(), sys.executable, HERE / "export_tiktoc_codeworkout.py",
         pickle.resolve(), submissions.resolve(), "--acknowledge-trusted-pickle")
    _script("prepare_codeworkout_java_sources", submissions, work / "java-sources")
    _script("compile_codeworkout_in_container", work / "java-sources", work / "compile-status", "--image", image)
    _script("collect_codeworkout_compile", submissions, work / "compile-status", output_root / "compile-cache.jsonl")
    _script("build_codeworkout_trajectories", submissions, output_root / "compile-cache.jsonl", output_root / "trajectories.jsonl",
            "--summary", output_root / "trajectory-summary.json", "--seed", 2027)
    filtered = output_root / "trajectories-4k.jsonl"
    _script("filter_codeworkout_trajectories", output_root / "trajectories.jsonl", filtered, "--base-model", base_model,
            "--max-total-tokens", 4096, "--seed", 2027, "--summary", output_root / "trajectory-4k-summary.json")
    _script("build_codeworkout_repair_datasets", filtered, output_root / "datasets")
    holdout = output_root / "problem-holdout"
    holdout.mkdir()
    _script("split_codeworkout_problems", filtered, holdout / "trajectories.jsonl", "--summary", holdout / "split-summary.json",
            "--seed", 2027)
    _script("build_codeworkout_repair_datasets", holdout / "trajectories.jsonl", holdout / "datasets", "--split-unit", "problem")
    paired = output_root / "paired-java-control"
    paired.mkdir()
    for split in ("train", "valid"):
        _script("build_paired_target_control", output_root / f"datasets/{split}-progress.jsonl", output_root / f"datasets/{split}-answer.jsonl",
                paired / f"{split}-progress.jsonl", paired / f"{split}-answer.jsonl", "--summary", paired / f"{split}.summary.json")
    _run(sys.executable, ROOT / "run.py", "make-current-code-only", output_root / "datasets/test-final.jsonl", paired / "test.jsonl")
    tests = output_root / "tests"
    tests.mkdir()
    for name in TEST_FILES:
        shutil.copyfile(source_root / "test-case-query-results" / name, tests / name)
    shutil.rmtree(work)
    return {"submissions": str(submissions), "datasets": str(output_root / "datasets"), "tests": str(tests)}
