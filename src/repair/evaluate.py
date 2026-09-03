from __future__ import annotations

import ast
import json
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from ..runner.dataset import load_testcases
from ..runner.python_runner import PythonSubmissionRunner


@dataclass(frozen=True)
class EvaluationSummary:
    method: str
    examples: int
    repaired: int
    improved: int
    repair_rate: float
    improvement_rate: float
    average_time_taken_sec: float
    mean_generation_time_sec: float
    mean_execution_time_sec: float
    mean_ted_buggy_fixed_on_repaired: float | None
    mean_ted_fixed_oracle_on_repaired: float | None
    parseable_repaired_for_buggy_fixed_ted: int
    parseable_repaired_for_fixed_oracle_ted: int
    output_path: Path


def evaluate_generations(
    data_root: Path,
    dataset_path: Path,
    generations_path: Path,
    output_path: Path,
    *,
    workers: int = 8,
    timeout_sec: float = 2.5,
    resume: bool = True,
    ted_workers: int | None = None,
    compute_tree_edit_distance: bool = True,
    baseline_reference_path: Path | None = None,
) -> EvaluationSummary:
    records = {item["example_id"]: item for item in _iter_jsonl(dataset_path)}
    generations = list(_iter_jsonl(generations_path))
    baseline_by_id = (
        {str(item["example_id"]): item for item in _iter_jsonl(baseline_reference_path)}
        if baseline_reference_path is not None
        else {}
    )
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generation_by_id = {
        str(generation["example_id"]): generation for generation in generations
    }
    if len(generation_by_id) != len(generations):
        raise ValueError(f"Duplicate example_id in generations: {generations_path}")
    if baseline_reference_path is not None and set(baseline_by_id) != set(records):
        raise ValueError("Baseline reference example IDs do not match the dataset")
    results = (
        _load_resumable_evaluations(output_path, generation_by_id)
        if resume and output_path.is_file()
        else []
    )
    completed_ids = {str(item["example_id"]) for item in results}
    pending_generations = [
        generation
        for generation in generations
        if str(generation["example_id"]) not in completed_ids
    ]
    runner = PythonSubmissionRunner(
        timeout_sec=timeout_sec,
        memory_limit_mb=2048,
    )

    def evaluate_one(generation: dict[str, Any]) -> dict[str, Any]:
        record = records[generation["example_id"]]
        problem_id = record["problem_id"]
        testcases = load_testcases(data_root / problem_id / "testcases.jsonl")
        buggy = record["history"][-1]
        buggy_code = str(buggy["code"])
        fixed_code = str(generation.get("generated_code", ""))
        oracle_code = str(record["target_code"])
        baseline = baseline_by_id.get(str(record["example_id"]))
        if baseline is None:
            buggy_started = time.perf_counter()
            buggy_outcome = runner.run_submission(
                submission_id=f"{record['example_id']}:buggy",
                problem_id=problem_id,
                code=buggy_code,
                source_verdict=str(buggy.get("verdict")),
                testcases=testcases,
            )
            buggy_execution_time = time.perf_counter() - buggy_started
            buggy_pass_rate = _pass_rate(buggy_outcome)
            buggy_verdict = buggy_outcome.verdict.value
        else:
            buggy_execution_time = 0.0
            buggy_pass_rate = float(baseline["buggy_pass_rate"])
            buggy_verdict = str(baseline["buggy_verdict"])
        fixed_started = time.perf_counter()
        fixed_outcome = runner.run_submission(
            submission_id=f"{record['example_id']}:fixed",
            problem_id=problem_id,
            code=fixed_code,
            source_verdict=None,
            testcases=testcases,
        )
        fixed_execution_time = time.perf_counter() - fixed_started
        fixed_pass_rate = _pass_rate(fixed_outcome)
        changed = fixed_code.strip() != buggy_code.strip()
        repaired = changed and fixed_pass_rate == 1.0
        return {
            **generation,
            "buggy_execution_time_sec": buggy_execution_time,
            "fixed_execution_time_sec": fixed_execution_time,
            "execution_time_sec": buggy_execution_time + fixed_execution_time,
            "online_time_sec": (
                float(generation.get("generation_time_sec", 0.0))
                + buggy_execution_time
                + fixed_execution_time
            ),
            "buggy_verdict": buggy_verdict,
            "fixed_verdict": fixed_outcome.verdict.value,
            "buggy_pass_rate": buggy_pass_rate,
            "fixed_pass_rate": fixed_pass_rate,
            "repaired": repaired,
            "improved": fixed_pass_rate > buggy_pass_rate,
            "ted_buggy_fixed": None,
            "ted_fixed_oracle": None,
            "tree_edit_distance": None,
            "fixed_tc_outcomes": {
                case.case_id: case.verdict.value for case in fixed_outcome.cases
            },
        }

    output_mode = "a" if resume and output_path.is_file() else "w"
    with output_path.open(output_mode, encoding="utf-8", buffering=1) as output:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(evaluate_one, item)
                for item in pending_generations
            ]
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Execute generated repairs",
                unit="repair",
            ):
                result = future.result()
                results.append(result)
                output.write(json.dumps(result, ensure_ascii=False) + "\n")
                output.flush()

    if compute_tree_edit_distance:
        _compute_repaired_ted(
            results,
            records,
            workers=workers if ted_workers is None else ted_workers,
        )
    results.sort(key=lambda item: item["example_id"])
    _rewrite_completed_evaluations(output_path, results)

    return _evaluation_summary(results, output_path)


