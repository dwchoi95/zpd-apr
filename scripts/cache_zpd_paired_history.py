"""Public-only, four-block source feedback cache for a separately released host.

The caller authenticates and detaches tasks before entry, enforces the OS/cgroup
envelope, and verifies child cleanup after return. ``guard()`` must raise (or
return False) on an envelope/deadline violation. This module has no dataset
loader, targets, CLI execution path, retries, or production runner override.
It reuses the unchanged SandboxRunner/run_source; its /tmp is sandbox tmpfs,
and this worker creates no host temporary files outside its new output folder.
"""
from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time

from scripts import zpd_repair_evaluate as evaluator
from src.repair.pilot_contracts import ExecutionBlock, ExecutionVector
from src.runner.models import CaseOutcome, TestCase

VERSION = "paired_history_public_cache_v1"
WORKERS = (1, 8, 8, 1)
SECONDS = 12 * 60 * 60
KNOWN = frozenset(("AC", "WA", "CE", "RE", "TLE"))
ARTIFACTS = ("manifest.json", "tasks.json", "case-completions.jsonl",
             "completions.jsonl", "vectors.json", "STATUS.json")


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def _is_sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def source_key(problem_id, source_sha256, language="Python"):
    """Filesystem-independent key; the full identity is also kept in each row."""
    require(type(problem_id) is str and bool(problem_id), "problem ID required")
    require(_is_sha(source_sha256) and language == "Python", "Python source identity required")
    return sha(encoded([problem_id, source_sha256, language]))


@dataclass(frozen=True)
class _Task:
    problem_id: str
    source_sha256: str
    language: str
    source: bytes
    sample_set_sha256: str
    cases: tuple[TestCase, ...]

    @property
    def identity(self):
        return self.problem_id, self.source_sha256, self.language

    @property
    def key(self):
        return source_key(*self.identity)

    def ledger(self):
        return dict(identity=list(self.identity), source_sha256=self.source_sha256,
                    sample_set_sha256=self.sample_set_sha256,
                    case_ids=[c.case_id for c in self.cases])


def _tasks(rows):
    require(type(rows) in (list, tuple) and bool(rows), "nonempty detached task sequence required")
    result, seen, suites = [], set(), {}
    fields = {"problem_id", "source_sha256", "language", "source", "sample_set_sha256", "cases"}
    for row in rows:
        require(type(row) is dict and set(row) == fields, "exact public task schema required")
        require(type(row["source"]) is str, "source must be an exact UTF-8 string")
        raw = row["source"].encode("utf-8", errors="strict")
        require(sha(raw) == row["source_sha256"], "source SHA differs")
        require(type(row["language"]) is str and row["language"] == "Python", "Python only")
        key = source_key(row["problem_id"], row["source_sha256"], row["language"])
        require(key not in seen, "duplicate source identity")
        require(_is_sha(row["sample_set_sha256"]), "sample set SHA required")
        require(type(row["cases"]) is list, "ordered public cases list required")
        cases, pairs, previous = [], [], 0
        prefix = f"statement-sample:{row['problem_id']}:"
        for case in row["cases"]:
            require(type(case) is dict and set(case) == {"case_id", "input", "expected_output"},
                    "exact public case schema required")
            require(all(type(v) is str for v in case.values()), "exact case strings required")
            identity = case["case_id"]
            require(identity.startswith(prefix), "case problem identity differs")
            suffix = identity[len(prefix):]
            require(re.fullmatch(r"[1-9][0-9]*", suffix) is not None, "canonical positive case index required")
            index = int(suffix)
            require(index > previous, "case indices must be sorted and unique")
            previous = index
            pairs.append(dict(index=index, input_hex=case["input"].encode("utf-8").hex(),
                              output_hex=case["expected_output"].encode("utf-8").hex()))
            cases.append(TestCase(identity, case["input"], case["expected_output"]))
        digest = sha(encoded(dict(namespace="statement_sample_set_v1", samples=pairs)))
        require(digest == row["sample_set_sha256"], "public case bytes or sample set SHA differ")
        require(suites.setdefault(row["problem_id"], digest) == digest, "one public universe per problem required")
        result.append(_Task(row["problem_id"], row["source_sha256"], row["language"],
                            raw, digest, tuple(cases)))
        seen.add(key)
    return tuple(result)


