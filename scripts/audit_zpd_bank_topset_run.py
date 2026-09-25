"""Fresh final-gradient replay for the NEW completed top-set models, no refit.

Numerical arithmetic uses direct per-top feature contrasts, not the optimizer's
centered score derivatives, Hessian or evaluation helper. Feature/label-plan
authentication reuses the separately tested original capsule and new planner.
This is a float64 cross-check, not an interval or optimization-trace proof.
"""
from scripts import run_zpd_statement_sample_replay as launcher

import argparse
import math
from pathlib import Path
import numpy as np

from scripts import run_zpd_bank_topset_job as job
from scripts.supervise_zpd_history_action import verify_marker

worker = job.worker
authority = job.authority


def direct_value_gradient(theta, banks, weights):
    """Independent affine-LSE formula over raw rest-minus-top features."""
    gradient = theta.copy(); terms = []
    for bank, weight in zip(banks, weights, strict=True):
        rest = [i for i in range(len(bank.features)) if i not in bank.top_indices]
        if not rest or weight == 0.: continue
        for top in bank.top_indices:
            delta = bank.features[rest]-bank.features[top]
            logits = delta@theta-math.log(len(rest))
            if not np.isfinite(delta).all() or not np.isfinite(logits).all():
                raise FloatingPointError('independent contrast arithmetic nonfinite')
            maximum = max(0.,float(np.max(logits)))
            numerators = np.exp(logits-maximum)
            denominator = math.exp(-maximum)+math.fsum(map(float,numerators))
            factor = .1*float(weight)/len(bank.top_indices)
            terms.append(factor*(maximum+math.log(denominator)))
            gradient += factor*(delta.T@(numerators/denominator))
    penalty = .5*float(theta@theta); data = math.fsum(terms)
    if not np.isfinite(gradient).all() or not all(math.isfinite(v) for v in (penalty,data)):
        raise FloatingPointError('independent objective/gradient nonfinite')
    return penalty+data, gradient, data, penalty


