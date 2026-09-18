"""Development-only, fresh-output four-block execution label evaluator.

No legacy caches, ranking features, generation, or retries are used. Bubblewrap
isolates execution from project/data/home and network. It is not a full aggregate
resource-control system; use an isolated execution host. Every source-task
completion is durably recorded, including unknowns. The 2.5 s deadline includes
sandbox startup and is not directly identical to canonical benchmark execution.
"""
from __future__ import annotations

import argparse
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.repair.pilot_contracts import (CandidateAttempt, CandidateBank,
    ExecutionBlock, ExecutionVector, canonical_hash, compare_bank_candidate)
from src.runner.models import CaseOutcome, TestCase, Verdict
from src.runner.python_runner import _SUBPROCESS_RUNNER
from src.runner.compare import outputs_match

WORKERS = (1, 8, 8, 1)
LIMIT_SECONDS = 6 * 60 * 60
SYSTEM_PYTHON = "/usr/bin/python3"


def sandbox_command():
    command = ["/usr/bin/bwrap", "--unshare-net", "--unshare-pid", "--die-with-parent",
        "--new-session", "--cap-drop", "ALL", "--clearenv", "--setenv", "LANG", "C.UTF-8",
        "--setenv", "PATH", "/usr/bin:/bin"]
    for directory in ("/usr", "/lib", "/lib64"):
        if Path(directory).exists():
            command += ["--ro-bind", directory, directory]
    return command + ["--tmpfs", "/tmp", "--proc", "/proc", "--dev", "/dev",
        "--chdir", "/tmp", SYSTEM_PYTHON, "-I", "-c"]


class SandboxRunner:
    """No project/home/data mounts or network; fail closed without bubblewrap."""
    timeout_sec = 2.5
    memory_limit_mb = 2048
    case_workers = 1

    def run_case(self, code, testcase):
        started = time.monotonic()
        payload = json.dumps({"code": code, "stdin": testcase.input_text,
            "memory_limit_mb": self.memory_limit_mb})
        try:
            completed = subprocess.run(sandbox_command() + [_SUBPROCESS_RUNNER],
                input=payload, text=True, capture_output=True, timeout=self.timeout_sec,
                check=False)
        except subprocess.TimeoutExpired:
            return CaseOutcome(testcase.case_id, Verdict.TLE, self.timeout_sec)
        try:
            response = json.loads(completed.stdout)
        except (ValueError, TypeError):
            raise RuntimeError("sandbox/runner produced no valid JSON: " + completed.stderr[:1000])
        if completed.returncode != 0 or not isinstance(response, dict):
            raise RuntimeError("sandbox/runner failed: " + completed.stderr[:1000])
        stdout, stderr = str(response.get("stdout", "")), str(response.get("stderr", ""))
        if response.get("ok") is True:
            verdict = Verdict.AC if outputs_match(testcase.expected_text, stdout) else Verdict.WA
        else:
            verdict = Verdict.CE if "SyntaxError:" in stderr or "IndentationError:" in stderr else Verdict.RE
        return CaseOutcome(testcase.case_id, verdict, time.monotonic() - started, stdout, stderr)


def sandbox_preflight():
    probe = "import os,sys; assert not os.path.exists('/home'); assert not os.path.exists('/Users'); print(sys.version)"
    result = subprocess.run(sandbox_command() + [probe], capture_output=True,
        text=True, timeout=10, check=True)
    return result.stdout.strip()


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_row(handle, value):
    handle.write(json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False) + "\n")
    handle.flush()
    os.fsync(handle.fileno())