def _diagnostic(value):
    require(type(value) is str, "diagnostic string required")
    return dict(excerpt=value[:1024], characters=len(value),
                json_string_sha256=sha(encoded(value)), truncated=len(value) > 1024)


def _write(path, value, *, replace=False):
    data = encoded(value) + b"\n"
    target = path.with_name(path.name + ".partial") if replace else path
    with target.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    if replace:
        os.replace(target, path)
    return sha(data)


def _append(handle, value):
    handle.write(encoded(value) + b"\n")
    handle.flush()
    os.fsync(handle.fileno())


class _State:
    """Serialize completion persistence, without buffering behind slow futures."""
    def __init__(self, tasks, output, guard, runtime_sha256):
        self.tasks, self.output, self.guard = tasks, output, guard
        self.runtime_sha256 = runtime_sha256
        self.started = time.monotonic()
        self.deadline = self.started + SECONDS
        self.lock, self.guard_lock = threading.RLock(), threading.Lock()
        self.cancelled = threading.Event()
        self.error = None
        self.blocks = {t.key: {} for t in tasks}
        self.case_attempts = 0
        self.completed_blocks = self.terminal_blocks = self.journaled_cases = 0
        self.unique_sources = len(tasks)
        self.unavailable_sources = sum(not t.cases for t in tasks)
        self.planned_blocks = 4 * (self.unique_sources - self.unavailable_sources)
        self.planned_cases = 4 * sum(len(t.cases) for t in tasks)
        self.case_journal = self.block_journal = None
        self.current_block = None

    def fail(self, error):
        with self.lock:
            if self.error is None:
                self.error = error
            self.cancelled.set()

    def check(self):
        if self.error is not None:
            raise self.error
        try:
            require(time.monotonic() < self.deadline, "twelve-hour cache deadline exceeded")
            with self.guard_lock:
                require(self.guard() is not False, "caller guard rejected execution")
            require(time.monotonic() < self.deadline, "twelve-hour cache deadline exceeded")
        except BaseException as error:
            self.fail(error)
            raise
        if self.error is not None:
            raise self.error

    def execution_clock(self):
        if self.cancelled.is_set():
            return self.deadline
        try:
            self.check()
        except BaseException:
            return self.deadline
        return time.monotonic()

    def status(self, phase):
        return dict(phase=phase, current_block=self.current_block,
                    elapsed_seconds=time.monotonic() - self.started,
                    completed_source_blocks=self.completed_blocks,
                    terminal_source_blocks=self.terminal_blocks,
                    planned_source_blocks=self.planned_blocks,
                    completed_case_attempts=self.case_attempts,
                    journaled_case_attempts=self.journaled_cases,
                    planned_case_attempts=self.planned_cases,
                    unique_sources=self.unique_sources,
                    unavailable_unique_sources=self.unavailable_sources)

    def write_status(self, phase="running"):
        return _write(self.output / "STATUS.json", self.status(phase), replace=True)

    def case_completed(self, task, index, case, result, error):
        with self.lock:
            try:
                value = dict(execution_id=task.key, identity=list(task.identity),
                             block_index=index, case_id=case.case_id)
                if error is not None:
                    value["error"] = _diagnostic(f"{type(error).__name__}: {error}")
                else:
                    value.update(observed_case_id=result.case_id, raw_verdict=str(result.verdict),
                                 runtime_sec=result.runtime_sec, stderr=_diagnostic(result.stderr))
                _append(self.case_journal, value)
                self.case_attempts += 1
                self.write_status()
            except BaseException as failure:
                self.fail(failure)

    def source_completed(self, task, index, future, finished):
        try:
            value = future.result()
            with self.lock:
                require(index not in self.blocks[task.key], "duplicate source block completion")
                _append(self.block_journal, value)
                self.blocks[task.key][index] = value
                self.terminal_blocks += 1
                self.completed_blocks += value["block"]["complete"]
                self.journaled_cases += len(value["block"]["outcomes"])
                self.write_status()
                require(value["block"]["complete"], "incomplete source block")
        except BaseException as error:
            self.fail(error)
        finally:
            finished.set()


