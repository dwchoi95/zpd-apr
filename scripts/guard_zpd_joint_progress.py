"""Fixed coordinator stages for the separately released joint4131 experiment.

This module is never imported by an own-fold worker. Previous receipt hashes
are supplied by the outside supervisor, not inferred from the current files.
Preparation is metadata-only; all six label bodies are accessed only by the
post-prediction independent audit. No release, retry, generation or refit API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

# Must precede numerical imports, just as in the own-job entry point.
from scripts import run_zpd_statement_sample_replay as launcher
from scripts import audit_zpd_statement_sample_readiness as accepted
from scripts import guard_zpd_repair_directed as oldguard
from scripts import run_zpd_joint_progress_job as job
from scripts import run_zpd_joint_progress_cv as worker
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_repair_progress_inputs as frozen_observed
from scripts import zpd_joint_progress_inputs as observed
from scripts import zpd_joint_progress_features as features
from scripts import zpd_joint_progress_architecture as architecture
from scripts import guard_zpd_repair_progress as previous_guard
from scripts import zpd_joint_progress_stages as stages
from scripts import zpd_repair_feedback_labels as labels
from scripts.supervise_zpd_history_action import verify_marker

ROOT=Path(__file__).resolve().parents[1]
PROJECT=job.PROJECT
FAMILY=job.FAMILY
PREPARED=job.LABELS
PREPARED_COMPLETE_SHA256=oldguard.PREPARED_COMPLETE_SHA256
RELEASE='analysis_protocols/zpd-joint-progress-release-20260925.json'
SIDECAR=RELEASE+'.sha256'
PROTOCOL='analysis_protocols/zpd-joint-progress-prospective-20260925.md'
STAGES=('preflight','initialize',*(f'fold-{f}' for f in range(5)),'finalize','assess','audit')
COORDINATOR_STAGES=tuple(s for s in STAGES if not s.startswith('fold-'))
RUNTIME=dict(accepted.preparation.RUNTIME)
ENVIRONMENT=dict(launcher.ENVIRONMENT)
CHILD_MEMORY_BYTES=32*1024**3
HEARTBEAT_SECONDS=30
TIMEOUTS={s:3600 if s.startswith('fold-') or s=='audit' else 900 for s in STAGES}
OLD_RUN='outputs/zpd-repair-statement-progress-20260925/run-v1'
OLD_COMPLETE_SHA256='2d0fcc31221073cdf961934924f6559eb4eb324012a96dc698d76b2cbc26b1d9'
NEW_SOURCES=(
    'scripts/zpd_joint_progress_features.py',
    'scripts/zpd_joint_progress_newton.py',
    'scripts/zpd_joint_progress_capsule.py',
    'scripts/zpd_joint_progress_assessment.py',
    'scripts/zpd_joint_progress_inputs.py',
    'scripts/zpd_joint_progress_stages.py',
    'scripts/zpd_joint_progress_audit.py',
    'scripts/zpd_joint_progress_architecture.py',
    'scripts/run_zpd_joint_progress_cv.py',
    'scripts/run_zpd_joint_progress_job.py',
    'scripts/audit_zpd_joint_progress_independent.py',
    'scripts/guard_zpd_joint_progress.py',
    'scripts/supervise_zpd_joint_progress.py',
    'tests/test_zpd_joint_progress_features.py',
    'tests/test_zpd_joint_progress_features_review.py',
    'tests/test_zpd_joint_progress_newton.py',
    'tests/test_zpd_joint_progress_newton_review.py',
    'tests/test_zpd_joint_progress_capsule.py',
    'tests/test_zpd_joint_progress_capsule_review.py',
    'tests/test_zpd_joint_progress_assessment.py',
    'tests/test_zpd_joint_progress_assessment_review.py',
    'tests/test_zpd_joint_progress_inputs.py',
    'tests/test_zpd_joint_progress_inputs_review.py',
    'tests/test_zpd_joint_progress_stages.py',
    'tests/test_zpd_joint_progress_stages_review.py',
    'tests/test_zpd_joint_progress_audit.py',
    'tests/test_zpd_joint_progress_audit_review.py',
    'tests/test_zpd_joint_progress_architecture.py',
    'tests/test_zpd_joint_progress_architecture_review.py',
    'tests/test_zpd_joint_progress_cv.py',
    'tests/test_zpd_joint_progress_cv_review.py',
    'tests/test_zpd_joint_progress_job.py',
    'tests/test_zpd_joint_progress_job_review.py',
    'tests/test_zpd_joint_progress_independent.py',
    'tests/test_zpd_joint_progress_independent_review.py',
    'tests/test_zpd_joint_progress_guard.py',
    'tests/test_zpd_joint_progress_guard_review.py',
    'tests/test_zpd_joint_progress_supervisor.py',
    'tests/test_zpd_joint_progress_supervisor_review.py',
    'analysis_protocols/zpd-joint-progress-features-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-newton-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-capsule-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-assessment-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-inputs-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-stages-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-audit-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-architecture-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-cv-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-job-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-independent-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-guard-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-supervisor-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-protocol-independent-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-ranking-candidate-20260925.md',
    'analysis_protocols/zpd-joint-progress-ranking-design-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-newton-candidate-20260925.md',
    'analysis_protocols/zpd-joint-progress-newton-design-review-20260925.md',
    'analysis_protocols/zpd-joint-progress-method-selection-20260925.md',
    PROTOCOL)
SOURCE_FILES=tuple(sorted(set((*previous_guard.SOURCE_FILES,*observed.LOCAL_SOURCES,*NEW_SOURCES))))
PREREQUISITE_RELEASES={accepted.RELEASE:frozen_observed.RELEASE_SHA,accepted.SIDECAR:frozen_observed.SIDECAR_SHA}
canonical=worker.canonical
sha=worker.sha
write=worker.write
read=stages.read
same=stages.same
require=job.require
runtime=job.runtime
controller_native=job.controller_native
verify_child_boundary=job.verify_child_boundary


def digest(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None,'strict SHA256 required')
    return value


def source_state():
    canonical(ROOT)
    require(not subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=ROOT,text=True).strip(),
            'clean committed source snapshot required')
    return {k:subprocess.check_output(['git','rev-parse',v],cwd=ROOT,text=True).strip()
            for k,v in (('revision','HEAD'),('tree','HEAD^{tree}'))}


def paths(project):
    project=canonical(project);require(project==PROJECT,'fixed canonical production project required')
    family=canonical(project/FAMILY);supervisor=canonical(family/'supervised-v1')
    return dict(project=project,family=family,prepared=canonical(project/PREPARED),
        run=canonical(family/'run-v1'),jobs=canonical(family/'jobs'),supervisor=supervisor,
        verified=canonical(supervisor/'verified'))


def release_configuration():
    return dict(primary='H',arms=list(worker.ARMS),folds=5,recipients=320,problems=23,candidates=2544,
        fits=35,methods=list(worker.METHODS),dimension=4131,representation=features.configuration(),
        solver=worker.solver.configuration(worker.SPEC),process_stages=list(STAGES),
        learned_base_input=False,base_offset_present=False,intercept=False,
        current_only_control='C_joint_same_joint_solver_with_zero_progress32',
        shared_controls='all4131_H_coefficients_fixed',
        old_architecture_reference=dict(architecture.REFERENCE_PINS),
        old_architecture_run_complete_sha256=OLD_COMPLETE_SHA256,
        old_architecture_gate_effect='none',old_architecture_model_promotion=False,
        candidate_space='all_original_train320_banks_with_fixed8_terminal_attempts',
        prepared_labels='read_only_reuse_exact_six_original_files',preparation_permitted=False,
        worker_access='one_externally_pinned_own_job_and_own_training_file_only',
        worker_global_manifest=False,worker_sibling_label_hashes=False,
        full_train_refits=0,automatic_retries=0,model_promotion=False,
        child_memory_bytes=CHILD_MEMORY_BYTES,environment=ENVIRONMENT,
        heartbeat_seconds=HEARTBEAT_SECONDS,stage_timeout_seconds=TIMEOUTS)


def serialized_contracts(contracts):
    return {str(f) if f is not None else 'assessment':dict(vars(c)) for f,c in contracts.items()}


def contracts_from_context(context):
    return {None if k=='assessment' else int(k):worker.LabelContract(**v)
            for k,v in context['label_contracts'].items()}


def _bindings(mapping):
    for raw,pin in mapping.items():
        require(sha(canonical(raw))==digest(pin),'bound source/input changed: '+raw)


def _sources(mapping):
    require(type(mapping) is dict and set(mapping)==set(SOURCE_FILES),'exact complete source closure required')
    job.validate_source_map(mapping)  # Code/protocol ONLY, including worker payload.
    for name,pin in mapping.items():
        require(sha(canonical(ROOT/name))==digest(pin),'released source changed: '+name)
        if name.endswith('.py'):
            module=sys.modules.get(name[:-3].replace('/','.'))
            if module is not None:require(canonical(module.__file__)==ROOT/name,'loaded module outside clean snapshot')


def preflight(project):
    """Read-only release, source/native runtime and prerequisite METADATA."""
    location=paths(project)
    require(canonical(ROOT).is_relative_to(location['project']/'.runtime') and ROOT!=location['project']/'.runtime',
            'dedicated clean source snapshot required')
    release=canonical(ROOT/RELEASE);side=canonical(ROOT/SIDECAR)
    require(release.is_file() and side.is_file(),'separate joint4131 release and sidecar required')
    state=source_state();raw=release.read_bytes();side_raw=side.read_bytes()
    require(re.fullmatch(b'[0-9a-f]{64}\n',side_raw) is not None
            and hashlib.sha256(raw).hexdigest()==side_raw[:-1].decode('ascii'),'strict release sidecar mismatch')
    approval=frozen_observed.decode_json(raw)
    tracked={RELEASE,SIDECAR,*SOURCE_FILES,*PREREQUISITE_RELEASES}
    actual=subprocess.check_output(['git','ls-files','--error-unmatch','-z','--',*sorted(tracked)],cwd=ROOT)
    require(set(actual.decode('utf-8').rstrip('\0').split('\0'))==tracked,'entire release/source inventory must be tracked')
    contracts,_,_=oldguard._metadata_preparation(location)  # No label-body reads/hashes.
    pins={frozen_observed.SUPPORT+'/COMPLETE.json':job.READINESS_COMPLETE_SHA256,
          accepted.observed.PARENT+'/COMPLETE.json':job.PARENT_COMPLETE_SHA256,
          PREPARED+'/COMPLETE.json':PREPARED_COMPLETE_SHA256}
    metadata={PREPARED+'/'+n:sha(canonical(location['prepared']/n)) for n in ('manifest.json','folds.json')}
    expected=dict(kind='joint_progress4131_fixed35_fit_release_v1',project=str(PROJECT),family=FAMILY,
        fit_release_authorized=True,confirmatory=False,fresh_test_opened=False,configuration=release_configuration(),
        runtime=RUNTIME,input_complete_sha256=pins,prepared_metadata_sha256=metadata,
        prepared_label_contracts=serialized_contracts(contracts),prerequisite_release_sha256=PREREQUISITE_RELEASES,
        protocol_sha256=sha(canonical(ROOT/PROTOCOL)))
    require(type(approval) is dict and set(approval)==set(expected)|{'source_sha256','controller_native','decision_reason'}
        and all(same(approval[k],v) for k,v in expected.items())
        and type(approval['decision_reason']) is str and bool(approval['decision_reason'].strip()),
            'strict fixed release schema/configuration required')
    _sources(approval['source_sha256'])
    require(same(runtime(),RUNTIME) and same(controller_native(),approval['controller_native']),
            'fixed numerical/native runtime required')
    bindings={str(release):hashlib.sha256(raw).hexdigest(),str(side):hashlib.sha256(side_raw).hexdigest()}
    for name,pin in {**pins,**metadata}.items():
        path=canonical(location['project']/name);require(sha(path)==pin,'fixed prerequisite metadata mismatch')
        bindings[str(path)]=pin
    for name,pin in PREREQUISITE_RELEASES.items():
        path=canonical(ROOT/name);require(sha(path)==pin,'frozen readiness release changed');bindings[str(path)]=pin
    bindings.update(old_metadata(location))  # Metadata only; never old prediction bytes before the new barrier.
    context=dict(source=state,release_sha256=hashlib.sha256(raw).hexdigest(),
        source_sha256=approval['source_sha256'],input_sha256=bindings,runtime=RUNTIME,
        controller_native=approval['controller_native'],label_contracts=serialized_contracts(contracts),project=str(location['project']))
    recheck(context);return context


def recheck(context):
    require(same(source_state(),context['source']) and same(runtime(),context['runtime'])
        and same(controller_native(),context['controller_native']),'source/runtime/native drift')
    _sources(context['source_sha256']);_bindings(context['input_sha256'])
    location=paths(context['project'])
    for base in (location['prepared'],location['project']/frozen_observed.SUPPORT,location['project']/accepted.observed.PARENT):
        require(not (base/'FAILED.json').exists() and not any(base.glob('REJECTED_*')),'failed prerequisite forbidden')
    old_metadata(location)


def old_metadata(location):
    """Authenticate fixed old seals without opening any old prediction/label body."""
    run=canonical(location['project']/OLD_RUN)
    for base in (run.parent,run):
        require(not (base/'FAILED.json').exists() and not any(base.glob('REJECTED_*')),
                'failed old architecture reference forbidden')
    pins={'COMPLETE.json':OLD_COMPLETE_SHA256,
        'PREDICTIONS_COMPLETE.json':architecture.REFERENCE_PINS['prediction_seal_sha256']}
    values={}
    for name,pin in pins.items():
        raw=canonical(run/name).read_bytes()
        require(hashlib.sha256(raw).hexdigest()==pin,'fixed old architecture metadata changed')
        values[name]=frozen_observed.decode_json(raw)
    complete=values['COMPLETE.json'];predicted=values['PREDICTIONS_COMPLETE.json']
    require(type(complete) is dict and complete.get('status')=='complete'
        and type(complete.get('completed_fits')) is int and complete['completed_fits']==30
        and complete.get('recipients')==320 and complete.get('model_promotion') is False
        and complete.get('files_sha256',{}).get('predictions.json')==architecture.REFERENCE_PINS['predictions_sha256']
        and complete['files_sha256'].get('PREDICTIONS_COMPLETE.json')==pins['PREDICTIONS_COMPLETE.json']
        and type(predicted) is dict and predicted.get('predictions_sha256')==architecture.REFERENCE_PINS['predictions_sha256']
        and predicted.get('status')=='all30_models_and_full_oof_predictions_complete',
        'fixed completed old architecture metadata required')
    return {str(run/name):pin for name,pin in pins.items()}


def old_reference(location,restored):
    """Only after all35 joint models/predictions: fixed old-H diagnostic bytes."""
    stages.prediction_barrier(restored)  # Never replace with a caller-supplied Boolean.
    metadata=old_metadata(location)
    path=canonical(location['project']/OLD_RUN/'predictions.json')
    raw=path.read_bytes();pin=architecture.REFERENCE_PINS['predictions_sha256']
    require(hashlib.sha256(raw).hexdigest()==pin,'fixed old predictions changed')
    predictions=frozen_observed.decode_json(raw)
    require(type(predictions) is list and len(predictions)==320,'complete fixed old prediction list required')
    def barrier():
        require(same(old_metadata(location),metadata),'old metadata binding changed')
        _bindings(metadata)
        verify_old_reference_body(location)
    barrier();return predictions,barrier


def verify_old_reference_body(location):
    """Post-consumption only: also used after the supervisor's verified audit.

    This is an integrity check, not label-opening or fitting authority. The
    coordinator calls it only after prediction_barrier, and the supervisor
    only after all ten externally pinned stage receipts, including audit.
    """
    old_metadata(location)
    require(sha(canonical(location['project']/OLD_RUN/'predictions.json'))==architecture.REFERENCE_PINS['predictions_sha256'],
            'old diagnostic prediction body drift after consumption')
    old_metadata(location)


def _load_inputs(location,context):
    components=observed.load_observed_components(location['project'])
    require(components['synthetic'] is False and same(components['feature_configuration'],frozen_observed.progress.configuration())
        and same(components['joint_feature_configuration'],features.configuration()),
            'exact production joint4131 and unchanged accepted progress32 components required')
    bindings=dict(context['input_sha256'])
    for raw,pin in components['source_bindings'].items():
        path=canonical(raw);require(path.is_relative_to(ROOT),'coordinator source outside snapshot')
        name=str(path.relative_to(ROOT))
        if name in PREREQUISITE_RELEASES:
            require(pin==PREREQUISITE_RELEASES[name],'accepted release binding differs');bindings[raw]=pin
        else:require(context['source_sha256'].get(name)==pin,'component source outside released closure')
    for raw,pin in components['input_bindings'].items():
        require(raw not in bindings or bindings[raw]==pin,'conflicting consumed input hash');bindings[raw]=pin
    inputs={f:observed.project_fold(components,f) for f in range(5)}
    contracts,_,folds=oldguard._metadata_preparation(location)
    require(same(serialized_contracts(contracts),context['label_contracts']) and same(folds,inputs[0].assignment),
            'released preparation/fold assignment differs')
    provenance=dict(source_sha256={str(ROOT/n):v for n,v in context['source_sha256'].items()},input_sha256=bindings)
    def barrier():
        recheck(context);_bindings(provenance['input_sha256'])
    barrier()
    return inputs,contracts,provenance,barrier


def job_source(context):
    return dict(source_state=context['source'],source_root=str(ROOT),source_sha256=context['source_sha256'],
        runtime=context['runtime'],controller_native=context['controller_native'])


def authority(context):
    return dict(release_sha256=context['release_sha256'],readiness_complete_sha256=job.READINESS_COMPLETE_SHA256,
        parent_complete_sha256=job.PARENT_COMPLETE_SHA256)


def artifact_names(stage):
    if stage=='preflight':return ()
    if stage=='initialize':return tuple('run-v1/'+n for n in (*stages.INITIAL_FILES,'INITIALIZATION_COMPLETE.json','JOBS_COMPLETE.json'))+tuple(f'jobs/fold-{f}.json' for f in range(5))
    if stage.startswith('fold-'):return tuple(f'run-v1/{stage}/'+n for n in (*worker.FILES,'COMPLETE.json'))
    if stage=='finalize':return ('run-v1/PREDICTIONS_COMPLETE.json','run-v1/predictions.json')
    if stage=='assess':return ('run-v1/COMPLETE.json','run-v1/assessment/COMPLETE.json','run-v1/assessment/report.json','run-v1/assessment/STATUS.json')
    if stage=='audit':return ('supervised-v1/verified/COMPLETE.json','supervised-v1/verified/report.json')
    raise ValueError('unknown fixed stage')


def _artifacts(location,stage):return {name:sha(canonical(location['family']/name)) for name in artifact_names(stage)}


def _terminal_flags(location,stage):
    """Live failure markers are not covered by hashes of earlier success files."""
    directory=canonical(location['supervisor']/'stages'/stage)
    bases={location['family'],location['supervisor'],directory.parent,directory}
    for name in artifact_names(stage):
        current=canonical(location['family']/name).parent
        require(current.is_relative_to(location['family']),'engine artifact outside fixed family')
        while current!=location['family']:
            bases.add(current);current=current.parent
    for base in sorted(bases):
        require(not (base/'FAILED.json').exists() and not any(base.glob('REJECTED_*')),
                'failed stage or bound engine artifact forbidden: '+str(base))


def verify_wrapper(project,stage,expected_sha):
    location=paths(project);require(stage in STAGES,'fixed stage required')
    directory=canonical(location['supervisor']/'stages'/stage)
    _terminal_flags(location,stage)
    require(sha(directory/'COMPLETE.json')==digest(expected_sha),'externally pinned stage receipt changed')
    seal=verify_marker(directory,required_files=('report.json',));marker=read(directory/'COMPLETE.json');report=read(directory/'report.json')
    require(set(marker['files_sha256'])=={'report.json'} and set(report)=={'kind','stage','status','source','release_sha256','result','engine_artifact_sha256'}
        and report['kind']=='joint_progress4131_production_stage_v1' and report['stage']==stage and report['status']=='complete',
            'strict stage receipt schema required')
    require(same(report['engine_artifact_sha256'],_artifacts(location,stage)),'bound actual engine artifacts changed')
    result=report['result'];artifacts=report['engine_artifact_sha256']
    require(type(result) is dict,'stage result object required')
    if stage=='initialize':
        require(result.get('initialization_sha256')==artifacts['run-v1/INITIALIZATION_COMPLETE.json']
            and result.get('jobs_complete_sha256')==artifacts['run-v1/JOBS_COMPLETE.json']
            and same(result.get('job_sha256'),{str(f):artifacts[f'jobs/fold-{f}.json'] for f in range(5)})
            and same(result.get('fingerprints'),read(location['run']/'manifest.json').get('input_fingerprints')),
                'initialization result and actual engine seals differ')
    if stage.startswith('fold-'):
        fold=int(stage[-1]);own=location['run']/stage
        verify_marker(own,required_files=worker.FILES);actual=read(own/'COMPLETE.json')
        require(set(actual['files_sha256'])==set(worker.FILES) and actual.get('kind')=='joint_progress4131_fold_complete_v1'
            and type(actual.get('completed_fits')) is int and actual['completed_fits']==7
            and type(actual.get('fold')) is int and actual['fold']==fold
            and type(actual.get('predicted_examples')) is int and 0<actual['predicted_examples']<=320,
                'actual seven-fit own-fold seal required')
        require(result.get('fold_complete_sha256')==artifacts[f'run-v1/{stage}/COMPLETE.json']
            and result.get('predicted_examples')==actual['predicted_examples']
            and result.get('completed_fits')==7,'fold result and actual engine seal differ')
    elif stage=='finalize':
        require(result.get('predictions_complete_sha256')==artifacts['run-v1/PREDICTIONS_COMPLETE.json'],
                'finalize result and prediction seal differ')
    elif stage=='assess':
        verify_marker(location['run'],required_files=('assessment/report.json','PREDICTIONS_COMPLETE.json','predictions.json'))
        actual=read(location['run']/'COMPLETE.json')
        require(actual.get('completed_fits')==35 and actual.get('recipients')==320
            and actual.get('model_promotion') is False and actual.get('full_train_refits')==0,'full no-refit experiment required')
        require(result.get('experiment_complete_sha256')==artifacts['run-v1/COMPLETE.json'],
                'assessment result and engine seal differ')
    elif stage=='audit':
        verify_marker(location['verified'],required_files=('report.json',))
        require(read(location['verified']/'report.json').get('verified') is True,'positive independent audit required')
        require(same(result,read(location['verified']/'report.json'))
            and result.get('experiment_complete_sha256')==sha(location['run']/'COMPLETE.json'),
                'audit result and actual run seal differ')
    verify_marker(directory,required_files=('report.json',))
    require(same(report['engine_artifact_sha256'],_artifacts(location,stage)),'stage artifact drift after consumption')
    require(sha(directory/'COMPLETE.json')==expected_sha,'stage receipt drift after consumption')
    _terminal_flags(location,stage)
    return dict(seal,report=report)


def previous(project,stage,pins,context):
    require(type(pins) is dict and set(pins)==set(STAGES[:STAGES.index(stage)]),'exact externally supplied previous-stage pins required')
    result={}
    for name,pin in pins.items():
        value=verify_wrapper(project,name,pin)['report']
        require(same(value['source'],context['source']) and value['release_sha256']==context['release_sha256'],
                'previous source/release differs');result[name]=value
    return result


def restore(location,context,inputs,contracts,provenance,barrier,receipts):
    saved=receipts['initialize']['result']
    require(set(saved)=={'initialization_sha256','jobs_complete_sha256','job_sha256','fingerprints'},'strict external initialization receipt required')
    require(set(saved['job_sha256'])==set(saved['fingerprints'])=={str(f) for f in range(5)},'all five job/fingerprint pins required')
    for value in (saved['initialization_sha256'],saved['jobs_complete_sha256'],*saved['job_sha256'].values(),*saved['fingerprints'].values()):digest(value)
    run=location['run'];manifest=read(run/'manifest.json')
    require(same(manifest['provenance'],provenance) and same(manifest['source'],job_source(context))
        and same(manifest['authority'],authority(context)) and same(manifest['input_fingerprints'],saved['fingerprints']),
            'initialized provenance/source/input identity changed')
    restored=dict(run=run,jobs=location['jobs'],family=location['family'],inputs=inputs,contracts=contracts,
        recheck=barrier,source=job_source(context),authority=authority(context),manifest=manifest,**saved)
    if 'finalize' in receipts:restored['predictions_complete_sha256']=receipts['finalize']['result']['predictions_complete_sha256']
    stages.verify_initialization(restored);return restored


def reject(directory,error):
    marker=directory/'COMPLETE.json'
    if marker.exists():
        rejected=directory/'REJECTED_COMPLETE.json';require(not rejected.exists(),'prior rejected marker exists');marker.rename(rejected)
    if not (directory/'FAILED.json').exists():
        write(directory/'FAILED.json',dict(status='failed',error_type=type(error).__name__,error=str(error),automatic_retries=0))


def verify_audit_label_inputs(location,contracts):
    require(set(contracts)=={*range(5),None},'all six audit contracts required')
    for fold,contract in contracts.items():
        name='assessment/all320-labels.json' if fold is None else f'fold-{fold}/train-labels.json'
        require(sha(canonical(location['prepared']/name))==contract.expected_sha256,'audit label body drift: '+name)


def _independent_audit(location,restored):
    from scripts import audit_zpd_joint_progress_independent as auditor
    run=location['run'];contracts=restored['contracts'];inputs=restored['inputs']
    verify_marker(run,required_files=('assessment/report.json','PREDICTIONS_COMPLETE.json','predictions.json'))
    consumed=sha(run/'COMPLETE.json')
    predictions=stages.prediction_barrier(restored)  # Mandatory before ANY audit labels.
    models={f:{a:read(run/f'fold-{f}'/(a+'.json')) for a in worker.ARMS} for f in range(5)}
    training={}
    for f in range(5):
        train,_=capsule.scope(inputs[f])
        training[f]=labels.load_fold_labels(location['prepared'],f,{e.bank_id:inputs[f].banks[e.bank_id] for e in train},
            {e.example_id:e.bank_id for e in train},**vars(contracts[f]))
    raw=canonical(location['prepared']/'assessment/all320-labels.json').read_bytes()
    require(hashlib.sha256(raw).hexdigest()==contracts[None].expected_sha256,'assessment label SHA mismatch')
    assessed=labels.validate_assessment_envelope(frozen_observed.decode_json(raw),inputs[0].banks,
        {e.example_id:e.bank_id for e in inputs[0].examples},
        expected_fold_assignment_sha256=contracts[None].expected_fold_assignment_sha256,
        expected_source_binding_sha256=contracts[None].expected_source_binding_sha256)
    report=read(run/'assessment/report.json')
    require(report['predictions_complete_sha256']==restored['predictions_complete_sha256'],
            'assessment report must bind externally sealed predictions')
    scalers={f:read(run/f'fold-{f}'/'SCALER.json') for f in range(5)}
    old_predictions,reference_barrier=old_reference(location,restored)
    result=auditor.audit_run(inputs,models,scalers,predictions,training,assessed,report,
        old_predictions=old_predictions,reference_pins=dict(architecture.REFERENCE_PINS),
        expected_predictions_complete_sha256=restored['predictions_complete_sha256'],
        expected_input_fingerprint={f:restored['fingerprints'][str(f)] for f in range(5)},
        expected_label_contracts={f:vars(contracts[f]) for f in range(5)},
        expected_runtime={k:RUNTIME[k] for k in ('python','numpy','scipy')})
    require(result.get('verified') is True and result.get('recipients')==320 and result.get('models')==35
        and result.get('methods')==14 and result.get('architecture_verified') is True,
        'full independent320/35/14 and old architecture audit required')
    stages.prediction_barrier(restored);restored['recheck']();verify_audit_label_inputs(location,contracts);reference_barrier()
    verify_marker(run,required_files=('assessment/report.json',));require(sha(run/'COMPLETE.json')==consumed,'consumed run seal drift')
    return dict(result,experiment_complete_sha256=consumed)


def publish_wrapper(location,context,stage,result,barrier):
    directory=canonical(location['supervisor']/'stages'/stage)
    require(not directory.exists(),'new stage receipt required; no overwrite/retry');directory.mkdir(parents=True)
    try:
        artifacts=_artifacts(location,stage)
        report=dict(kind='joint_progress4131_production_stage_v1',stage=stage,status='complete',
            source=context['source'],release_sha256=context['release_sha256'],result=result,engine_artifact_sha256=artifacts)
        report_sha=write(directory/'report.json',report)
        barrier();require(same(_artifacts(location,stage),artifacts),'late stage artifact drift')
        barrier();require(sha(directory/'report.json')==report_sha,'late receipt report drift')
        complete_sha=write(directory/'COMPLETE.json',dict(status='complete',files_sha256={'report.json':report_sha}))
        barrier();require(same(_artifacts(location,stage),artifacts),'post-seal artifact drift')
        return verify_wrapper(location['project'],stage,complete_sha)
    except BaseException as error:reject(directory,error);raise


def finish_fold(project,fold,pins,context):
    """Outside coordinator only, after direct own-job child exits successfully."""
    stage=f'fold-{fold}';location=paths(project);receipts=previous(project,stage,pins,context)
    saved=receipts['initialize']['result'];job_pin=saved['job_sha256'][str(fold)]
    require(sha(location['jobs']/f'fold-{fold}.json')==job_pin,'externally initialized own job changed')
    own=location['run']/stage;seal=verify_marker(own,required_files=worker.FILES);marker=read(own/'COMPLETE.json')
    require(marker.get('input_fingerprint')==saved['fingerprints'][str(fold)],'own fold differs from initialized projection')
    result=dict(completed_fits=7,predicted_examples=marker['predicted_examples'],job_sha256=job_pin,
        fold_complete_sha256=seal['complete_sha256'])
    def barrier():
        previous(project,stage,pins,context);recheck(context)
        require(sha(location['jobs']/f'fold-{fold}.json')==job_pin,'own job drift after exit')
    return publish_wrapper(location,context,stage,result,barrier)


def execute_stage(project,stage,pins):
    require(stage in COORDINATOR_STAGES,'coordinator stage only; folds must use isolated own-job CLI')
    location=paths(project);require(not (location['supervisor']/'stages'/stage).exists(),'new fixed stage required')
    context=preflight(project);verify_child_boundary();receipts=previous(project,stage,pins,context)
    inputs,contracts,provenance,input_barrier=_load_inputs(location,context)
    restored=None;audit_result=None;audit_report_pin=None;audit_inner_pin=None;reference_barrier=None
    def barrier():
        previous(project,stage,pins,context);input_barrier()
        if reference_barrier is not None:reference_barrier()
        if restored is not None:stages.verify_initialization(restored)
        if stage=='assess' and (location['run']/'COMPLETE.json').exists():
            require(sha(location['prepared']/'assessment/all320-labels.json')==contracts[None].expected_sha256,
                    'assessment body drift after engine completion')
        if audit_result is not None:
            verify_marker(location['run'],required_files=('assessment/report.json',))
            require(sha(location['run']/'COMPLETE.json')==audit_result['experiment_complete_sha256'],'audited run seal drift')
            verify_audit_label_inputs(location,contracts)
            if audit_report_pin is not None:
                require(sha(location['verified']/'report.json')==audit_report_pin,'consumed audit report drift')
            if audit_inner_pin is not None:
                require(sha(location['verified']/'COMPLETE.json')==audit_inner_pin,'consumed audit inner seal drift')
    try:
        if stage=='preflight':
            result=dict(recipients=320,labels_opened=False,label_bodies_opened=False,
                fingerprints={str(f):capsule.fingerprint(v) for f,v in inputs.items()})
        elif stage=='initialize':
            restored=stages.initialize(inputs,contracts,location['family'],job_source=job_source(context),
                authority=authority(context),provenance=provenance,recheck=input_barrier)
            result={k:restored[k] for k in ('initialization_sha256','jobs_complete_sha256','job_sha256','fingerprints')}
        else:
            restored=restore(location,context,inputs,contracts,provenance,input_barrier,receipts)
            if stage=='finalize':
                stages.finalize_predictions(restored)
                result=dict(predictions_complete_sha256=restored['predictions_complete_sha256'],recipients=320,completed_fits=35)
            elif stage=='assess':
                old_predictions,reference_barrier=old_reference(location,restored)
                def architecture_reporter(cohort,predictions,assessment_labels):
                    reference_barrier()
                    value=architecture.report(cohort,predictions,old_predictions,assessment_labels,
                        reference_pins=dict(architecture.REFERENCE_PINS),synthetic=False)
                    reference_barrier();return value
                report=stages.assess_predictions(restored,location['prepared'],architecture_reporter=architecture_reporter)
                result=dict(experiment_complete_sha256=sha(location['run']/'COMPLETE.json'),gate=report['gate'])
            else:
                audit_result=_independent_audit(location,restored);result=audit_result
                _,reference_barrier=old_reference(location,restored)
                verified=location['verified'];require(not verified.exists(),'new independent audit output required');verified.mkdir()
                audit_report_pin=write(verified/'report.json',result)
                barrier()
                audit_inner_pin=write(verified/'COMPLETE.json',dict(status='complete',files_sha256={'report.json':audit_report_pin}))
                barrier()
        return publish_wrapper(location,context,stage,result,barrier)
    except BaseException as error:
        if stage=='audit' and location['verified'].exists():reject(location['verified'],error)
        directory=location['supervisor']/'stages'/stage
        if not directory.exists():directory.mkdir(parents=True)
        reject(directory,error);raise


def main(argv=None):
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--stage',choices=COORDINATOR_STAGES,required=True)
    parser.add_argument('--previous-stage-sha256',required=True)
    args=parser.parse_args(argv)
    return execute_stage(args.project,args.stage,frozen_observed.decode_json(args.previous_stage_sha256.encode('utf-8')))


if __name__=='__main__':main()
