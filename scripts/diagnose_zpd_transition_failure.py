"""Retrospective source-keyed generation/selection diagnosis; never executes code.

``load(project)`` authenticates the frozen 2026-10-12 artifacts and returns inputs,
attempts, predictions, vector_map, public_masks, scoring, manifest, and input pins.
``assess(inputs, attempts, predictions, vector_map, public_masks=None)`` accepts a
map of (problem_id, source_sha256) -> ExecutionVector, or serialized vector rows.
Its caller must authenticate supplementary execution and normal exit first.
``prepare(project, output)`` writes an exclusive, sealed missing-only task bundle.
Missing and unstable evidence stay unknown. No selector, model, or gate is changed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re

from src.repair.pilot_contracts import (
    CandidateAttempt, ExecutionBlock, ExecutionVector, canonical_hash,
    compare_execution, source_hash,
)

VERSION = 'transition_generation_selection_diagnosis_v1'
ARMS = ('C', 'H', 'HS', 'U')
ARCHIVE = Path('archive/zpd-transition-generation-20261012')
STAGES = {
    'generation': ('recovered-generation-v1', '0e309b224bfce72995888b02853c7e1aaa785d09000caacf154bed25b343ca6e'),
    'public': ('recovered-public-v1', 'fc60dca0c43f0e0eaee53c6e779da9b6cff4206a3af46abf034ec7684e4b3f47'),
    'private': ('completed-private-v1', '4dedf4345136594bd89c0ebd942e9ccee1230b7975397ba5ec2910d4bb451252'),
}
PINS = {
    'prepared-v1/COMPLETE.json': 'fbcfe0ed515e0792fa5d7439e5869ed2025327dd7ca899eff9f9994c6f874ab7',
    'prepared-v1/inputs.json': 'd8b981633a7180828f35b9c7ad9b6a9b1beefdd07fad702e19b9d1cde692e8fd',
    'completed-private-v1/VERIFIED_COMPLETE.json': 'f19f519578ffe14730ed948190d1273de74ab702352fa47a8a45defbe46cd319',
    'completed-private-v1/private-v1/evaluation/vectors.json': '55ec803749b985627999198b4e93efc43381cdde66cb3de1e71b79262e98ea8c',
}
RELEASE = 'analysis_protocols/zpd-transition-generation-release-20261012.json'
RELEASE_SHA = 'dba5aa43b104d0c20f056cf2a71b5bbaf96a5a6b8f939f3fcab55acafec43b59'
RECOVERY = 'analysis_protocols/zpd-transition-evaluation-recovery-20261012.json'
RECOVERY_SHA = 'ca64904546e1f1863c509da61dcf7895498297b54de2695953c0f151f454bd71'


def require(value, message):
    if not value:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      allow_nan=False, separators=(',', ':')).encode() + b'\n'


def file_sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _read(path, expected=None):
    path = Path(path)
    require(path.resolve() == path.absolute(), 'redirected artifact forbidden: ' + str(path))
    raw = path.read_bytes()
    require(expected is None or hashlib.sha256(raw).hexdigest() == expected,
            'artifact SHA mismatch: ' + str(path))
    return json.loads(raw)


def _seal(directory, marker, expected, *, exact=False):
    seal = _read(directory / marker, expected)
    require(seal['status'] == 'complete', 'incomplete artifact seal')
    for name, digest in seal['files_sha256'].items():
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,
                'unsafe sealed artifact path')
        path = directory / name
        require(path.resolve() == path.absolute(), 'redirected sealed artifact')
        require(file_sha(path) == digest, 'sealed file SHA mismatch: ' + str(path))
    if exact:
        actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
        require(actual == set(seal['files_sha256']) | {marker}, 'extra or missing stage artifact')
    return seal


def deserialize_vectors(rows):
    """Validate serialized seals and retain exact (problem, source) identity."""
    result = {}
    for row in rows:
        require(set(row) == {'problem_id', 'vector', 'vector_sha256'}, 'strict vector row required')
        value = row['vector']
        blocks = tuple(ExecutionBlock(**dict(b, outcomes=tuple(tuple(x) for x in b['outcomes'])))
                       for b in value['blocks'])
        vector = ExecutionVector(**dict(value, blocks=blocks, testcase_ids=tuple(value['testcase_ids'])))
        require(vector.seal_sha256 == row['vector_sha256'], 'execution vector SHA mismatch')
        key = row['problem_id'], vector.source_sha256
        require(key not in result, 'duplicate problem/source execution vector')
        result[key] = vector
    return result


def _inventory(inputs, attempts, predictions):
    recipients = {row['example_id']: row for row in inputs['recipients']}
    require(len(recipients) == len(inputs['recipients']) and recipients, 'unique recipients required')
    planned = {row['attempt_id']: row for row in inputs['attempts']}
    require(len(planned) == len(inputs['attempts']) == 8 * len(recipients), 'eight planned draws required')
    require(len(attempts) == len(planned) and {r['attempt_id'] for r in attempts} == set(planned),
            'exact unique terminal attempt coverage required')
    membership, generated, sources, counts, draw_indices = {}, defaultdict(set), {}, defaultdict(Counter), defaultdict(set)
    for eid, row in recipients.items():
        pid = row['problem_id']
        require(type(pid) is str and re.fullmatch(r'[A-Za-z0-9_-]+', pid), 'safe problem ID required')
        current = source_hash(row['current_source'].encode('utf-8'))
        require(current == row['current_source_sha256'], 'current source SHA mismatch')
        sources[pid, current] = row['current_source']
        for arm in ARMS:
            membership[eid, arm] = {current}
    for row in attempts:
        require(all(row[k] == value for k, value in planned[row['attempt_id']].items()), 'planned attempt binding differs')
        eid, arm = row['example_id'], row['arm']
        require(eid in recipients and arm in ARMS and row['problem_id'] == recipients[eid]['problem_id'],
                'foreign attempt recipient/arm/problem')
        require(row['draw_index'] in (0, 1) and row['draw_index'] not in draw_indices[eid, arm],
                'duplicate or foreign arm draw')
        draw_indices[eid, arm].add(row['draw_index'])
        entry = row['attempt']
        CandidateAttempt(**dict(entry, source=entry['source'].encode('utf-8') if entry['source'] is not None else None))
        require(entry['index'] == row['draw_index'] and entry['seed'] == row['seed'], 'attempt seed/index differs')
        counts[arm][entry['status']] += 1
        if entry['status'] == 'success':
            cid = source_hash(entry['source'].encode('utf-8'))
            key = row['problem_id'], cid
            require(key not in sources or sources[key] == entry['source'], 'source identity conflict')
            sources[key] = entry['source']
            membership[eid, arm].add(cid)
            generated[eid, arm].add(cid)
    require(all(draw_indices[k] == {0, 1} for k in membership), 'two terminal draws per arm required')
    selected = {}
    for row in predictions:
        key = row['example_id'], row['arm']
        require(key in membership and key not in selected, 'duplicate or foreign prediction')
        eid, _ = key
        require(row['problem_id'] == recipients[eid]['problem_id'] and row['fold'] == recipients[eid]['fold'],
                'prediction problem/fold differs')
        require(set(row['eligible_candidate_ids']) == membership[key]
                and len(row['eligible_candidate_ids']) == len(membership[key]), 'arm candidate membership differs')
        cid = source_hash(row['selected_source'].encode('utf-8'))
        require(cid == row['selected_source_sha256'] and cid in membership[key], 'selected source binding differs')
        selected[key] = cid
    require(set(selected) == set(membership), 'complete four-arm prediction coverage required')
    return recipients, membership, generated, sources, selected, counts


def _vectors(value, sources, recipients):
    vectors = deserialize_vectors(value) if isinstance(value, list) else dict(value)
    contexts = {}
    for key, vector in vectors.items():
        require(key in sources and isinstance(vector, ExecutionVector)
                and key[1] == vector.source_sha256, 'foreign or miskeyed execution vector')
        context = vector.universe_sha256, vector.runtime_sha256, vector.testcase_ids
        require(contexts.setdefault(key[0], context) == context, 'problem execution context drift')
    require(len({v.runtime_sha256 for v in vectors.values()}) == 1, 'mixed runtime vectors forbidden')
    require(all((r['problem_id'], r['current_source_sha256']) in vectors for r in recipients.values()),
            'original current vectors required')
    return vectors


def assess(inputs, attempts, predictions, vector_map, public_masks=None):
    """Diagnose authenticated original/merged vectors without new selection.

    Pair-contract oracle requires a stable current and candidate, matching the
    original selected report. Source-only oracle is reported separately; neither
    oracle is a deployable method or an observed improvement.
    """
    recipients, membership, generated, sources, selected, attempts_count = _inventory(inputs, attempts, predictions)
    vectors = _vectors(vector_map, sources, recipients)
    if public_masks is not None:
        require(set(public_masks) == {pid + '|' + cid for pid, cid in sources}, 'public source inventory differs')
    per_arm, details = {}, []
    for arm in ARMS:
        count = Counter({k: 0 for k in (
            'selected_stable_ac', 'selected_stable_nonac', 'selected_unknown',
            'oracle_lower', 'oracle_upper', 'source_only_oracle_lower', 'source_only_oracle_upper',
            'generated_only_oracle_lower', 'generated_only_oracle_upper',
            'missed_known_ac', 'known_ac_with_selected_unknown', 'proven_no_ac', 'unresolved_no_known_ac',
            'examples_with_missing', 'eligible_candidate_references', 'missing_candidate_references',
            'executed_unknown_candidate_references', 'known_candidate_references',
            'known_ac_candidate_references', 'unselected_covered_references',
        )})
        arm_keys, generated_keys = set(), set()
        for eid in sorted(recipients):
            row = recipients[eid]
            pid, current_sha = row['problem_id'], row['current_source_sha256']
            current = vectors[pid, current_sha]
            known, source_known, missing, executed_unknown = {}, {}, [], []
            for cid in sorted(membership[eid, arm]):
                key = pid, cid
                arm_keys.add(key)
                if key not in vectors:
                    known[cid] = source_known[cid] = None
                    missing.append(cid)
                else:
                    evidence = compare_execution(current, vectors[key])
                    known[cid] = evidence.candidate_all_ac if evidence.status == 'stable' else None
                    outcomes = vectors[key].stable_outcomes
                    source_known[cid] = None if outcomes is None else all(x == 'AC' for x in outcomes)
                    if evidence.status == 'unknown':
                        executed_unknown.append(cid)
            generated_keys.update((pid, c) for c in generated[eid, arm])
            cid = selected[eid, arm]
            require((pid, cid) in vectors, 'frozen selected vector missing')
            observed = known[cid]
            count['selected_unknown' if observed is None else 'selected_stable_ac' if observed else 'selected_stable_nonac'] += 1
            lower = any(x is True for x in known.values())
            upper = lower or any(x is None for x in known.values())
            count['oracle_lower'] += lower
            count['oracle_upper'] += upper
            count['source_only_oracle_lower'] += any(x is True for x in source_known.values())
            count['source_only_oracle_upper'] += any(x is not False for x in source_known.values())
            count['generated_only_oracle_lower'] += any(known[c] is True for c in generated[eid, arm])
            count['generated_only_oracle_upper'] += any(known[c] is not False for c in generated[eid, arm])
            count['missed_known_ac'] += lower and observed is False
            count['known_ac_with_selected_unknown'] += lower and observed is None
            count['proven_no_ac'] += not upper
            count['unresolved_no_known_ac'] += upper and not lower
            count['examples_with_missing'] += bool(missing)
            count['eligible_candidate_references'] += len(known)
            count['missing_candidate_references'] += len(missing)
            count['executed_unknown_candidate_references'] += len(executed_unknown)
            count['known_candidate_references'] += sum(x is not None for x in known.values())
            count['known_ac_candidate_references'] += sum(x is True for x in known.values())
            count['unselected_covered_references'] += sum(c != cid and (pid, c) in vectors for c in known)
            details.append(dict(example_id=eid, problem_id=pid, arm=arm,
                selected_source_sha256=cid, selected_all_ac=observed,
                oracle_lower=lower, oracle_upper=upper,
                known_ac_candidate_ids=[c for c, value in known.items() if value is True],
                missing_candidate_ids=missing, executed_unknown_candidate_ids=executed_unknown))
        per_arm[arm] = dict(count, examples=len(recipients), attempts=dict(sorted(attempts_count[arm].items())),
            unique_source_tasks=len(arm_keys), covered_unique_source_tasks=len(arm_keys & set(vectors)),
            missing_unique_source_tasks=len(arm_keys - set(vectors)), generated_unique_source_tasks=len(generated_keys))
    generated_keys = {(recipients[eid]['problem_id'], c) for (eid, _), values in generated.items() for c in values}
    missing = set(sources) - set(vectors)
    return dict(version=VERSION, retrospective_diagnostic=True, confirmatory=False,
        model_promotion=False, method_improvement_established=False, historical_gates_passed=False,
        unknown_bounds_are_confidence_intervals=False,
        oracle_definition='Any arm-owned terminal success or current has stable compare_execution all-AC; unexecuted/unstable stays unknown.',
        source_only_oracle_definition='Candidate stability only; separate from the current-and-candidate contract used by selected AC.',
        limitations=['Exposed adaptive development cohort.',
            'Oracle is retrospective availability, not deployable selection or observed method improvement.',
            'Existing unstable vectors are not failed or retried; missing-only replay cannot resolve their unknowns.',
            'Source reuse requires exact problem, source bytes, universe, runtime, and testcase IDs.'],
        examples=len(recipients), problems=len({r['problem_id'] for r in recipients.values()}),
        coverage=dict(unique_source_tasks=len(sources), generated_unique_source_tasks=len(generated_keys),
            observed_unique_source_tasks=len(vectors), missing_unique_source_tasks=len(missing),
            stable_observed_vectors=sum(v.stable_outcomes is not None for v in vectors.values()),
            unstable_observed_vectors=sum(v.stable_outcomes is None for v in vectors.values()),
            candidate_references=sum(len(s) for s in membership.values()),
            generated_candidate_references=sum(len(s) for s in generated.values())),
        per_arm=per_arm, rows=details)


def load(project):
    """Authenticate only local sealed artifacts; never opens private testcase files."""
    project = Path(project).resolve()
    root = project / ARCHIVE
    release = _read(project / RELEASE, RELEASE_SHA)
    _read(project / RECOVERY, RECOVERY_SHA)
    prepared = _seal(root / 'prepared-v1', 'COMPLETE.json', PINS['prepared-v1/COMPLETE.json'])
    require(release['inputs_complete_sha256'] == PINS['prepared-v1/COMPLETE.json']
            and release['inputs_sha256'] == PINS['prepared-v1/inputs.json'], 'release prepared pins differ')
    outer = _read(root / 'completed-private-v1/VERIFIED_COMPLETE.json', PINS['completed-private-v1/VERIFIED_COMPLETE.json'])
    require(outer['status'] == 'complete' and outer['release_sha256'] == RELEASE_SHA
            and outer['recovery_release_sha256'] == RECOVERY_SHA, 'outer completion differs')
    stage_seals = {}
    for phase, (folder, digest) in STAGES.items():
        marker = _read(root / folder / (phase + '-VERIFIED_COMPLETE.json'), outer['phases'][phase])
        require(marker['complete_sha256'] == digest and marker['status'] == 'complete'
                and marker['release_sha256'] == RELEASE_SHA and marker['recovery_release_sha256'] == RECOVERY_SHA
                and marker['cgroup_removed'] and marker['cleanup_verified'], 'phase certification differs')
        require(marker['exit'] == dict(ExecMainCode='1', ExecMainStatus='0', MainPID='0', Result='success', SubState='exited'),
                'phase normal exit absent')
        stage = root / folder / (phase + '-v1')
        seal = _seal(stage, 'STAGE_COMPLETE.json', digest, exact=True)
        require(seal['phase'] == phase and seal['release_sha256'] == RELEASE_SHA, 'stage release differs')
        stage_seals[phase] = seal
    gen = root / STAGES['generation'][0] / 'generation-v1'
    public = root / STAGES['public'][0] / 'public-v1'
    private = root / STAGES['private'][0] / 'private-v1/evaluation'
    complete = _seal(private, 'COMPLETE.json', stage_seals['private']['files_sha256']['evaluation/COMPLETE.json'])
    inputs = _read(root / 'prepared-v1/inputs.json', PINS['prepared-v1/inputs.json'])
    attempts, predictions = _read(gen / 'attempts.json'), _read(public / 'predictions.json')
    require(len(inputs['recipients']) == 320 and len(attempts) == 2560 and len(predictions) == 1280,
            'frozen population differs')
    prediction_seal = _read(public / 'PREDICTIONS_COMPLETE.json')
    require(prediction_seal['predictions_sha256'] == file_sha(public / 'predictions.json')
            and prediction_seal['private_assessment_accessed'] is False, 'prediction seal differs')
    manifest, labels = _read(private / 'manifest.json'), _read(private / 'labels.json')
    require(canonical_hash(manifest['runtime']) == manifest['runtime_sha256'] == complete['runtime_sha256'],
            'runtime hash differs')
    require(manifest['testcase_files_sha256'] == release['testcase_sha256'], 'private testcase pins differ')
    for name, pin in manifest['runtime']['implementation_sha256'].items():
        require(file_sha(project / name) == pin, 'original implementation source drift: ' + name)
    vectors = deserialize_vectors(_read(private / 'vectors.json', PINS['completed-private-v1/private-v1/evaluation/vectors.json']))
    recipients, membership, generated, sources, selected, counts = _inventory(inputs, attempts, predictions)
    _vectors(vectors, sources, recipients)
    selections = [dict(example_id=r['example_id'], problem_id=r['problem_id'], fold=r['fold'],
        current_source_sha256=r['current_source_sha256'], choices={a: selected[r['example_id'], a] for a in ARMS})
        for r in inputs['recipients']]
    require(selections == manifest['selections'] and canonical_hash(selections) == manifest['input_sha256'] == complete['input_sha256'],
            'private input selection seal differs')
    require(set(vectors) == {(r['problem_id'], c) for r in selections
                           for c in (r['current_source_sha256'], *r['choices'].values())}, 'selected-only vector coverage differs')
    for (pid, _), vector in vectors.items():
        require(vector.runtime_sha256 == manifest['runtime_sha256']
                and vector.universe_sha256 == manifest['universe_sha256'][pid], 'manifest vector context differs')
    require(len(labels) == 1600 and len({(x['example_id'], x['arm']) for x in labels}) == 1600,
            'private label coverage differs')
    for label in labels:
        eid, arm = label['example_id'], label['arm']
        require(eid in recipients and arm in (*ARMS, 'noop'), 'foreign private label')
        row = recipients[eid]
        cid = row['current_source_sha256'] if arm == 'noop' else selected[eid, arm]
        require(label['source_sha256'] == cid and label['problem_id'] == row['problem_id']
                and label['current_source_sha256'] == row['current_source_sha256'], 'private label source binding differs')
        evidence = compare_execution(vectors[row['problem_id'], row['current_source_sha256']], vectors[row['problem_id'], cid])
        require(canonical_hash(asdict(evidence)) == canonical_hash(label['evidence'])
                and label['status'] == evidence.status and label['all_ac'] == evidence.candidate_all_ac,
                'private label differs from vector contracts')
    public_masks, scoring = _read(public / 'public-vectors.json'), _read(public / 'scoring.json')
    require(file_sha(project / 'scripts/zpd_public_candidate_selection.py') == release['source_sha256']['scripts/zpd_public_candidate_selection.py'],
            'public selector implementation drift')
    from scripts.zpd_public_candidate_selection import choose
    for row in predictions:
        eid, arm = row['example_id'], row['arm']
        owned = membership[eid, arm]
        scores = {cid: scoring[eid][cid] for cid in owned}
        masks = {cid: public_masks[row['problem_id'] + '|' + cid] for cid in owned}
        choice, diagnostic = choose(scores, masks, recipients[eid]['current_source_sha256'], min(scores, key=lambda cid: (-scores[cid], cid)))
        require(choice == row['selected_source_sha256'] and diagnostic == row['diagnostic'], 'frozen selector replay differs')
    report = _read(private / 'report.json')
    diagnostic = assess(inputs, attempts, predictions, vectors, public_masks)
    require(all(diagnostic['per_arm'][a]['selected_stable_ac'] == report['full']['results'][a]['counts']['stable_ac']
                and diagnostic['per_arm'][a]['selected_unknown'] == report['full']['results'][a]['counts']['unknown'] for a in ARMS),
            'frozen selected report differs')
    pins = {str(ARCHIVE / name): pin for name, pin in PINS.items()}
    pins.update({RELEASE: RELEASE_SHA, RECOVERY: RECOVERY_SHA})
    pins.update({str(ARCHIVE / folder / (phase + '-v1/STAGE_COMPLETE.json')): pin
                 for phase, (folder, pin) in STAGES.items()})
    return dict(inputs=inputs, attempts=attempts, predictions=predictions, vector_map=vectors,
        public_masks=public_masks, scoring=scoring, manifest=manifest, original_report=report,
        input_files_sha256=pins, report=diagnostic, sources=sources)


def prepare(project, output):
    project, output = Path(project).resolve(), Path(output).absolute()
    require(output.resolve() == output, 'nonsymlink output required')
    if output.exists():
        raise FileExistsError('diagnostic output exists; overwrite forbidden')
    loaded = load(project)
    vectors, manifest = loaded['vector_map'], loaded['manifest']
    tasks = [dict(problem_id=pid, source_sha256=cid, source=loaded['sources'][pid, cid])
             for pid, cid in sorted(set(loaded['sources']) - set(vectors))]
    universes = {pid: dict(universe_sha256=vector.universe_sha256, case_ids=list(vector.testcase_ids))
                 for (pid, _), vector in vectors.items()}
    roster, membership, _, _, _, _ = _inventory(loaded['inputs'], loaded['attempts'], loaded['predictions'])
    recipient_tasks = []
    for eid in sorted(roster):
        pid = roster[eid]['problem_id']
        keys = {(pid, cid) for arm in ARMS for cid in membership[eid, arm]}
        recipient_tasks.append(dict(example_id=eid, problem_id=pid,
            task_keys=[list(k) for k in sorted(keys)],
            missing_task_keys=[list(k) for k in sorted(keys - set(vectors))]))
    bundle = dict(version=VERSION, missing_only=True, tasks=tasks,
        existing_task_keys=[list(k) for k in sorted(vectors)], recipients=recipient_tasks,
        total_planned_source_blocks=4 * len(tasks),
        total_planned_case_attempts=4 * sum(len(universes[t['problem_id']]['case_ids']) for t in tasks),
        expected_runtime=manifest['runtime'], expected_runtime_sha256=manifest['runtime_sha256'],
        testcase_pins=manifest['testcase_files_sha256'], universes=universes,
        input_sha256=canonical_hash(tasks), original_selected_input_sha256=manifest['input_sha256'],
        input_files_sha256=loaded['input_files_sha256'],
        original_vectors_sha256=PINS['completed-private-v1/private-v1/evaluation/vectors.json'],
        retrospective_diagnostic=True, generation_authorized=False, selection_changes_authorized=False,
        model_promotion=False, retry_existing_vectors=False)
    source_names = ('scripts/diagnose_zpd_transition_failure.py', 'src/repair/pilot_contracts.py',
                    'scripts/zpd_public_candidate_selection.py')
    output.mkdir(parents=True, exist_ok=False)
    files = {}
    for name, value in [('report.json', loaded['report']), ('missing-tasks.json', bundle)]:
        with (output / name).open('xb') as stream:
            stream.write(encoded(value))
        files[name] = file_sha(output / name)
    complete = dict(version=VERSION, status='complete', files_sha256=files,
        input_files_sha256=loaded['input_files_sha256'], source_sha256={n: file_sha(project / n) for n in source_names},
        missing_unique_source_tasks=len(tasks), input_sha256=bundle['input_sha256'],
        execution_performed=False, private_testcases_opened=False, model_promotion=False)
    with (output / 'COMPLETE.json').open('xb') as stream:
        stream.write(encoded(complete))
    return dict(report=loaded['report'], bundle=bundle, complete=complete, output=str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.project, args.output)
    print(json.dumps(dict(output=result['output'], coverage=result['report']['coverage'],
        per_arm={a: {k: result['report']['per_arm'][a][k] for k in
            ('selected_stable_ac', 'oracle_lower', 'oracle_upper', 'missed_known_ac')} for a in ARMS}), sort_keys=True))


if __name__ == '__main__':
    main()