class _CheckedRunner:
    def __init__(self, delegate, task, index, state):
        self.delegate, self.task, self.index, self.state = delegate, task, index, state

    def run_case(self, code, case):
        result, error = None, None
        try:
            result = self.delegate.run_case(code, case)
            require(isinstance(result, CaseOutcome) and type(result.case_id) is str
                    and type(result.stdout) is str and type(result.stderr) is str
                    and type(result.runtime_sec) in (int, float)
                    and math.isfinite(result.runtime_sec) and result.runtime_sec >= 0,
                    "malformed or nonfinite runner response")
            return result
        except BaseException as failure:
            error = failure
            raise
        finally:
            self.state.case_completed(self.task, self.index, case, result, error)


def _run_block(task, index, state):
    runner = _CheckedRunner(evaluator.SandboxRunner(), task, index, state)
    outcomes, details, complete = evaluator.run_source(
        runner, task.source, task.cases, state.deadline, state.execution_clock)
    require([c for c, _ in outcomes] == [c.case_id for c in task.cases[:len(outcomes)]],
            "ordered case execution identity differs")
    require(not complete or len(outcomes) == len(task.cases), "complete source block lacks cases")
    for detail in details:
        for name in ("stderr", "error"):
            if name in detail:
                detail[name] = _diagnostic(detail[name])
    block = ExecutionBlock(WORKERS[index], task.sample_set_sha256, state.runtime_sha256,
                           tuple(outcomes), complete, task.source_sha256)
    return dict(execution_id=task.key, identity=list(task.identity), block_index=index,
                block=asdict(block), cases=details)


def _vector(task, records, runtime_sha256):
    ordered = [records[i]["block"] for i in sorted(records)]
    blocks = tuple(ExecutionBlock(b["workers"], b["universe_sha256"], b["runtime_sha256"],
                                 tuple(tuple(p) for p in b["outcomes"]), b["complete"], b["source_sha256"])
                   for b in ordered)
    stable, reasons = None, []
    if not task.cases:
        reasons.append("no_public_samples")
    else:
        contract = ExecutionVector(task.source_sha256, task.sample_set_sha256, runtime_sha256,
                                   tuple(c.case_id for c in task.cases), blocks)
        stable = contract.stable_outcomes
        if len(blocks) != 4 or not all(b.complete for b in blocks):
            reasons.append("incomplete_four_blocks")
        elif any(v not in KNOWN for b in blocks for _, v in b.outcomes):
            reasons.append("unknown_case")
        elif stable is None:
            reasons.append("unstable_full_verdict_vector")
    return dict(**task.ledger(), runtime_sha256=runtime_sha256, blocks=ordered,
                stable_verdicts=None if stable is None else list(stable),
                ac_mask=None if stable is None else [v == "AC" for v in stable],
                feedback_unavailable_reasons=reasons)


