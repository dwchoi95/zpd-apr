"""Pure synthetic all-fold audit; no optimizer, real inputs, I/O or execution.

Whole-run certificates are analytic stationary cases: theta=0 for zero-X
pairs, or a closed-form one-coordinate solution. Exact sources remain distinct.
Neither is a fitted model, an actual trace reconstruction, or repair evidence.
Separate nonzero current-feature comparisons exercise the independent builder.
"""
import copy
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from scipy import sparse

from scripts import audit_zpd_joint_progress_independent as audit
from scripts import zpd_joint_progress_capsule as capsule
from scripts import zpd_joint_progress_features as features
from scripts import zpd_joint_progress_newton as solver
from scripts import zpd_joint_progress_assessment as assessment
from scripts import zpd_joint_progress_architecture as architecture
from scripts import run_zpd_joint_progress_cv as worker
from scripts import zpd_repair_structure as structural
from scripts.run_zpd_repair_feedback_cv import LabelContract
from src.repair.pilot_contracts import CandidateAttempt, CandidateBank, canonical_hash, source_hash
from tests.test_zpd_joint_progress_capsule import fixture as capsule_fixture
from tests.test_zpd_joint_progress_cv import fixture as varying_fixture
from tests.test_zpd_joint_progress_audit import array_sha, seal


RUNTIME = dict(python='synthetic', numpy='synthetic', scipy='synthetic')
BARRIER = 'e'*64


def stationary_certificate(matrix, y, weights, nonzero=False):
    """Construct zero-X or one-coordinate analytic stationary coefficients.

    For the latter z=log(3), a=z/sqrt(190*z/4) and theta=z/a. The supplied
    schema-consistent toy trace is not a claim that Newton actually ran.
    """
    x = matrix.copy(); x.sum_duplicates(); x.eliminate_zeros(); x.sort_indices()
    theta = np.zeros(4131)
    if nonzero: theta[4115] = math.sqrt(190.*math.log(3.)/4.)
    else: assert x.nnz == 0
    margin = (2*y-1)*(x@theta)
    gradient = theta+x.T@(-.1*weights*(2*y-1)/(1+np.exp(margin)))
    norm = float(np.max(np.abs(gradient))); norm2 = float(np.linalg.norm(gradient))
    assert norm <= 1e-8
    mass = math.fsum(map(float, weights)); initial = .1*mass*math.log(2.)
    loss = float(.1*(weights@np.logaddexp(0., -margin))); penalty = float(theta@theta)/2; value = loss+penalty
    if not nonzero: loss = value = initial  # The sole zero-update trace row is both initial and terminal.
    sq = np.asarray(x.multiply(x).sum(axis=1)).ravel(); weighted = math.fsum(float(a)*float(b) for a,b in zip(weights,sq))
    updates = int(nonzero); trace = []
    if nonzero:
        initial_g = x.T@(-.05*weights*(2*y-1))
        trace.append(dict(iteration=0, objective=initial, gradient_infinity_norm=float(np.max(np.abs(initial_g))),
            gradient_l2_norm=float(np.linalg.norm(initial_g)), a=1., q=1., r=0., alpha=1., normalized_solve_residual=0.))
    trace.append(dict(iteration=updates, objective=value, gradient_infinity_norm=norm, gradient_l2_norm=norm2))
    n = len(y)
    return seal(dict(configuration=audit.numeric.expected_configuration(audit.expected_spec()),
        coefficients=theta.tolist(), final_gradient=gradient.tolist(),
        training=dict(rows=n, unordered_pairs=n//2, positive_rows=int(y.sum()), zero_difference_rows=int(np.sum(sq == 0.)),
            weight_mass=mass, maximum_row_squared_norm=float(np.max(sq)), weighted_row_squared_norm_sum=weighted,
            strong_convexity_lower_bound=1., hessian_spectral_upper_bound=1.+.025*weighted,
            input_sha256=dict(features=array_sha(np.array(x.shape, dtype='<i8'), x.indptr.astype('<i8'),
                x.indices.astype('<i8'), x.data.astype('<f8')), labels=array_sha(y.astype('<i8')),
                weights=array_sha(weights.astype('<f8')), base_margin=array_sha(np.zeros(n, dtype='<f8')))),
        optimization=dict(status='converged_gradient', accepted=True, updates=updates, loop_evaluations=updates+1,
            hessian_evaluations=updates, linear_solves=updates, final_checks=1, total_evaluations=updates+2,
            initial_objective=initial, objective=value, weighted_logistic_loss=loss, l2_penalty=penalty,
            loop_gradient_infinity_norm=norm, loop_gradient_l2_norm=norm2, gradient_infinity_norm=norm,
            gradient_l2_norm=norm2, trace=trace), runtime=dict(RUNTIME)))


