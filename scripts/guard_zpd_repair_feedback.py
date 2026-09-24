"""One-stage, separately released production boundary for fixed repair CV.

No release artifact is manufactured here. A fixed JSON and its strict SHA256
sidecar must both be tracked in the same clean source snapshot. The JSON pins
the exact source/test/protocol closure; excluding only those two release files
avoids a circular checksum. Root records the clean Git revision/tree at launch.
The supervisor, not a fold worker, owns process orchestration. There are no
retry, optimizer, subset, path-family or release/configuration overrides.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import subprocess
from importlib.metadata import version

from scripts import audit_zpd_repair_feedback_support as support
from scripts import run_zpd_repair_feedback_cv as engine
from scripts import zpd_repair_feedback_inputs as observed
from scripts import zpd_repair_feedback_labels as labels
from scripts import zpd_repair_feedback_offset as offset
from scripts.supervise_zpd_history_action import verify_marker

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = 'outputs/zpd-repair-feedback-20260924'
RELEASE = 'analysis_protocols/zpd-repair-feedback-fit-release-20260924.json'
SIDECAR = RELEASE+'.sha256'
PROTOCOL = 'analysis_protocols/zpd-repair-feedback-prospective-contract-20260924.md'
RUNTIME = dict(python='3.13.11', numpy='2.5.2', scipy='1.18.1', sklearn='1.9.0')
STAGES = ('preflight', 'prepare', 'initialize', *(f'fold-{i}' for i in range(5)), 'finalize', 'assess', 'audit')
CHILD_MEMORY_BYTES = 32*1024**3
BLAS_ENVIRONMENT = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')
SOURCE_FILES = tuple(sorted(set((*support.SOURCE_FILES, *observed.BASE_SOURCE_FILES,
    'scripts/run_zpd_repair_feedback_cv.py', 'scripts/zpd_repair_feedback_pairs.py',
    'scripts/zpd_repair_feedback_offset.py', 'scripts/zpd_repair_feedback_assessment.py',
    'scripts/zpd_repair_feedback_labels.py', 'scripts/zpd_repair_feedback_inputs.py',
    'scripts/audit_zpd_repair_feedback_cv.py', 'scripts/guard_zpd_repair_feedback.py',
    'scripts/supervise_zpd_repair_feedback.py', 'scripts/supervise_zpd_history_action.py',
    'scripts/run_zpd_repair_structure_cv.py', 'scripts/zpd_repair_pairwise_replication.py',
    'scripts/zpd_repair_replication.py', 'scripts/zpd_repair_risk_development.py',
    'scripts/zpd_repair_evaluate.py', 'scripts/prepare_zpd_repair_next.py',
    'tests/test_zpd_repair_feedback_offset.py', 'tests/test_zpd_repair_feedback_pairs.py',
    'tests/test_zpd_repair_feedback_assessment.py', 'tests/test_zpd_repair_feedback_labels.py',
    'tests/test_zpd_repair_feedback_inputs.py', 'tests/test_zpd_repair_feedback_cv.py',
    'tests/test_zpd_repair_feedback_audit.py', 'tests/test_zpd_repair_feedback_audit_review.py',
    'tests/test_zpd_repair_feedback_assessment_review.py', 'tests/test_zpd_repair_feedback_guard.py',
    'tests/test_zpd_repair_feedback_guard_review.py', 'tests/test_zpd_repair_feedback_supervisor.py',
    'analysis_protocols/zpd-repair-feedback-fit-preflight-20260924.md', PROTOCOL))))


def canonical(path):
    path = Path(path).absolute()
    if path.resolve() != path: raise ValueError('canonical nonsymlink path required')
    return path


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, allow_nan=False); stream.write('\n')


def source_state():
    if canonical(ROOT) != ROOT or subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, text=True).strip():
        raise ValueError('clean committed source snapshot required')
    return dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                tree=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip())


def runtime():
    return dict(python=platform.python_version(), numpy=version('numpy'), scipy=version('scipy'), sklearn=version('scikit-learn'))


def paths(project):
    project = canonical(project)
    if project != PROJECT: raise ValueError('fixed canonical production project required')
    base = project/FAMILY
    return dict(project=project, family=base, prepared=canonical(base/'prepared-v1'),
                run=canonical(base/'run-v1'), supervisor=canonical(base/'supervised-v1'),
                verified=canonical(base/'supervised-v1/verified'))


def release_configuration():
    return dict(primary='H', arms=list(engine.ARMS), folds=5, recipients=320, fits=25,
        methods=list(engine.METHODS), dimension=1296, offset=offset.configuration(),
        candidate_space='all_original_train320_banks_with_fixed8_terminal_attempts',
        base='same_fold_frozen_structural_C_additive_coefficient_one',
        full_train_refits=0, automatic_retries=0, model_promotion=False,
        process_stages=list(STAGES), original_valid32_materialized=False,
        child_memory_bytes=CHILD_MEMORY_BYTES, blas_threads=1, heartbeat_seconds=30,
        stage_timeout_seconds={stage: 3600 if stage.startswith('fold-') or stage == 'audit' else 900 for stage in STAGES},
        source_cache_limitation='preparation_verifies_original64_plus_valid32_physical_container_only_train64_retained')


def verify_child_boundary():
    """Observe, never alter, limits installed before the child interpreter starts."""
    if any(os.environ.get(name) != '1' for name in BLAS_ENVIRONMENT):
        raise ValueError('all four frozen child BLAS thread settings must equal one')
    if resource.getrlimit(resource.RLIMIT_AS) != (CHILD_MEMORY_BYTES, CHILD_MEMORY_BYTES):
        raise ValueError('fixed child32GiB soft and hard address-space limits required')


def _same(actual, expected):
    if type(actual) is not type(expected): return False
    if isinstance(expected, dict): return set(actual) == set(expected) and all(_same(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list): return len(actual) == len(expected) and all(_same(a, b) for a, b in zip(actual, expected))
    return actual == expected


def preflight(project):
    """Fail closed before labels or output; only fixed observed metadata here."""
    location = paths(project)
    if not ROOT.is_relative_to(location['project']/'.runtime'):
        raise ValueError('clean source snapshot must be beneath the fixed project .runtime directory')
    state = source_state()
    release = canonical(ROOT/RELEASE); sidecar = canonical(ROOT/SIDECAR)
    if not release.is_file() or not sidecar.is_file():
        raise RuntimeError('repair-feedback production is unreleased: fixed tracked release and sidecar required')
    tracked = (RELEASE, SIDECAR, *SOURCE_FILES)
    output = subprocess.check_output(['git', 'ls-files', '--error-unmatch', '--', *tracked], cwd=ROOT, text=True)
    if set(output.splitlines()) != set(tracked): raise ValueError('exact release/source closure must be tracked')
    digest_text = sidecar.read_text(encoding='ascii')
    if re.fullmatch(r'[0-9a-f]{64}\n', digest_text) is None or sha(release) != digest_text[:-1]:
        raise ValueError('strict release SHA256 sidecar mismatch')
    if runtime() != RUNTIME: raise ValueError('fixed production numerical runtime required')
    approval = read(release)
    expected = dict(kind='repair_feedback_fixed25_fit_release_v1', project=str(PROJECT), family=FAMILY,
        fit_release_authorized=True, confirmatory=False, fresh_test_opened=False, runtime=RUNTIME,
        input_complete_sha256={observed.SUPPORT+'/COMPLETE.json': engine.SUPPORT_COMPLETE_SHA256,
                              support.PARENT+'/COMPLETE.json': engine.PARENT_COMPLETE_SHA256},
        protocol_sha256=sha(ROOT/PROTOCOL), configuration=release_configuration())
    if (type(approval) is not dict or set(approval) != set(expected) | {'source_sha256', 'decision_reason'}
            or any(not _same(approval[k], v) for k, v in expected.items())
            or type(approval['decision_reason']) is not str or not approval['decision_reason'].strip()
            or type(approval['source_sha256']) is not dict or set(approval['source_sha256']) != set(SOURCE_FILES)):
        raise ValueError('strict complete prospective release schema/configuration required')
    source_bindings = {}
    for relative, digest in approval['source_sha256'].items():
        path = canonical(ROOT/relative)
        if sha(path) != digest: raise ValueError('released source closure hash mismatch: '+relative)
        source_bindings[str(path)] = digest
    bindings = {str(release): digest_text[:-1], str(sidecar): sha(sidecar)}
    for relative, digest in expected['input_complete_sha256'].items():
        path = canonical(location['project']/relative)
        if sha(path) != digest: raise ValueError('fixed support/parent input pin mismatch')
        bindings[str(path)] = digest
    support_root = location['project']/observed.SUPPORT
    marker = read(support_root/'COMPLETE.json')
    required = {'manifest.json', 'folds.json', 'report.json', 'STATUS.json'}
    if set(marker.get('files_sha256', {})) != required: raise ValueError('fixed observation support artifact inventory required')
    verify_marker(support_root, required_files=required)
    bindings.update({str(support_root/name): digest for name, digest in marker['files_sha256'].items()})
    report = read(support_root/'report.json'); manifest = read(support_root/'manifest.json')
    if (report.get('variation_prerequisite') is not True or report.get('totals', {}).get('prefixes') != 320
            or report.get('excluded_prefixes') != 0 or any(report.get(k) is not False for k in
                ('fitting_performed', 'outcomes_opened', 'successors_opened', 'models_opened', 'predictions_opened', 'fit_release_authorized'))):
        raise ValueError('unchanged full320 observation-only support required')
    if set(manifest.get('source_sha256', {})) != set(support.SOURCE_FILES):
        raise ValueError('exact inherited support source inventory required')
    for relative, digest in manifest['source_sha256'].items():
        if approval['source_sha256'].get(relative) != digest:
            raise ValueError('support and released feature source differ')
    if read(location['project']/support.PARENT/'COMPLETE.json').get('status') != 'complete':
        raise ValueError('completed frozen parent required')
    context = dict(source=state, release_sha256=digest_text[:-1], source_sha256=source_bindings,
                   input_sha256=bindings, runtime=RUNTIME, project=str(location['project']))
    recheck(context)
    return context


def recheck(context):
    if source_state() != context['source'] or runtime() != context['runtime']:
        raise ValueError('production source/runtime changed')
    for mapping in (context['source_sha256'], context['input_sha256']):
        for raw, digest in mapping.items():
            path = canonical(raw)
            if sha(path) != digest: raise ValueError('production source/input changed: '+raw)


def _metadata_preparation(location):
    """Never hash/read sibling label bodies: only immutable metadata files."""
    directory = location['prepared']; marker = read(directory/'COMPLETE.json')
    names = {'manifest.json', 'folds.json', *(f'fold-{f}/train-labels.json' for f in range(5)), 'assessment/all320-labels.json'}
    if (marker.get('status') != 'complete' or set(marker.get('files_sha256', {})) != names
            or marker.get('parent_complete_sha256') != engine.PARENT_COMPLETE_SHA256):
        raise ValueError('fixed six-label-file preparation seal required')
    for name in ('manifest.json', 'folds.json'):
        if sha(canonical(directory/name)) != marker['files_sha256'][name]: raise ValueError('preparation metadata changed')
    manifest = read(directory/'manifest.json'); folds = read(directory/'folds.json')
    if (manifest.get('kind') != 'repair_feedback_fold_label_materialization_v1' or manifest.get('train_prefixes') != 320
            or manifest.get('original_valid32_materialized') is not False or manifest.get('fitting_performed') is not False
            or manifest.get('parent_complete_sha256') != engine.PARENT_COMPLETE_SHA256
            or manifest.get('fold_assignment_sha256') != marker.get('fold_assignment_sha256')
            or set(manifest.get('source_sha256', {})) != labels.SOURCE_PATHS):
        raise ValueError('verified preparation metadata contract differs')
    source_binding = labels.canonical_hash(manifest['source_sha256'])
    contracts = {f: engine.LabelContract(marker['files_sha256'][f'fold-{f}/train-labels.json'],
        manifest['fold_assignment_sha256'], source_binding) for f in range(5)}
    contracts[None] = engine.LabelContract(marker['files_sha256']['assessment/all320-labels.json'],
        manifest['fold_assignment_sha256'], source_binding)
    return contracts, manifest, folds


def _load_inputs(location, context):
    components = observed.load_observed_components(location['project'])
    source_bindings = components.pop('source_bindings'); input_bindings = components.pop('input_bindings')
    components['parent_folds'] = {f: engine.ParentFold(**row) for f, row in components['parent_folds'].items()}
    inputs = engine.PreparedInputs(**components)  # synthetic is FALSE, not configurable
    if inputs.synthetic is not False: raise ValueError('synthetic production inputs forbidden')
    for raw, digest in source_bindings.items():
        if context['source_sha256'].get(raw) != digest: raise ValueError('observed source outside released source closure')
    provenance = dict(source_sha256=dict(context['source_sha256']), input_sha256={**context['input_sha256'], **input_bindings})
    engine.validate_inputs(inputs); engine._bindings(provenance)
    return inputs, provenance


def _artifact_paths(stage):
    if stage == 'preflight': return ()
    if stage == 'prepare': return tuple('prepared-v1/'+n for n in ('COMPLETE.json', 'manifest.json', 'folds.json'))
    if stage == 'initialize': return tuple('run-v1/'+n for n in ('FOLDS_COMPLETE.json', 'manifest.json', 'cohort.json', 'folds.json'))
    if stage.startswith('fold-'): return (f'run-v1/{stage}/COMPLETE.json', f'run-v1/{stage}/MODELS_COMPLETE.json')
    if stage == 'finalize': return ('run-v1/PREDICTIONS_COMPLETE.json', 'run-v1/predictions.json')
    if stage == 'assess': return tuple('run-v1/'+n for n in ('COMPLETE.json', 'assessment/COMPLETE.json', 'assessment/report.json', 'assessment/next_action.json'))
    if stage == 'audit': return ('supervised-v1/verified/COMPLETE.json', 'supervised-v1/verified/report.json')
    raise ValueError('unknown fixed stage')


def verify_wrapper(project, stage, *, deep=False):
    """Workers bind completion metadata only; supervisor deep-checks models.

    Even the deep path NEVER scans the six preparation label files. Their
    externally expected hashes are consumed only by the appropriate worker,
    the post-barrier assessor, and the final independent audit process.
    """
    location = paths(project); directory = canonical(location['supervisor']/'stages'/stage)
    if stage not in STAGES or (directory/'FAILED.json').exists(): raise ValueError('valid completed fixed stage required')
    verified = verify_marker(directory, required_files=('report.json',))
    marker = read(directory/'COMPLETE.json'); report = read(directory/'report.json')
    if set(marker['files_sha256']) != {'report.json'} or report.get('stage') != stage or report.get('status') != 'complete':
        raise ValueError('strict stage wrapper required')
    expected = {FAMILY+'/'+name for name in _artifact_paths(stage)}
    if set(report.get('engine_artifact_sha256', {})) != expected:
        raise ValueError('stage wrapper must bind its exact actual engine artifacts')
    for relative, digest in report['engine_artifact_sha256'].items():
        if sha(canonical(location['project']/relative)) != digest: raise ValueError('actual stage artifact changed')
    if stage == 'prepare':
        _metadata_preparation(location)  # hashes metadata only, never label bodies
    elif stage == 'initialize':
        seal = read(location['run']/'FOLDS_COMPLETE.json')
        if set(seal.get('files_sha256', {})) != {'manifest.json', 'cohort.json', 'folds.json'}:
            raise ValueError('actual initialization seal required')
        engine._verify_files(location['run'], seal['files_sha256'])
    elif stage.startswith('fold-'):
        seal = read(location['run']/stage/'COMPLETE.json')
        model_seal = read(location['run']/stage/'MODELS_COMPLETE.json')
        expected_files = {*(arm+'.json' for arm in engine.ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'}
        if (seal.get('status') != 'complete' or type(seal.get('completed_fits')) is not int or seal['completed_fits'] != 5
                or type(seal.get('fold')) is not int or seal['fold'] != int(stage[-1])
                or set(seal.get('files_sha256', {})) != expected_files
                or set(model_seal.get('model_files_sha256', {})) != {arm+'.json' for arm in engine.ARMS}
                or sha(location['run']/stage/'MODELS_COMPLETE.json') != seal['files_sha256']['MODELS_COMPLETE.json']):
            raise ValueError('actual fixed five-model fold seal required')
    elif stage == 'finalize':
        seal = read(location['run']/'PREDICTIONS_COMPLETE.json')
        if (seal.get('status') != 'all_folds_label_blind_predictions_complete' or seal.get('completed_fits') != 25
                or seal.get('recipients') != 320 or seal.get('methods') != list(engine.METHODS)
                or set(seal.get('fold_complete_sha256', {})) != {str(f) for f in range(5)}
                or sha(location['run']/'predictions.json') != seal.get('predictions_sha256')):
            raise ValueError('actual all25/all320 prediction barrier required')
        for f, digest in seal['fold_complete_sha256'].items():
            if sha(location['run']/f'fold-{f}/COMPLETE.json') != digest: raise ValueError('prediction fold marker changed')
    elif stage == 'assess':
        seal = read(location['run']/'COMPLETE.json')
        if seal.get('status') != 'complete' or seal.get('completed_fits') != 25 or seal.get('recipients') != 320 or seal.get('full_train_refits') != 0 or seal.get('model_promotion') is not False:
            raise ValueError('actual complete no-refit engine required')
    elif stage == 'audit':
        if read(location['verified']/'report.json').get('verified') is not True:
            raise ValueError('actual positive independent audit required')
    if deep and stage.startswith('fold-'):
        verify_marker(location['run']/stage, required_files=(*(arm+'.json' for arm in engine.ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'))
    elif deep and stage == 'assess':
        verify_marker(location['run'], required_files=('assessment/report.json', 'predictions.json', 'PREDICTIONS_COMPLETE.json'))
    elif deep and stage == 'audit':
        verify_marker(location['verified'], required_files=('report.json',))
    return dict(verified, report=report)


def _previous(location, stage, context):
    for previous in STAGES[:STAGES.index(stage)]:
        verified = verify_wrapper(location['project'], previous)
        report = verified['report']
        if report['source'] != context['source'] or report['release_sha256'] != context['release_sha256']:
            raise ValueError('previous stage belongs to another frozen release/source')


def _independent_audit(inputs, location, contracts, provenance):
    """All seals/barriers first; only then all fold labels in audit process."""
    from scripts import audit_zpd_repair_feedback_cv as auditor
    run = location['run']
    verify_marker(run, required_files=('manifest.json', 'cohort.json', 'predictions.json', 'PREDICTIONS_COMPLETE.json', 'assessment/report.json'))
    consumed_complete_sha256 = sha(run/'COMPLETE.json')
    if (run/'FAILED.json').exists(): raise ValueError('failed engine cannot be audited as complete')
    manifest = read(run/'manifest.json')
    expected = {str(f) if f is not None else 'assessment': vars(c) for f, c in contracts.items()}
    if manifest['label_contracts'] != expected or manifest['input_fingerprint'] != engine.input_fingerprint(inputs):
        raise ValueError('audit preparation/input differs from completed engine')
    predictions = engine._prediction_barrier(inputs, run, expected)
    observed_rows, banks, assignment, _, reader = support.load_inputs(location['project'])
    if assignment != inputs.assignment or {k: b.seal_sha256 for k, b in banks.items()} != {k: b.seal_sha256 for k, b in inputs.banks.items()}:
        raise ValueError('independent audit observed join differs')
    models = {f: {arm: read(run/f'fold-{f}'/(arm+'.json')) for arm in engine.ARMS} for f in range(5)}
    training_labels = {}
    for fold in range(5):
        train, _ = engine._scope(inputs, fold); bs = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
        training_labels[fold] = labels.load_fold_labels(location['prepared'], fold, bs,
            {ex.example_id: ex.bank_id for ex in train}, **vars(contracts[fold]))
    assessment_path = canonical(location['prepared']/'assessment/all320-labels.json')
    raw = assessment_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != contracts[None].expected_sha256: raise ValueError('audit assessment label hash differs')
    assessment_labels = labels.validate_assessment_envelope(json.loads(raw.decode('utf-8')), inputs.banks,
        {ex.example_id: ex.bank_id for ex in inputs.examples},
        expected_fold_assignment_sha256=contracts[None].expected_fold_assignment_sha256,
        expected_source_binding_sha256=contracts[None].expected_source_binding_sha256)
    result = auditor.audit_run(inputs, observed_rows, models, predictions, training_labels, assessment_labels,
        read(run/'assessment/report.json'), expected_input_fingerprint=manifest['input_fingerprint'],
        expected_label_contracts={f: vars(contracts[f]) for f in range(5)},
        expected_runtime={k: RUNTIME[k] for k in ('python', 'numpy', 'scipy')})
    if result.get('verified') is not True: raise ValueError('positive independent numerical/result audit required')
    # After all consumption/replay, recheck labels only in THIS audit process.
    for fold in range(5):
        if sha(location['prepared']/f'fold-{fold}/train-labels.json') != contracts[fold].expected_sha256:
            raise ValueError('audit training label drift')
    if sha(assessment_path) != contracts[None].expected_sha256: raise ValueError('audit assessment label drift')
    reader.recheck(); engine._bindings(provenance)
    verify_marker(run, required_files=('assessment/report.json', 'predictions.json'))
    if sha(run/'COMPLETE.json') != consumed_complete_sha256:
        raise ValueError('consumed experiment COMPLETE changed during independent audit')
    return dict(result, experiment_complete_sha256=consumed_complete_sha256)


def execute_stage(project, stage):
    if stage not in STAGES: raise ValueError('fixed one-stage execution required')
    location = paths(project); directory = canonical(location['supervisor']/'stages'/stage)
    if directory.exists(): raise ValueError('new stage wrapper required; no retry')
    context = preflight(project)  # Before output and any label access.
    verify_child_boundary()
    _previous(location, stage, context)
    directory.mkdir(parents=True)
    provenance = None
    try:
        if stage == 'preflight':
            inputs, provenance = _load_inputs(location, context)
            result = dict(recipients=len(inputs.examples), labels_opened=False, input_fingerprint=engine.input_fingerprint(inputs))
        elif stage == 'prepare':
            if location['prepared'].exists(): raise ValueError('new preparation path required')
            blobs = {}
            for relative in sorted(labels.SOURCE_PATHS):
                path = canonical(location['project']/relative)
                blobs[relative] = path.read_bytes()
            hashes = {name: hashlib.sha256(data).hexdigest() for name, data in blobs.items()}
            engine.prepare_labels(blobs, location['prepared'])
            del blobs
            for relative, digest in hashes.items():
                if sha(canonical(location['project']/relative)) != digest: raise ValueError('preparation raw source changed')
            result = dict(materialized_train_prefixes=320, original_valid32_materialized=False,
                          physical_original_valid32_container_verified=True, raw_source_sha256=hashes)
        else:
            inputs, provenance = _load_inputs(location, context)
            contracts, _, assignment = _metadata_preparation(location)
            if assignment != inputs.assignment or contracts[0].expected_fold_assignment_sha256 != inputs.fold_assignment_sha256:
                raise ValueError('preparation and observed parent folds differ')
            if stage == 'initialize':
                engine.initialize(inputs, location['run'], provenance=provenance, label_contracts=contracts)
                result = dict(recipients=320, planned_fits=25, label_bodies_opened=False)
            elif stage.startswith('fold-'):
                fold = int(stage[-1]); predicted = engine.fit_fold(inputs, fold, location['prepared'], contracts[fold], location['run'])
                result = dict(fold=fold, fitted_cells=5, predicted_examples=len(predicted), only_label_file=f'fold-{fold}/train-labels.json')
            elif stage == 'finalize':
                predicted = engine.finalize_predictions(inputs, location['run'])
                result = dict(recipients=len(predicted), fitted_cells=25, label_bodies_opened=False)
            elif stage == 'assess':
                report = engine.assess_predictions(inputs, location['run'], location['prepared'], contracts[None])
                result = dict(gate=report['gate'], recipients=320, full_train_refits=0)
            else:
                if location['verified'].exists(): raise ValueError('new independent verification path required')
                result = _independent_audit(inputs, location, contracts, provenance)
                location['verified'].mkdir()
                write(location['verified']/'report.json', result)
                # The inner audit seal follows the SAME source/runtime/prior
                # barriers as its outer wrapper, never preceding those checks.
                _previous(location, stage, context); recheck(context); engine._bindings(provenance)
                verify_marker(location['run'], required_files=('assessment/report.json', 'predictions.json'))
                if sha(location['run']/'COMPLETE.json') != result['experiment_complete_sha256']:
                    raise ValueError('audited experiment changed before inner audit seal')
                engine._seal(location['verified'], ['report.json'], verified=True)
        # Stage wrappers bind real immutable engine outputs, not exit status.
        artifacts = {FAMILY+'/'+name: sha(canonical(location['family']/name)) for name in _artifact_paths(stage)}
        report = dict(kind='repair_feedback_production_stage_v1', stage=stage, status='complete',
            source=context['source'], release_sha256=context['release_sha256'], runtime=RUNTIME,
            result=result, engine_artifact_sha256=artifacts, retries=0, model_promotion=False)
        write(directory/'report.json', report)
        _previous(location, stage, context)
        if provenance is not None: engine._bindings(provenance)
        recheck(context)
        for relative, digest in artifacts.items():
            if sha(canonical(location['project']/relative)) != digest: raise ValueError('engine artifacts drifted before wrapper seal')
        engine._seal(directory, ['report.json'], stage=stage)
        return report
    except BaseException as error:
        write(directory/'FAILED.json', dict(stage=stage, error_type=type(error).__name__, error=str(error), retry_authorized=False))
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--stage', choices=STAGES, required=True)
    args = parser.parse_args(argv)
    return execute_stage(args.project, args.stage)


if __name__ == '__main__':
    main()