def execute_cache(tasks, output, *, guard, runtime_sha256):
    """Create a new sealed cache; any failed/incomplete run raises with evidence.

    Task fields are problem_id/source_sha256/language/source/sample_set_sha256/
    cases. ``source`` and case input/output are exact strings. Case IDs use the
    frozen ``statement-sample:{problem_id}:{original_positive_index}`` contract;
    sorted indices may have gaps. Empty sample suites remain unavailable.
    No completion is authorization for fitting or substitutes for host cleanup.
    """
    require(callable(guard), "caller OS envelope/deadline guard required")
    require(_is_sha(runtime_sha256), "externally authenticated runtime SHA required")
    frozen = _tasks(tasks)
    require((evaluator.SandboxRunner.timeout_sec, evaluator.SandboxRunner.memory_limit_mb,
             evaluator.SandboxRunner.case_workers) == (2.5, 2048, 1), "unchanged SandboxRunner limits required")
    output = Path(output).absolute()
    # mkdir itself is the exclusive check, including dangling symlinks/races.
    output.mkdir(parents=True, exist_ok=False)
    state = _State(frozen, output, guard, runtime_sha256)
    pool = None
    expected = {}
    try:
        expected["manifest.json"] = _write(output / "manifest.json", dict(
            schema_version=VERSION, runtime_sha256=runtime_sha256, block_workers=list(WORKERS),
            timeout_sec=2.5, memory_limit_mb=2048, case_workers=1, max_seconds=SECONDS,
            tasks_sha256=sha(encoded(tasks)), public_only=True, retries=0,
            host_cleanup_verification_required=True, fitting_authorized=False))
        expected["tasks.json"] = _write(output / "tasks.json", {t.key: t.ledger() for t in frozen})
        _write(output / "STATUS.json", state.status("starting"))
        with (output / "case-completions.jsonl").open("xb") as cases, (output / "completions.jsonl").open("xb") as journal:
            state.case_journal, state.block_journal = cases, journal
            eligible = tuple(t for t in frozen if t.cases)
            for index, workers in enumerate(WORKERS):
                state.check()
                state.current_block = index
                remaining, pending = iter(eligible), {}
                pool = ThreadPoolExecutor(max_workers=workers)

                def submit_one():
                    state.check()
                    task = next(remaining, None)
                    if task is None:
                        return
                    finished = threading.Event()
                    future = pool.submit(_run_block, task, index, state)
                    pending[future] = finished
                    future.add_done_callback(lambda f, t=task, i=index, done=finished:
                                             state.source_completed(t, i, f, done))

                try:
                    for _ in range(workers):
                        submit_one()
                    while pending:
                        state.check()
                        done, _ = wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)
                        for future in done:
                            # Future.done precedes its callbacks: wait for its
                            # immediate durable journal/status callback as well.
                            pending.pop(future).wait()
                            state.check()
                            submit_one()
                except BaseException as error:
                    state.fail(error)
                    raise
                finally:
                    # No new cases start after cancellation. Existing sandbox
                    # calls have the unchanged 2.5s timeout; the host owns reaping.
                    if state.error is not None:
                        state.cancelled.set()
                    pool.shutdown(wait=True, cancel_futures=True)
                    pool = None
                state.check()
            with state.lock:
                final_status = state.status("complete")
                require(final_status["completed_source_blocks"] == final_status["planned_source_blocks"],
                        "not every source block completed")
                require(final_status["completed_case_attempts"] == final_status["journaled_case_attempts"]
                        == final_status["planned_case_attempts"], "not every case attempt journaled")
        vectors = {t.key: _vector(t, state.blocks[t.key], runtime_sha256) for t in frozen}
        expected["vectors.json"] = _write(output / "vectors.json", dict(schema_version=VERSION,
            runtime_sha256=runtime_sha256, usable_only_with_valid_terminal_COMPLETE=True, vectors=vectors))
        expected["STATUS.json"] = state.write_status("complete")
        for name in ("case-completions.jsonl", "completions.jsonl"):
            expected[name] = sha((output / name).read_bytes())
        state.check()
        require(set(p.name for p in output.iterdir()) == set(ARTIFACTS), "unexpected output inventory")
        require(all(sha((output / n).read_bytes()) == h for n, h in expected.items()), "cache output drift")
        state.check()
        report = dict(status="complete", schema_version=VERSION, runtime_sha256=runtime_sha256,
                      files_sha256=expected, counts=final_status, fitting_authorized=False,
                      host_cleanup_verification_required=True)
        complete_sha = _write(output / "COMPLETE.json", report)
        return dict(report, vectors_path=str(output / "vectors.json"),
                    vectors_sha256=expected["vectors.json"], complete_sha256=complete_sha)
    except BaseException as error:
        state.fail(error)
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        marker = output / "COMPLETE.json"
        if marker.exists():
            marker.rename(output / "REJECTED_COMPLETE.json")
        with state.lock:
            _write(output / "FAILED.json", dict(status="failed", error_type=type(error).__name__,
                error=_diagnostic(str(error)), partial_coverage=state.status("failed"),
                feedback_available=False, fitting_authorized=False,
                host_cleanup_verification_required=True))
            try:
                state.write_status("failed")
            except OSError:
                # A failed atomic write can leave STATUS.json.partial. Preserve
                # that evidence; FAILED still makes the cache unusable.
                pass
        raise


