"""One new objective comparison over immutable old source-only fold capsules.

Five bounded own-job children; all predictions sealed before assessment labels.
No generation, retries, outcome selection, promotion or modified scientific gate.
The external release SHA names the new clean code snapshot, not the old release.
"""
from scripts import run_zpd_statement_sample_replay as launcher

import argparse
import hashlib
import json
from pathlib import Path
import sys

from scripts import run_zpd_bank_topset_job as job
from scripts import supervise_zpd_joint_progress as bounded
from scripts.supervise_zpd_history_action import verify_marker
from scripts import zpd_repair_feedback_labels as provider

authority = job.authority
worker = job.worker
OLD = 'outputs/zpd-repair-joint-progress-20260925'
OLD_OUTER = 'f4d7249e12a879b2212678d2590cac62aea391915122901919f9b9b6b593440e'
OLD_RUN = '2e7c60d1378b4e3b1e0e5df574e2c9623203a5ab6c38b1deba4a5381e3db33ed'
PREPARED = '71a9f8803895b9585364589554811c67c9a99969d16e6c5247716d643e21048e'
RELEASE_FIELDS = {'kind','source_root','source_state','source_sha256','runtime','controller_native',
                  'protocol_sha256','independent_preflight_passed','empirical_fits_authorized'}
PROTOCOL = 'analysis_protocols/zpd-bank-topset-prospective-20260925.md'


def read_pinned(path, pin):
    raw = authority.canonical(path).read_bytes()
    authority.require(authority.digest(raw) == pin, 'pinned artifact differs: '+str(path))
    return launcher.core.decode_json(raw)