def parse_bank(row):
    required = {"bank_id", "problem_id", "current_source", "generator_config_sha256", "seeds", "attempts"}
    if set(row) != required:
        raise ValueError("bank fields must match evaluator allowlist")
    if not isinstance(row["bank_id"], str) or not row["bank_id"]:
        raise ValueError("bank_id required")
    problem = row["problem_id"]
    if not isinstance(problem, str) or not problem or Path(problem).name != problem or problem in (".", ".."):
        raise ValueError("problem ID must be a single directory component")
    attempts = []
    for attempt in row["attempts"]:
        if set(attempt) != {"index", "seed", "status", "source", "error"}:
            raise ValueError("attempt allowlist violation")
        attempts.append(CandidateAttempt(**{**attempt, "source":
            None if attempt["source"] is None else attempt["source"].encode("utf-8")}))
    return CandidateBank(problem, row["current_source"].encode("utf-8"),
        row["generator_config_sha256"], tuple(row["seeds"]), tuple(attempts))


def load_cases(path):
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        values = [row[k] for k in ("case_id", "input", "expected_output")]
        if not all(isinstance(v, str) for v in values) or not values[0]:
            raise ValueError("testcases require string ID/input/expected_output")
        cases.append(TestCase(*values))
    if not cases or len({c.case_id for c in cases}) != len(cases):
        raise ValueError("testcase universe must be nonempty with unique IDs")
    return cases


def run_source(runner, source, cases, deadline, clock=time.monotonic):
    outcomes, details = [], []
    for case in cases:
        if clock() >= deadline:
            return outcomes, details, False
        try:
            result = runner.run_case(source.decode("utf-8"), case)
            verdict = str(result.verdict)
            stderr = result.stderr or ""
            # Existing runner folds infrastructure failures into RE. Do not turn
            # those into ordinary failed cases or supervised zero gain/loss.
            resource = any(s in stderr for s in ("MemoryError", "Cannot allocate memory",
                "runner memory limit error", "runner payload error", "No space left on device"))
            if result.case_id != case.case_id or resource or (verdict == "RE" and "Traceback (most recent call last)" not in stderr):
                verdict = "UNKNOWN"
            if verdict not in {"AC", "WA", "CE", "RE", "TLE"}:
                verdict = "UNKNOWN"
            outcomes.append((case.case_id, verdict))
            details.append({"case_id": case.case_id, "verdict": verdict,
                "runtime_sec": result.runtime_sec, "stderr": stderr})
        except Exception as exc:
            outcomes.append((case.case_id, "UNKNOWN"))
            details.append({"case_id": case.case_id, "verdict": "UNKNOWN",
                "error": f"{type(exc).__name__}: {exc}"})
    return outcomes, details, True