def audit(project, expected_run):
    project = authority.canonical(project)
    authority.require(project == job.PROJECT and authority.preparation.is_sha(expected_run), 'fixed project/run SHA required')
    authority.verify_child_boundary()
    root = project/job.FAMILY; run = root/'run-v1'; output = root/'verified-v1'
    authority.require(not output.exists(), 'fresh independent numerical audit output required')
    authority.require(authority.sha(run/'COMPLETE.json') == expected_run, 'external completed run SHA differs')
    verify_marker(run,required_files=('report.json','PREDICTIONS_COMPLETE.json'))
    def read(path, pin):
        raw = authority.canonical(path).read_bytes()
        authority.require(authority.digest(raw) == pin, 'audit input SHA differs: '+str(path))
        return launcher.core.decode_json(raw)
    marker = read(run/'COMPLETE.json',expected_run)
    manifest = read(run/'manifest.json',marker['files_sha256']['manifest.json'])
    reports = []; label_pins = {}; audit_bindings = {}; source_payloads = []
    seen_held = set(); cohort_ids = None; seen_methods = set()
    for fold in range(5):
        jobpath = root/'jobs'/f'fold-{fold}.json'; jobpin = manifest['job_sha256'][str(fold)]
        payload = read(jobpath,jobpin)
        source_payloads.append(payload)
        authority.require(authority.same(authority.source_state(),payload['source_state'])
            and authority.same(authority.runtime(),payload['runtime'])
            and authority.same(authority.controller_native(),payload['controller_native']), 'audit source/runtime drift')
        job.check_sources(payload['source_sha256'])
        inputs = worker.capsule.decode_inputs(payload['inputs'])
        authority.require(inputs.fold == fold and inputs.synthetic is False
            and inputs.readiness_complete_sha256 == authority.READINESS_COMPLETE_SHA256,
            'audit needs exact own production fold/readiness')
        roster = {e.example_id for e in inputs.examples}
        authority.require(len(roster) == len(inputs.examples) == 320
            and (cohort_ids is None or roster == cohort_ids), 'audit full320 source roster differs')
        cohort_ids = roster
        transform = worker.previous.decode_transform(payload['transform'])
        train, held = worker.capsule.scope(inputs)
        held_ids = {e.example_id for e in held}
        authority.require(not (held_ids & seen_held) and len(held_ids) == len(held), 'held scope duplicates across folds')
        seen_held.update(held_ids)
        contract = worker.previous.LabelContract(**payload['own_label_contract'])
        labels = worker.labels.load_fold_labels(project/job.LABELS,fold,
            {e.bank_id:inputs.banks[e.bank_id] for e in train},
            {e.example_id:e.bank_id for e in train},**worker.contract_values(contract,inputs))
        label_pins[str(fold)] = contract.expected_sha256
        plan = worker.planner.build_plan(inputs,transform,labels); plan_payload = plan.payload()
        saved_plan = read(run/f'fold-{fold}'/'PLAN.json',marker['files_sha256'][f'fold-{fold}/PLAN.json'])
        authority.require(authority.same(saved_plan,plan_payload), 'replayed own masks/ancestry/coverage differ')
        models = {}
        for arm in worker.ARMS:
            relative = f'fold-{fold}/{arm}.json'
            outer = read(run/relative,marker['files_sha256'][relative])
            theta = worker.validate_model(outer,inputs,arm,transform,plan_payload)
            banks, weights = plan.banks(arm); model = outer['top_model']
            worker.solver.validate_model(model,expected_banks=banks,expected_weights=weights)
            value, gradient, data, penalty = direct_value_gradient(theta,banks,weights)
            norm = float(np.max(np.abs(gradient)))
            authority.require(norm <= 1e-8, 'independent full gradient exceeds unchanged1e-8')
            authority.require(np.allclose(gradient,model['final_gradient'],rtol=1e-10,atol=1e-10), 'independent gradient differs')
            for key,actual in (('objective',value),('weighted_bank_loss',data),('l2_penalty',penalty)):
                authority.require(math.isclose(actual,model['optimization'][key],rel_tol=1e-10,abs_tol=1e-10), 'independent objective decomposition differs')
            reports.append(dict(fold=fold,arm=arm,training_banks=len(train),objective=value,
                weighted_bank_loss=data,l2_penalty=penalty,gradient_infinity_norm=norm,
                maximum_gradient_difference=float(np.max(np.abs(gradient-np.asarray(model['final_gradient']))))))
            models[arm] = outer
        replay = worker.predict_fold(inputs,models,transform,plan_payload)
        saved = read(run/f'fold-{fold}'/'predictions.json',marker['files_sha256'][f'fold-{fold}/predictions.json'])
        authority.require(authority.same(replay,saved), 'all seven/shared/frozen held predictions differ')
        authority.require([r['example_id'] for r in saved] == [e.example_id for e in held]
            and all(set(r['choices']) == set(worker.METHODS) for r in saved), 'observed held/method coverage differs')
        seen_methods.update(m for r in saved for m in r['choices'])
        audit_bindings[str(jobpath)] = jobpin
    authority.require(len(reports) == 35 and len({(r['fold'],r['arm']) for r in reports}) == 35
        and seen_held == cohort_ids and len(seen_methods) == 14 and seen_methods == set(worker.METHODS),
        'exact all35 models/full320/fourteen methods required')
    def barrier():
        authority.verify_child_boundary()
        for payload in source_payloads:
            authority.require(authority.same(authority.source_state(),payload['source_state'])
                and authority.same(authority.runtime(),payload['runtime'])
                and authority.same(authority.controller_native(),payload['controller_native']), 'terminal audit source/runtime drift')
            job.check_sources(payload['source_sha256'])
        for directory in (run, output, *(run/f'fold-{f}' for f in range(5))):
            authority.require(not (directory/'FAILED.json').exists()
                and not any(directory.glob('REJECTED_*')), 'failed or rejected artifact cannot pass audit')
        # Source/native identity checks are consumers too. Recheck all consumed
        # data AFTER them; this is a drift guard, not an atomic filesystem proof.
        verify_marker(run,required_files=('report.json','PREDICTIONS_COMPLETE.json'))
        authority.require(authority.sha(run/'COMPLETE.json') == expected_run, 'completed run changed')
        for fold,pin in label_pins.items():
            authority.require(authority.sha(project/job.LABELS/f'fold-{fold}'/'train-labels.json') == pin, 'consumed own labels changed')
        for path,pin in audit_bindings.items(): authority.require(authority.sha(Path(path)) == pin, 'consumed job changed')
    barrier()
    output.mkdir()
    try:
        report_pin = worker.write(output/'report.json',dict(kind='bank_topset_direct_contrast_numerical_audit_v1',
            verified=True,models=len(reports),recipients=len(seen_held),methods=len(seen_methods),experiment_complete_sha256=expected_run,
            maximum_gradient_infinity_norm=max(r['gradient_infinity_norm'] for r in reports),models_replayed=reports,
            independent_arithmetic='raw_rest_minus_top_affine_logsumexp',feature_plan_reused=True,
            optimization_trace_reexecuted=False,interval_certificate=False,refits=0,model_promotion=False,
            own_training_label_sha256=label_pins,own_job_sha256=manifest['job_sha256']))
        barrier()
        complete_pin = worker.write(output/'COMPLETE.json',dict(status='complete',files_sha256={'report.json':report_pin},
            experiment_complete_sha256=expected_run,verified=True))
        barrier()
        authority.require(verify_marker(output,required_files=('report.json',))['complete_sha256'] == complete_pin,
            'audit completion drift after writing')
    except BaseException as error:
        if (output/'COMPLETE.json').exists(): (output/'COMPLETE.json').rename(output/'REJECTED_COMPLETE.json')
        if not (output/'FAILED.json').exists():
            worker.write(output/'FAILED.json',dict(status='failed',error_type=type(error).__name__,error=str(error),automatic_retries=0))
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--expected-run-sha',required=True)
    args = parser.parse_args(); audit(args.project,args.expected_run_sha)


if __name__ == '__main__': main()