def fixture(n=10, *, synthetic=True, nonzero=False):
    seed = capsule_fixture(n, synthetic=synthetic)
    examples = []; banks = {}; raw = {}; labels = {}; phi = {a: {} for a in capsule.ARMS}
    for i, original in enumerate(seed.examples):
        current_code = b'pass\n'+b' '*(i % 5)
        current = replace(original.observation.current, source=current_code, source_sha256=source_hash(current_code))
        ex = replace(original, observation=replace(original.observation, current=current)); examples.append(ex)
        count = 6 if n == 320 and i < 16 else 7
        # Same byte length, lexical bag and AST, but distinct source identities.
        codes = [b'pass'+bytes(9 if j & (1 << bit) else 32 for bit in range(3))+b'\n' for j in range(count)]
        attempts = codes+[codes[-1]]*(8-len(codes))
        bank = CandidateBank(ex.observation.problem_id, current.source, 'a'*64, tuple(range(8)),
            tuple(CandidateAttempt(j, j, 'success', code) for j, code in enumerate(attempts)))
        banks[ex.bank_id] = bank; raw[ex.bank_id] = features.raw_current(ex, bank)
        ids = tuple(c.candidate_id for c in bank.candidates)
        for k, arm in enumerate(capsule.ARMS):
            values = np.zeros((len(ids), 32), dtype=np.float64)
            values[0, 5] = -0.; values[1:, 0] = .1
            if arm != 'CF':
                if nonzero: values[1::2, 16] = math.log(3.)/math.sqrt(190.*math.log(3.)/4.)
                else: values[1:, 16] = .02/(k+1)
            phi[arm][ex.bank_id] = capsule.CandidateBlock(ids, values)
        for j, cid in enumerate(ids):
            unknown = j == 0 and i % 10 not in (0, 1)
            all_ac = None if unknown else (True if i % 10 == 0 else False if i % 10 == 1 else j % 2 == 1)
            labels[ex.bank_id, cid] = dict(bank_id=ex.bank_id, candidate_id=cid,
                status='unknown' if unknown else 'stable', all_ac=all_ac,
                gain=None if unknown else 0., loss=None if unknown else 0.)
    examples = tuple(examples); inputs = {}; contracts = {}; ownlabels = {}; transforms = {}; models = {}; scalers = {}
    predictions = []
    for fold in range(5):
        train = tuple(ex for ex in examples if seed.assignment['example_fold'][ex.example_id] != fold)
        held = tuple(ex for ex in examples if seed.assignment['example_fold'][ex.example_id] == fold)
        trainbanks = {ex.bank_id: banks[ex.bank_id] for ex in train}
        ownlabels[fold] = {k: v for k, v in labels.items() if k[0] in trainbanks}
        _, _, _, _, info = structural.training_data(list(train), trainbanks, ownlabels[fold], 'C', 'structural')
        parents = []
        for ex in held:
            bank = banks[ex.bank_id]; ids = tuple(c.candidate_id for c in bank.candidates)
            scores = {m: {cid: float(j)/10 for j, cid in enumerate(ids)} for m in ('structural_C', 'lexical_C')}
            choices = {m: min(ids, key=lambda cid: (-scores[m][cid], cid)) for m in scores}
            choices.update(noop=source_hash(bank.current_source), first_attempt=source_hash(bank.attempts[0].source))
            parents.append(dict(example_id=ex.example_id, user_id=ex.user_id, bank_id=ex.bank_id,
                problem_id=bank.problem_id, fold=fold, bank_seal_sha256=bank.seal_sha256, choices=choices, candidate_scores=scores))
        part = capsule.FoldInputs(fold, examples, banks, seed.assignment, raw, phi, tuple(parents), info,
            hashlib.sha256(str(fold).encode()).hexdigest(), seed.fold_assignment_sha256, seed.readiness_complete_sha256, synthetic)
        inputs[fold] = part
        contract = LabelContract(hashlib.sha256(('labels'+str(fold)).encode()).hexdigest(), part.fold_assignment_sha256, 'f'*64)
        contracts[fold] = vars(contract)
        # Producer feature construction creates the supplied fixture, not the auditor's expected answer.
        transform = features.fit_own_scaler(train, trainbanks, {bid: raw[bid] for bid in trainbanks}, ownlabels[fold])
        transforms[fold] = transform; scalers[fold] = worker.transform_payload(transform)
        blocks = {bid: features.compose_blocks(raw[bid], transform, {a: phi[a][bid] for a in capsule.ARMS}) for bid in trainbanks}
        matrices = {a: features.mirrored_pairs(transform, {bid: blocks[bid][a] for bid in blocks})[0] for a in audit.ARMS}
        models[fold] = {a: worker._model(part, a, matrices[a], transform.weights,
            stationary_certificate(matrices[a], transform.y, transform.weights,
                nonzero and a not in ('CF', 'C_joint')), contract, transform) for a in audit.ARMS}
        # Actual producer prediction is pure supplied-model scoring, not fitting.
        predictions.extend(worker.predict_fold(part, models[fold], transform))
    cohort = capsule.validate_inputs(inputs[0])
    old_predictions = copy.deepcopy(predictions)
    for p in old_predictions:
        p.pop(audit.JOINT_FLAG); p[audit.OLD_FLAG] = True
        p['choices'].pop('C_joint'); p['candidate_scores'].pop('C_joint')
    projected = [{**{k: p[k] for k in audit.IDENTITIES}, 'choices': p['choices']} for p in predictions]
    report = assessment.assess(cohort, projected, labels)
    report.update(completed_fits=35, full_train_refits=0, model_promotion=False, predictions_complete_sha256=BARRIER,
        shared_theta_diagnostics=audit.old.shared_diagnostics(predictions), architecture_diagnostic=architecture.report(
            cohort, predictions, old_predictions, labels, reference_pins=audit.REFERENCE_PINS, synthetic=synthetic))
    return dict(fold_inputs=inputs, fold_models=models, scaler_payloads=scalers, predictions=predictions,
        train_labels_by_fold=ownlabels, assessment_labels=labels, report=report, old_predictions=old_predictions,
        reference_pins=dict(audit.REFERENCE_PINS), expected_input_fingerprint={f: capsule.fingerprint(v) for f, v in inputs.items()},
        expected_label_contracts=contracts, expected_runtime=dict(RUNTIME), expected_predictions_complete_sha256=BARRIER,
        synthetic=synthetic)


class JointFullRunAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data = fixture()

    def run_audit(self, data=None): return audit.audit_run(**(self.data if data is None else data))

    def test_analytic_whole_run_no_io_fit_or_new_producer_recalculation(self):
        with ExitStack() as stack:
            for owner, name in ((features, 'fit_own_scaler'), (features, 'mirrored_pairs'), (features, 'compose_blocks'),
                    (worker, 'predict_fold'), (solver, 'fit_joint'), (solver, 'validate_model'), (solver, '_evaluate'),
                    (assessment, 'assess'), (architecture, 'report')):
                stack.enter_context(patch.object(owner, name, side_effect=AssertionError('independent '+name)))
            stack.enter_context(patch('builtins.open', side_effect=AssertionError('no I/O')))
            stack.enter_context(patch.object(Path, 'read_bytes', side_effect=AssertionError('no bodies')))
            result = self.run_audit()
        self.assertEqual((result['recipients'], result['models'], result['methods']), (10, 35, 14))
        self.assertTrue(result['verified']); self.assertTrue(result['architecture_verified'])
        self.assertEqual(result['maximum_score_recompute_difference'], 0.)
        for key in ('fitting_performed', 'fitting_authorized', 'source_runtime_raw_artifact_provenance_verified',
                'accepted_progress32_feedback_ancestry_verified', 'actual_intermediate_newton_execution_verified',
                'complete_experiment_label_opening_barrier_verified'):
            self.assertIs(result[key], False)

    def test_original_nonzero_scaler_and_pair_bytes_match_independent_construction(self):
        inputs, labels = varying_fixture(); part = inputs[0]; train, _ = capsule.scope(part)
        banks = {ex.bank_id: part.banks[ex.bank_id] for ex in train}
        own = {k: v for k, v in labels.items() if k[0] in banks}
        transform = features.fit_own_scaler(train, banks, {bid: part.raw_current[bid] for bid in banks}, own)
        blocks = {bid: features.compose_blocks(part.raw_current[bid], transform,
            {a: part.interactions[a][bid] for a in capsule.ARMS}) for bid in banks}
        expected = {a: features.mirrored_pairs(transform, {bid: blocks[bid][a] for bid in blocks})[0] for a in audit.ARMS}
        reconstructed = audit.reconstruct(part, own)
        self.assertEqual(audit.feature_configuration(), features.configuration())
        self.assertEqual(reconstructed['scaler'], worker.transform_payload(transform))
        self.assertTrue(expected['H'].nnz)
        for arm in audit.ARMS:
            a, b = expected[arm].copy(), reconstructed['matrices'][arm].copy()
            for x in (a, b): x.eliminate_zeros(); x.sort_indices()
            self.assertEqual(a.data.tobytes(), b.data.tobytes()); self.assertTrue(np.array_equal(a.indices, b.indices))
            self.assertTrue(np.array_equal(a.indptr, b.indptr))

    def test_nonzero_analytic_thirtyfive_certificates_shared_theta_without_optimization(self):
        data = fixture(nonzero=True)
        with patch.object(solver, 'fit_joint', side_effect=AssertionError('no optimizer')):
            result = self.run_audit(data)
        self.assertTrue(result['verified']); self.assertEqual(result['models'], 35)
        self.assertTrue(any(p['candidate_scores']['H'] != p['candidate_scores']['shared_H_CF'] for p in data['predictions']))
        self.assertTrue(any(data['fold_models'][0]['H']['joint_model']['coefficients']))

    def test_independent_rational_assessment_varied_choices_and_unknown_bounds(self):
        cohort = capsule.validate_inputs(self.data['fold_inputs'][0]); rng = np.random.default_rng(20270925)
        for _ in range(12):
            predictions = []
            for row in cohort:
                choices = {m: row['candidate_ids'][int(rng.integers(len(row['candidate_ids'])))] for m in audit.METHODS}
                choices['noop'] = row['noop_candidate_id']
                predictions.append({**{k: row[k] for k in audit.IDENTITIES}, 'choices': choices})
            expected = assessment.assess(cohort, predictions, self.data['assessment_labels'])
            self.assertEqual(audit.independent_assessment(cohort, predictions, self.data['assessment_labels']), expected)

    def test_scaler_labels_and_external_authorities_reject_changes(self):
        cases = []
        def add(change):
            d = copy.deepcopy(self.data); change(d); cases.append(d)
        add(lambda d: d['scaler_payloads'][0]['numeric_scale'].__setitem__(0, 1.001))
        add(lambda d: d['scaler_payloads'][0]['y'].__setitem__(0, True))
        add(lambda d: d['scaler_payloads'][0]['row_keys'][0].reverse())
        add(lambda d: d['scaler_payloads'][0]['weights'].__setitem__(0, 1.))
        add(lambda d: d['expected_input_fingerprint'].__setitem__(0, '0'*64))
        add(lambda d: d['expected_label_contracts'][0].__setitem__('expected_sha256', '0'*64))
        add(lambda d: d['expected_runtime'].__setitem__('numpy', 'other'))
        add(lambda d: d['train_labels_by_fold'][0].pop(next(iter(d['train_labels_by_fold'][0]))))
        add(lambda d: d['fold_models'][0].pop('C_joint'))
        for i, data in enumerate(cases):
            with self.subTest(case=i), self.assertRaises(ValueError): self.run_audit(data)

    def test_resealed_numerical_model_and_near_tie_selected_SHA_rejected(self):
        data = copy.deepcopy(self.data); model = data['fold_models'][0]['H']
        model['joint_model']['coefficients'][0] = .01; seal(model['joint_model'])
        model['model_sha256'] = canonical_hash({k: v for k, v in model.items() if k != 'model_sha256'})
        with self.assertRaises(ValueError): self.run_audit(data)
        data = copy.deepcopy(self.data); p = data['predictions'][0]
        wrong = max(p['candidate_scores']['H']); p['candidate_scores']['H'][wrong] = 1e-12; p['choices']['H'] = wrong
        with self.assertRaisesRegex(ValueError, 'selected candidate'): self.run_audit(data)

    def test_exact_fraction_report_and_mandatory_architecture_not_optional(self):
        # Check reporting directly without paying for repeated35-certificate validation.
        data = self.data; cohort = capsule.validate_inputs(data['fold_inputs'][0])
        self.assertEqual(audit.independent_architecture(cohort, data['predictions'], data['old_predictions'],
            data['assessment_labels'], data['reference_pins'], True), data['report']['architecture_diagnostic'])
        expected = audit.independent_assessment(cohort, data['predictions'], data['assessment_labels'])
        self.assertEqual(expected, {k: data['report'][k] for k in expected})
        for key in ('architecture_diagnostic', 'shared_theta_diagnostics', 'predictions_complete_sha256'):
            changed = copy.deepcopy(data); changed['report'].pop(key)
            with self.subTest(key=key), self.assertRaises(ValueError): self.run_audit(changed)
        changed = copy.deepcopy(data); changed['old_predictions'].pop()
        with self.assertRaises(ValueError): self.run_audit(changed)

    def test_global_scope_and_rich_schema_reject_no_subset_or_extra_payload(self):
        for mode in ('fold', 'prediction', 'method', 'rich_extra', 'assessment', 'old_pin', 'barrier', 'bool_key'):
            d = copy.deepcopy(self.data)
            if mode == 'fold': d['fold_inputs'].pop(4)
            elif mode == 'prediction': d['predictions'].pop()
            elif mode == 'method': d['predictions'][0]['choices'].pop('CF')
            elif mode == 'rich_extra': d['predictions'][0]['global_model'] = {}
            elif mode == 'assessment': d['assessment_labels'].pop(next(iter(d['assessment_labels'])))
            elif mode == 'old_pin': d['reference_pins'].pop('prediction_seal_sha256')
            elif mode == 'barrier': d['expected_predictions_complete_sha256'] = 'wrong'
            else: d['fold_models'][True] = d['fold_models'].pop(1)
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.run_audit(d)

    def test_full_production_membership_320_23_2544_without_optimizer(self):
        # All objects are invented; the production membership checks stay on.
        data = fixture(320, synthetic=False)
        result = self.run_audit(data)
        self.assertEqual((result['recipients'], result['models'], result['methods']), (320, 35, 14))
        self.assertFalse(result['synthetic']); self.assertFalse(result['gate']['passed'])
        self.assertEqual(sum(f['held_prefixes'] for f in result['folds']), 320)
        changed = dict(data, reference_pins={**audit.REFERENCE_PINS, 'predictions_sha256': '0'*64})
        # Literal old production pin is checked independently even with a valid SHA shape.
        with self.assertRaises(ValueError): audit.independent_architecture(capsule.validate_inputs(data['fold_inputs'][0]),
            data['predictions'], data['old_predictions'], data['assessment_labels'], changed['reference_pins'], False)


if __name__ == '__main__': unittest.main()
