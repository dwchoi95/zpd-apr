"""One selected-only private replay after the caller seals all arm choices.

This module does not authenticate the caller's prediction seal, release, source
snapshot, or aggregate cgroup. The outer controller must do those checks before
entry and after normal exit. No old labels, unselected candidates, generation,
fitting, retries, or historical fourteen-method gates are used here.
"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time

from scripts import zpd_repair_evaluate as evaluator
from src.repair.pilot_contracts import (
    ExecutionBlock, ExecutionVector, canonical_hash, compare_execution,
)
from src.runner.models import TestCase

VERSION = 'transition_selected_private_v1'
ARMS = ('C', 'H', 'HS', 'U')
METHODS = (*ARMS, 'noop')
WORKERS = (1, 8, 8, 1)
EXAMPLES = 320
MAX_SECONDS = 21600
METRICS = ('ac_lower', 'ac_upper', 'regression_lower', 'regression_upper')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode() + b'\n'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, value):
    raw = encoded(value)
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return sha(raw)


def _status(output, value):
    temporary = output / 'STATUS.partial'
    write_new(temporary, value)
    temporary.replace(output / 'STATUS.json')


def _validate(recipients, predictions, testcase_pins):
    """Detach and validate the complete source-bound inventory before any I/O."""
    require(type(recipients) is list and len(recipients) == EXAMPLES,
            'exact fixed 320 recipient population required')
    require(type(predictions) is list and len(predictions) == EXAMPLES * len(ARMS),
            'exact 1280 sealed arm predictions required')
    by_example, folds, tasks = {}, {}, {}
    for row in recipients:
        require(type(row) is dict and set(row) == {
            'example_id', 'problem_id', 'current_source', 'fold'},
            'strict recipient fields required')
        eid, pid = row['example_id'], row['problem_id']
        require(type(eid) is str and bool(eid) and eid not in by_example,
                'unique nonempty example IDs required')
        require(type(pid) is str and re.fullmatch(r'[A-Za-z0-9_-]+', pid),
                'problem ID must be a safe single directory component')
        require(type(row['fold']) is int and row['fold'] in range(5),
                'integer five-fold membership required')
        require(folds.setdefault(pid, row['fold']) == row['fold'],
                'problem cannot cross fixed folds')
        require(type(row['current_source']) is str, 'exact UTF-8 current source required')
        source = row['current_source'].encode('utf-8', errors='strict')
        current = sha(source)
        by_example[eid] = {**row, 'current_source_sha256': current, 'choices': {}}
        tasks[pid, current] = source
    require(set(folds.values()) == set(range(5)), 'all five fixed folds required')
    for pred in predictions:
        require(type(pred) is dict and set(pred) == {
            'example_id', 'arm', 'selected_source', 'selected_source_sha256'},
            'strict selected-only prediction fields required')
        eid, arm = pred['example_id'], pred['arm']
        require(type(eid) is str and eid in by_example and type(arm) is str and arm in ARMS,
                'foreign recipient or generation arm')
        row = by_example[eid]
        require(arm not in row['choices'], 'duplicate recipient arm prediction')
        require(type(pred['selected_source']) is str, 'exact UTF-8 selected source required')
        source = pred['selected_source'].encode('utf-8', errors='strict')
        cid = sha(source)
        require(type(pred['selected_source_sha256']) is str
                and pred['selected_source_sha256'] == cid, 'selected source SHA mismatch')
        row['choices'][arm] = cid
        key = row['problem_id'], cid
        require(key not in tasks or tasks[key] == source, 'conflicting exact source identity')
        tasks[key] = source
    require(all(set(row['choices']) == set(ARMS) for row in by_example.values()),
            'every recipient must retain all four sealed arms')
    expected = {pid + '/testcases.jsonl' for pid in folds}
    require(type(testcase_pins) is dict and set(testcase_pins) == expected,
            'exact recipient-problem testcase pin inventory required')
    require(all(type(v) is str and re.fullmatch(r'[0-9a-f]{64}', v)
                for v in testcase_pins.values()), 'lowercase testcase SHA256 pins required')
    # All strings are immutable; copy containers to prevent caller mutation.
    return list(by_example.values()), dict(sorted(tasks.items())), dict(testcase_pins)


def _read_cases(root, pins):
    """Parse only the same exact bytes that were authenticated, without reread."""
    require(root.resolve() == root, 'canonical nonsymlink testcase root required')
    cases, universes = {}, {}
    for relative, digest in sorted(pins.items()):
        path = root / relative
        require(path.resolve() == path, 'testcase symlink or redirected path forbidden')
        raw = path.read_bytes()
        require(sha(raw) == digest, 'private testcase SHA mismatch: ' + relative)
        result = []
        for line in raw.decode('utf-8', errors='strict').splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            values = [row[k] for k in ('case_id', 'input', 'expected_output')]
            require(all(type(v) is str for v in values) and bool(values[0]),
                    'testcases require string ID/input/expected output')
            result.append(TestCase(*values))
        require(result and len({c.case_id for c in result}) == len(result),
                'nonempty unique private testcase universe required')
        pid = relative.split('/')[0]
        cases[pid] = tuple(result)
        universes[pid] = canonical_hash([asdict(c) for c in result])
    return cases, universes


def _runtime_identity():
    require((evaluator.SandboxRunner.timeout_sec, evaluator.SandboxRunner.memory_limit_mb,
             evaluator.SandboxRunner.case_workers) == (2.5, 2048, 1),
            'unchanged sandbox resource settings required')
    root = Path(__file__).resolve().parents[1]
    names = ('scripts/zpd_transition_private.py', 'scripts/zpd_repair_evaluate.py',
             'src/runner/python_runner.py', 'src/runner/compare.py',
             'src/runner/models.py', 'src/repair/pilot_contracts.py')
    return dict(timeout_sec=2.5, memory_limit_mb=2048, case_workers=1,
        block_workers=list(WORKERS), python=sys.version, platform=platform.platform(),
        execution_python=evaluator.sandbox_preflight(), sandbox_command=evaluator.sandbox_command(),
        binaries_sha256={p: file_sha(p) for p in ('/usr/bin/python3', '/usr/bin/bwrap')},
        implementation_sha256={name: file_sha(root / name) for name in names},
        outer_source_and_resource_attestation_required=True)


def _metrics(rows, arm):
    counts = Counter(stable_ac=0, stable_regression=0, unknown=0, noop_selected=0)
    for row in rows:
        label = row['labels'][arm]
        counts['unknown'] += label['status'] == 'unknown'
        counts['stable_ac'] += label['status'] == 'stable' and label['all_ac']
        counts['stable_regression'] += label['status'] == 'stable' and label['loss'] > 0
        counts['noop_selected'] += label['is_noop']
    n = len(rows)
    a, r, u = (counts[k] for k in ('stable_ac', 'stable_regression', 'unknown'))
    return dict(examples=n, evaluable=bool(n), counts=dict(counts), fractions={
        'ac_lower': Fraction(a, n), 'ac_upper': Fraction(a + u, n),
        'regression_lower': Fraction(r, n), 'regression_upper': Fraction(r + u, n),
    } if n else None)


def _group(rows):
    problems = {pid: [row for row in rows if row['problem_id'] == pid]
                for pid in sorted({row['problem_id'] for row in rows})}
    per_problem = {pid: {arm: _metrics(group, arm) for arm in METHODS}
                   for pid, group in problems.items()}
    equal = {arm: {metric: sum((p[arm]['fractions'][metric] for p in per_problem.values()),
                              Fraction()) / len(problems) for metric in METRICS}
             for arm in METHODS} if problems else None
    return dict(examples=len(rows), problems=len(problems),
                results={arm: _metrics(rows, arm) for arm in METHODS},
                problem_results=per_problem, equal_problem=equal)


def _paired(rows, control):
    counts = Counter(examples=len(rows), selected_candidate_changed=0, ac_gained=0,
        ac_lost=0, regression_prevented=0, regression_introduced=0,
        not_jointly_known=0, to_noop=0, from_noop=0, edited_to_edited=0)
    for row in rows:
        left, right = row['labels']['H'], row['labels'][control]
        if left['source_sha256'] != right['source_sha256']:
            counts['selected_candidate_changed'] += 1
            counts['to_noop' if left['is_noop'] else 'from_noop' if right['is_noop']
                   else 'edited_to_edited'] += 1
        if left['status'] == 'unknown' or right['status'] == 'unknown':
            counts['not_jointly_known'] += 1
        else:
            counts['ac_gained'] += left['all_ac'] and not right['all_ac']
            counts['ac_lost'] += right['all_ac'] and not left['all_ac']
            counts['regression_prevented'] += left['loss'] == 0 and right['loss'] > 0
            counts['regression_introduced'] += left['loss'] > 0 and right['loss'] == 0
    return dict(counts)


def _serialize(value):
    if isinstance(value, Fraction):
        return dict(numerator=value.numerator, denominator=value.denominator, value=float(value))
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_serialize(v) for v in value]
    return value


def assess(recipients, labels, *, execution_complete):
    """Descriptive new-experiment gate; never projects fictitious old arms."""
    indexed = {(label['example_id'], label['arm']): label for label in labels}
    require(len(indexed) == len(labels)
            and set(indexed) == {(r['example_id'], arm) for r in recipients for arm in METHODS},
            'exact unique selected-and-current label coverage required')
    rows = [{**r, 'labels': {arm: indexed[r['example_id'], arm] for arm in METHODS}}
            for r in recipients]
    groups = {name: [] for name in ('known_ac', 'known_nonac', 'unknown')}
    for row in rows:
        current = row['labels']['noop']
        group = 'unknown' if current['status'] == 'unknown' else 'known_ac' if current['all_ac'] else 'known_nonac'
        groups[group].append(row)
    full = _group(rows)
    folds = {str(f): _group([r for r in rows if r['fold'] == f]) for f in range(5)}
    h, c = (full['results'][arm]['counts'] for arm in ('H', 'C'))
    checks = {f'strict_pooled_ac_H_over_{arm}': h['stable_ac'] > full['results'][arm]['counts']['stable_ac']
              for arm in ('C', 'HS', 'U')}
    checks.update(pooled_regression_nonincrease_vs_C=h['stable_regression'] <= c['stable_regression'],
                  pooled_unknown_nonincrease_vs_C=h['unknown'] <= c['unknown'],
                  pooled_regression_upper_nonincrease_vs_C=h['stable_regression'] + h['unknown']
                    <= c['stable_regression'] + c['unknown'])
    nonworse = {f: cell['results']['H']['counts']['stable_ac']
                  >= cell['results']['C']['counts']['stable_ac'] for f, cell in folds.items()}
    checks['all_five_folds_ac_nonworse_vs_C'] = all(nonworse.values())
    checks['complete_execution'] = execution_complete is True
    passed = all(checks.values())
    return _serialize(dict(version=VERSION, methods=list(METHODS), primary='H',
        full=full, folds=folds, current_status_subgroups={k: _group(v) for k, v in groups.items()},
        current_status_subgroup_folds={k: {str(f): _group([r for r in v if r['fold'] == f])
                                          for f in range(5)} for k, v in groups.items()},
        paired_H={arm: _paired(rows, arm) for arm in ('C', 'HS', 'U')},
        development_gate=dict(checks=checks, passed=passed, decision='proceed' if passed else 'hold',
            nonworse_ac_folds=nonworse, required_nonworse_ac_folds=5,
            scope='Predeclared pooled descriptive new-generation gate; equal-problem and current-status slices are reported separately.'),
        exclusions=0, execution_complete=execution_complete, historical_gates_evaluated=False,
        historical_gate_status='not_applicable_to_new_generation_arms', confirmatory=False,
        model_promotion=False, educational_benefit_established=False,
        unknown_bounds_are_confidence_intervals=False))


def execute_private(recipients, predictions, testcases_root, testcase_pins, output,
                    deadline_seconds=MAX_SECONDS):
    """Return and save labels/report for exactly 320 sealed four-arm recipients.

    ``testcase_pins`` maps ``<problem_id>/testcases.jsonl`` to exact SHA256.
    The caller owns seal authentication, clean-source/cgroup checks and final
    normal-exit certification. An incomplete execution is retained as unknown
    evidence and always holds; an existing output is never resumed/overwritten.
    """
    roster, tasks, pins = _validate(recipients, predictions, testcase_pins)
    require(type(deadline_seconds) in (int, float) and math.isfinite(deadline_seconds)
            and 0 < deadline_seconds <= MAX_SECONDS, 'private deadline must be positive and at most six hours')
    output, root = Path(output).absolute(), Path(testcases_root).absolute()
    require(output.resolve() == output, 'canonical nonsymlink output required')
    if output.exists():
        raise FileExistsError('private output exists; retries/resume/overwrite forbidden')
    started = time.monotonic()
    deadline = started + deadline_seconds
    cases, universes = _read_cases(root, pins)
    runtime = _runtime_identity()
    runtime_sha = canonical_hash(runtime)
    # Detach the input seal from caller-owned containers, excluding source bodies.
    inventory = [{k: v for k, v in row.items() if k != 'current_source'} for row in roster]
    input_sha = canonical_hash(inventory)
    output.mkdir(parents=True, exist_ok=False)
    records = {key: [] for key in tasks}
    recipient_tasks = [{(row['problem_id'], cid) for cid in
                        (row['current_source_sha256'], *row['choices'].values())}
                       for row in roster]
    completed_blocks = completed_cases = 0
    total_blocks = 4 * len(tasks)
    total_cases = 4 * sum(len(cases[pid]) for pid, _ in tasks)
    files = {}

    def progress(phase, block):
        finished = {key for key, blocks in records.items()
                    if len(blocks) == 4 and all(item.complete for item in blocks)}
        return dict(phase=phase, block_index=block, examples=EXAMPLES,
            completed_examples=sum(required <= finished for required in recipient_tasks),
            total_examples=EXAMPLES,
            completed_source_blocks=completed_blocks, total_source_blocks=total_blocks,
            completed_case_attempts=completed_cases, total_case_attempts=total_cases,
            elapsed_seconds=time.monotonic() - started)

    try:
        files['manifest.json'] = write_new(output / 'manifest.json', dict(version=VERSION,
            input_sha256=input_sha, selections=inventory, testcase_files_sha256=pins,
            universe_sha256=universes, runtime=runtime, runtime_sha256=runtime_sha,
            block_workers=list(WORKERS), deadline_seconds=deadline_seconds,
            unique_sources=len(tasks), planned_source_blocks=total_blocks,
            planned_case_attempts=total_cases, selected_only=True, old_labels_opened=False,
            selection_seal_authentication='caller_precondition_not_verified_here'))
        _status(output, progress('private_execution', -1))
        with (output / 'completions.jsonl').open('xb') as journal:
            for block_index, workers in enumerate(WORKERS):
                remaining, pending = iter(tasks), {}
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    def submit():
                        if time.monotonic() >= deadline:
                            return
                        key = next(remaining, None)
                        if key is not None:
                            future = pool.submit(evaluator.run_source, evaluator.SandboxRunner(),
                                tasks[key], cases[key[0]], deadline)
                            pending[future] = key
                    for _ in range(workers):
                        submit()
                    while pending:
                        done, _ = wait(pending, timeout=10, return_when=FIRST_COMPLETED)
                        for future in done:
                            key = pending.pop(future)
                            outcomes, details, complete = future.result()
                            block = ExecutionBlock(workers, universes[key[0]], runtime_sha,
                                tuple(outcomes), complete, key[1])
                            records[key].append(block)
                            journal.write(encoded(dict(problem_id=key[0], source_sha256=key[1],
                                block_index=block_index, block=asdict(block), cases=details)))
                            journal.flush()
                            os.fsync(journal.fileno())
                            completed_blocks += 1
                            completed_cases += len(outcomes)
                            submit()
                        _status(output, progress('private_execution', block_index))
                if any(len(v) != block_index + 1 or not v[-1].complete for v in records.values()):
                    break
        complete = (completed_blocks == total_blocks and completed_cases == total_cases
                    and all(len(v) == 4 and all(b.complete for b in v) for v in records.values())
                    and time.monotonic() < deadline)
        if complete:
            require(_runtime_identity() == runtime, 'private runtime changed during execution')
            require(root.resolve() == root, 'private testcase root changed during execution')
            for relative, digest in pins.items():
                path = root / relative
                require(path.resolve() == path and file_sha(path) == digest,
                        'private testcase changed during execution: ' + relative)
        vectors = {key: ExecutionVector(key[1], universes[key[0]], runtime_sha,
                    tuple(c.case_id for c in cases[key[0]]), tuple(blocks))
                   for key, blocks in records.items()}
        labels = []
        for row in roster:
            pid = row['problem_id']
            current = vectors[pid, row['current_source_sha256']]
            for arm in METHODS:
                cid = row['current_source_sha256'] if arm == 'noop' else row['choices'][arm]
                evidence = compare_execution(current, vectors[pid, cid])
                n = len(cases[pid])
                labels.append(dict(example_id=row['example_id'], problem_id=pid, fold=row['fold'],
                    arm=arm, source_sha256=cid, current_source_sha256=row['current_source_sha256'],
                    is_noop=cid == row['current_source_sha256'], status=evidence.status,
                    gain=None if evidence.gained_testcases is None else len(evidence.gained_testcases) / n,
                    loss=None if evidence.lost_testcases is None else len(evidence.lost_testcases) / n,
                    all_ac=evidence.candidate_all_ac, n_cases=n, evidence=asdict(evidence)))
        report = assess(roster, labels, execution_complete=complete)
        report['execution'] = progress('complete' if complete else 'incomplete', block_index)
        files['vectors.json'] = write_new(output / 'vectors.json', [dict(problem_id=pid,
            vector=asdict(vector), vector_sha256=vector.seal_sha256)
            for (pid, _), vector in vectors.items()])
        files['labels.json'] = write_new(output / 'labels.json', labels)
        files['report.json'] = write_new(output / 'report.json', report)
        _status(output, report['execution'])
        for name in ('STATUS.json', 'completions.jsonl'):
            files[name] = file_sha(output / name)
        require(all(file_sha(output / name) == digest for name, digest in files.items()),
                'private output artifact changed')
        marker = 'COMPLETE.json' if complete else 'INCOMPLETE.json'
        write_new(output / marker, dict(status='complete' if complete else 'time_budget_exhausted',
            version=VERSION, input_sha256=input_sha, runtime_sha256=runtime_sha,
            files_sha256=files, examples=EXAMPLES, labels=len(labels),
            development_decision=report['development_gate']['decision'],
            provisional_until_normal_unit_exit=True, model_promotion=False))
        return dict(labels=labels, report=report, complete=complete, output=str(output))
    except BaseException as exc:
        write_new(output / 'FAILED.json', dict(error_type=type(exc).__name__, error=str(exc),
            completed_source_blocks=completed_blocks, assessment_valid=False))
        raise