def evaluate(banks_path, testcases_root, output, *, runner_factory=None,
             clock=time.monotonic, max_seconds=LIMIT_SECONDS):
    if not 0 < max_seconds <= LIMIT_SECONDS:
        raise ValueError("wall-time budget must be positive and at most six hours")
    banks_path, testcases_root, output = map(Path, (banks_path, testcases_root, output))
    if output.exists():
        raise FileExistsError("output must be new; silent resume/re-execution is forbidden")
    rows = [json.loads(line) for line in banks_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or len({row["bank_id"] for row in rows}) != len(rows):
        raise ValueError("nonempty unique bank IDs required")
    banks = [(row["bank_id"], parse_bank(row)) for row in rows]
    by_key = {}
    for _, bank in banks:
        previous = by_key.setdefault(bank.key, bank.seal_sha256)
        if previous != bank.seal_sha256:
            raise ValueError("identical current/config key has conflicting banks")
    cases, universes, testcase_files = {}, {}, {}
    for problem in sorted({bank.problem_id for _, bank in banks}):
        path = testcases_root / problem / "testcases.jsonl"
        cases[problem] = load_cases(path)
        universes[problem] = canonical_hash([asdict(c) for c in cases[problem]])
        testcase_files[problem] = sha_file(path)
    sandbox_version = sandbox_preflight() if runner_factory is None else "fixture-only"
    config = {"timeout_sec": 2.5, "memory_limit_mb": 2048, "case_workers": 1,
        "block_workers": WORKERS, "python": sys.version, "platform": platform.platform(),
        "execution_python_version": sandbox_version,
        "sandbox_command": sandbox_command(),
        "executable_sha256": sha_file(SYSTEM_PYTHON if runner_factory is None else sys.executable),
        "implementation_sha256": {str(p.relative_to(ROOT)): sha_file(p) for p in
            (Path(__file__), ROOT / "src/runner/python_runner.py", ROOT / "src/runner/compare.py",
             ROOT / "src/runner/models.py", ROOT / "src/repair/pilot_contracts.py")},
        "injected_runner": runner_factory is not None}
    runtime_hash = canonical_hash(config)
    tasks = {}
    for _, bank in banks:
        for candidate in bank.candidates:
            tasks.setdefault((bank.problem_id, candidate.source_sha256), candidate.source)
    output.mkdir(parents=True)
    manifest = {"development_only": True, "banks_sha256": sha_file(banks_path),
        "bank_seals": {i: b.seal_sha256 for i, b in banks}, "runtime": config,
        "runtime_sha256": runtime_hash, "testcase_files_sha256": testcase_files,
        "universe_sha256": universes, "unique_sources": len(tasks), "max_seconds": max_seconds}
    with (output / "manifest.json").open("x") as handle:
        write_row(handle, manifest)
    blocks = {key: [] for key in tasks}
    deadline = clock() + max_seconds
    stopped = False
    factory = runner_factory or SandboxRunner
    with (output / "completions.jsonl").open("x") as journal:
        for block_index, workers in enumerate(WORKERS):
            pending, remaining = {}, iter(tasks)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                def submit_one():
                    if clock() >= deadline:
                        return False
                    key = next(remaining, None)
                    if key is None:
                        return False
                    pending[pool.submit(run_source, factory(), tasks[key], cases[key[0]], deadline, clock)] = key
                    return True
                for _ in range(workers):
                    submit_one()
                while pending:
                    done, _ = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        key = pending.pop(future)
                        outcomes, details, complete = future.result()
                        block = ExecutionBlock(workers, universes[key[0]], runtime_hash,
                            tuple(outcomes), complete, key[1])
                        blocks[key].append(block)
                        write_row(journal, {"problem_id": key[0], "source_sha256": key[1],
                            "block_index": block_index, "block": asdict(block), "cases": details})
                        submit_one()
            if any(len(v) != block_index + 1 or not v[-1].complete for v in blocks.values()):
                stopped = True
                break
    vectors = {key: ExecutionVector(key[1], universes[key[0]], runtime_hash,
        tuple(c.case_id for c in cases[key[0]]), tuple(value)) for key, value in blocks.items()}
    with (output / "labels.jsonl").open("x") as labels:
        for bank_id, bank in banks:
            current = vectors[(bank.problem_id, bank.candidates[0].candidate_id)]
            for candidate in bank.candidates:
                vector = vectors[(bank.problem_id, candidate.candidate_id)]
                evidence = compare_bank_candidate(bank, candidate.candidate_id, current, vector)
                n = len(current.testcase_ids)
                write_row(labels, {"bank_id": bank_id, "candidate_id": candidate.candidate_id,
                    "problem_id": bank.problem_id, "is_noop": candidate.is_noop,
                    "status": evidence.status, "gain": None if evidence.gained_testcases is None else len(evidence.gained_testcases)/n,
                    "loss": None if evidence.lost_testcases is None else len(evidence.lost_testcases)/n,
                    "all_ac": evidence.candidate_all_ac, "n_cases": n,
                    "evidence": asdict(evidence), "bank_seal_sha256": bank.seal_sha256})
    marker = "INCOMPLETE.json" if stopped else "COMPLETE.json"
    with (output / marker).open("x") as handle:
        write_row(handle, {"status": "time_budget_exhausted" if stopped else "fully_executed",
            "development_only": True, "files_sha256": {name: sha_file(output / name) for name in
                ("manifest.json", "completions.jsonl", "labels.jsonl")}})
    return not stopped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--banks", required=True, type=Path)
    parser.add_argument("--testcases-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return 0 if evaluate(args.banks, args.testcases_root, args.output) else 2


if __name__ == "__main__":
    raise SystemExit(main())