def _compute_repaired_ted(
    results: list[dict[str, Any]],
    records: dict[str, dict[str, Any]],
    *,
    workers: int,
) -> None:
    repaired = [item for item in results if item.get("repaired")]
    if not repaired:
        return

    def arguments(item: dict[str, Any]) -> tuple[str, str, str]:
        record = records[str(item["example_id"])]
        return (
            str(record["history"][-1]["code"]),
            str(item.get("generated_code", "")),
            str(record["target_code"]),
        )

    if workers <= 1:
        computed = [
            _repaired_tree_edit_distances(*arguments(item))
            for item in repaired
        ]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_repaired_tree_edit_distances, *arguments(item))
                for item in repaired
            ]
            computed = [
                future.result()
                for future in tqdm(
                    futures,
                    total=len(futures),
                    desc="Compute TED on repaired programs",
                    unit="repair",
                )
            ]

    for item, (buggy_fixed, fixed_oracle) in zip(repaired, computed, strict=True):
        item["ted_buggy_fixed"] = buggy_fixed
        item["ted_fixed_oracle"] = fixed_oracle
        item["tree_edit_distance"] = buggy_fixed


def _repaired_tree_edit_distances(
    buggy_code: str,
    fixed_code: str,
    oracle_code: str,
) -> tuple[int | None, int | None]:
    return (
        tree_edit_distance(buggy_code, fixed_code),
        tree_edit_distance(fixed_code, oracle_code),
    )