def supervise(project, expected_release):
    project = authority.canonical(project)
    authority.require(project == job.PROJECT and authority.preparation.is_sha(expected_release),
        'canonical project and external new release SHA required')
    root = project/job.FAMILY; run = root/'run-v1'; jobs = root/'jobs'; supervisor = root/'supervised-v1'
    authority.require(not any(p.exists() for p in (run,jobs,supervisor,root/'verified-v1')),
        'fresh run/jobs/supervisor/audit; no duplicate or resume')
    release_path = root/'release.json'; release = read_pinned(release_path, expected_release)
    authority.require(type(release) is dict and set(release) == RELEASE_FIELDS
        and release['kind'] == 'bank_topset4131_release_v1'
        and release['source_root'] == str(authority.ROOT)
        and authority.ROOT.is_relative_to(project/'.runtime')
        and release['independent_preflight_passed'] is True and release['empirical_fits_authorized'] is True,
        'independently issued new top-set release required')
    authority.require(type(release['source_sha256']) is dict
        and set(release['source_sha256']) == set(job.SOURCE_FILES)
        and authority.preparation.is_sha(release['protocol_sha256'])
        and PROTOCOL in release['source_sha256']
        and release['protocol_sha256'] == release['source_sha256'][PROTOCOL], 'exact source closure and prospective protocol required')
    def recheck():
        authority.require(authority.sha(release_path) == expected_release, 'release changed')
        authority.require(authority.same(authority.source_state(),release['source_state'])
            and authority.same(authority.runtime(),release['runtime'])
            and authority.same(release['runtime'],authority.preparation.RUNTIME)
            and authority.same(authority.controller_native(),release['controller_native']), 'source/runtime/native drift')
        job.check_sources(release['source_sha256'])
    recheck()
    old = project/OLD
    outer = read_pinned(old/'supervised-v1/COMPLETE.json',OLD_OUTER)
    previous = read_pinned(old/'run-v1/COMPLETE.json',OLD_RUN)
    authority.require(outer['status'] == previous['status'] == 'complete'
        and outer['experiment_complete_sha256'] == OLD_RUN and previous['recipients'] == 320
        and previous['completed_fits'] == 35, 'completed original full320 experiment required')
    metadata = read_pinned(old/'run-v1/manifest.json',previous['files_sha256']['manifest.json'])
    prepared = read_pinned(project/job.LABELS/'COMPLETE.json',PREPARED)
    # Metadata only here: do NOT open assessment label bodies before prediction seal.
    inputs = {}; ownjobs = {}; ancestors = {}
    for fold in range(5):
        oldpin = previous['job_sha256'][str(fold)]
        oldjob = read_pinned(old/'jobs'/f'fold-{fold}.json',oldpin)
        scalerpin = previous['files_sha256'][f'fold-{fold}/SCALER.json']
        scaler = read_pinned(old/'run-v1'/f'fold-{fold}'/'SCALER.json',scalerpin)
        inputs[fold] = worker.capsule.decode_inputs(oldjob['inputs'])
        authority.require(inputs[fold].synthetic is False and inputs[fold].fold == fold, 'exact original production fold required')
        worker.previous.validate_transform(worker.previous.decode_transform(scaler),inputs[fold])
        contract = metadata['label_contracts'][str(fold)]
        authority.require(authority.same(contract,oldjob['own_label_contract'])
            and prepared['files_sha256'][f'fold-{fold}/train-labels.json'] == contract['expected_sha256'],
            'original own-label contract ancestry differs')
        ownjobs[fold] = dict(kind=job.KIND, fold=fold, inputs=oldjob['inputs'], transform=scaler,
            own_label_contract=contract, source_state=release['source_state'], source_sha256=release['source_sha256'],
            runtime=release['runtime'], controller_native=release['controller_native'], release_sha256=expected_release,
            original_job_sha256=oldpin, original_transform_sha256=scalerpin)
        ancestors[f'jobs/fold-{fold}.json'] = oldpin
        ancestors[f'run-v1/fold-{fold}/SCALER.json'] = scalerpin
    expected_ids = {e.example_id for e in inputs[0].examples}
    authority.require(len(expected_ids) == 320 and all({e.example_id for e in v.examples} == expected_ids for v in inputs.values()),
        'same full320 roster required')
    recheck(); run.mkdir(parents=True); jobs.mkdir(); supervisor.mkdir()
    jobpins = {str(f):worker.write(jobs/f'fold-{f}.json',ownjobs[f]) for f in range(5)}
    manifest_pin = worker.write(run/'manifest.json',dict(kind='bank_topset4131_run_v1',release_sha256=expected_release,
        original_outer_complete_sha256=OLD_OUTER, original_run_complete_sha256=OLD_RUN,
        original_inputs_sha256=ancestors, job_sha256=jobpins, methods=list(worker.METHODS),
        recipients=320, fits=35, candidate_execution=False, original_scaler_reused=True,
        automatic_retries=0, model_promotion=False, confirmatory=False))
    results = []; predictions = []; foldpins = {}
    def barrier():
        recheck()
        authority.require(authority.sha(run/'manifest.json') == manifest_pin, 'run manifest changed')
        for name,pin in ancestors.items(): authority.require(authority.sha(old/name) == pin, 'original own input changed')
        for fold in range(5): authority.require(authority.sha(jobs/f'fold-{fold}.json') == jobpins[str(fold)], 'own job changed')
        for fold,pin in foldpins.items():
            actual = verify_marker(run/f'fold-{fold}',required_files=worker.FILES)
            authority.require(actual['complete_sha256'] == pin, 'completed own fold changed')
    try:
        for fold in range(5):
            barrier()
            command = [sys.executable,'-B','-m','scripts.run_zpd_bank_topset_job','--project',str(project),
                '--fold',str(fold),'--expected-capsule-sha',jobpins[str(fold)]]
            result = bounded.run_child(command,name=f'fold-{fold}',cwd=authority.ROOT,
                stage_output=run/f'fold-{fold}',output=supervisor,timeout_seconds=3600,required_files=worker.FILES)
            results.append(result); foldpins[fold] = result['complete_sha256']; barrier()
            marker = read_pinned(run/f'fold-{fold}'/'COMPLETE.json',foldpins[fold])
            authority.require(marker['kind'] == worker.COMPLETE_KIND and marker['completed_fits'] == 7, 'seven completed fits required')
            rows = read_pinned(run/f'fold-{fold}'/'predictions.json',marker['files_sha256']['predictions.json'])
            authority.require([r['example_id'] for r in rows] == [e.example_id for e in worker.capsule.scope(inputs[fold])[1]],
                'exact original held order required')
            predictions.extend(rows)
            worker.write(run/f'STATUS-fold-{fold}.json',dict(phase='predicting',completed_examples=len(predictions),total_examples=320))
        authority.require(len(predictions) == 320 and {r['example_id'] for r in predictions} == expected_ids, 'exact full prediction coverage required')
        prediction_pin = worker.write(run/'predictions.json',predictions)
        prediction_seal = worker.write(run/'PREDICTIONS_COMPLETE.json',dict(status='complete',completed_fits=35,
            recipients=320,fold_complete_sha256={str(f):p for f,p in foldpins.items()},
            files_sha256={'predictions.json':prediction_pin,'manifest.json':manifest_pin}))
        barrier()
        def prediction_barrier():
            barrier()
            authority.require(authority.sha(run/'predictions.json') == prediction_pin
                and authority.sha(run/'PREDICTIONS_COMPLETE.json') == prediction_seal, 'sealed predictions changed')
        prediction_barrier()  # MUST precede the sole assessment-label read below.
        contract = metadata['label_contracts']['assessment']
        authority.require(prepared['files_sha256']['assessment/all320-labels.json'] == contract['expected_sha256'], 'assessment ancestry differs')
        label_path = project/job.LABELS/'assessment/all320-labels.json'
        envelope = read_pinned(label_path,contract['expected_sha256'])
        labels = provider.validate_assessment_envelope(envelope,inputs[0].banks,
            {e.example_id:e.bank_id for e in inputs[0].examples},
            expected_fold_assignment_sha256=contract['expected_fold_assignment_sha256'],
            expected_source_binding_sha256=contract['expected_source_binding_sha256'])
        choices = [{k:r[k] for k in worker.assessment.PREDICTION_FIELDS} for r in predictions]
        report = worker.assessment.assess(worker.capsule.validate_inputs(inputs[0]),choices,labels)
        report.update(methodology_intervention='bank_topset_objective_same4131_features_and_controls',
            predictions_complete_sha256=prediction_seal,completed_fits=35,model_promotion=False,
            independent_numerical_audit_required=True, educational_benefit_established=False)
        report_pin = worker.write(run/'report.json',report)
        worker.write(run/'STATUS.json',dict(phase='complete_pending_independent_audit',completed_examples=320,total_examples=320))
        pins = {name:authority.sha(run/name) for name in ('manifest.json','predictions.json','PREDICTIONS_COMPLETE.json','report.json','STATUS.json')}
        pins.update({f'STATUS-fold-{f}.json':authority.sha(run/f'STATUS-fold-{f}.json') for f in range(5)})
        pins.update({f'fold-{f}/'+name:authority.sha(run/f'fold-{f}'/name) for f in range(5) for name in (*worker.FILES,'COMPLETE.json')})
        prediction_barrier(); authority.require(authority.sha(label_path) == contract['expected_sha256'], 'assessment labels changed')
        run_pin = worker.write(run/'COMPLETE.json',dict(status='complete',kind='bank_topset4131_complete_v1',recipients=320,
            completed_fits=35,files_sha256=pins,scientific_gate_passed=report['gate']['passed'],
            report_sha256=report_pin,independent_audit_required=True,automatic_retries=0,model_promotion=False))
        prediction_barrier(); verify_marker(run,required_files=('report.json','PREDICTIONS_COMPLETE.json'))
        audit_command = [sys.executable,'-B','-m','scripts.audit_zpd_bank_topset_run',
            '--project',str(project),'--expected-run-sha',run_pin]
        audit_result = bounded.run_child(audit_command,name='audit',cwd=authority.ROOT,
            stage_output=root/'verified-v1',output=supervisor,timeout_seconds=3600,required_files=('report.json',))
        results.append(audit_result)
        audit_marker = read_pinned(root/'verified-v1/COMPLETE.json',audit_result['complete_sha256'])
        audit_report = read_pinned(root/'verified-v1/report.json',audit_marker['files_sha256']['report.json'])
        authority.require(audit_report['verified'] is True and audit_report['models'] == 35
            and audit_report['recipients'] == 320 and audit_report['experiment_complete_sha256'] == run_pin,
            'all35 new-model final-gradient audit required')
        worker.write(supervisor/'stages.json',results)
        worker.write(supervisor/'next_action.json',dict(action='inspect_verified_results_and_select_next_evidence_supported_intervention',
            gate=report['gate'],model_promotion=False,confirmatory=False,educational_benefit_established=False))
        bounded.event(supervisor,phase='complete',completed_oof_examples=320,total_oof_examples=320)
        outer_names = ('stages.json','next_action.json','STATUS.json','events.jsonl',
                       *(f'fold-{f}.log' for f in range(5)),'audit.log')
        outer_pins = {name:authority.sha(supervisor/name) for name in outer_names}
        def final_barrier():
            prediction_barrier(); verify_marker(run,required_files=('report.json',))
            authority.require(authority.sha(run/'COMPLETE.json') == run_pin, 'audited run completion changed')
            authority.require(verify_marker(root/'verified-v1',required_files=('report.json',))['complete_sha256']
                == audit_result['complete_sha256'], 'numerical audit changed')
            for f in range(5):
                authority.require(authority.sha(project/job.LABELS/f'fold-{f}'/'train-labels.json')
                    == metadata['label_contracts'][str(f)]['expected_sha256'], 'consumed own labels changed')
            authority.require(authority.sha(label_path) == contract['expected_sha256'], 'consumed assessment labels changed')
            authority.require(all(authority.sha(supervisor/name) == pin for name,pin in outer_pins.items()),
                'terminal supervisor outputs changed')
        final_barrier()
        outer_pin = worker.write(supervisor/'COMPLETE.json',dict(status='complete',completed_oof_examples=320,completed_fits=35,
            files_sha256=outer_pins,experiment_complete_sha256=run_pin,
            audit_complete_sha256=audit_result['complete_sha256'],release_sha256=expected_release,
            automatic_retries=0,model_promotion=False))
        final_barrier()
        authority.require(verify_marker(supervisor,required_files=outer_names)['complete_sha256'] == outer_pin,
            'outer completion changed after write')
        return report['gate']
    except BaseException as error:
        for directory in (run,supervisor):
            marker = directory/'COMPLETE.json'
            if marker.exists(): marker.rename(directory/'REJECTED_COMPLETE.json')
        worker.write(run/'FAILED.json',dict(status='failed',error_type=type(error).__name__,error=str(error),automatic_retries=0))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--expected-release-sha',required=True)
    args = parser.parse_args()
    print(json.dumps(supervise(args.project,args.expected_release_sha),sort_keys=True),flush=True)


if __name__ == '__main__': main()
