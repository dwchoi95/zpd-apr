"""Fixed directed144 production boundary; one child stage, no prepare or retry.

The separately authored tracked release and strict SHA256 sidecar must exist
in the same clean committed snapshot. Reuse the six already sealed label files
read-only; metadata checks never hash sibling or assessment label bodies.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from scripts import audit_zpd_repair_directed_support as support
from scripts import audit_zpd_repair_feedback_support as ancestry
from scripts import guard_zpd_repair_feedback as frozen
from scripts import run_zpd_repair_directed_cv as engine
from scripts import zpd_repair_directed_history as directed
from scripts import zpd_repair_directed_inputs as observed
from scripts import zpd_repair_feedback_labels as labels
from scripts import zpd_repair_residual_core as core
from scripts.supervise_zpd_history_action import verify_marker

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('/home/cdw/VSCode/zpd-apr')
FAMILY = 'outputs/zpd-repair-directed-history-20260924'
PREPARED = 'outputs/zpd-repair-feedback-20260924/prepared-v1'
PREPARED_COMPLETE_SHA256 = '71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e'
RELEASE = 'analysis_protocols/zpd-repair-directed-fit-release-20260924.json'
SIDECAR = RELEASE+'.sha256'
PROTOCOL = 'analysis_protocols/zpd-repair-directed-history-prospective-20260924.md'
STAGES = ('preflight', 'initialize', *(f'fold-{f}' for f in range(5)), 'finalize', 'assess', 'audit')
RUNTIME = dict(python='3.13.11', numpy='2.5.2', scipy='1.18.1', sklearn='1.9.0')
CHILD_MEMORY_BYTES = 32*1024**3
BLAS_ENVIRONMENT = frozen.BLAS_ENVIRONMENT
SOURCE_FILES = tuple(sorted(set((*frozen.SOURCE_FILES, *support.SOURCE_FILES, *observed.LOCAL_SOURCES,
    'scripts/run_zpd_repair_directed_cv.py', 'scripts/audit_zpd_repair_directed_independent.py',
    'scripts/guard_zpd_repair_directed.py', 'scripts/supervise_zpd_repair_directed.py',
    'tests/test_zpd_repair_residual_core.py', 'tests/test_zpd_repair_directed_inputs.py',
    'tests/test_zpd_repair_directed_cv.py', 'tests/test_zpd_repair_directed_independent.py',
    'tests/test_zpd_repair_directed_guard.py', 'tests/test_zpd_repair_directed_supervisor.py',
    'analysis_protocols/zpd-repair-directed-fit-integration-plan-20260924.md', PROTOCOL))))

# Only dimension/path-family-independent reviewed primitives are reused.
canonical = frozen.canonical
sha = frozen.sha
read = frozen.read
write = frozen.write
runtime = frozen.runtime
verify_child_boundary = frozen.verify_child_boundary
_same = frozen._same


def source_state():
    if canonical(ROOT) != ROOT or subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=all'], cwd=ROOT, text=True).strip():
        raise ValueError('clean committed source snapshot required')
    return dict(revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                tree=subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip())


def paths(project):
    project = canonical(project)
    if project != PROJECT: raise ValueError('fixed canonical production project required')
    family = canonical(project/FAMILY)
    return dict(project=project, family=family, prepared=canonical(project/PREPARED),
                run=canonical(family/'run-v1'), supervisor=canonical(family/'supervised-v1'),
                verified=canonical(family/'supervised-v1/verified'))


def release_configuration():
    return dict(primary='H', arms=list(engine.ARMS), folds=5, recipients=320, fits=25,
        methods=list(engine.METHODS), dimension=144, representation=directed.configuration(),
        offset=core.configuration(engine.SPEC),
        candidate_space='all_original_train320_banks_with_fixed8_terminal_attempts',
        base='same_fold_frozen_structural_C_additive_coefficient_one',
        full_train_refits=0, automatic_retries=0, model_promotion=False, process_stages=list(STAGES),
        prepared_labels='read_only_reuse_exact_six_original_files', preparation_permitted=False,
        new_label_files=0, original_valid32_materialized=False, original_mixed_cache_reopened=False,
        child_memory_bytes=CHILD_MEMORY_BYTES, blas_threads=1, heartbeat_seconds=30,
        stage_timeout_seconds={stage: 3600 if stage.startswith('fold-') or stage == 'audit' else 900 for stage in STAGES})


def _metadata_preparation(location):
    directory = location['prepared']
    if sha(canonical(directory/'COMPLETE.json')) != PREPARED_COMPLETE_SHA256:
        raise ValueError('exact reused preparation COMPLETE pin required')
    # This frozen helper reads ONLY COMPLETE/manifest/folds and constructs six
    # contracts from hashes. It never opens or hashes any of the label bodies.
    contracts, manifest, folds = frozen._metadata_preparation(location)
    for contract in contracts.values():
        for digest in vars(contract).values():
            if type(digest) is not str or re.fullmatch('[0-9a-f]{64}', digest) is None:
                raise ValueError('strict externally sealed preparation contract hashes required')
    return contracts, manifest, folds


def _serialized_contracts(contracts):
    return {str(f) if f is not None else 'assessment': vars(value) for f, value in contracts.items()}


def preflight(project):
    """Read-only: reject unreleased/source/runtime drift before outputs/labels."""
    location = paths(project)
    if not ROOT.is_relative_to(location['project']/'.runtime'):
        raise ValueError('clean source snapshot must be beneath canonical project .runtime')
    state = source_state(); release = canonical(ROOT/RELEASE); sidecar = canonical(ROOT/SIDECAR)
    if not release.is_file() or not sidecar.is_file():
        raise RuntimeError('directed144 is unreleased: fixed tracked release and sidecar required')
    tracked = (RELEASE, SIDECAR, *SOURCE_FILES)
    output = subprocess.check_output(['git', 'ls-files', '--error-unmatch', '--', *tracked], cwd=ROOT, text=True)
    if set(output.splitlines()) != set(tracked): raise ValueError('exact tracked release/source closure required')
    digest = sidecar.read_text(encoding='ascii')
    if re.fullmatch('[0-9a-f]{64}\n', digest) is None or sha(release) != digest[:-1]:
        raise ValueError('strict release SHA256 sidecar mismatch')
    if runtime() != RUNTIME: raise ValueError('fixed production numerical runtime required')
    approval = read(release)
    pins = {observed.SUPPORT+'/COMPLETE.json': engine.SUPPORT_COMPLETE_SHA256,
            ancestry.PARENT+'/COMPLETE.json': engine.PARENT_COMPLETE_SHA256,
            PREPARED+'/COMPLETE.json': PREPARED_COMPLETE_SHA256}
    bindings = {str(release): digest[:-1], str(sidecar): sha(sidecar)}
    for relative, expected in pins.items():
        path = canonical(location['project']/relative)
        if sha(path) != expected: raise ValueError('fixed support/parent/preparation input pin mismatch')
        bindings[str(path)] = expected
    contracts, _, prepared_folds = _metadata_preparation(location)
    prep_metadata = {PREPARED+'/'+name: sha(canonical(location['prepared']/name)) for name in ('manifest.json', 'folds.json')}
    expected = dict(kind='repair_directed_fixed25_fit_release_v1', project=str(PROJECT), family=FAMILY,
        fit_release_authorized=True, confirmatory=False, fresh_test_opened=False, runtime=RUNTIME,
        input_complete_sha256=pins, prepared_metadata_sha256=prep_metadata,
        prepared_label_contracts=_serialized_contracts(contracts),
        protocol_sha256=sha(ROOT/PROTOCOL), configuration=release_configuration())
    if (type(approval) is not dict or set(approval) != set(expected) | {'source_sha256', 'decision_reason'}
            or any(not _same(approval[k], v) for k, v in expected.items())
            or type(approval['decision_reason']) is not str or not approval['decision_reason'].strip()
            or type(approval['source_sha256']) is not dict or set(approval['source_sha256']) != set(SOURCE_FILES)):
        raise ValueError('strict complete directed release schema/configuration required')
    sources = {}
    for relative, expected_sha in approval['source_sha256'].items():
        path = canonical(ROOT/relative)
        if sha(path) != expected_sha: raise ValueError('released source closure hash mismatch: '+relative)
        sources[str(path)] = expected_sha
    bindings.update({str(location['project']/name): value for name, value in prep_metadata.items()})
    support_root = location['project']/observed.SUPPORT
    complete = read(support_root/'COMPLETE.json')
    if set(complete.get('files_sha256', {})) != observed.FILES: raise ValueError('exact directed source-support inventory required')
    verify_marker(support_root, required_files=observed.FILES)
    saved = {name: read(canonical(support_root/name)) for name in observed.FILES}
    observed._validate_headers(complete, saved)
    bindings.update({str(support_root/name): value for name, value in complete['files_sha256'].items()})
    if not _same(prepared_folds, saved['folds.json']): raise ValueError('reused labels and directed support folds differ')
    manifest = saved['manifest.json']
    if set(manifest.get('source_sha256', {})) != set(support.SOURCE_FILES): raise ValueError('exact inherited support source inventory required')
    for relative, expected_sha in manifest['source_sha256'].items():
        if approval['source_sha256'].get(relative) != expected_sha: raise ValueError('support and released feature source differ')
    if read(location['project']/ancestry.PARENT/'COMPLETE.json').get('status') != 'complete':
        raise ValueError('completed frozen parent required')
    context = dict(source=state, release_sha256=digest[:-1], source_sha256=sources, input_sha256=bindings,
                   runtime=RUNTIME, project=str(location['project']), label_contracts=_serialized_contracts(contracts))
    recheck(context)
    return context


def recheck(context):
    if source_state() != context['source'] or runtime() != context['runtime']: raise ValueError('production source/runtime changed')
    for mapping in (context['source_sha256'], context['input_sha256']):
        for raw, expected in mapping.items():
            if sha(canonical(raw)) != expected: raise ValueError('production source/input changed: '+raw)


def _load_inputs(location, context):
    components = observed.load_observed_components(location['project'])
    sources = components.pop('source_bindings'); bindings = components.pop('input_bindings')
    if not _same(components.pop('feature_configuration'), directed.configuration()):
        raise ValueError('loader representation differs from released directed configuration')
    components['parent_folds'] = {f: engine.ParentFold(**row) for f, row in components['parent_folds'].items()}
    inputs = engine.PreparedInputs(**components)
    if inputs.synthetic is not False: raise ValueError('synthetic production inputs forbidden')
    for raw, digest in sources.items():
        if context['source_sha256'].get(raw) != digest: raise ValueError('input source outside released closure')
    overlap = set(bindings) & set(context['input_sha256'])
    if any(bindings[name] != context['input_sha256'][name] for name in overlap): raise ValueError('conflicting input binding')
    provenance = dict(source_sha256=dict(context['source_sha256']), input_sha256={**context['input_sha256'], **bindings})
    engine.validate_inputs(inputs); engine._bindings(provenance)
    return inputs, provenance


def _artifact_paths(stage):
    if stage == 'preflight': return ()
    if stage == 'initialize': return tuple('run-v1/'+name for name in ('FOLDS_COMPLETE.json', 'manifest.json', 'cohort.json', 'folds.json'))
    if stage.startswith('fold-'): return (f'run-v1/{stage}/COMPLETE.json', f'run-v1/{stage}/MODELS_COMPLETE.json')
    if stage == 'finalize': return ('run-v1/PREDICTIONS_COMPLETE.json', 'run-v1/predictions.json')
    if stage == 'assess': return tuple('run-v1/'+name for name in ('COMPLETE.json', 'assessment/COMPLETE.json', 'assessment/report.json', 'assessment/next_action.json'))
    if stage == 'audit': return ('supervised-v1/verified/COMPLETE.json', 'supervised-v1/verified/report.json')
    raise ValueError('unknown fixed stage; preparation is forbidden')


def verify_wrapper(project, stage, *, deep=False):
    """Shallow worker checks never open prior fitted models or label bodies."""
    location = paths(project); directory = canonical(location['supervisor']/'stages'/stage)
    if stage not in STAGES or (directory/'FAILED.json').exists(): raise ValueError('valid completed fixed stage required')
    verified = verify_marker(directory, required_files=('report.json',))
    marker = read(directory/'COMPLETE.json'); report = read(directory/'report.json')
    if set(marker['files_sha256']) != {'report.json'} or report.get('stage') != stage or report.get('status') != 'complete':
        raise ValueError('strict stage wrapper required')
    expected = {FAMILY+'/'+name for name in _artifact_paths(stage)}
    if set(report.get('engine_artifact_sha256', {})) != expected: raise ValueError('wrapper must bind exact actual engine artifacts')
    for relative, digest in report['engine_artifact_sha256'].items():
        if sha(canonical(location['project']/relative)) != digest: raise ValueError('actual stage artifact changed')
    if stage == 'initialize':
        seal = read(location['run']/'FOLDS_COMPLETE.json')
        if set(seal.get('files_sha256', {})) != {'manifest.json', 'cohort.json', 'folds.json'}: raise ValueError('actual initialization seal required')
        engine._verify_files(location['run'], seal['files_sha256'])
    elif stage.startswith('fold-'):
        seal = read(location['run']/stage/'COMPLETE.json'); models = read(location['run']/stage/'MODELS_COMPLETE.json')
        names = {*(arm+'.json' for arm in engine.ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'}
        if (seal.get('status') != 'complete' or type(seal.get('completed_fits')) is not int or seal['completed_fits'] != 5
                or type(seal.get('fold')) is not int or seal['fold'] != int(stage[-1])
                or set(seal.get('files_sha256', {})) != names
                or set(models.get('model_files_sha256', {})) != {arm+'.json' for arm in engine.ARMS}
                or sha(location['run']/stage/'MODELS_COMPLETE.json') != seal['files_sha256']['MODELS_COMPLETE.json']):
            raise ValueError('actual five-model fold seal required')
    elif stage == 'finalize':
        seal = read(location['run']/'PREDICTIONS_COMPLETE.json')
        if (seal.get('status') != 'all_folds_label_blind_predictions_complete' or seal.get('completed_fits') != 25
                or seal.get('recipients') != 320 or seal.get('methods') != list(engine.METHODS)
                or set(seal.get('fold_complete_sha256', {})) != {str(f) for f in range(5)}
                or sha(location['run']/'predictions.json') != seal.get('predictions_sha256')):
            raise ValueError('actual all25/all320 prediction barrier required')
        for fold, digest in seal['fold_complete_sha256'].items():
            if sha(location['run']/f'fold-{fold}/COMPLETE.json') != digest: raise ValueError('prediction fold marker changed')
    elif stage == 'assess':
        seal = read(location['run']/'COMPLETE.json')
        if (seal.get('status') != 'complete' or seal.get('completed_fits') != 25 or seal.get('recipients') != 320
                or seal.get('full_train_refits') != 0 or seal.get('model_promotion') is not False):
            raise ValueError('actual complete no-refit engine required')
    elif stage == 'audit':
        if read(location['verified']/'report.json').get('verified') is not True: raise ValueError('actual positive independent audit required')
    if deep and stage.startswith('fold-'):
        verify_marker(location['run']/stage, required_files=(*(arm+'.json' for arm in engine.ARMS), 'MODELS_COMPLETE.json', 'predictions.json', 'STATUS.json'))
    elif deep and stage == 'assess': verify_marker(location['run'], required_files=('assessment/report.json', 'predictions.json', 'PREDICTIONS_COMPLETE.json'))
    elif deep and stage == 'audit': verify_marker(location['verified'], required_files=('report.json',))
    return dict(verified, report=report)


def _previous(location, stage, context):
    for previous in STAGES[:STAGES.index(stage)]:
        report = verify_wrapper(location['project'], previous)['report']
        if report['source'] != context['source'] or report['release_sha256'] != context['release_sha256']:
            raise ValueError('previous stage belongs to another source/release')


def _independent_audit(inputs, location, contracts, provenance):
    from scripts import audit_zpd_repair_directed_independent as auditor
    run = location['run']
    verify_marker(run, required_files=('manifest.json', 'cohort.json', 'predictions.json', 'PREDICTIONS_COMPLETE.json', 'assessment/report.json'))
    consumed_complete = sha(run/'COMPLETE.json')
    if (run/'FAILED.json').exists(): raise ValueError('failed engine cannot be audited as complete')
    manifest = read(run/'manifest.json'); expected = _serialized_contracts(contracts)
    if manifest['label_contracts'] != expected or manifest['input_fingerprint'] != engine.input_fingerprint(inputs):
        raise ValueError('audit preparation/input differs from completed engine')
    predictions = engine._prediction_barrier(inputs, run, expected)  # Before ANY labels.
    models = {f: {arm: read(run/f'fold-{f}'/(arm+'.json')) for arm in engine.ARMS} for f in range(5)}
    training = {}
    for fold in range(5):
        train, _ = engine._scope(inputs, fold); banks = {ex.bank_id: inputs.banks[ex.bank_id] for ex in train}
        training[fold] = labels.load_fold_labels(location['prepared'], fold, banks,
            {ex.example_id: ex.bank_id for ex in train}, **vars(contracts[fold]))
    path = canonical(location['prepared']/'assessment/all320-labels.json'); raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != contracts[None].expected_sha256: raise ValueError('audit assessment hash differs')
    assessment = labels.validate_assessment_envelope(json.loads(raw.decode('utf-8')), inputs.banks,
        {ex.example_id: ex.bank_id for ex in inputs.examples},
        expected_fold_assignment_sha256=contracts[None].expected_fold_assignment_sha256,
        expected_source_binding_sha256=contracts[None].expected_source_binding_sha256)
    result = auditor.audit_run(inputs, inputs.observations, models, predictions, training, assessment,
        read(run/'assessment/report.json'), expected_input_fingerprint=manifest['input_fingerprint'],
        expected_label_contracts={f: vars(contracts[f]) for f in range(5)},
        expected_runtime={key: RUNTIME[key] for key in ('python', 'numpy', 'scipy')})
    if result.get('verified') is not True: raise ValueError('positive independent numerical/result audit required')
    verify_audit_label_inputs(location, contracts)
    engine._bindings(provenance)
    verify_marker(run, required_files=('assessment/report.json', 'predictions.json'))
    if sha(run/'COMPLETE.json') != consumed_complete: raise ValueError('consumed experiment COMPLETE changed during audit')
    return dict(result, experiment_complete_sha256=consumed_complete)


def verify_audit_label_inputs(location, contracts):
    """Audit-only terminal check AFTER all prediction/assessment barriers.

    Never call from preflight, a fold worker, or the label-blind finalize stage.
    The guard and supervisor invoke this only after a completed numerical audit.
    """
    if type(contracts) is not dict or set(contracts) != {0, 1, 2, 3, 4, None}:
        raise ValueError('all six externally expected audit label contracts required')
    for fold, contract in contracts.items():
        relative = 'assessment/all320-labels.json' if fold is None else f'fold-{fold}/train-labels.json'
        if sha(canonical(location['prepared']/relative)) != contract.expected_sha256:
            raise ValueError('audit consumed label drift: '+relative)


def execute_stage(project, stage):
    if stage not in STAGES: raise ValueError('fixed one-stage execution required; preparation forbidden')
    location = paths(project); directory = canonical(location['supervisor']/'stages'/stage)
    if directory.exists(): raise ValueError('new stage wrapper required; no retry')
    context = preflight(project)
    verify_child_boundary(); _previous(location, stage, context)
    directory.mkdir(parents=True)
    try:
        inputs, provenance = _load_inputs(location, context)
        contracts, _, assignment = _metadata_preparation(location)
        if (_serialized_contracts(contracts) != context['label_contracts'] or assignment != inputs.assignment
                or contracts[0].expected_fold_assignment_sha256 != inputs.fold_assignment_sha256):
            raise ValueError('released preparation and observed parent folds differ')
        if stage == 'preflight':
            result = dict(recipients=len(inputs.examples), labels_opened=False, label_bodies_opened=False,
                          reused_preparation_complete_sha256=PREPARED_COMPLETE_SHA256, input_fingerprint=engine.input_fingerprint(inputs))
        elif stage == 'initialize':
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
            location['verified'].mkdir(); write(location['verified']/'report.json', result)
            _previous(location, stage, context); engine._bindings(provenance); recheck(context)
            verify_marker(location['run'], required_files=('assessment/report.json', 'predictions.json'))
            if sha(location['run']/'COMPLETE.json') != result['experiment_complete_sha256']:
                raise ValueError('audited experiment changed before inner seal')
            verify_audit_label_inputs(location, contracts)
            engine._seal(location['verified'], ['report.json'], verified=True)
        artifacts = {FAMILY+'/'+name: sha(canonical(location['family']/name)) for name in _artifact_paths(stage)}
        report = dict(kind='repair_directed_production_stage_v1', stage=stage, status='complete', source=context['source'],
            release_sha256=context['release_sha256'], runtime=RUNTIME, result=result, engine_artifact_sha256=artifacts,
            reused_preparation_complete_sha256=PREPARED_COMPLETE_SHA256, retries=0, model_promotion=False)
        write(directory/'report.json', report)
        _previous(location, stage, context); engine._bindings(provenance); recheck(context)
        for relative, digest in artifacts.items():
            if sha(canonical(location['project']/relative)) != digest: raise ValueError('engine artifact drift before wrapper seal')
        if stage == 'audit': verify_audit_label_inputs(location, contracts)
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


if __name__ == '__main__': main()
