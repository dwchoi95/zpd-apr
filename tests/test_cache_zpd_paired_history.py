"""Synthetic runners only: no submitted code, sandbox, model or private data."""
from concurrent.futures import Future
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts import cache_zpd_paired_history as cache
from src.runner.models import CaseOutcome, Verdict

RUNTIME = "a" * 64


def task(source="print('fixture')\n", *, indexes=(1, 3), problem="fixture"):
    cases = [dict(case_id=f"statement-sample:{problem}:{i}", input=f"  {i}\r\n\n",
                  expected_output=f"결과 {i}\n ") for i in indexes]
    pairs = [dict(index=i, input_hex=c["input"].encode().hex(),
                  output_hex=c["expected_output"].encode().hex()) for i, c in zip(indexes, cases)]
    return dict(problem_id=problem, source_sha256=cache.sha(source.encode()), language="Python",
                source=source, sample_set_sha256=cache.sha(cache.encoded(
                    dict(namespace="statement_sample_set_v1", samples=pairs))), cases=cases)


class FixtureRunner:
    timeout_sec, memory_limit_mb, case_workers = 2.5, 2048, 1

    def run_case(self, code, case):
        return CaseOutcome(case.case_id, Verdict.AC, 0.01, case.expected_text, "")


class ImmediateExecutor:
    """Fully synchronous fake also exercises callbacks on already-done futures."""
    workers = []

    def __init__(self, *, max_workers):
        self.workers.append(max_workers)

    def submit(self, fn, *args):
        future = Future()
        try:
            future.set_result(fn(*args))
        except BaseException as error:
            future.set_exception(error)
        return future

    def shutdown(self, **kwargs):
        pass


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "cache"
        ImmediateExecutor.workers = []

    def run_cache(self, rows=None, runner=FixtureRunner, guard=lambda: None, *, immediate=True):
        with patch.object(cache.evaluator, "SandboxRunner", runner):
            if immediate:
                with patch.object(cache, "ThreadPoolExecutor", ImmediateExecutor):
                    return cache.execute_cache([task()] if rows is None else rows, self.output,
                                               guard=guard, runtime_sha256=RUNTIME)
            return cache.execute_cache(rows, self.output, guard=guard, runtime_sha256=RUNTIME)

    def read(self, name):
        return json.loads((self.output / name).read_bytes())

    def rows(self, name):
        return [json.loads(row) for row in (self.output / name).read_bytes().splitlines()]

    def test_stable_full_verdicts_and_original_case_indices(self):
        observed = []

        class ExactRunner(FixtureRunner):
            def run_case(self, code, case):
                observed.append((code, case.case_id, case.input_text, case.expected_text))
                return CaseOutcome(case.case_id, Verdict.WA if case.case_id.endswith(":3") else Verdict.AC,
                                   0.01, "", "")

        row = task()
        report = self.run_cache([row], ExactRunner)
        self.assertEqual(ImmediateExecutor.workers, [1, 8, 8, 1])
        self.assertEqual(report["counts"]["completed_source_blocks"], 4)
        self.assertEqual(report["counts"]["completed_case_attempts"], 8)
        self.assertEqual(len(self.rows("completions.jsonl")), 4)
        self.assertEqual(len(self.rows("case-completions.jsonl")), 8)
        self.assertEqual(observed, [(row["source"], c["case_id"], c["input"], c["expected_output"])
                                    for _ in range(4) for c in row["cases"]])
        vectors = cache.load_vectors(report["vectors_path"], expected_sha256=report["vectors_sha256"],
                                     runtime_sha256=RUNTIME)
        vector = vectors[(row["problem_id"], row["source_sha256"], "Python")]
        self.assertEqual(vector.stable_outcomes, ("AC", "WA"))
        self.assertEqual(vector.universe_sha256, row["sample_set_sha256"])
        self.assertEqual(self.read("STATUS.json")["phase"], "complete")
        self.assertEqual(cache.sha((self.output / "COMPLETE.json").read_bytes()), report["complete_sha256"])

    def test_duplicate_identity_wrong_sha_types_and_extra_target_fail_before_execution(self):
        rows = [task(), task()]
        mutations = [lambda r: r.update(source_sha256="b" * 64),
                     lambda r: r.update(source=b"bytes"),
                     lambda r: r.update(language="C++"),
                     lambda r: r.update(target="private"),
                     lambda r: r["cases"][0].update(input=7)]
        bad = [rows]
        for mutate in mutations:
            row = task()
            mutate(row)
            bad.append([row])
        with patch.object(cache.evaluator.SandboxRunner, "run_case") as execute:
            for records in bad:
                with self.subTest(records=records), self.assertRaises((ValueError, TypeError)):
                    cache.execute_cache(records, self.output, guard=lambda: None, runtime_sha256=RUNTIME)
                self.assertFalse(self.output.exists())
            execute.assert_not_called()

    def test_case_hash_identity_order_duplicate_and_whitespace_validation(self):
        mutations = [lambda r: r.update(sample_set_sha256="b" * 64),
                     lambda r: r["cases"][0].update(input=r["cases"][0]["input"].strip()),
                     lambda r: r["cases"][0].update(case_id="statement-sample:other:1"),
                     lambda r: r["cases"][0].update(case_id="statement-sample:fixture:01"),
                     lambda r: r["cases"].reverse(),
                     lambda r: r["cases"].append(deepcopy(r["cases"][0]))]
        for mutate in mutations:
            row = task()
            mutate(row)
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.run_cache([row])
            self.assertFalse(self.output.exists())

    def test_same_source_different_problem_is_distinct_identity(self):
        report = self.run_cache([task(problem="first"), task(problem="second")])
        self.assertEqual(report["counts"]["unique_sources"], 2)
        self.assertEqual(len(self.read("vectors.json")["vectors"]), 2)

    def test_conflicting_universes_for_one_problem_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "one public universe"):
            self.run_cache([task(), task(source="other\n", indexes=(1,))])
        self.assertFalse(self.output.exists())

    def test_empty_suite_is_unavailable_not_vacuous_pass(self):
        report = self.run_cache([task(indexes=())])
        vector = next(iter(self.read("vectors.json")["vectors"].values()))
        self.assertEqual(vector["feedback_unavailable_reasons"], ["no_public_samples"])
        self.assertIsNone(vector["stable_verdicts"])
        self.assertEqual(report["counts"]["completed_source_blocks"], 0)
        values = cache.load_vectors(report["vectors_path"], expected_sha256=report["vectors_sha256"],
                                    runtime_sha256=RUNTIME)
        self.assertIsNone(next(iter(values.values())))

    def test_same_pass_mask_but_different_full_verdicts_is_unstable(self):
        calls = 0

        class DifferentRunner(FixtureRunner):
            def run_case(self, code, case):
                nonlocal calls
                calls += 1
                return CaseOutcome(case.case_id, Verdict.WA if calls == 1 else Verdict.CE)

        report = self.run_cache([task(indexes=(1,))], DifferentRunner)
        row = next(iter(self.read("vectors.json")["vectors"].values()))
        self.assertEqual(row["feedback_unavailable_reasons"], ["unstable_full_verdict_vector"])
        self.assertIsNone(row["ac_mask"])
        self.assertIsNone(next(iter(cache.load_vectors(report["vectors_path"],
            expected_sha256=report["vectors_sha256"], runtime_sha256=RUNTIME).values())).stable_outcomes)

    def test_runner_exception_malformed_identity_resource_and_ambiguous_re_are_unknown(self):
        responses = [RuntimeError("sandbox failed"),
                     CaseOutcome("wrong-case", Verdict.AC),
                     CaseOutcome("statement-sample:fixture:1", Verdict.RE, stderr="MemoryError"),
                     CaseOutcome("statement-sample:fixture:1", Verdict.RE, stderr="runner failed")]
        calls = []

        class UnknownRunner(FixtureRunner):
            def run_case(self, code, case):
                result = responses[len(calls)]
                calls.append(1)
                if isinstance(result, Exception):
                    raise result
                return result

        self.run_cache([task(indexes=(1,))], UnknownRunner)
        row = next(iter(self.read("vectors.json")["vectors"].values()))
        self.assertEqual(row["feedback_unavailable_reasons"], ["unknown_case"])
        self.assertTrue(all(b["outcomes"][0][1] == "UNKNOWN" for b in row["blocks"]))
        self.assertEqual(len(calls), 4)  # Never retry a failed attempt.
        self.assertIsNone(row["stable_verdicts"])

    def test_nonfinite_runner_diagnostics_become_unknown_without_nan_artifacts(self):
        class NonfiniteRunner(FixtureRunner):
            def run_case(self, code, case):
                return CaseOutcome(case.case_id, Verdict.AC, float("nan"))

        self.run_cache([task(indexes=(1,))], NonfiniteRunner)
        row = next(iter(self.read("vectors.json")["vectors"].values()))
        self.assertEqual(row["feedback_unavailable_reasons"], ["unknown_case"])
        self.assertIsNone(row["ac_mask"])
        self.assertNotIn(b"NaN", (self.output / "case-completions.jsonl").read_bytes())

    def test_caller_mutation_does_not_change_detached_execution_strings(self):
        row = task()
        original = deepcopy(row)
        observed = []

        class DetachedRunner(FixtureRunner):
            def run_case(self, code, case):
                observed.append((code, case.input_text))
                return super().run_case(code, case)

        def guard():
            row["source"] = "mutated after validation"
            row["cases"][0]["input"] = "mutated after validation"

        self.run_cache([row], DetachedRunner, guard)
        self.assertEqual(observed, [(original["source"], c["input"])
                                    for _ in range(4) for c in original["cases"]])

    def test_per_case_status_updates_before_source_finishes(self):
        observed = []

        class ObserveRunner(FixtureRunner):
            def run_case(inner, code, case):
                status = self.read("STATUS.json")
                observed.append(status["completed_case_attempts"])
                return super().run_case(code, case)

        self.run_cache(runner=ObserveRunner)
        self.assertEqual(observed, list(range(8)))

    def test_future_callback_persists_before_scheduler_wait(self):
        observed = []
        real_wait = cache.wait

        def wait_after_callback(pending, **kwargs):
            observed.append(self.read("STATUS.json")["completed_source_blocks"])
            return real_wait(pending, **kwargs)

        with patch.object(cache, "wait", wait_after_callback):
            self.run_cache()
        self.assertEqual(observed, [1, 2, 3, 4])

    def test_guard_failure_preserves_completed_cases_partial_block_and_failed_marker(self):
        attempts = []

        class OneRunner(FixtureRunner):
            def run_case(inner, code, case):
                attempts.append(case.case_id)
                return super().run_case(code, case)

        def guard():
            if attempts:
                raise RuntimeError("envelope breached")

        with self.assertRaisesRegex(RuntimeError, "envelope breached"):
            self.run_cache(runner=OneRunner, guard=guard)
        self.assertEqual(len(attempts), 1)
        self.assertFalse((self.output / "COMPLETE.json").exists())
        self.assertTrue((self.output / "FAILED.json").exists())
        self.assertEqual(self.read("STATUS.json")["phase"], "failed")
        self.assertEqual(len(self.rows("case-completions.jsonl")), 1)
        partial = self.rows("completions.jsonl")
        self.assertEqual(len(partial), 1)
        self.assertFalse(partial[0]["block"]["complete"])

    def test_late_guard_failure_never_leaves_complete(self):
        def guard():
            if (self.output / "vectors.json").exists():
                raise RuntimeError("late envelope failure")

        with self.assertRaisesRegex(RuntimeError, "late envelope failure"):
            self.run_cache(guard=guard)
        self.assertEqual(self.read("FAILED.json")["partial_coverage"]["completed_source_blocks"], 4)
        self.assertTrue((self.output / "vectors.json").exists())
        self.assertFalse((self.output / "COMPLETE.json").exists())
        with self.assertRaisesRegex(ValueError, "failed cache"):
            cache.load_vectors(self.output / "vectors.json", expected_sha256="b" * 64,
                               runtime_sha256=RUNTIME)

    def test_guard_false_rejects_before_any_case_attempt(self):
        with self.assertRaisesRegex(ValueError, "caller guard rejected"):
            self.run_cache(guard=lambda: False)
        self.assertEqual(self.read("FAILED.json")["partial_coverage"]["completed_case_attempts"], 0)
        self.assertEqual(self.rows("completions.jsonl"), [])

    def test_late_complete_write_failure_demotes_terminal_bytes(self):
        write = cache._write

        def late_failure(path, value, **kwargs):
            result = write(path, value, **kwargs)
            if path.name == "COMPLETE.json":
                raise OSError("simulated fsync failure after bytes appeared")
            return result

        with patch.object(cache, "_write", late_failure), self.assertRaises(OSError):
            self.run_cache()
        self.assertFalse((self.output / "COMPLETE.json").exists())
        self.assertTrue((self.output / "REJECTED_COMPLETE.json").exists())
        self.assertTrue((self.output / "FAILED.json").exists())

    def test_no_overwrite_or_resume_even_dangling_symlink(self):
        report = self.run_cache()
        before = (self.output / "COMPLETE.json").read_bytes()
        with self.assertRaises(FileExistsError):
            self.run_cache()
        self.assertEqual((self.output / "COMPLETE.json").read_bytes(), before)
        self.assertEqual(cache.sha(before), report["complete_sha256"])
        alias = Path(self.tmp.name) / "dangling"
        alias.symlink_to(Path(self.tmp.name) / "nonexistent")
        with self.assertRaises(FileExistsError):
            cache.execute_cache([task()], alias, guard=lambda: None, runtime_sha256=RUNTIME)

    def test_incomplete_run_source_never_seals(self):
        with patch.object(cache.evaluator, "run_source", return_value=([], [], False)):
            with self.assertRaisesRegex(ValueError, "incomplete source block"):
                self.run_cache()
        self.assertFalse((self.output / "COMPLETE.json").exists())
        self.assertTrue((self.output / "FAILED.json").exists())

    def test_core_deadline_is_twelve_hours_and_fail_closed(self):
        with patch.object(cache.time, "monotonic", side_effect=[0, 0, cache.SECONDS + 1,
                                                               cache.SECONDS + 1, cache.SECONDS + 1,
                                                               cache.SECONDS + 1]):
            with self.assertRaisesRegex(ValueError, "twelve-hour"):
                self.run_cache()
        self.assertEqual(cache.SECONDS, 43200)
        self.assertTrue((self.output / "FAILED.json").exists())
        self.assertFalse((self.output / "COMPLETE.json").exists())

    def test_sealed_artifact_drift_and_wrong_runtime_are_rejected(self):
        report = self.run_cache()
        with self.assertRaisesRegex(ValueError, "completion seal"):
            cache.load_vectors(report["vectors_path"], expected_sha256=report["vectors_sha256"],
                               runtime_sha256="b" * 64)
        (self.output / "completions.jsonl").write_bytes(b"tamper\n")
        with self.assertRaisesRegex(ValueError, "artifact SHA"):
            cache.load_vectors(report["vectors_path"], expected_sha256=report["vectors_sha256"],
                               runtime_sha256=RUNTIME)

    def test_concurrent_callbacks_track_every_completion(self):
        rows = [task(source=f"fixture_{i}\n") for i in range(12)]
        lock, completed = threading.Lock(), []

        class ConcurrentRunner(FixtureRunner):
            def run_case(inner, code, case):
                with lock:
                    completed.append((code, case.case_id))
                return super().run_case(code, case)

        report = self.run_cache(rows, ConcurrentRunner, immediate=False)
        self.assertEqual(len(completed), 96)
        self.assertEqual(report["counts"]["completed_source_blocks"], 48)
        self.assertEqual(report["counts"]["completed_case_attempts"], 96)
        unique = {(r["execution_id"], r["block_index"]) for r in self.rows("completions.jsonl")}
        self.assertEqual(len(unique), 48)


if __name__ == "__main__":
    unittest.main()