def load_vectors(path, *, expected_sha256, runtime_sha256):
    """Reconstruct exact contracts after checking the caller-pinned cache seal.

    The caller must additionally authenticate the release and OS cleanup. None
    denotes an unavailable sample suite; unstable/UNKNOWN contracts retain all
    blocks and naturally have ``stable_outcomes is None``.
    """
    path = Path(path)
    require(path.name == "vectors.json" and _is_sha(expected_sha256) and _is_sha(runtime_sha256),
            "pinned vectors path/runtime required")
    require(not (path.parent / "FAILED.json").exists(), "failed cache is unavailable")
    seal = json.loads((path.parent / "COMPLETE.json").read_bytes())
    require(seal["status"] == "complete" and seal["schema_version"] == VERSION
            and seal["runtime_sha256"] == runtime_sha256
            and set(seal["files_sha256"]) == set(ARTIFACTS), "cache completion seal differs")
    require(seal["files_sha256"][path.name] == expected_sha256, "vector pin differs from completion")
    require(all(sha((path.parent / n).read_bytes()) == digest
                for n, digest in seal["files_sha256"].items()), "sealed cache artifact SHA differs")
    raw = path.read_bytes()
    require(sha(raw) == expected_sha256, "vector artifact SHA differs")
    body = json.loads(raw)
    require(body["schema_version"] == VERSION and body["runtime_sha256"] == runtime_sha256
            and body["usable_only_with_valid_terminal_COMPLETE"] is True, "vector runtime/schema differs")
    result = {}
    for key, row in body["vectors"].items():
        identity = tuple(row["identity"])
        require(len(identity) == 3 and source_key(*identity) == key and identity not in result,
                "vector source identity differs")
        require(row["source_sha256"] == identity[1] and row["runtime_sha256"] == runtime_sha256,
                "vector source/runtime differs")
        blocks = tuple(ExecutionBlock(b["workers"], b["universe_sha256"], b["runtime_sha256"],
                       tuple(tuple(p) for p in b["outcomes"]), b["complete"], b["source_sha256"])
                       for b in row["blocks"])
        if row["case_ids"]:
            vector = ExecutionVector(identity[1], row["sample_set_sha256"], runtime_sha256,
                                     tuple(row["case_ids"]), blocks)
            require(len(blocks) == 4 and all(b.complete for b in blocks), "sealed vector is incomplete")
            require(all(tuple(k for k, _ in b.outcomes) == vector.testcase_ids for b in blocks),
                    "vector exact ordered case identity differs")
            stable = vector.stable_outcomes
        else:
            require(not blocks, "unavailable suite has execution blocks")
            vector, stable = None, None
        require(row["stable_verdicts"] == (None if stable is None else list(stable))
                and row["ac_mask"] == (None if stable is None else [v == "AC" for v in stable]),
                "cached stable vector summary differs")
        result[identity] = vector
    return result


if __name__ == "__main__":
    raise SystemExit("A separately released and resource-enforced host must call execute_cache.")