def _load_resumable_evaluations(
    output_path: Path,
    generation_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    results = list(_iter_jsonl(output_path))
    completed_ids: set[str] = set()
    for result in results:
        example_id = str(result.get("example_id", ""))
        if not example_id or example_id in completed_ids:
            raise ValueError(
                f"Invalid or duplicate example_id in partial evaluation: {example_id!r}"
            )
        generation = generation_by_id.get(example_id)
        if generation is None:
            raise ValueError(
                f"Partial evaluation contains unknown example_id: {example_id}"
            )
        if str(result.get("generated_code", "")) != str(
            generation.get("generated_code", "")
        ):
            raise ValueError(
                f"Generated code changed for resumed example: {example_id}"
            )
        completed_ids.add(example_id)
    return results


def _rewrite_completed_evaluations(
    output_path: Path,
    results: list[dict[str, Any]],
) -> None:
    temporary_path = output_path.with_name(f".{output_path.name}.complete.tmp")
    with temporary_path.open("w", encoding="utf-8") as output:
        for item in results:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
        output.flush()
    temporary_path.replace(output_path)


def rescore_evaluations(
    dataset_path: Path,
    evaluations_path: Path,
    output_path: Path,
) -> EvaluationSummary:
    """Recompute metrics from stored outcomes without executing programs again."""

    records = {str(item["example_id"]): item for item in _iter_jsonl(dataset_path)}
    results: list[dict[str, Any]] = []
    for item in _iter_jsonl(evaluations_path):
        record = records[str(item["example_id"])]
        buggy_code = str(record["history"][-1]["code"])
        fixed_code = str(item.get("generated_code", ""))
        oracle_code = str(record["target_code"])
        buggy_pass_rate = float(item["buggy_pass_rate"])
        fixed_pass_rate = float(item["fixed_pass_rate"])
        repaired = (
            fixed_code.strip() != buggy_code.strip()
            and fixed_pass_rate == 1.0
        )
        ted_buggy_fixed = (
            tree_edit_distance(buggy_code, fixed_code) if repaired else None
        )
        ted_fixed_oracle = (
            tree_edit_distance(fixed_code, oracle_code) if repaired else None
        )
        results.append(
            {
                **item,
                "repaired": repaired,
                "improved": fixed_pass_rate > buggy_pass_rate,
                "ted_buggy_fixed": ted_buggy_fixed,
                "ted_fixed_oracle": ted_fixed_oracle,
                "tree_edit_distance": ted_buggy_fixed,
            }
        )
    results.sort(key=lambda item: str(item["example_id"]))
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output:
        for item in results:
            output.write(json.dumps(item, ensure_ascii=False) + "\n")
    return _evaluation_summary(results, output_path)


def tree_edit_distance(before: str, after: str) -> int | None:
    try:
        before_ast = ast.parse(before)
        after_ast = ast.parse(after)
    except (SyntaxError, ValueError, TypeError):
        return None
    try:
        return _apted_distance(before_ast, after_ast)
    except ImportError:
        try:
            return _zss_distance(before_ast, after_ast)
        except ImportError:
            return None


def _apted_distance(before_ast: ast.AST, after_ast: ast.AST) -> int:
    from apted import APTED, Config

    class AstConfig(Config):
        def children(self, node: ast.AST) -> list[ast.AST]:
            return list(ast.iter_child_nodes(node))

        def rename(self, left: ast.AST, right: ast.AST) -> int:
            return int(_ast_label(left) != _ast_label(right))

    return int(APTED(before_ast, after_ast, AstConfig()).compute_edit_distance())


def _zss_distance(before_ast: ast.AST, after_ast: ast.AST) -> int:
    from zss import Node, distance

    before_tree = _ast_to_zss(before_ast, Node)
    after_tree = _ast_to_zss(after_ast, Node)
    return int(
        distance(
            before_tree,
            after_tree,
            Node.get_children,
            insert_cost=lambda _node: 1,
            remove_cost=lambda _node: 1,
            update_cost=lambda left, right: int(left.label != right.label),
        )
    )


def budget_bounded_tree_edit_distance(
    before: str, after: str, *, maximum_budget: int
) -> int | None:
    """Return exact TED when needed, or a sound greater-than-budget sentinel."""
    if maximum_budget < 0:
        raise ValueError("maximum_budget must be non-negative")
    try:
        before_ast = ast.parse(before)
        after_ast = ast.parse(after)
    except (SyntaxError, ValueError, TypeError):
        return None
    before_nodes = sum(1 for _ in ast.walk(before_ast))
    after_nodes = sum(1 for _ in ast.walk(after_ast))
    # Unit-cost insertions and removals change the node count by at most one, so
    # the absolute count difference is a lower bound on exact tree edit distance.
    if abs(before_nodes - after_nodes) > maximum_budget:
        return maximum_budget + 1
    try:
        return _apted_distance(before_ast, after_ast)
    except ImportError:
        try:
            return _zss_distance(before_ast, after_ast)
        except ImportError:
            return None


def _ast_to_zss(node: ast.AST, node_type: Any) -> Any:
    root = node_type(_ast_label(node))
    for child in ast.iter_child_nodes(node):
        root.addkid(_ast_to_zss(child, node_type))
    return root


def _ast_label(node: ast.AST) -> str:
    label = node.__class__.__name__
    if isinstance(node, ast.Name):
        label += f":{node.id}"
    elif isinstance(node, ast.arg):
        label += f":{node.arg}"
    elif isinstance(node, ast.Constant):
        label += f":{node.value!r}"
    return label


def _pass_rate(outcome: Any) -> float:
    if not outcome.cases:
        return 0.0
    passed = sum(case.verdict.value == "AC" for case in outcome.cases)
    return passed / len(outcome.cases)


def _evaluation_summary(
    results: list[dict[str, Any]],
    output_path: Path,
) -> EvaluationSummary:
    repaired = sum(bool(item["repaired"]) for item in results)
    improved = sum(bool(item["improved"]) for item in results)
    elapsed = [float(item.get("generation_time_sec", 0.0)) for item in results]
    execution = [float(item.get("execution_time_sec", 0.0)) for item in results]
    online = _problem_level_online_times(results)
    repaired_buggy_fixed_distances = [
        float(item["ted_buggy_fixed"])
        for item in results
        if item.get("repaired") and item.get("ted_buggy_fixed") is not None
    ]
    repaired_fixed_oracle_distances = [
        float(item["ted_fixed_oracle"])
        for item in results
        if item.get("repaired") and item.get("ted_fixed_oracle") is not None
    ]
    method = str(results[0].get("method", "unknown")) if results else "unknown"
    summary = EvaluationSummary(
        method=method,
        examples=len(results),
        repaired=repaired,
        improved=improved,
        repair_rate=repaired / len(results) if results else 0.0,
        improvement_rate=improved / len(results) if results else 0.0,
        average_time_taken_sec=(
            sum(item["elapsed_sec"] for item in online)
            / sum(item["buggy_count"] for item in online)
            if online
            else 0.0
        ),
        mean_generation_time_sec=sum(elapsed) / len(elapsed) if elapsed else 0.0,
        mean_execution_time_sec=(
            sum(execution) / len(execution) if execution else 0.0
        ),
        mean_ted_buggy_fixed_on_repaired=(
            sum(repaired_buggy_fixed_distances)
            / len(repaired_buggy_fixed_distances)
            if repaired_buggy_fixed_distances
            else None
        ),
        mean_ted_fixed_oracle_on_repaired=(
            sum(repaired_fixed_oracle_distances)
            / len(repaired_fixed_oracle_distances)
            if repaired_fixed_oracle_distances
            else None
        ),
        parseable_repaired_for_buggy_fixed_ted=len(
            repaired_buggy_fixed_distances
        ),
        parseable_repaired_for_fixed_oracle_ted=len(
            repaired_fixed_oracle_distances
        ),
        output_path=output_path,
    )
    output_path.with_suffix(".summary.json").write_text(
        json.dumps(asdict(summary), indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return summary


def _problem_level_online_times(
    results: list[dict[str, Any]],
) -> list[dict[str, float | int | str]]:
    """Return one wall-clock timing per problem for ATT.

    RQ1 runners attach the same problem-level elapsed time and buggy count to
    every result from that problem. Legacy evaluation files fall back to one
    aggregate pseudo-problem so ATT remains readable without pretending that
    independently measured per-example times are problem wall-clock timings.
    """

    problem_times: dict[str, dict[str, float | int | str]] = {}
    for item in results:
        problem_id = str(item.get("problem_id", ""))
        elapsed = item.get("problem_repair_time_sec")
        buggy_count = item.get("problem_buggy_count")
        if elapsed is None or buggy_count is None:
            continue
        timing = {
            "problem_id": problem_id,
            "elapsed_sec": float(elapsed),
            "buggy_count": int(buggy_count),
        }
        previous = problem_times.get(problem_id)
        if previous is not None and previous != timing:
            raise ValueError(f"Inconsistent problem timing for {problem_id}")
        problem_times[problem_id] = timing
    if problem_times:
        return list(problem_times.values())

    elapsed = sum(
        float(
            item.get(
                "online_time_sec",
                float(item.get("generation_time_sec", 0.0))
                + float(item.get("execution_time_sec", 0.0)),
            )
        )
        for item in results
    )
    return [
        {
            "problem_id": "__legacy_aggregate__",
            "elapsed_sec": elapsed,
            "buggy_count": len(results),
        }
    ] if results else []


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.expanduser().open(encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)
