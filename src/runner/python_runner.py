from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

from .compare import outputs_match
from .models import CaseOutcome, SubmissionOutcome, TestCase, Verdict

_SUBPROCESS_RUNNER = r"""
import contextlib
import builtins
import io
import json
import sys
import time
import traceback

try:
    import fractions
    import math
    if not hasattr(fractions, "gcd"):
        fractions.gcd = math.gcd
except Exception:
    pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
        code = payload["code"]
        stdin_text = payload["stdin"]
        memory_limit_mb = int(payload.get("memory_limit_mb", 0))
    except Exception as exc:
        sys.stdout.write(json.dumps({
            "ok": False,
            "stdout": "",
            "stderr": f"runner payload error: {exc}",
            "runtime_sec": 0.0,
        }))
        return

    if sys.platform.startswith("linux") and memory_limit_mb > 0:
        try:
            import resource
            limit_bytes = memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
        except Exception as exc:
            sys.stdout.write(json.dumps({
                "ok": False,
                "stdout": "",
                "stderr": f"runner memory limit error: {exc}",
                "runtime_sec": 0.0,
            }))
            return

    stdin_bytes = stdin_text.encode()
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    old_stdin = sys.stdin
    old_open = builtins.open
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding="utf-8")

    def runner_open(file, mode="r", *args, **kwargs):
        if file == 0:
            if "b" in mode:
                return io.BytesIO(stdin_bytes)
            return io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding="utf-8")
        return old_open(file, mode, *args, **kwargs)

    builtins.open = runner_open
    started = time.perf_counter()
    ok = True
    try:
        compiled = compile(code, "<student_code>", "exec")
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exec(compiled, {"__name__": "__main__", "__builtins__": __builtins__})
    except SystemExit:
        pass
    except BaseException:
        ok = False
        traceback.print_exc(file=stderr_buffer)
    finally:
        runtime = time.perf_counter() - started
        sys.stdin = old_stdin
        builtins.open = old_open

    sys.stdout.write(json.dumps({
        "ok": ok,
        "stdout": stdout_buffer.getvalue(),
        "stderr": stderr_buffer.getvalue(),
        "runtime_sec": runtime,
    }))


if __name__ == "__main__":
    main()
"""


@dataclass(frozen=True)
class PythonSubmissionRunner:
    timeout_sec: float = 2.5
    memory_limit_mb: int = 512
    case_workers: int = 1

    def run_submission(
        self,
        *,
        submission_id: str,
        problem_id: str,
        code: str,
        source_verdict: str | None,
        testcases: list[TestCase],
    ) -> SubmissionOutcome:
        compile_error = self._compile_error(code)
        if compile_error is not None:
            cases = [
                CaseOutcome(case_id=tc.case_id, verdict=Verdict.CE, stderr=compile_error)
                for tc in testcases
            ]
            return SubmissionOutcome(
                submission_id=submission_id,
                problem_id=problem_id,
                language="python",
                source_verdict=source_verdict,
                verdict=Verdict.CE,
                cases=cases,
                compile_error=compile_error,
            )

        if self.case_workers > 1 and len(testcases) > 1:
            with ThreadPoolExecutor(
                max_workers=min(self.case_workers, len(testcases))
            ) as executor:
                cases = list(executor.map(partial(self.run_case, code), testcases))
        else:
            cases = [self.run_case(code, tc) for tc in testcases]
        return SubmissionOutcome(
            submission_id=submission_id,
            problem_id=problem_id,
            language="python",
            source_verdict=source_verdict,
            verdict=_overall_verdict(cases),
            cases=cases,
        )

    def run_case(self, code: str, testcase: TestCase) -> CaseOutcome:
        payload = json.dumps(
            {
                "code": code,
                "stdin": testcase.input_text,
                "memory_limit_mb": self.memory_limit_mb,
            },
            ensure_ascii=False,
        )
        started = time.perf_counter()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                completed = subprocess.run(
                    [sys.executable, "-c", _SUBPROCESS_RUNNER],
                    input=payload,
                    text=True,
                    capture_output=True,
                    timeout=self.timeout_sec,
                    check=False,
                    cwd=tmpdir,
                    env=_subprocess_environment(),
                )
        except subprocess.TimeoutExpired as exc:
            return CaseOutcome(
                case_id=testcase.case_id,
                verdict=Verdict.TLE,
                runtime_sec=self.timeout_sec,
                stdout=_text(exc.stdout or ""),
                stderr=_text(exc.stderr or ""),
            )

        wall_time = time.perf_counter() - started
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return CaseOutcome(
                case_id=testcase.case_id,
                verdict=Verdict.RE,
                runtime_sec=wall_time,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )

        stdout = str(response.get("stdout", ""))
        stderr = str(response.get("stderr", ""))
        runtime = float(response.get("runtime_sec") or wall_time)
        if completed.returncode != 0 or not response.get("ok", False):
            return CaseOutcome(
                case_id=testcase.case_id,
                verdict=Verdict.RE,
                runtime_sec=runtime,
                stdout=stdout,
                stderr=stderr or completed.stderr,
            )

        verdict = Verdict.AC if outputs_match(testcase.expected_text, stdout) else Verdict.WA
        return CaseOutcome(
            case_id=testcase.case_id,
            verdict=verdict,
            runtime_sec=runtime,
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _compile_error(code: str) -> str | None:
        try:
            compile(code, "<student_code>", "exec")
        except SyntaxError as exc:
            return f"{exc.__class__.__name__}: {exc}"
        return None


def _overall_verdict(cases: list[CaseOutcome]) -> Verdict:
    order = (Verdict.CE, Verdict.TLE, Verdict.RE, Verdict.WA)
    case_verdicts = {case.verdict for case in cases}
    for verdict in order:
        if verdict in case_verdicts:
            return verdict
    return Verdict.AC
def _text(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _subprocess_environment() -> dict[str, str]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "PYTHONPATH": "",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        environment["VIRTUAL_ENV"] = virtual_env
    return environment
