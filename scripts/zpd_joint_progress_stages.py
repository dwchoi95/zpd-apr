"""Coordinator-only joint4131 artifact stages; no production entry point.

The trusted external supervisor authenticates release/source/runtime/input pins
and provides recheck. It alone schedules the five own-capsule worker processes.
This module creates their metadata, seals every prediction before assessment,
and preserves failures. It never trains, generates or executes a candidate.

Implementation-stage component, not an empirical release. A separate reviewed
provider must bind the old progress32 architecture comparison to its fixed seal;
the callback here is a trusted coordinator boundary, not artifact authentication.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts import run_zpd_joint_progress_cv as worker
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_assessment as assessment
from scripts import zpd_repair_feedback_labels as provider
from scripts.run_zpd_repair_feedback_cv import LabelContract
from scripts.zpd_statement_sample_replay import decode_json

JOB_KIND = 'joint_progress4131_own_fold_job_v1'
INITIAL_FILES = ('manifest.json', 'cohort.json', 'folds.json')
JOB_SOURCE_FIELDS = {'source_state', 'source_root', 'source_sha256', 'runtime', 'controller_native'}
sha = worker.sha
write = worker.write
canonical = worker.canonical


def same(left, right):
    return json.dumps(left, sort_keys=True, separators=(',', ':'), allow_nan=False) == \
           json.dumps(right, sort_keys=True, separators=(',', ':'), allow_nan=False)


def read(path): return decode_json(canonical(path).read_bytes())


def _hash(value):
    if not capsule.original._sha(value): raise ValueError('exact SHA256 required')
    return value


def _valid_inputs(inputs):
    if type(inputs) is not dict or set(inputs) != set(range(5)) or any(type(k) is not int for k in inputs):
        raise ValueError('exact five own-fold projections required')
    cohort = None; common = None; fingerprints = {}
    private = {'fold', 'parent_predictions', 'parent_training', 'parent_structure_model_sha256'}
    for fold in range(5):
        value = inputs[fold]
        if value.fold != fold: raise ValueError('own-fold projection index differs')
        current = capsule.validate_inputs(value)
        encoded = capsule.encode_inputs(value)
        shared = {k: v for k, v in encoded.items() if k not in private}
        if common is not None and (not same(current, cohort) or not same(shared, common)):
            raise ValueError('all folds must retain identical observations, candidates, assignments and six-arm features')
        cohort = current; common = shared; fingerprints[str(fold)] = capsule.fingerprint(value)
    return cohort, fingerprints


def _contracts(inputs, contracts):
    if type(contracts) is not dict or set(contracts) != {*range(5), None}:
        raise ValueError('coordinator requires all six externally authenticated original label contracts')
    result = {str(f) if f is not None else 'assessment': worker.contract_values(v, inputs[0]) for f, v in contracts.items()}
    if len({v['expected_source_binding_sha256'] for v in result.values()}) != 1:
        raise ValueError('all original contracts must share the same source binding')
    return result


def _failure(directory, error):
    for name in ('INITIALIZATION_COMPLETE.json', 'JOBS_COMPLETE.json', 'PREDICTIONS_COMPLETE.json', 'COMPLETE.json'):
        path = directory/name
        if path.exists():
            rejected = directory/('REJECTED_'+name)
            if rejected.exists(): raise ValueError('prior rejected marker cannot be overwritten') from error
            path.rename(rejected)
    failed = directory/'FAILED.json'
    if not failed.exists():
        write(failed, dict(status='failed', error_type=type(error).__name__, error=str(error), automatic_retries=0,
                           model_promotion=False))


def _files(directory, expected, *, exact_inventory=False):
    if type(expected) is not dict or not expected: raise ValueError('nonempty exact file bindings required')
    parents = {canonical(directory)}
    for name in expected:
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or str(relative) != name:
            raise ValueError('canonical relative artifact name required')
        parents.add(canonical(directory/relative).parent)
    def live():
        for parent in parents:
            if (parent/'FAILED.json').exists() or any(parent.glob('REJECTED_*')):
                raise ValueError('failed or rejected artifact directory cannot advance')
    live()
    for name, pin in expected.items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts or str(relative) != name:
            raise ValueError('canonical relative artifact name required')
        _hash(pin)
        if sha(directory/name) != pin: raise ValueError('sealed artifact changed: '+name)
    if exact_inventory and {p.name for p in directory.iterdir()} != set(expected)|{'COMPLETE.json'}:
        raise ValueError('unexpected completed fold inventory')
    live()


def _fold_files(run, markers):
    """Cheap terminal check against already consumed, externally retained seals."""
    if type(markers) is not dict or set(markers) != {str(f) for f in range(5)}:
        raise ValueError('all five consumed fold receipts required')
    for fold in range(5):
        directory = run/f'fold-{fold}'; path = directory/'COMPLETE.json'
        raw = canonical(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != markers[str(fold)]: raise ValueError('consumed fold completion changed')
        marker = decode_json(raw)
        if set(marker['files_sha256']) != set(worker.FILES): raise ValueError('exact own-fold file set required')
        _files(directory, marker['files_sha256'], exact_inventory=True)
        if sha(path) != markers[str(fold)]: raise ValueError('consumed fold completion changed during terminal check')


def initialize(inputs, contracts, family, *, job_source, authority, provenance, recheck):
    """Coordinator metadata only; label body I/O is never performed here.

    `authority` contains only release/readiness/parent COMPLETE hashes. The
    initialization hash is added after sealing the global metadata, avoiding
    circular job hashes. Workers receive only their job path and external SHA.
    """
    family = canonical(family); run = canonical(family/'run-v1'); jobs = canonical(family/'jobs')
    if run.exists() or jobs.exists(): raise ValueError('fresh fixed run and job directories required; no retry')
    if not callable(recheck): raise ValueError('external coordinator boundary required')
    if type(job_source) is not dict or set(job_source) != JOB_SOURCE_FIELDS:
        raise ValueError('exact externally verified job source/runtime metadata required')
    if type(authority) is not dict or set(authority) != {'release_sha256', 'readiness_complete_sha256', 'parent_complete_sha256'}:
        raise ValueError('exact external release/readiness/parent authority required')
    for value in authority.values(): _hash(value)
    cohort, fingerprints = _valid_inputs(inputs); saved_contracts = _contracts(inputs, contracts)
    if any(v.readiness_complete_sha256 != authority['readiness_complete_sha256'] for v in inputs.values()):
        raise ValueError('accepted readiness authority differs from supplied features')
    recheck(); run.mkdir(parents=True, exist_ok=False)
    context = dict(run=run, jobs=jobs, family=family, inputs=inputs, contracts=contracts,
                   fingerprints=fingerprints, recheck=recheck, source=job_source, authority=authority)
    try:
        jobs.mkdir(exist_ok=False)
        manifest = dict(kind='joint_progress4131_coordinator_manifest_v1', authority=authority,
            source=job_source, provenance=provenance, input_fingerprints=fingerprints,
            label_contracts=saved_contracts, arms=list(worker.ARMS), methods=list(worker.METHODS), fits=35,
            full_train_refits=0, automatic_retries=0, model_promotion=False, worker_reads_global_manifest=False,
            synthetic=inputs[0].synthetic)
        initial_pins = {'manifest.json': write(run/'manifest.json', manifest),
                        'cohort.json': write(run/'cohort.json', cohort),
                        'folds.json': write(run/'folds.json', inputs[0].assignment)}
        context['manifest'] = manifest
        init = dict(kind='joint_progress4131_initialization_complete_v1', files_sha256=initial_pins)
        recheck()
        if _valid_inputs(inputs)[1] != fingerprints: raise ValueError('input drift during initialization')
        if {path.name for path in run.iterdir()} != set(INITIAL_FILES):
            raise ValueError('exact initial metadata inventory required')
        _files(run, initial_pins)
        context['initialization_sha256'] = write(run/'INITIALIZATION_COMPLETE.json', init)
        _files(run, initial_pins)
        job_hashes = {}
        for fold in range(5):
            body = dict(kind=JOB_KIND, fold=fold, inputs=capsule.encode_inputs(inputs[fold]),
                own_label_contract=saved_contracts[str(fold)], **job_source,
                authority=dict(authority, initialization_sha256=context['initialization_sha256']))
            job_hashes[str(fold)] = write(jobs/f'fold-{fold}.json', body)
        context['job_sha256'] = job_hashes
        context['jobs_complete_sha256'] = write(run/'JOBS_COMPLETE.json', dict(kind='joint_progress4131_jobs_complete_v1',
            initialization_sha256=context['initialization_sha256'], job_sha256=job_hashes))
        verify_initialization(context)
        return context
    except BaseException as error:
        _failure(run, error); raise


def verify_initialization(context):
    """Coordinator-only; deliberately never invoked by a fold worker."""
    run = context['run']; jobs = context['jobs']; inputs = context['inputs']
    if (run/'FAILED.json').exists() or any(run.glob('REJECTED_*')):
        raise ValueError('failed or rejected run cannot advance')
    context['recheck']()
    if _valid_inputs(inputs)[1] != context['fingerprints']: raise ValueError('projected inputs changed')
    if sha(run/'INITIALIZATION_COMPLETE.json') != context['initialization_sha256']:
        raise ValueError('externally retained initialization hash changed')
    init = read(run/'INITIALIZATION_COMPLETE.json')
    if set(init) != {'kind', 'files_sha256'} or init['kind'] != 'joint_progress4131_initialization_complete_v1' \
            or set(init['files_sha256']) != set(INITIAL_FILES): raise ValueError('strict initialization inventory required')
    _files(run, init['files_sha256'])
    if not same(read(run/'manifest.json'), context['manifest']): raise ValueError('coordinator manifest changed')
    if not same(read(run/'cohort.json'), capsule.validate_inputs(inputs[0])) \
            or not same(read(run/'folds.json'), inputs[0].assignment):
        raise ValueError('coordinator cohort/folds differ from original supplied membership')
    if not same(_contracts(inputs, context['contracts']), context['manifest']['label_contracts']):
        raise ValueError('externally initialized label contracts changed')
    if not same(context['source'], context['manifest']['source']) or not same(context['authority'], context['manifest']['authority']):
        raise ValueError('externally initialized source or authority changed')
    if sha(run/'JOBS_COMPLETE.json') != context['jobs_complete_sha256']:
        raise ValueError('externally retained job index hash changed')
    if not same(read(run/'JOBS_COMPLETE.json'), dict(kind='joint_progress4131_jobs_complete_v1',
            initialization_sha256=context['initialization_sha256'], job_sha256=context['job_sha256'])):
        raise ValueError('strict five-job index required')
    if {p.name for p in jobs.iterdir()} != {f'fold-{f}.json' for f in range(5)}:
        raise ValueError('exact five-job directory required')
    for f in range(5):
        if sha(jobs/f'fold-{f}.json') != context['job_sha256'][str(f)]: raise ValueError('own job changed')
    context['recheck']()
    _files(run, init['files_sha256'])
    if sha(run/'INITIALIZATION_COMPLETE.json') != context['initialization_sha256'] \
            or sha(run/'JOBS_COMPLETE.json') != context['jobs_complete_sha256']:
        raise ValueError('initialization receipts changed at terminal boundary')
    for f in range(5):
        if sha(jobs/f'fold-{f}.json') != context['job_sha256'][str(f)]: raise ValueError('own job changed at terminal boundary')


def fold_predictions(context):
    """All thirty-five model/contract checks and score replay; no label reads."""
    verify_initialization(context); rows = []; markers = {}; artifact_pins = {}
    for fold in range(5):
        inputs = context['inputs'][fold]; directory = context['run']/f'fold-{fold}'
        marker_raw = canonical(directory/'COMPLETE.json').read_bytes()
        marker = decode_json(marker_raw); markers[str(fold)] = hashlib.sha256(marker_raw).hexdigest()
        expected = dict(status='complete', kind='joint_progress4131_fold_complete_v1', fold=fold,
            completed_fits=7, predicted_examples=len(capsule.scope(inputs)[1]),
            input_fingerprint=context['fingerprints'][str(fold)], automatic_retries=0)
        if (type(marker) is not dict or set(marker) != set(expected)|{'files_sha256'}
                or any(not same(marker[k], v) for k, v in expected.items())
                or set(marker['files_sha256']) != set(worker.FILES)):
            raise ValueError('exact completed seven-model fold marker required')
        _files(directory, marker['files_sha256'], exact_inventory=True)
        artifact_pins[str(fold)] = dict(marker['files_sha256'])
        transform = worker.decode_transform(read(directory/'SCALER.json'))
        worker.validate_transform(transform, inputs)
        models = {arm: read(directory/(arm+'.json')) for arm in worker.ARMS}
        contract = worker.contract_values(context['contracts'][fold], inputs)
        for arm, model in models.items():
            worker.validate_model(model, inputs, arm, transform)
            if not same(model['label_contract'], contract): raise ValueError('model own-label contract differs from coordinator authority')
        train, held = capsule.scope(inputs)
        models_marker = dict(fold=fold, model_files_sha256={a+'.json': marker['files_sha256'][a+'.json'] for a in worker.ARMS},
            scaler_file_sha256=marker['files_sha256']['SCALER.json'], transform_sha256=worker.validate_transform(transform, inputs),
            train_example_ids=[e.example_id for e in train], held_example_ids=[e.example_id for e in held],
            input_fingerprint=context['fingerprints'][str(fold)], label_contract=contract)
        if not same(read(directory/'MODELS_COMPLETE.json'), models_marker): raise ValueError('exact own model marker required')
        expected_status = dict(phase='complete', fold=fold, completed_fits=7, total_fits=7,
                               predicted_examples=len(held), total_held_examples=len(held))
        if not same(read(directory/'STATUS.json'), expected_status): raise ValueError('full own-fold prediction status required')
        predictions = read(directory/'predictions.json')
        if not same(predictions, worker.predict_fold(inputs, models, transform)): raise ValueError('held scores/choices differ from sealed model replay')
        rows.extend(predictions); _files(directory, marker['files_sha256'], exact_inventory=True)
    if len(rows) != len(context['inputs'][0].examples) or {p['example_id'] for p in rows} != {e.example_id for e in context['inputs'][0].examples}:
        raise ValueError('complete unique out-of-fold recipients required')
    verify_initialization(context)
    # Do not let the final input/runtime consumer silently invalidate earlier
    # fold checks or adopt newly written artifact hashes as authority.
    context['recheck']()
    for fold in range(5):
        directory = context['run']/f'fold-{fold}'
        if sha(directory/'COMPLETE.json') != markers[str(fold)]: raise ValueError('consumed fold completion changed')
        _files(directory, artifact_pins[str(fold)], exact_inventory=True)
    return sorted(rows, key=lambda p: p['example_id']), markers


def finalize_predictions(context):
    run = context['run']
    if (run/'PREDICTIONS_COMPLETE.json').exists() or (run/'predictions.json').exists():
        raise ValueError('prediction barrier already written; no overwrite')
    try:
        rows, markers = fold_predictions(context)
        predictions_sha = write(run/'predictions.json', rows)
        context['recheck']()
        again, same_markers = fold_predictions(context)
        if not same(again, rows) or same_markers != markers or sha(run/'predictions.json') != predictions_sha:
            raise ValueError('predictions or fold markers changed before barrier')
        context['predictions_complete_sha256'] = write(run/'PREDICTIONS_COMPLETE.json', dict(
            status='all35_models_and_full_oof_predictions_complete', completed_fits=35, recipients=len(rows),
            methods=list(worker.METHODS), predictions_sha256=predictions_sha, fold_complete_sha256=markers,
            initialization_sha256=context['initialization_sha256']))
        verify_initialization(context)
        if sha(run/'predictions.json') != predictions_sha \
                or sha(run/'PREDICTIONS_COMPLETE.json') != context['predictions_complete_sha256']:
            raise ValueError('prediction barrier changed after writing')
        context['recheck']()
        if sha(run/'predictions.json') != predictions_sha \
                or sha(run/'PREDICTIONS_COMPLETE.json') != context['predictions_complete_sha256']:
            raise ValueError('prediction artifacts changed at terminal boundary')
        for fold in range(5):
            if sha(run/f'fold-{fold}'/'COMPLETE.json') != markers[str(fold)]:
                raise ValueError('fold completion changed after prediction barrier')
        _fold_files(run, markers)
        return rows
    except BaseException as error:
        _failure(run, error); raise


def prediction_barrier(context):
    run = context['run']
    if sha(run/'PREDICTIONS_COMPLETE.json') != context.get('predictions_complete_sha256'):
        raise ValueError('externally retained complete prediction barrier required before assessment')
    rows, markers = fold_predictions(context)
    expected = dict(status='all35_models_and_full_oof_predictions_complete', completed_fits=35, recipients=len(rows),
        methods=list(worker.METHODS), predictions_sha256=sha(run/'predictions.json'), fold_complete_sha256=markers,
        initialization_sha256=context['initialization_sha256'])
    if not same(read(run/'PREDICTIONS_COMPLETE.json'), expected) or not same(read(run/'predictions.json'), rows):
        raise ValueError('global full prediction barrier changed')
    context['recheck']()
    if sha(run/'PREDICTIONS_COMPLETE.json') != context['predictions_complete_sha256'] \
            or sha(run/'predictions.json') != expected['predictions_sha256']:
        raise ValueError('consumed prediction barrier changed')
    _fold_files(run, markers)
    return rows


def assess_predictions(context, label_directory, *, architecture_reporter):
    """Coordinator assessor opens its sole label body only after the barrier."""
    run = context['run']; directory = run/'assessment'
    if directory.exists(): raise ValueError('new assessment output required; no overwrite')
    try:
        if not callable(architecture_reporter): raise ValueError('sealed old-H architecture diagnostic provider required')
        predictions = prediction_barrier(context)  # MUST precede assessment file I/O.
        inputs = context['inputs'][0]; contract = context['contracts'][None]
        if not same(worker.contract_values(contract, inputs), context['manifest']['label_contracts']['assessment']):
            raise ValueError('assessment contract changed before label access')
        path = canonical(canonical(label_directory)/'assessment/all320-labels.json')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != contract.expected_sha256: raise ValueError('external assessment label hash differs')
        labels = provider.validate_assessment_envelope(decode_json(raw), inputs.banks,
            {e.example_id: e.bank_id for e in inputs.examples},
            expected_fold_assignment_sha256=contract.expected_fold_assignment_sha256,
            expected_source_binding_sha256=contract.expected_source_binding_sha256)
        choices = [{k: p[k] for k in assessment.PREDICTION_FIELDS} for p in predictions]
        report = assessment.assess(capsule.validate_inputs(inputs), choices, labels)
        report.update(completed_fits=35, full_train_refits=0, model_promotion=False,
                      predictions_complete_sha256=context['predictions_complete_sha256'],
            shared_theta_diagnostics={arm: {stratum: dict(
                examples=sum(p['shared_theta_diagnostics'][arm]['features_identical_exact'] == equal for p in predictions),
                choices_changed=sum(p['shared_theta_diagnostics'][arm]['choice_changed'] for p in predictions
                    if p['shared_theta_diagnostics'][arm]['features_identical_exact'] == equal),
                **{transition: sum(p['shared_theta_diagnostics'][arm]['transition'] == transition for p in predictions
                    if p['shared_theta_diagnostics'][arm]['features_identical_exact'] == equal)
                   for transition in ('same', 'edited_to_edited', 'to_noop', 'from_noop')})
                for stratum, equal in [('identical_features', True), ('different_features', False)]}
                for arm in ('HS', 'Jm', 'CF')})
        # This callback is invoked only after all35 predictions and assessment
        # labels are authenticated. It must load only the pinned completed old-H
        # result, never fit or select a reference. Its returned diagnostics cannot
        # amend, rescue or replace the already-computed primary scientific gate.
        architecture = architecture_reporter(capsule.validate_inputs(inputs), predictions, labels)
        if type(architecture) is not dict or architecture.get('kind') != 'joint_vs_sealed_progress32_H_diagnostic_v1' \
                or architecture.get('model_promotion') is not False or architecture.get('primary_gate_effect') != 'none':
            raise ValueError('strict non-promotable old-H architecture diagnostic required')
        report['architecture_diagnostic'] = architecture
        directory.mkdir(); report_sha = write(directory/'report.json', report)
        status_sha = write(directory/'STATUS.json', dict(phase='complete', assessed_examples=len(predictions), total_examples=len(predictions)))
        prediction_barrier(context); context['recheck']()
        if sha(path) != contract.expected_sha256: raise ValueError('assessment label drift')
        _files(directory, {'report.json': report_sha, 'STATUS.json': status_sha})
        assessment_pins = {'report.json': report_sha, 'STATUS.json': status_sha}
        assessment_complete_sha = write(directory/'COMPLETE.json', dict(status='complete', assessed_examples=len(predictions),
            predictions_complete_sha256=context['predictions_complete_sha256'], assessment_label_sha256=contract.expected_sha256,
            files_sha256=assessment_pins))
        _files(directory, assessment_pins)
        names = [*INITIAL_FILES, 'INITIALIZATION_COMPLETE.json', 'JOBS_COMPLETE.json', 'predictions.json', 'PREDICTIONS_COMPLETE.json',
                 'assessment/report.json', 'assessment/STATUS.json', 'assessment/COMPLETE.json']
        names += [f'fold-{f}/'+n for f in range(5) for n in (*worker.FILES, 'COMPLETE.json')]
        bindings = {n: sha(run/n) for n in names}
        bindings.update({'assessment/'+n: pin for n, pin in assessment_pins.items()})
        bindings['assessment/COMPLETE.json'] = assessment_complete_sha
        prediction_barrier(context); context['recheck']()
        if sha(path) != contract.expected_sha256: raise ValueError('assessment labels changed before run completion')
        _files(run, bindings)
        complete_sha = write(run/'COMPLETE.json', dict(status='complete', completed_fits=35, recipients=len(predictions), methods=list(worker.METHODS),
            files_sha256=bindings, job_sha256=context['job_sha256'], full_train_refits=0, automatic_retries=0,
            model_promotion=False, scientific_gate_passed=report['gate']['passed'], independent_audit_required=True))
        context['recheck']()
        if sha(path) != contract.expected_sha256: raise ValueError('assessment labels changed after completion')
        _files(run, bindings)
        context['recheck']()
        if sha(path) != contract.expected_sha256: raise ValueError('assessment labels changed at terminal boundary')
        _files(run, bindings)
        if sha(run/'COMPLETE.json') != complete_sha: raise ValueError('run completion changed after writing')
        return report
    except BaseException as error:
        if directory.exists(): _failure(directory, error)
        _failure(run, error); raise


if __name__ == '__main__':
    raise SystemExit('No production CLI: trusted external supervisor and separate fitting release required.')
